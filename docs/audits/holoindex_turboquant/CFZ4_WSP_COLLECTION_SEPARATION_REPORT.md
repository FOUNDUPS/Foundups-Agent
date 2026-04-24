# CFZ4 — WSP Collection Separation (Phase 1)

**Slice**: `CFZ4_WSP_COLLECTION_SEPARATION_PHASE1`
**Date**: 2026-04-24
**Worker**: CFZ4
**Decision**: IMPLEMENTED (semantic drift fixed; collections now truthful)

---

## Context

`navigation_wsp` was polluted with non-WSP content:
- 83.2% module docs (2,765 files)
- 9.2% root docs (305 files)
- 3.6% TRUE WSP protocols (121 files)
- 2.2% papers/research (72 files)
- 1.2% WSP_framework/docs (39 files)

All documents received `wsp_` ID prefix regardless of content type, violating WSP 97 truthful naming.

---

## Architecture Decision

| Collection | Content | ID Prefix | Source Path |
|------------|---------|-----------|-------------|
| `navigation_wsp` | WSP protocols ONLY | `wsp_` | `WSP_framework/src/WSP_*.md` |
| `navigation_docs` | Module/root docs | `doc_` | `modules/**`, `docs/**`, `holo_index/docs/**`, `WSP_framework/docs/**` |
| `navigation_knowledge` | Papers/research | `paper_` | `WSP_knowledge/docs/Papers/**` |

---

## Deliverables

| Artifact | Path |
|----------|------|
| Indexing separation | `holo_index/core/indexing_engine.py` |
| Collection registration | `holo_index/core/holo_index.py` |
| Search extension | `holo_index/core/search_engine.py` |
| Tests | `holo_index/tests/test_cfz4_collection_separation.py` |
| Report | `docs/audits/holoindex_turboquant/CFZ4_WSP_COLLECTION_SEPARATION_REPORT.md` |

---

## Counts Before/After

| Collection | Before CFZ4 | After CFZ4 | Delta |
|------------|-------------|------------|-------|
| navigation_wsp | 3,323 | 117 | -3,206 |
| navigation_docs | 0 (new) | 3,120 | +3,120 |
| navigation_knowledge | 0 (new) | 47 | +47 |
| **Total indexed** | 3,323 | 3,284 | -39 |

*Note: 39 fewer docs due to hygiene filters (hidden/backup/archive exclusions)*

---

## Sample IDs (Prefix Verification)

### navigation_wsp (wsp_ prefix)
```
wsp_1: WSP_00_Zen_State_Attainment_Protocol.md
wsp_2: WSP_100_DAE_SmartDAO_Escalation_Protocol.md
wsp_3: WSP_101_UPS_Utility_Classification_Protocol.md
```

### navigation_docs (doc_ prefix)
```
doc_1: modules/.../0102_orchestrator/INTERFACE.md
doc_2: modules/.../memory/README.md
doc_3: modules/.../0102_orchestrator/ModLog.md
```

### navigation_knowledge (paper_ prefix)
```
paper_1: 0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md
paper_2: 0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md
paper_3: 0102_TECHNICAL_EXTRACTIONS_2026-03-08.md
```

**Prefix violations: 0**

---

## Mapping Rules Implemented

### index_wsp_entries() (modified)
```python
# CFZ4: WSP protocols ONLY from WSP_framework/src
wsp_src_path = holo.project_root / "WSP_framework" / "src"
all_wsp_files = sorted(wsp_src_path.glob("WSP_*.md"))
```

### index_docs_entries() (new)
```python
doc_paths = [
    holo.project_root / "modules",
    holo.project_root / "docs",
    holo.project_root / "holo_index" / "docs",
    holo.project_root / "WSP_framework" / "docs",
]
```

### index_knowledge_entries() (new)
```python
knowledge_path = holo.project_root / "WSP_knowledge" / "docs" / "Papers"
```

---

## Search Compatibility

Search results now include:
- `wsp_hits` / `wsps` — WSP protocols only (truthful)
- `docs_hits` / `docs` — Module/root docs (new)
- `knowledge_hits` / `knowledge` — Papers/research (new)

Metadata includes:
- `wsp_count`, `docs_count`, `knowledge_count`

**Backward compatible**: Existing callers using `wsp_hits` continue to work; content is now semantically correct.

---

## Test Results

### CFZ4 Tests
```
holo_index/tests/test_cfz4_collection_separation.py: 12 passed
```

### Doc Type Filtering Tests
```
holo_index/tests/test_doc_type_filtering.py: 2 passed
```

### CFZ3 Hygiene Tests
```
holo_index/tests/test_cfz3_corpus_hygiene.py: 10 passed
```

---

## HoloIndex Search Commands

```bash
# Search 1: Collection routing patterns
python holo_index.py --search "index_wsp_entries navigation_wsp doc_type_filter" --limit 5
# Top hit: WSP_35_HoloIndex_Qwen_Advisor_Plan.md

# Search 2: WSP paths configuration
python holo_index.py --search "DEFAULT_WSP_PATHS get_wsp_paths helpers.py" --limit 5
# Top hit: MODULE_PLACEMENT_GUIDE.md

# Search 3: CFZ3 hygiene patterns
python holo_index.py --search "CFZ3 corpus hygiene navigation_wsp drift" --limit 5
# Top hit: CFZ3_CORPUS_HYGIENE_AND_SENTINEL_HARDENING_REPORT.md
```

---

## TQ4 Recommendation

**Next slice**: `TQ4_CLEAN_COLLECTION_BASELINE_REAUDIT`

The TQ2/TQ3 audits measured quality on the polluted `navigation_wsp` (3,323 docs). After CFZ4 separation:
- `navigation_wsp` now has 117 docs (true WSP protocols)
- Gate thresholds may need adjustment for smaller corpus
- Sentinel queries must target protocol-specific content

**Recommended actions**:
1. Re-freeze corpus manifest with new collection structure
2. Review/update sentinel queries to target WSP protocols
3. Re-run TQ2/TQ3 on clean baseline
4. Evaluate if thresholds need adjustment for smaller corpus

---

## WSP 97 Applied

- **Truthful naming**: `wsp_` prefix now only on WSP protocols
- **Semantic separation**: Each collection has clear, honest scope
- **No overclaiming**: Non-WSP docs no longer pollute protocol collection
- **Backward compatible**: Search API preserved with extended hit categories
