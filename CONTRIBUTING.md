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
- [ ] PR approved � merged to dev

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

**Hierarchy**: Epic (Milestone) � Feature (Issue) � Task (Sub-issue)

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

# � MUST target dev branch, NOT main
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
feature/* � dev (staging) � main (production)
```

**Rules**:
- � main ONLY accepts PRs from dev
- � dev ONLY accepts PRs from feature/fix/spike branches
- � No direct commits to dev or main

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

## CI/CD Workflows

**Automated workflows enforce code quality and deployment safety.**

### Branch Protection
- **enforce-main-pr-source.yml**: Blocks PRs to `main` unless from `dev`
- Prevents accidental direct merges to production

### Continuous Integration (on PRs to dev/main)
- **ci.yml**: Runs lint, typecheck, format check, tests, and build
- **security.yml**: Dependency audit, CodeQL analysis, secret scanning
- **terraform.yml**: Infrastructure validation (only when terraform/ changes)

### Auto-merge (feature → dev)
- **auto-merge-to-dev.yml**: Automatically merges feature/* and fix/* branches to dev after CI passes
- Reduces manual PR merging overhead
- Squash commits for clean history

### Deployments
- **deploy-staging.yml**: Deploys dev → staging (comprehensive E2E tests)
- **deploy-production.yml**: Deploys main → production (smoke tests + auto-rollback)
- **e2e-tests.yml**: Reusable E2E testing workflow

### Deployment Strategy (Amazon-style)
- **Staging**: Comprehensive E2E tests (full validation)
- **Production**: Minimal smoke tests + health checks + CloudWatch monitoring
- **Auto-rollback**: Production deployments roll back automatically if health checks fail

---

## Best Practices

1. Read `STATUS.md` before starting
2. Update issue status when working
3. Commit frequently
4. Link commits to issues
5. Run pre-commit checklist (see DEVELOPMENT.md)
6. Update docs with code
7. Let CI/CD handle merges and deployments (automation reduces errors)

---

**Last Updated**: 2025-11-13
