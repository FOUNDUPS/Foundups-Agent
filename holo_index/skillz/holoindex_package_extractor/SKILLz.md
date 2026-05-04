---
name: holoindex_package_extractor
description: Extract HoloIndex core into standalone pip-installable package for external FoundUps
version: 1.0
author: 0102
created: 2026-05-05
agents: [qwen]
primary_agent: qwen
intent_type: BUILD
promotion_state: development
pattern_fidelity_threshold: 0.90
trigger:
  cadence: manual
  event: on_demand
category: workflow
evals: []
---
# HoloIndex Package Extractor

**Purpose**: Extract HoloIndex core search/index functionality into a standalone pip-installable package for use in external FoundUp repositories.

**Problem Solved**: External FoundUps (gotjunk, autopost, science-swarm-hub, GeozeAI) cannot use internal HoloIndex from Foundups-Agent.

---

## What This Skill Does

1. **Analyzes** `holo_index/core/` for dependencies
2. **Extracts** core files (search, index, backend, cache)
3. **Stubs** internal dependencies (WSP summaries, NAVIGATION)
4. **Generates** `pyproject.toml` for pip installation
5. **Outputs** to FOUNDUPS/holoindex repository

---

## Core Files Extracted

| File | Size | Purpose |
|------|------|---------|
| holo_index.py | 26KB | Main HoloIndex class |
| search_engine.py | 31KB | Search logic |
| indexing_engine.py | 30KB | Indexing logic |
| backend_routing.py | 6KB | ChromaDB interface |
| search_cache.py | 10KB | Query caching |
| circuit_breaker.py | 10KB | Resilience |

**Total**: ~113KB core

---

## Dependencies

### Required (pip)
- chromadb>=0.4.0
- sentence-transformers>=2.2.0

### Optional
- onnxruntime (for turboquant backend)

### Stubbed (internal)
- WSP summaries → empty dict
- NAVIGATION.py → empty dict
- qwen_advisor → EXCLUDED

---

## Execution

```bash
# Analyze dependencies (dry run)
python holo_index/skillz/holoindex_package_extractor/executor.py --analyze

# Extract to target directory
python holo_index/skillz/holoindex_package_extractor/executor.py --extract /tmp/holoindex

# Generate pyproject.toml only
python holo_index/skillz/holoindex_package_extractor/executor.py --pyproject

# Full extraction with tests
python holo_index/skillz/holoindex_package_extractor/executor.py --extract /tmp/holoindex --with-tests
```

---

## Output Structure

```
holoindex/
├── src/holoindex/
│   ├── __init__.py
│   ├── core.py          (HoloIndex main class)
│   ├── search.py        (search_engine)
│   ├── indexing.py      (indexing_engine)
│   ├── backend.py       (backend_routing)
│   ├── cache.py         (search_cache)
│   └── resilience.py    (circuit_breaker)
├── tests/
│   ├── test_core.py
│   ├── test_search.py
│   └── test_indexing.py
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## WSP 97 Truth Boundaries

| Claim | Status |
|-------|--------|
| Package is pip-installable | MUST be verified post-extraction |
| All tests pass standalone | MUST be verified post-extraction |
| No internal deps leaked | Verified by stub analysis |
| ChromaDB integration works | MUST be verified with fresh index |

---

## Target FoundUps

| FoundUp | Repo | Priority |
|---------|------|----------|
| gotjunk | FOUNDUPS/gotjunk | P1 (has manifest) |
| science-swarm-hub | FOUNDUPS/science-swarm-hub | P1 (already exfoliated) |
| autopost | FOUNDUPS/autopost | P2 |
| GeozeAI | FOUNDUPS/GeozeAI | P2 |

---

## Related WSPs

- **WSP 103**: pAVS MCP Tools (holo_search stub)
- **WSP 104**: FoundUp Independence (local HoloIndex per FoundUp)
- **WSP 97**: Truth Boundaries

---

## Autonomy Test

**Question**: Can N compute cycles complete without 012?

**Answer**: PARTIAL
- Analysis phase: YES (fully autonomous)
- Extraction phase: YES (file copy)
- Verification phase: NEEDS 012 (pip install test)
- Deployment phase: NEEDS 012 (push to external repo)

---

*This skill extracts HoloIndex for external FoundUp independence.*
*Created: 2026-05-05 | Author: 0102*
