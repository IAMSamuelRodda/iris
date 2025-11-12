# CI/CD Documentation

This document describes the continuous integration and deployment workflows for the Star Atlas Agent project.

## GitHub Actions Workflows

### CI Workflow (`.github/workflows/ci.yml`)

Runs on every PR and push to `dev` and `main` branches.

**Jobs**:

1. **lint-and-typecheck**
   - Runs ESLint on all TypeScript files
   - Type checks all packages with `tsc`
   - Checks code formatting with Prettier
   - **Timeout**: 10 minutes

2. **test**
   - Runs Vitest unit tests across all packages
   - **Timeout**: 10 minutes

3. **build**
   - Builds all packages to verify compilation
   - Ensures no build errors before merge
   - **Timeout**: 15 minutes

**Optimizations**:
- pnpm store caching (speeds up installs)
- Frozen lockfile (`--frozen-lockfile`)
- Parallel job execution

### Terraform Workflow (`.github/workflows/terraform.yml`)

Runs on PRs that modify Terraform files.

**Triggers**:
- Changes to `terraform/**`
- Changes to `.github/workflows/terraform.yml`

**Jobs**:

1. **terraform-plan**
   - Format check (`terraform fmt -check`)
   - Initialization (`terraform init -backend=false`)
   - Validation (`terraform validate`)
   - Plan with dev variables
   - **Posts plan to PR as comment**
   - **Timeout**: 15 minutes

**Features**:
- Automatic PR comments with plan output
- Validation errors visible in PR
- Format violations fail the check

### Branch Protection Workflow (`.github/workflows/enforce-main-pr-source.yml`)

Enforces three-tier branching strategy.

**Rules**:
- PRs to `main` must originate from `dev` branch only
- Prevents accidental direct merges from feature branches
- Fails with clear error message if violated

## Branching Strategy

```
feature/fix branches → dev (staging) → main (production)
```

**Workflow**:
1. Create feature branch from `dev`
2. Make changes and commit
3. Open PR to `dev` (CI runs: lint, test, build)
4. Merge to `dev` after approval
5. Periodically promote `dev` to `main` via PR (production release)

## Required Status Checks

### For PRs to `dev`:
- ✅ CI: lint-and-typecheck
- ✅ CI: test
- ✅ CI: build
- ✅ Terraform: plan (if Terraform files modified)
- ✅ Branch protection: allow any source branch

### For PRs to `main`:
- ✅ CI: lint-and-typecheck
- ✅ CI: test
- ✅ CI: build
- ✅ Terraform: plan (if Terraform files modified)
- ✅ Branch protection: must be from `dev` branch only

## Terraform State Management

### Remote State Backend

**Location**: S3 bucket with DynamoDB locking

**Setup** (one-time):

```bash
# 1. Bootstrap state backend
cd terraform/bootstrap
terraform init
terraform apply

# 2. Update terraform/versions.tf with backend config
terraform output -raw backend_config

# 3. Migrate state to remote
cd ../
terraform init -migrate-state
```

**Benefits**:
- Team collaboration (shared state)
- State locking (prevents concurrent modifications)
- State versioning (rollback capability)
- Encryption at rest

### State Backend Resources

- **S3 Bucket**: `star-atlas-agent-terraform-state-{region}`
  - Versioning: Enabled
  - Encryption: AES256
  - Public access: Blocked

- **DynamoDB Table**: `star-atlas-agent-terraform-locks`
  - Billing: Pay-per-request
  - Purpose: Atomic state locking

## Local Development

### Running CI Checks Locally

Before pushing, run these locally to catch issues:

```bash
# Install dependencies
pnpm install

# Lint
pnpm lint

# Type check
pnpm typecheck

# Format check
pnpm format:check

# Fix formatting
pnpm format

# Test
pnpm test

# Build
pnpm build
```

### Terraform Validation

```bash
cd terraform

# Format
terraform fmt -recursive

# Validate
terraform init -backend=false
terraform validate

# Plan
terraform plan -var-file=environments/dev/terraform.tfvars
```

## Secrets Management

**Current**: No secrets in CI yet

**Future** (when implementing AWS deployments):
- AWS credentials via GitHub Secrets
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- Environment-specific secrets for dev/staging/prod

## Deployment Pipeline

**Current**: Manual deployment (infrastructure code only)

**Future** (post-MVP):
1. **Continuous Integration** (current)
   - Lint, test, build on every PR

2. **Continuous Deployment to Staging** (dev branch)
   - Auto-deploy to AWS dev environment
   - Run E2E tests
   - Performance validation

3. **Continuous Deployment to Production** (main branch)
   - Manual approval required
   - Deploy to AWS prod environment
   - Smoke tests
   - Rollback capability

## Monitoring CI/CD

### GitHub Actions
- View workflow runs: `Actions` tab in GitHub
- Failed builds: Red X on PR
- Logs: Click on workflow run → job → step

### Terraform Plans
- View in PR comments
- Check for unexpected changes
- Validate resource changes before merge

## Troubleshooting

### CI Failures

**Lint errors**:
```bash
pnpm lint  # See errors
pnpm format  # Auto-fix formatting
```

**Type errors**:
```bash
pnpm typecheck  # See type issues
# Fix manually in code
```

**Build failures**:
```bash
pnpm build  # Reproduce locally
# Check for missing dependencies or syntax errors
```

### Terraform Failures

**Format check failed**:
```bash
terraform fmt -recursive
git add .
git commit --amend
```

**Plan failed**:
```bash
cd terraform
terraform init -backend=false
terraform plan -var-file=environments/dev/terraform.tfvars
# Fix issues and commit
```

## Cost Optimization

**GitHub Actions**:
- Free for public repos
- 2000 minutes/month for private repos (Free Tier)
- Current usage: ~5 minutes per PR

**Terraform State**:
- S3: $0/month (Free Tier)
- DynamoDB: $0/month (Free Tier, pay-per-request)

**Total CI/CD Cost**: **$0/month**
