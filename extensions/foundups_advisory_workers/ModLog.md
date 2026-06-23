# FoundUps Fusion Worker ModLog

## V0.3.17b — REDDOG_WORKING_TRAIL_PHASE1_REPAIR — 2026-06-23

- Repair pass on docs/REDDOG_WORKING_TRAIL_PHASE1.md.
- ASCII pixel grammar: replaced `.v.`, `xvx`, `!v!`, `IvI` Unicode glyphs with `.rd.`, `<rd>`, `!rd!`, `>rd>` throughout (tables, code blocks, prose, JS signatures, CSS). Zero non-ASCII confirmed by rg scan.
- Phase 2/3 split: clarified Phase 2 = extension.js only (~123 lines, no advisory_model_once.py); Phase 3 = bounded working_trail_summary / review event emission. Renamed "training events" to `working_trail_events` / `trail telemetry` in Phase 2 scope.
- Terminal state hold: corrected `setRunning(false)` contract -- terminal states (`>rd>`, `!rd!`) held >=3s via `setTimeout(3000)` before idle reset; immediate reset removed.
- Structured stage first: Section 2 now specifies stage-field primary match (advisory_model_once.py emits `_progress(stage, text)` confirmed); text regex is fallback only.
- Resolved Open Questions (Section 10): Q1=review-packet append, Q2=ASCII-safe Phase 2, Q3=continue elapsed; removed as open questions.
- WSP_97 expanded from 10 to 16 rows (items 11-16: MOJIBAKE_FREE, ASCII_PIXEL_FALLBACK, PHASE2_EXTENSION_ONLY, TRAINING_EVENTS_DEFERRED, TERMINAL_STATE_VISIBLE, STRUCTURED_STAGE_FIRST).

WSP: WSP_22, WSP_97.

## V0.3.17 — REDDOG_WORKING_TRAIL_PHASE1 (Design Contract) — 2026-06-23

- Authored design contract for RedDog working trail (docs/REDDOG_WORKING_TRAIL_PHASE1.md).
- Defines UI contract (`reddogWorkingTrail` strip), event-to-action mapping for all 16 bridge progress events, JSONL training schema, and WSP_97 truth boundary checklist.
- Phase 1: design only. Phase 2 implements extension.js trail strip + elapsed timer; advisory_model_once.py unchanged in Phase 2.
- WSP_97 N/10 (all 10 truth boundary items PASS per design).

WSP: WSP_22, WSP_97, WSP_15.

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

**Follow-up slice recorded:** `HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1` — index extension.js, advisory_model_once.py, and Skillz discovery paths for RedDog queries.

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
