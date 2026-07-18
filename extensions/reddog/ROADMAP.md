# RedDog Roadmap

## Status

Phase: RedDog 0.4.4 resident architect thin-client surface.

Current implementation:

- Semantic HoloIndex grounding is generation-bound to the authenticated owner service. Stale, lexical, unreceipted, or repository-mismatched owner results are withheld and surfaced as an index gap; RedDog never re-indexes during a reasoning run.

- Cursor command: `RedDog: Open`.
- Bottom-composer webview with scrollback output.
- OpenRouter bridge with redaction gate.
- WSP_00/WSP_97/WSP_15 operating prompt.
- HoloIndex semantic-first bundle-json recall with truthful mode/backend receipts and an operational offline lexical fallback.
- Manual lead+panel mode for review-packet traceability.
- REDDOG_FUSION_ORCHESTRATOR_PHASE1: internal task classifier, auto effort, schema validator, one repair pass.
- REDDOG_UX_PACKET_POLISH_PHASE1 (v0.3.19): Working Tail above controls; 0102 Role label; Copy MD Run Trace; mojibake flag; validation-failure packet semantics.
- REDDOG_BLOCKED_COPY_POLISH_PHASE1 (v0.3.21, #878): Work Trail dedupe; conservative blocked-local Governed Handoff.
- REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1 (docs): fixed 15-prompt pack, rubric, runbook, artifact template for 012 replacement scoreboard.
- REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (v0.3.44): repo paths named with read-intent in free-form prose / WSP_99 M2M / "Read first" sections (not only under the exact `Required direct-read targets:` header) are promoted to required direct-read targets so the governed fetch fires even on HoloIndex semantic miss; command/validation fences and scope-out sections excluded.
- REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (v0.3.45): flowing-prose `Read first:` lines are tokenized with the bounded path-token regex (not the comma-splitter), so a path followed by prose and an embedded-slash English fragment (`breadcrumb/handoff`) no longer corrupt derived targets; tiered strictness (flowing prose requires a file extension, explicit/M2M/bullet tiers keep slash-OR-extension); slash-only prose fragments reported in `work_focus_targets_dropped_low_confidence` and never flip `target_recall_ok`; `}` added to trailing-punctuation trim.
- REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1 (v0.3.46): Copy MD/review packet emits typed WRE operational spine dry-run preview; no Python spine invocation, worktree create, task execution, OpenClaw enqueue, Hermes dispatch, PR, push, merge, or repo mutation.
- REDDOG_JUDGMENT_GENERATION_WIRING_PHASE1 (v0.3.47): Determine prompts now request canonical `## Determine Answers` JSON and run a local deterministic verifier against already-fetched direct-read evidence; Run Trace/Copy MD expose verifier verdicts and advisory INDEX_GAP metadata. No re-index, WRE enqueue, shell, repo mutation, or network authority is added.
- HOLOINDEX_READONLY_QUERY_GUARD_PHASE1 (v0.3.48): RedDog launches HoloIndex with `HOLOINDEX_QUERY_READONLY=1`; HoloIndex search/query mode is read-only by default, search-time auto-refresh requires explicit `--allow-auto-refresh`, and collection reset refuses read-only query contexts.
- REDDOG_EXTENSION_GOVERNED_WORK_ORDER_RUNTIME_EMISSION_PHASE1 (v0.3.49): WRE preview embeds a full `RedDogGovernedWorkOrder` candidate with digest, derived path scope, HoloIndex evidence posture, nonce, expiry, and fail-closed authority readiness flags. It still does not invoke Python, create a worktree, run tasks, enqueue, push, merge, or settle rewards.
- REDDOG_EXTENSION_WORK_ORDER_PERMISSION_AND_SIGNATURE_BINDING_PHASE1 (v0.3.50): WRE preview candidate now binds supplied permission-snapshot and signed-authority verifier metadata. It can mark a candidate ready only when the permission snapshot is fresh/trusted, the signed-authority result is accepted for the same work order, path scope exists, and the explicit worktree valve is requested. No GitHub probe, crypto verification, WRE invocation, worktree, enqueue, PR, merge, or reward settlement is performed by the extension.
- REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_RUNTIME_WIRE_PHASE1 (v0.3.51): extension runtime now emits a guarded WRE invoke result and has a stdin-only Python bridge to the landed explicit-valve guard. Default runs skip invocation; Python is called only when a ready candidate plus explicit invoke metadata, sovereign wardrobe-selection receipt, valve environment, permission snapshot, and accepted signed-authority result are supplied. No task execution, file edits, OpenClaw enqueue, Hermes dispatch, PR, merge, or reward settlement is added.
- REDDOG_EXTENSION_OPERATOR_WARDROBE_SELECTION_RUNTIME_BRIDGE_PHASE1 (v0.3.52): extension runtime now calls the deterministic operator-loop wardrobe-selection dry-run and emits its receipt into Copy MD/review packets. This supplies the runtime wire with a local selection receipt while preserving no-execution/no-enqueue and fail-closed authority boundaries.
- REDDOG_EXTENSION_GITHUB_PERMISSION_PROBE_RUNTIME_BRIDGE_PHASE1 (v0.3.53): extension runtime now calls the existing read-only GitHub permission probe and emits a fresh `repo_permission_snapshot` into Copy MD/review packets. This removes the missing-permission-snapshot blocker when `gh` reports trusted repository permission, while preserving no signing, no worktree, no enqueue, no PR/merge, no reward, and no HoloIndex mutation.

## Architecture Direction

This extension is the RedDog thin client. The resident backend and OpenClaw/WRE/Hermes workers remain the authority-bearing runtime.

RedDog is the resident FoundUps architect thin client and product surface. Fusion is one internal reasoning mode; authority-bearing work remains in the resident backend and signed OpenClaw/WRE/Hermes worker path.

### RedDog and the Recursive 0102 DAE Ecosystem

012 does not orchestrate every worker. 012 talks to RedDog. RedDog participates in the recursive 0102 DAE ecosystem. Autonomous WRE/DAE agents perform bounded system work under Hermes/OpenClaw/WRE governance.

```text
012 work focus
  -> RedDog digital twin / architect interface
  -> recursive 0102 DAE ecosystem
  -> Hermes scaffolding / lifecycle / scheduling
  -> OpenClaw policy + intent gate
  -> HoloIndex memory / retrieval
  -> Skillz / Rolodex capability catalog
  -> autonomous WRE/DAE agents
  -> Sentinels / AI overseer review
  -> WRE verification + repo/process authority
  -> CABR / pAVS benefit validation
  -> receipts / memory / recursive improvement
```

Autonomous WRE/DAE agents are NOT 012 work. 012 provides work focus, testing, sovereign approval, and override. 0102 DAEs communicate recursively and perform bounded autonomous work.

Target path:

```text
IDE extension POC
  -> RedDog Architect contract hardening
  -> WSP_109 FoundUps intake packet generation
  -> WRE/OpenClaw/Hermes dispatch surface
  -> pfMALL RedDog surface
  -> governed public FoundUps launch flow
```

## WSP_15 Priorities

| Work Item | Complexity | Importance | Deferability | Impact | MPS | Priority | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Layout + RedDog Architect contract | 2 | 5 | 5 | 4 | 16 | P0 | Required for usable 012 feedback loop |
| Tier-0/Tier-1 memory files | 1 | 4 | 4 | 4 | 13 | P1 | Required for HoloIndex discovery |
| WSP_109 intake packet mode | 3 | 5 | 4 | 5 | 17 | P0 | Converts external project ideas into FoundUps intake artifacts |
| Review packet persistence | 3 | 4 | 3 | 4 | 14 | P1 | Enables outcome learning and model performance memory |
| pfMALL RedDog binding | 4 | 5 | 3 | 5 | 17 | P0 | Public/operator surface after safety contracts harden |
| WRE/OpenClaw dispatch bridge | 4 | 5 | 3 | 5 | 17 | P0 | Must remain governed; extension cannot dispatch directly |

## External RedDog Lane Queue (post-#888)

Goal: **RedDog replaces Claude Code-style work** - not only extension polish. Advisory RedDog must bridge to governed WRE execution before random implementation.

```text
DONE
1. #886 Unicode / UTF-8 bridge (ca5703611, v0.3.25)
2. #888 schema repair hardening (9c3a8f829, v0.3.27)
3. #889 governed repo work-order contract (764084bc4)
4. #890 governed work-order dry-run validator (bd68ab83a)
5. #891 post-#890 queue docs (3cbc58913)
6. #892 GitHub permission probe (21aeff32d)
7. #893 OpenClaw policy gate (329db7113)
8. #894 Hermes-compatible receipt (b42db2165)
9. #896 runtime invocation dry-run (f65ecff4e)
10. #897 WRE isolated worktree executor contract (2fe60a280)
11. #898 WRE executor plan dry-run (e215bf890)
12. #899 RedDog continuation memory (c70433d7d)
13. #901 OpenClaw FoundUpsJob adapter contract (2c8df23dd)
14. #903 WRE execution valve (2761f2e65)

P0 NEXT (execution track)
15. REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1
    - refreshed contract boundary for future live OpenClaw enqueue; no runtime enqueue
15. REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1
    - propose FoundUpsJob / autonomous_task intake; no live enqueue

P1
16. REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1
    - first real isolated worktree; valve OPEN only
17. REDDOG_WRE_OPERATIONAL_SPINE_WORKTREE_CREATE_PHASE1
    - compose invocation dry-run -> executor plan -> valve -> worktree create; no task execution
18. REDDOG_SANITIZED_TARGET_CONTEXT_PROVENANCE_PHASE1
19. REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1
20. HOLOINDEX_REDDOG_GOVERNED_WORK_ORDER_INDEX_GAP_PHASE1
21. HOLOINDEX_REDDOG_WRE_EXECUTOR_CONTRACT_INDEX_GAP_PHASE1
22. HOLOINDEX_REDDOG_WRE_EXECUTOR_DRYRUN_INDEX_GAP_PHASE1
23. HOLOINDEX_REDDOG_OPENCLAW_ADAPTER_CONTRACT_INDEX_GAP_PHASE1

P2/P3
24. REDDOG_REVIEW_CONSENSUS_RECEIPTS_PHASE1
25. REDDOG_AUTONOMOUS_MERGE_POLICY_PHASE1 (blocked)
```

**Rationale:** Sanitized provenance and telemetry are real polish issues, but the strategic blocker is that RedDog still cannot safely become a worker. The work-order contract is the missing bridge between "advisory RedDog" and "RedDog can direct WRE to do meaningful code work."

## Next Slices

### RedDog extension.js WSP_62 decomposition

- **Owner:** RedDog Maintainers.
- **Temporary exemption expiry:** 2026-09-30 (2026-Q3 technical-architect review).
- **Current boundary:** `extension.js` is a legacy 7,880-line thin-client integration file. The temporary exact-file threshold is 7,900 lines; this is not permission for further feature growth. New generation-bound HoloIndex logic lives in a focused module rather than expanding this file.
- **Remediation:** extract model configuration plus stdin bridge invocation first, then UI rendering, retrieval/context assembly, and governed work-order receipt composition into separately tested JavaScript modules of at most 400 lines.
- **Parity gate:** retain the focused Fusion panel ingress/payload contract and exhaustive extension contract across each extraction; preserve no-network, stdin-only model payloads and review-packet truth.
- **Exit criterion:** remove `extensions/reddog/wsp_62_exemptions.yaml` once `extension.js` and its touched functions comply with WSP_62 limits. If the expiry arrives first, block additional extension feature work and renew only through a new architect-reviewed remediation slice.

### RedDog advisory Python bridge WSP_62 decomposition

- **Owner:** RedDog Maintainers.
- **Temporary exemption expiry:** 2026-09-30 (2026-Q3 technical-architect review).
- **Current boundary:** `scripts/advisory_model_once.py` remains below the 1,200-line Python threshold. The public `_run_foundups_fusion` panel guard is compliant; its inherited `_run_foundups_fusion_core` body (201 lines) and `main` (179 lines) exceed the function limit. Their exact-function ceiling is 201 lines and is not permission for growth.
- **Remediation:** extract manual Fusion provider fan-out, quorum/synthesis assembly, request normalization, and CLI routing into focused helpers while preserving a single stdin/stdout bridge contract.
- **Parity gate:** retain both focused panel-mode matrices, hostile metadata proofs, provider-call fail-closed assertions, and the exhaustive RedDog extension contract across each extraction.
- **Exit criterion:** remove the `scripts/advisory_model_once.py` entry from root `wsp_62_exemptions.yaml` once both named functions are at most 50 lines. If the expiry arrives first, block additional bridge feature work and renew only through a new architect-reviewed remediation slice.

### REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1

- **Baseline pass (v0.3.21):** 15 fixed prompts, 012 rubric, redacted artifact template (`docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`).
- Measures "Can 012 use Foundups(R)Agent instead of Claude Code for advisory work?" - does **not** require fixes in the same slice.
- **Replacement pass (future):** rerun same pack after HoloIndex index-gap and dispatch improvements; compare against baseline artifacts in `docs/acceptance/`.

### REDDOG_EXTERNAL_ACCEPTANCE_REPLACEMENT_PHASE1

- Re-run baseline prompt pack after HOLOINDEX + dispatch slices land.
- Pass criteria: improved rubric scores and 012 verdicts vs baseline artifacts.

### FOUNDUPS_AGENT_INTAKE_MODE_PHASE1

- Assess arbitrary external repositories for FoundUps integration readiness.
- Produce advisory WSP readiness audit, FoundUps intake packet, Skillz map, and integration risk report.
- No automatic onboarding, repo mutation, package install, or execution.
- Governed WRE handoff recommendation only.

### REDDOG_BRIDGE_HARDENING_PHASE1

Addendum B required controls (after v0.3.15 lands):

- Python resolver: configured path -> .venv/venv -> system fallback; report selected interpreter in non-secret metadata
- Subprocess output caps: hard stdout/stderr caps; kill on exceed; bounded failure reason
- Orphan cleanup: webview dispose kills in-flight bridge child
- Python panel cap: advisory_model_once.py max 6 panel_models
- Retry invariant: only HTTP 429/502/503, max 2 retries, same redacted body, no re-redaction, no retry on redaction block or 400-class (except 429)
- Retry tests: 429-then-success and 400-no-retry
- Context budget: bounded char budget before bridge; truncation_applied + truncation_reason in packet
- Failure taxonomy: redaction_blocked, valve_closed, missing_key, timeout, retry_exhausted, http_error, malformed_response, subprocess_failed, output_cap_exceeded

Add slice spec section before WSP_15 table or after - actually add to ROADMAP with full acceptance criteria

### REDDOG_REDACTION_GATE_CONTEXT_ERROR_DIAGNOSTIC_PHASE1

- **Trigger:** Post-#882 EXT-ACC-001/003 probe returns `redactor_error` on `wsp_holo_skillz` bounded context (~25k chars).
- **Purpose:** Identify what in post-#882 bounded context triggers `redactor_error`; preserve fail-closed behavior.
- **In scope:** Low-cardinality reason telemetry; safe category reporting (`blocked_policy`, `residual_forbidden`, `non_text_context`, etc.); redaction tests.
- **Out of scope:** Policy weakening; raw blocked snippets in Copy MD; OpenRouter routing changes.
- **Acceptance:**
  - Same EXT-ACC-001 prompt no longer returns `redactor_error`
  - If blocked, reports specific safe category (not generic `redactor_error`)
  - No raw blocked content included
  - Redaction gate tests pass
- **Blocks:** `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1` until diagnostic lands and probe reruns successfully.

### HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1

- Index `extensions/reddog/extension.js`, `scripts/advisory_model_once.py`, and Skillz/Rolodex discovery paths.
- Improve semantic recall for RedDog auto-router, WSP_15/97, and governed-handoff queries.
- Add regression retrieval tests so extension bridge code ranks above adjacent WRE routers.
- **Status:** **LANDED** #882 (`99d0e35c2`) - ranking + target recall telemetry only; not source-content inclusion.

### REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (v0.3.45)

- **Status:** VERIFIED_READY (draft PR only; do NOT self-merge -- merge is harness/012-gated, VSIX build is a 012 host step). P0 hotfix on the live derivation path.
- **Problem (OBSERVED):** a real 0.3.44 run on a FLOWING-PROSE `Read first:` prompt (three files named in one sentence, `.../breadcrumb_tracer.py. Determine ...` then `and the breadcrumb/handoff layer`) reported `target_recall_ok: false`. The read-capture branch tokenized the prose line with the COMMA-splitter, gluing trailing prose onto the path (`breadcrumb_tracer.py. Determine current lane-state sources` -> `not_a_file`, breadcrumb_tracer.py MISSED) and capturing the embedded-slash English fragment whole (`and the breadcrumb/handoff layer` -> garbage). Result `required_targets_total=4 / recalled=2`.
- **Fix (extension.js only; no Python change):** (A) NON-bullet read-capture prose is tokenized with the bounded path-token regex (`extractInlinePathTokens` via new `extractProsePathTokens`), not the comma-splitter; CLEAN BULLETS keep the comma/`or`-splitter to preserve the `a / b / c` alternatives shape. (B) Tiered strictness: flowing-prose tokens (read-first prose + inline + backtick) are required ONLY with a lowercase file extension (file shape); slash-only-no-extension prose fragments (`breadcrumb/handoff`) are dropped, reported in `work_focus_targets_dropped_low_confidence`, and EXCLUDED from `required_targets_total` / `_missing` (cannot flip `target_recall_ok`). Explicit header / M2M / clean bullets keep the broader slash-OR-extension tier. (C) `normalizeTargetPath` adds `}` to the trailing-punctuation trim set.
- **Guards / reuse:** `extractProsePathTokens` REUSES the existing bounded ReDoS-safe `extractInlinePathTokens` (no new backtracking regex); `stripListMarker` untouched. Governed direct-read gate (`bundle_json.py`) unchanged; derived paths still flow through it. No ranking/index/reindex change; no live-writer / orchestration-brain / budget-prioritization change.
- **Telemetry:** `work_focus_targets_dropped_low_confidence` (OBSERVED). Tests WFTD-015..WFTD-020 (the exact failed 0.3.44 prose prompt as fixture) plus WFTD-001..014 regression.
- **Follow-up:** none new (budget-prioritization deferred to Phase 2, out of scope here).

### REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (v0.3.44)

- **Status:** VERIFIED_READY (draft PR only; do NOT self-merge -- merge is harness/012-gated, VSIX build is a 012 host step).
- **Problem (OBSERVED):** a real multi-lane-orchestration audit named three repo files in prose bullets, not under the exact `Required direct-read targets:` header -> `required_targets_total: 0`, `direct_read_fetch_attempted: false`; the whole direct-read stack stayed dormant. RedDog was retrieval-blind to free-form targets.
- **Fix (extension.js only; no Python change):** `deriveWorkFocusTargets(taskText)` derives required direct-read targets from read-intent shapes (`Read first:` / `READ BEFORE EDITING`, WSP_99 M2M `READ:` arrays, M2M `CTX.FILES` / `CTX: FILES:` arrays, markdown bullet path lists, inline + backticked prose paths). `collectRequiredTargets(taskText)` merges the explicit-header list (FIRST, byte-identical for the header-only shape) with derived targets, deduped case-insensitively; `evaluateTargetRecall` + `buildBoundedRepoContext` consume the merged list so a named path makes `required_targets_total > 0` and fires the SAME governed direct-read fetch regardless of HoloIndex recall.
- **Guards:** (A) bounded/anchored ReDoS-safe path-TOKEN regex (slash-less token requires a LOWERCASE extension, so M2M keys / acronyms and surrounding prose words are not captured); (B) command/validation fences (```powershell / ```bash with `git diff --check`, `node --check`, `python holo_index.py ...`) and scope-out / `Do NOT touch` / `OUT OF SCOPE` sections excluded; ambiguous read-intent prefers precision.
- **Governance:** denied paths (`.env`, traversal, secret-like) emitted honestly and rejected by the UNCHANGED Python direct-read gate; denylist / byte budgets / redaction / packing untouched. No ranking/index/reindex change; no live-writer / orchestration-brain change.
- **Telemetry:** `work_focus_targets_derived`, `work_focus_target_derivation_sources` (both OBSERVED). Tests WFTD-001..WFTD-013 including a real end-to-end regression on the multi-lane prompt.
- **Follow-up if not indexed:** `HOLOINDEX_REDDOG_WORK_FOCUS_TARGET_DERIVATION_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED).

### REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (v0.3.39 -> v0.3.40 dedup -> v0.3.41 all-section + legacy-path closure)

- **Status (v0.3.41):** VERIFIED_READY. Closes the LAST two forgery vectors so `forgery_inert=true`
  holds on ALL paths/sections, not only the authoritative (packProtected=true) path.
  - **VECTOR A (incomplete lower-section neutralization):** four raw file-body lower sections still
    pushed UN-neutralized content that could carry a literal `### Required direct-read target: <path>`
    marker minted from file CONTENT -- target-recall (`buildTargetRecallContentSection`), WSP_97 excerpt
    (`buildWsp97ProtocolExcerpt`), Skillz/Wardrobe/Rolodex (`skillzWardrobeRolodexContext` ->
    `readBoundedRepoFile`), and the plain direct-read section (`buildDirectReadContentSection`, reachable
    only when packProtected=false). Fix: EVERY `lowerSections.push(...)` now routes through
    `neutralizeRequiredTargetMarker`; no file-body section can emit the marker prefix into the splitter.
  - **VECTOR B (legacy None path):** `audit_context=true` + `packProtected=false` (direct-read code_hits
    present -> audit_context true, `direct_read_fallback_used` false -> `authoritativePacked=[]`) collapsed
    `[]` -> `None` in `scripts/advisory_model_once.py`, hitting the legacy `_isolate_required_targets(None)`
    no-filter path where every marker (incl. content-minted phantoms) is checked/counted. Fix: under
    `audit_context_requested` forward an EXPLICIT EMPTY tuple `()` -> the gate builds an EMPTY
    `authoritative_set` so every marker folds back as ordinary content (checked==0, no forged
    `blocked_paths`), while a real token in a folded body STILL fails the whole payload closed. Non-audit
    legacy behavior stays byte-identical (absent/empty -> None); the direct None legacy contract unchanged.
- **Completeness / forward-safety (v0.3.41):** MFH-J-008 ENUMERATES every `lowerSections.push` site and
  asserts 100% route through `neutralizeRequiredTargetMarker` -- a FUTURE new raw-body section pushed
  un-neutralized fails the runner rather than silently reopening the forgery. MFH-J-007b pins the four new
  file-body call sites. Python: `test_mfh_vectorb_*` (empty-set folds every marker, zero counts, still fails
  closed on a token, differs from legacy None) + `test_vectorb_*` (bridge forwards `()` under audit_mode,
  `None` on the non-audit path). No weakening: identification/counting-only; no ACTION_BLOCK detector
  relaxed; `AUDIT_STRUCTURAL_CATEGORIES` untouched; #917 content-safety + #914 budget preserved.

### REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (v0.3.39 -> v0.3.40 dedup completion)

- **Status:** VERIFIED_READY (this slice). Required-target telemetry is now AUTHORITATIVE and
  unforgeable by file content. JS `computeRequiredTargetContextProof` iterates the packer's
  structured record (`protectedInfo.included_paths`) plus `requiredTargetSectionSurvived`, NOT marker
  substrings scanned from merged text. JS `neutralizeRequiredTargetMarker` breaks literal marker bytes
  inside excerpt bodies at pack time (defense-in-depth). The extension threads
  `required_targets_authoritative_paths` through the bridge payload as `required_target_paths`; Python
  `_isolate_required_targets(context, authoritative_paths)` treats marker-delimited sections as
  required-target sections only when their path is in the authoritative list -- phantom markers minted
  by file content fold back as ordinary content and cannot inflate checked/passed/blocked/missing or
  forge `blocked_paths`.
- Root cause it fixes: marker-reparse forgery -- realistic self-referential audit bodies containing
  `### Required direct-read target: <path>` could flip never-fetched targets to in_model_context (JS)
  or mint phantom sections that inflated per-target redaction counts (Python).
- **v0.3.40 dedup completion (closes the residual duplicate-authoritative bypass):** the 0.3.39 JS
  neutralization protected only the packed EXCERPT bodies; the LOWER sections (git diff, HoloIndex
  recall JSON, active editor) merged UN-neutralized into the same `gate_context` Python splits, so a
  MODIFIED required file whose OWN body contains its authoritative marker line rendered a SECOND marker
  section that normalized to an ALREADY-authoritative path -- checked/passed exceeded the authoritative
  count and a hard-block token in that diff body forged a `blocked_paths` entry for the clean protected
  section. Closure: (1) PRIMARY robust fix -- Python per-path dedup in `_isolate_required_targets`
  (first occurrence is authoritative; any later marker whose normalized path is already-consumed folds
  back as ordinary content) so each authoritative path is checked/passed/blocked AT MOST ONCE and the
  invariant checked/passed/blocked/missing <= authoritative count now HOLDS FOR REAL; (2) defense-in-depth
  -- `neutralizeRequiredTargetMarker` now also wraps the git-diff / HoloIndex-recall / active-editor
  lower-section bodies before assembly; (3) JS threading contract assertion (MFH-J-006) pins the bridge
  payload line that sets `required_target_paths` from `bridgeMeta.required_targets_authoritative_paths`
  so a future edit cannot silently drop it (which would make Python receive None -> forgeable fallback).
- No weakening: identification-only. No ACTION_BLOCK detector relaxed; AUDIT_STRUCTURAL_CATEGORIES
  untouched; #917 per-target isolation preserved (one blocked sibling omitted, rest survive).
- Tests: 9 Python MFH tests (6 authoritative + 3 dedup regression) -- 98/98 gate pass; the 3 dedup tests
  FAIL without the per-path dedup (proven non-vacuous) and PASS with it; contract MFH-J-001..007
  adversarial + threading + lower-section-neutralization proofs; full JS contract suite exit 0 on 0.3.40.
- Golden bar: 6-file prompt yields `required_targets_in_model_context: 6`,
  `required_targets_context_missing: []`, `required_targets_redaction_blocked: 0`; adversarial fixture
  with embedded phantom AND duplicate-authoritative markers cannot inflate counts;
  `required_targets_redaction_checked` never exceeds authoritative packed count.
- Stacked on REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (#917).

### REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (v0.3.38)

- **Status:** VERIFIED_READY (this slice). The audit-mode redaction gate now isolates each
  required-target excerpt INDEPENDENTLY. When the merged context carries the stable marker
  `### Required direct-read target: <path>`, the Python redaction layer
  (`fusion_redaction_gate.py::_isolate_required_targets`) splits it into preamble + per-target
  sections, evaluates each section's block status on its own, OMITS only the sections that hit a
  non-audit-structural hard block (marker + a redaction notice kept, body gone), preserves the rest,
  reassembles, and runs the UNCHANGED whole-context audit-mode gate over the survivors.
- Root cause it fixes: the packing path (#914) merged all required excerpts into ONE context gated as
  a single unit, so ONE hard-block token (private_reasoning / private_key_residual) blocked the ENTIRE
  payload (`redacted_context=None`) and dropped ALL required targets even in audit_mode.
- No weakening: granularity-only change. No ACTION_BLOCK detector relaxed; nothing added to
  AUDIT_STRUCTURAL_CATEGORIES; audit-mode value-vs-structure behavior unchanged; a blocked target's
  secrets never reach the model. Fail-closed: no markers / ambiguous split / block outside a section
  all fall back to the unchanged whole-context block.
- Telemetry: 5 new counts-only fields in the Run Trace scorecard (`required_targets_redaction_checked`,
  `_passed`, `_blocked`, `_blocked_paths`, `_blocked_reasons`), emitted by the gate report through the
  bridge. Default zero/empty on the non-audit / no-marker path (backward compatible).
- Golden bar: the 6-file FoundUps-creation audit (clean, 0 triggers) yields
  `required_targets_redaction_blocked: 0` and `required_targets_in_model_context: 6`. Adversarial proof:
  N>=3 sections with exactly ONE private_reasoning trigger -> only that target omitted, the rest survive,
  overall gate passes. 89/89 Python redaction tests pass; JS contract suite exit 0 on 0.3.38.
- Stacked on REDDOG_RUN_TRACE_BUILD_VERSION_FIELD_PHASE1 (#916).

### REDDOG_RUN_TRACE_BUILD_VERSION_FIELD_PHASE1 (v0.3.37)

- **Status:** VERIFIED_READY (this slice). The `## Run Trace` scorecard now emits
  `- extension_version: <EXTENSION_VERSION>` near the top of the block (after the header, before the
  role/tier fields). It reads the real installed-build constant, NOT any prompt/packet/model value.
- Incident driving it: a golden rerun was mistakenly run on a STALE 0.3.34 build while the model OUTPUT
  header claimed "Build: 0.3.36" (it parroted a "Version expected:" prompt line). The trace carried no
  machine-checkable build field, so staleness was invisible from telemetry.
- Purely additive telemetry. No packing/redaction/fetch/continuation change; no new file-read; no
  execution authority.
- Golden bar: `buildRunTraceSection(...)` output contains `- extension_version: ` == package.json version;
  the source line reads the EXTENSION_VERSION constant. 012 gates build staleness on this field, not model
  text.
- Stacked on REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1 (#915).

### REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1 (v0.3.36)

- **Status:** VERIFIED_READY (this slice). The webview "Use last RedDog packet" checkbox now defaults
  UNCHECKED - continuation is opt-IN, not opt-out. One-line HTML edit removed the `checked` attribute; the
  feature stays manually available (012 checks the box to append the prior WSP_97-safe summary).
- No backend logic change: the #911 fail-closed backend (`message.useLastPacket === true`) already treats
  missing/false as OFF, so an unchecked default yields `continuation_enabled=false` AND
  `continuation_appended=false` with no new code. The "Continuation: disabled for this run." status line
  (from #911) renders by default.
- No packing change (#914), no direct-read change, no redaction change, no new telemetry.
- Golden bar: default submit yields continuation_enabled=false AND continuation_appended=false; manual
  check still appends when a prior packet exists. Golden rerun no longer needs a manual uncheck.
- Stacked on REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1 (#914).

### REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1 (v0.3.35)

- **Status:** PACKING COMPLETE (this slice). Golden 6-file FoundUps-creation audit on 0.3.34 proved senses
  PASS (direct_read_fallback_used=true, 6/6 recalled) and audit egress PASS, but the MODEL claimed fetched
  files were "not in bounded context". Root cause = PACKING: `buildBoundedRepoContext()` joined all sections
  then applied one `.slice(0, 42000)` tail cut, so the HoloIndex JSON blob + git diff + self-file
  `extension.js` snippet crowded out the fetched required-target excerpts.
- Fix: when an explicit "Required direct-read targets" list is present AND the governed fetch succeeded, pack
  a PROTECTED required-target block FIRST with stable markers `### Required direct-read target: <path>`
  (per-target min 1800 / max 6000 chars, protected total 30000). Lower-priority sections yield to the 42K cut;
  the self-file snippet is demoted/omitted and can never precede the required-target markers.
- Proof (ADDENDUM B): `required_targets_in_model_context` / `_context_missing` / `_context_chars` /
  `_context_truncated` computed from the FINAL post-cut context string (marker scan), not fetch telemetry.
  Run Trace shows BOTH `required_targets_recalled` (fetched) and `required_targets_in_model_context`
  (model-visible).
- Backward compat: no required list => byte-identical packing, proof fields `unknown`. No new fs read path,
  no execution authority, no redaction/allowlist change.
- Tests: RTP-001..005 + ADDENDUM B in `verify_extension_contract.js` (`GOLDEN_6FILE_FOUNDUP_PROMPT`).
- HoloIndex: static anchors in INTERFACE/ModLog; indexing follow-up
  `HOLOINDEX_REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_INDEX_GAP_PHASE1` if queries still miss the packing files.

### REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_PHASE1 (v0.3.34)

- **Status:** WIRE COMPLETE (this slice). Golden 0.3.33 proved senses stack PASS but egress FAIL
  (`BLOCKED_LOCALLY`) because `audit_mode` never reached `advisory_model_once.py`.
- Wire path: `buildDirectReadContentSection().audit_context` -> `buildBoundedRepoContext().audit_context`
  -> `callFusion()` payload `audit_context` -> `evaluate_redaction_gate(..., audit_mode=True)`.
- Run Trace: `audit_context_requested`, `audit_context_applied`.
- Default path unchanged: no governance direct-read => strict gate unchanged.
- HoloIndex: static anchors in INTERFACE/ModLog; indexing follow-up
  `HOLOINDEX_REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_INDEX_GAP_PHASE1` if queries still miss implementation files.

### REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3)

- **Status:** GOVERNED FETCH (this slice), stacked on slice 1 (#906). When slice-1's detector reports
  `index_gap_detected=true` with missing required targets, the extension asks the Python bundle layer to FETCH
  those exact repo files (via `--bundle-must-include`) so RedDog reasons on real source instead of HOLDing blind.
- Fetch lives in `holo_index/cli/commands/bundle_json.py::_direct_read_fetch` (NOT raw fs in extension.js; no
  shell-out, no model/router change). Fetched hits splice into `code_hits`; slice-1 recall re-runs and flips
  `target_recall_ok` true; `direct_read_fallback_used=true`.
- HARD security allowlist: repo-relative only; realpath must stay in repo root (rejects absolute, `..` traversal,
  symlink-escape); hard-deny `.env*`/`*.pem`/`*.key`/`id_rsa*`/`id_ed25519*`/`*.p12`/`*.keystore`/
  `*secret*`/`*credential*`/`*token*`/`.git/`; per-file cap (12KB) + total budget (96KB) spread across many
  targets; denials recorded (`direct_read_rejected`), never abort the bundle.
- New telemetry: `direct_read_paths`, `direct_read_rejected`, `direct_read_bytes`, `direct_read_truncated`.
- **Slice boundary:** NO redaction-category change, NO audit-mode change (slice 3); NO execution authority.
  Fetched content passes the EXISTING redaction gate unchanged (governance content may still be over-sanitized
  until slice 3 - that is the slice-3 deliverable). Slice-2 bar = targets fetched + present + recall satisfied,
  NOT final answer quality.

### REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1 (slice 1/3)

- **Status:** DETECTOR ONLY (this slice). Parse an explicit "Required direct-read targets" prompt list; compare against
  content-bearing bundle locations (path-aware), with a self-file guard so retrieving `extension.js` (RedDog itself)
  cannot satisfy a required target.
- Fixes the `content_included(any file) != required_targets_recalled` false negative: RedDog now HONESTLY reports
  `index_gap_detected=true` when required targets are absent instead of falsely reporting no gap.
- New scorecard fields: `required_targets_total`, `required_targets_recalled`, `required_targets_missing`,
  and honest `target_recall_ok` / `index_gap_detected` (never `unknown` when a required list exists).
- Backward compatible: prompts with no required-target list keep prior inferred-target behavior.
- **Slice split:** 1/3 = this detector; 2 = direct-read-by-path fetch (0/8 -> 8/8 recall); 3 = audit-mode redaction.
  This slice makes the blindness VISIBLE; it does NOT add any file-read or change redaction.

### REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1

- **Status:** **LANDED** #885 (`888d0c9cc`) - REGULAR auto context `none` -> `wsp_holo`.
- Every auto-routed tier attaches HoloIndex bundle-json at minimum; REGULAR stays single-model without Skillz/git.
- Prerequisite: #883 landed (target content + sanitization on v0.3.22).
- Does not fix output validation, made_network_call telemetry, or mojibake (separate slices).

### REDDOG_CONTEXT_UNICODE_NORMALIZATION_PHASE1

- **Status:** **LANDED** #886 (`ca5703611`) - JS surrogate normalization + bridge UTF-8 stdin (0.3.25).

### REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1

- **Status:** **LANDED** #888 (`9c3a8f829`) - v0.3.27; 012 smoke PASS (2026-06-27).
- Repair telemetry, isolated Work Trail (`repair_single_*`), section-aware merge, OSR-007..010.
- Run Trace: `repair_context_mode: repair_minimal`, `repair_mode: openrouter_single`.
- Stale `provider_reasoning_note` deferred to `REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1`.

### REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1

- **Status:** **LANDED** #889 (`764084bc4`) - docs/audit only; no runtime wiring.
- **Canonical audit:** `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md`
- **Purpose:** Authority model for RedDog -> WRE worker path; `RedDogGovernedWorkOrder` schema draft.
- **Records:** authenticated principal -> GitHub permission snapshot -> governed work order -> OpenClaw -> Hermes -> WRE -> review -> merge gate.
- **RedDog receives bounded delegated capability per work order** - does not hold standing repo authority.
- **F0 autonomous merge:** SPECIFIED_NOT_IMPLEMENTED (not planned until prior gates land).
- **Blocks:** runtime execution slices until dryrun + permission probe land.
- **HoloIndex:** `--index-docs` gate PASS for audit doc (query 1); INDEX_GAP for extension ROADMAP/INTERFACE (probe 7) - follow-up slice required.

### REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1

- **Status:** **LANDED** #890 (`bd68ab83a`) - pure validation; stdlib only; `no_mutation_performed: true` invariant.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py`
- **Tests:** 13 pytest in `test_reddog_governed_work_order_dryrun.py`

### REDDOG_GITHUB_PERMISSION_PROBE_PHASE1

- **Status:** **LANDED** #892 (`21aeff32d`) - read-only `probe_repo_permission()` in github_integration.
- **Module:** `modules/platform_integration/github_integration/src/reddog_github_permission_probe.py`

### REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1

- **Status:** **LANDED** #893 (`329db7113`) - `evaluate_work_order_policy_gate()` in moltbot_bridge.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py`

### REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1

- **Status:** **LANDED** #894 (`b42db2165`) - `emit_work_order_receipt()` + SQLite audit store.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_work_order_receipt.py`

### REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1

- **Status:** **LANDED** #896 (`f65ecff4e`) - `invoke_reddog_work_order_dryrun()` chains #893 + #894.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py`

### REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1

- **Status:** **LANDED** #897 (`2fe60a280`) - contract-only audit doc; no executor code.
- **Canonical:** `docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md`

### REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1

- **Status:** **LANDED** #898 (`e215bf890`) - `plan_wre_isolated_worktree_execution_dryrun()`.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py`

### REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1

- **Status:** **LANDED** #899 (`c70433d7d`) - in-memory WSP_97-safe continuation; v0.3.28.

### REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1

- **Status:** **LANDED** #901 (`2c8df23dd`) -- contract-only audit doc; OpenClaw owns worker loop.
- **Canonical:** `docs/audits/architecture/REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md`
- **Ruling:** `AssignmentDispatcher` is simulated scaffold -- **not** canonical intake target.

### REDDOG_WRE_EXECUTION_VALVE_PHASE1

- **Status:** **LANDED** #903 (`2761f2e65`) -- `evaluate_reddog_execution_valve()`; default `VALVE_CLOSED`.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py`
- **Contract:** `docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md`

### REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1

- **Status:** **PR-READY** -- `plan_reddog_openclaw_adapter_dryrun()`; propose only, no enqueue.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_openclaw_adapter_dryrun.py`
- **Contract:** `docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md`

### REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1

- **Status:** **IMPLEMENTED (worktree-create only)** -- `create_reddog_wre_worktree()` consumes an accepted executor dry-run plan plus `VALVE_OPEN_WORKTREE_CREATE`, creates the isolated worktree through an injected runner, and stops before edits/tests/PR/merge.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_wre_worktree_create.py`
- **Runner:** `modules/communication/moltbot_bridge/src/reddog_wre_worktree_runner.py`

### REDDOG_WRE_OPERATIONAL_SPINE_WORKTREE_CREATE_PHASE1

- **Status:** **IMPLEMENTED (worktree-create spine only)** -- `run_reddog_wre_worktree_create_spine()` composes #896 invocation dry-run, #898 executor plan, #903 execution valve, and `create_reddog_wre_worktree()` into one callable API.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_wre_operational_spine.py`
- **Boundary:** no task execution, file edits, tests, PR, OpenClaw enqueue, Hermes dispatch, push, or merge. VS Code extension live invocation is a future gated slice.

### REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1

- **Status:** **IMPLEMENTED (extension dry-run preview only, v0.3.46)** -- `buildWreOperationalSpineDryRunPreview()` emits a typed candidate envelope into Copy MD and `review_packet.wre_operational_spine_dryrun_preview`.
- **Boundary:** no `cp.execFileSync` call to `reddog_wre_operational_spine.py`, no worktree create, no task execution, no file edit, no PR, no OpenClaw enqueue, no Hermes dispatch, no push, no merge. Blocked-local packets skip the preview.
- **Runtime emission:** **IMPLEMENTED (candidate only, v0.3.49)** -- `governed_work_order_runtime_emission` embeds a full `RedDogGovernedWorkOrder` candidate with digest and not-ready reasons. It is not executable authority.
- **Authority binding:** **IMPLEMENTED (metadata only, v0.3.50)** -- `permission_binding` and `signed_authority_binding` can make a candidate invocation-ready only when trusted/fresh and matching; the extension itself still does not run the GitHub probe or signature verifier.
- **Runtime wire:** **IMPLEMENTED (guarded bridge seam, v0.3.51)** -- `invokeWreOperationalSpineExplicitValveBridge()` emits a skipped/rejected/accepted invoke result and can call the one-shot Python guard only after a caller supplies accepted binding metadata plus `VALVE_OPEN_WORKTREE_CREATE` / sovereign wardrobe selection. Default runs skip invocation.
- **Wardrobe selection:** **IMPLEMENTED (dry-run receipt, v0.3.52)** -- `runOperatorWardrobeSelectionBridge()` emits the WSP_97/WSP_95 selection receipt that classifies the work focus into solo/audit/implementation/sovereign planes without executing or enqueueing.
- **GitHub permission probe:** **IMPLEMENTED (read-only snapshot, v0.3.53)** -- `runGithubPermissionProbeBridge()` emits a fresh trusted `repo_permission_snapshot` for the governed work-order candidate when the local authenticated `gh` context can observe repository permission. It performs no repo mutation.
- **Next gate:** RedDog must produce or receive accepted signed authority automatically before the runtime wire can create a real WRE worktree without 012 copy/paste.
- **Discoverability:** `HOLOINDEX_REDDOG_EXTENSION_GOVERNED_WORK_ORDER_EMISSION_INDEX_GAP_PHASE1` -- query-only preflight finds adjacent RedDog work-order modules/contracts but not the extension runtime-emission surface; WRE/CI re-index remains the maintenance owner.

### REDDOG_REVIEW_CONSENSUS_RECEIPTS_PHASE1

- **Status:** **P1 QUEUED** - Sentinel + reviewer signed opinions; Hermes receipts.

### REDDOG_AUTONOMOUS_MERGE_POLICY_PHASE1

- **Status:** **P3 BLOCKED** - until dryrun, permission probe, OpenClaw gate, WRE executor, review receipts land.

### HOLOINDEX_REDDOG_GOVERNED_WORK_ORDER_INDEX_GAP_PHASE1

- **Status:** **P1 REQUIRED** - probe query 7 misses `extensions/reddog/{ROADMAP,INTERFACE}.md`; `index_docs_entries` excludes `extensions/`.

### REDDOG_SANITIZED_TARGET_CONTEXT_PROVENANCE_PHASE1

- **Status:** **P1 QUEUED** - tell RedDog target snippets may contain egress-safe placeholders; not repo source truth.
- **Trigger:** model misreads `[SANITIZED_BLOCK:NN]` in bounded context as live repo source (F10 class).

### REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1

- **Status:** **P1 QUEUED** - report-only telemetry fixes; not functional blockers.
- **Scope:** stale `provider_reasoning_note: Report-only in v0.3.23`; `made_network_call: unknown`; Work Trail duplicate cleanup.

### REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1

- **Status:** VERIFIED_READY on #883 (v0.3.22) - stacked base for grounding slice.
- Inject target file **content/snippets** into bounded bridge context when HoloIndex ranks the path but omits source body.
- Trigger: EXT-ACC-001 criterion #2 fail with model egress (path hit ~7.4%, no source body) - **OBSERVED**.
- Run Trace: `target_content_included`, `target_content_paths`, `target_content_chars`, `target_content_omitted_reason`, `target_content_truncated`.
- WSP_97 tasks: bounded protocol excerpt section.
- Bump version **0.3.22** (install hygiene after #882 no-bump trap).
- Distinct from HoloIndex ranking (#882); bounded context assembly in `buildBoundedRepoContext`.
- 012 only: installed Cursor UX smoke + Copy MD usability after PR VERIFIED_READY.

### REDDOG_GOVERNED_HANDOFF_CONTRACT_PHASE1

- **Status:** DEFERRED - implementation follows `REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1` audit.
- Typed handoff from RedDog review packet to WRE/OpenClaw/Hermes.
- Skillz match recommendations become structured dispatch payloads.
- Extension remains advisory; WRE retains execution authority.

### REDDOG_PFMALL_SURFACE_BINDING_PHASE1

- Bind RedDog architect review packets to pfMALL operator surfaces.
- Classify public vs member-gated flows.
- No automatic publication without verification gate.

### REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1

- **Status:** **PR-READY** - in-memory WSP_97-safe continuation summary; "Use last RedDog packet" toggle (default OFF as of v0.3.36 - opt-in; see REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1).
- Sanitized follow-up memory from last run; appends to WSP task prompt without raw Copy MD paste.
- No disk persistence, no WRE/OpenClaw runtime wiring.

### REDDOG_REVIEW_PACKET_MEMORY_PHASE1

- **Status:** **PARTIAL** - Phase 1 in-memory continuation only (`REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1`).
- Persist redacted review packets for HoloIndex recall and cross-session continuity (future).

### REDDOG_FUSION_ORCHESTRATOR_PHASE2

- Structured JSON review packet schema for findings/evidence/fixes/WSP_15 rows/truth labels.
- Parser tests proving output remains copyable and shareable with 0102.
- Optional effort override audit trail in review packet.

### REDDOG_ARCHITECT_EXTENSION_CONTRACT_PHASE2

- Add a structured JSON review packet schema for findings, evidence, fixes, WSP_15 rows, and truth labels.
- Add parser tests proving the output remains copyable and shareable with 0102.
- Keep advisory-only boundary.

### REDDOG_FOUNDUP_INTAKE_PACKET_MODE_PHASE1

- Add worker mode that produces WSP_109 packet drafts:
  - `INTAKE_SOURCE.md`
  - `OUTCOME.md`
  - `SOLUTION.md`
  - `PAIN.md`
  - `POC_SCOPE.md`
  - `PROTOTYPE_GATE.md`
  - `SKILLS_MAP.md`
  - `FOUNDUP_MANIFEST_DRAFT.md`
- Do not write files automatically.
- Output as advisory packet for 012/0102 review.

### REDDOG_PFMALL_SURFACE_AUDIT_PHASE1

- Audit current pfMALL RedDog surfaces and determine where the advisory packet belongs.
- Explicitly classify public vs member-gated flows.
- No runtime wiring in audit slice.

### REDDOG_WRE_OPENCLAW_HANDOFF_CONTRACT_PHASE1

- **Status:** DEFERRED - folded under work-order contract + dryrun phases.
- Define a typed handoff from RedDog review packet to WRE/OpenClaw.
- No direct Hermes/Kanban dispatch from the extension.
- WRE remains dispatch authority.

## Non-Goals

- No direct merge authority.
- No direct repo creation.
- No automatic pfMALL publication.
- No CABR/payout/source-authority claims.
- No hidden access to `.env` or gitignored files.
- No automatic F0 mutation.
- No worm-like self-propagation, auto-install, or background repo modification behavior.
