#!/usr/bin/env python3
"""
Voice Flow Test - Automated test with audio playback.

Tests the full pipeline: Ollama LLM -> TTS -> Play audio
Uses Ollama directly for fast local inference (not Claude Cloud).

Usage:
    python test_voice_flow.py
    python test_voice_flow.py --models qwen2.5:7b,mistral:7b
"""

import os
import sys
import time
import json
import requests
import numpy as np
import scipy.io.wavfile as wav
import subprocess
import tempfile
import argparse

# Setup cuDNN before imports
def _setup_cudnn():
    try:
        import nvidia.cudnn
        cudnn_lib = os.path.join(os.path.dirname(nvidia.cudnn.__file__), "lib")
        if os.path.exists(cudnn_lib):
            import ctypes
            ctypes.CDLL(os.path.join(cudnn_lib, "libcudnn.so.9"), mode=ctypes.RTLD_GLOBAL)
    except:
        pass

_setup_cudnn()

from src.tts_kokoro import get_kokoro_tts

# IRIS system prompt for voice responses
SYSTEM_PROMPT = """You are IRIS, the AI assistant for Star Atlas players.
Keep responses SHORT (1-2 sentences max) - they will be spoken aloud.
Be helpful, friendly, and concise. No markdown or special formatting."""


def play_audio(audio_data, sample_rate=24000):
    """Play audio using aplay."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav.write(f.name, sample_rate, audio_data)
        subprocess.run(["aplay", "-q", f.name], check=True)
        os.unlink(f.name)


def call_ollama(model: str, prompt: str) -> tuple[str, float]:
    """Call Ollama directly for fast local inference."""
    start = time.perf_counter()

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
        },
        timeout=30,
    )

    elapsed = (time.perf_counter() - start) * 1000

    if response.status_code != 200:
        return "", elapsed

    result = response.json()
    return result.get("response", "").strip(), elapsed


def test_voice_flow(tts, query: str, model: str):
    """Test full voice flow: Ollama LLM -> TTS -> Play."""

    # Big banner showing current model
    print(f"\n{'#'*60}")
    print(f"#  MODEL: {model:^46} #")
    print(f"#  Query: {query[:44]:<46} #")
    print(f"{'#'*60}")

    # Step 1: Call Ollama directly
    print(f"\n[1] LLM: Generating with {model}...")
    text, llm_time = call_ollama(model, query)

    print(f"    Time: {llm_time:.0f}ms")
    if text:
        display = text[:80] + "..." if len(text) > 80 else text
        print(f"    Response: \"{display}\"")
    else:
        print("    [No response]")
        return llm_time, 0

    # Step 2: TTS
    print(f"[2] TTS: Synthesizing...")
    start = time.perf_counter()
    tts_result = tts.synthesize(text)
    tts_time = (time.perf_counter() - start) * 1000
    print(f"    Time: {tts_time:.0f}ms | Audio: {tts_result.duration_seconds:.1f}s")

    # Step 3: Play audio with model announcement
    print(f"[3] 🔊 Playing: [{model}]")
    audio_int16 = (tts_result.audio.squeeze() * 32767).astype(np.int16)
    play_audio(audio_int16, tts_result.sample_rate)

    total = llm_time + tts_time
    print(f"\n>>> {model}: {total:.0f}ms total (LLM: {llm_time:.0f}ms + TTS: {tts_time:.0f}ms)")
    return llm_time, tts_time


def main():
    parser = argparse.ArgumentParser(description="Voice flow test with Ollama")
    parser.add_argument("--models", default="qwen2.5:7b,mistral:7b",
                       help="Comma-separated list of models to test")
    parser.add_argument("--queries", default=None,
                       help="Comma-separated list of queries")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",")]

    if args.queries:
        queries = [q.strip() for q in args.queries.split(",")]
    else:
        queries = [
            "What is your name?",
            "Give me a quick status update.",
            "How are you today?",
        ]

    print("=" * 60)
    print("VOICE FLOW TEST - Direct Ollama (Fast Local LLM)")
    print("=" * 60)
    print(f"Models: {', '.join(models)}")
    print(f"Queries: {len(queries)}")

    # Pre-load TTS
    print("\nLoading TTS model...")
    tts = get_kokoro_tts("cuda")
    print("TTS ready!")

    # Warm up Ollama
    print("\nWarming up Ollama...")
    for model in models:
        call_ollama(model, "Hello")
    print("Ollama warm!\n")

    results = {}
    for model in models:
        results[model] = []

        for query in queries:
            try:
                llm_t, tts_t = test_voice_flow(tts, query, model)
                if llm_t:
                    results[model].append((llm_t, tts_t))
                time.sleep(0.5)  # Pause between tests
            except Exception as e:
                print(f"Error: {e}")

    # Summary
    print("\n\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for model, times in results.items():
        if times:
            avg_llm = np.mean([t[0] for t in times])
            avg_tts = np.mean([t[1] for t in times])
            print(f"{model:20s}: LLM={avg_llm:6.0f}ms, TTS={avg_tts:5.0f}ms, Total={avg_llm+avg_tts:6.0f}ms")


if __name__ == "__main__":
    main()
