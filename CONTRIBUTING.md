# Contributing to Star Atlas Agent

> **Purpose**: Workflow guide and progress tracking
> **Lifecycle**: Stable (update when processes change)

> **Technical setup**: See `DEVELOPMENT.md` for git workflow, pre-commit checklist, CI/CD

---

## Quick Start

```bash
git clone https://github.com/IAMSamuelRodda/star-atlas-agent.git
cd star-atlas-agent
pnpm install
pnpm dev
```

See [`DEVELOPMENT.md`](./DEVELOPMENT.md) for complete setup.

---

## Definition of Done

### Feature
- [ ] Implemented and tested
- [ ] Tests passing
- [ ] Docs updated
- [ ] Issue linked (`Closes #N`)
- [ ] PR approved ’ merged to dev

### Bug Fix
- [ ] Root cause documented
- [ ] Reproduction test written
- [ ] Fix implemented
- [ ] Test passing
- [ ] Issue updated

### Spike
- [ ] Research questions answered
- [ ] Options evaluated
- [ ] Recommendation documented
- [ ] Findings in ARCHITECTURE.md or docs/

---

## Progress Tracking

**Tool**: GitHub Issues + Projects

**Hierarchy**: Epic (Milestone) ’ Feature (Issue) ’ Task (Sub-issue)

**Labels**:
- Type: `epic`, `feature`, `task`, `bug`, `spike`
- Status: `pending`, `in-progress`, `completed`, `blocked`
- Priority: `critical`, `high`, `medium`, `low`

**Commands**:
```bash
# Start work
gh issue edit <N> --add-label "status: in-progress"

# Mark blocked
gh issue edit <N> --add-label "status: blocked"
gh issue comment <N> --body "Blocked by #<other-issue>"

# Complete
# (Automatic via "Closes #N" in commit message)
```

---

## Workflow

### Start Work
```bash
git checkout dev
git pull origin dev
git checkout -b feature/my-feature

gh issue edit <N> --add-label "status: in-progress"
```

### During Work
```bash
git commit -m "feat: add feature

Relates to #42"

git push
```

### Complete Work
```bash
git commit -m "feat: complete feature

Closes #42"

git push
gh pr create --base dev --head feature/my-feature

#   MUST target dev branch, NOT main
```

### Release to Production
```bash
# After staging validation
gh pr create --base main --head dev --title "Release v0.2.0"

#  ONLY way to merge to main
```

---

## Git Branching

**Strategy**: Three-tier with branch protection

```
feature/* ’ dev (staging) ’ main (production)
```

**Rules**:
- Ô main ONLY accepts PRs from dev
- Ô dev ONLY accepts PRs from feature/fix/spike branches
- Ô No direct commits to dev or main

See [`DEVELOPMENT.md`](./DEVELOPMENT.md) for complete workflow.

---

## Commit Format

**Pattern**: `<type>: <description>`

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Issue Linking** (REQUIRED):
- `Closes #42` - Closes on merge
- `Relates to #42` - References only
- `Fixes #42` - Same as Closes

**Example**:
```
feat: add voice streaming

Implements WebSocket STT with <500ms latency.

Closes #42
```

---

## Best Practices

1. Read `STATUS.md` before starting
2. Update issue status when working
3. Commit frequently
4. Link commits to issues
5. Run pre-commit checklist (see DEVELOPMENT.md)
6. Update docs with code

---

**Last Updated**: 2025-11-12
