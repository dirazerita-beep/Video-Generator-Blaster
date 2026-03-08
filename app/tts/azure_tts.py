"""Azure Cognitive Services Speech TTS provider."""

import logging

from .base import BaseTTS

logger = logging.getLogger(__name__)


class AzureTTS(BaseTTS):
    """Generates speech using Azure Cognitive Services Speech SDK."""

    def __init__(self, api_key: str, region: str, voice_name: str = "en-US-JennyNeural"):
        """Initialize Azure TTS.

        Args:
            api_key: Azure Speech subscription key.
            region: Azure region (e.g. 'eastus').
            voice_name: Azure voice name (e.g. 'en-US-JennyNeural').
        """
        self.api_key = api_key
        self.region = region
        self.voice_name = voice_name

    def generate(self, text: str, output_wav_path: str) -> bool:
        """Generate speech using Azure Speech SDK and save to WAV file."""
        try:
            import azure.cognitiveservices.speech as speechsdk

            speech_config = speechsdk.SpeechConfig(
                subscription=self.api_key,
                region=self.region,
            )
            speech_config.speech_synthesis_voice_name = self.voice_name
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_wav_path)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
            result = synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            logger.error(
                "Azure TTS failed with reason: %s — %s",
                result.reason,
                result.cancellation_details.error_details if hasattr(result, "cancellation_details") else "",
            )
            return False
        except Exception as exc:
            logger.error("Azure TTS error: %s", exc)
            return False
