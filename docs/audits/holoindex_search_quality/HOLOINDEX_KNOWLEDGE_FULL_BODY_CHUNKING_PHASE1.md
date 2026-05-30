# HOLOINDEX_KNOWLEDGE_FULL_BODY_CHUNKING_PHASE1

**Date**: 2026-05-30
**Agent**: W6 (0102)
**Status**: COMPLETE
**PR**: (pending)

## Problem Statement

The HoloIndex knowledge indexer (`index_knowledge_entries()`) only embedded the first
5 lines of each paper after the title. For research papers like rESP, this captured
only metadata (author, date, contact), missing the abstract and all body content.

**Root cause** in `indexing_engine.py:923-925`:
```python
title = lines[0].lstrip('# ')
summary = ' '.join(lines[1:6])[:400]
doc_payload = f"{title}\n{summary}"
```

**Impact**: Deep sections unretrievable. rESP Section 4.4 ("Null-Model Comparison Status")
at line 406 was invisible to semantic search.

## Solution

Implemented heading-based full-body chunking:

1. **`_chunk_markdown_by_headings()`** helper:
   - Splits on `# ## ###` headings
   - Sub-splits oversized sections (>1200 chars) at word boundaries
   - Handles code fences, tables, mermaid as raw text

2. **Modified `index_knowledge_entries()`**:
   - Produces `paper_summary` record (title + first 5 lines, backward compatible)
   - Produces `paper_chunk` records for each heading section
   - Stable IDs: `paper_{idx}` for summary, `paper_{idx}_chunk_{m}` for chunks
   - Batched inserts (100/batch) to avoid Chroma limits
   - New metadata: `record_kind`, `section`, `section_title`

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| rESP §4.4 terms in indexed chunks | PASS |
| Summary + chunk records produced | PASS |
| Stable deterministic IDs | PASS |
| Metadata has section/record_kind | PASS |
| No timeout default changes | PASS |
| Batched collection.add() | PASS |

## Test Coverage

**New file**: `holo_index/tests/test_knowledge_full_body_chunking.py`

| Test | Purpose |
|------|---------|
| `test_splits_on_headings` | Chunker produces sections |
| `test_large_section_gets_sub_split` | Oversized sections split |
| `test_handles_code_fences` | Code blocks preserved |
| `test_section_44_pattern` | §4.4 content in chunk |
| `test_produces_summary_and_chunk_records` | Both record types created |
| `test_deep_section_is_indexed` | §4.4 acceptance test |
| `test_chunk_ids_are_deterministic` | Stable ID format |
| `test_metadata_has_required_fields` | Required fields present |

**Result**: 8/8 tests passing

## WSP_97 Truth Boundary Checklist

- [x] NO_LIVE_CHROMA_MUTATION_IN_TESTS: Tests use mock collection
- [x] NO_DOC_CONTENT_CHANGE: Only indexing behavior changed
- [x] NO_TIMEOUT_DEFAULT_CHANGE: Defaults unchanged (20/30)
- [x] NO_UNRELATED_FILE_TOUCH: Scope limited to indexing_engine.py + test

## Files Changed

| File | Change |
|------|--------|
| `holo_index/core/indexing_engine.py` | Added chunker, modified indexer |
| `holo_index/tests/test_knowledge_full_body_chunking.py` | New test file |
| `holo_index/ModLog.md` | Entry added |

## Manual Verification

After reindexing (`python holo_index.py --index-knowledge`):
```
python holo_index.py --search "Null-Model Comparison Status phase-randomized surrogates" --limit 6
```
Should return `rESP_Quantum_Self_Reference.md` under `[KNOWLEDGE]`.
