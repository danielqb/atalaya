"""Genera un evento CASEVAC real contra la API de OTS para probar el listener
end-to-end (login -> POST /api/casevac -> OTS emite socketio 'casevac').

Uso: .venv/bin/python scripts/simulate_casevac.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone

import requests

OTS_BASE_URL = os.environ.get("OTS_BASE_URL", "http://localhost:8081")
USERNAME = os.environ.get("OTS_USERNAME", "atalaya_listener")
PASSWORD = os.environ["OTS_PASSWORD"]


def main():
    session = requests.Session()
    login = session.post(
        f"{OTS_BASE_URL}/api/login", json={"username": USERNAME, "password": PASSWORD}
    )
    login.raise_for_status()
    csrf_token = login.json()["response"]["csrf_token"]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    payload = {
        "uid": str(uuid.uuid4()),
        "latitude": 4.7111,
        "longitude": -74.0721,
        "timestamp": now,
        "title": "Alpha-2: 1 herido, sangrado moderado, requiere extraccion",
        "casevac": True,
        "urgent": 1,
        "us_military": 1,
    }
    resp = session.post(
        f"{OTS_BASE_URL}/api/casevac",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )
    print("status:", resp.status_code)
    print(resp.text[:800])
    if not resp.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
