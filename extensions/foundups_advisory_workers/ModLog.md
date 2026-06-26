# Foundups®Agent ModLog

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
