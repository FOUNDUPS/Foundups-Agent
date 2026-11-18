# WRE Gateway

**Status:** legacy/compatibility DAE router; not the authoritative RedDog worker
executor and not production RSI.

`DAEGateway` validates an incoming envelope and reports observed routing
counters. Generic pattern recall returns a proposal, while an assembled FoundUp
route returns current metadata without evolving the DAE or starting a worker.
The route still depends on legacy recursive-learning and DAE-cube components.
It does not replace WSP 95 admission, the FoundUpJob consumer, OpenClaw/Hermes
worker contracts, or an independent outcome verifier.

## Current callable surface

```python
from modules.infrastructure.wre_core.wre_gateway.src.dae_gateway import DAEGateway

gateway = DAEGateway()
result = await gateway.route_to_dae(
    "compliance",
    {
        "objective": "Inspect a bounded work item",
        "context": {},
        "wsp_protocols": ["WSP 50", "WSP 97"],
        "token_budget": 1000,
    },
)
metrics = gateway.get_gateway_metrics()
```

Public methods include:

- `route_to_dae(dae_name, envelope)`;
- `get_last_validation_result()`;
- `list_available_daes()`;
- `get_gateway_metrics()`;
- `validate_wsp_compliance(operation)`.

## Validation and authority

- FoundUpJob-shaped envelopes use the strict WSP 97 validator when its import is
  available.
- Generic DAE envelopes require an objective and receive advisory checks for
  recommended fields.
- A valid envelope authorizes only bounded in-process proposal generation. It does not
  authenticate effects or grant file, Git, network, model-provider, worker,
  production, or HoloIndex-maintenance authority.
- Missing-DAE spawn requests fail closed as proposals until a governed worker
  executor exists. Existing FoundUp metadata is not proof that an OpenClaw or
  Hermes sandbox exists, evolved, started, or executed work.
- Generic pattern recall returns `success: false`, `proposal_only: true`,
  `compliance_verified: false`, and no effect receipt.

## Token telemetry truth

Configured token values are budgets or legacy pattern hints. They are not
measured usage. Gateway results expose `token_usage_measured: false` where a
budget hint is returned. `get_gateway_metrics()` reports:

```python
{
    "efficiency": {
        "avg_tokens_per_request": None,
        "total_tokens_saved": None,
        "token_reduction_measured": False,
        "pattern_recall_rate": 0.0,
    }
}
```

No reduction percentage is claimed until authenticated provider/runtime usage
receipts and a defined comparison baseline are implemented.

The MLE-STAR compatibility DAE follows the same rule: configured budget is not
usage, and its efficiency fields remain `None`/unmeasured. Its output is always
projected through the gateway's proposal-only wrapper; nested success, worker,
effect, compliance, or validity claims are discarded. Proof-of-Benefit receipt
structure is checked, but `valid` remains false until a real signature verifier
is implemented. The removed MLE-STAR runtime stubs cannot claim ablation or
refinement effects.

## Tests

```powershell
$root = 'O:\pytest_tmp\reddog_wre_truth\gateway'
$env:TMP = $root
$env:TEMP = $root
$env:FOUNDUPS_DB_PATH = Join-Path $root 'foundups.db'
$env:WRE_PATTERN_MEMORY_DB = Join-Path $root 'pattern-memory.db'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m pytest -q `
  modules/infrastructure/wre_core/wre_gateway/tests/test_dae_gateway_policyflags_guards.py `
  modules/infrastructure/wre_core/tests/test_wre_telemetry_truth.py `
  --basetemp (Join-Path $root 'pytest') `
  -o "cache_dir=$(Join-Path $root 'cache')"
```

These tests are local policy/telemetry guards. They do not start a live worker,
call a model/provider, or prove production DAE execution.

## Missing production layers

- a single authenticated FoundUpJob-to-worker authority chain;
- durable OpenClaw/Hermes sandbox lifecycle evidence;
- independent outcome evaluation and promotion;
- receipt-backed token/compute telemetry;
- concurrency, recovery, rollback, and production RSI canaries.

The RedDog/WRE roadmap tracks these as future focused transactions.
