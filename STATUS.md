# IRIS - Project Status

> **Purpose**: Current work, active bugs, and recent changes (2-week rolling window)
> **Lifecycle**: Living (update daily/weekly during active development)

**Last Updated**: 2025-12-03 (Kokoro TTS integration: 500ms → 42ms synthesis)
**Current Phase**: Implementation (Voice Latency Optimization)
**Version**: 0.1.0 (Pre-MVP)

---

## Quick Overview

| Aspect | Status | Notes |
|--------|--------|-------|
| Planning | Done | Vision alignment complete, architecture refreshed |
| Architecture Docs | Done | CLAUDE.md, README.md, ARCHITECTURE.md updated for VPS |
| Infrastructure | Done | Using existing DO VPS (640MB+ RAM available) |
| Monorepo Setup | Done | pnpm workspaces, 6 packages (voice-backend added) |
| MCP Server Foundation | Done | Feature 1.1 complete (lifecycle, tools, errors) |
| **Memory Service** | **Done** | Epic 2 complete (knowledge graph, MCP tools, tests) |
| **Agent Core** | **Done** | Epic 3 complete (Claude Agent SDK, IrisAgent class) |
| **Voice Service** | **Done** | Epic 4 complete (faster-whisper STT, Kokoro TTS) |
| **Web App** | **Done** | Epic 5 complete (React + Vite, chat UI, voice PTT) |
| CI/CD Pipeline | N/A | Main-only workflow; deploy via docker-compose |
| Test Coverage | Partial | 12 tests for memory service |
| Known Bugs | None | Early implementation |
| **MVP Scope** | **Reduced** | 3 tasks + 1 epic deferred (see below) |

---

## Current Focus

**Completed (2025-12-02):**
- **Web App (Epic 5) complete**:
  - React + Vite frontend with space-themed dark UI
  - Chat interface with streaming SSE responses
  - Voice interface (push-to-talk) with WebSocket
  - Agent HTTP API server (Hono + SSE streaming)
  - Environment-based configuration (VITE_AGENT_API_URL, VITE_VOICE_WS_URL)
- **Voice Service (Epic 4) complete**:
  - Python voice-backend (FastAPI + faster-whisper + Kokoro)
  - Node.js WebSocket bridge for browser audio streaming
  - STT: faster-whisper with int8 quantization (~200MB for base model)
  - TTS: Kokoro-82M (~42ms synthesis, 11 curated voices)
  - Docker Compose orchestration for voice services
  - Modular architecture: browser → WebSocket → Python backend
- **Agent Core (Epic 3) complete**:
  - Claude Agent SDK integration (`@anthropic-ai/claude-agent-sdk`)
  - In-process MCP server via `createSdkMcpServer()` (zero subprocess overhead)
  - `IrisAgent` class with streaming `chat()` and `chatComplete()` methods
  - IRIS system prompt with voice-optimized personality
  - Dynamic user context injection from memory
  - Session management via Agent SDK `resume` option
  - Key decision: Agent-first architecture (not just chat API wrapper)
- **Memory Service (Epic 2) complete**:
  - SQLite knowledge graph (entities, observations, relations)
  - MCP tools: 11 tools aligned with Anthropic memory server
  - Conversation TTL (48h default, cleanup job)
  - User edit tracking ("remember that..." requests)
  - Prose summaries with staleness detection
  - 12 unit tests passing
  - Pattern extracted to agentic-framework: `patterns/sqlite-knowledge-graph.md`
- Monorepo initialized with pnpm workspaces (5 packages)
- MCP Server Foundation (Feature 1.1) complete:
  - TypeScript + MCP SDK setup
  - Server lifecycle handlers (connect, shutdown)
  - Tool registration framework with error handling
  - First tool: `getWalletBalance` (Solana)
- Solana Blockchain Tools (Feature 1.2) complete:
  - `getTransactionHistory` tool with pagination support
  - Transaction type inference (SOL/token transfers, program interactions)
  - MVP scope refined (prepareTransaction deferred)
- Star Atlas Fleet Tools (Feature 1.3) complete:
  - `getFleetStatus` MVP: player profile verification
  - `predictFuelDepletion`: fuel status and recommendations
  - SAGE SDK spike needed for auto-fetch fleet data

**Completed (2025-12-01):**
- Vision alignment session (docs/planning-session-2025-11-12.md)
- Architecture pivot: AWS -> Digital Ocean VPS
- Memory architecture simplified to SQLite (pip-by-arc-forge pattern)
- Voice service updated to use Chatterbox (self-hosted STT/TTS)

**Completed (2025-12-03):**
- **Voice Styles System** (UX Enhancement):
  - 5 voice styles: Normal, Formal, Concise, Immersive, Learning
  - Voice style selector in web-app UI (persists to localStorage)
  - Style-specific system prompt injection via `buildVoiceStylePrompt()`
  - TTS parameters: `speechRate`, `exaggeration` per style
  - Thinking feedback control: "none", "minimal", "verbose"
- **Fast Layer (Haiku 4.5)** - Quick acknowledgments:
  - **OPTIMIZED**: Direct Anthropic SDK (not Agent SDK) for minimal latency
  - Model: `claude-haiku-4-5-20251001` for <200ms acknowledgments
  - **Expanded pattern-based fallbacks**: Now covers ~90% of voice queries
    - Domain patterns: fleet, wallet, market, mission, account
    - Question patterns: what/where/when/why/who/how/can you/etc.
    - Request patterns: tell me/show me/find/search/explain/etc.
    - Action patterns: do/make/create/start/stop/enable/etc.
    - Fallback: Any message >10 chars gets generic acknowledgment
  - **Results**: Pattern fallbacks = 3-12ms, Haiku dynamic = 1.7-2.7s
  - Acknowledgment streaming via SSE `acknowledgment` chunk type
  - Respects voice style `thinkingFeedback` setting
- **Fast Layer Testing** (End-to-end verified):
  - Fixed `needsAcknowledgment()` threshold: 20 chars → 5 chars
  - Acknowledgments now trigger for typical voice input
  - Voice-only feedback (no text shown) - intentional for speed
  - Measured warm TTS: 2-3s for acknowledgment synthesis
  - Known issue: TTS cold start ~2s (Kokoro model load)
  - ✅ Fixed: Audio overlap (ack + response now play sequentially)

**In Progress:**
- ✅ **Voice Latency Architecture Overhaul** (2025-12-03 - ARCH-003) **COMPLETE**:
  - ✅ Phase 1.1: WebSocket endpoint added to Python FastAPI (`/ws/voice`)
  - ✅ Phase 1.3: Browser VoiceClient updated for direct Python connection
  - ✅ Phase 1.4: Node.js voice-service marked as DEPRECATED
  - ✅ Phase 2: Binary WebSocket protocol (eliminates base64 overhead)
    - Binary protocol: 2-byte header + raw PCM payload
    - Browser sends raw PCM audio (no base64 encode)
    - Server sends raw PCM TTS (no base64 encode)
    - ~33% less data transfer, eliminates btoa/atob overhead
  - ✅ Phase 3.1: Streaming audio capture (real-time PCM via ScriptProcessorNode)
  - ✅ Phase 3.3: GPU STT working (cuDNN fix: auto-load nvidia-cudnn libs at startup)
  - ✅ Phase 4: Rust gateway design document (`specs/DESIGN-rust-voice-gateway.md`)
  - **Architecture change**: 12 hops → 3 hops, ~76% encoding overhead → ~10%
  - **Full GPU config**: STT=CUDA (181ms), TTS=CUDA (520ms) - both now work together
  - **Plan**: `specs/PLAN-voice-latency-optimization.md`

- 🟢 **Voice Latency Optimization** (2025-12-03 - ARCH-002):
  - ✅ Empirical benchmark created: `test_e2e_latency.py`
  - ✅ Measured: E2E latency = 6.2s (target: <500ms)
  - ✅ GPU TTS acceleration: Kokoro on RTX 4090 (42ms, 12x faster than Chatterbox)
  - ✅ Full GPU config: STT=CUDA (181ms), TTS=CUDA (42ms)
  - ✅ Fast Layer: Haiku 4.5 for quick acknowledgments while Sonnet processes
  - ✅ Fast Layer tested: acknowledgments working via voice
  - ✅ Audio queue: Fixed overlap with producer-consumer pattern
  - ❌ Bottleneck: Claude API (Sonnet) = 5030ms (81% of total)
  - **Target**: ~225ms audio latency (STT + pattern match + TTS)

- 🟢 **Voice Integration** (Complete 2025-12-03):
  - ✅ STT (faster-whisper) - **GPU WORKING** - 181ms latency (32% faster than CPU)
  - ✅ WebSocket bridge - audio streaming from browser functional
  - ✅ Push-to-talk UI - recording and sending audio
  - ✅ TTS (Kokoro) - **WORKING** - 42ms on GPU (12x faster than Chatterbox)
  - ✅ Response conciseness - max 2 sentences for TTS
  - ✅ Duplicate response bug - fixed
  - ✅ cuDNN conflict resolved - auto-load nvidia-cudnn libs at startup
  - Note: Full GPU mode (STT_DEVICE=cuda, TTS_DEVICE=cuda)
  - Note: Kokoro-82M model cached in ~/.cache/huggingface/

- 🟡 **Integration Testing** (2025-12-02):
  - ✅ Agent API (port 3001) - working, tested chat endpoint
  - ✅ Web App (port 3002) - serving, chat interface functional
  - ✅ Voice backend (port 8001) - STT working on CPU
  - ✅ Voice WebSocket (port 8002) - audio streaming works
  - ✅ Dockerfiles fixed (UID 1000 conflict resolved)
  - Branding: "guy in the chair" personality

- 🟡 **ARCH-001**: IRIS/CITADEL separation - decision made (2025-12-02)
  - MCP tools **stay in IRIS** (wrap Citadel REST API)
  - Citadel provides REST + WebSocket only
  - BLOCKED: Waiting for Citadel REST API (Epic 2-3)

**Next Up (MVP scope):**
- [x] **Voice conciseness**: IRIS responses max 2 sentences for TTS
- [x] **TTS testing**: Chatterbox voice synthesis working
- [x] **End-to-end voice testing**: Full voice loop tested (ack + response)
- [ ] **Audio queue**: Fix playback overlap (ack plays over response)
- [ ] **TTS pre-warming**: Load model on startup to avoid cold start
- [ ] CITADEL: REST API for blockchain/game data (separate repo)

**Deferred from MVP (2025-12-02):**
- ⏸️ `prepareTransaction` tool - users execute via Star Atlas UI
- ⏸️ `subscribeToFleetUpdates` WebSocket - use polling instead
- ⏸️ Latency optimization - measure first, optimize post-MVP
- ⏸️ CITADEL Integration (Epic 8) - entire epic is post-MVP
- ⏸️ CI/CD pipelines - main-only workflow, deploy via docker-compose

---

## Deployment Status

### Production (Planned)
- **Target**: Digital Ocean VPS (production-syd1)
- **URL**: TBD (staratlas.rodda.xyz or similar)
- **Status**: Not deployed

---

## Known Issues

### Critical

**ARCH-002: Voice Latency Optimization** ✅ RESOLVED
- **Fast-Layer Benchmark** (v2): `packages/voice-backend/test_e2e_latency_v2.py`
- **Measured Fast Path** (Full GPU, warm):
  - STT: 181ms + Pattern match: 3-12ms + TTS: 42ms = **~225ms to first audio** ✅
- **Pattern-based acknowledgments**: 3-12ms (covers ~90% of voice queries)
- **Haiku dynamic acknowledgments**: 1.7-2.7s (for unmatched patterns)
- **GPU STT**: 181ms (vs 266ms on CPU - 32% faster) - cuDNN conflict RESOLVED
- **GPU TTS (Kokoro)**: 42ms (vs 500ms with Chatterbox - 12x improvement)
- **Claude main model**: Currently Haiku for testing (switch to Sonnet for production)
- **Run services**: `STT_DEVICE=cuda TTS_DEVICE=cuda` (default, both GPU)
- **Run benchmark**: `python test_e2e_latency_v2.py --compare-styles`

### High Priority
None

### Medium Priority

**Audio Playback Overlap** ✅ RESOLVED (2025-12-03)
- Fixed: Audio now queued sequentially (nextPlayTime scheduling)
- File: `packages/web-app/src/api/voice.ts`

**TTS Cold Start** ✅ RESOLVED (2025-12-03)
- Switched to Kokoro-82M: cold start ~2s, warm synthesis ~42ms
- Model pre-warmed on server startup (see warmup_tts() in main.py)
- 11 curated voices available (default: af_heart)

**Acknowledgment Timing** (Low priority)
- Acknowledgments may feel "too fast" - slightly robotic
- Future: Add small delay or use TTS prosody for natural pacing

---

## Recent Achievements (Last 2 Weeks)

**Voice Latency Optimization (2025-12-03)**
- **GPU STT**: 181ms (32% faster than CPU 266ms) - cuDNN conflict RESOLVED
- **GPU TTS (Kokoro)**: 42ms (12x faster than Chatterbox's 500ms)
- cuDNN fix: Auto-load nvidia-cudnn libs at startup via ctypes.CDLL
- Full GPU pipeline: STT=CUDA + TTS=CUDA both working together
- Streaming audio capture: Real-time PCM via ScriptProcessorNode (~93ms chunks)
- Binary WebSocket protocol: 2-byte header + raw PCM (~33% less overhead)

**Fast Layer Optimization (2025-12-03)**
- **BLAZING FAST**: Pattern-based acknowledgments now 3-12ms (was 5+ seconds)
- Root cause: Agent SDK `query()` had ~5s overhead for Haiku calls
- Fix 1: Replaced Agent SDK with direct `@anthropic-ai/sdk` for fast-layer
- Fix 2: Expanded pattern matching to cover ~90% of voice queries
- Fix 3: VoiceClient race condition fixed (connect() promise resolution)
- Fix 4: Acknowledgment yielded BEFORE prompt building (parallel execution)
- **Results**: User gets audio feedback in <500ms after speaking

**Voice UX Enhancement (2025-12-03)**
- Voice Styles: 5 distinct conversation modes (Normal, Formal, Concise, Immersive, Learning)
- GPU TTS: 42ms synthesis with Kokoro (12x faster than Chatterbox's 500ms)
- **Time to first audio: ~225ms** (STT ~180ms + pattern match 3ms + TTS ~42ms)
- UI: Voice style selector with persistent preferences

**Architecture Refresh (2025-12-01)**
- Migrated from AWS to Digital Ocean VPS (cost-predictable)
- Deferred personality progression (colleague -> partner -> friend)
- Adopted pip-by-arc-forge pattern (SQLite + Node.js)
- Self-hosted voice with Kokoro-82M ($0/month, Apache 2.0 license)

**Vision & Planning Session (2025-11-12)**
- Established multi-user SaaS scope with voice-first interface
- Documented strategic differentiation from EvEye (AI insights vs data viz)
- Extracted wisdom from galactic-data archives (Solana integration patterns)

---

## Next Steps (Priority Order)

1. ✅ **Simple Git Workflow** (Complete 2025-12-02)
   - `main` only, no branch protection
   - Worktrees for parallel agent work
   - See `CONTRIBUTING.md` for workflow

2. ✅ **Memory Service** (Complete 2025-12-02)
   - SQLite knowledge graph with MCP tools
   - Pattern extracted to agentic-framework

3. ✅ **Agent Core** (Complete 2025-12-02)
   - Claude Agent SDK integration
   - In-process MCP server with memory + Star Atlas tools
   - IrisAgent class with streaming support

4. ✅ **Voice Service** (Complete 2025-12-02)
   - Python voice-backend: faster-whisper (STT) + Chatterbox (TTS)
   - Node.js WebSocket bridge for browser audio streaming
   - Docker Compose orchestration

5. ✅ **Web App** (Complete 2025-12-02)
   - React + Vite frontend with dark theme
   - Chat UI with streaming responses
   - Voice interface (push-to-talk)
   - Agent HTTP API with Hono

6. **Integration & Deployment** - Next
   - Docker Compose for all services
   - End-to-end testing
   - VPS deployment

---

## Open Questions

**Resolved:**
1. ~~Architecture?~~ -> VPS + SQLite (Digital Ocean, pip-by-arc-forge pattern)
2. ~~Price monitoring?~~ -> Secondary feature (context for AI, not charting)
3. ~~Target users?~~ -> Multi-user SaaS
4. ~~Personality progression?~~ -> DEFERRED (focus on robust memory first)
5. ~~Infrastructure?~~ -> Existing DO VPS (640MB+ RAM available)
6. ~~Voice processing?~~ -> Chatterbox (self-hosted, $0/month)
7. ~~Voice UX?~~ -> Push-to-talk for MVP

**Still pending:**
1. **Authentication flow**: Magic link vs wallet-first? (Lean: email-first)
2. **Subscription tiers**: Decide after MVP validation

---

**Note**: Archive items older than 2 weeks to keep document focused.
