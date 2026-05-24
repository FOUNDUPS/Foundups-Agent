# HoloIndex CodeIndex Retrieval System Audit — Phase 1

**Slice**: `HOLOINDEX_CODEINDEX_RETRIEVAL_SYSTEM_AUDIT_PHASE1`
**Worker**: W6
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Audit (read-only, docs-only)
**Branch**: `docs/holoindex-codeindex-retrieval-system-audit-phase1`
**Base commit**: `778d4bc97` (origin/main, post-PR #703)
**WSP Lock**: WSP_00 → WSP_50 → WSP_87 → WSP_97

---

## A. Mission + Scope Statement

This slice answers two architect questions:
1. **Is HoloIndex a retrieval system?**
2. **Does HoloIndex replace grep/glob?**

This is an **audit-only** slice. No code changes, no test changes, no indexing changes. The output is this document with evidence.

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| AUDIT_ONLY | YES |
| DOCS_ONLY | YES |
| NO_CODE_MUTATION | YES |
| NO_TEST_MUTATION | YES |
| NO_INDEX_MUTATION | YES |
| NO_COLLECTION_MUTATION | YES |
| NO_DEPENDENCY_CHANGE | YES |

**Verdict**: PASS (7/7)

---

## B. Executive Summary

### B.1 Is HoloIndex a Retrieval System?

**YES** — HoloIndex is a **semantic retrieval system** implementing:

| Component | Technology | Evidence |
|-----------|------------|----------|
| Vector Store | ChromaDB PersistentClient | `holo_index/core/holo_index.py:190` |
| Embedding Model | SentenceTransformer (all-MiniLM-L6-v2) | `holo_index/core/holo_index.py:205` |
| Search Pipeline | Hybrid vector + keyword scoring | `holo_index/core/search_engine.py:778-900` |
| Fallback | Lexical search (ripgrep subprocess) | `holo_index/core/search_engine.py:703-771` |

### B.2 Does HoloIndex Replace grep/glob?

**NO** — HoloIndex **complements** but does not replace grep/glob:

| Tool | Purpose | Use Case |
|------|---------|----------|
| `grep` / `rg` | Exact pattern matching | Find string literals, regex patterns |
| `glob` | File path matching | Find files by name/extension |
| HoloIndex | Semantic/intent retrieval | Find code by concept, WSP by alias |

**Key Distinction**: HoloIndex finds "pump.fun due diligence" → Trade module files. grep/glob find "pump" → literal string matches. Different retrieval paradigms.

---

## C. Collection Health Snapshot

**Probe**: `python holo_index.py --collection-health-json`
**Vector Path**: `E:\HoloIndex\vectors`

| Collection | Count | Status | Agentic RAG Required |
|------------|-------|--------|---------------------|
| navigation_code | 296 | healthy | YES |
| navigation_wsp | 116 | healthy | YES |
| navigation_symbols | 20,000 | healthy | YES |
| navigation_docs | 3,332 | healthy | NO |
| navigation_knowledge | 47 | healthy | NO |
| navigation_skills | 65 | healthy | NO |
| navigation_tests | 0 | **empty** | NO |
| navigation_work_ledger | (indexed) | healthy | NO |

**Overall Status**: `degraded` (navigation_tests empty)
**Agentic RAG Ready**: `true` (core collections healthy)

---

## D. CLI Surface Inventory

**Entry Point**: `holo_index/_cli_main.py` (main function at line 616)

### D.1 Core CLI Flags

| Flag | Purpose | Lines |
|------|---------|-------|
| `--search`, `-s` | Semantic search query | 622 |
| `--limit` | Result count (default 5) | 623 |
| `--fast-search` | Skip heavy advisor/orchestration | 664 |
| `--offline` | Disable model downloads | 663 |
| `--index-all` | Index code + WSP + docs + knowledge | 640 |
| `--index-code` | Index NAVIGATION.py entries | 641 |
| `--index-wsp` | Index WSP documents | 642 |
| `--index-symbols` | Index function/class symbols | 643 |
| `--index-docs` | Index module/root docs | 654 |
| `--index-knowledge` | Index papers/research | 655 |
| `--index-skillz` | Index SKILLz.md files | 645 |
| `--index-cli` | Index CLI entrypoints → catalog | 649 |
| `--index-work-ledger` | Index work ledger slices | 650 |
| `--collection-health` | Inspect collection health | 721 |
| `--collection-health-json` | JSON output for collection health | 722 |
| `--code-index-report` | Generate CodeIndex surgical report | 659 |
| `--bundle-json` | Emit machine-readable WSP memory bundle | 627-628 |

### D.2 Advisory/Monitoring Flags

| Flag | Purpose | Lines |
|------|---------|-------|
| `--llm-advisor` | Force enable Qwen advisor | 666 |
| `--pattern-coach` | Prevent behavioral vibecoding | 707 |
| `--start-holodae` | Start autonomous monitoring | 691 |
| `--stop-holodae` | Stop autonomous monitoring | 692 |
| `--holodae-status` | Show HoloDAE status | 693 |
| `--verbose` | Show detailed output | 676 |

### D.3 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `HOLO_OFFLINE` | Disable network/model | `0` |
| `HOLO_SKIP_MODEL` | Skip embedding model load | `0` |
| `HOLO_FAST_SEARCH` | Enable fast search mode | `false` |
| `HOLO_USE_TURBOQUANT` | Enable TurboQuant int8 backend | `0` |
| `HOLO_MIN_SIMILARITY` | Minimum similarity threshold | `0.35` |
| `HOLO_MODEL_LOAD_TIMEOUT` | Model load timeout (seconds) | `30` |
| `HOLO_ENCODE_TIMEOUT` | Encoding timeout (seconds) | `3` |

---

## E. Indexing Pipeline Analysis

**Source**: `holo_index/core/indexing_engine.py`

### E.1 Index Entry Flow

```
NAVIGATION.py → parse → extract NEED_TO map → embed → store in navigation_code
WSP_framework/** → glob *.md → extract frontmatter → embed → store in navigation_wsp
modules/**/*.py → AST parse → extract functions/classes → embed → store in navigation_symbols
docs/**/*.md → glob → extract chunks → embed → store in navigation_docs
```

### E.2 Federation Metadata

Per `resolve_foundup_metadata()` (lines 90-129):
- Files under `modules/foundups/{name}/` tagged with `foundup_id` from manifest
- All other files tagged as `"core"`
- Supports external repo flag for future federation

### E.3 IndexResult Observability

Per `IndexResult` dataclass (lines 39-62):
- `discovered_count`: Files found by glob
- `indexed_count`: Docs inserted to ChromaDB
- `is_empty`: True if zero discovered or indexed
- Used to prevent rewarding empty indexing runs

---

## F. Search Pipeline Analysis

**Source**: `holo_index/core/search_engine.py`

### F.1 Hybrid Scoring Components

| Component | Boost | Evidence |
|-----------|-------|----------|
| Vector similarity | Base score | `similarity = 1.0 / (1.0 + distance)` |
| Keyword match | Variable | Title/path/summary token overlap |
| WSP number exact match | +5.0 | `_wsp_number_match_boost()` |
| Slice ID exact match | +5.0 | `_slice_id_match_boost()` |
| WSP alias phrase match | +5.0 | `_wsp_alias_match_boost()` |
| Trade intent path match | +5.0 to +8.0 | `_trade_path_boost()` |
| PR number match | +2.5 | `_pr_number_match_boost()` |
| Owner worker match | +2.0 | `_owner_worker_match_boost()` |
| Work ledger priority | Scaled 1-5 | `_coerce_priority()` |

### F.2 Lexical Fallback

When embedding model unavailable, `_rg_symbol_search()` (lines 703-771):
- Uses ripgrep (`rg`) subprocess
- 15-second timeout
- Returns top matches sorted by file extension priority

### F.3 Backend Quality Taxonomy

| Backend | Quality | Default Ready |
|---------|---------|---------------|
| `sentence_transformers` | production | YES |
| `turboquant_onnx_int8` | experimental | NO |
| `none` | n/a | n/a |
| `routed` | mixed | mixed |

---

## G. Subprocess Usage Audit

### G.1 ripgrep (rg) Fallback

**Location**: `holo_index/core/search_engine.py:703-771`

```python
cmd = [
    rg_path,
    "-n",
    "--no-heading",
    f"--max-count={max(1, limit * 3)}",
    "-S",
    query,
    root,
]
proc = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=15,
)
```

**Purpose**: Exact symbol search when embedding model unavailable
**Timeout**: 15 seconds
**Error Handling**: Returns empty list on failure (no exception propagation)

### G.2 chromadb Dependency Bootstrap

**Location**: `holo_index/core/holo_index.py:33-41`

```python
try:
    import chromadb
except ImportError as exc:
    if os.getenv("HOLO_DISABLE_PIP_INSTALL") == "1" or os.getenv("HOLO_OFFLINE") == "1":
        raise ImportError("chromadb is required but auto-install is disabled...")
    print("Installing required dependencies...")
    subprocess.check_call([__import__('sys').executable, "-m", "pip", "install", "chromadb"])
    import chromadb
```

**Purpose**: Auto-install chromadb if missing (unless offline mode)
**Guarded**: By `HOLO_OFFLINE` and `HOLO_DISABLE_PIP_INSTALL` env vars

---

## H. RAG Readiness Assessment

### H.1 Agentic RAG Collection Status

Per `--collection-health-json` output:

| Requirement | Status |
|-------------|--------|
| Core collections populated | YES (code=296, wsp=116, symbols=20000) |
| Semantic retrieval functional | YES (SentenceTransformer loaded) |
| Fallback available | YES (ripgrep lexical search) |
| Query boost heuristics | YES (WSP, slice, Trade aliases) |
| Federation metadata | YES (foundup_id tagging) |

**Agentic RAG Ready**: `true`

### H.2 Retrieval Quality Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| navigation_tests empty | Test file retrieval degraded | Use grep for test discovery |
| Long-form audit slice IDs | Regex extraction, not semantic | `_AUDIT_SPEC_SLICE_ID_PATTERN` heuristic |
| WSP alias coverage | Only WSP 97 aliased | Expand `_WSP_ALIAS_REGISTRY` |

---

## I. Key Architectural Findings

### I.1 HoloIndex IS a Retrieval System

Evidence:
1. **Vector Store**: ChromaDB PersistentClient with 8 collections
2. **Embedding Model**: SentenceTransformer (all-MiniLM-L6-v2, 384-dim)
3. **Hybrid Scoring**: Vector similarity + keyword boosts
4. **Caching**: Search cache with TTL (WSP 91 observability)
5. **Fallback**: Lexical search via ripgrep subprocess

### I.2 HoloIndex Does NOT Replace grep/glob

Evidence:
1. **Different Retrieval Paradigm**: Semantic (concept) vs syntactic (pattern)
2. **Explicit Fallback**: When embedding fails, HoloIndex calls ripgrep
3. **Complementary Use**: "Find code about X" (HoloIndex) vs "Find string Y" (grep)
4. **CLI Guidance**: `python holo_index.py --search` for intent, `grep`/`rg` for exact

### I.3 TurboQuant Backend Status

Per `_turboquant_enabled()` (line 97-104):
- Opt-in via `HOLO_USE_TURBOQUANT=1`
- Loads int8 ONNX model alongside fp32
- Per-collection routing when both backends healthy
- Experimental quality gate (NOT default ready)

---

## J. Verdict Tables

### J.1 Is HoloIndex a Retrieval System?

| Criterion | Evidence | Result |
|-----------|----------|--------|
| Stores embeddings | ChromaDB PersistentClient | PASS |
| Generates embeddings | SentenceTransformer.encode() | PASS |
| Accepts natural language queries | `--search "..."` flag | PASS |
| Returns ranked results | Hybrid similarity scoring | PASS |
| Supports fallback | ripgrep lexical search | PASS |

**Verdict**: **YES** — HoloIndex is a retrieval system.

### J.2 Does HoloIndex Replace grep/glob?

| Criterion | Evidence | Result |
|-----------|----------|--------|
| Exact pattern matching | Uses ripgrep as fallback, not replacement | NO |
| File path matching | Requires separate glob for path-only queries | NO |
| Semantic intent retrieval | Primary use case for HoloIndex | YES |

**Verdict**: **NO** — HoloIndex complements but does not replace grep/glob.

---

## K. Chain-of-Thought / Chain-of-Action / Chain-of-Evidence (CoT/CoA/CoE)

### K.1 Chain-of-Thought (Assumptions)

This audit is read-only because:
- The architect asked clarifying questions, not implementation requests
- No indexing changes were authorized
- No code changes were in scope
- Evidence gathering requires only file reads and CLI probes

### K.2 Chain-of-Action

| Step | Action | Mutates Code? |
|------|--------|---------------|
| 1 | Read `_cli_main.py` (1-750+ lines) | NO |
| 2 | Read `core/holo_index.py` (1-500+ lines) | NO |
| 3 | Read `core/search_engine.py` (1-900+ lines) | NO |
| 4 | Read `core/indexing_engine.py` (1-200 lines) | NO |
| 5 | Read `core/intelligent_subroutine_engine.py` | NO |
| 6 | Run `--collection-health-json` probe | NO |
| 7 | Run `--fast-search` probe | NO |
| 8 | Write audit document | NO (new file) |

### K.3 Chain-of-Evidence

| Evidence | Source | Value |
|----------|--------|-------|
| Collection counts | `--collection-health-json` | code=296, wsp=116, symbols=20000 |
| Embedding backend | `holo_index/core/holo_index.py:205` | all-MiniLM-L6-v2 |
| Vector store | `holo_index/core/holo_index.py:190` | ChromaDB PersistentClient |
| Subprocess usage | `search_engine.py:717` | ripgrep with 15s timeout |
| Hybrid scoring | `search_engine.py:778-900` | Vector + keyword boosts |

---

## L. Completion Summary

| Item | Value |
|------|-------|
| Branch | `docs/holoindex-codeindex-retrieval-system-audit-phase1` |
| Base commit | `778d4bc97` |
| Files added | 1 (this audit doc) |
| Worker-Lane | W6 |
| Slice | HOLOINDEX_CODEINDEX_RETRIEVAL_SYSTEM_AUDIT_PHASE1 |
| Primary Question 1 | Is HoloIndex a retrieval system? |
| Answer 1 | **YES** |
| Primary Question 2 | Does HoloIndex replace grep/glob? |
| Answer 2 | **NO** (complements) |
| WSP_97 | PASS (7/7) |
| Collection Health | Agentic RAG Ready |

---

## M. Recommendations (Out of Scope)

These are NOT implemented in this slice but noted for future consideration:

1. **Populate navigation_tests**: Currently empty, degrading test file retrieval
2. **Expand WSP alias registry**: Only WSP 97 has aliases; others should follow
3. **TurboQuant graduation**: Currently experimental; needs equivalence proof for default
4. **Test suite discovery**: No pytest tests found in holo_index/ directory itself

---

**Worker**: W6
**Slice**: HOLOINDEX_CODEINDEX_RETRIEVAL_SYSTEM_AUDIT_PHASE1
**WSP Lock**: WSP_00 → WSP_50 → WSP_87 → WSP_97
