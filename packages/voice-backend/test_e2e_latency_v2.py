#!/usr/bin/env python3
"""
End-to-end Voice Latency Benchmark v2 - With Fast-Layer Tracking

Measures the full voice pipeline with fast-layer acknowledgment support:

FAST PATH (Time to first audio response):
  1. STT: Audio → Transcription
  2. Acknowledgment (Haiku 4.5): Transcription → Quick ack
  3. TTS (ack): Ack text → Audio
  → USER HEARS FIRST AUDIO

FULL PATH (Time to complete response):
  4. Claude Sonnet: Transcription → Full response
  5. TTS (full): Response text → Audio
  → USER HEARS FULL RESPONSE

Run with: python test_e2e_latency_v2.py
Options:
  --audio FILE    Use a real audio file instead of synthetic
  --iterations N  Number of test iterations (default: 3)
  --voice-style   Voice style to test (normal, formal, concise, etc.)
"""

import argparse
import time
import requests
import numpy as np
from scipy.io import wavfile
from pathlib import Path
import io
import json
from dataclasses import dataclass, field
from typing import Optional
import sys

# Configuration
VOICE_BACKEND_URL = "http://localhost:8001"
AGENT_API_URL = "http://localhost:3001"

# Test messages that should trigger acknowledgments
TEST_MESSAGES = [
    "Check my fleet status please",  # Should trigger fleet ack
    "What's my wallet balance?",     # Should trigger wallet ack
    "How do I configure mining?",    # Should trigger help ack
    "Show me the transaction history for my account",  # Complex request
]

@dataclass
class LatencyResult:
    """Results from a single latency test run."""
    # STT Stage
    stt_latency_ms: float = 0.0
    transcription: str = ""

    # Fast Layer Stage (Acknowledgment)
    ack_received: bool = False
    ack_latency_ms: float = 0.0  # Time from request to ack event
    ack_text: str = ""
    ack_tts_latency_ms: float = 0.0  # TTS for acknowledgment

    # Main Response Stage (Sonnet)
    first_token_latency_ms: float = 0.0
    full_response_latency_ms: float = 0.0
    response_text: str = ""
    response_tts_latency_ms: float = 0.0  # TTS for full response

    # Derived Metrics
    time_to_first_audio_ms: float = 0.0  # STT + ack + ack_tts
    time_to_full_audio_ms: float = 0.0   # STT + full_response + full_tts

    # Voice style used
    voice_style: str = "normal"

    def calculate_derived(self):
        """Calculate derived metrics."""
        if self.ack_received and self.ack_tts_latency_ms > 0:
            # Fast path: acknowledgment audio
            self.time_to_first_audio_ms = (
                self.stt_latency_ms +
                self.ack_latency_ms +
                self.ack_tts_latency_ms
            )
        else:
            # No ack: first audio is full response
            self.time_to_first_audio_ms = (
                self.stt_latency_ms +
                self.full_response_latency_ms +
                self.response_tts_latency_ms
            )

        self.time_to_full_audio_ms = (
            self.stt_latency_ms +
            self.full_response_latency_ms +
            self.response_tts_latency_ms
        )


def create_test_audio(duration: float = 2.0) -> bytes:
    """Create synthetic test audio (16kHz mono WAV with speech-like patterns)."""
    sample_rate = 16000
    samples = int(sample_rate * duration)

    # Generate audio with some variation (simulate speech-like patterns)
    t = np.linspace(0, duration, samples)
    # Add multiple frequencies for more realistic audio
    audio = np.sin(2 * np.pi * 200 * t) * 0.1
    audio += np.sin(2 * np.pi * 400 * t) * 0.05
    audio += np.random.randn(samples) * 0.02
    audio = (audio * 32767).astype(np.int16)

    # Write to WAV bytes
    buffer = io.BytesIO()
    wavfile.write(buffer, sample_rate, audio)
    return buffer.getvalue()


def load_audio_file(path: str) -> bytes:
    """Load an audio file for testing."""
    with open(path, 'rb') as f:
        return f.read()


def measure_stt(audio_data: bytes) -> tuple[float, str]:
    """Measure STT latency. Returns (latency_ms, transcription)."""
    start = time.perf_counter()
    response = requests.post(
        f"{VOICE_BACKEND_URL}/transcribe",
        files={"audio": ("test.wav", audio_data, "audio/wav")}
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    if response.status_code == 200:
        result = response.json()
        return elapsed_ms, result.get("text", "")
    else:
        return elapsed_ms, f"Error: {response.status_code}"


def measure_agent_response(
    message: str,
    voice_style: str = "normal"
) -> tuple[float, float, float, str, str, bool]:
    """
    Measure Agent API response with acknowledgment tracking.

    Returns:
        (ack_latency_ms, first_token_ms, total_ms, ack_text, response_text, ack_received)
    """
    start = time.perf_counter()
    ack_time = None
    ack_text = ""
    first_token_time = None
    response_text = ""
    ack_received = False

    try:
        response = requests.post(
            f"{AGENT_API_URL}/api/chat",
            json={
                "userId": "latency-test",
                "message": message,
                "voiceStyle": voice_style
            },
            stream=True,
            headers={"Accept": "text/event-stream"}
        )

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    try:
                        data = json.loads(line_str[6:])
                        event_type = data.get("type")

                        if event_type == "acknowledgment":
                            ack_time = (time.perf_counter() - start) * 1000
                            ack_text = data.get("content", "")
                            ack_received = True

                        elif event_type == "text":
                            if first_token_time is None:
                                first_token_time = (time.perf_counter() - start) * 1000
                            response_text += data.get("content", "")

                    except json.JSONDecodeError:
                        pass

        total_time = (time.perf_counter() - start) * 1000
        return (
            ack_time or 0.0,
            first_token_time or total_time,
            total_time,
            ack_text,
            response_text,
            ack_received
        )

    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return (0.0, elapsed, elapsed, "", f"Error: {e}", False)


def measure_tts(text: str, exaggeration: float = 0.5, speech_rate: float = 1.0) -> tuple[float, int]:
    """Measure TTS latency. Returns (latency_ms, audio_bytes)."""
    if not text:
        return 0.0, 0

    start = time.perf_counter()
    response = requests.post(
        f"{VOICE_BACKEND_URL}/synthesize",
        json={
            "text": text,
            "exaggeration": exaggeration,
            "speed": speech_rate
        }
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    if response.status_code == 200:
        return elapsed_ms, len(response.content)
    else:
        return elapsed_ms, 0


def run_single_test(
    audio_data: bytes,
    test_message: str,
    voice_style: str = "normal"
) -> LatencyResult:
    """Run a single end-to-end latency test."""
    result = LatencyResult(voice_style=voice_style)

    # Stage 1: STT
    result.stt_latency_ms, result.transcription = measure_stt(audio_data)

    # Stage 2 & 3: Agent API (acknowledgment + full response)
    (
        result.ack_latency_ms,
        result.first_token_latency_ms,
        result.full_response_latency_ms,
        result.ack_text,
        result.response_text,
        result.ack_received
    ) = measure_agent_response(test_message, voice_style)

    # Stage 4: TTS for acknowledgment (if received)
    if result.ack_received and result.ack_text:
        result.ack_tts_latency_ms, _ = measure_tts(result.ack_text)

    # Stage 5: TTS for full response
    if result.response_text:
        result.response_tts_latency_ms, _ = measure_tts(result.response_text[:200])  # Limit for testing

    result.calculate_derived()
    return result


def print_result(result: LatencyResult, iteration: int):
    """Print a single test result."""
    print(f"\n--- Iteration {iteration} (style: {result.voice_style}) ---")
    print(f"  Message: \"{result.transcription[:40] or 'synthetic audio'}...\"")
    print()

    print(f"  STT:              {result.stt_latency_ms:>7.1f}ms")

    if result.ack_received:
        print(f"  Ack (Haiku):      {result.ack_latency_ms:>7.1f}ms  → \"{result.ack_text}\"")
        print(f"  Ack TTS:          {result.ack_tts_latency_ms:>7.1f}ms")
        print(f"  ───────────────────────────────────────")
        print(f"  🔊 FIRST AUDIO:   {result.time_to_first_audio_ms:>7.1f}ms  ← User hears acknowledgment")
        print()
    else:
        print(f"  Ack (Haiku):      [SKIPPED - style has thinkingFeedback: none]")

    print(f"  Claude (first):   {result.first_token_latency_ms:>7.1f}ms")
    print(f"  Claude (total):   {result.full_response_latency_ms:>7.1f}ms  → \"{result.response_text[:40]}...\"")
    print(f"  Response TTS:     {result.response_tts_latency_ms:>7.1f}ms")
    print(f"  ───────────────────────────────────────")
    print(f"  🔊 FULL AUDIO:    {result.time_to_full_audio_ms:>7.1f}ms  ← User hears complete response")


def print_summary(results: list[LatencyResult]):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print()

    # Calculate averages
    ack_results = [r for r in results if r.ack_received]
    no_ack_results = [r for r in results if not r.ack_received]

    def avg(values):
        return np.mean(values) if values else 0

    stt_avg = avg([r.stt_latency_ms for r in results])
    ack_avg = avg([r.ack_latency_ms for r in ack_results]) if ack_results else None
    ack_tts_avg = avg([r.ack_tts_latency_ms for r in ack_results]) if ack_results else None
    first_token_avg = avg([r.first_token_latency_ms for r in results])
    full_response_avg = avg([r.full_response_latency_ms for r in results])
    response_tts_avg = avg([r.response_tts_latency_ms for r in results])

    time_to_first_audio_avg = avg([r.time_to_first_audio_ms for r in results])
    time_to_full_audio_avg = avg([r.time_to_full_audio_ms for r in results])

    print(f"{'Component':<25} {'Avg (ms)':>12} {'% of Total':>12}")
    print("-" * 50)
    print(f"{'STT':<25} {stt_avg:>11.1f}  {stt_avg/time_to_full_audio_avg*100:>10.1f}%")

    if ack_avg is not None:
        print(f"{'Acknowledgment (Haiku)':<25} {ack_avg:>11.1f}  {ack_avg/time_to_full_audio_avg*100:>10.1f}%")
        print(f"{'Ack TTS':<25} {ack_tts_avg:>11.1f}  {ack_tts_avg/time_to_full_audio_avg*100:>10.1f}%")

    print(f"{'Claude Sonnet (full)':<25} {full_response_avg:>11.1f}  {full_response_avg/time_to_full_audio_avg*100:>10.1f}%")
    print(f"{'Response TTS':<25} {response_tts_avg:>11.1f}  {response_tts_avg/time_to_full_audio_avg*100:>10.1f}%")
    print("-" * 50)
    print(f"{'TIME TO FIRST AUDIO':<25} {time_to_first_audio_avg:>11.1f}")
    print(f"{'TIME TO FULL AUDIO':<25} {time_to_full_audio_avg:>11.1f}")

    # Visual pipeline breakdown
    print("\n" + "=" * 70)
    print("LATENCY PIPELINE VISUALIZATION")
    print("=" * 70)
    print()

    if ack_results:
        ack_path_total = stt_avg + ack_avg + ack_tts_avg
        full_path_total = stt_avg + full_response_avg + response_tts_avg
        improvement = full_path_total - ack_path_total
        improvement_pct = (improvement / full_path_total) * 100

        print("  FAST PATH (with acknowledgment):")
        print(f"  User stops speaking")
        print(f"       │")
        print(f"       ├─ STT Processing:     {stt_avg:>7.1f}ms")
        print(f"       ├─ Haiku 4.5 Ack:      {ack_avg:>7.1f}ms")
        print(f"       └─ TTS (ack):          {ack_tts_avg:>7.1f}ms")
        print(f"       ↓")
        print(f"  🔊 USER HEARS ACK:          {ack_path_total:>7.1f}ms")
        print()
        print("  FULL PATH (main response):")
        print(f"       │")
        print(f"       ├─ STT Processing:     {stt_avg:>7.1f}ms")
        print(f"       ├─ Claude Sonnet:      {full_response_avg:>7.1f}ms  ← BOTTLENECK")
        print(f"       └─ TTS (response):     {response_tts_avg:>7.1f}ms")
        print(f"       ↓")
        print(f"  🔊 USER HEARS RESPONSE:     {full_path_total:>7.1f}ms")
        print()
        print(f"  ✨ FAST PATH IMPROVEMENT: -{improvement:.0f}ms ({improvement_pct:.1f}% faster to first audio)")
    else:
        print("  NO ACKNOWLEDGMENTS (voice style has thinkingFeedback: none)")
        print()
        print(f"  User stops speaking")
        print(f"       │")
        print(f"       ├─ STT Processing:     {stt_avg:>7.1f}ms")
        print(f"       ├─ Claude Sonnet:      {full_response_avg:>7.1f}ms  ← BOTTLENECK")
        print(f"       └─ TTS (response):     {response_tts_avg:>7.1f}ms")
        print(f"       ↓")
        print(f"  🔊 USER HEARS RESPONSE:     {time_to_full_audio_avg:>7.1f}ms")

    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print()

    if full_response_avg > 3000:
        print(f"  🔴 Claude Sonnet is the main bottleneck ({full_response_avg:.0f}ms)")
        print(f"     The fast-layer helps but consider:")
        print(f"     → Sentence-level TTS streaming for progressive audio")
        print(f"     → Use Haiku for simple queries, Sonnet for complex")

    if ack_results and ack_path_total < 1000:
        print(f"  🟢 Fast path achieves <1s to first audio ({ack_path_total:.0f}ms)")
        print(f"     User gets immediate feedback while Sonnet processes")
    elif ack_results:
        print(f"  🟡 Fast path is {ack_path_total:.0f}ms - room for improvement")
        print(f"     Consider optimizing TTS or using pre-cached acknowledgments")

    if response_tts_avg > 1000:
        print(f"  🟡 TTS is slow ({response_tts_avg:.0f}ms)")
        print(f"     → Enable GPU: TTS_DEVICE=cuda")
        print(f"     → Consider streaming TTS for progressive playback")

    print()


def check_services() -> bool:
    """Check if required services are running."""
    print("[1] Checking services...")

    try:
        r = requests.get(f"{VOICE_BACKEND_URL}/health", timeout=2)
        health = r.json()
        stt_status = health.get("stt", {}).get("status", "unknown")
        tts_status = health.get("tts", {}).get("status", "unknown")
        print(f"    ✓ Voice backend: {VOICE_BACKEND_URL}")
        print(f"      STT: {stt_status}, TTS: {tts_status}")
    except Exception as e:
        print(f"    ✗ Voice backend NOT RUNNING: {VOICE_BACKEND_URL}")
        print(f"      Error: {e}")
        return False

    try:
        r = requests.get(f"{AGENT_API_URL}/health", timeout=2)
        print(f"    ✓ Agent API: {AGENT_API_URL}")
    except Exception as e:
        print(f"    ✗ Agent API NOT RUNNING: {AGENT_API_URL}")
        print(f"      Error: {e}")
        return False

    # Check available voice styles
    try:
        r = requests.get(f"{AGENT_API_URL}/api/styles", timeout=2)
        styles = r.json().get("styles", [])
        style_names = [s["id"] for s in styles]
        print(f"    ✓ Voice styles: {', '.join(style_names)}")
    except:
        print(f"    ⚠ Could not fetch voice styles")

    return True


def main():
    parser = argparse.ArgumentParser(description="IRIS Voice Latency Benchmark v2")
    parser.add_argument("--audio", type=str, help="Path to audio file (WAV)")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations")
    parser.add_argument("--voice-style", type=str, default="normal",
                       help="Voice style to test (normal, formal, concise, immersive, learning)")
    parser.add_argument("--compare-styles", action="store_true",
                       help="Compare all voice styles")
    args = parser.parse_args()

    print("=" * 70)
    print("IRIS Voice Pipeline - End-to-End Latency Benchmark v2")
    print("With Fast-Layer (Haiku 4.5) Acknowledgment Tracking")
    print("=" * 70)
    print()

    if not check_services():
        print("\nPlease start the required services and try again.")
        sys.exit(1)

    # Load or create test audio
    if args.audio:
        print(f"\n[2] Loading audio file: {args.audio}")
        audio_data = load_audio_file(args.audio)
    else:
        print(f"\n[2] Using synthetic test audio (2s)")
        audio_data = create_test_audio(2.0)

    print(f"\n[3] Running benchmark ({args.iterations} iterations)...")

    if args.compare_styles:
        # Test all styles
        styles = ["normal", "formal", "concise", "immersive", "learning"]
        all_results = {}

        for style in styles:
            print(f"\n{'='*70}")
            print(f"Testing voice style: {style.upper()}")
            print("=" * 70)

            results = []
            for i in range(args.iterations):
                message = TEST_MESSAGES[i % len(TEST_MESSAGES)]
                result = run_single_test(audio_data, message, style)
                results.append(result)
                print_result(result, i + 1)

            all_results[style] = results

        # Compare styles
        print("\n" + "=" * 70)
        print("STYLE COMPARISON")
        print("=" * 70)
        print()
        print(f"{'Style':<15} {'Ack?':<6} {'First Audio':<15} {'Full Audio':<15}")
        print("-" * 55)

        for style, results in all_results.items():
            ack = "Yes" if any(r.ack_received for r in results) else "No"
            first = np.mean([r.time_to_first_audio_ms for r in results])
            full = np.mean([r.time_to_full_audio_ms for r in results])
            print(f"{style:<15} {ack:<6} {first:>11.1f}ms   {full:>11.1f}ms")

    else:
        # Single style test
        results = []
        for i in range(args.iterations):
            message = TEST_MESSAGES[i % len(TEST_MESSAGES)]
            result = run_single_test(audio_data, message, args.voice_style)
            results.append(result)
            print_result(result, i + 1)

        print_summary(results)

    print("\nBenchmark complete.")


if __name__ == "__main__":
    main()
