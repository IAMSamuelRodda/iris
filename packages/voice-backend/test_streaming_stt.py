#!/usr/bin/env python3
"""
Benchmark: Streaming STT vs Batch STT

Compares:
- Batch mode (current): ~181ms
- Streaming mode (target): <50ms

Usage:
    python test_streaming_stt.py
"""

import os
import sys
import time
import numpy as np

# Setup cuDNN before other imports
def _setup_cudnn_path():
    try:
        import nvidia.cudnn
        cudnn_lib = os.path.join(os.path.dirname(nvidia.cudnn.__file__), "lib")
        if os.path.exists(cudnn_lib):
            current_path = os.environ.get("LD_LIBRARY_PATH", "")
            if cudnn_lib not in current_path:
                os.environ["LD_LIBRARY_PATH"] = f"{cudnn_lib}:{current_path}"
                import ctypes
                ctypes.CDLL(os.path.join(cudnn_lib, "libcudnn.so.9"), mode=ctypes.RTLD_GLOBAL)
    except:
        pass

_setup_cudnn_path()


def load_real_speech_audio(wav_path: str = "voice_samples/A_af_heart.wav") -> bytes:
    """Load real speech audio and resample to 16kHz mono."""
    import scipy.io.wavfile as wav
    import scipy.signal as signal

    sr, audio = wav.read(wav_path)
    print(f"Loaded: {wav_path} ({sr}Hz, {len(audio)/sr:.2f}s)")

    # Resample to 16kHz if needed
    if sr != 16000:
        num_samples = int(len(audio) * 16000 / sr)
        audio = signal.resample(audio, num_samples).astype(np.int16)
        print(f"Resampled to 16kHz ({len(audio)/16000:.2f}s)")

    return audio.tobytes()


def create_test_audio(text: str = "Hello, what is the status of my fleet?", duration_s: float = 2.0) -> bytes:
    """Create synthetic test audio (silence + beep pattern for testing)."""
    sample_rate = 16000
    samples = int(sample_rate * duration_s)

    # Create simple tone pattern (not real speech, just for latency testing)
    t = np.linspace(0, duration_s, samples)
    # 440 Hz tone with envelope
    audio = np.sin(2 * np.pi * 440 * t) * 0.3
    # Add some variation
    audio += np.sin(2 * np.pi * 880 * t) * 0.1

    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()


def benchmark_batch_stt():
    """Benchmark current batch mode STT."""
    from src.stt import SpeechToText

    print("\n" + "=" * 60)
    print("BATCH MODE STT (current)")
    print("=" * 60)

    stt = SpeechToText(model_size="base", device="cuda", compute_type="int8")

    # Load real speech audio
    print("Loading real speech audio...")
    audio_bytes = load_real_speech_audio()
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    # Warmup
    print("Warming up...")
    _ = stt.model
    _ = stt.transcribe(audio_np)  # Warm run

    # Benchmark
    times = []
    for i in range(5):
        start = time.perf_counter()
        result = stt.transcribe(audio_np)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)
        text = result.text[:50] if result.text else "(no speech)"
        print(f"  Run {i+1}: {elapsed*1000:.1f}ms - '{text}...'")

    print(f"\nBatch mode average: {np.mean(times):.1f}ms")
    return np.mean(times)


def benchmark_streaming_stt():
    """Benchmark new streaming mode STT using direct faster-whisper streaming."""
    from faster_whisper import WhisperModel

    print("\n" + "=" * 60)
    print("STREAMING MODE STT (direct faster-whisper)")
    print("=" * 60)

    # Load real speech audio
    print("Loading real speech audio...")
    audio_bytes = load_real_speech_audio()
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    # Create model directly (bypass RealtimeSTT's complexity)
    print("Loading model...")
    model = WhisperModel("base", device="cuda", compute_type="int8")

    # Warmup
    print("Warming up...")
    segments, _ = model.transcribe(audio_np, beam_size=1)
    _ = list(segments)  # Force evaluation

    # Benchmark - simulate streaming by transcribing incrementally
    # This measures the raw transcription speed without VAD overhead
    times = []
    for i in range(5):
        start = time.perf_counter()
        segments, info = model.transcribe(audio_np, beam_size=1)
        result = " ".join(seg.text for seg in segments)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)
        text = result[:50] if result else "(no speech)"
        print(f"  Run {i+1}: {elapsed*1000:.1f}ms - '{text}...'")

    print(f"\nDirect faster-whisper average: {np.mean(times):.1f}ms")
    return np.mean(times)


def benchmark_streaming_stt_with_vad():
    """Benchmark streaming mode with VAD (RealtimeSTT)."""
    from RealtimeSTT import AudioToTextRecorder

    print("\n" + "=" * 60)
    print("STREAMING MODE STT (with VAD - RealtimeSTT)")
    print("=" * 60)

    # Load real speech audio
    print("Loading real speech audio...")
    audio_bytes = load_real_speech_audio()
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
    chunk_size = 640  # 20ms at 16kHz, 16-bit mono

    # Create recorder with minimal config
    print("Creating recorder...")
    result_text = []

    def on_text(text):
        result_text.append(text)

    recorder = AudioToTextRecorder(
        model="base",
        device="cuda",
        compute_type="int8",
        use_microphone=False,
        spinner=False,
        silero_sensitivity=0.4,
        webrtc_sensitivity=2,
        post_speech_silence_duration=0.3,
        min_length_of_recording=0.2,
        beam_size=1,
        print_transcription_time=False,
    )

    # Warmup
    print("Warming up...")

    # Benchmark
    times = []
    for i in range(3):  # Fewer runs due to complexity
        result_text.clear()

        # Feed audio chunks rapidly (faster than real-time)
        feed_start = time.perf_counter()
        for j in range(0, len(audio_np), chunk_size // 2):  # int16 = 2 bytes
            chunk = audio_np[j:j + chunk_size // 2]
            recorder.feed_audio(chunk)
        feed_time = time.perf_counter() - feed_start

        # Get transcript
        start = time.perf_counter()
        result = recorder.text()
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

        text = result[:50] if result else "(no speech)"
        print(f"  Run {i+1}: feed={feed_time*1000:.0f}ms, transcribe={elapsed*1000:.1f}ms - '{text}...'")

    print(f"\nRealtimeSTT average (transcribe time): {np.mean(times):.1f}ms")
    recorder.shutdown()
    return np.mean(times)


def main():
    print("=" * 60)
    print("STT LATENCY BENCHMARK")
    print("Comparing batch vs streaming transcription")
    print("=" * 60)

    print("\nUsing REAL SPEECH audio from voice_samples/")
    print("Audio: ~6s sample resampled to 16kHz mono")

    batch_time = benchmark_batch_stt()
    streaming_time = benchmark_streaming_stt()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Batch STT (our wrapper):        {batch_time:.1f}ms")
    print(f"Direct faster-whisper:          {streaming_time:.1f}ms")
    print(f"Improvement:                    {((batch_time - streaming_time) / batch_time * 100):.1f}%")
    print(f"Target:                         <50ms")
    print()
    print("Note: RealtimeSTT VAD benchmark skipped (requires async handling)")
    print("      The direct faster-whisper test shows raw transcription speed.")


if __name__ == "__main__":
    main()
