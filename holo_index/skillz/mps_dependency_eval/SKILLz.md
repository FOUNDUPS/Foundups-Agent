---
name: mps_dependency_eval
description: Evaluate DEPENDENCY issues using WSP 15 MPS methodology
version: 1.0_prototype
author: 0102
created: 2026-01-02
agents: [qwen, gemma]
primary_agent: qwen
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: workflow
evals: []
---
# MPS DEPENDENCY Evaluation Skill

**Purpose**: Evaluate dependency issues (circular imports, version conflicts, missing deps).

**Agent**: Qwen (primary)

---

## What is DEPENDENCY?

Dependency-related problems:
- Circular imports
- Missing dependencies in requirements.txt
- Version conflicts
- Import errors at runtime

---

## Instructions

### Step 1: CLASSIFY DEPENDENCY ISSUE

Types:
- **CIRCULAR**: A imports B imports A
- **MISSING**: Module imports package not in requirements
- **CONFLICT**: Version incompatibility
- **BROKEN**: Import fails at runtime

### Step 2: SCORE DIMENSIONS

**Complexity (C)**: Usually 3 (requires analysis)
**Importance (I)**: Usually 4 (can break system)
**Deferability (D)**: Usually 4 (risks cascading)
**Impact (Im)**: Usually 4 (system stability)

---

## Benchmark Test Cases

### Test 1: Circular Import
- **Input**: "Circular import: `auth.py` imports `session.py` which imports `auth.py`"
- **Expected**: C:3 I:4 D:4 Im:4 ↁETotal: 15 (P1)

### Test 2: Missing Dependency
- **Input**: "Module imports `pydantic` but not in requirements.txt"
- **Expected**: C:1 I:4 D:5 Im:3 ↁETotal: 13 (P1)

### Test 3: Version Conflict
- **Input**: "Package A requires `numpy>=2.0` but Package B requires `numpy<2.0`"
- **Expected**: C:4 I:5 D:5 Im:4 ↁETotal: 18 (P0)

---

## Ground Truth Reference

```python
"DEPENDENCY": {
    "complexity": 3,      # Moderate - requires analysis
    "importance": 4,      # Critical - can break system
    "deferability": 4,    # Difficult to defer - risks cascading
    "impact": 4           # Major - system stability
}
# Total: 15 ↁEP1 (High priority)
```
