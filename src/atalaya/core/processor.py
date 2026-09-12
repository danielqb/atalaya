from __future__ import annotations

from atalaya.core.briefing import generate_tactical_brief
from atalaya.core.geo import assess_relative_position
from atalaya.core.models import CommandPost, GeoPoint, ProcessedEvent, TacticalEvent

DEFAULT_COMMAND_POST = CommandPost(
    callsign="Command",
    position=GeoPoint(lat=4.7100, lon=-74.0800),
)


def should_accept(event: TacticalEvent) -> tuple[bool, str]:
    if event.event_type == "CHAT":
        return False, "mensaje operativo de baja prioridad"
    if event.priority == "low":
        return False, "prioridad baja; se registra sin escalar"
    return True, "evento tactico aceptado para feed operativo"


def process_cot_payload(
    payload: dict,
    command_post: CommandPost = DEFAULT_COMMAND_POST,
) -> ProcessedEvent:
    event = TacticalEvent.from_cot_payload(payload)
    geo = assess_relative_position(command_post.position, event.position)
    tactical_brief = generate_tactical_brief(event, geo)
    accepted, decision_reason = should_accept(event)
    return ProcessedEvent(
        event=event,
        geo=geo,
        tactical_brief=tactical_brief,
        accepted=accepted,
        decision_reason=decision_reason,
    )
