# HXA29 Scope-to-Action-Class Enforcement Gap Audit (Phase 1)

Slice: HXA29_SCOPE_ACTION_VALIDATION_ENFORCEMENT_AUDIT_PHASE1
Worker-Lane: W6
Mode: READ-ONLY security audit (no code/test/worktree/main mutation)
Repo HEAD audited: main @ 40e0ef66a (post-PR #742)

---

## 1. Mission + Scope

PR #742 (worktree stranded-work triage) flagged a possible LIVE enforcement gap in
the HXA29 scope-to-action-class capability-token check. The reported concern:

- The stranded worktree `agent-ad998a8` appears to wire an integrated "Gate 10.5"
  scope-to-action-class check INTO `validate_token`, emitting
  `SCOPE_ACTION_CLASS_MISMATCH`.
- Current main appears to contain `validate_scope_for_action_class()` as a STANDALONE
  helper, but a preliminary grep found 0 callers wiring it into the token validation
  flow.

This audit determines whether the enforcement gap is REAL on current main, with
file:line evidence, by answering five questions:

1. Does current main enforce scope-to-action-class during capability token validation?
2. Is `validate_scope_for_action_class()` called from `validate_token` or any live
   validation path?
3. Does any test prove `SCOPE_ACTION_CLASS_MISMATCH` (or equivalent) is emitted on
   mismatch?
4. Does stranded HXA29 contain a real security primitive NOT landed in main?
5. Should remediation salvage HXA29's integrated Gate 10.5, or use another existing
   path?

Scope guards (hard constraints): READ_ONLY_SECURITY_AUDIT, NO_CODE_CHANGE,
NO_TEST_CHANGE, NO_CHERRY_PICK, NO_STRANDED_WORK_MUTATION, NO_BRANCH_DELETE,
NO_WORKTREE_REMOVAL, HXA29_PROTECTED, NO_CABR_READY, NO_PAYOUT_READY,
NO_DAO_ACTIVATION. The only file created is this audit doc on a new branch.

---

## 2. Predecessor Citation

- Predecessor: PR #742 "docs(audit): worktree stranded-work triage Phase 1
  (decision-only)" (MERGED, base=main). Its body raised:
  "Possible real enforcement gap (HXA29): `agent-ad998a8` wires an integrated
  scope->action-class check into `validate_token`; main's landed
  `validate_scope_for_action_class()` appears standalone/unwired (0 callers found).
  Flagged for security follow-up."
  PR #742 predecessors were #739 and #741.

- HXA29 landing: commit `18cbcad00` -- "feat(wre): add token scope-to-action-class
  validation (HXA29) (#575)" by W1. This landed the STANDALONE helper
  `validate_scope_for_action_class()` plus 54 unit tests, but did NOT add a caller
  inside `validate_token`. At the HXA29 boundary, #742's "0 callers" observation was
  accurate.

- HXA30 landing (the missing link #742 did not account for): commit `255bf3fc0` --
  "feat(wre): integrate scope-to-action-class validation into Hermes (HXA30) (#576)".
  This is the PR that wired the helper into `validate_token` (Gate 13) AND threaded
  `action_class` through the Hermes execution path. It landed ONE PR after HXA29.

---

## 3. Current Main Enforcement Map

File: `modules/infrastructure/wre_core/src/capability_token_validator.py`

- `validate_token()` body: defined at line 428
  (`LocalCapabilityTokenValidator.validate_token`).
- Gate 13 (HXA30) -- the live scope-to-action-class enforcement -- lines 594-617:
  - line 596: `if action_class is not None:`
  - line 604-608: iterates over ALL `token.scopes` and calls
    `validate_scope_for_action_class(scope, action_class)` (line 606) to check if ANY
    scope authorizes the requested class.
  - line 610-617: on mismatch returns
    `reason_code=TokenValidationReasonCode.SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS`
    with `scope_action_class_mismatch=True` and `requested_action_class=<name>`.
- Reason code enum: `TokenValidationReasonCode.SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS`
  defined at line 85 (commented "HXA30").
- Helper: `validate_scope_for_action_class()` defined at line 776 (module-level), in
  "SECTION 8: Action Class Scope Mappings (HXA29)" (line 749). It is NOT standalone
  -- it is the function Gate 13 calls.

Live wiring through Hermes (the production validation path):
File: `modules/infrastructure/wre_core/src/hermes_job_executor.py`

- line 1434: `action_class = self._classify_destructive_action(job, request)`
  (classifies the requested action into a `DestructiveActionClass`).
- line 1442-1443: `token_validation_result = self._validate_token_if_present(job,
  request, action_class=action_class)`.
- line 1312-1318: `_validate_token_if_present` calls
  `self.token_validator.validate_token(..., action_class=action_class)` (line 1312,
  passing `action_class=action_class` at line 1318) -- "HXA30: Pass action class for
  scope validation".

Conclusion: current main DOES enforce scope-to-action-class during capability token
validation, end-to-end, from Hermes job classification through `validate_token`
Gate 13.

Naming note: main emits `SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS` (the HXA30 reason
code). The stranded worktree's reason code `SCOPE_ACTION_CLASS_MISMATCH` does NOT
exist in main (0 occurrences). Both are the same logical "mismatch" signal; only the
string differs.

---

## 4. Stranded HXA29 Comparison (agent-ad998a8)

Stranded worktree: `.claude/worktrees/agent-ad998a8e0c488774a`
(branch `worktree-agent-ad998a8e0c488774a`, HEAD `facdd7362`, locked).
Per #742 the work is UNCOMMITTED/dirty. Confirmed read-only via
`git -C <wt> status --porcelain`:

- ` M modules/infrastructure/wre_core/ModLog.md`
- ` M modules/infrastructure/wre_core/src/capability_token_validator.py`
- ` M modules/infrastructure/wre_core/tests/TestModLog.md`
- `?? docs/audits/openclaw_hermes/HXA29_TOKEN_SCOPE_VALIDATION.md`
- `?? modules/infrastructure/wre_core/tests/test_hxa29_token_scope_validation.py`

What the stranded validator wires in (from `git -C <wt> diff` of
`capability_token_validator.py`, +225 lines):

- New reason code `SCOPE_ACTION_CLASS_MISMATCH` (added to `TokenValidationReasonCode`).
- New helper classes `ActionClassScope` and `ScopeActionClassMapping` (severity-based
  scope->max-class mapping, fail-closed on unknown scope).
- "Gate 10.5 (HXA29)" inside `validate_token`:
  `if action_class is not None and requested_scope is not None:` then
  `ScopeActionClassMapping.scope_authorizes_class(requested_scope, action_class)`;
  on failure returns
  `reason_code=TokenValidationReasonCode.SCOPE_ACTION_CLASS_MISMATCH`.
- `action_class` parameter added to the `ICapabilityTokenValidator` Protocol and to
  `LocalCapabilityTokenValidator.validate_token`.

Key difference vs main (security-relevant):

- Stranded Gate 10.5 is gated on BOTH `action_class is not None` AND
  `requested_scope is not None`. It validates against the SINGLE caller-supplied
  `requested_scope` parameter only. A caller that omits `requested_scope` (or supplies
  none) bypasses the check entirely.
- Main Gate 13 is gated only on `action_class is not None`. It iterates over ALL
  `token.scopes` and blocks unless SOME scope authorizes the class. It does not depend
  on the caller passing `requested_scope`, so it cannot be bypassed by omitting that
  argument. Main's wiring is therefore the STRONGER, harder-to-bypass implementation.

Net: the stranded worktree contains an EARLIER, partial design of the same primitive.
Its core security idea (scope must authorize action class, fail-closed) is the same
idea that main already implements -- and main implements it more robustly. The
stranded primitive is NOT a unique capability missing from main; main supersedes it.

---

## 5. Test Coverage Evidence

Production callers of `validate_scope_for_action_class()` in main (excluding the
`def`, docstring `>>>` examples, and test files):

- COUNT = 1.
  - `modules/infrastructure/wre_core/src/capability_token_validator.py:606`
    (inside `validate_token` Gate 13).

Tests asserting mismatch enforcement (`SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS` and/or
`scope_action_class_mismatch is True`) via the live `validate_token` path:

- File `modules/infrastructure/wre_core/tests/test_hxa30_scope_to_action_class_integration.py`
  (drives the real `HermesJobExecutor.execute -> _validate_token_if_present ->
  validate_token` path, dry_run, then asserts BLOCKED_BY_TOKEN_VALIDATION + reason
  code + `guard_evaluated is False`):
  - `test_d3_token_d4_action_blocked_before_guard` (assertion at line 276-279,
    `requested_action_class == "D4_WRITE_REPO"`).
  - `test_d3_token_d5_action_blocked_before_guard` (assertion at line 352-353,
    `requested_action_class == "D5_EXTERNAL_SIDE_EFFECT"`).
  - `test_d3_token_d6_action_blocked_before_guard` (assertion at line 426).

- File `modules/infrastructure/wre_core/tests/test_hxa29_token_scope_validation.py`
  (the landed HXA29 test file; note the landed version asserts the HXA30 reason code,
  confirming it was aligned to the wired implementation):
  - `test_d3_token_blocked_for_d4_create_repo` (assertion at line 287-288).
  - `test_d3_token_blocked_for_d5_send_email` (assertion at line 353-354).
  - `test_d3_token_blocked_for_d6_delete_foundup` (assertion at line 419-420).

- COUNT of distinct test methods proving mismatch enforcement: 6 (3 in the HXA30
  integration suite + 3 in the landed HXA29 suite). All assert reason code
  `SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS`; the HXA30 D4 case and all three HXA29 cases
  additionally assert `scope_action_class_mismatch is True`.

No test in main references `SCOPE_ACTION_CLASS_MISMATCH` (the stranded reason code);
that string has 0 occurrences in main `*.py`.

---

## 6. Gap Verdict

GAP_NOT_CONFIRMED.

Rationale: #742's "0 callers" observation was correct only at the HXA29 (#575)
boundary, which landed the standalone helper without a caller. The subsequent HXA30
(#576) landed Gate 13 in `validate_token` (caller at
`capability_token_validator.py:606`) and threaded `action_class` through the Hermes
path (`hermes_job_executor.py:1318`, `:1443`). Current main therefore enforces
scope-to-action-class during live capability-token validation, with 6 tests proving
mismatch emission. There is no LIVE enforcement gap on main @ 40e0ef66a.

The discrepancy with #742 is explained by PR sequencing: #742's preliminary grep
searched for the helper's callers but did not detect that HXA30 (one PR later) had
already wired it in.

---

## 7. Security Impact If Confirmed

Not confirmed, so no live exposure exists on current main. For completeness, IF the
gap had been real (helper present but never called), the impact would have been:
a D3-sandbox-scoped capability token could pass `validate_token` while requesting a
D4/D5/D6 action (repo write, external side effect, irreversible), because the
scope->action-class ceiling would not be enforced at the token layer. The
`DestructiveActionGuard` still blocks D4+ in Phase 1, so this would have degraded a
defense-in-depth layer rather than fully opening privilege escalation -- but the
intended belt-and-suspenders token-layer check would have been silently inert. Main
does not have this exposure.

Residual (non-blocking) observation: the stranded design and the landed design use
DIFFERENT reason-code strings (`SCOPE_ACTION_CLASS_MISMATCH` vs
`SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS`). Any external consumer or doc that referenced
the stranded string would not match main's emitted code. This is a naming/consistency
note only, not an enforcement gap.

---

## 8. Recommended Remediation Slice

Recommended slice name (if any follow-up is desired): NONE REQUIRED for the
enforcement gap -- it is already closed by HXA30 (#576).

Salvage decision: DO NOT salvage `agent-ad998a8`'s integrated Gate 10.5. Main already
wires the equivalent (and stronger) check via the existing standalone helper at Gate
13. Salvaging the stranded Gate 10.5 would (a) duplicate enforcement, (b) introduce a
weaker, `requested_scope`-dependent variant that can be bypassed by omitting the
argument, and (c) add a second, conflicting reason-code string. The stranded worktree
should remain parked per #742 (HXA29_PROTECTED); this audit does not authorize its
removal or unlock.

Optional, separate, low-priority hygiene slice (NOT part of this Phase 1 and not a
security fix): HXA29_SCOPE_ACTION_REASON_CODE_DOC_ALIGNMENT_PHASE1 -- confirm all
docs/consumers reference the landed `SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS` string and
retire any lingering references to the stranded `SCOPE_ACTION_CLASS_MISMATCH` name.
This is documentation-only and may be deferred indefinitely.

---

## 9. Internal Review Verdict

READY.

The doc answers all five mission questions with file:line evidence:

1. YES -- main enforces scope-to-action-class during token validation
   (`capability_token_validator.py:594-617`, Gate 13).
2. YES -- `validate_scope_for_action_class()` is called from `validate_token`
   (`capability_token_validator.py:606`), reached live via Hermes
   (`hermes_job_executor.py:1318` and `:1443`). Production caller count = 1.
3. YES -- 6 test methods assert mismatch enforcement (3 in
   `test_hxa30_scope_to_action_class_integration.py`, 3 in
   `test_hxa29_token_scope_validation.py`), all emitting
   `SCOPE_DOES_NOT_AUTHORIZE_ACTION_CLASS`.
4. NO unique missing primitive -- the stranded HXA29 Gate 10.5 is an earlier, weaker
   variant of the same idea main already implements more robustly.
5. Use the EXISTING wired path (HXA30 Gate 13); do NOT salvage the stranded Gate 10.5.

Verdict: GAP_NOT_CONFIRMED.

---

## 10. WSP_97 Truth Boundary Checklist

Declared items: 14 - Rows: 14 - All YES

| # | Truth Boundary Checklist Item | Status | Evidence |
| - | ----------------------------- | ------ | -------- |
| 1 | READ_ONLY_SECURITY_AUDIT | YES | Only read commands used (git status/diff/show/log, Grep, Read); no source edited. |
| 2 | NO_CODE_CHANGE | YES | `git status --porcelain` shows only the new audit doc; no `*.py` modified. |
| 3 | NO_TEST_CHANGE | YES | No test file added/modified/deleted; tests only read for evidence (Section 5). |
| 4 | NO_CHERRY_PICK | YES | No `git cherry-pick`/merge/apply run; stranded diff only read via `git -C <wt> diff`. |
| 5 | NO_STRANDED_WORK_MUTATION | YES | Stranded worktree inspected read-only (`git -C <wt> status/diff/rev-parse`); not modified/committed/unlocked/cleaned. |
| 6 | NO_BRANCH_DELETE | YES | No branch deleted; only created `docs/hxa29-scope-action-validation-enforcement-audit-phase1`. |
| 7 | NO_WORKTREE_REMOVAL | YES | No `git worktree remove/prune` run; stranded worktree remains locked. |
| 8 | HXA29_PROTECTED | YES | `agent-ad998a8` left untouched and locked; Section 8 declines salvage/removal. |
| 9 | CITES_PR_742 | YES | Section 2 cites #742 (and #575/HXA29, #576/HXA30 landings). |
| 10 | NO_CABR_READY | YES | No CABR readiness claimed/changed; audit is read-only docs. |
| 11 | NO_PAYOUT_READY | YES | No payout readiness claimed/changed. |
| 12 | NO_DAO_ACTIVATION | YES | No DAO activation claimed/changed. |
| 13 | SINGLE_NEW_FILE_ONLY | YES | Exactly one new file: this audit doc; `.claude/settings.local.json` left unstaged. |
| 14 | ASCII_CLEAN | YES | Doc authored ASCII-only; no smart quotes/mojibake. |
