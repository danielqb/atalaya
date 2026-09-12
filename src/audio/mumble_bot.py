"""Bot de voz: retransmite avisos tacticos como audio hablado en un canal Mumble.

Se conecta directo a Murmur con credenciales propias (no via cuentas OTS: ver
docker-compose.yml en OpenTAKServer-Docker para el porque). Cualquier cliente
ATAK conectado por voz al mismo servidor Mumble escucha el aviso.
"""

import io
import logging
import os
import ssl
import time

# pymumble 1.6.1 calls the module-level ssl.wrap_socket(), removed in Python 3.12.
# Shim it back via SSLContext so pymumble works unmodified on 3.12+.
if not hasattr(ssl, "wrap_socket"):

    def _wrap_socket_compat(
        sock,
        keyfile=None,
        certfile=None,
        server_side=False,
        cert_reqs=ssl.CERT_NONE,
        ssl_version=ssl.PROTOCOL_TLS,
        ca_certs=None,
        do_handshake_on_connect=True,
        suppress_ragged_eofs=True,
        ciphers=None,
    ):
        context = ssl.SSLContext(ssl_version)
        context.check_hostname = False
        context.verify_mode = cert_reqs
        if certfile:
            context.load_cert_chain(certfile, keyfile)
        if ca_certs:
            context.load_verify_locations(ca_certs)
        return context.wrap_socket(
            sock,
            server_side=server_side,
            do_handshake_on_connect=do_handshake_on_connect,
            suppress_ragged_eofs=suppress_ragged_eofs,
        )

    ssl.wrap_socket = _wrap_socket_compat

import pymumble_py3 as pymumble
from elevenlabs import ElevenLabs
from pydub import AudioSegment

logger = logging.getLogger("atalaya.mumble_bot")

MUMBLE_HOST = os.environ["MUMBLE_HOST"]
MUMBLE_PORT = int(os.environ.get("MUMBLE_PORT", "64738"))
MUMBLE_USERNAME = os.environ.get("MUMBLE_USERNAME", "Atalaya-Agent")
MUMBLE_PASSWORD = os.environ.get("MUMBLE_PASSWORD", "")

ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")

_elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def synthesize_pcm(text: str) -> bytes:
    """Genera audio con ElevenLabs y lo deja en PCM 48kHz mono s16le (formato que pymumble espera)."""
    audio_stream = _elevenlabs.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    mp3_bytes = b"".join(audio_stream)
    segment = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
    segment = segment.set_frame_rate(48000).set_channels(1).set_sample_width(2)
    return segment.raw_data


class TacticalVoiceBot:
    """Cliente Mumble que habla los avisos tacticos generados por el coordinador."""

    def __init__(self):
        self._mumble = pymumble.Mumble(
            MUMBLE_HOST,
            MUMBLE_USERNAME,
            port=MUMBLE_PORT,
            password=MUMBLE_PASSWORD,
            reconnect=True,
        )

    def start(self):
        self._mumble.start()
        self._mumble.is_ready()
        logger.info("Conectado a Murmur en %s:%s como %s", MUMBLE_HOST, MUMBLE_PORT, MUMBLE_USERNAME)

    def speak(self, text: str):
        pcm = synthesize_pcm(text)
        sound = self._mumble.sound_output
        sound.add_sound(pcm)
        while sound.get_buffer_size() > 0:
            time.sleep(0.01)

    def speak_alert(self, alert: dict):
        """alert sigue el contrato RiskAlert: usa 'brief' y cae a 'summary' si no esta."""
        text = alert.get("brief") or alert.get("summary")
        if text:
            self.speak(text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = TacticalVoiceBot()
    bot.start()
    bot.speak("Atalaya conectado. Bucle de prueba de audio tactico activo.")
