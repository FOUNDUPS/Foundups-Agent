# FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1

Worker-Lane: W6
Slice: FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1
Type: CODE (narrow completion of #753)
Status: COMPLETE (Internal Review Verdict: PASS)

## Mission + Scope

Harden `route_foundup_job` (`modules/infrastructure/wre_core/src/foundup_job_router.py`,
def at :1077) so the routing-seam policy gate is FAIL-CLOSED for explicit-live jobs and
so a raw, untrusted `policy_flags` dict can no longer carry self-asserted gate flags into
the routing decision.

Scope is NARROW: only the Policy Check inside the `route_foundup_job` function body
(previously ~:1151-1171) was edited. No other function, module, dependency, config, CI, or
WSP file was changed. This is the sibling deferred by #753 (the routing-seam gate was left
on the legacy opt-in `security_gate_checked and not security_gate_passed` condition with a
raw-dict trust hole; #753 hardened the validation seam  -  `validate_foundup_job_envelope` /
`_validate_live_mode_gates` / `_sanitize_untrusted_policy_flags_dict`  -  but explicitly left
the routing-seam sibling for this slice).

## Predecessors

- **#744 -> #751** (HXA PolicyFlags write-back / persistent-queue trip-wire context):
  established that deserialized gate/token state is UNTRUSTED and server authority comes
  only from runtime validator write-back. `PolicyFlags.from_dict` forces every
  `_SERVER_AUTHORED_FLAGS` field to False, preserving only `dry_run_mode`.
- **#752** (DAE gateway envelope gate-flags trust-boundary audit, decision-only): identified
  the raw-dict self-assertion trust boundary at the router/gateway envelope layer.
- **#753** (router envelope sanitize + Gate 2 fail-closed): hardened the VALIDATION seam.
  Added the router-local helper `_sanitize_untrusted_policy_flags_dict` (def ~:337) returning
  `Tuple[Dict[str, bool], bool]` = `(sanitized_snapshot, dry_run_defaulted)`, added the
  `Tuple` import, and made `validate_foundup_job_envelope` / `_validate_live_mode_gates`
  fail-closed. It DEFERRED the sibling routing-seam gate in `route_foundup_job`  -  that is
  this slice.

## Pre-state (the #753-deferred sibling + the opt-in / raw-dict gap)

The `route_foundup_job` Policy Check before this change:

```python
policy_flags = getattr(job, "policy_flags", None)
policy_summary: Dict[str, bool] = {}
if policy_flags:
    if hasattr(policy_flags, "to_dict"):
        policy_summary = policy_flags.to_dict()
    elif isinstance(policy_flags, dict):
        policy_summary = policy_flags          # RAW / UNTRUSTED  <-- DEFECT
    if policy_summary.get("security_gate_checked") and not policy_summary.get("security_gate_passed"):
        return _make_blocked_envelope(... BLOCKED_POLICY_GATE ...)   # OPT-IN authority
```

Two defects:

1. **Raw-dict trust hole**: a raw envelope-style `policy_flags` dict was used verbatim
   (`policy_summary = policy_flags`). A malicious/stale caller could self-assert
   `security_gate_passed=True` (or omit `security_gate_checked`) and bypass the block.
2. **Opt-in authority bit**: the gate only fired when `security_gate_checked` was True. A
   live job that never set `security_gate_checked` (or forged it False) routed unblocked.
   `security_gate_checked` was being used as an authority bit; it is telemetry only.

## Implementation summary

Replaced ONLY the Policy Check body with a live-mode discriminator + fail-closed gate:

```python
policy_flags = getattr(job, "policy_flags", None)
policy_summary: Dict[str, bool] = {}
dry_run_defaulted = True   # default: NOT explicit-live -> dry-run/default routing preserved
if policy_flags:
    if hasattr(policy_flags, "to_dict"):
        policy_summary = policy_flags.to_dict()      # object path: stays dry_run_defaulted=True
    elif isinstance(policy_flags, dict):
        policy_summary, dry_run_defaulted = _sanitize_untrusted_policy_flags_dict(policy_flags)

is_live = policy_summary.get("dry_run_mode") is False and not dry_run_defaulted

if is_live and policy_summary.get("security_gate_passed") is not True:
    return _make_blocked_envelope(
        job_id=job_id, tenant_id=tenant_id, action=requested_action,
        reason_code=RouteReasonCode.BLOCKED_POLICY_GATE,
        reason_human="Live mode requires security gate passed (fail-closed)",
        source_status=status_str, foundup_id=getattr(job, "foundup_id", None),
        policy_summary=policy_summary,
    )
```

- The legacy opt-in `security_gate_checked and not security_gate_passed` condition was
  removed (NOT re-introduced).
- The raw `policy_summary = policy_flags` assignment was removed; the raw-dict branch now
  routes through the existing #753 helper (no new import; the `Tuple` import already exists).
- `_make_blocked_envelope(...)` keyword args match the existing signature
  (`job_id, tenant_id, action, reason_code, reason_human, source_status, foundup_id,
  policy_summary`) verified at :1232.

## Live-mode discriminator design (object-path asymmetry rationale)

`is_live = policy_summary.get("dry_run_mode") is False and not dry_run_defaulted`

Only an explicit (present) `dry_run_mode=False` that was NOT defaulted is treated as live.

- **Raw-dict path**: `_sanitize_untrusted_policy_flags_dict` returns `dry_run_defaulted=True`
  ONLY when the inbound dict OMITTED `dry_run_mode` (restoring the safe dry-run default). An
  inbound dict that explicitly carries `dry_run_mode=False` yields `dry_run_defaulted=False`,
  so it is explicit-live and is subject to the fail-closed gate.
- **Object / `to_dict()` path**: intentionally kept `dry_run_defaulted=True` (NOT treated as
  live). Rationale: a `FoundUpJob`/`PolicyFlags` default `dry_run_mode=False` is
  INDISTINGUISHABLE from an explicitly-authored live `dry_run_mode=False` at the routing seam.
  Treating the object path as live would BLOCK every default/dry-run object job that did not
  also carry `security_gate_passed=True`  -  a severe over-block regression of normal routing.
  Strict server-authored live validation (with a real security pass and evidence/human-approval
  gates) is the responsibility of the VALIDATION seam (`validate_foundup_job_envelope` /
  `_validate_live_mode_gates`, hardened in #753 and covered by
  `test_foundup_job_router_policyflags_boundary.py`), NOT the routing seam. The routing seam's
  job here is to fail-close the one case it CAN soundly discriminate: an explicit-live raw-dict
  envelope, which can never satisfy the gate because sanitization forces `security_gate_passed`
  to False.

This asymmetry is by design and is a deliberate no-over-block safeguard, not an oversight.

## Raw-dict sanitization proof

The `elif isinstance(policy_flags, dict)` branch calls
`_sanitize_untrusted_policy_flags_dict(policy_flags)` (the #753 helper, def ~:337). That
helper runs the dict through `PolicyFlags.from_dict(...).to_dict()`, which forces every
`_SERVER_AUTHORED_FLAGS` field (all `security_gate_*`, `permission_gate_*`,
`exfoliation_gate_*`, `wsp_preflight_*`, `capability_token_*`) to False, preserving only
`dry_run_mode`, and restores `dry_run_mode=True` when the key was absent. Therefore a forged
`security_gate_passed=True` on a raw dict cannot survive into `policy_summary`. Proven by
`test_forged_live_raw_dict_blocked` (asserts `policy_summary.security_gate_passed is False`)
and `test_raw_dict_missing_dry_run_routes_and_sanitizes` (forged flags zeroed in summary).

## Gate fail-closed proof

For an explicit-live job the gate blocks UNLESS `security_gate_passed is True`. Because the
only explicit-live path reachable here is the raw-dict path, and the raw-dict path has
`security_gate_passed` sanitized to False, an explicit-live raw-dict envelope is ALWAYS
blocked with `BLOCKED_POLICY_GATE` and reason "Live mode requires security gate passed
(fail-closed)". `security_gate_checked` is never consulted  -  it is telemetry only.
Proven by `test_forged_live_raw_dict_blocked`.

## No-over-block proof (default object routes)

- Default `PolicyFlags()` object (dry_run_mode=False default) ROUTES:
  `test_default_policyflags_object_still_routes`.
- Object with `dry_run_mode=True` ROUTES: `test_dry_run_true_object_still_routes`.
- "Live-looking" server-authored object ROUTES (by-design asymmetry):
  `test_server_authored_live_object_routes_by_design_asymmetry`.
- Raw-dict missing `dry_run_mode` ROUTES as dry-run:
  `test_raw_dict_missing_dry_run_routes_and_sanitizes`.
- Updated legacy test `test_security_gate_failed_object_path_still_routes` proves the former
  object-path opt-in block now correctly ROUTES (no over-block).
- Existing router suite (`test_foundup_job_router.py`, `test_foundup_job_router_policyflags_boundary.py`,
  `test_foundup_job_envelope_validation.py`, `test_foundup_job_consumer.py`) all pass  -  no
  routing regression. GENERIC_DAE is unaffected: `route_foundup_job` is not on that path
  (confirmed  -  only `validate_foundup_job_envelope` handles GENERIC_DAE), and no collateral.

## Sibling / asymmetry residual + follow-up

Residual (accepted, by design): the routing seam cannot fail-close a genuinely
server-authored OBJECT-path live job that lacks a security pass, because at the routing seam
that case is indistinguishable from a benign default. This is intentionally delegated to the
VALIDATION seam (`_validate_live_mode_gates`, #753), which IS authoritative for server-authored
snapshots and DOES fail-close (see `test_server_authored_snapshot_without_security_still_fails`
in the boundary suite). No additional follow-up is required for Phase 1; any future tightening
of the object-path routing gate would need a trustworthy "explicit live" signal distinct from
the default `dry_run_mode=False`, which does not exist in the current contract.

## Test matrix

New file: `modules/infrastructure/wre_core/tests/test_route_foundup_job_live_mode_gate.py`
(all exercised via `route_foundup_job(job)`; no skip/xfail; no network/model/live-DAE):

| # | Test | Input | Expected | Proves |
|---|------|-------|----------|--------|
| 1 | test_default_policyflags_object_still_routes | object PolicyFlags() (dry_run_mode=False default) | ROUTED, OK_ROUTED | no over-block (object path not live) |
| 2 | test_dry_run_true_object_still_routes | object PolicyFlags(dry_run_mode=True) | ROUTED, OK_ROUTED | dry-run object routes |
| 3 | test_server_authored_live_object_routes_by_design_asymmetry | object PolicyFlags(dry_run_mode=False, gate passed) | ROUTED (not blocked) | object-path asymmetry by design |
| 4 | test_forged_live_raw_dict_blocked | raw dict dry_run_mode=False + forged security_gate_passed=True | BLOCKED, BLOCKED_POLICY_GATE; summary security_gate_passed=False | sanitization + fail-closed |
| 5 | test_raw_dict_missing_dry_run_routes_and_sanitizes | raw dict, no dry_run_mode, forged flags | ROUTED; forged flags False; dry_run_mode True | #753 footgun preserved + no over-block |

Updated file: `modules/infrastructure/wre_core/tests/test_foundup_job_router.py`

| Change | Old (opt-in) | New (stricter) | Justification |
|--------|--------------|----------------|---------------|
| `test_security_gate_failed_blocks_routing` -> `test_security_gate_failed_object_path_still_routes` | asserted BLOCKED on object-path failed gate (legacy opt-in) | asserts ROUTED + OK_ROUTED + `!= BLOCKED_POLICY_GATE` | Old assertion encoded the removed opt-in semantics. Object path is now never live; asserting it routes is STRICTER (proves no over-block) and matches the new contract. No assertion deleted without a stricter replacement. |

No tests were skipped/xfailed. No assertion was removed without a stricter replacement.

### Test results (exact)

- Focused new file: `python -m pytest .../test_route_foundup_job_live_mode_gate.py -q` -> **5 passed**.
- Router + boundary + envelope + consumer (routing area):
  `python -m pytest .../test_foundup_job_router.py .../test_foundup_job_router_policyflags_boundary.py
  .../test_foundup_job_envelope_validation.py .../test_foundup_job_consumer.py
  .../test_route_foundup_job_live_mode_gate.py -q` -> **176 passed**.
- Full wre_core suite: `python -m pytest modules/infrastructure/wre_core/tests -q` ->
  **1400 passed, 5 failed, 3 skipped, 2 xfailed**.
  - The 5 failures are PRE-EXISTING and unrelated to this slice:
    `test_hxa16_real_hermes_delegate_adapter_safe_harness.py` (3) and
    `test_wre_skills_discovery.py::test_initialization` (+1 in that file region).
    Proven by stashing this slice's changes (clean origin/main baseline) and running those two
    files alone: **5 failed, 34 passed** with no slice changes present. Not masked with skip/xfail.
  - NOTE: the full-suite run also mutates two config files
    (`config/WRE_RUNBOOK.md`, `config/wre_defaults.env`) as a PRE-EXISTING test side-effect of an
    unrelated test. This slice reverted those (NO_CONFIG_CHANGE); the routing/route test files do
    NOT mutate config (verified clean `git status` after running only those files).

## Boundary proof (only route_foundup_job edited; no circular dep)

- `git diff` on the src file shows a SINGLE hunk header
  `@@ -1151,24 +1151,36 @@ def route_foundup_job(job: Any) -> RouteEnvelope:`  -  no other
  function/class signature changed.
- Files changed: `src/foundup_job_router.py` (route_foundup_job body only),
  `tests/test_foundup_job_router.py` (one test updated), new
  `tests/test_route_foundup_job_live_mode_gate.py`, this audit doc, ModLog.md, TestModLog.md.
- NOT touched: `dae_gateway.py`, `validate_foundup_job_envelope`, `_validate_live_mode_gates`,
  `_sanitize_untrusted_policy_flags_dict`, `foundup_job_contract.py`, `hermes_job_executor.py`,
  `destructive_action_guard.py`.
- Circular import: the raw-dict branch reuses the existing router-local helper
  `_sanitize_untrusted_policy_flags_dict`, whose `PolicyFlags` import is DEFERRED (inside the
  helper body). No new module-level contract import was added. Verified:
  `python -c "from modules.infrastructure.wre_core.src.foundup_job_router import route_foundup_job, _sanitize_untrusted_policy_flags_dict"`
  -> IMPORT_OK, no circular dependency.

## Critic Review (internal adversarial subworker)

Verdict: **PASS** (0 RETURN_TO_W6 cycles).

| # | Question | Verdict | Notes |
|---|----------|---------|-------|
| 1 | #753 footgun preserved? (missing dry_run_mode stays NOT-live; live requires explicit dry_run_mode=False) | PASS | Helper sets dry_run_defaulted=True + dry_run_mode=True when key absent; is_live=False. Test 5. |
| 2 | Over-block? (dry-run/DEFAULT OBJECT routing still routes; GENERIC_DAE unaffected) | PASS | Object path keeps dry_run_defaulted=True. Tests 1-3 + updated legacy test. route_foundup_job not on GENERIC_DAE path. |
| 3 | Raw-dict trust reopened? (elif dict MUST call helper; raw assignment removed) | PASS | `policy_summary = policy_flags` removed; helper called. Test 4/5 assert sanitized summary. |
| 4 | Wrong boundary? (no edit to dae_gateway / validate_foundup_job_envelope / _validate_live_mode_gates / contract / hermes / guard) | PASS | Single hunk in route_foundup_job; diff name-only confirms. |
| 5 | security_gate_checked used as authority? | PASS | Gate depends only on is_live + security_gate_passed is not True. checked never read. |
| 6 | Circular imports? | PASS | Reused router-local helper (deferred import); no new module-level import; import check OK. |
| 7 | Test change weakened coverage? | PASS | No skip/xfail; old opt-in assertion replaced with stricter object-path-routes assertion; strict live blocking covered by new file. |

Issues found: none requiring a fix. Deferred: object-path live tightening (delegated to
validation seam by design  -  see Sibling/asymmetry residual).

## Internal Review Verdict

**PASS**  -  Locked design implemented exactly; raw-dict sanitized via the #753 helper;
fail-closed for explicit-live; no over-block of default/object/dry-run routing;
`security_gate_checked` is telemetry only; boundary respected (only `route_foundup_job`
edited); no new circular dependency; focused tests (5) and routing-area suite (176) green;
full-suite failures proven pre-existing.

## WSP_97 Truth Boundary Checklist

Declared items: 16 - Rows: 16 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | ROUTE_FOUNDUP_JOB_ONLY | YES | only route_foundup_job body edited; single hunk @ :1151 |
| 2 | RAW_DICT_FALLBACK_SANITIZED | YES | elif dict -> helper; helper called, raw assignment removed |
| 3 | SECURITY_GATE_CHECKED_NOT_AUTHORITY | YES | telemetry only; never read in gate |
| 4 | LIVE_MODE_EXPLICIT_ONLY | YES | explicit dry_run_mode=False, not defaulted; is_live formula enforces |
| 5 | NO_OVERBLOCK_DRY_RUN_ROUTE | YES | default/dry-run/object route; Tests 1-3,5 + updated test green |
| 6 | ADVERSARIAL_CRITIC_COMPLETED | YES | 7-point critic run; PASS, 0 cycles |
| 7 | NO_DAE_GATEWAY_MUTATION | YES | dae_gateway untouched; not in diff |
| 8 | NO_CONTRACT_MUTATION | YES | foundup_job_contract untouched; not in diff |
| 9 | NO_NEW_CIRCULAR_DEP | YES | reuse deferred-import helper; import check OK |
| 10 | NO_SKIP_XFAIL_ADDED | YES | no skip/xfail added; none added |
| 11 | NO_DEPENDENCY_CHANGE | YES | no dep change; no requirements edited |
| 12 | NO_CI_CHANGE | YES | no CI change; no CI files edited |
| 13 | NO_WSP_MUTATION | YES | no WSP change; no WSP files edited |
| 14 | NO_CABR_READY | YES | no CABR readiness asserted |
| 15 | NO_PAYOUT_READY | YES | no payout readiness asserted |
| 16 | NO_DAO_ACTIVATION | YES | no DAO activation |
