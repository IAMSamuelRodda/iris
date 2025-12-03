"""
IRIS Voice Backend - FastAPI Server

Provides HTTP endpoints for speech-to-text (STT) and text-to-speech (TTS).
Designed for low-latency voice-first interaction.

Usage:
    uvicorn iris_voice_backend.main:app --host 0.0.0.0 --port 8001
"""

import io
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Literal

# =============================================================================
# CUDA/cuDNN Library Path Fix
#
# ctranslate2 (used by faster-whisper) requires cuDNN libraries to be in
# LD_LIBRARY_PATH. PyTorch bundles cuDNN in nvidia-cudnn package but doesn't
# add it to the library path. This fix adds it automatically.
# =============================================================================
def _setup_cudnn_path():
    """Add nvidia-cudnn lib to LD_LIBRARY_PATH for ctranslate2 compatibility."""
    try:
        import nvidia.cudnn
        cudnn_lib = os.path.join(os.path.dirname(nvidia.cudnn.__file__), "lib")
        if os.path.exists(cudnn_lib):
            current_path = os.environ.get("LD_LIBRARY_PATH", "")
            if cudnn_lib not in current_path:
                os.environ["LD_LIBRARY_PATH"] = f"{cudnn_lib}:{current_path}"
                # Also need to update ctypes search path for already-loaded process
                import ctypes
                ctypes.CDLL(os.path.join(cudnn_lib, "libcudnn.so.9"), mode=ctypes.RTLD_GLOBAL)
    except ImportError:
        pass  # nvidia-cudnn not installed, skip

_setup_cudnn_path()

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from scipy.io import wavfile

from fastapi import WebSocket

from .stt import ModelSize, SpeechToText, get_stt
from .tts_kokoro import (
    KokoroTTS,
    get_kokoro_tts,
    list_kokoro_voices,
    set_kokoro_voice,
    DEFAULT_VOICE,
    AVAILABLE_VOICES,
)
from .websocket import get_voice_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration from environment
STT_MODEL_SIZE: ModelSize = os.getenv("STT_MODEL_SIZE", "base")  # type: ignore
# Both STT and TTS can now use CUDA thanks to the cuDNN path fix above
# Set STT_DEVICE=cuda for ~32% faster transcription (181ms vs 266ms)
STT_DEVICE: Literal["cpu", "cuda", "auto"] = os.getenv("STT_DEVICE", "cuda")  # type: ignore
TTS_DEVICE: Literal["cpu", "cuda", "auto"] = os.getenv("TTS_DEVICE", "cuda")  # type: ignore
PRELOAD_MODELS = os.getenv("PRELOAD_MODELS", "false").lower() == "true"


async def warmup_tts():
    """Warm up TTS by synthesizing a short phrase."""
    import asyncio
    loop = asyncio.get_event_loop()
    tts = get_kokoro_tts(TTS_DEVICE)
    # Run synthesis in thread pool to not block
    await loop.run_in_executor(
        None,
        lambda: tts.synthesize("Ready.")
    )
    logger.info("Kokoro TTS warmup complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - preload models and warmup."""
    logger.info(f"Voice backend starting: STT={STT_DEVICE}, TTS={TTS_DEVICE}")
    logger.info(f"Default voice: {DEFAULT_VOICE}")

    # Always preload STT model (it's fast)
    logger.info("Loading STT model...")
    _ = get_stt(STT_MODEL_SIZE, STT_DEVICE).model
    logger.info("STT model loaded")

    # Always preload and warmup Kokoro TTS (important for first-request latency)
    logger.info("Loading Kokoro TTS model and warming up...")
    _ = get_kokoro_tts(TTS_DEVICE).pipeline
    await warmup_tts()
    logger.info(f"Kokoro TTS ready with voice: {DEFAULT_VOICE}")

    yield
    logger.info("Shutting down voice backend")


app = FastAPI(
    title="IRIS Voice Backend",
    description="Speech-to-text and text-to-speech for IRIS AI companion",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Request/Response Models
# ==============================================================================


class TranscribeResponse(BaseModel):
    """Response from STT transcription."""

    text: str
    language: str
    language_probability: float = Field(ge=0.0, le=1.0)
    duration_seconds: float = Field(ge=0.0)


class SynthesizeRequest(BaseModel):
    """Request for TTS synthesis."""

    text: str = Field(min_length=1, max_length=5000)
    exaggeration: float = Field(default=0.5, ge=0.0, le=1.0)
    cfg_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    speech_rate: float = Field(default=1.0, ge=0.5, le=2.0)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    stt_loaded: bool
    tts_loaded: bool
    device: str


class VoicesResponse(BaseModel):
    """List of available voices."""

    voices: list[str]
    current: str


class VoiceSelectRequest(BaseModel):
    """Request to select a voice."""

    voice: str


class VoiceSelectResponse(BaseModel):
    """Response after selecting a voice."""

    success: bool
    voice: str
    message: str


class WarmupResponse(BaseModel):
    """Response from warmup endpoint."""

    ready: bool
    voice: str
    warmup_time_ms: float


# ==============================================================================
# API Endpoints
# ==============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and model status."""
    stt = get_stt(STT_MODEL_SIZE, STT_DEVICE)
    tts = get_kokoro_tts(TTS_DEVICE)

    return HealthResponse(
        status="ok",
        stt_loaded=stt._model is not None,
        tts_loaded=tts._pipeline is not None,
        device=f"stt={STT_DEVICE}, tts={TTS_DEVICE} (kokoro)",
    )


# ==============================================================================
# Voice Management Endpoints
# ==============================================================================


@app.get("/api/voices", response_model=VoicesResponse)
async def get_voices():
    """List all available Kokoro voice options."""
    tts = get_kokoro_tts(TTS_DEVICE)

    return VoicesResponse(
        voices=[v["id"] for v in list_kokoro_voices()],
        current=tts.current_voice,
    )


@app.post("/api/voice/select", response_model=VoiceSelectResponse)
async def select_voice(request: VoiceSelectRequest):
    """
    Select a Kokoro voice.

    Voice switching is instant with Kokoro - no model reload needed.
    """
    import time

    voice_id = request.voice

    # Check if voice exists in curated list
    available = [v["id"] for v in list_kokoro_voices()]
    if voice_id not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Voice '{voice_id}' not found. Available: {', '.join(available[:5])}..."
        )

    # Switch voice (instant - just changes the embedding ID)
    set_kokoro_voice(voice_id)

    # Quick warmup with new voice
    start = time.time()
    await warmup_tts()
    warmup_ms = (time.time() - start) * 1000

    return VoiceSelectResponse(
        success=True,
        voice=voice_id,
        message=f"Voice changed to {voice_id}. Warmup took {warmup_ms:.0f}ms",
    )


@app.post("/api/warmup", response_model=WarmupResponse)
async def warmup_voice():
    """
    Warm up the Kokoro TTS system with current voice.

    Call this after the voice backend starts or after changing voices
    to ensure the first synthesis request is fast.
    """
    import time

    tts = get_kokoro_tts(TTS_DEVICE)

    start = time.time()
    await warmup_tts()
    warmup_ms = (time.time() - start) * 1000

    return WarmupResponse(
        ready=True,
        voice=tts.current_voice,
        warmup_time_ms=warmup_ms,
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (WAV, 16kHz, mono)"),
    language: str | None = None,
):
    """
    Transcribe audio to text using faster-whisper.

    Accepts WAV audio files (16kHz, mono recommended).
    Returns transcribed text with language detection.
    """
    try:
        # Read audio file
        content = await audio.read()

        # Parse WAV file
        try:
            buffer = io.BytesIO(content)
            sample_rate, audio_data = wavfile.read(buffer)

            # Convert to float32
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483648.0

            # Convert stereo to mono
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            # Resample to 16kHz if needed
            if sample_rate != 16000:
                from scipy import signal

                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = signal.resample(audio_data, num_samples)

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio format: {e}. Please provide WAV audio.",
            )

        # Transcribe
        stt = get_stt(STT_MODEL_SIZE, STT_DEVICE)
        result = stt.transcribe(audio_data, language=language)

        return TranscribeResponse(
            text=result.text,
            language=result.language,
            language_probability=result.language_probability,
            duration_seconds=result.duration_seconds,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


@app.post("/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """
    Synthesize speech from text using Kokoro.

    Returns WAV audio file.
    """
    try:
        tts = get_kokoro_tts(TTS_DEVICE)
        result = tts.synthesize(
            text=request.text,
            speed=request.speech_rate,
        )

        # Return as WAV
        wav_bytes = result.to_wav_bytes()

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav",
                "X-Duration-Seconds": str(result.duration_seconds),
            },
        )

    except Exception as e:
        logger.exception("Synthesis failed")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e}")


@app.post("/synthesize/stream")
async def synthesize_speech_streaming(request: SynthesizeRequest):
    """
    Synthesize speech with streaming response using Kokoro.

    Returns raw PCM audio chunks for lower latency.
    Client should buffer and play as received.
    """
    try:
        tts = get_kokoro_tts(TTS_DEVICE)

        def generate():
            for chunk in tts.synthesize_streaming(request.text):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="audio/pcm",
            headers={
                "X-Sample-Rate": "24000",
                "X-Channels": "1",
                "X-Bit-Depth": "16",
            },
        )

    except Exception as e:
        logger.exception("Streaming synthesis failed")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e}")


# ==============================================================================
# WebSocket Endpoint (Direct browser connection - eliminates Node.js relay)
# ==============================================================================


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    Direct WebSocket connection for voice interaction.

    This endpoint eliminates the Node.js voice-service relay,
    reducing latency by ~40-80ms (4 fewer network hops).

    Protocol:
    1. Client connects with ?userId=xxx query param
    2. Server sends {"type": "ready"}
    3. Client sends audio_start/audio_chunk/audio_end for STT
    4. Server sends {"type": "transcription", "text": "..."}
    5. Client sends {"type": "synthesize", "text": "..."}
    6. Server streams audio_start/audio_chunk/audio_end for TTS
    """
    handler = get_voice_handler(
        stt_model_size=STT_MODEL_SIZE,
        stt_device=STT_DEVICE,
        tts_device=TTS_DEVICE,
    )
    await handler.handle_connection(websocket)


# ==============================================================================
# Development entry point
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
