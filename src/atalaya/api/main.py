from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from atalaya.core.models import EventValidationError
from atalaya.core.processor import process_cot_payload

app = FastAPI(title="Atalaya Tactical Event API", version="0.1.0")

EVENTS: list[dict[str, Any]] = []
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "atalaya"}


@app.post("/api/cot")
async def ingest_cot(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        processed = process_cot_payload(payload)
    except EventValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    event = processed.to_dict()
    EVENTS.insert(0, event)
    return event


@app.get("/api/events")
def list_events() -> dict[str, Any]:
    return {"events": EVENTS}


@app.post("/api/events/reset")
def reset_events() -> dict[str, Any]:
    EVENTS.clear()
    return {"events": EVENTS}


@app.post("/api/simulate")
def simulate_events() -> dict[str, Any]:
    sample_events = json.loads((DATA_DIR / "sample_events.json").read_text())
    processed = []
    for payload in sample_events:
        event = process_cot_payload(payload).to_dict()
        EVENTS.insert(0, event)
        processed.append(event)
    return {"events": processed}


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return (STATIC_DIR / "dashboard.html").read_text()
