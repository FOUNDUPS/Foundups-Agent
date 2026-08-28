# Idle Automation Test Module Log

**Module**: `modules/infrastructure/idle_automation`
**Framework**: pytest
**Last Updated**: 2026-08-28
**WSP Compliance**: WSP 22 (Module ModLog Protocol), WSP 34 (Test Validation)

---

## 2026-08-28: Linked-control dependency runtime RED/GREEN

- RED proved the post-merge executor forwarded its clean linked control
  checkout directly to the authority transaction, reproducing the missing
  `.venv`/snapshot-probe failure seen in the exact-main OpenClaw run.
- GREEN reuses `resolve_holoindex_runtime_root()` and proves a distinct
  same-repository primary runtime reaches the authority transaction while the
  dedicated authority root remains unchanged.
- Fresh focused result: **38 passed** across
  `test_holoindex_postmerge_coordinator.py` and
  `test_holoindex_postmerge_authority_order.py` plus the bounded
  `test_holoindex_postmerge_runtime_root.py`, using O:-local temp storage.
- The canonical WRE registry was regenerated from the staged new test and is
  current at **1,609 tracked Python tests / 268 quarantined**; its focused
  registry contract is **28 passed**.

## 2026-08-27: Exact-SHA activation order and AgentDB truth

- Added split-lease ordering, initial/final lease contention, post-activation
  supersession, exact generation/receipt mismatch, sealed public signatures,
  and owner-cleanup regressions.
- Added both composed FakeDB and real SQLite AgentDB failure paths. A failed
  route activation cannot create a completion event or resolve the durable
  request, and the task is explicitly failed.
- Focused authority/executor/coordinator/database result: **62 passed** with no
  live Holo, Git, route, replica, or network mutation.
- The module macro audit found two startup-dispatch tests executing live
  self-research and pattern training, causing repeatable 90--240 second test
  timeouts. Replaced them with exact mocked executor-boundary proofs. The tests
  still verify constructor arguments, self-research keyword arguments,
  dispatch selection, and result projection without launching real work.

## 2026-07-24: Daily OpenRouter Catalog Schedule POC

**Files:** `test_schedule_evaluator.py`,
`test_scheduled_routines_integration.py`, and AI Gateway provider-catalog tests.

- Proves the parser accepts only the exact daily routine and rejects forged
  cadence before adapter/provider work.
- Proves default-off execution makes zero adapter/provider calls and trusted
  runtime roots are code/config owned.
- Proves exact full-claim mapping, replay/finalize ordering, and no legacy
  `last_run` after failed finalization.
- Rejects truthy string/integer success, wrong status/reason, malformed replay,
  missing/forged IDs, extra/missing keys, and secret-bearing projections with a
  fixed content-free failure.
- Runs a real offline concatenation from `add_schedule` through canonical ID
  `e324884d66c4`, durable claim, DAE dispatch, exact-token finalization, and
  successful legacy recording.
- Proves cancellation propagates without finalization or legacy recording,
  leaving the claim leased for bounded expiry/replay recovery.
- Provider tests remain offline and verify no selection, promotion, registry,
  runtime-binding, direct-discovery, or catalog-bridge authority expansion.

**Focused Result:** `174 passed, 1 skipped`

**Combined AI Gateway + IdleAutomation + Runtime-Artifact-Safety Result:**
`575 passed, 3 skipped`

## 2026-07-24: Canonical HoloIndex Maintenance Dispatch Mock

**File**: `test_startup_maintenance_gate.py`

- Replaced the obsolete `SelfResearchRefresher.refresh_holo_index` mock with
  the canonical RedDog maintenance-handshake boundary.
- Uses the production `RedDogHoloIndexOperationalResult` type and a complete,
  secret-free ready receipt.
- Proves exact `repo_root`, `requested=True`, and `auto_maintenance=True`
  arguments without running HoloIndex, runtime maintenance, or network work.
- Retains exact executor, success, structured receipt, and serialized receipt
  assertions.

**Targeted Result**: `1 passed`

**Canonical Dispatch Result**: `3 passed`

**Full Idle Automation Result**: `126 passed`

---

## 2026-07-24: Legacy Failed-Row Migration Regression

- Proves a persisted current-window `failed:` row remains due after restart and
  receives a durable claim.
- Proves missing, empty, case-variant, and unknown legacy results fail safe as
  due.
- Proves only explicit canonical `success:` suppresses the current window.
- Proves failed `record_execution()` calls do not advance `last_run`.

**Focused Result**: `91 passed`

**Full Module Result**: `125 passed, 1 pre-existing failure`

**Neighbor Runtime Safety**: `11 passed, 1 skipped`

---

## 2026-07-24: Durable Schedule Claim Lease Phase 1

**Files**: `test_schedule_claim_state.py`, `test_schedule_evaluator.py`,
`test_scheduled_routines_integration.py`

- Proves two independent stores cannot double-claim one canonical window.
- Proves active-lease blocking, one expiry recovery, and stale-token rejection.
- Proves restart completion idempotency and 60/300/max-three failure retry.
- Proves malformed, partial, duplicate-key, timestamp-order, and token-collision
  state fails closed without mutation.
- Proves writer and wrong-success replacer failures preserve exact prior bytes
  and leave no owned temp files.
- Proves outside-repository confinement and payload path non-influence.
- Proves disabled/unknown/out-of-window schedules create no claim.
- Proves DAE performs zero dispatch on claim uncertainty and treats finalize
  failure as completion unknown without legacy `last_run`.

**Focused Result**: `83 passed`

**Full Module Result**: `117 passed, 1 pre-existing failure`

**Neighbor Runtime Safety**: `11 passed, 1 skipped`

---

## 2026-03-27: Caller Wiring + Runtime Emitter Instrumentation

**File**: `test_caller_wiring.py`
- Validates `run_idle_automation()` propagates `triggering_session` to DAE
- Validates `parent_context` takes precedence over `triggering_session`
- Validates empty string `triggering_session` treated as absent
- Validates auto_moderator caller site passes `self._last_stream_id`
- Validates breadcrumb written before idle handoff (source wiring)
- Validates breadcrumb → recovery → lineage path (integration test)
- Validates no false lineage when breadcrumb absent

**Run**:
- `python -m pytest modules/infrastructure/idle_automation/tests/test_caller_wiring.py -q`

**Result**:
- `8 passed`

**Runtime Emitter**:
- `_execute_pattern_training()` now emits `pattern_training` events via `runtime_emitter.py`
- Events include: patterns_stored, lines_processed, error on failure

---

## Test Implementation Status

### Planned Test Coverage

#### Core Functionality Tests
- [ ] `test_idle_automation_initialization()` - DAE initialization and config loading
- [ ] `test_idle_state_persistence()` - JSON state loading/saving with backup recovery
- [ ] `test_execution_history_management()` - Telemetry logging and history limits
- [ ] `test_daily_limits_enforcement()` - Rate limiting and reset logic

#### Git Integration Tests
- [ ] `test_git_status_detection()` - File change detection and commit message generation
- [ ] `test_git_push_simulation()` - Mock git operations without actual commits
- [ ] `test_git_error_handling()` - Network failures and permission errors

#### Social Media Tests
- [ ] `test_linkedin_content_generation()` - Post content creation from commits
- [ ] `test_linkedin_circuit_breaker()` - Failure threshold and recovery logic
- [ ] `test_linkedin_posting_disabled()` - Safety mechanisms for production

#### Health Monitoring Tests
- [ ] `test_health_score_calculation()` - Success/failure impact on health
- [ ] `test_critical_recovery_triggers()` - Automatic recovery when health critical
- [ ] `test_health_status_reporting()` - Status API accuracy

#### Configuration Tests
- [ ] `test_environment_config_parsing()` - Boolean and integer env var validation
- [ ] `test_config_bounds_enforcement()` - Min/max value constraints
- [ ] `test_invalid_config_defaults()` - Fallback to safe defaults

#### Integration Tests
- [ ] `test_youtube_dae_integration()` - Idle hook calling mechanism
- [ ] `test_wre_integration()` - Recursive improvement data reporting
- [ ] `test_async_execution_flow()` - End-to-end async task execution

### Test Infrastructure Needed

#### Mock Objects
- Git repository mock for safe testing
- LinkedIn API mock for posting simulation
- Network connectivity mock for offline testing
- File system mock for state persistence testing

#### Test Fixtures
- `idle_dae_fixture` - Pre-configured DAE instance
- `mock_git_repo` - Fake git repository with test commits
- `mock_linkedin_api` - Simulated LinkedIn posting responses

### 2026-03-23: Grant Task Cleanup Regression Test

- **Location**: `modules/communication/moltbot_bridge/tests/test_hardening_tranche.py`
- **Test**: `test_stale_grant_task_cleanup_preserves_pqn_and_ecosystem`
- **Status**: PASS
- **Coverage**:
  - Seeds old slugified grant rows, PQN rows, ecosystem rows in real temp DB
  - Calls `SelfResearchRefresher.publish_autonomous_tasks()` with stable grant IDs
  - Asserts: old grant rows deleted, PQN/ecosystem rows preserved, stable grant rows created
  - Uses `DatabaseManager.reset_for_tests()` pattern for singleton isolation

---

### Current Test Status: NOT IMPLEMENTED

**Reason**: Module is in MVP phase with safety-disabled social media posting. Full test implementation requires:
1. Social media posting re-enabled with proper safeguards
2. Mock infrastructure for external dependencies
3. CI/CD pipeline integration for automated testing

### Safety Considerations for Testing

**LinkedIn Posting**: Currently disabled in production code for safety. Tests must use mocks only.
**Git Operations**: Must use test repositories to avoid polluting production git history.
**Network Dependencies**: Tests must work offline and handle network failures gracefully.

### Test Execution Commands

```bash
# Run all idle automation tests
cd modules/infrastructure/idle_automation
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test
python -m pytest tests/test_idle_automation.py::test_idle_state_persistence -v
```

### Future Test Roadmap

**Phase 1 (Current)**: Basic unit tests for core functionality
**Phase 2 (Next Sprint)**: Integration tests with mocked external services
**Phase 3 (Future)**: End-to-end tests with real (but safe) external services

## WSP 22 Compliance

This TestModLog.md satisfies WSP 22 requirements by:
- Tracking test implementation status
- Documenting planned test coverage
- Recording safety considerations
- Providing execution commands
- Maintaining compliance with WSP 34 test validation protocol
