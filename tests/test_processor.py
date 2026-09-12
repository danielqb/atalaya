from atalaya.core.processor import process_cot_payload


def test_process_casevac_payload() -> None:
    processed = process_cot_payload(
        {
            "uid": "demo-casevac-001",
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

    assert processed.accepted is True
    assert processed.event.event_type == "CASEVAC"
    assert processed.tactical_brief.priority == "high"
    assert processed.to_dict()["priority_label"] == "alta"
    assert "Alpha-2" in processed.tactical_brief.brief
    assert "extraccion" in processed.tactical_brief.recommended_action


def test_process_chat_as_noise() -> None:
    processed = process_cot_payload(
        {
            "uid": "demo-noise-001",
            "type": "CHAT",
            "callsign": "Unknown",
            "lat": 4.7101,
            "lon": -74.0801,
            "time": "2026-09-12T16:30:00Z",
            "detail": {
                "message": "probando radio, ignora este mensaje",
                "priority": "low",
            },
        }
    )

    assert processed.accepted is False
    assert "baja prioridad" in processed.tactical_brief.headline.lower()
