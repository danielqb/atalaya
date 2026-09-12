"""Prueba: simula un terremoto en Cali y retransmite los avisos criticos/altos por voz en Mumble.

Procesa los 6 eventos (3 dispositivos, 2 mensajes cada uno: reporte inicial y
actualizacion) de src/atalaya/data/sample_events_cali_terremoto.json contra un
puesto de mando ubicado en Cali (no el de Bogota que usa la API/dashboard por defecto).
Los eventos estan ordenados por dispositivo (Alpha-1, luego Bravo-2, luego Charlie-3)
para que la transmision por voz se escuche una unidad a la vez, no todas juntas, como
en un neto de radio real. Imprime el aviso tactico de cada uno y lo habla en el canal
Mumble configurado en .env para que cualquier cliente conectado (incluido ATAK por voz)
lo escuche.

Uso:
    uv run python scripts/simulate_cali_terremoto.py           # procesa y transmite por voz
    uv run python scripts/simulate_cali_terremoto.py --no-voice  # solo imprime, no conecta a Mumble
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from atalaya.core.models import CommandPost, GeoPoint  # noqa: E402
from atalaya.core.processor import process_cot_payload  # noqa: E402

PMU_CALI = CommandPost(
    callsign="PMU-Cali",
    position=GeoPoint(lat=3.4478, lon=-76.5305),
)

EVENTS_PATH = SRC_DIR / "atalaya" / "data" / "sample_events_cali_terremoto.json"


def main() -> int:
    speak = "--no-voice" not in sys.argv
    events = json.loads(EVENTS_PATH.read_text())

    bot = None
    if speak:
        from dotenv import load_dotenv

        load_dotenv()
        from audio.mumble_bot import TacticalVoiceBot

        bot = TacticalVoiceBot()
        bot.start()

    for payload in events:
        processed = process_cot_payload(payload, command_post=PMU_CALI).to_dict()
        print(
            f"[{processed['priority_label'].upper()}] {processed['callsign']} "
            f"-> {processed['headline']}"
        )
        print(f"  {processed['brief']}")
        print(f"  Accion sugerida: {processed['recommended_action']}")

        if bot and processed["priority"] in {"high", "critical"}:
            bot.speak_alert(processed)
            time.sleep(2.5)

    if bot:
        bot.stop()

    return 0


if __name__ == "__main__":
    exit_code = main()
    # pymumble corre en un hilo no-daemon que no siempre responde a stop() de
    # forma inmediata (bloqueado en el socket SSL); una vez transmitidos los
    # avisos el trabajo esta terminado, asi que forzamos la salida del proceso.
    import os

    os._exit(exit_code)
