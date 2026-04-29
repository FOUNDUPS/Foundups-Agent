# BuildPlan Swarm WRE Queue Contract

**Status**: Architecture Specification (ADR)
**Owner**: 0102
**Slice**: `OC15_SWARM_WORKER_ASSIGNMENT_WRE_QUEUE_CONTRACT_PHASE1`
**WSP References**: WSP 11 (Interface Protocol), WSP 50 (Pre-Action Verification), WSP 77 (Agent Coordination), WSP 97 (Truth Boundaries)

---

## WSP 97 Truthfulness Statement

This document is an **architecture specification only**. No real WRE queue integration is implemented.

| Claim | Status |
|-------|--------|
| SwarmWorkerQueue interface defined | `SPECIFIED_SCAFFOLD_ONLY` |
| Queue entry creation | `SCAFFOLD_SIMULATED` |
| Worker dequeue | `SCAFFOLD_SIMULATED` |
| Heartbeat/lease renewal | `SCAFFOLD_SIMULATED` |
| Completion reporting | `SCAFFOLD_SIMULATED` |
| Real WRE queue integration | `NOT_IMPLEMENTED` |
| Real worker process dequeue | `NOT_IMPLEMENTED` |
| CABR/payout/reward | `NOT_IMPLEMENTED` |

**Canonical Rule**: Queue entries are simulated. No real workers are started.

---

## 1. Purpose

The Swarm WRE Queue Contract defines how SwarmCoordinator step assignments flow into a queue model for worker dequeue.

**Architecture Position**:
```
SwarmCoordinator.assign_step()
    │
    ▼
SwarmWorkerQueue.enqueue_assignment()
    │
    ▼
SwarmWorkerQueueEntry (QUEUED)
    │
    ├─> Worker dequeue_for_worker() ─> WorkerDequeueResult
    │       │
    │       ▼
    │   Entry (PROCESSING) with lease
    │       │
    │       ├─> heartbeat() ─> renew lease
    │       │
    │       └─> complete_assignment() ─> Entry (COMPLETED)
    │
    └─> expire_entries() ─> Entry (EXPIRED) or requeue
```

**PoC Goal**: Swarm assignments can be enqueued and simulated dequeue.
**MVP Goal**: Real workers dequeue assignments from WRE queue.

---

## 2. Core Interfaces

### 2.1 SwarmWorkerQueue

```python
class SwarmWorkerQueue:
    """Queue for swarm worker assignment dispatch."""
    
    def enqueue_assignment(
        self,
        assignment: StepAssignment,
        priority: QueuePriority = QueuePriority.NORMAL,
    ) -> QueueAssignmentResult:
        """Enqueue a step assignment for worker pickup."""
    
    def dequeue_for_worker(
        self,
        request: WorkerDequeueRequest,
    ) -> WorkerDequeueResult:
        """Attempt to dequeue an assignment for a worker."""
    
    def heartbeat(
        self,
        worker_id: str,
        entry_id: str,
    ) -> WorkerHeartbeat:
        """Send heartbeat to renew processing lease."""
    
    def complete_assignment(
        self,
        report: AssignmentCompletionReport,
    ) -> QueueAssignmentResult:
        """Report assignment completion with evidence."""
    
    def expire_entries(self, now: datetime) -> list[str]:
        """Expire stale entries and requeue if retriable."""
    
    def list_entries(
        self,
        status: QueueEntryStatus | None = None,
    ) -> list[SwarmWorkerQueueEntry]:
        """List queue entries, optionally filtered by status."""
```

### 2.2 SwarmWorkerQueueEntry

```python
@dataclass
class SwarmWorkerQueueEntry:
    entry_id: str                    # Unique queue entry ID
    assignment_id: str               # Source StepAssignment ID
    step_id: str                     # BuildStep being assigned
    required_capability: str         # Capability needed to process
    priority: QueuePriority          # CRITICAL, HIGH, NORMAL, LOW
    status: QueueEntryStatus         # QUEUED, PROCESSING, COMPLETED, FAILED, EXPIRED
    
    worker_id: Optional[str]         # Worker processing (if any)
    owned_files: list[str]           # Files claimed by assignment
    
    queued_at: datetime
    processing_started_at: Optional[datetime]
    completed_at: Optional[datetime]
    lease_expires_at: Optional[datetime]
    
    retry_count: int = 0
    max_retries: int = 3
    
    evidence_refs: list[str]         # Evidence from completion
    simulated: bool = True           # WSP 97: Always True
```

### 2.3 WorkerDequeueRequest

```python
@dataclass
class WorkerDequeueRequest:
    worker_id: str                   # Worker requesting assignment
    capabilities: list[str]          # Worker capabilities
    max_entries: int = 1             # Max entries to dequeue
    preferred_step_ids: list[str]    # Preferred steps (optional)
```

### 2.4 WorkerDequeueResult

```python
@dataclass
class WorkerDequeueResult:
    success: bool
    decision: DequeueDecision        # ASSIGNED, NO_MATCH, QUEUE_EMPTY, BLOCKED
    entries: list[SwarmWorkerQueueEntry]  # Entries assigned
    lease_expires_at: Optional[datetime]
    reason: str
```

### 2.5 WorkerHeartbeat

```python
@dataclass
class WorkerHeartbeat:
    entry_id: str
    worker_id: str
    lease_renewed: bool
    new_expires_at: Optional[datetime]
    heartbeat_at: datetime
```

### 2.6 AssignmentCompletionReport

```python
@dataclass
class AssignmentCompletionReport:
    entry_id: str
    worker_id: str
    status: CompletionStatus         # SUCCEEDED, FAILED, SKIPPED
    evidence_refs: list[str]
    error_message: Optional[str]
    completed_at: datetime
    simulated: bool = True           # WSP 97: Always True
```

### 2.7 QueueAssignmentResult

```python
@dataclass
class QueueAssignmentResult:
    success: bool
    entry_id: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
```

---

## 3. Enums

### 3.1 QueuePriority

```python
class QueuePriority(str, Enum):
    CRITICAL = "critical"   # Must process immediately
    HIGH = "high"           # Process before normal
    NORMAL = "normal"       # Default priority
    LOW = "low"             # Process when idle
```

### 3.2 QueueEntryStatus

```python
class QueueEntryStatus(str, Enum):
    QUEUED = "queued"           # Waiting for worker
    PROCESSING = "processing"   # Worker has dequeued
    COMPLETED = "completed"     # Successfully completed
    FAILED = "failed"           # Failed after max retries
    EXPIRED = "expired"         # Lease expired, not retried
```

### 3.3 DequeueDecision

```python
class DequeueDecision(str, Enum):
    ASSIGNED = "assigned"       # Entry assigned to worker
    NO_MATCH = "no_match"       # No entry matches capabilities
    QUEUE_EMPTY = "queue_empty" # No entries in queue
    BLOCKED = "blocked"         # Worker blocked from dequeue
```

### 3.4 CompletionStatus

```python
class CompletionStatus(str, Enum):
    SUCCEEDED = "succeeded"     # Assignment completed successfully
    FAILED = "failed"           # Assignment failed
    SKIPPED = "skipped"         # Assignment skipped (optional step)
```

---

## 4. Queue Lifecycle

### 4.1 Enqueue

```
StepAssignment (from SwarmCoordinator)
    │
    ▼
SwarmWorkerQueue.enqueue_assignment()
    │
    ├─> Create SwarmWorkerQueueEntry
    ├─> Set status = QUEUED
    ├─> Set required_capability from step action
    └─> Return QueueAssignmentResult
```

### 4.2 Dequeue

```
Worker sends WorkerDequeueRequest
    │
    ▼
SwarmWorkerQueue.dequeue_for_worker()
    │
    ├─> Match entries by capability
    ├─> Sort by priority, queued_at
    ├─> Assign entry to worker
    ├─> Set status = PROCESSING
    ├─> Set lease_expires_at
    └─> Return WorkerDequeueResult
```

### 4.3 Heartbeat

```
Worker sends heartbeat(worker_id, entry_id)
    │
    ▼
SwarmWorkerQueue.heartbeat()
    │
    ├─> Verify worker owns entry
    ├─> Extend lease_expires_at
    └─> Return WorkerHeartbeat
```

### 4.4 Completion

```
Worker sends AssignmentCompletionReport
    │
    ▼
SwarmWorkerQueue.complete_assignment()
    │
    ├─> Verify worker owns entry
    ├─> Set status = COMPLETED (or FAILED)
    ├─> Record evidence_refs
    └─> Return QueueAssignmentResult
```

### 4.5 Expiration

```
SwarmWorkerQueue.expire_entries(now)
    │
    ▼
For each entry where lease_expires_at < now:
    ├─> If retry_count < max_retries:
    │       ├─> Increment retry_count
    │       ├─> Clear worker_id
    │       └─> Set status = QUEUED (requeue)
    └─> Else:
            └─> Set status = EXPIRED
```

---

## 5. Capability Matching

Dequeue matches worker capabilities to entry requirements:

| Step Action | Required Capability |
|-------------|---------------------|
| VALIDATE_GENESIS | `validate` |
| VALIDATE_MANIFEST | `validate` |
| VALIDATE_STRUCTURE | `validate` |
| CREATE_SPEC | `build` |
| CREATE_TEST | `build` |
| CREATE_MODULE | `build` |
| CREATE_ADAPTERS | `build` |
| RUN_TESTS | `test` |
| UPDATE_* | `build` |

Workers with capability `all` can dequeue any entry.

---

## 6. Lease Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| Lease Duration | 300s | Time before lease expires |
| Heartbeat Interval | 60s | Recommended heartbeat frequency |
| Max Retries | 3 | Times entry can be requeued |

Lease expiration triggers:
1. Entry returns to QUEUED (if retries remain)
2. Entry moves to EXPIRED (if max retries exceeded)
3. Worker loses claim on entry

---

## 7. Evidence Flow

Evidence flows from completion back to SwarmCoordinator:

```
AssignmentCompletionReport.evidence_refs
    │
    ▼
SwarmWorkerQueueEntry.evidence_refs
    │
    ▼
StepAssignment.evidence_refs (via callback)
    │
    ▼
SwarmCoordinator.aggregate_evidence() -> EvidenceBundle
```

---

## 8. WSP 97 Truth Boundaries

This scaffold enforces the following truth fields:

| Field | Value | Location |
|-------|-------|----------|
| `SwarmWorkerQueueEntry.simulated` | True | Always |
| `AssignmentCompletionReport.simulated` | True | Always |
| `real_execution_performed` | False | No field exists |
| `cabr_ready` | False | No field exists |
| `payout_ready` | False | No field exists |

**No CABR/reward/payout/token fields exist in this contract.**

---

## 9. Queue Rules

| Rule | Description |
|------|-------------|
| R1 | Dequeue is capability-aware |
| R2 | Dequeue creates/renews a lease |
| R3 | Expired entries requeue if retries remain |
| R4 | Completion reports simulated completion only |
| R5 | Completion may carry evidence_refs |
| R6 | No real worker process is started |
| R7 | No files are edited |
| R8 | No CABR/payout/reward fields exist |
| R9 | Queue state is in-memory for Phase 1 |

---

## 10. VoteBallot Example (SPEC_EXAMPLE_NOT_EXECUTED)

```python
# VoteBallot swarm assignment enqueued and dequeued

from modules.foundups.agent.src.build_plan_swarm import (
    SwarmCoordinator, WorkerIdentity, create_swarm_coordinator
)
from modules.foundups.agent.src.build_plan_swarm_queue import (
    SwarmWorkerQueue, WorkerDequeueRequest, AssignmentCompletionReport,
    QueuePriority, CompletionStatus
)
from modules.foundups.agent.src.build_plan_generator import create_build_plan_from_job
from modules.communication.moltbot_bridge.src.foundup_job_contract import create_job

# Create job and plan
job = create_job(
    tenant_id="foundups",
    requested_action="build_foundup",
    foundup_id="voteballots",
)
plan = create_build_plan_from_job(job)

# Create swarm and queue
coordinator = create_swarm_coordinator(plan)
queue = SwarmWorkerQueue()

# Register worker
coordinator.register_worker(WorkerIdentity(
    worker_id="worker_vb_001",
    worker_type="openclaw",
    capabilities=["validate", "build"],
))

# Assign step and enqueue
assignment = coordinator.assign_step(
    plan.steps[0],
    "worker_vb_001",
    ["modules/foundups/voteballots/README.md"],
)
queue.enqueue_assignment(assignment, priority=QueuePriority.NORMAL)

# Worker dequeues
result = queue.dequeue_for_worker(WorkerDequeueRequest(
    worker_id="worker_vb_001",
    capabilities=["validate", "build"],
))
assert result.success
assert result.decision == DequeueDecision.ASSIGNED

# Worker completes
queue.complete_assignment(AssignmentCompletionReport(
    entry_id=result.entries[0].entry_id,
    worker_id="worker_vb_001",
    status=CompletionStatus.SUCCEEDED,
    evidence_refs=["evidence/vb/step1"],
))

# Entry is completed, simulated only
entries = queue.list_entries()
assert entries[0].status == QueueEntryStatus.COMPLETED
assert entries[0].simulated is True
```

**NOTE**: This example is specification only. No real execution occurs.

---

## 11. Future Extensions (Out of Scope)

The following are explicitly out of scope for OC15:

- Real WRE queue integration
- Persistent queue storage (Redis, PostgreSQL)
- Real worker process dequeue
- Cross-machine coordination
- Queue metrics/observability hooks
- RedDog/pfMALL UI integration
- CABR/rewards/payouts

These will be addressed in future OC slices.
