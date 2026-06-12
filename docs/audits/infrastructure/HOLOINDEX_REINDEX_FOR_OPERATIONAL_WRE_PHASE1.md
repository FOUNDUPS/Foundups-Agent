# HOLOINDEX_REINDEX_FOR_OPERATIONAL_WRE_PHASE1

**Worker-Lane**: W6
**Slice**: HOLOINDEX_REINDEX_FOR_OPERATIONAL_WRE_PHASE1
**Type**: Docs-only audit PR + external index refresh (E:/HoloIndex, untracked, outside repo)
**Base**: a3e70b5a4 (origin/main, re-pinned fresh at execution time; equals dispatch base)
**Date**: 2026-06-12

## 1. Mission

Restore HoloIndex retrieval signal for the operational-WRE component chain
(#768-#778: FoundUpJob consumer seam, Hermes executor, receipts, ContextBundle,
BuildPlan, manifest validator) BEFORE the OPERATIONAL_WRE_MONOREPO_POC program
dispatches. Measure signal with 5 falsifiable benchmark queries (named expected
components, Y/N + rank) in both search modes, before and after a full
`--index-all` reindex.

## 2. Failure-Mode Taxonomy (012-canonical, applied throughout)

| Classification | Meaning |
|---|---|
| TOOL_CLASSIFIER_UNAVAILABLE | Shell command never ran (safety harness outage); no HoloIndex result exists |
| HOLOINDEX_LOW_SIGNAL | HoloIndex ran but returned weak/noisy results |
| HOLOINDEX_STALE_INDEX | HoloIndex ran; index freshness predates relevant repo changes |
| HOLOINDEX_RUNTIME_FAILURE | HoloIndex process started and failed |

The command-runner safety classifier is NOT HoloIndex. HoloIndex is local
(GGUF/Qwen/ChromaDB) with no Anthropic/Fable runtime dependency. Stale-index
results are never scored as architecture evidence and never justify duplicate
components.

## 3. Execution Environment

- Reindex and benchmarks ran from the shared worktree `O:/Foundups-Agent`
  (required: `holo_index.py` derives `project_root` from its own file location,
  `holo_index/_cli_main.py:39`; running from an isolated worktree would embed
  worktree paths into the index).
- Shared worktree HEAD during the run: `71de0229c` on
  `w6/build-plan-generator-module-path-trust-removal-phase1` (the #779 head =
  a3e70b5a4 + 1 commit). The shared HEAD was NEVER moved. Indexed content is
  therefore a3e70b5a4 plus one commit that only touches two files which are
  themselves benchmark targets (build_plan_generator.py, validator) - a
  disclosed superset of base.
- This report was authored and committed from an isolated worktree
  (`w6/holoindex-reindex-for-operational-wre-phase1` based at a3e70b5a4),
  per the one-active-worker rule.
- Index store target: `E:/HoloIndex/vectors` via `CHROMADB_DATA_PATH`
  (`holo_index/_cli_main.py:135-137`).

## 4. BEFORE Evidence

### 4.1 Index artifact timestamps (captured 2026-06-12 07:12:33 local)

| Artifact | mtime |
|---|---|
| E:/HoloIndex/chroma | 2026-05-22 06:46:58 |
| E:/HoloIndex/chroma.sqlite3 | 2026-05-06 14:51:59 |
| E:/HoloIndex/vectors | 2026-06-12 06:59:42 |
| E:/HoloIndex/vectors/chroma.sqlite3 | 2026-06-12 06:59:42 |
| E:/HoloIndex/indexes | 2026-01-08 06:04:40 |
| E:/HoloIndex/indexes/index_state.json | 2026-06-12 06:59:42 |
| E:/HoloIndex/models | 2026-04-23 19:20:18 |
| E:/HoloIndex/cache | 2026-01-20 07:39:27 |

`index_state.json` BEFORE content:
`last_indexed_at=2026-06-11T21:59:42+00:00, source=auto_refresh, code_count=296, wsp_count=117, test_count=0, skillz_count=0`.

### 4.2 Premise refinement (evidence-backed)

The dispatch premise said the chroma store (2026-05-06/2026-05-22) predates the
#768-#778 chain. The BEFORE evidence refines this into two facts:

1. The legacy store (`E:/HoloIndex/chroma`, `E:/HoloIndex/chroma.sqlite3`) is
   stale exactly as stated (2026-05-06 / 2026-05-22).
2. The ACTIVE store (`E:/HoloIndex/vectors`, the `CHROMADB_DATA_PATH` target)
   had been auto-refreshed the same morning (06:59, `source=auto_refresh`) but
   only over `code=296, wsp=117` entries - and the code collection indexes
   ONLY `NAVIGATION.py` `NEED_TO` entries plus web assets
   (`holo_index/core/indexing_engine.py:404-447`, `nav_entries =
   list(holo.need_to.items())`).

Therefore the operational-WRE retrieval failure is structurally
NAVIGATION-coverage-bounded, not purely timestamp-bounded: of the 9 expected
benchmark components, only `wsp_00_zen_state_tracker.py` appears in
`NAVIGATION.py` `NEED_TO` (line 162). The 8 consumer-chain components
(#768-#778) are absent from NAVIGATION.py entirely.

Additional architecture fact: `--offline` lexical mode does not query ChromaDB
at all - it scores ONLY `NAVIGATION.py` `NEED_TO` entries
(`holo_index/_cli_main.py:1301-1366`). Reindexing can never change lexical
results; lexical misses are NAVIGATION coverage gaps by construction.

### 4.3 BEFORE benchmark results

Raw evidence: 10 runs (5 queries x 2 modes), all rc=0. Semantic runs 15.8-18.4s
each; lexical runs 0.4s each. Renderer displays top code/WSP matches.

| Query | Mode | Expected component(s) | Surfaced? | Rank | Top noise instead |
|---|---|---|---|---|---|
| Q1 | semantic | foundup_job_consumer.py | NO | - | agent_market/in_memory.py, pattern_memory.py, WSP 26/58/109 |
| Q1 | semantic | hermes_foundup_job_executor.py | NO | - | |
| Q1 | semantic | receipt_emitter.py | NO | - | |
| Q1 | offline | (all three) | NO | - | simulator/deploy-sse.sh, foundup-cube.js |
| Q2 | semantic | context_bundle_builder.py | NO | - | public/kosei/sw.js, WSP 9/85/56 |
| Q2 | semantic | foundup_manifest_validator.py | NO | - | |
| Q2 | offline | (both) | NO | - | foundup-cube.js, sse_server.py |
| Q3 | semantic | build_plan_generator.py | NO | - | public/litepaper.html, vision_executor.py, WSP 46/97/9 |
| Q3 | semantic | build_plan_executor.py | NO | - | |
| Q3 | offline | (both) | NO | - | deploy-sse.sh, vision_executor.py |
| Q4 | semantic | foundup_job_router.py | NO | - | red-dog-concierge.js, WSP 104/98/26 |
| Q4 | offline | foundup_job_router.py | NO | - | foundup-cube.js, mesa_model.py |
| Q5 | semantic | wsp_00_zen_state_tracker.py | YES | 3 (code lane) | WSP_00 doc rank 1 in WSP lane (correct) |
| Q5 | offline | wsp_00_zen_state_tracker.py | YES | 1 | - |

BEFORE summary: 1/9 expected components retrievable (the single
NAVIGATION-listed one). The entire #768-#778 consumer chain (8 components) is
invisible in BOTH modes. This confirms the dispatch's measurement and the
HOLOINDEX_STALE_INDEX + coverage-gap diagnosis for the BEFORE state.

Anomaly observed (BEFORE Q5 semantic, stderr): WSP-GUARDIAN logged a unicode
check error against the pseudo-path
`modules/infrastructure/wsp_core/src/wsp_compliance_checker.py:WSPComplianceChecker.scan()`
(a NAVIGATION entry string, not a file). Classification: benign internal
warning, none of the four failure modes; search completed rc=0 with results.

## 5. REINDEX Execution

Command: `PYTHONIOENCODING=utf-8 python holo_index.py --index-all`
(cwd `O:/Foundups-Agent`).

| Field | Value |
|---|---|
| Start | 2026-06-12 07:16:01 |
| End | 2026-06-12 07:24:16 |
| Duration | 494.6s (8m 15s) |
| Exit code | 0 (no errors; stderr empty) |

Pass counts (stdout + index_state.json):

| Pass | Count | Time |
|---|---|---|
| SYMBOLS | 20000 symbols | 305.80s |
| DOCS | 3399 module/root docs | 93.32s |
| KNOWLEDGE | 1451 papers/research | 41.27s |
| SKILLS | 65 SKILLz | 5.79s |
| CLI | 701 entrypoints (121 WRE-connected, 580 orphans) | 26.34s |
| CODE (NAVIGATION) | 296 entries (index_state.json) | (not printed) |
| WSP | 117 protocols (index_state.json) | (not printed) |

Note: the run proved `--index-all` includes a SYMBOLS pass (20000 symbols) in
addition to the six passes named in `_cli_main.py:952-1083`. Symbol indexing is
the only pass that embeds `.py` content beyond NAVIGATION entries.

## 6. AFTER Evidence

### 6.1 Index artifact timestamps (captured 2026-06-12 07:25:02 local)

| Artifact | BEFORE mtime | AFTER mtime | Changed |
|---|---|---|---|
| E:/HoloIndex/chroma | 2026-05-22 06:46:58 | 2026-05-22 06:46:58 | no (orphaned legacy store) |
| E:/HoloIndex/chroma.sqlite3 | 2026-05-06 14:51:59 | 2026-05-06 14:51:59 | no (orphaned legacy store) |
| E:/HoloIndex/vectors | 2026-06-12 06:59:42 | 2026-06-12 07:23:48 | YES (active store rewritten) |
| E:/HoloIndex/vectors/chroma.sqlite3 | 2026-06-12 06:59:42 | 2026-06-12 07:23:48 | YES |
| E:/HoloIndex/indexes/index_state.json | 2026-06-12 06:59:42 | 2026-06-12 07:24:15 | YES |
| E:/HoloIndex/models | 2026-04-23 19:20:18 | 2026-04-23 19:20:18 | no (models unchanged, expected) |

`index_state.json` AFTER content:
`last_indexed_at=2026-06-11T22:24:15+00:00, source=manual_index, code_count=296, wsp_count=117, test_count=0, skillz_count=65`.

Evidence note: the legacy `E:/HoloIndex/chroma` + `chroma.sqlite3` artifacts
named in the dispatch premise were NOT touched by `--index-all`; the active
pipeline reads/writes `E:/HoloIndex/vectors` only. The stale timestamps on the
legacy store are real but describe an orphaned artifact, not the live index.

### 6.2 AFTER benchmark results

Raw evidence: 10 runs, all rc=0. Semantic 15.9-16.9s; lexical 0.4s. Semantic
result sets now span 4 lanes (code/wsp/docs/knowledge = 40 hits) versus 2 lanes
BEFORE (code/wsp = 20 hits) - the docs/knowledge/symbols collections did not
exist in the active store before this reindex.

Scoring is STRICT: a component counts as surfaced only if the named .py file
itself appears in the rendered results.

| Query | Mode | Expected component | BEFORE | AFTER | Rank AFTER |
|---|---|---|---|---|---|
| Q1 | semantic | foundup_job_consumer.py | NO | NO | - |
| Q1 | semantic | hermes_foundup_job_executor.py | NO | YES | 1 (code) |
| Q1 | semantic | receipt_emitter.py | NO | NO (adjacent: proof_of_compute_receipt.py r3) | - |
| Q1 | offline | (all three) | NO | NO (unchanged, NAVIGATION-bounded) | - |
| Q2 | semantic | context_bundle_builder.py | NO | YES | 1 (code) |
| Q2 | semantic | foundup_manifest_validator.py | NO | YES | 3 (code; its test at r2) |
| Q2 | offline | (both) | NO | NO (unchanged) | - |
| Q3 | semantic | build_plan_generator.py | NO | NO (adjacent: BUILD_PLAN contracts in docs lane) | - |
| Q3 | semantic | build_plan_executor.py | NO | YES | 1 (code; its test at r2) |
| Q3 | offline | (both) | NO | NO (unchanged) | - |
| Q4 | semantic | foundup_job_router.py | NO | NO (adjacent: foundup_job_contract.py r2, two FOUNDUP_JOB_ROUTER security audit docs r1-r2 in docs lane) | - |
| Q4 | offline | foundup_job_router.py | NO | NO (unchanged) | - |
| Q5 | semantic | wsp_00_zen_state_tracker.py | YES r3 | NO in code lane (bridge-symbol noise displaced it; WSP_00 doc still r1 in wsp lane; monitoring/INTERFACE.md r2 in docs lane) | - |
| Q5 | offline | wsp_00_zen_state_tracker.py | YES r1 | YES r1 (unchanged) | 1 |

## 7. Per-Query Verdicts

| Query | Semantic verdict | Lexical verdict |
|---|---|---|
| Q1 | IMPROVED (0/3 -> 1/3, rank 1; receipt/consumer still missing) | UNCHANGED (by construction) |
| Q2 | IMPROVED (0/2 -> 2/2, ranks 1 and 3) | UNCHANGED (by construction) |
| Q3 | IMPROVED (0/2 -> 1/2, rank 1; generator still missing) | UNCHANGED (by construction) |
| Q4 | UNCHANGED on the named component (0/1 -> 0/1); adjacent signal improved (router audit docs now r1-r2 in docs lane) | UNCHANGED (by construction) |
| Q5 | DEGRADED in code lane (r3 -> absent; displaced by wre_bridge/fam_bridge symbol matches); wsp-lane signal unchanged (WSP_00 r1) | UNCHANGED (HIT r1 retained) |

Aggregate (strict, semantic): 1/9 components -> 4/9 components, with three
rank-1 placements. Lexical: 1/9 -> 1/9, reindex-invariant as predicted by
`_cli_main.py:1301-1366` (offline mode scores only NAVIGATION NEED_TO).

## 8. Residual Gaps and Follow-Ups

Residual after a successful full reindex - each now a REAL
HOLOINDEX_LOW_SIGNAL finding (the index is fresh; retrieval still misses):

| Gap | Evidence | Classification |
|---|---|---|
| foundup_job_consumer.py invisible (Q1) | sibling hermes_foundup_job_executor.py ranks 1; consumer absent from all lanes | HOLOINDEX_LOW_SIGNAL |
| receipt_emitter.py invisible (Q1) | sibling proof_of_compute_receipt.py surfaced instead | HOLOINDEX_LOW_SIGNAL |
| build_plan_generator.py invisible (Q3) | sibling build_plan_executor.py ranks 1 | HOLOINDEX_LOW_SIGNAL |
| foundup_job_router.py invisible (Q4) | sibling foundup_job_contract.py r2; the router's own audit docs rank 1-2 in docs lane | HOLOINDEX_LOW_SIGNAL |
| Q5 semantic code-lane regression | zen tracker displaced by bridge-symbol matches after the 20000-symbol pass | HOLOINDEX_LOW_SIGNAL |

Pattern: all four missing components are shadowed by same-domain sibling files
whose symbols/embeddings dominate the shared vocabulary (consumer vs executor,
emitter vs receipt, generator vs executor, router vs contract). The SYMBOLS
pass reported a round 20000 - a likely cap that may truncate symbol coverage.

Named follow-up (NOT executed here; retrieval internals untouched per scope
fence): `HOLOINDEX_RETRIEVAL_QUALITY_PHASE1` - investigate symbol-pass
truncation at 20000, sibling-file shadowing, and ranking fusion across the new
4-lane result set; include the 5 benchmark queries above as its regression
fixture. A NAVIGATION.py NEED_TO coverage update for the 8 consumer-chain
components is a cheap complementary fix but mutates NAVIGATION.py, which is
outside this slice's fence; fold it into the follow-up.

## 9. Freshness Statement

Index freshness NOW POSTDATES a3e70b5a4. Evidence: the active store
(`E:/HoloIndex/vectors/chroma.sqlite3`) was rewritten 2026-06-12 07:23:48 with
`source=manual_index`, and the indexed working tree contained a3e70b5a4 plus
71de0229c (#779 head). All #768-#778 chain files were on disk during indexing.
Caveat recorded: the legacy `E:/HoloIndex/chroma` + `chroma.sqlite3` artifacts
remain at 2026-05-22 / 2026-05-06 because the current pipeline does not use
them; their staleness is permanent-by-orphanhood, not a defect of this run.

For the OPERATIONAL_WRE_MONOREPO_POC program: cite this report as the
freshness baseline; require index freshness to postdate the latest merged
relevant slice at each phase-0 check.

## 10. Failure-Mode Classifications Used (complete list)

| # | Event | Classification | Disposition |
|---|---|---|---|
| 1 | Shell harness refused 3 commands during outage windows (git fetch wrapper, BEFORE-timestamp capture attempt 1, BEFORE-summary attempt) | TOOL_CLASSIFIER_UNAVAILABLE (x3) | Retried (python-prefix / Read tool); all recovered; never scored as HoloIndex results |
| 2 | BEFORE semantic misses for the #768-#778 chain | HOLOINDEX_STALE_INDEX (docs/symbols/knowledge collections absent from active store; code lane structurally NAVIGATION-bounded) | Remediated by --index-all |
| 3 | BEFORE/AFTER lexical misses Q1-Q4 | Not stale-index: NAVIGATION NEED_TO coverage gap (offline mode never queries chroma) | Folded into follow-up |
| 4 | AFTER residual misses (4 components) + Q5 code-lane regression | HOLOINDEX_LOW_SIGNAL (real finding; index fresh, retrieval misses) | Named follow-up HOLOINDEX_RETRIEVAL_QUALITY_PHASE1 |
| 5 | WSP-GUARDIAN unicode warnings on NAVIGATION pseudo-paths (stderr, Q5 BEFORE; Q2/Q4/Q5 AFTER) | Benign internal warning - none of the four failure modes; searches completed rc=0 | Recorded only |
| 6 | --index-all | No failure: rc=0, 494.6s, stderr empty | HOLOINDEX_RUNTIME_FAILURE: NOT triggered |

No stale-index result was scored as architecture evidence; no duplicate
component was proposed on the basis of a retrieval miss.

## 11. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | DOCS_ONLY_REPO_DIFF | YES | Repo diff is exactly this report + one root ModLog entry |
| 2 | NO_SOURCE_TESTS_RUNTIME_CHANGE | YES | No .py/runtime/test file modified; benchmarks were read-only searches |
| 3 | NO_HOLOINDEX_CODE_CHANGE | YES | holo_index/ untouched; reindex used the existing CLI as-is |
| 4 | NO_WSP_MUTATION | YES | WSP_framework/ untouched |
| 5 | NO_CI_DEPENDENCY_CHANGE | YES | No workflow/requirements file in diff |
| 6 | EXTERNAL_INDEX_MUTATION_RECORDED_NOT_COMMITTED | YES | E:/HoloIndex changes documented in sections 5-6; nothing under E:/ is in the repo |
| 7 | SHARED_HEAD_NEVER_MOVED | YES | Shared worktree stayed at 71de0229c on the #779 branch throughout; report authored in isolated worktree |
| 8 | BENCHMARK_MEASURABLE_BEFORE_AFTER | YES | 20 result sets captured (5 queries x 2 modes x before/after), strict Y/N + rank scoring |
| 9 | TAXONOMY_APPLIED_NO_CONFLATION | YES | Section 10: classifier outages vs stale index vs low signal vs runtime failure kept distinct |
| 10 | CLASSIFIER_OUTAGES_NOT_SCORED_AS_HOLOINDEX | YES | Section 10 row 1: three TOOL_CLASSIFIER_UNAVAILABLE events, all recovered, none logged as retrieval results |
| 11 | STALE_RESULTS_NOT_ARCHITECTURE_EVIDENCE | YES | No architecture claim in this report rests on a BEFORE retrieval result |
| 12 | NO_DUPLICATE_COMPONENT_JUSTIFIED_BY_MISSES | YES | Residual misses produced a retrieval-quality follow-up, not new components |
| 13 | RESIDUAL_GAPS_NAMED_WITH_FOLLOWUP | YES | Section 8: HOLOINDEX_RETRIEVAL_QUALITY_PHASE1 with regression fixture |
| 14 | FRESHNESS_POSTDATES_BASE_STATED | YES | Section 9: vectors store 2026-06-12 07:23:48 postdates a3e70b5a4 |
| 15 | DEGRADATIONS_REPORTED_HONESTLY | YES | Q5 semantic code-lane regression reported as DEGRADED, not hidden |
| 16 | NO_SECRETS_IN_REPORT | YES | No keys/tokens/env values; timestamps, counts, and repo paths only |
| 17 | ASCII_CLEAN | YES | Byte-checked 0 non-ASCII before commit |
| 18 | REPORT_PATH_IGNORE_RULE_RESOLVED_BY_AUTHORIZED_REPAIR | YES | `.gitignore:324` (`docs/audits/*`) ignored the mandated report dir; `infrastructure/` lacked the negation pair other audit dirs have (17 precedent pairs incl. `!docs/audits/architecture/**`). Initial commit used explicit `git add -f` with the deviation disclosed for W10. 012 returned the slice for micro-repair and authorized the fix: the 2-line negation pair (`!docs/audits/infrastructure/` + `/**`) is now added at `.gitignore:358-359` matching the precedent convention, and the report is tracked WITHOUT requiring force-add (`git check-ignore` returns not-ignored). Repair scope: .gitignore + this report + ModLog only |

Declared 18 / Rows 18 / All YES.
