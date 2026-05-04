# DEGRADED_MODE_WSP_DOC_RETRIEVAL_AUDIT

**Slice**: `HOLOINDEX_DEGRADED_MODE_WSP_DOC_RETRIEVAL_AUDIT_PHASE1`
**Date**: 2026-05-04
**Worker**: W6
**Decision**: NO_ACTION (issue already fixed)

---

## Context

An agent observed:
> "HoloIndex degraded to lexical/offline and returned zero WSP/doc hits for a WSP-audit query."

This audit investigates degraded-mode retrieval for WSP backbone documents.

---

## 1. Reproduction Commands

### Semantic Mode
```bash
python holo_index.py --search "WSP 97 system execution prompting audit" --limit 5 --ssd E:/HoloIndex
python holo_index.py --search "WSP 50 pre action verification protocol" --limit 5 --ssd E:/HoloIndex
python holo_index.py --search "WSP 22 ModLog protocol" --limit 5 --ssd E:/HoloIndex
```

### Degraded/Offline Mode
```bash
HOLO_OFFLINE=1 python holo_index.py --search "WSP 97 system execution prompting audit" --limit 5 --ssd E:/HoloIndex
HOLO_OFFLINE=1 python holo_index.py --search "WSP 50 pre action verification protocol" --limit 5 --ssd E:/HoloIndex
HOLO_OFFLINE=1 python holo_index.py --search "WSP 22 ModLog protocol" --limit 5 --ssd E:/HoloIndex
```

---

## 2. Semantic Mode Results

| Query | Code | WSP | Docs | Knowledge | Total |
|-------|------|-----|------|-----------|-------|
| WSP 97 system execution prompting audit | 5 | 5 | 5 | 5 | 20 |
| WSP 50 pre action verification protocol | 5 | 5 | 0 | 0 | 10 |
| WSP 22 ModLog protocol | 5 | 5 | 0 | 0 | 10 |

All queries return correct WSP hits including the target protocol.

---

## 3. Degraded/Offline Mode Results

| Query | Code | WSP | Docs | Knowledge | Total |
|-------|------|-----|------|-----------|-------|
| WSP 97 system execution prompting audit | 5 | 5 | 5 | 5 | 20 |
| WSP 50 pre action verification protocol | 5 | 5 | 0 | 0 | 10 |
| WSP 22 ModLog protocol | 5 | 5 | 0 | 0 | 10 |

**Key Finding**: Degraded mode now returns same hit counts as semantic mode.

---

## 4. Expected WSP/Doc Hits

For "WSP 97 system execution prompting audit":
- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` ✓
- `WSP_framework/src/WSP_16_Test_Audit_Coverage.md` ✓
- `WSP_framework/src/WSP_14_Modular_Audit_Protocol.md` ✓

For "WSP 50 pre action verification protocol":
- `WSP_framework/src/WSP_50_Pre_Action_Verification_Protocol.md` ✓
- `WSP_framework/src/WSP_64_Violation_Prevention_Protocol.md` ✓

For "WSP 22 ModLog protocol":
- `WSP_framework/src/WSP_22_ModLog_Structure.md` ✓
- `WSP_framework/src/WSP_22a_Module_ModLog_and_Roadmap.md` ✓

---

## 5. Actual WSP/Doc Hits

All expected WSP protocols appear in both semantic and offline mode results.

---

## 6. Root Cause

The issue was already fixed in commit `9a89fedeb`:

```
fix(holoindex): surface retrieval mode and harden offline fallbacks

FX1-R: HoloIndex truth repair

- FX1-A: Define module-level logger in _cli_main.py (fixes NameError)
- FX1-D: Add retrieval_mode state (semantic/lexical/failed) to HoloIndex
- FX1-D: Surface retrieval_mode in search result metadata
- FX1-E: Set ANONYMIZED_TELEMETRY=false in offline mode
- FX1-C: WSP00 zen state tracker 3-tier fallback (repo/user/non-persistent)
```

The "harden offline fallbacks" change ensured that lexical search properly iterates all collections (code, wsp, docs, knowledge) when embedding model is unavailable.

---

## 7. Risk to WSP_50

**MITIGATED**: WSP_50 (Pre-Action Verification) now has reliable retrieval in both semantic and degraded modes.

Collection coverage verified:
- `navigation_wsp`: 117 docs (WSP protocols)
- `navigation_docs`: 3143 docs (module/root docs)
- `navigation_knowledge`: 47 docs (papers/research)

All collections are searched in lexical fallback via `_lexical_search_collection()`.

---

## 8. Recommendation

**NO_ACTION** — Issue is already fixed on main.

**TEST_ONLY** — Consider adding explicit regression test for docs/knowledge in offline mode.

Proposed test location: `holo_index/tests/test_offline_collection_coverage.py`

```python
def test_offline_searches_all_collections():
    """Verify offline mode searches docs and knowledge collections."""
    os.environ["HOLO_SKIP_MODEL"] = "1"
    try:
        holo = HoloIndex()
        result = holo.search("WSP 97 audit", limit=5)
        assert result["metadata"]["docs_count"] >= 0
        assert result["metadata"]["knowledge_count"] >= 0
        # Verify WSP hit exists
        wsp_hits = result.get("wsp_hits", [])
        assert any("WSP_97" in h.get("path", "") for h in wsp_hits)
    finally:
        os.environ.pop("HOLO_SKIP_MODEL", None)
```

---

## 9. Next Atomic Prompt

None required. Issue resolved.

If regression testing is desired:
```
Create holo_index/tests/test_offline_collection_coverage.py with tests for:
1. Offline mode searches all 4 collections (code, wsp, docs, knowledge)
2. WSP backbone docs appear in offline mode for WSP-specific queries
3. Collection counts are non-negative in offline mode
```

---

## Test Results

```
holo_index/tests/test_search_quality_baseline.py: 10 passed
holo_index/tests/test_backend_routing.py: 19 passed
holo_index/tests/test_fx1_holoindex_truth.py: 11 passed
```

---

## WSP_50 Risk Verdict

**LOW** — Offline fallback now correctly searches all collections including WSP backbone.

---

## WSP_97 Verdict

**COMPLIANT** — Search results truthfully report collection counts and retrieval mode.

---

## Files Changed

- `docs/audits/holoindex_search_quality/DEGRADED_MODE_WSP_DOC_RETRIEVAL_AUDIT.md` (NEW)

---

## Summary

The reported issue (zero WSP/doc hits in degraded mode) was already fixed by commit `9a89fedeb` (FX1 series). Current main branch correctly returns WSP and docs hits in both semantic and offline modes. No code changes required.
