# Star Atlas Agent - CLAUDE.md

> **Purpose**: Minimal critical directives for AI agents (pointers to detailed documentation)
> **Lifecycle**: Living (keep minimal, move verbose content to CONTRIBUTING.md or DEVELOPMENT.md)

## 📍 Critical Documents

**Before starting work:**
1. Read `STATUS.md` → Current issues, active work, what's broken
2. Read `ARCHITECTURE.md` → System architecture, database schema, tech stack
3. Read `CONTRIBUTING.md` → How to track progress with issues/PRs

**Before finishing work:**
1. Update `STATUS.md` → Add investigation notes, mark issues resolved
2. Update GitHub issues → Close completed tasks, link commits
3. Check `DEVELOPMENT.md` → Run pre-commit checklist (lint, format, tests)

**Planning artifact:** `specs/BLUEPRINT.yaml` is for generating GitHub issues when planning NEW features, NOT for reference during implementation. It becomes historical once issues are created.

---

## 🏗️ Architecture Quick Facts

### Style
- **Microservices Architecture** (Voice Service, Agent Core, MCP Server, Web App)
- **Event-Driven** (WebSocket subscriptions for real-time blockchain monitoring)
- **Voice-First** (Cortana-like experience with STT/TTS)

### Structure Pattern
```
packages/
├── mcp-staratlas-server/   # MCP tools for Star Atlas + Solana
├── agent-core/              # Claude Agent SDK orchestrator
├── voice-service/           # WebRTC + Whisper + ElevenLabs
├── web-app/                 # React + Vite UI
└── galactic-data/           # Price monitoring (existing)

backend/functions/           # Firebase Functions
.claude/
├── agents/                  # Sub-agents (market, fleet, craft, voice)
└── skills/                  # Star Atlas & Solana knowledge
```

See `ARCHITECTURE.md` for complete details (database schema, tech stack, ADRs, infrastructure).

---

## 🎯 Project-Specific Conventions

### Naming Conventions
- Packages: `kebab-case` (e.g., `mcp-staratlas-server`)
- Components: `PascalCase.tsx` (e.g., `PushToTalk.tsx`)
- Hooks: `use{FeatureName}.ts` (e.g., `useVoice.ts`)
- Services: `{feature}Service.ts` (e.g., `voiceService.ts`)
- Tests: `{filename}.test.ts`

### Voice Response Formatting
- Text mode: Technical, concise, structured
- Voice mode: Natural, conversational, no technical jargon

---

## ⚠️ Critical Constraints

1. **Voice Latency**: Voice round-trip MUST be < 500ms (use streaming STT/TTS)
2. **Wallet Security**: NEVER auto-sign transactions - always require explicit user approval
3. **Real-Time Data**: Use WebSocket subscriptions for Solana account changes (not polling)
4. **Offline Context**: MCP tools MUST handle RPC failures gracefully with fallbacks
5. **pnpm Only**: ALWAYS use `pnpm` for package management, never `npm` or `yarn`

---

## 🚀 Getting Started

```bash
# Install dependencies
pnpm install

# Start all services in development
pnpm dev
```

See `CONTRIBUTING.md` for complete workflow.

---

## 🔄 GitHub Workflow

**Commit-Issue Linking**: Every commit MUST reference a GitHub issue (`Closes #N`, `Relates to #N`). See `CONTRIBUTING.md` § Link Commits to Issues.

**PR Merge Strategy**: Use `gh pr merge --merge` (NOT `--squash`) to preserve feature branch history. See `DEVELOPMENT.md` § Git Branching Strategy.

---

## 🔗 External Links

- **Repository**: https://github.com/IAMSamuelRodda/star-atlas-agent
- **Star Atlas Docs**: https://build.staratlas.com/
- **SAGE API**: https://www.npmjs.com/package/@staratlas/sage
- **Claude Agent SDK**: https://docs.claude.com/en/api/agent-sdk/overview

---

## 🧪 Testing Notes

**Run tests:**
```bash
# All tests
pnpm test

# Specific package
pnpm --filter mcp-staratlas-server test

# E2E tests (requires test wallet)
pnpm test:e2e
```

**Details**: See `DEVELOPMENT.md` for complete setup and troubleshooting.

---

**Last Updated**: 2025-11-12
