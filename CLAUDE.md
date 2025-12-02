# IRIS - CLAUDE.md

> **Voice-first AI companion for Star Atlas** | *by Arc Forge*
> **Purpose**: Minimal navigation hub for AI agents (pointers to detailed documentation)
> **Lifecycle**: Living (target: ~100 lines max)

## 📍 Critical Documents

**Before starting work:**
1. `STATUS.md` → Current issues, active work, blockers
2. `ARCHITECTURE.md` → System design, database schema, tech stack
3. `CONTRIBUTING.md` → Progress tracking workflow
4. `docs/planning-session-2025-11-12.md` → Vision alignment & constraints

**Before finishing work:**
1. Update `STATUS.md` → Document investigation notes
2. Update issues → Close completed tasks, link commits
3. Check `DEVELOPMENT.md` → Run pre-commit checklist

---

## 🏗️ Architecture Quick Facts

**Style**: Event-Driven Microservices (Voice Service, Agent Core, MCP Server, Web App)

**Structure**: Serverless + DynamoDB (AWS Free Tier optimized)

See `ARCHITECTURE.md` for complete details.

---

## 🎯 Naming Conventions

- Packages: `kebab-case` (e.g., `mcp-staratlas-server`)
- Components: `PascalCase.tsx` (e.g., `FleetStatus.tsx`)
- Hooks: `use{Name}.ts` (e.g., `useVoice.ts`)
- Services: `{name}Service.ts` (e.g., `voiceService.ts`)

---

## ⚠️ Critical Constraints

1. **Voice latency**: <500ms round-trip (streaming STT/TTS required)
2. **Wallet security**: NEVER auto-sign transactions (explicit approval)
3. **Real-time data**: WebSocket subscriptions (not polling)
4. **AWS Free Tier**: <$10/month MVP budget
5. **pnpm only**: Package management consistency

---

## 🔄 Workflow Quick Reference

**Tier**: Simple (`main` only, no branch protection)

**Git Worktrees** (for parallel agent work):
```bash
# Create worktree on main
git worktree add ../iris--work main

# Work in isolated directory
cd ../iris--work

# Commit and push to main
git push origin main

# Clean up
git worktree remove ../iris--work
```

**Why worktrees?** Multiple Claude Code agents on same machine need isolated directories. Worktrees share the same `.git` objects without checkout conflicts.

**Commit linking**: Use `Closes #N` or `Relates to #N` in all commits.

---

## 🔗 External Links

- **Repository**: https://github.com/IAMSamuelRodda/iris
- **Star Atlas Docs**: https://build.staratlas.com/
- **SAGE API**: https://www.npmjs.com/package/@staratlas/sage
- **Claude Agent SDK**: https://docs.claude.com/en/api/agent-sdk/overview

---

**Last Updated**: 2025-12-02
