from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

Priority = Literal["low", "medium", "high", "critical"]
PRIORITY_LABELS_ES = {
    "low": "baja",
    "medium": "media",
    "high": "alta",
    "critical": "critica",
}


class EventValidationError(ValueError):
    """Raised when an inbound tactical event cannot be normalized."""


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float


@dataclass(frozen=True)
class CommandPost:
    callsign: str
    position: GeoPoint


@dataclass(frozen=True)
class TacticalEvent:
    uid: str
    event_type: str
    callsign: str
    position: GeoPoint
    time: datetime
    message: str
    priority: Priority
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_cot_payload(cls, payload: dict[str, Any]) -> TacticalEvent:
        detail = payload.get("detail") or {}
        if not isinstance(detail, dict):
            raise EventValidationError("detail must be an object")

        uid = _required_string(payload, "uid")
        event_type = _required_string(payload, "type").upper()
        callsign = _required_string(payload, "callsign")
        message = str(detail.get("message") or "").strip()
        if not message:
            raise EventValidationError("detail.message is required")

        priority = _normalize_priority(detail.get("priority"))
        lat = _required_float(payload, "lat")
        lon = _required_float(payload, "lon")
        event_time = _parse_time(_required_string(payload, "time"))

        return cls(
            uid=uid,
            event_type=event_type,
            callsign=callsign,
            position=GeoPoint(lat=lat, lon=lon),
            time=event_time,
            message=message,
            priority=priority,
            raw=payload,
        )


@dataclass(frozen=True)
class GeoAssessment:
    distance_m: int
    bearing_deg: int
    relative_direction: str


@dataclass(frozen=True)
class TacticalBrief:
    headline: str
    brief: str
    priority: Priority
    recommended_action: str
    llm_used: bool


@dataclass(frozen=True)
class ProcessedEvent:
    event: TacticalEvent
    geo: GeoAssessment
    tactical_brief: TacticalBrief
    accepted: bool
    decision_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.event.uid,
            "type": self.event.event_type,
            "callsign": self.event.callsign,
            "lat": self.event.position.lat,
            "lon": self.event.position.lon,
            "time": self.event.time.isoformat(),
            "message": self.event.message,
            "priority": self.event.priority,
            "priority_label": PRIORITY_LABELS_ES[self.event.priority],
            "distance_m": self.geo.distance_m,
            "bearing_deg": self.geo.bearing_deg,
            "relative_direction": self.geo.relative_direction,
            "headline": self.tactical_brief.headline,
            "brief": self.tactical_brief.brief,
            "recommended_action": self.tactical_brief.recommended_action,
            "llm_used": self.tactical_brief.llm_used,
            "accepted": self.accepted,
            "decision_reason": self.decision_reason,
        }


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EventValidationError(f"{key} is required")
    return value.strip()


def _required_float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EventValidationError(f"{key} must be a number") from exc


def _normalize_priority(value: Any) -> Priority:
    normalized = str(value or "medium").lower().strip()
    if normalized in {"low", "medium", "high", "critical"}:
        return normalized  # type: ignore[return-value]
    return "medium"


def _parse_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EventValidationError("time must be ISO-8601") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
