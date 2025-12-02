"""
IRIS Voice Backend - FastAPI Server

Provides HTTP endpoints for speech-to-text (STT) and text-to-speech (TTS).
Designed for low-latency voice-first interaction.

Usage:
    uvicorn iris_voice_backend.main:app --host 0.0.0.0 --port 8001
"""

import io
import logging
from contextlib import asynccontextmanager
from typing import Literal

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from scipy.io import wavfile

from .stt import ModelSize, SpeechToText, get_stt
from .tts import TextToSpeech, get_tts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration from environment
import os

STT_MODEL_SIZE: ModelSize = os.getenv("STT_MODEL_SIZE", "base")  # type: ignore
# Separate devices for STT and TTS to avoid cuDNN issues with faster-whisper
# STT uses CPU (int8 is already fast, ~1-2s for short utterances)
# TTS uses CUDA (Chatterbox with PyTorch works fine with GPU)
STT_DEVICE: Literal["cpu", "cuda", "auto"] = os.getenv("STT_DEVICE", "cpu")  # type: ignore
TTS_DEVICE: Literal["cpu", "cuda", "auto"] = os.getenv("TTS_DEVICE", "cuda")  # type: ignore
PRELOAD_MODELS = os.getenv("PRELOAD_MODELS", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - preload models if configured."""
    logger.info(f"Voice backend starting: STT={STT_DEVICE}, TTS={TTS_DEVICE}")
    if PRELOAD_MODELS:
        logger.info("Preloading voice models...")
        # Access models to trigger lazy loading
        _ = get_stt(STT_MODEL_SIZE, STT_DEVICE).model
        _ = get_tts(TTS_DEVICE).model
        logger.info("Voice models preloaded successfully")
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


# ==============================================================================
# API Endpoints
# ==============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and model status."""
    stt = get_stt(STT_MODEL_SIZE, STT_DEVICE)
    tts = get_tts(TTS_DEVICE)

    return HealthResponse(
        status="ok",
        stt_loaded=stt._model is not None,
        tts_loaded=tts._model is not None,
        device=f"stt={STT_DEVICE}, tts={TTS_DEVICE}",
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
    Synthesize speech from text using Chatterbox.

    Returns WAV audio file.
    """
    try:
        tts = get_tts(TTS_DEVICE)
        result = tts.synthesize(
            text=request.text,
            exaggeration=request.exaggeration,
            cfg_weight=request.cfg_weight,
            speech_rate=request.speech_rate,
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
    Synthesize speech with streaming response.

    Returns raw PCM audio chunks for lower latency.
    Client should buffer and play as received.
    """
    try:
        tts = get_tts(TTS_DEVICE)

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
# Development entry point
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
