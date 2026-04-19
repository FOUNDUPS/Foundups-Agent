# AF2 — AntifaFM OBS Failure Escalation Spec (Phase 1)

**Date**: 2026-04-19
**Window**: CW2
**Slice**: AF2
**Lane**: AF
**Mode**: read-only spec
**Depends on**: AF1 (INTERNAL_NOT_READY verdict, OBS gap identified)
**Files edited**: none
**Live systems touched**: none

---

## Objective

Define the OBS inactive-output failure hook specification. Produce the event schema,
remediation ordering, DJ-OBS implementation contract, and test plan so DJ-OBS can
implement without ambiguity.

## OBS Failure Branch Mapping

| Field | Value |
|-------|-------|
| File | `modules/platform_integration/antifafm_broadcaster/src/obs_controller.py` |
| Method | `OBSController.start_streaming()` |
| Lines | 325-395 |
| Timeout branch | Lines 376-390 |
| Error code | `stream_output_inactive_after_start` |
| Current behavior | Logs error, sets `self.last_start_error`, returns `False` |
| Missing behavior | No structured dispatch to `on_preflight_fail()` |

### Timeout Branch Code (lines 376-390)

```python
reconnecting = bool(getattr(last_status, "output_reconnecting", False))
output_bytes = getattr(last_status, "output_bytes", 0)
output_duration = getattr(last_status, "output_duration", 0)

self.last_start_error = "stream_output_inactive_after_start"
logger.error(
    "[OBS] Start stream request was accepted but output never became active "
    f"within {verify_timeout_s:.1f}s "
    f"(reconnecting={reconnecting}, bytes={output_bytes}, duration={output_duration}ms)."
)
logger.error(
    "[OBS] Likely waiting on YouTube broadcast setup modal in OBS. "
    "If visible, click 'Create broadcast and start streaming'."
)
return False
```

## Dispatch Infrastructure Summary

The dispatch contract already exists and is production-tested:

| Component | Location | Status |
|-----------|----------|--------|
| `on_preflight_fail()` | `modules/ai_intelligence/ai_overseer/src/preflight_resolution.py` | 231 lines, operational |
| Test suite | `modules/ai_intelligence/ai_overseer/tests/test_preflight_resolution.py` | 12 tests, all passing |
| Emitter: dep_security | `main.py:~537` | Wired, tested |
| Emitter: wsp_framework | `main.py:~908` | Wired, tested |
| Emitter: obs_start | Not yet wired | **DJ-OBS target** |
| PR #383 | `feat/dj-ai-resolution-hook-contract-phase1` | OPEN (dispatch contract) |

State machine: `detected → dispatched/skipped/proposed → escalated`

## Event Contract

DJ-OBS emitter call signature:

```python
from modules.ai_intelligence.ai_overseer.src.preflight_resolution import on_preflight_fail

result = on_preflight_fail(
    component="obs_start",
    severity="high",
    payload={
        "error_code": "stream_output_inactive_after_start",
        "timeout_s": verify_timeout_s,
        "reconnecting": reconnecting,
        "output_bytes": output_bytes,
        "output_duration": output_duration,
        "output_active": False,
        "last_status_raw": str(last_status) if last_status else None,
        "stream_service_type": getattr(self, '_last_stream_service_type', None),
        "automation_candidate": True,
        "requires_012": False,
    },
    source="obs_controller:start_streaming",
)
```

### Payload Fields (17)

| # | Field | Type | Source |
|---|-------|------|--------|
| 1 | `error_code` | str | Hardcoded: `stream_output_inactive_after_start` |
| 2 | `timeout_s` | float | `verify_timeout_s` parameter |
| 3 | `reconnecting` | bool | `last_status.output_reconnecting` |
| 4 | `output_bytes` | int | `last_status.output_bytes` |
| 5 | `output_duration` | int | `last_status.output_duration` (ms) |
| 6 | `output_active` | bool | Always `False` at this branch |
| 7 | `last_status_raw` | str/None | String repr of last OBS status |
| 8 | `stream_service_type` | str/None | Current OBS stream service type |
| 9 | `automation_candidate` | bool | `True` (steps 1-3 are autonomous) |
| 10 | `requires_012` | bool | `False` initially; dispatch contract auto-escalates on severity=high |
| 11 | `component` | str | `obs_start` (passed to dispatcher) |
| 12 | `severity` | str | `high` (passed to dispatcher) |
| 13 | `source` | str | `obs_controller:start_streaming` |
| 14 | `state` | str | Set by dispatcher (escalated for high severity) |
| 15 | `requires_012` (event) | bool | Set by dispatcher (True for high severity) |
| 16 | `artifact_path` | str | Set by dispatcher (alerts/preflight/*.json) |
| 17 | `detected_at` | str | Set by dispatcher (UTC ISO timestamp) |

Note: Fields 11-17 are set by the dispatch contract, not the emitter. The emitter provides fields 1-10 via the `payload` dict plus `component`, `severity`, and `source` as top-level arguments.

## Remediation Plan (Future — NOT part of DJ-OBS)

| Step | Action | Autonomous? | Implementation |
|------|--------|-------------|----------------|
| 1 | Create broadcast + bind stream | Yes | `YouTubeBroadcastManager.create_live_broadcast()` |
| 2 | Set OBS to `rtmp_custom` service | Yes | `OBSController.ensure_stream_service_custom()` |
| 3 | Retry `start_streaming()` | Yes | Re-invoke with fresh timeout |
| 4 | Click YouTube modal in OBS | **No — requires 012** | Manual intervention or UI automation |

Steps 1-3 are autonomous remediation candidates. Step 4 is the hard floor —
YouTube's "Create broadcast and start streaming" modal cannot be dismissed
programmatically without UI automation infrastructure that does not yet exist.

## DJ-OBS Implementation Contract

### MUSTs

1. **MUST** add a single `on_preflight_fail()` call in `obs_controller.py:start_streaming()` timeout branch (between line 389 and `return False` at line 390)
2. **MUST** use `try/except` import for `on_preflight_fail` — failure to import must not break OBS operation
3. **MUST** set `severity="high"` and `automation_candidate=True`
4. **MUST** pass all diagnostic fields from the timeout branch into `payload`

### MUST NOTs

1. **MUST NOT** edit `preflight_resolution.py` or any `ai_overseer` source files
2. **MUST NOT** edit `main.py`
3. **MUST NOT** implement any remediation logic (steps 1-4 above)
4. **MUST NOT** modify existing log lines or error codes
5. **MUST NOT** change `return False` behavior — dispatch is additive

### MAYs

1. **MAY** log the dispatch result at DEBUG level
2. **MAY** read `self._last_stream_service_type` if available, or pass `None`

## DJ-OBS Test Plan (6 required tests)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_obs_timeout_calls_dispatcher` | Mock `on_preflight_fail`, simulate timeout branch, verify called with `component="obs_start"` |
| 2 | `test_obs_timeout_payload_fields` | Verify payload contains `error_code`, `timeout_s`, `reconnecting`, `output_bytes`, `output_duration` |
| 3 | `test_obs_timeout_severity_is_high` | Verify `severity="high"` |
| 4 | `test_obs_timeout_automation_candidate_true` | Verify `payload["automation_candidate"] is True` |
| 5 | `test_obs_dispatch_import_failure_is_nonfatal` | Patch import to raise `ImportError`, verify `start_streaming()` still returns `False` without raising |
| 6 | `test_obs_dispatch_failure_is_nonfatal` | Patch `on_preflight_fail` to raise, verify `start_streaming()` still returns `False` without raising |

Test location: `modules/platform_integration/antifafm_broadcaster/tests/test_obs_preflight_dispatch.py`

Mocking pattern: Follow existing tests in `test_preflight_resolution.py` — mock the dispatcher, not the OBS WebSocket.

## Verdict

**DJ-OBS_READY**

The dispatch contract is proven (12 tests, 2 emitters). The insertion point is
unambiguous (obs_controller.py:376-390). The event schema is fully specified.
DJ-OBS is a bounded emitter addition — no infrastructure work required.

---

**WSP**: WSP 15 (pre-action verification), WSP 22 (ModLog), WSP 97 (no overclaiming)
**Generated**: 2026-04-19
**Agent**: 0102 (Claude Opus 4.6), CW2
