# MCPA9D Gemma Classify Backend Connection

**Slice**: MCPA9D_GEMMA_CLASSIFY_BACKEND_CONNECTION_PHASE1
**Worker**: W1
**Date**: 2026-05-09
**Status**: COMPLETE

---

## 1. Mission

Connect S3 `pavs_mcp` `gemma_classify` to the real local Gemma backend.

---

## 2. Preconditions

| Check | Status |
|-------|--------|
| MCPA9C re-audit complete | ✓ |
| Gemma callable seam identified | ✓ |
| WSP 15 priority score: 13 (highest) | ✓ |
| GemmaRAGInference available | ✓ |

---

## 3. Callable Seam Used

**Module**: `holo_index/qwen_advisor/gemma_rag_inference.py`

### GemmaRAGInference Class (line 97)

```python
class GemmaRAGInference:
    def __init__(
        self,
        gemma_model_path: Optional[Path] = None,
        qwen_model_path: Optional[Path] = None,
        qwen_backend: str = "qwen-coder-7b",
        confidence_threshold: float = 0.7
    ):
```

### _gemma_inference Method (line 351)

```python
def _gemma_inference(self, prompt: str) -> Dict[str, Any]:
    """
    Run Gemma 3 270M inference.
    
    Returns:
        dict with response, confidence, and latency
    """
```

### Model Resolution

Uses `resolve_triage_model_path()` from `shared_utilities/local_model_selection.py`
to locate Gemma 3 270M GGUF model.

---

## 4. Implementation

### Backend Adapter

```python
def _call_gemma_classify(text: str, categories: list[str]) -> dict[str, Any]:
    """Call Gemma backend for text classification."""
    engine = _get_gemma_engine()  # Lazy singleton
    
    # Build classification prompt
    prompt = f"""Classify the following text into exactly ONE of these categories: {categories_str}
Text: {text}
Reply with ONLY the category name, nothing else.
Category:"""
    
    result = engine._gemma_inference(prompt)
    # Parse classification from response
    return {
        "classification": classification,
        "confidence": result["confidence"],
        "latency_ms": result["latency_ms"],
        "model": "gemma-3-270m",
    }
```

### Before/After: gemma_classify

**Before** (placeholder):
```python
async def gemma_classify(self, text: str, categories: list[str]):
    return {
        "classification": categories[0] if categories else "unknown",
        "confidence": 0.92,  # Hardcoded
        "all_scores": {cat: 1.0 / len(categories) for cat in categories}
    }
```

**After** (real backend):
```python
async def gemma_classify(self, text: str, categories: list[str]):
    result = _call_gemma_classify(text, categories)
    return {
        "status": "ok",
        "data": {
            "classification": result["classification"],
            "confidence": result["confidence"],
            "all_scores": all_scores,
            "model": result["model"],
            "latency_ms": result["latency_ms"],
        },
        "meta": {
            "real_backend": True,
            "delegated_to": "GEMMA",
        },
    }
```

---

## 5. Test Commands

```bash
python -m pytest modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py -q
# Result: 102 passed

python -m pytest modules/infrastructure/pavs_mcp/tests/test_transport.py -q
# Result: 20 passed

python -m pytest modules/infrastructure/pavs_mcp/tests/ -q
# Result: 122 passed
```

---

## 6. Files Changed

| File | Changes |
|------|---------|
| `src/server.py` | +90 lines: adapter, method rewrite, banner update |
| `tests/test_server_holo_search.py` | +100 lines: TestGemmaBackendDelegation class |
| `tests/test_transport.py` | +50 lines: TestGemmaViaTransport class |
| `README.md` | Updated status, tool table |
| `ModLog.md` | MCPA9D entry added |

---

## 7. WSP 97 Truth Table

| Tool | real_backend | delegated_to | implementation_status |
|------|--------------|--------------|----------------------|
| holo_search | true | S2 | placeholder_stub |
| fam_emit | true | FAM_DAEMON | placeholder_stub |
| pattern_recall | true | PATTERN_MEMORY | placeholder_stub |
| pattern_store | true | PATTERN_MEMORY | placeholder_stub |
| gemma_classify | **true** | **GEMMA** | placeholder_stub |
| foundup_register | false | — | placeholder_stub |
| cabr_validate | false | — | placeholder_stub |
| qwen_plan | false | — | placeholder_stub |

---

## 8. Remaining Placeholder Tools

| Tool | Status | Next Steps |
|------|--------|------------|
| `cabr_validate` | PLACEHOLDER | Interface mismatch with CABRHooks |
| `qwen_plan` | PLACEHOLDER | QwenInferenceEngine adapter needed |

---

## 9. Verdict

```
GEMMA_CLASSIFY_BACKEND_CONNECTED
```

**5/8 tools now have real backends.** Gemma enables AI-powered text classification.

---

*Worker W1 complete for MCPA9D_GEMMA_CLASSIFY_BACKEND_CONNECTION_PHASE1.*
