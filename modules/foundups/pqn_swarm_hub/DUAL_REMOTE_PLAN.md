# Dual-Remote Plan - PQN Swarm Hub

**Status**: Phase 3 COMPLETE — Repos Live (2026-03-30)
**Created**: 2026-03-29
**Executed**: 2026-03-30
**Slice**: `pqn_swarm_hub_phase3_migration_exec`

---

## Repository Configuration (LIVE)

### Origin (Org Repo)

| Property | Value | Status |
|----------|-------|--------|
| Name | `FOUNDUPS/science-swarm-hub` | **LIVE** |
| Visibility | public | CONFIGURED |
| Purpose | Primary development, PRs, releases | OPERATIONAL |
| Remote name | `origin` | SET |
| URL | https://github.com/FOUNDUPS/science-swarm-hub | ACCESSIBLE |

### Backup (Personal Repo)

| Property | Value | Status |
|----------|-------|--------|
| Name | `Foundup/science-swarm-hub` | **LIVE** |
| Visibility | private | CONFIGURED |
| Purpose | Mirror, disaster recovery | OPERATIONAL |
| Remote name | `backup` | SET |
| URL | https://github.com/Foundup/science-swarm-hub | ACCESSIBLE |

---

## Creation Commands (EXECUTED)

### Step 1: Create Repositories (DONE)

```bash
# Origin (org repo) - PUBLIC
gh repo create FOUNDUPS/science-swarm-hub \
    --public \
    --description "PQN Swarm Hub FoundUp - Work registry, verification, contribution measurement" \
    --clone=false
# STATUS: EXECUTED

# Backup (personal repo) - PRIVATE
gh repo create Foundup/science-swarm-hub \
    --private \
    --description "PQN Swarm Hub FoundUp - Backup mirror" \
    --clone=false
# STATUS: EXECUTED
```

### Step 2: Initialize Local Clone (DONE)

```bash
# Create fresh directory
mkdir -p ~/repos/science-swarm-hub
cd ~/repos/science-swarm-hub
git init

# Add both remotes
git remote add origin https://github.com/FOUNDUPS/science-swarm-hub.git
git remote add backup https://github.com/Foundup/science-swarm-hub.git
# STATUS: EXECUTED
```

### Step 3: Copy Files Per Manifest (DONE)

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
# STATUS: EXECUTED
```

### Step 4: Create Package Files (DONE)

```bash
# pyproject.toml (modern packaging)
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "science-swarm-hub"
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
# STATUS: EXECUTED
```

### Step 5: Initial Commit and Push (DONE)

```bash
# Stage all
git add .

# Initial commit
git commit -m "feat: initialize science-swarm-hub standalone repo

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
# STATUS: EXECUTED
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

### Origin (FOUNDUPS/science-swarm-hub)

```bash
# Require PR reviews
gh api repos/FOUNDUPS/science-swarm-hub/branches/main/protection \
    -X PUT \
    -F required_pull_request_reviews='{"required_approving_review_count":1}'
```

### Backup (Foundup/science-swarm-hub)

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

## Verification Checklist (COMPLETE)

### Pre-Push Verification (DONE)

```bash
# Run tests in standalone
cd ~/repos/science-swarm-hub
pip install -e .[test]
pytest tests/ -v

# Result: 108 passed
```

### Post-Push Verification (DONE)

- [x] `FOUNDUPS/science-swarm-hub` accessible
- [x] `Foundup/science-swarm-hub` accessible
- [x] README renders correctly
- [x] Tests pass in standalone (108/108)

---

## Rollback Plan

If migration had failed:

1. Delete external repos (if created)
2. Monorepo module remains intact
3. Resume internal development

**Not needed** — migration succeeded.

---

## Approval Gates (ALL CLEARED)

| Action | Status |
|--------|--------|
| Plan documented | COMPLETE |
| 012 approval | APPROVED |
| Repo creation | COMPLETE |
| Migration push | COMPLETE |

---

*Created: 2026-03-29*
*Last Updated: 2026-03-30 (migration executed — both repos live)*
