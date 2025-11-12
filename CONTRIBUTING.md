# Contributing to Star Atlas Agent

> **Purpose**: Workflow guide, progress tracking, and planning new features
> **Lifecycle**: Stable (update when workflow processes change)

> **Before submitting code**: See `DEVELOPMENT.md` for pre-commit checklist, CI/CD expectations, and test organization.

## Getting Started: Local Development

**🚀 Quick Start**

```bash
# Clone repository
git clone https://github.com/IAMSamuelRodda/star-atlas-agent.git
cd star-atlas-agent

# Install dependencies
pnpm install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys (Anthropic, OpenAI, ElevenLabs, Solana RPC)

# Start all services in development mode
pnpm dev
```

**What it sets up:**
- MCP server on `http://localhost:3000`
- Agent core on `http://localhost:3001`
- Voice service on `http://localhost:3002`
- Web app on `http://localhost:5173`

**Result:** Browser opens at http://localhost:5173, ready to interact with the agent!

**Full setup details:** See [`DEVELOPMENT.md`](./DEVELOPMENT.md) for complete environment configuration.

---

## Definition of Done

### For Feature Development

**Required:**
- [ ] Feature implemented and tested locally
- [ ] Unit tests written and passing
- [ ] Integration tests written (if applicable)
- [ ] Documentation updated (README, ARCHITECTURE, or comments)
- [ ] PR created with descriptive title and issue reference
- [ ] CI/CD pipeline passing (lint, format, tests)
- [ ] Code reviewed and approved
- [ ] STATUS.md updated with implementation notes

### For Bug Fixes

**⚠️ CRITICAL REQUIREMENT**: All bug fixes MUST include automated tests that verify the fix.

**Required:**
- [ ] Root cause identified and documented in STATUS.md
- [ ] Fix implemented
- [ ] Test written that reproduces the bug (fails before fix, passes after)
- [ ] Regression test added to test suite
- [ ] Issue updated with investigation notes
- [ ] STATUS.md updated in "Known Issues" → "Recent Achievements"

### For Voice Feature Bug Fixes

**Additional Requirements:**
- [ ] Voice latency measured (must be < 500ms round-trip)
- [ ] Audio quality verified (no distortion, clear playback)
- [ ] WebRTC connection stability tested (no disconnections)

---

## Progress Tracking

This project uses **GitHub Issues + GitHub Projects v2** for progress tracking.

### Issue Hierarchy

```
Milestone (timeboxed release group: MVP, Phase 2, etc.)
  ↓
Epic (large feature/initiative: "Voice Service Foundation")
  ├─ Feature (user-facing functionality: "Whisper STT integration")
  │   └─ Task (implementation work: "Add Whisper API client")
  └─ Feature ("ElevenLabs TTS integration")
      └─ Task ("Configure voice selection")
```

### Quick Reference

```bash
# View all issues
gh issue list

# View specific epic/feature
gh issue view 123

# View project board
gh project list
gh project view 1
```

---

## Working on Features/Tasks

### Starting Work

```bash
# 1. Create branch from main
git checkout main
git pull origin main
git checkout -b feature/feature-name

# 2. Update issue status (if using GitHub Projects)
gh issue edit 123 --add-label "status: in-progress"

# 3. Add comment with plan
gh issue comment 123 --body "Starting implementation:
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3"
```

### Completing Work

```bash
# 1. Run pre-commit checklist (see DEVELOPMENT.md)
pnpm lint:fix
pnpm format
pnpm test

# 2. Create commit with issue reference
git add .
git commit -m "feat: add Whisper STT integration

Implements speech-to-text conversion using OpenAI Whisper API.
Supports streaming audio from WebRTC and returns transcribed text.

Closes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Push and create PR
git push -u origin feature/feature-name
gh pr create --title "feat: add Whisper STT integration" \
  --body "Closes #123

## Summary
- Integrated OpenAI Whisper API for speech-to-text
- Added streaming support for WebRTC audio
- Configured voice activity detection

## Testing
- Unit tests for Whisper client
- Integration test with sample audio file
- Latency measured at 180ms average

## Screenshots
(Add if applicable)"

# 4. Wait for CI to pass, then merge
gh pr merge --merge
```

### Marking as Blocked

```bash
# Add blocked label and link to blocker
gh issue edit 123 --add-label "status: blocked"
gh issue comment 123 --body "🚫 Blocked by #124: Need Solana RPC endpoint configured before implementing blockchain monitoring"

# When unblocked
gh issue edit 123 --remove-label "status: blocked" --add-label "status: in-progress"
gh issue comment 123 --body "✅ Unblocked: RPC endpoint configured in #124"
```

---

## Git Workflow

This project uses a **feature branch workflow** with direct merges to `main`.

**Quick Reference:**
```bash
# Create feature branch from main
git checkout main && git pull origin main
git checkout -b feature/my-feature

# Commit with issue reference
git commit -m "feat: implement feature

Detailed description of changes.

Closes #N

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Create PR
gh pr create --title "feat: implement feature" --body "Closes #N"
```

**See [`DEVELOPMENT.md`](./DEVELOPMENT.md)** for complete git workflow, CI/CD expectations, and troubleshooting.

---

## Best Practices

### 1. Always Check Current State First

```bash
# See what's being worked on
gh issue list --label "status: in-progress"

# View specific item's progress
gh issue view 123
```

### 2. Update Status When Starting Work

```bash
# Mark in-progress
gh issue edit 123 --add-label "status: in-progress"
```

### 3. Comment on Progress

```bash
# Add detailed progress comments
gh issue comment 123 --body "Completed Whisper integration milestone:
- ✅ API client configured
- ✅ Streaming audio support
- ✅ Error handling and retries

Next: Test with WebRTC audio pipeline"
```

### 4. Link Commits to Issues

```bash
# Reference issue in commit messages
git commit -m "feat: add voice command parser

Implements natural language parsing for voice commands.
Uses Claude Agent SDK for intent recognition.

Relates to #45

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Planning New Features

### BLUEPRINT.yaml Lifecycle

**BLUEPRINT.yaml** is a planning tool for generating GitHub issues from structured roadmaps, NOT a living reference document.

**When to Use:**
- Planning new multi-phase features
- Estimating project scope and timelines
- Generating hierarchical issue structures

**When NOT to Use:**
- ❌ As reference during implementation (use GitHub issues instead)
- ❌ For tracking current progress (use STATUS.md and GitHub Projects)
- ❌ For architectural decisions (use ARCHITECTURE.md ADRs)

### Lifecycle Flow

```
1. Plan Feature → Write BLUEPRINT.yaml structure
2. Generate Issues → Use github-project-infrastructure skill
3. Archive → BLUEPRINT.yaml becomes historical
4. Track Progress → Use GitHub Issues/Projects, NOT BLUEPRINT.yaml
```

---

## Agent Delegation

### Sub-Agent Architecture

This project uses specialized sub-agents for domain-specific tasks:

**Market Analyst Agent** (`.claude/agents/market-analyst.md`):
- Price analysis and trend identification
- Trading recommendations
- Alert management

**Usage:**
```
Delegate when analyzing market data:
"Analyze the price trend for titanium over the last 7 days and recommend if it's a good time to buy"
```

**Fleet Commander Agent** (`.claude/agents/fleet-commander.md`):
- Fleet status queries
- Movement commands
- Resource management

**Usage:**
```
Delegate when managing fleets:
"Check Fleet Alpha's status and recommend next actions based on fuel and health levels"
```

**Craft Optimizer Agent** (`.claude/agents/craft-optimizer.md`):
- Recipe analysis
- Cost optimization
- Material allocation

**Usage:**
```
Delegate when optimizing crafting:
"Find the cheapest way to craft a medium fighter using current market prices"
```

---

## Project Links

- **GitHub Repository**: https://github.com/IAMSamuelRodda/star-atlas-agent
- **Issues**: https://github.com/IAMSamuelRodda/star-atlas-agent/issues
- **Star Atlas Docs**: https://build.staratlas.com/

---

## Example Workflow

### Starting a New Feature

```bash
# 1. Check current state
gh issue list

# 2. View feature details
gh issue view 45

# 3. Start work
git checkout main && git pull origin main
git checkout -b feature/voice-commands
gh issue edit 45 --add-label "status: in-progress"

# 4. Do the work
# ... implement feature ...

# 5. Commit with issue reference
git add .
git commit -m "feat: add voice command parser

Implements natural language parsing for voice commands.

Relates to #45

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 6. Comment on progress
gh issue comment 45 --body "✅ Voice command parser complete:
- Intent recognition working
- 95% accuracy on test set
- Integrated with agent core

Next: Add error handling for ambiguous commands"

# 7. When feature complete
gh pr create --title "feat: add voice command parser" --body "Closes #45"
gh pr merge --merge
```

---

## Troubleshooting

### GitHub CLI Not Authenticated

```bash
gh auth login
# Follow prompts to authenticate
```

### Can't See Issues

```bash
# Refresh authentication with required scopes
gh auth refresh -h github.com -s repo,project,read:project
```

---

## Need Help?

### Documentation
- Review `specs/BLUEPRINT.yaml` for project roadmap
- Check `ARCHITECTURE.md` for system architecture
- View git history: `git log --oneline --graph`

### Progress Tracking
- View all issues: `gh issue list`
- View project status: See `STATUS.md`

---

**Last Updated**: 2025-11-12
