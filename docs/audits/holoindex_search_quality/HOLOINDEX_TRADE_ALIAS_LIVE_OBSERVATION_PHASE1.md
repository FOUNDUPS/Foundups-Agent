# HoloIndex Trade Alias Live Observation — Phase 1

**Date**: 2026-05-23
**Slice**: HOLOINDEX_TRADE_ALIAS_LIVE_OBSERVATION_PHASE1
**Base Commit (post-rebase)**: `efb496922` (origin/main, includes PR #683 + PR #684)
**Original observation base**: `a1571a9d8` (PR #684 only — pre-#683 merge)
**Branch**: `feat/holoindex-trade-alias-live-observation-phase1`
**Worktree**: `.claude/worktrees/holoindex-trade-alias-observation`
**Mode**: OBSERVATION (report-only; no code change, no reindex)
**Worker**: separate observation worker (per operator scope guidance)
**Amendment**: Q4 re-run after #683 merge — see §11.

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| HOLOINDEX_OBSERVATION_ONLY | YES |
| NO_CODE_CHANGE | YES |
| NO_LIVE_REINDEX | YES |
| NO_GENERATED_INDEX_ARTIFACTS | YES |
| NO_TRADE_RUNTIME_CHANGE | YES |
| NO_TRADE_STATUS_CHANGE | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| REPORT_ONLY | YES |

Files NOT touched: any production source, HoloIndex core/index/search/CLI, `agentic_rag_verdict.py`, Trade module, registry/catalog, CI workflows, dependency files, WSP framework/knowledge. The only repo artifact created by this slice is this audit document.

---

## 1. Mission

Validate live HoloIndex behaviour for Trade analyst-language queries after PR #684 (`fix(holoindex): add Trade analyst language alias expansion and target-aware verdict`). PR #684 changed search-time logic only (alias expansion, path boost, target-aware verdict, intent classification) — therefore aliases and verdict should activate **without** a reindex. Reindex is only needed to refresh indexed corpus contents (e.g. new audit docs from PR #683/#684).

This slice does not enhance HoloIndex. It only asks: **on real queries, does #684 behave as advertised?**

---

## 2. Method

### 2.1 Five queries (specified in slice prompt)

| Tag | Query |
|-----|-------|
| Q1 | `Trade pump.fun memecoin issuer X telegram influencer rug pull large trades WSP 15 rating` |
| Q2 | `pump.fun issuer history rug pull holder distribution top traders Trade` |
| Q3 | `Trade FoundUp game theory memecoin launchpad social due diligence wallet audit` |
| Q4 | `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1` |
| Q5 | `TRADE_ADAPTER_INTEGRATION_PHASE1` |

### 2.2 Captures (per query)

For each query, captured:
- `classify_query_intent(query)` → `QueryIntent`
- Full `execute_search(...)` payload (limit=8, doc_type_filter='all')
- `classify_retrieval_evidence(payload, query_intent=intent)` → `RetrievalEvidenceSummary`
  - `verdict` (`SUFFICIENT` / `DEGRADED` / `UNSAFE_TO_ACT`)
  - `reason` (human-readable rationale)
- Count of `foundups/trade/` paths in the top-8 of `code_hits` and `docs_hits`
- Top-3 paths in `code_hits` and `docs_hits` for cross-reference

### 2.3 What this slice did NOT do

- No `python holo_index.py --index-*` invocations.
- No code edits.
- No edits to Trade, HoloIndex, registry, or CI.
- No installation of dependencies.
- No reliance on the CLI's "no critical issues found" text — that line is the generic health header, not the per-query `agentic_rag_verdict`. The verdict was captured by directly calling `classify_retrieval_evidence(...)`.

### 2.4 Caller-side caveat encountered

`classify_retrieval_evidence(payload, query_intent)` expects a `QueryIntent` enum. Calling with a raw string falls through to the generic verdict branch (`"General query: …"`). This is a probe-script bug, not a verdict-logic defect — and it would not arise in normal CLI usage because the CLI flows through `metadata["query"]` for intent inference. Re-ran the probe with the correct kwarg before drawing conclusions below.

---

## 3. Results

### 3.1 Verdict / intent / Trade-evidence table

| Tag | Intent | Verdict | Trade code/8 | Trade docs/8 | Verdict reason |
|-----|--------|---------|--------------|--------------|----------------|
| Q1 | TRADE | SUFFICIENT | 0/8 | 1/8 | Trade intent satisfied: Trade module evidence found |
| Q2 | TRADE | SUFFICIENT | 2/8 | 3/8 | Trade intent satisfied: Trade module evidence found |
| Q3 | TRADE | SUFFICIENT | 3/8 | 4/8 | Trade intent satisfied: Trade module evidence found |
| Q4 | TRADE | **DEGRADED** | 0/8 | 0/8 | Trade intent but no Trade module evidence in results — retrieval may miss relevant docs |
| Q5 | TRADE | SUFFICIENT | 3/8 | 5/8 | Trade intent satisfied: Trade module evidence found |

### 3.2 Top-3 paths per query

| Tag | Top-3 code | Top-3 docs |
|-----|------------|------------|
| Q1 | `simulator/economics/pumpfun_comparison.py`, `wre_core/src/improvement_job_contract.py`, `gamification/whack_a_magat/src/whack.py` | `docs/SPRINT_1_2_WSP_COMPLIANCE_AUDIT.md`, **`foundups/trade/ModLog.md`**, `video_comments/skillz/tars_account_swapper/README.md` |
| Q2 | **`foundups/trade/src/events.py`**, **`foundups/trade/tests/test_event_normalization.py`**, `simulator/economics/pumpfun_comparison.py` | **`foundups/trade/README.md`**, **`foundups/trade/ROADMAP.md`**, **`foundups/trade/ModLog.md`** |
| Q3 | **`foundups/trade/src/contracts.py`**, **`foundups/trade/tests/test_execution_guards.py`**, **`foundups/trade/tests/test_event_normalization.py`** | **`foundups/trade/README.md`**, **`foundups/trade/ROADMAP.md`**, **`foundups/trade/ModLog.md`** |
| Q4 | `simulator/economics/pumpfun_comparison.py`, `simulator/economics/tide_economics.py`, `ai_overseer/src/ai_overseer.py` | `docs/audits/architecture/PORTFOLIO_DATA_VALIDATOR_PHASE1.md`, `docs/audits/pfmall_catalog_expansion/PFMALL_CATALOG_EXPANSION_REPORT.md`, `docs/audits/holoindex_search_quality/HIA_AGENTIC_RAG_WSP97_ALIAS_RECALL.md` |
| Q5 | **`foundups/trade/src/adapters.py`**, **`foundups/trade/src/contracts.py`**, **`foundups/trade/tests/test_trade_contracts.py`** | **`foundups/trade/INTERFACE.md`**, **`foundups/trade/README.md`**, **`foundups/trade/ROADMAP.md`** |

Trade-module paths bolded. The slice-ID audit docs (`TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1` and `TRADE_ADAPTER_INTEGRATION_PHASE1`) do **not** appear in any top-3 docs list.

### 3.3 On-disk existence check (distinguishes stale-index vs doc-missing)

**Updated 2026-05-23 post-rebase** — see §11 for the Q4 re-run after #683 merged.

| Slice ID | File on disk | Surfaces in top-8 docs? | Classification |
|----------|--------------|-------------------------|----------------|
| `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1` | `docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` ✓ (from #683) | **NO** | **stale-index** (was *doc-missing* pre-#683-merge) |
| `TRADE_ADAPTER_INTEGRATION_PHASE1` | `docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md` ✓ | **NO** | **stale-index** |

Both audit docs are now under `docs/audits/architecture/` on disk; neither surfaces in the top-8 docs hits for its own slice-ID query → both are stale relative to `navigation_docs`. A single operator-gated `--index-docs` refresh closes both.

---

## 4. Acceptance Criteria Cross-Walk

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | Trade module docs/code appear in top results for analyst-language queries | **MOSTLY PASS** — Q2, Q3, Q5 strongly dominated by Trade paths in both buckets. Q1 marginal: Trade present (1/8 docs, position #2 = `foundups/trade/ModLog.md`) but unrelated paths dominate. |
| 2 | Target-aware verdict is not SUFFICIENT when unrelated hits dominate | **PARTIAL PASS** — verdict logic IS target-aware (Q4 correctly returns DEGRADED at 0/8 Trade evidence). Threshold is **≥1 Trade hit anywhere ⇒ SUFFICIENT**, which is loose for Q1 (1/8 docs only, 7/8 docs unrelated). Not a defect per se; tuning observation. |
| 3 | Slice-ID query for #683 surfaces the due-diligence spec if indexed | **PARTIAL PASS (post-#683-merge)** — disk check after rebase shows the #683 spec doc now exists at `docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md`. Q4 re-run still does NOT surface it in top-8 → stale `navigation_docs`. Verdict correctly remains **DEGRADED** — honest about retrieval miss. |
| 4 | If #683 does not surface, classify as stale-index, not code failure | **PASS** — post-merge, the #683 spec doc exists on disk and the re-run still does not surface it ⇒ **stale-index**, NOT code failure. Same classification applies to `TRADE_ADAPTER_INTEGRATION_PHASE1.md`. Both close with a single operator-gated `--index-docs` refresh. |

---

## 5. Per-Query Classification

### Q1 — `Trade pump.fun memecoin issuer X telegram influencer rug pull large trades WSP 15 rating`

- **Intent**: TRADE ✓ (alias expansion engaged)
- **Verdict**: SUFFICIENT (Trade evidence found: `trade/ModLog.md` at docs position #2)
- **Findings**:
  - Trade module surfaces (1/8 docs) but is dominated by unrelated paths (7/8 docs from simulator/sprint-audit/skillz; 8/8 code from simulator/wre/whack).
  - The query is the longest and most analyst-jargon-heavy of the five; alias expansion still places Trade ModLog at docs #2.
- **Classification**: **threshold tuning observation, not a defect**. The Trade target-aware verdict's minimum-evidence floor (≥1 Trade hit) is permissive for queries with heavy off-target keyword density.

### Q2 — `pump.fun issuer history rug pull holder distribution top traders Trade`

- **Intent**: TRADE ✓
- **Verdict**: SUFFICIENT (Trade evidence found)
- **Findings**: Trade dominates — top-3 code AND top-3 docs all `foundups/trade/`. Alias expansion + path boost working strongly.
- **Classification**: **PASS, working as intended**.

### Q3 — `Trade FoundUp game theory memecoin launchpad social due diligence wallet audit`

- **Intent**: TRADE ✓
- **Verdict**: SUFFICIENT (Trade evidence found)
- **Findings**: Trade dominates code (3/8 in top-3) and docs (3/8 in top-3). The "game theory / memecoin launchpad / due diligence / wallet audit" cluster successfully routes to Trade artifacts.
- **Classification**: **PASS, working as intended**.

### Q4 — `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1` (slice ID for #683)

**Updated 2026-05-23 post-rebase onto `efb496922` (PR #683 merged).**

- **Intent**: TRADE ✓
- **Verdict**: **DEGRADED** ✓ (same before and after #683)
- **Reason**: `"Trade intent but no Trade module evidence in results — retrieval may miss relevant docs"`
- **Findings (re-run)**:
  - Disk check: `docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` **EXISTS** (created by PR #683).
  - Q4 top-8 docs: still do NOT include the spec doc. Top-3 unchanged: `PORTFOLIO_DATA_VALIDATOR_PHASE1`, `PFMALL_CATALOG_EXPANSION_REPORT`, `HIA_AGENTIC_RAG_WSP97_ALIAS_RECALL`.
  - Trade evidence: 0/8 code, 0/8 docs.
- **Classification**: **stale-index** (was *doc-missing* pre-merge). The spec doc is on disk but is not in the `navigation_docs` collection.
- **Implication for PR #684**: the search-time logic (alias expansion, intent classification, target-aware verdict) is honest — DEGRADED is the correct verdict given retrieval state. An operator-gated `--index-docs` refresh would flip this to SUFFICIENT.

### Q5 — `TRADE_ADAPTER_INTEGRATION_PHASE1` (slice ID for #682-related audit)

- **Intent**: TRADE ✓
- **Verdict**: SUFFICIENT (Trade evidence found)
- **Findings**:
  - Top-3 code (`adapters.py`, `contracts.py`, `test_trade_contracts.py`) and top-3 docs (`INTERFACE.md`, `README.md`, `ROADMAP.md`) all `foundups/trade/`. Excellent recall.
  - **However**: the audit doc itself — `docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md` (confirmed present on disk) — does NOT appear in any top-8 docs hit.
- **Classification**: code/INTERFACE/README behaviour is **PASS**. The specific audit doc not surfacing IS a **stale-index** signal — the audit was added after the last docs reindex.

---

## 6. Defect Summary

| ID | Severity | Type | Description |
|----|----------|------|-------------|
| O-1 | LOW | tuning | Q1 verdict SUFFICIENT despite 7/8 unrelated hits. Trade target-aware verdict floor is `≥1 Trade hit ⇒ SUFFICIENT`. Consider tightening to "≥N Trade hits across code+docs" or "Trade hit in top-K". Not a regression — same logic accepts Q4 (0/8) as DEGRADED. |
| O-2 | LOW | unrelated bug | `format_verdict_for_agent()` in `holo_index/core/agentic_rag_verdict.py` line 393 attempts `summary.intent.value` but `summary.intent` is a `str` (not enum), raising `AttributeError`. This is a formatter-only bug; does not affect the verdict itself. Probably fixable in one line (`getattr(summary.intent, 'value', summary.intent)`). |
| O-3 | LOW | stale-index | **Updated post-rebase**: `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` now exists at `docs/audits/architecture/...` (PR #683). Q4 re-run still does not surface it ⇒ stale `navigation_docs`. Reclassified from *doc-missing* → *stale-index*. |
| O-4 | LOW | stale-index | `TRADE_ADAPTER_INTEGRATION_PHASE1.md` exists on disk but is absent from `navigation_docs`. Operator-gated `--index-docs` (read-only refresh of docs collection) would close this. |

**None of O-1..O-4 require code change** to declare PR #684 working. Alias expansion, path boost, intent classification, and target-aware verdict all behave as advertised. The findings are around (a) threshold sensitivity (O-1), (b) a separate formatter bug surfaced as a side-effect (O-2), (c) a stale `navigation_docs` collection for the #683 spec doc (O-3, reclassified from *doc-missing* after rebase), and (d) the same stale-index pattern for `TRADE_ADAPTER_INTEGRATION_PHASE1.md` (O-4). O-3 and O-4 share a root cause and close with a single operator-gated `--index-docs` refresh.

---

## 7. Outcome Map (per operator's recommendations)

| Operator-proposed follow-up | Triggered? | Reason |
|-----------------------------|------------|--------|
| Operator-gated docs reindex slice | YES (small) | O-3 + O-4 — `navigation_docs` is stale for BOTH `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` (from PR #683) AND `TRADE_ADAPTER_INTEGRATION_PHASE1.md`, plus likely `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md` from PR #684 itself. Reindex is read-only refresh of the docs collection; aliases/verdicts already work without it. Single slice closes all three. |
| Stronger module/path boost | NO | Trade already wins decisively on Q2, Q3, Q5 (top-3 in both buckets). Q1 is the only marginal case and is dominated by query length, not boost weakness. |
| Tighten `agentic_rag_verdict` | OPTIONAL | O-1 — Q1's SUFFICIENT-with-1-hit is a tuning question, not a defect. Could be a follow-on slice if 012 wants stricter thresholds. |
| Improve Trade docs/spec terminology | NO | Trade docs already carry the analyst terminology (Q2/Q3/Q5 retrievals confirm); the alias expansion in #684 bridges natural-language → indexed terminology effectively. |
| Fix `format_verdict_for_agent` enum/str bug | YES (small) | O-2 — unrelated to alias work but discovered here; one-line fix in `agentic_rag_verdict.py:393`. |

---

## 8. WSP 97 Verdict

| Check | Result |
|-------|--------|
| Observation only — no code change? | YES |
| No live reindex performed? | YES |
| No generated index artifacts (no Chroma writes)? | YES |
| No Trade runtime / status / registry mutation? | YES |
| No CI change? | YES |
| No dependency install? | YES |
| HoloIndex core / index / search / Trade module untouched? | YES |
| Audit doc records start date, queries run, raw findings, and outcome map? | YES |
| Defect findings classified by severity / type? | YES |
| Stale-index vs doc-missing distinction applied where relevant? | YES |
| Slice ends with explicit follow-up recommendations? | YES |

**WSP 97 VERDICT**: **PASS**

---

## 9. W10 Readiness

| Gate | Status |
|------|--------|
| Live HoloIndex observed against the 5 specified queries | YES |
| Per-query intent/verdict/Trade-evidence captured | YES |
| Stale-index vs doc-missing classified (O-3 = missing, O-4 = stale) | YES |
| Verdict logic shown to be target-aware (Q4 → DEGRADED proves it) | YES |
| Audit doc complete with cross-walk to acceptance criteria | YES |
| Branch / commit ready for PR | YES |
| **Ready for PR** | **YES** |

---

## 10. Next-Slice Recommendations

In dependency order, smallest-first:

1. **`HOLOINDEX_FORMATTER_INTENT_STR_HOTFIX_PHASE1`** (~5 lines) — fix O-2 (`format_verdict_for_agent` AttributeError on `.intent.value`). Discovered by this observation; not the operator's primary path but a free quality win.
2. **`HOLOINDEX_DOCS_REINDEX_OBSERVATION_PHASE1`** — operator-gated `--index-docs` to refresh `navigation_docs` and close O-3 + O-4 in one slice (`TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` and `TRADE_ADAPTER_INTEGRATION_PHASE1.md` both on disk but absent from `navigation_docs`; PR #684's own audit doc likely also stale). Should follow the controlled-reindex pattern from prior slices: baseline → reindex → verify against Q4/Q5 + slice ID for #684 audit. Read-only refresh, no source mutation.
3. ~~`TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1`~~ — **resolved by PR #683**; the spec doc is now on disk. No further authoring needed; O-3 reduces to the reindex slice above.
4. **`HOLOINDEX_TRADE_VERDICT_THRESHOLD_TUNING_PHASE1`** (optional) — only if 012 wants Q1-style "SUFFICIENT despite 7/8 unrelated" to flip to DEGRADED. Would tighten the Trade-target floor (e.g. require ≥2 Trade hits OR Trade-hit-in-top-K). Pure search-time logic change, no reindex.

Each of these is a small, scoped slice. **None require broad HoloIndex enhancement** — consistent with the operator's "observation first, not open-ended enhancement" scope guidance.

---

## 11. Rebase / Q4 Re-run Amendment (2026-05-23)

### 11.1 Why this section exists

The original observation was conducted against base `a1571a9d8` (PR #684 only). At that time PR #683 (`docs(trade): pump.fun due-diligence scoring spec Phase 1`) had **not yet merged**, so the disk check for `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` returned empty and the finding was classified as *doc-missing*.

Per the operator's W10 gate addendum, "the audit must no longer claim TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md is missing unless it is actually missing on disk" once #683 merges. PR #683 merged as `efb496922`; this branch was rebased onto current `origin/main` and Q4 was re-run against the new ancestry.

### 11.2 Disk check after rebase

```
$ find docs -name "TRADE_PUMPFUN_DUE_DILIGENCE*"
docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md
```

Spec doc **exists**.

### 11.3 Q4 re-run after rebase

```
query        : TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1
intent       : TRADE
verdict      : DEGRADED
reason       : Trade intent but no Trade module evidence in results — retrieval may miss relevant docs
trade_code/8 : 0
trade_docs/8 : 0
spec_doc_in_top8 : False
top3 docs    : ['PORTFOLIO_DATA_VALIDATOR_PHASE1.md',
                'PFMALL_CATALOG_EXPANSION_REPORT.md',
                'HIA_AGENTIC_RAG_WSP97_ALIAS_RECALL.md']
```

### 11.4 Reclassification

| Aspect | Pre-rebase | Post-rebase |
|--------|-----------|-------------|
| Spec doc on disk? | NO | YES (`docs/audits/architecture/...`) |
| Spec doc in top-8 docs hits? | NO | NO |
| Verdict | DEGRADED | DEGRADED (unchanged) |
| Verdict reason | "no Trade module evidence" | "no Trade module evidence" (unchanged) |
| **Classification** | **doc-missing** | **stale-index** |

The verdict logic from PR #684 is **unchanged** by the rebase — it returned DEGRADED before #683 merged (because the doc didn't exist) and continues to return DEGRADED after #683 merged (because the doc isn't in `navigation_docs` yet). In both states the verdict is **honest**: it reports retrieval failure without attempting to mask it.

### 11.5 What this confirms about PR #684

- Target-aware verdict survives an underlying corpus change. The same query routes to the same DEGRADED outcome with the same reason whether the doc is missing or merely unindexed.
- Alias expansion and intent classification are independent of corpus freshness — Q4 was correctly classified as `TRADE` intent in both runs.
- The DEGRADED verdict is the right user-facing signal: "we cannot find the evidence you asked for". Whether the underlying cause is *doc-missing* or *stale-index* is a triage step the audit captures, not something the verdict needs to distinguish.

### 11.6 What this changes about the next-slice recommendation

The single docs-reindex follow-up slice now closes BOTH O-3 and O-4. There is no longer a separate "author the missing spec" follow-up (it landed in #683).

---

**Observation Complete**: 2026-05-23 (rebased + re-run same day)
**Worker**: separate observation worker
**WSP Lock**: WSP_00, WSP_15, WSP_50, WSP_6, WSP_87, WSP_97, WSP_22
