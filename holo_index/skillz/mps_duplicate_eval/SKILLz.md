---
name: mps_duplicate_eval
description: Evaluate DUPLICATE issues using WSP 15 MPS methodology
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
# MPS DUPLICATE Evaluation Skill

**Purpose**: Evaluate duplicate/similar functionality across modules.

**Agent**: Qwen (requires semantic understanding)

---

## What is DUPLICATE?

Similar functionality implemented in multiple places:
- Same utility function in 3+ modules
- Parallel implementations of same feature
- Copy-pasted code blocks

---

## Instructions

### Step 1: IDENTIFY DUPLICATE SCOPE

Severity by count:
- **2 copies**: Minor - may be intentional
- **3-5 copies**: Moderate - consolidation needed
- **5+ copies**: Severe - urgent consolidation

### Step 2: SCORE DIMENSIONS

**Complexity (C)**: Usually 3 (requires consolidation)
**Importance (I)**: Usually 3 (architectural coherence)
**Deferability (D)**: Usually 3 (should fix soon)
**Impact (Im)**: Usually 3 (improves maintainability)

---

## Benchmark Test Cases

### Test 1: Utility Duplication
- **Input**: "Similar `format_timestamp()` function exists in 4 different modules"
- **Expected**: C:3 I:3 D:3 Im:3 ↁETotal: 12 (P2)

### Test 2: Feature Duplication
- **Input**: "Retry logic implemented separately in `api_client.py` and `http_utils.py`"
- **Expected**: C:3 I:4 D:4 Im:4 ↁETotal: 15 (P1)

---

## Ground Truth Reference

```python
"DUPLICATE": {
    "complexity": 3,      # Moderate - requires consolidation
    "importance": 3,      # Important - architectural coherence
    "deferability": 3,    # Moderate - should fix soon
    "impact": 3           # Moderate - improves maintainability
}
# Total: 12 ↁEP2 (Medium priority)
```
