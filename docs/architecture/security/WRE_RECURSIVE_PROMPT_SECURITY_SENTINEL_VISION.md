# WRE Recursive Prompt Security Sentinel - Vision Architecture

**Date**: 2026-05-09
**Worker**: W4
**Phase**: VISION_PHASE1
**Status**: ARCHITECTURE ONLY - NO CODE

---

## Executive Summary

The WRE Recursive Prompt Security Sentinel (RPSS) is an execution-time security layer that protects 0102 agents from indirect prompt injection, unauthorized tool calls, and recursive execution attacks. It operates as a pre-execution gate within the WRE (Windsurf Recursive Engine) architecture.

**Key Principle**: Every tool call and external content ingestion passes through the sentinel before execution.

---

## 1. Threat Model

### 1.1 Indirect Prompt Injection

External content sources that may contain adversarial instructions:
- Web pages fetched via `WebFetch`
- GitHub issues/PRs via `gh` commands
- File contents from untrusted paths
- API responses from external services
- Chat messages from external platforms (Discord, YouTube, Slack)
- User-uploaded documents

### 1.2 Tool Call Exploitation

Adversarial patterns attempting to:
- Escalate permissions via crafted tool arguments
- Exfiltrate data via tool call chaining
- Modify `.env`, credentials, or security-critical files
- Execute shell commands with injected payloads
- Bypass sandbox restrictions

### 1.3 Recursive Execution Attacks

Patterns that exploit recursive agent behavior:
- Infinite loops via self-referential instructions
- Resource exhaustion through nested agent spawning
- Authority escalation through recursive delegation
- State corruption through contradictory instructions

---

## 2. Architecture Layers

### 2.1 Layer 0: Content Ingestion Gate

```
External Content --> [INGESTION_GATE] --> Sanitized Content --> WRE
                          |
                          v
                   [THREAT_HOTLIST]
                          |
                          v
                   [QUARANTINE_LOG]
```

**Components**:
- **Content Classifier**: Distinguishes trusted vs untrusted sources
- **Pattern Scanner**: Regex/ML detection of injection patterns
- **Threat Hotlist**: Known malicious patterns from HoloIndex memory
- **Quarantine Log**: Isolated storage for suspicious content

### 2.2 Layer 1: Tool Call Authorization

```
Tool Call Request --> [AUTH_GATE] --> [POLICY_CHECK] --> Execution
                          |                  |
                          v                  v
                   [SIGNATURE_VERIFY]  [CAPABILITY_LIMIT]
                          |                  |
                          v                  v
                   [0102_AUTHORITY]    [AUDIT_LOG]
```

**Components**:
- **Auth Gate**: Verifies caller identity (0102 vs external agent)
- **Signature Verify**: Validates prompt chain of custody
- **Policy Check**: Allowlist/denylist per tool type
- **Capability Limit**: Enforces per-session resource bounds
- **0102 Authority**: Final approval for sensitive operations

### 2.3 Layer 2: Recursive Execution Sentinel

```
WRE Skill Invocation --> [RECURSION_GUARD] --> [DEPTH_LIMIT] --> Execute
                                |                    |
                                v                    v
                         [CYCLE_DETECT]       [STATE_SNAPSHOT]
                                |                    |
                                v                    v
                         [HALT_TRIGGER]       [ROLLBACK_POINT]
```

**Components**:
- **Recursion Guard**: Tracks call stack depth
- **Cycle Detect**: Identifies circular invocation patterns
- **Depth Limit**: Hard cap on recursive invocations (default: 5)
- **State Snapshot**: Checkpoint before each recursive call
- **Rollback Point**: Recovery mechanism on failure

---

## 3. Integration Points

### 3.1 WRE Core Integration

```
Location: modules/infrastructure/wre_core/src/

Existing SEC Stack:
  SEC1: Scanner execution
  SEC2: Policy routing
  SEC3: WRE skill wrapper
  SEC4: Trigger detection
  SEC5: Pattern memory storage
  SEC6: Historical recall
  SEC7-SEC9: Control hooks

Sentinel Addition:
  SEC10: RPSS Ingestion Gate (NEW)
  SEC11: RPSS Auth Gate (NEW)
  SEC12: RPSS Recursion Guard (NEW)
```

### 3.2 HoloIndex Memory Integration

```
Threat Hotlist Storage:
  holo_index/.ssd/security/threat_hotlist.json

Pattern Memory:
  modules/infrastructure/wre_core/src/security_pattern_memory.py (existing)

Recall Interface:
  modules/infrastructure/wre_core/src/security_recall.py (existing)
```

### 3.3 Agent Permission Integration

```
Permission Checks:
  modules/ai_intelligence/agent_permissions/src/agent_permission_manager.py

Authority Verification:
  - 0102 identity confirmation
  - Confidence threshold enforcement
  - Allowlist/forbidlist validation
```

### 3.4 MCP Governance Integration

```
WSP 96 Compliance:
  - Bell State verification before tool calls
  - Consensus requirement for sensitive operations
  - Gateway Sentinel registration
```

---

## 4. Security Policies

### 4.1 Content Trust Levels

| Trust Level | Source | Treatment |
|-------------|--------|-----------|
| TRUSTED | Local repo files, WSP protocols | Pass through |
| VERIFIED | Signed 012 artifacts | Signature check |
| UNTRUSTED | Web fetches, external APIs | Full sanitization |
| HOSTILE | Known injection sources | Block + quarantine |

### 4.2 Tool Call Policies

| Tool Category | Policy | Override |
|---------------|--------|----------|
| Read-only (Read, Grep, Glob) | ALLOW | None required |
| Write (Edit, Write) | ALLOW with allowlist | 0102 authority |
| Execute (Bash, PowerShell) | SANITIZE + ALLOW | 0102 authority |
| External (WebFetch, WebSearch) | UNTRUSTED content | Content gate |
| Agent (Agent, subagent) | RECURSION_GUARD | Depth limit |

### 4.3 Recursion Limits

| Context | Max Depth | Timeout |
|---------|-----------|---------|
| Agent spawning | 3 | 5 min per level |
| Skill invocation | 5 | 2 min per call |
| Tool chaining | 10 | 30s cumulative |

---

## 5. Threat Hotlist Schema

```json
{
  "hotlist_version": "1.0.0",
  "last_updated": "2026-05-09T12:00:00Z",
  "patterns": [
    {
      "id": "INJ-001",
      "type": "indirect_injection",
      "pattern": "ignore previous instructions",
      "severity": "CRITICAL",
      "action": "BLOCK",
      "source": "known_attack_pattern"
    },
    {
      "id": "ESC-001",
      "type": "permission_escalation",
      "pattern": "execute.*--no-sandbox",
      "severity": "HIGH",
      "action": "QUARANTINE",
      "source": "security_research"
    }
  ],
  "sources": [
    {
      "name": "HoloIndex Security Memory",
      "type": "internal",
      "update_frequency": "continuous"
    },
    {
      "name": "012 Security Alerts",
      "type": "manual",
      "update_frequency": "on_incident"
    }
  ]
}
```

---

## 6. WSP Compliance

| WSP | Requirement | Implementation |
|-----|-------------|----------------|
| WSP 97 | Truthful state reporting | Audit log with action/outcome distinction |
| WSP 77 | Agent coordination | Authority verification for multi-agent ops |
| WSP 96 | MCP governance | Bell State check before tool calls |
| WSP 50 | Pre-action verification | Policy check before execution |
| WSP 60 | Memory architecture | HoloIndex threat hotlist storage |

---

## 7. Proposed Module Structure

```
modules/infrastructure/wre_core/src/
  security_sentinel/
    __init__.py
    ingestion_gate.py      # Layer 0: Content sanitization
    auth_gate.py           # Layer 1: Tool authorization
    recursion_guard.py     # Layer 2: Recursive execution safety
    threat_hotlist.py      # Hotlist management
    policy_engine.py       # Policy evaluation
    audit_logger.py        # Security event logging
```

---

## 8. Interface Boundaries

### 8.1 External Boundary (DO NOT TOUCH)

- Claude Code harness internals
- MCP server transport layer
- External API authentication

### 8.2 Internal Boundary (Sentinel Scope)

- WRE skill execution pre-hook
- HoloIndex query post-processing
- Tool call argument validation

### 8.3 Integration Boundary (Requires Coordination)

- `security_control_hooks.py` (SEC9)
- `agent_permission_manager.py`
- `wre_master_orchestrator.py`

---

## 9. Open Questions

1. **Hotlist Update Frequency**: How often should threat patterns sync from external sources?
2. **ML Detection**: Should pattern detection use Gemma for classification?
3. **Performance Budget**: What latency is acceptable for pre-execution checks?
4. **012 Escalation**: When should the sentinel require explicit 012 approval?
5. **Rollback Scope**: How much state should be preserved for rollback?

---

## 10. Non-Goals (Phase 1)

- Runtime code patching
- Automatic vulnerability remediation
- External threat intelligence feeds
- Cross-FoundUp threat sharing
- Real-time ML model updates

---

## 11. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| Architecture designed | TRUE | This document |
| Code implemented | FALSE | Vision only |
| Integration tested | FALSE | No code exists |
| Threat hotlist populated | FALSE | Schema defined only |
| Production deployed | FALSE | Architecture phase |

---

## 12. Next Steps

1. **Phase 2**: Detailed interface contracts per layer
2. **Phase 3**: Prototype ingestion gate with known injection patterns
3. **Phase 4**: Integration with existing SEC stack
4. **Phase 5**: HoloIndex threat memory population
5. **Phase 6**: Production hardening with Gemma classification

---

**Verdict**: `VISION_COMPLETE` - Architecture defined. Ready for Phase 2 interface contracts.
