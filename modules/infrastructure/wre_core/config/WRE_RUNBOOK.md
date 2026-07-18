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
| WRE_CODEACT_STRICT | 1 | Enforce strict CodeAct shell safety policy |
| WRE_SKILL_SCAN_REQUIRED | 1 | Require WRE per-skill scan gate before execute |
| WRE_SKILL_SCAN_ENFORCED | 1 | Block WRE execution when scan gate fails |
| WRE_SKILL_SCAN_ALWAYS | 0 | Re-scan every execution instead of TTL cache |
| WRE_SKILL_SCAN_TTL_SEC | 900 | Scan result cache TTL for WRE skill gate |
| WRE_SKILL_SCAN_MAX_SEVERITY | medium | Max allowed skill scan severity |
| OPENCLAW_DEP_SECURITY_PREFLIGHT | 1 | Enable startup dependency/CVE preflight |
| OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED | 0 | Block startup on dependency/CVE policy violations |
| OPENCLAW_DEP_SECURITY_PREFLIGHT_TTL_SEC | 21600 | Dependency preflight cache TTL (seconds) |
| OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS | 0 | Require pip-audit/npm/cargo-audit tool availability |
| OPENCLAW_DEP_SECURITY_MAX_CRITICAL | 0 | Max allowed critical CVEs before FAIL |
| OPENCLAW_DEP_SECURITY_MAX_HIGH | 0 | Max allowed high CVEs before FAIL |
| OPENCLAW_DEP_SECURITY_MAX_UNKNOWN | 0 | Max allowed unknown-severity findings before FAIL |
| OPENCLAW_DEP_SECURITY_CHECK_NODE | 1 | Enable Node lockfile CVE checks |
| OPENCLAW_DEP_SECURITY_NODE_LOCK_SCOPE | all | Node lockfile coverage (`all` or `root`) |
| OPENCLAW_DEP_SECURITY_CHECK_RUST | 1 | Enable Rust CVE checks when Cargo.lock exists |
| OPENCLAW_SELF_AUDIT_ENABLED | 1 | Start 0102 daemon self-audit loop at startup |
| OPENCLAW_SELF_AUDIT_RUNTIME_ROOT | (outside repo default) | External root for redacted self-audit receipts, state, and diagnostics |
| OPENCLAW_SELF_AUDIT_AUTO_FIX | 1 | Enable policy-bound automatic remediations |
| OPENCLAW_SELF_AUDIT_ALLOWED_FIXES | start_ironclaw_gateway,diagnose_microphone_device,verify_dae_event_store | Allowlisted auto-fix handlers |
| OPENCLAW_SELF_AUDIT_ALLOW_SHELL_START_CMD | 0 | Keep startup command dispatch on `shell=False` by default |
| OPENCLAW_SELF_AUDIT_TELEMETRY | 1 | Emit self-audit counters into PatternMemory |
| OPENCLAW_SELF_AUDIT_ESCALATE_AFTER | 3 | Escalate after repeated matching failures |
| OPENCLAW_SELF_AUDIT_ESCALATION_WINDOW_SEC | 900 | Rolling window for repeated-failure escalation |
| OPENCLAW_SELF_AUDIT_ESCALATION_COOLDOWN_SEC | 600 | Cooldown between escalations per signature |
| OPENCLAW_SELF_AUDIT_ESCALATE_CMD | (empty) | Optional command dispatched on escalation |
| OPENCLAW_SELF_AUDIT_ESCALATE_ALLOW_SHELL_CMD | 0 | Keep escalation command on `shell=False` by default |

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
