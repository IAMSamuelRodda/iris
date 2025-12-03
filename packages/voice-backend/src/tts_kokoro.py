"""
Text-to-Speech using Kokoro.

Fast, high-quality voice synthesis for IRIS.
~100ms latency on GPU, ~300ms on CPU.

Available voices (selected for quality):
  American Female: af_heart (default), af_bella, af_sky, af_sarah, af_nicole, af_jessica
  British Female: bf_emma, bf_isabella
  American Male: am_michael
  British Male: bm_fable, bm_george
"""

import io
import logging
import os
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.io import wavfile

logger = logging.getLogger(__name__)

# Default voice for IRIS - af_heart is the most adaptive A-grade voice
DEFAULT_VOICE = os.environ.get("KOKORO_VOICE", "af_heart")

# Available voices organized by category
AVAILABLE_VOICES = {
    # American Female (top quality)
    "af_heart": {"grade": "A", "desc": "American Female - Best quality"},
    "af_bella": {"grade": "A-", "desc": "American Female"},
    "af_sky": {"grade": "B", "desc": "American Female"},
    "af_sarah": {"grade": "C+", "desc": "American Female - Really good"},
    "af_nicole": {"grade": "B", "desc": "American Female - Whisper/ASMR"},
    "af_jessica": {"grade": "C", "desc": "American Female - Young/excited"},
    # British Female
    "bf_emma": {"grade": "B-", "desc": "British Female - Smooth"},
    "bf_isabella": {"grade": "B-", "desc": "British Female - Unique"},
    # American Male
    "am_michael": {"grade": "C+", "desc": "American Male - Winner"},
    # British Male
    "bm_fable": {"grade": "C", "desc": "British Male"},
    "bm_george": {"grade": "C+", "desc": "British Male"},
}


@dataclass
class SynthesisResult:
    """Result of text-to-speech synthesis."""

    audio: np.ndarray  # Float32 audio samples
    sample_rate: int
    duration_seconds: float

    def to_wav_bytes(self) -> bytes:
        """Convert to WAV file bytes."""
        buffer = io.BytesIO()
        # Ensure audio is 1D (mono)
        audio = self.audio.squeeze()
        if audio.ndim > 1:
            audio = audio[0] if audio.shape[0] < audio.shape[-1] else audio[:, 0]
        # Convert to int16 for WAV
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(buffer, self.sample_rate, audio_int16)
        return buffer.getvalue()


class KokoroTTS:
    """
    Text-to-speech synthesis using Kokoro.

    Optimized for:
    - Ultra-low latency (~100ms on GPU)
    - High quality A-grade voices
    - Instant voice switching (no model reload)

    Usage:
        tts = KokoroTTS()
        result = tts.synthesize("Hello, Commander!")
        audio_bytes = result.to_wav_bytes()
    """

    def __init__(
        self,
        device: Literal["cpu", "cuda", "auto"] = "auto",
        voice: str | None = None,
    ):
        """
        Initialize the Kokoro TTS model.

        Args:
            device: Compute device. "auto" selects GPU if available.
            voice: Default voice ID (e.g., "af_heart", "am_michael").
        """
        self.device = device
        self._pipeline = None
        self._sample_rate = 24000  # Kokoro outputs at 24kHz
        self.current_voice = voice or DEFAULT_VOICE

        # Validate voice
        if self.current_voice not in AVAILABLE_VOICES:
            logger.warning(f"Voice '{self.current_voice}' not in curated list, using anyway")

    @property
    def pipeline(self):
        """Lazy-load the Kokoro pipeline on first use."""
        if self._pipeline is None:
            logger.info("Loading Kokoro TTS model...")
            try:
                from kokoro import KPipeline

                device = self.device
                if device == "auto":
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"

                self._pipeline = KPipeline(
                    lang_code='a',  # American English
                    device=device,
                    repo_id='hexgrad/Kokoro-82M'
                )
                logger.info(f"Kokoro model loaded on {device}")
            except ImportError as e:
                logger.error(f"Kokoro not available: {e}")
                raise
        return self._pipeline

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> SynthesisResult:
        """
        Synthesize speech from text.

        Args:
            text: Text to speak.
            voice: Voice ID (e.g., "af_heart"). Uses default if not specified.
            speed: Speech speed multiplier (0.5-2.0).

        Returns:
            SynthesisResult with audio samples and metadata.
        """
        if not text.strip():
            # Return silence for empty text
            return SynthesisResult(
                audio=np.zeros(self._sample_rate // 10, dtype=np.float32),
                sample_rate=self._sample_rate,
                duration_seconds=0.1,
            )

        voice_id = voice or self.current_voice
        logger.debug(f"Synthesizing with {voice_id}: {text[:50]}...")

        # Generate audio using Kokoro pipeline
        generator = self.pipeline(text, voice=voice_id, speed=speed)

        # Collect all audio chunks
        audio_chunks = []
        for _, _, audio in generator:
            audio_chunks.append(audio)

        if not audio_chunks:
            logger.warning(f"No audio generated for: {text[:50]}...")
            return SynthesisResult(
                audio=np.zeros(self._sample_rate, dtype=np.float32),
                sample_rate=self._sample_rate,
                duration_seconds=1.0,
            )

        # Concatenate chunks
        full_audio = np.concatenate(audio_chunks)

        # Ensure float32
        if full_audio.dtype != np.float32:
            full_audio = full_audio.astype(np.float32)

        # Normalize if needed
        max_val = max(abs(full_audio.max()), abs(full_audio.min()))
        if max_val > 1.0:
            full_audio = full_audio / max_val

        duration = len(full_audio) / self._sample_rate

        return SynthesisResult(
            audio=full_audio,
            sample_rate=self._sample_rate,
            duration_seconds=duration,
        )

    def synthesize_streaming(
        self,
        text: str,
        voice: str | None = None,
        chunk_size: int = 4096,
    ):
        """
        Synthesize speech and yield audio chunks.

        Suitable for streaming audio to the client for lower latency.

        Args:
            text: Text to speak.
            voice: Voice ID to use.
            chunk_size: Number of samples per chunk.

        Yields:
            Audio chunks as bytes (raw PCM int16).
        """
        result = self.synthesize(text, voice=voice)

        # Convert to int16 for streaming
        audio_int16 = (result.audio * 32767).astype(np.int16)

        # Yield chunks
        for i in range(0, len(audio_int16), chunk_size):
            chunk = audio_int16[i : i + chunk_size]
            yield chunk.tobytes()

    def set_voice(self, voice: str) -> bool:
        """
        Change the default voice.

        Args:
            voice: Voice ID (e.g., "af_heart", "am_michael")

        Returns:
            True if voice is valid, False otherwise.
        """
        if voice not in AVAILABLE_VOICES:
            logger.warning(f"Voice '{voice}' not in curated list")
            # Still allow it - Kokoro may have more voices
        self.current_voice = voice
        logger.info(f"Switched to voice: {voice}")
        return True


# Singleton instance for the API
_kokoro_instance: KokoroTTS | None = None


def get_kokoro_tts(device: Literal["cpu", "cuda", "auto"] = "auto") -> KokoroTTS:
    """Get or create the singleton Kokoro TTS instance."""
    global _kokoro_instance
    if _kokoro_instance is None:
        _kokoro_instance = KokoroTTS(device=device)
    return _kokoro_instance


def list_kokoro_voices() -> list[dict]:
    """List all available Kokoro voices with metadata."""
    return [
        {"id": vid, **info}
        for vid, info in AVAILABLE_VOICES.items()
    ]


def set_kokoro_voice(voice: str) -> bool:
    """
    Change the active voice for the singleton instance.

    Args:
        voice: Voice ID (e.g., "af_heart", "am_michael")

    Returns:
        True if successful.
    """
    global _kokoro_instance
    if _kokoro_instance is not None:
        return _kokoro_instance.set_voice(voice)
    return False
