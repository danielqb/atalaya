from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib import request


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    events_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "atalaya"
        / "data"
        / "sample_events.json"
    )
    events = json.loads(events_path.read_text())

    for event in events:
        payload = json.dumps(event).encode("utf-8")
        req = request.Request(
            f"{base_url}/api/cot",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=10) as response:
            processed = json.loads(response.read().decode("utf-8"))
        print(f"{processed['callsign']} -> {processed['headline']}")
        time.sleep(0.8)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
