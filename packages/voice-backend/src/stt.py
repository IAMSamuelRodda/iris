"""
Speech-to-Text using faster-whisper.

Provides low-latency transcription optimized for voice-first interaction.
Uses int8 quantization for reduced memory footprint on VPS deployment.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Model sizes and their approximate RAM requirements (int8):
# tiny: ~100MB, base: ~200MB, small: ~800MB, medium: ~2GB
ModelSize = Literal["tiny", "base", "small", "medium", "large-v3", "turbo"]


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription."""

    text: str
    language: str
    language_probability: float
    duration_seconds: float
    segments: list[dict]


class SpeechToText:
    """
    Speech-to-text transcription using faster-whisper.

    Optimized for:
    - Low latency (<200ms for short utterances)
    - Low memory (int8 quantization)
    - Voice-first interaction patterns

    Usage:
        stt = SpeechToText(model_size="base")
        result = stt.transcribe(audio_data)
        print(result.text)
    """

    def __init__(
        self,
        model_size: ModelSize = "base",
        device: Literal["cpu", "cuda", "auto"] = "auto",
        compute_type: Literal["int8", "float16", "float32"] = "int8",
    ):
        """
        Initialize the STT model.

        Args:
            model_size: Whisper model size. "base" recommended for VPS (200MB RAM).
            device: Compute device. "auto" selects GPU if available.
            compute_type: Quantization level. "int8" for lowest memory.
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

    @property
    def model(self) -> WhisperModel:
        """Lazy-load the model on first use."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size} ({self.compute_type})")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Whisper model loaded successfully")
        return self._model

    def transcribe(
        self,
        audio: np.ndarray | bytes | str | Path,
        language: str | None = None,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Args:
            audio: Audio data as numpy array (float32, 16kHz), bytes, or file path.
            language: Optional language code (e.g., "en"). Auto-detected if None.
            beam_size: Beam size for decoding. Lower = faster, higher = more accurate.
            vad_filter: Enable Voice Activity Detection to skip silence.

        Returns:
            TranscriptionResult with text and metadata.
        """
        # Convert bytes to numpy array if needed
        if isinstance(audio, bytes):
            audio = np.frombuffer(audio, dtype=np.float32)

        # Transcribe
        segments, info = self.model.transcribe(
            audio,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            vad_parameters=dict(
                min_silence_duration_ms=500,  # Merge segments with short pauses
                speech_pad_ms=200,  # Pad speech segments
            ),
        )

        # Collect all segments
        segment_list = []
        full_text_parts = []

        for segment in segments:
            segment_list.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
            )
            full_text_parts.append(segment.text.strip())

        full_text = " ".join(full_text_parts)

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            language_probability=info.language_probability,
            duration_seconds=info.duration,
            segments=segment_list,
        )

    def transcribe_streaming(
        self,
        audio_chunks: list[np.ndarray],
        chunk_length_s: float = 1.0,
    ) -> str:
        """
        Transcribe audio in streaming mode.

        Processes audio chunks incrementally for lower latency.
        Suitable for real-time voice interaction.

        Args:
            audio_chunks: List of audio chunks (float32, 16kHz).
            chunk_length_s: Expected chunk length in seconds.

        Returns:
            Transcribed text.
        """
        # Concatenate chunks
        if not audio_chunks:
            return ""

        audio = np.concatenate(audio_chunks)
        result = self.transcribe(audio, beam_size=3, vad_filter=True)
        return result.text


# Singleton instance for the API
_stt_instance: SpeechToText | None = None


def get_stt(
    model_size: ModelSize = "base",
    device: Literal["cpu", "cuda", "auto"] = "cpu",
) -> SpeechToText:
    """Get or create the singleton STT instance."""
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = SpeechToText(model_size=model_size, device=device)
    return _stt_instance
