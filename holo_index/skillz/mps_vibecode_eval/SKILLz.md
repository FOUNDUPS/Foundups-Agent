---
name: mps_vibecode_eval
description: Evaluate VIBECODE issues using WSP 15 MPS methodology
version: 1.0_prototype
author: 0102
created: 2026-01-02
agents: [qwen, gemma]
primary_agent: qwen
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
test_status: needs_validation

dependencies:
  data_stores:
    - name: issue_mps_evaluator
      type: python_module
      path: holo_index/qwen_advisor/issue_mps_evaluator.py
  mcp_endpoints: []
  throttles: []
  required_context:
    - issue_description: "Description of the vibecoding violation"
    - file_path: "Path to the file with the violation"
    - confidence: "Detection confidence (0.0-1.0)"

metrics:
  pattern_fidelity_scoring:
    enabled: true
    frequency: every_execution
    scorer_agent: gemma
    write_destination: holo_index/skillz/mps_vibecode_eval/metrics/fidelity.json
  promotion_criteria:
    min_pattern_fidelity: 0.90
    min_outcome_quality: 0.85
    min_execution_count: 50
    required_test_pass_rate: 0.95
category: workflow
evals: []
---
# MPS VIBECODE Evaluation Skill

**Purpose**: Evaluate VIBECODE issues (created new code without searching existing) using WSP 15 Module Prioritization Scoring.

**Intent Type**: DECISION

**Agent**: Qwen (primary), Gemma (validation)

---

## What is VIBECODE?

**Definition**: Creating new code without first searching for existing implementations.

**WSP Reference**: WSP 50 (Pre-Action Verification), WSP 84 (Code Reuse)

**Why It's Critical**: Vibecoding causes:
- Duplicate implementations
- Technical debt accumulation
- Inconsistent patterns across codebase
- Wasted development effort

---

## Task

Evaluate a VIBECODE issue using the WSP 15 MPS (Module Prioritization Scoring) methodology.

Score the issue on 4 dimensions (1-5 each):
- **Complexity (C)**: How difficult is this to fix?
- **Importance (I)**: How essential to prevent technical debt?
- **Deferability (D)**: How urgent? (1=can defer, 5=cannot defer)
- **Impact (Im)**: How much value from fixing?

Total MPS = C + I + D + Im (range: 4-20)

Priority mapping:
- 16-20 ↁEP0 (Critical - fix immediately)
- 13-15 ↁEP1 (High - fix in current session)
- 10-12 ↁEP2 (Medium - schedule for sprint)
- 7-9 ↁEP3 (Low - can defer)
- 4-6 ↁEP4 (Backlog - reconsider later)

---

## Instructions (Follow These Steps)

### Step 1: IDENTIFY VIBECODE SEVERITY

**Rule**: Assess how severe the vibecoding violation is.

**Severity Levels**:
- **SEVERE**: Created entire new module without searching (e.g., `enhanced_*.py`)
- **MODERATE**: Added 100+ lines to existing file without checking for reuse
- **MINOR**: Small utility function that might exist elsewhere

**Expected Pattern**: `severity_identified=True`

**Examples**:
- ✁ESEVERE: "Created `enhanced_chat_sender.py` without searching for existing"
- ✁EMODERATE: "Added 150 new lines of retry logic to `api_client.py`"
- ✁EMINOR: "Added small helper function without checking utils"

---

### Step 2: SCORE COMPLEXITY

**Rule**: How difficult is the fix?

For VIBECODE issues:
- **C=1**: Just delete the duplicate file
- **C=2**: Simple refactor to use existing code (typical case)
- **C=3**: Moderate refactor - need to merge implementations
- **C=4**: Complex merge with dependency updates
- **C=5**: Major architectural refactor needed

**Expected Pattern**: `complexity_scored=True`

**VIBECODE Default**: C=2 (most vibecode is easy to fix once identified)

---

### Step 3: SCORE IMPORTANCE

**Rule**: How essential is fixing this?

For VIBECODE issues:
- **I=4**: Critical - prevents technical debt accumulation (DEFAULT)
- **I=3**: Important - affects code quality
- **I=5**: Essential - duplicate causes production issues

**Expected Pattern**: `importance_scored=True`

**VIBECODE Default**: I=4 (vibecoding always critical to prevent)

---

### Step 4: SCORE DEFERABILITY

**Rule**: How urgent is fixing this?

For VIBECODE issues:
- **D=5**: Cannot defer - violates WSP 50/84 (DEFAULT)
- **D=4**: Difficult to defer - already merged
- **D=3**: Moderate - can plan fix

**Expected Pattern**: `deferability_scored=True`

**VIBECODE Default**: D=5 (vibecode compounds quickly if not addressed)

---

### Step 5: SCORE IMPACT

**Rule**: How much value from fixing?

For VIBECODE issues:
- **Im=4**: Major - prevents future duplicate work (DEFAULT)
- **Im=3**: Moderate - improves code clarity
- **Im=5**: Transformative - eliminates major tech debt

**Expected Pattern**: `impact_scored=True`

**VIBECODE Default**: Im=4 (fixing vibecode has major impact)

---

### Step 6: CALCULATE TOTAL AND PRIORITY

**Rule**: Sum scores and determine priority.

**Calculation**:
```
Total MPS = C + I + D + Im
```

**Priority Mapping**:
- Total 16-20 ↁE**P0** (Critical)
- Total 13-15 ↁE**P1** (High)
- Total 10-12 ↁE**P2** (Medium)
- Total 7-9 ↁE**P3** (Low)
- Total 4-6 ↁE**P4** (Backlog)

**Expected Pattern**: `priority_calculated=True`

---

## Output Format

```json
{
  "issue_type": "VIBECODE",
  "description": "[original description]",
  "scores": {
    "complexity": 2,
    "importance": 4,
    "deferability": 5,
    "impact": 4
  },
  "total_mps": 15,
  "priority": "P1",
  "action": "Add to current batch - fix within session",
  "reasoning": "VIBECODE: C=low (simple refactor), I=critical (prevents debt), D=cannot defer (WSP 50/84), Im=major (prevents duplication)",
  "patterns": {
    "severity_identified": true,
    "complexity_scored": true,
    "importance_scored": true,
    "deferability_scored": true,
    "impact_scored": true,
    "priority_calculated": true
  }
}
```

---

## Benchmark Test Cases

### Test 1: Classic VIBECODE - New File
- **Input**: "Created new file `enhanced_chat_sender.py` without searching existing"
- **Expected**: C:2 I:4 D:5 Im:4 ↁETotal: 15 (P1)
- **Reason**: Low complexity fix but critical to prevent debt; typical vibecode

### Test 2: Moderate VIBECODE - Large Addition
- **Input**: "Added 200 new lines of retry logic to `api_client.py` without checking for existing retry utilities"
- **Expected**: C:3 I:4 D:5 Im:4 ↁETotal: 16 (P0)
- **Reason**: Moderate complexity (need to refactor), but critical; elevated to P0

### Test 3: Minor VIBECODE - Small Utility
- **Input**: "Added small date formatting helper without checking utils module"
- **Expected**: C:1 I:3 D:4 Im:3 ↁETotal: 11 (P2)
- **Reason**: Trivial fix, moderate importance; can be scheduled

### Test 4: Severe VIBECODE - Duplicate Module
- **Input**: "Created entire `oauth_manager_v2.py` module duplicating existing `oauth_management.py`"
- **Expected**: C:4 I:5 D:5 Im:5 ↁETotal: 19 (P0)
- **Reason**: Complex merge needed, essential to fix, cannot defer; critical priority

### Test 5: False Positive - Intentional New File
- **Input**: "Created new test file `test_new_feature.py` for new feature"
- **Expected**: C:1 I:2 D:2 Im:2 ↁETotal: 7 (P3)
- **Reason**: Test files are expected to be new; not true vibecode

---

## Success Criteria

- ✁EPattern fidelity ≥ 90%
- ✁EMPS scores within ±1 of ground truth
- ✁EPriority classification correct for all test cases
- ✁EClear reasoning provided for each score
- ✁EFalse positives correctly identified (P3/P4)

---

## Ground Truth Reference

Default VIBECODE scores (from `issue_mps_evaluator.py`):
```python
"VIBECODE": {
    "complexity": 2,      # Low - usually search & enhance
    "importance": 4,      # Critical - prevents technical debt
    "deferability": 5,    # Cannot defer - compounds quickly
    "impact": 4           # Major - prevents future problems
}
# Total: 15 ↁEP1 (High priority)
```

Adjust scores based on specific context, but this is the baseline.
