"""
IRIS Voice WebSocket Handler

Direct WebSocket connection from browser to Python backend.
Eliminates the Node.js voice-service relay for lower latency.

Protocol Support:
- Phase 1 (JSON + base64): Compatible with existing browser client
- Phase 2 (Binary): Raw PCM audio, ~33% less overhead

The handler auto-detects which protocol the client uses based on the
first message type (text vs binary) and responds in the same mode.

Message flow:
1. Client connects → server sends "ready"
2. Client sends audio_start → server acknowledges
3. Client streams audio_chunk messages (PCM audio)
4. Client sends audio_end → server transcribes
5. Server sends transcription
6. Client sends synthesize → server synthesizes and streams audio back
"""

import asyncio
import base64
import io
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from scipy.io import wavfile

from .stt import get_stt
from .tts_kokoro import get_kokoro_tts
from .protocol import (
    MessageType,
    MessageFlags,
    BinaryMessage,
    parse_binary_message,
    encode_ready,
    encode_pong,
    encode_transcription,
    encode_tts_audio,
    encode_audio_start,
    encode_audio_end,
    encode_error,
    encode_done,
)

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Voice session state machine."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class VoiceSession:
    """Track state for a voice WebSocket connection."""
    id: str
    user_id: str
    state: SessionState = SessionState.IDLE
    audio_buffer: list[bytes] = field(default_factory=list)
    sample_rate: int = 16000
    channels: int = 1
    binary_mode: bool = False  # True if client uses binary protocol


class VoiceWebSocketHandler:
    """
    Handle WebSocket connections for voice interaction.

    This replaces the Node.js voice-service bridge, connecting
    the browser directly to the Python STT/TTS services.
    """

    def __init__(
        self,
        agent_api_url: str = "http://localhost:3001",
        stt_model_size: str = "base",
        stt_device: str = "cpu",
        tts_device: str = "cuda",
    ):
        """
        Initialize the WebSocket handler.

        Args:
            agent_api_url: URL of the agent-core HTTP API for LLM calls.
            stt_model_size: Whisper model size (tiny, base, small, etc.)
            stt_device: Device for STT (cpu, cuda, auto).
            tts_device: Device for TTS (cpu, cuda, auto).
        """
        self.agent_api_url = agent_api_url
        self.stt_model_size = stt_model_size
        self.stt_device = stt_device
        self.tts_device = tts_device
        self.sessions: dict[str, VoiceSession] = {}

    async def handle_connection(self, websocket: WebSocket):
        """
        Handle a WebSocket connection lifecycle.

        This is the main entry point called from FastAPI.
        Auto-detects protocol (JSON vs binary) from client messages.
        """
        await websocket.accept()

        # Extract user ID and protocol preference from query params
        user_id = websocket.query_params.get("userId", "anonymous")
        # Client can request binary mode via query param: ?binary=true
        binary_requested = websocket.query_params.get("binary", "").lower() == "true"
        session_id = str(uuid4())

        logger.info(
            f"[VoiceWS] New connection: {session_id} (user: {user_id}, "
            f"binary_requested: {binary_requested})"
        )

        # Create session
        session = VoiceSession(
            id=session_id,
            user_id=user_id,
            binary_mode=binary_requested,
        )
        self.sessions[session_id] = session

        try:
            # Send ready message (in requested mode)
            await self._send_ready(websocket, session)

            # Handle messages until disconnect
            while True:
                # Receive either text or bytes
                message = await websocket.receive()

                if "text" in message:
                    # JSON mode
                    data = json.loads(message["text"])
                    await self._handle_json_message(websocket, session, data)

                elif "bytes" in message:
                    # Binary mode - switch session to binary
                    if not session.binary_mode:
                        session.binary_mode = True
                        logger.info(
                            f"[VoiceWS] Session {session_id} switched to binary mode"
                        )
                    await self._handle_binary_message(
                        websocket, session, message["bytes"]
                    )

        except WebSocketDisconnect:
            logger.info(f"[VoiceWS] Disconnected: {session_id}")
        except Exception as e:
            logger.exception(f"[VoiceWS] Error in session {session_id}: {e}")
            await self._send_error(websocket, session, str(e), "INTERNAL_ERROR")
        finally:
            # Clean up session
            self.sessions.pop(session_id, None)

    # =========================================================================
    # JSON Protocol (Phase 1 - backwards compatible)
    # =========================================================================

    async def _handle_json_message(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        message: dict[str, Any],
    ):
        """Handle an incoming JSON WebSocket message."""
        msg_type = message.get("type")

        if msg_type == "ping":
            await self._send_json(websocket, {"type": "pong"})

        elif msg_type == "audio_start":
            session.state = SessionState.LISTENING
            session.audio_buffer = []
            session.sample_rate = message.get("sampleRate", 16000)
            session.channels = message.get("channels", 1)
            logger.info(
                f"[VoiceWS] Audio start ({session.id}): "
                f"{session.sample_rate}Hz, {session.channels}ch"
            )

        elif msg_type == "audio_chunk":
            if session.state != SessionState.LISTENING:
                raise ValueError("Not in listening state")

            # Decode base64 audio data
            chunk_data = base64.b64decode(message["data"])
            session.audio_buffer.append(chunk_data)

        elif msg_type == "audio_end":
            await self._process_audio_end(websocket, session)

        elif msg_type == "synthesize":
            text = message.get("text", "")
            exaggeration = message.get("exaggeration", 0.5)
            speech_rate = message.get("speechRate", 1.0)
            await self._process_synthesize(
                websocket, session, text, exaggeration, speech_rate
            )

        else:
            raise ValueError(f"Unknown message type: {msg_type}")

    # =========================================================================
    # Binary Protocol (Phase 2 - low overhead)
    # =========================================================================

    async def _handle_binary_message(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        data: bytes,
    ):
        """Handle an incoming binary WebSocket message."""
        msg = parse_binary_message(data)

        if msg.msg_type == MessageType.PING:
            await websocket.send_bytes(encode_pong())

        elif msg.msg_type == MessageType.AUDIO_START:
            session.state = SessionState.LISTENING
            session.audio_buffer = []
            # Parse metadata from payload if present
            if msg.payload:
                meta = msg.json
                session.sample_rate = meta.get("sampleRate", 16000)
                session.channels = meta.get("channels", 1)
            else:
                session.sample_rate = 16000
                session.channels = 1
            logger.info(
                f"[VoiceWS] Audio start ({session.id}): "
                f"{session.sample_rate}Hz, {session.channels}ch [binary]"
            )

        elif msg.msg_type == MessageType.AUDIO_CHUNK:
            if session.state != SessionState.LISTENING:
                raise ValueError("Not in listening state")
            # Raw PCM bytes - no base64 decode needed!
            session.audio_buffer.append(msg.payload)

        elif msg.msg_type == MessageType.AUDIO_END:
            await self._process_audio_end(websocket, session)

        elif msg.msg_type == MessageType.SYNTHESIZE:
            # Parse synthesis request from payload
            req = msg.json
            text = req.get("text", "")
            exaggeration = req.get("exaggeration", 0.5)
            speech_rate = req.get("speechRate", 1.0)
            await self._process_synthesize(
                websocket, session, text, exaggeration, speech_rate
            )

        else:
            raise ValueError(f"Unknown binary message type: {msg.msg_type}")

    # =========================================================================
    # Shared Processing Logic
    # =========================================================================

    async def _process_audio_end(
        self,
        websocket: WebSocket,
        session: VoiceSession,
    ):
        """Process audio_end - transcribe collected audio."""
        if session.state != SessionState.LISTENING:
            raise ValueError("Not in listening state")

        session.state = SessionState.PROCESSING
        logger.info(
            f"[VoiceWS] Audio end ({session.id}): "
            f"{len(session.audio_buffer)} chunks"
        )

        # Concatenate audio chunks
        audio_data = b"".join(session.audio_buffer)
        session.audio_buffer = []

        try:
            # Transcribe audio
            text = await self._transcribe_audio(
                audio_data,
                session.sample_rate,
                session.channels,
            )
            logger.info(f"[VoiceWS] Transcription ({session.id}): \"{text}\"")

            await self._send_transcription(websocket, session, text)

        except Exception as e:
            logger.exception(f"[VoiceWS] Transcription failed ({session.id})")
            await self._send_error(
                websocket, session, "Transcription failed", "TRANSCRIPTION_ERROR"
            )

        session.state = SessionState.IDLE

    async def _process_synthesize(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        text: str,
        exaggeration: float,
        speech_rate: float,
    ):
        """Process synthesize request - generate and stream TTS audio."""
        session.state = SessionState.SPEAKING

        logger.info(
            f"[VoiceWS] Synthesize ({session.id}): "
            f"\"{text[:50]}{'...' if len(text) > 50 else ''}\""
        )

        try:
            # Synthesize speech
            wav_bytes = await self._synthesize_speech(
                text,
                exaggeration=exaggeration,
                speech_rate=speech_rate,
            )

            # Strip WAV header (44 bytes) to get raw PCM
            pcm_data = wav_bytes[44:]

            # Send audio start
            await self._send_audio_start(websocket, session, sample_rate=24000)

            # Send PCM audio in chunks
            chunk_size = 8192
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i:i + chunk_size]
                await self._send_audio_chunk(websocket, session, chunk)

            # Send audio end
            duration_seconds = len(pcm_data) / (24000 * 2)  # 16-bit samples
            await self._send_audio_end(websocket, session, duration_seconds)

            logger.info(
                f"[VoiceWS] Synthesis complete ({session.id}): "
                f"{duration_seconds:.2f}s"
            )

        except Exception as e:
            logger.exception(f"[VoiceWS] Synthesis failed ({session.id})")
            await self._send_error(
                websocket, session, "Synthesis failed", "SYNTHESIS_ERROR"
            )

        session.state = SessionState.IDLE

    # =========================================================================
    # Protocol-Aware Send Methods
    # =========================================================================

    async def _send_json(self, websocket: WebSocket, message: dict[str, Any]):
        """Send a JSON message to the client."""
        await websocket.send_text(json.dumps(message))

    async def _send_ready(self, websocket: WebSocket, session: VoiceSession):
        """Send ready message in the appropriate protocol."""
        if session.binary_mode:
            await websocket.send_bytes(encode_ready())
        else:
            await self._send_json(websocket, {"type": "ready"})

    async def _send_transcription(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        text: str,
    ):
        """Send transcription in the appropriate protocol."""
        if session.binary_mode:
            await websocket.send_bytes(encode_transcription(text, is_final=True))
        else:
            await self._send_json(websocket, {
                "type": "transcription",
                "text": text,
                "language": "en",
                "isFinal": True,
            })

    async def _send_audio_start(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        sample_rate: int = 24000,
    ):
        """Send audio_start in the appropriate protocol."""
        if session.binary_mode:
            await websocket.send_bytes(encode_audio_start(sample_rate))
        else:
            await self._send_json(websocket, {
                "type": "audio_start",
                "sampleRate": sample_rate,
            })

    async def _send_audio_chunk(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        pcm_data: bytes,
    ):
        """Send audio chunk in the appropriate protocol."""
        if session.binary_mode:
            # Binary: send raw PCM directly
            await websocket.send_bytes(encode_tts_audio(pcm_data))
        else:
            # JSON: base64 encode
            await self._send_json(websocket, {
                "type": "audio_chunk",
                "data": base64.b64encode(pcm_data).decode("ascii"),
            })

    async def _send_audio_end(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        duration_seconds: float,
    ):
        """Send audio_end in the appropriate protocol."""
        if session.binary_mode:
            await websocket.send_bytes(encode_audio_end(duration_seconds))
        else:
            await self._send_json(websocket, {
                "type": "audio_end",
                "durationSeconds": duration_seconds,
            })

    async def _send_error(
        self,
        websocket: WebSocket,
        session: VoiceSession,
        message: str,
        code: str,
    ):
        """Send error in the appropriate protocol."""
        if session.binary_mode:
            await websocket.send_bytes(encode_error(message, code))
        else:
            await self._send_json(websocket, {
                "type": "error",
                "message": message,
                "code": code,
            })

    async def _transcribe_audio(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int,
    ) -> str:
        """
        Transcribe audio to text using faster-whisper.

        Args:
            audio_data: Raw PCM audio bytes (int16).
            sample_rate: Audio sample rate.
            channels: Number of channels.

        Returns:
            Transcribed text.
        """
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Convert to float32 (whisper expects -1.0 to 1.0)
        audio_float = audio_array.astype(np.float32) / 32768.0

        # Convert stereo to mono if needed
        if channels > 1:
            audio_float = audio_float.reshape(-1, channels).mean(axis=1)

        # Resample to 16kHz if needed
        if sample_rate != 16000:
            from scipy import signal
            num_samples = int(len(audio_float) * 16000 / sample_rate)
            audio_float = signal.resample(audio_float, num_samples)

        # Run transcription in thread pool (faster-whisper is synchronous)
        loop = asyncio.get_event_loop()
        stt = get_stt(self.stt_model_size, self.stt_device)
        result = await loop.run_in_executor(
            None,
            lambda: stt.transcribe(audio_float),
        )

        return result.text

    async def _synthesize_speech(
        self,
        text: str,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        speech_rate: float = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text using Kokoro.

        Args:
            text: Text to synthesize.
            exaggeration: Unused (Kokoro doesn't support this).
            cfg_weight: Unused (Kokoro doesn't support this).
            speech_rate: Speech rate multiplier.

        Returns:
            WAV audio bytes.
        """
        # Run synthesis in thread pool (Kokoro uses PyTorch)
        loop = asyncio.get_event_loop()
        tts = get_kokoro_tts(self.tts_device)

        result = await loop.run_in_executor(
            None,
            lambda: tts.synthesize(
                text=text,
                speed=speech_rate,
            ),
        )

        return result.to_wav_bytes()


# Singleton handler instance
_handler: VoiceWebSocketHandler | None = None


def get_voice_handler(
    agent_api_url: str = "http://localhost:3001",
    stt_model_size: str = "base",
    stt_device: str = "cpu",
    tts_device: str = "cuda",
) -> VoiceWebSocketHandler:
    """Get or create the singleton WebSocket handler."""
    global _handler
    if _handler is None:
        _handler = VoiceWebSocketHandler(
            agent_api_url=agent_api_url,
            stt_model_size=stt_model_size,
            stt_device=stt_device,
            tts_device=tts_device,
        )
    return _handler
