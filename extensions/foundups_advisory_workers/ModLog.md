# Foundups®Agent ModLog

# ModLog - Foundups®Agent Extension

## 2026-07-12 - REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_RUNTIME_WIRE_PHASE1 (guarded invoke seam, 0.3.51)

- Added `invokeWreOperationalSpineExplicitValveBridge()` and `scripts/reddog_extension_wre_spine_invoke_once.py` as the extension-side runtime seam to the landed Python explicit-valve guard.
- Default RedDog runs remain fail-closed: the runtime wire emits `EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_SKIPPED` unless a ready governed work-order candidate, explicit WRE invocation request, sovereign wardrobe selection receipt, valve environment, permission snapshot, and signed-authority verifier result are all supplied.
- The bridge passes authority metadata through stdin, never argv, and Copy MD surfaces the invoke decision without raw token/signature material.
- Version 0.3.50 -> 0.3.51 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_WORK_ORDER_PERMISSION_AND_SIGNATURE_BINDING_PHASE1 (authority binding, 0.3.50)

- `buildRedDogGovernedWorkOrderCandidate()` now binds supplied repo permission snapshots and signed-authority verifier results into `permission_binding` and `signed_authority_binding` metadata.
- Readiness is fail-closed: a caller-supplied boolean is not authority; `ready_for_wre_invocation=true` requires a fresh trusted permission snapshot, matching accepted signed-authority result, derived path scope, and explicit worktree valve request.
- The extension does not run the GitHub permission probe, verify signatures, sign payloads, invoke Python/WRE, create worktrees, enqueue OpenClaw, dispatch Hermes, create PRs, merge, or settle rewards in this slice.
- Version 0.3.49 -> 0.3.50 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_GOVERNED_WORK_ORDER_RUNTIME_EMISSION_PHASE1 (governed work-order candidate, 0.3.49)

- `buildWreOperationalSpineDryRunPreview()` now embeds a full `RedDogGovernedWorkOrder` candidate under `governed_work_order_runtime_emission`.
- The candidate binds extension version, work-focus digest, WSP prompt digest, HoloIndex evidence posture, derived path scope, rollback plan, nonce, expiry, and safe advisory source digests without storing raw work focus.
- Fail-closed boundary: the candidate uses `repo_permission_snapshot.source=extension_runtime_candidate`, `permission_level=needs_verification`, `signed_authority_verified=false`, and `explicit_valve_requested=false`, so it is not WRE-invocation-ready until later authority gates land.
- HoloIndex query-only preflight found the existing RedDog work-order spine and contracts, but not the new extension runtime-emission surface itself; recorded follow-up `HOLOINDEX_REDDOG_EXTENSION_GOVERNED_WORK_ORDER_EMISSION_INDEX_GAP_PHASE1`.
- Version 0.3.48 -> 0.3.49 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-11 - REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1 (refreshed contract pointer)

- Refresh stale #905 contract on current main after signed authority (#950) and signed receipt chain (#951).
- Contract remains docs/static-test only: no extension runtime call, no OpenClaw enqueue, no AgentDB write, no Hermes/WRE dispatch.
- Future live enqueue requires `VALVE_OPEN_LIVE_ENQUEUE`, accepted signed work authority, and signed receipt-chain verification.

## 2026-07-12 - HOLOINDEX_READONLY_QUERY_GUARD_PHASE1 (RedDog HoloIndex query posture, 0.3.48)

- RedDog HoloIndex calls now pass `HOLOINDEX_QUERY_READONLY=1` for bundle-json and offline fallback paths.
- HoloIndex CLI now defaults plain query/search mode to read-only and gates search-time auto-refresh behind explicit `--allow-auto-refresh`.
- HoloIndex collection reset refuses to run when `HOLOINDEX_QUERY_READONLY=1`, so a RedDog query process cannot mutate the semantic store even if a write path is accidentally reached.
- Version 0.3.47 -> 0.3.48 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-11 - REDDOG_JUDGMENT_GENERATION_WIRING_PHASE1 (Determine verifier wiring, 0.3.47)

- Wire the landed Determine contract plus adversarial verifier panel into the live RedDog extension path.
- `constructWspTaskPrompt()` now instructs RedDog to emit the canonical `## Determine Answers` fenced JSON block when the 012 work focus contains a Determine numbered list.
- Add `runJudgmentVerifier()` -> `scripts/reddog_judgment_verifier_once.py`, which verifies final Determine answers against already-fetched governed direct-read hits and the HoloIndex scorecard.
- Boundary: local/advisory only. No HoloIndex re-index, WRE enqueue, shell, repo mutation, OpenClaw/Hermes dispatch, or network call is performed by the verifier bridge.
- Copy MD / Run Trace now surface `judgment_verifier_*` telemetry plus an advisory INDEX_GAP event when direct-read evidence masks stale semantic retrieval.
- Version 0.3.46 -> 0.3.47 (package.json + EXTENSION_VERSION + README + contract-test assertions).
## 2026-07-09 - REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1 (extension dry-run preview, 0.3.46)

- Added `buildWreOperationalSpineDryRunPreview()` and `buildWreOperationalSpineDryRunPreviewSection()`.
  Substantive non-blocked RedDog packets now emit `review_packet.wre_operational_spine_dryrun_preview`
  and a Copy MD `## WRE Operational Spine Dry-Run Preview` section after the governed handoff section.
- Boundary: preview metadata only. The extension does NOT call
  `modules/communication/moltbot_bridge/src/reddog_wre_operational_spine.py`, does NOT create a worktree,
  does NOT execute tasks, does NOT edit files, does NOT create PRs, does NOT enqueue OpenClaw, does NOT
  dispatch Hermes, and does NOT push or merge. Blocked-local packets skip the preview.
- Safety: raw work focus is not stored in the preview; it records a full SHA256 `command_digest`, bounded
  sanitized `command_redacted_summary`, digest evidence refs, `required_future_valve: VALVE_OPEN_WORKTREE_CREATE`,
  and `required_human_gate: 012_sovereign`.
- Version 0.3.45 -> 0.3.46 (package.json + EXTENSION_VERSION + README + contract-test version assertions)
  so this dry-run preview build is distinguishable from the prior prose-tokenization 0.3.45 build.
- Next gate: `REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_EXPLICIT_VALVE_INVOKE_PHASE1` only after explicit
  `012_sovereign` + `VALVE_OPEN_WORKTREE_CREATE` and leak/non-mutation tests.

## 2026-07-07 - REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (P0 hotfix, 0.3.44 -> 0.3.45)

- Problem (OBSERVED, real 0.3.44 run on a free-form prose prompt): a `Read first:` prompt naming three
  files in ONE flowing sentence produced `target_recall_ok: false`. The read-capture branch tokenized the
  NON-bullet prose line with the COMMA-splitter (`extractTargetTokensFromLine`), so
  `holo_index/adaptive_learning/breadcrumb_tracer.py. Determine current lane-state sources` was captured
  WHOLE as `not_a_file` (breadcrumb_tracer.py MISSED) and `and the breadcrumb/handoff layer` (an
  embedded-slash English fragment) was captured whole as a garbage target. Result:
  `required_targets_total=4, recalled=2, target_recall_ok=false`. Derivation ENGAGED (0->4 derived,
  2 fetched) but prose tokenization was imprecise.
- Root cause (VERIFIED by reading): `deriveWorkFocusTargets`'s `read_first` capture used the comma-splitter
  on NON-bullet prose lines. The comma-splitter treats each comma-chunk as one token, so a chunk with a
  path+trailing-prose or an embedded slash becomes a bad target. The bounded path-token regex
  (`extractInlinePathTokens`, already used for source-6 inline prose) isolates clean path substrings.
- Fix (extension.js only; NO Python change):
  - Fix A (essential): the NON-bullet read-capture branch now tokenizes with `extractInlinePathTokens`
    (via new `extractProsePathTokens`) instead of `extractTargetTokensFromLine`. CLEAN BULLETS
    (`stripListMarker(...).isList`) keep the comma/`or`-splitter to preserve the `a / b / c` alternatives
    shape. Recovers `breadcrumb_tracer.py` cleanly.
  - Fix B (recall semantics + tiered strictness): FLOWING-PROSE-derived tokens (read-first prose +
    source-6 inline + source-7 backtick) are LOW-confidence -- a required target ONLY if it normalizes to a
    FILE SHAPE (a lowercase file extension). A prose token with a slash but NO extension
    (`breadcrumb/handoff`) is NOT required: dropped from `required_targets_total` / `required_targets_missing`
    (so it cannot flip `target_recall_ok`) and reported in the NEW `work_focus_targets_dropped_low_confidence`
    telemetry array. The explicit "Required direct-read targets" header, M2M `READ:`, M2M `CTX.FILES`, and
    CLEAN BULLETS keep the broader slash-OR-extension tier (a named directory path is still accepted). Only
    flowing prose is stricter -- the explicit/M2M/bullet tiers were NOT tightened.
  - Fix C (punctuation trim): `normalizeTargetPath` trailing set adds `}` to the existing
    `.` `,` `;` `:` `)` `]`, so `.../breadcrumb_tracer.py. Determine` -> `.../breadcrumb_tracer.py`.
- Reuse / ReDoS: `extractProsePathTokens` REUSES the existing bounded/anchored ReDoS-safe
  `extractInlinePathTokens` (no new backtracking regex introduced); `stripListMarker` (the ReDoS fix) is
  untouched. No `js/polynomial-redos`-style regex added. The governed fetch gate
  (`--bundle-must-include` -> `bundle_json.py` deny/traversal/budget) is unchanged; derived paths still flow
  through it. No Python / bundle_json.py / HoloIndex ranking / redaction change; no live-writer /
  orchestration-brain / budget-prioritization change (budget-prioritization is Phase 2, separate).
- Telemetry: NEW `work_focus_targets_dropped_low_confidence` (array of dropped raw tokens) threaded through
  `evaluateTargetRecall` -> `holoIndexMetaFromBundle` -> `extractHoloIndexScorecard` ->
  `formatHoloIndexScorecardLines` (Run Trace). Labeled OBSERVED (WSP_97). All existing fields preserved.
- Tests: WFTD-015..WFTD-020 in `tests/verify_extension_contract.js` using the EXACT failed 0.3.44 flowing-
  prose prompt as a fixture (`WORK_FOCUS_PROSE_READ_FIRST_PROMPT` in `tests/fixtures.js`): asserts
  `required_targets_total=3 / recalled=3 / target_recall_ok=true / index_gap_detected=false`, the 3 real
  files present + breadcrumb_tracer.py clean (no trailing " Determine..."), `breadcrumb/handoff` in
  `work_focus_targets_dropped_low_confidence` and NOT in required, Fix C trailing-punctuation trim, the
  bulleted-Read-first Option-3 regression, and the explicit/M2M/bullet broader-tier proof. WFTD-001..014
  regression preserved.
- Version 0.3.44 -> 0.3.45 (package.json + EXTENSION_VERSION + README + contract-test version assertions).
- Gate: VERIFIED_READY draft PR only (do NOT self-merge; merge is harness/012-gated, VSIX build is a 012
  host step).

## 2026-07-07 - REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (free-form target derivation, 0.3.44)

- Problem (OBSERVED, real run at 0.3.41/0.3.43): a multi-lane-orchestration audit named
  `docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md`, `docs/0102_session_briefings/work_ledger.schema.json`,
  and `holo_index/adaptive_learning/breadcrumb_tracer.py` in prose bullets, but NOT under the exact
  `Required direct-read targets:` header. Result: `required_targets_total: 0`,
  `direct_read_fetch_attempted: false`, `direct_read_fallback_used: false` -- the whole direct-read stack
  stayed dormant even though real paths were named. RedDog was retrieval-blind to free-form targets.
- Fix (extension.js only; NO Python change): new `deriveWorkFocusTargets(taskText)` derives required
  direct-read targets from read-intent shapes -- `Read first:` / `READ BEFORE EDITING` blocks, WSP_99 M2M
  `READ:` arrays, M2M `CTX.FILES` / `CTX: FILES:` arrays, markdown bullet path lists, and inline/backticked
  repo paths in prose. New `collectRequiredTargets(taskText)` MERGES the explicit-header list (kept FIRST,
  byte-identical for the header-only shape) with derived targets, de-duped case-insensitively in first-seen
  order. `evaluateTargetRecall` and `buildBoundedRepoContext` consume the MERGED list, so a derived path
  makes `required_targets_total > 0`, fires the SAME governed direct-read fetch, and is packed/proven like
  a header target -- regardless of HoloIndex semantic recall.
- False-positive guards: (A) inline/prose extraction uses a bounded, anchored, ReDoS-safe path-TOKEN regex
  (`WORK_FOCUS_PATH_TOKEN_RE`; a slash-less token requires a LOWERCASE file extension so acronyms / M2M keys
  like `CTX.FILES` are not captured and surrounding prose words are never swept in) -- heeds the CodeQL
  js/polynomial-redos lesson at `normalizeTargetPath`; (B) command/validation fences
  (```powershell / ```bash with `git diff --check`, `node --check`, `python holo_index.py ...`, `rg ...`)
  and scope-out / `Do NOT touch` / `OUT OF SCOPE` sections are EXCLUDED; ambiguous read-intent prefers
  precision (no derivation).
- CI hardening (folded into this PR before promotion): CodeQL flagged 2 new HIGH `js/polynomial-redos`
  alerts on the bullet-list marker regex (marker + `\s+` + greedy capture, where the leading whitespace
  class overlapped the trailing capture) -- the same rule/family as pre-existing alert #174. Replaced ALL
  THREE instances (the pre-existing one in `parseRequiredTargetPaths` plus the two new derivation instances)
  with a single linear O(n) `stripListMarker(line)` helper (no backtracking; the only regex is a
  quantifier-free single-character `\s` test), mirroring the `normalizeTargetPath` linear-trim remediation.
  Behavior is byte-identical (`{ isList, itemText }` matches the old `listMatch ? listMatch[1] : stripped`
  idiom). `stripListMarker` exported; WFTD-014 adds parity + regex-absence + pathological-input timing
  guards. Version stays 0.3.44 (unreleased; fix folded in, no VSIX churn).
- Governance unchanged: denied paths (`.env`, traversal, secret-like) are EMITTED honestly by the deriver
  and REJECTED by the unchanged Python direct-read gate (`bundle_json.py`); denylist / traversal protection /
  byte budgets / redaction / audit_context / required-target packing are all untouched. No HoloIndex
  ranking/index change; no runtime reindex; no live-writer / orchestration-brain change.
- Telemetry: `work_focus_targets_derived` (bool) + `work_focus_target_derivation_sources` (array from
  `{required_block, read_first, m2m_read, ctx_files, markdown_bullet, inline_path, backtick_path, symbol}`),
  threaded through `evaluateTargetRecall` -> `holoIndexMetaFromBundle` -> `extractHoloIndexScorecard` ->
  `formatHoloIndexScorecardLines` (Run Trace). Both labeled OBSERVED (WSP_97).
- Tests: WFTD-001..WFTD-013 in `tests/verify_extension_contract.js` (+ fixtures in `tests/fixtures.js`),
  covering all 8 source shapes, both guards, the denied-path honesty case, the HoloIndex-miss-still-fetches
  case, the no-path backward-compat case, and a real end-to-end regression (`holoIndexOutput` on the
  multi-lane prompt: `required_targets_total >= 3`, `direct_read_fetch_attempted: true`, all three files
  fetched/rejected/honestly-missing).
- Version 0.3.43 -> 0.3.44 (package.json + EXTENSION_VERSION + README + contract-test version assertions).
- Gate: VERIFIED_READY draft PR only (do NOT self-merge; merge is harness/012-gated, VSIX build is a 012
  host step). Judgment-lane retrieval-blindness fix (parallel to the judgment-lane slices #933-#935).

## 2026-07-05 - REDDOG_SYMBOL_AWARE_EXCERPT_DEPTH_PHASE1 (symbol line windows reach the model, 0.3.43)

- A required direct-read target may now be `path#symbol`. The Python bundle layer
  (holo_index/cli/commands/bundle_json.py) returns a bounded LINE WINDOW around the symbol's
  DEFINITION instead of the head-clip of the first 12KB, so a symbol defined deep in a large file
  (e.g. `build_foundup` / `extract_foundup`) actually reaches the model.
- Extension wiring: the full `path#symbol` token is forwarded to `--bundle-must-include` verbatim
  (a pathless `symbol:` prefix is still excluded, unchanged). `stripSymbolSuffix(target)` normalizes
  `path#symbol` -> the bare path for all recall/resolve comparisons (`requiredTargetMatchesLocation`,
  the resolver, the required-target context-proof denominator), because the fetched hit's location is
  the bare path. `extractTargetTokensFromLine` shape-checks the PATH portion so a `path#symbol` target
  parses. `stripSymbolSuffix` is bounded/anchored (ReDoS-safe).
- Extension contract test extended: stripSymbolSuffix behavior, recall-by-bare-path for a `path#symbol`
  target, forwarded `--bundle-must-include` token, end-to-end `parseRequiredTargetPaths`, and the
  unchanged `symbol:`-prefix exclusion.
- Gate: VERIFIED_READY draft PR only (do NOT self-merge). Judgment-lane slice 3 (after #933/#934).

## 2026-07-05 - REDDOG_REPAIR_PRESERVES_EVIDENCE_PHASE1 (repair preserves Determine evidence, 0.3.42)

- The schema-repair pass now PRESERVES a primary Determine answer block. A repair exists to ADD missing
  sections; it must not silently drop / reorder / weaken (OBSERVED -> vague NEEDS_VERIFICATION) / strip
  file:line evidence / fabricate anchors in the evidence-backed Determine answers.
- Wiring (repair path, callFusion review flow):
  - PRE-REPAIR: `runRepairGuard(context, 'protect', ...)` extracts the protected block and prepends it to
    the `repair_minimal` bounded context, so the repair model reproduces the answers UNCHANGED.
  - POST-MERGE: after `mergeRepairedOutput`, `runRepairGuard(context, 'guard', ...)` revalidates the merged
    output. On `keep_original` the merge is DISCARDED and the primary + its validation failure is kept
    (`repair_failure_reason: repair_dropped_determine_evidence`). Existing schema-completeness acceptance is
    unchanged for the non-keep-original branch.
  - Fail-closed: if the guard bridge is unavailable, a primary that carried a Determine block still keeps
    the original (`repair_evidence_reasons: ['guard_bridge_unavailable']`).
- REUSES the Python Determine contract's `assert_repair_preserves` (no preservation rules reimplemented in
  JS) via `scripts/reddog_repair_guard_once.py` (synchronous `cp.execFileSync`, same pattern as HoloIndex/git).
  New helpers `runRepairGuard` / `hasDetermineAnswersBlock` exported; telemetry `repair_evidence_protected` /
  `repair_evidence_preserved` / `repair_evidence_reasons` added to output_validation.
- Guard hardened via a 5-round 8-lens adversarial CoR (R5 all SAFE, 0 findings). Extension contract test
  extended: source wiring + ATX/SETEXT block presence + real end-to-end guard bridge (protect/faithful/strip/drop).
- Gate: VERIFIED_READY draft PR only (do NOT self-merge). Judgment-lane slice 2 (after #933 Determine contract).

## 2026-07-03 - REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (all-section + legacy-path closure, 0.3.41)

- Closes the LAST two residual required-target-telemetry forgery vectors so forgery_inert=true holds on
  ALL paths/sections, not only the authoritative (packProtected=true) path that 0.3.39/0.3.40 hardened.
- VECTOR A (incomplete lower-section neutralization): `neutralizeRequiredTargetMarker` was applied to the
  HoloIndex recall blob, active-editor content, and git status/stat/diff bodies, but THREE (really four)
  raw file-body lower sections still pushed UN-neutralized content that could contain a literal
  "### Required direct-read target: <path>" marker minted from file CONTENT:
    - target-recall section (`buildTargetRecallContentSection` -> `#### <rel>` fenced raw snippets),
      neutralized at push (extension.js ~2636).
    - WSP_97 excerpt (`buildWsp97ProtocolExcerpt` -> raw protocol body), neutralized at push (~2648).
    - Skillz/Wardrobe/Rolodex discovery (`skillzWardrobeRolodexContext` -> `readBoundedRepoFile` raw
      snippets), neutralized at push (~2661).
    - plain direct-read section (`buildDirectReadContentSection` -> raw fetched `hit.content`), reachable
      only when packProtected=false (the exact Vector B window); neutralized at push (~2617).
  Now EVERY `lowerSections.push(...)` routes its body through `neutralizeRequiredTargetMarker`. No
  file-body section can emit the literal marker prefix into the Python isolation splitter.
- VECTOR B (legacy None path): when `audit_context=true` but `packProtected=false` (direct-read code_hits
  present -> audit_context true, but `direct_read_fallback_used` false -> `authoritativePacked=[]`), the
  JS emitted an EMPTY authoritative list. `scripts/advisory_model_once.py` collapsed the empty list to
  `None`, and `fusion_redaction_gate._isolate_required_targets(None)` is the LEGACY path where
  `authoritative_set` is None -> EVERY marker section (including content-minted phantoms) is
  checked/counted and could mint content-controlled `blocked_paths`. Fix: under `audit_context_requested`
  the empty/absent list is NOT collapsed to None -- an EXPLICIT EMPTY tuple `()` is forwarded, so the gate
  builds an EMPTY `authoritative_set`: every marker's `norm_path not in authoritative_set` is true ->
  every marker folds back as ordinary content (checked==0, passed==0, no forged blocked_paths), while any
  real secret/token in a folded body STILL fails the whole payload closed via the audit-mode whole-context
  gate. Non-audit legacy behavior stays byte-identical (absent/empty -> None). The direct
  `_isolate_required_targets(..., None)` legacy contract is unchanged (no frg.py guard added), so
  `test_mfh_authoritative_none_is_byte_identical_legacy` still holds.
- Completeness / forward-safety: MFH-J-008 ENUMERATES every `lowerSections.push` site in the extension
  source and asserts 100% route through `neutralizeRequiredTargetMarker`; a FUTURE new raw-body section
  pushed without neutralization fails the contract runner rather than silently reopening the forgery.
  MFH-J-007b pins the four new file-body call sites explicitly. Python: `test_mfh_vectorb_*` (empty-set
  folds every marker, zero counts, still fails closed on a token; differs from legacy None) +
  `test_vectorb_*` (bridge forwards `()` under audit_mode, `None` on the non-audit legacy path).
- No weakening: identification/counting only. No ACTION_BLOCK detector relaxed, `AUDIT_STRUCTURAL_CATEGORIES`
  unchanged, #917 one-blocked-sibling-survives content-safety and #914 budget preserved. Authoritative path
  (dedup / neutralization / #917 / #914) still inert. Version bump 0.3.40 -> 0.3.41.

## 2026-07-03 - REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (per-path dedup completion, 0.3.40)

- Closes the residual duplicate-authoritative-marker bypass that survived the 0.3.39 authoritative fix.
  #918 made the JS `in_model_context` proof unforgeable, but the Python isolation telemetry
  (`required_targets_redaction_checked/passed/blocked/blocked_paths/reasons`) was still forgeable:
  `neutralizeRequiredTargetMarker` was applied ONLY to the protected required-target EXCERPT bodies, so
  the LOWER sections (git diff, HoloIndex recall JSON blob, active editor) merged UN-neutralized into the
  same `gate_context` that Python's `_isolate_required_targets` splits. In `wsp_holo_git*` modes a
  MODIFIED required file whose OWN body contains the literal line
  "### Required direct-read target: <its-own-authoritative-path>" rendered that marker un-neutralized in
  the git diff; Python split it as a SECOND section whose path normalized to the SAME authoritative path,
  PASSED the authoritative gate, and was counted AGAIN (no per-path dedup) -> checked/passed EXCEEDED the
  authoritative count (falsifying the docstring invariant). If that diff body also carried a hard-block
  token, the clean authoritative path was appended to blocked_paths with a forged reason while its REAL
  protected section was clean.
- Fix (robust single point = per-path dedup; identification only, no policy change):
  - PRIMARY (Python per-path dedup) in `_isolate_required_targets` (fusion_redaction_gate.py ~:499-543):
    a `consumed_paths` set tracks normalized authoritative paths already consumed. An authoritative path
    is checked/passed/blocked AT MOST ONCE (the FIRST marker section for that path -- the real packed
    protected section, packed BEFORE any lower section). Any SUBSEQUENT marker whose normalized path is
    already-consumed folds back as ORDINARY content (exactly like a non-authoritative phantom). This makes
    checked/passed/blocked/missing <= authoritative count HOLD FOR REAL, even with duplicate authoritative
    markers minted by lower sections; blocked_paths stays a subset of authoritative paths.
  - Defense-in-depth (JS lower-section neutralization) in extension.js: `neutralizeRequiredTargetMarker`
    now also wraps the git-diff (`### git status/--stat/git diff -- .` bodies ~:2643-2649), HoloIndex
    recall JSON blob (~:2583), and active-editor content (~:2639) before assembly, so a literal marker in
    those sections cannot reach the Python splitter as a real marker in the first place.
  - JS threading contract assertion (MFH-J-006 in verify_extension_contract.js): pins the bridge payload
    line that sets `required_target_paths` from `bridgeMeta.required_targets_authoritative_paths` so a
    future edit cannot silently drop it (which would make Python receive None -> the forgeable #917
    fallback at runtime while Python-direct tests still pass). MFH-J-007 pins the three lower-section
    neutralization call sites.
- No weakening: identification-only. No ACTION_BLOCK detector relaxed; AUDIT_STRUCTURAL_CATEGORIES
  untouched; the #917 one-blocked-sibling-survives content-safety fix and #914 budget math preserved.
- Tests: 3 new Python dedup regression tests in test_fusion_redaction_gate.py
  (duplicate-authoritative-marker-in-git-diff-not-recounted; duplicate-with-hard-block-token-does-not-
  forge-blocked-path; counts-never-exceed-authoritative-with-many-duplicates) -> 98/98 gate tests pass.
  Proven non-vacuous: the 3 dedup tests FAIL when the per-path dedup condition is disabled (checked=6
  instead of 2) and PASS with it. Contract test adds MFH-J-006 (threading) + MFH-J-007 (lower-section
  neutralization). Full JS contract suite exit 0 on 0.3.40; golden 6-file still in_model_context=6,
  redaction_blocked=0.
- Version: LIVE-surface bump 0.3.39 -> 0.3.40.
- Stacked on the 0.3.39 authoritative fix (same #918 slice) and REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (#917).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (authoritative unforgeable required-target telemetry, 0.3.39)

- Root cause (marker-reparse forgery): the required-target telemetry was derived by REPARSING marker
  strings out of merged text, so file CONTENT could forge it. JS `computeRequiredTargetContextProof`
  (extension.js) counted marker substrings via `text.indexOf(REQUIRED_TARGET_MARKER_PREFIX + target)`
  over the FINAL text, so a phantom marker inside a target BODY flipped a never-fetched target from
  missing -> in_model_context. Python `_isolate_required_targets` (fusion_redaction_gate.py) split the
  context on the marker and derived checked/passed/blocked + blocked_paths from marker-delimited
  SECTIONS, so a body containing "### Required direct-read target: <path>" minted a PHANTOM section ->
  inflated checked/passed and forged blocked_paths. The marker is not exotic (RedDog's own
  docs/ModLog/INTERFACE/verify_extension_contract.js contain it), so this fired on realistic
  self-referential audits, not just attacks.
- Fix (structured-records; identification only, no policy change):
  - JS proof is now AUTHORITATIVE: `computeRequiredTargetContextProof` iterates the packer's STRUCTURED
    record (`protectedInfo.included_paths` -- the paths actually packed), NOT markers scanned out of
    text. A requested target counts as in_model_context only if it is in the authoritative packed set
    AND its OWN fenced section survived the final cut (`requiredTargetSectionSurvived`). A phantom marker
    for a path not in the authoritative set is never counted; a requested-but-never-packed path is
    reported missing (never flipped present by a stray marker).
  - JS pack-time defense-in-depth: `neutralizeRequiredTargetMarker` inserts a zero-width WORD JOINER
    (U+2060, written in source as the ASCII escape backslash-u-2060) after the "### " lead of any literal
    marker occurring INSIDE an excerpt BODY, so a target's content can never mint a sibling marker (nor
    a phantom section for the Python splitter). Visually inert to reader/model; breaks the byte sequence.
  - Python authoritative-list intersection: the JS packer threads its authoritative `included_paths`
    through the bridge payload (`required_target_paths`) -> `advisory_model_once.py` ->
    `evaluate_redaction_gate(..., required_target_paths=...)` -> `_isolate_required_targets(context,
    authoritative_paths)`. A marker-delimited section is treated as a required-target section only when
    its path is IN the authoritative list; phantom markers (path not in list) are folded back verbatim
    as ORDINARY content (still redacted by the whole-context gate, never counted as a section). So
    checked/passed/blocked/missing can never exceed the authoritative count and blocked_paths is a
    subset of authoritative paths. When no list is threaded (None) behavior is byte-identical to #917.
- No weakening: identification-only. No ACTION_BLOCK detector relaxed; AUDIT_STRUCTURAL_CATEGORIES
  untouched; audit-mode value-vs-structure behavior unchanged; the #917 content-safety fix (one blocked
  target omitted while siblings survive) is preserved. This slice only changes how telemetry / sections
  are IDENTIFIED, never what is blocked.
- Tests: 6 new Python tests in test_fusion_redaction_gate.py (embedded-marker-not-a-section;
  malicious-fixture-no-extra-sections; blocked_paths-subset-of-authoritative; the ADVERSARIAL
  full-fixture no-inflation/no-phantom; authoritative-None-byte-identical-legacy;
  authoritative-one-blocked-sibling-survives) -> 95/95 gate tests pass. Contract test adds
  MFH-J-001..005 (authoritative structured proof; the adversarial phantom-marker-in-final-text proof;
  body neutralization; packed-section marker-count == included_paths; post-cut survival honesty). Full
  JS contract suite exit 0 on 0.3.39.
- Version: LIVE-surface bump 0.3.38 -> 0.3.39.
- Stacked on REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (#917).
- HoloIndex: the new hardening functions do not surface in semantic recall (index gap) ->
  HOLOINDEX_REDDOG_MARKER_FORGERY_INDEX_GAP_PHASE1 (SPECIFIED_NOT_IMPLEMENTED; static anchors here + in
  INTERFACE only; no ranking/reindex code changed). HoloIndex discoverability is NOT an acceptance gate.
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (per-target redaction isolation for required-target evidence, 0.3.38)

- Root cause: the packing path (#914) assembles all required-target excerpts into ONE merged context,
  then the WHOLE context is redaction-gated once (advisory_model_once.py evaluate_redaction_gate;
  fusion_alias_live.py line ~199). The gate had NO per-target isolation: if ONE required excerpt
  contained a hard-block token (private_reasoning / private_key_residual), the ENTIRE merged payload
  blocked -> redacted_context=None -> ALL required targets dropped, even in audit_mode. The 6 golden
  files are clean (0 triggers), but this was a known sharp edge on the evidence-ingress path.
- Fix (granularity only, in the Python redaction layer fusion_redaction_gate.py): when audit_mode AND
  the context carries the stable marker `### Required direct-read target: <path>`, the gate now splits
  the context into preamble + per-target sections, evaluates each section's block status INDEPENDENTLY,
  OMITS only the sections that trigger a non-audit-structural block (marker + a redaction notice kept,
  body gone -> secrets never reach the model), preserves all other sections verbatim, reassembles, and
  runs the UNCHANGED whole-context audit-mode gate over the survivors. One blocked required target no
  longer drops the clean ones; the overall gate passes (redacted_context non-None).
- No weakening: this changes ONLY the GRANULARITY of the block (per-target instead of whole-payload),
  never WHAT is blocked. No ACTION_BLOCK detector relaxed; AUDIT_STRUCTURAL_CATEGORIES untouched;
  audit-mode value-vs-structure behavior unchanged; private_reasoning / private_key_residual still
  always block their section. The in-context notice sanitizes the block-category name (underscore ->
  dot) so it can never re-trigger a detector; the real category name lives only in counts-only
  telemetry. Fail-closed: no markers or an ambiguous split -> the unchanged whole-context gate runs; a
  block outside a target section still blocks the whole payload.
- Telemetry (5 new counts-only fields; surfaced in the Run Trace scorecard): required_targets_redaction_checked,
  required_targets_redaction_passed, required_targets_redaction_blocked, required_targets_redaction_blocked_paths[],
  required_targets_redaction_blocked_reasons[]. Emitted by the Python gate report -> advisory_model_once.py
  (top-level result + review_packet) -> extension.js holoScorecard -> formatHoloIndexScorecardLines. Default
  zero/empty on the non-audit / no-marker path (backward compatible).
- Tests: 10 new per-target isolation tests in test_fusion_redaction_gate.py (adversarial one-blocked-others-survive;
  secret target withheld; loose secret redacted-in-place; all-clean 6-file mirror; backward-compat no-markers;
  non-audit path unchanged; block-outside-section still blocks; notice-does-not-reintroduce-trigger;
  no-detector-relaxed; zero-network). 89/89 pass. Contract test adds RPTI-001..004 (scorecard mapping +
  render + defaults). Full JS contract suite exit 0 on 0.3.38.
- Version: LIVE-surface bump 0.3.37 -> 0.3.38.
- Stacked on REDDOG_RUN_TRACE_BUILD_VERSION_FIELD_PHASE1 (#916).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_RUN_TRACE_BUILD_VERSION_FIELD_PHASE1 (emit extension_version in Run Trace scorecard, 0.3.37)

- Incident: a golden rerun was mistakenly run on a STALE 0.3.34 build, but the model OUTPUT header claimed
  "Build: 0.3.36" because it parroted a "Version expected:" line from the prompt. The Run Trace scorecard
  did NOT emit the actual installed build version as a telemetry field, so staleness could not be detected
  from the trace itself (only from the UI footer). The model text masked the real build.
- Fix: `buildRunTraceSection(...)` now emits `- extension_version: ` + `EXTENSION_VERSION` (the real
  installed-build constant) near the TOP of the `## Run Trace` block, immediately after the header and
  before the role/tier fields. It reads the constant, NOT any value from the prompt, packet, or model
  output, so build staleness is machine-checkable from telemetry and can never be masked by model text.
- Purely additive telemetry. No packing, redaction, fetch, or continuation logic changed. No new
  file-read. No execution authority.
- Tests (verify_extension_contract.js): (a) `buildRunTraceSection(...)` output contains
  `- extension_version: ` followed by the current EXTENSION_VERSION; (b) that value equals the
  package.json version (they must agree - the trace proves the build); (c) the source line reads the
  EXTENSION_VERSION constant, not prompt/packet/model text. Full JS contract suite exit 0 on 0.3.37.
- 012 note: the Run Trace now carries `extension_version` = the real installed build; use it (not model
  text) as the staleness gate.
- Version: LIVE-surface bump 0.3.36 -> 0.3.37.
- Stacked on REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1 (#915).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1 (default Use-last-packet checkbox OFF, opt-in continuation, 0.3.36)

- Change: the webview "Use last RedDog packet" checkbox now defaults UNCHECKED. Continuation is opt-IN
  instead of opt-out. The feature stays manually available (012 can check the box to append the prior
  WSP_97-safe summary). One-line HTML edit: removed the `checked` attribute from
  `<input id="useLastPacket" type="checkbox">`.
- No backend logic change. The #911 fail-closed backend (`const continuationEnabled = message.useLastPacket
  === true`) already treats missing/false as OFF, so an unchecked default yields
  `continuation_enabled=false` AND `continuation_appended=false` with no new code. The frontend still sends
  `useLastPacket: continuationOn` where `continuationOn = !!(useLastPacket && useLastPacket.checked)`.
- The "Continuation: disabled for this run." status line (from #911) now renders by default (unchecked run),
  which is the intended opt-in signal.
- No packing change (#914), no direct-read change, no redaction change, no new telemetry (continuation
  telemetry already exists from #911).
- Tests (verify_extension_contract.js): (a) the useLastPacket checkbox HTML default has NO `checked`
  attribute; (b) default submit (useLastPacket false/absent) yields continuation_enabled=false AND
  continuation_appended=false and Copy MD does NOT append the summary even when a prior packet exists;
  (c) manual check (useLastPacket=true) still appends when a summary is present (feature not removed). Full
  JS contract suite exit 0 on 0.3.36.
- Golden rerun note: default-off is now the shipped behavior; the golden rerun no longer needs a manual
  uncheck of the box.
- Version: LIVE-surface bump 0.3.35 -> 0.3.36.
- Stacked on REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1 (#914).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1 (protect required-target excerpts in final model context, 0.3.35)

- Problem (golden 6-file FoundUp-creation audit on 0.3.34): senses stack PASS
  (direct_read_fallback_used=true, target_recall_ok=true, 6/6 recalled) and audit egress PASS
  (audit_context requested+applied, redaction passed), but the model pass FAILED: the model claimed
  fetched files (foundup_job_contract.py, hermes_foundup_job_executor.py,
  reddog_governed_work_order_dryrun.py, reddog_wre_execution_valve.py) were "not in bounded context".
- Root cause = PACKING, not fetch/recall. `buildBoundedRepoContext()` joined all sections then applied a
  single `.slice(0, 42000)` tail cut. Section order put the HoloIndex raw JSON blob (18KB), the git diff
  (24KB), and the self-file `extension.js` target-recall snippet (24KB) ahead of / around the fetched
  direct-read required-target content, so the required-target excerpts were guillotined by the tail cut.
  direct_read_bytes=72000 but final bounded context = 42000 chars; the fetch/recall telemetry read 6/6
  while the model saw far fewer.
- Fix: when a prompt carries an explicit "Required direct-read targets" list AND the governed fetch
  succeeded (`direct_read_fallback_used`), pack a PROTECTED required-target block FIRST (right after the
  WSP contract head), each target rendered with a STABLE marker `### Required direct-read target: <path>`.
  Per-target minimum-first budget (min 1800 / max 6000 chars, protected total 30000) so a large early file
  cannot starve later required files. Lower-priority sections (HoloIndex JSON blob, git diff, Skillz,
  self-file snippet) yield to the 42K cut instead of the required-target excerpts; the self-file
  `extension.js` target-recall snippet is DEMOTED/OMITTED in explicit-target audit mode.
- ADDENDUM B (model-context proof): new telemetry `required_targets_in_model_context`,
  `required_targets_context_total`, `required_targets_context_chars`, `required_targets_context_missing`,
  `required_targets_context_truncated` are computed by scanning the FINAL post-cut context string for the
  stable markers -- NOT from fetch/bundle telemetry. Run Trace renders BOTH `required_targets_recalled`
  (fetched/available layer) and `required_targets_in_model_context` (actually model-visible layer); the two
  layers are never conflated.
- Backward compat: prompts WITHOUT a required-target list pack byte-identically (head+lower join+same 42K
  cut); model-context proof fields stay 'unknown'. No new file-read paths (protected block reuses the
  already-fetched, already-redaction-gated direct-read hit content). No execution authority, no redaction
  policy change, no change to the Python fetch/allowlist or the #913 audit_mode wire.
- Tests: RTP-001..RTP-005 + ADDENDUM B assertions in `verify_extension_contract.js`
  (`GOLDEN_6FILE_FOUNDUP_PROMPT` live packing proof: all 6 markers survive the 42K cut;
  in_model_context == total when recall satisfied; context_missing == []; legacy prompt preserves ordering
  and stays 'unknown'; large required file does not starve siblings; a marker cut post-slice counts as
  missing). Full JS contract suite exit 0. Python `test_reddog_extension_bundle_recall.py`: 15 pass, 2 pre-
  existing discoverability failures (extension.js not in top HoloIndex hits) that also fail on the base SHA
  -- index-staleness, not a regression of this slice.
- HoloIndex discoverability (ADDENDUM A, pre-edit): queries "RedDog required target context packing",
  "buildBoundedRepoContext 42000 slice", "buildDirectReadContentSection direct-read target content",
  "buildTargetRecallContentSection extension.js" did NOT surface `extension.js` or
  `verify_extension_contract.js` in top code hits (INDEX_GAP -- OBSERVED). Static anchors added to
  INTERFACE.md / ROADMAP.md. Follow-up indexing slice:
  `HOLOINDEX_REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED -- no
  ranking/reindex code changed here). Discoverability is NOT the acceptance bar; acceptance is final-context
  marker proof + golden model answer quality.
- Version: LIVE-surface bump 0.3.34 -> 0.3.35.
- WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-07-02 - REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_PHASE1 (audit_context bridge wire, 0.3.34)

- Problem (golden rerun on 0.3.33): **senses stack PASS** (7/7 recall, direct_read_fallback_used=true,
  continuation off) but **model pass FAIL** — `redaction gate status: BLOCKED_LOCALLY`,
  `made_network_call: false`. Root cause: slice-3 `audit_mode` exists in `fusion_redaction_gate.py` and
  `buildDirectReadContentSection()` surfaces `audit_context: true`, but the live path
  `extension.js` -> `scripts/advisory_model_once.py` never passed the flag into
  `evaluate_redaction_gate()`.
- Fix: `buildBoundedRepoContext()` preserves `audit_context` from `holo.direct_read_section`;
  `callFusion()` payload carries `audit_context: true` when `promptConstruction.audit_context_requested`;
  `advisory_model_once.py` passes `audit_mode=audit_context_requested` into the entry gate only.
  Run Trace telemetry: `audit_context_requested`, `audit_context_applied`.
- Default path byte-identical: no direct-read governance context => `audit_context=false` => strict gate unchanged.
- Tests: ACB-001..005 in `verify_extension_contract.js`; 3 bridge tests in
  `scripts/tests/test_advisory_model_once_hardening.py`.
- HoloIndex discoverability (ADDENDUM A, pre-edit): queries for bridge wire / audit_mode did NOT surface
  `extension.js`, `advisory_model_once.py`, or `fusion_redaction_gate.py` in top code hits
  (INDEX_GAP — OBSERVED). Static anchors added to INTERFACE.md / ROADMAP.md. Follow-up indexing slice:
  `HOLOINDEX_REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED — no ranking
  code changed in this slice).
- Version: mechanical LIVE-surface bump 0.3.33 -> 0.3.34.
- WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-07-02 - REDDOG_DIRECT_READ_FALLBACK_TRIGGER_DIAGNOSTIC_PHASE1 (enriched-fetch buffer + fetch-error telemetry, 0.3.33)

- Problem (golden rerun on landed 0.3.31): slice-1 detector WORKED (index_gap_detected=true,
  required_targets_total=8, recalled=0) but slice-2 enriched fetch NEVER surfaced in the scorecard
  (direct_read_fallback_used=false, 0 paths, 0 rejected). CONFIRMED ROOT CAUSE = maxBuffer overflow,
  swallowed silently. The caller passes maxChars=18000; the enriched `execFileSync` set
  `maxBuffer: Math.max(maxChars*8, 131072)` = 144000 bytes (~141KB). The enriched bundle for the 8
  FoundUp targets is ~184.5KB (proxy-measured 184529 bytes = semantic bundle + governed fetched
  content). 184.5KB > 141KB => the subprocess throws ENOBUFS+SIGTERM, and the EMPTY `catch (fetchErr)`
  swallowed it, keeping the pre-fetch bundle/meta and reporting fallback_used=false with no cause.
- Fix 1 (buffer + timeout): the enriched call now sizes `maxBuffer = Math.max(maxChars*16, 8*1024*1024)`
  (8MB floor, wide headroom over the ~185KB observed size and the ~96KB Python total fetch budget) and
  `timeout = 45000` (up from 30s; the enriched call re-runs HoloIndex + reads N target files under load).
- Fix 2 (fetch-error telemetry): the previously-empty catch now classifies the caught error via
  `classifyDirectReadFetchError` and surfaces it. Attempt telemetry is set BEFORE the enriched call so a
  failure can never again read as "never triggered". New meta/scorecard/Run-Trace fields:
  `direct_read_fetch_attempted` (bool), `direct_read_fetch_error` (timeout | max_buffer | process_error |
  unknown | null), `direct_read_fetch_arg_count` (fetchable target count), `direct_read_fetch_timeout_ms`.
- Secondary bug found + fixed: a maxBuffer overflow raises BOTH `code='ENOBUFS'` AND `signal='SIGTERM'`;
  the classifier now checks the definitive ENOBUFS/maxBuffer signal BEFORE the SIGTERM timeout branch so
  an overflow is not misclassified as a timeout (a real timeout is ETIMEDOUT+SIGTERM with no ENOBUFS).
- Trigger hardening: the `index_gap_detected === true` condition is coercion-hardened to also accept the
  string 'true', so no upstream serialization can silently defeat the strict-equality trigger.
- Honest-gap invariant preserved: the golden 8th target is a non-fetchable `symbol:`; the fallback resolves
  all 7 fetchable paths (recalled=7) and leaves exactly the symbol missing -- it never fabricates symbol
  resolution. arg_count (7) therefore equals the fetchable target count, not the total (8).
- Version: mechanical LIVE-surface bump 0.3.32 -> 0.3.33 (`package.json`, `EXTENSION_VERSION`, README header,
  every LIVE 0.3.32 assertion in `tests/verify_extension_contract.js` incl. target-snippet content checks).
  Historical annotations untouched.
- Tests: DRT-001..DRT-008 in `tests/verify_extension_contract.js` - classifier ordering (ENOBUFS+SIGTERM =>
  max_buffer); default + error telemetry through meta/scorecard/formatter; regression guard on the >=8MB
  buffer floor and the removed 144KB constant; END-TO-END trigger via `holoIndexOutput` on the golden prompt
  proving direct_read_fetch_attempted=true + direct_read_fallback_used=true + 7 fetchable paths under the
  raised buffer; a real 4KB-buffer overflow simulation classifying as max_buffer; continuation-independence
  (fetch fires identically with/without a trailing continuation block); golden 8-target contract (total 8,
  arg pairs 7). Full node suite PASS on 0.3.33. Python `test_reddog_extension_bundle_recall.py`: 15 pass;
  the 2 `*_top_hits_/_recall` lexical-ranking failures are PRE-EXISTING on the #911 base (reproduced with all
  changes stashed) and out of scope for this slice.
- Stacked on REDDOG_CONTINUATION_TOGGLE_HARDENING_PHASE1 (#911). No continuation change here; the direct-read
  trigger reads only the required-target list + bundle recall and is independent of the continuation toggle.
- Out of scope (unchanged): no new file-write authority; no Python fetch/allowlist change (that is #910); no
  redaction policy change; no continuation change (that is #911).

WSP: WSP_22, WSP_50, WSP_97.

## 2026-07-02 - REDDOG_CONTINUATION_TOGGLE_HARDENING_PHASE1 (deterministic Use-last-packet toggle + telemetry, 0.3.32)

- Problem (012-observed): 012 unchecked "Use last RedDog packet" but Copy MD still emitted the
  "Continuation from last RedDog packet" block. Two independent defects in landed 0.3.31 `extension.js`:
  1. Backend default too permissive: `const useLastPacket = message.useLastPacket !== false` defaulted
     ON unless the field was exactly `false` (missing/stale field => ON).
  2. Copy MD continuation append was gated only on `ctx.continuationSummary` EXISTING, not on the toggle;
     and the summary is always built + stored, so even a correct `false` would not strip Copy MD.
- Fix (fail-closed): continuation is included THIS run ONLY when `message.useLastPacket === true`.
  Single boolean `continuationEnabled` drives both append sites. `continuationAppended = continuationEnabled
  && !!state.lastContinuationSummary`. Missing/stale toggle => OFF (a stale packet no longer contaminates
  redaction or acceptance scoring).
- Both append sites now gated on the toggle: the model-prompt append (`appendContinuationSummaryToWspPrompt`)
  and the Copy MD append (`buildContinuationSummaryCopySection`, now requires `ctx.continuationEnabled`).
  Building/storing the summary for the NEXT run is unchanged; only INCLUDING it this run is gated.
- Telemetry (Run Trace + Copy MD "## Continuation Telemetry"): `continuation_enabled`, `continuation_appended`,
  `continuation_source_run_id` (`run_xxx` when appended, else `none`). New helpers:
  `normalizeContinuationTelemetry`, `formatContinuationTelemetryLines`, `buildContinuationTelemetrySection`.
- UI: when disabled, webview shows status line "Continuation: disabled for this run." (frontend on send +
  backend on assemble).
- Version: mechanical LIVE-surface bump 0.3.31 -> 0.3.32 (`package.json`, `EXTENSION_VERSION`, README header,
  every LIVE 0.3.31 assertion in `tests/verify_extension_contract.js` incl. target-snippet content checks).
  Historical `vX.Y.Z` annotations untouched.
- Tests: ADDENDUM H in `tests/verify_extension_contract.js` - enabled+stored => appended (prompt + Copy MD)
  with `continuation_appended=true`; disabled+stored => NOT appended with `continuation_enabled=false`;
  missing toggle => fail-closed NOT appended; telemetry fields present in Run Trace + Copy MD. Full suite PASS.
- Out of scope (unchanged): no model/routing/redaction policy change; no direct-read fallback change; no
  cross-session memory; no mid-run steering.

WSP: WSP_22, WSP_50, WSP_97.

## 2026-07-02 - Version bump to 0.3.31 (REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3)

- Mechanical build-label bump 0.3.30 -> 0.3.31 across LIVE version surfaces.
- Surfaces: `package.json`, `extension.js` (`EXTENSION_VERSION`), `README.md` header,
  `tests/verify_extension_contract.js` LIVE-version assertions.

WSP: WSP_22.

## 2026-07-01 - REDDOG_AUDIT_MODE_REDACTION_PHASE1 (slice 3/3, structure-preserving redaction)

- Files: `modules/communication/moltbot_bridge/src/fusion_redaction_gate.py` (audit_mode + structural
  categories + audit value redactors), `.../src/fusion_alias_live.py` (`audit_context` param),
  `extensions/foundups_advisory_workers/extension.js` (`buildDirectReadContentSection` surfaces
  `audit_context=true` when slice-2 direct-read fetched required governance targets).
- Goal: fix the FoundUp-creation over-sanitization -- `source_authority`, `merge_authorization`,
  `cabr_payout_authority`, `governance_instruction` matched on the bare identifier and BLOCKED the whole
  fetched payload, hiding the enum members / field names / gate ordering a governance audit must read.
- Value-vs-structure line: audit_mode PRESERVES identifiers (enum members `SourceAuthority.MONOREPO_POC`,
  field names, `CANONICAL_ACTIONS` incl. `build_foundup`/`extract_foundup`, valve gate names, WSP refs)
  and STILL REDACTS every secret VALUE / payout AMOUNT / authorization TOKEN / private_reasoning free-text.
- SAFETY: audit_mode never relaxes `private_reasoning`, `private_key_residual`, or any REDACT category.
  Fake `sk-...` key / OAuth token / payout amount / merge token remain `[REDACTED]` in audit mode.
- Trigger: OFF by default (backward compatible; non-audit path byte-identical). ON only for audit-context
  retrieval (direct-read of required targets). No detector/fetch/allowlist change; no execution/write/shell.
- Tests: 14 audit-mode unit tests in `modules/communication/moltbot_bridge/tests/test_fusion_redaction_gate.py`
  (79/79 pass); DRF-008 (structure readable in audit mode) + DRF-009 (secret STILL redacted) in
  `tests/verify_extension_contract.js`. INTERFACE truth-boundary rows 27-32 added (32/32 YES).

## 2026-07-02 - Version bump to 0.3.30 (REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1, slice 2/3)

- Mechanical build-label bump 0.3.29 -> 0.3.30 across LIVE version surfaces.
- Surfaces: `package.json`, `extension.js` (`EXTENSION_VERSION`), `README.md` header,
  `tests/verify_extension_contract.js` LIVE-version assertions.

WSP: WSP_22.

## 2026-07-02 - Version bump to 0.3.29 (REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1, slice 1/3)

- Mechanical build-label bump 0.3.28 -> 0.3.29 across LIVE version surfaces so an installed
  host does not stay stale on this senses-spine slice. No runtime logic change.
- Surfaces: `package.json`, `extension.js` (`EXTENSION_VERSION`), `README.md` header,
  `tests/verify_extension_contract.js` LIVE-version assertions.

WSP: WSP_22.

## 2026-07-01 - REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3, governed fetch)

- Files: `holo_index/cli/commands/bundle_json.py` (fetch + hard allowlist), `holo_index/_cli_main.py`
  (`--bundle-must-include`), `extensions/foundups_advisory_workers/extension.js` (request paths + telemetry).
- Goal: when slice-1's detector reports `index_gap_detected=true` and the prompt named required targets absent
  from the bundle, FETCH those exact files' content so RedDog reasons on real source instead of HOLDing blind.
- Architecture: the FETCH lives in the PYTHON bundle layer (`_direct_read_fetch`); the extension only REQUESTS
  must-include paths via `--bundle-must-include` (no raw fs in extension.js, no shell-out, no model/router change).
  Fetched hits are spliced into `task_retrieval.code_hits`; slice-1's `evaluateTargetRecall` re-runs so
  `target_recall_ok` / `required_targets_recalled` reflect the now-present content.
- HARD security allowlist (WSP_50): repo-relative only; realpath must stay inside repo root (rejects absolute,
  `..` traversal, symlink-escape); hard-deny `.env*`, `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `*.p12`,
  `*.keystore`, `*secret*`/`*credential*`/`*token*`, `.git/` and credential dot-dirs; per-file byte cap (12KB)
  plus total fetch budget (96KB) spread across MANY targets (ranked by prompt order) so no single file starves
  the rest; every rejection recorded and never aborts the bundle.
- Telemetry: `direct_read_fallback_used`, `direct_read_paths`, `direct_read_rejected` (`{path, reason}`),
  `direct_read_bytes`, `direct_read_truncated` (`{path, bytes}`) added to the Run Trace scorecard.
- Boundary: NO redaction-category change and NO audit-mode change (slice 3). Fetched content passes through the
  EXISTING redaction gate unchanged (governance content may still be over-sanitized until slice 3 - expected).
  NO execution authority, NO write capability, NO shell-out added.
- Acceptance (slice-2 bar): on the FoundUp-creation required-target list against a bundle lacking them, the
  targets (WSP_109, openclaw_foundup_orchestrator, hermes_foundup_job_executor, foundup_job_contract,
  reddog_governed_work_order_dryrun, reddog_wre_execution_valve, source_authority) are fetched + present,
  `direct_read_fallback_used=true`, `target_recall_ok=true`.
- Tests: `holo_index/tests/test_reddog_extension_bundle_recall.py` (deny-gate unit, real-target fetch,
  recall-flip via node, traversal/absolute/secret-fixture/symlink-escape rejection, per-file cap + total budget
  spread, CLI end-to-end) + `tests/verify_extension_contract.js` (DRF-001..007 incl. slice-boundary proof that
  the existing redaction gate STILL blocks governance content, unchanged).
- Stacked on slice 1 (#906). WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.


## 2026-07-01 - REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1 (slice 1/3, detector only)

- File: `extensions/foundups_advisory_workers/extension.js`
- Problem: on the FoundUp-creation audit run, the run trace reported `index_gap_detected: false` even though
  none of the 20+ required direct-read targets were retrieved. The only retrieved file was `extension.js`
  (RedDog itself), and that "content included" falsely satisfied the recall check
  (`content_included(any file) != required_targets_recalled`).
- Fix (detector only): `parseRequiredTargetPaths()` parses an explicit "Required direct-read targets" prompt
  list into repo-relative paths/globs; `evaluateTargetRecall()` now compares that list against content-bearing
  bundle locations, with a self-file guard (`isSelfFileLocation()`) so retrieving `extension.js` never counts.
- New truthful scorecard/telemetry fields: `required_targets_total`, `required_targets_recalled`,
  `required_targets_missing`, honest `target_recall_ok` and `index_gap_detected`
  (never `unknown` when a required list exists).
- Backward compatible: prompts with no required-target list preserve prior inferred-target behavior.
- No file-read added (slice 2), no redaction-category change (slice 3). Advisory boundary preserved.
- Tests: `holo_index/tests/test_reddog_extension_bundle_recall.py` (4 new: 0/N gap, self-file guard, all-present,
  backward-compat) + `tests/verify_extension_contract.js` (TRP-001..007 scorecard vocabulary).

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1 (extension pointers)

- Module: `modules/communication/moltbot_bridge/src/reddog_openclaw_adapter_dryrun.py`
- `plan_reddog_openclaw_adapter_dryrun()` -- propose FoundUpJob / autonomous_task intake; no enqueue.
- Contract: `docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md`

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WRE_EXECUTION_VALVE_PHASE1 (extension pointers)

- Module: `modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py`
- `evaluate_reddog_execution_valve()` -- closed-by-default; pure evaluation only.
- Contract: `docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md`

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1 (LANDED #901)

- Canonical: `docs/audits/architecture/REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md`
- Ruling: OpenClaw Supervisor / FoundUpJob intake is canonical; AssignmentDispatcher is simulated scaffold only.
- No runtime adapter in this slice.

WSP: WSP_00, WSP_15, WSP_50, WSP_77, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1 (LANDED #899)

- ADD `buildSanitizedContinuationSummary()` — WSP_97-safe packet memory from last run (success or BLOCKED_LOCALLY).
- ADD `appendContinuationSummaryToWspPrompt()` — follow-up path without pasting raw Copy MD.
- UI: "Use last RedDog packet" checkbox (default ON); in-memory `state.lastContinuationSummary` only.
- Copy MD optional safe Continuation Summary section; fusion redaction gate tested on continuation block.

WSP: WSP_00, WSP_50, WSP_97, WSP_22. Version 0.3.27 -> 0.3.28.

## 2026-06-28 - REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1 (extension pointers)

- Module: `modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py`
- `plan_wre_isolated_worktree_execution_dryrun()` — plan + phase receipts; no git/worktree mutation.

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1 (audit doc)

- Canonical: `docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md`
- Defines executor cage: entry conditions, isolation, mutation bounds, rollback, output contract.
- No runtime implementation in this slice.

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1 (extension pointers)

- Points to `modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py`.
- Chains #893 policy gate + #894 receipt; proves handoff without repo mutation.

WSP: WSP_34, WSP_50, WSP_97.

## 2026-06-28 - REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1 (extension pointers)

- Points to `modules/communication/moltbot_bridge/src/reddog_work_order_receipt.py`.
- Pre-execution audit trail from #893 `PolicyGateReceipt`; Hermes-compatible, not live queue.

WSP: WSP_34, WSP_50, WSP_91, WSP_97.

## 2026-06-28 - REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1 (extension pointers)

- Points to `modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py`.
- Policy gate composes #890 dry-run + #892 permission snapshot freshness; Hermes-shaped receipt; no execution.

WSP: WSP_34, WSP_50, WSP_97.

## 2026-06-28 - REDDOG_GITHUB_PERMISSION_PROBE_PHASE1 (extension pointers)

- Points to `modules/platform_integration/github_integration/src/reddog_github_permission_probe.py`.
- Read-only snapshot feeds `repo_permission_snapshot` for future work-order emission.

WSP: WSP_34, WSP_50, WSP_97.

## 2026-06-28 - #890 LANDED + post-dryrun queue revision

- **#890 merged** @ `bd68ab83a` — `validate_work_order_dryrun()` pure validation module.
- P0 sequence: GitHub permission probe → OpenClaw policy gate → Hermes receipts → WRE executor.

WSP: WSP_15, WSP_22.

## 2026-06-28 - REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1

- Added `reddog_governed_work_order_dryrun.py` — typed `RedDogGovernedWorkOrder` + `HoloIndexEvidencePacket` dry-run validator.
- Decisions: `WOULD_ACCEPT`, `WOULD_REJECT`, `WOULD_ACCEPT_WITH_RETRIEVAL_GAP`; receipt digest; in-memory nonce replay guard.
- Gates: required fields, expiry, nonce, forbidden ops/paths, main mutation block, HoloIndex evidence (Addendum A), WAE-L1 mapping docstring (Addendum B).
- Tests: 13 pytest cases (accept + all rejection paths).
- No GitHub, branch, PR, write, shell, or merge calls.

WSP: WSP_34, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1

- Added `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md` — authority model, `RedDogGovernedWorkOrder` schema, HoloIndex discoverability + reindex gate.
- Updated ROADMAP queue: contract DONE; P0 dryrun + GitHub probe + OpenClaw gate + WRE executor.
- README/INTERFACE: governed work-order contract pointers; authenticated principal wording; F0 merge SPECIFIED_NOT_IMPLEMENTED.
- HoloIndex: baseline Phase 0 + targeted `--index-docs` post-edit (Addendum C).
- No extension runtime, bridge, or HoloIndex ranking code changes.

WSP: WSP_00, WSP_34, WSP_50, WSP_54, WSP_95, WSP_97, WSP_109, WSP_22.

## 2026-06-27 - #888 LANDED + external lane queue revision (v0.3.27)

- **#888 merged** to `main` @ `9c3a8f829`; 012 smoke PASS (schema repair minimal path, `output_validation: passed`).
- **Queue revised:** P0 next is `REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1` (docs/audit authority model).
- P1: sanitized-target provenance, Run Trace telemetry correction.
- P2: governed work-order dryrun (after contract).
- Stale `provider_reasoning_note` tracked under telemetry slice, not #888.

WSP: WSP_15, WSP_22.

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1 addendum (v0.3.27)

- Run Trace always emits `repair_context_mode` / `repair_mode` when `repair_attempted`.
- Dedicated repair Work Trail mapping (`repair_single_started`, no `panel_started` after repair).
- `extractMarkdownSection` + section-aware `mergeRepairedOutput(..., missingSections)`.
- Repair prompt lists required `## Section` headers explicitly; repair `max_tokens: 2400`.
- Contract tests OSR-007..OSR-010 (smoke-missing tail sections).
- Version bump 0.3.26 -> 0.3.27.

WSP: WSP_97, WSP_22.

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1 (v0.3.26)

- Repair pass uses `buildRepairBoundedContext()` (minimal WSP contract; no HoloIndex resend).
- Repair routes `openrouter_single` with sanitized draft via `sanitizeTargetSnippetForRedaction`.
- `mergeRepairedOutput()` appends schema supplement to primary Fusion output.
- Run Trace: `repair_context_mode`, `repair_mode` on validation state.
- Contract tests OSR-001..OSR-006.
- Version bump 0.3.25 -> 0.3.26.

WSP: WSP_97, WSP_22, WSP_84.

## 2026-06-14 - ADDENDUM B bridge UTF-8 stdin invariant (v0.3.25)

- **Problem:** Valid U+2014 em dash in HoloIndex context passed JS normalization but Windows Python text stdin mis-decoded UTF-8 to surrogate `\udc94`, causing `redactor_error` at digest.
- **`scripts/advisory_model_once.py`:** `_read_stdin_json()` reads `sys.stdin.buffer` as UTF-8 (`errors="replace"`).
- **`extension.js`:** `buildBridgePythonEnv()` sets `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1` on bridge child.
- Tests UNI-008..UNI-010; Python `test_main_em_dash_utf8_stdin_not_redactor_error`.
- Prior surrogate normalization (Addendum A / UNI-001..007) unchanged.
- Version bump 0.3.24 -> 0.3.25.

WSP: WSP_00, WSP_97, WSP_22, WSP_84.

## 2026-06-14 - REDDOG_CONTEXT_UNICODE_NORMALIZATION_PHASE1 (v0.3.24)

- Added `normalizeBridgeTextForUnicode()` to replace isolated UTF-16 surrogates with `[MALFORMED_SURROGATE]` and apply NFC before bridge/redaction gate.
- Wired normalization in `callFusion` for WSP task prompt, bounded context, and repair prompt (`repair_prompt` source label).
- Run Trace / review packet: `unicode_normalization_applied`, `unicode_replacements_count`, `unicode_normalization_sources`, `unicode_normalization_form`.
- Contract tests UNI-001..UNI-007; fixtures `MALFORMED_UNICODE_CONTEXT`, `BLOCKED_POLICY_CONTEXT`.
- `fusion_redaction_gate.py` unchanged; policy not weakened.
- Version bump 0.3.23 -> 0.3.24.

WSP: WSP_00, WSP_15, WSP_97, WSP_22, WSP_84.

## 2026-06-14 - REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1 (v0.3.23)

- REGULAR auto context: `none` -> `wsp_holo` (HoloIndex bundle-json; no Skillz/git/Fusion panel).
- Updated `modeSelectionReasoning` for REGULAR: cites HoloIndex-grounded wsp_holo.
- Contract tests THG-001..006; fixtures `REGULAR_SMOKE_PROMPT`.
- Preserved #883 target content + TCI-001..TCI-010 + ADDENDUM F gate tests.
- Version bump 0.3.22 -> 0.3.23.

WSP: WSP_00, WSP_15, WSP_87, WSP_97, WSP_22.

## 2026-06-14 - ADDENDUM F redaction-safe target snippets (v0.3.22)

- Raw `extension.js` snippets tripped Fusion BLOCK categories (`governance_instruction`, `private_reasoning`, etc.) before OpenRouter.
- Added `sanitizeTargetSnippetForRedaction()` mirroring `fusion_redaction_gate.py` BLOCK detectors; neutral `[SANITIZED_BLOCK:NN]` placeholders (category names in metadata only).
- Run Trace: `target_content_sanitized`, `target_content_sanitized_categories`.
- Contract tests TCI-009/TCI-010: Python gate probe on EXT-ACC-001 bounded context (no OpenRouter).
- `fusion_redaction_gate.py` unchanged.

WSP: WSP_97, WSP_22, WSP_84.

## 2026-06-14 - REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1 (v0.3.22)

- Added workspace-confined target snippet readers: `readBoundedTargetSnippet`, `buildTargetRecallContentSection`, `buildWsp97ProtocolExcerpt`.
- Wired `buildBoundedRepoContext` to egress `### Target recall content` after HoloIndex bundle-json (before Skillz noise).
- WSP_97 tasks append bounded `### WSP protocol excerpt (bounded)` from `WSP_97_System_Execution_Prompting_Protocol.md`.
- Run Trace scorecard: `target_content_included`, `target_content_paths`, `target_content_chars`, `target_content_omitted_reason`, `target_content_truncated`.
- Path safety rejects absolute paths, `..`, `.git`, `node_modules`, `.env`, `.vsix`; realpath confinement.
- ADDENDUM E contract tests: inferRecallTargetPaths, snippet inclusion, buildBoundedRepoContext integration, path denial (no OpenRouter).
- Shared fixtures: `tests/fixtures.js`; TEST_REGISTRY TCI-001..008 in `tests/TestModLog.md`; `tests/README.md` for reuse policy.
- Version bump 0.3.21 -> 0.3.22 (install hygiene).

WSP: WSP_00, WSP_15, WSP_87, WSP_97, WSP_22, WSP_84.

## 2026-06-26 - REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1 (docs)
- Added `docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`: 15-prompt pack, 012 rubric, runbook, WSP_97 truth rows, baseline vs replacement pass.
- Added `docs/acceptance/README.md` artifact storage rules.
- HoloIndex Phase 0: INDEX_GAP for extension.js and advisory_model_once.py retrieval.
- No runtime behavior changes; external lane scoreboard only.

WSP: WSP_00, WSP_15, WSP_87, WSP_97, WSP_22.

## 2026-06-26 - Content inclusion prompt REQUEST_CHANGES resolved

- Architect addenda A-D merged into `.prompt_reddog_context_target_content_inclusion_phase1.md`
- ASCII clean dispatch; MOJIBAKE validation via `MOJIBAKE_MARKERS` export not embedded chars
- Workspace-confined read safety + final-context telemetry + test exports specified
- Status: **APPROVE_WORKER_DISPATCH** (architect) pending worker implementation

WSP: WSP_97, WSP_22.

## 2026-06-26 - REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION worker prompt (review)

- Worker prompt: `.prompt_reddog_context_target_content_inclusion_phase1.md`
- Queued from EXT-ACC-001 evidence: path hit, no source content in bounded context.
- Version bump 0.3.22 planned in slice (install hygiene).

WSP: WSP_97, WSP_22.

## 2026-06-26 - EXT-ACC-001 post-#882 probe r3 (telemetry gate still open)

- Same path-only signal as r2; repair redaction passed (r2 repair blocked).
- Run Trace still `v0.3.20` — force-install did not reflect in host; telemetry gate open.
- Queue content inclusion; hold dispatch until `target_recall_ok` appears in Run Trace.

WSP: WSP_97, WSP_22.

## 2026-06-26 - Install trap: header 0.3.21 vs stale host (docs)

- **OBSERVED:** Cursor header `Build: 0.3.21` while installed `extension.js` had `v0.3.20` provider note and no #882 telemetry.
- **Cause:** #882 landed without version bump beyond `0.3.21`; force VSIX install required.
- **Runbook:** Preflight requires Run Trace internals, not header alone.

WSP: WSP_97, WSP_22.

## 2026-06-26 - EXT-ACC-001 post-#882 probe r2 (needs_repair, stale telemetry)

- Main egress succeeded; RedDog correctly BLOCKed on missing source (path hit ~7.4%, no content body).
- **Queue** `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1` — do **not** treat as final post-#882 proof (v0.3.20 note; no `target_recall_ok` / `code_hits_count`).
- **Pending:** Clean EXT-ACC-001 after force-install VSIX; then dispatch content-inclusion if criterion #2 still fails with telemetry active.

WSP: WSP_97, WSP_22.

## 2026-06-26 - EXT-ACC-001 post-#882 probe recorded (blocked)

- **Verdict:** `blocked` — `redactor_error` before OpenRouter; HoloIndex fix not assessable at model layer.
- **Distinction:** `redactor_error` (gate scan error, fail-closed) ≠ `blocked_policy` (intentional policy block).
- **Next slice (P0):** `REDDOG_REDACTION_GATE_CONTEXT_ERROR_DIAGNOSTIC_PHASE1` — before `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1`.
- **Pending:** EXT-ACC-003 post-#882 probe (confirms context bundle vs work focus if same error).
- **Note:** Trace showed `v0.3.20` provider note — reinstall post-#882 VSIX before reruns.

WSP: WSP_97, WSP_22.

## 2026-06-26 - Post-#882 acceptance criteria update (docs)

- Updated `REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`: EXT-ACC-001 replacement pass requires five criteria (path hit, source content in bounded context, WSP_97 finding on source, `target_recall_ok`, output validation).
- Documented path-ranking vs content-inclusion distinction; post-#882 probe order (001 + 003 only before full 15-pack).
- Recorded conditional follow-on `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1` — do not start until post-land probe proves path-only context.

WSP: WSP_97, WSP_22.

## 2026-06-26 - HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1 (worker slice)

**Problem (OBSERVED):** EXT-ACC-001 showed `bundle_json_ok` + `code_hits=5` but `extension.js` not retrieved; `index_gap_detected` falsely reported `false`.

**Root causes (OBSERVED):**
- `bundle_json.py` path fallback `allowed_ext` excluded `.js`.
- RedDog NAVIGATION recall keys were appended to `DAE_ARCHITECTURE` instead of `NEED_TO`.
- `holoIndexMetaFromBundle()` inferred gap from structured memory / zero WSP hits, not target path recall.

**Fixes (IMPLEMENTED):**
- Added `.js` to lexical path fallback; filename token + NEED_TO exact/substring scoring boosts.
- Moved RedDog keys into `NEED_TO`; added `HOLOINDEX.md` manifest.
- Added `inferRecallTargetPaths()`, `evaluateTargetRecall()`, `target_recall_ok`, `code_hits_count` scorecard fields.
- Regression tests: `holo_index/tests/test_reddog_extension_bundle_recall.py`; contract tests updated.

**Architect review packet:** `docs/REDDOG_HOLOINDEX_INDEX_GAP_ARCHITECT_REVIEW_PHASE1.md`

WSP: WSP_50, WSP_84, WSP_87, WSP_97.

## 2026-06-25 - v0.3.21 Blocked RedDog Copy MD polish
- Adjacent duplicate Work Trail events collapse to one entry (detail-bearing event retained).
- Redaction-block-only runs use conservative Governed Handoff defaults: `handoff_needed: unknown`, `reason: blocked_context_needs_local_0102_review`, `wsp15_priority: P1`, `suggested_slice_name: none`.
- Target may remain `[INFERRED]` from work focus; no automatic WRE dispatch assertion on blocked-local packets.

WSP: WSP_22, WSP_97.

## 2026-06-24 - v0.3.20 Redaction Gate Report + WRE Handoff Readiness (Addendum F)
- Rebased onto #871 bridge hardening (`9e5416af4`); version bump 0.3.19 -> 0.3.20.
- Copy MD redaction blocks now include `## Redaction Gate Report` with WSP_97 truth labels (OBSERVED/UNKNOWN); no raw blocked content.
- Required fields: `BLOCKED_LOCALLY`, `made_network_call: false`, `blocked_stage: pre_openrouter_request`, `blocked_payload_part: unknown` when gate cannot identify part, `raw_snippets_included: false`, bounded digest, safe summary, `next_safe_context`.
- Substantive tasks append `## Governed Handoff Recommendation` (`advisory_only`, bounded evidence refs, WSP_15 priority inference).
- Copy MD Work Trail: allowlisted normalized events (cap 50), `sanitizeCopyMdText` for secret-adjacent phrases.
- Run Trace: dual effort (`reddog_effort` + provider reasoning report-only); HoloIndex recall scorecard when bundle context used.

WSP: WSP_22, WSP_97, WSP_15.

## 2026-06-24 - v0.3.19 RedDog UX + Review Packet Polish
- Moved Working Tail strip above controls row (output → trail → 0102 Role/controls → 012 work focus).
- Renamed UI label `Worker` → `0102 Role`; role options unchanged.
- Copy MD now prepends `Run Trace` (role, tier, effort, mode, models, context, redaction, validation).
- Redaction-block and repair-failure Copy MD include `BLOCKED_LOCALLY` / `OUTPUT_VALIDATION_FAILED` with explicit incomplete-advisory wording.
- Added mojibake detector (`窶`, `竊`) with `mojibake_detected` flag in output_validation and Copy MD warning.
- Validation repair failure appends local static footer (Verification Gaps + Next safest step); no extra network call.

WSP: WSP_22, WSP_97.

## 2026-06-24 - v0.3.18 Foundups®Agent Branding
- Renamed user-facing extension surface from "FoundUps Fusion Worker" to "Foundups®Agent".
- Kept internal package id and command id stable (`foundups-fusion-worker`, `foundupsFusion.open`) to avoid breaking existing installs/settings.
- Clarified that RedDog is the 0102 digital-twin architect inside Foundups®Agent and Fusion is an internal reasoning mode.

## V0.3.17 窶・REDDOG_WORKING_TRAIL_PHASE1_CODE 窶・2026-06-23

- Implemented RedDog working trail strip (`#reddogWorkingTrail`) under work focus composer.
- ASCII pixel grammar: `~~~`, `.rd.`, `<rd>`, `>rd>`, `!rd!`.
- Structured progress: host posts `{ command: 'progress', stage, text }`; scrollback uses `{ command: 'status', text }` unchanged.
- `REDDOG_STAGE_ACTIONS` covers all 16 unique `advisory_model_once.py` bridge stages; regex fallback for webview-local events.
- Elapsed timer (1s), 10s no-event sitting fallback, idle pixel cycle while running, terminal hold 3000ms.
- Redaction-block UX: operator message, `made_network_call=false`, `retry_count=0`; no raw blocked content in scrollback.
- `advisory_model_once.py` unchanged (Phase 3 review-packet summary deferred).

WSP: WSP_22, WSP_97.

## 2026-06-23 - REDDOG_RECURSIVE_DAE_ECOSYSTEM_ARCHITECTURE_PHASE1

Audit and doc additions for correct FoundUps architecture capture:

- Added "RedDog and the Recursive 0102 DAE Ecosystem" section to README.md, INTERFACE.md, ROADMAP.md.
- Architecture stack: 012 -> RedDog digital twin / architect -> recursive 0102 DAE ecosystem.
- Layer roles table: RedDog, Hermes, OpenClaw, HoloIndex, Skillz/Rolodex, Autonomous WRE/DAE agents, Sentinels, WRE, CABR/pAVS, 012.
- Key correction documented: Autonomous WRE/DAE agents are NOT 012 work. 012 provides work focus, testing, sovereign approval, and override.
- Added WSP_97 truth table rows: REDDOG_IS_ARCHITECT_INTERFACE, AUTONOMOUS_DAE_WORK_NOT_012_WORK, HERMES_IS_SCAFFOLDING_NOT_POLICY, OPENCLAW_IS_POLICY_GATE, WRE_RETAINS_REPO_AUTHORITY, SENTINELS_REVIEW_NOT_EXECUTE, CABR_PAVS_VALIDATES_BENEFIT, EXTENSION_REMAINS_ADVISORY_ONLY.
- HoloIndex Phase 0 retrieval audit complete (4 queries, all PASS, INDEX_GAP noted for extension.js/advisory_model_once.py).

WSP: WSP_00, WSP_48, WSP_54, WSP_73, WSP_97.

## V0.3.17b 窶・REDDOG_WORKING_TRAIL_PHASE1_REPAIR 窶・2026-06-23

- Repair pass on docs/REDDOG_WORKING_TRAIL_PHASE1.md.
- ASCII pixel grammar: replaced `.v.`, `xvx`, `!v!`, `IvI` Unicode glyphs with `.rd.`, `<rd>`, `!rd!`, `>rd>` throughout (tables, code blocks, prose, JS signatures, CSS). Zero non-ASCII confirmed by rg scan.
- Phase 2/3 split: clarified Phase 2 = extension.js only (~123 lines, no advisory_model_once.py); Phase 3 = bounded working_trail_summary / review event emission. Renamed "training events" to `working_trail_events` / `trail telemetry` in Phase 2 scope.
- Terminal state hold: corrected `setRunning(false)` contract -- terminal states (`>rd>`, `!rd!`) held >=3s via `setTimeout(3000)` before idle reset; immediate reset removed.
- Structured stage first: Section 2 now specifies stage-field primary match (advisory_model_once.py emits `_progress(stage, text)` confirmed); text regex is fallback only.
- Resolved Open Questions (Section 10): Q1=review-packet append, Q2=ASCII-safe Phase 2, Q3=continue elapsed; removed as open questions.
- WSP_97 expanded from 10 to 16 rows (items 11-16: MOJIBAKE_FREE, ASCII_PIXEL_FALLBACK, PHASE2_EXTENSION_ONLY, TRAINING_EVENTS_DEFERRED, TERMINAL_STATE_VISIBLE, STRUCTURED_STAGE_FIRST).

WSP: WSP_22, WSP_97.

## V0.3.17 - REDDOG_WORKING_TRAIL_PHASE1 (Design Contract) - 2026-06-23

- Authored design contract for RedDog working trail (docs/REDDOG_WORKING_TRAIL_PHASE1.md).
- Defines UI contract (`reddogWorkingTrail` strip), event-to-action mapping for all 16 bridge progress events, JSONL training schema, and WSP_97 truth boundary checklist.
- Phase 1: design only. Phase 2 implements extension.js trail strip + elapsed timer; advisory_model_once.py unchanged in Phase 2.
- WSP_97 N/10 (all 10 truth boundary items PASS per design).

WSP: WSP_22, WSP_97, WSP_15.

## 2026-06-22 - REDDOG_BRIDGE_HARDENING_PHASE1 (v0.3.16)

- Python resolver chain: configured -> .venv/venv -> system fallback; reports interpreter in bridge_meta.
- Subprocess stdout/stderr caps with kill-on-exceed and output_cap_exceeded reason.
- Webview dispose kills in-flight bridge child (orphan cleanup).
- Context/prompt char budget before bridge; truncation_applied + truncation_reason in review packet.
- advisory_model_once: panel_models cap 6; HTTP retry only on 429/502/503 (max 2); same redacted body; retry metadata in packet.
- Failure taxonomy: redaction_blocked, missing_key, timeout, retry_exhausted, http_error, malformed_response, subprocess_failed, output_cap_exceeded.
- Added scripts/tests/test_advisory_model_once_hardening.py for retry invariants.

WSP: WSP_97, WSP_87.

## 2026-06-22 - Addendum A Gate Precision (#870 pre-land)

- Verified exact scope: 8 extension-local files only; `scripts/advisory_model_once.py` unchanged.
- Strengthened contract tests: WSP_00/97/15 non-vacuity, raw-focus bypass guard, digest boundedness.
- Added WSP_97 truth rows: WORK_FOCUS_NOT_AUTHORITY, WSP_PROMPT_0102_GENERATED, RAW_FOCUS_NOT_SENT_AS_SOLE_AUTHORITY, DIGESTS_NOT_RAW_CONTEXT, ROUTING_UNCHANGED_FROM_0_3_14.
- Recorded Addendum B bridge hardening controls in ROADMAP (next slice; not in #870).

## 2026-06-22 - REDDOG_WORK_FOCUS_TO_WSP_PROMPT_PHASE1 (v0.3.15)

- Renamed 012-facing UI language from "prompt" to **work focus** (composer, scrollback labels, placeholders).
- Added `constructWspTaskPrompt()` and `redactedDigest()` - 0102 assembles WSP task prompt from work focus before bridge call.
- Bridge now receives WSP task prompt, not raw composer text alone; classification/context still derived from work focus.
- Review packet adds `work_focus_digest`, `wsp_prompt_digest`, `prompt_construction: 0102_generated_from_work_focus`.
- HoloIndex Phase 0 (pre-edit): Q1/Q2 INDEX_GAP for extension.js; Q3 MEDIUM_SIGNAL; Q4 adjacent redaction gate hits.
- Preserved v0.3.14 auto-router, architect trace schema, and advisory-only boundary unchanged.

WSP: WSP_00, WSP_87, WSP_97.

## 2026-06-22 - HoloIndex Phase 0 / WSP_87 (REDDOG_ARCHITECT_AUTO_ROUTER_PHASE1)

Pre-edit retrieval audit (bundle-json; all four queries PASS, no offline fallback required):

| Query | Status | WSP | Code | Edit target | Classification |
| --- | --- | --- | --- | --- | --- |
| Q1 RedDog extension | PASS | 8 | 6 | `extension.js` **missed**; module README/INTERFACE in bundle | **INDEX_GAP** |
| Q2 Bridge/redaction | PASS | 8 | 5 | `advisory_model_once.py` **missed** | **INDEX_GAP** |
| Q3 Skillz/handoff | PASS | 8 | 8 | `video_comments/skillz/qwen_studio_engage` in docs; extension discovery unwired in index | **MEDIUM_SIGNAL** |
| Q4 WSP protocols | PASS | 8 | 8 | WSP_00/15/87/97 not top-ranked; RedDog briefings adjacent | **MEDIUM_SIGNAL** |

**WSP_97 finding (retrieval weakness):** HoloIndex bundle-json correctly resolved extension module memory (tier0_complete, README/INTERFACE present) but semantic code search returned adjacent routers (`fusion_adapter.py`, `wsp_adaptive_router_integration.py`) instead of `extensions/foundups_advisory_workers/extension.js` or `scripts/advisory_model_once.py`. Direct-read confirmed edit targets post-retrieval.

**Follow-up slice recorded:** `HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1` - index extension.js, advisory_model_once.py, and Skillz discovery paths for RedDog queries.

WSP: WSP_87, WSP_97.

## 2026-06-22 - REDDOG_AUTO_ROUTER_SKILLZ_CONTEXT_PHASE1 (v0.3.14)

- Changed RedDog defaults to GLM-5.2 principal, DeepSeek V4 Pro adversarial critic, and Kimi K2.7 Code implementation critic.
- Removed Mode/Effort/Context from the 012-facing prompt controls; routing and context now resolve automatically from WSP_15 task classification.
- Added bounded Skillz/Wardrobe/Rolodex/OpenClaw/Hermes discovery to HIGH/ULTRA context packets for governed handoff recommendations.
- Added visible `RedDog Routing` output and review-packet metadata for resolved effort, mode, context, principal, and panel.
- Wired Skillz/Wardrobe/Rolodex context into `buildBoundedRepoContext` for HIGH/ULTRA modes; ULTRA git diff now includes `wsp_holo_git_skillz`.
- Extended architect output schema: Architect Trace (structured CoR, not raw CoT), Verification gaps, mode-selection reasoning, Fusion panel structure validation.
- Added WSP_97 truth table to README/INTERFACE; recorded future slices in ROADMAP.
- Preserved advisory-only boundary: the extension can recommend handoffs but cannot execute Skillz, shell, OpenClaw, Hermes, repo, browser, merge, or deployment actions.
## 2026-06-22 - REDDOG_FUSION_ORCHESTRATOR_TRACKING_PHASE1 (git land)

- First tracked commit of `extensions/foundups_advisory_workers/` and `scripts/advisory_model_once.py`.
- VSIX remains a local build artifact only (`*.vsix` gitignored; package via `vsce package --no-dependencies`).
- No behavior change from v0.3.13 gate; discoverability/PR scope only.
- Explicit non-overlap: livechat #841 selective cancellation untouched.

WSP: WSP_22, WSP_49, WSP_97.

## 2026-06-22 - REDDOG_FUSION_ORCHESTRATOR_PHASE1 (v0.3.13)

- Added internal orchestrator contract in `extension.js`:
  - `classifyTaskForRedDog` WSP_15-style task classifier
  - `resolveAutoEffort` auto effort selection (ULTRA/HIGH/REGULAR)
  - `resolveModelMode` RedDog WSP default to auditable manual panel
  - `validateRedDogOutput` required schema section validator
  - `buildRepairPrompt` bounded one-pass repair helper
- Substantive RedDog answers now require WSP_97 Truth Labels in the output schema.
- On missing schema sections, run one repair pass through the existing redaction-gated bridge; attach validator/repair status to review packet.
- OpenRouter Fusion alias remains selectable but is not the RedDog WSP default.
- Extended contract tests in `tests/verify_extension_contract.js` (15 assertions including inject/revert classifier paths).

WSP: WSP_00, WSP_15, WSP_22, WSP_97, WSP_109.

## 2026-06-22 - RedDog Architect Webview Contract (v0.3.12)

- Reworked the Cursor webview into a VS Code terminal/chat-style surface:
  - compact header
  - scrollback output pane
  - fixed bottom composer
  - no separate status notices outside output
  - `Enter` sends and `Shift+Enter` inserts newline
- Added worker controls:
  - RedDog Architect
  - WSP Gate Critic
  - Repair Planner
  - Smoke Test
- Added effort controls:
  - Auto
  - Regular
  - High
  - Ultra
- Strengthened WSP operating prompt:
  - WSP_00 role/origin framing
  - WSP_97 truth labels
  - WSP_15 priority block at bottom
  - proposed fix required for every finding
  - HoloIndex retrieval weakness must become a remediation finding
- Changed HoloIndex context gathering to WSP_00 bundle-json first with `HOLO_SKIP_MODEL=1`, falling back to offline lexical only if bundle recall fails.
- Updated the bridge so prompt and bounded context are redaction-gated separately and the explicit RedDog system prompt reaches regular, Fusion alias, and manual panel modes.
- Added Tier-0/Tier-1 memory files for HoloIndex discoverability: `INTERFACE.md`, `ROADMAP.md`, `ModLog.md`, and `tests/TestModLog.md`.

WSP: WSP_00, WSP_15, WSP_22, WSP_87, WSP_97, WSP_109.
