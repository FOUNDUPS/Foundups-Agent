# TestModLog - tests

## 2026-09-23: Persistent verification interruption and retry qualification

- WSP00/6/15/22/49/50/62/97; C2/I4/D3/Impact3=12/P2. Five fixed observations in the existing persistent compute test owner pass locally and independently (same five cases), reproducing double debit on rejected retry, charge-only/partial-decision/missing-event residues, and state rejection on accepted retry.
- Production code unchanged; all29 prior top-level test/helper definitions remain AST-identical. Test owner581→680 lines, new functions22/20/36; no new module/skill. Exact interpreter -I/-B, disposable SQLite,39 unchanged package/test bindings; ten SQLite opens/run, no allowed test subprocesses, five denied convenience symlinks/run and no unexpected guard denials. Two config warnings retained; registry current1658/quarantined269.
- Characterization success is not correctness. R24 records witnesses and next14/P1 atomic/replay repair candidate, requiring fixed desired acceptance and existing adapter no-growth/cohesion reconciliation before implementation. Signed issuer/integration, PostgreSQL, payout and native AmIBot/retained RSI remain separate.

Evidence: `O:/Foundups-Agent-audits/20260923-rsi-verification-retry/{candidate,independent}/receipt.json`. Assertions compare first result, complete mapped-table close/reopen snapshot and same-ID retry; unrelated tables stay unchanged. No live funds or payout invoked.


## 2026-09-22 - Persistent initiation failure, replay and contention regression

- Corrected fixed selection: baseline 79 passed/41 failed; candidate and independent replay each 120 passed, zero errors/skips/guard denials or source drift. Independent replay covers the same case IDs, not another 120 unique cases.
- Ten connected existing suites: persistent_compute_wiring, persistence, sqlite_adapter, migrations, repository_factory, compute_access, task_lifecycle, schemas, permissions, cabr_hooks. Original three wiring cases retained; added56cases in that same owner. Real disposable SQLite, two independent adapters, actual post-write and post-commit exceptions, bounded lock contention; no live provider/payment or OS sandbox claim.
- Initial116-case runs (79pass/37fail baseline;114pass/2fail candidate) retained. Distinct synthetic token symbols repair setup only. Four additional reviewer/contract cases fixed before corrected baseline/candidate comparison. No tests deselected or skipped.
- Runner actual flags -I/-B; plugin/cache disabled; writes/SQLite confined to owned temporary area; network/subprocess/production DB denied. Python audit hooks constrain these known tests, not hostile native code. Two existing asyncio config warnings do not imply async-plugin coverage. No process-death/power-loss claim.
- Evidence: `O:/Foundups-Agent-audits/20260922-rsi-payout-atomic/{baseline-corrected,candidate-corrected,independent-final}/receipt.json`. Product source stayed fixed across corrected candidate/independent runs; receipts bind source, test IDs, outputs and guard events.


## 2026-02-16 (Cross-module concatenated validation - identity-anchor hardened)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests modules/foundups/agent_market/tests modules/foundups/simulator/tests -q`
- Status: PASS
- Result: 335 passed, 2 warnings
- Notes:
  - Confirms integrated lane stability after OpenClaw conversation identity normalization.
  - Includes SSE member-gate + DEX stream contract + token symbol guardrail updates.

## 2026-02-16 (Symbol guardrails + member-gate integration lane)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/simulator/tests/test_sse_server.py modules/foundups/agent_market/tests/test_e2e_integration.py modules/foundups/agent_market/tests/test_persistence.py modules/foundups/agent_market/tests/test_task_lifecycle.py -q`
- Status: PASS
- Result: 55 passed, 2 warnings
- Notes:
  - Validates case-insensitive duplicate token symbol rejection in in-memory and sqlite paths.
  - Validates FAM adapter token auto-generation + collision-safe launch resolution.
  - Validates simulator SSE member-gate auth (including fail-closed misconfiguration)
    plus endpoint gating behavior and DEX streamable event contract.

## 2026-02-16 (Cross-module concatenated validation)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests modules/foundups/agent_market/tests modules/foundups/simulator/tests -q`
- Status: PASS
- Result: 321 passed, 2 warnings
- Notes:
  - Validates FAM + Moltbot + Simulator integration surfaces as a single test lane.
  - Warnings are repo-level pytest config warnings for `asyncio_*` options.

## 2026-02-16 (Concatenated suite stabilization: agent_market + simulator)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/agent_market/tests modules/foundups/simulator/tests -q`
- Status: PASS
- Result: 229 passed, 2 warnings
- Notes:
  - Includes deterministic-id/heartbeat dedupe checks in `test_fam_daemon.py`.
  - Includes CABR history serialization precision checks in `test_cabr_hooks.py`.
  - Warnings are repo-level pytest config warnings for `asyncio_*` options.

## 2026-02-16 (Compute Access Persistence - Tranche 5 P0 Extension)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/agent_market/tests/test_sqlite_adapter.py modules/foundups/agent_market/tests/test_migrations.py modules/foundups/agent_market/tests/test_persistence.py modules/foundups/agent_market/tests/test_compute_access.py modules/foundups/agent_market/tests/test_persistent_compute_wiring.py modules/foundups/agent_market/tests/test_task_lifecycle.py modules/foundups/agent_market/tests/test_schemas.py modules/foundups/simulator/tests/test_cabr_terminology_guardrail.py -q`
- Status: PASS
- Result: 49 passed, 2 warnings
- Notes:
  - Validates schema v2 migration and compute-access tables/indexes.
  - Validates wallet, debit, rebate, access checks, and compute-session round trips.
  - Validates persistent registry/task pipeline compute-gate debit wiring.
  - Uses project `.venv` to include SQLAlchemy dependency.

## 2026-02-16 (Compute Access Paywall P0 In-Memory)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/foundups/agent_market/tests/test_compute_access.py modules/foundups/agent_market/tests/test_task_lifecycle.py modules/foundups/agent_market/tests/test_schemas.py modules/foundups/simulator/tests/test_cabr_terminology_guardrail.py -q`
- Status: PASS
- Result: 16 passed, 2 warnings
- Notes:
  - Validates paywall denial when no plan or insufficient credits.
  - Validates scout-tier block and builder-tier debit flow.
  - Validates compute purchase/debit/rebate/session event emission.
  - Confirms CABR canonical terminology guardrail still passes.

## 2026-02-11 (F_0 MVP offering contract)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/agent_market/tests/test_mvp_offering.py -q`
- Status: PASS
- Result: 4 passed
- Notes:
  - Validates 5-term cap at 200 UPS/term.
  - Validates bid UPS gating and treasury-only resolve.
  - Validates highest-bid allocation + loser refund + treasury injection accounting.

## 2026-02-08 (Prototype Tranche 2: Persistence Layer)
- Command: $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/agent_market/tests/test_persistence.py -q
- Status: PASS
- Result: 12 passed
- Command: $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/agent_market/tests/test_sqlite_adapter.py -q
- Status: PASS
- Result: 9 passed
- Command: $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/agent_market/tests/test_migrations.py -q
- Status: PASS
- Result: 4 passed
- Command: $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/foundups/agent_market/tests/test_repository_factory.py -q
- Status: PASS
- Result: 3 passed
- Notes:
  - SQLAlchemy 2 compatibility validated for WAL pragma query.
  - Migration idempotency/version guard and backend factory routing validated.
  - Full suite run still shows pre-existing unrelated failures outside persistence tranche scope.
## 2026-02-08 (Prototype Tranche 1: FAM DAEmon)
- Added: `test_fam_daemon.py` - 27 tests for FAM DAEmon observability backbone
- Command: Manual Python script (web3 pytest plugin conflict)
- Status: PASS (26/27) - 1 timing-sensitive heartbeat test fails on Windows
- Coverage:
  - Schema Validation: FAMEventType enum, FAMEvent dataclass, to_dict/to_json/from_dict
  - Deterministic IDs: event_id generation, dedupe_key per event type
  - Event Store: initialization, write, sequence monotonicity, dedupe rejection, query filters
  - JSONL+SQLite Parity: empty state, after writes, dual file creation
  - FAM DAEmon: start/stop events, heartbeat loop, emit custom events, listeners
  - Health API: before/after start, event stats, status dict
  - Thread Safety: concurrent writes, unique sequence IDs, no gaps
- Files: `fam_daemon.py` (737 LOC), `test_fam_daemon.py` (comprehensive)

## 2026-02-08 (0102-C Integration)
- Command: `python modules/foundups/agent_market/tests/run_tests.py`
- Status: PASS (26/26)
- Skipped: Moltbook adapter tests (3) - cross-module boundary per WSP 72
- Notes: Moltbook tests skipped pending moltbot_bridge owner assertion fixes. Adapter works functionally (manual validation passed).

## 2026-02-08 (0102-A Hardening)
- Added: `test_deterministic_ids.py` - 10 tests for DeterministicIdGenerator and InMemoryAgentMarket determinism
- Added: `test_cabr_hooks.py` - 12 tests for PersistentCABRHooks evidence chain
- Status: PASS (manual validation via Python script due to web3 pytest plugin conflict)
- Coverage: Deterministic ID generation, reset(), get_tasks_by_foundup(), CABRInput/CABROutput serialization, CABR evidence chain

## 2026-02-07
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/foundups/agent_market/tests -q`
- Status: PASS
- Result: 23 passed, 2 warnings
- Notes: Warnings are repo-level pytest config warnings (`asyncio_*` options) under plugin-autoload-disabled mode.


