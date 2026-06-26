# Foundups®Agent TestModLog

## 2026-06-14 - REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1 (THG-001..006)

| ID | Asserts |
| --- | --- |
| THG-001 | `resolveAutoContextMode(regular, 'auto') === 'wsp_holo'` |
| THG-002 | HIGH -> `wsp_holo_skillz` (unchanged) |
| THG-003 | ULTRA -> `wsp_holo_git_skillz` (unchanged) |
| THG-004 | `buildBoundedRepoContext('wsp_holo', REGULAR_SMOKE_PROMPT)` includes HoloIndex recall |
| THG-005 | `wsp_holo` returns non-null `holoindex_scorecard` |
| THG-006 | `modeSelectionReasoning` cites HoloIndex-grounded `wsp_holo` for REGULAR |

Regression: TCI-001..TCI-010 (#883) must still pass.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-14 - REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1 (ADDENDUM E)

**Reuse:** `tests/fixtures.js` + registry below. Do not duplicate EXT-ACC-001 prompt strings in new tests.

### TEST_REGISTRY (contract runner)

| ID | Location | Asserts | Reuse for |
| --- | --- | --- | --- |
| TCI-001 | `verify_extension_contract.js` | `inferRecallTargetPaths(EXT_ACC_001_PROMPT)` -> `extension.js` | Recall inference regressions |
| TCI-002 | same | `readBoundedTargetSnippet` nonzero body, `omitted_reason: none` | Snippet read regressions |
| TCI-003 | same | `TARGET_READ_DENIED_PATHS` all rejected by `isTargetReadPathDenied` | Path safety regressions |
| TCI-004 | same | `resolveSafeRepoFile` ok for `extension.js` | Workspace confinement |
| TCI-005 | same | `buildTargetRecallContentSection` header + `target_content_included: true` | Section assembly |
| TCI-006 | same | `buildWsp97ProtocolExcerpt` protocol title present | WSP_97 excerpt on task match |
| TCI-007 | same | `buildBoundedRepoContext('wsp_holo_skillz', EXT_ACC_001_PROMPT)` integration | End-to-end bounded context |
| TCI-008 | same | `inferRecallTargetPaths(BUILD_COPY_MARKDOWN_PROMPT)` -> `extension.js` | Symbol/path dual inference |
| TCI-009 | same | `target_content_sanitized` + no raw block literals in target section | ADDENDUM F sanitization |
| TCI-010 | same | Python `evaluate_redaction_gate` PASS on target section + full EXT-ACC-001 context | Egress safety (no OpenRouter) |

**Gate probe helper:** `assertFusionRedactionGatePasses()` in contract runner (stdin to Python policy).

**Fixtures file:** `tests/fixtures.js` exports `EXT_ACC_001_PROMPT`, `EXT_ACC_001_TARGET_PATH`, `BUILD_COPY_MARKDOWN_PROMPT`, `TARGET_READ_DENIED_PATHS`.

**Prior slice (do not recreate):** HoloIndex path ranking -> `holo_index/tests/test_reddog_extension_bundle_recall.py` + TCI predecessor block (`evaluateTargetRecall`, `target_recall_ok`) in same contract file ~line 443.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-26 - HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1
- Verified `extension.js` in top 3 for EXT-ACC-001 review query (bundle-json + pytest).
- Verified `extension.js:buildCopyMarkdown` top hit for buildCopyMarkdown query.
- Verified `scripts/advisory_model_once.py` in top 3 for bridge query.
- Verified `evaluateTargetRecall`: `target_recall_ok` false + `index_gap_detected` true when adjacent hits only.
- Verified Run Trace scorecard includes `code_hits_count` and `target_recall_ok`.

Commands:

```powershell
python -m pytest holo_index/tests/test_reddog_extension_bundle_recall.py -q
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-26 - External acceptance baseline docs
- Verified acceptance baseline doc exists with 15 prompt IDs (EXT-ACC-001..015).
- Verified WSP_97 acceptance rows and baseline-vs-replacement language present.
- Verified static contract references acceptance doc path (no live OpenRouter in CI).

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
python -B -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/advisory_model_once.py').read_text(encoding='utf-8'))"
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-25 - v0.3.21 Blocked Copy MD polish
- Verified adjacent duplicate Work Trail events dedupe; detail-bearing event retained.
- Verified blocked-local Copy MD has no duplicate `redaction_gate_blocked` lines.
- Verified conservative blocked-local handoff: `handoff_needed: unknown`, `reason: blocked_context_needs_local_0102_review`, `WSP_15 priority: P1`, `suggested_slice_name: none`.
- Verified successful substantive runs retain prior assertive handoff behavior when model output exists.
- Verified Copy MD excludes secret-adjacent strings.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-24 - v0.3.20 Redaction Gate + Governed Handoff Contract
- Verified blocked Copy MD includes `## Redaction Gate Report` with `BLOCKED_LOCALLY`, `made_network_call: false`, `blocked_payload_part: unknown`, `raw_snippets_included: false`.
- Verified blocked packet contains no `OPENROUTER_API_KEY`, Bearer, or sk- token patterns.
- Verified substantive Copy MD includes `## Governed Handoff Recommendation` with `authority_level: advisory_only`.
- Verified Work Trail cap at 50 events; `sanitizeCopyMdText` maps key visibility to `key_env_present: true/false`.
- Verified HoloIndex recall scorecard fields in Run Trace for `wsp_holo_skillz` context.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-24 - v0.3.19 UX + Copy MD Contract
- Verified Working Tail DOM precedes toolbar and work focus composer in HTML order.
- Verified `Worker` UI label removed; `0102 Role` label present.
- Verified `buildCopyMarkdown` Run Trace fields, BLOCKED_LOCALLY redaction block, repair-failure warnings.
- Verified `detectMojibake` catches `窶` and `竊`.

## 2026-06-24 - v0.3.18 Branding Contract
- Verified user-facing branding uses Foundups®Agent while the internal package id and command id remain stable.
- Verified Fusion remains documented as an internal mode, not the product identity.

## 2026-06-23 窶・v0.3.17 Working Trail Phase 2 CODE Tests

- Trail DOM + progress command shape + operator message rg gate.
- `REDDOG_STAGE_ACTIONS` key set equals unique `_progress` stages from bridge (16/16).
- Stage mapping: redaction_blocked -> barking, single_done -> pointing, panel_blocked -> sitting.
- Regex fallback: Work focus sent -> sniffing; Output schema incomplete -> digging.
- Terminal hold constant 3000ms; enrichRedactionBlockResult metadata contract.
- #870 work-focus regression guards retained.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
rg "Stopped before OpenRouter. Nothing left the machine." extensions/foundups_advisory_workers/extension.js
```

## 2026-06-22 - v0.3.16 Addendum C Gate Tests

- Python (8 tests): panel truncation meta; 429 main-path redaction-once + same body; 400 no retry; redaction_blocked zero network; panel_models_truncated in review_packet.
- JS contract: bridgeStreamCapExceeded non-vacuity; killBridgeChild once; shouldAcceptBridgeCompletion dispose guard; resolver configured/system/dotvenv paths; WSP_97 survives truncation; #870 work-focus regression guards.

Commands:

```powershell
python -B -m unittest scripts.tests.test_advisory_model_once_hardening -v
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-22 - v0.3.16 Bridge Hardening Tests

- Contract tests for python resolver, context budget, bridge_meta, output_cap_exceeded.
- Python unittest: panel cap, 429 retry then success (same body, one redaction path), 400 no retry.

## 2026-06-22 - v0.3.15 Work Focus to WSP Prompt Tests

- Verified UI uses work focus composer (`#workFocus`) and `012 work focus` scrollback label.
- Verified `constructWspTaskPrompt` embeds WSP_97, WSP_15 tier, and non-authoritative work focus.
- Verified `redactedDigest` hash/excerpt contract.
- Verified review packet fields: `work_focus_digest`, `wsp_prompt_digest`, `prompt_construction`.
- v0.3.14 auto-router contract tests remain unchanged.

## 2026-06-22 - v0.3.14 Auto Router + Skillz Context Tests

- Updated contract test for GLM-5.2 principal, DeepSeek V4 Pro critic, and Kimi K2.7 Code implementation critic.
- Verified Mode/Effort/Context are no longer 012-facing dropdowns.
- Verified auto context mapping: REGULAR -> none, HIGH -> WSP/Holo/Skillz, ULTRA -> WSP/Holo/git/Skillz.
- Verified Skillz/Wardrobe/Rolodex discovery context remains advisory-only and non-vacuous for YouTube comment ops.
- Verified `modeSelectionReasoning`, Architect Trace / Verification gaps schema, Fusion panel structure validation, and Skillz wiring in bounded repo context.
## 2026-06-22 - v0.3.13 Orchestrator Contract Tests

Validation added for REDDOG_FUSION_ORCHESTRATOR_PHASE1:

- Auto effort classifier functions exist in extension source.
- Security/auth prompts classify `ULTRA`.
- WSP/architecture prompts classify `HIGH` or `ULTRA`.
- Simple smoke prompts classify `REGULAR`.
- RedDog WSP work defaults to `foundups_fusion` manual panel.
- OpenRouter Fusion alias remains selectable when explicitly chosen.
- Schema validator detects missing required sections.
- Repair prompt forbids invented evidence and preserves content.
- Review packet includes `output_validation` metadata path.
- Layout contract from v0.3.12 still holds.

Command:

```powershell
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-22 - v0.3.12 Contract Tests

Validation added:

- Webview layout contract:
  - grid rows `auto minmax(0, 1fr) auto`
  - output pane owns scrolling
  - composer stays after output in DOM order
  - no Send/Clear buttons required
- WSP operating contract:
  - RedDog Architect worker mode present
  - WSP_15 priority requirement present
  - WSP_97 truth-label requirement present
- HoloIndex retrieval contract:
  - bundle-json first
  - `HOLO_SKIP_MODEL=1`
  - offline fallback only after bundle failure
- Bridge contract:
  - prompt/context redaction gate path present
  - explicit system prompt reaches Fusion alias/manual modes
- Package contract:
  - package version matches README and extension build string

Command:

```powershell
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```
