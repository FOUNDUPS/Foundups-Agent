# DEP_SECURITY_REMEDIATION_CLASSIFICATION_PHASE1

**Slice**: `DEP_SECURITY_REMEDIATION_CLASSIFICATION_PHASE1`
**Worker**: W9
**Date**: 2026-05-14
**Mode**: Audit / Classification only
**WSP Lock**: WSP_00, WSP_97, WSP_87, WSP_12, WSP_50

---

## WSP 97 Labels

| Label | Status |
|-------|--------|
| `DOCS_ONLY` | Applied |
| `CLASSIFICATION_ONLY` | Applied |
| `NO_DEPENDENCY_CHANGES` | ENFORCED |
| `NO_RUNTIME_CHANGE` | ENFORCED |
| `NO_BROAD_UPGRADE` | ENFORCED |
| `PINNED_VERSION_REQUIRED` | Applicable |
| `MODULE_LEVEL_FIRST` | Applicable |
| `ROOT_AGGREGATION_SECOND` | Applicable |
| `NO_CABR_READY` | Applied |
| `NO_PAYOUT_READY` | Applied |
| `NO_DAO_ACTIVATION` | Applied |

---

## 1. Retrieval Summary

### HoloIndex Preflight Assessment

**Query 1**: `dependency security vulnerability CVE update remediation WSP 12`
- **Useful**: Partial - found WSP 12, wsp_compliance_checker, wsp_85_validator
- **Noisy**: Some irrelevant knowledge docs returned (patent series, papers)
- **Missing**: Did not return dependency_security_preflight.py directly
- **Ordering**: WSP results correctly prioritized

**Query 2**: `DEP_SECURITY_PREFLIGHT_AUDIT_20260517 dependency remediation`
- **Useful**: YES - found dependency_security_preflight.py directly
- **Noisy**: Low - mostly relevant results
- **Missing**: None critical
- **Ordering**: Correct - code results first

**Query 3**: `requirements pinned versions WSP 12 dependency management`
- **Useful**: YES - found WSP_12_Dependency_Management.md
- **Noisy**: Moderate - some unrelated INTERFACE.md files
- **Missing**: None
- **Ordering**: WSP 12 correctly in top 5

**Fallback Required**: Manual grep for module-level requirements files was necessary to complete dependency mapping.

### Files Retrieved

| File | Purpose | Retrieved Via |
|------|---------|---------------|
| `docs/audits/security/DEP_SECURITY_PREFLIGHT_AUDIT_20260517.md` | Source audit | Direct read |
| `WSP_framework/src/WSP_12_Dependency_Management.md` | Dependency protocol | HoloIndex |
| `modules/infrastructure/wre_core/src/dependency_security_preflight.py` | Scanner implementation | HoloIndex |
| `requirements.txt` (root) | Root dependencies | Direct read |
| Module-level requirements files (98+) | Module dependencies | Glob + grep |

---

## 2. Audit Source Summary

**Source**: pip-audit scan of `.venv` environment
**Scan Date**: 2026-05-14 (live scan during this classification)
**Tool**: `pip-audit -f json --progress-spinner off`

### Aggregate Counts

| Severity | Count |
|----------|-------|
| **Critical** | 4 |
| **High** | 7 |
| **Medium** | 0 |
| **Low** | 0 |
| **Unknown** | 3 |
| **Total** | 14 vulnerabilities in 8 packages |

**Note**: The original preflight audit (PR #607) reported `critical=4 high=7 unknown=14`. The current scan shows 14 total vulnerabilities, suggesting some findings may have been resolved or reclassified since the original scan.

---

## 3. Vulnerability Classification Table

### Critical Severity (4 CVEs)

| ID | Package | Current | CVE | Fix Version | Classification | Affected Modules | Upgrade Type | Risk |
|----|---------|---------|-----|-------------|----------------|------------------|--------------|------|
| V001 | litellm | 1.83.0 | CVE-2026-42203 | 1.83.7 | Transitive / Dev-Tool | cisco-ai-skill-scanner (transitive) | Patch | LOW - Scanner tool dependency |
| V002 | litellm | 1.83.0 | CVE-2026-42208 | 1.83.7 | Transitive / Dev-Tool | cisco-ai-skill-scanner (transitive) | Patch | LOW - Scanner tool dependency |
| V003 | litellm | 1.83.0 | CVE-2026-42271 | 1.83.7 | Transitive / Dev-Tool | cisco-ai-skill-scanner (transitive) | Patch | LOW - Scanner tool dependency |
| V004 | litellm | 1.83.0 | CVE-2026-40217 | 1.83.10 | Transitive / Dev-Tool | cisco-ai-skill-scanner (transitive) | Patch | LOW - Scanner tool dependency |

**litellm Assessment**:
- **Pulled by**: cisco-ai-skill-scanner 2.0.9 (dev tool, not runtime)
- **Impact**: SQL injection, RCE via template injection, RCE via MCP test endpoints
- **Runtime Exposure**: NONE - this is a development/scanning tool, not used in production
- **Action**: Update cisco-ai-skill-scanner or pin litellm>=1.83.10

### High Severity (7 CVEs)

| ID | Package | Current | CVE | Fix Version | Classification | Affected Modules | Upgrade Type | Risk |
|----|---------|---------|-----|-------------|----------------|------------------|--------------|------|
| V005 | authlib | 1.6.9 | CVE-2026-41425 | 1.6.11 | Transitive | fastmcp (transitive) | Patch | MEDIUM - OAuth CSRF on cache |
| V006 | pip | 26.0.1 | CVE-2026-3219 | None | Tool / Risk-Accepted | System tool | N/A | LOW - Zip/tar confusion |
| V007 | pip | 26.0.1 | CVE-2026-6357 | 26.1 | Tool / Risk-Accepted | System tool | Minor | LOW - Self-update timing |
| V008 | python-dotenv | 1.2.1 | CVE-2026-28684 | 1.2.2 | Direct + Module | Root + 11 modules | Patch | MEDIUM - Symlink overwrite |
| V009 | python-multipart | 0.0.22 | CVE-2026-40347 | 0.0.26 | Transitive + Module | fastapi, gotjunk/backend | Patch | MEDIUM - DoS on multipart |
| V010 | python-multipart | 0.0.22 | CVE-2026-42561 | 0.0.27 | Transitive + Module | fastapi, gotjunk/backend | Patch | MEDIUM - DoS on headers |
| V011 | urllib3 | 2.6.3 | CVE-2026-44431 | 2.7.0 | Transitive | requests (transitive) | Minor | LOW - Redirect header leak |

### Unknown/Other Severity (3 CVEs)

| ID | Package | Current | CVE | Fix Version | Classification | Affected Modules | Upgrade Type | Risk |
|----|---------|---------|-----|-------------|----------------|------------------|--------------|------|
| V012 | diskcache | 5.6.3 | CVE-2025-69872 | None | Transitive | llama-cpp-python (transitive) | N/A | **HIGH** - Pickle RCE |
| V013 | transformers | 4.57.6 | CVE-2026-1839 | 5.0.0rc3 | Direct | rESP_o1o2, pqn_mcp | Major | MEDIUM - torch.load RCE |
| V014 | urllib3 | 2.6.3 | CVE-2026-44432 | 2.7.0 | Transitive | requests (transitive) | Minor | LOW - Decompression DoS |

---

## 4. WSP_12 Compliance Plan

### Current State Analysis

Per WSP 12 Section 2:
1. Module-level `requirements.txt` MUST declare dependencies with pinned `==` versions
2. Root `requirements.txt` serves as aggregation of all module-level files

**Current Violations Observed**:
- Root `requirements.txt` uses `>=` ranges, not `==` pins
- Module-level files use mix of `>=` ranges and `==` pins
- Some modules pin (e.g., `gotjunk/backend`: `python-multipart==0.0.6`)
- Most modules use ranges (e.g., `python-dotenv>=1.0.0`)

### Required Actions for WSP 12 Compliance

1. **Module-level updates FIRST**:
   - Update module requirements files to pinned versions
   - Test module in isolation before updating root

2. **Root aggregation SECOND**:
   - After all module-level updates verified
   - Root requirements.txt updated to match aggregate pins

3. **Preserve `==` constraint**:
   - Do NOT convert pins to open ranges during update
   - New pins must use exact version specifier

---

## 5. Remediation PR Grouping Plan

### Group 1: Dev Tools (Low Priority)
**Scope**: litellm via cisco-ai-skill-scanner
**Packages**: litellm (4 CVEs)
**PR Title**: `fix(deps): update cisco-ai-skill-scanner litellm to 1.83.10`
**Risk**: LOW - development tool only
**Test Coverage**: Unit tests for skill scanner functionality

### Group 2: python-dotenv (High Priority)
**Scope**: Direct dependency in root + 11 modules
**Packages**: python-dotenv 1.2.1 -> 1.2.2
**PR Title**: `fix(deps): update python-dotenv to 1.2.2 (CVE-2026-28684)`
**Risk**: MEDIUM - widely used but patch-level
**Affected Modules**:
- Root requirements.txt
- modules/platform_integration/linkedin_agent
- modules/development/module_creator
- modules/platform_integration/youtube_auth
- modules/platform_integration/stream_resolver
- modules/platform_integration/social_media_orchestrator
- modules/platform_integration/utilities/oauth_management
- modules/ai_intelligence/rESP_o1o2
- modules/communication/youtube_shorts
- modules/communication/livechat
- modules/communication/liberty_alert
- modules/foundups

### Group 3: python-multipart (High Priority)
**Scope**: Direct pin in gotjunk + transitive via fastapi
**Packages**: python-multipart 0.0.22 -> 0.0.27
**PR Title**: `fix(deps): update python-multipart to 0.0.27 (CVE-2026-40347, CVE-2026-42561)`
**Risk**: MEDIUM - DoS vectors in file upload handling
**Affected Modules**:
- modules/foundups/gotjunk/backend (direct pin: ==0.0.6 -> ==0.0.27)
**Note**: Root and other modules get this transitively via fastapi

### Group 4: urllib3 (Medium Priority)
**Scope**: Transitive dependency via requests
**Packages**: urllib3 2.6.3 -> 2.7.0
**PR Title**: `fix(deps): update urllib3 to 2.7.0 (CVE-2026-44431, CVE-2026-44432)`
**Risk**: LOW - redirect and decompression edge cases
**Action**: No direct requirements changes needed; update via venv refresh

### Group 5: authlib (Medium Priority)
**Scope**: Transitive dependency via fastmcp
**Packages**: authlib 1.6.9 -> 1.6.11
**PR Title**: `fix(deps): update authlib to 1.6.11 (CVE-2026-41425)`
**Risk**: MEDIUM - OAuth CSRF when using cache feature
**Action**: Update fastmcp or add authlib>=1.6.11 constraint

### Group 6: transformers (Low Priority - Major Version)
**Scope**: Direct dependency in 2 modules
**Packages**: transformers 4.57.6 -> 5.0.0rc3+
**PR Title**: `fix(deps): update transformers for CVE-2026-1839`
**Risk**: **HIGH** - MAJOR version bump, breaking changes likely
**Affected Modules**:
- modules/ai_intelligence/rESP_o1o2
- modules/ai_intelligence/pqn_mcp
**Recommendation**: Defer until v5.0.0 stable release; document risk acceptance

### Group 7: diskcache (HIGH RISK - No Fix Available)
**Scope**: Transitive via llama-cpp-python
**Packages**: diskcache 5.6.3 (no fix)
**Risk**: **CRITICAL** - Pickle deserialization RCE
**Action**: RISK ACCEPTANCE REQUIRED
- No fix available from upstream
- Mitigate by ensuring cache directory is not writable by attackers
- Document accepted risk with expiration date

### Group 8: pip (Tool - Risk Accepted)
**Scope**: System tool, not application dependency
**Packages**: pip 26.0.1 -> 26.1 (partial fix)
**Risk**: LOW - affects pip self-update behavior
**Action**: RISK ACCEPTED - pip is system tooling, not runtime

---

## 6. Required Test Matrix

| Group | Package | Test Scope | Test Type |
|-------|---------|------------|-----------|
| G1 | litellm | cisco-ai-skill-scanner functionality | Unit |
| G2 | python-dotenv | All modules using env loading | Integration |
| G3 | python-multipart | gotjunk file upload endpoints | Integration |
| G4 | urllib3 | requests-based HTTP clients | Unit |
| G5 | authlib | fastmcp OAuth flows | Integration |
| G6 | transformers | rESP_o1o2, pqn_mcp model loading | Integration |
| G7 | diskcache | N/A (no fix) | N/A |
| G8 | pip | N/A (system tool) | N/A |

### CI/CD Integration Tests Required

```yaml
test_matrix:
  - name: python-dotenv-smoke
    command: pytest modules/*/tests/ -k "dotenv or env" --tb=short
    
  - name: multipart-upload
    command: pytest modules/foundups/gotjunk/backend/tests/ -k "upload" --tb=short
    
  - name: transformers-model-load
    command: pytest modules/ai_intelligence/rESP_o1o2/tests/ -k "model" --tb=short
```

---

## 7. Risks / Blockers

### Critical Blockers

| Risk | Package | Description | Mitigation |
|------|---------|-------------|------------|
| NO_FIX | diskcache | CVE-2025-69872 has no upstream fix | Risk acceptance + cache directory hardening |
| MAJOR_BUMP | transformers | v5.0.0 is release candidate only | Wait for stable release |

### Medium Risks

| Risk | Package | Description | Mitigation |
|------|---------|-------------|------------|
| TRANSITIVE_DEPTH | authlib, urllib3 | Changes via parent packages | Pin constraints in root |
| PIN_CONVERSION | Multiple | Some modules use `>=` not `==` | Phase migration per WSP 12 |

### Low Risks

| Risk | Package | Description | Mitigation |
|------|---------|-------------|------------|
| DEV_ONLY | litellm | 4 CVEs but dev tool only | Update with normal priority |
| SYSTEM_TOOL | pip | Not application dependency | Document risk acceptance |

---

## 8. WSP_97 Truth Boundary

| Claim | Status | Evidence |
|-------|--------|----------|
| No dependencies updated in this PR | ENFORCED | Classification only |
| No runtime mutation | ENFORCED | Documentation only |
| No broad upgrade performed | ENFORCED | Analysis only |
| Pinned versions documented | VERIFIED | See classification table |
| Module-level first strategy | DOCUMENTED | See Group plan |
| Root aggregation second | DOCUMENTED | See Group plan |
| No CABR readiness claimed | ENFORCED | Labels applied |
| No payout readiness claimed | ENFORCED | Labels applied |
| No DAO activation claimed | ENFORCED | Labels applied |

---

## 9. WSP_15 Next-Slice Recommendation

### Immediate Priority Slices

1. **`DEP_SECURITY_REMEDIATION_PYTHON_DOTENV_PHASE1`**
   - Scope: python-dotenv 1.2.1 -> 1.2.2
   - Why: Direct dependency, patch-level, wide usage
   - Estimated effort: 1-2 hours
   - Risk: LOW

2. **`DEP_SECURITY_REMEDIATION_PYTHON_MULTIPART_PHASE1`**
   - Scope: python-multipart -> 0.0.27
   - Why: Direct pin in gotjunk, DoS vectors
   - Estimated effort: 1 hour
   - Risk: LOW

3. **`DEP_SECURITY_REMEDIATION_TRANSITIVE_PINS_PHASE1`**
   - Scope: urllib3, authlib via root constraint pins
   - Why: Close transitive gaps without touching modules
   - Estimated effort: 1 hour
   - Risk: LOW

### Deferred Slices

4. **`DEP_SECURITY_RISK_ACCEPTANCE_DISKCACHE_PHASE1`**
   - Scope: Document risk acceptance for diskcache (no fix available)
   - Why: No upstream fix; requires security review
   - Estimated effort: 30 minutes
   - Risk: DOCUMENTATION ONLY

5. **`DEP_SECURITY_REMEDIATION_TRANSFORMERS_PHASE1`**
   - Scope: transformers 4.x -> 5.x
   - Why: Major version bump requires compatibility audit
   - Trigger: After transformers v5.0.0 stable release
   - Risk: HIGH - defer

6. **`DEP_SECURITY_REQUIREMENTS_AGGREGATION_SYNC_PHASE1`**
   - Scope: Verify root requirements matches module pins
   - Why: WSP 12 compliance verification
   - Dependencies: After all module updates complete
   - Risk: LOW

### Recommended Order

```
1. DEP_SECURITY_REMEDIATION_PYTHON_DOTENV_PHASE1      [IMMEDIATE]
2. DEP_SECURITY_REMEDIATION_PYTHON_MULTIPART_PHASE1   [IMMEDIATE]
3. DEP_SECURITY_REMEDIATION_TRANSITIVE_PINS_PHASE1    [IMMEDIATE]
4. DEP_SECURITY_RISK_ACCEPTANCE_DISKCACHE_PHASE1      [IMMEDIATE]
5. DEP_SECURITY_REMEDIATION_DEV_TOOLS_PHASE1          [NORMAL]
6. DEP_SECURITY_REQUIREMENTS_AGGREGATION_SYNC_PHASE1  [POST-UPDATES]
7. DEP_SECURITY_REMEDIATION_TRANSFORMERS_PHASE1       [DEFERRED]
```

---

## Classification Summary

**Total Vulnerabilities**: 14 in 8 packages
**Direct Dependencies Affected**: 3 (python-dotenv, python-multipart, transformers)
**Transitive Dependencies Affected**: 5 (litellm, authlib, diskcache, urllib3, pip)
**No Fix Available**: 2 (diskcache, pip CVE-2026-3219)
**Major Version Required**: 1 (transformers)
**Patch/Minor Available**: 11

**Recommended Priority Order**:
1. python-dotenv (patch, wide impact)
2. python-multipart (patch, DoS vector)
3. Transitive pins (urllib3, authlib)
4. Risk acceptance (diskcache)
5. Dev tools (litellm)
6. Root aggregation sync
7. Major version (transformers) - DEFERRED

---

*Classification completed by Worker W9 under WSP_00, WSP_97, WSP_87, WSP_12, WSP_50.*
*No dependencies were modified. This is audit/classification only.*
