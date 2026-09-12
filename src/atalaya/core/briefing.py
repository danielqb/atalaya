from __future__ import annotations

from atalaya.core.models import PRIORITY_LABELS_ES, GeoAssessment, TacticalBrief, TacticalEvent

ACTION_BY_TYPE = {
    "CASEVAC": "coordinar extraccion medica y confirmar ruta segura",
    "FINDING": "enviar evaluacion y mantener comunicacion con el equipo",
    "HAZARD": "aislar el area, redirigir unidades y confirmar mitigacion",
    "ALERT": "verificar el reporte y asignar recurso de reconocimiento",
}

def generate_tactical_brief(event: TacticalEvent, geo: GeoAssessment) -> TacticalBrief:
    """Generate a tactical brief.

    The MVP uses a deterministic fallback so the demo remains reliable. The API layer can
    later swap this for an OpenAI/OpenRouter call while preserving the same output contract.
    """

    recommended_action = ACTION_BY_TYPE.get(
        event.event_type, "verificar el reporte antes de asignar recursos"
    )
    headline = f"{event.event_type} a {geo.distance_m} m al {geo.relative_direction}"

    if event.event_type == "CHAT" or event.priority == "low":
        return TacticalBrief(
            headline="Evento de baja prioridad registrado",
            brief=(
                f"{event.callsign} reporta informacion de baja prioridad a "
                f"{geo.distance_m} metros al {geo.relative_direction}; "
                "no interrumpe el feed tactico."
            ),
            priority=event.priority,
            recommended_action="registrar sin escalar salvo corroboracion posterior",
            llm_used=False,
        )

    priority_label = PRIORITY_LABELS_ES[event.priority]
    brief = (
        f"{event.callsign} reporta {event.event_type} a {geo.distance_m} metros al "
        f"{geo.relative_direction}. Prioridad {priority_label}: {event.message}; "
        f"{recommended_action}."
    )

    return TacticalBrief(
        headline=headline,
        brief=brief,
        priority=event.priority,
        recommended_action=recommended_action,
        llm_used=False,
    )
