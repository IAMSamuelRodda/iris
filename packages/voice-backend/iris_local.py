#!/usr/bin/env python3
"""
IRIS Local - Native Python voice client with minimal latency.

Bypasses all web infrastructure for direct audio I/O:
- sounddevice for microphone/speaker access (no WebSocket)
- Silero VAD for always-listening mode
- Direct integration with STT, LLM, TTS components

Target: <300ms first audio (vs ~500ms with web stack)

Modes:
- PTT (Push-to-Talk): Spacebar to record
- VAD (Voice Activity Detection): Always listening, auto-detects speech

Usage:
    python iris_local.py                    # PTT mode (default)
    python iris_local.py --vad              # VAD always-listening mode
    python iris_local.py --model mistral:7b # Different LLM model
    python iris_local.py --gui              # Launch GUI (DearPyGui)

Architecture:
    ┌─────────────────────────────────────────────────┐
    │                iris_local.py                    │
    ├─────────────────────────────────────────────────┤
    │  Audio I/O (sounddevice)                        │
    │  ├── Input: 16kHz mono (microphone)             │
    │  └── Output: 24kHz stereo (speaker)             │
    ├─────────────────────────────────────────────────┤
    │  VAD (Silero) - optional always-listening       │
    ├─────────────────────────────────────────────────┤
    │  Pipeline (existing components)                 │
    │  ├── STT: faster-whisper (22-28ms)              │
    │  ├── LLM: Ollama streaming (70ms first token)   │
    │  └── TTS: Kokoro (40-95ms per chunk)            │
    └─────────────────────────────────────────────────┘
"""

import os
import sys
import time
import queue
import asyncio
import argparse
import tempfile
import threading
import logging
from dataclasses import dataclass
from typing import Callable, Generator

import numpy as np
import requests

# Tools module
from src.tools import TOOLS, execute_tool, supports_tools

# Setup cuDNN before other imports
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ==============================================================================
# System Prompts (Global + Model-Specific)
# ==============================================================================

# TODO(ISSUE-015): Remove capability limitations when MCP tools are integrated
# See ISSUES.md for tracking. Current restrictions prevent hallucinations in local testing mode.

SYSTEM_PROMPT_BASE = """You are IRIS, a voice assistant for Star Atlas players.

CRITICAL RULES:
- Keep responses SHORT (1-2 sentences max) - they will be spoken aloud
- NEVER use placeholder text like [Event Name], [Time], [Location], etc.
- If you don't know something specific, say so directly
- No markdown, bullet points, or special formatting
- Speak naturally as if in conversation

TOOLS AVAILABLE:
- get_current_time: Get the current time and date (use for "what time is it", "what day is it")
- calculate: Do math calculations (use for any arithmetic, percentages, etc.)

Use tools when the user asks about time/date or needs calculations. After getting tool results, give a natural spoken response.

You're a helpful companion who chats about Star Atlas, space gaming, and general topics.
You DON'T have access to: fleet data, wallet balances, real-time prices, or game APIs.
If asked about these, explain you're in local testing mode without those integrations."""

# Model-specific prompts - keyed by model family (prefix match)
# These are APPENDED to the base prompt for specific model quirks
MODEL_PROMPTS: dict[str, str] = {
    "qwen": """

QWEN-SPECIFIC:
- Respond ONLY in English, never Chinese characters
- Don't use emoji or special unicode symbols""",

    "mistral": """

MISTRAL-SPECIFIC:
- Be more concise than your default - aim for 1 sentence when possible
- Avoid being overly formal or verbose""",

    "llama": """

LLAMA-SPECIFIC:
- Stay focused on the question asked
- Don't add unnecessary caveats or disclaimers""",

    "phi": """

PHI-SPECIFIC:
- Keep responses extremely brief (1 sentence ideal)
- Don't over-explain simple concepts""",
}


def get_system_prompt(model_name: str, log: bool = False) -> str:
    """
    Build system prompt from base + model-specific additions.

    Args:
        model_name: Ollama model name (e.g., "qwen2.5:7b", "mistral:7b")
        log: If True, log which model-specific prompt was used

    Returns:
        Combined system prompt
    """
    prompt = SYSTEM_PROMPT_BASE
    matched_family = None

    # Find matching model-specific prompt (prefix match)
    model_lower = model_name.lower()
    for model_family, model_prompt in MODEL_PROMPTS.items():
        if model_lower.startswith(model_family):
            prompt += model_prompt
            matched_family = model_family
            break

    if log:
        if matched_family:
            logger.info(f"[LLM] Using {matched_family.upper()}-specific system prompt")
        else:
            logger.info(f"[LLM] Using base system prompt (no model-specific rules for {model_name})")

    return prompt


# ==============================================================================
# Configuration
# ==============================================================================

@dataclass
class IrisConfig:
    """Configuration for IRIS Local."""
    # Audio
    sample_rate_in: int = 16000   # Mic input (Whisper expects 16kHz)
    sample_rate_out: int = 24000  # Speaker output (Kokoro outputs 24kHz)
    channels_in: int = 1
    channels_out: int = 1
    input_device: int | None = None   # None = default, or device index
    output_device: int | None = None  # None = default, or device index

    # LLM
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    max_tokens: int = 150
    enable_tools: bool = True  # Enable Ollama tool calling

    # STT
    stt_model: str = os.getenv("STT_MODEL_SIZE", "base")
    stt_device: str = os.getenv("STT_DEVICE", "cuda")

    # TTS
    tts_device: str = os.getenv("TTS_DEVICE", "cuda")
    tts_voice: str = "af_heart"

    # VAD
    vad_threshold: float = 0.5
    silence_duration: float = 0.5  # Seconds of silence to end recording
    min_speech_duration: float = 1.0  # Minimum speech to process (filters short noises)


# ==============================================================================
# Silero VAD Integration
# ==============================================================================

class SileroVAD:
    """
    Silero Voice Activity Detection.

    Detects speech in audio stream with ~50ms latency.
    Does NOT use RealtimeSTT - direct model inference.
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._model = None
        self._utils = None

    @property
    def model(self):
        """Lazy-load VAD model."""
        if self._model is None:
            import torch
            logger.info("[VAD] Loading Silero VAD model...")
            self._model, self._utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,  # Use PyTorch for CUDA support
            )
            logger.info("[VAD] Model loaded")
        return self._model

    def is_speech(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> tuple[bool, float]:
        """
        Check if audio chunk contains speech.

        Args:
            audio_chunk: Audio samples (float32, -1 to 1)
            sample_rate: Sample rate (16000 for Whisper compatibility)

        Returns:
            (is_speech, confidence) tuple
        """
        import torch

        # Ensure float32 and correct shape
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)

        # Silero expects 512 samples at 16kHz (32ms chunks)
        tensor = torch.from_numpy(audio_chunk)

        # Get speech probability
        speech_prob = self.model(tensor, sample_rate).item()

        return speech_prob > self.threshold, speech_prob


# ==============================================================================
# Audio I/O
# ==============================================================================

class AudioIO:
    """
    Direct audio I/O using sounddevice or ffmpeg fallback.

    Zero network overhead - talks directly to hardware.
    Uses ffmpeg for PipeWire compatibility when sounddevice fails.
    """

    def __init__(self, config: IrisConfig):
        import sounddevice as sd
        self.sd = sd
        self.config = config
        self._recording = False
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._use_ffmpeg = False
        self._ffmpeg_process = None

        # Auto-detect if we need ffmpeg fallback (PipeWire without direct device)
        if config.input_device is None:
            self._use_ffmpeg = self._should_use_ffmpeg()

    def _should_use_ffmpeg(self) -> bool:
        """
        Detect if we need ffmpeg fallback for audio capture.

        Returns True if:
        - Running on PipeWire and sounddevice captures silence
        - No direct ALSA device available
        """
        # Check if ffmpeg is available
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.debug("[Audio] ffmpeg not available, using sounddevice")
            return False

        # Check if PipeWire is running
        try:
            result = subprocess.run(["pgrep", "-x", "pipewire"], capture_output=True)
            if result.returncode != 0:
                logger.debug("[Audio] PipeWire not running, using sounddevice")
                return False
        except FileNotFoundError:
            return False

        # Try a quick sounddevice capture test
        try:
            test_audio = self.sd.rec(
                int(0.1 * self.config.sample_rate_in),  # 100ms test
                samplerate=self.config.sample_rate_in,
                channels=self.config.channels_in,
                dtype='float32',
            )
            self.sd.wait()
            peak = np.max(np.abs(test_audio))

            # If peak is extremely low, sounddevice isn't getting real audio
            if peak < 0.0001:
                logger.info("[Audio] sounddevice capturing silence - enabling ffmpeg fallback")
                return True
            else:
                logger.debug(f"[Audio] sounddevice working (peak={peak:.4f})")
                return False
        except Exception as e:
            logger.warning(f"[Audio] sounddevice test failed: {e} - enabling ffmpeg fallback")
            return True

    def list_devices(self):
        """List available audio devices."""
        print(self.sd.query_devices())

    def _record_with_ffmpeg(self, on_chunk: Callable[[np.ndarray], None] = None) -> np.ndarray:
        """
        Record audio using ffmpeg (PipeWire/PulseAudio fallback).

        Uses: ffmpeg -f pulse -i default -ar 16000 -ac 1 -f s16le pipe:1
        """
        import subprocess

        chunks = []
        chunk_samples = 512  # Match sounddevice blocksize

        # Start ffmpeg process
        cmd = [
            "ffmpeg",
            "-f", "pulse",
            "-i", "default",
            "-ar", str(self.config.sample_rate_in),
            "-ac", str(self.config.channels_in),
            "-f", "s16le",  # Raw 16-bit little-endian PCM
            "-loglevel", "error",
            "pipe:1"
        ]

        logger.debug(f"[Audio] Starting ffmpeg: {' '.join(cmd)}")
        self._ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        bytes_per_sample = 2  # 16-bit = 2 bytes
        bytes_per_chunk = chunk_samples * bytes_per_sample

        try:
            while self._recording and self._ffmpeg_process.poll() is None:
                # Read chunk from ffmpeg stdout
                data = self._ffmpeg_process.stdout.read(bytes_per_chunk)
                if not data:
                    break

                # Convert to float32 numpy array
                audio_int16 = np.frombuffer(data, dtype=np.int16)
                chunk = audio_int16.astype(np.float32) / 32768.0

                chunks.append(chunk)
                if on_chunk:
                    on_chunk(chunk)
        finally:
            # Cleanup
            if self._ffmpeg_process:
                self._ffmpeg_process.terminate()
                self._ffmpeg_process.wait()
                self._ffmpeg_process = None

        if chunks:
            return np.concatenate(chunks)
        return np.array([], dtype=np.float32)

    def record_until_release(self, on_chunk: Callable[[np.ndarray], None] = None) -> np.ndarray:
        """
        Record audio until stopped.

        Uses ffmpeg fallback automatically if PipeWire detected and sounddevice fails.

        Returns:
            Audio samples as float32 numpy array
        """
        self._recording = True

        # Use ffmpeg fallback if enabled
        if self._use_ffmpeg:
            logger.debug("[Audio] Recording with ffmpeg (PipeWire mode)")
            return self._record_with_ffmpeg(on_chunk)

        # Standard sounddevice recording
        chunks = []

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"[Audio] {status}")
            if self._recording:
                chunk = indata.copy().flatten()
                chunks.append(chunk)
                if on_chunk:
                    on_chunk(chunk)

        with self.sd.InputStream(
            device=self.config.input_device,
            samplerate=self.config.sample_rate_in,
            channels=self.config.channels_in,
            dtype='float32',
            callback=callback,
            blocksize=512,  # ~32ms chunks at 16kHz
        ):
            while self._recording:
                self.sd.sleep(10)

        if chunks:
            return np.concatenate(chunks)
        return np.array([], dtype=np.float32)

    def stop_recording(self):
        """Stop the current recording."""
        self._recording = False
        # Also terminate ffmpeg if running
        if self._ffmpeg_process:
            self._ffmpeg_process.terminate()

    def play(self, audio: np.ndarray, sample_rate: int = None):
        """
        Play audio through speakers.

        Args:
            audio: Audio samples (float32 or int16)
            sample_rate: Sample rate (default: config.sample_rate_out)
        """
        if sample_rate is None:
            sample_rate = self.config.sample_rate_out

        # Convert int16 to float32 if needed
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        self.sd.play(audio, sample_rate, device=self.config.output_device)
        self.sd.wait()  # Block until done

    def play_async(self, audio: np.ndarray, sample_rate: int = None):
        """Play audio without blocking."""
        if sample_rate is None:
            sample_rate = self.config.sample_rate_out

        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        self.sd.play(audio, sample_rate, device=self.config.output_device)

    def play_interruptible(self, audio: np.ndarray, sample_rate: int = None,
                          check_interrupt: callable = None) -> int:
        """
        Play audio with interrupt checking using streaming output.

        Args:
            audio: Audio samples
            sample_rate: Sample rate
            check_interrupt: Callable returning True if playback should stop

        Returns:
            Number of samples actually played before interruption (or total if completed)
        """
        if sample_rate is None:
            sample_rate = self.config.sample_rate_out

        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        # Use streaming output for smooth playback with interrupt checking
        samples_played = 0
        interrupted = False
        check_interval = 0.05  # Check for interrupt every 50ms

        # Start playback
        self.sd.play(audio, sample_rate, device=self.config.output_device)

        # Monitor for interrupts while playing
        total_duration = len(audio) / sample_rate
        start_time = time.perf_counter()

        while True:
            elapsed = time.perf_counter() - start_time
            if elapsed >= total_duration:
                break

            # Check for interrupt
            if check_interrupt and check_interrupt():
                self.sd.stop()
                samples_played = int(elapsed * sample_rate)
                interrupted = True
                logger.info(f"[Audio] Playback interrupted at {elapsed:.2f}s")
                break

            time.sleep(check_interval)

        if not interrupted:
            self.sd.wait()  # Wait for playback to finish
            samples_played = len(audio)

        return samples_played

    def stop_playback(self):
        """Stop any ongoing playback."""
        self.sd.stop()


# ==============================================================================
# Voice Pipeline
# ==============================================================================

@dataclass
class InterruptionEvent:
    """Tracks interruption context for natural conversation flow."""
    intended_response: str      # Full response IRIS was going to say
    spoken_up_to: str           # What user actually heard
    user_interruption: str      # What they said (filled after STT)
    timestamp: float = 0.0


class IrisLocal:
    """
    Main IRIS Local voice pipeline.

    Orchestrates: Audio → VAD → STT → LLM → TTS → Audio
    Supports barge-in interruption for natural conversation.
    """

    def __init__(self, config: IrisConfig = None):
        self.config = config or IrisConfig()
        self.audio = AudioIO(self.config)
        self.vad = SileroVAD(self.config.vad_threshold)

        # Lazy-loaded components
        self._stt = None
        self._tts = None
        self._warmed_up = False

        # Interruption handling
        self._is_speaking = False
        self._interrupt_requested = False
        self._last_interruption: InterruptionEvent | None = None
        self._vad_monitor_thread: threading.Thread | None = None
        self._vad_monitor_active = False

        # Conversation history (last N turns)
        self._conversation_history: list[dict] = []
        self._max_history_turns = 10  # Keep last 10 exchanges

        # Context window tracking
        self._context_used = 0  # Tokens used in last request (prompt_eval_count)
        self._context_max = 8192  # Default, updated from model info
        self._total_tokens_session = 0  # Running total for session

    @property
    def stt(self):
        """Lazy-load STT."""
        if self._stt is None:
            from src.stt import get_stt
            self._stt = get_stt(self.config.stt_model, self.config.stt_device)
        return self._stt

    @property
    def tts(self):
        """Lazy-load TTS."""
        if self._tts is None:
            from src.tts_kokoro import get_kokoro_tts
            self._tts = get_kokoro_tts(self.config.tts_device)
            # Set voice from config
            self._tts.current_voice = self.config.tts_voice
        return self._tts

    def warmup(self):
        """Warm up all components for minimum first-request latency."""
        if self._warmed_up:
            return

        logger.info("=" * 50)
        logger.info("WARMING UP COMPONENTS...")
        logger.info("=" * 50)

        start = time.perf_counter()

        # Warm STT
        logger.info("[STT] Loading model...")
        _ = self.stt.model
        audio = np.random.randn(32000).astype(np.float32) * 0.01
        self.stt.transcribe(audio, beam_size=1)

        # Warm TTS
        logger.info("[TTS] Loading model...")
        _ = self.tts.pipeline
        self.tts.synthesize("Ready.")

        # Warm VAD
        logger.info("[VAD] Loading model...")
        _ = self.vad.model

        # Warm LLM
        logger.info(f"[LLM] Warming {self.config.ollama_model}...")
        self._call_llm("Hello", stream=False)

        elapsed = time.perf_counter() - start
        logger.info(f"WARMUP COMPLETE: {elapsed:.1f}s")
        logger.info("=" * 50)

        self._warmed_up = True

    def _start_vad_monitor(self):
        """Start VAD monitoring for barge-in detection during TTS playback."""
        import subprocess

        self._vad_monitor_active = True
        self._interrupt_requested = False

        def monitor_loop():
            # Create separate VAD instance to avoid thread conflicts with main VAD
            monitor_vad = SileroVAD(threshold=0.7)  # Higher threshold for interruption

            # Use ffmpeg to capture audio for VAD
            cmd = [
                "ffmpeg", "-f", "pulse", "-i", "default",
                "-ar", "16000", "-ac", "1", "-f", "s16le",
                "-loglevel", "error", "pipe:1"
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            chunk_samples = 512
            bytes_per_chunk = chunk_samples * 2
            speech_frames = 0
            speech_threshold = 3  # Need 3 consecutive speech frames (~100ms)

            try:
                while self._vad_monitor_active and process.poll() is None:
                    data = process.stdout.read(bytes_per_chunk)
                    if not data:
                        break

                    audio_int16 = np.frombuffer(data, dtype=np.int16)
                    chunk = audio_int16.astype(np.float32) / 32768.0

                    # Skip chunks that are too short for VAD (min 512 samples at 16kHz)
                    if len(chunk) < 512:
                        continue

                    is_speech, confidence = monitor_vad.is_speech(chunk)

                    if is_speech and confidence > 0.7:  # Higher threshold for interruption
                        speech_frames += 1
                        if speech_frames >= speech_threshold:
                            logger.info(f"[VAD] Barge-in detected! (confidence: {confidence:.2f})")
                            self._interrupt_requested = True
                            break
                    else:
                        speech_frames = 0
            finally:
                process.terminate()
                process.wait()

        self._vad_monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._vad_monitor_thread.start()

    def _stop_vad_monitor(self):
        """Stop VAD monitoring."""
        self._vad_monitor_active = False
        if self._vad_monitor_thread:
            self._vad_monitor_thread.join(timeout=0.5)
            self._vad_monitor_thread = None

    def _check_interrupt(self) -> bool:
        """Check if interruption was requested."""
        return self._interrupt_requested

    def _call_llm_stream(self, prompt: str) -> Generator[str, None, None]:
        """
        Call Ollama LLM with streaming.

        Yields tokens as they arrive for progressive TTS.
        """
        payload = {
            "model": self.config.ollama_model,
            "prompt": prompt,
            "system": get_system_prompt(self.config.ollama_model),
            "stream": True,
            "options": {
                "num_predict": self.config.max_tokens,
            },
        }

        response = requests.post(
            f"{self.config.ollama_url}/api/generate",
            json=payload,
            stream=True,
            timeout=60,
        )

        import json
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "response" in data:
                    yield data["response"]
                if data.get("done", False):
                    break

    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self._conversation_history.append({"role": role, "content": content})
        # Trim to max turns (each turn = user + assistant = 2 messages)
        max_messages = self._max_history_turns * 2
        if len(self._conversation_history) > max_messages:
            self._conversation_history = self._conversation_history[-max_messages:]

    def clear_history(self):
        """Clear conversation history."""
        self._conversation_history = []
        self._total_tokens_session = 0

    def get_context_stats(self) -> dict:
        """Get current context window usage stats."""
        return {
            "context_used": self._context_used,
            "context_max": self._context_max,
            "session_tokens": self._total_tokens_session,
            "history_turns": len(self._conversation_history) // 2,
            "max_history_turns": self._max_history_turns,
        }

    def _call_llm(self, prompt: str, stream: bool = False) -> str:
        """
        Call Ollama LLM with conversation history and tool support.

        Args:
            prompt: User prompt
            stream: If True, use _call_llm_stream instead

        Returns:
            Full response string
        """
        if stream:
            # For streaming, caller should use _call_llm_stream directly
            return "".join(self._call_llm_stream(prompt))

        # Build messages with history (uses model-specific system prompt)
        messages = [{"role": "system", "content": get_system_prompt(self.config.ollama_model, log=True)}]

        # Add interruption context if present - persist in conversation history
        if self._last_interruption:
            ie = self._last_interruption
            interruption_note = (
                f"[INTERRUPTION: You were interrupted. "
                f"You intended to say: \"{ie.intended_response}\" "
                f"but user only heard: \"{ie.spoken_up_to}\"]"
            )
            # Add to conversation history so it persists for future reference
            self._conversation_history.append({
                "role": "assistant",
                "content": interruption_note
            })
            logger.info(f"[LLM] Added interruption context to history")
            self._last_interruption = None

        # Add conversation history
        messages.extend(self._conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": prompt})

        # Check if tools are enabled and model supports them
        use_tools = (
            self.config.enable_tools
            and supports_tools(self.config.ollama_model)
        )

        payload = {
            "model": self.config.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": self.config.max_tokens,
            },
        }

        # Add tools if enabled
        if use_tools:
            payload["tools"] = TOOLS
            logger.debug(f"[LLM] Tools enabled: {len(TOOLS)} tools available")

        response = requests.post(
            f"{self.config.ollama_url}/api/chat",
            json=payload,
            timeout=60,
        )
        result = response.json()

        # Check for tool calls
        message = result.get("message", {})
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            # Execute tools and get final response
            assistant_response = self._handle_tool_calls(messages, message, tool_calls)
        else:
            assistant_response = message.get("content", "").strip()

        # Track token usage from Ollama response
        prompt_tokens = result.get("prompt_eval_count", 0)
        completion_tokens = result.get("eval_count", 0)
        self._context_used = prompt_tokens
        self._total_tokens_session += prompt_tokens + completion_tokens

        # Log token usage
        logger.info(f"[LLM] Tokens: {prompt_tokens} prompt + {completion_tokens} completion = {prompt_tokens + completion_tokens} total (session: {self._total_tokens_session})")

        # Add to history
        self.add_to_history("user", prompt)
        self.add_to_history("assistant", assistant_response)

        return assistant_response

    def _handle_tool_calls(
        self,
        messages: list[dict],
        assistant_message: dict,
        tool_calls: list[dict],
    ) -> str:
        """
        Execute tool calls and get final response from LLM.

        Args:
            messages: Conversation messages so far
            assistant_message: The assistant's message with tool calls
            tool_calls: List of tool calls to execute

        Returns:
            Final assistant response after tool execution
        """
        # Add assistant's tool call message
        messages.append(assistant_message)

        # Execute each tool and add results
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            tool_name = func.get("name", "unknown")
            tool_args = func.get("arguments", {})

            logger.info(f"[LLM] Tool call: {tool_name}({tool_args})")

            # Execute the tool
            tool_result = execute_tool(tool_name, tool_args)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "content": tool_result,
            })

        # Call LLM again for final response
        payload = {
            "model": self.config.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": self.config.max_tokens,
            },
        }

        response = requests.post(
            f"{self.config.ollama_url}/api/chat",
            json=payload,
            timeout=60,
        )
        result = response.json()
        final_response = result.get("message", {}).get("content", "").strip()

        # Track additional tokens from tool follow-up
        prompt_tokens = result.get("prompt_eval_count", 0)
        completion_tokens = result.get("eval_count", 0)
        self._total_tokens_session += prompt_tokens + completion_tokens

        logger.info(f"[LLM] Tool follow-up tokens: {prompt_tokens} + {completion_tokens}")

        return final_response

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text."""
        start = time.perf_counter()
        # Disable faster-whisper's internal VAD - we use Silero VAD externally
        result = self.stt.transcribe(audio, beam_size=1, vad_filter=False)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"[STT] {elapsed:.0f}ms: \"{result.text}\"")
        return result.text

    def speak(self, text: str, stream_sentences: bool = True, interruptible: bool = None) -> str:
        """
        Synthesize and play text.

        Args:
            text: Text to speak
            stream_sentences: If True, play as sentences complete (lower latency)
            interruptible: If True, check for barge-in interrupts. Defaults to _is_speaking state.

        Returns:
            Text that was actually spoken (may be truncated if interrupted)
        """
        # Default to current speaking state for interrupt checking
        if interruptible is None:
            interruptible = self._is_speaking

        spoken_text = []

        if stream_sentences:
            # Split into sentences for progressive playback
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)

            for sentence in sentences:
                if sentence.strip():
                    # Check for interrupt before each sentence
                    if interruptible and self._interrupt_requested:
                        logger.info(f"[TTS] Interrupted before sentence: \"{sentence[:30]}...\"")
                        break

                    start = time.perf_counter()
                    result = self.tts.synthesize(sentence)
                    elapsed = (time.perf_counter() - start) * 1000
                    logger.debug(f"[TTS] {elapsed:.0f}ms for \"{sentence[:30]}...\"")

                    audio = (result.audio.squeeze() * 32767).astype(np.int16)

                    if interruptible:
                        samples_played = self.audio.play_interruptible(
                            audio, result.sample_rate, self._check_interrupt
                        )
                        # Calculate how much of the sentence was spoken
                        if samples_played < len(audio):
                            # Partial playback - estimate words spoken
                            fraction = samples_played / len(audio)
                            words = sentence.split()
                            words_spoken = int(len(words) * fraction)
                            spoken_text.append(' '.join(words[:max(1, words_spoken)]) + "—")
                            logger.info(f"[TTS] Interrupted mid-sentence at {fraction:.0%}")
                            break
                        else:
                            spoken_text.append(sentence)
                    else:
                        self.audio.play(audio, result.sample_rate)
                        spoken_text.append(sentence)
        else:
            start = time.perf_counter()
            result = self.tts.synthesize(text)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(f"[TTS] {elapsed:.0f}ms total")

            audio = (result.audio.squeeze() * 32767).astype(np.int16)

            if interruptible:
                samples_played = self.audio.play_interruptible(
                    audio, result.sample_rate, self._check_interrupt
                )
                if samples_played < len(audio):
                    fraction = samples_played / len(audio)
                    words = text.split()
                    words_spoken = int(len(words) * fraction)
                    spoken_text.append(' '.join(words[:max(1, words_spoken)]) + "—")
                else:
                    spoken_text.append(text)
            else:
                self.audio.play(audio, result.sample_rate)
                spoken_text.append(text)

        return ' '.join(spoken_text)

    def process_voice(self, audio: np.ndarray, allow_interrupt: bool = True) -> str:
        """
        Full voice pipeline: STT → LLM → TTS with barge-in support.

        Args:
            audio: Input audio from user
            allow_interrupt: If True, monitor for user interruption during TTS

        Returns:
            LLM response text (or partial if interrupted)
        """
        total_start = time.perf_counter()

        # Check for previous interruption context - add to conversation history
        if self._last_interruption:
            ie = self._last_interruption
            interruption_note = (
                f"[INTERRUPTION: You were interrupted. "
                f"You intended to say: \"{ie.intended_response}\" "
                f"but user only heard: \"{ie.spoken_up_to}\"]"
            )
            # Add to conversation history so it persists for future reference
            self._conversation_history.append({
                "role": "assistant",
                "content": interruption_note
            })
            logger.info(f"[LLM] Added interruption context to history")
            self._last_interruption = None

        # STT
        text = self.transcribe(audio)
        if not text.strip():
            logger.info("[Pipeline] No speech detected")
            return ""

        prompt = text

        # LLM (streaming) + TTS (progressive with interruption)
        logger.info(f"[LLM] Generating response...")

        llm_start = time.perf_counter()
        first_token_time = None

        # Accumulate for sentence detection
        buffer = ""
        full_response = ""
        spoken_text = ""
        was_interrupted = False
        import re

        # Start VAD monitoring for barge-in if enabled
        if allow_interrupt:
            self._start_vad_monitor()
            self._is_speaking = True

        try:
            for token in self._call_llm_stream(prompt):
                # Check for interruption
                if allow_interrupt and self._check_interrupt():
                    logger.info("[Pipeline] User interrupted - stopping response")
                    was_interrupted = True
                    self.audio.stop_playback()
                    break

                if first_token_time is None:
                    first_token_time = (time.perf_counter() - llm_start) * 1000
                    logger.info(f"[LLM] First token: {first_token_time:.0f}ms")

                buffer += token
                full_response += token

                # Check for complete sentence
                match = re.match(r'(.+?[.!?])\s*', buffer)
                if match:
                    sentence = match.group(1)
                    buffer = buffer[len(match.group(0)):]

                    # Check interrupt before speaking each sentence
                    if allow_interrupt and self._check_interrupt():
                        logger.info("[Pipeline] User interrupted before sentence")
                        was_interrupted = True
                        break

                    # Speak sentence with interrupt checking
                    logger.info(f"[TTS] Speaking: \"{sentence}\"")
                    result = self.tts.synthesize(sentence)
                    tts_audio = (result.audio.squeeze() * 32767).astype(np.int16)

                    if allow_interrupt:
                        samples_played = self.audio.play_interruptible(
                            tts_audio, result.sample_rate, self._check_interrupt
                        )
                        # Track what was actually spoken
                        if samples_played < len(tts_audio):
                            # Partial playback - estimate spoken portion
                            ratio = samples_played / len(tts_audio)
                            chars_spoken = int(len(sentence) * ratio)
                            spoken_text += sentence[:chars_spoken]
                            was_interrupted = True
                            break
                        else:
                            spoken_text += sentence + " "
                    else:
                        self.audio.play(tts_audio, result.sample_rate)
                        spoken_text += sentence + " "

            # Speak any remaining text (if not interrupted)
            if not was_interrupted and buffer.strip():
                logger.info(f"[TTS] Speaking final: \"{buffer}\"")
                result = self.tts.synthesize(buffer)
                tts_audio = (result.audio.squeeze() * 32767).astype(np.int16)

                if allow_interrupt:
                    self.audio.play_interruptible(tts_audio, result.sample_rate, self._check_interrupt)
                else:
                    self.audio.play(tts_audio, result.sample_rate)
                spoken_text += buffer

        finally:
            self._is_speaking = False
            if allow_interrupt:
                self._stop_vad_monitor()

        # Store interruption event for next turn
        if was_interrupted:
            self._last_interruption = InterruptionEvent(
                intended_response=full_response + buffer,  # What we were going to say
                spoken_up_to=spoken_text.strip(),
                user_interruption="",  # Will be filled by next STT
                timestamp=time.time()
            )
            logger.info(f"[Pipeline] Interrupted. Spoken: \"{spoken_text[:50]}...\"")

        total_elapsed = (time.perf_counter() - total_start) * 1000
        logger.info(f"[Pipeline] Total: {total_elapsed:.0f}ms")

        return full_response


# ==============================================================================
# PTT Mode (Push-to-Talk)
# ==============================================================================

def run_ptt_mode(iris: IrisLocal):
    """
    Push-to-Talk mode using keyboard.

    Press Enter to start/stop recording.
    """
    import sys
    import select
    import termios
    import tty

    print("\n" + "=" * 50)
    print("IRIS LOCAL - Push-to-Talk Mode")
    print("=" * 50)
    print("Press ENTER to start recording")
    print("Press ENTER again to stop and process")
    print("Press Ctrl+C to exit")
    print("=" * 50 + "\n")

    # Store terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin.fileno())

        while True:
            print("\n[Ready] Press ENTER to speak...")

            # Wait for Enter key
            while True:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    c = sys.stdin.read(1)
                    if c == '\n' or c == '\r':
                        break
                    elif c == '\x03':  # Ctrl+C
                        raise KeyboardInterrupt

            print("[Recording] Speak now... (Press ENTER to stop)")

            # Start recording in background thread
            audio_chunks = []
            recording = True

            def record_callback(chunk):
                audio_chunks.append(chunk)

            record_thread = threading.Thread(
                target=lambda: iris.audio.record_until_release(record_callback)
            )
            record_thread.start()

            # Wait for Enter to stop
            while True:
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    c = sys.stdin.read(1)
                    if c == '\n' or c == '\r':
                        iris.audio.stop_recording()
                        break
                    elif c == '\x03':
                        iris.audio.stop_recording()
                        raise KeyboardInterrupt

            record_thread.join()

            if audio_chunks:
                audio = np.concatenate(audio_chunks)
                duration = len(audio) / iris.config.sample_rate_in
                print(f"[Recorded] {duration:.1f}s of audio")

                # Process through pipeline
                iris.process_voice(audio)
            else:
                print("[No audio captured]")

    except KeyboardInterrupt:
        print("\n\nExiting...")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


# ==============================================================================
# VAD Mode (Always Listening)
# ==============================================================================

def run_vad_mode(iris: IrisLocal):
    """
    Voice Activity Detection mode - always listening.

    Automatically detects speech start/end and processes.
    """
    import sounddevice as sd

    print("\n" + "=" * 50)
    print("IRIS LOCAL - VAD Mode (Always Listening)")
    print("=" * 50)
    print("Speak at any time - IRIS is listening")
    print("Press Ctrl+C to exit")
    print("=" * 50 + "\n")

    # State
    is_speaking = False
    audio_buffer = []
    silence_samples = 0
    silence_threshold = int(iris.config.silence_duration * iris.config.sample_rate_in)
    min_samples = int(iris.config.min_speech_duration * iris.config.sample_rate_in)

    chunk_size = 512  # ~32ms at 16kHz

    def audio_callback(indata, frames, time_info, status):
        nonlocal is_speaking, audio_buffer, silence_samples

        if status:
            logger.warning(f"[Audio] {status}")

        chunk = indata.copy().flatten()

        # Check VAD
        is_speech, confidence = iris.vad.is_speech(chunk)

        if is_speech:
            if not is_speaking:
                # Speech started
                logger.info(f"[VAD] Speech detected (confidence: {confidence:.2f})")
                is_speaking = True
                audio_buffer = []

            audio_buffer.append(chunk)
            silence_samples = 0

        else:
            if is_speaking:
                # Count silence
                silence_samples += len(chunk)
                audio_buffer.append(chunk)

                if silence_samples >= silence_threshold:
                    # Speech ended
                    is_speaking = False

                    if audio_buffer:
                        audio = np.concatenate(audio_buffer)

                        if len(audio) >= min_samples:
                            duration = len(audio) / iris.config.sample_rate_in
                            logger.info(f"[VAD] Speech ended ({duration:.1f}s)")

                            # Process in separate thread to not block audio
                            threading.Thread(
                                target=iris.process_voice,
                                args=(audio,)
                            ).start()
                        else:
                            logger.debug("[VAD] Too short, ignoring")

                    audio_buffer = []
                    silence_samples = 0

    try:
        with sd.InputStream(
            samplerate=iris.config.sample_rate_in,
            channels=iris.config.channels_in,
            dtype='float32',
            callback=audio_callback,
            blocksize=chunk_size,
        ):
            print("[Listening] Say something...")
            while True:
                sd.sleep(100)

    except KeyboardInterrupt:
        print("\n\nExiting...")


# ==============================================================================
# Main Entry Point
# ==============================================================================

def run_gui_mode(iris: IrisLocal):
    """
    Run with DearPyGui graphical interface.

    Provides visual waveform, PTT button, transcript display, and config panel.
    """
    try:
        from iris_gui import IrisGUI
    except ImportError:
        logger.error("DearPyGui not installed. Install with: uv pip install dearpygui")
        return

    gui = IrisGUI(iris)

    # Wire up callbacks
    audio_buffer = []
    recording_active = False

    def on_ptt_start():
        nonlocal audio_buffer, recording_active
        audio_buffer = []
        recording_active = True

        # Start recording in background
        def record():
            def on_chunk(chunk):
                if recording_active:
                    audio_buffer.append(chunk)
                    gui._audio_queue.put(chunk)  # Update waveform

            iris.audio.record_until_release(on_chunk)

        threading.Thread(target=record, daemon=True).start()

    def on_ptt_stop():
        nonlocal recording_active
        recording_active = False
        iris.audio.stop_recording()

        # Process audio
        if audio_buffer:
            audio = np.concatenate(audio_buffer)
            duration = len(audio) / iris.config.sample_rate_in

            if duration > 0.3:  # Minimum 300ms
                gui.add_message("user", "[recording...]")
                gui._update_status("Processing...", gui.COLOR_ACCENT)
                gui._set_pipeline_status("stt", "active")

                # Process in background
                def process():
                    try:
                        # STT
                        text = iris.transcribe(audio)
                        if text.strip():
                            gui.state.messages[-1]["content"] = text  # Update placeholder
                            gui._update_transcript()

                            # LLM + TTS
                            gui._set_pipeline_status("stt", "done")
                            gui._set_pipeline_status("llm", "active")

                            response = iris._call_llm(text)

                            gui._set_pipeline_status("llm", "done")
                            gui._set_pipeline_status("tts", "active")

                            gui.add_message("assistant", response)

                            # TTS playback
                            iris.speak(response)

                            gui._set_pipeline_status("tts", "done")
                        else:
                            gui._update_status("No speech detected", gui.COLOR_ERROR)

                    except Exception as e:
                        logger.exception("Processing error")
                        gui._update_status(f"Error: {e}", gui.COLOR_ERROR)
                    finally:
                        gui._update_status("Ready", gui.COLOR_SUCCESS)
                        gui._set_pipeline_status("stt", "idle")
                        gui._set_pipeline_status("llm", "idle")
                        gui._set_pipeline_status("tts", "idle")

                threading.Thread(target=process, daemon=True).start()

    gui.on_ptt_start = on_ptt_start
    gui.on_ptt_stop = on_ptt_stop

    gui.setup()
    gui.run()


def main():
    parser = argparse.ArgumentParser(
        description="IRIS Local - Native Python voice client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python iris_local.py                     # PTT mode (default)
    python iris_local.py --vad               # Always-listening mode
    python iris_local.py --gui               # Graphical interface
    python iris_local.py --model mistral:7b  # Use different LLM
    python iris_local.py --list-devices      # List audio devices
        """
    )

    parser.add_argument("--vad", action="store_true",
                       help="Enable VAD (always-listening) mode")
    parser.add_argument("--gui", action="store_true",
                       help="Launch graphical interface (DearPyGui)")
    parser.add_argument("--model", default=None,
                       help="Ollama model to use (default: from OLLAMA_MODEL env)")
    parser.add_argument("--cpu", action="store_true",
                       help="Use CPU instead of GPU")
    parser.add_argument("--max-tokens", type=int, default=150,
                       help="Maximum tokens in LLM response")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices and exit")
    parser.add_argument("--input-device", type=int, default=None,
                       help="Input device index (see --list-devices)")
    parser.add_argument("--output-device", type=int, default=None,
                       help="Output device index (see --list-devices)")
    parser.add_argument("--ffmpeg", action="store_true",
                       help="Force ffmpeg for audio capture (PipeWire fallback)")
    parser.add_argument("--no-warmup", action="store_true",
                       help="Skip component warmup")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create config
    config = IrisConfig()

    if args.model:
        config.ollama_model = args.model
    if args.cpu:
        config.stt_device = "cpu"
        config.tts_device = "cpu"
    if args.max_tokens:
        config.max_tokens = args.max_tokens
    if args.input_device is not None:
        config.input_device = args.input_device
    if args.output_device is not None:
        config.output_device = args.output_device

    # Create IRIS instance
    iris = IrisLocal(config)

    # Force ffmpeg mode if requested
    if args.ffmpeg:
        iris.audio._use_ffmpeg = True
        logger.info("[Audio] Forced ffmpeg mode enabled")

    if args.list_devices:
        iris.audio.list_devices()
        return

    # Warmup
    if not args.no_warmup:
        iris.warmup()

    # Run appropriate mode
    if args.gui:
        run_gui_mode(iris)
    elif args.vad:
        run_vad_mode(iris)
    else:
        run_ptt_mode(iris)


if __name__ == "__main__":
    main()
