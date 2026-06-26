# RedDog Architect Review — HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1

**Status:** `VERIFIED_READY` (draft PR pending sovereign token)  
**Lane:** External 012-facing Foundups(R)Agent / RedDog only — Lane B excluded  
**Branch:** `feat/holoindex-reddog-extension-index-gap-phase1`  
**Baseline:** EXT-ACC batch 1 (001, 003, 007, 011, 015) on extension **v0.3.21**  
**Worker slice:** `HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1`  
**Date:** 2026-06-26

---

## Architect decision request

Review this packet and return one of:

| Decision | Meaning |
| --- | --- |
| `APPROVE_DRAFT_PR` | Hard checks 1–5 satisfied; merge after sovereign token |
| `REQUEST_CHANGES` | Cite failing check IDs + required evidence |
| `DEFER` | Blocked on prerequisite (name slice) |

After merge: 012 reruns **EXT-ACC-001** and **EXT-ACC-003** only before scheduling full replacement pass.

---

## Executive summary

Baseline proved **`bundle_json_ok + code_hits > 0 ≠ target_recall_ok`**. HoloIndex returned adjacent extension module docs (`package.json`, `INTERFACE.md`, `ModLog.md`) but missed **`extension.js`** and **`scripts/advisory_model_once.py`**.

This slice closes three root causes:

1. **Lexical path fallback excluded `.js`** — `extension.js` never entered module-scoped code hits.
2. **NAVIGATION entries landed in `DAE_ARCHITECTURE` instead of `NEED_TO`** — `_load_need_to()` never saw RedDog recall keys.
3. **Scorecard semantics were transport-level** — `index_gap_detected` used `missing_required` / `wsp_hits === 0`, not target-specific recall.

Minimal extension telemetry adds **`target_recall_ok`** and **`code_hits_count`**; fixes stale **`provider_reasoning_note`** (v0.3.21).

---

## Baseline evidence (OBSERVED — do not re-litigate)

```yaml
EXT-ACC-001:
  verdict: needs_repair
  holoindex_status: bundle_json_ok
  code_hits: 5
  extension_js_retrieved: false
  index_gap_detected_reported: false   # WRONG
  index_gap_detected_actual: true
  model_quality: partial_good          # correctly BLOCKED review vs inventing findings

EXT-ACC-003:
  verdict: blocked
  blocked_before_openrouter: true
  model_recall_analysis: none          # gate blocked holo-heavy prompt
```

Core finding:

```text
bundle_json_ok + code_hits=5 ≠ target_recall_ok
```

---

## Changes (worker execution summary)

| File | Change |
| --- | --- |
| `holo_index/cli/commands/bundle_json.py` | Add `.js` to path fallback; filename token boost; NEED_TO exact/substring match boost |
| `NAVIGATION.py` | RedDog recall keys in **`NEED_TO`** (not `DAE_ARCHITECTURE`) |
| `extensions/foundups_advisory_workers/extension.js` | `inferRecallTargetPaths`, `evaluateTargetRecall`, scorecard fields, v0.3.21 note |
| `extensions/foundups_advisory_workers/HOLOINDEX.md` | Tier-2 retrieval manifest (new) |
| `extensions/foundups_advisory_workers/tests/verify_extension_contract.js` | Target-recall + scorecard vocabulary tests |
| `holo_index/tests/test_reddog_extension_bundle_recall.py` | CI-safe regression tests (new) |

**Out of scope (unchanged):** OpenRouter routing, redaction tuning, output schema repair, UI polish, acceptance prompt pack edits.

---

## HoloIndex before / after (6 regression queries)

Mode: `HOLO_SKIP_MODEL=1 --bundle-json --limit 5`

| Query | Before (baseline / preflight) | After (this slice) | Class |
| --- | --- | --- | --- |
| **Q1** Foundups advisory workers extension Copy MD Work Trail Run Trace | Adjacent module docs; **extension.js missed** | `extension.js` #1 | **HIGH** |
| **Q2** advisory_model_once redaction gate bridge OpenRouter | **advisory_model_once.py missed**; openclaw gate noise | `scripts/advisory_model_once.py` #1 | **HIGH** |
| **Q3** Foundups Agent acceptance suite RedDog external worker | Acceptance doc weak/absent | `REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md` #1 | **HIGH** |
| **Q4** WSP_15 WSP_97 RedDog acceptance rubric | WSP docs not top-ranked | Acceptance baseline doc #1; `extension.js` in top 3 | **MEDIUM** |
| **Q5** buildCopyMarkdown Redaction Gate Report Governed Handoff | **extension.js / symbol missed** | `extension.js:buildCopyMarkdown` #1 | **HIGH** |
| **Q6** extension.js WSP_97 truth label compliance review | **extension.js often missed** | `extension.js` #3 (verify_contract.js #1) | **MEDIUM** |

Top-3 after detail (2026-06-26 worker run):

```text
Q1: extension.js | REDDOG_WORKING_TRAIL_PHASE1.md | HOLOINDEX.md
Q2: advisory_model_once.py | openclaw_dae._check_permission_gate | extension.js:buildCopyMarkdown
Q3: REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md | REDDOG_WORKING_TRAIL_PHASE1.md | agent_market/README.md
Q4: REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md | REDDOG_WORKING_TRAIL_PHASE1.md | extension.js
Q5: extension.js:buildCopyMarkdown | advisory_model_once.py | openclaw_dae._check_permission_gate
Q6: verify_extension_contract.js | package.json | extension.js
```

---

## Hard acceptance checks 1–5

| # | Criterion | Result | Evidence |
| ---: | --- | ---: | --- |
| 1 | `extension.js` in top 3 for EXT-ACC-001 review query | **PASS** | bundle-json + pytest `test_extension_js_in_top_hits_for_review_query` |
| 2 | buildCopyMarkdown query returns `extension.js` + symbol | **PASS** | Q5 top hit `extension.js:buildCopyMarkdown`; pytest `test_buildcopymarkdown_query_surfaces_extension_js` |
| 3 | Bridge query returns `advisory_model_once.py` in top 3 | **PASS** | Q2 #1; pytest `test_advisory_bridge_query_surfaces_advisory_model_once` |
| 4 | `index_gap_detected` = target-specific miss | **PASS** | `evaluateTargetRecall()` — gap true when hits exist but target path missing; contract tests |
| 5 | Run Trace vocabulary updated | **PASS** | `code_hits_count`, `target_recall_ok`, `index_gap_detected`, `direct_read_fallback_used`, `bundle_json_ok` in scorecard lines |

---

## Validation output (OBSERVED)

```text
pytest holo_index/tests/test_reddog_extension_bundle_recall.py → 4 passed
node --check extension.js → OK
node tests/verify_extension_contract.js → Foundups®Agent extension contract checks passed
```

Recommended pre-merge (architect may re-run):

```powershell
python -m pytest holo_index/tests/test_reddog_extension_bundle_recall.py -q
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
python -B -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/advisory_model_once.py').read_text(encoding='utf-8'))"
git diff --check -- extensions/foundups_advisory_workers holo_index NAVIGATION.py
```

---

## WSP_97 truth table

| Label | Status | Notes |
| --- | --- | --- |
| INDEX_GAP_BASELINE_EVIDENCED | OBSERVED | EXT-ACC-001 artifacts + batch-1 stop decision |
| TARGET_RECALL_DISTINCT_FROM_QUERY_OK | IMPLEMENTED | `target_recall_ok` vs `bundle_json_ok` |
| RETRIEVAL_REGRESSION_ADDED | IMPLEMENTED | `test_reddog_extension_bundle_recall.py` |
| EXTENSION_JS_RECALL_TARGET | IMPLEMENTED | `.js` in path fallback + NEED_TO keys |
| ADVISORY_BRIDGE_RECALL_TARGET | IMPLEMENTED | NEED_TO + exact-match boost |
| ACCEPTANCE_DOC_RECALL_TARGET | IMPLEMENTED | Q3/Q4 baseline doc #1 |
| SCORECARD_VOCABULARY_UPDATED | IMPLEMENTED | Run Trace fields + contract tests |
| NO_RUNTIME_AUTHORITY_ADDED | OBSERVED | Retrieval/telemetry only |
| LANE_B_EXCLUDED | OBSERVED | No WRE/Sakana/internal architect runtime |
| REPLACEMENT_PASS_NOT_IN_SCOPE | OBSERVED | Full 15-pack deferred |

**WSP_15:** C=3, I=5, D=4, Impact=5 → MPS **17 (P0)**

---

## Residual INDEX_GAP (INFERRED — post-merge watch)

| Area | Risk | Mitigation |
| --- | --- | --- |
| Q6 ranking | `verify_extension_contract.js` can outrank `extension.js` on WSP_97 query | Acceptable for lexical mode; monitor semantic (`HOLO_SKIP_MODEL=0`) path |
| EXT-ACC-003 | Redaction gate may still block holo-heavy prompts | Separate slice: `REDDOG_REDACTION_CONTEXT_TUNING_PHASE1` |
| EXT-ACC-001 repair | Output schema + repair redaction | Separate slice: `REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1` |
| Skillz discovery | Q3 still surfaces `agent_market/README.md` at #3 | Future: Skillz path indexing (not this slice) |
| Telemetry | `made_network_call: unknown`, duplicate Work Trail events | `REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1` |

---

## Follow-on slices (ordered)

1. **Merge this slice** → rerun EXT-ACC-001 + EXT-ACC-003  
2. `REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1`  
3. `REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1`  
4. `REDDOG_REDACTION_CONTEXT_TUNING_PHASE1`  
5. `REDDOG_EXTERNAL_ACCEPTANCE_REPLACEMENT_PHASE1` (full 15-pack)

---

## PR specification (worker to open)

```text
Branch: feat/holoindex-reddog-extension-index-gap-phase1
Title:  fix(holoindex): close RedDog extension and bridge retrieval gaps
Type:   Draft PR — do not merge without sovereign token
```

PR body must embed: baseline citations, this before/after table, hard checks 1–5, residual INDEX_GAP, rerun note for EXT-ACC-001/003.

---

## Architect review checklist

- [ ] Baseline finding acknowledged: transport OK ≠ target recall OK  
- [ ] Hard checks 1–5 evidence acceptable  
- [ ] NAVIGATION fix verified (`NEED_TO` not `DAE_ARCHITECTURE`)  
- [ ] No Lane B / OpenRouter / redaction scope creep  
- [ ] Residual gaps assigned to correct follow-on slices  
- [ ] Ready to rerun EXT-ACC-001 + EXT-ACC-003 after merge  

**Worker recommendation:** `APPROVE_DRAFT_PR`
