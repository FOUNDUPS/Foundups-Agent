# MCPA9C Backend Re-Audit

**Slice**: MCPA9C_BACKEND_REAUDIT_PHASE1
**Worker**: W1
**Date**: 2026-05-09
**Precondition PR**: #541 (pattern memory backend)
**Verdict**: `HOLO_FAM_PATTERN_BACKENDS_CONFIRMED_PARTIAL_BACKEND_READY`

---

## 1. Final Verdict

```
HOLO_FAM_PATTERN_BACKENDS_CONFIRMED_PARTIAL_BACKEND_READY
```

**4/8 tools now have real backends.** S3 is partially backend-ready but not production-ready.

---

## 2. Precondition Verification

| Marker | Status | Location |
|--------|--------|----------|
| `PatternMemory` | ✓ | server.py:180 |
| `recall_successful_patterns` | ✓ | server.py:184 |
| `store_outcome` | ✓ | server.py:214 |
| `SkillOutcome` | ✓ | server.py:241 |
| `PATTERN_MEMORY` | ✓ | server.py:189 |
| MCPA9C audit doc | ✓ | `docs/audits/mcp_system/MCPA9C_PATTERN_MEMORY_BACKEND_CONNECTION.md` |

---

## 3. What Changed After MCPA9C

| Change | Details |
|--------|---------|
| `pattern_recall` | Now delegates to `PatternMemory.recall_successful_patterns()` |
| `pattern_store` | Now delegates to `PatternMemory.store_outcome()` with SkillOutcome construction |
| PLACEHOLDER_BANNER | Updated to show 4/8 tools with real backends |
| Tests | 108 passing (added 29 pattern memory tests) |

---

## 4. Backend Readiness Table

| Tool | Status | Backend | Callable Seam | Evidence |
|------|--------|---------|---------------|----------|
| `holo_search` | **REAL_BACKEND** | S2/HoloIndex | `holo_search()` via MCP | MCPA9A |
| `fam_emit` | **REAL_BACKEND** | FAM DAEmon | `get_fam_daemon().emit()` | MCPA9B |
| `pattern_recall` | **REAL_BACKEND** | PatternMemory | `recall_successful_patterns()` | MCPA9C |
| `pattern_store` | **REAL_BACKEND** | PatternMemory | `store_outcome()` | MCPA9C |
| `foundup_register` | **BOOTSTRAP_REGISTRY** | Local JSON | N/A | Auth bootstrap |
| `cabr_validate` | **PLACEHOLDER_BACKEND** | — | Interface mismatch | See analysis |
| `gemma_classify` | **PLACEHOLDER_BACKEND** | — | Strong seam exists | See analysis |
| `qwen_plan` | **PLACEHOLDER_BACKEND** | — | Strong seam exists | See analysis |

---

## 5. Closed Blockers

| Blocker | Closed By | Status |
|---------|-----------|--------|
| H4a: holo_search placeholder | MCPA9A | ✓ |
| H4b: No real backend at all | MCPA9A | ✓ |
| H4c: fam_emit placeholder | MCPA9B | ✓ |
| H4d: pattern_recall placeholder | MCPA9C | ✓ |
| H4e: pattern_store placeholder | MCPA9C | ✓ |

---

## 6. Remaining Placeholder Tools

| Tool | Current Output | Required Interface |
|------|----------------|-------------------|
| `cabr_validate` | Hardcoded `score=0.85` | V1/V2/V3 content validation |
| `gemma_classify` | Hardcoded `confidence=0.92` | Binary/multi-class classification |
| `qwen_plan` | Hardcoded 3-step plan | Strategic planning |

---

## 7. Remaining Production Blockers

| Blocker | Description | Severity |
|---------|-------------|----------|
| H5a | `cabr_validate` returns hardcoded data | HIGH |
| H5b | `gemma_classify` returns hardcoded data | MEDIUM |
| H5c | `qwen_plan` returns hardcoded data | MEDIUM |
| H6 | No key rotation mechanism | LOW |
| H7 | No rate limiting | LOW |
| H8 | Local transport only (no TLS) | MEDIUM |

---

## 8. Candidate Backend Seam Analysis

### 8.1 cabr_validate

**File**: `modules/foundups/agent_market/src/cabr_hooks.py`

**Current Interface**:
```python
class PersistentCABRHooks:
    def build_cabr_input(foundup_id: str, window: str) -> Dict
    # Returns: CABRInput with task metrics, completion rates
    # CABROutput: score, confidence, factors (FoundUp health)
```

**pAVS Interface Needed**:
```python
async def cabr_validate(content: str, context: dict) -> dict:
    # Returns: score, passed, feedback, v1/v2/v3 results
```

**Seam Assessment**: **INTERFACE_MISMATCH**
- `cabr_hooks.py` scores FoundUp health metrics, NOT content
- V1/V2/V3 content validation is a different concern
- Would require new implementation, not just adapter
- No callable seam exists for content validation

### 8.2 gemma_classify

**Files**:
- `modules/communication/video_comments/src/gemma_validator.py`
- `modules/ai_intelligence/video_indexer/src/gemma_segment_classifier.py`

**Current Interface** (gemma_validator.py):
```python
class GemmaValidator:
    def _gemma_inference(prompt: str) -> Optional[str]
    def validate_maga_pattern(comment_text: str) -> Dict
    # Uses llama_cpp with lazy loading
    # Binary yes/no classification
```

**pAVS Interface Needed**:
```python
async def gemma_classify(text: str, categories: list[str]) -> dict:
    # Returns: classification, confidence, all_scores
```

**Seam Assessment**: **STRONG_SEAM_WITH_ADAPTER**
- `_gemma_inference(prompt)` is generic enough for multi-class
- llama_cpp integration proven working
- Adapter needed to:
  1. Build classification prompt from `text` + `categories`
  2. Parse response into classification result
  3. Extract confidence scores
- Estimate: ~80 LOC adapter

### 8.3 qwen_plan

**File**: `holo_index/qwen_advisor/llm_engine.py`

**Current Interface**:
```python
class QwenInferenceEngine:
    def initialize() -> bool
    def generate_response(prompt: str, system_prompt: str = None) -> str
    # Uses llama_cpp with lazy loading
    # General text generation
```

**pAVS Interface Needed**:
```python
async def qwen_plan(objective: str, constraints: dict = None) -> dict:
    # Returns: plan[], reasoning, alternatives
```

**Seam Assessment**: **STRONG_SEAM_WITH_ADAPTER**
- `generate_response()` is generic text generation
- llama_cpp integration proven working
- Adapter needed to:
  1. Build planning prompt from `objective` + `constraints`
  2. Parse structured plan from response
  3. Extract reasoning and alternatives
- Estimate: ~100 LOC adapter

---

## 9. WSP 15 Next-Slice Scoring

Scale: 1 (low) to 5 (high). Lower total = higher priority.

| Backend | Complexity | Importance | Deferability | Impact | Risk | **Total** |
|---------|------------|------------|--------------|--------|------|-----------|
| **gemma_classify** | 2 | 3 | 3 | 3 | 2 | **13** |
| qwen_plan | 3 | 3 | 4 | 3 | 3 | 16 |
| cabr_validate | 5 | 4 | 2 | 4 | 4 | 19 |

### Scoring Rationale

**gemma_classify (Score: 13 - LOWEST = HIGHEST PRIORITY)**
- **Complexity: 2** — Direct callable seam exists. `GemmaValidator._gemma_inference(prompt)` accepts any prompt. Just need adapter to build classification prompt and parse result.
- **Importance: 3** — Binary/multi-class classification useful for content gates.
- **Deferability: 3** — Can defer, but enables V1 validation gates.
- **Impact: 3** — Unlocks AI-powered classification for FoundUps.
- **Risk: 2** — llama_cpp proven working. Model loading pattern established.

**qwen_plan (Score: 16)**
- **Complexity: 3** — `generate_response()` is generic but parsing structured plan from free-form output adds complexity.
- **Importance: 3** — Strategic planning useful but not blocking.
- **Deferability: 4** — Can defer; 012/0102 handles planning currently.
- **Impact: 3** — Autonomous planning valuable but optional.
- **Risk: 3** — Plan parsing from LLM output is fragile.

**cabr_validate (Score: 19 - HIGHEST = LOWEST PRIORITY)**
- **Complexity: 5** — No callable seam for content validation. `cabr_hooks.py` does FoundUp health scoring. V1/V2/V3 validation needs new implementation.
- **Importance: 4** — CABR engine critical, but current hooks don't match.
- **Deferability: 2** — Important but blocked on interface design.
- **Impact: 4** — Full content validation high-value.
- **Risk: 4** — Interface mismatch requires architectural decision.

---

## 10. Recommended Next Slice

**MCPA9D_GEMMA_CLASSIFY_BACKEND_CONNECTION_PHASE1**

### Justification

1. **Lowest WSP 15 score** (13) = highest priority
2. **Direct callable seam** — `GemmaValidator._gemma_inference()` proven working
3. **Pattern established** — Same llama_cpp loading pattern as existing Gemma code
4. **Low complexity** — Adapter only (~80 LOC)
5. **Model available** — Uses same Gemma GGUF model path resolution

### Implementation Estimate

- **LOC**: ~80 (adapter + prompt builder)
- **Tests**: ~15 new test cases
- **Risk**: LOW (llama_cpp proven, model exists)

### Required Interface

```python
# _call_gemma_classify(text, categories) -> dict
# Returns: {"classification": "cat_a", "confidence": 0.92, "all_scores": {...}}
```

---

## 11. WSP 97 Truth Table

| Tool | real_backend | delegated_to | implementation_status |
|------|--------------|--------------|----------------------|
| holo_search | **true** | S2 | placeholder_stub |
| fam_emit | **true** | FAM_DAEMON | placeholder_stub |
| pattern_recall | **true** | PATTERN_MEMORY | placeholder_stub |
| pattern_store | **true** | PATTERN_MEMORY | placeholder_stub |
| foundup_register | false | — | placeholder_stub |
| cabr_validate | false | — | placeholder_stub |
| gemma_classify | false | — | placeholder_stub |
| qwen_plan | false | — | placeholder_stub |

**Notes**:
- `implementation_status = "placeholder_stub"` remains at surface level
- `meta.real_backend = true` indicates actual backend delegation
- S3 is **not canonical owner** of any tool
- **Local transport only** — no public production deployment
- **4/8 tools have real backends** — partial readiness only

---

## 12. HoloIndex Top Hit

```
[CODE] modules\infrastructure\pavs_mcp\src\server.py
```

---

*Audited by W1 | MCPA9C_BACKEND_REAUDIT_PHASE1 | 2026-05-09*
