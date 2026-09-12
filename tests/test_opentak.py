from atalaya.data_sources.opentak import cot_record_to_atalaya_payload


def test_cot_record_with_nested_point() -> None:
    payload = cot_record_to_atalaya_payload(
        {
            "uid": "cot-001",
            "type": "a-f-G-U-C",
            "sender_callsign": "Alpha-2",
            "sender_uid": "device-alpha",
            "timestamp": "2026-09-12T16:25:00+00:00",
            "point": {
                "uid": "point-001",
                "latitude": 4.7111,
                "longitude": -74.0721,
                "callsign": "Alpha-2",
            },
        }
    )

    assert payload["uid"] == "cot-001"
    assert payload["type"] == "POSITION"
    assert payload["callsign"] == "Alpha-2"
    assert payload["lat"] == 4.7111
    assert payload["lon"] == -74.0721
    assert payload["detail"]["priority"] == "low"


def test_cot_record_with_alert() -> None:
    payload = cot_record_to_atalaya_payload(
        {
            "uid": "cot-alert-001",
            "type": "b-a-o-tbl",
            "sender_callsign": "Charlie-3",
            "timestamp": "2026-09-12T16:29:00+00:00",
            "alert": {
                "uid": "alert-001",
                "alert_type": "hazard",
                "callsign": "Charlie-3",
                "point": {
                    "latitude": 4.714,
                    "longitude": -74.086,
                },
            },
        }
    )

    assert payload["type"] == "ALERT"
    assert payload["detail"]["priority"] == "high"
    assert "hazard" in payload["detail"]["message"]


def test_cot_record_with_xml_point_and_remarks() -> None:
    payload = cot_record_to_atalaya_payload(
        {
            "type": "b-a-o-tbl",
            "sender_uid": "device-bravo",
            "xml": """
                <event version="2.0" uid="xml-001" type="b-a-o-tbl"
                    time="2026-09-12T16:30:00Z">
                  <point lat="4.7065" lon="-74.0832" hae="0" ce="10" le="10" />
                  <detail>
                    <contact callsign="Bravo-1" />
                    <remarks>Persona localizada consciente, movilidad limitada</remarks>
                  </detail>
                </event>
            """,
        }
    )

    assert payload["uid"] == "xml-001"
    assert payload["callsign"] == "Bravo-1"
    assert payload["type"] == "ALERT"
    assert payload["lat"] == 4.7065
    assert payload["detail"]["message"] == "Persona localizada consciente, movilidad limitada"


def test_cot_record_with_casevac() -> None:
    payload = cot_record_to_atalaya_payload(
        {
            "uid": "cot-casevac-001",
            "type": "b-r-f-h-c",
            "sender_callsign": "Medic-1",
            "timestamp": "2026-09-12T16:35:00+00:00",
            "casevac": {
                "point": {
                    "latitude": 4.713,
                    "longitude": -74.081,
                },
            },
        }
    )

    assert payload["type"] == "CASEVAC"
    assert payload["detail"]["priority"] == "critical"
