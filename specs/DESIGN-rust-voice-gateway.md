# Rust Voice Gateway - Design Document

**Status**: Future Planning (Post-MVP)
**Created**: 2025-12-03
**Related**: ARCH-003, PLAN-voice-latency-optimization.md

---

## Overview

This document outlines the design for a high-performance Rust voice gateway to replace the Python FastAPI voice-backend. The goal is to achieve sub-200ms time-to-first-audio for voice interactions.

### Current Architecture (Python)

```
Browser ←WebSocket(binary)→ Python FastAPI ←HTTP→ Claude API
                              ↓
                        faster-whisper (STT)
                        Chatterbox (TTS)
```

**Measured latencies (hybrid mode: STT=CPU, TTS=CUDA)**:
- STT: ~266ms (faster-whisper, CPU int8)
- TTS: ~520ms (Chatterbox, GPU CUDA)
- Claude API: ~4700ms (Sonnet, varies)
- Network overhead: ~50ms

**Current bottleneck**: Claude API latency dominates (80%+ of total).

### Proposed Architecture (Rust)

```
Browser ←WebSocket(binary)→ Rust Gateway ←HTTP/2→ Claude API
                              ↓
                        whisper.cpp (STT)
                        External TTS service
```

---

## Performance Targets

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| STT latency | 266ms | <100ms | whisper.cpp on GPU |
| TTS latency | 520ms | <300ms | ONNX/Piper TTS |
| Network overhead | 50ms | <20ms | Binary protocol |
| Total (excl LLM) | ~840ms | <420ms | 50% reduction |

---

## Component Selection

### STT: whisper.cpp

**Library**: [whisper-rs](https://crates.io/crates/whisper-rs) (bindings to whisper.cpp)

**Advantages**:
- 2-3x faster than Python faster-whisper
- Native CUDA/Metal support
- Same Whisper models (compatible quality)
- No Python GIL overhead

**Configuration**:
```rust
use whisper_rs::{WhisperContext, WhisperContextParameters};

let ctx = WhisperContext::new_with_params(
    "models/ggml-base.en.bin",
    WhisperContextParameters::default()
        .use_gpu(true)
)?;
```

**Expected latency**: ~100ms for 2s audio on GPU

### TTS: Options Analysis

**Option 1: Piper TTS (Recommended)**
- Native C++ with ONNX runtime
- Very fast (~50-100ms for short text)
- Multiple voice models available
- Rust bindings: [piper-rs](https://crates.io/crates/piper-rs) (community)

**Option 2: Coqui TTS ONNX**
- Export Coqui models to ONNX
- Use ort (ONNX Runtime for Rust)
- More complex setup

**Option 3: External Python TTS Service**
- Keep Chatterbox as separate microservice
- HTTP call from Rust gateway
- Adds network hop but proven quality

**Recommendation**: Start with Option 3 (external Chatterbox), migrate to Piper later.

### WebSocket: tokio-tungstenite

**Library**: [tokio-tungstenite](https://crates.io/crates/tokio-tungstenite)

```rust
use tokio_tungstenite::accept_async;
use futures::{StreamExt, SinkExt};

async fn handle_connection(stream: TcpStream) {
    let ws_stream = accept_async(stream).await?;
    let (mut write, mut read) = ws_stream.split();

    while let Some(msg) = read.next().await {
        match msg? {
            Message::Binary(data) => {
                // Handle audio chunk
                let audio = parse_audio_chunk(&data);
                // Process...
            }
            _ => {}
        }
    }
}
```

### Claude API: reqwest + SSE

**Library**: [reqwest](https://crates.io/crates/reqwest) with async/streaming

```rust
use reqwest::Client;
use eventsource_stream::Eventsource;

async fn call_claude(messages: Vec<Message>) -> impl Stream<Item = String> {
    let response = client
        .post("https://api.anthropic.com/v1/messages")
        .header("anthropic-version", "2024-01-01")
        .json(&request)
        .send()
        .await?;

    response
        .bytes_stream()
        .eventsource()
        .filter_map(|event| async move {
            // Parse SSE events
        })
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Rust Voice Gateway                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │   tokio      │  │  whisper.cpp │  │     Claude HTTP Client     │ │
│  │ tungstenite  │  │   (STT)      │  │     (reqwest + SSE)        │ │
│  │  (WebSocket) │  └──────────────┘  └────────────────────────────┘ │
│  └──────────────┘                                                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────────┤
│  │              TTS (External Service Initially)                    │
│  │  - HTTP call to Python Chatterbox service                       │
│  │  - Future: Piper TTS native integration                         │
│  └──────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
```

### Message Flow

1. **Audio In**: Browser → Binary WS → Rust → whisper.cpp → text
2. **LLM Call**: text → Claude API → SSE stream → response chunks
3. **Audio Out**: response → TTS service → PCM → Binary WS → Browser

---

## State Machine

```rust
enum SessionState {
    Idle,
    Listening { buffer: Vec<u8>, sample_rate: u32 },
    Processing { audio_data: Vec<u8> },
    Speaking { pending_chunks: VecDeque<Vec<u8>> },
}

struct VoiceSession {
    id: Uuid,
    user_id: String,
    state: SessionState,
    whisper_ctx: Arc<WhisperContext>,
}
```

---

## Binary Protocol (Same as Python)

```
Byte 0: Message type (0x01-0x0C)
Byte 1: Flags
Bytes 2+: Payload

Types:
  0x01: audio_start
  0x02: audio_chunk (raw PCM)
  0x03: audio_end
  0x04: transcription
  0x06: tts_audio
  0x07: error
  0x08: ready
```

---

## Dependencies (Cargo.toml)

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
tokio-tungstenite = "0.21"
futures = "0.3"
reqwest = { version = "0.11", features = ["stream", "json"] }
eventsource-stream = "0.2"
whisper-rs = "0.10"
uuid = { version = "1", features = ["v4"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tracing = "0.1"
tracing-subscriber = "0.3"
```

---

## Implementation Phases

### Phase 1: WebSocket Server (1 day)
- [ ] Basic tokio-tungstenite server
- [ ] Binary protocol parsing
- [ ] Session management

### Phase 2: Claude API Integration (1 day)
- [ ] HTTP client with SSE streaming
- [ ] Message formatting
- [ ] Error handling

### Phase 3: STT Integration (2 days)
- [ ] whisper-rs setup and testing
- [ ] Audio buffer management
- [ ] GPU configuration

### Phase 4: TTS Integration (1 day)
- [ ] HTTP client to Python Chatterbox
- [ ] Audio streaming back to client

### Phase 5: Testing & Optimization (2 days)
- [ ] Latency benchmarks
- [ ] Memory profiling
- [ ] Connection pooling

---

## Decision Criteria

**Proceed with Rust gateway if**:
1. Python gateway hits latency floor and can't go lower
2. TTS has viable Rust/ONNX option (or external service is acceptable)
3. Development time is justified by gains (50%+ latency reduction)

**Stay with Python if**:
1. Latency bottleneck remains Claude API (can't fix locally)
2. Chatterbox quality is critical (no Rust equivalent)
3. Rapid iteration more important than raw performance

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| whisper-rs quality differs | Medium | Benchmark against faster-whisper |
| TTS quality loss with Piper | High | Keep Chatterbox as fallback |
| Complex async Rust | Medium | Use tokio patterns, good error handling |
| Build complexity | Low | Docker multi-stage builds |

---

## Next Steps

1. Benchmark Python gateway at current state
2. Prototype whisper-rs STT in isolation
3. Evaluate Piper TTS quality
4. Decision: proceed or defer

---

**Recommendation**: Defer until Python gateway is fully optimized and measured. Claude API latency (~5s) dominates total time, making local optimizations less impactful. Focus on fast-layer acknowledgments to mask LLM latency.
