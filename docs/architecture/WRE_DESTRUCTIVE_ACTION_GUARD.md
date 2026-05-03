# WRE Destructive Action Guard

**Slice**: WRE_DESTRUCTIVE_ACTION_GUARD_DESIGN_PHASE1  
**Status**: Design Document (No Runtime Changes)  
**WSP References**: WSP 97 (Truth Boundaries), WSP 15 (Priority Matrix), WSP 11 (Interface)

---

## 1. Overview

This document defines guardrails for destructive actions in the WRE (Windsurf Recursive Engine) agent execution layer. Destructive actions are operations that:

- Delete, overwrite, or corrupt data
- Modify production state irreversibly
- Affect external systems (APIs, databases, infrastructure)
- Impact security boundaries (credentials, permissions)

**Core Principle**: Deny-by-default. Agents cannot perform destructive actions unless explicitly authorized through capability tokens and multi-gate approval.

---

## 2. Destructive Action Taxonomy

### 2.1 Action Classes

| Class | Severity | Description | Examples |
|-------|----------|-------------|----------|
| D0_OBSERVE | None | Read-only operations | File read, API GET, log inspection |
| D1_LOCAL_TEMP | Low | Local temporary changes | Create temp files, local branch |
| D2_LOCAL_PERSIST | Medium | Local persistent changes | Edit tracked files, commit locally |
| D3_REMOTE_SOFT | High | Remote reversible changes | Push branch, create PR, post comment |
| D4_REMOTE_HARD | Critical | Remote difficult-to-reverse | Merge PR, delete branch, close issue |
| D5_PRODUCTION | Catastrophic | Production state modification | Deploy, database write, API mutation |
| D6_IRREVERSIBLE | Terminal | Cannot be undone | Drop table, delete backup, revoke keys |

### 2.2 Scope Detection

| Scope | Detection Signals | Risk Multiplier |
|-------|-------------------|-----------------|
| `development` | Branch name contains `dev/`, `feat/`, `test/` | 1x |
| `staging` | Branch name contains `staging/`, env=staging | 2x |
| `production` | Branch = `main`/`master`, env=production | 10x |
| `backup` | Path contains `backup/`, `archive/`, `.bak` | 20x |
| `credentials` | Path contains `.env`, `secrets/`, `credentials/` | 50x |

---

## 3. WSP 97 Gate Mapping

### 3.1 Gate Definitions

```
Gate 1: IDENTITY_VERIFIED
  - tenant_id validated
  - job_id traced to origin
  - actor identity confirmed

Gate 2: POLICY_FLAGS_SET
  - security_gate_passed = True
  - permission_gate_checked = True
  - All WSP 97 truth fields = False (no false claims)

Gate 3: DESTRUCTIVE_ACTION_APPROVED
  - Explicit approval for action class
  - Capability token valid
  - Scope matches token scope

Gate 4: DELAY_SATISFIED
  - delay_until timestamp passed (for D5+)
  - Cancellation window honored
  - No pending vetoes

Gate 5: TWO_PARTY_APPROVAL (D6 only)
  - First approver confirmed
  - Second approver confirmed (different principal)
  - Approval window not expired
```

### 3.2 Class-to-Gate Requirements

| Class | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 |
|-------|--------|--------|--------|--------|--------|
| D0_OBSERVE | Required | Required | - | - | - |
| D1_LOCAL_TEMP | Required | Required | - | - | - |
| D2_LOCAL_PERSIST | Required | Required | Required | - | - |
| D3_REMOTE_SOFT | Required | Required | Required | - | - |
| D4_REMOTE_HARD | Required | Required | Required | Required | - |
| D5_PRODUCTION | Required | Required | Required | Required | - |
| D6_IRREVERSIBLE | Required | Required | Required | Required | Required |

---

## 4. Deny-by-Default Policy

### 4.1 Default State

All FoundUpJob envelopes start with:

```python
destructive_action_requested: bool = False
destructive_action_class: Optional[str] = None  # D0-D6
destructive_action_approved: bool = False
destructive_action_delay_until: Optional[datetime] = None
production_scope_detected: bool = False
backup_scope_detected: bool = False
real_execution_performed: bool = False  # WSP 97
```

### 4.2 Escalation Required

Any action classified D2 or higher requires explicit escalation:

1. Agent detects action class from requested operation
2. Agent sets `destructive_action_requested = True`
3. Agent sets `destructive_action_class = "D{N}"`
4. Job BLOCKS until approval flow completes
5. Approval sets `destructive_action_approved = True`
6. Agent may proceed (if all gates pass)

### 4.3 Scope Detection Logic

```python
def detect_scope(job: FoundUpJob) -> ScopeFlags:
    flags = ScopeFlags()
    
    # Production detection
    if job.target_branch in ("main", "master"):
        flags.production_scope_detected = True
    if os.environ.get("ENV") == "production":
        flags.production_scope_detected = True
    
    # Backup detection
    for path in job.affected_paths:
        if any(p in path for p in ("backup/", "archive/", ".bak")):
            flags.backup_scope_detected = True
    
    return flags
```

---

## 5. Capability Token Rules

### 5.1 Token Structure

```json
{
  "token_id": "cap_abc123",
  "issued_to": "tenant_id",
  "issued_at": "2026-05-03T12:00:00Z",
  "expires_at": "2026-05-03T13:00:00Z",
  "max_class": "D3",
  "allowed_scopes": ["development", "staging"],
  "denied_scopes": ["production", "backup"],
  "single_use": true,
  "job_id_binding": "j_specific_job_123"
}
```

### 5.2 Token Validation

```
MUST:
- Token not expired
- Token max_class >= requested action class
- Token allowed_scopes includes detected scope
- Token denied_scopes excludes detected scope
- Token job_id_binding matches (if set)
- Token not already consumed (if single_use)

MUST NOT:
- Accept tokens from untrusted sources
- Allow token scope escalation
- Cache tokens beyond TTL
```

### 5.3 Token Issuance Authority

| Action Class | Issuance Authority |
|--------------|-------------------|
| D0-D1 | Implicit (no token required) |
| D2-D3 | Agent self-issue with audit log |
| D4 | 012 approval or pre-authorized workflow |
| D5 | 012 explicit approval per-action |
| D6 | 012 + second approver (two-party) |

---

## 6. Production Credential Isolation

### 6.1 Environment Separation

```
DEVELOPMENT:
  - Uses mock/stub credentials
  - Cannot access production secrets
  - API endpoints point to dev/staging
  - Database is isolated copy

STAGING:
  - Uses staging credentials
  - Cannot access production secrets
  - May access staging external APIs
  - Database is staging copy

PRODUCTION:
  - Credentials stored in secure vault
  - Accessed only via capability token
  - All access logged to immutable audit
  - Requires D5+ approval
```

### 6.2 Credential Access Flow

```
1. Agent requests credential access
2. Request includes capability token
3. Vault validates token scope
4. Vault validates action class
5. Vault returns credential (or denies)
6. Credential has short TTL (5 min max)
7. Access logged to immutable audit
```

### 6.3 Prohibited Actions

Agents MUST NOT:
- Store production credentials in memory beyond immediate use
- Log credential values (log credential IDs only)
- Pass credentials to external services not in allowlist
- Embed credentials in code, commits, or evidence files

---

## 7. Backup Immutability and Offsite Requirements

### 7.1 Backup Classification

| Backup Type | Retention | Immutability | Offsite |
|-------------|-----------|--------------|---------|
| Hourly snapshots | 24 hours | Mutable | Local only |
| Daily backups | 30 days | Immutable after 24h | Required |
| Weekly archives | 1 year | Immutable | Required + verified |
| Critical state | Indefinite | Immutable | Required + encrypted |

### 7.2 Immutability Rules

```
IMMUTABLE BACKUPS:
- Cannot be modified after grace period
- Cannot be deleted by single actor
- Deletion requires D6 approval (two-party)
- Deletion has mandatory delay (72 hours)

OFFSITE REQUIREMENTS:
- Different cloud provider OR region
- Encryption at rest with separate key
- Access requires separate credential chain
- Verified via integrity check (SHA-256)
```

### 7.3 Agent Backup Interaction

Agents CAN:
- Trigger backup creation (D2)
- Read backup metadata (D0)
- Initiate restore to non-production (D3)

Agents CANNOT:
- Modify backup contents
- Delete backups (D6, two-party only)
- Access backup encryption keys
- Restore to production without D5 approval

---

## 8. Two-Party Approval for Irreversible Actions

### 8.1 Two-Party Requirement

Class D6 actions require approval from two distinct principals:

```
Principal Types:
- 012 (human operator)
- Authorized delegate (pre-approved human)
- Governance quorum (multi-sig equivalent)

NOT Valid Second Party:
- Same person as first approver
- Same agent session
- Automated approval without human
```

### 8.2 Approval Flow

```
1. Agent requests D6 action
2. First approver reviews and approves
3. System records first approval with timestamp
4. Second approver notified
5. Second approver reviews independently
6. Second approver approves (or vetoes)
7. If both approve: action proceeds after delay
8. If veto: action cancelled, logged
```

### 8.3 Approval Window

```
First approval valid for: 24 hours
Second approval must occur within: 12 hours of first
Combined approval valid for: 6 hours
Action must complete within: validity window

Expired approvals require restart of flow.
```

---

## 9. Delayed Delete Queue

### 9.1 Queue Behavior

All delete operations D4+ enter a delayed delete queue:

```python
@dataclass
class DeleteQueueEntry:
    entry_id: str
    job_id: str
    action_class: str  # D4, D5, D6
    target: str  # Resource identifier
    requested_at: datetime
    delay_until: datetime
    approver_1: Optional[str]
    approver_2: Optional[str]  # D6 only
    status: str  # PENDING, APPROVED, VETOED, EXECUTED, EXPIRED
    veto_reason: Optional[str]
```

### 9.2 Delay Periods

| Action Class | Minimum Delay | Cancellation Window |
|--------------|---------------|---------------------|
| D4 | 1 hour | Full delay period |
| D5 | 24 hours | Full delay period |
| D6 | 72 hours | Full delay period |

### 9.3 Queue Operations

```
ENQUEUE:
- Record delete request with target and class
- Calculate delay_until timestamp
- Notify approvers (if required)
- Set status = PENDING

VETO (during cancellation window):
- Set status = VETOED
- Record veto_reason
- Notify requester
- No execution occurs

EXECUTE (after delay_until):
- Verify status = APPROVED
- Verify no pending veto
- Execute delete operation
- Set status = EXECUTED
- Record evidence

EXPIRE (if not approved in time):
- Set status = EXPIRED
- No execution occurs
- Requires new request to retry
```

---

## 10. WRE Envelope Fields

### 10.1 FoundUpJob Extensions

Add to FoundUpJob contract:

```python
# Destructive Action Guard Fields
destructive_action_requested: bool = False
destructive_action_class: Optional[str] = None  # D0-D6
destructive_action_approved: bool = False
destructive_action_delay_until: Optional[datetime] = None
destructive_action_approver_1: Optional[str] = None
destructive_action_approver_2: Optional[str] = None  # D6 only

# Scope Detection Fields
production_scope_detected: bool = False
backup_scope_detected: bool = False
credentials_scope_detected: bool = False

# WSP 97 Truth Fields (existing)
real_execution_performed: bool = False
verification_complete: bool = False
cabr_ready: bool = False
payout_ready: bool = False
```

### 10.2 HermesDelegationResult Extensions

Add to HermesDelegationResult:

```python
# Destructive Action Result Fields
destructive_action_attempted: bool = False
destructive_action_blocked: bool = False
destructive_action_block_reason: Optional[str] = None
```

### 10.3 Validation Rules

```python
def validate_destructive_action(job: FoundUpJob) -> ValidationResult:
    if not job.destructive_action_requested:
        return ValidationResult.PASS
    
    if job.destructive_action_class is None:
        return ValidationResult.FAIL("Class required when requested")
    
    if job.destructive_action_class not in ("D0", "D1", "D2", "D3", "D4", "D5", "D6"):
        return ValidationResult.FAIL("Invalid class")
    
    class_num = int(job.destructive_action_class[1])
    
    if class_num >= 2 and not job.destructive_action_approved:
        return ValidationResult.FAIL("D2+ requires approval")
    
    if class_num >= 4 and job.destructive_action_delay_until:
        if datetime.now(UTC) < job.destructive_action_delay_until:
            return ValidationResult.FAIL("Delay not satisfied")
    
    if class_num == 6:
        if not job.destructive_action_approver_2:
            return ValidationResult.FAIL("D6 requires two-party approval")
    
    if job.production_scope_detected and class_num < 5:
        return ValidationResult.FAIL("Production scope requires D5+")
    
    return ValidationResult.PASS
```

---

## 11. WSP 15 Priority Matrix

### 11.1 Destructive Action Priority

| Priority | Description | SLA | Escalation |
|----------|-------------|-----|------------|
| P0 | D6 action detected (irreversible) | Immediate block | 012 alert |
| P1 | D5 action in production scope | Block, notify | 012 within 1h |
| P2 | D4 action affecting shared state | Queue, delay | Standard approval |
| P3 | D3 action (remote soft) | Log, proceed | Post-hoc audit |
| P4 | D2 or below | Log only | None |

### 11.2 Incident Response

```
D6 BLOCKED:
1. Immediate halt of agent execution
2. Alert to 012 via all channels
3. Preserve full execution state
4. Wait for explicit resume or cancel

D5 BLOCKED:
1. Queue action in delayed delete
2. Notify 012 of pending action
3. Continue non-destructive work
4. Execute after delay if approved

D4 BLOCKED:
1. Queue action with standard delay
2. Log to audit trail
3. Continue other work
4. Execute after delay
```

---

## 12. Next Implementation Slice

### 12.1 Phase 2: Runtime Integration

**Slice**: WRE_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE2

Scope:
- Add destructive action fields to FoundUpJob
- Add validation in foundup_job_router.py
- Add block logic in hermes_job_executor.py
- Add tests for all action classes
- Update envelope validation tests

Files:
- modules/communication/moltbot_bridge/src/foundup_job_contract.py
- modules/infrastructure/wre_core/src/foundup_job_router.py
- modules/infrastructure/wre_core/src/hermes_job_executor.py
- modules/infrastructure/wre_core/tests/test_destructive_action_guard.py

### 12.2 Phase 3: Approval Flow

**Slice**: WRE_DESTRUCTIVE_ACTION_APPROVAL_PHASE3

Scope:
- Capability token issuance
- Approval queue implementation
- Two-party approval for D6
- Delayed delete queue
- 012 notification integration

### 12.3 Phase 4: Production Hardening

**Slice**: WRE_DESTRUCTIVE_ACTION_PRODUCTION_PHASE4

Scope:
- Production credential vault integration
- Backup immutability enforcement
- Offsite backup verification
- Audit trail immutability
- Security review and penetration testing

---

## 13. WSP 97 Compliance Statement

This design maintains WSP 97 truth boundaries:

```
real_execution_performed = False
  Design phase only. No runtime changes.

verification_complete = False
  No CABR scoring of destructive actions.

cabr_ready = False
  No V3 engine integration.

payout_ready = False
  No blockchain or token implications.
```

All destructive action guardrails are defensive infrastructure.
They prevent false claims, not enable new capabilities.

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| D0-D6 | Destructive action classification scale |
| Capability Token | Short-lived authorization for specific action |
| Two-Party | Requirement for two independent approvers |
| Delayed Delete | Queue with mandatory wait before execution |
| Production Scope | Actions affecting live/main systems |
| Backup Scope | Actions affecting backup or archive data |
| Immutable | Cannot be modified after creation |
| Offsite | Stored in separate infrastructure/region |

---

## Appendix B: Related Documents

- [WSP 97: Truth Boundaries](../../WSP_framework/src/WSP_97_Truthful_Agent_Contract.md)
- [WSP 15: Priority Matrix](../../WSP_framework/src/WSP_15_Priority_Matrix.md)
- [WSP 11: Interface Protocol](../../WSP_framework/src/WSP_11_Interface_Protocol.md)
- [FoundUpJob Contract](../../modules/communication/moltbot_bridge/src/foundup_job_contract.py)
- [Hermes Job Executor](../../modules/infrastructure/wre_core/src/hermes_job_executor.py)

---

*Design Document - No Runtime Changes*  
*WSP 97: real_execution_performed = False*
