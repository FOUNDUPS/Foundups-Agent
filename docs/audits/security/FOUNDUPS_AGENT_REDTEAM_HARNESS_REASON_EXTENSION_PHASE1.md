# FoundUps Agent Red-Team Harness Reason Extension — Phase 1

**Contract ID**: FOUNDUPS_AGENT_REDTEAM_HARNESS_REASON_EXTENSION_PHASE1
**Status**: IMPLEMENTED
**Author**: 0102
**Date**: 2026-05-22
**Base Commit**: origin/main
**Branch**: feat/redteam-harness-reason-extension-phase1

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| REDTEAM_HARNESS_REASON_EXTENSION_ONLY | YES |
| TEST_HARNESS_ONLY | YES |
| NO_PRODUCTION_CODE_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_CI_GATE_ACTIVATION | YES |
| NO_REAL_SECRET_ACCESS | YES |
| NO_NETWORK_CALL | YES |
| NO_HOLOINDEX_MUTATION | YES |
| NO_AGENTDB_MUTATION | YES |
| ZERO_SKIPPED_TESTS_REQUIRED | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Mission

Tighten the red-team harness reason-code and scope-normalization layer before Family C implementation.

### 1.1 Problem Statement

Family A's `_action_in_scope` used naive `target.startswith(pattern)` matching, vulnerable to:
- Path traversal: `docs/../src/malicious.py` bypasses `write:docs/*`
- Cross-tenant access: No detection of tenant isolation violations
- Tool escalation: No distinction between "tool not granted" vs "scope violation"

Fine-grained reason codes existed in `reasons.py` but were not wired:
- `PERMISSION_ESCALATION_DENIED`
- `TENANT_ISOLATION_VIOLATION`
- `TOOL_NOT_GRANTED`

### 1.2 Canonical Inputs

| Source | Path |
|--------|------|
| Harness Skeleton | `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_HARNESS_SKELETON_PHASE2.md` |
| Reason Codes | `modules/infrastructure/wre_core/tests/redteam/reasons.py` |
| Harness Fixtures | `modules/infrastructure/wre_core/tests/redteam/conftest.py` |
| Family A Tests | `modules/infrastructure/wre_core/tests/redteam/test_scope_lock_violation.py` |

---

## 2. HoloIndex Assessment

| Query | Hits | Quality |
|-------|------|---------|
| `redteam harness reason codes path normalization _action_in_scope tenant isolation tool not granted` | 32 | LOW (no direct redteam hits) |
| `Family A scope lock naive startswith path traversal reason extension` | 32 | LOW (no direct redteam hits) |

**Retrieval Notes**:
- Redteam directory not yet indexed with high semantic weight
- Fell back to direct file reads

---

## 3. Implementation

### 3.1 Path Normalization

Added `_normalize_and_classify()` method:

```python
def _normalize_and_classify(self, action: str, target: str) -> Tuple[str, Optional[ReasonCode]]:
    # Reject .. traversal immediately
    if ".." in target:
        return target, ReasonCode.PERMISSION_ESCALATION_DENIED
    
    # Normalize slashes
    normalized = posixpath.normpath(target.replace("\\", "/")).lstrip("/")
    
    # Double-check post-normalization
    if ".." in normalized:
        return target, ReasonCode.PERMISSION_ESCALATION_DENIED
    
    # Cross-tenant detection
    if self._is_cross_tenant(normalized):
        return normalized, ReasonCode.TENANT_ISOLATION_VIOLATION
    
    # Tool not granted detection
    action_perms = [p for p in self.permissions if p.startswith(f"{action}:")]
    if not action_perms:
        return normalized, ReasonCode.TOOL_NOT_GRANTED
    
    return normalized, None
```

### 3.2 Reason Code Mapping

| Input Pattern | Reason Code | Priority |
|---------------|-------------|----------|
| `..` anywhere in path | PERMISSION_ESCALATION_DENIED | 1 (highest) |
| `tenant_<other>/` in path | TENANT_ISOLATION_VIOLATION | 2 |
| Action not in any permission | TOOL_NOT_GRANTED | 3 |
| Path outside granted scope | SCOPE_VIOLATION | 4 (default) |

### 3.3 New Threat Scenarios

| Scenario ID | Target | Expected Reason |
|-------------|--------|-----------------|
| SL-002-traversal | `docs/../src/malicious.py` | PERMISSION_ESCALATION_DENIED |
| SL-003-tenant | `tenant_other/data/secrets.json` | TENANT_ISOLATION_VIOLATION |
| SL-004-tool | delete with only read:* | TOOL_NOT_GRANTED |
| SL-005-nested-traversal | `docs/sub/../../etc/passwd` | PERMISSION_ESCALATION_DENIED |

---

## 4. Test Results

### 4.1 Red-Team Suite

```
============================= 30 passed in 0.33s ==============================

Family A: 13 passed (8 W7 SL-001..SL-006 + 5 new reason-extension)
Family B: 14 passed (preserved)
Family C: 3 passed (preserved)
```

Family A breakdown:
- W7 W6 carry-over (8): SL-001, SL-001-neg, SL-001b, SL-002, SL-003, SL-004, SL-005, SL-006
  - SL-002 and SL-004 expected_reason upgraded from SCOPE_VIOLATION to TOOL_NOT_GRANTED
    (the previously-aspirational reason is now wired)
- REASON_EXTENSION (5): SL-002-traversal, SL-003-tenant, SL-004-tool,
  SL-005-nested-traversal, SL-negative-same-tenant

### 4.2 Vault Resolver Suite

```
============================= 47 passed in 2.18s ==============================
```

### 4.3 New Tests Added

| Test | What It Verifies |
|------|------------------|
| `test_SL_002_path_traversal_blocked_with_escalation_reason` | `..` returns PERMISSION_ESCALATION_DENIED |
| `test_SL_003_cross_tenant_blocked_with_isolation_reason` | tenant_other/ returns TENANT_ISOLATION_VIOLATION |
| `test_SL_004_missing_tool_permission_blocked` | delete with read:* returns TOOL_NOT_GRANTED |
| `test_SL_005_nested_traversal_blocked` | nested `../../` returns PERMISSION_ESCALATION_DENIED |
| `test_SL_negative_same_tenant_not_blocked` | own tenant (tenant_test/) not blocked |

---

## 5. Files Changed

| File | Change |
|------|--------|
| `modules/infrastructure/wre_core/tests/redteam/conftest.py` | MODIFIED (+~60 lines) |
| `modules/infrastructure/wre_core/tests/redteam/test_scope_lock_violation.py` | MODIFIED (+~130 lines: 5 new tests + 2 expected_reason upgrades) |
| `modules/infrastructure/wre_core/tests/redteam/TestModLog.md` | MODIFIED |
| `docs/audits/security/FOUNDUPS_AGENT_REDTEAM_HARNESS_REASON_EXTENSION_PHASE1.md` | NEW (this file) |

---

## 6. Preserved Contracts

| Contract | Status |
|----------|--------|
| Family A W7 SL-001..SL-006 | PRESERVED (8 pass; SL-002/SL-004 reason upgraded) |
| Family B credential exfil tests | PRESERVED (14 pass) |
| Family C HoloIndex poisoning tests | PRESERVED (3 pass) |
| `[SAFETY-EVENT]` emission on all refusals | PRESERVED |
| Three-part assertion shape | PRESERVED |
| Vault resolver tests | PRESERVED (47/47) |
| No skipped tests | VERIFIED (0 skipped) |

---

## 7. WSP 97 Verdict

| Check | Result |
|-------|--------|
| Path normalization blocks `..`? | YES |
| PERMISSION_ESCALATION_DENIED wired? | YES |
| TENANT_ISOLATION_VIOLATION wired? | YES |
| TOOL_NOT_GRANTED wired? | YES |
| SCOPE_VIOLATION still works? | YES |
| Family B tests preserved? | YES (14 pass) |
| Family C tests preserved? | YES (3 pass) |
| `[SAFETY-EVENT]` emission preserved? | YES |
| Zero skipped tests? | YES (0 skipped) |
| No production code changed? | YES |
| No CI gate activated? | YES |

**WSP 97 VERDICT**: **PASS**

---

## 8. W10 Readiness

| Gate | Status |
|------|--------|
| Path normalization implemented | YES |
| Fine-grained reason codes wired | YES |
| Regression tests for traversal bypass | YES |
| All 30 redteam tests pass | YES |
| All 47 vault resolver tests pass | YES |
| 0 skipped tests | YES |
| Audit doc complete | YES |
| TestModLog updated | YES |
| **Ready for commit** | **YES** |

---

## 9. Next Slice

| Slice ID | What it adds |
|----------|--------------|
| `FOUNDUPS_AGENT_REDTEAM_FAMILY_C_HOLOINDEX_POISONING_PHASE1` | HP-002..HP-006 |
| `FOUNDUPS_AGENT_REDTEAM_CI_OBSERVATION_PHASE1` | CI integration (report-only) |

---

**Implementation Complete**: 2026-05-22
**WSP Lock**: WSP_00, WSP_15, WSP_50, WSP_6, WSP_71, WSP_87, WSP_97, WSP_104, WSP_22
