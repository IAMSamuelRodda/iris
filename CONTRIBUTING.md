# Contributing to IRIS

> **Purpose**: Workflow guide for development
> **Lifecycle**: Stable (update when processes change)

---

## Workflow Tier: Simple

**Branches**: `main` only
**Protection**: None (direct pushes allowed)
**Worktrees**: For parallel agent work on main

### Why Simple Tier?

- Solo developer / small team
- Fast iteration and experimentation
- AI-assisted development
- No external stakeholder approval needed

---

## Git Workflow: Direct Commits to Main

### Standard Development

```bash
# Pull latest
git pull origin main

# Make changes
# ... edit files ...

# Commit with issue reference
git add .
git commit -m "feat: add voice streaming

Closes #42"

# Push directly to main
git push origin main
```

### Issue Linking (REQUIRED)

Every commit should reference an issue:
- `Closes #42` - Closes on merge
- `Relates to #42` - References only
- `Fixes #42` - Closes on merge (bug fixes)

---

## Parallel Agent Work: Worktrees

**Why worktrees?** Multiple Claude Code agents on the same machine cause conflicts when switching branches. Worktrees provide isolated directories sharing the same `.git` objects.

### When to Use Worktrees

Use worktrees when:
- Multiple agents need to work simultaneously
- Testing changes in isolation before committing to main
- Large refactors that shouldn't block other work

### Worktree Commands

```bash
# From main repo directory
cd /home/x-forge/repos/iris

# Create worktree for isolated work
git worktree add ../iris--experiment main

# Work in the isolated directory
cd ../iris--experiment

# Make changes, test locally
pnpm install
pnpm dev

# When ready, commit and push (still on main)
git add .
git commit -m "feat: experimental feature

Relates to #42"
git push origin main

# Clean up worktree
cd /home/x-forge/repos/iris
git worktree remove ../iris--experiment
```

### Parallel Agent Example

```
Terminal 1: /home/x-forge/repos/iris (main)
Terminal 2: /home/x-forge/repos/iris--voice (worktree on main)
Terminal 3: /home/x-forge/repos/iris--mcp (worktree on main)
```

Each worktree is isolated - agents can work in parallel without conflicts.

---

## Quick Reference

```bash
# List active worktrees
git worktree list

# Create worktree (for parallel work)
git worktree add ../iris--<name> main

# Remove worktree (when done)
git worktree remove ../iris--<name>

# Prune stale worktrees
git worktree prune
```

---

## Commit Format

**Pattern**: `<type>: <description>`

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Example**:
```
feat: add voice streaming

Implements WebSocket STT with <500ms latency.

Closes #42
```

---

## Progress Tracking

**Tool**: GitHub Issues (simple)

**Labels**:
- Type: `feature`, `bug`, `spike`
- Status: `in-progress`, `blocked` (only when needed)

**Start work**:
```bash
gh issue edit <N> --add-label "in-progress"
```

**Complete work**: Use `Closes #N` in commit message (auto-closes)

---

## Definition of Done

### Feature
- [ ] Implemented
- [ ] Tests passing (when applicable)
- [ ] Issue linked (`Closes #N`)
- [ ] Pushed to main

### Bug Fix
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Issue updated
- [ ] Pushed to main

---

**Last Updated**: 2025-12-02
