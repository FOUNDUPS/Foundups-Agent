# HXA PolicyFlags Write-Back Remediation (Phase 1)

**Slice:** `HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1`
**Worker-Lane:** W6 · **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** Targeted security remediation (code + tests). NO broad refactor.
**Base:** `origin/main` @ `d602d874b` (after #746 enforcement audit).
**Branch:** `fix/hxa-policyflags-writeback-remediation-phase1`

---

## 1. Mission and Scope

Close the `#746` bounded PolicyFlags write-back defect with **positive control**:
security/token gate flags must be **server-authored only**, never trusted from deserialized job
data, and the runtime validator verdict must be written into `job.policy_flags` **before** the
destructive-action guard reads it.

Two surgical changes, no behavior expansion:

1. **Deserialization sanitization** at the single chokepoint `PolicyFlags.from_dict`
   (`modules/communication/moltbot_bridge/src/foundup_job_contract.py`).
2. **Validator verdict write-back** in `HermesJobExecutor.execute()`
   (`modules/infrastructure/wre_core/src/hermes_job_executor.py`), before guard evaluation.

Out of scope (explicitly deferred): wiring a real security-gate verdict in this executor; any
production caller of `FoundUpJob.from_dict`; persistent-queue rehydrate boundary.

---

## 2. Predecessor Citations

| PR / Item | Relationship |
|-----------|--------------|
| **#746** `HXA_POLICYFLAGS_WRITEBACK_ENFORCEMENT_AUDIT_PHASE1` | The read-only audit that classified this defect `GAP_CONFIRMED_BOUNDED` and specified the remediation shape (its §9). This slice implements §9 steps 1-3. |
| **#744** `HXA26_HXA27_DEFENSE_PRIMITIVES_REDUNDANCY_AUDIT_PHASE1` | Addendum that first surfaced the write-back seam. |
| **#743** `HXA29_SCOPE_ACTION_VALIDATION_ENFORCEMENT_AUDIT_PHASE1` | Scope→action-class enforcement precedent. |
| HXA24 capability-token PolicyFlags · HXA27 Hermes token integration · HXA30 scope-to-action-class | Primitive lineage the write-back consumes. |

---

## 3. Pre-State Defect Summary (from #746)

From the #746 audit (`GAP_CONFIRMED_BOUNDED`):

- **Two independent channels.** The live `TokenValidationResult` from `_validate_token_if_present`
  was used only to (a) hard-block an explicitly-present-and-invalid token and (b) serialize into
  result metadata — it was **never written into `job.policy_flags`**
  (`anyValidatorVerdictWriteback = False`).
- **Guard trusts inbound flags.** `capability_token_present_for_guard` is the AND of the four
  inbound `policy_flags.capability_token_*` (`hermes_job_executor.py:1131-1138`); `security_gate_passed`
  read straight from the envelope. A caller could omit the token entirely (validator returns `None`,
  no block) yet still present `capability_token_*=True` to collapse the guard's token gate to `True`.
- **Zero sanitization.** `PolicyFlags.from_dict` blindly `bool()`-cast every gate/token flag verbatim.
- **Bounded, not exploitable today** only because `FoundUpJob.from_dict` has **zero production callers**
  and the live chat path uses `create_job` (born all-`False`). "The boundary is held by the *accident*
  that `from_dict` is unwired, not by positive control."

This slice replaces that accident with positive control.

---

## 4. Implementation Summary

### CHANGE 1 — Deserialization sanitization (`foundup_job_contract.py`)

- Added module-level `_SERVER_AUTHORED_FLAGS` frozenset (12 gate/token field names).
- Rewrote `PolicyFlags.from_dict` to **force every server-authored flag to `False` regardless of
  inbound data** (the inbound dict is not read for those fields). Only `dry_run_mode` is preserved
  (operator-authored; `True` is the safe/sandbox direction; router already defaults it `True`).
- Updated the `from_dict` docstring: deserialized gate/token state is UNTRUSTED and forced `False`;
  server authority comes from runtime validation write-back (cites this slice).
- `FoundUpJob.from_dict` (`:613`) and `FoundUpJob.__post_init__` (dict→PolicyFlags coercion,
  `:411-412`) both route through `PolicyFlags.from_dict`, so this one edit covers every deserialization
  path.
- **Unchanged:** the direct `PolicyFlags(...)` constructor and `field(default_factory=PolicyFlags)`.
  Server code can still author `True` flags by direct object construction / attribute assignment. Only
  the untrusted-deserialization path is locked down.

### CHANGE 2 — Validator verdict write-back (`hermes_job_executor.py`)

- Added private helper `_writeback_token_verdict(job, token_validation_result)` (executor `:1158`).
- Called once in `execute()` (`:1521`) **immediately before** `_evaluate_destructive_action_guard`
  (`:1524`), after `_validate_token_if_present` (`:1496`) and after the invalid-token early-return.
- Writes the server-authored verdict into `job.policy_flags`. `security_gate_*` is intentionally left
  at the server-default `False` (no security-gate evaluator in this executor; out of scope).

---

## 5. Sanitization Field Matrix

`PolicyFlags.from_dict` outcome for each field (inbound value is the attacker/stale value):

| Field | Disposition | Source after from_dict |
|-------|-------------|------------------------|
| `security_gate_checked` | FORCED FALSE | server-default (ignores inbound) |
| `security_gate_passed` | FORCED FALSE | server-default (ignores inbound) |
| `permission_gate_checked` | FORCED FALSE | server-default (ignores inbound) |
| `permission_gate_passed` | FORCED FALSE | server-default (ignores inbound) |
| `exfoliation_gate_checked` | FORCED FALSE | server-default (ignores inbound) |
| `exfoliation_gate_passed` | FORCED FALSE | server-default (ignores inbound) |
| `wsp_preflight_checked` | FORCED FALSE | server-default (ignores inbound) |
| `wsp_preflight_passed` | FORCED FALSE | server-default (ignores inbound) |
| `capability_token_checked` | FORCED FALSE | server-default (ignores inbound) |
| `capability_token_present` | FORCED FALSE | server-default (ignores inbound) |
| `capability_token_validated` | FORCED FALSE | server-default (ignores inbound) |
| `capability_token_scope_authorized` | FORCED FALSE | server-default (ignores inbound) |
| `dry_run_mode` | **PRESERVED** | `bool(data.get("dry_run_mode", False))` |

All 12 fields in `_SERVER_AUTHORED_FLAGS` are forced `False`; `dry_run_mode` is the sole preserved
inbound flag.

---

## 6. Validator Write-Back Field Matrix

`_writeback_token_verdict` mapping (executor `:1158`). `result = token_validation_result`
(`None` when no token was present in the payload):

| PolicyFlags field | Source expression | Rationale |
|-------------------|-------------------|-----------|
| `capability_token_checked` | `True` (unconditional) | `execute()` always runs token validation, so a check was always performed. |
| `capability_token_present` | `result is not None` | A token was present iff the validator returned a (non-None) result. |
| `capability_token_validated` | `result is not None and result.token_valid` | The validator marked the token valid. |
| `capability_token_scope_authorized` | `validated and not result.scope_action_class_mismatch` | Token valid AND scopes authorize the classified action class. `token_valid=True` already implies no scope/action-class mismatch (validator success return `capability_token_validator.py:628` leaves `scope_action_class_mismatch=False`; the mismatch return at `:610-617` sets `token_valid=False, scope_action_class_mismatch=True`). The `not …mismatch` term is defensive belt-and-suspenders. Field defined at `capability_token_validator.py:304`. |
| `security_gate_checked` | NOT WRITTEN — server-default `False` | No security-gate evaluator in this executor. |
| `security_gate_passed` | NOT WRITTEN — server-default `False` | The only writer of `security_gate_*` is the SEPARATE `modules/foundups/agent/src/hermes_foundup_job_executor.py:362`. Fabricating `security_gate_passed=True` is out of scope (future). |

---

## 7. Guard Sequencing Proof

Within `HermesJobExecutor.execute()` (`modules/infrastructure/wre_core/src/hermes_job_executor.py`):

```
:1496  token_validation_result = self._validate_token_if_present(job, request, action_class=...)
:1500  (invalid-token early-return block — if token present and not valid -> BLOCKED_BY_TOKEN_VALIDATION)
:1521  self._writeback_token_verdict(job, token_validation_result)   # server-authored verdict written
:1524  guard_result = self._evaluate_destructive_action_guard(job, request)  # guard reads policy_flags
```

The write-back at line **1521** strictly precedes the guard evaluation at line **1524**. The guard's
`_build_destructive_action_request` reads `policy_flags.capability_token_*` (`:1131-1138`), so it now
reads the server-authored verdict, never attacker-supplied flags.

---

## 8. D3 / D4 / D5 / D6 Boundary Proof (behavior unchanged; bypass closed)

| Path | Before | After | Mechanism |
|------|--------|-------|-----------|
| No-token D3 | BLOCKED (`MISSING_CAPABILITY_TOKEN`) | BLOCKED | write-back sets `present/validated/scope=False` → guard token gate False. |
| Invalid-token D3/D4 | BLOCKED (`BLOCKED_BY_TOKEN_VALIDATION`, early-return before guard) | BLOCKED | unchanged; early-return at `:1500` precedes write-back's effect on guard. |
| Valid-token D3 | ALLOW dry-run only **iff** other gates True | ALLOW dry-run only **iff** other gates True | capability flags True via write-back; `security_gate_passed` still server-default False → D3 BLOCKED unless server authors security gate. `live_execution_allowed=False` always. |
| Forged flags, no token, D3 (**the bypass**) | (would clear guard token gate if ingress could pre-set flags) | **BLOCKED** | sanitization zeroes inbound flags AND write-back demotes to no-token verdict. Bypass closed. |
| D4 / D5 / D6 (any flags / valid token) | BLOCKED (class-based, unconditional) | BLOCKED | unchanged; guard blocks by class regardless of token/flags. |

No behavior expansion: D3 remains bounded/dry-run only; D4/D5/D6 remain unconditionally blocked.

---

## 9. Test Scenario Matrix

| # | Scenario | Test(s) | Result |
|---|----------|---------|--------|
| 1 | from_dict ignores malicious inbound gate/token flags; `dry_run_mode` preserved | `test_foundup_job_contract.py::TestPolicyFlagsDeserializationSanitization::*` (malicious-all-true, dry_run preserved/false/missing, FoundUpJob.from_dict, __post_init__) | PASS |
| 2 | `create_job()` yields all-False gate/token flags at birth | `…::test_create_job_yields_all_false_gate_flags` | PASS |
| 3 | Executor writes verdict back (valid / no-token / invalid) | `test_hxa_policyflags_writeback_remediation.py::TestWriteBackReflectsVerdict::*` + `TestWriteBackHelperSemantics::*` | PASS |
| 4 | Guard sees server-authored fields — pre-set flags + no token still BLOCKED at D3 | `…::TestBypassClosed::test_payload_preset_capability_flags_but_no_token_blocked_at_d3`, `…::test_writeback_overrides_stale_object_flags_before_guard` | PASS |
| 5 | D4/D5/D6 remain BLOCKED regardless of flags | `…::TestBoundaryUnchanged::test_d4_d5_d6_blocked_even_with_valid_token` (parametrized) | PASS |
| 6 | D3 bounded/dry-run only (`live_execution_allowed=False`) | `…::test_d3_valid_token_remains_dry_run_only`, `…::test_security_gate_not_fabricated_by_writeback` | PASS |

**Existing tests updated to the new (correct) semantics** — each change justified:

| Test (file) | Old assertion (insecure) | New assertion (secure) | Justification |
|-------------|--------------------------|------------------------|---------------|
| `test_foundup_job_contract.py::test_to_dict_roundtrip` → `test_from_dict_sanitizes_server_authored_flags` | from_dict preserves True gate flags | gate flags forced False; `dry_run_mode` preserved | Sanitization (CHANGE 1). |
| `…::test_from_dict_missing_fields_default_false` | `security_gate_checked is True` from data | `security_gate_checked is False` (sanitized) | Sanitization. |
| `…::test_policy_flags_in_job_roundtrip` → `…_sanitizes_gates` | restored gates True | restored gates False; `dry_run_mode` True | Sanitization via FoundUpJob.from_dict. |
| `…::test_capability_token_fields_from_dict` → `…_sanitized` | token flags True | token flags False | Sanitization. |
| `…::test_capability_token_roundtrip` → `…_sanitized_on_roundtrip` | token roundtrip preserves True | to_dict True, from_dict False | Sanitization. |
| `test_hxa24_capability_token_policyflags.py::test_from_dict_restores_capability_token_fields` → `…_sanitizes…` | token flags restored True | token flags forced False | Sanitization. |
| `…::test_roundtrip_preserves_all_fields` → `…_sanitizes_server_authored_preserves_dry_run` | all fields preserved | gate/token False; `dry_run_mode` preserved | Sanitization. |
| `…::test_job_from_dict_restores_capability_token_flags` → `…_sanitizes…` | job token flags restored True | job token flags forced False | Sanitization. |
| `…::test_all_four_true_with_security_gate_allows_d3` | forged 4 token flags + security gate → ALLOW | REAL valid token in payload (server-authored verdict) + security gate → ALLOW | Write-back: forging flags no longer works; a real token is required. |
| `…::test_all_four_true_but_missing_security_gate_blocks_d3` | forged 4 token flags, no security gate → `MISSING_SECURITY_GATE` | REAL valid token, no security gate → `MISSING_SECURITY_GATE` | Write-back: real token promotes capability flags; security gate still blocks. |
| `test_hxa25` / `test_hxa28` `_create_*_with_all_gates` helpers | forged capability flags | REAL broad-scope token in payload (D3 passes, D4/D5/D6 guard-blocked) | Write-back authority. |
| `test_hxa4` / `test_hxa12` / `test_hxa14` / `test_hxa16` `set_d3_capability_token_gates` | forged capability flags | REAL valid D3 token attached to payload (`dry_run_only=False` so it validates in both dry/live executor modes) | Write-back authority; harness/guard still bounds execution. |

### Test run results (exact counts)

| File | Result |
|------|--------|
| `modules/communication/moltbot_bridge/tests/test_foundup_job_contract.py` | **78 passed** |
| `modules/infrastructure/wre_core/tests/test_hermes_job_executor.py` | **94 passed** |
| `modules/infrastructure/wre_core/tests/test_hxa_policyflags_writeback_remediation.py` (new) | **13 passed** |
| Full `modules/infrastructure/wre_core/tests/` | **1383 passed, 3 skipped, 2 xfailed, 5 deselected** |

**5 deselected are PRE-EXISTING environmental failures (NOT caused by this slice), verified against
the clean tree:**
- `test_wre_skills_discovery.py::test_initialization` — asserts repo dir name `Foundups-Agent`; fails
  because this is an isolated worktree dir (`agent-…`).
- `test_hxa16…::TestHermesRealDelegateInterfaceExists::{test_delegate_tool_file_exists,
  test_delegate_tool_contains_delegate_task_function, test_delegate_task_requires_parent_agent,
  test_delegate_task_spawns_child_agents}` — require vendored `vendor/hermes-agent/tools/delegate_tool.py`
  which is absent in this worktree. All four fail identically on `git stash` of this slice's changes.

### Regression confirm

`git grep -n "FoundUpJob.from_dict" -- '*.py' | grep -v test` → **1 match, and it is a comment line in
`foundup_job_contract.py` (not a caller). Production-caller count = 0.** No production caller of
`FoundUpJob.from_dict` was added (NO_FROM_DICT_PRODUCTION_WIRING honored).

---

## 10. Residual Risks / Deferred Trip-Wire

1. **Persistent-queue `from_dict` wiring (the trip-wire).** The in-memory `_FOUNDUP_JOB_QUEUE` has no
   serialize/deserialize hop today. The moment any HTTP/API/message-queue/persisted-job ingress is
   wired to `FoundUpJob.from_dict`, this slice's sanitization is the positive control that holds the
   boundary. Recommended follow-up: `HXA_PERSISTENT_QUEUE_POLICYFLAGS_TRIPWIRE_AUDIT_PHASE1`.
2. **Security-gate write-back (future).** This executor has no security-gate evaluator;
   `security_gate_*` stays server-default `False`. Wiring a real security-gate verdict (analogous to the
   token write-back) is deferred. Until then, valid-token D3 stays BLOCKED unless a server component
   authors the security gate by direct assignment.
3. **Provenance marker (optional hardening, #746 §9.4).** A non-serialized server-authored marker could
   assert provenance so a future `from_dict` path cannot reintroduce caller-asserted gate state. Not
   implemented in this slice (the sanitization already forces False; the marker is defense-in-depth).

---

## 11. Internal Review Verdict

**READY.** Both changes implemented exactly to the locked design with verified `file:line` evidence:
(1) sanitization forces all 12 server-authored flags False, preserves only `dry_run_mode`, at the single
chokepoint `PolicyFlags.from_dict`; (2) write-back at `execute():1521` precedes guard eval at `:1524`,
mapping the real verdict (capability_token_* from `TokenValidationResult`; security_gate_* left
server-default). The bypass is closed (sanitization + write-back), D3 stays bounded dry-run only, and
D4/D5/D6 remain unconditionally blocked — no behavior expansion. All target suites green
(78 / 94 / 13); full wre_core green except 5 pre-existing worktree-environmental failures (verified
unrelated). Zero production callers of `FoundUpJob.from_dict`. Engineering/security only — no 012 ruling
requested.

---

## 12. WSP_97 Truth Boundary Checklist

Declared count: **24 / 24 YES** (rows below = 24).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | POLICYFLAGS_WRITEBACK_REMEDIATION_ONLY | YES | Only `PolicyFlags.from_dict` sanitization + `_writeback_token_verdict` + their tests/audit changed; no broad refactor. |
| 2 | NO_LIVE_HERMES_DELEGATION | YES | No delegation path enabled; tests run with `HERMES_DELEGATE_ENABLED=0`. |
| 3 | NO_HERMES_RUNTIME_LAUNCH | YES | No Hermes runtime launched. |
| 4 | NO_OLLAMA_LAUNCH | YES | No Ollama process started. |
| 5 | NO_WSL_INSTALL | YES | No WSL install. |
| 6 | NO_API_INGRESS_WIRING | YES | No HTTP/API ingress added. |
| 7 | NO_FROM_DICT_PRODUCTION_WIRING | YES | `git grep` production-caller count of `FoundUpJob.from_dict` = 0 (only a comment line). |
| 8 | NO_D4_D5_D6_WEAKENING | YES | D4/D5/D6 remain unconditional class blocks; parametrized test proves blocked even with valid token. |
| 9 | NO_D3_LIVE_EXECUTION | YES | D3 ALLOW is dry-run only; `live_execution_allowed=False` asserted; `real_execution_performed=False`. |
| 10 | NO_ENV_MUTATION | YES | Only `patch.dict(os.environ, …)` scoped within tests; no persistent env change. |
| 11 | NO_DEPENDENCY_CHANGE | YES | No requirements/imports of new packages. |
| 12 | NO_CI_CHANGE | YES | No CI/workflow files touched. |
| 13 | NO_WSP_MUTATION | YES | No WSP framework file modified. |
| 14 | NO_REGISTRY_MUTATION | YES | No registry modified. |
| 15 | NO_MANIFEST_MUTATION | YES | No manifest modified. |
| 16 | NO_PUBLIC_SURFACE_MUTATION | YES | No public API signature changed; `from_dict` signature unchanged (semantics hardened only). |
| 17 | NO_SECRET_VALUES | YES | No secrets/keys/tokens printed; only test fake tokens via `LocalCapabilityTokenIssuer`. |
| 18 | NO_CABR_READY | YES | No CABR-ready claim; not touched. |
| 19 | NO_PAYOUT_READY | YES | No payout-ready claim; not touched. |
| 20 | NO_DAO_ACTIVATION | YES | No DAO activation. |
| 21 | NO_HERMES_DELEGATE_ENABLED_TOUCH | YES | `HERMES_DELEGATE_ENABLED` not modified in source; only read in scoped test env. |
| 22 | CONFIG_SIDE_EFFECTS_REVERTED | YES | Test-run truncation of `wre_core/config/{WRE_RUNBOOK.md,wre_defaults.env}` restored via `git checkout`; not committed. |
| 23 | TESTS_NOT_WEAKENED | YES | Existing tests updated to NEW correct semantics (Test Scenario Matrix §9), each justified; none weakened to pass. |
| 24 | WORKTREE_ISOLATION | YES | All edits/tests/commits in the isolated worktree; other worktrees untouched. |

**WSP 97 Truth Boundary Checklist: 24/24 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Targeted remediation of `origin/main` @ `d602d874b`. Implements #746 §9 steps 1-3: deserialization
sanitization (positive control) + validator verdict write-back before guard evaluation. Bypass closed;
no behavior expansion.*
