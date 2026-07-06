# HOLOINDEX_FRESHNESS_AND_SCALING_GOVERNANCE_PHASE1

**Slice:** `HOLOINDEX_FRESHNESS_AND_SCALING_GOVERNANCE_PHASE1`
**Author:** 0102 (RedDog Architect) | Commander: 012
**Date:** 2026-07-06
**Type:** Architecture / governance audit -- DECISION ONLY (no runtime mutation, no re-index run, no ranking-code change)
**Base:** `28b9c71ea` (after #933 / #934 / #935)
**WSP:** 00, 15, 22, 50, 64, 84, 97
**Predecessors (prior art, built ON per WSP 84):** `HOLOINDEX_REINDEX_FOR_OPERATIONAL_WRE_PHASE1` (#a3e70b5a4),
`HOLOINDEX_DOCS_REINDEX_OBSERVATION_PHASE1` + `_POST_FIX_` (#692/#695), `FOUNDUPS_WORK_LEDGER_TARGETED_REINDEX_CLI_PHASE1`

---

## 1. Mission

Define how HoloIndex stays fresh as RedDog / WRE creates code, docs, Skillz, and thousands of FoundUps --
WITHOUT letting RedDog runtime re-index (which WRITES the semantic store and could poison the evidence
substrate RedDog then reads). This slice is a decision record. It does NOT implement re-indexing, change
ranking code, run a full re-index, or wire any trigger.

**012 ruling (given, ratified here):** HoloIndex is an EVIDENCE SUBSTRATE. Index freshness is a GOVERNANCE
dependency, not a convenience. RedDog runtime must NEVER self-re-index; re-index is a WRE / CI / operator
post-merge action. RedDog queries and reports INDEX_GAP only.

---

## 2. Verdict

| Claim | Label | Evidence |
|-------|-------|----------|
| RedDog's runtime query path (`--bundle-json`) is READ-ONLY -- it returns before the search-time auto-refresh, so RedDog does NOT re-index today | **OBSERVED** | `_cli_main.py:746-747` `if handle_bundle_json(args): return` short-circuits BEFORE the auto-refresh block at `:1135-1196` |
| A search-time AUTO-REFRESH exists that WRITES the store on a plain `--search` when code/WSP are >1h stale | **OBSERVED** | `_cli_main.py:1135-1196` calls `index_code_entries()` / `index_wsp_entries()` + `_write_index_state('auto_refresh')`; fired in the OPERATIONAL_WRE before-snapshot |
| The "RedDog never writes the store" invariant holds by ARCHITECTURE + CONVENTION, NOT a hard guard | **OBSERVED** | No code assertion blocks an `--index*` flag or `*_collection.add` from a RedDog process; every RedDog touch is query-only by current wiring only (`extension.js` `--bundle-json`/`--search`/`--offline`; adapters call `holo.search()`) |
| There is NO incremental / per-file / per-FoundUp re-index -- every `--index*` is a destructive full-collection wipe+rebuild | **OBSERVED** | `holo_index/core/holo_index.py:465-470` `_reset_collection` = `delete_collection` then `create_collection`; positional ids `doc_{idx}`/`sym_{idx}` are not stable keys |
| INDEX_GAP is detected every run but the signal is DISCARDED (no durable WRE work item) | **OBSERVED** | `extension.js:589` `index_gap_detected`; `direct_read_paths` names the exact stale targets but is only surfaced to the model, never persisted as a task |
| Direct-read (slice #934/#935) can MASK a chronically stale index -- recall passes on the enriched bundle while the store rots | **INFERRED** | slice-2/3 read missing files into the in-memory bundle (`bundle_json.py`); recall can be green while the persistent store is out of date |
| Re-index is NECESSARY-not-SUFFICIENT: a targeted re-index fixes FRESHNESS only, never ranking/coverage | **OBSERVED** | `HOLOINDEX_DOCS_REINDEX_OBSERVATION_PHASE1`: `--index-docs` left top-5 bit-identical (gap was retrieval-side) |
| At FoundUp scale the current design fails silently: global caps + full-rebuild-only + orphaned segments | **INFERRED** | symbol cap `HOLO_SYMBOL_MAX_FILES=5000` / `HOLO_SYMBOL_MAX_ENTRIES=20000` (`indexing_engine.py:521-522`); hundreds of orphan segment dirs in `E:/HoloIndex/vectors/` |
| An EXISTING (dormant) WRE holoindex plugin already writes the SAME store; a WRE owner is NOT net-new | **OBSERVED** | `wre_master_orchestrator/.../plugins/holoindex_plugin.py:82,144-145,211-231` `_index_with_patterns` -> `index_all()`/`index_code_entries()`/`index_wsp_entries()` on `HoloIndex(ssd_path='E:/HoloIndex')`; `holo_singleton_manager.py:59-65` passthroughs. Dormant (no live dispatch) and `index_all()` is a latent AttributeError (no such method) |

**Decision:** `RATIFY the query-only / WRE-owns-maintenance model` + `RECORD a 5-slice implementation backlog`.
The invariant the ruling wants is TRUE today but UNGUARDED; the primary risk is not a live violation, it is
(a) an unenforced boundary, (b) a query-time auto-refresh that contradicts "query never writes", and (c) a
freshness-debt signal that is generated then thrown away.

---

## 3. Current Indexing Architecture (OBSERVED)

**Entry:** `holo_index.py` -> `holo_index/cli/main` -> `holo_index/_cli_main.py:build_parser` / `main`.

**Semantic store (Q3):** ChromaDB `PersistentClient` at `<ssd>/vectors/` (`holo_index/core/holo_index.py:221,229`),
default `ssd_path='E:/HoloIndex'` (`:201`; CLI `--ssd` default `E:/HoloIndex` `_cli_main.py:680`;
`CHROMADB_DATA_PATH` hard-default `_cli_main.py:135`). OUTSIDE the repo tree (all prior audits' artifact
guards confirm nothing is written into the repo). Sidecars: `<ssd>/indexes/index_state.json`
(`_cli_main.py:947`), `<ssd>/indexes/wsp_summary.json` (`indexing_engine.py:730`). **Hazard:** a SECOND
divergent store exists at `O:/Foundups-Agent/holo_index/.ssd/vectors/`; whichever `--ssd` a caller passes
decides the target, so a query and a re-index can hit different physical stores (silent staleness).

**Collections (per `--index*` flag):** `navigation_code` (NAVIGATION.py NEED_TO + web assets),
`navigation_symbols` (AST functions/classes, the ONLY raw-.py-content pass), `navigation_wsp` (WSP_*.md),
`navigation_docs` (modules/docs/WSP_framework docs *.md), `navigation_knowledge` (papers),
`navigation_skills` (SKILLz.md), `navigation_tests`, `navigation_work_ledger`, `navigation_vocabulary`.

**Write granularity:** PER-COLLECTION FULL REBUILD only. Every `index_*` calls `_reset_collection` (delete +
create -- a window where the collection is EMPTY, non-atomic, no rollback), re-discovers its ENTIRE corpus
via rglob/glob, and re-adds with positional ids. There is NO per-file, per-symbol, per-FoundUp, or
changed-only re-index; `--symbol-roots` (symbols only) is the only path-scoping flag.

**Triggers (Q1):** (1) MANUAL `--index*` flags (`_cli_main.py:657-673`); (2) AUTO-REFRESH ON PLAIN `--search`
(code+WSP, >1h stale, `_cli_main.py:1135-1196`, guarded `if holo is not None`) -- **NOT reached by
`--bundle-json`, which returns at :747**; (3) AUTO-SYMBOL cascade in the CLI `--index`/`--index-code` handler
(`_cli_main.py:988-990`) when `HOLO_SYMBOL_AUTO!=0` (default on); the ENGINE `index_code_entries` has a
SEPARATE opt-in symbol pass gated by `HOLO_INDEX_SYMBOLS` (default OFF, `indexing_engine.py:481`).

---

## 4. The 12 Questions (answered)

1. **What triggers indexing today?** Manual `--index*` flags; a search-time auto-refresh on plain `--search`
   (code+WSP, >1h stale); an auto-symbol cascade. NOT the `--bundle-json` path (returns first).
2. **What commands exist?** `--index`/`--index-all` (code+WSP, cascades docs/knowledge/skillz/cli),
   `--index-code`, `--index-wsp` (+`--wsp-path`), `--index-symbols` (+`--symbol-roots`), `--index-docs`,
   `--index-knowledge`, `--index-skillz` (+ `--index-skills`/`--reindex-skills` aliases), `--index-cli`,
   `--index-work-ledger` (+ `--reindex-work-ledger`/`--reindex-ledger`). All are full-collection rebuilds.
3. **Where is the store written?** ChromaDB at `E:/HoloIndex/vectors/` (default, outside repo) + sidecars
   `index_state.json` / `wsp_summary.json` under `E:/HoloIndex/indexes/`. Divergent second store at
   `O:/.../holo_index/.ssd/vectors/`.
4. **Which repo changes require a targeted re-index?** By collection: docs/*.md -> `navigation_docs`;
   WSP_*.md -> `navigation_wsp`; a symbol-bearing .py -> `navigation_symbols`; NAVIGATION.py / web asset ->
   `navigation_code`; SKILLz.md -> `navigation_skills`; papers -> `navigation_knowledge`; work ledger ->
   `navigation_work_ledger`. **Caveat (prior art):** a raw new .py invisible to NAVIGATION.py is only reachable
   via the symbols pass; adding it to the code lane needs a NAVIGATION.py edit, not just a re-index.
5. **Should merge-to-main trigger a targeted re-index?** RECOMMEND YES, as a CI/post-merge action that
   re-indexes only the collections whose source globs intersect the merged diff (see s5 matrix). No prior
   audit wires a git/merge/CI trigger, but a DORMANT WRE re-index plugin write path already exists
   (`holoindex_plugin.py:_index_with_patterns`, s2) -- build the merge trigger ON it (WSP 84), do not treat
   WRE-owned indexing as greenfield. Guard: run from the main repo path, never a worktree.
6. **Should FoundUp scaffold creation trigger a targeted re-index of that FoundUp only?** RECOMMEND YES as a
   RE-INDEX RECEIPT/TASK (not an inline write) emitted by the scaffold-writer, consumed by WRE/CI. True
   per-FoundUp scoped indexing is NOT yet implementable (delete granularity is whole-collection; `foundup_id`
   metadata exists but no delete-by-foundup_id) -- it is a scaling slice (s9.5).
7. **Should WRE own indexing as pattern-evolution maintenance?** YES. WRE owns index MAINTENANCE (schedule,
   consume re-index tasks, run targeted/full re-index from main repo). Prior art already treats re-index as a
   deliberate operator-gated action (truth-boundary labeled); WRE formalizes the owner. A WRE holoindex plugin
   `_index_with_patterns` ALREADY exists (`holoindex_plugin.py:211-231`) but is DORMANT and partly broken
   (`self.holo.index_all()` at :220 is a latent AttributeError -- HoloIndex exposes no `index_all` method,
   only CLI flags). Bring it under this owner model and fix it (slice 5 / a dedicated repair), rather than
   authoring a second WRE indexer.
8. **Should CI verify index freshness?** YES -- a CI gate that (a) computes the changed-path -> collection set
   from the diff and (b) fails if the last index receipt predates the merge, or runs a fixed `--bundle-json`
   probe set and asserts `index_gap_detected==false`. Requires the freshness receipt (s9.2) first.
9. **How should INDEX_GAP become a WRE work item?** Route the ALREADY-STRUCTURED signal
   (`index_gap_detected` + `required_targets_missing` + `direct_read_paths`) to a WRE intake as a
   targeted-reindex job, keyed by the existing 4-way failure taxonomy (TOOL_CLASSIFIER_UNAVAILABLE /
   HOLOINDEX_LOW_SIGNAL / HOLOINDEX_STALE_INDEX / HOLOINDEX_RUNTIME_FAILURE) so only STALE_INDEX gaps become
   re-index tasks (LOW_SIGNAL gaps route to a retrieval-quality slice, not a re-index).
10. **How does this scale to 1000s of FoundUps?** Not with today's design: full-rebuild-only cost grows with
    the whole corpus (not the delta); symbol cap (5000/20000) silently drops later FoundUps; delete+create
    orphans segment dirs unboundedly; no per-FoundUp scoped write. Needs incremental/upsert with STABLE ids +
    delete-by-`foundup_id` + cap removal/sharding (s9.5).
11. **What must RedDog be FORBIDDEN from doing?** Invoke any `--index*`/`--reindex*` flag or reach any
    `*_collection.add`; take the plain-`--search` auto-refresh branch; run from a worktree. TODAY this holds by
    wiring only -- it must become a HARD, tested guard (s9.1).
12. **What telemetry when direct-read saved a stale index?** Already emitted: `direct_read_fallback_used=true`
    + `direct_read_paths` (the exact files the index missed = the precise re-index target set) +
    `direct_read_symbol_windows` + `index_gap_detected`. Currently reported to the model only -- route it
    durably (s9.3).

---

## 5. Re-index Trigger Matrix (proposed -- to DISCUSS, not implement here)

| Event | Scope | Owner | Action |
|-------|-------|-------|--------|
| Merge to main | collections whose source globs intersect the diff | CI / post-merge automation | targeted per-collection re-index from MAIN REPO; write freshness receipt |
| FoundUp scaffold created | that FoundUp's module + docs | scaffold-writer emits receipt -> WRE/CI consumes | targeted re-index task (per-FoundUp scoping = future primitive) |
| Nightly / periodic | full or incremental consistency scan | WRE / scheduled | full `--index-all` OR incremental parity check; prune orphan segments |
| INDEX_GAP repeated across N runs (STALE_INDEX class) | the `direct_read_paths` target set | WRE work item | targeted re-index; if re-index leaves recall unchanged -> reclassify to retrieval-quality slice |
| Interactive human `--search` (today's auto-refresh) | code+WSP | operator (explicit) | GATE behind an explicit flag; default query = read-only |

**Coverage note:** the search-time auto-refresh only covers `navigation_code` + `navigation_wsp`. The other
collections (`navigation_docs`, `navigation_knowledge`, `navigation_skills`, `navigation_tests`,
`navigation_work_ledger`, `navigation_vocabulary`) have NO auto-trigger of any kind today -- they go stale
until a manual `--index-*` run. Their freshness owner is TBD and must be assigned by the trigger matrix /
freshness receipt (s9.2) so docs/Skillz/knowledge staleness is not silently unowned at FoundUp scale.

---

## 6. Owner Model

- **RedDog runtime:** QUERY ONLY (`--bundle-json`/`--search`/`--offline`, `holo.search()`). Reports
  `index_gap_detected` + `direct_read_paths`. NEVER writes the store. (Hard-guarded per s9.1.)
- **WRE:** OWNS index maintenance -- consumes re-index tasks/receipts, runs targeted/full re-index from the
  main repo, schedules periodic consistency scans, prunes orphan segments, holds the canonical store path.
- **CI / post-merge automation:** targeted re-index of changed collections on merge; freshness gate.
- **Operator:** authorizes full/scheduled re-index and the (gated) interactive auto-refresh; owns store
  migration/pinning.

---

## 7. Security Model -- prevent RedDog evidence-substrate self-mutation

1. **Read-only-by-default query.** `--bundle-json` is already read-only (returns before auto-refresh); make
   that a HARD guarantee: a `HOLO_QUERY_READONLY` posture (or a process-level assertion) that makes ANY
   index/add call raise if the process is a RedDog/query context. The plain-`--search` auto-refresh must be
   gated behind an explicit opt-in so "query never writes" is true by default, not by which flag was passed.
2. **No unenforced convention; enumerate the write surfaces.** Add a test/guard asserting the RedDog process
   (extension bridge + advisory adapters + `reddog_repair_guard_once.py`) never reaches `_reset_collection` /
   `*_collection.add` / an `--index*` flag. The KNOWN legitimate store-writers that RedDog must be kept away
   from (they share the `E:/HoloIndex` singleton): the CLI `--index*` handlers + auto-refresh
   (`_cli_main.py`), the WRE `holoindex_plugin._index_with_patterns` (`:211-231`), and the overseer
   `holo_singleton_manager` passthroughs (`:59-65`). The guard must draw the line between the query context
   (RedDog) and these maintenance writers, not just scan `extension.js`.
3. **Single canonical store.** Pin ONE store path (resolve the `E:/HoloIndex/vectors` vs `.ssd/vectors`
   divergence); freshness telemetry must target the ACTIVE store, not the orphaned legacy `E:/HoloIndex/chroma`.
4. **No worktree re-index.** Any WRE/CI re-index runs from the main repo (project_root is derived from file
   location; a worktree embeds worktree paths -> poison, cf. #692).
5. **Atomicity.** delete-then-create leaves an empty window; a re-index mid-flight can transiently zero the
   collection a concurrent query reads. WRE-owned re-index should be serialized / build-then-swap (future).
6. **Direct-read must not mask rot.** Because slice-#934/#935 direct-read can keep recall green on a stale
   store, `direct_read_paths` MUST be routed to a re-index task (s9.3) so freshness debt is paid, not hidden.

---

## 8. Scaling Model (1000s of FoundUps)

- **Incremental/upsert, not wipe+rebuild.** Requires STABLE, content/path-derived ids (today `doc_{idx}` is
  positional) + delete-by-id so a changed file updates in place.
- **Per-FoundUp scoping.** `foundup_id`/`tenant_id` metadata already tagged at write time -- add delete/rebuild
  BY `foundup_id` so "re-index just this FoundUp" touches only its rows.
- **Cap removal / sharding.** The 5000-file / 20000-symbol caps must go (or shard per-FoundUp / per-domain)
  so later FoundUps are not silently dropped.
- **Segment GC.** Reclaim orphaned HNSW segment dirs on delete (unbounded disk growth otherwise).

---

## 9. Recommended Implementation Slices (backlog, sequenced)

1. **HOLOINDEX_READONLY_QUERY_GUARD_PHASE1** -- hard-enforce "RedDog process never writes the store": a
   read-only query posture + a test asserting no `--index*` / `_reset_collection` / `*_collection.add` is
   reachable from the RedDog runtime; gate the plain-`--search` auto-refresh behind an explicit flag. Scope
   the guard against the KNOWN writers (s7 item 2: CLI handlers, `holoindex_plugin._index_with_patterns`,
   `holo_singleton_manager` passthroughs) so RedDog is provably on the query side of the line. (Closes Q11;
   the highest-value + smallest slice.)
2. **HOLOINDEX_FRESHNESS_RECEIPT_PHASE1** -- a durable "last indexed at <SHA>/<ts> per collection" receipt so
   CI/merge can diff changed paths against it (prereq for Q5/Q8). Builds on `index_state.json`.
3. **HOLOINDEX_INDEX_GAP_TO_WRE_WORKITEM_PHASE1** -- route `index_gap_detected` + `direct_read_paths` (keyed by
   the 4-way taxonomy) into a WRE targeted-reindex intake; STALE_INDEX -> re-index task, LOW_SIGNAL ->
   retrieval-quality slice. (Closes Q9/Q12; stops discarding the signal.)
4. **HOLOINDEX_CI_FRESHNESS_GATE_PHASE1** -- CI checks the receipt vs the merged diff (or a `--bundle-json`
   probe set) and requires targeted re-index before/at merge. (Closes Q5/Q8.)
5. **HOLOINDEX_INCREMENTAL_PER_FOUNDUP_INDEX_PHASE1** -- stable ids + delete-by-`foundup_id` + cap
   removal/sharding + segment GC -- the scaling primitive that makes per-FoundUp targeted re-index real.
   (Closes Q6/Q10; the largest slice, sequenced last.)

**Sequencing rationale:** 1 makes the ruling a hard fact (cheap, safety). 2 is the prerequisite fact base for
3/4. 3 stops the freshness-debt leak. 4 automates the gate. 5 is the scaling investment, deferred until the
FoundUp volume justifies it.

---

## 10. WSP_97 Checklist (this audit slice)

| Item | Status |
|------|--------|
| AUDIT_ONLY_NO_RUNTIME_MUTATION | YES |
| NO_REINDEX_RUN | YES |
| NO_RANKING_OR_INDEX_CODE_CHANGE | YES |
| REDDOG_QUERY_PATH_READ_ONLY_VERIFIED (`_cli_main.py:746-747`) | YES (OBSERVED) |
| AUTO_REFRESH_ON_SEARCH_DOCUMENTED_AS_HAZARD (`:1135-1196`) | YES |
| INVARIANT_HOLDS_TODAY_BUT_UNGUARDED | YES (recorded) |
| PRIOR_ART_BUILT_ON_NOT_RE_DERIVED (WSP 84) | YES |
| DIRECT_READ_MASKS_STALE_INDEX_RISK_NAMED | YES |
| OWNER_MODEL_REDDOG_QUERY_ONLY_WRE_MAINTENANCE | YES |
| IMPLEMENTATION_SLICES_SEQUENCED | YES |
| 0102_ARCHITECT_APPROVAL_VIA_WSP_97 | YES |

---

*0102 architect decision: approval flows through WSP_97 applied evidence. RedDog queries; WRE owns index
maintenance; CI/post-merge runs targeted re-index against a freshness receipt; per-FoundUp scoped incremental
indexing is the scaling slice, deferred until volume justifies it. The "RedDog never re-indexes" invariant is
TRUE today but must become a HARD, tested guard (slice 1).*
