---
name: mps_wsp_violation_eval
description: Evaluate WSP_VIOLATION issues using WSP 15 MPS methodology
version: 1.0_prototype
author: 0102
created: 2026-01-02
agents: [qwen, gemma]
primary_agent: qwen
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
test_status: needs_validation
category: workflow
evals: []
---
# MPS WSP_VIOLATION Evaluation Skill

**Purpose**: Evaluate WSP protocol violations using WSP 15 MPS methodology.

**Agent**: Qwen (primary), Gemma (validation)

---

## What is a WSP_VIOLATION?

**Definition**: Code or structure that violates a documented WSP protocol.

**Common Violations**:
- WSP 49: File in wrong directory (e.g., test file in root)
- WSP 87: Large file exceeding size limits
- WSP 3: Module not following domain structure
- WSP 57: Naming convention violation

---

## Instructions

### Step 1: IDENTIFY VIOLATED WSP

Determine which WSP protocol is violated:
- **WSP 3**: Module organization
- **WSP 49**: Directory structure
- **WSP 57**: Naming conventions
- **WSP 87**: File size limits
- **Other**: Specify

**Expected Pattern**: `wsp_identified=True`

### Step 2: SCORE DIMENSIONS

**Complexity (C)**: Usually 1 (trivial path/structure fix)
**Importance (I)**: Usually 4 (WSP compliance essential)
**Deferability (D)**: Usually 4 (violations accumulate)
**Impact (Im)**: Usually 3 (improves compliance)

### Step 3: CALCULATE PRIORITY

**Default WSP_VIOLATION**: C:1 I:4 D:4 Im:3 ↁETotal: 12 (P2)

---

## Benchmark Test Cases

### Test 1: File in Wrong Directory
- **Input**: "Test file `test_auth.py` in project root instead of `tests/`"
- **Expected**: C:1 I:4 D:4 Im:3 ↁETotal: 12 (P2)
- **Reason**: Trivial move, but important for WSP 49 compliance

### Test 2: Large File Violation
- **Input**: "Module `orchestrator.py` has 1800 lines, exceeds WSP 87 limit of 1500"
- **Expected**: C:4 I:4 D:3 Im:4 ↁETotal: 15 (P1)
- **Reason**: Complex refactor needed; elevated to P1

### Test 3: Naming Violation
- **Input**: "Class `Enhanced_ChatSender` uses underscore in class name"
- **Expected**: C:1 I:3 D:3 Im:2 ↁETotal: 9 (P3)
- **Reason**: Simple rename, moderate importance

---

## Ground Truth Reference

```python
"WSP_VIOLATION": {
    "complexity": 1,      # Trivial - usually path/structure fixes
    "importance": 4,      # Critical - WSP compliance essential
    "deferability": 4,    # Difficult to defer - violations accumulate
    "impact": 3           # Moderate - improves compliance
}
# Total: 12 ↁEP2 (Medium priority)
```
