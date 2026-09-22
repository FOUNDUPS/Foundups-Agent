## 2026-09-22: Truthful broker stop acknowledgment

- WSP00/10/15/22/49/50/62/91/97; C3/I3/D3/Impact3=12/P2. The existing broker distinguishes accepted stop requests from observed worker exit, binds the active handle's hook and rejects changed ownership across callbacks.
- Fixed baseline:25failed/26passed; candidate and independent replay:51passed (same cases). Existing13 import cases retained; three threaded lifecycle cases deselected, with only the legacy stop-status expectation updated for the new contract.
- Callbacks stay outside broker locks; finite replacement tests do not prove atomic publication against arbitrary concurrent registry writers. No stop/join/kill scheduler or runtime update authority added. Canonical backlog records source, package checks, review and publication.

## 2026-09-22: Preserve broker import-failure streaks

- WSP00/10/15/22/49/50/62/91/97; C3/I3/D3/Impact3=12/P2. Existing broker counter now survives repeated caught import errors and reaches threshold3; successful full launch handling or a caught non-import exception resets only the affected DAE.
- Preserve broad existing catch, events/finally, disabled admission and manual re-enable semantics. Same-file failure-transition extraction shrinks inherited class and oversized method; no new broker/module or process authority.
- Fixed baseline:9failed/4passed; candidate and independent replay:13passed, original3 lifecycle methods unchanged/deselected. Inert fixtures only; no service, real thread, provider or default database.
- Corrects the historical V1.2.5 completion claim in the [module ModLog](../ModLog.md); no measured live crash-loop/noise improvement is asserted. Exact source, manifest, checks and closure are in the canonical RSI backlog. Re-score after closure.

# dae_daemon TestModLog

## 2026-09-22: Seven persistence/acknowledgment characterization cases

- Reuse the existing observer file; preserve the original nine retry regressions and three observer methods exactly. Seven ordinary cases characterize six boundaries, including a separate raised-exception control; production methods are unchanged.
- Local and independent selected runs:16passed,3deselected, two plugin-configuration warnings. Same16cases overlap; no new crash, cross-process, live WRE/FAM or power-loss evidence.
- Run with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`: `python -B -m pytest modules/infrastructure/dae_daemon/tests/test_dae_observer.py -k test_event_store_ -q -o addopts= -p no:cacheprovider`. Exact interpreter, external temporary paths and JUnit are in the evidence receipts.
- Test command, frozen hashes, independent result and any failed attempts are bound in the current backlog evidence. Existing prior process-witness screening block remains unchanged; this uses ordinary pytest only.
- Compare returned versus raised store failure, record/append state after error and reopen, duplicate identity ambiguity and equal-count content mismatch. Do not promote a characterization pass into a durability or retained RSI claim.

## 2026-09-22: Fixed sequence-collision regression oracles

- Reuse `test_dae_observer.py`; nine new standalone cases, original three observer methods unchanged.
- Before repair:5pass/4fail under the frozen baseline runner; a separate real-lock collision witness timed out with recursive acquisition observed and its own child termination confirmed. Partial-write and volatile-listener witnesses characterized remaining defects.
- After repair: ordinary focused pytest9pass/3deselected, two configuration warnings; test IDs and assertions unchanged. Independent ordinary replay is recorded in the backlog, not added as unique test count.
- The broader candidate process-witness harness remains paused after automatic screening blocked review. No candidate actual-lock subprocess, crash-recovery, cross-process concurrency or live-runtime proof is claimed.
- Acceptance covers the existing retry method only; parity failures after failed attempts remain deliberate test assertions and an open durability obligation.

## V1.4.0 - Runtime Emitter Tests (2026-03-27)

**File**: `test_runtime_emitter.py`
- Validates `RuntimeEvent` dataclass strips None values, includes non-None
- Validates `emit()` writes JSONL, appends correctly
- Validates `emit_start()` returns monotonic time for duration tracking
- Validates `emit_success()` computes duration_ms correctly
- Validates `emit_failure()` includes error, truncates to 500 chars
- Validates continuity_id/parent_continuity_id propagation
- Validates mandatory fields present (surface, event_type, status, timestamp)
- Validates details dict stays compact (<2KB)

**Run**:
- `python -m pytest modules/infrastructure/dae_daemon/tests/test_runtime_emitter.py -q`

**Result**:
- `11 passed`

---

## V1.2.4 - Cursor-based observer follow tests (2026-03-18)

**Updated**: `test_dae_observer.py`
- validates `follow_events(...)` returns only events beyond a known cursor
- validates the observer emits a usable `next_cursor` for incremental polling

**Run**:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/infrastructure/dae_daemon/tests/test_dae_observer.py -q`

**Result**:
- `3 passed`

## V1.2.1 - Structured Action Details Test (2026-03-16)

**Created**: `test_dae_adapter.py`
- validates `CentralDAEAdapter.report_action(...)` preserves structured `details`
- validates the adapter still no-ops cleanly when DAEmon is absent

**Run**:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/infrastructure/dae_daemon/tests/test_dae_adapter.py -q`

**Result**:
- `2 passed`

## V1.0.0 - Initial Test Suite (2026-02-17)

**Created**: `test_schemas.py` — Layer 0 formal pytest tests (50+ assertions)
- TestDAEState: enum values, round-trips
- TestDAEEventType: lifecycle, cardiovascular, security event categories
- TestDAERegistration: defaults, round-trip, state serialization
- TestDAEEvent: auto-fields, deterministic IDs, different payload divergence, JSON serialization
- TestKillswitchReport: defaults, full field round-trip

**Integration tests**: Layers 1-7 validated via manual scripts during development.
All 50+ assertions passing. End-to-end smoke test covers full cardiovascular flow:
register -> start -> heartbeat -> cardiovascular observation -> security detach -> re-enable.

## V1.0.1 - Popup Alert Tests (2026-02-17)

**Updated**: Killswitch tests verify popup alert triggers on HIGH events.
MessageBoxW mocked to no-op in test environment.

## V1.2.0 - Runtime Launch Broker Tests (2026-03-15)

**Created**: `test_dae_launch_broker.py`
- Validates one-shot broker launches transition to `stopped`
- Validates launch failures transition to `crashed`
- Validates stop-capable DAEs can be started, reported, and stopped through the broker

**Run**:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/infrastructure/dae_daemon/tests/test_dae_launch_broker.py -q`

**Result**:
- `3 passed`

## V1.3.0 - DAEmon Observer Tests (2026-03-17)

**Created**: `test_dae_observer.py`
- validates recent event tail retrieval for a registered DAE
- validates live status snapshots combine registry state and recent event history

**Run**:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/infrastructure/dae_daemon/tests/test_dae_observer.py -q`

**Result**:
- `2 passed`
