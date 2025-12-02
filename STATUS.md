# IRIS - Project Status

> **Purpose**: Current work, active bugs, and recent changes (2-week rolling window)
> **Lifecycle**: Living (update daily/weekly during active development)

**Last Updated**: 2025-12-02 (Web App complete)
**Current Phase**: Implementation (Epic 5 complete, MVP ready for testing)
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

**In Progress:**
- 🟡 **ARCH-001**: IRIS/CITADEL separation - decision made (2025-12-02)
  - MCP tools **stay in IRIS** (wrap Citadel REST API)
  - Citadel provides REST + WebSocket only
  - BLOCKED: Waiting for Citadel REST API (Epic 2-3)

**Next Up (MVP scope):**
- [ ] **Integration Testing**: End-to-end test of all services
- [ ] **Docker Compose**: Add agent-core and web-app to docker-compose
- [ ] CITADEL: REST API for blockchain/game data (separate repo)
- [ ] IRIS: Update MCP tools to wrap Citadel REST (blocked on CITADEL)

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
None

### High Priority
None

### Medium Priority
None

---

## Recent Achievements (Last 2 Weeks)

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
