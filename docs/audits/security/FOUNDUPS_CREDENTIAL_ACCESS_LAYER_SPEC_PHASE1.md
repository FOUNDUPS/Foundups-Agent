# FoundUps Credential Access Layer Specification — Phase 1

**Date**: 2026-05-22
**Window**: 0102
**Slice**: FOUNDUPS_CREDENTIAL_ACCESS_LAYER_SPEC_PHASE1
**Base Commit**: `84037f7a2` (origin/main)
**Branch**: `docs/foundups-credential-access-layer-spec`
**Mode**: SPEC/DOCS_ONLY

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| DOCS_ONLY | YES |
| CREDENTIAL_ACCESS_SPEC_ONLY | YES |
| NO_SECRET_ACCESS | YES |
| NO_CREDENTIAL_CREATION | YES |
| NO_1PASSWORD_CONFIGURATION | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_MCP_RUNTIME_CHANGE | YES |
| NO_AGENTDB_MUTATION | YES |
| NO_HOLOINDEX_MUTATION | YES |
| NO_ENV_FILE_CREATION | YES |
| NO_RUNTIME_CHANGE | YES |
| FAIL_CLOSED_REQUIRED | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Source of Truth

### 1.1 Canonical Policy Documents

| Document | Location | Relevance |
|----------|----------|-----------|
| WSP_71 Secrets Management Protocol | `WSP_framework/src/WSP_71_Secrets_Management_Protocol.md` | Core secrets policy, Annex A MCP runtime credential access |
| WSP_71 Annex A | Same file, lines 343-426 | MCP Runtime Credential Access spec |
| Security Audit Phase 1 | `docs/audits/security/AGENT_SECURITY_STACK_EXTERNAL_INTEGRATION_AUDIT_PHASE1.md` | 1Password/RAMPART/Clarity external tool assessment |
| WSP Annex Mapping | `docs/audits/wsp/AGENT_SECURITY_STACK_WSP_ANNEX_MAPPING_PHASE1.md` | Gap analysis, WSP ownership assignment |
| WSP_50 Pre-Action Verification | `WSP_framework/src/WSP_50_Pre_Action_Verification_Protocol.md` | External tool adoption preflight |
| WSP_97 Execution Prompting | `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` | High-risk assumption audit gate |

### 1.2 Key Findings from Phase 1 Audit

Per `AGENT_SECURITY_STACK_EXTERNAL_INTEGRATION_AUDIT_PHASE1.md`:
- 1Password `op://` pattern resolves secrets at runtime without storing plaintext
- Hash-based audit trails enable rotation detection without value exposure
- Secrets must NEVER enter prompts, model context, logs, or terminal output
- Fail-closed behavior required: if vault unavailable, deny access

---

## 2. Current Secret Handling Inventory

### 2.1 Existing Infrastructure

| Component | Path | Function | Security Model |
|-----------|------|----------|----------------|
| **secrets_mcp** | `modules/infrastructure/secrets_mcp/` | MCP server for env var access | Pattern-based filtering |
| **oauth_management** | `modules/platform_integration/utilities/oauth_management/` | OAuth token handling | Token storage in files |
| **.env files** | Various (gitignored) | API keys, configuration | No runtime injection |
| **agent_db** | `modules/infrastructure/database/src/agent_db.py` | Agent state | Should not contain secrets |

### 2.2 secrets_mcp Security Model (Current)

**Pattern-Based Filtering**:
```python
sensitive_patterns = [
    r'password|pwd|secret|key|token|auth',
    r'api.*key|access.*key|secret.*key',
    r'database.*url|db.*url|connection.*string',
    r'private.*key|ssl.*key|certificate',
    r'credential|login|username|user',
    r'salt|hash|encrypt'
]
```

**Allowed Prefixes**:
```python
allowed_prefixes = [
    'PYTHON', 'PATH', 'HOME', 'USER', 'SHELL', 'TERM',
    'FOUNDUPS', 'WSP', 'MCP', 'HOLO', 'GIT',
    'LANG', 'LC_', 'TZ', 'HOSTNAME'
]
```

**Assessment**: Reactive filtering, not preventive vault-backed access.

### 2.3 Current Secret Surfaces

| Surface | Secret Can Enter? | Current Protection | Gap |
|---------|-------------------|-------------------|-----|
| `.env` files | YES | gitignore | No vault backend |
| Environment variables | YES | Pattern filtering | No op:// resolution |
| Prompts | YES (if coded poorly) | Code review only | HIGH RISK |
| Model context | YES | None | HIGH RISK |
| Logs | YES | Pattern filtering | No runtime gate |
| Terminal output | YES | None | HIGH RISK |
| AgentDB | NO (architecture) | Design constraint | OK |
| HoloIndex | NO (architecture) | Design constraint | OK |
| Git repository | NO | .gitignore, scanning | OK |

### 2.4 API Key Reference Patterns Found

| Pattern | Example | Current Handling |
|---------|---------|------------------|
| `.env` direct | `API_KEY=sk-abc123` | gitignored, read by code |
| Environment injection | `os.environ["YOUTUBE_API_KEY"]` | Read at runtime |
| Hardcoded (forbidden) | `key = "sk-abc123"` | Should not exist |
| Vault reference (proposed) | `op://foundups/youtube/key` | NOT IMPLEMENTED |

---

## 3. Credential Access Layer Contract

### 3.1 Secret Reference Format

**Pattern**: `op://vault/item/field`

| Component | Description | Example |
|-----------|-------------|---------|
| `vault` | Vault namespace identifier | `foundups-secrets` |
| `item` | Secret item name | `youtube-api-key` |
| `field` | Specific field within item | `credential` |

**Full Example**: `op://foundups-secrets/youtube-api-key/credential`

**Storage Rule**: Only the reference string (`op://...`) is stored in:
- Configuration files
- Environment variables
- Code comments (as documentation)

The actual secret value MUST NEVER be stored anywhere except the vault backend.

### 3.2 Allowed Resolver Boundary

```
                      RESOLVER BOUNDARY
                            |
                            v
Agent Request --> MCP Gateway --> [Secret Scanner] --> [Vault SDK]
                            |                              |
                            |                              v
                            |                       [Inject Value]
                            |                              |
                            v                              v
                       [Clear Memory] <----- Request Complete
```

**Resolver Location**: MCP Gateway only (S2 surface per WSP 96)
- Secrets resolved ONLY at MCP gateway layer
- Resolved values exist in memory ONLY for request duration
- No disk caching, no database storage, no prompt embedding

### 3.3 Prohibited Secret Exposure

| Action | Allowed? | Enforcement |
|--------|----------|-------------|
| Store secret reference (`op://...`) | YES | By design |
| Store resolved value | NEVER | Fail-closed gate |
| Echo secret to terminal | NEVER | Output filter |
| Log secret value | NEVER | Log sanitizer |
| Include in prompt | NEVER | Scanner before MCP |
| Cache to disk | NEVER | Architecture |
| Write to AgentDB | NEVER | Architecture |
| Index in HoloIndex | NEVER | Architecture |

### 3.4 Runtime-Only Injection

**Just-In-Time Access**:
1. Request arrives at MCP gateway
2. Scanner detects `op://` reference
3. Vault SDK resolves value
4. Value injected into upstream tool call
5. Response returned
6. Value cleared from memory

**Session Boundaries**:
- Each request is isolated
- No credential caching across requests
- TTL enforced per session

### 3.5 TTL and Session Expiration

| TTL Type | Duration | Enforcement |
|----------|----------|-------------|
| Request TTL | Request lifetime only | Memory cleared on response |
| Session TTL | Max 15 minutes | Re-authentication required |
| Rotation TTL | Vault-defined | Hash comparison |

---

## 4. Fail-Closed Rules

### 4.1 Failure Modes

| Failure | Behavior | Error Code |
|---------|----------|------------|
| Vault unreachable | BLOCK request | `VAULT_UNAVAILABLE` |
| Reference malformed | BLOCK request | `INVALID_SECRET_REF` |
| Secret not found | BLOCK request | `SECRET_NOT_FOUND` |
| TTL expired | BLOCK request | `TTL_EXPIRED` |
| Permission denied | BLOCK request | `PERMISSION_DENIED` |
| Unauthorized agent | BLOCK request | `AGENT_UNAUTHORIZED` |
| Missing approval for high-risk | BLOCK request | `APPROVAL_REQUIRED` |
| Attempted plaintext output | BLOCK and log violation | `SECRET_LEAK_BLOCKED` |

### 4.2 Fail-Closed Principle

**IF ANY STEP FAILS, THE ENTIRE CREDENTIAL ACCESS MUST FAIL.**

- No fallback to cached credentials
- No fallback to stale secrets
- No fallback to .env file
- No "degrade gracefully" for security failures

### 4.3 Recovery Path

On failure:
1. Log failure (without secret values)
2. Return error to caller
3. Do NOT retry automatically
4. Require explicit re-request with valid context

---

## 5. Agent Identity and Scope Model

### 5.1 Worker/Session Identity

| Identity Field | Source | Purpose |
|----------------|--------|---------|
| `worker_id` | MCP request context | Track requesting worker |
| `session_id` | MCP gateway | Isolate request context |
| `slice_id` | Request metadata | Audit correlation |
| `surface_id` | S1/S2/S3 tag | Enforce surface boundary |

### 5.2 Allowed Secret Classes

| Secret Class | Example | Allowed Agents |
|--------------|---------|----------------|
| `public_api` | Public API keys | All agents |
| `internal_api` | Internal service keys | Service agents only |
| `infrastructure` | Cloud credentials | Deployment agents only |
| `admin` | Admin tokens | 012 Rider only |

### 5.3 Task-Scoped Access

**Minimum Privilege Rule**:
- Agent requests secret for specific task
- Access granted for task duration only
- Secret cleared when task completes
- No persistent access grants

### 5.4 FoundUp-Scoped Access

When `foundup_id` is present:
- Secret access limited to FoundUp scope
- Cross-FoundUp access denied by default
- Shared secrets require `include_shared=true` flag

---

## 6. Audit Trail Design

### 6.1 Required Audit Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO8601 | Event time |
| `worker_id` | string | Requesting worker |
| `session_id` | string | Request session |
| `tool` | string | MCP tool name |
| `surface` | string | S1/S2/S3 |
| `secret_ref_hash` | string | SHA-256 of reference (not value) |
| `action` | enum | `resolve`, `deny`, `expire` |
| `result` | enum | `allow`, `deny`, `error` |
| `ttl_applied` | int | TTL in seconds |
| `purpose` | string | slice_id or task description |
| `violation_id` | string | If denied, violation reference |

### 6.2 What Is Logged

| Data | Logged? |
|------|---------|
| Secret reference (`op://...`) | YES (hashed) |
| Secret value | NEVER |
| Requesting agent | YES |
| Request timestamp | YES |
| Allow/deny result | YES |
| TTL applied | YES |
| Violation reason | YES |

### 6.3 Audit Log Format

```json
{
  "timestamp": "2026-05-22T12:34:56.789Z",
  "worker_id": "w6_mcp_validation",
  "session_id": "sess_abc123",
  "tool": "holo_search",
  "surface": "S2",
  "secret_ref_hash": "sha256:a1b2c3d4...",
  "action": "resolve",
  "result": "allow",
  "ttl_applied": 300,
  "purpose": "MCP_FOUNDUP_SCOPE_S2_VALIDATION_IMPL_PHASE1",
  "violation_id": null
}
```

---

## 7. Violations Integration

### 7.1 When to Update violations.md

| Event | Update Required? |
|-------|-----------------|
| Attempted secret in prompt | YES |
| Attempted secret in log | YES |
| Unauthorized agent access | YES |
| Vault bypass attempt | YES |
| TTL override attempt | YES |
| Pattern filter bypass | YES |
| Normal access denied | NO (audit log only) |

### 7.2 Violation Record Format

```markdown
## [VIOLATION-CRED-001] Secret Leak Attempt

**Date**: 2026-05-22
**Worker**: w6_test
**Surface**: S2
**Action**: Attempted to include resolved secret in log output
**Result**: BLOCKED
**Remediation**: Worker terminated, log sanitized
**Prevention**: Output filter enforced
```

---

## 8. PoC Slice Plan

### 8.1 Narrowest First Implementation

**PoC Scope**:
1. ONE fake/test credential reference only
2. NO production secret
3. Resolver mocked OR test vault only
4. Proves no secret enters logs/model context

### 8.2 Test Credential Definition

```yaml
# Test vault entry (not production)
vault: foundups-test
item: poc-test-credential
field: value
reference: op://foundups-test/poc-test-credential/value
value: "THIS_IS_A_TEST_VALUE_NOT_A_REAL_SECRET"
```

### 8.3 PoC Acceptance Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| T1 | Reference resolves | Value returned to caller |
| T2 | Value not in logs | Log scan shows no plaintext |
| T3 | Value not in prompt | Prompt scan shows no plaintext |
| T4 | Value not in terminal | Output capture shows no plaintext |
| T5 | Value cleared after request | Memory inspection shows cleared |
| T6 | Invalid reference blocked | Error returned, no search |
| T7 | Vault unavailable blocked | Error returned, no fallback |

### 8.4 Mock Resolver Interface

```python
class MockVaultResolver:
    """Test-only vault resolver for PoC."""

    def resolve(self, reference: str) -> str | None:
        """Resolve op:// reference to value.

        Returns None if not found (fail-closed).
        """
        if reference == "op://foundups-test/poc-test-credential/value":
            return "THIS_IS_A_TEST_VALUE_NOT_A_REAL_SECRET"
        return None
```

---

## 9. Explicit Non-Goals

### 9.1 Out of Scope for Phase 1

| Non-Goal | Rationale |
|----------|-----------|
| Real 1Password setup | PoC first, production later |
| 1Password SDK installation | No dependencies in spec |
| Broad agent access | One test credential only |
| Production credential fetch | Safety first |
| CI secret changes | CI owns its secrets |
| HashiCorp Vault setup | Alternative to 1Password, not Phase 1 |
| Secret rotation implementation | After basic resolve works |
| Cross-FoundUp credential sharing | After single-FoundUp works |

### 9.2 What This Spec Does NOT Authorize

- Installing any vault software
- Creating any vault accounts
- Accessing any production secrets
- Modifying CI/CD pipelines
- Changing existing .env handling
- Implementing TTL enforcement (spec only)

---

## 10. Acceptance Criteria for Future Implementation

### 10.1 Phase 1 PoC Acceptance

| Criterion | Test |
|-----------|------|
| Reference scanner exists | Unit test: detects `op://` pattern |
| Mock resolver works | Unit test: returns test value |
| Fail-closed on invalid | Unit test: returns error, not fallback |
| No secret in logs | Integration test: log scan clean |
| No secret in output | Integration test: output scan clean |
| Audit trail generated | Unit test: audit record created |

### 10.2 Phase 2 Production Acceptance

| Criterion | Test |
|-----------|------|
| 1Password SDK integration | Integration test: real vault resolve |
| TTL enforcement | Integration test: expire after TTL |
| Hash-based audit | Integration test: hash logged, not value |
| Memory cleanup | Security test: value cleared after request |
| Multi-secret support | Integration test: multiple references |
| Rotation detection | Integration test: hash change detected |

---

## 11. HoloIndex Assessment

### 11.1 Queries Executed

| Query | Hits | Quality |
|-------|------|---------|
| `WSP 71 MCP runtime credential access op vault secret audit TTL` | 32 | GOOD — found WSP_71, secrets_mcp |
| `1Password MCP credential access Foundups agent security stack` | 32 | GOOD — found secrets_mcp, pavs_mcp |
| `secrets management env API key MCP agent boundary` | 32 | EXCELLENT — found secrets_mcp.py, WSP_71 |
| `WSP 50 external agent tool adoption preflight credential` | 32 | MEDIUM — found WSP_43, WSP_54 |

### 11.2 Retrieval Quality

- **WSP_71**: Surfaced correctly with Annex A
- **secrets_mcp**: Surfaced correctly (INTERFACE.md, README.md, src)
- **Security audit docs**: NOT surfaced directly (paths known from prior context)
- **WSP annex mapping**: NOT surfaced directly

### 11.3 Improvement Recommendation

Index `docs/audits/security/` and `docs/audits/wsp/` with audit-specific metadata for better retrieval of security specs and mappings.

---

## 12. Current Secret-Handling Gaps Found

| Gap ID | Description | Risk | Mitigation in This Spec |
|--------|-------------|------|------------------------|
| G1 | No `op://` vault reference resolver | HIGH | Section 3 contract |
| G2 | Secrets could leak to prompts | CRITICAL | Section 3.3 prohibitions |
| G3 | No hash-based audit trail | MEDIUM | Section 6 audit design |
| G4 | No TTL/session enforcement | MEDIUM | Section 3.5 TTL spec |
| G5 | Pattern filtering is reactive | LOW | Vault-backed replaces |
| G6 | No agent identity for secrets | MEDIUM | Section 5 identity model |

---

## 13. WSP 97 Verdict

**PASS**: This document is SPEC/DOCS ONLY. No runtime changes, no credential access, no dependency installation.

---

## 14. WSP 15 Next Slice Recommendation

### 14.1 Immediate Next

**`FOUNDUPS_CREDENTIAL_ACCESS_LAYER_POC_PHASE1`**

**Scope**:
- Implement mock vault resolver
- Implement `op://` reference scanner in secrets_mcp
- Add 7 PoC acceptance tests
- Prove no secret leakage in test path

**NOT in scope**:
- Real 1Password integration
- Production credentials
- TTL enforcement
- Rotation detection

### 14.2 Subsequent Slices

1. `FOUNDUPS_1PASSWORD_SDK_INTEGRATION_PHASE1` — Real vault connection
2. `FOUNDUPS_CREDENTIAL_TTL_ENFORCEMENT_PHASE1` — Session TTL
3. `FOUNDUPS_CREDENTIAL_AUDIT_HASH_TRAIL_PHASE1` — Hash-based audit
4. `FOUNDUPS_CREDENTIAL_ROTATION_DETECTION_PHASE1` — Rotation hash comparison

---

## Appendix A: HoloIndex Query Log

```
Query 1: WSP 71 MCP runtime credential access op vault secret audit TTL
  - WSP: WSP_71_Secrets_Management_Protocol.md (FOUND)
  - Code: secrets_mcp.py (FOUND)
  - Docs: secrets_mcp/INTERFACE.md (FOUND)

Query 2: 1Password MCP credential access Foundups agent security stack
  - Code: secrets_mcp.py, pavs_mcp/server.py (FOUND)
  - Docs: secrets_mcp/README.md (FOUND)

Query 3: secrets management env API key MCP agent boundary
  - Code: secrets_mcp.py (FOUND)
  - WSP: WSP_71, WSP_96 (FOUND)

Query 4: WSP 50 external agent tool adoption preflight credential
  - WSP: WSP_43, WSP_36, WSP_54 (PARTIAL)
  - WSP_50 not in top hits (GAP)
```

---

## Appendix B: Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-05-22 | 0102 | Initial spec |
