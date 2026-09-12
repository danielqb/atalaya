"""Utilidad local de una sola vez: crea el usuario de servicio 'atalaya-listener' en OTS.

Se loguea como admin (contra OTS directo en :8081, sin pasar por el proxy nginx),
crea el usuario con rol 'user', y escribe las credenciales generadas en .env
(gitignorado) bajo OTS_USERNAME / OTS_PASSWORD.
"""

import os
import secrets
import sys

import requests

OTS_BASE_URL = "http://localhost:8081"
SERVICE_USERNAME = "atalaya_listener"
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")


def main():
    password = secrets.token_urlsafe(18)

    session = requests.Session()
    login = session.post(
        f"{OTS_BASE_URL}/api/login",
        json={"username": "administrator", "password": "password"},
    )
    login.raise_for_status()
    csrf_token = login.json()["response"]["csrf_token"]

    resp = session.post(
        f"{OTS_BASE_URL}/api/user/add",
        json={
            "username": SERVICE_USERNAME,
            "password": password,
            "confirm_password": password,
            "roles": ["user"],
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    print("status:", resp.status_code)
    print(resp.text[:500])

    if resp.status_code not in (200, 201):
        sys.exit(1)

    with open(ENV_PATH, "a") as f:
        f.write(f"\nOTS_USERNAME={SERVICE_USERNAME}\n")
        f.write(f"OTS_PASSWORD={password}\n")
        f.write("OTS_BASE_URL=http://localhost:8081\n")

    print(f"Usuario '{SERVICE_USERNAME}' creado. Credenciales agregadas a {ENV_PATH}")


if __name__ == "__main__":
    main()
