# Agent Module Interface

Public API and schema contracts for agent lifecycle management, BuildPlan generation, and controlled execution.

## BuildPlan Pipeline (OC8/OC9/OC12)

### Core Dataclasses

```python
# modules/foundups/agent/src/build_plan.py
BuildPlan        # Multi-step orchestration contract
BuildTarget      # Target paths and scope
BuildStep        # Step definition with action enum
BuildGate        # Gate checkpoints (genesis, dry_run, human_approval)
BuildEvidence    # Evidence reference with verification status
```

### BuildPlan Generator

```python
# modules/foundups/agent/src/build_plan_generator.py
def create_build_plan_from_job(job: FoundUpJob) -> BuildPlan:
    """Generate BuildPlan from FoundUpJob. Always produces dry_run=True plans."""

def can_generate_build_plan(job: FoundUpJob) -> bool:
    """Check if job can generate a BuildPlan."""
```

### BuildPlan Executor (Interface Stub)

```python
# modules/foundups/agent/src/build_plan_executor.py
class BuildPlanExecutor:
    """Controlled step execution. Real execution NOT implemented."""
    
    def __init__(self, dry_run: bool = True): ...
    def validate_plan(self, plan: BuildPlan) -> ValidationResult: ...
    def evaluate_gate(self, plan: BuildPlan, gate_type: GateType) -> GateEvaluationResult: ...
    def simulate_step(self, plan: BuildPlan, step: BuildStep) -> StepExecutionResult: ...
    def execute_step(self, plan: BuildPlan, step: BuildStep) -> StepExecutionResult: ...
    def create_execution_receipt(self, plan: BuildPlan, results: List[StepExecutionResult]) -> ExecutionReceipt: ...

# Execution Result Types
StepExecutionStatus  # SUCCEEDED | FAILED | BLOCKED | SKIPPED | SIMULATED
ExecutionReceipt     # Terminal receipt with WSP 97 truth fields
```

### WSP 97 Truth Fields

ExecutionReceipt enforces these fields as False always:
- `verification_complete = False`
- `cabr_ready = False`
- `payout_ready = False`
- `real_execution_performed = False`

---

## Swarm Coordination (OC13)

### SwarmCoordinator

```python
# modules/foundups/agent/src/build_plan_swarm.py
class SwarmCoordinator:
    """Multi-agent step assignment and file ownership coordination."""
    
    def register_worker(self, worker: WorkerIdentity) -> None: ...
    def assign_step(self, step: BuildStep, worker_id: str, owned_files: list[str]) -> StepAssignment: ...
    def claim_files(self, worker_id: str, files: list[str], step_id: str) -> list[FileOwnershipClaim]: ...
    def release_files(self, worker_id: str, files: list[str]) -> None: ...
    def detect_conflicts(self) -> list[ConflictReport]: ...
    def renew_lease(self, lease_id: str) -> Lease: ...
    def expire_leases(self, now: datetime) -> list[str]: ...
    def aggregate_evidence(self) -> EvidenceBundle: ...
    def summarize(self) -> SwarmExecutionSummary: ...
```

### Coordination Dataclasses

```python
WorkerIdentity      # Worker ID, type, capabilities, lease
StepAssignment      # Step-to-worker assignment (simulated=True always)
FileOwnershipClaim  # File ownership with expiration
Lease               # Worker lease with renewal
ConflictReport      # File ownership conflict
EvidenceBundle      # Aggregated evidence refs
SwarmExecutionSummary  # Execution state summary
```

### Coordination Enums

```python
AssignmentStatus     # ASSIGNED | IN_PROGRESS | COMPLETED | FAILED | CANCELLED
LeaseStatus          # ACTIVE | EXPIRED | RELEASED
ConflictSeverity     # WARNING | ERROR | FATAL
WorkerCapability     # VALIDATE | BUILD | TEST | ALL
```

### Coordination Rules

| Rule | Description |
|------|-------------|
| R1 | Two workers cannot own same file simultaneously |
| R2 | Claims must be within BuildPlan target scope |
| R3 | Lease expiration releases file claims |
| R4 | Assignments are simulated only |

### Swarm WSP 97 Truth Fields

- `StepAssignment.simulated = True` (always)
- `EvidenceBundle.verification_complete = False` (always)
- `EvidenceBundle.cabr_ready = False` (always)
- `SwarmExecutionSummary.all_simulated = True` (always)
- `SwarmExecutionSummary.real_execution_performed = False` (always)

---

## Swarm WRE Queue (OC15)

### SwarmWorkerQueue

```python
# modules/foundups/agent/src/build_plan_swarm_queue.py
class SwarmWorkerQueue:
    """Queue for swarm worker assignment dispatch."""
    
    def enqueue_assignment(self, assignment: StepAssignment, priority: QueuePriority, step_action: BuildStepAction) -> QueueAssignmentResult: ...
    def dequeue_for_worker(self, request: WorkerDequeueRequest) -> WorkerDequeueResult: ...
    def heartbeat(self, worker_id: str, entry_id: str) -> WorkerHeartbeat: ...
    def complete_assignment(self, report: AssignmentCompletionReport) -> QueueAssignmentResult: ...
    def expire_entries(self, now: datetime) -> list[str]: ...
    def list_entries(self, status: QueueEntryStatus) -> list[SwarmWorkerQueueEntry]: ...
```

### Queue Dataclasses

```python
SwarmWorkerQueueEntry  # Queue entry with status, lease, evidence
WorkerDequeueRequest   # Worker request with capabilities
WorkerDequeueResult    # Dequeue result with assigned entries
WorkerHeartbeat        # Heartbeat response with lease renewal
AssignmentCompletionReport  # Completion report with evidence
QueueAssignmentResult  # Operation result
```

### Queue Enums

```python
QueuePriority     # CRITICAL | HIGH | NORMAL | LOW
QueueEntryStatus  # QUEUED | PROCESSING | COMPLETED | FAILED | EXPIRED
DequeueDecision   # ASSIGNED | NO_MATCH | QUEUE_EMPTY | BLOCKED
CompletionStatus  # SUCCEEDED | FAILED | SKIPPED
```

### Capability Matching

| Step Action | Required Capability |
|-------------|---------------------|
| VALIDATE_* | validate |
| CREATE_*, UPDATE_* | build |
| RUN_TESTS | test |

### Queue Lifecycle

```
Enqueue → QUEUED → Dequeue → PROCESSING → Complete → COMPLETED
                       ↓ (lease expired)
                    Requeue → QUEUED (if retriable)
                       ↓
                    EXPIRED (if max retries)
```

### Queue WSP 97 Truth Fields

- `SwarmWorkerQueueEntry.simulated = True` (always)
- `AssignmentCompletionReport.simulated = True` (always)
- No `real_execution_performed` field exists
- No CABR/reward/payout/token fields

---

## Worker Assignment Protocol (OC17)

### AssignmentDispatcher

```python
# modules/foundups/agent/src/worker_assignment_protocol.py
class AssignmentDispatcher:
    """Dispatches SwarmWorkerQueue assignments to worker processes."""
    
    def register_worker(self, registration: WorkerRegistration) -> WorkerProcess: ...
    def deregister_worker(self, worker_id: str) -> WorkerDeregistration: ...
    def dispatch_assignment(self, request: AssignmentDispatchRequest) -> AssignmentDispatchResult: ...
    def receive_heartbeat(self, event: WorkerHeartbeatEvent) -> WorkerProcess: ...
    def receive_completion(self, event: WorkerCompletionEvent) -> AssignmentDispatchResult: ...
    def list_workers(self, status: WorkerProcessStatus | None) -> list[WorkerProcess]: ...
```

### Protocol Dataclasses

```python
WorkerProcess           # Registered worker with status, capabilities
WorkerRegistration      # Worker registration request
WorkerDeregistration    # Deregistration result
AssignmentDispatchRequest   # Dispatch request with step details
AssignmentDispatchResult    # Dispatch result (simulated)
WorkerHeartbeatEvent    # Heartbeat from worker
WorkerCompletionEvent   # Completion report with evidence
```

### Protocol Enums

```python
WorkerProcessStatus      # IDLE | ASSIGNED | PROCESSING | FAILED | TERMINATED
WorkerRuntimeType        # OPENCLAW | HERMES | CLAUDE_0102 | QWEN | GEMMA | GENERIC
AssignmentDispatchStatus # SIMULATED_DISPATCH | SPECIFIED_NOT_IMPLEMENTED | WORKER_NOT_FOUND | ...
WorkerTrustLevel         # UNTRUSTED | VERIFIED | TRUSTED | SYSTEM
```

### Protocol WSP 97 Truth Fields

- `WorkerProcess.simulated = True` (always)
- `AssignmentDispatchResult.simulated = True` (always)
- `AssignmentDispatchResult.real_process_started = False` (always)
- `WorkerCompletionEvent.simulated = True` (always)
- No CABR/reward/payout/token fields

---

## Swarm Dispatch Integration (OC18)

### SwarmDispatchCoordinator

```python
# modules/foundups/agent/src/swarm_dispatch_integration.py
class SwarmDispatchCoordinator:
    """Coordinates between SwarmWorkerQueue and AssignmentDispatcher."""
    
    def __init__(self, queue: SwarmWorkerQueue, dispatcher: AssignmentDispatcher): ...
    def dispatch_next(self, worker_id: str) -> DispatchCycleResult: ...
    def complete_dispatched_assignment(self, worker_id: str, entry_id: str, evidence_refs: list[str]) -> DispatchCycleResult: ...
    def run_simulated_cycle(self, worker_id: str, evidence_refs: list[str] | None) -> DispatchCycleResult: ...
    def summarize(self) -> QueueDispatchSummary: ...
```

### Integration Dataclasses

```python
DispatchCycleResult     # Result of dispatch cycle (simulated)
QueueDispatchSummary    # Queue/dispatcher state summary
```

### Integration Enums

```python
DispatchCycleStatus     # SUCCESS | NO_QUEUED_ENTRIES | NO_CAPABILITY_MATCH | ...
```

### Integration WSP 97 Truth Fields

- `DispatchCycleResult.simulated = True` (always)
- `DispatchCycleResult.real_process_started = False` (always)
- `QueueDispatchSummary.all_simulated = True` (always)
- `QueueDispatchSummary.real_execution_performed = False` (always)
- No CABR/reward/payout/token fields

---

## Event Schemas

### agent_joins

Emitted when agent enters the ecosystem in dormant 01(02) state.

```python
{
    "event_type": "agent_joins",
    "actor_id": "founder_001",           # Unique agent identifier
    "foundup_id": "F_0",                 # FoundUp context (F_0 = ecosystem-level)
    "payload": {
        "agent_type": "founder",         # founder | user
        "public_key": "0xfoundup001...", # Wallet address
        "rank": 1,                       # Initial rank (1=Apprentice)
        "state": "01(02)",               # Dormant until awakened
        "foundup_idx": 0,                # FoundUp index for display
    }
}
```

### agent_awakened

Emitted when agent transitions to 0102 zen state (coherence >= 0.618).

```python
{
    "event_type": "agent_awakened",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "coherence": 0.72,               # Coherence score (0.618-1.0)
        "state": "0102",                 # Zen state - active
    }
}
```

### agent_idle

Emitted when agent decays to 01/02 state (inactivity or coherence drop).

```python
{
    "event_type": "agent_idle",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "inactive_ticks": 150,           # Ticks since last activity
        "current_tick": 1000,            # Current simulation tick
        "state": "01/02",                # Decayed - awaiting ORCH
    }
}
```

### agent_ranked

Emitted when agent rank increases.

```python
{
    "event_type": "agent_ranked",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "old_rank": 2,                   # Previous rank (1-7)
        "new_rank": 3,                   # New rank (1-7)
        "old_title": "Builder",          # Previous title
        "new_title": "Contributor",      # New title
    }
}
```

### agent_earned

Emitted when agent receives F_i payout.

```python
{
    "event_type": "agent_earned",
    "actor_id": "founder_001",
    "foundup_id": "F_001",
    "task_id": "task_0042",
    "payload": {
        "amount": 50,                    # F_i tokens earned
        "foundup_idx": 1,                # FoundUp index
        "task_id": "task_0042",          # Task context
    }
}
```

### agent_leaves

Emitted when agent logs off with wallet balance.

```python
{
    "event_type": "agent_leaves",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "public_key": "0xfoundup001...", # Wallet address
        "wallet_balance": 1250.0,        # Final F_i balance
    }
}
```

## State Transitions

### Valid Transitions

```
01(02) → 0102   # agent_awakened (coherence >= 0.618)
0102 → 01/02    # agent_idle (inactivity > threshold OR coherence < 0.618)
01/02 → 0102    # agent_awakened (re-awakening via WSP_00)
```

### Coherence Thresholds

| Threshold | Meaning |
|-----------|---------|
| 0.618 | Minimum for 0102 zen state (golden ratio) |
| 0.50 | Minimum for any activity |
| < 0.50 | Cannot perform actions |

## Dedupe Keys

Each event type has a unique dedupe key pattern:

```
agent_joins:    agent_joins:{agent_id}:{foundup_id}
agent_awakened: agent_awakened:{agent_id}:{timestamp[:19]}
agent_idle:     agent_idle:{agent_id}:{tick // 100}
agent_ranked:   agent_ranked:{agent_id}:{new_rank}
agent_earned:   agent_earned:{agent_id}:{task_id}
agent_leaves:   agent_leaves:{agent_id}:{timestamp[:19]}
```

## Service Boundaries

### AgentLifecycleService (Future)

```python
class AgentLifecycleService:
    """Manage agent state transitions."""

    def join(self, agent_id: str, agent_type: str, public_key: str) -> None:
        """Register agent in 01(02) dormant state."""

    def awaken(self, agent_id: str) -> bool:
        """Transition to 0102 zen state if coherence >= 0.618."""

    def mark_idle(self, agent_id: str, inactive_ticks: int) -> None:
        """Transition to 01/02 decayed state."""

    def rank_up(self, agent_id: str) -> int:
        """Evaluate and update agent rank. Returns new rank."""

    def leave(self, agent_id: str) -> float:
        """Log off agent and return final wallet balance."""

    def get_state(self, agent_id: str) -> str:
        """Return current state: '01(02)', '0102', or '01/02'."""
```

## Integration

### FAMBridge Methods

```python
# In modules/foundups/simulator/adapters/fam_bridge.py
emit_agent_joins(agent_id, agent_type, foundup_id, public_key, rank)
emit_agent_awakened(agent_id, coherence, foundup_id)
emit_agent_idle(agent_id, foundup_id, inactive_ticks, current_tick)
emit_agent_ranked(agent_id, old_rank, new_rank, foundup_id)
emit_agent_earned(agent_id, foundup_id, amount, task_id)
emit_agent_leaves(agent_id, wallet_balance, public_key, foundup_id)
```

### SSE Streaming

Events are streamed via `STREAMABLE_EVENT_TYPES` in `sse_server.py`:

```python
"agent_joins", "agent_awakened", "agent_idle",
"agent_ranked", "agent_earned", "agent_leaves",
```

### Animation Display

Ticker messages in `foundup-cube.js`:

```javascript
agent_joins:    "01(02) 0xfound001... enters (founder)"
agent_awakened: "0102 founder_001 ZEN (0.72)"
agent_idle:     "01/02 founder_001 IDLE (150 ticks)"
agent_ranked:   "founder_001 rank UP: 2→3 (Contributor)"
agent_earned:   "founder_001 earned 50 F₁"
agent_leaves:   "0xfound001... logs off (1250 F_i)"
```
