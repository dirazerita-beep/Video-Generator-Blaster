"""OpenAI TTS provider using the openai SDK."""

import logging
import pathlib

from .base import BaseTTS

logger = logging.getLogger(__name__)


class OpenAITTS(BaseTTS):
    """Generates speech using the OpenAI TTS API."""

    def __init__(self, api_key: str, voice: str = "alloy", model: str = "tts-1"):
        """Initialize OpenAI TTS.

        Args:
            api_key: OpenAI API key.
            voice: Voice name (alloy, echo, fable, onyx, nova, shimmer).
            model: TTS model (tts-1 or tts-1-hd).
        """
        self.api_key = api_key
        self.voice = voice
        self.model = model

    def generate(self, text: str, output_wav_path: str) -> bool:
        """Generate speech using OpenAI TTS API and save to file."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            response = client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
            )
            output_path = pathlib.Path(output_wav_path)
            response.stream_to_file(output_path)
            return True
        except Exception as exc:
            logger.error("OpenAI TTS failed: %s", exc)
            return False
