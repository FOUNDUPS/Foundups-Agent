# AutoAgent Lab

Isolated experiment harness for WRE skill optimization.

Adopts the AutoAgent pattern (iterate, eval, keep/discard) but targets WRE
skill configs — not arbitrary code. Production WRE is read-only to this module.

## Quick Start

```bash
# Enable the lab
export AUTOAGENT_LAB_ENABLED=true

# Copy and edit the experiment spec
cp config/experiment_spec_template.yaml my_experiment.yaml
# Edit my_experiment.yaml with your target skill

# Run (Layer 4+)
python -m modules.infrastructure.autoagent_lab.src.cli run --spec my_experiment.yaml
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTOAGENT_LAB_ENABLED` | NO | `false` | Master switch |
| `AUTOAGENT_MAX_ITERATIONS` | NO | `10` | Max iterations per experiment |

## What This Does

- Loads experiment specs from YAML
- Enforces safety gates (file allowlist, iteration budget, workspace isolation)
- Validates configs before any mutation
- **Scores skill configs** (0.0-1.0) using deterministic eval harness

## Quick Score (Layer 2)

```python
from modules.infrastructure.autoagent_lab.src.eval_harness import eval_skill_config

result = eval_skill_config(
    "path/to/SKILL.md",
    context={"historical_fidelity": 0.85, "historical_quality": 0.80},
)
print(f"Score: {result.total_score:.2f}")
print(f"Reasons: {result.reasons}")
```

Score components:
- `config_validity` (0.2) — YAML valid, required fields present
- `wsp_compliance` (0.2) — WSP refs are valid numbers (1-200)
- `historical_fidelity` (0.3) — From context (PatternMemory adapter future)
- `historical_quality` (0.3) — From context (PatternMemory adapter future)

## Target Surface IO (Layer 3)

```python
from modules.infrastructure.autoagent_lab.src.target_surface import (
    load_skill_surface,
    create_workspace_copy,
    write_candidate_surface,
)

# Load production skill (read-only)
surface = load_skill_surface("path/to/SKILL.md")

# Create isolated workspace copy
surface = create_workspace_copy(surface)

# Write candidate with updated mutable fields
candidate = write_candidate_surface(
    surface,
    {"agents": ["haiku"], "tokens_budget": 1000},
)
```

Mutable fields: `agents`, `wsp_chain`, `domains`, `tokens_budget`, `prompt`
Immutable fields: `name`, `version`, `description`, etc. (preserved exactly)

## What This Does NOT Do

- No production WRE mutation
- No OpenClaw DAE mutation
- No source code editing
- No unbenchmarked changes
- No automatic deployment

## Architecture

- **Module**: `modules/infrastructure/autoagent_lab/`
- **Position**: Adjacent to WRE (reads WRE data, never writes production)
- **Safety**: 4 fail-closed gates (score regression, file allowlist, budget, workspace isolation)

## Related Specs

- `docs/audits/autoagent_wre/AUTOAGENT_WRE_INTEGRATION_SPEC.md`
- `docs/audits/autoagent_wre/AUTOAGENT_BUILD_ORDER.md`
