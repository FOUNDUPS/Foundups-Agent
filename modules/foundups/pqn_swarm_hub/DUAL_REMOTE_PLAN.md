# Dual-Remote Plan - PQN Swarm Hub

**Status**: Phase 3 Prep (ready for 012 approval)
**Created**: 2026-03-29
**Slice**: `pqn_swarm_hub_phase3_prep_scaffold`

---

## Repository Configuration

### Origin (Org Repo)

| Property | Value |
|----------|-------|
| Name | `FOUNDUPS/pqn-swarm-hub` |
| Visibility | public |
| Purpose | Primary development, PRs, releases |
| Remote name | `origin` |

### Backup (Personal Repo)

| Property | Value |
|----------|-------|
| Name | `Foundup/pqn-swarm-hub` |
| Visibility | private |
| Purpose | Mirror, disaster recovery |
| Remote name | `backup` |

---

## Creation Commands (Blocked on 012 Approval)

### Step 1: Create Repositories

```bash
# Origin (org repo) - PUBLIC
gh repo create FOUNDUPS/pqn-swarm-hub \
    --public \
    --description "PQN Swarm Hub FoundUp - Work registry, verification, contribution measurement" \
    --clone=false

# Backup (personal repo) - PRIVATE
gh repo create Foundup/pqn-swarm-hub \
    --private \
    --description "PQN Swarm Hub FoundUp - Backup mirror" \
    --clone=false
```

### Step 2: Initialize Local Clone

```bash
# Create fresh directory
mkdir -p ~/repos/pqn-swarm-hub
cd ~/repos/pqn-swarm-hub
git init

# Add both remotes
git remote add origin https://github.com/FOUNDUPS/pqn-swarm-hub.git
git remote add backup https://github.com/Foundup/pqn-swarm-hub.git
```

### Step 3: Copy Files Per Manifest

```bash
# From monorepo
SOURCE="O:/Foundups-Agent/modules/foundups/pqn_swarm_hub"

# Copy documentation
cp $SOURCE/README.md .
cp $SOURCE/INTERFACE.md .
cp $SOURCE/ROADMAP.md .
cp $SOURCE/ModLog.md .
cp $SOURCE/CONTRIBUTING.md .
cp $SOURCE/RUNBOOK.md .
cp $SOURCE/requirements.txt .

# Copy source (restructure for package)
mkdir -p src/pqn_swarm_hub
cp $SOURCE/src/*.py src/pqn_swarm_hub/
cp $SOURCE/__init__.py src/pqn_swarm_hub/

# Copy tests
mkdir -p tests
cp $SOURCE/tests/*.py tests/
cp $SOURCE/tests/*.md tests/
```

### Step 4: Create Package Files

```bash
# pyproject.toml (modern packaging)
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pqn-swarm-hub"
version = "0.11.0"
description = "PQN Swarm Hub FoundUp - Work registry, verification, contribution measurement"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
dependencies = [
    "dataclasses-json>=0.6.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=1.3.0",
]

[tool.setuptools.packages.find]
where = ["src"]
EOF
```

### Step 5: Initial Commit and Push

```bash
# Stage all
git add .

# Initial commit
git commit -m "feat: initialize pqn-swarm-hub standalone repo

Migrated from modules/foundups/pqn_swarm_hub in Foundups-Agent monorepo.

Phase 2 complete:
- 108 tests passing
- All exfoliation blockers cleared
- Architect decision: APPROVE_PHASE_3_PREP

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"

# Push to both remotes
git push -u origin main
git push backup main
```

---

## Sync Strategy

### Daily Development

```bash
# Push to origin (primary)
git push origin main

# Sync to backup
git push backup main
```

### Git Aliases (Optional)

```bash
# Add to ~/.gitconfig
git config --global alias.sync-pqn '!git push origin main && git push backup main'
```

---

## Branch Protection (Post-Creation)

### Origin (FOUNDUPS/pqn-swarm-hub)

```bash
# Require PR reviews
gh api repos/FOUNDUPS/pqn-swarm-hub/branches/main/protection \
    -X PUT \
    -F required_pull_request_reviews='{"required_approving_review_count":1}'
```

### Backup (Foundup/pqn-swarm-hub)

No branch protection (mirror only).

---

## CI/CD Setup (Post-Migration)

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e .[test]
      - run: pytest tests/ -v
```

---

## Verification Checklist

### Pre-Push Verification

```bash
# Run tests in standalone
cd ~/repos/pqn-swarm-hub
pip install -e .[test]
pytest tests/ -v

# Expected: 108 passed
```

### Post-Push Verification

- [ ] `FOUNDUPS/pqn-swarm-hub` accessible
- [ ] `Foundup/pqn-swarm-hub` accessible
- [ ] README renders correctly
- [ ] CI workflow passes (if configured)

---

## Rollback Plan

If migration fails:

1. Delete external repos (if created)
2. Monorepo module remains intact
3. Resume internal development

---

## Approval Gate

**This plan requires explicit 012 approval before execution.**

| Action | Status |
|--------|--------|
| Plan documented | COMPLETE |
| 012 approval | PENDING |
| Repo creation | BLOCKED |
| Migration push | BLOCKED |

---

*Created: 2026-03-29*
