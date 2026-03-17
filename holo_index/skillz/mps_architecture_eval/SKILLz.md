---
name: mps_architecture_eval
description: Evaluate ARCHITECTURE issues using WSP 15 MPS methodology
version: 1.0_prototype
author: 0102
created: 2026-01-02
agents: [qwen]
primary_agent: qwen
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: workflow
evals: []
---
# MPS ARCHITECTURE Evaluation Skill

**Purpose**: Evaluate architectural issues that require refactoring.

**Agent**: Qwen (requires deep analysis)

---

## What is ARCHITECTURE?

Issues requiring structural changes to the codebase:
- Module exceeds size limits (WSP 62/87)
- Circular dependencies
- Incorrect layer boundaries
- Poor separation of concerns

---

## Instructions

### Step 1: CLASSIFY ARCHITECTURE ISSUE

Types:
- **SIZE**: Module too large (>1500 lines)
- **CIRCULAR**: Circular import dependencies
- **BOUNDARY**: Layer violation (e.g., DAE calling infrastructure directly)
- **COHESION**: Poor module cohesion

### Step 2: SCORE DIMENSIONS

**Complexity (C)**: Usually 4 (requires careful refactoring)
**Importance (I)**: Usually 5 (essential for system structure)
**Deferability (D)**: Usually 3 (plan carefully)
**Impact (Im)**: Usually 5 (transformative improvement)

---

## Benchmark Test Cases

### Test 1: Size Violation
- **Input**: "Module `orchestrator.py` has 2100 lines, needs WSP 62 refactoring"
- **Expected**: C:4 I:5 D:3 Im:5 ↁETotal: 17 (P0)

### Test 2: Circular Dependency
- **Input**: "Module A imports Module B which imports Module A"
- **Expected**: C:4 I:5 D:4 Im:4 ↁETotal: 17 (P0)

### Test 3: Layer Boundary Violation
- **Input**: "DAE directly accesses database instead of going through infrastructure layer"
- **Expected**: C:3 I:4 D:3 Im:4 ↁETotal: 14 (P1)

---

## Ground Truth Reference

```python
"ARCHITECTURE": {
    "complexity": 4,      # High - requires careful refactoring
    "importance": 5,      # Essential - system structure
    "deferability": 3,    # Moderate - plan carefully
    "impact": 5           # Transformative - major improvement
}
# Total: 17 ↁEP0 (Critical)
```
