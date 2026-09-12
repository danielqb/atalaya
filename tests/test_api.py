import asyncio

from fastapi import HTTPException

from atalaya.api.main import health, ingest_cot


def test_health() -> None:
    response = health()

    assert response["status"] == "ok"


def test_ingest_cot_endpoint() -> None:
    body = asyncio.run(
        ingest_cot(
            {
                "uid": "test-casevac-001",
                "type": "CASEVAC",
                "callsign": "Alpha-2",
                "lat": 4.7111,
                "lon": -74.0721,
                "time": "2026-09-12T16:25:00Z",
                "detail": {
                    "message": "1 herido, sangrado moderado, requiere extraccion",
                    "priority": "high",
                },
            }
        )
    )

    assert body["callsign"] == "Alpha-2"
    assert body["accepted"] is True
    assert body["distance_m"] > 0


def test_ingest_rejects_invalid_payload() -> None:
    try:
        asyncio.run(ingest_cot({"type": "CASEVAC"}))
    except HTTPException as exc:
        assert exc.status_code == 422
        assert "uid is required" in exc.detail
    else:
        raise AssertionError("invalid payload should raise HTTPException")
