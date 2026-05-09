# MCPA9D Backend Re-Audit

**Slice**: MCPA9D_BACKEND_REAUDIT_PHASE1
**Worker**: W1
**Date**: 2026-05-10
**Precondition PR**: #543 (Gemma classify backend)
**Verdict**: `HOLO_FAM_PATTERN_GEMMA_BACKENDS_CONFIRMED_PARTIAL_BACKEND_READY`

---

## 1. Final Verdict

```
HOLO_FAM_PATTERN_GEMMA_BACKENDS_CONFIRMED_PARTIAL_BACKEND_READY
```

**5/8 tools now have real backends.** S3 is partially backend-ready but not production-ready. CABR and Qwen remain placeholders.

---

## 2. Precondition Verification

| Marker | Status | Location |
|--------|--------|----------|
| `GemmaRAGInference` | ✓ | server.py:294 |
| `_call_gemma_classify` | ✓ | server.py:300 |
| `classify_text` | ✓ | server.py:344 |
| `GEMMA` | ✓ | server.py:912 (delegated_to) |
| `real_backend` | ✓ | server.py:912 |
| MCPA9D audit doc | ✓ | `docs/audits/mcp_system/MCPA9D_GEMMA_CLASSIFY_BACKEND_CONNECTION.md` |

---

## 3. What Changed After MCPA9D

| Change | Details |
|--------|---------|
| `gemma_classify` | Now delegates to `GemmaRAGInference.classify_text()` |
| `_get_gemma_engine()` | Singleton lazy-loader for llama_cpp model |
| PLACEHOLDER_BANNER | Updated to show 5/8 tools with real backends |
| Error handling | `GEMMA_BACKEND_UNAVAILABLE` when model not loaded |
| Tests | 122 passing (added 14 Gemma classify tests) |

---

## 4. Backend Readiness Table

| Tool | Status | Backend | Callable Seam | Evidence |
|------|--------|---------|---------------|----------|
| `holo_search` | **REAL_BACKEND** | S2/HoloIndex | `holo_search()` via MCP | MCPA9A |
| `fam_emit` | **REAL_BACKEND** | FAM DAEmon | `get_fam_daemon().emit()` | MCPA9B |
| `pattern_recall` | **REAL_BACKEND** | PatternMemory | `recall_successful_patterns()` | MCPA9C |
| `pattern_store` | **REAL_BACKEND** | PatternMemory | `store_outcome()` | MCPA9C |
| `gemma_classify` | **REAL_BACKEND** | GemmaRAGInference | `classify_text()` | MCPA9D |
| `foundup_register` | **BOOTSTRAP_REGISTRY** | Local JSON | N/A | Auth bootstrap |
| `cabr_validate` | **PLACEHOLDER_BACKEND** | — | Interface mismatch | See §8.1 |
| `qwen_plan` | **PLACEHOLDER_BACKEND** | — | Strong seam exists | See §8.2 |

---

## 5. Closed Blockers

| Blocker | Closed By | Status |
|---------|-----------|--------|
| H4a: holo_search placeholder | MCPA9A | ✓ |
| H4b: No real backend at all | MCPA9A | ✓ |
| H4c: fam_emit placeholder | MCPA9B | ✓ |
| H4d: pattern_recall placeholder | MCPA9C | ✓ |
| H4e: pattern_store placeholder | MCPA9C | ✓ |
| H5b: gemma_classify placeholder | MCPA9D | ✓ |

---

## 6. Remaining Placeholder Tools

| Tool | Current Output | Required Interface |
|------|----------------|-------------------|
| `cabr_validate` | Hardcoded `score=0.85` | V1/V2/V3 content validation |
| `qwen_plan` | Hardcoded 3-step plan | Strategic planning |

---

## 7. Remaining Production Blockers

| Blocker | Description | Severity |
|---------|-------------|----------|
| H5a | `cabr_validate` returns hardcoded data | HIGH |
| H5c | `qwen_plan` returns hardcoded data | MEDIUM |
| H6 | No key rotation mechanism | LOW |
| H7 | No rate limiting | LOW |
| H8 | Local transport only (no TLS) | MEDIUM |

---

## 8. Candidate Backend Seam Analysis

### 8.1 cabr_validate

**Candidate files**:
- `modules/foundups/agent_market/src/cabr_hooks.py` — FoundUp health metrics (tasks, agents, completion rates)
- `modules/platform_integration/x_twitter/src/x_twitter_dae.py:CABREngine` — Smart DAO evolution for X/Twitter

**pAVS interface**: `cabr_validate(content, context) → {score, passed, v1/v2/v3_result}`

**Mismatch analysis**:
- `cabr_hooks.py` provides `CABRInput` with FoundUp-level metrics (tasks_total, completion_rate, etc.)
- pAVS `cabr_validate` expects content-level V1/V2/V3 validation (gate/verify/valuate)
- `CABREngine` in x_twitter is for Smart DAO scoring, not content validation

**Verdict**: Interface mismatch. Would require new adapter or redefining pAVS tool contract.

**Integration complexity**: HIGH (new code needed, unclear V1/V2/V3 spec)

### 8.2 qwen_plan

**Candidate file**: `holo_index/qwen_advisor/llm_engine.py:QwenInferenceEngine`

**Method**: `generate_response(prompt, system_prompt, max_tokens)`

**pAVS interface**: `qwen_plan(objective, constraints) → {plan[], reasoning, alternatives}`

**Seam strength**: MEDIUM — `QwenInferenceEngine` exists and works, but needs prompt engineering to format output as structured plan.

**Integration complexity**: MEDIUM (prompt wrapper + JSON parsing)

---

## 9. WSP 15 Next-Slice Scoring

| Candidate | Complexity | Importance | Deferability | Impact | Risk | **Total** |
|-----------|------------|------------|--------------|--------|------|-----------|
| `qwen_plan` | 3 | 3 | 3 | 3 | 2 | **14** |
| `cabr_validate` | 5 | 4 | 2 | 3 | 4 | **18** |

**Scoring**: Lower = higher priority

---

## 10. Recommended Next Slice

**MCPA9E_QWEN_PLAN_BACKEND_CONNECTION_PHASE1**

Rationale:
- `QwenInferenceEngine` already exists and is tested
- Prompt wrapper is straightforward (objective → plan JSON)
- `cabr_validate` has interface mismatch requiring spec clarification first
- Qwen completes the "AI planning" capability tier

---

## 11. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| gemma_classify is real backend via GemmaRAGInference | ✅ TRUE | `_call_gemma_classify()` imports and calls backend |
| pattern_recall/store are real backends via PatternMemory | ✅ TRUE | Delegates to `recall_successful_patterns()` and `store_outcome()` |
| fam_emit is real backend via FAM DAEmon | ✅ TRUE | `get_fam_daemon().emit_event()` |
| holo_search is real backend via S2/HoloIndex | ✅ TRUE | `_call_s2_holo_search()` |
| pAVS MCP is still only partially backend-ready | ✅ TRUE | 5/8 real, 2/8 placeholder, banner confirms |
| No production readiness overclaim | ✅ TRUE | README says "CABR/Qwen are PLACEHOLDERS" |

---

## HoloIndex Research

```bash
python holo_index.py --fast-search --search "MCPA9D gemma_classify GemmaRAGInference real_backend pAVS MCP qwen cabr re-audit" --limit 5
```

**Top CODE hit**: `holo_index/qwen_advisor/orchestration/autonomous_refactoring.py`
**Mode**: Lexical fallback (offline)

---

## Files Changed This Slice

- `docs/audits/mcp_system/MCPA9D_BACKEND_REAUDIT.md` (NEW)

No runtime code edits. No commits made.

---

*Worker W1 complete for MCPA9D_BACKEND_REAUDIT_PHASE1.*
