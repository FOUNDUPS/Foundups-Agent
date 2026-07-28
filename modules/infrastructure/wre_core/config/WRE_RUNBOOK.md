# WRE CoT System - Operations Runbook

## Quick Start

1. Ensure Python 3.10+ installed
2. Load environment defaults:
   ```bash
   source modules/infrastructure/wre_core/config/wre_defaults.env
   ```

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| WRE_REACT_MODE | 1 | Enable ReAct retry loop (max 3 iterations) |
| WRE_REACT_MAX_ITER | 3 | Maximum ReAct retry iterations |
| WRE_REACT_FIDELITY | 0.90 | Fidelity threshold for success |
| WRE_AGENTIC_RAG | 1 | Enable HoloIndex retrieval preflight |
| WRE_TOT_SELECTION | 1 | Enable Tree-of-Thought skill selection |
| WRE_TOT_MAX_BRANCHES | 5 | Maximum ToT candidates to evaluate |
| WRE_CODEACT_ENABLED | 1 | Enable hybrid CodeAct execution |

## Disabling Features

To disable a feature, set its flag to 0:
```bash
export WRE_REACT_MODE=0  # Disable ReAct
export WRE_TOT_SELECTION=0  # Disable ToT
```

## Monitoring

Dashboard endpoint:
```python
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
memory = PatternMemory()
dashboard = memory.get_telemetry_dashboard()
print(dashboard)
```

Key metrics:
- `tot_confidence_rate`: Should be >70% for healthy ToT
- `codeact_success_rate`: Should be >90% for healthy CodeAct
- `retrieval_coverage`: Should be >80% for healthy RAG

## Troubleshooting

### Low fidelity scores
1. Check ReAct is enabled: `WRE_REACT_MODE=1`
2. Verify RAG retrieval: `WRE_AGENTIC_RAG=1`
3. Check skill variations: `dashboard['variations_promoted']`

### CodeAct failures
1. Check safety gates in skill spec
2. Verify allowed_commands includes required commands
3. Check `codeact_gate_triggers` counter

### ToT poor selection
1. Verify sufficient execution history (need 5+ per skill)
2. Check `tot_confidence_rate` in dashboard
3. Consider increasing `WRE_TOT_MAX_BRANCHES`
