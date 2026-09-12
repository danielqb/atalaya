from __future__ import annotations

import json
import os
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib import parse, request
from xml.etree import ElementTree

from atalaya.core.models import EventValidationError


class OpenTAKServerError(RuntimeError):
    """Raised when OpenTAKServer cannot be reached or returns unusable data."""


@dataclass
class OpenTAKServerConfig:
    base_url: str
    map_url: str | None = None
    username: str | None = None
    password: str | None = None
    auth_token: str | None = None
    verify_tls: bool = True
    timeout_s: float = 10

    @classmethod
    def from_env(cls) -> OpenTAKServerConfig:
        base_url = os.getenv("OTS_BASE_URL", "").strip()
        if not base_url:
            raise OpenTAKServerError("OTS_BASE_URL is required")

        return cls(
            base_url=base_url,
            map_url=os.getenv("OTS_MAP_URL") or base_url,
            username=os.getenv("OTS_USERNAME") or None,
            password=os.getenv("OTS_PASSWORD") or None,
            auth_token=os.getenv("OTS_AUTH_TOKEN") or None,
            verify_tls=os.getenv("OTS_VERIFY_TLS", "true").lower() != "false",
            timeout_s=float(os.getenv("OTS_TIMEOUT_S", "10")),
        )


class OpenTAKServerClient:
    def __init__(self, config: OpenTAKServerConfig):
        self.config = config

    def health(self) -> dict[str, Any]:
        return self._json_request("GET", "/api/health", auth=False)

    def login(self) -> str:
        if not self.config.username or not self.config.password:
            raise OpenTAKServerError("OTS_USERNAME and OTS_PASSWORD are required for login")

        response = self._json_request(
            "POST",
            "/api/login",
            query={"include_auth_token": ""},
            body={
                "username": self.config.username,
                "password": self.config.password,
            },
            auth=False,
        )
        token = (
            response.get("response", {})
            .get("user", {})
            .get("authentication_token")
        )
        if not token:
            raise OpenTAKServerError("OpenTAKServer login did not return authentication_token")
        self.config.auth_token = str(token)
        return self.config.auth_token

    def fetch_cot(self, page: int = 1, per_page: int = 20) -> list[dict[str, Any]]:
        response = self._json_request(
            "GET",
            "/api/cot",
            query={"page": str(page), "per_page": str(per_page)},
        )
        results = response.get("results")
        if not isinstance(results, list):
            raise OpenTAKServerError("OpenTAKServer /api/cot response did not include results")
        return results

    def fetch_map_state(self) -> dict[str, Any]:
        return self._json_request("GET", "/api/map_state")

    def post_marker(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request("POST", "/api/markers", body=payload)

    def post_casevac(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request("POST", "/api/casevac", body=payload)

    def publish_tactical_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_type = str(payload.get("type") or "UNKNOWN").upper()
        if event_type == "CASEVAC":
            return {
                "target": "/api/casevac",
                "response": self.post_casevac(tactical_payload_to_casevac(payload)),
            }

        return {
            "target": "/api/markers",
            "response": self.post_marker(tactical_payload_to_marker(payload)),
        }

    def _json_request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        url = self._url(path, query)
        headers = {"Accept": "application/json"}
        data = None

        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if auth:
            token = self.config.auth_token or self.login()
            headers["Authentication-Token"] = token
            headers["Authorization"] = f"Bearer {token}"

        req = request.Request(url, data=data, headers=headers, method=method)

        try:
            with request.urlopen(
                req,
                timeout=self.config.timeout_s,
                context=self._ssl_context(),
            ) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:
            raise OpenTAKServerError(f"OpenTAKServer request failed: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenTAKServerError("OpenTAKServer returned non-JSON response") from exc

        if not isinstance(parsed, dict):
            raise OpenTAKServerError("OpenTAKServer returned unexpected JSON shape")
        return parsed

    def _url(self, path: str, query: dict[str, str] | None) -> str:
        base = self.config.base_url.rstrip("/")
        url = f"{base}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        return url

    def _ssl_context(self) -> ssl.SSLContext | None:
        if self.config.verify_tls:
            return None
        return ssl._create_unverified_context()


def cot_record_to_atalaya_payload(record: dict[str, Any]) -> dict[str, Any]:
    point = _extract_point(record)
    if not point:
        raise EventValidationError("OTS CoT record does not include point coordinates")

    uid = str(
        record.get("uid") or _nested(record, "alert", "uid") or point.get("uid") or ""
    ).strip()
    if not uid:
        raise EventValidationError("OTS CoT record does not include uid")

    callsign = str(
        record.get("sender_callsign")
        or point.get("callsign")
        or _nested(record, "alert", "callsign")
        or record.get("sender_uid")
        or "Unknown"
    ).strip()

    event_type = _classify_event_type(record)
    message = _extract_message(record, event_type)
    priority = _infer_priority(event_type, record, message)
    timestamp = _extract_timestamp(record, point)

    return {
        "uid": uid,
        "type": event_type,
        "callsign": callsign,
        "lat": point["lat"],
        "lon": point["lon"],
        "time": timestamp,
        "detail": {
            "message": message,
            "priority": priority,
            "ots_type": record.get("type"),
            "sender_uid": record.get("sender_uid"),
        },
    }


def tactical_payload_to_marker(payload: dict[str, Any]) -> dict[str, Any]:
    detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else {}
    return {
        "uid": _required_payload_string(payload, "uid"),
        "name": _marker_name(payload),
        "type": _marker_cot_type(payload),
        "latitude": _required_payload_float(payload, "lat"),
        "longitude": _required_payload_float(payload, "lon"),
        "ce": 10,
        "le": 10,
        "hae": 0,
        "remarks": str(detail.get("message") or "").strip(),
    }


def tactical_payload_to_casevac(payload: dict[str, Any]) -> dict[str, Any]:
    detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else {}
    priority = str(detail.get("priority") or "high").lower()
    urgent = 1 if priority in {"critical", "high"} else 0

    return {
        "uid": _required_payload_string(payload, "uid"),
        "title": _marker_name(payload),
        "latitude": _required_payload_float(payload, "lat"),
        "longitude": _required_payload_float(payload, "lon"),
        "casevac": True,
        "urgent": urgent,
        "routine": 0 if urgent else 1,
        "priority": 1 if priority == "critical" else 2,
        "medline_remarks": str(detail.get("message") or "").strip(),
        "marked_by": str(payload.get("callsign") or "Atalaya"),
    }


def _marker_name(payload: dict[str, Any]) -> str:
    event_type = str(payload.get("type") or "UNKNOWN").upper()
    callsign = str(payload.get("callsign") or "Atalaya").strip()
    return f"{event_type} - {callsign}"


def _marker_cot_type(payload: dict[str, Any]) -> str:
    event_type = str(payload.get("type") or "").upper()
    if event_type == "HAZARD":
        return "a-u-G"
    if event_type == "FINDING":
        return "a-f-G"
    if event_type == "CHAT":
        return "a-u-G"
    return "a-f-G"


def _extract_point(record: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        record.get("point"),
        _nested(record, "alert", "point"),
        _nested(record, "casevac", "point"),
    ]

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        lat = candidate.get("latitude") or candidate.get("lat")
        lon = candidate.get("longitude") or candidate.get("lon")
        if lat is not None and lon is not None:
            return {
                "uid": candidate.get("uid"),
                "callsign": candidate.get("callsign"),
                "timestamp": candidate.get("timestamp"),
                "lat": float(lat),
                "lon": float(lon),
            }

    return _extract_point_from_xml(record.get("xml"))


def _required_payload_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EventValidationError(f"{key} is required")
    return value.strip()


def _required_payload_float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EventValidationError(f"{key} must be a number") from exc


def _extract_point_from_xml(xml: Any) -> dict[str, Any] | None:
    if not isinstance(xml, str) or not xml.strip():
        return None

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return None

    point = root.find("point")
    if point is None:
        return None

    lat = point.attrib.get("lat")
    lon = point.attrib.get("lon")
    if lat is None or lon is None:
        return None

    contact = root.find("./detail/contact")
    return {
        "uid": root.attrib.get("uid"),
        "callsign": contact.attrib.get("callsign") if contact is not None else None,
        "timestamp": root.attrib.get("time") or root.attrib.get("start"),
        "lat": float(lat),
        "lon": float(lon),
    }


def _classify_event_type(record: dict[str, Any]) -> str:
    cot_type = str(record.get("type") or "").lower()
    alert = record.get("alert")

    if record.get("casevac"):
        return "CASEVAC"
    if isinstance(alert, dict):
        alert_type = str(alert.get("alert_type") or "").lower()
        if "casevac" in alert_type:
            return "CASEVAC"
        return "ALERT"
    if cot_type.startswith("b-a"):
        return "ALERT"
    if cot_type.startswith("a-"):
        return "POSITION"
    return str(record.get("type") or "UNKNOWN").upper()


def _extract_message(record: dict[str, Any], event_type: str) -> str:
    alert_type = _nested(record, "alert", "alert_type")
    if alert_type:
        return f"Alerta OTS recibida: {alert_type}"

    xml_message = _extract_remarks_from_xml(record.get("xml"))
    if xml_message:
        return xml_message

    cot_type = record.get("type") or "sin tipo CoT"
    sender = record.get("sender_callsign") or record.get("sender_uid") or "fuente desconocida"
    return f"Evento {event_type} recibido desde OpenTAKServer ({cot_type}) por {sender}"


def _extract_remarks_from_xml(xml: Any) -> str | None:
    if not isinstance(xml, str) or not xml.strip():
        return None

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return None

    remarks = root.find("./detail/remarks")
    if remarks is not None and remarks.text:
        return remarks.text.strip()
    return None


def _infer_priority(event_type: str, record: dict[str, Any], message: str) -> str:
    combined = " ".join(
        [
            event_type,
            str(record.get("type") or ""),
            str(_nested(record, "alert", "alert_type") or ""),
            message,
        ]
    ).lower()

    if event_type == "CASEVAC" or any(term in combined for term in ["critical", "emergency"]):
        return "critical"
    if event_type == "ALERT" or any(term in combined for term in ["danger", "hazard", "riesgo"]):
        return "high"
    if event_type == "POSITION":
        return "low"
    return "medium"


def _extract_timestamp(record: dict[str, Any], point: dict[str, Any]) -> str:
    timestamp = (
        record.get("timestamp")
        or record.get("start")
        or point.get("timestamp")
        or datetime.now(UTC).isoformat()
    )
    return str(timestamp).replace("Z", "+00:00")


def _nested(record: dict[str, Any], *keys: str) -> Any:
    value: Any = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value
