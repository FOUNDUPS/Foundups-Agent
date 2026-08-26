# WRE Master Orchestrator

**Status:** compatibility orchestrator with WSP 95 admitted Skillz execution;
production RSI is incomplete.

The master orchestrator coordinates registered Skillz, bounded ReAct retries,
a blocked legacy plugin registry, and PatternMemory observations. It is not a
repository, Git, network, HoloIndex, worker-dispatch, evaluation, or production-
promotion authority.

## Current execution boundary

- `execute_skill()` admits a production Skillz bundle only after registry,
  frontmatter, hygiene, exact bundle fingerprint, adjacent manifest, and Cisco
  scanner checks pass.
- Dispatch compiles the captured adjacent executor bytes only while their
  fingerprint still matches the admission receipt.
- Success requires an exact built-in Boolean plus typed effect receipts.
- Local model output is proposal-only and never proves an effect.
- ReAct retries preserve execution success separately from structural fidelity.
- Generic A/B activation, automatic promotion, CodeAct, and direct legacy Holo
  retrieval are fail closed.
- Loader or scanner failure blocks execution. No fallback instruction is
  generated or treated as executed work.

See the root [WRE interface](../INTERFACE.md) and
[WSP 95](../../../../WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md)
for the authoritative admission and result contracts.

## Compatibility surface

The module retains:

- `register_plugin()` and `get_plugin()` for in-process compatibility plugins;
- `validate_module_path()` for exact-checkout directory containment;
- `execute()` gates then blocks legacy plugins pending WSP 95 admission;
- `select_skill_tot()` and `find_skill_candidates()` for candidate selection;
- `execute_skill()` and `execute_skill_with_reasoning()` for admitted Skillz;
- `evolve_skill()` for non-production proposal storage;
- `get_skill_statistics()` and `get_metrics()` for observed records.

`execute_codeact_skill()` is retained only as a blocked compatibility API.

## Metrics truth

The orchestrator reports observed counters and structural/outcome records. It
does not synthesize token usage or reduction. `get_metrics()` returns
`token_reduction_measured: false` until authenticated provider/runtime receipts
and a defined comparison baseline exist. Configured pattern token values are
budget hints, not usage measurements.

## Example

```python
from modules.infrastructure.wre_core.wre_master_orchestrator import (
    WREMasterOrchestrator,
)

master = WREMasterOrchestrator()
result = master.execute_skill(
    skill_name="auto_test_registry_audit",
    agent="qwen",
    input_context={"scope": "registered-tests"},
)
```

Callers must inspect `success`, `_effect_evidence`, typed receipts, and any
`blocked_by` value. A returned dictionary alone is not proof of execution.

## Configuration

- `WRE_PATTERN_MEMORY_DB`: explicit PatternMemory database path.
- `WRE_REACT_MODE`, `WRE_REACT_MAX_ITER`, `WRE_REACT_FIDELITY`: bounded ReAct.
- `WRE_SKILL_SCAN_REQUIRED=1` and `WRE_SKILL_SCAN_ENFORCED=1`: mandatory
  production scanner gates.
- `WRE_AGENTIC_RAG`: legacy flag; enabling it remains blocked.
- `WRE_CODEACT_ENABLED`: legacy flag; CodeAct remains blocked.

Tests must isolate temporary paths and both WRE database variables under the
documented `O:\pytest_tmp\reddog_wre_truth` boundary.

## Not yet implemented or proven

- governed generation-bound Holo owner retrieval;
- authenticated independent outcome evaluation;
- signed durable promotion, activation, rollback, and canary evidence;
- authenticated runtime A/B candidate binding;
- hundred-agent distributed scheduling;
- production end-to-end RSI.
