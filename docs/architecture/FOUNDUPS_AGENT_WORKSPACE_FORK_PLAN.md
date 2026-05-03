# FoundUps Agent Workspace Fork Plan

**Status**: Architecture Documentation  
**WSP Compliance**: WSP 15 (Priority), WSP 50 (Pre-Action), WSP 97 (Truth Boundaries)  
**Date**: 2026-05-03  
**Author**: 0102 Architectural Worker  

---

## 1. Executive Summary

**FoundUps Agent Workspace** is an **external compatible system** designed to provide autonomous swarm execution capabilities for FoundUps. It is:

- **Forked from**: [outsourc-e/hermes-workspace](https://github.com/outsourc-e/hermes-workspace) (external repository)
- **Verified SHA**: `6485d2002f6a5c615fa000b2d8f0945d7dadc738` (2026-05-02)
- **Audit Reference**: [HERMES_WORKSPACE_EXTERNAL_REPO_AUDIT.md](../audits/hermes_swarm/HERMES_WORKSPACE_EXTERNAL_REPO_AUDIT.md)
- **NOT embedded** in FoundUps Core
- **NOT a submodule** of this repository
- **NOT vendored** into this codebase

The workspace provides a swarm UI, Kanban/task board, autonomous execution runtime, and workspace lifecycle management. It integrates with FoundUps through well-defined gateway APIs, WSP task packets, and checkpoint/evidence artifact contracts.

**Key principle**: FoundUps Core owns governance (WSP, WRE, CABR). FoundUps Agent Workspace owns execution (swarm workers, tmux sessions, UI).

---

## 2. Architecture Boundary

### 2.1 FoundUps Core (This Repository)

| Component | Responsibility |
|-----------|----------------|
| **WSP Framework** | Governance protocols, compliance rules, truth boundaries |
| **WRE (Windsurf Recursive Engine)** | Job validation, policy gates, routing, retention semantics |
| **OpenClaw** | Intent parsing, job queueing, orchestration |
| **HoloIndex** | Semantic search, knowledge retrieval, corpus management |
| **FoundUpJob Contract** | Job identity, payload, status, evidence refs, policy flags |
| **HermesJobExecutor Adapter** | Dry-run seam mapping FoundUpJob to delegation request |
| **ConsumerResult** | Checkpoint/evidence exposure, WSP 97 truth fields |

### 2.2 FoundUps Agent Workspace (External System)

| Component | Responsibility |
|-----------|----------------|
| **Swarm UI** | Visual task board, Kanban lanes, agent status |
| **Autonomous Execution Runtime** | tmux workers, agent coordination, tool execution |
| **Workspace Lifecycle** | Session management, cleanup, persistence |
| **Gateway Adapter** | Receives WSP task packets, emits checkpoint/evidence events |
| **Checkpoint Router** | Writes STATE/RESULT/BLOCKER/NEXT_ACTION to evidence path |

### 2.3 Boundary Diagram

```
+--------------------------------------------------+
|              FoundUps Core (this repo)           |
|                                                  |
|  OpenClaw -> FoundUpJob -> WRE Router            |
|       |                         |                |
|       v                         v                |
|  Intent Parser           Policy Gates            |
|       |                         |                |
|       +--------> HermesJobExecutor <-------------+
|                       |                          |
|                       | (dry-run seam)           |
|                       v                          |
|              HermesDelegationRequest             |
|                       |                          |
+--------------------------------------------------+
                        |
                        | Gateway API / WSP Task Packet
                        v
+--------------------------------------------------+
|        FoundUps Agent Workspace (external)       |
|                                                  |
|  Gateway Adapter -> Workspace Scheduler          |
|       |                   |                      |
|       v                   v                      |
|  Task Board         Agent Workers (tmux)         |
|       |                   |                      |
|       v                   v                      |
|  Checkpoint Router   Tool Execution              |
|       |                   |                      |
|       +----> Evidence Artifacts <----------------+
|                                                  |
+--------------------------------------------------+
                        |
                        | checkpoint.json, metadata.json
                        v
+--------------------------------------------------+
|              FoundUps Core (this repo)           |
|                                                  |
|  ConsumerResult <- Evidence Path                 |
|       |                                          |
|       v                                          |
|  Retention Decision -> Receipt (future)          |
|       |                                          |
|       v                                          |
|  pAVS Verification (future)                      |
|                                                  |
+--------------------------------------------------+
```

---

## 3. Integration Model

### 3.1 End-to-End Flow

```
OpenClaw intent
  -> FoundUpJob creation (job_id, foundup_id, requested_action)
  -> WRE validation and policy gates (envelope validation, security checks)
  -> HermesJobExecutor adapter (build delegation request)
  -> FoundUps Agent Workspace gateway (accept WSP task packet)
  -> Workspace scheduler (assign to agent worker)
  -> Agent execution (tool calls, file changes, commands)
  -> Checkpoint router (write STATE/RESULT/BLOCKER/NEXT_ACTION)
  -> Evidence writer (metadata.json, checkpoint.json)
  -> FoundUps Core receives evidence path
  -> ConsumerResult with checkpoint_state, evidence_path
  -> WRE retention/clear decision
  -> Receipt emission (future, requires real execution)
  -> pAVS verification (future, requires CABR pipeline)
```

### 3.2 Current State (Phase 1)

- **HermesJobExecutor**: Operational dry-run seam (PR #478, #479, #481)
- **Evidence collection**: metadata.json and checkpoint.json written to `.hermes_evidence/{job_id}/`
- **Live delegation**: BLOCKED by design (WSP 97 truth boundary)
- **Receipt emission**: Skipped for dry-run (evidence in checkpoint files)

### 3.3 Future State (Phase 2+)

- **FoundUps Agent Workspace**: Deployed as external service
- **Gateway API**: Accepts WSP task packets over HTTP/WebSocket
- **Live delegation**: Enabled with human approval, security gate, compute budget gates
- **Receipt emission**: Enabled for real terminal jobs
- **pAVS verification**: Connected to CABR pipeline

---

## 4. WSP Task Packet Contract

### 4.1 Proposed Schema

```json
{
  "packet_version": "1.0.0",
  "packet_type": "wsp_task",
  
  "identity": {
    "job_id": "string (UUID)",
    "foundup_id": "string | null",
    "tenant_id": "string",
    "intent_id": "string | null"
  },
  
  "task": {
    "requested_action": "string (build_foundup | validate_foundup | extract_foundup | ...)",
    "goal": "string (human-readable task description)",
    "context": "string (serialized job context)",
    "module_path": "string | null (e.g., modules/foundups/gotjunk)",
    "workspace_path": "string | null (relative path hint)"
  },
  
  "policy": {
    "dry_run_mode": "boolean (default: true)",
    "security_gate_checked": "boolean",
    "security_gate_passed": "boolean",
    "human_approval_received": "boolean",
    "live_mode_authorized": "boolean"
  },
  
  "compute": {
    "compute_budget": "integer | null (max compute units)",
    "compute_used": "integer (current usage)",
    "compute_tier": "string (freemium | basic | enterprise)",
    "model_preference": "string (auto | free | standard | premium)"
  },
  
  "evidence": {
    "evidence_refs": ["string (paths to evidence files)"],
    "evidence_output_path": "string (where to write new evidence)"
  },
  
  "checkpoint": {
    "checkpoint_state": "string (SIMULATED | DONE | BLOCKED | NEEDS_INPUT | HANDOFF)",
    "checkpoint_result": "string | null",
    "checkpoint_blocker": "string | null",
    "checkpoint_next_action": "string | null"
  },
  
  "wsp97_truth": {
    "real_execution_performed": "boolean (false until live execution)",
    "verification_complete": "boolean (false until CABR verification)",
    "cabr_ready": "boolean (false until CABR pipeline)",
    "payout_ready": "boolean (false until payout engine)"
  },
  
  "metadata": {
    "created_at": "ISO8601 timestamp",
    "executor_version": "string"
  }
}
```

### 4.2 Validation Rules

| Field | Required | Validation |
|-------|----------|------------|
| `job_id` | Yes | Non-empty UUID |
| `tenant_id` | Yes | Non-empty string |
| `requested_action` | Yes | Recognized action type |
| `dry_run_mode` | Yes | Default true if omitted |
| `compute_tier` | Yes for live | Must match allowed tiers |
| `wsp97_truth.*` | Yes | All false in Phase 1 |

---

## 5. Workspace Gateway Contract

### 5.1 Proposed Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `job.accepted` | Workspace -> Core | Gateway accepted WSP task packet |
| `job.started` | Workspace -> Core | Agent worker began execution |
| `agent.step` | Workspace -> Core | Agent completed one step/tool call |
| `checkpoint.written` | Workspace -> Core | Checkpoint file written to evidence path |
| `evidence.written` | Workspace -> Core | Metadata/evidence file written |
| `job.blocked` | Workspace -> Core | Execution blocked (gate/error/input needed) |
| `job.completed` | Workspace -> Core | Execution reached terminal state |
| `job.retained` | Core -> Workspace | Job retained for retry/inspection |
| `job.cleared` | Core -> Workspace | Job cleared from queue |

### 5.2 Event Schema

```json
{
  "event_type": "job.started",
  "event_id": "string (UUID)",
  "timestamp": "ISO8601",
  "job_id": "string",
  "payload": {
    "agent_id": "string",
    "workspace_session": "string",
    "tools_enabled": ["string"]
  }
}
```

### 5.3 Gateway Endpoints (Proposed)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tasks` | POST | Submit WSP task packet |
| `/api/v1/tasks/{job_id}` | GET | Get task status |
| `/api/v1/tasks/{job_id}/checkpoint` | GET | Get latest checkpoint |
| `/api/v1/tasks/{job_id}/evidence` | GET | Get evidence artifacts |
| `/api/v1/tasks/{job_id}/cancel` | POST | Request task cancellation |
| `/ws/v1/events` | WebSocket | Real-time event stream |

---

## 6. Fork Adaptation Plan

### Phase A: Fork and Rename (Docs Only)

**Objective**: Create fork, rename branding, no functional changes.

- [ ] Fork `outsourc-e/hermes-workspace` to `FOUNDUPS/foundups-agent-workspace`
- [ ] Rename references: "Hermes" -> "FoundUps Agent"
- [ ] Update README with FoundUps positioning
- [ ] Preserve all existing functionality
- [ ] No integration code yet

### Phase B: Add FoundUps Gateway Adapter

**Objective**: Add adapter layer for FoundUps integration.

- [ ] Create `foundups_gateway_adapter.py` or equivalent
- [ ] Implement WSP task packet import
- [ ] Implement event emission (job.accepted, job.started, etc.)
- [ ] Add configuration for FoundUps Core endpoint
- [ ] No live execution yet

### Phase C: Add WSP Task Packet Import/Export

**Objective**: Full task packet contract compliance.

- [ ] Implement packet validation against schema
- [ ] Map packet fields to workspace internal structures
- [ ] Export checkpoint/evidence in FoundUps format
- [ ] Add packet version negotiation

### Phase D: Add Checkpoint/Evidence Compatibility

**Objective**: Evidence artifacts match FoundUps format.

- [ ] Write checkpoint.json with STATE/RESULT/BLOCKER/NEXT_ACTION
- [ ] Write metadata.json with job identity, timing, workspace binding
- [ ] Use `.hermes_evidence/{job_id}/` path convention
- [ ] Emit evidence.written events

### Phase E: Add Dry-Run Swarm Execution Demo

**Objective**: Demonstrate end-to-end flow without real execution.

- [ ] Accept WSP task packet from FoundUps Core
- [ ] Spawn tmux worker in dry-run mode
- [ ] Execute simulated tool calls
- [ ] Write checkpoint/evidence artifacts
- [ ] Return completion status to FoundUps Core

### Phase F: Add Live Delegation Gate

**Objective**: Enable real execution with proper gates.

- [ ] Require human_approval_received=true
- [ ] Require security_gate_passed=true
- [ ] Require compute_budget > 0
- [ ] Require live_mode_authorized=true
- [ ] Enable terminal/file tools
- [ ] WSP 97: Set real_execution_performed=true only after real execution

---

## 7. WSP 97 Truth Boundaries

### 7.1 Explicit Statements

This documentation does **NOT** enable:

1. **Live FoundUps Core execution** - All execution remains in dry-run/simulation mode
2. **CABR verification claims** - `cabr_ready` remains false
3. **Reward/payout claims** - `payout_ready` remains false
4. **Token minting/distribution** - No token operations enabled
5. **Real delegate_task calls** - Hermes delegation remains blocked

### 7.2 Evidence Artifact Truth

- Evidence artifacts (metadata.json, checkpoint.json) are **observability artifacts**
- They prove a job was processed through the WRE pipeline
- They do **NOT** prove real work was executed
- They do **NOT** constitute verification or audit proof
- `checkpoint_state="SIMULATED"` indicates dry-run, not real execution

### 7.3 Future Live Execution Requirements

Live execution (Phase F) requires **ALL** of these gates:

1. `human_approval_received=true` - Human reviewed and approved
2. `security_gate_passed=true` - WSP 15 security audit passed
3. `compute_budget > 0` - Explicit compute budget allocated
4. `live_mode_authorized=true` - Policy flag set
5. `dry_run_mode=false` - Explicitly disabled
6. HermesJobExecutor real delegation implemented (currently BLOCKED)

Only when all gates pass can `real_execution_performed=true` be set.

---

## 8. WSP 15 Priority Matrix

### 8.1 Scoring Criteria

| Factor | Weight | Description |
|--------|--------|-------------|
| Security Risk | 40% | Potential for harm if done wrong |
| Dependency Blocking | 30% | How many other items depend on this |
| Effort | 20% | Implementation complexity |
| Value | 10% | Direct user/system value |

### 8.2 Priority Scores

| Item | Security | Blocking | Effort | Value | Score | Priority |
|------|----------|----------|--------|-------|-------|----------|
| Fork plan docs (this doc) | Low (0) | High (9) | Low (2) | Med (5) | 6.1 | **P0** |
| Gateway adapter design | Low (1) | High (8) | Med (5) | Med (5) | 5.3 | **P1** |
| Additional WRE hardening | Med (5) | Med (5) | Med (4) | Low (3) | 4.5 | **P1** |
| Full workspace fork impl | Med (4) | Low (3) | High (8) | High (8) | 4.4 | **P2** |
| Live delegation | High (9) | Low (2) | High (9) | High (9) | 5.7 | **P3** |

### 8.3 Recommendation

**Immediate (P0)**:
- Complete this fork plan documentation (current task)

**Next Sprint (P1)**:
- Design gateway adapter contract in detail
- Add WRE hardening tests for edge cases

**Future (P2/P3)**:
- Implement workspace fork (external repo)
- Enable live delegation (requires security audit, human approval gates)

---

## 9. Repo Impact / Non-Goals

### 9.1 What This Document Does

- Defines architecture boundary between FoundUps Core and Agent Workspace
- Specifies WSP task packet contract
- Specifies gateway event contract
- Documents fork adaptation phases
- Establishes WSP 97 truth boundaries
- Provides WSP 15 priority guidance

### 9.2 What This Document Does NOT Do

| Non-Goal | Explanation |
|----------|-------------|
| Runtime code changes | No `.py` files modified |
| Vendor updates | No vendor/ directory changes |
| Submodule additions | No git submodule add |
| CI behavior changes | No workflow modifications |
| Live delegation enable | Blocked by WSP 97 |
| External repo clone | No `git clone outsourc-e/hermes-workspace` |

### 9.3 Files Changed by This Slice

```
docs/architecture/FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md  (NEW)
ROADMAP.md                                               (UPDATE)
WSP_framework/ModLog.md                                  (UPDATE)
```

---

## 10. External Repository Reference

### 10.1 Source Repository

- **URL**: https://github.com/outsourc-e/hermes-workspace
- **Inspected**: NOT directly cloned or inspected in this slice
- **Hook compatibility**: NOT verified (requires direct audit of external repo)

### 10.2 Future Inspection Requirements

Before Phase A (fork), the following must be verified:

1. License compatibility with FoundUps project
2. Hook/callback compatibility with WSP task packet contract
3. tmux worker lifecycle compatibility
4. Evidence output format compatibility
5. Security audit of external codebase

---

## Appendix A: Related Documents

- [WRE Hermes Executor Lane](../../modules/infrastructure/wre_core/src/hermes_job_executor.py)
- [FoundUpJob Consumer](../../modules/infrastructure/wre_core/src/foundup_job_consumer.py)
- [WSP 97: System Execution Prompting](../../WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md)
- [WSP 15: Security Priority](../../WSP_framework/src/WSP_15_Secure_Operations_Protocol.md)

## Appendix B: Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-05-03 | 0102 W1 | Initial fork plan documentation |
