---
name: mps_dead_code_eval
description: Evaluate DEAD_CODE issues using WSP 15 MPS methodology
version: 1.0_prototype
author: 0102
created: 2026-01-02
agents: [gemma, qwen]
primary_agent: gemma
intent_type: CLASSIFICATION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: workflow
evals: []
---
# MPS DEAD_CODE Evaluation Skill

**Purpose**: Evaluate dead/orphan code that is never imported or used.

**Agent**: Gemma (primary - simple pattern matching), Qwen (validation)

---

## What is DEAD_CODE?

Code that exists but is never used:
- Orphaned modules (no imports)
- Unused functions
- Commented-out code blocks
- Deprecated modules not removed

---

## Instructions

### Step 1: VERIFY ORPHAN STATUS

Use Gemma L0 pattern matching:
```python
# Check if any file imports this module
grep_result = grep("from {module_name} import|import {module_name}")
is_orphan = len(grep_result) == 0
```

### Step 2: SCORE DIMENSIONS

**Complexity (C)**: Usually 1 (just delete)
**Importance (I)**: Usually 2 (helpful for cleaner codebase)
**Deferability (D)**: Usually 2 (not urgent)
**Impact (Im)**: Usually 2 (reduces bloat)

---

## Benchmark Test Cases

### Test 1: Orphaned Module
- **Input**: "Module `old_auth_handler.py` has no imports anywhere in codebase"
- **Expected**: C:1 I:2 D:2 Im:2 ↁETotal: 7 (P3)

### Test 2: Unused Large Module
- **Input**: "800-line module `legacy_processor.py` never imported, has documentation"
- **Expected**: C:2 I:3 D:2 Im:3 ↁETotal: 10 (P2)
- **Reason**: Need to verify no side effects before deletion

### Test 3: False Positive - Entry Point
- **Input**: "Module `main.py` has no imports (it's the entry point)"
- **Expected**: C:1 I:1 D:1 Im:1 ↁETotal: 4 (P4)
- **Reason**: Entry points are not orphans

---

## Ground Truth Reference

```python
"DEAD_CODE": {
    "complexity": 1,      # Trivial - just delete unused code
    "importance": 2,      # Helpful - cleaner codebase
    "deferability": 2,    # Deferrable - not urgent
    "impact": 2           # Minor - reduces bloat
}
# Total: 7 ↁEP3 (Low priority)
```
