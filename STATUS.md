# IRIS - Project Status

> **Purpose**: Current work, active bugs, and recent changes (2-week rolling window)
> **Lifecycle**: Living (update daily/weekly during active development)

**Last Updated**: 2025-12-02 (MVP scope refined)
**Current Phase**: Implementation (Epic 1 - MCP Server)
**Version**: 0.1.0 (Pre-MVP)

---

## Quick Overview

| Aspect | Status | Notes |
|--------|--------|-------|
| Planning | Done | Vision alignment complete, architecture refreshed |
| Architecture Docs | Done | CLAUDE.md, README.md, ARCHITECTURE.md updated for VPS |
| Infrastructure | Done | Using existing DO VPS (640MB+ RAM available) |
| Monorepo Setup | Done | pnpm workspaces, 5 packages scaffolded |
| MCP Server Foundation | Done | Feature 1.1 complete (lifecycle, tools, errors) |
| CI/CD Pipeline | N/A | Main-only workflow; deploy via docker-compose |
| Test Coverage | Pending | No tests yet |
| Known Bugs | None | Early implementation |
| **MVP Scope** | **Reduced** | 3 tasks + 1 epic deferred (see below) |

---

## Current Focus

**Completed (2025-12-02):**
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
- 🔴 **ARCH-001**: IRIS/CITADEL separation (blocking MCP tool development)

**Next Up (MVP scope):**
- [ ] Create CITADEL repo and move blockchain/game tools
- [ ] IRIS: Focus on voice service (Chatterbox) + user memory
- [ ] CITADEL: Own all blockchain/game data tools

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

2. **Begin Implementation**
   - MCP server first (Solana + Star Atlas data access)
   - Memory service (SQLite, simple schema)
   - Agent core (Claude Agent SDK integration)
   - Voice service (Chatterbox STT/TTS)
   - Web app (React + Vite frontend)

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
