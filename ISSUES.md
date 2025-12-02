# IRIS - Issues & Flagged Items

> **Purpose**: Track items needing attention before/during IRIS implementation
> **Generated from**: specs/BLUEPRINT-project-staratlas-20251201.yaml

**Last Updated**: 2025-12-02

---

## High Complexity Items (needs_decomposition)

These tasks have complexity >3.0 and should be broken down further before implementation.

### task_1_2_3: prepareTransaction tool
**Complexity**: 3.2 | **Epic**: MCP Server

**Issue**: High technical complexity (4.0) and risk (4.0) due to transaction construction and security requirements.

**Why flagged**:
- Creating unsigned Solana transactions requires deep blockchain knowledge
- Security-critical: mistakes could cause fund loss
- Must handle various transaction types (SPL transfers, SAGE operations)

**Decomposition** (updated 2025-12-02):

| Subtask | Description | Est. | Complexity | Status |
|---------|-------------|------|------------|--------|
| subtask_1_2_3_1 | **Spike**: Research Solana transaction structure | 0.5d | 1.5 | 🔴 |
| subtask_1_2_3_2 | Implement basic SOL transfer builder | 1d | 2.0 | 🔴 |
| subtask_1_2_3_3 | Add SPL token transfer support | 1d | 2.2 | 🔴 |
| subtask_1_2_3_4 | Add SAGE operation templates | 1d | 2.5 | ⏸️ DEFERRED |
| subtask_1_2_3_5 | Transaction validation & security checks | 0.5d | 2.5 | 🔴 |

**MVP Recommendation**: ⏸️ **DEFER ENTIRE TASK** - Voice assistant MVP doesn't need transaction preparation. Users check balances/status via voice, execute transactions via Star Atlas UI. Revisit post-MVP if user demand exists.

**Status**: ⏸️ Deferred (MVP scope cut)

---

### task_1_3_3: subscribeToFleetUpdates WebSocket
**Complexity**: 3.5 | **Epic**: MCP Server

**Issue**: High technical complexity (4.0), dependencies (4.0), and uncertainty (4.0) due to WebSocket state management and Solana account subscriptions.

**Why flagged**:
- Solana account subscriptions are complex (RPC WebSocket)
- State management across reconnections
- Must handle rate limiting and backpressure

**Decomposition** (updated 2025-12-02):

| Subtask | Description | Est. | Complexity | Status |
|---------|-------------|------|------------|--------|
| subtask_1_3_3_1 | Basic Solana WebSocket connection handler | 1d | 2.0 | 🔴 |
| subtask_1_3_3_2 | Account subscription management (subscribe/unsubscribe) | 1d | 2.5 | 🔴 |
| subtask_1_3_3_3 | Reconnection and state recovery | 0.5d | 2.8 | 🔴 |
| subtask_1_3_3_4 | Rate limiting and backpressure handling | 0.5d | 2.3 | 🔴 |
| subtask_1_3_3_5 | Fleet update event transformation (Solana → IRIS format) | 0.5d | 2.0 | 🔴 |

**MVP Recommendation**: ⏸️ **DEFER - Use polling instead.** Implement `getFleetStatus` on 30-60s interval for MVP. Provides "near real-time" with far less complexity. WebSocket subscriptions are a post-MVP optimization when users demand faster updates.

**Status**: ⏸️ Deferred (MVP scope cut - use polling)

---

### task_4_3_3: Latency monitoring and optimization
**Complexity**: 3.5 | **Epic**: Voice Service

**Issue**: High technical complexity (4.0) and uncertainty (4.0) due to real-time performance requirements.

**Why flagged**:
- <500ms round-trip is aggressive target
- Multiple components in chain (WebRTC → Chatterbox → Agent → Chatterbox → WebRTC)
- Optimization requires profiling across distributed system

**Decomposition** (updated 2025-12-02):

| Subtask | Description | Est. | Complexity | Status | MVP? |
|---------|-------------|------|------------|--------|------|
| subtask_4_3_3_1 | Add timing instrumentation to voice pipeline | 0.5d | 2.0 | 🔴 | ✅ Yes |
| subtask_4_3_3_2 | Create latency logging/dashboard | 0.5d | 1.8 | 🔴 | ✅ Yes |
| subtask_4_3_3_3 | Profile and identify bottlenecks | 0.5d | 2.5 | 🔴 | Post-MVP |
| subtask_4_3_3_4 | Implement streaming optimizations (overlap STT/Agent/TTS) | 1d | 3.0 | 🔴 | Post-MVP |
| subtask_4_3_3_5 | Add latency alerts and text-only fallback trigger | 0.5d | 2.2 | 🔴 | ✅ Yes |

**MVP Recommendation**: Implement 4_3_3_1, 4_3_3_2, and 4_3_3_5 only. Get baseline measurements first, then optimize post-MVP. Text-only should be the default fallback if voice latency exceeds threshold.

**Status**: 🟡 Partially in scope (3 of 5 subtasks for MVP)

---

## Needs Spike Investigation

These items have high uncertainty (≥4) and need research before implementation.

### SPIKE: SAGE SDK Fleet Enumeration
**Feature**: task_1_3_1 enhancement (getFleetStatus full implementation)
**Uncertainty**: 4.0

**Current State**:
MVP implementation verifies player profile existence. Full fleet data (ship counts, states, resources) requires proper SAGE SDK integration with Anchor IDL parsing.

**Questions to answer**:
1. How to load and use @staratlas/sage IDL with Anchor?
2. What's the correct account structure for Fleet enumeration?
3. How to filter Fleet accounts by player profile efficiently?
4. What's the data size/RPC cost for fetching all fleet data?

**Suggested spike structure**:
```yaml
BLUEPRINT-spike-sage-sdk-integration-20251203.yaml

deliverables:
  - Research report: SAGE SDK account structures
  - POC: Fetch one fleet's full state
  - Decision: IDL loading strategy
  - Documentation: Fleet data parsing guide

duration: 2-3 days
```

**Status**: 🔍 Needs spike before full implementation

---

### SPIKE: Chatterbox Integration
**Feature**: feature_4_1 (Chatterbox Installation & Configuration)
**Uncertainty**: 4.0

**Questions to answer**:
1. What Docker image/setup works best on DO VPS?
2. What are the RAM/CPU requirements?
3. How to configure STT/TTS endpoints?
4. What models are available and their latency characteristics?
5. How to handle concurrent audio streams?

**Suggested spike structure**:
```yaml
BLUEPRINT-spike-chatterbox-integration-20251202.yaml

deliverables:
  - Research report: Chatterbox deployment options
  - POC: Basic STT/TTS working on VPS
  - Decision: Model selection for latency vs quality
  - Documentation: Setup steps for team

duration: 3-5 days
```

**Status**: 🔍 Needs spike before implementation

---

## Risk Register

### High Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Voice latency >500ms | High | Medium | Early Chatterbox spike + fallback to text-only |
| VPS RAM insufficient | High | Low | Load test early, upgrade path ($24/month for 8GB) |
| Solana RPC rate limiting | High | Medium | Aggressive caching (5-min TTL), paid RPC fallback |

### Medium Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| WebSocket stability on mobile | Medium | Medium | Auto-reconnect, polling fallback |
| SQLite concurrent writes | Medium | Low | WAL mode, connection pool, PostgreSQL migration path |
| Star Atlas API changes | Medium | Low | Version lock SAGE SDK, monitor changelog |

---

## Dependencies

### Blocking Dependencies

| Dependency | Blocks | Notes |
|------------|--------|-------|
| Epic 1 (MCP Server) | Epic 3 (Agent Core) | Agent needs MCP tools |
| Epic 2 (Memory Service) | Epic 3 (Agent Core) | Agent needs conversation context |
| Feature 3.4 (Agent API) | Feature 4.4 (Voice API) | Voice needs agent endpoints |

### External Dependencies

| Service | Criticality | Fallback |
|---------|-------------|----------|
| Solana blockchain | High | Cached data, offline mode |
| Star Atlas SAGE API | High | Cached fleet state |
| CoinGecko API | Medium | Stale prices acceptable |
| Chatterbox | High | Text-only fallback |

---

## Assumptions

1. ✅ Digital Ocean VPS has 640MB+ RAM available (verified 2025-12-01)
2. ⚠️ Chatterbox can run alongside other services (needs spike)
3. ⚠️ Star Atlas SAGE API will remain stable (monitor)
4. ✅ SQLite performance adequate for <500 users
5. ✅ WebRTC supported in target browsers

---

## CITADEL Integration (Epic 8)

### task_8_10_2: E2E tests for voice queries
**Complexity**: 3.0 | **Epic**: CITADEL Integration

**Issue**: High technical complexity (4.0) and dependencies (4.0) - requires both IRIS and CITADEL running.

**Why flagged**:
- Playwright tests need to simulate voice input
- Requires CITADEL API running or mocked
- Complex assertion chain: voice → agent → CITADEL API → response

**Suggested breakdown**:
1. Mock CITADEL API responses
2. Test voice input simulation separately
3. Integration test voice → agent flow
4. Full E2E with mock CITADEL

**Status**: 🔴 Not started

---

### CITADEL ↔ IRIS Coordination Notes

**Integration Contract** (defined in blueprint):
```
CITADEL Provides:
├── GET /api/dashboard/prices (30s cache)
├── GET /api/dashboard/fleets/:fleetId (60s cache)
├── GET /api/recommendations/mining (5min cache)
├── GET /api/recommendations/transport/:from/:to (5min cache)
├── WebSocket ws://citadel/ws/prices
└── MCP Tools: citadel_calculate_*, citadel_get_*

IRIS Provides:
├── Voice interface
├── User preferences from knowledge graph
└── Session context
```

**Parallel Development Strategy**:
- IRIS can start immediately with mock APIs (task_8_1_3)
- CITADEL Decision API priority: /api/dashboard/prices first
- Integration testing blocked until both systems have staging

**Risks**:
1. **CITADEL APIs not ready** → Mitigation: Mock responses unblock IRIS
2. **MCP incompatibility** → Mitigation: HTTP API fallback
3. **Voice latency budget** → Mitigation: Aggressive caching (30s-5min TTLs)

---

## Aspirational Features (from CITADEL)

> **Note**: These ML/RL features were originally scoped for CITADEL but moved to IRIS since IRIS is the "intelligent assistant" layer. CITADEL provides reliable data; IRIS provides intelligence.

### ASP-001: Price Prediction Model
**Type**: Machine Learning | **Priority**: Future
**Origin**: CITADEL Epic 6 (removed from scope)

**Concept**: Time-series forecasting (ARIMA, LSTM, Prophet) for Star Atlas resource prices.

**Why IRIS (not CITADEL)**:
- Predictions are recommendations, not raw data
- IRIS provides intelligent insights; CITADEL provides facts
- Can leverage CITADEL's historical data API

**Prerequisites**:
- CITADEL Milestone 2 (TimescaleDB historical data)
- Sufficient price history (~90 days minimum)
- Spike to assess if market has predictable patterns

**Rough scope**:
1. Feature engineering from CITADEL historical API
2. Model training pipeline (Python/scikit-learn)
3. Prediction endpoint for IRIS agent to consume
4. Confidence scoring and fallback to heuristics

**Status**: 🔮 Aspirational (post-MVP)

---

### ASP-002: Automated Strategy Optimizer (RL Agent)
**Type**: Reinforcement Learning | **Priority**: Future
**Origin**: CITADEL Epic 6 (removed from scope)

**Concept**: RL agent that learns optimal fleet allocation and operation strategies.

**Why IRIS (not CITADEL)**:
- Strategy is intelligence, not automation
- IRIS is the "brain"; CITADEL is the "hands"
- Agent can suggest to user; user decides to execute

**Prerequisites**:
- ASP-001 working (price predictions inform rewards)
- CITADEL profitability calculators stable
- Environment simulator for safe training (no real fleets)

**Rough scope**:
1. Design state/action/reward spaces
2. Build simulator using CITADEL APIs
3. Train with Stable-Baselines3 (DQN or PPO)
4. Shadow mode: suggest but don't execute
5. User approval gate before any real actions

**Status**: 🔮 Aspirational (post-MVP, post ASP-001)

---

## Architectural Issues

### ARCH-002: Voice Latency Exceeds Natural Conversation Threshold
**Severity**: 🔴 Critical | **Created**: 2025-12-02 | **Updated**: 2025-12-02

**Issue**: End-to-end voice latency is ~6.2 seconds, far exceeding the <500ms target for natural conversation.

**Empirical Measurements** (2025-12-02, hybrid STT=CPU/TTS=CUDA):
```
Stage                           Mean        Min        Max        Std
-----------------------------------------------------------------
STT (faster-whisper CPU)      266.4ms     258.1ms     270.6ms       5.9ms
Claude API (first token)     1975.2ms    1697.1ms    2450.1ms     337.4ms
Claude API (total)           5030.5ms    4163.6ms    6589.4ms    1104.6ms
TTS (Chatterbox GPU)          896.3ms     888.3ms     905.2ms       6.9ms
-----------------------------------------------------------------
TOTAL E2E                    6193.2ms    5329.3ms    7748.4ms    1101.9ms
```

**Latency Breakdown**:
```
  User stops speaking
       ↓
  STT Processing:      266.4ms (  4.3%)
       ↓
  Claude API:         5030.5ms ( 81.2%)  ← BOTTLENECK
       ↓
  TTS Synthesis:       896.3ms ( 14.5%)
       ↓
  First audio plays

  TOTAL:              6193.2ms
```

**Root Cause Analysis**:
1. **Claude API is the bottleneck** (81.2% of total latency)
2. **Current architecture waits for full response** before starting TTS
   - Location: `packages/web-app/src/components/Chat.tsx:118-125`
   - TTS triggers on `type: "done"` event (full completion)
   - Streaming tokens arrive but aren't used until stream ends

**Optimization Options** (prioritized by impact):

| Option | Effort | Impact | Description |
|--------|--------|--------|-------------|
| **1. Sentence-level TTS streaming** | High | ~50% reduction | Start TTS on first sentence, don't wait for full response |
| **2. Use Claude Haiku for voice** | Low | ~40% reduction | Faster model for voice queries (Sonnet for complex tasks) |
| **3. Speculative first response** | Medium | ~30% reduction | Pre-generate greeting while processing |
| **4. Parallel STT during recording** | Low | ~5% reduction | Start transcription during silence gaps |

**Implementation Plan**:
```
Phase 1 (Quick wins):
- [ ] Switch to Claude Haiku for voice interactions
- [ ] Measure new latency with benchmark

Phase 2 (Streaming optimization):
- [ ] Implement sentence boundary detection in Claude response stream
- [ ] Start TTS on first sentence while Claude continues generating
- [ ] Update WebSocket bridge to support interleaved text/audio
```

**Benchmark Script**: `packages/voice-backend/test_e2e_latency.py`

**Status**: 🔴 Active issue - affects user experience

---

### ARCH-001: IRIS/CITADEL Separation of Concerns
**Severity**: 🔴 Critical | **Created**: 2025-12-02 | **Updated**: 2025-12-02

**Issue**: IRIS MCP server currently contains blockchain/game data tools that belong in CITADEL.

**Current State**:
The `mcp-staratlas-server` package contains tools that should be CITADEL's responsibility:
- `getWalletBalance` - Solana RPC query
- `getTransactionHistory` - Solana RPC query
- `getFleetStatus` - SAGE SDK integration
- `predictFuelDepletion` - Game calculation with on-chain formulas

**Architecture Decision (2025-12-02)**:

| Layer | CITADEL | IRIS |
|-------|---------|------|
| **REST API** | ✅ Provides | Consumes |
| **WebSocket** | ✅ Provides | Consumes |
| **MCP Tools** | ❌ None | ✅ Wraps REST |
| **Blockchain data** | ✅ | ❌ |
| **Game calculations** | ✅ | ❌ |
| **Voice interface** | ❌ | ✅ |
| **User memory** | ❌ | ✅ |

**Key Decision: MCP tools live in IRIS, not CITADEL**

Rationale:
- Separation of concerns: Citadel = data/execution, IRIS = intelligence
- Tool descriptions should be tailored to IRIS's persona
- IRIS can compose Citadel data with other sources (user memory, etc.)
- REST is the universal contract; MCP is Claude-specific
- Keeps Citadel simpler

**Implementation Pattern**:
```
IRIS MCP Tool → wraps → CITADEL REST API → queries → Solana/SAGE
```

**Example**:
```typescript
// IRIS MCP tool (in iris/packages/mcp-staratlas-server)
const iris_get_fleet_status = async (fleetId: string) => {
  const response = await fetch(`${CITADEL_API}/api/dashboard/fleets/${fleetId}`);
  return response.json();
};
```

**Detailed Design**: See `citadel/docs/IRIS-INTEGRATION.md`

**Action Items**:
1. [x] ~~Create CITADEL repository with MCP server~~ → MCP stays in IRIS
2. [ ] CITADEL: Implement REST API endpoints for blockchain/game data (Epic 2-3)
3. [ ] CITADEL: Implement "Galactic Data Service" pattern for cached game data
4. [ ] IRIS: Update MCP tools to wrap CITADEL REST API (Epic 8) - **BLOCKED on Citadel API**
5. [ ] IRIS: Remove direct Solana RPC calls from MCP tools

**Dependency Chain**:
```
Citadel REST API (Epic 2-3) → IRIS MCP wrappers (Epic 8) → Voice agent queries
```

**Why This Matters**:
- Game formulas are on-chain (SAGE program) - hardcoding them in IRIS will break when Star Atlas updates
- CITADEL should own the "source of truth" for all blockchain/game data
- IRIS should be a thin voice layer + user context, not a data service
- Prevents duplicate RPC costs and inconsistent caching strategies

**Status**: 🟡 In Progress - Citadel REST API under development, IRIS MCP blocked until complete

---

## Action Items

1. [x] **ARCH-001**: Architecture decision made - MCP tools stay in IRIS, wrap Citadel REST (2025-12-02)
2. [ ] **ARCH-001**: Wait for Citadel REST API (Epic 2-3) before updating IRIS MCP tools (BLOCKED)
3. [ ] **Create spike blueprint** for Chatterbox integration
4. [x] **Decompose task_1_2_3** (prepareTransaction) - DONE, DEFERRED from MVP (2025-12-02)
5. [x] **Decompose task_1_3_3** (subscribeToFleetUpdates) - DONE, DEFERRED from MVP (2025-12-02)
6. [x] **Decompose task_4_3_3** (latency monitoring) - DONE, partial MVP scope (2025-12-02)
7. [ ] **Set up monitoring** for external API availability
8. [ ] **Coordinate with CITADEL** on API timeline and contract validation
9. [ ] **Create mock API** responses for CITADEL endpoints (task_8_1_3)
10. [ ] **Spike ASP-001** after CITADEL historical data available (assess prediction feasibility)

## MVP Scope Decisions (2025-12-02)

| Decision | Rationale |
|----------|-----------|
| **DEFER prepareTransaction** | Voice assistant checks status; users execute via Star Atlas UI |
| **DEFER WebSocket subscriptions** | Use polling (30-60s) for MVP; near real-time is sufficient |
| **SKIP traditional CI/CD** | Main-only workflow; deploy via `docker-compose` on VPS |
| **Text-only fallback default** | Voice is aspirational for MVP; must work without it |
| **MCP tools stay in IRIS** | IRIS wraps Citadel REST API; keeps separation clean (ARCH-001) |
| **BLOCKED: MCP wrapper updates** | Wait for Citadel REST API (Epic 2-3) before refactoring MCP tools |

---

**Note**: Update this file as issues are resolved or new ones discovered.
