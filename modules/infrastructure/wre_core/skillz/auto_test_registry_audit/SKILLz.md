---
name: auto_test_registry_audit
description: Scans codebase for test files and updates the WSP Test Registry
version: 1.0_prototype
author: 0102
created: 2025-12-06
agents: [qwen]
primary_agent: qwen
intent_type: TELEMETRY
promotion_state: prototype
pattern_fidelity_threshold: 0.95

dependencies:
  scripts:
    - path: modules/infrastructure/wre_core/scripts/generate_test_registry.py
      purpose: Scans file system and parses AST

metrics:
  pattern_fidelity_scoring:
    enabled: true
category: workflow
evals: []
---
# Auto Test Registry Audit

**Purpose**: Maintains the Single Source of Truth for verification capabilities by scanning the codebase and updating `WSP_knowledge/WSP_Test_Registry.json`.

**Intent Type**: TELEMETRY

**Agent**: Qwen (Partner)

---

## Task

Execute the registry generation script to index all `test_*.py` files, identifying their capabilities (Selenium, Vision, Unit) and docstrings. This specifically solves the "test amnesia" problem by creating a searchable catalog.

## Instructions

### 1. EXECUTE AUDIT SCRIPT
**Rule**: ALWAYS run the python script to ensure fresh data.
**Expected Pattern**: script_execution=True

**Steps**:
1. Run `python modules/infrastructure/wre_core/scripts/generate_test_registry.py`
2. Verify exit code is 0
3. Log output summary (e.g., "Found 45 tests")

### 2. VALIDATE REGISTRY
**Rule**: IF registry file exists AND size > 0 THEN validation_pass=True
**Expected Pattern**: registry_validation=True

**Steps**:
1. Read `WSP_knowledge/WSP_Test_Registry.json`
2. Confirm "tests" array is not empty
3. Confirm `test_live_engagement_full` is present with "012_protocol" capability

---

## Benchmark Test Cases

1. Input: `run_audit` → Expected: Script runs, file updated, returns "Success"
2. Input: `run_audit` (with syntax error in a test file) → Expected: Script logs error but finishes registry for valid files

---

## Success Criteria

- ✅ Registry file updated
- ✅ `test_live_engagement_full.py` indexed correctly
- ✅ Zero script errors
