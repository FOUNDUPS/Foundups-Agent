# OpenClaw Training Route Status

**Audit Date**: 2026-04-03
**Worker**: G
**PR Reference**: #250 (OPEN)

---

## Current State

### What Exists (in PR #250 branch)

| Component | Location | Status |
|-----------|----------|--------|
| `training_adapter.py` | `moltbot_bridge/src/` | PR OPEN |
| `execute_training()` | `openclaw_execution_routes.py:711` | MERGED (main) |
| Tests | `test_training_adapter.py` | 35 tests in PR |

### Route Type

**CLI-only / Internal DAE**

The training route is accessible via:
1. OpenClaw text interface (CLI/chat)
2. Internal DAE message routing

**NOT browser-callable.** No HTTP API exposed.

---

## API Surface

### Commands Exposed

| Command Pattern | Function | Auth Required |
|-----------------|----------|---------------|
| `training status` | Show checkpoint, progress, due status | 012 only |
| `training progress` | Same as status | 012 only |
| `show training metrics` | Same as status | 012 only |
| `start training batch` | Trigger batch execution | 012 only |
| `run training batch` | Same as start | 012 only |
| `is training due` | Boolean check | 012 only |

### Response Format

```python
# Status response:
{
    "checkpoint_line": int,
    "corpus_lines": int,
    "progress_pct": float,
    "training_due": bool,
    "exists": bool,
    "age_hours": float
}

# Batch response:
"**Training Batch: STARTED|COMPLETE|FAILED|ERROR**"
```

---

## Auth/Permission Model

### Current

```python
if not intent.is_authorized_commander:
    return "Training commands require @012 authorization. Your request has been logged."
```

**Only 012 (the operator) can execute training commands.**

### Red Dog Implication

Red Dog cannot access training routes under current auth model.
Training is a system-level operation, not a user-facing capability.

---

## Integration Path to Red Dog

### NOT RECOMMENDED

Training commands are:
- 012-only operations
- Backend infrastructure concerns
- Not relevant to user-facing Red Dog capabilities

### If Needed Later

The smallest safe path would be:
1. Expose read-only status endpoint (no `start` command)
2. Add permission tier check (EMPOWERED state only)
3. Rate limit queries (1/minute max)

---

## Test Coverage

PR #250 includes 35 tests:
- 6 status command variants
- 5 batch command variants
- 4 due command variants
- 6 non-training command rejection tests
- 5 false-positive rejection tests
- 4 status state tests
- 4 batch outcome tests
- 1 async integration test

---

## Gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| No HTTP API | LOW | Not needed for Red Dog |
| 012-only auth | LOW | Correct for training ops |
| PR not merged | MEDIUM | Blocks any integration |
| No browser surface | N/A | Not a Red Dog concern |

---

## Summary

**Training route is real but not Red Dog relevant.**

The training system is infrastructure-level, 012-only operation.
Red Dog's compute-feeding and state machine do not require training access.
Defer from Red Dog integration scope.

---

*Worker G - 2026-04-03*
