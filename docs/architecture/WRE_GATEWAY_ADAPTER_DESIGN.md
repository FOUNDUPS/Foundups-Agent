# WRE Gateway Adapter Design

**Status**: Architecture Design Document  
**WSP Compliance**: WSP 11 (Interface), WSP 15 (Priority), WSP 50 (Pre-Action), WSP 97 (Truth)  
**Date**: 2026-05-03  
**Author**: 0102 Architectural Worker  
**Prerequisite**: [FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md](./FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md)

---

## 1. Purpose

The **WRE Gateway Adapter** is the boundary layer between **FoundUps Core** (this repository) and the external **FoundUps Agent Workspace** (autonomous execution environment).

### 1.1 Design Goals

| Goal | Description |
|------|-------------|
| **Clear boundary** | FoundUps Core owns governance; Workspace owns execution |
| **Typed contracts** | All messages are strongly typed with validation |
| **Truth preservation** | WSP 97 truth fields pass through unchanged |
| **Retention semantics** | Failure modes map to retention reasons |
| **Dry-run first** | Live delegation blocked until all gates pass |

### 1.2 Scope

This document defines:
- API/event contracts between Core and Workspace
- WSP task packet schema (complete specification)
- Security and policy gate requirements
- Failure and retention semantics
- Sequence diagrams for key flows

---

## 2. Non-Goals

This design document explicitly does **NOT**:

| Non-Goal | Rationale |
|----------|-----------|
| Enable live delegation | Blocked by WSP 97 until Phase F |
| Modify runtime code | Docs-only slice |
| Add vendor/submodule | Workspace is external |
| Claim CABR/reward/payout | No token operations |
| Verify external compatibility | Requires direct inspection (future slice) |

---

## 3. Adapter Responsibilities

### 3.1 Core-Side (HermesJobExecutor Adapter)

| Responsibility | Implementation Status |
|----------------|----------------------|
| Build WSP task packets from FoundUpJob | Implemented (PR #481) |
| Validate job identity and policy flags | Implemented |
| Apply workspace binding constraints | Implemented (PR #478) |
| Write checkpoint/evidence artifacts | Implemented (PR #479) |
| Return HermesDelegationResult | Implemented |
| Expose WSP 97 truth fields | Implemented |

### 3.2 Gateway-Side (Future External Adapter)

| Responsibility | Implementation Status |
|----------------|----------------------|
| Accept WSP task packets | NOT implemented (external) |
| Validate packet schema | NOT implemented |
| Translate to workspace scheduler | NOT implemented |
| Emit checkpoint/evidence events | NOT implemented |
| Return completion status | NOT implemented |
| Preserve tenant/job identity | NOT implemented |

### 3.3 Truth Field Preservation

The gateway adapter MUST preserve these fields unchanged:

```
real_execution_performed  -> Pass through (false until real execution)
verification_complete     -> Pass through (false until CABR verification)
cabr_ready               -> Pass through (false until CABR pipeline)
payout_ready             -> Pass through (false until payout engine)
```

---

## 4. Proposed API/Event Contract

### 4.1 Transport Options

| Option | Protocol | Use Case |
|--------|----------|----------|
| HTTP REST | HTTPS + JSON | Request/response patterns |
| WebSocket | WSS + JSON | Real-time event streaming |
| gRPC | HTTP/2 + Protobuf | High-performance (future) |

Recommended: **HTTP REST** for requests, **WebSocket** for events.

### 4.2 Request/Response Contracts

#### 4.2.1 `gateway.health`

Health check endpoint.

**Request:**
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy | degraded | unhealthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "active_jobs": 5,
  "active_agents": 2,
  "capabilities": {
    "dry_run": true,
    "live_execution": false,
    "checkpoint_protocol": true
  }
}
```

#### 4.2.2 `job.accept`

Submit WSP task packet for execution.

**Request:**
```http
POST /api/v1/tasks
Content-Type: application/json

{
  "packet_version": "1.0.0",
  "packet_type": "wsp_task",
  "identity": { ... },
  "task": { ... },
  "policy": { ... },
  "compute": { ... },
  "evidence": { ... },
  "checkpoint": { ... },
  "wsp97_truth": { ... },
  "metadata": { ... }
}
```

**Response (accepted):**
```json
{
  "status": "accepted",
  "job_id": "uuid",
  "workspace_session_id": "uuid",
  "estimated_start_time": "ISO8601 | null",
  "queue_position": 0
}
```

**Response (rejected):**
```json
{
  "status": "rejected",
  "job_id": "uuid",
  "reason_code": "VALIDATION_FAILED | POLICY_BLOCKED | CAPACITY_EXCEEDED",
  "reason_human": "Human-readable explanation",
  "retry_after_seconds": 60
}
```

#### 4.2.3 `job.status`

Query current job status.

**Request:**
```http
GET /api/v1/tasks/{job_id}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued | running | blocked | completed | failed",
  "checkpoint": {
    "state": "SIMULATED | DONE | BLOCKED | NEEDS_INPUT | HANDOFF",
    "result": "string | null",
    "blocker": "string | null",
    "next_action": "string | null"
  },
  "progress": {
    "steps_completed": 5,
    "files_changed": ["path1", "path2"],
    "commands_run": ["cmd1", "cmd2"]
  },
  "evidence_path": ".hermes_evidence/job_id/",
  "wsp97_truth": {
    "real_execution_performed": false,
    "verification_complete": false,
    "cabr_ready": false,
    "payout_ready": false
  }
}
```

#### 4.2.4 `job.cancel`

Request job cancellation.

**Request:**
```http
POST /api/v1/tasks/{job_id}/cancel
Content-Type: application/json

{
  "reason": "User requested | Timeout | Policy change"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "cancellation_requested | cancelled | cannot_cancel",
  "reason": "string"
}
```

### 4.3 Event Contracts (WebSocket)

#### 4.3.1 Event Envelope

All events share this envelope:

```json
{
  "event_type": "string",
  "event_id": "uuid",
  "timestamp": "ISO8601",
  "job_id": "uuid",
  "tenant_id": "string",
  "payload": { ... }
}
```

#### 4.3.2 `job.started`

Agent worker began execution.

```json
{
  "event_type": "job.started",
  "payload": {
    "agent_id": "uuid",
    "workspace_session_id": "uuid",
    "tools_enabled": ["read", "write", "bash"],
    "dry_run_mode": true
  }
}
```

#### 4.3.3 `agent.step`

Agent completed one step.

```json
{
  "event_type": "agent.step",
  "payload": {
    "step_number": 5,
    "tool_called": "bash",
    "tool_input": "git status",
    "tool_output_summary": "3 files modified",
    "duration_ms": 150
  }
}
```

#### 4.3.4 `checkpoint.write`

Checkpoint file written.

```json
{
  "event_type": "checkpoint.write",
  "payload": {
    "checkpoint_path": ".hermes_evidence/job_id/checkpoint.json",
    "checkpoint_state": "SIMULATED",
    "checkpoint_result": "Dry-run validation complete",
    "files_changed": [],
    "commands_run": []
  }
}
```

#### 4.3.5 `evidence.write`

Evidence file written.

```json
{
  "event_type": "evidence.write",
  "payload": {
    "evidence_path": ".hermes_evidence/job_id/metadata.json",
    "evidence_type": "metadata | checkpoint | artifact",
    "size_bytes": 1024
  }
}
```

#### 4.3.6 `job.block`

Execution blocked.

```json
{
  "event_type": "job.block",
  "payload": {
    "blocker": "Human input required for merge conflict",
    "blocker_type": "input_required | permission_denied | external_dependency",
    "suggested_action": "Resolve conflict and resubmit",
    "timeout_seconds": 3600
  }
}
```

#### 4.3.7 `job.complete`

Execution reached terminal state.

```json
{
  "event_type": "job.complete",
  "payload": {
    "final_status": "succeeded | failed | blocked",
    "checkpoint_state": "DONE | BLOCKED | SIMULATED",
    "evidence_path": ".hermes_evidence/job_id/",
    "files_changed": ["src/main.py", "tests/test_main.py"],
    "commands_run": ["pytest -v"],
    "duration_seconds": 45.5,
    "wsp97_truth": {
      "real_execution_performed": false,
      "verification_complete": false,
      "cabr_ready": false,
      "payout_ready": false
    }
  }
}
```

#### 4.3.8 `job.retain`

Core requests job retention (not cleared).

```json
{
  "event_type": "job.retain",
  "payload": {
    "retention_reason": "dry_run_evidence_only | receipt_emission_failed | gateway_rejected",
    "retry_eligible": true,
    "retry_after_seconds": 300
  }
}
```

#### 4.3.9 `job.clear`

Core clears job (successfully processed).

```json
{
  "event_type": "job.clear",
  "payload": {
    "cleared_at": "ISO8601",
    "receipt_id": "uuid | null"
  }
}
```

---

## 5. WSP Task Packet Schema (Complete)

### 5.1 Full Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "WSP Task Packet",
  "version": "1.0.0",
  "type": "object",
  "required": ["packet_version", "packet_type", "identity", "task", "policy", "wsp97_truth"],
  
  "properties": {
    "packet_version": {
      "type": "string",
      "const": "1.0.0"
    },
    "packet_type": {
      "type": "string",
      "const": "wsp_task"
    },
    
    "identity": {
      "type": "object",
      "required": ["job_id", "tenant_id"],
      "properties": {
        "job_id": { "type": "string", "format": "uuid" },
        "foundup_id": { "type": ["string", "null"] },
        "tenant_id": { "type": "string", "minLength": 1 },
        "intent_id": { "type": ["string", "null"] }
      }
    },
    
    "task": {
      "type": "object",
      "required": ["requested_action"],
      "properties": {
        "requested_action": {
          "type": "string",
          "enum": ["build_foundup", "extract_foundup", "validate_foundup", "queue_foundup_job"]
        },
        "goal": { "type": "string" },
        "context": { "type": "string" },
        "module_path": { "type": ["string", "null"] },
        "workspace_path": { "type": ["string", "null"] }
      }
    },
    
    "policy": {
      "type": "object",
      "required": ["dry_run_mode"],
      "properties": {
        "dry_run_mode": { "type": "boolean", "default": true },
        "security_gate_checked": { "type": "boolean", "default": false },
        "security_gate_passed": { "type": "boolean", "default": false },
        "human_approval_received": { "type": "boolean", "default": false },
        "live_mode_authorized": { "type": "boolean", "default": false }
      }
    },
    
    "compute": {
      "type": "object",
      "properties": {
        "compute_budget": { "type": ["integer", "null"], "minimum": 0 },
        "compute_used": { "type": "integer", "minimum": 0, "default": 0 },
        "compute_tier": { 
          "type": "string", 
          "enum": ["freemium", "basic", "enterprise"],
          "default": "freemium"
        },
        "model_preference": {
          "type": "string",
          "enum": ["auto", "free", "standard", "premium"],
          "default": "auto"
        }
      }
    },
    
    "evidence": {
      "type": "object",
      "properties": {
        "evidence_refs": {
          "type": "array",
          "items": { "type": "string" },
          "default": []
        },
        "evidence_output_path": { "type": "string" }
      }
    },
    
    "checkpoint": {
      "type": "object",
      "properties": {
        "checkpoint_state": {
          "type": "string",
          "enum": ["SIMULATED", "DONE", "BLOCKED", "NEEDS_INPUT", "HANDOFF"],
          "default": "SIMULATED"
        },
        "checkpoint_result": { "type": ["string", "null"] },
        "checkpoint_blocker": { "type": ["string", "null"] },
        "checkpoint_next_action": { "type": ["string", "null"] }
      }
    },
    
    "wsp97_truth": {
      "type": "object",
      "required": ["real_execution_performed", "verification_complete", "cabr_ready", "payout_ready"],
      "properties": {
        "real_execution_performed": { "type": "boolean", "default": false },
        "verification_complete": { "type": "boolean", "default": false },
        "cabr_ready": { "type": "boolean", "default": false },
        "payout_ready": { "type": "boolean", "default": false }
      }
    },
    
    "metadata": {
      "type": "object",
      "properties": {
        "created_at": { "type": "string", "format": "date-time" },
        "executor_version": { "type": "string" }
      }
    }
  }
}
```

### 5.2 Field Mapping from FoundUpJob

| WSP Packet Field | FoundUpJob Source | Notes |
|------------------|-------------------|-------|
| `identity.job_id` | `FoundUpJob.job_id` | Required UUID |
| `identity.foundup_id` | `FoundUpJob.foundup_id` | May be null |
| `identity.tenant_id` | `FoundUpJob.tenant_id` | Required |
| `identity.intent_id` | `FoundUpJob.intent_id` | May be null |
| `task.requested_action` | `FoundUpJob.requested_action` | Canonical actions only |
| `task.goal` | Derived from action | See HermesJobExecutor |
| `task.context` | Serialized payload | Truncated if >1000 chars |
| `policy.dry_run_mode` | `PolicyFlags.dry_run_mode` | Default true |
| `policy.security_gate_*` | `PolicyFlags.security_gate_*` | Gate status |
| `compute.*` | `FoundUpJob.compute_*` | Optional budget fields |
| `evidence.evidence_refs` | `FoundUpJob.evidence_refs` | List of paths |
| `checkpoint.*` | `HermesDelegationResult.*` | Checkpoint protocol |
| `wsp97_truth.*` | `HermesDelegationResult.*` | Truth fields |

---

## 6. Security and Policy Gates

### 6.1 Gate Hierarchy

Gates are evaluated in order. If any gate fails, execution stops.

```
1. Permission Gate     -> tenant_id authorized for action?
2. Security Gate       -> WSP 15 audit passed?
3. Human Approval Gate -> human_approval_received?
4. Evidence Policy     -> evidence_refs valid and complete?
5. Compute Budget Gate -> compute_budget >= estimated_cost?
6. Model Routing Gate  -> model_preference allowed for compute_tier?
7. Workspace Path Gate -> allowed_paths permit target paths?
8. Live Mode Gate      -> live_mode_authorized AND !dry_run_mode?
```

### 6.2 Gate Definitions

| Gate | Condition | Failure Retention Reason |
|------|-----------|--------------------------|
| **Permission** | tenant_id in allowed_tenants | `routing_blocked` |
| **Security** | security_gate_passed=true | `routing_blocked` |
| **Human Approval** | human_approval_received=true (for live) | `routing_blocked` |
| **Evidence Policy** | evidence_refs non-empty (for live) | `routing_blocked` |
| **Compute Budget** | compute_budget > 0 (for live) | `routing_blocked` |
| **Model Routing** | model allowed for tier | `routing_blocked` |
| **Workspace Path** | paths in allowed_paths, not in blocked_paths | `routing_blocked` |
| **Live Mode** | live_mode_authorized AND !dry_run_mode | `dry_run_evidence_only` |

### 6.3 Blocked Paths (Security)

These paths are NEVER accessible:

```python
BLOCKED_PATHS = frozenset([
    ".env", ".env.*", "**/.env", "**/.env.*",
    "*.pem", "*.key",
    "**/secrets/", "**/credentials/",
    ".git/config", ".git/credentials",
    "**/__pycache__/",
    "vendor/", ".hermes/",
    "node_modules/", ".venv/", "venv/",
])
```

---

## 7. Failure and Retention Semantics

### 7.1 Retention Reasons

| Reason Code | Description | Retry Eligible |
|-------------|-------------|----------------|
| `routing_failed` | WRE router returned FAILED | Yes |
| `routing_blocked` | Policy gate blocked execution | No (until gate clears) |
| `action_unsupported` | Action not in CANONICAL_ACTIONS | No |
| `dry_run_evidence_only` | Dry-run completed, evidence only | Yes (with live mode) |
| `receipt_emission_failed` | Receipt creation failed | Yes |
| `gateway_unavailable` | Gateway not reachable | Yes |
| `gateway_rejected` | Gateway rejected packet | Depends on reason |
| `evidence_write_failed` | Evidence write failed | Yes |

### 7.2 Retention Decision Matrix

| Route Status | Terminal | Has Receipt | Retention Reason |
|--------------|----------|-------------|------------------|
| ROUTED | SIMULATED | No | `dry_run_evidence_only` |
| ROUTED | DONE | Yes | (cleared) |
| ROUTED | BLOCKED | No | `routing_blocked` |
| BLOCKED | N/A | N/A | `routing_blocked` |
| FAILED | N/A | N/A | `routing_failed` |
| UNSUPPORTED | N/A | N/A | `action_unsupported` |

### 7.3 Gateway-Specific Failures

| Gateway Response | Retention Reason | Action |
|------------------|------------------|--------|
| HTTP 503 | `gateway_unavailable` | Retry with backoff |
| HTTP 400 | `gateway_rejected` | Check packet schema |
| HTTP 403 | `gateway_rejected` | Check permissions |
| HTTP 429 | `gateway_unavailable` | Retry after delay |
| WebSocket disconnect | `gateway_unavailable` | Reconnect |

---

## 8. Sequence Diagram

### 8.1 Dry-Run Flow (Current State)

```
OpenClaw              WRE                 HermesJobExecutor      Evidence
   |                   |                         |                  |
   | create_job()      |                         |                  |
   |------------------>|                         |                  |
   |                   | route_foundup_job()     |                  |
   |                   |------------------------>|                  |
   |                   |                         |                  |
   |                   | <-- RouteEnvelope --    |                  |
   |                   |                         |                  |
   |                   | execute_foundup_job()   |                  |
   |                   |------------------------>|                  |
   |                   |                         |                  |
   |                   |                         | _write_evidence()
   |                   |                         |----------------->|
   |                   |                         |                  |
   |                   |                         | <-- evidence_path
   |                   |                         |                  |
   |                   | <-- HermesDelegation    |                  |
   |                   |     Result              |                  |
   |                   |                         |                  |
   | <-- ConsumerResult|                         |                  |
   |    (checkpoint,   |                         |                  |
   |     evidence_path)|                         |                  |
```

### 8.2 Future Gateway Flow (Phase 2+)

```
OpenClaw    WRE       HermesJobExecutor    Gateway         Workspace
   |         |               |                |                |
   | job     |               |                |                |
   |-------->|               |                |                |
   |         | route()       |                |                |
   |         |-------------->|                |                |
   |         |               |                |                |
   |         |               | POST /tasks    |                |
   |         |               |--------------->|                |
   |         |               |                | accept         |
   |         |               |                |--------------->|
   |         |               |                |                |
   |         |               |                | job.started    |
   |         |               |<---------------|<---------------|
   |         |               |                |                |
   |         |               |                | agent.step     |
   |         |               |<---------------|<---------------|
   |         |               |                |                |
   |         |               |                | checkpoint.write
   |         |               |<---------------|<---------------|
   |         |               |                |                |
   |         |               |                | job.complete   |
   |         |               |<---------------|<---------------|
   |         |               |                |                |
   |         |<-- Result ----|                |                |
   |<--------|               |                |                |
```

---

## 9. Compatibility Status

### 9.1 Verified Against FoundUps Core

| Component | Status | Evidence |
|-----------|--------|----------|
| `HermesJobExecutor` | Compatible | PR #478, #479, #481 |
| `FoundUpJobConsumer` | Compatible | PR #481 |
| `FoundUpJob contract` | Compatible | `foundup_job_contract.py` |
| `RouteEnvelope` | Compatible | `foundup_job_router.py` |
| `ConsumerResult` | Compatible | checkpoint/evidence fields |
| `WorkspaceBinding` | Compatible | path constraints |

### 9.2 External Workspace Compatibility

| Component | Status | Notes |
|-----------|--------|-------|
| `outsourc-e/hermes-workspace` | **NOT INSPECTED** | No SHA verified |
| Gateway adapter | **PROPOSED ONLY** | Design in this doc |
| Event contract | **PROPOSED ONLY** | Not implemented |

**Explicit statement**: External workspace compatibility is PROPOSED, not verified. Direct inspection of `outsourc-e/hermes-workspace` repository required before implementation.

---

## 10. WSP 15 Recommendation

### 10.1 Priority Scores

| Item | Security | Blocking | Effort | Value | Score | Priority |
|------|----------|----------|--------|-------|-------|----------|
| Gateway adapter contract (this doc) | Low (1) | High (9) | Low (2) | High (8) | 6.5 | **P0** |
| External workspace repo inspection | Med (4) | High (7) | Low (3) | Med (5) | 5.2 | **P1** |
| Runtime gateway client stub | Med (3) | Med (5) | Med (5) | Med (5) | 4.3 | **P2** |
| Live delegation | High (9) | Low (2) | High (8) | High (8) | 5.5 | **P3** |

### 10.2 Recommended Next Slice

**P1: External Workspace Repository Inspection**

```
HERMES_WORKSPACE_COMPATIBILITY_AUDIT_PHASE1

Objective:
  Directly inspect outsourc-e/hermes-workspace to verify:
  1. License compatibility
  2. Hook/callback contract compatibility with WSP task packet
  3. tmux worker lifecycle compatibility
  4. Evidence output format compatibility
  5. Security posture (no obvious vulnerabilities)

Deliverable:
  docs/architecture/HERMES_WORKSPACE_COMPATIBILITY_AUDIT.md
  with explicit SHA and compatibility verdict for each component.
```

---

## 11. WSP 97 Truth Boundaries

### 11.1 What This Document Enables

- API/event contract design for future gateway adapter
- WSP task packet schema definition
- Retention semantics for gateway failures
- Sequence diagrams for implementation guidance

### 11.2 What This Document Does NOT Enable

| Blocked | Reason |
|---------|--------|
| Live delegation | Phase F requires all gates |
| CABR verification | No CABR pipeline exists |
| Reward/payout | No token operations |
| Real execution | `real_execution_performed=false` |
| Receipt emission | Skipped for dry-run |

### 11.3 Truth Field Invariants

```
real_execution_performed = false  # Until Phase F live execution
verification_complete    = false  # Until CABR pipeline (Phase 7+)
cabr_ready              = false  # Until CABR consensus (Phase 7+)
payout_ready            = false  # Until payout engine (Phase 8+)
```

---

## Appendix A: Related Documents

- [FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md](./FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md) - Fork strategy
- [hermes_job_executor.py](../../modules/infrastructure/wre_core/src/hermes_job_executor.py) - Current adapter
- [foundup_job_consumer.py](../../modules/infrastructure/wre_core/src/foundup_job_consumer.py) - Consumer with retention
- [foundup_job_contract.py](../../modules/communication/moltbot_bridge/src/foundup_job_contract.py) - Job contract
- [foundup_job_router.py](../../modules/infrastructure/wre_core/src/foundup_job_router.py) - Routing/gates

## Appendix B: Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-05-03 | 0102 W1 | Initial gateway adapter design |
