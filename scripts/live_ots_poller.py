"""Poller en vivo: cada pocos segundos revisa los CoT mas recientes de OTS y
publica los que no se han visto contra la API de Atalaya (POST /api/cot), que
ya se encarga de normalizar, guardar en el feed y hablar por Mumble si aplica.

Al arrancar, marca como 'vistos' todos los CoT existentes sin publicarlos, para
no re-hablar el historial completo; solo reacciona a eventos nuevos desde que
el poller esta corriendo.

Uso:
    uv run python scripts/live_ots_poller.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

load_dotenv()

from atalaya.core.models import EventValidationError  # noqa: E402
from atalaya.data_sources.opentak import (  # noqa: E402
    OpenTAKServerClient,
    OpenTAKServerConfig,
    OpenTAKServerError,
    cot_record_to_atalaya_payload,
)

ATALAYA_API_URL = "http://localhost:8000"
POLL_INTERVAL_S = 4
# fetch_cot() pagina en orden ascendente por id (mas viejo primero) y no expone
# sort_by/sort_direction de forma confiable (probado: rompe la query y devuelve
# vacio). Para una demo de pocas horas basta un per_page grande para traer todo
# el historial en una sola pagina; el dedup por uid evita re-hablar lo viejo.
PER_PAGE = 500


def fetch_and_normalize(client: OpenTAKServerClient) -> list[dict]:
    """Devuelve los payloads ya normalizados (formato atalaya), en el mismo
    orden que entrega OTS. record.get("uid") viene vacio para CASEVAC/marker
    (el CoT.uid de nivel superior no se llena); cot_record_to_atalaya_payload
    ya resuelve el uid real (alert.uid o point.uid), asi que normalizamos aqui
    una sola vez y usamos ese uid tanto para el seeding como para el dedup.
    """
    records = client.fetch_cot(page=1, per_page=PER_PAGE)
    normalized = []
    for record in records:
        try:
            normalized.append(cot_record_to_atalaya_payload(record))
        except EventValidationError:
            continue
    return normalized


def main() -> int:
    client = OpenTAKServerClient(OpenTAKServerConfig.from_env())

    try:
        initial = fetch_and_normalize(client)
    except OpenTAKServerError as exc:
        print(f"No se pudo hacer el fetch inicial contra OTS: {exc}")
        return 1

    seen_uids = {payload["uid"] for payload in initial}
    print(f"Poller listo. {len(seen_uids)} CoT existentes marcados como ya vistos. Escuchando eventos nuevos...")

    while True:
        try:
            payloads = fetch_and_normalize(client)
        except OpenTAKServerError as exc:
            print(f"Error consultando OTS: {exc}")
            time.sleep(POLL_INTERVAL_S)
            continue

        for payload in payloads:
            uid = payload["uid"]
            if uid in seen_uids:
                continue
            seen_uids.add(uid)

            try:
                resp = requests.post(f"{ATALAYA_API_URL}/api/cot", json=payload, timeout=15)
                resp.raise_for_status()
                event = resp.json()
                print(f"[{event['priority_label'].upper()}] {event['callsign']} -> {event['headline']}")
            except requests.RequestException as exc:
                print(f"No se pudo publicar el evento {uid} en la API de Atalaya: {exc}")

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    raise SystemExit(main())
