# MCPA9E: S3 Qwen Plan Backend Connection Audit

**Author**: 0102 (Worker W1)
**Date**: 2026-05-10
**Status**: COMPLETE
**WSP**: 96 (MCP Governance), 97 (Truth Boundaries)
**Slice**: `MCPA9E_QWEN_PLAN_BACKEND_CONNECTION_PHASE1`

## Summary

Connected S3 `qwen_plan` to real QwenInferenceEngine backend via llama_cpp.
The tool now generates actual strategic plans from local Qwen model instead
of returning hardcoded placeholder data.

## Before/After

### Before (Placeholder)
```python
async def qwen_plan(self, objective: str, constraints: dict = None):
    # Hardcoded 3-step plan
    return {
        "status": "ok",
        "data": {
            "plan": ["Step 1: Analyze", "Step 2: Execute", "Step 3: Review"],
            "reasoning": "Standard 3-step approach"
        },
        "meta": {"real_backend": False, "implementation_status": "placeholder_stub"}
    }
```

### After (Real Backend)
```python
async def qwen_plan(self, objective: str, constraints: dict = None):
    # Real Qwen inference via llama_cpp
    engine = _get_qwen_engine()  # Lazy singleton
    prompt = f"Create a strategic plan for: {objective}\n..."
    response = engine.generate_response(prompt)
    steps = _parse_plan_steps(response)
    return {
        "status": "ok",
        "data": {"plan": steps, "objective": objective, "constraints": constraints},
        "meta": {"real_backend": True, "delegated_to": "QWEN"}
    }
```

## Callable Seam

| Component | Location | Method |
|-----------|----------|--------|
| Model path resolver | `modules/infrastructure/shared_utilities/local_model_selection.py` | `resolve_code_model_path()` |
| Qwen engine | `holo_index/qwen_advisor/llm_engine.py` | `QwenInferenceEngine` |
| Inference method | `llm_engine.py` | `generate_response(prompt) -> str` |

## Implementation Pattern

```python
_QWEN_BACKEND_AVAILABLE: Optional[bool] = None
_QWEN_ENGINE: Optional[Any] = None

def _get_qwen_engine() -> Any:
    """Lazy singleton for Qwen engine."""
    global _QWEN_ENGINE
    if _QWEN_ENGINE is not None:
        return _QWEN_ENGINE
    
    from modules.infrastructure.shared_utilities.local_model_selection import resolve_code_model_path
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
    
    model_path = resolve_code_model_path()
    _QWEN_ENGINE = QwenInferenceEngine(
        model_path=model_path,
        max_tokens=512,
        temperature=0.3,
        context_length=2048
    )
    return _QWEN_ENGINE

def _call_qwen_plan(objective: str, constraints: Optional[dict] = None) -> dict:
    """Delegate to QwenInferenceEngine for strategic planning."""
    engine = _get_qwen_engine()
    
    prompt = f"""Create a strategic plan for the following objective.

Objective: {objective}
{f'Constraints: {constraints}' if constraints else ''}

Provide a numbered list of actionable steps (1-5 steps).
Each step should be specific and achievable.
"""
    
    response = engine.generate_response(prompt)
    steps = _parse_plan_steps(response)
    
    if not steps:
        raise RuntimeError("Qwen returned empty plan response")
    
    return {
        "plan": steps,
        "objective": objective,
        "constraints": constraints or {},
        "model": "qwen-local"
    }
```

## Error Handling

| Condition | Error Code | Behavior |
|-----------|------------|----------|
| Model not found | `BACKEND_UNAVAILABLE` | `meta.real_backend=False` |
| Empty response | `BACKEND_UNAVAILABLE` | RuntimeError raised, caught as unavailable |
| Empty objective | `INVALID_INPUT` | Rejected before backend call |

## Test Coverage

**File**: `modules/infrastructure/pavs_mcp/tests/test_server_holo_search.py`
**Class**: `TestQwenBackendDelegation` (12 tests)

| Test | Purpose |
|------|---------|
| `test_qwen_plan_returns_ok_or_unavailable` | Status field validation |
| `test_qwen_plan_meta_shows_qwen_delegation` | Delegation metadata |
| `test_qwen_plan_empty_objective_rejected` | Input validation |
| `test_qwen_plan_constraints_passthrough` | Constraint echoing |
| `test_qwen_plan_data_contains_plan_steps` | Plan array validation |
| ... | 7 more tests |

**File**: `modules/infrastructure/pavs_mcp/tests/test_transport.py`
**Class**: `TestQwenViaTransport` (3 tests)

## Test Results

```
PYTHONPATH=. python -m pytest modules/infrastructure/pavs_mcp/tests/ -q
137 passed, 35 warnings in 194.68s
```

## Backend Status After MCPA9E

| Tool | Real Backend | Delegated To |
|------|-------------|--------------|
| holo_search | YES | S2/HoloIndex |
| fam_emit | YES | FAM_DAEMON |
| pattern_recall | YES | PATTERN_MEMORY |
| pattern_store | YES | PATTERN_MEMORY |
| gemma_classify | YES | GEMMA |
| qwen_plan | YES | QWEN |
| cabr_validate | NO | (placeholder) |
| foundup_register | N/A | (registration stub) |

## WSP 97 Truth Boundary Note

Real backends (6 tools) return:
- `meta.real_backend = True`
- `meta.implementation_status = "real_backend"`
- `meta.delegated_to = "<BACKEND_NAME>"`

Placeholder (cabr_validate) returns:
- `meta.real_backend = False`
- `meta.implementation_status = "placeholder_stub"`

Conforming clients MUST check `meta.real_backend` before treating results
as production-grade per WSP 96 Annex A.5 C3.

## Next Steps

- **MCPA10**: Connect `cabr_validate` to real CABR engine (final placeholder)
- Consider load testing for concurrent Qwen calls (lazy singleton may need mutex)
