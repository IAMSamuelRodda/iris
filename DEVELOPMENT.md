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

## Deployment (VPS + Docker)

**Infrastructure**: Digital Ocean VPS (existing droplet, $0 incremental)
**Pattern**: Docker Compose with manual deploy

### Deploy to VPS

```bash
# 1. Build locally
pnpm build

# 2. Push to main
git push origin main

# 3. SSH to VPS and pull + restart
ssh vps 'cd /opt/iris && git pull && docker-compose up -d --build'
```

### Docker Compose Services

```yaml
# docker-compose.yml (on VPS)
services:
  mcp-server:     # MCP tools for Solana/Star Atlas
  agent-core:     # Claude Agent SDK
  voice-backend:  # Python (FastAPI + faster-whisper + Kokoro)
  web-app:        # React frontend (static)
```

### Why No CI/CD Pipeline?

Simple workflow tier = manual deploy via SSH. Benefits:
- No GitHub Actions complexity
- Immediate visibility into deploy process
- $0 CI/CD cost
- Easy rollback (`git checkout HEAD~1 && docker-compose up -d`)

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
3. VPS environment (set in docker-compose or systemd)

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
DATABASE_PATH=/data/iris.db  # SQLite database
```

**voice-backend (Python):**
```env
STT_DEVICE=cuda          # or cpu
TTS_DEVICE=cuda          # or cpu
STT_MODEL_SIZE=base      # tiny, base, small, medium, large-v3
KOKORO_VOICE=af_heart    # default voice
```

**web-app:**
```env
VITE_API_URL=http://localhost:3000
```

---

## Native Client Secrets (API Keys for Tools)

The native IRIS client (`iris_local.py`) uses a separate secrets file for tool API keys.

### Setup

```bash
# 1. Create config directory (first time only)
mkdir -p ~/.config/iris

# 2. Create secrets file from template (template is in repo)
cp packages/voice-backend/secrets.env.template ~/.config/iris/secrets.env

# 3. Edit and add your API keys
nano ~/.config/iris/secrets.env
```

### Available API Keys

```env
# ~/.config/iris/secrets.env

# Brave Search API (free tier at https://brave.com/search/api/)
BRAVE_API_KEY=your_brave_api_key_here
```

### Priority Order

1. `~/.config/iris/secrets.env` (recommended, persistent)
2. Environment variables (fallback)

### Security Notes

- `secrets.env` is user-only readable (Unix permissions)
- Never commit secrets to version control
- For AI agents setting up new machines: prompt user to provide keys via secure input

### Tools Requiring API Keys

| Tool | API Key | Free Tier |
|------|---------|-----------|
| `web_search` | `BRAVE_API_KEY` | Yes (2,000/month) |

### Verifying Setup

```bash
cd packages/voice-backend
source .venv/bin/activate
python src/tools.py  # Shows which tools are configured
```

---

## Local Development Setup

### Prerequisites

- Node.js >= 20.0.0
- pnpm >= 9.0.0
- Docker + Docker Compose (for local services)

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

# Voice Backend (Python)
cd packages/voice-backend
python -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8001
```

### Voice Backend Testing

```bash
cd packages/voice-backend
source .venv/bin/activate

# Run text preprocessing tests (26 test cases)
python src/text_processing.py

# Run preprocessing performance benchmark
python test_preprocessing_perf.py

# Run with audio playback
python test_preprocessing_perf.py --play

# Run voice flow test (STT → LLM → TTS)
python test_voice_flow.py --models qwen2.5:7b

# GPU configuration (default)
STT_DEVICE=cuda TTS_DEVICE=cuda python -m uvicorn src.main:app --port 8001
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

### Docker containers won't start

```bash
# Check container logs
docker-compose logs -f

# Rebuild containers
docker-compose build --no-cache

# Check port conflicts
lsof -i :3000  # or other ports
```

### Voice Backend connection fails

1. Verify voice-backend is running: `curl http://localhost:8001/health`
2. Check WebSocket connectivity in browser console
3. Ensure CORS is configured for your frontend URL
4. For GPU issues, check CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`

### TTS says "Chinese letter" repeatedly

This happens when LLM outputs CJK characters. The text preprocessing module
converts them, but if you hear this:
1. Check LLM output for Chinese characters
2. Verify `preprocess_for_tts()` is being called in `tts_kokoro.py`
3. Run: `python src/text_processing.py` to verify 26 tests pass

---

## LLM Infrastructure & Future Architecture

### Current Setup: Ollama (Single Model)

IRIS currently uses Ollama for local LLM inference. This is appropriate for:
- Single-user voice assistant
- Simple tool calling
- Fast inference with ~0ms tool overhead

### Future: Subagent Delegation Architecture

When IRIS needs to perform complex tasks while preserving the main conversation context:

```
┌─────────────────────────────────────────────────────────────┐
│                    IRIS Main Agent                           │
│  (Conversational model - preserves user context)             │
│                          │                                   │
│    "I need to research that. Give me a moment..."           │
│                          │                                   │
│              ┌───────────┴───────────┐                      │
│              ▼                       ▼                      │
│     ┌─────────────┐         ┌─────────────┐                │
│     │ Task Runner │         │ Deep Thinker │                │
│     │ (small/fast)│         │ (larger model)│               │
│     └─────────────┘         └─────────────┘                │
│              │                       │                      │
│              └───────────┬───────────┘                      │
│                          ▼                                   │
│              [Results returned to main agent]               │
└─────────────────────────────────────────────────────────────┘
```

**Current Limitation (Ollama)**:
- `OLLAMA_MAX_LOADED_MODELS=2` - only 2 models hot at once
- Model swaps take ~2-3 seconds
- Acceptable for MVP with proper UX feedback

**Future Migration Path**:
- **vLLM**: Better concurrent model management, production-grade
- **SGLang**: Superior tool calling with constrained decoding
- See ISSUES.md ARCH-008 for trigger conditions

### UX for Delegation

When IRIS delegates to a subagent, user feedback is critical:

```python
# Example delegation flow
async def delegate_research(query: str):
    # 1. Inform user (they'll wait)
    yield "Let me look into that for you..."

    # 2. Run subagent (thinking model)
    result = await thinking_agent.process(query)

    # 3. Return with context
    yield f"I found: {result.summary}"
```

**Key Principle**: IRIS communicates what she's doing. Users expect delays for complex tasks.

### Context Window Optimization (Future)

See ISSUES.md ARCH-009 for context window optimization strategies:
- Conversation summarization
- Sliding window with key facts
- Tool result compression
- Semantic chunking

---

## Additional Resources

- **Architecture**: `ARCHITECTURE.md` - Complete technical specifications
- **Workflow Guide**: `CONTRIBUTING.md` - Git workflow and progress tracking
- **Project Navigation**: `CLAUDE.md` - Quick reference for finding information
- **Tool Research**: `specs/RESEARCH-tool-integration-architecture.md` - Ollama vs MCP tools

---

**Last Updated**: 2025-12-06
