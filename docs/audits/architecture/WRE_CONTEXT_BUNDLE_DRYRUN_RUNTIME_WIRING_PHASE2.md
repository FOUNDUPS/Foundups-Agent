# WRE ContextBundle Dry-Run Runtime Wiring Phase 2 (W6)

**Slice**: WRE_CONTEXT_BUNDLE_DRYRUN_RUNTIME_WIRING_PHASE2
**Author**: 0102 (W6) | **Commander**: 012 | **Reviewer**: W10
**Base**: `22423bfd0` (origin/main = #786 dry-run consumer)
**Branch**: `w6/wre-context-bundle-dryrun-runtime-wiring-phase2`
**Type**: Limited implementation (FIRST runtime integration; dry-run path only; no live execution)
**Effort**: ULTRA

## Summary

Wires the standalone #786 ContextBundle dry-run consumer
(`consume_context_bundle_dry_run` -> `DryRunResult`) into the EXISTING #774
OpenClaw/WRE dispatch seam (`FoundUpJobConsumer` -> `ConsumerResult`) on the
seam's PRE-EXISTING dry-run branch ONLY. The wiring builds the read-only #775
`ContextBundle` and calls the #786 consumer, then maps the returned
`DryRunResult` into the EXISTING `ConsumerResult` receipt via one new OPTIONAL
evidence field (`context_bundle_dry_run`). NO live Hermes delegation, NO real
execution, NO subprocess, NO second orchestrator, NO second resolver, NO new
receipt type, NO synthetic dry-run branch. The real-exec / Hermes-delegation
boundary stays BLOCKED and byte-unchanged.

## Existing seam + PRE-EXISTING dry-run branch (identified, not invented)

All constructs below pre-existed at Base `22423bfd0` (proven via
`git show 22423bfd0:<path>`):

- EXISTING seam: `modules/infrastructure/wre_core/src/foundup_job_consumer.py`
  - `class ConsumerResult` (line 112 at Base) -- the EXISTING receipt /
    evidence type the seam emits.
  - `FoundUpJobConsumer.consume_one` -> `_dispatch_to_hermes` (line 405 at
    Base) -> `execute_foundup_job(job)` -- the WRE consumer that consumes a
    FoundUpJob and dispatches to the Hermes backend.
- PRE-EXISTING dry-run branch/gate:
  `modules/infrastructure/wre_core/src/hermes_job_executor.py`
  - `is_hermes_delegation_enabled()` reads `HERMES_DELEGATE_ENABLED`
    (default "0") (line 92-95 at Base).
  - `execute` Step 4 `if not is_hermes_delegation_enabled():` (line 1767 at
    Base) returns `HermesExecutionStatus.SIMULATED` (line 1773) with
    `real_execution_performed=False` -- the dry-run branch.
  - `execute` Step 5 `if self.dry_run:` (line 1795) also returns `SIMULATED`.
  - `execute` Step 7 `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` (line 1849) --
    the real-exec branch, only reachable when the flag is enabled AND
    `dry_run=False`. UNCHANGED by this slice.

The wiring attaches the bundle evidence ONLY when the executor returns
`SIMULATED` AND `real_execution_performed` is False AND
`is_hermes_delegation_enabled()` is False (positive control). On the real-exec
/ BLOCKED branch the helper returns None and contributes no evidence.

## Consumed AS-IS (NOT modified)

- `context_bundle_dry_run_consumer.py` (#786) -- `consume_context_bundle_dry_run`.
- `context_bundle_builder.py` (#775) -- `build_context_bundle`.
- `module_path_resolution.py` (#778/#779) -- single `_resolve_validated_module_path`.
- `source_authority.py` (#777) -- `resolve_source_authority` / `ACTIVE_STAGES`.
- `hermes_job_executor.py` -- the executor + its real-exec branch (untouched).

`git diff --name-only` does NOT list any of these files.

## Files

- CHANGED `modules/infrastructure/wre_core/src/foundup_job_consumer.py`
  (+192 lines, 0 deletions): one OPTIONAL field `context_bundle_dry_run` on
  the EXISTING `ConsumerResult` (+ its `to_dict`), one new private method
  `_attach_context_bundle_dry_run`, and one call to it inside the
  PRE-EXISTING dry-run branch of `_dispatch_to_hermes`.
- NEW `modules/infrastructure/wre_core/tests/test_foundup_job_consumer_context_bundle_wiring.py`
  (24 tests, 0 skip/xfail).
- DOCS: `modules/infrastructure/wre_core/ModLog.md`, root `ModLog.md`, this
  WSP_97 table (WSP 22).

## Pinned-design conformance

1. Wiring runs INSIDE the EXISTING dry-run branch only; builds #775 bundle and
   calls the #786 consumer; maps `DryRunResult` into the EXISTING
   `ConsumerResult` via one optional field. No new orchestrator/loop, no new
   receipt type.
2. Real-exec / Hermes-delegation branch UNCHANGED and BLOCKED
   (`HERMES_DELEGATE_ENABLED=0` boundary intact;
   `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` untouched; executor not modified).
3. `module_path` resolves via the single shared resolver / the bundle; no
   second resolver.
4. `source_authority=monorepo_poc` visible in the emitted result;
   non-monorepo_poc refused (inherited from #786). Readiness stays False; gates
   are recheck-NAMES; no external agents; ContextBundle stays refs + sha256
   only (no bodies) end-to-end.

## WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | 3 HoloIndex queries run (Phase 0). Top hits: foundup_job_consumer.py, foundup_job_router.py, hermes_job_executor.py, proof_of_compute_receipt.py, openclaw_foundup_orchestrator.py, hermes_adapter.py. |
| 2 | HOLOINDEX_RETRIEVAL_ASSESSED | YES | Retrieval signal GOOD: the canonical seam files surfaced in code hits; cross-checked every load-bearing file vs committed Base via `git show 22423bfd0:<path>` + Grep before edit (tool-staleness guard). |
| 3 | EXISTING_774_SEAM_DRYRUN_BRANCH_IDENTIFIED | YES | Seam = `foundup_job_consumer.py` (`ConsumerResult`, `_dispatch_to_hermes` -> `execute_foundup_job`); dry-run branch = `hermes_job_executor.py:1767` `if not is_hermes_delegation_enabled()` -> `SIMULATED`. |
| 4 | EXISTING_DRYRUN_BRANCH_PREEXISTED_THIS_SLICE | YES | `git show 22423bfd0:.../hermes_job_executor.py` shows `is_hermes_delegation_enabled` (l.92), `SIMULATED` dry-run branch (l.1767/1773, l.1795/1801) and `ConsumerResult` (l.112) BEFORE this slice. |
| 5 | USES_EXISTING_SEAM_NOT_NEW_LOOP | YES | Change adds one optional field + one helper + one call inside the EXISTING `_dispatch_to_hermes` dry-run path; AST test asserts no `WREMasterOrchestrator` / new orchestrator import. |
| 6 | CONSUMER_CALLED_DRYRUN_PATH_ONLY | YES | `_attach_context_bundle_dry_run` returns None unless status==SIMULATED AND `real_execution_performed` False AND `is_hermes_delegation_enabled()` False; tests `test_real_exec_branch_attaches_no_bundle`, `test_real_execution_performed_true_attaches_no_bundle`. |
| 7 | HERMES_DELEGATE_FLAG_0_BOUNDARY_INTACT | YES | Helper imports `is_hermes_delegation_enabled` as a positive control; flag is never assigned; `test_flag_zero_keeps_real_delegation_blocked`. |
| 8 | REAL_EXEC_SINKS_ASSERT_NOT_CALLED | YES | `test_subprocess_sinks_not_called_through_seam` (Popen/run/call assert_not_called) + `test_hermes_real_delegate_loader_not_called_through_seam` (`_lazy_import_delegate_task` assert_not_called) through `consume_one`. |
| 9 | DRYRUNRESULT_REACHES_EXISTING_CONSUMERRESULT_RECEIPT | YES | `DryRunResult.to_dict()` stored on `ConsumerResult.context_bundle_dry_run` and surfaced via `ConsumerResult.to_dict`; `test_dry_run_evidence_survives_consumerresult_to_dict`. |
| 10 | CONTEXTBUNDLE_REFS_HASHES_ONLY_NO_BODIES | YES | `test_evidence_refs_are_refs_and_hashes_only_no_bodies`: ref keys subset {path,sha256,size_bytes,role}; 64-hex sha256; no body/content/source_text key in serialized receipt. |
| 11 | SOURCE_AUTHORITY_MONOREPO_POC_VISIBLE | YES | `test_source_authority_monorepo_poc_visible`, `test_seam_only_ever_emits_monorepo_poc`: `context_bundle_dry_run.source_authority == "monorepo_poc"`. |
| 12 | GATES_ARE_RECHECK_NAMES_NOT_PASS | YES | `test_gates_are_recheck_names_not_pass_state` (each gate is a name str, never bool) + `test_no_gate_pass_boolean_serialized` (forbidden pass-state keys absent). |
| 13 | READINESS_REMAINS_FALSE | YES | `test_readiness_remains_false`: every `readiness_flags` value is False; inherited from #786 / #775 refusal of promoted readiness. |
| 14 | NO_EXTERNAL_AGENTS | YES | No external-agent import/enable added; #786 consumer refuses `external_agent_allowed=True` (consumed as-is); seam adds no agent surface. |
| 15 | NO_NEW_ORCHESTRATOR | YES | `test_seam_imports_no_new_orchestrator`; the only loop is the PRE-EXISTING drain; no new orchestrator/loop class added. |
| 16 | NO_SECOND_RESOLVER | YES | `test_seam_defines_no_module_path_resolver` + `test_exactly_one_resolver_definition_repo_wide`; grep: 1 `def _resolve_validated_module_path` in module_path_resolution.py:196. |
| 17 | NO_REAL_EXECUTION | YES | Helper is return-value-only (build bundle + consume); no subprocess/Popen/network/file-write; executor real-exec branch untouched; `real_execution_performed` stays False. |
| 18 | NO_CONSUMER_OR_PRODUCER_OR_VALIDATOR_MUTATION | YES | `git diff --name-only` lists only `foundup_job_consumer.py` (+ new test, docs); #786 consumer / #775 builder / resolver / source_authority / validator / executor NOT modified. |
| 19 | NO_USER_QUESTION_FRAMING | YES | This doc and the completion report state evidence-backed WSP_97 conclusions; no "user questions"; the operator is 012. |
| 20 | CITES_PR_774_775_786 | YES | Seam = #774 consumer; producer = #775 `build_context_bundle`; consumer = #786 `consume_context_bundle_dry_run`; resolver = #778/#779; authority = #777. |
| 21 | ASCII_CLEAN | YES | New test file 0 non-ASCII; added seam lines 0 non-ASCII (`test_wiring_additions_are_ascii_clean`; byte-check via diff). |
