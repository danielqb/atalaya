from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from atalaya.core.models import EventValidationError
from atalaya.core.processor import process_cot_payload
from atalaya.data_sources.opentak import (
    OpenTAKServerClient,
    OpenTAKServerConfig,
    OpenTAKServerError,
    cot_record_to_atalaya_payload,
)

app = FastAPI(title="Atalaya Tactical Event API", version="0.1.0")

EVENTS: list[dict[str, Any]] = []
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "atalaya"}


@app.get("/api/ots/config")
def ots_config() -> dict[str, Any]:
    try:
        config = OpenTAKServerConfig.from_env()
    except OpenTAKServerError:
        return {"configured": False}

    return {
        "configured": True,
        "base_url": config.base_url,
        "has_token": bool(config.auth_token),
        "has_credentials": bool(config.username and config.password),
        "verify_tls": config.verify_tls,
    }


@app.get("/api/ots/health")
def ots_health() -> dict[str, Any]:
    try:
        client = OpenTAKServerClient(OpenTAKServerConfig.from_env())
        return {"ok": True, "response": client.health()}
    except OpenTAKServerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/ots/sync")
def sync_ots_cot(page: int = 1, per_page: int = 20) -> dict[str, Any]:
    try:
        client = OpenTAKServerClient(OpenTAKServerConfig.from_env())
        records = client.fetch_cot(page=page, per_page=per_page)
    except OpenTAKServerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    processed = []
    skipped = []
    for record in records:
        try:
            payload = cot_record_to_atalaya_payload(record)
            event = process_cot_payload(payload).to_dict()
        except (EventValidationError, ValueError) as exc:
            skipped.append({"uid": record.get("uid"), "reason": str(exc)})
            continue
        EVENTS.insert(0, event)
        processed.append(event)

    return {"events": processed, "skipped": skipped}


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
