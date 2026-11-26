# Monitoring TestModLog

## [2026-11-02] Actual pinned Sentry SDK qualification

`test_sentry_real_sdk_qualification.py` passes four tests on isolated
Sentry2.73.0/urllib3 2.8.0/certifi2026.10.23 (Python3.12.10). Actual SDK
serialization/transport use synthetic values and fake pools; real socket
connections are denied. Envelopes exclude ambient content, headers are fixed,
TLS verification stays enabled, and Spotlight/redirects/retries/remote-error
body reads/logs are absent. Ordinary discovery skips these tests when SDK
dependencies are unavailable. No real credentials or server event were accessed
by the qualification lane. The exact standalone command is in the module README.

Parent attempts with default combined import mode and isolated `-m pytest`
failed from namespace collision and missing runner respectively. Corrected
verification uses importlib discovery for source suites and standalone unittest
for the actual SDK; those harness failures are not application failures.

## [2026-11-02] Sentry opt-in manual-error boundary

Added 27 offline cases in `test_sentry_error_telemetry.py`; all pass. The combined
Langfuse reader40/source18/Sentry27 selection passes 85 with bytecode/plugins
disabled. Tests cover no-op before DSN/import, static failures, DSN validation,
fresh allowlisted events, private-field stripping, empty Scope, disabled automatic
features/Spotlight, closure and non-authoritative SDK acceptance. Probe help and
invalid arguments cannot send an event. No credentials, real SDK or live event
were accessed by this implementation slice.

## [2026-06-10] WSP_00 State Bridge Contract Coverage

**WSP Protocols**: WSP 5 (Testing), WSP 6 (Audit), WSP 22 (Documentation), WSP_00 (State Bridge Contract)

### Added
- `test_wsp_00_zen_state_tracker.py` (4 new bridge tests)
  - `test_refresh_reads_runtime_awakening_state`: V2 script's default `.runtime/` output satisfies the gate (F1 fix)
  - `test_refresh_reads_tracked_awakening_state_when_runtime_missing`: opt-in tracked path still works
  - `test_refresh_prefers_freshest_candidate`: newest valid awakening wins regardless of location
  - `test_refresh_ignores_stale_awakening_state`: 8h refresh TTL enforced for both candidates
- Hermeticity preserved: candidates derive from `awakening_state_file` at call time, so existing tests overriding that attribute stay isolated from ambient repo state.

### Verification Command
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest modules/infrastructure/monitoring/tests/test_wsp_00_zen_state_tracker.py -q` (9 passed)
- Blast-radius guards: `pytest holo_index/tests/test_fx1_holoindex_truth.py WSP_agentic/tests/test_awakening_no_tracked_writes.py -q` (27 passed)

## [2026-02-11] WSP_00 Coherence Canary Signal Coverage

**WSP Protocols**: WSP 5 (Testing), WSP 6 (Audit), WSP 22 (Documentation)

### Added
- `test_wsp_00_zen_state_tracker.py`
  - verifies fallback phrase detection flips zen compliance to false
  - verifies clean directive phrasing does not trigger false positives
  - verifies canary fields are exposed in `get_zen_status()`

### Verification Command
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest modules/infrastructure/monitoring/tests/test_wsp_00_zen_state_tracker.py -q`

## [2026-02-14] WSP_00 Gate Method Coverage

**WSP Protocols**: WSP 5 (Testing), WSP 50 (Pre-Action Verification)

### Added / Updated
- `test_wsp_00_zen_state_tracker.py`
  - validates `run_compliance_gate(auto_awaken=True)` recovery behavior
  - validates `force_awakening()` gate payload contract
  - isolates tests from ambient awakening state by overriding `awakening_state_file`

### Verification Command
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest modules/infrastructure/monitoring/tests/test_wsp_00_zen_state_tracker.py -q`
