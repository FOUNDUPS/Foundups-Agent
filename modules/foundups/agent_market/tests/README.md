# Tests - FoundUps Agent Market

## Coverage Goals
- Schema validation for core entities.
- Lifecycle state transition correctness.
- Permission gating for verification and payout.
- Distribution gating and idempotent verified-milestone publish behavior.
- Launch orchestration and repo provisioning boundaries.
- Persistence migration/versioning and backend selection boundaries.
- F_0 investor subscription caps and MVP bid/resolve treasury injection rules.

## Persistent initiation acceptance (2026-09-22)

`test_persistent_compute_wiring.py` preserves the original three compute cases and adds56 bounded initiation cases: pending state, replay/reopen/lost response, immutable lineage, complete legacy history, zero-cost and changed-policy replay, all-write rollback, simultaneous adapters/shared wallet, lock timeout and pre-effect non-SQLite rejection. Connected persistence/migration/factory/compute/lifecycle/schema/permission/CABR suites total120 cases. Permission cases cover the in-memory PoC; they do not establish persistent role authority.

Keep baseline and candidate on identical case IDs and acceptance oracles. Use disposable explicit SQLite paths, actual -I/-B isolation and a reviewed external effect guard when qualifying this path. Preserve failed attempts and fixture corrections; test execution grants no live reward or runtime authority. Detailed counts and limitations are in [TestModLog](TestModLog.md).

## Run
```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest modules/foundups/agent_market/tests -q
```

## Tranche 2 Focused Run
```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest `
  modules/foundups/agent_market/tests/test_persistence.py `
  modules/foundups/agent_market/tests/test_sqlite_adapter.py `
  modules/foundups/agent_market/tests/test_migrations.py `
  modules/foundups/agent_market/tests/test_repository_factory.py -q
```
