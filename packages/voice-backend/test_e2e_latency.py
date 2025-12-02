#!/usr/bin/env python3
"""
End-to-end voice latency benchmark.

Measures the full pipeline from audio submission to TTS response:
1. STT latency (audio → transcription)
2. Claude API latency (transcription → AI response)
3. TTS latency (AI response → audio)
4. Total end-to-end latency

Run with: python test_e2e_latency.py
"""

import time
import requests
import numpy as np
from scipy.io import wavfile
from pathlib import Path
import io
import json

# Configuration
VOICE_BACKEND_URL = "http://localhost:8001"
AGENT_API_URL = "http://localhost:3001"

def create_test_audio(text_prompt: str = "Hello") -> bytes:
    """Create a 2-second test audio file (16kHz mono WAV)."""
    sample_rate = 16000
    duration = 2.0
    samples = int(sample_rate * duration)

    # Generate audio with some variation (simulate speech-like patterns)
    t = np.linspace(0, duration, samples)
    audio = np.sin(2 * np.pi * 200 * t) * 0.1
    audio += np.random.randn(samples) * 0.01
    audio = (audio * 32767).astype(np.int16)

    # Write to WAV bytes
    buffer = io.BytesIO()
    wavfile.write(buffer, sample_rate, audio)
    return buffer.getvalue()

def measure_stt_latency() -> tuple[float, str]:
    """Measure STT (Speech-to-Text) latency."""
    audio_data = create_test_audio()

    start = time.perf_counter()
    response = requests.post(
        f"{VOICE_BACKEND_URL}/transcribe",
        files={"audio": ("test.wav", audio_data, "audio/wav")}
    )
    elapsed = time.perf_counter() - start

    if response.status_code == 200:
        result = response.json()
        return elapsed, result.get("text", "")
    else:
        return elapsed, f"Error: {response.status_code}"

def measure_claude_api_latency(message: str = "Hello") -> tuple[float, float, str]:
    """
    Measure Claude API latency.
    Returns (first_token_latency, total_latency, full_response)
    """
    start = time.perf_counter()
    first_token_time = None
    full_response = ""

    try:
        response = requests.post(
            f"{AGENT_API_URL}/api/chat",
            json={"userId": "latency-test", "message": message},
            stream=True,
            headers={"Accept": "text/event-stream"}
        )

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    if first_token_time is None:
                        first_token_time = time.perf_counter() - start
                    try:
                        data = json.loads(line_str[6:])
                        if data.get("type") == "text":
                            full_response += data.get("content", "")
                    except json.JSONDecodeError:
                        pass

        total_time = time.perf_counter() - start
        return (first_token_time or total_time, total_time, full_response)
    except Exception as e:
        elapsed = time.perf_counter() - start
        return (elapsed, elapsed, f"Error: {e}")

def measure_tts_latency(text: str) -> tuple[float, int]:
    """Measure TTS (Text-to-Speech) latency. Returns (latency, audio_bytes)."""
    start = time.perf_counter()
    response = requests.post(
        f"{VOICE_BACKEND_URL}/synthesize",
        json={"text": text}
    )
    elapsed = time.perf_counter() - start

    if response.status_code == 200:
        return elapsed, len(response.content)
    else:
        return elapsed, 0

def run_full_e2e_test(num_iterations: int = 3):
    """Run full end-to-end latency test."""
    print("=" * 70)
    print("IRIS Voice Pipeline - End-to-End Latency Benchmark")
    print("=" * 70)
    print()

    # Check services are running
    print("[1] Checking services...")
    try:
        requests.get(f"{VOICE_BACKEND_URL}/health", timeout=2)
        print(f"    ✓ Voice backend: {VOICE_BACKEND_URL}")
    except:
        print(f"    ✗ Voice backend NOT RUNNING: {VOICE_BACKEND_URL}")
        return

    try:
        requests.get(f"{AGENT_API_URL}/health", timeout=2)
        print(f"    ✓ Agent API: {AGENT_API_URL}")
    except:
        print(f"    ✗ Agent API NOT RUNNING: {AGENT_API_URL}")
        return

    print()
    print("[2] Running benchmark...")
    print()

    results = {
        "stt": [],
        "claude_first_token": [],
        "claude_total": [],
        "tts": [],
        "total_e2e": []
    }

    for i in range(num_iterations):
        print(f"--- Iteration {i+1}/{num_iterations} ---")

        # Stage 1: STT
        stt_time, transcription = measure_stt_latency()
        results["stt"].append(stt_time)
        print(f"  STT:            {stt_time*1000:>7.1f}ms  → \"{transcription[:50]}...\"")

        # Stage 2: Claude API
        test_message = "Hi"  # Short message to minimize response time
        first_token, total_claude, ai_response = measure_claude_api_latency(test_message)
        results["claude_first_token"].append(first_token)
        results["claude_total"].append(total_claude)
        print(f"  Claude (first): {first_token*1000:>7.1f}ms")
        print(f"  Claude (total): {total_claude*1000:>7.1f}ms  → \"{ai_response[:50]}...\"")

        # Stage 3: TTS
        tts_text = ai_response if ai_response else "Hello Commander."
        tts_time, audio_size = measure_tts_latency(tts_text)
        results["tts"].append(tts_time)
        print(f"  TTS:            {tts_time*1000:>7.1f}ms  → {audio_size} bytes")

        # Total E2E
        total = stt_time + total_claude + tts_time
        results["total_e2e"].append(total)
        print(f"  TOTAL E2E:      {total*1000:>7.1f}ms")
        print()

    # Summary statistics
    print("=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print()
    print(f"{'Stage':<25} {'Mean':>10} {'Min':>10} {'Max':>10} {'Std':>10}")
    print("-" * 65)

    for stage, values in results.items():
        if values:
            mean_ms = np.mean(values) * 1000
            min_ms = np.min(values) * 1000
            max_ms = np.max(values) * 1000
            std_ms = np.std(values) * 1000
            print(f"{stage:<25} {mean_ms:>9.1f}ms {min_ms:>9.1f}ms {max_ms:>9.1f}ms {std_ms:>9.1f}ms")

    print()
    print("=" * 70)
    print("LATENCY BREAKDOWN (Current Architecture)")
    print("=" * 70)
    print()

    stt_mean = np.mean(results["stt"]) * 1000
    claude_mean = np.mean(results["claude_total"]) * 1000
    tts_mean = np.mean(results["tts"]) * 1000
    total_mean = np.mean(results["total_e2e"]) * 1000

    print(f"  User stops speaking")
    print(f"       ↓")
    print(f"  STT Processing:    {stt_mean:>7.1f}ms ({stt_mean/total_mean*100:>5.1f}%)")
    print(f"       ↓")
    print(f"  Claude API:        {claude_mean:>7.1f}ms ({claude_mean/total_mean*100:>5.1f}%)  ← BOTTLENECK")
    print(f"       ↓")
    print(f"  TTS Synthesis:     {tts_mean:>7.1f}ms ({tts_mean/total_mean*100:>5.1f}%)")
    print(f"       ↓")
    print(f"  First audio plays")
    print()
    print(f"  TOTAL:             {total_mean:>7.1f}ms")
    print()

    # Recommendations
    print("=" * 70)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("=" * 70)
    print()

    if claude_mean > 2000:
        print("  🔴 Claude API is the main bottleneck ({:.1f}ms)".format(claude_mean))
        print("     → Option 1: Start TTS on first sentence (don't wait for full response)")
        print("     → Option 2: Use Haiku for voice queries (faster model)")
        print("     → Option 3: Implement sentence-level TTS streaming")

    if tts_mean > 2000:
        print("  🔴 TTS is slow ({:.1f}ms)".format(tts_mean))
        print("     → Enable GPU acceleration (TTS_DEVICE=cuda)")

    if stt_mean > 500:
        print("  🟡 STT could be optimized ({:.1f}ms)".format(stt_mean))
        print("     → Consider smaller model or GPU acceleration")

    if total_mean < 2000:
        print("  🟢 Total latency is acceptable ({:.1f}ms < 2s)".format(total_mean))
    elif total_mean < 4000:
        print("  🟡 Total latency is noticeable ({:.1f}ms)".format(total_mean))
    else:
        print("  🔴 Total latency is too high for natural conversation ({:.1f}ms)".format(total_mean))

    print()
    return results

if __name__ == "__main__":
    run_full_e2e_test(num_iterations=3)
