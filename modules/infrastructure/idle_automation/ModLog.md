# Idle Automation Module - ModLog

This log tracks changes specific to the **idle_automation** module in the **infrastructure** enterprise domain.

## WSP 22 ModLog Protocol
- **Purpose**: Track module-specific changes and evolution per WSP 22
- **Format**: Reverse chronological order (newest first)
- **Scope**: Module-specific features, fixes, and WSP compliance updates
- **Cross-Reference**: Main ModLog references this for detailed module history

---

## MODLOG ENTRIES

### 2026-07-26 - Exact-SHA HoloIndex Post-Merge WRE Coordinator

**WSP Protocol:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 87, WSP 97

- Added a durable one-task-per-main-SHA coordinator and exact OpenClaw
  maintenance route without query-time indexing.
- Added CAS claim, bounded retry, supersession, and atomic task/request/proof
  completion semantics.
- Added a bounded assignment lease so process interruption cannot leave a
  post-merge task permanently assigned.
- Added a separate authority-update lease around clean non-rewind detached
  checkout updates while retaining `MaintenanceSession` as the canonical SSD
  writer and receipt transaction.
- Allows recovery only when the trusted blocker marker is the sole dirty
  authority path; all other dirty worktree states remain rejected.
- Required canonical exact-HEAD admission proof before reporting `CURRENT`;
  self-hashed AgentDB events alone are never operational authority.
- Moved network polling off the synchronous supervisor observation path.

**WSP_15 MPS:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19
(P0).

### 2026-07-24 - Daily OpenRouter Catalog Schedule POC

**WSP Protocol:** WSP 00, WSP 15, WSP 22, WSP 62, WSP 97

- Added `openrouter_catalog_refresh` as a daily-only allowlisted schedule with
  canonical ID `e324884d66c4`.
- Passed the full exact durable claim through DAE dispatch while leaving the
  legacy string dispatcher unchanged.
- Added default-off `AUTO_OPENROUTER_CATALOG_REFRESH` and trusted
  `OPENROUTER_CATALOG_RUNTIME_ROOT`, defaulting outside the repository.
- Added a pure exact-projection boundary: only six-key
  `COMPLETED/completed` evidence with canonical receipt/candidate IDs may
  finalize success; every malformed or nonterminal result becomes a fixed
  content-free failure.
- Preserved claim ordering: dispatch, exact-token finalize, then legacy
  successful `last_run` recording. Finalization uncertainty records no legacy
  completion.
- Kept candidate discovery separate from selection, promotion, registry
  mutation, and runtime binding.

**WSP_15 MPS:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19
(P0).

**MPS rationale/remediation:** Truthy non-boolean adapter values could have
been coerced into successful claim finalization. Exact six-key/type/token/ID
validation now rejects truthy strings/integers, wrong states, missing or forged
IDs, extra/missing keys, and secret-bearing text before finalization. Deep claim
validation remains canonical in the AI Gateway adapter; the DAE retains only
the narrow exact type/routine/daily/schedule-ID pre-import check.

**Validation:** `174 passed, 1 skipped` focused; `575 passed, 3 skipped`
combined AI Gateway + IdleAutomation + runtime-artifact-safety scope. The
concatenation test uses real parser, schedule ID, durable claim, dispatch, and
finalization with an offline mocked provider boundary.

**WSP_62 remediation status:** `test_scheduled_routines_integration.py` is
1,057 lines, above the 1,000-line remediation trigger but below the current
1,200-line Python limit; future provider-schedule tests move to
`test_openrouter_catalog_schedule_integration.py`. `idle_automation_dae.py` is
1,444 lines in the 1,200-1,500 DAE guideline window; scheduled-claim
orchestration/configuration must be extracted before further feature growth or
the 1,500-line boundary.

### 2026-07-24 - Legacy Failed-Row Durable Retry Migration

**WSP Protocol**: WSP 22, WSP 62, WSP 97

- Corrected legacy migration so a current-window `last_run` suppresses work
  only when `last_result` is explicit canonical `success:...`.
- Failed or unknown legacy results now remain due and enter durable claim
  control instead of being silently skipped.
- `record_execution()` advances `last_run` only for successful executions.
- Added persisted failed-row, unknown-result fail-safe, canonical-success, and
  failed-record timestamp regressions.

### 2026-07-24 - Durable Schedule Claim Lease Phase 1

**WSP Protocol**: WSP 15, WSP 22, WSP 62, WSP 97
**Phase**: P0 autonomous scheduling correctness
**Agent**: 0102

#### Problem

Scheduled dispatch used a non-atomic `get_due -> await dispatch ->
record_execution` sequence. Independent workers could observe the same due
schedule and both execute it; crashes also left no authoritative retry or
completion boundary.

#### Solution

- Kept `ScheduleEvaluator` as the single cadence/window owner.
- Added canonical full SHA-256 window execution IDs.
- Added trusted outside-repository `schedule_claim_state.json`.
- Added one-window durable leases with opaque exact-token finalization.
- Added restart idempotency, one lease recovery, three attempts, and 60/300
  second backoff.
- Added strict malformed/partial/duplicate/cap validation, bounded retention,
  content-free outcomes, atomic publication proof, and exact LKG restoration.
- Changed DAE ordering to claim immediately before dispatch and finalize before
  recording successful legacy `last_run`; failed attempts no longer suppress
  their bounded retry.

#### Safety Boundary

Lease recovery is at-least-once and therefore permits only repeat-safe or
independently fenced routines. The Windows `Local\` mutex coordinates the same
logon session, not cross-session services.

#### Tests

- 83 focused claim/evaluator/DAE tests pass.
- Full module run: 117 passed; one unrelated pre-existing startup HoloIndex
  mock-target mismatch remains outside this lane.
- Neighbor runtime safety: 11 passed, 1 skipped.
- Adversarial coverage includes concurrency, stale tokens, expiry recovery,
  retry cap, malformed state, exact LKG preservation, path confinement,
  retention, disabled zero-dispatch, and completion-unknown finalization.

### 2026-03-27 - Cross-Surface Continuity Wiring (triggering_session)

**WSP Protocol**: WSP 22, WSP 54 (Multi-Agent Coordination)
**Phase**: Gateway Continuity closure
**Agent**: 0102

#### Problem

`run_idle_automation()` had no way to correlate background work to the originating livechat session. Idle tasks ran as independent roots even when triggered from auto_moderator with a known video_id.

#### Solution

Added `triggering_session` parameter to `run_idle_automation()`:
- When provided (and no `parent_context`), calls `set_triggering_session()` before execution
- `_try_recover_origin_continuity()` looks up AgentDB breadcrumbs by session_id
- Returns parent-linked context if breadcrumb found, otherwise independent root

#### Files Changed
- `idle_automation_dae.py`: Added `triggering_session` param, wired to `set_triggering_session()`
- `INTERFACE.md`: Updated `run_idle_automation()` signature and continuity docs

#### Tests
- `test_caller_wiring.py`: 8 tests proving session storage, precedence, and recovery

---

### 2026-03-26 - Startup Maintenance Gate Execution Path Fix (P0)

**WSP Protocol**: WSP 22, WSP 27 (DAE Architecture)
**Phase**: Fix dead work gap
**Agent**: 0102

#### Problem (Round 1)

Startup maintenance gate queued tasks with phantom skill names (`openclaw-monitor`, `holo-search`, `training-system`) that had no executors in `run_task.py`. Result: gate queued dead work that would always fail with `no_executor_matched`.

#### Problem (Round 2)

Initial fix used incorrect kwargs for `SelfResearchRefresher.run()` and routed training to wrong executor:
- `run_training_refresh`, `run_compliance_scan`, `run_update_candidates` don't exist
- Training was calling `SelfResearchRefresher.run()` instead of `IdleAutomationDAE._execute_pattern_training()`

#### Solution

Added dispatch path 4 in `run_task.py` for startup maintenance tasks:

1. Detects `source == "startup_maintenance_gate"` tasks
2. Dispatches by task_id to real executors:
   - `startup_refresh_self_research` → `SelfResearchRefresher.run(run_compliance=True, run_self_audit=True, ...)`
   - `startup_refresh_holo_index` → `SelfResearchRefresher.refresh_holo_index()`
   - `startup_refresh_model_status` → `get_dependency_status()` + write JSON
   - `startup_training_batch` → `IdleAutomationDAE()._execute_pattern_training()` via asyncio.run()

#### Integration Tests (Live Dispatch)

5 tests proving executability without mocking the critical paths:
- `test_model_status_task_executes`: Proves model status has executor
- `test_holo_index_task_executes`: Proves HoloIndex has executor (mocked to avoid 30s index)
- `test_self_research_task_executes_live`: **LIVE** - proves kwargs are correct
- `test_training_batch_task_executes_live`: **LIVE** - proves IdleAutomationDAE routing
- `test_unknown_task_returns_none`: Proves unknown tasks fall through

#### Files Modified

- `modules/communication/moltbot_bridge/scripts/run_task.py`: +95 lines (dispatch path 4 with correct routing)
- `tests/test_startup_maintenance_gate.py`: +90 lines (live dispatch integration tests)

#### Round 3: Success Classification Fix

**Problem**: `startup_refresh_self_research` returned `ok=False` even on success because success detection checked `result.get("status") == "completed"` but `SelfResearchRefresher.run()` returns a report dict with `generated_on`, not a `status` field.

**Fix**: Changed success detection to `isinstance(result, dict) and "generated_on" in result`

**Regression test**: `test_self_research_task_executes_live` now asserts `ok=True`

#### Test Results

18 tests pass (13 existing + 5 integration tests)

#### Final Verification

```
startup_refresh_model_status:    ok=True
startup_refresh_holo_index:      ok=True
startup_refresh_self_research:   ok=True
startup_training_batch:          ok=False (expected - training already complete)
```

---

### 2026-03-24 - Startup Maintenance Gate (P0)

**WSP Protocol**: WSP 22, WSP 27 (DAE Architecture)
**Phase**: Compute-conserving startup
**Agent**: 0102

#### Problem

Heavy work like training, HoloIndex refresh, and doc generation was potentially blocking startup.
The system needed a way to detect staleness cheaply and queue maintenance for later execution.

#### Solution

Created `startup_maintenance_gate.py` that implements a compute-conserving startup pattern:

1. **Detect** staleness without heavy execution:
   - Self-research status (max 6h)
   - HoloIndex freshness (max 12h)
   - Training readiness (max 24h)
   - Model routing status (max 24h)

2. **Queue** maintenance tasks to AgentDB:
   - `startup_refresh_self_research`
   - `startup_refresh_holo_index`
   - `startup_training_batch` (only if explicitly due)
   - `startup_refresh_model_status`

3. **Return quickly** without blocking startup

#### Integration

Added call in `main.py` after preflights pass, before `bootstrap_runtime_dae_launches()`.

#### Constraints Enforced

- Preflight may inspect timestamps/hashes
- Preflight must NOT run model training
- Preflight must NOT run full HoloIndex indexing
- Preflight must NOT rewrite narrative docs
- Heavy work belongs in queued/background execution

#### Files Added

- `src/startup_maintenance_gate.py`: 300 lines, StartupMaintenanceGate class
- `tests/test_startup_maintenance_gate.py`: 13 tests

#### Files Changed

- `main.py`: Added startup maintenance gate call after preflights

#### Verification

- `pytest test_startup_maintenance_gate.py` → 13 passed
- In-process: Detects 3 stale artifacts, prints `[STARTUP-MAINT] preflight=PASS stale=3`
- No heavy compute inline (tests verify < 5s execution)

---

### 2026-03-24 - Scheduled Natural Language Automations

**WSP Protocol**: WSP 22, WSP 27 (DAE Architecture), WSP 60 (Memory Architecture)
**Phase**: Automation Hardening
**Agent**: 0102

#### New Files

**schedule_evaluator.py** - Deterministic natural-language schedule parser and evaluator:
- `ScheduleParser`: Parses phrases like "run self research daily", "run nightly queue audit"
- `ScheduleEvaluator`: Manages schedule persistence, due evaluation, execution tracking
- `ScheduleSpec`: Dataclass for individual schedule definitions
- Supported routines: `self_research`, `queue_audit`, `grant_watchlist`
- Supported cadences: `daily`, `nightly`, `morning`, `evening`
- Persistence: `memory/schedules.json` with atomic writes

**scripts/manage_schedules.py** - CLI for schedule management:
- `add "run self research daily"` - Add a schedule
- `list` - List all schedules
- `remove <id>` - Remove a schedule
- `enable/disable <id>` - Toggle a schedule
- `due` - Show due schedules
- `phrases` - Show supported phrases

#### Changes to idle_automation_dae.py

- **Added**: `_execute_scheduled_routines()` method - Phase 5 in idle loop
- **Added**: `_dispatch_scheduled_routine()` method - routes to existing native paths
- **Added**: `_run_queue_audit()` method - executes queue builder script
- **Added**: `_run_grant_watchlist_refresh()` method - calls `refresh_grant_watchlist()` (fixed method name)
- **Added**: `_get_scheduled_routines_status()` method - status reporting
- **Updated**: `run_idle_tasks()` to include scheduled routines execution
- **Updated**: `get_idle_status()` to include scheduled routines info
- **Updated**: Telemetry with `scheduled_routines_success` and `scheduled_routines_executed`
- **Fixed**: Success logic - only reports True when all due routines succeed
- **Fixed**: Semantic deduplication - ID now derived from `(routine, cadence)` tuple, not raw phrase
- **Fixed**: Grant watchlist summary reads correct keys (`watch_count`, `changed_count`, `error_count`)

#### Changes to openclaw_execution_routes.py

- **Added**: `_try_schedule_command()` - OpenClaw route for schedule management
- **Added**: `_list_schedules()`, `_show_due_schedules()`, `_add_schedule()`, `_remove_schedule()`, `_toggle_schedule()`
- Supported OpenClaw commands:
  - `list schedules` / `show schedules`
  - `schedule self research daily` / `run queue audit nightly`
  - `show due schedules`
  - `remove schedule <id>` / `enable schedule <id>` / `disable schedule <id>`

#### Acceptance Criteria Met

1. 12 deterministic NL schedule combinations supported
2. Schedules persist across runs (JSON artifact)
3. Due schedules execute through existing native paths
4. Execution writes reportable outcome (`last_run`, `last_result`)
5. Duplicate immediate reruns prevented (window-based dedup)
6. Tests cover parse, persistence, due-checking, and dispatch (59 tests)
7. CLI and OpenClaw entry points for creating/managing schedules

#### Tests Added

- `test_schedule_evaluator.py`: 40 tests for parser, evaluator, semantic dedup, due evaluation
- `test_scheduled_routines_integration.py`: 12 tests for dispatch, partial failures, and integration

---

### 2026-03-23 - Grant Task Stable IDs and Stale Cleanup

**WSP Protocol**: WSP 22, WSP 97 (Autonomy Boundaries)
**Phase**: Automation Hardening
**Agent**: 0102

#### Changes to self_research_refresh.py

- **Added**: `stable_task_id` parameter to `_build_manual_candidate()` for explicit task IDs
- **Added**: Stable IDs for all watchlist tasks:
  - `grant_watchlist_review`, `grant_watchlist_stabilize`
  - `pqn_watchlist_review`, `pqn_watchlist_stabilize`
  - `openclaw_ecosystem_watchlist_review`, `openclaw_ecosystem_watchlist_stabilize`
- **Added**: Stale task cleanup in `publish_autonomous_tasks()`:
  - Combined filter: `task_id LIKE 'self_research_external_watchlist_%'` + `required_skills LIKE '%openclaw-grants%'`
  - Preserves stable IDs via `NOT IN` clause
  - Only triggers when stable grant tasks are in candidates
- **Added**: Completed task protection - skips republish if same `changed_items`/`error_items`

#### Tests

Regression test in `test_hardening_tranche.py::test_stale_grant_task_cleanup_preserves_pqn_and_ecosystem`:
- Seeds old slugified grant rows, PQN rows, ecosystem rows
- Publishes stable grant tasks
- Asserts only old grant rows deleted, PQN/ecosystem preserved

---

### 2026-03-23 - Memory Nudge Runtime Wiring

**WSP Protocol**: WSP 22, WSP 60 (Memory Architecture), WSP 97 (Autonomy Boundaries)
**Phase**: Automation Hardening
**Agent**: 0102

#### Changes to self_research_refresh.py

- **Added**: `emit_nudges` parameter to `run()` method (default: True)
- **Added**: `_emit_memory_nudges()` method to call memory nudge engine after report written
- **Added**: `--no-nudges` CLI flag for disabling nudge emission
- **Added**: `memory_nudges_emitted` count in final report

#### Integration Points

The memory nudge engine (from moltbot_bridge) is now called at the end of each self-research cycle:
1. Self-research writes status reports
2. Nudge engine scans those reports for high-value events
3. Creates deduplicated memory notes in workspace/memory/
4. Records breadcrumbs in AgentDB for cross-session recall

#### Tests Added

- `test_run_emits_memory_nudges_when_high_value_events_detected`
- `test_run_skips_nudges_when_emit_nudges_false`

---

### 2026-03-22 - OpenClaw Self-Research Refresh Loop
**WSP Protocol**: WSP 15 (MPS Prioritization), WSP 27 (DAE Architecture), WSP 48 (Recursive Improvement), WSP 60 (Memory Architecture), WSP 84 (Code Reuse)
**Phase**: Automation Hardening
**Agent**: 0102 Codex

#### Self-Research Orchestration
- **Added**: `src/self_research_refresh.py` to consolidate internal and external system research
- **Reused**: `AgentDB` index freshness + autonomous task queue instead of inventing a new backlog store
- **Integrated**: HoloIndex refresh checks, WSP compliance scan, daemon self-audit sampling, and grant watchlist refresh
- **Applied**: WSP 15 scoring to generate ranked update candidates for 0102

#### Idle DAE Wiring
- **Added**: `AUTO_SELF_RESEARCH` and `AUTO_SELF_RESEARCH_TIMEOUT` configuration
- **Integrated**: `_execute_self_research_refresh()` into `IdleAutomationDAE.run_idle_tasks()`
- **Exposed**: `last_self_research` and self-research config in idle status output
- **Verified**: Direct `IdleAutomationDAE` execution path now completes self-research refresh in cached mode

#### Runtime Artifacts
- **Created**: `scripts/refresh_self_research.py` CLI wrapper
- **Writes**: `modules/communication/moltbot_bridge/workspace/reports/openclaw_self_research_status.json`
- **Publishes**: Ranked tasks into `AgentDB.agents_autonomous_tasks`
- **Stores**: Summary outcome in WRE `PatternMemory`

#### Operational Result
- **Observed**: Fast cached refresh path completes in ~18-25s
- **Seeded**: Initial full compliance cache after scanner hardening
- **Outcome**: 0102 now has an always-refreshable update queue rather than static research notes

### Initial Module Creation - WSP 27 DAE Architecture Implementation
**WSP Protocol**: WSP 27 (Universal DAE Architecture), WSP 35 (Module Execution Automation), WSP 3 (Module Organization)
**Phase**: Foundation
**Agent**: 0102 Claude

#### DAE Architecture Implementation
- **Created**: Complete IdleAutomationDAE class following WSP 27 four-phase pattern
- **Implemented**: Idle state detection and background task execution
- **Added**: Git auto-commit functionality with contextual messages
- **Integrated**: LinkedIn posting via existing GitLinkedInBridge
- **Included**: Comprehensive safety controls and error handling

#### WSP 60 Memory Architecture
- **Implemented**: Persistent state storage in memory/idle_state.json
- **Added**: Execution history logging in memory/execution_history.jsonl
- **Created**: Telemetry collection for performance monitoring
- **Integrated**: Daily execution limits and reset logic

#### WSP 48 Recursive Improvement
- **Connected**: WRE integration for success/failure tracking
- **Added**: Pattern learning from task execution results
- **Implemented**: Optimized approach retrieval for task improvement

#### Safety & Control Systems
- **Added**: Network connectivity verification
- **Implemented**: Git status validation before operations
- **Created**: Daily execution limits to prevent resource exhaustion
- **Included**: Environment variable configuration system

#### YouTube DAE Integration
- **Prepared**: Hook system for idle task execution
- **Created**: run_idle_automation() convenience function
- **Designed**: Non-blocking integration that won't disrupt stream monitoring

#### WSP Compliance Verification
- **Validated**: WSP 3 infrastructure domain placement
- **Confirmed**: WSP 27 DAE architecture compliance
- **Verified**: WSP 35 module execution automation
- **Ensured**: WSP 11 interface documentation completeness

#### Module Structure Creation
- **Established**: Proper WSP module directory structure
- **Created**: README.md, ROADMAP.md, INTERFACE.md per WSP standards
- **Added**: requirements.txt and __init__.py
- **Prepared**: tests/ directory for future test implementation

---

*This ModLog follows WSP 22 protocol and will be updated with each module change.*
