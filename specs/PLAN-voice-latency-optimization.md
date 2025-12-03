# Voice Latency Optimization Plan

**Created**: 2025-12-03
**Status**: Planning
**Related Issue**: ARCH-003

---

## Problem Statement

Current voice pipeline has **12 network hops**, **11 serialization boundaries**, and **~76% encoding overhead**. This adds ~130-490ms of avoidable latency on top of the inherent ~1086ms (STT + LLM + TTS inference).

**Current**: ~1.1-1.7s end-to-end
**Target**: <800ms with acknowledgments masking LLM latency

---

## Solution Overview

Consolidate the voice pipeline into a **single Python WebSocket gateway** that handles:
- Audio capture (binary WebSocket)
- STT (faster-whisper)
- LLM (Claude API direct)
- TTS (Chatterbox)
- Audio streaming (binary WebSocket)

**Architecture: Before**
```
Browser → Node.js WS → Python HTTP → Node.js → Browser → Node.js HTTP →
Claude → Node.js → Browser → Node.js WS → Python HTTP → Node.js WS → Browser
```

**Architecture: After**
```
Browser ←WebSocket(binary)→ Python Gateway ←HTTP/2→ Claude API
```

---

## Phase 1: Architecture Simplification

**Goal**: Eliminate Node.js voice-service, go direct Browser → Python WebSocket

### 1.1 Add WebSocket Endpoint to Python FastAPI

**File**: `packages/voice-backend/src/main.py`

Add WebSocket endpoint that handles the complete voice flow:
- `/ws/voice` - Main voice WebSocket endpoint
- Session management (userId, state machine)
- Audio buffering and transcription
- Claude API calls (using anthropic Python SDK)
- TTS synthesis and streaming

**New dependencies**:
```
anthropic>=0.40.0  # Claude API
websockets>=12.0   # WebSocket support (FastAPI has it built-in)
```

### 1.2 Port Agent Logic to Python

**New file**: `packages/voice-backend/src/agent.py`

Port the IrisAgent class logic:
- System prompt construction
- Memory context loading (call memory-service HTTP API or port to Python)
- Fast-layer acknowledgments
- Streaming response handling

**Decision**: Call existing agent-core HTTP API vs port to Python
- **Recommended**: Call agent-core HTTP API initially
- **Reason**: Preserves MCP server integration, less code duplication
- **Trade-off**: One extra HTTP hop, but localhost so ~5ms

### 1.3 Update Browser VoiceClient

**File**: `packages/web-app/src/api/voice.ts`

Update to connect directly to Python WebSocket:
- Change URL from `ws://localhost:8002` to `ws://localhost:8001/ws/voice`
- Keep same message protocol initially (JSON + base64)
- Phase 2 will switch to binary

### 1.4 Deprecate voice-service Package

After migration verified:
- Remove `packages/voice-service/` directory
- Update `pnpm-workspace.yaml`
- Update `docker-compose.yml`

### 1.5 Estimated Savings

- Eliminates 4 network hops (Node.js relay in/out × 2)
- Eliminates 4 serialization boundaries
- **Expected savings**: ~40-80ms

---

## Phase 2: Binary WebSocket Protocol

**Goal**: Raw PCM over WebSocket instead of base64

### 2.1 Define Binary Protocol

**Message format** (first 2 bytes = header):
```
Byte 0: Message type
  0x01 = audio_start
  0x02 = audio_chunk (followed by raw PCM)
  0x03 = audio_end
  0x04 = transcription (followed by UTF-8 text)
  0x05 = llm_chunk (followed by UTF-8 text)
  0x06 = tts_audio (followed by raw PCM)
  0x07 = error (followed by UTF-8 message)
  0x08 = ready
  0x09 = done

Byte 1: Flags
  bit 0: is_final (for partial transcripts)
  bit 1: needs_followup (for acknowledgments)
  bits 2-7: reserved

Bytes 2+: Payload (raw bytes or UTF-8)
```

### 2.2 Update Python WebSocket Handler

**File**: `packages/voice-backend/src/websocket.py` (new)

- Accept binary WebSocket frames
- Parse message type from first byte
- Handle raw PCM audio (no base64 decode)
- Send TTS audio as raw PCM (no base64 encode)

### 2.3 Update Browser VoiceClient

**File**: `packages/web-app/src/api/voice.ts`

- Use `ws.binaryType = 'arraybuffer'`
- Send audio as raw `ArrayBuffer` (not base64 string)
- Parse binary response frames
- Direct `Int16Array` handling for playback

### 2.4 Estimated Savings

- Eliminates 33% base64 overhead on audio input
- Eliminates 33% base64 overhead on audio output
- Eliminates btoa/atob CPU time
- **Expected savings**: ~30-50ms

---

## Phase 3: Streaming STT + GPU

**Goal**: Process audio during recording, move STT to GPU

### 3.1 Streaming Audio During Capture

**Browser changes** (`packages/web-app/src/api/voice.ts`):
- Send 100ms audio chunks during recording (not after)
- MediaRecorder already collects every 100ms
- Send each chunk immediately via WebSocket

**Python changes** (`packages/voice-backend/src/websocket.py`):
- Buffer incoming chunks
- Run VAD to detect speech end
- Start transcription when speech ends (or timeout)

### 3.2 Streaming Transcription

**File**: `packages/voice-backend/src/stt.py`

faster-whisper supports streaming mode:
```python
# Process audio incrementally
segments, info = model.transcribe(
    audio,
    beam_size=3,  # Lower for speed
    word_timestamps=True,
    vad_filter=True,
)

# Yield partial results with confidence
for segment in segments:
    yield {
        "text": segment.text,
        "confidence": segment.avg_logprob,
        "is_final": segment.no_speech_prob < 0.1,
    }
```

### 3.3 Move STT to GPU

**Current**: STT=CPU, TTS=CUDA (separate to avoid cuDNN conflicts)

**Test**: Run both on CUDA
- faster-whisper int8 on CUDA: ~100ms (vs 266ms on CPU)
- Chatterbox on CUDA: ~520ms (already GPU)
- Total VRAM needed: ~4GB (whisper ~1GB + Chatterbox ~3GB)

**Environment variable**:
```bash
STT_DEVICE=cuda TTS_DEVICE=cuda
```

**Risk**: cuDNN version conflicts between faster-whisper and PyTorch
**Mitigation**: Test on target GPU (RTX 4090 has plenty of VRAM)

### 3.4 Estimated Savings

- Streaming capture: ~50-100ms perceived latency
- GPU STT: ~100-200ms (266ms → ~100ms)
- **Expected savings**: ~150-300ms

---

## Phase 4: Rust Gateway (Future Planning)

**Goal**: Design document for maximum-performance voice gateway

### 4.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Rust Voice Gateway                           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   tokio     │  │ whisper.cpp │  │    Anthropic Client     │ │
│  │ tungstenite │  │   (STT)     │  │    (reqwest + SSE)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              TTS (options)                                  │ │
│  │  - Chatterbox ONNX export (if possible)                    │ │
│  │  - Coqui TTS ONNX                                          │ │
│  │  - Piper (C++ neural TTS)                                  │ │
│  │  - External Python TTS service (fallback)                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Components to Evaluate

| Component | Rust Option | Notes |
|-----------|-------------|-------|
| WebSocket | tokio-tungstenite | Battle-tested, async |
| STT | whisper-rs (whisper.cpp bindings) | 2-3x faster than Python |
| LLM | anthropic-rs (community) | Or raw reqwest |
| TTS | Unclear | Chatterbox has no ONNX, may need subprocess |
| Audio | rodio / cpal | Native audio handling |

### 4.3 Key Questions to Answer

1. Can Chatterbox export to ONNX? (Check with maintainers)
2. whisper.cpp quality vs faster-whisper?
3. Memory footprint comparison?
4. Build complexity acceptable?

### 4.4 Decision Criteria

Proceed with Rust gateway if:
- Python gateway hits latency floor (can't go lower)
- TTS has viable Rust/ONNX option
- Development time justified by gains

**Recommendation**: Complete Phases 1-3 first, measure, then decide.

---

## Implementation Order

```
Phase 1.1: Add WebSocket endpoint to FastAPI          [2-3 days]
Phase 1.2: Port/integrate agent logic                 [1-2 days]
Phase 1.3: Update browser VoiceClient                 [1 day]
Phase 1.4: Deprecate voice-service                    [0.5 days]
--- Checkpoint: Measure latency ---
Phase 2.1: Design binary protocol                     [0.5 days]
Phase 2.2: Update Python WebSocket handler            [1 day]
Phase 2.3: Update browser VoiceClient                 [1 day]
--- Checkpoint: Measure latency ---
Phase 3.1: Streaming audio capture                    [1 day]
Phase 3.2: Streaming STT                              [1-2 days]
Phase 3.3: GPU STT testing                            [0.5 days]
--- Checkpoint: Measure latency ---
Phase 4: Rust gateway design doc                      [1 day]
```

**Total estimate**: ~11-14 days

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 2 | Phase 3 | Target |
|--------|---------|---------|---------|---------|--------|
| Network hops | 12 | 8 | 8 | 8 | 3 |
| Time to first audio (ack) | ~1.1s | ~1.0s | ~0.95s | ~0.8s | <0.8s |
| Time to full response | ~1.7s | ~1.6s | ~1.5s | ~1.3s | <1.5s |
| Audio encoding overhead | 76% | 76% | ~10% | ~10% | <15% |

---

## Files to Create/Modify

### Create
- `packages/voice-backend/src/websocket.py` - WebSocket handler
- `packages/voice-backend/src/agent.py` - Agent integration
- `packages/voice-backend/src/protocol.py` - Binary protocol helpers

### Modify
- `packages/voice-backend/src/main.py` - Add WS endpoint
- `packages/voice-backend/requirements.txt` - Add anthropic, etc.
- `packages/web-app/src/api/voice.ts` - Direct WS, binary support
- `docker-compose.yml` - Remove voice-service

### Delete (after verification)
- `packages/voice-service/` - Entire directory

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Claude SDK Python vs Node.js differences | Medium | Test API parity, fallback to HTTP |
| Memory context requires memory-service | Medium | HTTP API call, or port to Python |
| GPU STT cuDNN conflicts | Medium | Test on target hardware first |
| Binary protocol browser compatibility | Low | All modern browsers support binary WS |

---

## Approval Checklist

- [ ] User approves overall approach
- [ ] User confirms GPU hardware for Phase 3 testing
- [ ] User accepts that Rust gateway is future/design-only

---

**Ready for user approval.**
