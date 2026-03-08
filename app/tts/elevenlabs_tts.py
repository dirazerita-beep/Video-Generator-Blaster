"""ElevenLabs TTS provider using the elevenlabs SDK."""

import logging
import pathlib

from .base import BaseTTS

logger = logging.getLogger(__name__)


class ElevenLabsTTS(BaseTTS):
    """Generates speech using the ElevenLabs API."""

    def __init__(self, api_key: str, voice_id: str):
        """Initialize ElevenLabs TTS.

        Args:
            api_key: ElevenLabs API key.
            voice_id: ElevenLabs voice ID.
        """
        self.api_key = api_key
        self.voice_id = voice_id

    def generate(self, text: str, output_wav_path: str) -> bool:
        """Generate speech using ElevenLabs API and save to file."""
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=self.api_key)
            audio = client.generate(
                text=text,
                voice=self.voice_id,
                model="eleven_monolingual_v1",
            )
            output_path = pathlib.Path(output_wav_path)
            with open(output_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            return True
        except Exception as exc:
            logger.error("ElevenLabs TTS failed: %s", exc)
            return False
