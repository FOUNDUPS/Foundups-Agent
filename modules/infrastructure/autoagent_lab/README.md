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
