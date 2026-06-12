# Operational-WRE Monorepo-PoC Closeout (Phase 1)

Slice: OPERATIONAL_WRE_MONOREPO_POC_CLOSEOUT_PHASE1
Type: DECISION-ONLY closeout. No code, no tests, no production change.
Operator / Commander: 012 (routing + merge authority, sovereign valve)
Executor: 0102 (W6), audited via 0102/W10.

Base: origin/main = 4f57af5499c1a4c7f5ecffbcb58a360c5ece906a (#788 vertical proof).

This document is a plain, evidence-backed statement of WHERE the
operational-WRE monorepo-PoC stands as of the base SHA above. It does NOT
move toward real execution. Every claim is grounded in MERGED code, the
already-merged #788 vertical-proof test, and PR evidence -- not memory or
aspiration. PROVEN and DEFERRED are kept strictly separate.

---

## Phase 0 -- Discovery and grounding

### HoloIndex retrieval (discovery only)

| # | Query | Signal | Assessment |
|---|-------|--------|------------|
| 1 | `operational WRE monorepo PoC vertical proof dry-run consumer context bundle` | MEDIUM | 20 hits (code=5, wsp=5, docs=5, knowledge=5). Surfaced the ContextBundle producer (`modules/foundups/agent/src/context_bundle_builder.py`), its test, the OpenClaw execution bundle, and the prior `WRE_AUTONOMOUS_BUILD_CONTEXT_BUNDLE_AUDIT_PHASE1.md`. It did NOT surface the #788 vertical-proof test, the #786 consumer, or the #777 contract in the top hits. |

HoloIndex classification: DISCOVERY ONLY, MEDIUM signal. Related modules
surfaced, but the exact merged closeout-chain artifacts (#777 contract,
#786 consumer, #787 seam, #788 proof) were NOT in the top hits. Per 012's
HoloIndex-precision rule, closeout truth below is grounded in merged code,
the merged proof test, and PR evidence -- not HoloIndex.

### Merged PR chain (all MERGED at or before the base SHA)

| PR | State | Title |
|----|-------|-------|
| #775 | MERGED | feat(wre): add read-only ContextBundle builder Phase 1 |
| #777 | MERGED | feat(foundups): FoundUp lifecycle/source-authority contract Phase 1 (define stages, pin monorepo_poc) |
| #778 | MERGED | fix(foundups): guard Hermes module_path resolution with manifest validator (W6) |
| #779 | MERGED | fix(foundups): guard build_plan_generator module_path with shared validated resolver (W6) |
| #786 | MERGED | feat(wre): dry-run consumer adopts ContextBundle as trusted input (W6) |
| #787 | MERGED | feat(wre): wire dry-run ContextBundle consumer into dispatch seam, dry-run only (W6) |
| #788 | MERGED | test(wre): operational-WRE monorepo-PoC vertical dry-run proof (W6) |

### Grounding files (read at base 4f57af549)

- `modules/foundups/agent/src/context_bundle_builder.py` (#775 producer; `SOURCE_AUTHORITY` builder constant)
- `docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md` (#777 contract)
- `modules/foundups/agent/src/module_path_resolution.py` (#778/#779 shared validated resolver)
- `modules/foundups/agent/src/context_bundle_dry_run_consumer.py` (#786 consumer)
- `modules/infrastructure/wre_core/src/foundup_job_consumer.py` (#787 dispatch-seam wiring)
- `modules/infrastructure/wre_core/src/hermes_job_executor.py` (real-exec boundary + D0-D6 guard)
- `modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py` (#788 proof)
- `docs/audits/architecture/OPERATIONAL_WRE_MONOREPO_POC_VERTICAL_PROOF_PHASE1.md` (#788 proof doc)

---

## 1. WHAT NOW WORKS (PROVEN)

The dry-run producer -> consumer -> dispatch-seam loop is proven
end-to-end by the #788 vertical proof, which drives the REAL OpenClaw
create entry and the REAL WRE drain entry (the seam itself is never
mocked; only the real-execution sinks are mocked and asserted
never-called).

- REAL OpenClaw create -> WRE drain. The proof calls
  `openclaw_foundup_orchestrator.dispatch_foundup(None, intent)` for a
  natural-language `"validate foundup <id> --dry-run"` message, which the
  real orchestrator parses into a queued `validate_foundup` job, then
  drains it via `FoundUpJobConsumer.drain_openclaw_queue_with_retention(clear=False)`
  (test file `test_operational_wre_monorepo_poc_vertical_proof.py`,
  `_create_via_real_openclaw_entry` / `_drain_via_real_wre_entry`).
- SIMULATED branch reached. `validate_foundup` is the only canonical
  action that reaches the pre-existing SIMULATED (dry-run) branch; the
  proof asserts `result.checkpoint_state == "SIMULATED"` and
  `result.real_execution_performed is False`
  (`TestOperationalWREMonorepoPoCVerticalProof.test_full_dry_run_invocation_end_to_end`).
- ContextBundle built (#775) and consumed (#786). The proof asserts the
  attached `context_bundle_dry_run` carries a populated `bundle_id` and
  `consumer_version`, with no `context_bundle_error` -- proving both the
  #775 `build_context_bundle` producer and the #786
  `consume_context_bundle_dry_run` consumer ran and produced a
  `DryRunResult`.
- DryRunResult in the ConsumerResult receipt. `result.to_dict()` carries
  `context_bundle_dry_run`, which survives serialization with
  `source_authority == "monorepo_poc"` and `dry_run is True`
  (`ConsumerResult.to_dict` at
  `modules/infrastructure/wre_core/src/foundup_job_consumer.py:208-226`,
  field set at `:188`).
- Single validated module_path resolver. The create entry put NO
  `module_path` in the payload; the shared resolver derived the canonical
  path from the validated manifest. The proof asserts
  `cb["resolved_module_path"] == expected_module_path`,
  `rejected_input.resolver_run is True`,
  `payload_module_path_ignored is None`, `resolver_failed is False`. The
  resolver is the single source of truth, importing
  `foundup_manifest_validator.validate_manifest_file` (#773) and carrying
  a `NO_SECOND_MODULE_PATH_RESOLVER` self-scan
  (`modules/foundups/agent/src/module_path_resolution.py:21, :44-52, :67-70`).
- source_authority pinned monorepo_poc. `SOURCE_AUTHORITY = "monorepo_poc"`
  is a builder constant at
  `modules/foundups/agent/src/context_bundle_builder.py:132`, never read
  from any manifest. The consumer value-pins `REQUIRED_SOURCE_AUTHORITY =
  SourceAuthority.MONOREPO_POC.value` and rejects any other authority
  (`modules/foundups/agent/src/context_bundle_dry_run_consumer.py:129`).
- Negative path proven. A forged cross-FoundUp `module_path` injected onto
  the queued job is REJECTED end-to-end through the real seam:
  `context_bundle_error == "module_path_resolution_failed"`,
  `fail_token == "cross_foundup_mismatch"`,
  `payload_module_path_ignored == <forged path>`,
  `resolved_module_path is None`
  (`TestForgedModulePathFailsEndToEnd.test_forged_cross_foundup_module_path_rejected_via_seam`).

Scope of "works": the DRY-RUN evidence loop works. No real execution is
performed anywhere in this path (see Section 2).

---

## 2. WHAT IS STILL DRY-RUN / SIMULATED (real execution is BLOCKED)

Real execution is BLOCKED. The dispatch seam stays on its pre-existing
dry-run branch.

- Feature flag default 0. `is_hermes_delegation_enabled()` reads
  `HERMES_DELEGATE_ENABLED`, default `"0"`
  (`modules/infrastructure/wre_core/src/hermes_job_executor.py:89-95`).
  With the flag unset/0, the executor returns `SIMULATED`
  (`:1766-1791`, "Feature disabled, simulating job").
- Even with the flag enabled, real delegation is not implemented. With the
  flag set and `dry_run=False`, the executor returns
  `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` -- "Real Hermes delegation not
  implemented in Phase 1. ... Enable terminal/file toolsets in Phase 2"
  (`hermes_job_executor.py:300, :1845-1856`). No live Hermes delegation
  exists.
- Only validate_foundup reaches SIMULATED. `build_foundup` and
  `extract_foundup` are blocked earlier by the destructive-action guard,
  returning `BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD`
  (`hermes_job_executor.py:305`; proven in the #788
  `TestActionReachesSimulated.test_validate_reaches_simulated_build_extract_blocked`).
- D0-D6 destructive-action guard. Actions are classified D0-D6; D4
  (write-repo), D5 (external side effect), and D6 (irreversible /
  ambiguous fail-closed) are blocked in Phase 1
  (`hermes_job_executor.py:1016-1168`; module header `:11, :19-21`).
- No subprocess, no real mutation. The #788 proof patches
  `subprocess.Popen`, `subprocess.run`, `subprocess.call`, and the
  executor's real-delegate loader `_lazy_import_delegate_task`, and
  asserts all four `assert_not_called` THROUGH the full create+drain seam.
  Evidence writes are redirected to a tmp workspace via
  `FOUNDUPS_WORKSPACE_ROOT`, leaving no repo artifact.

There is no live Hermes delegation, no subprocess build, and no real
mutation anywhere in this PoC path.

---

## 3. WHAT IS NOT MVP (this is monorepo_poc ONLY)

This is `monorepo_poc` (PoC / Proto-in-monorepo) ONLY. It is NOT OPO, NOT
MVP, NOT `external_proto`, NOT `dao_managed`.

- monorepo_poc is the only reachable stage. The #777 contract defines five
  source-authority stages and marks `monorepo_poc` as the only one
  reachable in Phase-1; `external_proto`, `mvp_runtime`, `dao_managed`,
  `archived` are DEFINED but NOT reachable
  (`docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md:185-198`).
- Cannot self-promote. The Hard Rule (load-bearing): "A context bundle /
  manifest must be lifecycle-aware but CANNOT promote its lifecycle stage
  by declaration." `SourceAuthority.resolve_source_authority(declared)`
  ALWAYS returns `MONOREPO_POC` and surfaces (never trusts) any declared
  value; `request_promotion(target)` ALWAYS raises `NotImplementedError`
  (Hard Rule blockquote `:359-364`; enforcement `:366-389`;
  "Phase-1 IMPLEMENTS NONE OF THESE" `:354-355`).
- No external state. monorepo_poc source is monorepo-resident; the
  validated manifest is the source of truth. No external repo, no
  federation envelope (contract per-stage matrix
  `:202-214` for monorepo_poc).
- No CABR / payout / DAO. For monorepo_poc the contract states CABR is
  "NOT READY", and "CABR / payout / DAO surfaces are forbidden in the
  bundle" (contract `:210, :214`). The #788 proof asserts the receipt's
  WSP-97 truth fields `verification_complete`, `cabr_ready`,
  `payout_ready` all remain `False`, and scans the dry-run evidence blob
  for forbidden pass-state keys.
- No readiness / stage promotion. The proof asserts every `readiness_flag`
  remains `False` and `gates_to_recheck` are gate NAMES (strings), never
  pass-state booleans; `planned_actions` are declared-only
  (`action["executed"] is False`).

---

## 4. WHAT IS NEEDED FOR external_proto (DEFERRED -- enumerated, NOT a plan to start now)

The following is the honest gap. It is DEFERRED. This closeout does NOT
recommend or take any step toward enabling it.

### 4a. external_proto transition gates (per the #777 contract)

Per `FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md` Section 4.1
(`monorepo_poc -> external_proto`, `:303-318`) and the per-stage
`external_proto` matrix (`:216-228`), the required evidence is
(transition-gate lines `:306-318`):

- External source location: external repo owned by the spin-out team;
  source no longer in the monorepo (`:220, :309-310`).
- Evidence store: federation-bound provenance envelope (TBD); pAVS holds a
  signed sha256 pointer, not the source (`:222, :311-312`).
- Ownership / governance: spin-out team owns the source; 012 retains
  routing authority over the pAVS federation registry, not the source repo
  (`:223, :308`).
- Test contract / governance: defined by the external repo; a separate
  federation-bound validator is required (out of scope) (`:221`).
- Mutation permissions: external repo's own rules; pAVS validates only the
  federation contract, not the source (`:225`).
- Executor permissions: Hermes federation client only; no monorepo
  executor reach into external_proto (`:226`).
- Sovereign valve: spin-out team governance plus 012's pAVS-registry
  sovereign valve (`:227`).
- CABR readiness: NOT READY -- "No CABR readiness required; this is a
  pre-OPO transition" (`:312`; matrix `:224`).
- Payout / DAO gates: NONE (still pre-OPO) (`:228`).
- Required WSP gate: WSP 103 federation contract (TBD) + WSP 109
  intake-archive (`entity_type` -> `external_foundup`) (`:314-318`).

The contract states "Phase-1 IMPLEMENTS NONE OF THESE" (`:354-355`).

### 4b. Separately, what enabling REAL execution would require (DEFERRED)

Independent of the source-authority transition, enabling real (non-dry-run)
execution would require:

- The D0-D6 destructive-action guard to permit the action class instead of
  blocking D4/D5/D6 (`hermes_job_executor.py:1016-1168`).
- A sovereign / human valve for any non-dry-run action -- the monorepo_poc
  matrix requires `policy_required_sovereign_valve_for_non_dry_run`
  (contract `:213`).
- CABR readiness, currently "NOT READY" and forbidden in the bundle
  (contract `:210, :214`).
- An actual real-delegation implementation: Phase-1 returns
  `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` ("Enable terminal/file
  toolsets in Phase 2") (`hermes_job_executor.py:1845-1856`).

All of the above are DEFERRED. This closeout enumerates the gap honestly
and takes NO step toward enabling it.

---

## Reproducible PoC Proof

This section is a POINTER to the already-merged #788 proof. It introduces
no new test and runs no new code; the existing test was run once for
verification.

- Proof test file:
  `modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py`
  (merged in #788).
- Proof doc:
  `docs/audits/architecture/OPERATIONAL_WRE_MONOREPO_POC_VERTICAL_PROOF_PHASE1.md`
  (merged in #788).
- Exact command:
  `python -m pytest modules/infrastructure/wre_core/tests/test_operational_wre_monorepo_poc_vertical_proof.py -q`
- Expected / observed pass condition: `3 passed` (observed
  `3 passed in 0.73s`, exit 0) -- 0 failed, 0 skipped, 0 xfailed.

### Evidence-chain fields PROVEN present (and where asserted)

All citations are to the #788 test file
`test_operational_wre_monorepo_poc_vertical_proof.py`,
`TestOperationalWREMonorepoPoCVerticalProof.test_full_dry_run_invocation_end_to_end`
unless noted:

- Validated manifest reference: the resolver derives the canonical path
  from the validated manifest;
  `cb["rejected_input"]["resolver_run"] is True`,
  `resolver_failed is False`, and `payload_module_path_ignored is None`
  (the create entry injected no module_path).
- ContextBundle metadata: `cb["bundle_id"]` is a non-empty str,
  `cb["consumer_version"]` is a non-empty str, `cb["dry_run"] is True`,
  `cb["real_execution_performed"] is False`, and no
  `context_bundle_error`.
- source_authority = monorepo_poc: `cb["source_authority"] ==
  "monorepo_poc"` and, after serialization,
  `receipt["context_bundle_dry_run"]["source_authority"] == "monorepo_poc"`.
- resolved_module_path from the shared resolver:
  `cb["resolved_module_path"] == expected_module_path` (the validated
  canonical path, not the payload).
- DryRunResult: populated `bundle_id` + `consumer_version` with no
  `context_bundle_error` proves the #786 `consume_context_bundle_dry_run`
  ran and produced a `DryRunResult`.
- ConsumerResult / receipt: `result` is a `ConsumerResult` with
  `dispatched is True`; `result.to_dict()` carries a non-None
  `context_bundle_dry_run`.
- Receipt-integrity / pAVS truth fields: `receipt["verification_complete"]`,
  `receipt["cabr_ready"]`, `receipt["payout_ready"]` all `False`; every
  `readiness_flag` `False`; `gates_to_recheck` are NAMES (strings), never
  booleans; no forbidden pass-state key in the dry-run evidence blob.
- No file bodies: the whole serialized receipt is scanned; none of
  `"body"`, `"content"`, `"source_text"`, `"file_body"` appear; evidence
  refs carry only `{path, sha256, size_bytes, role}` with a 64-char
  sha256.
- No live execution: `subprocess.Popen` / `run` / `call` and the
  executor's `_lazy_import_delegate_task` are all `assert_not_called`
  through the full seam; `checkpoint_state == "SIMULATED"`,
  `real_execution_performed is False`.

---

## WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | Phase 0 HoloIndex query run (1 query, 20 hits); recorded in the HoloIndex retrieval table. |
| 2 | HOLOINDEX_RETRIEVAL_ASSESSED | YES | Classification recorded: DISCOVERY ONLY, MEDIUM signal; exact closeout-chain artifacts not in top hits; truth grounded in merged code/PR instead. |
| 3 | STATE_GROUNDED_IN_MERGED_CODE_NOT_MEMORY | YES | Every claim cites a file:line at base 4f57af549 or a merged PR; read via `git show 4f57af549:<path>`; #788 test run once. |
| 4 | WHAT_WORKS_PROVEN_WITH_PR_EVIDENCE | YES | Section 1 cites #775/#786/#787/#788 file:line and the #788 proof assertions. |
| 5 | STILL_DRYRUN_REAL_EXEC_BLOCKED | YES | Section 2: `hermes_job_executor.py:89-95, :300, :1766-1791, :1845-1856`; #788 sinks `assert_not_called`. |
| 6 | NOT_MVP_MONOREPO_POC_ONLY | YES | Section 3: contract `:185-198, :202-214, :359-389`; not OPO/MVP/external_proto/dao_managed; cannot self-promote. |
| 7 | EXTERNAL_PROTO_GAP_ENUMERATED_DEFERRED | YES | Section 4: contract `:216-228, :303-318, :354-355`; plus real-exec gap (4b); enumerated as DEFERRED, no plan to start. |
| 8 | NO_MOVE_TOWARD_REAL_EXECUTION | YES | Decision-only doc; no recommendation or step to enable real execution / live delegation. |
| 9 | NO_CODE_CHANGE | YES | Deliverable is this doc + root ModLog entry; `git diff --name-only 4f57af549 HEAD` lists no .py / test files. |
| 10 | NO_OVERCLAIM_PROVEN_VS_DEFERRED_SEPARATED | YES | Sections 1 (PROVEN) and 4 (DEFERRED) are separate; dry-run/simulated never stated as "working" real execution. |
| 11 | REPRODUCIBLE_POC_PROOF_POINTER_INCLUDED | YES | Reproducible PoC Proof section names the #788 test file, exact command, pass condition (`3 passed`), and evidence-chain fields. |
| 12 | NO_USER_QUESTION_FRAMING | YES | No "user questions"; evidence -> recommendation -> proceed. |
| 13 | CITES_PR_775_777_778_779_786_787_788 | YES | All seven PRs cited in the merged-PR-chain table and throughout Sections 1-4. |
| 14 | ASCII_CLEAN | YES | Document is 0 non-ASCII bytes (byte-checked before commit). |
