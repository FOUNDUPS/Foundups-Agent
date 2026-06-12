# Operational-WRE Monorepo-PoC -- Operator Runbook (Phase 1)

Slice: OPERATIONAL_WRE_MONOREPO_POC_OPERATOR_RUNBOOK_PHASE1
Base SHA: a9fd0cb19
Status: dry-run reproduce/interpret guide, decision-only.

This runbook lets 012/0102 (a) reproduce the merged monorepo-PoC dry-run
vertical proof and (b) correctly interpret its evidence and boundary. It adds
NO code, NO test, NO production change, and does NOT move toward real
execution. Every operator-visible field cite below is grounded against the
merged proof test at base a9fd0cb19; every architecture/boundary fact POINTS to
the already-merged closeout doc rather than re-citing raw boundary file:line.

Pointers used throughout:
- Closeout (formal boundary):
  `docs/audits/architecture/OPERATIONAL_WRE_MONOREPO_POC_CLOSEOUT_PHASE1.md`
- Proof test (stable evidence artifact, merged in #788):
  `modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py`

---

## 1. PURPOSE & SCOPE

This runbook is for two operator tasks and nothing more:

1. Reproduce the merged dry-run vertical proof (one command).
2. Interpret the proof evidence and its boundary correctly.

Scope is `monorepo_poc`, DRY-RUN ONLY. Stated plainly:

- This is NOT MVP.
- This is NOT external_proto.
- This is NOT real / live execution.
- This is NOT a deployment guide.

A green run proves the dry-run evidence loop works. It does NOT prove
real-execution viability. For the formal boundary, see the closeout doc
Section 3 (WHAT IS NOT MVP -- this is monorepo_poc ONLY) and Section 4 (WHAT IS
NEEDED FOR external_proto -- DEFERRED).

---

## 2. PREREQUISITES

- Repo checked out at current main (a9fd0cb19 or later). The proof test landed
  in #788 (base 4f57af549) and is present at a9fd0cb19.
- A Python test environment per the repo standard (the same env that runs the
  rest of the suite). No extra packages are required by the proof itself.
- `HERMES_DELEGATE_ENABLED` unset or `"0"`. This is the dry-run-branch
  precondition. The flag is truthy only for `"1"` / `"true"` / `"yes"`
  (case-insensitive); if it is enabled, the seam intentionally does NOT take
  the dry-run evidence path and the proof's dry-run assertions do not apply.
  For why real delegation stays blocked on the dry-run branch, see the closeout
  doc Section 2 (WHAT IS STILL DRY-RUN / SIMULATED -- real execution is
  BLOCKED).
- No manual mocking is required. The proof test self-contains its
  real-execution-sink mocks (subprocess and the executor's real-delegate
  loader); the operator does not patch anything.

---

## 3. REPRODUCE THE PROOF

Run this EXACT command from the repo root:

```
python -m pytest modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py -q
```

Expected result: `3 passed`, exit code 0. (The duration varies run to run and
is not a pass criterion -- do not pin it.)

The 3 tests, one line each:

- `TestActionReachesSimulated::test_validate_reaches_simulated_build_extract_blocked`
  -- only `validate_foundup` reaches SIMULATED; `build_foundup` /
  `extract_foundup` are guard-blocked.
- `TestOperationalWREMonorepoPoCVerticalProof::test_full_dry_run_invocation_end_to_end`
  -- real `dispatch_foundup` (create) + drain seam end-to-end; the dry-run
  evidence attaches and no real execution occurs.
- `TestForgedModulePathFailsEndToEnd::test_forged_cross_foundup_module_path_rejected_via_seam`
  -- a forged cross-FoundUp `module_path` is rejected end-to-end.

The SEAM ITSELF is never mocked (real create entry, real drain entry, real
dispatch, real executor, real #786 consumer). ONLY the real-execution sinks are
mocked, and they are asserted `assert_not_called`.

---

## 4. INTERPRET THE EVIDENCE

What a green run of `test_full_dry_run_invocation_end_to_end` (and, where noted,
the forged-path test) demonstrates. Cites are file:line in the proof test at
base a9fd0cb19.

| Field | What a green run shows | Expected value | Proof-test cite (a9fd0cb19) |
|-------|------------------------|----------------|-----------------------------|
| `checkpoint_state` | Seam took the dry-run (SIMULATED) branch | `"SIMULATED"` | test:289 |
| `real_execution_performed` (consumer-level) | No real execution occurred | `False` | test:290 |
| `dry_run` | Evidence blob is a dry-run | `True` | test:302 |
| `bundle_id` | ContextBundle producer (#775) ran | non-empty str | test:304 |
| `consumer_version` | Dry-run consumer (#786) ran | non-empty str | test:305 |
| `source_authority` | Authority pinned to monorepo_poc | `"monorepo_poc"` | test:314 (serialized receipt: test:311) |
| `resolved_module_path` | Path came from the validated resolver, NOT the payload | manifest-validated canonical path | test:318 |
| `rejected_input.resolver_run` | The shared resolver actually ran | `True` | test:321 |
| `rejected_input.payload_module_path_ignored` | No payload module_path was trusted (create entry injected none) | `None` | test:322 |
| `rejected_input.resolver_failed` | Resolution succeeded | `False` | test:323 |
| WSP_97 receipt: `verification_complete` | Truth field not promoted | `False` | test:372 |
| WSP_97 receipt: `cabr_ready` | Truth field not promoted | `False` | test:373 |
| WSP_97 receipt: `payout_ready` | Truth field not promoted | `False` | test:374 |
| No-file-body scan (`_FORBIDDEN_BODY_KEYS`) | No file bodies leak into the receipt | none present | keys def test:106; scan test:341-344 |
| No-pass-state scan (`_FORBIDDEN_SERIALIZED_KEYS`) | No gate-pass / pass-state key leaks into the dry-run evidence | none present | keys def test:98-103; scan test:354-358 |
| Mocked sink `subprocess.Popen` | Real execution sink never fired through the seam | not called | patch test:252; assert test:277 |
| Mocked sink `subprocess.run` | Real execution sink never fired through the seam | not called | patch test:253; assert test:278 |
| Mocked sink `subprocess.call` | Real execution sink never fired through the seam | not called | patch test:254; assert test:279 |
| Mocked sink `HermesJobExecutor._lazy_import_delegate_task` | Real-delegate loader never ran in dry-run | not called | patch test:255-261; assert test:280 |
| Forged-path: `context_bundle_error` | Forged cross-FoundUp path is rejected | `"module_path_resolution_failed"` | test:434 |
| Forged-path: `fail_token` | Rejection reason is cross-FoundUp mismatch | `"cross_foundup_mismatch"` | test:435 |
| Forged-path: `resolved_module_path` | Forged value is never used as the resolved path | `None` | test:438 |

The no-body and no-pass-state scans are the load-bearing leak guards: a green
run means none of those keys appeared in the serialized evidence.

---

## 5. THE BOUNDARY -- WHAT A GREEN RUN DOES NOT PROVE

For the formal boundary, POINT to the closeout doc (do not re-derive raw
file:line here):

- Closeout Section 2 -- real execution is BLOCKED.
- Closeout Section 3 -- this is NOT MVP (monorepo_poc ONLY).
- Closeout Section 4 -- external_proto is DEFERRED (enumerated, not a plan to
  start now).

Operator takeaways, in plain language:

- Real Hermes delegation is NOT implemented. With the flag enabled the executor
  returns `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED`; it does not perform real
  work.
- Only `validate_foundup` reaches SIMULATED. `build_foundup` and
  `extract_foundup` are stopped earlier by the D0-D6 destructive-action guard
  (`BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD`).
- There is no CABR, no payout, no DAO in this path. The WSP_97 truth fields stay
  `False`.
- A FoundUp cannot self-promote past `monorepo_poc`.
- `3 passed` proves the dry-run EVIDENCE loop (producer -> consumer ->
  dispatch-seam -> receipt) works. It does NOT prove real-execution viability.

---

## 6. TROUBLESHOOTING / FAILURE INTERPRETATION

If the result is not `3 passed`, map the failure class to the owning seam/PR to
check first:

- `context_bundle_dry_run` fields missing, or `bundle_id` / `consumer_version`
  is `None` -> the ContextBundle producer (#775) or the dry-run consumer (#786)
  is broken.
- `module_path` resolution wrong, `source_authority` wrong, or
  `resolver_failed` is `True` -> the shared validated resolver or the manifest
  validator (#778 / #779) is broken.
- `checkpoint_state` is not `"SIMULATED"`, or the path never reaches SIMULATED
  -> the dispatch-seam wiring (#787) is broken, OR `HERMES_DELEGATE_ENABLED` is
  enabled (re-check the Prerequisites).
- ANY subprocess mock is called (an `assert_not_called` fires) -> real
  execution LEAKED into the dry-run path. STOP. Do not proceed. Escalate. This
  is the load-bearing safety invariant of the proof.

---

## 7. WSP_97 TRUTH BOUNDARY CHECKLIST

This checklist has 11 rows (declared == actual).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | DECISION_DOC_ONLY_NO_CODE_CHANGE | YES | Deliverable is this runbook + one root ModLog entry; `git diff --name-only` against base lists 0 .py / test / .json / .yml files. |
| 2 | POINTS_TO_CLOSEOUT_NOT_DUPLICATED | YES | Section 5 POINTS to closeout Sections 2/3/4 by name; no raw boundary file:line is re-cited. |
| 3 | FIELD_CITES_VERIFIED_AGAINST_MERGED_TEST | YES | Every Section 4 cite verified via `git show a9fd0cb19:modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py`. |
| 4 | REPRODUCE_COMMAND_QUOTED_EXACTLY | YES | Section 3 quotes `python -m pytest modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py -q` verbatim. |
| 5 | EXPECTED_RESULT_3_PASSED_NO_DURATION_PINNED | YES | Section 3 states `3 passed`, exit 0, and explicitly does not pin duration. |
| 6 | BOUNDARY_NOT_PROVEN_SECTION_PRESENT | YES | Section 5 enumerates what a green run does NOT prove. |
| 7 | NO_MOVE_TOWARD_REAL_EXECUTION | YES | No step enables real execution; the dry-run precondition (`HERMES_DELEGATE_ENABLED` unset/0) is preserved as a prerequisite. |
| 8 | SCOPE_MONOREPO_POC_ONLY | YES | Sections 1 and 5 confine scope to monorepo_poc dry-run; not MVP / external_proto / DAO / CABR. |
| 9 | ASCII_CLEAN | YES | Document is 0 non-ASCII bytes (byte-checked before commit). |
| 10 | CITES_PR_775_786_787_788 | YES | #775 (producer), #786 (consumer), #787 (dispatch seam), #788 (proof) cited in Sections 3/4/6. |
| 11 | FILE_SCOPE_EXACTLY_DOC_PLUS_MODLOG | YES | Only this runbook and the root ModLog entry change; `git diff --cached --name-only` lists exactly those two. |
