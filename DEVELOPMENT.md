# Development Workflow

> **Purpose**: Git workflow, CI/CD pipelines, and pre-commit checklist
> **Lifecycle**: Stable (update when branching strategy or CI/CD processes change)

---

## 🌿 Git Branching Strategy

This project uses a **feature branch workflow** with direct merges to `main`.

### Branch Overview

| Branch | Purpose | Deployments | Auto-Merge | Approval Required |
|--------|---------|-------------|-----------|-------------------|
| `main` | Production-ready code | Firebase Hosting + Functions | No | Yes (1 approval) |
| `feature/*` | New features | None (local dev only) | No | N/A |
| `fix/*` | Bug fixes | None (local dev only) | No | N/A |

### Development Flow

```bash
# 1. Always branch from main
git checkout main
git pull origin main
git checkout -b feature/my-feature

# 2. Work on feature with frequent commits
git add .
git commit -m "feat: add feature (Relates to #123)"

# 3. Push and create PR
git push -u origin feature/my-feature
gh pr create --title "feat: add feature" --body "Closes #123"

# 4. CI runs: lint → format → test → build
# 5. After approval, merge to main
gh pr merge --merge
```

### PR Merge Strategy

**RULE**: Use `--merge` for all PRs (creates merge commit).

**Why**: Preserves feature branch history for easier debugging and rollback.

**How to Merge**:
```bash
# After PR approval and CI passes
gh pr merge 123 --merge

# Do NOT use:
gh pr merge --squash  # ❌ Loses commit history
gh pr merge --rebase  # ❌ Rewrites history
```

---

## 🔍 Pre-Commit Checklist (CRITICAL)

**Before EVERY commit**, complete this checklist:

```bash
# 1. Run linting and auto-fix issues
pnpm lint:fix

# 2. Format code
pnpm format

# 3. Run unit tests (if applicable to changes)
pnpm test

# 4. [OPTIONAL] Run E2E tests (if modifying critical paths)
pnpm test:e2e

# 5. Review staged changes
git status
git diff --staged

# 6. Verify commit message includes issue reference
#    Use: "Closes #N", "Relates to #N", "Fixes #N"
```

**Why**: CI runs these same checks. Catching issues locally saves time and prevents broken builds.

---

## 🚀 CI/CD Workflow Expectations

After pushing to branches, **GitHub Actions** automatically runs these workflows:

| Workflow | Triggers | Checks | Pass Criteria | Duration |
|----------|----------|--------|---------------|----------|
| **Validate** | Push to any branch | Lint, format check | All pass | ~2 min |
| **Test** | Push to any branch | Unit tests, integration tests | All pass | ~5 min |
| **Build** | Push to any branch | TypeScript compile, package build | No errors | ~3 min |
| **Deploy** | Merge to `main` | Deploy to Firebase | Successful deployment | ~5 min |

### Branch-Specific Workflows

**On `feature/*` → `main` PR**:
1. Lint check (`eslint`)
2. Format check (`prettier`)
3. Unit tests (`vitest`)
4. TypeScript compilation
5. Build all packages

**On `main` push (after merge)**:
1. All validation steps above
2. Deploy web app to Firebase Hosting
3. Deploy functions to Firebase Functions
4. Deploy voice service to Cloud Run

### Monitoring Workflow Status

```bash
# View recent workflow runs
gh run list

# Watch latest workflow (blocks until complete)
gh run watch

# View specific workflow logs
gh run view 1234567890
```

### If Workflows Fail

1. **Check which workflow failed**: `gh run list`
2. **View failure logs**: `gh run view --log-failed`
3. **Fix issues locally** using pre-commit checklist
4. **Push fix**: CI will re-run automatically

**Common failures**:
- **Test failures**: Check test output, fix failing tests
- **Lint failures**: Run `pnpm lint:fix` to auto-fix
- **Build failures**: Check TypeScript errors, fix type issues

---

## 🧪 Test Organization

### Directory Structure

```
packages/
├── mcp-staratlas-server/
│   └── src/
│       ├── tools/
│       │   └── marketplace.test.ts    # Unit tests
│       └── __tests__/
│           └── integration/           # Integration tests
│               └── sage-client.test.ts
│
├── agent-core/
│   └── src/
│       ├── agent.test.ts             # Unit tests
│       └── __tests__/
│           └── e2e/                  # E2E tests
│               └── voice-flow.test.ts
│
└── voice-service/
    └── src/
        ├── stt/
        │   └── whisper.test.ts       # Unit tests
        └── __tests__/
            └── integration/           # Integration tests
                └── webrtc-flow.test.ts
```

### Test Types

| Test Type | Location | External Deps | Run Command |
|-----------|----------|---------------|-------------|
| **Unit** | `*.test.ts` (co-located) | No | `pnpm test:unit` |
| **Integration** | `__tests__/integration/` | Yes (Solana devnet) | `pnpm test:integration` |
| **E2E** | `__tests__/e2e/` | Yes (all services) | `pnpm test:e2e` |

**Rule**: Unit tests have no external dependencies (mocked). Integration tests use real services (devnet). E2E tests test the full system.

### Running Tests Locally

```bash
# Unit tests (fast, no dependencies)
pnpm test:unit

# Integration tests (requires Solana devnet)
pnpm test:integration

# E2E tests (requires all services running)
pnpm test:e2e

# All tests
pnpm test

# With coverage
pnpm test:coverage
```

---

## 🔐 Environment Variables

### How It Works

Environment variables are loaded from `.env` files in each package directory. The project uses `dotenv` to load variables at runtime.

**Priority order:**
1. `.env.local` (git-ignored, for local development)
2. `.env` (template, committed to repo)
3. Environment variables set in CI/CD (GitHub Secrets)

### Usage

```bash
# Copy template for each package
cp packages/mcp-staratlas-server/.env.example packages/mcp-staratlas-server/.env
cp packages/agent-core/.env.example packages/agent-core/.env

# Edit with your API keys
# Never commit .env.local files (they're git-ignored)
```

### Required Variables

**mcp-staratlas-server:**
```env
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_WS_URL=wss://api.mainnet-beta.solana.com
HELIUS_API_KEY=your_helius_key (optional, for enhanced RPC)
```

**agent-core:**
```env
ANTHROPIC_API_KEY=sk-ant-...
```

**voice-service:**
```env
OPENAI_API_KEY=sk-...  # For Whisper STT
ELEVENLABS_API_KEY=... # For TTS
```

**web-app:**
```env
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_API_KEY=your_api_key
```

### Troubleshooting

#### Error: Missing environment variable

**Cause**: `.env` file not present or variable not set

**Solutions:**
1. Copy `.env.example` to `.env` in the package directory
2. Set all required variables with your API keys
3. Restart development server after changes

---

## 📦 Local Development Setup

### Prerequisites

- Node.js >= 20.0.0
- pnpm >= 9.0.0
- Firebase CLI (`npm install -g firebase-tools`)

### Monorepo Setup

```bash
# Clone repository
git clone https://github.com/IAMSamuelRodda/star-atlas-agent.git
cd star-atlas-agent

# Install all dependencies
pnpm install

# Set up environment variables for each package
cp packages/mcp-staratlas-server/.env.example packages/mcp-staratlas-server/.env
cp packages/agent-core/.env.example packages/agent-core/.env
cp packages/voice-service/.env.example packages/voice-service/.env
cp packages/web-app/.env.example packages/web-app/.env
# Edit each .env file with your API keys

# Start all services in development mode
pnpm dev
```

### Individual Package Setup

```bash
# MCP Server
cd packages/mcp-staratlas-server
pnpm install
pnpm dev

# Agent Core
cd packages/agent-core
pnpm install
pnpm dev

# Voice Service
cd packages/voice-service
pnpm install
pnpm dev

# Web App
cd packages/web-app
pnpm install
pnpm dev
```

---

## 🐛 Troubleshooting

### pnpm install fails

```bash
# Clear pnpm cache
pnpm store prune

# Remove node_modules and lockfile
rm -rf node_modules pnpm-lock.yaml

# Reinstall
pnpm install
```

### TypeScript errors in IDE

```bash
# Rebuild TypeScript project references
pnpm -r build

# Restart TypeScript server in IDE
# VS Code: Cmd+Shift+P → "TypeScript: Restart TS Server"
```

### Firebase Functions deploy fails

**Cause**: Missing Firebase credentials or project not selected

**Solution**:
```bash
# Login to Firebase
firebase login

# Select project
firebase use your-project-id

# Deploy
firebase deploy --only functions
```

### Voice Service WebRTC connection fails

**Cause**: STUN/TURN server not accessible or misconfigured

**Solution**:
1. Check browser console for WebRTC errors
2. Verify STUN/TURN server configuration in `packages/voice-service/src/webrtc/config.ts`
3. Test connection with minimal WebRTC example

---

## 📚 Additional Resources

- **Architecture**: `ARCHITECTURE.md` - Complete technical specifications
- **Progress Tracking**: `CONTRIBUTING.md` - Issue workflow and commands
- **Project Navigation**: `CLAUDE.md` - Quick reference for finding information

---

**Last Updated**: 2025-11-12
