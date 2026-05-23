# HoloIndex Docs Reindex Observation — Phase 1

**Date**: 2026-05-24
**Slice**: HOLOINDEX_DOCS_REINDEX_OBSERVATION_PHASE1
**Base Commit**: `89410a88b` (origin/main, includes PR #686 trade-alias observation merge)
**Branch**: `docs/holoindex-docs-reindex-observation-phase1`
**Worktree**: `.claude/worktrees/holoindex-docs-reindex-observation`
**Worker**: W7
**Mode**: OBSERVATION (report-only) + operator-gated `--index-docs`

---

## WSP 97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| HOLOINDEX_DOCS_REINDEX_OBSERVATION_ONLY | YES |
| OPERATOR_GATED_INDEX_DOCS_AUTHORIZED_FOR_THIS_SLICE | YES (single `--index-docs` execution, exit 0, 15.6 s) |
| NO_CODE_CHANGE | YES |
| NO_HOLOINDEX_CORE_MUTATION | YES |
| NO_TRADE_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_GENERATED_INDEX_ARTIFACTS_COMMITTED | YES (artifact guard `git status --porcelain` empty after reindex) |
| REPORT_ONLY | YES (only repo edits are this audit doc + commit) |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Run the operator-gated docs reindex needed after PR #686 ("HoloIndex Trade Alias Live Observation Phase 1"), which logged two stale-index findings:

- **O-3** (post-rebase): `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` exists on disk (from PR #683) but absent from `navigation_docs`.
- **O-4**: `TRADE_ADAPTER_INTEGRATION_PHASE1.md` exists on disk but absent from `navigation_docs`.

Plus the suspected stale `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md` (PR #684's own audit doc).

This slice refreshes `navigation_docs` via `python holo_index.py --index-docs` and observes whether the three target docs surface afterward. No code change.

---

## 2. Preflight

| Check | Status | Evidence |
|-------|--------|----------|
| Current main includes PR #686 | PASS | `git log -1` → `89410a88b docs(holoindex): Trade alias live observation Phase 1 (rebased onto #683) (#686)` |
| `--index-docs` exists in HoloIndex CLI | PASS | `python holo_index.py --help` lists `--index-docs Index module/root docs into navigation_docs (CFZ4)` |
| Index path outside repo | PASS | `--ssd` default `E:/HoloIndex` (Chroma persistence dir lives on E:; not under any worktree) |
| Worktree clean pre-reindex | PASS | `git status --porcelain` empty |

---

## 3. BEFORE Snapshot

Three queries run pre-reindex. None of the three target audit docs appear in the top-5 docs hits.

### Q1 — `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1`

Top-5 `[DOCS]` hits (BEFORE):

| Rank | Path |
|------|------|
| 1 | `docs/audits/architecture/PORTFOLIO_DATA_VALIDATOR_PHASE1.md` |
| 2 | `docs/audits/pfmall_catalog_expansion/PFMALL_CATALOG_EXPANSION_REPORT.md` |
| 3 | `docs/audits/holoindex_search_quality/HIA_AGENTIC_RAG_WSP97_ALIAS_RECALL.md` |
| 4–5 | (CLI truncates output to 3 docs visible in tail; target absent in any case) |

Target rank: **ABSENT from top-5.**

### Q2 — `TRADE_ADAPTER_INTEGRATION_PHASE1`

Top-5 `[DOCS]` hits (BEFORE):

| Rank | Path |
|------|------|
| 1 | `modules/foundups/trade/INTERFACE.md` |
| 2 | `modules/foundups/trade/README.md` |
| 3 | `modules/foundups/trade/ModLog.md` |

Target rank: **ABSENT from top-5.**

### Q3 — `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1`

Top-5 `[DOCS]` hits (BEFORE):

| Rank | Path |
|------|------|
| 1 | `docs/audits/holoindex_search_quality/HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1.md` |
| 2 | `docs/audits/holoindex_search_quality/FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1.md` |
| 3 | `docs/audits/architecture/HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1.md` |

Target rank: **ABSENT from top-5.**

---

## 4. Reindex Execution

```bash
$ python holo_index.py --index-docs
```

| Property | Value |
|----------|-------|
| Start (UTC) | `2026-05-23T16:28:27Z` |
| End (UTC) | `2026-05-23T16:28:43Z` |
| Duration | **15.596 s** (`time` real) |
| Exit code | **0** |
| stdout marker | `[POINTS] Session Summary: +5 Refreshed indexes Total: 5 pts (variant A)` |
| stderr summary | empty (CLI usage banner emitted on stdout) |

The CLI emits the `+5 Refreshed indexes` reward marker, confirming `index_docs_entries()` was executed end-to-end against the docs collection.

---

## 5. Artifact Guard

Run after reindex, before AFTER queries, AND again after AFTER queries:

```bash
$ git status --porcelain
$ (no output)
```

**Result**: empty. No generated Chroma / index / cache / log / temp artifact appeared in the repo tree. The Chroma collection state lives on `E:/HoloIndex` (outside any worktree), confirmed by the absence of any staged or untracked file.

If any artifact had leaked into the repo, this slice would have STOPPED and reported a blocker per slice §4 protocol. None did.

---

## 6. AFTER Snapshot

Same three queries, re-run identically after the reindex.

### Q1 — `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1`

Top-5 `[DOCS]` hits (AFTER):

| Rank | Path |
|------|------|
| 1 | `docs/audits/architecture/PORTFOLIO_DATA_VALIDATOR_PHASE1.md` |
| 2 | `docs/audits/pfmall_catalog_expansion/PFMALL_CATALOG_EXPANSION_REPORT.md` |
| 3 | `docs/audits/holoindex_search_quality/HIA_AGENTIC_RAG_WSP97_ALIAS_RECALL.md` |

Target rank: **STILL ABSENT from top-5.**

### Q2 — `TRADE_ADAPTER_INTEGRATION_PHASE1`

Top-5 `[DOCS]` hits (AFTER):

| Rank | Path |
|------|------|
| 1 | `modules/foundups/trade/INTERFACE.md` |
| 2 | `modules/foundups/trade/README.md` |
| 3 | `modules/foundups/trade/ModLog.md` |

Target rank: **STILL ABSENT from top-5.**

### Q3 — `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1`

Top-5 `[DOCS]` hits (AFTER):

| Rank | Path |
|------|------|
| 1 | `docs/audits/holoindex_search_quality/HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1.md` |
| 2 | `docs/audits/holoindex_search_quality/FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1.md` |
| 3 | `docs/audits/architecture/HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1.md` |

Target rank: **STILL ABSENT from top-5.**

---

## 7. Before/After Rank Table

| Query | Target doc | Disk status | BEFORE rank | AFTER rank | Delta |
|-------|-----------|-------------|-------------|------------|-------|
| Q1 | `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` | EXISTS at `docs/audits/architecture/` | ABSENT (>5) | ABSENT (>5) | none |
| Q2 | `TRADE_ADAPTER_INTEGRATION_PHASE1.md` | EXISTS at `docs/audits/architecture/` | ABSENT (>5) | ABSENT (>5) | none |
| Q3 | `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md` | EXISTS at `docs/audits/holoindex_search_quality/` | ABSENT (>5) | ABSENT (>5) | none |

For all three, the BEFORE and AFTER top-5 docs lists are **identical** — same paths, same order.

---

## 8. Acceptance Verdict

Slice §2 acceptance criteria:

> - all target docs should surface in top 3, ideally rank #1.
> - if any target still fails, classify as retrieval-quality issue, not stale-index.

| Target | In top-3? | Verdict |
|--------|-----------|---------|
| Q1 due-diligence spec | NO | **retrieval-quality issue** |
| Q2 adapter integration audit | NO | **retrieval-quality issue** |
| Q3 #684 audit doc | NO | **retrieval-quality issue** |

**Overall acceptance: FAIL** — none of the three targets reached top-3 after reindex. **All three reclassify from *stale-index* to *retrieval-quality issue*** per slice §2 directive.

---

## 9. Observation Notes

### 9.1 What we learned

- `--index-docs` ran successfully (exit 0, ~16 s, reward marker emitted, no generated artifacts leaked into repo). The CFZ4 docs indexer executed end-to-end.
- Despite the successful refresh, the three target docs' rank did not improve. The top-5 docs lists are bit-identical between BEFORE and AFTER for all three queries.
- This is **not a freshness problem**. The docs either are already in the index but rank below other items, or are filtered out by the CFZ4 `index_docs_entries()` source-path policy. Either way, the symptom is retrieval-side, not index-side.
- The `audits/holoindex_search_quality/*.md` family does index (Q3's top-3 are all in that family), proving the CFZ4 pipeline DOES pick up `docs/audits/*.md`. So the target docs being absent is a per-doc retrieval issue, not a directory-scope issue.

### 9.2 Plausible retrieval-quality root causes (hypotheses; out of scope for this observation)

1. **Slice-ID alias gap (most likely)**: PR #684 introduced Trade-language alias expansion, but the Trade ALIASES list may not include the *literal slice ID strings* (`TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1`, `TRADE_ADAPTER_INTEGRATION_PHASE1`). Without an alias mapping the slice-ID → tokens in the indexed doc body, the embedding match is dominated by surrounding text (e.g. `PORTFOLIO_DATA_VALIDATOR_PHASE1` for Q1 because both mention "phase 1" + "validator/data" semantics). Cf. `HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1.md` (already indexed, top-1 for Q3) — its slice-ID matched because some prior slice deliberately addressed this.
2. **Path-boost gap**: Q2's top-3 are `foundups/trade/INTERFACE.md`, `README.md`, `ModLog.md` — Trade path-boost (added by #684) lifts those three over the audit doc. Path-boost is currently coarse-grained ("anything under `foundups/trade/`") and doesn't differentiate between module-root docs and `docs/audits/architecture/TRADE_*` docs.
3. **Title-anchor weight**: HoloIndex's title-anchor boost may favour shorter, README-style docs over long audit docs of equivalent slice-ID-string density.

These are diagnostic guesses, not assertions. A retrieval-quality slice would be needed to confirm and fix.

### 9.3 What this slice did NOT prove

- That `--index-docs` did or did not pick up the three target files specifically. The CLI's `+5 Refreshed indexes` reward is at the collection level, not per-file. To prove per-file inclusion, a future slice would need either a Chroma-side probe (count of docs in `navigation_docs` collection with `path` containing each target) or a `--verbose` reindex log.
- That the target docs are NOT in the collection at all. The fact that the top-5 is identical BEFORE and AFTER is consistent with both "already indexed, just outranked" AND "still not indexed". This observation cannot distinguish without a deeper probe.

### 9.4 Sequencing implication

PR #686's stale-index hypothesis (O-3, O-4) is **not refuted but is reframed**: the docs reindex is not sufficient on its own to surface these audit docs. The follow-on work is retrieval-quality, not freshness.

---

## 10. Recommendations (smallest-first)

| # | Slice ID | Scope | Why |
|---|----------|-------|-----|
| 1 | `HOLOINDEX_TRADE_SLICE_ID_ALIAS_EXTENSION_PHASE1` | Add literal slice-ID tokens for `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1` and `TRADE_ADAPTER_INTEGRATION_PHASE1` to the Trade alias group (likely 1 file, ~5 lines). Pure search-time change, no reindex. | Most likely root cause; minimal change. |
| 2 | `HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1` | Diagnostic-only slice: probe the `navigation_docs` Chroma collection to confirm whether the three target docs ARE actually indexed (counts/IDs). Read-only Chroma query, no mutation. | Disambiguates "outranked" vs "not indexed" for any future fix. |
| 3 | `HOLOINDEX_AUDIT_TITLE_ANCHOR_TUNING_PHASE1` (optional) | Increase title-anchor weight for audit doc filename matches against the query string. Search-time only. | Addresses Q3 / generic audit-doc-by-slice-ID retrieval, not just Trade. |
| 4 | `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1` audit doc | Author missing? Confirm on disk (this observation confirmed it IS on disk at `docs/audits/holoindex_search_quality/`), so no action needed beyond #1 / #3. | n/a — confirmation only |

None of these require broad HoloIndex enhancement.

---

## 11. Completion Summary

| Item | Value |
|------|-------|
| Branch | `docs/holoindex-docs-reindex-observation-phase1` |
| Base commit | `89410a88b` (origin/main, post-PR #686) |
| New commit SHA | *(populated by W10 on merge)* |
| Files changed | exactly 1: this audit doc |
| Reindex command | `python holo_index.py --index-docs` |
| Reindex duration | 15.596 s (real) |
| Reindex exit code | 0 |
| Reindex artifact guard | PASS (`git status --porcelain` empty post-reindex) |
| BEFORE rank for all 3 targets | ABSENT (>5) |
| AFTER rank for all 3 targets | ABSENT (>5) |
| Acceptance verdict | FAIL (none in top-3 after reindex) |
| Classification | **retrieval-quality issue** (all three) — NOT stale-index |
| WSP 97 truth boundary | PASS (full checklist §) |

---

## 12. WSP 97 Verdict

| Check | Result |
|-------|--------|
| Observation only — single authorised `--index-docs` invocation? | YES |
| No code / runtime / index-core mutation? | YES |
| No Trade / registry / catalog / manifest / projection mutation? | YES |
| No CI / dependency change? | YES |
| No generated Chroma / index / cache artifact committed? | YES (artifact guard empty) |
| BEFORE and AFTER snapshots captured for all three targets? | YES |
| Reindex command, exit code, duration recorded? | YES (§4) |
| Acceptance verdict honest about retrieval-quality classification? | YES (§8) |
| Recommendations smallest-first, no broad enhancement? | YES (§10) |

**WSP 97 VERDICT**: **PASS**

The slice executed its authorised scope cleanly. The empirical answer — that reindex alone is insufficient — is itself the deliverable.

---

## 13. W10 Readiness

| Gate | Status |
|------|--------|
| Branch base = origin/main post-PR #686 | YES |
| Files changed = exactly 1 (this audit doc) | YES |
| Reindex executed once, exit 0, no generated artifacts in repo | YES |
| BEFORE/AFTER snapshots present with rank table | YES |
| Acceptance verdict and classification recorded | YES |
| Recommendations queued (3 smallest-first follow-on slices) | YES |
| WSP 97 truth boundary checklist complete | YES |
| **Ready for PR** | **YES** |

---

**Observation Complete**: 2026-05-24
**Worker**: W7
**WSP Lock**: WSP_00, WSP_15, WSP_50, WSP_87, WSP_97, WSP_22
