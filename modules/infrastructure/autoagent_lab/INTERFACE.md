# AutoAgent Lab — Interface

## Configuration

```python
from modules.infrastructure.autoagent_lab.src.experiment_config import (
    ExperimentSpec,
    load_experiment_spec,
    is_lab_enabled,
)

# Check master switch
if not is_lab_enabled():
    print("Lab disabled")

# Load and validate spec
spec = load_experiment_spec("path/to/spec.yaml")
print(spec.name, spec.target.skill_path, spec.budget.max_iterations)
```

## ExperimentSpec

```python
@dataclass
class ExperimentSpec:
    name: str              # Human-readable experiment name
    target: TargetSpec     # What to optimize
    eval: EvalSpec         # How to score
    budget: BudgetSpec     # Iteration limits
    log_level: str         # Logging level
```

## Safety Gates

```python
from modules.infrastructure.autoagent_lab.src.safety_gates import (
    check_score_regression,
    FileAllowlist,
    IterationBudget,
    validate_workspace_path,
    SafetyViolation,
)

# Score gate
decision = check_score_regression(baseline=0.72, candidate=0.78)
assert decision.keep is True

# File allowlist
allowlist = FileAllowlist()
allowlist.enforce_write("modules/infrastructure/autoagent_lab/workspace/exp_001/SKILL.md")

# Iteration budget
budget = IterationBudget(max_iterations=10)
budget.consume()  # OK
assert budget.remaining == 9

# Workspace isolation
validate_workspace_path(
    workspace_dir=Path("modules/infrastructure/autoagent_lab/workspace"),
    target_path=Path("modules/infrastructure/autoagent_lab/workspace/exp_001/file.yaml"),
)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTOAGENT_LAB_ENABLED` | `false` | Master switch |
| `AUTOAGENT_MAX_ITERATIONS` | `10` | Default iteration budget |

## Evaluation Harness (Layer 2)

```python
from modules.infrastructure.autoagent_lab.src.eval_harness import (
    EvalResult,
    eval_skill_config,
    quick_score,
    validate_weights,
    WEIGHTS,
)

# Evaluate a skill config
result = eval_skill_config(
    skill_path="path/to/SKILL.md",
    context={
        "historical_fidelity": 0.85,  # From PatternMemory
        "historical_quality": 0.80,   # From PatternMemory
    },
)
print(result.total_score)  # 0.0-1.0

# Quick score (just the total)
score = quick_score("path/to/SKILL.md")

# Custom weights
custom_weights = {
    "config_validity": 0.1,
    "wsp_compliance": 0.1,
    "historical_fidelity": 0.4,
    "historical_quality": 0.4,
}
errors = validate_weights(custom_weights)  # [] if valid
result = eval_skill_config(path, context, weights=custom_weights)
```

### EvalResult

```python
@dataclass
class EvalResult:
    total_score: float           # Weighted composite (0.0-1.0)
    config_validity: float       # YAML parse + required fields
    wsp_compliance: float        # WSP refs valid/plausible
    historical_fidelity: float   # From context (PatternMemory adapter future)
    historical_quality: float    # From context (PatternMemory adapter future)
    reasons: list[str]           # Human-readable scoring reasons
```

### Score Weights

| Component | Weight | Description |
|-----------|--------|-------------|
| config_validity | 0.2 | YAML frontmatter valid, required fields present |
| wsp_compliance | 0.2 | WSP references are structurally valid (1-200) |
| historical_fidelity | 0.3 | From context dict (default 0.5 if missing) |
| historical_quality | 0.3 | From context dict (default 0.5 if missing) |

### Context Pattern (Phase 2)

Historical scores are passed via `context` dict, not read directly from PatternMemory.
This keeps the eval harness pure and testable. Production PatternMemory adapter is future work.

```python
# Future: PatternMemory adapter will provide context
context = pattern_memory_adapter.get_context("skill_name")
result = eval_skill_config(path, context)
```

## WSP Compliance

- WSP 49: Standard module structure
- WSP 72: Module independence (no WRE coupling)
- WSP 91: Observability (structured logging)
- WSP 97: Internal boundaries (reads WRE, never writes production)
