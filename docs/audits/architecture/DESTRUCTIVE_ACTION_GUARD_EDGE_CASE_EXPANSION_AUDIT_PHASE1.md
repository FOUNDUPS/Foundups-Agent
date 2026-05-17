# Destructive Action Guard Edge Case Expansion Audit Phase 1

**Audit ID**: DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_EXPANSION_AUDIT_PHASE1  
**Worker**: W9  
**Branch**: `worktree-w9-destructive-guard-edge-audit`  
**Base**: `98035cc70` (main after PR #612)  
**Date**: 2026-05-17  
**WSP Lock**: WSP_00, WSP_50, WSP_97, WSP_15  
**Mode**: DOCS_ONLY -- NO IMPLEMENTATION

---

## Safety Labels

- DOCS_ONLY
- AUDIT_ONLY
- NO_RUNTIME_CHANGE
- NO_TEST_MODIFICATION
- NO_GUARD_IMPLEMENTATION
- NO_TOKEN_IMPLEMENTATION
- NO_CABR_READY
- NO_PAYOUT_READY
- NO_DAO_ACTIVATION

---

## 1. Retrieval Summary

### 1.1 Commit/PR Reality Check

| Check | Status | Evidence |
|-------|--------|----------|
| Main branch current | VERIFIED | `98035cc70` (PR #612 merged) |
| HXA22-HXA30 merged | VERIFIED | Test files exist, 230 tests passing |
| Gemini reconciliation merged | VERIFIED | PR #609, file exists |
| Guard files exist | VERIFIED | All 3 files confirmed |

### 1.2 HoloIndex Searches Executed

| Query | Top Results |
|-------|-------------|
| destructive action guard path validation | WRE_DESTRUCTIVE_ACTION_GUARD.md, guards.py |
| HXA22 HXA23 Hermes guard | hermes_job_executor.py, HXA audits |
| HXA28 D3 native classification | dae_cube_assembler.py, HXA2 audit |
| Gemini architectural feedback | guardrail.py, WRE_DESTRUCTIVE_ACTION_GUARD.md |

### 1.3 Documents Examined

| Document | Lines | Purpose |
|----------|-------|---------|
| `destructive_action_guard.py` | 700+ | Phase 1 guard implementation |
| `capability_token_validator.py` | 900+ | Token path validation |
| `hermes_job_executor.py` | 1200+ | Hermes path binding |
| `test_hxa29_token_scope_validation.py` | 1000+ | Path traversal tests |
| `0102_GEMINI_ARCHITECTURAL_FEEDBACK_RECONCILIATION_AUDIT_PHASE1.md` | 116 | Gemini feedback reconciliation |

### 1.4 Test Execution

| Suite | Result |
|-------|--------|
| `test_hxa22_destructive_action_guard_runtime.py` | PASS |
| `test_hxa23_hermes_guard_integration.py` | PASS |
| `test_hxa28_d3_native_classification.py` | PASS |
| `test_hxa30_scope_to_action_class_integration.py` | PASS |
| **Total** | **230 passed** |

---

## 2. Current Guard Behavior

### 2.1 Path Validation in `capability_token_validator.py`

```python
def is_path_allowed(self, target_path: str) -> bool:
    # Normalize path
    normalized = os.path.normpath(target_path).replace("\\", "/")
    
    # Check blocked paths first (override)
    for blocked in self.blocked_paths:
        blocked_clean = os.path.normpath(blocked).replace("\\", "/")
        if normalized.startswith(blocked_clean + "/"):
            return False
    
    # Check allowed paths
    for allowed_root in self.allowed_paths:
        allowed_clean = os.path.normpath(allowed_root).replace("\\", "/")
        if normalized.startswith(allowed_clean + "/"):
            return True
    
    return False  # Fail-closed
```

**Key Observations**:
- Uses `os.path.normpath()` which normalizes `..` but does NOT resolve symlinks
- Uses string `.startswith()` for boundary checking
- Does NOT call `os.path.realpath()` to resolve symlinks
- Backslash normalization: replaces `\\` with `/`

### 2.2 Path Validation in `hermes_job_executor.py`

```python
def is_path_allowed(self, path: str) -> bool:
    normalized = os.path.normpath(path).replace("\\", "/")
    # Uses fnmatch for glob patterns, string startswith for allowed paths
```

**Same pattern**: `os.path.normpath` without symlink resolution.

### 2.3 Guard Evaluation in `destructive_action_guard.py`

The guard checks boolean flags set by caller:
- `path_constraints_validated: bool` - Caller claims path is validated
- `workspace_binding_enforced: bool` - Caller claims workspace binding is enforced

**Critical Finding**: Guard trusts caller to validate paths. If caller's validation is bypassed, guard is bypassed.

### 2.4 Current D0-D6 Coverage

| Class | Name | Phase 1 Status | Test Coverage | Edge Case Gaps |
|-------|------|----------------|---------------|----------------|
| D0 | OBSERVE | ALLOWED | HXA22 tests | None identified |
| D1 | READ | ALLOWED | HXA22 tests | None identified |
| D2 | SIMULATE | ALLOWED | HXA22 tests | Temp file cleanup timing |
| D3 | WRITE_SANDBOX | ALLOWED (path-bound) | HXA22, HXA29 | Symlink traversal (P0) |
| D4 | WRITE_REPO | BLOCKED | HXA22 tests | N/A (blocked) |
| D5 | EXTERNAL_SIDE_EFFECT | BLOCKED | HXA22 tests | N/A (blocked) |
| D6 | IRREVERSIBLE | BLOCKED | HXA22 tests | N/A (blocked) |

### 2.5 Cross-Class Boundary Risks

| Boundary | Risk | Scenario | Mitigation |
|----------|------|----------|------------|
| D2 -> D3 | MEDIUM | Simulation claims to be dry-run but writes to sandbox | Guard checks `live_execution_allowed` flag |
| D3 -> D4 | HIGH | Sandbox write escapes to repo root | Path binding must prevent repo root access |
| D4 -> D5 | LOW | Repo write triggers external webhook | Phase 1 blocks all D4+ |
| D5 -> D6 | LOW | External call has irreversible effect | Phase 1 blocks all D5+ |

**Critical Boundary**: D3 -> D4 is the key risk surface. If path validation fails, a D3 action could modify repo files.

### 2.6 Token Scope Mismatch Scenarios

| Scenario | Token Scope | Requested Action | Expected Result | Current Behavior |
|----------|-------------|------------------|-----------------|------------------|
| Token allows D2, request D3 | `max_action_class=D2_SIMULATE` | D3_WRITE_SANDBOX | BLOCKED | COMPLIANT |
| Token allows D3, request D4 | `max_action_class=D3_WRITE_SANDBOX` | D4_WRITE_REPO | BLOCKED | COMPLIANT |
| Token path mismatch | `allowed_paths=[/tmp/]` | Write to `/var/` | BLOCKED | COMPLIANT |
| Token expired | `expiry < now` | Any action | BLOCKED | COMPLIANT |
| Token revoked | `revoked=True` | Any action | BLOCKED | COMPLIANT |
| **Gap: Symlink escape** | `allowed_paths=[/workspace/]` | Symlink -> `/etc/` | Should be BLOCKED | **ALLOWED (BUG)** |

---

## 3. Edge-Case Risk Matrix

| Edge Case | Current Coverage | Risk | Evidence | Recommended Future Test | Future Fix Direction |
|-----------|------------------|------|----------|-------------------------|----------------------|
| **Symlink traversal** | NONE | HIGH | `os.path.normpath` does not resolve symlinks | `test_symlink_inside_allowed_pointing_outside_blocked` | Add `os.path.realpath()` before boundary check |
| **Directory traversal (`../`)** | PARTIAL | LOW | `os.path.normpath` handles `..` | Existing `TestPathTraversalBlocked` | None (already handled) |
| **Windows UNC paths (`\\server\share`)** | NONE | MEDIUM | No explicit UNC handling | `test_unc_path_blocked_fail_closed` | Detect and block UNC paths explicitly |
| **Mixed separators (`/` + `\`)** | PARTIAL | LOW | Backslash replaced with forward slash | Existing implicit coverage | None (already normalized) |
| **Drive-relative paths (`C:` vs `c:`)** | NONE | MEDIUM | No case normalization on Windows | `test_windows_drive_case_sensitivity` | Use `os.path.normcase()` on Windows |
| **Unicode normalization (NFC/NFD)** | NONE | LOW | No Unicode normalization | `test_unicode_nfc_nfd_bypass` | Add `unicodedata.normalize("NFC", path)` |
| **Control characters in path** | NONE | MEDIUM | No control char filtering | `test_control_char_path_blocked` | Filter ASCII control characters (0x00-0x1F) |
| **URL-encoded paths (`%2e%2e`)** | NONE | LOW | Not applicable (filesystem paths) | N/A | N/A |
| **Env variable expansion (`$HOME`)** | NONE | LOW | No env var expansion | `test_env_var_not_expanded` | Ensure env vars not interpreted |
| **Repo boundary escape via allowed path** | LOW | MEDIUM | Allowed paths may be overly broad | `test_allowed_path_scope_minimization` | Audit default allowed paths |
| **Dry-run/live boundary leakage** | NONE | LOW | `live_execution_allowed=False` hardcoded | Existing HXA22 tests | None (Phase 1 blocks all live) |
| **Action name obfuscation** | NONE | LOW | Enum comparison, not string | `test_action_class_enum_only` | Existing fail-closed on unknown |

### 3.1 Risk Severity Legend

| Risk | Impact | Likelihood | Priority |
|------|--------|------------|----------|
| HIGH | Workspace escape possible | Attacker-controlled symlink | P0 |
| MEDIUM | Non-standard paths bypass checks | Edge environment | P1 |
| LOW | Theoretical bypass, unlikely | Requires specific conditions | P2 |

---

## 4. Empirical Probe Notes

### 4.1 Symlink Traversal Probe (Conceptual)

```python
# CONCEPTUAL PROBE - NOT IMPLEMENTED
# 1. Create allowed directory: modules/foundups/kosei/
# 2. Create symlink inside: modules/foundups/kosei/escape -> /etc/
# 3. Request path: modules/foundups/kosei/escape/passwd

# Current behavior with os.path.normpath:
# - normalized = "modules/foundups/kosei/escape/passwd"
# - allowed_root = "modules/foundups/kosei"
# - normalized.startswith(allowed_root + "/") = True
# - ALLOWED despite escape!

# Expected behavior with os.path.realpath:
# - resolved = "/etc/passwd"
# - Does NOT start with "modules/foundups/kosei"
# - BLOCKED
```

### 4.2 Windows UNC Path Probe (Conceptual)

```python
# CONCEPTUAL PROBE - NOT IMPLEMENTED
# Path: \\\\server\\share\\sensitive\\data.txt
# After normpath: \\server\share\sensitive\data.txt
# After replace("\\", "/"): //server/share/sensitive/data.txt
# Does NOT start with any allowed root
# Result: BLOCKED (fail-closed works here)

# BUT: \\\\?\\C:\\Windows\\System32 (long path prefix)
# Needs explicit handling
```

### 4.3 Drive Letter Case Probe (Conceptual)

```python
# CONCEPTUAL PROBE - NOT IMPLEMENTED
# Allowed: C:/Users/agent/workspace
# Request: c:/Users/agent/workspace/file.txt
# After normpath: c:\Users\agent\workspace\file.txt
# After replace: c:/Users/agent/workspace/file.txt
# Does NOT match C:/Users... (case mismatch)
# Result: BLOCKED (false negative on Windows)

# Fix: os.path.normcase() on Windows normalizes case
```

---

## 5. Required Test Cases For Future Implementation

### 5.1 Symlink Traversal Tests (P0)

| Test ID | Description | Expected Behavior |
|---------|-------------|-------------------|
| SYM-01 | Symlink inside allowed dir pointing outside | BLOCKED |
| SYM-02 | Nested symlinks (symlink -> symlink -> outside) | BLOCKED |
| SYM-03 | Symlink pointing to allowed dir (valid) | ALLOWED |
| SYM-04 | Symlink loop detection | BLOCKED (error handling) |

### 5.2 Windows Path Tests (P1)

| Test ID | Description | Expected Behavior |
|---------|-------------|-------------------|
| WIN-01 | UNC path `\\server\share\file` | BLOCKED |
| WIN-02 | Long path `\\?\C:\...` | BLOCKED |
| WIN-03 | Drive case `C:` vs `c:` | Normalized before check |
| WIN-04 | Relative drive path `C:file.txt` | BLOCKED |
| WIN-05 | Device path `\\.\COM1` | BLOCKED |

### 5.3 Unicode and Control Char Tests (P1)

| Test ID | Description | Expected Behavior |
|---------|-------------|-------------------|
| UNI-01 | NFC vs NFD normalization | Normalized before check |
| UNI-02 | NULL byte in path | BLOCKED |
| UNI-03 | Newline/CR in path | BLOCKED |
| UNI-04 | Non-ASCII allowed in valid paths | ALLOWED |

### 5.4 Environment Variable Tests (P2)

| Test ID | Description | Expected Behavior |
|---------|-------------|-------------------|
| ENV-01 | `$HOME` not expanded | Treated as literal |
| ENV-02 | `%USERPROFILE%` not expanded | Treated as literal |
| ENV-03 | `~` not expanded | Treated as literal |

---

## 6. Recommended Guard Hardening

### 6.1 Symlink Resolution (P0)

```python
# RECOMMENDATION - NOT IMPLEMENTATION
def is_path_allowed(self, target_path: str) -> bool:
    # First normalize to handle ..
    normalized = os.path.normpath(target_path)
    
    # Then resolve symlinks
    try:
        resolved = os.path.realpath(normalized)
    except OSError:
        return False  # Fail-closed on resolution error
    
    # Normalize separators
    resolved = resolved.replace("\\", "/")
    
    # Continue with boundary check...
```

### 6.2 Windows Path Normalization (P1)

```python
# RECOMMENDATION - NOT IMPLEMENTATION
import sys

def normalize_path_for_comparison(path: str) -> str:
    normalized = os.path.normpath(path)
    if sys.platform == "win32":
        normalized = os.path.normcase(normalized)  # Lowercase on Windows
    normalized = normalized.replace("\\", "/")
    return normalized
```

### 6.3 Control Character Filter (P1)

```python
# RECOMMENDATION - NOT IMPLEMENTATION
import re

def is_path_safe(path: str) -> bool:
    # Block control characters (0x00-0x1F except tab)
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', path):
        return False
    return True
```

### 6.4 UNC Path Detection (P1)

```python
# RECOMMENDATION - NOT IMPLEMENTATION
def is_unc_path(path: str) -> bool:
    # Block UNC paths on Windows
    return path.startswith("\\\\") or path.startswith("//")
```

---

## 7. WSP_97 Truth Boundary Verification

### 7.1 Audit Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Does guard canonicalize paths before allow/block? | PARTIAL | `os.path.normpath` used, not `realpath` |
| Does it resolve symlinks before workspace boundary? | NO | Only `normpath`, no `realpath` |
| Are Windows paths, UNC, mixed separators handled? | PARTIAL | Backslash normalized, UNC not blocked |
| Are blocked paths checked after normalization? | YES | `normpath` applied before check |
| Can D3 sandbox escape via symlink? | YES (RISK) | Symlinks not resolved |
| Can action names be obfuscated to avoid D4/D5/D6? | NO | Enum comparison, fail-closed |
| Are dry-run-only and live_execution_allowed=False preserved? | YES | Hardcoded in Phase 1 |
| Are repo_created, production_source_modified impossible? | YES | Always False in result |
| What changes before D0/D1 live sandbox? | Symlink resolution, UNC blocking, Unicode normalization |

### 7.2 Truth Field Verification

| Field | Current Value | Source | Status |
|-------|---------------|--------|--------|
| `live_execution_allowed` | `False` | `destructive_action_guard.py:282` | COMPLIANT |
| `repo_created` | `False` | `destructive_action_guard.py:285` | COMPLIANT |
| `production_source_modified` | `False` | `destructive_action_guard.py:288` | COMPLIANT |
| `verification_complete` | `False` | `destructive_action_guard.py:294` | COMPLIANT |
| `cabr_ready` | `False` | `destructive_action_guard.py:297` | COMPLIANT |
| `payout_ready` | `False` | `destructive_action_guard.py:300` | COMPLIANT |

### 7.3 WSP 97 Verdict

**COMPLIANT WITH GAPS**

The destructive action guard correctly maintains all WSP 97 truth fields as False. However, the path validation layer has edge-case gaps (symlink traversal, UNC paths, control characters) that should be addressed before any Phase 2 live execution discussions.

---

## 8. WSP_15 Next-Slice Recommendation

### 8.1 Candidate Ranking

| Rank | Slice | MPS Score | Rationale |
|------|-------|-----------|-----------|
| 1 | `DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_TEST_IMPL_PHASE1` | 16 | Add test coverage for identified gaps (symlink, UNC, control chars) |
| 2 | `DESTRUCTIVE_ACTION_GUARD_PATH_CANONICALIZATION_IMPL_PHASE1` | 14 | Implement `os.path.realpath()` and UNC blocking |
| 3 | `OPENCLAW_WSP97_METHOD_WRAPPER_AUDIT_PHASE1` | 12 | Separate concern (intelligence layer, not guard) |
| 4 | `HERMES_D0_D1_LIVE_READ_ONLY_SANDBOX_AUDIT_PHASE1` | BLOCKED | Requires guard hardening first |

### 8.2 Recommended Next Slice

**Slice**: `DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_TEST_IMPL_PHASE1`

**Purpose**: Implement test cases for identified edge-case gaps without modifying guard runtime code.

**Scope**:
- Add `TestSymlinkTraversalBlocked` test class
- Add `TestWindowsUNCPathBlocked` test class
- Add `TestControlCharacterPathBlocked` test class
- Add `TestDriveLetterCaseNormalization` test class
- All tests should FAIL (documenting current gaps)
- Tests become regression targets for future fix

**Dependencies**: This audit (gap identification complete)

**Gate**: Requires W10 merge gate

### 8.3 Blocked Slice

**Slice**: `HERMES_D0_D1_LIVE_READ_ONLY_SANDBOX_AUDIT_PHASE1`

**Status**: BLOCKED

**Blocking Condition**: Blocked pending sovereign internal consensus gate specification. Guard hardening (symlink resolution, UNC blocking) must be complete before any D0/D1 live execution audit.

---

## Appendix A: Source Files Examined

| File | Lines | Purpose |
|------|-------|---------|
| `destructive_action_guard.py` | 700+ | Guard implementation |
| `capability_token_validator.py` | 900+ | Token path validation |
| `hermes_job_executor.py` | 1200+ | Hermes path binding |
| `test_hxa22_destructive_action_guard_runtime.py` | 900+ | Guard tests |
| `test_hxa29_token_scope_validation.py` | 1000+ | Token tests (incl. traversal) |

## Appendix B: Test Execution

```bash
python -m pytest modules/infrastructure/wre_core/tests/test_hxa22_destructive_action_guard_runtime.py \
  modules/infrastructure/wre_core/tests/test_hxa23_hermes_guard_integration.py \
  modules/infrastructure/wre_core/tests/test_hxa28_d3_native_classification.py \
  modules/infrastructure/wre_core/tests/test_hxa30_scope_to_action_class_integration.py -q

# Result: 230 passed in 1.09s
```

---

*Audit performed by Worker W9 under WSP 00/50/97/15 truth boundaries.*

Worker-Lane: W9  
Slice: DESTRUCTIVE_ACTION_GUARD_EDGE_CASE_EXPANSION_AUDIT_PHASE1
