"""Offline Windows SAPI TTS using pyttsx3."""

import logging

from .base import BaseTTS

logger = logging.getLogger(__name__)


class SapiTTS(BaseTTS):
    """Uses pyttsx3 to generate speech via Windows SAPI (offline)."""

    def __init__(self, voice_id: str = None, rate: int = 150):
        """Initialize SAPI TTS.

        Args:
            voice_id: Windows SAPI voice ID string. If None, uses system default.
            rate: Speech rate in words per minute (default 150).
        """
        self.voice_id = voice_id
        self.rate = rate

    @staticmethod
    def get_available_voices() -> list[dict]:
        """Return list of available SAPI voices as dicts with 'id' and 'name' keys."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            result = [{"id": v.id, "name": v.name} for v in voices]
            engine.stop()
            return result
        except Exception as exc:
            logger.warning("Could not enumerate SAPI voices: %s", exc)
            return []

    def generate(self, text: str, output_wav_path: str) -> bool:
        """Generate speech using Windows SAPI and save to WAV file."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            if self.voice_id:
                engine.setProperty("voice", self.voice_id)
            engine.setProperty("rate", self.rate)
            engine.save_to_file(text, output_wav_path)
            engine.runAndWait()
            engine.stop()
            return True
        except Exception as exc:
            logger.error("SAPI TTS failed: %s", exc)
            return False
