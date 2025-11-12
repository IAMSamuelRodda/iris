# Star Atlas Agent

> **Purpose**: Project introduction and quick start guide
> **Lifecycle**: Stable (update when fundamentals change)

Voice-first AI agent for Star Atlas fleet monitoring, economic optimization, and gameplay assistance.

**Current Work**: See [`STATUS.md`](./STATUS.md)

---

## Overview

Star Atlas Agent is a multi-user SaaS platform that provides intelligent, voice-driven assistance for Star Atlas players. Monitor your fleet status, optimize crafting economics, and get AI-powered gameplay recommendations through a natural conversational interface.

**Key Features:**
- 🎙️ **Voice-First Interface** - Cortana-like experience with <500ms response time
- 🚀 **Fleet Monitoring** - Real-time alerts for fuel, repairs, and resource needs
- 💰 **Economic Optimization** - Crafting ROI analysis and resource allocation
- 🔗 **Blockchain Integration** - WebSocket subscriptions to Solana for real-time data
- 🔐 **Secure Transactions** - Explicit wallet approval required (never auto-sign)


---

## Quick Start

**For Developers:**
```bash
# Clone and setup
git clone https://github.com/IAMSamuelRodda/star-atlas-agent.git
cd star-atlas-agent
pnpm install

# Start all services
pnpm dev
```

**For AI Agents:**
See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for workflow.

---

## Architecture

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite
- Backend: AWS Lambda + API Gateway (serverless)
- Database: DynamoDB (NoSQL)
- Voice: WebRTC + OpenAI Whisper + ElevenLabs
- Infrastructure: AWS (Free Tier optimized, <$10/month)

**Pattern**: Event-driven microservices with voice service, agent core, MCP server, and web app.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for complete details.

---

## Documentation

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - System architecture, database schema, ADRs
- [`STATUS.md`](./STATUS.md) - Current work, known issues
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) - Workflow, progress tracking
- [`DEVELOPMENT.md`](./DEVELOPMENT.md) - Git workflow, CI/CD, testing
- [`CHANGELOG.md`](./CHANGELOG.md) - Release history
- [`docs/planning-session-2025-11-12.md`](./docs/planning-session-2025-11-12.md) - Vision & constraints

---

## Testing

```bash
# All tests
pnpm test

# Specific package
pnpm --filter mcp-staratlas-server test

# E2E tests (requires test wallet)
pnpm test:e2e
```

See [`DEVELOPMENT.md`](./DEVELOPMENT.md) for complete testing setup.

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for workflow guide and best practices.

**Branch strategy**: `feature/* → dev → main` (three-tier with aggressive branch protection)

---

## License

MIT

---

**Last Updated**: 2025-11-12
