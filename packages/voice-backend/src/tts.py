"""
Text-to-Speech using Chatterbox.

Provides expressive, low-latency voice synthesis for IRIS.
Supports voice cloning and emotion control.
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from scipy.io import wavfile

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    """Result of text-to-speech synthesis."""

    audio: np.ndarray  # Float32 audio samples
    sample_rate: int
    duration_seconds: float

    def to_wav_bytes(self) -> bytes:
        """Convert to WAV file bytes."""
        buffer = io.BytesIO()
        # Ensure audio is 1D (mono) - squeeze out any extra dimensions
        audio = self.audio.squeeze()
        if audio.ndim > 1:
            # If still multi-dimensional, take first channel
            audio = audio[0] if audio.shape[0] < audio.shape[-1] else audio[:, 0]
        # Convert to int16 for WAV
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(buffer, self.sample_rate, audio_int16)
        return buffer.getvalue()


class TextToSpeech:
    """
    Text-to-speech synthesis using Chatterbox.

    Optimized for:
    - Voice-first interaction (<200ms latency target)
    - Expressive speech with emotion control
    - Optional voice cloning from reference audio

    Usage:
        tts = TextToSpeech()
        result = tts.synthesize("Hello, Commander!")
        audio_bytes = result.to_wav_bytes()
    """

    def __init__(
        self,
        device: Literal["cpu", "cuda", "auto"] = "auto",
        voice_reference: str | Path | None = None,
    ):
        """
        Initialize the TTS model.

        Args:
            device: Compute device. "auto" selects GPU if available.
            voice_reference: Optional path to reference audio for voice cloning.
        """
        self.device = device
        self.voice_reference = voice_reference
        self._model = None
        self._sample_rate = 24000  # Chatterbox default

    @property
    def model(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            logger.info("Loading Chatterbox TTS model...")
            try:
                from chatterbox.tts import ChatterboxTTS

                device = self.device
                if device == "auto":
                    import torch

                    device = "cuda" if torch.cuda.is_available() else "cpu"

                self._model = ChatterboxTTS.from_pretrained(device=device)
                logger.info(f"Chatterbox model loaded on {device}")
            except ImportError as e:
                logger.warning(f"Chatterbox not available: {e}. Using placeholder TTS.")
                self._model = "placeholder"
        return self._model

    def synthesize(
        self,
        text: str,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        voice_reference: str | Path | None = None,
        speech_rate: float = 1.0,
    ) -> SynthesisResult:
        """
        Synthesize speech from text.

        Args:
            text: Text to speak.
            exaggeration: Emotion exaggeration level (0.0-1.0).
            cfg_weight: Classifier-free guidance weight (0.0-1.0).
            voice_reference: Optional path to reference audio for voice cloning.
                            Overrides instance-level voice_reference.
            speech_rate: Speech rate multiplier (0.5-2.0). >1.0 is faster, <1.0 is slower.

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

        # Check for placeholder mode (Chatterbox not available)
        if self.model == "placeholder":
            logger.warning(f"TTS placeholder mode - no audio for: {text[:50]}...")
            # Return 1 second of silence
            return SynthesisResult(
                audio=np.zeros(self._sample_rate, dtype=np.float32),
                sample_rate=self._sample_rate,
                duration_seconds=1.0,
            )

        # Use voice reference if provided
        ref_path = voice_reference or self.voice_reference
        ref_path_str = str(ref_path) if ref_path else None

        # Generate audio
        logger.debug(f"Synthesizing: {text[:50]}...")

        wav = self.model.generate(
            text,
            audio_prompt_path=ref_path_str,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )

        # Convert to numpy array
        if hasattr(wav, "numpy"):
            audio = wav.numpy()
        elif hasattr(wav, "cpu"):
            audio = wav.cpu().numpy()
        else:
            audio = np.array(wav)

        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Normalize if needed
        if audio.max() > 1.0 or audio.min() < -1.0:
            audio = audio / max(abs(audio.max()), abs(audio.min()))

        # Apply speech rate adjustment via resampling
        if speech_rate != 1.0 and 0.5 <= speech_rate <= 2.0:
            from scipy import signal
            # To speed up audio (rate > 1), we resample to fewer samples
            # To slow down audio (rate < 1), we resample to more samples
            original_len = len(audio)
            target_len = int(original_len / speech_rate)
            audio = signal.resample(audio, target_len).astype(np.float32)
            logger.debug(f"Applied speech rate {speech_rate}: {original_len} -> {target_len} samples")

        duration = len(audio) / self._sample_rate

        return SynthesisResult(
            audio=audio,
            sample_rate=self._sample_rate,
            duration_seconds=duration,
        )

    def synthesize_streaming(
        self,
        text: str,
        chunk_size: int = 4096,
    ):
        """
        Synthesize speech and yield audio chunks.

        Suitable for streaming audio to the client for lower latency.

        Args:
            text: Text to speak.
            chunk_size: Number of samples per chunk.

        Yields:
            Audio chunks as bytes (WAV format).
        """
        result = self.synthesize(text)

        # Convert to int16 for streaming
        audio_int16 = (result.audio * 32767).astype(np.int16)

        # Yield chunks
        for i in range(0, len(audio_int16), chunk_size):
            chunk = audio_int16[i : i + chunk_size]
            yield chunk.tobytes()


# Singleton instance for the API
_tts_instance: TextToSpeech | None = None


def get_tts(device: Literal["cpu", "cuda", "auto"] = "auto") -> TextToSpeech:
    """Get or create the singleton TTS instance."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TextToSpeech(device=device)
    return _tts_instance
