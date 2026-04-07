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

## WSP Compliance

- WSP 49: Standard module structure
- WSP 72: Module independence (no WRE coupling)
- WSP 91: Observability (structured logging)
- WSP 97: Internal boundaries (reads WRE, never writes production)
