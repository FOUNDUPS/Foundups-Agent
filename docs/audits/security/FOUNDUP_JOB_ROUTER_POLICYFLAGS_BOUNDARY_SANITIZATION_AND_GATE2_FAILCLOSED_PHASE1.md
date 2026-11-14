# FOUNDUP_JOB_ROUTER_POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED_PHASE1

**Worker-Lane**: W6
**Slice**: FOUNDUP_JOB_ROUTER_POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED_PHASE1
**WSP**: WSP 97 (Truth Boundary), WSP 50 (Pre-Action), WSP 22 (ModLog), WSP 5 (Test Coverage)
**Base**: `origin/main` @ `f3b0293e5`
**Scope**: ROUTER BOUNDARY ONLY — `modules/infrastructure/wre_core/src/foundup_job_router.py` (+ its test/ModLog/audit).

---

## 1. Mission

Close the #752 bounded trust-boundary defect at the ROUTER boundary only:

1. Sanitize raw-dict envelope `policy_flags` so a caller cannot self-assert server-authored
   gate/token flags (e.g. `security_gate_passed=True`).
2. Preserve the safe dry-run default (an absent `dry_run_mode` must NOT be treated as live).
3. Make live-mode Gate 2 (security) FAIL-CLOSED: in live mode, security MUST have passed.

Edit ONLY the router file and its tests/ModLog/audit. Do NOT touch `dae_gateway.py`,
`foundup_job_contract.py`, `hermes_job_executor.py`, or `destructive_action_guard.py`.

---

## 2. Predecessors / Context

- **#752** (`docs/audits/security/DAE_GATEWAY_ENVELOPE_GATEFLAGS_TRUST_BOUNDARY_AUDIT_PHASE1.md`):
  decision-only audit of the gate-flags trust boundary at the DAE gateway envelope surface;
  identified the bounded router-side defect remediated here.
- **#744 → #746 → #747 → #751**: the PolicyFlags write-back / deserialization-chokepoint line of
  work. #747 established `PolicyFlags.from_dict` as the single deserialization chokepoint that
  zeroes all `_SERVER_AUTHORED_FLAGS` and preserves only `dry_run_mode`; #746 closed the
  Hermes executor write-back path. This slice reuses that same chokepoint (`from_dict`) to
  sanitize the router's raw-dict envelope branch.

The router's `validate_foundup_job_envelope` consumes a **raw envelope dict** (untrusted), which
the #747 chokepoint did NOT cover — that chokepoint runs on `FoundUpJob` deserialization, not on
the router's loose envelope-dict path. This slice plugs that bounded gap.

---

## 3. Pre-State Defect (origin/main @ f3b0293e5)

In `validate_foundup_job_envelope` (`def :337`):

- `:413 if policy_flags is None:` → `dry_run_defaulted=True`, `policy_snapshot={"dry_run_mode": True}` (SAFE).
- `:420 elif isinstance(policy_flags, dict):` → **`policy_snapshot = policy_flags` (RAW/UNSANITIZED — THE DEFECT)**.
  A caller's raw dict carrying `security_gate_passed=True` / `capability_token_validated=True`
  flowed straight into the snapshot used by the live-mode gate.
- `:428 elif hasattr(policy_flags, "to_dict"):` → server-authored `PolicyFlags` object (trusted).
- `:435 is_live_mode = policy_snapshot.get("dry_run_mode") is False and not dry_run_defaulted`.

Gate 2 in `_validate_live_mode_gates` (`def :549`):

- `:588 security_gate_checked = policy_snapshot.get("security_gate_checked", False)`
- `:589 security_gate_passed = policy_snapshot.get("security_gate_passed", False)`
- `:591 if security_gate_checked and not security_gate_passed:` → **OPT-IN (THE DEFECT)**.
  A caller could simply omit `security_gate_checked` (or set it False) and the security gate was
  never enforced; combined with the unsanitized raw dict, a caller could also forge a pass.

---

## 4. Implementation Summary

Three changes, exactly per the locked design. The object branch (`:428-432`) and the None branch
(`:413-419`) are unchanged.

**CHANGE 1 — Sanitization helper (NEW)** — `_sanitize_untrusted_policy_flags_dict(policy_flags) -> Tuple[Dict[str, bool], bool]`:
- Deferred import (inside the function) of `PolicyFlags` from
  `modules.communication.moltbot_bridge.src.foundup_job_contract`, matching the existing deferred
  cross-module import pattern in this module (`route_foundup_job` `:1073`). No module-level import
  added → no new circular dependency.
- `sanitized = PolicyFlags.from_dict(policy_flags).to_dict()` — zeroes ALL `_SERVER_AUTHORED_FLAGS`,
  preserves explicit `dry_run_mode`.
- `dry_run_defaulted = "dry_run_mode" not in policy_flags`; if defaulted, restore
  `sanitized["dry_run_mode"] = True` (because `from_dict({})` yields `dry_run_mode=False`).
- Returns `(sanitized, dry_run_defaulted)`.

**CHANGE 2 — Dict branch uses the helper** (`:420-427`):
- `policy_snapshot, dry_run_defaulted = _sanitize_untrusted_policy_flags_dict(policy_flags)`.
- The existing `[WSP97] ... missing dry_run_mode - defaulted to True` log is retained, fired when
  `dry_run_defaulted` is True.

**CHANGE 3 — Gate 2 fail-closed** (`:587-592`):
- `if not security_gate_passed: missing_gates.append("security_gate_passed")` (+ log-only line
  recording `security_gate_checked`). The legacy `security_gate_checked` opt-in is no longer a
  precondition. Docstring updated: "security_gate_passed=True (required in live mode)".

**CHANGE 4 — Sibling `route_foundup_job` (`:1017`, check `:1101`): DEFERRED** (see Section 9).

`Tuple` added to the `typing` import (the only import-line change).

---

## 5. Sanitization Field Matrix

For a raw inbound `policy_flags` dict, after `_sanitize_untrusted_policy_flags_dict`:

| Inbound flag                          | In `_SERVER_AUTHORED_FLAGS`? | PolicyFlags field? | Survives? | Sanitized value |
|---------------------------------------|------------------------------|--------------------|-----------|-----------------|
| `security_gate_checked`               | yes                          | yes                | forced    | False           |
| `security_gate_passed`                | yes                          | yes                | forced    | False           |
| `permission_gate_checked`             | yes                          | yes                | forced    | False           |
| `permission_gate_passed`              | yes                          | yes                | forced    | False           |
| `exfoliation_gate_checked`            | yes                          | yes                | forced    | False           |
| `exfoliation_gate_passed`             | yes                          | yes                | forced    | False           |
| `wsp_preflight_checked`               | yes                          | yes                | forced    | False           |
| `wsp_preflight_passed`                | yes                          | yes                | forced    | False           |
| `capability_token_checked`            | yes                          | yes                | forced    | False           |
| `capability_token_present`            | yes                          | yes                | forced    | False           |
| `capability_token_validated`          | yes                          | yes                | forced    | False           |
| `capability_token_scope_authorized`   | yes                          | yes                | forced    | False           |
| `dry_run_mode` (explicit)             | no (operator-authored)       | yes                | preserved | as supplied     |
| `dry_run_mode` (absent)               | n/a                          | yes                | defaulted | True (safe)     |
| `human_approval` (not a PolicyFlags field) | no                      | NO                 | dropped   | absent → `.get()` False |
| any other non-field key               | no                           | NO                 | dropped   | absent          |

Consequence: a raw dict can express ONLY a `dry_run_mode` choice (and even that defaults safe when
absent). All gate/token authority must come from a server-authored `PolicyFlags` object snapshot.

---

## 6. Dry-Run Default Preservation Proof

`PolicyFlags.from_dict({})` returns `dry_run_mode=False` (the `data.get("dry_run_mode", False)`
default). Left unrestored, a raw dict omitting `dry_run_mode` would be mis-classified as LIVE — the
unsafe direction. The helper detects absence (`"dry_run_mode" not in policy_flags`) and restores
`dry_run_mode=True`, so an absent flag is dry-run, NOT live.

- Helper-level: `test_raw_dict_missing_dry_run_defaults_true`
- Envelope-level: `test_envelope_raw_dict_missing_dry_run_not_live`
  (`dry_run_defaulted is True`, `is_live_mode is False`, snapshot `dry_run_mode is True`)
- None branch (unchanged): `test_missing_policy_flags_defaults_dry_run`
- Explicit `dry_run_mode=False` is PRESERVED (not over-defaulted):
  `test_foundup_envelope_with_explicit_dry_run_false_not_defaulted`
  (`dry_run_defaulted is False`, `is_live_mode is True`).

---

## 7. Gate 2 Fail-Closed Proof

In live mode, `security_gate_passed` must be True or the gate appends `security_gate_passed` to
`missing_gates` and blocks with `LIVE_MODE_REQUIRES_SECURITY_GATE`. `security_gate_checked` is now
log-only.

- `TestLiveModeSecurityGate::test_live_mode_security_gate_passed_false_fails`
  (server-authored snapshot passes Gate 1 via `permission_gate_passed`; `security_gate_passed=False`
  → blocked).
- `TestLiveModeSecurityGate::test_live_mode_security_gate_required_even_when_not_checked`
  (FAIL-CLOSED inversion: `security_gate_checked=False` no longer makes the gate optional).
- Boundary file: `TestLegitimateLivePassServerAuthored::test_server_authored_snapshot_without_security_still_fails`.
- End-to-end at the envelope: `TestLiveRawDictWithoutSecurityBlocked::test_live_raw_dict_no_security_blocked`,
  `TestLiveRawDictForgedSecurityBlocked::test_forged_security_gate_passed_blocked`
  (forged `security_gate_passed=True` sanitized to False → blocked; snapshot proves it did not survive).

A legitimate live PASS therefore requires a server-authored `PolicyFlags` snapshot with
`security_gate_passed=True`, proven directly on `_validate_live_mode_gates`:
`TestLegitimateLivePassServerAuthored::test_server_authored_snapshot_passes_gates`.

---

## 8. GENERIC_DAE No-Regression Proof

The GENERIC_DAE branch (`:354-370`) runs before any policy handling and is untouched. A
`run_wre`-style envelope (`{"objective": ...}`, no `policy_flags`, no identity fields) still
classifies GENERIC_DAE and passes.

- `TestGenericDAENoRegression::test_generic_dae_objective_only_passes` (VALID, GENERIC_DAE)
- `TestGenericDAENoRegression::test_generic_dae_with_context_passes`
- Pre-existing generic tests in `test_foundup_job_envelope_validation.py`
  (`TestGenericDAEEnvelope`, `TestGenericDAEEvidenceBehavior`) remain green.

---

## 9. Sibling `route_foundup_job` Decision — DEFERRED

`route_foundup_job` (`:1017`) has a Gate-2-like check at `:1101`:
`if policy_summary.get("security_gate_checked") and not policy_summary.get("security_gate_passed"):`.
**Decision: DEFER — do NOT change in this slice.** Confirmed during discovery:

1. **Object, not raw envelope.** `route_foundup_job` reads `job.policy_flags` off a `FoundUpJob`
   OBJECT (`:1092`), whose flags are already sanitized by the #747 `PolicyFlags.from_dict`
   deserialization chokepoint. Its `:1095-1098` only `to_dict()`s an object or copies a dict that
   has already passed through deserialization — it is not the loose untrusted-envelope surface.
2. **No live-mode discriminator.** There is NO `is_live_mode` (or `dry_run_mode`) discriminator
   anywhere in `:1091-1111`. The check is unconditional across dry-run and live. Forcing
   `if not security_gate_passed` fail-closed here would block legitimate dry-run / default routing
   (which is the common, safe path), an over-block regression.

**Follow-up named:** `FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1` — introduce a
live-mode discriminator at `:1091-1111` first, then apply fail-closed only in live mode.
`test_foundup_job_router.py` (the object-path suite) remains fully green, confirming the deferral
preserved that path.

---

## 10. Test Matrix

### New file: `tests/test_foundup_job_router_policyflags_boundary.py` (12 tests, all pass)

| # | Test | Proves |
|---|------|--------|
| 1 | `TestRawDictSelfAssertionSanitized::test_self_asserted_gate_and_token_flags_zeroed_in_helper` | All server-authored gate/token flags forced False; explicit dry_run preserved |
| 2 | `…::test_self_asserted_flags_zeroed_in_envelope_snapshot` | Envelope snapshot is sanitized end-to-end |
| 3 | `TestMissingDryRunDefaultsSafe::test_raw_dict_missing_dry_run_defaults_true` | Absent dry_run → True (helper) |
| 4 | `…::test_envelope_raw_dict_missing_dry_run_not_live` | Absent dry_run → not live (envelope) |
| 5 | `TestMissingPolicyFlagsNoneBranch::test_missing_policy_flags_defaults_dry_run` | None branch unchanged (dry_run True) |
| 6 | `TestLiveRawDictWithoutSecurityBlocked::test_live_raw_dict_no_security_blocked` | Live raw dict without real security → BLOCKED |
| 7 | `TestLiveRawDictForgedSecurityBlocked::test_forged_security_gate_passed_blocked` | Forged `security_gate_passed=True` → sanitized → BLOCKED |
| 8 | `TestLegitimateLivePassServerAuthored::test_server_authored_snapshot_passes_gates` | Server-authored snapshot live-passes |
| 9 | `…::test_server_authored_snapshot_human_approval_variant_passes` | human_approval Gate-1 variant passes |
| 10 | `…::test_server_authored_snapshot_without_security_still_fails` | Fail-closed even server-authored |
| 11 | `TestGenericDAENoRegression::test_generic_dae_objective_only_passes` | GENERIC_DAE non-regressed |
| 12 | `…::test_generic_dae_with_context_passes` | GENERIC_DAE non-regressed |

### Updated existing tests in `tests/test_foundup_job_envelope_validation.py` (each justified)

Root cause of every update: under the locked design (raw dict sanitized; object branch — unchanged —
coerces a falsy `dry_run_mode` object back to dry-run), a **legitimate live PASS is no longer
reachable through the public envelope API**. Per dispatch Test #6, legitimate live passes and
live-only gate codes are exercised directly on `_validate_live_mode_gates` /
`_validate_compute_budget` with a SERVER-AUTHORED snapshot. No assertion deleted without a
replacement; every security intent is preserved or strengthened (fail-closed).

| Test (updated) | Old (insecure/raw) | New (faithful) |
|----------------|--------------------|----------------|
| `test_foundup_envelope_with_explicit_dry_run_false_not_defaulted` | raw `human_approval` dict expected VALID live | proves explicit dry_run preserved (`dry_run_defaulted False`, `is_live_mode True`) AND fail-closed BLOCK (`security_gate_passed` missing) |
| `test_valid_evidence_does_not_set_verification_complete` | raw `human_approval` live dict | dry-run valid envelope (truth field guarantee is mode-independent) → `verification_complete is False` |
| `test_live_mode_with_empty_evidence_fails` | raw dict, `LIVE_MODE_REQUIRES_EVIDENCE` | direct gate call (server-authored), `evidence_count=0` → evidence the sole missing gate |
| `test_live_mode_with_no_evidence_field_fails` | raw dict, `LIVE_MODE_REQUIRES_EVIDENCE` | direct gate call (server-authored), `evidence_pending=True` |
| `test_live_mode_gate_pass_does_not_imply_verification_complete` (renamed) | raw `human_approval` live dict expected VALID | gate PASS via server-authored snapshot + WSP-97 truth field False on valid envelope |
| `test_live_mode_gate_pass_does_not_imply_cabr_ready` (renamed) | raw live dict | same pattern; `cabr_ready is False` |
| `test_live_mode_gate_pass_does_not_imply_payout_ready` (renamed) | raw live dict | same pattern; `payout_ready is False` |
| `test_live_mode_security_gate_passed_false_fails` (renamed) | raw `human_approval` + `security_gate_checked=True` opt-in | direct gate call: Gate 1 passes (permission), `security_gate_passed=False` → fail-closed |
| `test_live_mode_security_gate_required_even_when_not_checked` (renamed; was `..._not_checked_passes`) | asserted PASS when not checked (legacy opt-in) | INVERTED to fail-closed: `security_gate_checked=False` no longer makes the gate optional → BLOCKED |
| `test_live_mode_fields_in_serialized_result` | raw live dict expected `live_mode_gates_passed True` | serialization shape + `is_live_mode True` via explicit raw live dict; gate PASS proven at gate surface |
| `test_live_mode_with_budget_passes` | raw live dict expected VALID | direct `_validate_compute_budget(is_live_mode=True)` budget=5000 → valid |
| `test_live_mode_without_budget_fails` | raw live dict, `LIVE_MODE_REQUIRES_COMPUTE_BUDGET` | direct `_validate_compute_budget(is_live_mode=True)` budget=None |

All other live-FAILURE tests (`TestLiveModeWithoutApprovalFails`, malformed-evidence, missing-gates
detail, message tests) were left unchanged and remain green: they already expected a BLOCK and their
primary code (`LIVE_MODE_REQUIRES_HUMAN_APPROVAL`) is unaffected by sanitization (or fail earlier at
evidence-type validation).

---

## 11. Boundary Proof

- **dae_gateway.py** — NOT touched. `git status --porcelain` lists only the router src, the router
  test file, and the new boundary test file.
- **FoundUpJob / Hermes path** — NOT touched. `foundup_job_contract.py`, `hermes_job_executor.py`,
  `destructive_action_guard.py` unchanged. `test_foundup_job_router.py` (object path) fully green.
- **No circular dependency** — `PolicyFlags` is imported with a DEFERRED import inside the helper
  (matching the existing pattern at `:1073`); `import modules.infrastructure.wre_core.src.foundup_job_router`
  succeeds at module load.
- **No contract mutation** — `PolicyFlags.from_dict`/`to_dict`/`_SERVER_AUTHORED_FLAGS` are consumed,
  not modified.

---

## 12. Critic Review Result

Self-critic pass over the diff before writing this audit:

| Critic question | Result |
|-----------------|--------|
| Did missing `dry_run_mode` become live? | NO — helper restores True; tests confirm not live |
| Did GENERIC_DAE over-block? | NO — generic branch precedes policy handling; tests green |
| Did `route_foundup_job` dry-run routing break? | NO — DEFERRED; object-path suite green |
| Circular import introduced? | NO — deferred import; module loads |
| Touched dae_gateway / Hermes / contract / guard? | NO — status shows only 3 router files |
| Deleted an insecure assertion without replacement? | NO — every change preserves/strengthens intent |
| Did an explicit `dry_run_mode=False` get over-defaulted? | NO — helper preserves explicit False |

Critic verdict: PASS.

---

## 13. Internal Review Verdict

**APPROVED.** The defect is closed at the router boundary exactly per the locked design: raw-dict
envelope `policy_flags` are sanitized through the #747 chokepoint, the safe dry-run default is
preserved, and live-mode Gate 2 is fail-closed. The sibling `route_foundup_job` is correctly
deferred with a named follow-up. Focused tests are green (12/12); the broader `wre_core/tests`
suite is green except 5 pre-existing, unrelated failures proven via a clean-baseline comparison.

---

## 14. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | ROUTER_BOUNDARY_ONLY | YES | Only `foundup_job_router.py` (+ its tests) changed; `git status --porcelain` = 3 files |
| 2 | NO_DAE_GATEWAY_MUTATION | YES | `dae_gateway.py` untouched (not in status) |
| 3 | NO_FOUNDUPJOB_HERMES_PATH_CHANGE | YES | `hermes_job_executor.py` untouched; `test_foundup_job_router.py` object path green |
| 4 | NO_CONTRACT_MUTATION | YES | `foundup_job_contract.py` untouched; `from_dict`/`to_dict` only consumed |
| 5 | RAW_ENVELOPE_SANITIZED | YES | `_sanitize_untrusted_policy_flags_dict`; Group 1 + forged-block tests |
| 6 | DRY_RUN_DEFAULT_PRESERVED | YES | Helper restores True; `test_envelope_raw_dict_missing_dry_run_not_live` |
| 7 | GATE2_FAILCLOSED | YES | `if not security_gate_passed`; `test_live_mode_security_gate_passed_false_fails` |
| 8 | GENERIC_DAE_NO_REGRESSION | YES | `TestGenericDAENoRegression` + existing generic suites green |
| 9 | SIBLING_ROUTE_DECISION_DOCUMENTED | YES | Section 9 DEFERRED + follow-up `FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1` |
| 10 | NO_SKIP_XFAIL_ADDED | YES | No `skip`/`xfail` added; new file has none |
| 11 | NO_DEPENDENCY_CHANGE | YES | No requirements/imports added beyond `typing.Tuple` |
| 12 | NO_CI_CHANGE | YES | No CI files touched |
| 13 | NO_WSP_MUTATION | YES | No `WSP_*` files touched |
| 14 | NO_NEW_CIRCULAR_DEP | YES | Deferred import; `import foundup_job_router` succeeds |
| 15 | CRITIC_REVIEW_COMPLETED | YES | Section 12 |
| 16 | NO_CABR_READY | YES | No CABR claims; result `cabr_ready=False` unchanged |
| 17 | NO_PAYOUT_READY | YES | No payout claims; result `payout_ready=False` unchanged |
| 18 | NO_DAO_ACTIVATION | YES | No DAO activation introduced |

All declared == actual. All YES.
