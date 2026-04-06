# Science Swarm Hub — GitHub-Canonical Workflow

**Worker**: J
**Date**: 2026-04-06
**Slice**: `SCIENCE_SWARM_FOUNDUPS_SERVER_EMBED_SPEC_PHASE1`
**Parent**: `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`

---

## 1. Canonical Rule

**GitHub is the action surface. Discord is coordination only.**

| Action | Where |
|--------|-------|
| Code changes | GitHub PRs |
| Bug reports | GitHub Issues |
| Feature requests | GitHub Issues |
| Work unit creation | Python API (`pqn_swarm_hub`) |
| Result submission | Python API (`pqn_swarm_hub`) |
| Verification decisions | Python API or GitHub review |
| Release announcements | GitHub Releases |
| Discussion | Discord `#swarm-general` |
| Work visibility | Discord `#swarm-work` |

---

## 2. Repository

| Field | Value |
|-------|-------|
| **Org** | `FOUNDUPS` |
| **Repo** | `science-swarm-hub` |
| **URL** | `github.com/FOUNDUPS/science-swarm-hub` |
| **Package** | `pqn_swarm_hub` |
| **Version** | v0.12.0 |
| **License** | MIT |

---

## 3. Contributor Flow

### Step 1: Find Work

```
GitHub Issues → filter by "good first issue" label
  or
docs/seed_issues/ → browse starter tasks
  or
#swarm-work on Discord → see what others are working on
```

### Step 2: Claim Work

1. Comment on the GitHub Issue: "I'm working on this"
2. Post in `#swarm-work`: "Working on [issue link]"
3. This prevents duplicate effort

### Step 3: Do Work

```bash
# Clone
git clone https://github.com/FOUNDUPS/science-swarm-hub.git
cd science-swarm-hub

# Install
pip install -e .

# Create branch
git checkout -b fix/issue-42

# Make changes, run tests
pytest tests/ -v
```

### Step 4: Submit PR

1. Push branch to your fork (or directly if you have write access)
2. Open Pull Request against `main`
3. Reference the issue: "Fixes #42"
4. Wait for review

### Step 5: Review & Merge

- Maintainers review PRs
- CI must pass (tests, linting if configured)
- Once approved, maintainer merges
- GitHub webhook posts to `#swarm-github` (when configured)

---

## 4. Work Unit Flow (Python API)

For PQN research contributions (not code PRs):

### External Contributor Path

```python
from pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ParticipantGate,
    ParticipantIdentity,
)

# 1. Declare identity
identity = ParticipantIdentity(
    display_name="your_name",
    model_type="human",  # or "claude-opus-4-5", etc.
)

# 2. Request entry
gate = ParticipantGate()
gate.request_entry(identity)

# 3. Register work unit
registry = WorkUnitRegistry()
work_unit = registry.register_external(
    description="Your research description",
    config={"method": "your_method"},
    creator_id=identity.participant_id,
)

# 4. Submit results
sink = SubmissionSink(registry)
submission = sink.submit_external(
    work_unit_id=work_unit.work_unit_id,
    submitter_id=identity.participant_id,
    metrics={"coherence": 0.75},
)

# 5. Verification (auto if coherence >= 0.618)
engine = VerificationEngine(sink)
decision = engine.auto_verify(submission.submission_id)
```

### Reference

Full details: `CONTRIBUTING.md` in the repo.

---

## 5. Release Flow

1. Maintainer updates version in `pyproject.toml`
2. Maintainer creates GitHub Release with tag
3. Release notes document changes
4. GitHub webhook posts to `#swarm-github` (when configured)
5. No PyPI publish yet — install from source

---

## 6. Issue Labels

| Label | Meaning |
|-------|---------|
| `good first issue` | Suitable for new contributors |
| `bug` | Something isn't working |
| `enhancement` | New feature or improvement |
| `documentation` | Docs-only change |
| `research` | PQN research task |
| `verification` | Verification methodology |

---

## 7. Discord-GitHub Boundary

### What happens on Discord

- "I'm starting work on X" → `#swarm-work`
- "Question about Y" → `#swarm-general`
- "Anyone want to pair on Z?" → `#swarm-general`
- Webhook notifications → `#swarm-github`

### What does NOT happen on Discord

- Code review
- PR approval
- Issue creation/closing
- Release publishing
- Result submission
- Verification decisions

**If someone tries to submit results in Discord**: Direct them to the Python API and `CONTRIBUTING.md`.

---

## 8. Sync Expectations

| Event | GitHub → Discord |
|-------|-----------------|
| Issue opened | Webhook posts to `#swarm-github` |
| Issue closed | Webhook posts to `#swarm-github` |
| PR opened | Webhook posts to `#swarm-github` |
| PR merged | Webhook posts to `#swarm-github` |
| Release published | Webhook posts to `#swarm-github` |

| Event | Discord → GitHub |
|-------|-----------------|
| Discussion | Manual — contributor opens issue if needed |
| Question | Manual — contributor opens issue if recurring |
| Work claim | Manual — contributor comments on issue |

**No bidirectional automation.** Discord reads from GitHub (via webhook). GitHub does not read from Discord.

---

## 9. Non-Claims

- No GitHub-Discord bot exists
- No automated issue creation from Discord
- No automated PR creation from Discord
- No automated verification from Discord commands
- Webhook is one-way (GitHub → Discord), not bidirectional

See: `FOUNDUPS_SCIENCE_SWARM_NONCLAIMS.md` for full list.

---

*This document defines the GitHub-canonical workflow for Science Swarm. Discord is coordination only.*
