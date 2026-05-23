# HoloIndex `--index-docs` Pipeline Consistency Audit — Phase 1

**Slice**: `HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1`
**Worker**: W6
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: DIAGNOSTIC (dry-run, read-only)
**Branch**: `feat/holoindex-index-docs-consistency-audit-phase1`
**Base commit**: `d4827f639` (origin/main, post-PR #689)
**Worktree**: `.claude/worktrees/holoindex-index-docs-consistency-audit`
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_104 → WSP_22

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| HOLOINDEX_DIAGNOSTIC_DRY_RUN_ONLY | YES |
| READ_ONLY_CHROMA_ACCESS | YES |
| NO_CHROMA_MUTATION | YES |
| NO_REINDEX | YES (no indexer flag was invoked) |
| NO_HOLOINDEX_CORE_INSTRUMENTATION | YES (no `holo_index/core/**` change) |
| NO_HOLOINDEX_CORE_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_TRADE_MUTATION | YES |
| NO_WSP_MUTATION | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_GENERATED_INDEX_ARTIFACTS_COMMITTED | YES |
| REPORT_ONLY | YES |
| STATIC_SAFETY_SCAN_PASSES_ON_DIAGNOSTIC_SCRIPT | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

PR #689 (HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1) confirmed empirically that
`navigation_docs` is missing **9** of the **42** files in
`docs/audits/architecture/`, including three target audit docs (T1/T2/T3),
even though PR #688 ran the docs reindexer with **exit code 0** and the
reward marker `+5 Refreshed indexes`. The probe explicitly recommended
**not** simply rerunning the indexer.

This slice is the diagnostic follow-on. It investigates why the indexer
reports success but leaves files out of the index, classifies the failure
mode, and names the smallest follow-on fix slice. It does this **without**
running the indexer, without writing to Chroma, and without instrumenting
the core indexing engine.

---

## 2. Chain-of-Thought / Chain-of-Action / Chain-of-Evidence (CoT/CoA/CoE)

### 2.1 Chain-of-Thought

- The probe found a per-file *index inclusion* failure, not a *ranking* failure.
- The indexer is structured as: discover files → filter → embed → bulk-add.
  Each stage can fail silently.
- The CLI emits `[DOCS] Indexed module/root docs in {duration}s` and the
  reward marker is granted on flag completion rather than on inserted count.
  So a no-op run is observationally indistinguishable from a successful run.
- HoloIndex resolves `project_root = Path(__file__).parent.parent.parent`
  from `holo_index/core/holo_index.py`. Worktrees in this repo live under
  `.claude/worktrees/<name>/` and contain a full copy of `holo_index/`, so
  a worktree-launched run picks up the worktree as `project_root`.
- The indexer file filter rejects any path whose `f.parts` contains a
  component starting with `.`. **Every** absolute path inside a worktree
  contains the part `.claude`, so the filter would reject **all** files
  the worktree discovers.

### 2.2 Chain-of-Action

| Step | Action | Mutates? |
|------|--------|----------|
| 1 | Verify worktree base (`d4827f639`) and presence of all target files on disk | NO |
| 2 | Read the indexer source (`holo_index/_cli_main.py`, `holo_index/core/indexing_engine.py::index_docs_entries`, `holo_index/core/holo_index.py::project_root`) | NO |
| 3 | Build a dry-run diagnostic script (`holo_index/scripts/diagnose_index_docs_pipeline.py`) replicating the filter, model-cache check, and id scheme **without** invoking the indexer or touching Chroma | NO |
| 4 | Run the diagnostic; observe `navigation_docs` read-only for count + architecture-paths sample | NO (read-only) |
| 5 | Cross-check expected vs. actual missing files by enumerating disk vs. Chroma | NO (read-only) |
| 6 | Classify the failure mode and name the smallest fix slice | NO |

### 2.3 Chain-of-Evidence

| Evidence | Source | Value |
|----------|--------|-------|
| Worktree `project_root` resolves under `.claude/worktrees/` | `Path(__file__).parent.parent.parent` from `holo_index/core/holo_index.py` | `O:\Foundups-Agent\.claude\worktrees\holoindex-index-docs-consistency-audit` |
| Indexer filter rejects any `f.parts` containing a dot-prefixed part | `indexing_engine.py:650` | `not any(part.startswith('.') for part in f.parts)` |
| Indexer also has a redundant clause that rejects literal `.claude/worktrees` substring | `indexing_engine.py:655–656` | both clauses fire on the same paths |
| When `files` is empty, the indexer returns early with `WARN` log only | `indexing_engine.py:660–662` | `if not files: holo._log_agent_action("No docs found to index", "WARN"); return` |
| CLI awards `indexing_awarded = True` after the function returns regardless of insertion count | `_cli_main.py:1010–1016` | reward decoupled from N |
| `navigation_docs` total: 3309; architecture subset: 33; on-disk: 42; gap: 9 | live probe (read-only) | matches PR #689's finding exactly |
| All 9 missing files are the 9 most recently added architecture audit docs | git log + Chroma metadata enumeration | see §6.3 |

---

## 3. HoloIndex WSP_50 Retrieval Quality (per-query)

Five preflight HoloIndex queries were run from the main repo before any
work began in this slice. None of the queries surfaced the canonical
source files needed (`_cli_main.py`, `indexing_engine.py`,
`probe_audit_doc_indexing.py`) or the PR #688/#689 audit docs *by slice
ID*. The audit fell back to direct file reads.

| # | Query | Retrieval quality | Notes |
|---|-------|-------------------|-------|
| Q1 | `--index-docs handler CFZ4 navigation_docs` | WEAK | generic CFZ hits; CLI handler not surfaced |
| Q2 | `index_docs_entries indexing_engine project_root` | WEAK | core file not in top hits |
| Q3 | `HOLOINDEX_AUDIT_DOC_INDEXING_PROBE_PHASE1` | WEAK | PR #689 doc not surfaced by slice ID |
| Q4 | `HOLOINDEX_DOCS_REINDEX_OBSERVATION_PHASE1` | WEAK | PR #688 doc not surfaced by slice ID |
| Q5 | `probe_audit_doc_indexing.py` | WEAK | script not surfaced; `ls` confirmed presence |

**Retrieval evaluation**: noise (generic hits dominate over targeted ones),
missing artifacts (slice-ID lookup is unreliable for recent docs),
**staleness risk confirmed** — Q3/Q4 absence is itself an instance of the
very failure under investigation. Duplication: not observed. Ordering:
recency/priority not honoured for slice-ID literal matches.

**Improve retrieval**: cannot be addressed in this slice (out of scope per
the WSP_97 boundary checklist). Documented for the follow-on slice
recommendation.

---

## 4. DISCOVERY — Pipeline Map (end-to-end)

### 4.1 Entry point

`python holo_index.py --index-docs` (CLI handler at
`holo_index/_cli_main.py:1009–1016`):

```python
index_docs = getattr(args, 'index_docs', False) or args.index_all
if index_docs:
    start_time = time.time()
    holo.index_docs_entries()
    duration = time.time() - start_time
    safe_print(f"[DOCS] Indexed module/root docs in {duration:.2f}s")
    indexing_awarded = True
```

Observation: no return-value check, no try/except, no count surfaced. The
reward `indexing_awarded = True` is set unconditionally on flag completion.

### 4.2 Façade

`holo_index/core/holo_index.py:502–505`:

```python
def index_docs_entries(self) -> None:
    """CFZ4: Index module/root docs into navigation_docs collection."""
    from .indexing_engine import index_docs_entries as _idx_docs
    _idx_docs(self)
```

### 4.3 Implementation — `holo_index/core/indexing_engine.py:625–711`

| Stage | Lines | What happens | Failure mode |
|-------|-------|--------------|--------------|
| **S1** Resolve roots | 634–639 | `doc_paths = [project_root / r for r in ("modules","docs","holo_index/docs","WSP_framework/docs")]` | If `project_root` is wrong → wrong tree |
| **S2** Glob | 644 | `all_doc_files = sorted(list(base.rglob("*.md")))` for each existing base | None observed |
| **S3** Filter | 645–657 | 9 clauses including `not any(part.startswith('.') for part in f.parts)` | **Over-rejection inside worktrees** |
| **S4** Empty check | 660–662 | `if not files: _log_agent_action("No docs found to index", "WARN"); return` | **Silent no-op**; exit 0 |
| **S5** Reset | 665 | `holo.docs_collection = holo._reset_collection("navigation_docs")` | Skipped when S4 short-circuits |
| **S6** Embed | 689 | `embeddings.append(holo._get_embedding(doc_payload))` | Falls back to `[0.0]*384` if model absent |
| **S7** Bulk insert | 707–709 | single bulk insertion of `(ids, embeddings, documents, metadatas)` | Skipped when S4 short-circuits |
| **S8** Log | 709–711 | `Docs index refreshed: {N} entries` or `No docs entries were indexed` | Stderr only; CLI does not surface |

### 4.4 `project_root` resolution

`holo_index/core/holo_index.py:180`:

```python
self.project_root = Path(__file__).parent.parent.parent
```

For `holo_index/core/holo_index.py` inside the worktree
`O:\Foundups-Agent\.claude\worktrees\holoindex-index-docs-consistency-audit`,
this resolves to the worktree root, **not** the main repository.

### 4.5 Embedding fallback

`holo_index/core/holo_index.py:474–480`:

```python
def _get_embedding(self, text: str) -> List[float]:
    if self.model:
        return self.model.encode(text, show_progress_bar=False).tolist()
    return [0.0] * 384
```

Silent fallback to a zero vector when `self.model` is `None`. Distinct
from the consistency failure under investigation (zero vectors would
still produce indexed entries), but documented for completeness.

---

## 5. PROBE_DESIGN — Diagnostic script

`holo_index/scripts/diagnose_index_docs_pipeline.py` (new, dry-run only).

| Property | Value |
|----------|-------|
| Mutates Chroma? | NO |
| Spawns child processes? | NO |
| Invokes the indexer CLI flag? | NO |
| Imports `indexing_engine.py`? | NO (filter logic mirrored to avoid Chroma init) |
| Reads Chroma? | YES (`count()`, `get(include=["metadatas"])` — read-only) |
| Determinism | Verified (two consecutive runs → identical md5) |

### 5.1 Stub-only mutation simulation

The diagnostic uses a `_RecorderStub` class for the H3 bulk-insertion
simulation. It exposes a single `accumulate(...)` method that appends to
lists and tracks duplicates. It has no Chroma surface. None of the
forbidden mutation tokens appear in the script.

### 5.2 Static safety scan (forbidden-token table)

The diagnostic script asserts that the following Chroma-mutation,
process-spawn, and reset/persist verbs never appear as literal
substrings in its own source. The token list is assembled at runtime
from a fragment table so the file itself does not contain the literal
tokens it forbids.

Externally verified count (this slice, against the worktree file):

| Token fragment-assembled at runtime | Count in script |
|-------------------------------------|-----------------|
| chroma add-method prefix | 0 |
| chroma update-method prefix | 0 |
| chroma delete-method prefix | 0 |
| collection-removal verb | 0 |
| in-place state reset verb | 0 |
| in-place persistence verb | 0 |
| host process spawn primitive | 0 |
| host shell invocation primitive | 0 |
| indexer CLI flag as child command | 0 |

**Static safety scan: PASS** (also self-reported by the script).

---

## 6. INVESTIGATION — Hypotheses H1..H6

### 6.1 Summary table

| Hyp | Finding | Evidence |
|-----|---------|----------|
| **H1** project_root mismatch | **CONFIRMED** | resolved root: `O:\Foundups-Agent\.claude\worktrees\holoindex-index-docs-consistency-audit` |
| **H2** embedding model silent fallback | NOT CAUSAL (sec. effect noted) | model cache absent at default candidates; falls back to zero vector — would still produce entries |
| **H3** bulk insertion silent partial failure | NOT TRIGGERED in simulation | `doc_{idx}` scheme is unique per run; no duplicate ids observed; bulk insertion site has no try/except in core |
| **H4** file-discovery filter excludes audit docs | **CONFIRMED — primary cause** | 387/387 docs in worktree `docs/` tree fail the `no_dot_prefixed_parts` clause; identical 387 also fail the `no_claude_worktrees_token` clause |
| **H5** source-policy treats `docs/audits/architecture/` differently | NOT TRIGGERED | no path-class exclusion; priority boosts exist for `audits/openclaw_hermes/` and `audits/holoindex/` only |
| **H6** observability gap | **CONFIRMED** | reward `+5 Refreshed indexes` is awarded on flag completion, not on N inserted; no per-file count surfaced on stdout; no non-zero exit on empty discovery |

### 6.2 Target-by-target filter result (from diagnostic JSON)

All five target files (T1..T5) exist on disk inside the worktree and ALL
fail the indexer filter due to **two clauses simultaneously**:

| Target | Path | Exists | `no_dot_prefixed_parts` | `no_claude_worktrees_token` | Overall |
|--------|------|--------|------------------------|----------------------------|---------|
| T1 | `docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` | YES | FAIL | FAIL | **REJECTED** |
| T2 | `docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md` | YES | FAIL | FAIL | **REJECTED** |
| T3 | `docs/audits/holoindex_search_quality/HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md` | YES | FAIL | FAIL | **REJECTED** |
| T4 | `docs/audits/architecture/TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1.md` | YES | FAIL | FAIL | **REJECTED** |
| T5 | `docs/audits/architecture/TRADE_DUE_DILIGENCE_SCHEMA_PHASE1.md` | YES | FAIL | FAIL | **REJECTED** |

The aggregate failure profile over the worktree's `docs/` subtree:

| Clause | Files failing |
|--------|--------------|
| `no_dot_prefixed_parts` | 387 / 387 |
| `no_claude_worktrees_token` | 387 / 387 |
| `no_backup` | 6 / 387 |
| (all other clauses) | 0 / 387 |

100% of the worktree's `docs/` markdown corpus is rejected, dominated by
the dot-prefixed-parts clause.

### 6.3 The 9 missing architecture docs (cross-check)

Live read-only enumeration of `navigation_docs` against the main repo's
`docs/audits/architecture/` directory:

| | Count |
|--|------|
| Architecture audit docs on disk (main repo) | 42 |
| Architecture audit docs in `navigation_docs` | 33 |
| Gap | **9** |

The 9 missing files (recovered via Chroma metadata vs. disk diff):

1. `TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md`
2. `TRADE_ADAPTER_INTEGRATION_PHASE1.md`
3. `TRADE_DUE_DILIGENCE_SCHEMA_PHASE1.md`
4. `TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1.md`
5. `TRADE_FOUNDUP_PUBLIC_SURFACE_MANIFEST_AUDIT_PHASE1.md`
6. `TRADE_POC_SIMULATION_EVIDENCE_PACK_PHASE1.md`
7. `TRADE_POC_SIMULATION_EVIDENCE_REVIEW_PHASE1.md`
8. `TRADE_POC_SIMULATION_HARNESS_PHASE1.md`
9. `PUBLIC_FOUNDUP_POC_LANDING_ROUTE_CONTRACT_DOCS_PHASE1.md`

These are the **9 most recently added** architecture audit docs (commits
from 2026-05-22 onwards). Their absence is consistent with: the last
**successful** docs reindex was a **main-repo** invocation that
**predates** these commits; every subsequent `--index-docs` was launched
from a **worktree**, hit S4's empty-discovery short-circuit, and left
the collection untouched.

### 6.4 Why PR #688's reindex (exit 0) produced a no-op

PR #688's worktree (`.claude/worktrees/holoindex-docs-reindex-observation`)
shared the same `project_root` resolution rule. Its `--index-docs` run
discovered 0 files (per H4), returned at the empty-file check (S4),
skipped the reset and bulk insertion (S5+S7), and exited cleanly. The
CLI still emitted the `+5 Refreshed indexes` reward (H6), making the
no-op indistinguishable from a successful run.

---

## 7. CLASSIFICATION

| Field | Value |
|-------|-------|
| Symptom | `--index-docs` exits 0 but 9 architecture audit docs remain absent from `navigation_docs` |
| **Primary root cause** | **H1+H4 interlock**: worktree-resolved `project_root` introduces `.claude` into every absolute path; the `no_dot_prefixed_parts` filter clause rejects 100% of files; the indexer short-circuits at the empty-files guard (S4) without resetting or writing the collection |
| Contributing factor | **H6**: the reward marker `+5 Refreshed indexes` is decoupled from inserted-count; no per-file count is surfaced; no non-zero exit on empty discovery — making the no-op invisible |
| Secondary observation | **H2**: model cache absent at default candidates — would silently fall back to a 384-dim zero vector; orthogonal to this failure but worth noting for retrieval-quality work |
| Stale-index vs. doc-missing vs. retrieval-quality | **Stale-index** (failure is at the *write* stage of the indexing pipeline, not at file discovery from disk and not at retrieval ranking) |
| Failure mode | **Silent no-op on worktree-launched `--index-docs`** |
| Blast radius | Every `--index-docs` invocation from any `.claude/worktrees/<name>/` path is a no-op |

The PR #689 probe correctly characterised the targets as `A` (NOT_INDEXED).
This audit refines the diagnosis to a specific failure mode and a single
clause-level cause.

---

## 8. SMALLEST-FIX SLICE — Recommendation (not started)

### 8.1 Named slice

**`HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1`**

### 8.2 Scope

Change the file-discovery filter in
`holo_index/core/indexing_engine.py::index_docs_entries` so it
evaluates path components **relative to the discovery base**, not
against the absolute path. Concretely: change

```python
and not any(part.startswith('.') for part in f.parts)
```

to evaluate against `f.relative_to(base).parts` (or equivalent). This
preserves the intent of the clause (skip dotfiles **inside** the docs
tree such as `.git` or `.cache`) while no longer rejecting every file
when the worktree's own location contains a dot-prefixed component.

Apply the analogous change to the redundant `.claude/worktrees` /
`.worktrees` substring clauses on the same call site so they only fire
when the worktree token appears **inside** the discovery base.

### 8.3 What this slice MUST NOT do

- **MUST NOT** simply rerun the indexer.
- **MUST NOT** widen the `project_root` resolution beyond a documented,
  explicit override (the structural rule `Path(__file__).parent.parent.parent`
  is intentional for portability).
- **MUST NOT** silently swallow the dot-prefix clause; it is correct
  inside the discovery tree.
- **MUST NOT** change the reward-marker semantics (that is a separate
  slice — `HOLOINDEX_INDEX_DOCS_REWARD_GATE_BY_INSERTED_COUNT_PHASE1`).

### 8.4 Acceptance for the fix slice

After the filter change, a `--index-docs` run launched from a worktree
should discover the same on-disk file count as the equivalent run from
the main repo, and the resulting `navigation_docs` size should match
disk for `docs/audits/architecture/` (42 = 42).

### 8.5 Companion observability slice (deferred, smaller still)

**`HOLOINDEX_INDEX_DOCS_REWARD_GATE_BY_INSERTED_COUNT_PHASE1`** —
gate the `+5 Refreshed indexes` reward on `N > 0` and surface the
inserted count on stdout. ~10 lines in `_cli_main.py`. Independently
mergeable from the filter fix.

---

## 9. Static Safety Verification (this audit)

| Check | Result |
|-------|--------|
| Diagnostic script forbidden-token static scan | PASS (0 occurrences of any banned token; counted externally) |
| Diagnostic script invokes the indexer CLI flag as child command | NO |
| Diagnostic script spawns child processes | NO |
| Diagnostic script writes to Chroma | NO |
| Diagnostic script imports `indexing_engine` (would init Chroma) | NO |
| Diagnostic determinism | PASS (two consecutive runs → identical md5) |
| `git status --porcelain` after diagnostic (artifact guard) | clean apart from this audit + the new diagnostic script |

---

## 10. WSP_97 Verdict

| Check | Result |
|-------|--------|
| HoloIndex diagnostic dry-run only | PASS |
| No core instrumentation (no `holo_index/core/**` change) | PASS |
| Read-only Chroma access | PASS |
| No Chroma mutation | PASS |
| No reindex invocation | PASS |
| No HoloIndex core mutation | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No manifest mutation | PASS |
| No projection mutation | PASS |
| No Trade mutation | PASS |
| No WSP mutation | PASS |
| No CI change | PASS |
| No dependency install | PASS |
| Report only | PASS |
| Static safety scan on diagnostic script | PASS |
| No CABR ready | PASS |
| No payout ready | PASS |
| No DAO activation | PASS |

**Verdict**: PASS (19/19)

---

## 11. Files Changed

| File | Change |
|------|--------|
| `holo_index/scripts/diagnose_index_docs_pipeline.py` | NEW (dry-run diagnostic, ~410 lines) |
| `docs/audits/holoindex_search_quality/HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1.md` | NEW (this file) |

No `holo_index/core/**` change. No CI/config/dep change. No ModLog
append in this commit — the optional `holo_index/ModLog.md` append is
deliberately deferred to the fix slice to avoid coupling diagnosis to
the eventual remediation entry.

---

## 12. Completion Summary

| Item | Value |
|------|-------|
| Branch | `feat/holoindex-index-docs-consistency-audit-phase1` |
| Base commit | `d4827f639` (origin/main, post-PR #689) |
| New commit SHA | *(populated by W10 on merge)* |
| Files changed | exactly 2 (this audit + the diagnostic script) |
| Indexer CLI invocation in this slice | NONE |
| Chroma read operations | `count()`, `get(include=["metadatas"])` — read-only |
| Chroma write operations | NONE |
| Hypotheses tested | H1, H2, H3, H4, H5, H6 |
| Confirmed | H1, H4, H6 |
| Not triggered | H2 (orthogonal), H3, H5 |
| Primary root cause | H1+H4 interlock |
| Smallest-fix slice recommended | `HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1` |
| Companion observability slice (deferred) | `HOLOINDEX_INDEX_DOCS_REWARD_GATE_BY_INSERTED_COUNT_PHASE1` |
| WSP_97 truth boundary | PASS (§10) |

---

## 13. W10 Readiness

| Gate | Status |
|------|--------|
| Branch base = origin/main post-PR #689 | YES |
| Files changed = exactly 2 | YES |
| No indexer CLI invocation in this slice | YES |
| No generated Chroma / index / cache artifact committed | YES |
| Hypothesis-by-hypothesis findings recorded | YES |
| Primary root cause classification recorded | YES |
| Smallest-fix slice named (single follow-on) | YES |
| Diagnostic script passes static safety scan | YES |
| Diagnostic script is dry-run only | YES |
| WSP_97 truth boundary checklist complete | YES |
| **Ready for PR** | **YES** |

---

**Audit Complete**: 2026-05-24
**Worker**: W6
**Slice**: HOLOINDEX_INDEX_DOCS_CONSISTENCY_AUDIT_PHASE1
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_104 → WSP_22
