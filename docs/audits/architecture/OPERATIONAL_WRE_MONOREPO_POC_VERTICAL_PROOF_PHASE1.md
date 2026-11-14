# Operational WRE monorepo-PoC Vertical Dry-Run Proof Phase 1 (W6)

**Slice**: OPERATIONAL_WRE_MONOREPO_POC_VERTICAL_PROOF_PHASE1
**Author**: 0102 (W6) | **Commander**: 012 | **Reviewer**: W10
**Base**: `c7839c2ab` (origin/main = #787 dry-run runtime wiring)
**Branch**: `w6/operational-wre-monorepo-poc-vertical-proof-phase1`
**Type**: VERTICAL PROOF (integration test + proof doc). NO new production code,
NO new wiring, NO broadening of actions.
**Effort**: ULTRA

## Summary

Proves ONE full dry-run invocation end-to-end through the EXISTING OpenClaw/WRE
create+drain seam for a safe monorepo_poc FoundUp (default `gotjunk_001`). The
proof drives the REAL create entry (OpenClaw orchestrator enqueue) AND the REAL
drain entry (WRE consumer over the OpenClaw queue) -- it does NOT mock the seam
and does NOT call the #786 consumer in isolation. The only mocks are the
real-execution SINKS (subprocess `Popen`/`run`/`call` and the executor's
real-delegate loader), asserted `assert_not_called` THROUGH the full seam.

Every acceptance item is asserted in a single pytest invocation. A negative
case proves a forged `module_path` is rejected by the shared validated resolver
end-to-end (observable, never used). No production code changes; the proof
consumes the existing path AS-IS.

## The REAL create/drain path (identified, not invented)

All constructs below pre-existed at Base `c7839c2ab` (proven via
`git show c7839c2ab:<path>`). The proof's new test is the ONLY new file in the
WRE/consumer trees.

### REAL CREATE (OpenClaw orchestrator enqueue)

`modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py`

- `dispatch_foundup(dae, intent)` (line 840) -- the orchestrator entrypoint.
  On an explicit build/validate intent it calls `_handle_build_intent`.
- `_handle_build_intent(intent)` (line 914) -- builds the typed FoundUpJob via
  `create_job(...)` and appends it to the real in-memory queue:
  `_FOUNDUP_JOB_QUEUE.append(job)` (line 976). The queue is declared at
  line 39 (`_FOUNDUP_JOB_QUEUE: List[FoundUpJob] = []`).
- `get_job_queue()` (line 230) -- returns the same real queue the drain reads.

The natural-language intake message `"validate foundup gotjunk_001 --dry-run"`
makes the REAL orchestrator (not the test) extract
`requested_action=validate_foundup`, `foundup_id=gotjunk_001`, and
`policy_flags.dry_run_mode=True`. The create entry builds the job payload
itself; it carries NO `module_path` / `source_module`.

### REAL DRAIN (WRE consumer over the OpenClaw queue)

`modules/infrastructure/wre_core/src/foundup_job_consumer.py`

- `FoundUpJobConsumer.drain_openclaw_queue_with_retention(clear=...)`
  (line 858) -- the real queue drain. It pulls `get_job_queue()` and runs
  each job through `drain_jobs` (line 823) -> `consume_one` (line 370).
- `consume_one` -> `_dispatch_to_hermes` (line 424) -> `execute_foundup_job`
  (Hermes executor) -> `_attach_context_bundle_dry_run` (line 537).
- `ConsumerResult` (line 112) is the EXISTING typed receipt; its
  `context_bundle_dry_run` field (line 188) carries the #786 `DryRunResult`.

### PRE-EXISTING dry-run branch + the #786/#787 wiring

`modules/infrastructure/wre_core/src/hermes_job_executor.py`

- `is_hermes_delegation_enabled()` (line 92) reads `HERMES_DELEGATE_ENABLED`
  (default "0").
- `HermesJobExecutor.execute` Step 4 `if not is_hermes_delegation_enabled():`
  (line 1767) returns `HermesExecutionStatus.SIMULATED` (line 1773) with
  `real_execution_performed=False` -- the dry-run branch.
- `execute_foundup_job(job)` (line 2360) is the module-level convenience the
  consumer calls (singleton, dry_run=True).

The `_attach_context_bundle_dry_run` helper (#787 wiring, line 537) runs ONLY
when the executor returns SIMULATED AND `real_execution_performed` is False AND
`is_hermes_delegation_enabled()` is False. It builds the #775 ContextBundle and
calls the #786 consumer, attaching the returned `DryRunResult` to the EXISTING
receipt.

### Why validate_foundup is the action under proof

`validate_foundup` is the ONLY canonical action that reaches the PRE-EXISTING
SIMULATED branch. `build_foundup` / `extract_foundup` are blocked earlier by the
destructive-action guard (`BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD`). The proof
asserts this control directly (`TestActionReachesSimulated`). So the validate
action is what exercises the #786/#787 dry-run wiring.

## Consumed AS-IS (NOT modified)

- `openclaw_foundup_orchestrator.py` -- real create/enqueue entry.
- `foundup_job_consumer.py` (#774/#787) -- real drain seam + receipt.
- `hermes_job_executor.py` (#787) -- executor + its dry-run / real-exec branch.
- `context_bundle_dry_run_consumer.py` (#786) -- `consume_context_bundle_dry_run`.
- `context_bundle_builder.py` (#775) -- `build_context_bundle`.
- `module_path_resolution.py` (#778/#779) -- single `_resolve_validated_module_path`.
- `source_authority.py` (#777) -- `resolve_source_authority` / `ACTIVE_STAGES`.
- `foundup_manifest_validator.py` (#773) -- canonical module_path validator.

`git diff --name-only c7839c2ab HEAD` lists NONE of these files. It lists only:
the new test, this doc, the wre_core ModLog, and the root ModLog.

## The asserted acceptance chain (single invocation)

Test: `modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py`
Method: `TestOperationalWREMonorepoPoCVerticalProof::test_full_dry_run_invocation_end_to_end`

1. The OpenClaw/WRE path CREATES the job -- real `dispatch_foundup` enqueue
   (`_create_via_real_openclaw_entry`); job is QUEUED `validate_foundup`,
   `dry_run_mode=True`, payload carries NO `module_path` / `source_module`.
2. The OpenClaw/WRE path DRAINS the job -- real
   `drain_openclaw_queue_with_retention` over `get_job_queue()`.
3. The dispatch seam took the DRY-RUN branch -- `checkpoint_state == "SIMULATED"`,
   `real_execution_performed is False`.
4. A ContextBundle was BUILT (#775) and the #786 consumer RAN -- the attached
   `context_bundle_dry_run` carries a populated `DryRunResult`
   (`bundle_id`, `consumer_version`, no `context_bundle_error`).
5. DryRunResult is ATTACHED to the receipt -- `context_bundle_dry_run` present
   on `ConsumerResult` and survives `to_dict()`.
6. `source_authority == "monorepo_poc"`.
7. `module_path` from the shared validated resolver -- `resolved_module_path ==
   "modules/foundups/gotjunk"` (validated canonical, derived from the manifest,
   NOT the payload); `rejected_input.resolver_run is True`,
   `payload_module_path_ignored is None`, `resolver_failed is False`.
8. `evidence_refs` are refs + sha256 (+ size + role) ONLY -- each ref's keys are
   a subset of `{path, sha256, size_bytes, role}`; every sha256 is 64 hex chars.
9. NO file bodies anywhere in the receipt -- no `body`/`content`/`source_text`/
   `file_body` key in the serialized receipt.
10. NO pass-state key in the dry-run evidence -- no gate-pass key in the
    `context_bundle_dry_run` blob; gates are NAME strings, never booleans.
11. NO live Hermes delegation -- `HERMES_DELEGATE_ENABLED` unset; the executor's
    real-delegate loader is patched and `assert_not_called` through the seam.
12. NO subprocess / build execution -- `subprocess.Popen`/`run`/`call` are
    patched and `assert_not_called` through the full create+drain path.
13. Readiness flags remain False -- every flag in `readiness_flags` is `False`;
    the receipt's EXISTING WSP 97 truth fields (`verification_complete`,
    `cabr_ready`, `payout_ready`) are all `False`.

### Negative through the full seam

Method: `TestForgedModulePathFailsEndToEnd::test_forged_cross_foundup_module_path_rejected_via_seam`

A forged job arrives in the real OpenClaw queue carrying a cross-FoundUp
`module_path` (`modules/foundups/kosei` on a `gotjunk_001` job). Draining it
through the REAL WRE entry still reaches SIMULATED, but the shared resolver
REJECTS the forged path end-to-end: `context_bundle_error ==
"module_path_resolution_failed"`, `fail_token == "cross_foundup_mismatch"`,
`resolved_module_path is None` (never used), and the forged value is observable
in `payload_module_path_ignored`. Real-exec sinks are `assert_not_called` here
too. This is proven THROUGH the seam, not at unit level.

## Boundary / isolation notes

- The executor's PRE-EXISTING SIMULATED branch writes observability JSON to
  `.hermes_evidence/{job_id}/` under the workspace root (`_write_evidence`,
  line 2223). This is existing seam behaviour (no subprocess, no real
  delegation). The proof redirects writes to a tmp dir via
  `FOUNDUPS_WORKSPACE_ROOT` and resets the executor singleton, so it leaves no
  repo artifact.
- `gotjunk_001` is a PARAMETERIZED fixture default (`proof_foundup`), not a
  permanent hard-code: add a `(foundup_id, module_path)` tuple to the fixture
  `params` to run the whole vertical proof for any safe monorepo_poc FoundUp.
- The only mocks are the real-execution sinks (subprocess + real-delegate
  loader) for `assert_not_called`. The create entry, drain entry, dispatch,
  executor, and #786 consumer all run for real.

## WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | Phase 0: `holo_index.py --search "FoundUpJobConsumer drain consume_one dispatch foundup job queue create"` + "OpenClaw create foundup job enqueue WRE consumer ConsumerResult". Real entry located by glob + `git show`. |
| 2 | HOLOINDEX_RETRIEVAL_ASSESSED | YES | HoloIndex surfaced contract/router/webhook hits but NOT `foundup_job_consumer.py`; staleness/missing-artifact gap closed by glob (`**/foundup_job_consumer.py`) + base ground-truth read. |
| 3 | REAL_CREATE_DRAIN_PATH_USED_NOT_MOCKED | YES | Test drives `dispatch_foundup` enqueue (orchestrator.py:840/976) + `drain_openclaw_queue_with_retention` (consumer.py:858); `_dispatch_to_hermes` and `consume_context_bundle_dry_run` are NOT mocked. |
| 4 | SEAM_TOOK_DRYRUN_BRANCH | YES | `result.checkpoint_state == "SIMULATED"`, `result.real_execution_performed is False` (executor SIMULATED branch, hermes_job_executor.py:1767-1773). |
| 5 | CONTEXTBUNDLE_BUILT | YES | `context_bundle_dry_run` carries populated `bundle_id`; no `context_bundle_error` (build_context_bundle #775 ran). |
| 6 | CONSUMER_786_RAN | YES | `consumer_version` present and `resolved_module_path`/`evidence_refs` populated (consume_context_bundle_dry_run #786 ran). |
| 7 | DRYRUNRESULT_ATTACHED_TO_RECEIPT | YES | `ConsumerResult.context_bundle_dry_run` present and survives `to_dict()`. |
| 8 | SOURCE_AUTHORITY_MONOREPO_POC | YES | `cb["source_authority"] == "monorepo_poc"` (builder constant SOURCE_AUTHORITY, builder.py:132). |
| 9 | MODULE_PATH_FROM_SHARED_RESOLVER | YES | `resolved_module_path == "modules/foundups/gotjunk"` (validated canonical, payload had no module_path); `rejected_input.resolver_run is True`. |
| 10 | EVIDENCE_REFS_HASHES_ONLY_NO_BODIES | YES | Each ref's keys subset of `{path, sha256, size_bytes, role}`; sha256 64 hex; no body key. |
| 11 | NO_LIVE_HERMES_DELEGATION | YES | `HERMES_DELEGATE_ENABLED` unset; `HermesJobExecutor._lazy_import_delegate_task` patched, `assert_not_called`. |
| 12 | NO_SUBPROCESS_OR_BUILD_EXECUTION | YES | `subprocess.Popen`/`run`/`call` patched, `assert_not_called` through the full path. |
| 13 | READINESS_REMAINS_FALSE | YES | every `readiness_flags` value False; receipt `verification_complete`/`cabr_ready`/`payout_ready` all False. |
| 14 | FORGED_MODULE_PATH_FAILS_END_TO_END | YES | `TestForgedModulePathFailsEndToEnd`: forged kosei path on gotjunk_001 job -> `fail_token == "cross_foundup_mismatch"`, `resolved_module_path is None`, observable in `payload_module_path_ignored`. |
| 15 | GOTJUNK_001_PARAMETERIZED_NOT_HARDCODED | YES | `proof_foundup` pytest fixture with `params=[(gotjunk_001, modules/foundups/gotjunk)]`; swap param to run any safe monorepo_poc FoundUp. |
| 16 | NO_NEW_PRODUCTION_CODE | YES | `git diff --name-only c7839c2ab HEAD` lists only the new test + this doc + wre_core ModLog + root ModLog. |
| 17 | NO_REAL_EXECUTION | YES | dry-run branch only; real-exec sinks asserted not-called; no `_write_evidence` outside tmp workspace. |
| 18 | NO_USER_QUESTION_FRAMING | YES | This is a WSP_97 evidence-backed proof; no "user questions". |
| 19 | CITES_PR_775_786_787 | YES | #775 build_context_bundle, #786 consume_context_bundle_dry_run, #787 _attach_context_bundle_dry_run wiring cited above. |
| 20 | ASCII_CLEAN | YES | New `.py` and `.md` files are 0 non-ASCII bytes. |
