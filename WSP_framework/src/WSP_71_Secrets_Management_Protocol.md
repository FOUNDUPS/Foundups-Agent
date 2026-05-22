# WSP 71: Secrets Management Protocol
- **Status:** Active
- **Purpose:** To define the canonical method for storing, retrieving, and managing secrets across the WSP/WRE autonomous development ecosystem while ensuring security, auditability, and integration with agent permission systems.
- **Trigger:** When agents require access to sensitive information (API keys, tokens, credentials), when secrets need to be stored or rotated, or when security audits require secrets management validation.
- **Input:** Secret storage requests, secret retrieval requests, security configuration requirements, and audit queries.
- **Output:** Secure secret storage confirmation, retrieved secret values (to authorized agents only), security audit reports, and secret lifecycle management.
- **Responsible Agent(s):** ComplianceAgent (security validation), agents with SECRETS_READ permission, 012 Rider (policy definition)

## 1. Overview

This protocol establishes the **Canonical Secrets Management Architecture** for the WSP/WRE ecosystem, ensuring that sensitive information is never stored insecurely, is only accessible to authorized agents, and maintains comprehensive audit trails for security compliance.

## 2. Core Security Principles

### 2.1 Fundamental Rules

**Rule 1: No Secrets in Git Repository**
- Secrets MUST NEVER be stored in the Git repository in any form
- This includes configuration files, environment files, documentation, or any other repository artifacts
- All repository scanning MUST validate the absence of secrets per WSP 4 security scanning

**Rule 2: Centralized Secrets Management**
- The WRE MUST integrate with a dedicated secrets management system
- All secrets MUST be stored in the centralized system, never in local files or databases
- Supported systems: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, or encrypted local vault

**Rule 3: Permission-Based Access Control**
- Only agents with explicit SECRETS_READ permission (WSP 54) may request secrets
- Secret access MUST be validated against agent permissions before retrieval
- All secret access attempts MUST be logged and audited

**Rule 4: Skill Supply-Chain Safety Gate**
- Any executable skill set (`SKILL.md` and related assets) MUST pass automated security scanning before staged or production use.
- Runtime systems that execute mutating skill actions MUST enforce preflight scanning with fail-closed defaults.
- Scanner outcomes (status, severity, decision) MUST be logged as auditable security events.
- If scanner tooling is unavailable in required mode, execution MUST be blocked and treated as a security incident candidate.

### 2.2 Security Architecture

**Three-Layer Security Model:**
1. **Authentication Layer**: Agent identity verification and permission validation
2. **Authorization Layer**: Secret-specific access control and role-based permissions  
3. **Audit Layer**: Comprehensive logging and monitoring of all secret operations

## 3. Secrets Management Implementation

### 3.1 Secret Storage Standards

**Secret Categories:**
- **API Keys**: External service authentication tokens
- **Database Credentials**: Connection strings and authentication
- **Encryption Keys**: Data encryption and signing keys
- **Service Tokens**: Inter-service authentication tokens
- **Infrastructure Secrets**: Cloud provider credentials and configurations

**Storage Requirements:**
- All secrets MUST be encrypted at rest using industry-standard encryption (AES-256)
- Secrets MUST be encrypted in transit using TLS 1.3 or equivalent
- Secret values MUST never be logged, cached, or persisted outside the secrets manager
- Secrets MUST have defined lifecycle policies including rotation schedules

### 3.2 Secret Retrieval Interface

**Standardized Secret Access API:**
```python
class SecretsManager:
    def get_secret(self, secret_name: str, agent_id: str) -> SecretValue:
        """
        Retrieve secret with permission validation
        
        Args:
            secret_name: Identifier for the secret
            agent_id: Requesting agent identifier
            
        Returns:
            SecretValue: Encrypted secret value for authorized agents
            
        Raises:
            PermissionDeniedError: Agent lacks SECRETS_READ permission
            SecretNotFoundError: Secret does not exist
            AuditLogError: Audit logging failed
        """
        
    def store_secret(self, secret_name: str, secret_value: str, metadata: dict) -> bool:
        """Store secret with metadata and audit trail"""
        
    def rotate_secret(self, secret_name: str) -> bool:
        """Rotate secret and update dependent systems"""
        
    def audit_secret_access(self, timeframe: str) -> AuditReport:
        """Generate audit report for secret access patterns"""
```

### 3.3 Agent Integration Requirements

**Permission Validation Process:**
1. **Agent Authentication**: Verify agent identity and active status
2. **Permission Check**: Validate SECRETS_READ permission via WSP 54 permission matrix
3. **Secret Authorization**: Check agent-specific access rights for requested secret
4. **Audit Logging**: Log access attempt with full context
5. **Secure Delivery**: Return secret via encrypted channel with immediate cleanup

**Mandatory Security Practices for Agents:**
- **Just-In-Time Access**: Request secrets only when needed, release immediately after use
- **No Persistence**: Never store, cache, or log secret values
- **Secure Handling**: Use secrets in memory only, clear after use
- **Error Handling**: Ensure secrets are cleared even on error conditions
- **Rotation Support**: Implement automatic handling of secret rotation

### 3.4 Skill Safety Preflight Interface

Runtime skill execution must expose a preflight gate that can be enforced by policy:

```python
class SkillSafetyGate:
    def scan_skills(self, skills_path: str, max_severity: str = "medium") -> dict:
        """
        Scan skill artifacts before execution or promotion.

        Returns:
            {
              "available": bool,
              "passed": bool,
              "highest_severity": "none|low|medium|high|critical",
              "message": str
            }
        """
```

**Required behavior:**
- `required_mode=true`: block if scanner unavailable.
- `enforced_mode=true`: block when `highest_severity` exceeds threshold.
- Cache windows are allowed for runtime efficiency but MUST expire predictably.

## 4. Secrets Management Systems Integration

### 4.1 HashiCorp Vault Integration

**Configuration:**
```yaml
secrets_manager:
  type: "hashicorp_vault"
  address: "${VAULT_ADDR}"
  auth_method: "approle"
  mount_path: "foundups-secrets"
  
vault_config:
  approle:
    role_id: "${VAULT_ROLE_ID}"
    secret_id: "${VAULT_SECRET_ID}"
  policies:
    - "foundups-read-policy"
    - "foundups-write-policy"
```

**Vault Integration Features:**
- **Dynamic Secrets**: Automatically generated database credentials with TTL
- **Secret Versioning**: Maintain history of secret changes with rollback capability
- **Lease Management**: Automatic secret renewal and revocation
- **Policy Enforcement**: Fine-grained access control via Vault policies

### 4.2 AWS Secrets Manager Integration

**Configuration:**
```yaml
secrets_manager:
  type: "aws_secrets_manager"
  region: "${AWS_REGION}"
  kms_key_id: "${AWS_KMS_KEY_ID}"
  
aws_config:
  authentication: "iam_role"
  role_arn: "${AWS_SECRETS_ROLE_ARN}"
  policies:
    - "FoundupsSecretsReadPolicy"
    - "FoundupsSecretsWritePolicy"
```

**AWS Integration Features:**
- **Automatic Rotation**: Built-in rotation for RDS, DocumentDB, and custom secrets
- **Cross-Region Replication**: Multi-region secret availability
- **VPC Endpoint Support**: Private network access without internet routing
- **CloudTrail Integration**: Complete audit trail in AWS CloudTrail

### 4.3 Local Encrypted Vault (Development)

**Configuration:**
```yaml
secrets_manager:
  type: "local_encrypted_vault"
  vault_path: "/secure/foundups-vault"
  encryption_key: "${MASTER_ENCRYPTION_KEY}"
  
local_vault_config:
  encryption_algorithm: "AES-256-GCM"
  key_derivation: "PBKDF2"
  backup_enabled: true
  backup_path: "/secure/vault-backups"
```

**Security Requirements:**
- Master encryption key MUST be stored separately from vault file
- Vault file MUST have restricted filesystem permissions (600)
- Regular encrypted backups MUST be maintained
- Development-only: NEVER use in production environments

## 5. Security Monitoring and Compliance

### 5.1 Audit Requirements

**Mandatory Audit Logging:**
- All secret access attempts (successful and failed)
- Secret creation, modification, and deletion events
- Permission changes and security configuration updates
- System integration events and error conditions

**Audit Log Format:**
```json
{
  "timestamp": "2025-01-XX:XX:XX.XXXZ",
  "event_type": "secret_access",
  "agent_id": "scoring_agent_v1.2.3",
  "secret_name": "youtube_api_key",
  "action": "retrieve",
  "result": "success",
  "permission_validation": "passed",
  "source_ip": "10.0.1.50",
  "session_id": "sess_abc123def456"
}
```

### 5.2 Security Monitoring

**Real-Time Alerts:**
- **Permission Violations**: Immediate alert when agents attempt unauthorized access
- **Unusual Access Patterns**: Alert on abnormal secret access frequency or timing
- **Failed Authentication**: Alert on repeated authentication failures
- **Configuration Changes**: Alert on secrets management configuration modifications

**Security Metrics:**
- Secret access frequency and patterns per agent
- Permission violation rates and trends  
- Secret rotation compliance and overdue rotations
- System availability and error rates
- Skill scan pass/fail rates, severity distribution, and fail-closed blocks
- Promotion blocks due to skill scan failures

### 5.3 Compliance Validation

**Regular Security Audits:**
- **Quarterly Access Reviews**: Validate agent permissions against actual requirements
- **Annual Security Assessment**: Comprehensive review of secrets management architecture
- **Penetration Testing**: Regular testing of secrets security controls
- **Compliance Reporting**: Generate reports for regulatory and security compliance

## 6. Integration with WSP Framework

### 6.1 WSP 54 Agent Permission Integration

**Permission Matrix Integration:**
- SECRETS_READ permission defined in WSP 54 Section 2.3.4
- Agent permission validation enforced at secrets retrieval
- Permission violations reported to ComplianceAgent
- Regular permission audits coordinated with WSP 54 compliance

### 6.2 WSP 4 FMAS Security Integration

**Secret Scanning Integration:**
- FMAS security scans validate absence of secrets in repository
- Secret detection triggers high-severity audit failures
- Integration with bandit and custom secret detection tools
- Automated remediation guidance for detected secrets

### 6.3 WSP 50 Pre-Action Verification Integration

**Enhanced Verification:**
- Secret access requests subject to WSP 50 verification protocols
- Agent identity and permission validation before secret retrieval
- Integration with existing pre-action verification framework
- Comprehensive verification logging and audit trails

### 6.4 WSP 95 and WSP 96 Skill/MCP Governance Integration

**Cross-Protocol Enforcement:**
- WSP 95 promotion gates MUST include supply-chain scan evidence before `prototype -> staged` and `staged -> production`.
- WSP 96 MCP/agent activation workflows MUST reject unsafe skill bundles based on severity policy.
- Violations route to WSP 47 tracking with remediation records in module `violations.md`.

## 7. Implementation Roadmap

### 7.1 Phase 1: Core Infrastructure (P0 - Critical)
- Implement standardized secrets management interface
- Integrate with primary secrets management system (HashiCorp Vault recommended)
- Implement basic permission validation and audit logging
- Update WSP 54 agents with SECRETS_READ permission requirements

### 7.2 Phase 2: Security Enhancement (P1 - High)
- Implement comprehensive audit logging and monitoring
- Add real-time security alerting and violation detection
- Implement secret rotation automation and lifecycle management
- Enhanced integration with WSP 4 FMAS security scanning
- Enforce skill supply-chain scanner gate for promotion and runtime execution

### 7.3 Phase 3: Advanced Features (P2 - Medium)
- Multi-secrets-manager support with failover capabilities
- Advanced secret versioning and rollback functionality
- Integration with external security monitoring systems
- Automated compliance reporting and dashboard

## 8. Security Best Practices

### 8.1 Development Guidelines

**For Agent Developers:**
- Always use the standardized SecretsManager interface
- Never hardcode secrets in source code or configuration files
- Implement proper error handling that clears secrets from memory
- Test secret rotation handling in all agent implementations
- Follow just-in-time access patterns for secret retrieval

**For System Administrators:**
- Regularly rotate secrets according to defined policies
- Monitor secret access patterns for anomalies
- Maintain up-to-date documentation of secret dependencies
- Test disaster recovery procedures for secrets management systems
- Keep secrets management systems updated with latest security patches

### 8.2 Incident Response

**Secret Compromise Response:**
1. **Immediate Containment**: Revoke compromised secret and disable access
2. **Impact Assessment**: Identify all systems and agents using the compromised secret
3. **Secret Rotation**: Generate new secret and update all dependent systems
4. **System Validation**: Verify all systems operational with new secret
5. **Incident Documentation**: Complete post-incident analysis and lessons learned

## 9. Conclusion

WSP 71 establishes the foundation for secure secrets management across the autonomous WSP/WRE development ecosystem. By implementing centralized secrets management, comprehensive audit trails, and integration with agent permission systems, this protocol ensures that sensitive information is protected while enabling efficient autonomous development operations. The protocol transforms ad-hoc secrets handling into a systematic, secure, and auditable process that scales with the autonomous development ecosystem.

---

## Annex A: MCP Runtime Credential Access

**Status**: SPEC_ONLY (pending implementation)
**Source**: `docs/audits/security/AGENT_SECURITY_STACK_EXTERNAL_INTEGRATION_AUDIT_PHASE1.md`
**Pattern Reference**: Vault-backed MCP credential resolution (1Password Environments MCP / Runlayer pattern)

### A.1 Overview

This annex specifies runtime-only credential resolution at the MCP gateway layer. Credentials are resolved just-in-time from a vault backend and never stored in prompts, model context, logs, repository, or terminal output.

### A.2 Vault-Backed Secret References

**Reference Pattern**: `op://vault/item/field`

| Component | Description | Example |
|-----------|-------------|---------|
| `vault` | Vault or namespace identifier | `foundups-secrets` |
| `item` | Secret item name | `youtube-api-key` |
| `field` | Specific field within item | `credential` |

**Storage Rule**: Only the reference string is stored in code, configuration, or prompts. The actual secret value MUST NEVER be stored anywhere except the vault backend.

### A.3 Runtime-Only Resolution

**Resolution Architecture**:
```
Agent Request -> MCP Gateway -> [SCANNER] Detect op:// references -> [RESOLVER] Vault SDK -> [INJECT] Replace reference -> [CLEAR] Memory cleanup
```

**Critical Constraints**:
- Resolution occurs ONLY at runtime, ONLY at MCP gateway
- Resolved values exist in memory ONLY for request duration
- No disk caching, no database storage, no prompt embedding

### A.4 Secrets Forbidden Surfaces

| Surface | Secret Allowed |
|---------|----------------|
| Prompts | NEVER |
| Model context | NEVER |
| Logs | NEVER |
| Terminal output | NEVER |
| Repository (git) | NEVER |
| AgentDB | NEVER |
| HoloIndex | NEVER |

### A.5 Just-In-Time Access

**Session-Bounded Access Rules**:
- Credentials resolved per-request, not cached across requests
- TTL (time-to-live) enforced: maximum credential lifetime per session
- Memory cleared before response returns to agent

### A.6 Audit Logging Without Secret Values

**Hash-Based Audit Trail**:
- Log reference (`op://...`), NEVER the resolved value
- Log SHA-256 hash for rotation detection
- Log requesting agent identity and TTL applied

### A.7 Fail-Closed Behavior

| Failure | Behavior |
|---------|----------|
| Vault unreachable | BLOCK request |
| Reference malformed | BLOCK request |
| TTL expired | BLOCK request |
| Permission denied | BLOCK request |

**Fail-Closed Principle**: If ANY step fails, the entire credential access MUST fail. No fallback to cached/stale credentials.

### A.8 Implementation Gaps

| Gap | Status | Priority |
|-----|--------|----------|
| op:// reference scanner | OPEN | HIGH |
| Vault SDK integration | OPEN | HIGH |
| Hash-based audit trail | OPEN | MEDIUM |
| TTL enforcement | OPEN | MEDIUM |

### A.9 Next Slice

**`SECRETS_MCP_VAULT_RESOLVER_PHASE1`**: Implement op:// resolver with vault backend integration 
