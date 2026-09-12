"""Utilidad local de una sola vez: loguea como admin de OTS y guarda cookies de sesion.

No se versiona en git como parte del pipeline (vive en scripts/ para uso manual del dev).
"""

import json
import sys

import requests

BASE_URL = "http://localhost:8080"


def main():
    session = requests.Session()
    resp = session.post(
        f"{BASE_URL}/api/login",
        json={"username": "administrator", "password": "password"},
    )
    print("status:", resp.status_code)
    print(resp.text[:500])
    if resp.ok:
        with open("/tmp/ots_admin_session.json", "w") as f:
            json.dump(requests.utils.dict_from_cookiejar(session.cookies), f)
        print("cookies guardadas en /tmp/ots_admin_session.json")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
