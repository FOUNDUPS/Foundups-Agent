# WRE ContextBundle Dry-Run Consumer Phase 1 (W6)

**Slice**: WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1
**Author**: 0102 (W6) | **Commander**: 012 | **Reviewer**: W10
**Base**: `90a7ec0ee` (origin/main after #779 and #781)
**Branch**: `w6/wre-context-bundle-dryrun-consumer-phase1`
**Type**: Limited implementation (first consumer wiring; dry-run only; no live execution)
**Effort**: ULTRA

## Summary

First consumer wiring of the read-only #775 ContextBundle into the EXISTING
dry-run evidence path. STANDALONE module + tests (ruling A) that consume a
ContextBundle as TRUSTED input and RETURN a typed `DryRunResult` (ruling B:
return-value-only, no side effects). It performs NO live build, NO real
execution, NO subprocess, NO Hermes real delegation, NO executor sink, NO FAM
event, and NO file write. It is NOT plumbed into the live OpenClaw/WRE loop;
runtime wiring into the #774 WRE consumer dispatch seam is a separate Phase-2
slice.

## Existing dry-run path ADOPTED (not invented)

Two existing dry-run primitives were confirmed in Phase-0 and adopted
STANDALONE (no live-loop wiring, no second orchestrator):

- `modules/foundups/agent/src/hermes_foundup_job_executor.py:104-261`
  (`execute_foundup_job`) -- resolves module_path via the shared
  `_resolve_validated_module_path` (line 186) before any sink; real-exec sink
  is `HermesFoundUpBuilder.extract_foundup`.
- `modules/foundups/agent/src/build_plan_executor.py:618-665`
  (`BuildPlanExecutor.execute_step`) -- dry-run delegates to `simulate_step`
  (SIMULATED); real returns BLOCKED (`REAL_EXECUTION_NOT_IMPLEMENTED`);
  `ExecutionReceipt` truth fields always False.

The wre_core `modules/infrastructure/wre_core/src/hermes_job_executor.py`
real-delegation entry point remains BLOCKED
(`BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED`) with `HERMES_DELEGATE_ENABLED`
default 0; the consumer never enables the flag and never calls that sink.

## Files

- NEW `modules/foundups/agent/src/context_bundle_dry_run_consumer.py`
- NEW `modules/foundups/agent/tests/test_context_bundle_dry_run_consumer.py`
  (51 tests, 0 skip/xfail)
- DOCS: module `ModLog.md` / `INTERFACE.md` / `ROADMAP.md` /
  `tests/TestModLog.md` (WSP 22 order) + this WSP_97 table + root `ModLog.md`.

## DryRunResult contract (rulings A/B, pinned for the gate)

- `planned_actions` -- declared build/test actions that WOULD run (argv/None);
  every action `executed=False`; never executed.
- `resolved_module_path` -- validated canonical path from the bundle / shared
  resolver; never a payload value.
- `source_authority` -- equals `monorepo_poc`.
- `gates_to_recheck` -- gate NAMES from the bundle; not pass-state.
- `readiness_flags` -- echoed from the bundle, all False.
- `evidence_refs` -- the bundle's file_refs (path + sha256 + size + role);
  NO bodies.
- `rejected_input` -- observable-ignore of any payload value ignored/rejected.
- `dry_run: true` / `real_execution_performed: false`.

## Tests

- New consumer suite: 51 passed, 0 skip/xfail.
- Full `modules/foundups/agent/tests/`: 697 passed, 0 skip/xfail.

## WSP_97 Truth Boundary

| # | Truth Boundary Checklist Item | Status | Evidence |
| - | --- | --- | --- |
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | 3 HoloIndex queries run; top hits = build_plan_executor.py, hermes_foundup_job_executor.py, context_bundle_builder.py, module_path_resolution.py, source_authority.py (ModLog Phase 0). |
| 2 | HOLOINDEX_RETRIEVAL_ASSESSED | YES | Retrieval signal GOOD post-#781 reindex; canonical files in top hits; cross-checked via Read/Grep against committed base (ModLog Phase 0). |
| 3 | EXISTING_DRYRUN_PATH_ADOPTED_NOT_INVENTED | YES | Adopts hermes_foundup_job_executor.py:104-261 + build_plan_executor.py:618-665 dry-run primitives STANDALONE; no new orchestrator/loop. |
| 4 | CONTEXTBUNDLE_CONSUMED_AS_TRUSTED_INPUT | YES | `consume_context_bundle_dry_run(bundle, ...)` reads validated bundle fields; does NOT re-derive trust from raw payload (consumer step 1-6). |
| 5 | MODULE_PATH_VIA_SHARED_RESOLVER_ONLY | YES | `resolved_module_path = bundle.module_path`; job path re-validated via shared `_resolve_validated_module_path`; payload never used (consumer step 4). |
| 6 | NO_SECOND_RESOLVER | YES | AST test `test_consumer_defines_no_second_resolver` + `test_exactly_one_resolver_definition_repo_wide`; grep confirms 1 def in module_path_resolution.py:196. |
| 7 | SOURCE_AUTHORITY_MONOREPO_POC_ONLY | YES | `REQUIRED_SOURCE_AUTHORITY = monorepo_poc`; non-monorepo_poc refused (consumer step 1; tests dao_managed/mvp_runtime/external_proto). |
| 8 | NO_STAGE_PROMOTION | YES | Uses `resolve_source_authority` + `ACTIVE_STAGES`; `request_promotion` never called; `test_consumer_cannot_promote_stage`. |
| 9 | GATES_ARE_NAMES_NOT_PASS_STATE | YES | `gates_to_recheck` = bundle gate names verbatim; no gate-pass boolean computed/serialized (`test_no_gate_pass_boolean_in_serialized_result`). |
| 10 | DRYRUN_EMITS_EVIDENCE_NO_REAL_EXECUTION | YES | `dry_run=True`/`real_execution_performed=False`; extract_foundup + wre_core delegation + subprocess `assert_not_called` (TestNoRealExecution). |
| 11 | HERMES_DELEGATE_FLAG_RESPECTED | YES | Consumer never sets `HERMES_DELEGATE_ENABLED`; `is_hermes_delegation_enabled()` stays False (TestHermesDelegateFlagRespected). |
| 12 | NO_NEW_ORCHESTRATOR | YES | AST test `test_consumer_imports_no_orchestrator_or_runtime_loop` (openclaw / wre_master_orchestrator / build_plan_swarm / ai_overseer absent). |
| 13 | NO_EXTERNAL_AGENT | YES | `external_agent_allowed`/`can_self_authorize`==True refused (consumer step 3); bundle producer also keeps them False. |
| 14 | NO_READINESS_PROMOTION | YES | Readiness echoed all False; any True flag refused (consumer step 2); `test_readiness_flags_echoed_all_false`. |
| 15 | NO_REPO_CONCATENATION_NO_FILE_BODIES | YES | `evidence_refs` = path+sha256+size+role only; manifest body line asserted ABSENT (`test_no_manifest_body_text_in_serialized_result`). |
| 16 | REJECTED_INPUT_OBSERVABLE | YES | `rejected_input` surfaces the resolver's ignored payload candidate even on success; rejection messages include the rejected value (TestForgedPayloadRejected). |
| 17 | NO_PRODUCER_OR_VALIDATOR_MUTATION | YES | `git diff --name-only 90a7ec0ee` does not list context_bundle_builder.py / module_path_resolution.py / source_authority.py / foundup_manifest_validator.py. |
| 18 | STANDALONE_CONSUMER_NOT_RUNTIME_WIRED | YES | Module returns a preview only; no import of OpenClaw/WRE loop; Phase-2 runtime wiring deferred (ROADMAP). |
| 19 | DRYRUNRESULT_RETURN_VALUE_ONLY_NO_SIDE_EFFECTS | YES | Frozen dataclass returned; `test_no_file_write_during_consumption` (open write-mode sentinel) + `test_result_is_frozen_dataclass`. |
| 20 | NO_FAM_EVENT_NO_FILE_WRITE | YES | No fam_daemon/fam_event import (`test_no_fam_event_module_imported`); no write_text/open(w) (AST no-write test). |
| 21 | NO_USER_QUESTION_FRAMING | YES | This doc and the ModLog state evidence-backed recommendations; no "user questions"; operator is 012. |
| 22 | CITES_PR_775_777_778_779 | YES | #775 (ContextBundle producer), #777 (source_authority), #778/#779 (shared module_path resolver) cited in source docstring, ModLog, INTERFACE, ROADMAP, and this table. |
| 23 | ASCII_CLEAN | YES | Both new .py files 0 non-ASCII (byte-checked); this doc authored ASCII-clean. |
