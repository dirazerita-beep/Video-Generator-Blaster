"""Abstract base class for all TTS providers."""

from abc import ABC, abstractmethod


class BaseTTS(ABC):
    """Abstract interface for text-to-speech providers."""

    @abstractmethod
    def generate(self, text: str, output_wav_path: str) -> bool:
        """Generate speech audio from text and save to output_wav_path.

        Args:
            text: The text to synthesize into speech.
            output_wav_path: Path where the output audio file will be saved.

        Returns:
            True if generation succeeded, False otherwise.
        """
        raise NotImplementedError
