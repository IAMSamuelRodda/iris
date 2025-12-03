#!/usr/bin/env python3
"""
TTS Chunking Benchmark - Sentence vs Paragraph Mode

Compares the latency and TTS quality trade-offs between:
1. Sentence-level chunking: Faster first audio, potentially choppier
2. Paragraph-level chunking: More natural prosody, slower first audio

METRICS:
========
- Time to first chunk: How quickly we get a complete sentence/paragraph
- TTS synthesis time per chunk: How long Chatterbox takes
- Total time to first audio: STT + chunk detection + first TTS
- Number of TTS requests: More requests = more overhead
- Chunk sizes: Distribution of text lengths

TRADE-OFFS:
===========
Sentence Mode:
  + Faster time to first audio (~1-2s sooner)
  + More responsive feel
  - Choppier audio (less context for prosody)
  - More TTS requests (more overhead)

Paragraph Mode:
  + More natural prosody (Chatterbox gets more context)
  + Fewer TTS requests
  - Slower time to first audio
  - User waits longer before hearing anything

Usage:
  python test_tts_chunking.py                    # Compare both modes
  python test_tts_chunking.py --mode sentence    # Test sentence mode only
  python test_tts_chunking.py --mode paragraph   # Test paragraph mode only
  python test_tts_chunking.py --no-tts           # Skip TTS, just test chunking
"""

import argparse
import time
import requests
import json
import sys
import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

# Configuration
AGENT_API_URL = "http://localhost:3001"
VOICE_BACKEND_URL = "http://localhost:8001"

# Chunking settings (should match text-chunker.ts)
MIN_CHUNK_SIZE = 10
MAX_CHUNK_SIZE = 500

# Test prompts that generate multi-sentence/paragraph responses
TEST_PROMPTS = [
    "Tell me about Star Atlas and what makes it unique in the gaming space.",
    "Explain how fleet management works and what I should know as a beginner.",
    "What are the different resources in Star Atlas and how are they used?",
]


@dataclass
class ChunkResult:
    """Result of detecting a single chunk."""
    text: str
    mode: str
    detection_time_ms: float
    tts_time_ms: Optional[float] = None
    char_count: int = 0


@dataclass
class ChunkingBenchmark:
    """Full benchmark result for a prompt."""
    prompt: str
    mode: str
    total_response_chars: int = 0
    total_response_time_ms: float = 0
    time_to_first_chunk_ms: float = 0
    time_to_first_audio_ms: float = 0
    chunks: List[ChunkResult] = field(default_factory=list)
    total_tts_time_ms: float = 0


class TextChunker:
    """Python version of text-chunker.ts for testing."""

    # Common abbreviations that shouldn't trigger sentence breaks
    ABBREVIATIONS = {
        "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc",
        "inc", "ltd", "co", "corp", "dept", "est", "approx", "govt",
        "vol", "no", "fig", "e.g", "i.e", "viz", "cf", "al"
    }

    def __init__(self, mode: str = "sentence", min_size: int = MIN_CHUNK_SIZE, max_size: int = MAX_CHUNK_SIZE):
        self.mode = mode
        self.min_size = min_size
        self.max_size = max_size
        self.buffer = ""

    def add(self, text: str) -> List[str]:
        """Add text and return any complete chunks."""
        self.buffer += text
        return self._extract_chunks()

    def flush(self) -> Optional[str]:
        """Flush remaining text."""
        remaining = self.buffer.strip()
        self.buffer = ""
        return remaining if len(remaining) >= self.min_size else None

    def _extract_chunks(self) -> List[str]:
        chunks = []
        while True:
            chunk = self._extract_sentence() if self.mode == "sentence" else self._extract_paragraph()
            if not chunk:
                break
            if len(chunk) >= self.min_size:
                chunks.append(chunk)
            else:
                # Put it back if too small
                self.buffer = chunk + self.buffer
                break

        # Force yield if buffer exceeds max size
        if len(self.buffer) > self.max_size:
            forced = self._force_extract()
            if forced:
                chunks.append(forced)

        return chunks

    def _extract_sentence(self) -> Optional[str]:
        """Extract a complete sentence."""
        # Look for sentence-ending punctuation followed by space or newline
        for match in re.finditer(r'[.!?][\s\n]', self.buffer):
            end_pos = match.start() + 1
            potential = self.buffer[:end_pos]

            # Check for abbreviations
            if self._is_abbreviation(potential):
                continue

            self.buffer = self.buffer[end_pos:].lstrip()
            return potential.strip()

        return None

    def _extract_paragraph(self) -> Optional[str]:
        """Extract a complete paragraph."""
        # Double newline = paragraph break
        idx = self.buffer.find("\n\n")
        if idx != -1:
            paragraph = self.buffer[:idx]
            self.buffer = self.buffer[idx + 2:].lstrip()
            return paragraph.strip()

        # Single newline followed by whitespace
        idx = self.buffer.find("\n")
        if idx != -1:
            after = self.buffer[idx + 1:]
            if after.startswith("\n") or re.match(r'^\s{2,}', after):
                paragraph = self.buffer[:idx]
                self.buffer = after.lstrip()
                return paragraph.strip()

        return None

    def _force_extract(self) -> Optional[str]:
        """Force extract when buffer exceeds max size."""
        if not self.buffer:
            return None

        search_start = max(0, self.max_size - 50)
        search_end = self.max_size
        region = self.buffer[search_start:search_end]

        # Prefer breaking at: sentence > comma > space
        for pattern in ['. ', ', ', ' ']:
            idx = region.rfind(pattern)
            if idx != -1:
                break_point = search_start + idx + (1 if pattern != ' ' else 0)
                chunk = self.buffer[:break_point]
                self.buffer = self.buffer[break_point:].lstrip()
                return chunk.strip()

        # No good break point
        chunk = self.buffer[:self.max_size]
        self.buffer = self.buffer[self.max_size:]
        return chunk.strip()

    def _is_abbreviation(self, text: str) -> bool:
        """Check if text ends with an abbreviation."""
        words = text.strip().split()
        if not words:
            return False
        last_word = re.sub(r'[.!?]+$', '', words[-1].lower())
        return last_word in self.ABBREVIATIONS


def stream_agent_response(prompt: str, user_id: str = "benchmark-user") -> tuple[str, float, List[tuple[str, float]]]:
    """
    Stream a response from the agent API.
    Returns: (full_response, total_time_ms, [(chunk_text, chunk_time_ms), ...])
    """
    url = f"{AGENT_API_URL}/api/chat"
    payload = {
        "userId": user_id,
        "message": prompt,
        "voiceStyle": "normal"
    }

    chunks_with_times = []
    full_response = ""
    start_time = time.time()

    try:
        with requests.post(url, json=payload, stream=True, timeout=60) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                line_str = line.decode('utf-8')
                if not line_str.startswith('data: '):
                    continue

                try:
                    data = json.loads(line_str[6:])
                    if data.get('type') == 'text':
                        chunk_text = data.get('content', '')
                        chunk_time = (time.time() - start_time) * 1000
                        chunks_with_times.append((chunk_text, chunk_time))
                        full_response += chunk_text
                except json.JSONDecodeError:
                    continue

    except requests.RequestException as e:
        print(f"Error streaming from agent: {e}")
        return "", 0, []

    total_time = (time.time() - start_time) * 1000
    return full_response, total_time, chunks_with_times


def synthesize_tts(text: str) -> float:
    """
    Synthesize text with Chatterbox and return time in ms.
    """
    url = f"{VOICE_BACKEND_URL}/synthesize"
    payload = {
        "text": text,
        "exaggeration": 0.5,
        "speechRate": 1.0
    }

    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"TTS error: {e}")
        return -1

    return (time.time() - start_time) * 1000


def run_chunking_benchmark(
    prompt: str,
    mode: str,
    run_tts: bool = True
) -> ChunkingBenchmark:
    """
    Run a full chunking benchmark for a prompt.
    """
    result = ChunkingBenchmark(prompt=prompt, mode=mode)

    # Stream the response
    print(f"  Streaming response...")
    full_response, total_time, raw_chunks = stream_agent_response(prompt)
    result.total_response_chars = len(full_response)
    result.total_response_time_ms = total_time

    if not full_response:
        print(f"  No response received!")
        return result

    # Process chunks through the chunker
    chunker = TextChunker(mode=mode)
    first_chunk_time = None

    for chunk_text, chunk_time in raw_chunks:
        completed = chunker.add(chunk_text)
        for completed_chunk in completed:
            if first_chunk_time is None:
                first_chunk_time = chunk_time

            chunk_result = ChunkResult(
                text=completed_chunk,
                mode=mode,
                detection_time_ms=chunk_time,
                char_count=len(completed_chunk)
            )

            # Run TTS if enabled
            if run_tts:
                tts_time = synthesize_tts(completed_chunk)
                chunk_result.tts_time_ms = tts_time
                result.total_tts_time_ms += max(0, tts_time)

            result.chunks.append(chunk_result)

    # Flush remaining
    remaining = chunker.flush()
    if remaining:
        chunk_result = ChunkResult(
            text=remaining,
            mode=mode,
            detection_time_ms=total_time,
            char_count=len(remaining)
        )

        if run_tts:
            tts_time = synthesize_tts(remaining)
            chunk_result.tts_time_ms = tts_time
            result.total_tts_time_ms += max(0, tts_time)

        result.chunks.append(chunk_result)

    # Calculate timing metrics
    if result.chunks:
        result.time_to_first_chunk_ms = first_chunk_time or 0
        first_tts = result.chunks[0].tts_time_ms if run_tts else 0
        result.time_to_first_audio_ms = result.time_to_first_chunk_ms + (first_tts or 0)

    return result


def print_benchmark_result(result: ChunkingBenchmark):
    """Print a formatted benchmark result."""
    print(f"\n{'=' * 60}")
    print(f"Mode: {result.mode.upper()}")
    print(f"Prompt: {result.prompt[:50]}...")
    print(f"{'=' * 60}")

    print(f"\nTIMING:")
    print(f"  Total response time:    {result.total_response_time_ms:,.0f}ms")
    print(f"  Time to first chunk:    {result.time_to_first_chunk_ms:,.0f}ms")
    print(f"  Time to first audio:    {result.time_to_first_audio_ms:,.0f}ms")
    print(f"  Total TTS time:         {result.total_tts_time_ms:,.0f}ms")

    print(f"\nCHUNKS ({len(result.chunks)} total):")
    for i, chunk in enumerate(result.chunks):
        tts_str = f", TTS: {chunk.tts_time_ms:.0f}ms" if chunk.tts_time_ms else ""
        print(f"  {i+1}. [{chunk.char_count} chars{tts_str}] {chunk.text[:60]}{'...' if len(chunk.text) > 60 else ''}")

    print(f"\nSTATISTICS:")
    if result.chunks:
        sizes = [c.char_count for c in result.chunks]
        tts_times = [c.tts_time_ms for c in result.chunks if c.tts_time_ms and c.tts_time_ms > 0]
        print(f"  Avg chunk size:      {sum(sizes)/len(sizes):.0f} chars")
        print(f"  Min/Max chunk size:  {min(sizes)} / {max(sizes)} chars")
        if tts_times:
            print(f"  Avg TTS time:        {sum(tts_times)/len(tts_times):.0f}ms")
            print(f"  Min/Max TTS time:    {min(tts_times):.0f} / {max(tts_times):.0f}ms")


def compare_modes(prompt: str, run_tts: bool = True):
    """Compare sentence vs paragraph mode for a prompt."""
    print(f"\n{'#' * 70}")
    print(f"COMPARING CHUNK MODES")
    print(f"Prompt: {prompt[:60]}...")
    print(f"{'#' * 70}")

    # Run both modes
    sentence_result = run_chunking_benchmark(prompt, "sentence", run_tts)
    paragraph_result = run_chunking_benchmark(prompt, "paragraph", run_tts)

    # Print individual results
    print_benchmark_result(sentence_result)
    print_benchmark_result(paragraph_result)

    # Print comparison
    print(f"\n{'=' * 60}")
    print("COMPARISON SUMMARY")
    print(f"{'=' * 60}")

    diff_first_chunk = sentence_result.time_to_first_chunk_ms - paragraph_result.time_to_first_chunk_ms
    diff_first_audio = sentence_result.time_to_first_audio_ms - paragraph_result.time_to_first_audio_ms
    diff_tts = sentence_result.total_tts_time_ms - paragraph_result.total_tts_time_ms

    print(f"\n                         SENTENCE    PARAGRAPH    DIFF")
    print(f"  Time to first chunk:   {sentence_result.time_to_first_chunk_ms:>7.0f}ms   {paragraph_result.time_to_first_chunk_ms:>7.0f}ms   {diff_first_chunk:>+7.0f}ms")
    print(f"  Time to first audio:   {sentence_result.time_to_first_audio_ms:>7.0f}ms   {paragraph_result.time_to_first_audio_ms:>7.0f}ms   {diff_first_audio:>+7.0f}ms")
    print(f"  Total TTS time:        {sentence_result.total_tts_time_ms:>7.0f}ms   {paragraph_result.total_tts_time_ms:>7.0f}ms   {diff_tts:>+7.0f}ms")
    print(f"  Number of chunks:      {len(sentence_result.chunks):>7}      {len(paragraph_result.chunks):>7}")

    # Recommendation
    print(f"\nRECOMMENDATION:")
    if diff_first_audio < -500:
        print(f"  SENTENCE mode is {-diff_first_audio:.0f}ms faster to first audio.")
        print(f"  Use SENTENCE for responsive voice interactions.")
    elif diff_first_audio > 500:
        print(f"  PARAGRAPH mode is {diff_first_audio:.0f}ms faster to first audio.")
        print(f"  Use PARAGRAPH for this response pattern.")
    else:
        print(f"  Both modes are similar ({abs(diff_first_audio):.0f}ms difference).")
        print(f"  Use PARAGRAPH for better prosody with minimal latency cost.")

    return sentence_result, paragraph_result


def main():
    parser = argparse.ArgumentParser(description="TTS Chunking Benchmark")
    parser.add_argument("--mode", choices=["sentence", "paragraph"],
                        help="Test specific mode only")
    parser.add_argument("--no-tts", action="store_true",
                        help="Skip TTS synthesis, just test chunking")
    parser.add_argument("--prompt", type=str,
                        help="Custom prompt to test")
    parser.add_argument("--all", action="store_true",
                        help="Run all test prompts")
    args = parser.parse_args()

    prompts = TEST_PROMPTS if args.all else [args.prompt or TEST_PROMPTS[0]]
    run_tts = not args.no_tts

    print("=" * 70)
    print("TTS CHUNKING BENCHMARK")
    print("=" * 70)
    print(f"\nSettings:")
    print(f"  Agent API: {AGENT_API_URL}")
    print(f"  Voice Backend: {VOICE_BACKEND_URL}")
    print(f"  Run TTS: {run_tts}")
    print(f"  Mode: {args.mode or 'compare both'}")
    print(f"  Prompts: {len(prompts)}")

    # Check services are running
    try:
        requests.get(f"{AGENT_API_URL}/health", timeout=5)
        print(f"\n  Agent API: OK")
    except:
        print(f"\n  Agent API: NOT RUNNING - start with: pnpm --filter @iris/agent-core dev")
        sys.exit(1)

    if run_tts:
        try:
            requests.get(f"{VOICE_BACKEND_URL}/health", timeout=5)
            print(f"  Voice Backend: OK")
        except:
            print(f"  Voice Backend: NOT RUNNING - start with: cd packages/voice-backend && python -m src.main")
            sys.exit(1)

    # Run benchmarks
    all_results = []
    for prompt in prompts:
        if args.mode:
            result = run_chunking_benchmark(prompt, args.mode, run_tts)
            print_benchmark_result(result)
            all_results.append((args.mode, result))
        else:
            sentence, paragraph = compare_modes(prompt, run_tts)
            all_results.append(("sentence", sentence))
            all_results.append(("paragraph", paragraph))

    # Final summary
    print(f"\n{'#' * 70}")
    print("FINAL SUMMARY")
    print(f"{'#' * 70}")

    sentence_results = [r for m, r in all_results if m == "sentence"]
    paragraph_results = [r for m, r in all_results if m == "paragraph"]

    if sentence_results:
        avg_first = sum(r.time_to_first_audio_ms for r in sentence_results) / len(sentence_results)
        avg_chunks = sum(len(r.chunks) for r in sentence_results) / len(sentence_results)
        print(f"\nSENTENCE MODE:")
        print(f"  Avg time to first audio: {avg_first:.0f}ms")
        print(f"  Avg chunks per response: {avg_chunks:.1f}")

    if paragraph_results:
        avg_first = sum(r.time_to_first_audio_ms for r in paragraph_results) / len(paragraph_results)
        avg_chunks = sum(len(r.chunks) for r in paragraph_results) / len(paragraph_results)
        print(f"\nPARAGRAPH MODE:")
        print(f"  Avg time to first audio: {avg_first:.0f}ms")
        print(f"  Avg chunks per response: {avg_chunks:.1f}")


if __name__ == "__main__":
    main()
