# idle_automation Test Suite

Pytest contracts for idle scheduling, maintenance dispatch, and the durable
exact-SHA HoloIndex post-merge transaction. The suite is implemented; do not
use the historical placeholder claims of zero coverage or no executions.

## Current inventory

- `test_caller_wiring.py`: idle-automation call-site integration.
- `test_schedule_claim_state.py`: durable claim codec, lease, retry, and CAS.
- `test_schedule_evaluator.py`: cadence parsing and claim decisions.
- `test_scheduled_routines_integration.py`: scheduled dispatch integration;
  WSP_62 growth is frozen and new provider cases belong in a split module.
- `test_self_research_refresh.py`: self-research refresh behavior.
- `test_startup_maintenance_gate.py`: lightweight startup maintenance routing.
  Self-research and training dispatch are verified at exact mocked executor
  boundaries; this unit suite never launches those live workloads.
- `test_holoindex_postmerge_coordinator.py`: AgentDB queue/claim/retry,
  supersession, and atomic completion contracts.
- `test_holoindex_postmerge_authority_order.py`: split authority-lease order,
  activation failure, exact binding, owner cleanup, and finalization contracts.

## HoloIndex post-merge acceptance matrix

The authority-order suite proves canonical refresh runs under the first
authority lease, activation runs after release, and final repository/origin
proof runs under a reacquired lease while the process lock remains held.
Initial lease contention does not stop an unowned process; post-activation
contention does. A route or activation failure through the real authority
transaction and executor leaves the task non-completed, its request pending,
and no completion event. A ready owner cannot substitute another generation
or freshness receipt.

These are isolated tests. They do not mutate the live Holo store, route,
replica, AgentDB, authority checkout, or network. Production acceptance still
requires the merged exact-main OpenClaw replay described in `ROADMAP.md`.

## Running

From the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_ADDOPTS='-p no:cacheprovider'
python -m pytest -q modules/infrastructure/idle_automation/tests
```

Focused post-merge contracts:

```powershell
python -m pytest -q modules/infrastructure/idle_automation/tests/test_holoindex_postmerge_coordinator.py modules/infrastructure/idle_automation/tests/test_holoindex_postmerge_authority_order.py
```

Use an explicit O:-drive `--basetemp` if a host plugin requires pytest temp
storage. See `TestModLog.md` for dated commands and observed outcomes.

## WSP contracts

- WSP 5/6: expand verification from focused behavior to adjacent modules.
- WSP 22/34: keep this inventory and `TestModLog.md` current.
- WSP 62: extract cohesive test surfaces before adding growth debt.
- WSP 97: retrieve this inventory and nearest tests before authoring coverage.
