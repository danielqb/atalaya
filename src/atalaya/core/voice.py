"""Retransmite por voz (Mumble + ElevenLabs) los eventos procesados de prioridad
alta/critica. Ver mvp-spec.md #7 y src/audio/mumble_bot.py.

Se activa solo si MUMBLE_HOST y ELEVENLABS_API_KEY estan configurados; si el bot
no esta disponible o falla, el evento sigue su curso normal por texto (el audio
es un canal adicional, no bloqueante).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("atalaya.voice")

HIGH_PRIORITY_LEVELS = {"high", "critical"}

_bot: Any = None
_enabled = bool(os.environ.get("MUMBLE_HOST")) and bool(os.environ.get("ELEVENLABS_API_KEY"))


def _get_bot():
    global _bot
    if _bot is None:
        from audio.mumble_bot import TacticalVoiceBot

        _bot = TacticalVoiceBot()
        _bot.start()
    return _bot


def speak_if_high_priority(event: dict[str, Any]) -> None:
    if not _enabled or event.get("priority") not in HIGH_PRIORITY_LEVELS:
        return
    try:
        _get_bot().speak_alert(event)
    except Exception:
        logger.exception("Fallo al hablar la alerta por Mumble, evento %s sigue solo en texto", event.get("uid"))
