# HoloIndex Public Interface

## Scope
This document is the stable public contract for consuming HoloIndex programmatically and via CLI.
For exhaustive machine-level semantics, use:
- `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.md`
- `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json`

### Tool boundary (truth-recorded by PR #704)
HoloIndex is a **semantic retrieval system**. It **complements** `grep`/`glob`; it does not replace them. Choose the right tool for the query:

| Query shape | Use | Why |
|------------|-----|-----|
| Exact text / exact symbol (`pendingClassificationItem`) | `grep` / `rg` | Deterministic, fast, authoritative for literal matches |
| Known file path or glob (`modules/foundups/trade/**`) | `glob` / shell | Deterministic, path-native |
| Semantic / intent / role / WSP-alias / slice-ID (`"Trade pump.fun rug pull due diligence"`, `"WSP 97"`) | HoloIndex `--search` | Vector + keyword-boost recall over the indexed corpus |

HoloIndex has an internal ripgrep fallback (`_rg_symbol_search` inside `search_engine.py`) for in-search symbol probes, but that is an implementation detail of HoloIndex — it is not a substitute for invoking `grep`/`rg` directly when the user already knows the literal token.

Source-of-truth policy:
- Authoritative machine contract: `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json`
- Human-facing interface contract: this file
- Menu/operator atlas: `holo_index/CLI_REFERENCE.md` (non-normative)

## Programmatic API

### Core Retrieval
```python
from holo_index.core.holo_index import HoloIndex

holo = HoloIndex(ssd_path="E:/HoloIndex", quiet=True)
results = holo.search("send chat message", limit=5, doc_type_filter="all")
```

Storage resolution is deterministic:

1. explicit ssd_path / --ssd
2. HOLOINDEX_SSD_PATH
3. legacy HOLO_SSD_PATH
4. platform-safe absolute default

HOLOINDEX_QUERY_READONLY=1 requires an existing
vectors/chroma.sqlite3, never creates directories or collections, and never
writes the repository activity log. Storage failures raise
HoloIndexStorageError with one of the stable codes
HOLOINDEX_STORAGE_UNAVAILABLE, HOLOINDEX_STORAGE_NOT_WRITABLE,
HOLOINDEX_STORAGE_PATH_MISMATCH, or HOLOINDEX_COLLECTION_UNAVAILABLE.
ChromaDB itself is not a read-only database client. The supported RedDog
operational adapter uses the host-owned service at literal `127.0.0.1`, as
documented by modules/infrastructure/foundups_mcp_bridge/INTERFACE.md. This
adapter boundary is not an OS privilege boundary; host deployment must enforce
filesystem/process permissions separately when required. Legacy consumers,
including foundups_mcp_bridge `holo_tools.py`, remain outside this Phase-1
migration and may still open the store directly.

Linked-worktree owner queries keep repository evidence and dependency
ownership separate. Repository bytes come from the selected clean exact-HEAD
authority checkout. Python dependencies come from the primary worktree
derived from the same Git common directory and are still validated by the
checkout-local virtualenv contract. Failure to prove that relationship falls
back to the caller workspace and therefore fails closed when no valid runtime
exists. The resolver never checks out, updates, or indexes either worktree.

Search response contract:

The JSON machine specification is authoritative. Its complete response schema
is structurally compiled by `holo_index.query_result_contract_schema` and
enforced by `holo_index.query_result_contract`: successful owner
consumers require the exact response and metadata key sets, per-bucket hit
schemas, alias/count/query agreement, finite typed ranking fields, and
canonical collection/backend mappings before evidence can be projected or
cited. Malformed structures and rule declarations fail with one stable
contract-invalid boundary before owner startup. The machine specification is
content-bound in the RedDog runtime manifest, so a missing or modified
authority fails compatibility.

```python
{
  "code_hits": [
    {
      "need": str,
      "location": str,
      "similarity": "85.1%",
      "type": str,
      "priority": int,
      "path": str | None,
      "line": int | None,
      "preview": str | None,
      "cube": str | None,
    }
  ],
  "wsp_hits": [
    {
      "wsp": str,
      "title": str,
      "summary": str,
      "path": str,
      "similarity": "82.3%",
      "type": str,
      "priority": int,
      "cube": str | None,
    }
  ],
  "test_hits": list,

  # Backward-compatible aliases
  "code": list,
  "wsps": list,
  "tests": list,

  "skills": list,
  "skill_hits": list,
  "symbol_hits": list,
  "metadata": {
    "query": str,
    "code_count": int,
    "wsp_count": int,
    "test_count": int,
    "skill_count": int,
    "symbol_count": int,
    "timestamp": str,
    "cached": bool,
  }
}
```

### Indexing Methods
```python
holo.index_code_entries()
holo.index_symbol_entries()
holo.index_wsp_entries()
holo.index_test_registry()
holo.index_skillz_entries()
```

Each indexing method returns IndexResult. A zero/invalid test registry does
not reset navigation_tests. The canonical
WSP_knowledge/WSP_Test_Registry.json envelope is read from its tests list;
legacy mapping-only registries remain supported during migration. Any
malformed row in a mixed registry fails the result before embeddings or reset;
it cannot be silently filtered from a complete proof.

Scoped maintenance receipts must name only successfully refreshed
collections. Untouched collection proof is carried forward with its original
repository SHA, or marked UNVERIFIED when no prior proof exists.

Mutation owners use MaintenanceSession (CLI) or the incremental executor to
prove a clean Git worktree, acquire the canonical cross-process lease, and
publish atomic IN_PROGRESS invalidation before collection access. Final PASS
requires the same clean HEAD, exact declared collection scope, non-empty
manifests, the canonical source_scope_id for every baseline collection, zero
recorded source-read, cap, or Python-AST failures, and a durable atomic receipt
write. Canonical proofs cover Git-tracked sources and full raw source content.
They do not assert zero failures for every legacy format parser. Query
consumers fail closed
with HOLOINDEX_MAINTENANCE_ACTIVE or
HOLOINDEX_MAINTENANCE_LOCK_UNPROVEN.

Generation publication additionally requires the pinned HNSW collection
configuration and a complete persisted artifact set for each baseline vector
segment. This proof reads Chroma's SQLite catalog and segment files without
loading pickle content or invoking a mutation API. Missing policy or files
returns VECTOR_SEGMENT_UNAVAILABLE before snapshot comparison. Repeated
successful process opens do not override this durability failure.

### Module Compliance Helper
```python
status = holo.check_module_exists("modules/communication/livechat")
```

Returns:
- `exists`, `path`, `module_name`
- doc/test presence booleans
- `wsp_compliance`, `compliance_score`, `health_warnings`, `recommendation`

### HoloDAE Coordinator API
```python
from holo_index.qwen_advisor import start_holodae, stop_holodae, get_holodae_status

start_holodae()
status = get_holodae_status()
stop_holodae()
```

## CLI API

### Retrieval
```bash
python holo_index.py --search "query" --limit 5
python holo_index.py --search "query" --doc-type code
python holo_index.py --search "query" --fast-search
```

### Indexing
```bash
python holo_index.py --index-all
python holo_index.py --index-code
python holo_index.py --index-wsp
python holo_index.py --index-tests
python holo_index.py --index-symbols --symbol-roots modules/foundups
python holo_index.py --index-skillz
```

--index is an exact alias for --index-all. The baseline set is code, symbols,
WSP, tests, skills, docs, and knowledge. Work-ledger and CLI-catalog
generation remain explicit targeted operations and are not implied by
--index-all.

Canonical --index-all fixes its symbol roots to modules, scripts, and
holo_index; its WSP root to WSP_framework/src; and its web root/extensions to
the versioned source-scope contract. Scoped roots, file/entry caps, disabled
web indexing, or unreadable sources are diagnostic/incomplete and cannot
publish CURRENT baseline proof. Semantic backend initialization is required
before any baseline collection reset.

### Machine Bundle Output
```bash
python holo_index.py --bundle-json --search "task" --bundle-module-hint modules/foundups/agent_market
```

Bundle schema ID: `wsp_memory_bundle_v1`

Persistent `--search` and `--bundle-json` requests are admitted before backend
construction only when the freshness receipt proves the invoking repository
root, resolved SSD, clean exact HEAD, generation, complete canonical baseline,
embedding space, and no active/unprovable maintenance. A denied raw CLI search
exits with code `4`; JSON bundle denial returns content-free `error`,
`stale_reasons`, and `index_gap_detected` fields. Offline/fast lexical mode
does not open or read the persistent store and reports degraded/UNKNOWN
freshness. Raw CLI and bundle lexical paths share the same root-confined,
bounded, no-follow loader. Oversize NAVIGATION is rejected. WSP metadata is
repository-local and the supplied SSD is not a lexical metadata source.
Persistent admission reads only the canonical
`freshness_receipt_path(ssd)`. An explicit receipt argument must resolve to
that exact stable-ancestor identity, and a final symlink/reparse point is
rejected before receipt or backend access.
`rehydrate_canonical_freshness_proof()` exposes the same gate for a caller
that already holds an expected 40-character repository SHA. It rejects a
malformed or mismatched expected SHA before receipt loading and returns only
the existing `ReadonlyQueryAdmission` binding; it never starts an owner,
opens Chroma, writes a receipt, or reindexes.

HoloIndex also exposes a separate authority-update lease beside the canonical
maintenance lease. WRE may hold the outer lease while changing a dedicated
authority checkout; `MaintenanceSession` independently owns the inner SSD
writer lease and atomic freshness publication.
The fixed `.holoindex_authority_blocked` marker is a durable fail-closed
fallback when neither a newer checkout nor canonical invalidation can be
published. Only exact regular marker content is recognized for recovery.

Module hints accept only repository-relative components. Traversal, absolute
paths, links, and reparse points are rejected; nested enumeration has fixed
entry/depth bounds. Module-domain and WSP discovery fail closed on `cap + 1`
rather than selecting a partial directory prefix. Nested module-file
enumeration is complete-or-empty: entry overflow, depth overflow, or a scan
error returns no module-file evidence, and a complete set is sorted before
selection.

### Monitoring / Orchestration
```bash
python holo_index.py --start-holodae
python holo_index.py --stop-holodae
python holo_index.py --holodae-status
```

### Compliance / Diagnostics
```bash
python holo_index.py --check-module "livechat"
python holo_index.py --check-wsp-docs
python holo_index.py --fix-ascii --check-wsp-docs
python holo_index.py --system-check
python holo_index.py --health-check
```

## Environment Controls (Selected)
- `HOLO_OFFLINE=1`: disable model downloads/auto-install.
- `HOLO_SKIP_MODEL=1`: force lexical retrieval path.
- `HOLO_MIN_SIMILARITY=0.35`: vector hit floor.
- `HOLO_FAST_SEARCH=1`: retrieval-only fast path.
- `HOLO_INDEX_WEB=1`: include web assets during a targeted diagnostic
  `--index-code`; trusted baseline maintenance uses the canonical tracked web
  scope and does not accept this override.
- `HOLO_SYMBOL_AUTO=1`: auto symbol indexing during `--index-code`.

- HOLOINDEX_SSD_PATH: canonical persistent store root.
- HOLO_SSD_PATH: legacy store-root alias, lower precedence.
- HOLOINDEX_QUERY_READONLY=1: fail-closed query posture; no HoloIndex maintenance writes.

## Internal CLI Module Layout

The monolithic `cli.py` has been restructured into a package:

```
holo_index/
  _cli_main.py              # Entrypoint (argparse, search, indexing, advisor)
  cli/
    __init__.py              # Backward-compat shim — re-exports main, HoloIndex, QwenAdvisor
    commands/
      __init__.py            # Package marker
      bundle_json.py         # --bundle-json handler
      compliance.py          # --wsp88, --audit-docs, --check-module, --check-wsp-docs,
                             #   --rollback-ascii, --fix-violations, --docs-file
      holodae.py             # --start/stop/status-holodae, --pattern-coach, --module-analysis,
                             #   --health-check, --performance-metrics, --system-check,
                             #   --slow-mode, --pattern-memory, --mcp-hooks/log, --thought-log,
                             #   --monitor-work
      modules_cmd.py         # --link-modules, --query-modules, --wsp, --list-modules
```

All public imports remain stable:
```python
from holo_index.cli import main          # entrypoint
from holo_index.cli import HoloIndex     # core class
from holo_index.cli import QwenAdvisor   # advisor (may be None)
```

## Core Module Layout

```
holo_index/core/
  __init__.py              # Exports HoloIndex, SearchCache, get_search_cache
  holo_index.py            # HoloIndex class — bootstrap, collection helpers, thin delegates
  search_engine.py         # Extracted search surface — execute_search() entry point
  indexing_engine.py       # Extracted indexing surface — index_*() orchestrators
  introspection_engine.py  # Module compliance, preview enrichment, TS entity parsing
  search_cache.py          # LRU+TTL search cache
```

`HoloIndex.search()` delegates to `search_engine.execute_search(holo, ...)`.
All search logic (vector, lexical, ripgrep symbol, hit merging) lives in `search_engine.py`.

`HoloIndex.index_*()` methods delegate to `indexing_engine.index_*(holo, ...)`.
All indexing orchestrators, document classification, and web asset collection live in `indexing_engine.py`.

`HoloIndex.check_module_exists()` and preview enrichment delegate to `introspection_engine`.
`parse_typescript_entities` is re-exported from `holo_index.py` for import stability.

The public API (`holo.search(query)`, `holo.index_code_entries()`, `holo.check_module_exists()`, etc.) is unchanged.

## Compatibility Notes
- `code` / `wsps` keys remain present for backward compatibility.
- `search()` degrades to lexical mode when embedding model is unavailable.
- `CLI_REFERENCE.md` is a menu snapshot; use this file + machine spec JSON for exhaustive contracts.
