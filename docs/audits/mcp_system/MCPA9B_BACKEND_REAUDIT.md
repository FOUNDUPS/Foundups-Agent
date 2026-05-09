# MCPA9B Backend Re-Audit

**Slice**: MCPA9B_BACKEND_REAUDIT_PHASE1
**Worker**: W1
**Date**: 2026-05-09
**PR**: #539 (70a206d27)
**Verdict**: `HOLO_SEARCH_AND_FAM_EMIT_BACKENDS_CONFIRMED_PARTIAL_BACKEND_READY`

---

## 1. Preconditions

| Check | Status |
|-------|--------|
| PR #539 merged | ✓ 70a206d27 |
| 86/86 tests passing | ✓ |
| holo_search real_backend=true | ✓ |
| fam_emit real_backend=true | ✓ |

---

## 2. Backend Readiness Table

| Tool | Status | Backend | Callable Seam | Notes |
|------|--------|---------|---------------|-------|
| `holo_search` | **REAL** | S2/HoloIndex | `holo_search()` via MCP | Delegated, tested |
| `fam_emit` | **REAL** | FAM DAEmon | `get_fam_daemon().emit()` | Singleton, dual-write |
| `foundup_register` | **STUB** | Local JSON | N/A | Auth bootstrap only |
| `pattern_recall` | **PLACEHOLDER** | — | `PatternMemory.recall_successful_patterns()` | **Strong seam** |
| `pattern_store` | **PLACEHOLDER** | — | `PatternMemory.store_outcome()` | **Strong seam** |
| `cabr_validate` | **PLACEHOLDER** | — | `CABRHooks.check_foundup_health()` | Interface mismatch |
| `gemma_classify` | **PLACEHOLDER** | — | `gemma_rag_inference.py` | Adapter needed |
| `qwen_plan` | **PLACEHOLDER** | — | `qwen_strategic_planner.py` | Adapter needed |

---

## 3. WSP 15 Prioritization Scoring

Scale: 1 (low) to 5 (high)

| Backend | Complexity | Importance | Deferability | Impact | Risk | **Total** |
|---------|------------|------------|--------------|--------|------|-----------|
| **pattern_recall** | 2 | 4 | 2 | 4 | 1 | **13** |
| **pattern_store** | 2 | 4 | 2 | 4 | 1 | **13** |
| gemma_classify | 3 | 3 | 3 | 3 | 2 | 14 |
| qwen_plan | 4 | 3 | 4 | 3 | 3 | 17 |
| cabr_validate | 4 | 4 | 3 | 4 | 3 | 18 |

### Scoring Rationale

**pattern_recall / pattern_store (Score: 13 - LOWEST = HIGHEST PRIORITY)**
- **Complexity: 2** — Direct callable seam exists. `PatternMemory` singleton at `pattern_memory.py:82-87`. Methods `recall_successful_patterns(skill, min_fidelity, limit)` and `store_outcome(SkillOutcome)` match pAVS interface exactly.
- **Importance: 4** — Enables WRE recursive learning loop. FoundUps need pattern memory for skill evolution.
- **Deferability: 2** — Other backends depend on pattern storage for learning.
- **Impact: 4** — Completes WRE trigger chain: Skill → Execute → Store → Recall → Improve.
- **Risk: 1** — Singleton pattern proven. SQLite backend stable. No new dependencies.

**gemma_classify (Score: 14)**
- **Complexity: 3** — Requires adapter from `gemma_rag_inference.py`. Model loading pattern exists but needs classification wrapper.
- **Importance: 3** — Binary classification useful but not blocking.
- **Deferability: 3** — Can defer until pattern memory works.
- **Impact: 3** — Enables V1/V2 gates but CABR has higher abstraction.
- **Risk: 2** — Model loading on Windows has known quirks.

**qwen_plan (Score: 17)**
- **Complexity: 4** — Strategic planning requires prompt engineering. No direct callable seam.
- **Importance: 3** — Planning useful for complex tasks.
- **Deferability: 4** — Can defer; 012/0102 handles planning currently.
- **Impact: 3** — Autonomous planning valuable but not critical path.
- **Risk: 3** — LLM output parsing, timeout handling.

**cabr_validate (Score: 18 - HIGHEST = LOWEST PRIORITY)**
- **Complexity: 4** — `CABRHooks.check_foundup_health()` returns health scoring, NOT content V1/V2/V3 validation. Interface mismatch requires redesign.
- **Importance: 4** — CABR engine critical for validation but current hooks don't match pAVS tool signature.
- **Deferability: 3** — Can use gemma_classify for binary gates meanwhile.
- **Impact: 4** — Full V3 engine integration high-value but high-effort.
- **Risk: 3** — Semantic gap between health scoring and content validation.

---

## 4. WSP 97 Truth Table

| Tool | real_backend | delegated_to | implementation_status |
|------|--------------|--------------|----------------------|
| holo_search | true | S2 | real_backend |
| fam_emit | true | FAM_DAEmon | real_backend |
| foundup_register | false | — | placeholder_stub |
| pattern_recall | false | — | placeholder_stub |
| pattern_store | false | — | placeholder_stub |
| cabr_validate | false | — | placeholder_stub |
| gemma_classify | false | — | placeholder_stub |
| qwen_plan | false | — | placeholder_stub |

---

## 5. Evidence: PatternMemory Callable Seams

**File**: `modules/infrastructure/wre_core/src/pattern_memory.py`

### Singleton Pattern (lines 82-87)
```python
_pattern_memory_instance: Optional["PatternMemory"] = None

def get_pattern_memory() -> "PatternMemory":
    global _pattern_memory_instance
    if _pattern_memory_instance is None:
        _pattern_memory_instance = PatternMemory()
    return _pattern_memory_instance
```

### recall_successful_patterns (line 485)
```python
def recall_successful_patterns(
    self,
    skill_name: str,
    min_fidelity: float = 0.90,
    limit: int = 10
) -> List[Dict[str, Any]]:
```
**pAVS interface match**: `pattern_recall(skill, min_fidelity)` → returns `patterns[]`

### store_outcome (line 331)
```python
def store_outcome(self, outcome: SkillOutcome) -> str:
```
**pAVS interface match**: `pattern_store(skill, outcome)` → returns `pattern_id`

---

## 6. Recommended Next Slice

**MCPA9C_PATTERN_MEMORY_BACKEND_CONNECTION_PHASE1**

### Justification
1. **Lowest WSP 15 score** (13) = highest priority
2. **Direct callable seam** — No adapter design needed
3. **Singleton pattern** — Same as FAM DAEmon (proven)
4. **Interface alignment** — Methods match pAVS tool signatures
5. **Low risk** — SQLite backend stable, no new dependencies
6. **Unblocks learning loop** — Pattern storage enables recursive improvement

### Implementation Estimate
- **LOC**: ~60-80 (adapter + delegation)
- **Tests**: ~10-15 new test cases
- **Risk**: LOW

---

## 7. Verdict

```
HOLO_SEARCH_AND_FAM_EMIT_BACKENDS_CONFIRMED_PARTIAL_BACKEND_READY
```

**2/8 tools have real backends. Next: pattern_recall + pattern_store via PatternMemory singleton.**

---

*Audited by W1 | MCPA9B_BACKEND_REAUDIT_PHASE1 | 2026-05-09*
