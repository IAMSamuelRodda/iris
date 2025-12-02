# IRIS - Project Status

> **Purpose**: Current work, active bugs, and recent changes (2-week rolling window)
> **Lifecycle**: Living (update daily/weekly during active development)

**Last Updated**: 2025-12-03 (Voice acknowledgments tested + threshold fix)
**Current Phase**: Implementation (Voice UX improvements)
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
| **Voice Service** | **Done** | Epic 4 complete (faster-whisper STT, Chatterbox TTS) |
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
  - Python voice-backend (FastAPI + faster-whisper + Chatterbox)
  - Node.js WebSocket bridge for browser audio streaming
  - STT: faster-whisper with int8 quantization (~200MB for base model)
  - TTS: Chatterbox with emotion control and voice cloning
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
  - Uses Claude Agent SDK `query()` for consistency with main agent
  - Model: `claude-haiku-4-5-20251001` for <200ms acknowledgments
  - Pattern-based fallbacks for common requests (fleet, wallet, help)
  - Acknowledgment streaming via SSE `acknowledgment` chunk type
  - Respects voice style `thinkingFeedback` setting
- **Fast Layer Testing** (End-to-end verified):
  - Fixed `needsAcknowledgment()` threshold: 20 chars → 5 chars
  - Acknowledgments now trigger for typical voice input
  - Voice-only feedback (no text shown) - intentional for speed
  - Measured warm TTS: 2-3s for acknowledgment synthesis
  - Known issue: TTS cold start ~16s (Chatterbox model load)
  - Known issue: Audio overlap (ack + response play together)

**In Progress:**
- 🟢 **Voice Latency Optimization** (2025-12-03 - ARCH-002):
  - ✅ Empirical benchmark created: `test_e2e_latency.py`
  - ✅ Measured: E2E latency = 6.2s (target: <500ms)
  - ✅ GPU TTS acceleration: Chatterbox on RTX 4090 (896ms, down from ~60s on CPU)
  - ✅ Hybrid device config: STT=CPU (266ms), TTS=CUDA (896ms)
  - ✅ Fast Layer: Haiku 4.5 for quick acknowledgments while Sonnet processes
  - ✅ Fast Layer tested: acknowledgments working via voice (2-3s TTS)
  - ❌ Bottleneck: Claude API (Sonnet) = 5030ms (81% of total)
  - **Next**: Audio queue (prevent ack + response overlap), TTS pre-warming

- 🟢 **Voice Integration** (Complete 2025-12-02):
  - ✅ STT (faster-whisper) - **WORKING** - 266ms latency
  - ✅ WebSocket bridge - audio streaming from browser functional
  - ✅ Push-to-talk UI - recording and sending audio
  - ✅ TTS (Chatterbox) - **WORKING** - 896ms on GPU (55x faster than CPU)
  - ✅ Response conciseness - max 2 sentences for TTS
  - ✅ Duplicate response bug - fixed
  - Note: Hybrid mode (STT_DEVICE=cpu, TTS_DEVICE=cuda)
  - Note: Chatterbox model ~3GB cached in ~/.cache/huggingface/

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
- **Measured Fast Path** (GPU TTS, warm):
  - STT: 526ms + Haiku: 4ms + TTS: 520ms = **~1.05s to first audio** ✅
- **Haiku 4.5 acknowledgment**: 4ms (extremely fast!)
- **GPU TTS**: 520ms (vs 13s on CPU - 25x improvement)
- **Claude Sonnet**: 4.7s first token, 8.4s total (remaining bottleneck)
- **Run services**: `STT_DEVICE=cpu TTS_DEVICE=cuda`
- **Run benchmark**: `python test_e2e_latency_v2.py --compare-styles`

### High Priority
None

### Medium Priority

**Audio Playback Overlap** (2025-12-03)
- Acknowledgment and response TTS play simultaneously
- Frontend needs audio queue to play in sequence
- File: `packages/web-app/src/api/voice.ts`

**TTS Cold Start** (2025-12-03)
- First TTS request takes ~16s (Chatterbox model loading)
- Subsequent requests ~2-3s
- Consider pre-warming model on server startup

---

## Recent Achievements (Last 2 Weeks)

**Voice UX Enhancement (2025-12-03)**
- Voice Styles: 5 distinct conversation modes (Normal, Formal, Concise, Immersive, Learning)
- Fast Layer: Haiku 4.5 acknowledgments using Agent SDK `query()` function (4ms!)
- GPU TTS: 520ms acknowledgment synthesis (25x faster than CPU)
- **Time to first audio: ~1.05s** (with fast-layer acknowledgment)
- UI: Voice style selector with persistent preferences
- Architecture: Consistent Agent SDK usage across both layers (Haiku + Sonnet)

**Architecture Refresh (2025-12-01)**
- Migrated from AWS to Digital Ocean VPS (cost-predictable)
- Deferred personality progression (colleague -> partner -> friend)
- Adopted pip-by-arc-forge pattern (SQLite + Node.js)
- Updated to Chatterbox for self-hosted voice ($0/month)

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
