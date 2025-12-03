# IRIS - Progress Tracking

> **Purpose**: Task tracking for IRIS MVP development
> **Tracking Method**: Document-based (no GitHub Projects)
> **Generated from**: specs/BLUEPRINT-project-staratlas-20251201.yaml

**Last Updated**: 2025-12-03
**Milestone**: v0.1.0 MVP Release (8-10 weeks estimated)

---

## Status Legend

| Status | Meaning |
|--------|---------|
| 🔴 | Not Started |
| 🟡 | In Progress |
| 🟢 | Complete |
| ⚠️ | Blocked |
| 🔍 | Needs Spike |

---

## Epic 1: MCP Server - Star Atlas & Solana Integration

**Estimated**: 21 days | **Status**: 🟡

### Feature 1.1: MCP Server Foundation (4 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_1_1_1 | Initialize MCP server package with TypeScript and SDK | 1.5 | 1d | 🟢 |
| task_1_1_2 | Implement server lifecycle handlers | 1.8 | 1d | 🟢 |
| task_1_1_3 | Add tool registration and error handling framework | 2.2 | 2d | 🟢 |

### Feature 1.2: Solana Blockchain Tools (4 days MVP) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_1_2_1 | Implement getWalletBalance tool | 2.3 | 2d | 🟢 |
| task_1_2_2 | Implement getTransactionHistory tool | 2.5 | 2d | 🟢 |
| task_1_2_3 | Implement prepareTransaction tool | **3.2** ⚠️ | 2d | ⏸️ DEFERRED |

> **Note**: task_1_2_3 deferred from MVP - users check status via voice, execute via Star Atlas UI

### Feature 1.3: Star Atlas Fleet Tools (5 days MVP) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_1_3_1 | Implement getFleetStatus tool | 3.0 | 3d | 🟡 MVP |
| task_1_3_2 | Implement predictFuelDepletion tool | 2.8 | 2d | 🟢 |
| task_1_3_3 | Implement subscribeToFleetUpdates WebSocket | **3.5** ⚠️ | 2d | ⏸️ DEFERRED |

> **Note**: task_1_3_1 MVP implementation verifies player profile; full fleet enumeration needs SAGE SDK spike
> **Note**: task_1_3_2 works with user-provided data; auto-fetch after SAGE SDK integration
> **Note**: task_1_3_3 deferred from MVP - use polling (getFleetStatus on 30-60s interval) instead

### Feature 1.4: Market & Economic Tools (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_1_4_1 | Implement getTokenPrices tool | 1.8 | 1d | 🔴 |
| task_1_4_2 | Implement getMarketplaceOrders tool | 2.5 | 2d | 🔴 |
| task_1_4_3 | Add market data caching layer | 2.0 | 1d | 🔴 |

---

## Epic 2: Memory Service - User Context & Preferences

**Estimated**: 13 days | **Status**: 🟢

> **Pattern**: sqlite-knowledge-graph from agentic-framework
> **Reference**: https://github.com/IAMSamuelRodda/agentic-framework/blob/main/patterns/sqlite-knowledge-graph.md

### Feature 2.1: SQLite Database Setup (3 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_2_1_1 | Initialize better-sqlite3 with migrations | 2.2 | 2d | 🟢 |
| task_2_1_2 | Create users table | 1.5 | 0.5d | 🟢 |
| task_2_1_3 | Create conversations table with TTL | 1.8 | 0.5d | 🟢 |

### Feature 2.2: User Preference Management (3 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_2_2_1 | Implement preference CRUD operations | 1.7 | 2d | 🟢 |
| task_2_2_2 | Add preference validation | 2.0 | 1d | 🟢 |

> **Note**: Preferences stored as entities/observations in knowledge graph (e.g., "User → prefers → morning notifications")

### Feature 2.3: Conversation Context Storage (4 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_2_3_1 | Implement message append with limit | 2.0 | 2d | 🟢 |
| task_2_3_2 | Implement TTL cleanup job | 2.5 | 1d | 🟢 |
| task_2_3_3 | Add conversation retrieval | 1.8 | 1d | 🟢 |

### Feature 2.4: Memory Service API (3 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_2_4_1 | Create memory service module | 2.2 | 2d | 🟢 |
| task_2_4_2 | Expose memory methods to Agent Core | 1.8 | 1d | 🟢 |

> **Implemented**: Knowledge graph (entities/observations/relations), MCP tools (11 tools), conversation TTL, user edit tracking, prose summaries

---

## Epic 3: Agent Core - Claude Agent SDK Orchestration

**Estimated**: 15 days | **Status**: 🟢

> **Foundation**: Claude Agent SDK (`@anthropic-ai/claude-agent-sdk`)
> **Key Decision**: Agent-first architecture using battle-tested exploration/thinking patterns

### Feature 3.1: Agent SDK Integration (5 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_3_1_1 | Initialize Agent SDK | 2.0 | 1d | 🟢 |
| task_3_1_2 | Configure MCP server as tool provider | 2.8 | 2d | 🟢 |
| task_3_1_3 | Implement conversation loop | 2.7 | 2d | 🟢 |

> **Implemented**: In-process MCP server via `createSdkMcpServer()`, `query()` wrapper with streaming

### Feature 3.2: Agent Personality & System Prompt (3 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_3_2_1 | Write base system prompt | 1.5 | 1d | 🟢 |
| task_3_2_2 | Implement dynamic prompt injection | 2.0 | 2d | 🟢 |

> **Implemented**: IRIS personality, voice-optimized responses, security rules, dynamic user context injection

### Feature 3.3: Session Management (4 days) 🟢
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_3_3_1 | Implement session creation | 2.0 | 1.5d | 🟢 |
| task_3_3_2 | Add session state tracking | 2.2 | 1.5d | 🟢 |
| task_3_3_3 | Implement session cleanup | 2.5 | 1d | 🟢 |

> **Implemented**: Agent SDK session management via `resume` option, conversation history via memory-service

### Feature 3.4: Agent API Endpoints (3 days) 🟡
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_3_4_1 | Create /api/agent/message endpoint | 1.8 | 1.5d | 🔴 |
| task_3_4_2 | Add streaming response support | 2.5 | 1.5d | 🔴 |

> **Note**: API layer will be in web-app package, not agent-core. Agent-core provides `IrisAgent` class.

---

## Epic 4: Voice Service - Chatterbox STT/TTS Integration

**Estimated**: 18 days | **Status**: 🔴

### Feature 4.1: Chatterbox Installation (4 days) 🔍
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_4_1_1 | Deploy Chatterbox Docker container | 2.8 | 2d | 🔍 |
| task_4_1_2 | Configure Chatterbox models | 2.2 | 2d | 🔍 |

**⚠️ NEEDS SPIKE**: Chatterbox deployment patterns unclear - see ISSUES.md

### Feature 4.2: WebRTC Signaling Server (5 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_4_2_1 | Implement WebSocket server | 2.5 | 2d | 🔴 |
| task_4_2_2 | Add peer connection management | 3.0 | 2d | 🔴 |
| task_4_2_3 | Implement connection recovery | 2.8 | 1d | 🔴 |

### Feature 4.3: Audio Streaming Pipeline (5 days MVP)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_4_3_1 | Implement audio capture to STT | 3.0 | 2d | 🔴 |
| task_4_3_2 | Implement TTS response streaming | 3.2 | 2d | 🔴 |
| task_4_3_3 | Add latency monitoring | **3.5** ⚠️ | 1.5d | 🟡 Partial |

> **Note**: task_4_3_3 partial MVP scope - instrumentation + logging + fallback only (1.5d); optimization deferred

### Feature 4.4: Voice Service API (3 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_4_4_1 | Create voice session endpoints | 1.8 | 1.5d | 🔴 |
| task_4_4_2 | Add Agent Core integration | 2.2 | 1.5d | 🔴 |

---

## Epic 5: Web Application - React Frontend

**Estimated**: 20 days | **Status**: 🔴

### Feature 5.1: React + Vite Setup (2 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_5_1_1 | Initialize Vite project | 1.3 | 1d | 🔴 |
| task_5_1_2 | Configure routing | 1.7 | 1d | 🔴 |

### Feature 5.2: Authentication UI (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_5_2_1 | Create magic link form | 1.8 | 1.5d | 🔴 |
| task_5_2_2 | Implement JWT handling | 2.3 | 1.5d | 🔴 |
| task_5_2_3 | Add wallet connection | 2.5 | 1d | 🔴 |

### Feature 5.3: Voice Interaction UI (5 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_5_3_1 | Create push-to-talk button | 2.0 | 1.5d | 🔴 |
| task_5_3_2 | Implement useVoice hook | 2.8 | 2d | 🔴 |
| task_5_3_3 | Add audio waveform visualization | 2.7 | 1.5d | 🔴 |

### Feature 5.4: Chat Interface (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_5_4_1 | Create message list component | 1.8 | 1.5d | 🔴 |
| task_5_4_2 | Add text input fallback | 1.7 | 1.5d | 🔴 |
| task_5_4_3 | Implement streaming message display | 2.5 | 1d | 🔴 |

### Feature 5.5: Fleet Status Dashboard (5 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_5_5_1 | Create fleet card component | 2.0 | 2d | 🔴 |
| task_5_5_2 | Add real-time fleet updates | 2.7 | 2d | 🔴 |
| task_5_5_3 | Implement alert notifications | 2.2 | 1d | 🔴 |

---

## Epic 6: Deployment & Infrastructure

**Estimated**: 14 days | **Status**: 🔴

### Feature 6.1: Docker Compose Configuration (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_6_1_1 | Create Dockerfiles | 2.0 | 2d | 🔴 |
| task_6_1_2 | Write docker-compose.yml | 2.5 | 1.5d | 🔴 |
| task_6_1_3 | Add SQLite volume mounts | 2.3 | 0.5d | 🔴 |

### Feature 6.2: Caddy Reverse Proxy Integration (3 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_6_2_1 | Update Caddyfile | 1.8 | 1d | 🔴 |
| task_6_2_2 | Configure HTTPS | 2.2 | 1.5d | 🔴 |
| task_6_2_3 | Test routing | 2.0 | 0.5d | 🔴 |

### Feature 6.3: VPS Deployment (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_6_3_1 | Create deployment script | 2.3 | 2d | 🔴 |
| task_6_3_2 | Configure secrets management | 2.5 | 1.5d | 🔴 |
| task_6_3_3 | Verify VPS performance | 2.7 | 0.5d | 🔴 |

### Feature 6.4: Monitoring & Logging (3 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_6_4_1 | Configure Docker logging | 1.7 | 1.5d | 🔴 |
| task_6_4_2 | Add health check endpoints | 1.8 | 1d | 🔴 |
| task_6_4_3 | Set up Caddy access logs | 1.8 | 0.5d | 🔴 |

---

## Epic 7: Testing & Quality Assurance

**Estimated**: 15 days | **Status**: 🔴

### Feature 7.1: Unit Tests (5 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_7_1_1 | Unit tests for MCP server | 2.2 | 2d | 🔴 |
| task_7_1_2 | Unit tests for memory service | 1.8 | 1.5d | 🔴 |
| task_7_1_3 | Unit tests for agent core | 2.0 | 1.5d | 🔴 |

### Feature 7.2: E2E Tests (6 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_7_2_1 | Set up Playwright | 2.3 | 2d | 🔴 |
| task_7_2_2 | E2E tests for auth flow | 2.5 | 2d | 🔴 |
| task_7_2_3 | E2E tests for voice/chat | 2.8 | 2d | 🔴 |

### Feature 7.3: Integration Tests (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_7_3_1 | Test Agent + MCP integration | 2.5 | 2d | 🔴 |
| task_7_3_2 | Test Voice + Agent integration | 2.3 | 1.5d | 🔴 |
| task_7_3_3 | Test WebSocket subscriptions | 2.2 | 0.5d | 🔴 |

---

## Epic 8: CITADEL Integration - Voice Access to Fleet Data

**Estimated**: 37-40 days (2-3 weeks parallel) | **Status**: 🔴
**Dependency**: CITADEL MVP APIs (read-only, no automation triggers)
**Blueprint**: specs/archive/BLUEPRINT-feature-citadel-integration-20251202.yaml

### Feature 8.1: CITADEL API Client (3 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_1_1 | Define TypeScript types for CITADEL API contracts | 1.5 | 1d | 🔴 |
| task_8_1_2 | Implement CitadelClient class with retry/caching | 2.3 | 1.5d | 🔴 |
| task_8_1_3 | Add mock API responses for offline development | 1.8 | 0.5d | 🔴 |

### Feature 8.2: MCP Tool Proxy (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_2_1 | Configure IRIS to connect to CITADEL MCP server | 1.8 | 1d | 🔴 |
| task_8_2_2 | Implement MCP tool wrappers with user context | 2.7 | 2d | 🔴 |
| task_8_2_3 | Add fallback to HTTP API when MCP unavailable | 2.5 | 1d | 🔴 |

### Feature 8.3: WebSocket for Real-Time Prices (5 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_3_1 | Implement WebSocket client for price updates | 2.7 | 2d | 🔴 |
| task_8_3_2 | Integrate WebSocket updates into agent context | 2.3 | 1.5d | 🔴 |
| task_8_3_3 | Add voice notification for price changes | 2.8 | 1.5d | 🔴 |

### Feature 8.4: Price Query Voice Handlers (3 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_4_1 | "What's the price of [resource]?" handler | 1.8 | 1d | 🔴 |
| task_8_4_2 | "Show all resource prices" handler | 2.0 | 1d | 🔴 |
| task_8_4_3 | Price comparison queries | 2.2 | 1d | 🔴 |

### Feature 8.5: Fleet Recommendation Voice Handlers (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_5_1 | "What should my fleet mine?" handler | 2.5 | 1.5d | 🔴 |
| task_8_5_2 | "Best transport route from A to B" handler | 2.3 | 1.5d | 🔴 |
| task_8_5_3 | Fleet profitability comparison | 2.2 | 1d | 🔴 |

### Feature 8.6: Contextual Query Augmentation (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_6_1 | Retrieve user preferences from knowledge graph | 2.3 | 1.5d | 🔴 |
| task_8_6_2 | Augment CITADEL queries with user context | 2.7 | 1.5d | 🔴 |
| task_8_6_3 | Store CITADEL interaction outcomes | 2.5 | 1d | 🔴 |

### Feature 8.7: Dashboard Components (5 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_7_1 | ResourcePriceTable component | 2.0 | 1.5d | 🔴 |
| task_8_7_2 | RecommendationCard component | 2.3 | 2d | 🔴 |
| task_8_7_3 | FleetStatusPanel component | 2.3 | 1.5d | 🔴 |

### Feature 8.8: React Query Hooks (4 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_8_1 | useCitadelPrices hook | 2.5 | 1.5d | 🔴 |
| task_8_8_2 | useCitadelRecommendations hook | 2.3 | 1.5d | 🔴 |
| task_8_8_3 | useCitadelFleetStatus hook | 2.2 | 1d | 🔴 |

### Feature 8.9: CITADEL Dashboard Page (3 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_9_1 | Create /dashboard/citadel route | 1.8 | 1d | 🔴 |
| task_8_9_2 | Integrate all CITADEL components | 2.0 | 1d | 🔴 |
| task_8_9_3 | Add navigation and breadcrumbs | 1.5 | 1d | 🔴 |

### Feature 8.10: CITADEL Integration Tests (5 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_10_1 | Integration tests for API client | 2.5 | 2d | 🔴 |
| task_8_10_2 | E2E tests for voice queries | **3.0** ⚠️ | 2d | 🔴 |
| task_8_10_3 | Integration tests for WebSocket | 2.8 | 1d | 🔴 |

### Feature 8.11: Integration Documentation (2 days)
| ID | Task | Complexity | Est. | Status |
|----|------|------------|------|--------|
| task_8_11_1 | Document CITADEL integration architecture | 1.5 | 1d | 🔴 |
| task_8_11_2 | Create CITADEL setup guide for developers | 1.5 | 1d | 🔴 |

---

## Summary

| Epic | Features | Tasks | Est. Days | Status | MVP Scope |
|------|----------|-------|-----------|--------|-----------|
| MCP Server | 4 | 11 | 21 → **17** | 🟡 | 2 tasks deferred |
| Memory Service | 4 | 10 | 13 | 🔴 | Full |
| Agent Core | 4 | 9 | 15 | 🔴 | Full |
| Voice Service | 4 | 10 | 18 → **17.5** | 🔴 | Latency opt. deferred |
| Web Application | 5 | 13 | 20 | 🔴 | Full |
| Deployment | 4 | 10 | 14 | 🔴 | Full (no CI/CD) |
| Testing | 3 | 9 | 15 | 🔴 | Full |
| **CITADEL Integration** | **11** | **35** | **37-40** | 🔴 | Post-MVP |
| **MVP TOTAL** | **28** | **72** | **~97** | 🟡 | Reduced |

> **MVP Scope Cuts (2025-12-02)**: prepareTransaction, WebSocket subscriptions, latency optimization deferred. CITADEL is post-MVP.

---

## Deferred (Post-MVP)

**Original deferrals:**
- Personality progression (colleague → partner → friend)
- Vector embeddings for semantic memory
- Always-listening voice mode
- zProfile SSO integration

**MVP scope cuts (2025-12-02):**
- task_1_2_3: `prepareTransaction` tool (users execute via Star Atlas UI)
- task_1_3_3: `subscribeToFleetUpdates` WebSocket (use polling instead)
- task_4_3_3 partial: Latency optimization subtasks (measure first, optimize later)
- Epic 8: CITADEL Integration (entire epic is post-MVP)
- CI/CD pipelines (main-only workflow, deploy via docker-compose)

---

**Note**: Update this file as tasks complete. Use worktrees for parallel development.
