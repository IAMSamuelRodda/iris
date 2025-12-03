"""
IRIS Voice Binary WebSocket Protocol

Eliminates base64 encoding overhead (~33%) by sending raw PCM audio
directly over WebSocket binary frames.

Message Format:
- Byte 0: Message type
- Byte 1: Flags
- Bytes 2+: Payload (raw bytes or UTF-8 text)

Message Types (0x01-0x0F):
- 0x01: audio_start (+ JSON metadata in payload)
- 0x02: audio_chunk (+ raw PCM bytes)
- 0x03: audio_end (+ optional JSON metadata)
- 0x04: transcription (+ UTF-8 text)
- 0x05: llm_chunk (+ UTF-8 text, for streaming)
- 0x06: tts_audio (+ raw PCM bytes)
- 0x07: error (+ JSON error details)
- 0x08: ready (no payload)
- 0x09: done (no payload)
- 0x0A: synthesize (+ JSON request)
- 0x0B: ping (no payload)
- 0x0C: pong (no payload)

Flags (Byte 1):
- bit 0: is_final (for partial transcripts/streams)
- bit 1: needs_followup (ack before main response)
- bits 2-7: reserved (must be 0)
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import json


class MessageType(IntEnum):
    """Binary protocol message types."""
    AUDIO_START = 0x01
    AUDIO_CHUNK = 0x02
    AUDIO_END = 0x03
    TRANSCRIPTION = 0x04
    LLM_CHUNK = 0x05
    TTS_AUDIO = 0x06
    ERROR = 0x07
    READY = 0x08
    DONE = 0x09
    SYNTHESIZE = 0x0A
    PING = 0x0B
    PONG = 0x0C


class MessageFlags(IntEnum):
    """Binary protocol flags."""
    NONE = 0x00
    IS_FINAL = 0x01
    NEEDS_FOLLOWUP = 0x02


@dataclass
class BinaryMessage:
    """Parsed binary WebSocket message."""
    msg_type: MessageType
    flags: int
    payload: bytes

    @property
    def is_final(self) -> bool:
        return bool(self.flags & MessageFlags.IS_FINAL)

    @property
    def needs_followup(self) -> bool:
        return bool(self.flags & MessageFlags.NEEDS_FOLLOWUP)

    @property
    def text(self) -> str:
        """Decode payload as UTF-8 text."""
        return self.payload.decode("utf-8")

    @property
    def json(self) -> dict[str, Any]:
        """Decode payload as JSON."""
        return json.loads(self.payload.decode("utf-8"))


def parse_binary_message(data: bytes) -> BinaryMessage:
    """
    Parse a binary WebSocket message.

    Args:
        data: Raw bytes from WebSocket.

    Returns:
        Parsed BinaryMessage.

    Raises:
        ValueError: If message is too short or has invalid type.
    """
    if len(data) < 2:
        raise ValueError(f"Message too short: {len(data)} bytes (need at least 2)")

    msg_type = data[0]
    flags = data[1]
    payload = data[2:] if len(data) > 2 else b""

    try:
        msg_type_enum = MessageType(msg_type)
    except ValueError:
        raise ValueError(f"Unknown message type: 0x{msg_type:02x}")

    return BinaryMessage(
        msg_type=msg_type_enum,
        flags=flags,
        payload=payload,
    )


def encode_binary_message(
    msg_type: MessageType,
    payload: bytes = b"",
    flags: int = MessageFlags.NONE,
) -> bytes:
    """
    Encode a binary WebSocket message.

    Args:
        msg_type: Message type.
        payload: Message payload (raw bytes).
        flags: Message flags.

    Returns:
        Encoded bytes ready for WebSocket.send_bytes().
    """
    header = struct.pack("BB", msg_type, flags)
    return header + payload


# Convenience encoders for common message types

def encode_ready() -> bytes:
    """Encode a ready message."""
    return encode_binary_message(MessageType.READY)


def encode_pong() -> bytes:
    """Encode a pong message."""
    return encode_binary_message(MessageType.PONG)


def encode_transcription(text: str, is_final: bool = True) -> bytes:
    """Encode a transcription message."""
    flags = MessageFlags.IS_FINAL if is_final else MessageFlags.NONE
    return encode_binary_message(
        MessageType.TRANSCRIPTION,
        text.encode("utf-8"),
        flags,
    )


def encode_tts_audio(pcm_data: bytes, is_final: bool = False) -> bytes:
    """Encode a TTS audio chunk."""
    flags = MessageFlags.IS_FINAL if is_final else MessageFlags.NONE
    return encode_binary_message(MessageType.TTS_AUDIO, pcm_data, flags)


def encode_audio_start(sample_rate: int = 24000) -> bytes:
    """Encode an audio_start message with metadata."""
    metadata = json.dumps({"sampleRate": sample_rate}).encode("utf-8")
    return encode_binary_message(MessageType.AUDIO_START, metadata)


def encode_audio_end(duration_seconds: float = 0.0) -> bytes:
    """Encode an audio_end message with duration."""
    metadata = json.dumps({"durationSeconds": duration_seconds}).encode("utf-8")
    return encode_binary_message(MessageType.AUDIO_END, metadata, MessageFlags.IS_FINAL)


def encode_error(message: str, code: str = "ERROR") -> bytes:
    """Encode an error message."""
    error_data = json.dumps({"message": message, "code": code}).encode("utf-8")
    return encode_binary_message(MessageType.ERROR, error_data)


def encode_done() -> bytes:
    """Encode a done message."""
    return encode_binary_message(MessageType.DONE, flags=MessageFlags.IS_FINAL)
