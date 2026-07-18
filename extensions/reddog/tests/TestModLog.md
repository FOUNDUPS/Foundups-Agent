# Foundups(R)Agent TestModLog

## 2026-07-18 - REDDOG_HOLO_SEMANTIC_FIRST_PHASE1

- Asserted semantic is the production default and lexical retrieval requires explicit `REDDOG_HOLO_RETRIEVAL_MODE=lexical` opt-down.
- Asserted semantic mode removes inherited `HOLO_SKIP_MODEL`, preserves an operator-set `HOLO_OFFLINE` network boundary, and keeps the read-only query guard.
- Asserted requested mode, actual retrieval mode, embedding backend, and routing state reach RedDog metadata, scorecards, and summaries.
- Simulated primary semantic failure and proved exactly one offline lexical fallback receives a valid scoped environment, closing the previous `env` block-scope failure.
- The exhaustive contract suite opts down to lexical for deterministic runtime; a separate live smoke proves the production semantic path and `sentence_transformers` receipt.

## 2026-07-18 - REDDOG_FUSION_KIMI_K3_PHASE1

- Asserted the 0.4.1 package/runtime version lock and default Kimi K3 panel membership.
- Asserted the bridge emits Kimi K3 requests with mandatory `max` reasoning, without temperature, and with the 4096-token panel budget.
- Retained Kimi K2.7 Code coverage so the default panel can compare the two Kimi generations.
- Reconciled the stale resident-session contract assertion with the already-shipped durable AgentDB runtime symbol; production resident code was not changed.

## 2026-07-09 - REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1 (WRE-DRY-001..WRE-DRY-010)

| ID | Asserts |
| --- | --- |
| WRE-DRY-001 | `buildWreOperationalSpineDryRunPreview` / section builder exported and reachable |
| WRE-DRY-002 | Preview emits `REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1` and target `reddog_wre_operational_spine` |
| WRE-DRY-003 | Preview records `dry_run_only=true`, no Python invocation, no spine invocation, no worktree create, no task execution |
| WRE-DRY-004 | Preview records no OpenClaw enqueue, no Hermes dispatch, no PR, no merge |
| WRE-DRY-005 | Preview uses full SHA256 `command_digest` and does not store raw work focus |
| WRE-DRY-006 | Secret-adjacent env-name text is sanitized in `command_redacted_summary` and Copy MD |
| WRE-DRY-007 | Copy MD includes `## WRE Operational Spine Dry-Run Preview` after governed handoff |
| WRE-DRY-008 | Source has no `execFileSync(...reddog_wre_operational_spine.py...)` call in this slice |
| WRE-DRY-009 | Blocked-local packets skip WRE preview wiring |
| WRE-DRY-010 | Future live use is gated by `VALVE_OPEN_WORKTREE_CREATE` and `012_sovereign` |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-07-07 - REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (WFTD-015..WFTD-020, v0.3.45)

| ID | Asserts |
| --- | --- |
| WFTD-015 | Flowing-prose `Read first:` prompt (the EXACT failed 0.3.44 shape: 3 files in one sentence, period+prose after breadcrumb_tracer.py, `and the breadcrumb/handoff layer`) derives EXACTLY the 3 real files; breadcrumb_tracer.py is present AND clean (no trailing " Determine..." / period); `derived=true`, source `read_first`; `extractProsePathTokens` + `work_focus_targets_dropped_low_confidence` present in source |
| WFTD-016 | Recall on the prose prompt with all 3 files present: `required_targets_total=3`, `required_targets_recalled=3`, `target_recall_ok=true`, `index_gap_detected=false` (inverts the 0.3.44 `total 4 / recalled 2 / ok false`); the required targets are EXACTLY the 3 real files |
| WFTD-017 | The `breadcrumb/handoff` slash-only fragment IS in `work_focus_targets_dropped_low_confidence`, is NOT a required target, is NOT in `required_targets_missing`, and does NOT flip `target_recall_ok` |
| WFTD-018 | Fix C: trailing `. , ; : ) ] }` trimmed from a derived path (via `extractTargetTokensFromLine`); a `${docs/a/b.py}` brace wrapper trims to the clean path (via `extractProsePathTokens`) |
| WFTD-019 | Option-3 REGRESSION: a BULLETED `Read first:` list (one path per line) still derives all 3 cleanly; clean bullets drop nothing |
| WFTD-020 | Tiered strictness: the M2M tier still accepts an intentionally-named DIRECTORY-style path (slash, no extension) via `m2m_read`; the SAME slash-only shape is DROPPED in flowing prose (prose stricter, explicit/M2M/bullet broader) |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-07-07 - REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (WFTD-001..WFTD-014)

| ID | Asserts |
| --- | --- |
| WFTD-001 | Header-only shape: `collectRequiredTargets` == `parseRequiredTargetPaths` (byte-identical, backward compatible); `derived=false`, source `required_block` |
| WFTD-002 | `Read first:` list of 3 repo paths derives all 3; source `read_first` |
| WFTD-003 | WSP_99 M2M `READ:` array derives its paths; source `m2m_read` |
| WFTD-004 | M2M `CTX.FILES` array derives its paths; the `CTX.FILES` KEY token is NOT derived; source `ctx_files` |
| WFTD-005 | Backticked repo paths derive; source `backtick_path` |
| WFTD-006 | Inline prose repo paths derive AND do not capture surrounding prose words; source `inline_path` |
| WFTD-007 | Denied paths (`.env`, traversal) EMITTED honestly by the deriver but DENIED by the existing gate (`isTargetReadPathDenied`); a legitimate path still derives |
| WFTD-008 | HoloIndex miss on derived paths: `required_targets_total > 0`, `index_gap_detected=true` (fetch fires), `work_focus_targets_derived=true` |
| WFTD-009 | No explicit AND no derivable paths: `required_targets_total=0`, recall `unknown`, `derived=false` (inference path intact) |
| WFTD-010 | Guard B-i: a ```powershell validation block naming `extension.js` derives NOTHING |
| WFTD-011 | Guard B-ii: a `SCOPE - OUT` bullet path is NOT derived; an in-scope `Read first` path in the same prompt IS derived |
| WFTD-012 | Regression (real Python CLI): multi-lane orchestration `Read first` prompt -> `required_targets_total >= 3`, `direct_read_fetch_attempted=true`, each named file fetched / rejected / honestly-missing |
| WFTD-013 | `work_focus_targets_derived` + `work_focus_target_derivation_sources` surface in `extractHoloIndexScorecard` and render in the Run Trace scorecard lines |
| WFTD-014 | ReDoS remediation (CodeQL js/polynomial-redos): `stripListMarker` parity (dash/numbered/multi-space bullets stripped; non-list + marker-without-whitespace return `isList=false`); the flagged `.match(/^(?:[-*+]...)` bullet-regex USE is absent from source; pathological 200KB-whitespace input stays linear (<200ms) |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-06-28 - REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1 (Addendum G)

| ID | Asserts |
| --- | --- |
| G-001 | `buildSanitizedContinuationSummary` success path captures decision + PR refs |
| G-002 | Poisoned output strips private reasoning markers |
| G-003 | Blocked run stores safe redaction gate summary only |
| G-004 | `appendContinuationSummaryToWspPrompt` includes continuation block |
| G-005 | Continuation-augmented prompt passes fusion redaction gate |
| G-006 | Copy MD includes safe Continuation Summary section when provided |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING addendum (OSR-007..OSR-010)

| ID | Asserts |
| --- | --- |
| OSR-007 | Primary missing Evidence/Architect Trace/Verification gaps/Next safest step; supplement completes schema |
| OSR-008 | Repair trail maps single/panel stages to `repair_single_started` |
| OSR-009 | Repair prompt lists explicit `## Section` headers |
| OSR-010 | Failed repair still exposes repair metadata + missing_sections_after_repair |

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1 (OSR-001..OSR-006)

| ID | Asserts |
| --- | --- |
| OSR-001 | `buildRepairBoundedContext()` minimal, declares repair pass |
| OSR-002 | Repair context notes egress-safe placeholders |
| OSR-003 | Minimal repair context passes Python gate |
| OSR-004 | `buildRepairPrompt` sanitizes block literals; gate passes |
| OSR-005 | `mergeRepairedOutput` satisfies Fusion schema when supplemented |
| OSR-006 | Run Trace exposes `repair_context_mode` / `repair_mode` |

Regression: UNI, TCI, THG unchanged.

## 2026-06-14 - ADDENDUM B bridge UTF-8 stdin (UNI-008..UNI-010)

| ID | Asserts |
| --- | --- |
| UNI-008 | `evaluate_redaction_gate(safe, EMDASH_UNICODE_CONTEXT)` passes (U+2014) |
| UNI-009 | `buildBridgePythonEnv` sets PYTHONIOENCODING + PYTHONUTF8 |
| UNI-010 | `test_main_em_dash_utf8_stdin_not_redactor_error` passes |

Regression: UNI-001..UNI-007, TCI, THG unchanged.

## 2026-06-14 - REDDOG_CONTEXT_UNICODE_NORMALIZATION_PHASE1 (UNI-001..UNI-007)

| ID | Asserts |
| --- | --- |
| UNI-001 | Lone surrogate breaks UTF-8 digest path without normalization |
| UNI-002 | `evaluate_redaction_gate(safe, MALFORMED_UNICODE_CONTEXT)` -> `redactor_error` |
| UNI-003 | `normalizeBridgeTextForUnicode` replaces lone surrogate; count > 0 |
| UNI-004 | Normalized context passes Python gate |
| UNI-005 | `BLOCKED_POLICY_CONTEXT` still -> `blocked_policy` |
| UNI-006 | `buildRunTraceSection` exposes unicode normalization telemetry |
| UNI-007 | No raw malformed surrogate in normalized text or Run Trace |

Regression: TCI-001..TCI-010 and THG-001..THG-006 must still pass.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

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
- Verified `detectMojibake` catches `` and ``.

## 2026-06-24 - v0.3.18 Branding Contract
- Verified user-facing branding uses Foundups(R)Agent while the internal package id and command id remain stable.
- Verified Fusion remains documented as an internal mode, not the product identity.

## 2026-06-23 v0.3.17 Working Trail Phase 2 CODE Tests

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
