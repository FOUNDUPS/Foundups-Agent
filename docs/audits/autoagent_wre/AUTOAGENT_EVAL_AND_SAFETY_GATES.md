# AutoAgent Eval and Safety Gates

Worker: AD
Date: 2026-04-07
Parent: AUTOAGENT_WRE_INTEGRATION_SPEC.md

## 1. Evaluation Method: Deterministic Pytest Harness

Phase 1 uses a local pytest-based eval harness. No external services,
no stochastic LLM-as-judge, no Docker, no Harbor.

### Why Pytest

| Factor | Verdict |
|--------|---------|
| Already in repo | pytest.ini configured, conftest.py in place, 3 benchmark suites exist |
| Deterministic | Same input = same score (no LLM variance) |
| Fast | Runs in seconds, not minutes |
| Familiar | Every contributor knows pytest |
| Composable | Eval functions are regular Python — mix skill-specific and generic checks |

### Eval Function Contract

```python
def eval_skill_config(skill_path: Path, context: dict) -> float:
    """Evaluate a skill config and return a score.

    Args:
        skill_path: Path to the SKILL.md file (in experiment workspace)
        context: Dict with historical PatternMemory data

    Returns:
        Score between 0.0 and 1.0 where:
        - 0.0 = completely broken / invalid
        - 0.5 = baseline (no improvement)
        - 1.0 = perfect fidelity + quality
    """
```

### Score Components

| Component | Weight | Source | Description |
|-----------|--------|--------|-------------|
| Config validity | 0.2 | YAML parse + field validation | Is the config syntactically valid? |
| WSP compliance | 0.2 | WSP chain verification | Are cited WSPs real and applicable? |
| Historical fidelity | 0.3 | PatternMemory query | Average pattern_fidelity from past executions |
| Historical quality | 0.3 | PatternMemory query | Average outcome_quality from past executions |

The weighted score is the hill-climbing target. A change that improves the
composite score is kept; one that regresses is discarded.

### Baseline Measurement

Before any mutation, the eval harness runs against the unmodified config
to establish a baseline score. All improvement is measured relative to this baseline.

```
baseline_score = eval_skill_config(original_config, context)
# e.g., 0.72

# After mutation:
new_score = eval_skill_config(mutated_config, context)
# e.g., 0.78

improvement = new_score - baseline_score  # +0.06
# Decision: KEEP (improvement > 0)
```

## 2. Safety Gates

Six safety gates. All are fail-closed — if any gate cannot be evaluated,
the experiment halts.

### Gate 1: Score Regression Rejection

```
IF new_score < baseline_score:
    DISCARD change
    RECORD: "regression", delta, diff
```

No exceptions. Score regression = automatic discard.
This is the core AutoAgent discipline.

### Gate 2: File Allowlist

The experiment harness maintains a strict allowlist of files it can modify.
Any write attempt outside the allowlist is blocked at the code level.

```python
WRITE_ALLOWLIST = [
    "modules/infrastructure/autoagent_lab/workspace/**",
    "modules/infrastructure/autoagent_lab/logs/**",
]

# Enforced by target_surface.py — raises SafetyViolation on breach
```

### Gate 3: Iteration Budget

Each experiment has a maximum iteration count. When exhausted, the experiment
stops regardless of score trajectory.

```python
MAX_ITERATIONS = int(os.environ.get("AUTOAGENT_MAX_ITERATIONS", "10"))
```

This prevents runaway loops. The operator sets the budget before launch.

### Gate 4: Branch Isolation

Every experiment runs in its own git branch (or isolated workspace directory).
Production files are never modified in-place.

```
Experiment lifecycle:
1. Copy target to workspace/
2. Run all mutations against the copy
3. Best result saved as diff artifact
4. Operator reviews diff
5. Operator applies to production (or doesn't)
```

No automatic merge to main. The diff artifact is the deliverable.

### Gate 5: Diff Review Artifact

Every experiment produces a human-readable diff artifact:

```
logs/exp_001/
├── experiment_spec.yaml       # What was being optimized
├── baseline_score.json        # Starting score
├── iterations.jsonl           # Per-iteration: score, decision, timestamp
├── best_diff.patch            # Git-format diff of best improvement
├── final_score.json           # Ending score
└── summary.md                 # Human-readable summary
```

The operator reads `summary.md` and `best_diff.patch` to decide whether
to apply the improvement. The lab never applies it automatically.

### Gate 6: Hard Rollback

If an experiment corrupts its workspace, the fix is trivial:

```bash
rm -rf modules/infrastructure/autoagent_lab/workspace/exp_001/
```

The workspace is ephemeral. Production files are untouched.
Git history provides additional rollback for any file that was
accidentally modified outside the workspace (which Gate 2 prevents).

## 3. What Happens When a Gate Fails

| Gate | Failure Mode | Response |
|------|-------------|----------|
| Score regression | new_score < baseline | Discard change, log regression |
| File allowlist | Write outside allowlist | Raise SafetyViolation, halt experiment |
| Iteration budget | Budget exhausted | Stop experiment, produce summary |
| Branch isolation | Workspace corruption | Delete workspace, no production impact |
| Diff artifact | Artifact write failure | Halt experiment (can't record = can't review) |
| Hard rollback | N/A | Always available via workspace deletion |

All gates are independent. Failure of one does not disable the others.

## 4. What Is Explicitly Not Gated (Future)

These safety mechanisms are NOT in Phase 1 but are noted for future phases:

| Future Gate | Phase | Description |
|-------------|-------|-------------|
| Execution sandbox | Phase 2 | Run mutated configs in subprocess with resource limits |
| Multi-run statistical significance | Phase 2 | Require N>1 eval runs for confidence |
| Automated deployment | Phase 3+ | Auto-merge improvements (requires SOURCE tier) |
| Cross-skill impact analysis | Phase 3+ | Check if skill A improvement degrades skill B |
| LLM-as-judge eval | Phase 3+ | Add Gemma validation as eval component |

## 5. Monitoring and Observability

The experiment harness logs structured events for WSP 91 compliance:

```python
# Event types
EXPERIMENT_STARTED = "autoagent.experiment.started"
ITERATION_COMPLETE = "autoagent.iteration.complete"
SCORE_IMPROVED = "autoagent.score.improved"
SCORE_REGRESSED = "autoagent.score.regressed"
SAFETY_VIOLATION = "autoagent.safety.violation"
EXPERIMENT_COMPLETE = "autoagent.experiment.complete"
```

All events include: experiment_id, timestamp, iteration, score, decision.
