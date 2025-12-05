"""
Streaming Speech-to-Text using RealtimeSTT.

Provides low-latency streaming transcription with VAD-based end detection.
Target: sub-50ms final transcript latency (vs 181ms batch mode).

Architecture:
    WebSocket audio chunks → feed_audio() → VAD detects end → instant transcript
"""

import logging
import threading
import queue
from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StreamingTranscriptEvent:
    """Event emitted during streaming transcription."""

    text: str
    is_final: bool
    confidence: float = 1.0


class StreamingSTT:
    """
    Streaming speech-to-text using RealtimeSTT.

    Key features:
    - VAD-based end-of-speech detection (WebRTCVAD + SileroVAD)
    - Real-time partial transcripts (optional)
    - GPU-accelerated via faster-whisper backend

    Usage:
        stt = StreamingSTT()
        stt.start()

        # Feed audio chunks from WebSocket
        for chunk in websocket_audio:
            stt.feed_audio(chunk)

        # Get final transcript when VAD detects end
        result = stt.get_result()
    """

    def __init__(
        self,
        model: str = "base",
        device: Literal["cpu", "cuda"] = "cuda",
        compute_type: str = "int8",
        enable_realtime_transcription: bool = False,
        on_realtime_transcript: Callable[[str], None] | None = None,
        on_final_transcript: Callable[[str], None] | None = None,
    ):
        """
        Initialize streaming STT.

        Args:
            model: Whisper model size (tiny, base, small, medium, large-v3)
            device: Compute device (cpu, cuda)
            compute_type: Quantization (int8, float16, float32)
            enable_realtime_transcription: Emit partial transcripts while speaking
            on_realtime_transcript: Callback for partial transcripts
            on_final_transcript: Callback for final transcript
        """
        self.model = model
        self.device = device
        self.compute_type = compute_type
        self.enable_realtime = enable_realtime_transcription
        self.on_realtime = on_realtime_transcript
        self.on_final = on_final_transcript

        self._recorder = None
        self._result_queue: queue.Queue[str] = queue.Queue()
        self._is_recording = False

    def _create_recorder(self):
        """Lazy-load the AudioToTextRecorder."""
        from RealtimeSTT import AudioToTextRecorder

        logger.info(f"Creating StreamingSTT recorder: model={self.model}, device={self.device}")

        def on_recording_start():
            logger.debug("[StreamingSTT] Recording started (VAD detected speech)")

        def on_recording_stop():
            logger.debug("[StreamingSTT] Recording stopped (VAD detected silence)")

        def on_transcription_start():
            logger.debug("[StreamingSTT] Transcription starting...")

        recorder_config = {
            # Model settings
            "model": self.model,
            "device": self.device,
            "compute_type": self.compute_type,

            # VAD settings - tuned for responsiveness
            "silero_sensitivity": 0.4,  # Lower = more sensitive to silence
            "webrtc_sensitivity": 2,    # 0-3, higher = more sensitive
            "post_speech_silence_duration": 0.4,  # Seconds of silence to end
            "min_length_of_recording": 0.3,  # Minimum speech length

            # Realtime transcription (partials)
            "enable_realtime_transcription": self.enable_realtime,
            "realtime_model_type": "tiny" if self.enable_realtime else None,

            # Callbacks
            "on_recording_start": on_recording_start,
            "on_recording_stop": on_recording_stop,
            "on_transcription_start": on_transcription_start,

            # Performance
            "beam_size": 1,  # Fast decoding for real-time
            "beam_size_realtime": 1,

            # We're feeding audio manually, not using microphone
            "use_microphone": False,

            # Disable spinner and console output
            "spinner": False,
            "print_transcription_time": False,
        }

        if self.on_realtime:
            recorder_config["on_realtime_transcription_update"] = self.on_realtime

        self._recorder = AudioToTextRecorder(**recorder_config)
        logger.info("[StreamingSTT] Recorder created successfully")

    @property
    def recorder(self):
        """Get or create the recorder."""
        if self._recorder is None:
            self._create_recorder()
        return self._recorder

    def feed_audio(self, audio_chunk: bytes, sample_rate: int = 16000):
        """
        Feed an audio chunk for processing.

        Args:
            audio_chunk: Raw PCM audio (16-bit signed, mono)
            sample_rate: Sample rate (default 16000 Hz)
        """
        if not self._is_recording:
            logger.warning("[StreamingSTT] Not recording, ignoring audio chunk")
            return

        # Convert bytes to numpy array (16-bit signed int)
        audio_np = np.frombuffer(audio_chunk, dtype=np.int16)

        # RealtimeSTT expects int16 numpy array at 16kHz mono
        self.recorder.feed_audio(audio_np)

    def start(self):
        """Start listening for audio."""
        logger.info("[StreamingSTT] Starting streaming transcription")
        self._is_recording = True

        # Clear any previous results
        while not self._result_queue.empty():
            self._result_queue.get_nowait()

    def stop(self) -> str | None:
        """
        Stop listening and get final transcript.

        Returns:
            Final transcribed text, or None if no speech detected.
        """
        if not self._is_recording:
            return None

        self._is_recording = False
        logger.info("[StreamingSTT] Stopping, getting final transcript...")

        try:
            # Get the transcription result
            text = self.recorder.text()

            if text and self.on_final:
                self.on_final(text)

            return text

        except Exception as e:
            logger.exception("[StreamingSTT] Error getting transcript")
            return None

    def abort(self):
        """Abort current recording without transcribing."""
        self._is_recording = False
        if self._recorder:
            self._recorder.abort()

    def shutdown(self):
        """Clean up resources."""
        self._is_recording = False
        if self._recorder:
            self._recorder.shutdown()
            self._recorder = None


# ============================================================================
# Benchmark helper
# ============================================================================

async def benchmark_streaming_stt(audio_file: str = None):
    """
    Benchmark streaming STT latency.

    Compares:
    - Current batch mode: ~181ms
    - Target streaming mode: <50ms
    """
    import time
    import asyncio

    print("=" * 60)
    print("Streaming STT Benchmark")
    print("=" * 60)

    # Create streaming STT
    stt = StreamingSTT(
        model="base",
        device="cuda",
        compute_type="int8",
        enable_realtime_transcription=False,
    )

    print("\n1. Warming up model...")
    start = time.perf_counter()
    _ = stt.recorder  # Force model load
    warmup_time = time.perf_counter() - start
    print(f"   Warmup: {warmup_time*1000:.1f}ms")

    # TODO: Add actual audio file test
    print("\n2. Ready for streaming test")
    print("   Feed audio via: stt.feed_audio(chunk)")
    print("   Stop and get result: stt.stop()")

    return stt


if __name__ == "__main__":
    import asyncio
    asyncio.run(benchmark_streaming_stt())
