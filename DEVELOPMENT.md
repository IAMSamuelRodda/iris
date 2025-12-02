# Development Workflow

> **Purpose**: Git workflow, CI/CD pipelines, and pre-commit checklist
> **Lifecycle**: Stable (update when tooling or processes change)

---

## Workflow Tier: Simple

| Aspect | Configuration |
|--------|---------------|
| **Branches** | `main` only |
| **Protection** | None |
| **Deployment** | Push to main triggers deploy |
| **Worktrees** | For parallel agent work |

See `CONTRIBUTING.md` for detailed workflow guide.

---

## Development Flow

```bash
# 1. Pull latest
git pull origin main

# 2. Make changes
# ... edit files ...

# 3. Run pre-commit checks (see below)
pnpm lint:fix && pnpm format && pnpm test

# 4. Commit with issue reference
git add .
git commit -m "feat: add feature

Closes #123"

# 5. Push to main
git push origin main

# 6. CI runs automatically
gh run watch
```

---

## Pre-Commit Checklist (CRITICAL)

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

## CI/CD Workflow

After pushing to `main`, **GitHub Actions** automatically runs:

| Workflow | Checks | Duration |
|----------|--------|----------|
| **Validate** | Lint, format check | ~2 min |
| **Test** | Unit tests, integration tests | ~5 min |
| **Build** | TypeScript compile, package build | ~3 min |
| **Deploy** | Firebase Hosting + Functions | ~5 min |

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

## Test Organization

### Directory Structure

```
packages/
├── mcp-staratlas-server/
│   └── src/
│       ├── tools/
│       │   └── marketplace.test.ts    # Unit tests
│       └── __tests__/
│           └── integration/           # Integration tests
│
├── agent-core/
│   └── src/
│       ├── agent.test.ts             # Unit tests
│       └── __tests__/
│           └── e2e/                  # E2E tests
│
└── voice-service/
    └── src/
        ├── stt/
        │   └── whisper.test.ts       # Unit tests
        └── __tests__/
            └── integration/           # Integration tests
```

### Test Types

| Test Type | Location | External Deps | Run Command |
|-----------|----------|---------------|-------------|
| **Unit** | `*.test.ts` (co-located) | No | `pnpm test:unit` |
| **Integration** | `__tests__/integration/` | Yes (Solana devnet) | `pnpm test:integration` |
| **E2E** | `__tests__/e2e/` | Yes (all services) | `pnpm test:e2e` |

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

## Environment Variables

### Priority Order

1. `.env.local` (git-ignored, for local development)
2. `.env` (template, committed to repo)
3. Environment variables set in CI/CD (GitHub Secrets)

### Setup

```bash
# Copy template for each package
cp packages/mcp-staratlas-server/.env.example packages/mcp-staratlas-server/.env
cp packages/agent-core/.env.example packages/agent-core/.env
cp packages/voice-service/.env.example packages/voice-service/.env
cp packages/web-app/.env.example packages/web-app/.env

# Edit each .env file with your API keys
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

---

## Local Development Setup

### Prerequisites

- Node.js >= 20.0.0
- pnpm >= 9.0.0
- Firebase CLI (`npm install -g firebase-tools`)

### Monorepo Setup

```bash
# Clone repository
git clone https://github.com/IAMSamuelRodda/iris.git
cd iris

# Install all dependencies
pnpm install

# Set up environment variables (see above)

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

## Troubleshooting

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

```bash
# Login to Firebase
firebase login

# Select project
firebase use your-project-id

# Deploy
firebase deploy --only functions
```

### Voice Service WebRTC connection fails

1. Check browser console for WebRTC errors
2. Verify STUN/TURN server configuration in `packages/voice-service/src/webrtc/config.ts`
3. Test connection with minimal WebRTC example

---

## Additional Resources

- **Architecture**: `ARCHITECTURE.md` - Complete technical specifications
- **Workflow Guide**: `CONTRIBUTING.md` - Git workflow and progress tracking
- **Project Navigation**: `CLAUDE.md` - Quick reference for finding information

---

**Last Updated**: 2025-12-02
