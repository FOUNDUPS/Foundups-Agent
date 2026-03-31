# HoloIndex Public Interface

## Scope
This document is the stable public contract for consuming HoloIndex programmatically and via CLI.
For exhaustive machine-level semantics, use:
- `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.md`
- `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json`

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

Search response contract:
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
python holo_index.py --index-symbols --symbol-roots modules/foundups
python holo_index.py --index-skillz
```

### Machine Bundle Output
```bash
python holo_index.py --bundle-json --search "task" --bundle-module-hint modules/foundups/agent_market
```

Bundle schema ID: `wsp_memory_bundle_v1`

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
- `HOLO_INDEX_WEB=1`: include web assets during `--index-code`.
- `HOLO_SYMBOL_AUTO=1`: auto symbol indexing during `--index-code`.

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
