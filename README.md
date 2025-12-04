# IRIS

> **Voice-first agentic layer** | *by Arc Forge*

*IRIS - Intelligent Reconnaissance & Information System*

In Greek mythology, Iris was the goddess of the rainbow and messenger of the gods. IRIS is a voice-first optimized layer for agentic systems - bridging natural conversation to any domain through modular integrations.

**Current Integration**: Star Atlas (via Citadel)
**Current Work**: See [`STATUS.md`](./STATUS.md)

---

## Overview

IRIS is a **reusable voice-first layer** designed to plug into multiple agentic systems. The core provides voice processing, memory, and agent orchestration - while domain-specific integrations connect via MCP adapters.

**First implementation**: Star Atlas companion (via Citadel app) - your guy in the chair while you're out commanding fleets.

**Key Features:**
- **Voice-First Interface** - Push-to-talk with <500ms response time
- **Fleet Monitoring** - Real-time alerts for fuel, repairs, and resources
- **Economic Optimization** - Crafting ROI analysis and market insights
- **CITADEL Integration** - Fleet and market data via CITADEL REST API
- **Secure Transactions** - Explicit wallet approval required (never auto-sign)

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/IAMSamuelRodda/iris.git
cd iris
pnpm install

# Start development
pnpm dev
```

**For AI Agents:** See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for worktree workflow.

---

## Architecture

**Tech Stack:**
- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Node.js on Digital Ocean VPS
- **Database**: SQLite (pip-by-arc-forge pattern)
- **Voice**: Chatterbox (self-hosted STT/TTS)
- **Agent**: Claude Agent SDK with MCP tools
- **Cost**: $0/month incremental (existing VPS)

**Pattern**: Vertical slice architecture for AI-assisted development.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for complete details.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [`VISION.md`](./VISION.md) | Strategic vision, multi-system architecture |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | System design, database schema, ADRs |
| [`STATUS.md`](./STATUS.md) | Current work, blockers |
| [`PROGRESS.md`](./PROGRESS.md) | Task tracking (72 tasks) |
| [`ISSUES.md`](./ISSUES.md) | Flagged items, risks |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Git worktree workflow |

---

## Development

**Workflow**: Simple tier (`main` only, direct pushes)

```bash
# Create worktree for parallel work
git worktree add ../iris--work main
cd ../iris--work

# Work in isolation, push directly to main
git push origin main
```

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for workflow details.

---

## License

MIT

---

**Last Updated**: 2025-12-03
