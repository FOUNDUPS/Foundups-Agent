# DJ — AI_RESOLUTION_HOOK_CONTRACT_PHASE1 (Completion Report)

**Date**: 2026-04-19
**Worker**: DJ
**WSP**: 97 (truthful state distinction), 77 (agent coordination)
**Scope**: Option A (from architect) — dispatch contract + DEP-SECURITY + WSP-FRAMEWORK only.
**Deferred**: DJ-OBS (AntifaFM OBS-start emitter) until AF1 read-only audit completes.

---

## Goal

Add one structured AI-resolution dispatch contract for preflight failures that today log and continue. AI Overseer is initialized at boot (visible in logs) but nothing was handed off to it.

## Problem (from boot log, 2026-04-19 06:44)

```
[DEP-SECURITY] preflight=FAIL (fresh) critical=4 high=4 unknown=3 tool_failures=0
[WSP-FRAMEWORK] preflight=FAIL (fresh) drift=0 framework_only=1 knowledge_only=0 index_issues=1
```

Both emit to console, both set the process return code, neither route to the
`[AI-OVERSEER] ... initialized` daemon that could triage them.

## Architecture

```
preflight emitter  --on_preflight_fail(component, severity, payload)-->  ai_overseer
                                             |
                                             +-- pattern recall (wre_core/pattern_memory, graceful fallback)
                                             +-- AI proposal     (qwen/gemma,           graceful fallback)
                                             +-- durable artifact (alerts/preflight/*.json)
                                             +-- escalate if severity in {critical, high} or requires_012
```

Single entry point. Never raises. LLM-unavailable path returns a valid event
with `state="skipped"`.

## Files

| File | Change |
|---|---|
| `modules/ai_intelligence/ai_overseer/src/preflight_resolution.py` | new, dispatch contract + event dataclass |
| `modules/ai_intelligence/ai_overseer/tests/test_preflight_resolution.py` | new, 12 tests |
| `modules/ai_intelligence/ai_overseer/tests/conftest.py` | allowlist += `test_preflight_resolution.py` |
| `modules/ai_intelligence/ai_overseer/ModLog.md` | DJ phase entry prepended |
| `main.py` | DEP-SECURITY + WSP-FRAMEWORK emitters wired (try/except import, non-fatal) |

## Boot-log signal → dispatch mapping

| Boot-log signal | Source | Component key | Severity rule | Escalation |
|---|---|---|---|---|
| `[DEP-SECURITY] preflight=FAIL ... critical=N high=M` | `main.run_dependency_security_preflight` | `dep_security` | `critical` if N>0, else `high` if M>0, else `medium` | auto-escalate on critical/high |
| `[WSP-FRAMEWORK] preflight=FAIL ... drift=D framework_only=F index_issues=I` | `main.run_wsp_framework_preflight` | `wsp_framework` | `high` if D+F+I > 0 else `medium` | auto-escalate on high |

## WSP 97 state machine

```
detected     - emitter observed failure
dispatched   - event artifact written
proposed     - AI proposed remediation (never applied)
escalated    - severity or payload flag requires 012
skipped      - LLM/PatternMemory unavailable; deterministic event only
```

Each `alerts/preflight/<component>_<UTC>.json` reflects the final state.
The report strictly distinguishes **proposed** from **applied** — nothing is
applied in Phase 1.

## Acceptance

| Criterion | Status |
|---|---|
| DEP-SECURITY failure emits AI resolution event | ✅ wired in `main.py`, test asserts dispatcher call |
| WSP-FRAMEWORK failure emits AI resolution event | ✅ wired in `main.py`, test asserts dispatcher call |
| OBS-start emitter (requires_012 / automation_candidate) | ⏸ **deferred to DJ-OBS**, reason below |
| Existing logs remain | ✅ no `print`/`logger` lines removed; dispatch is additive |
| Durable artifact `alerts/preflight/*.json` | ✅ written on each dispatch |
| Tests mock each emitter and assert dispatch | ✅ `test_main_py_dep_security_calls_dispatcher`, `test_main_py_wsp_framework_calls_dispatcher` |
| Tests prove no fix applied | ✅ `test_no_fix_is_auto_applied` |
| LLM-unavailable path still works | ✅ `test_ai_unavailable_path_returns_valid_event` |
| Dispatch never raises | ✅ `test_dispatch_never_raises_even_on_internal_error` |

## Deferral note — DJ-OBS

**OBS-start emitter deferred to DJ-OBS after AF1 read-only AntifaFM readiness audit.**

Rationale: AF1 is a read-only audit of `modules/platform_integration/antifafm_broadcaster/`.
Wiring a dispatch call into `obs_controller.py` during DJ would contaminate that
audit surface. The dispatch contract is fully proven with 2 emitters; the OBS
branch can adopt it verbatim once AF1 confirms AntifaFM boundary stability.

## Out of scope (future slices)

- Chrome 9222 auto-start (DJ2)
- `google.generativeai` deprecation migration hook (DJ2)
- WRE dashboard WARN tier for `samples=0/25` (DJ2)
- IRONCLAW `preflight=SKIP` intentional-skip validation (DJ2)
- Actual OBS modal-click automation (DJ-OBS or Hermes)
- Orphan process reaper (unregistered python.exe survives heartbeat) — DJ3 candidate

## Verification

```
pytest modules/ai_intelligence/ai_overseer/tests/test_preflight_resolution.py -v
============================= 12 passed in 4.18s ==============================
```

No other tests touched. No runtime mutation introduced. Dispatch activates on
next `main.py` restart — current running `main.py` (PID 87616) keeps its
loaded bytecode and is unaffected.

## Next slice gates

- **AF1** — read-only AntifaFM internal-operational-readiness audit
- **DJ-OBS** — gated on AF1, wires the OBS-start emitter using the now-proven contract
- **DJ2** — other detection-without-resolution emitters from WSP 97 sweep
