# Real Worker Assignment Protocol

**Status**: Architecture Specification (ADR)
**Owner**: 0102
**Slice**: `OC17_REAL_WORKER_ASSIGNMENT_PROTOCOL_DESIGN_PHASE1`
**WSP References**: WSP 11 (Interface Protocol), WSP 50 (Pre-Action Verification), WSP 77 (Agent Coordination), WSP 97 (Truth Boundaries)

---

## WSP 97 Truthfulness Statement

This document is an **architecture specification only**. No real worker processes are started.

| Claim | Status |
|-------|--------|
| AssignmentDispatcher interface defined | `SPECIFIED_SCAFFOLD_ONLY` |
| Worker registration | `SCAFFOLD_SIMULATED` |
| Worker deregistration | `SCAFFOLD_SIMULATED` |
| Assignment dispatch | `SCAFFOLD_NOT_IMPLEMENTED` |
| Heartbeat tracking | `SCAFFOLD_SIMULATED` |
| Completion reporting | `SCAFFOLD_SIMULATED` |
| Worker identity verification | `SCAFFOLD_SIMULATED` |
| Real process start | `NOT_IMPLEMENTED` |
| Real Claude/OpenClaw/Hermes invocation | `NOT_IMPLEMENTED` |
| CABR/payout/reward | `NOT_IMPLEMENTED` |

**Canonical Rule**: Worker assignment is simulated. No real workers are started.

---

## 1. Purpose

The Real Worker Assignment Protocol defines how SwarmWorkerQueue entries are dispatched to actual worker processes (OpenClaw, Hermes, 0102 agents) when the system transitions from simulation to real execution.

**Architecture Position**:
```
SwarmWorkerQueue.dequeue_for_worker()
    │
    ▼
AssignmentDispatcher.dispatch_assignment()
    │
    ├─> WorkerProcess registration
    │       │
    │       ├─> Identity verification
    │       ├─> Capability check
    │       └─> Trust level assignment
    │
    ├─> Assignment dispatch (SIMULATED)
    │       │
    │       ├─> Lease acquisition
    │       ├─> Heartbeat monitoring
    │       └─> Completion tracking
    │
    └─> Evidence collection
            │
            └─> SwarmCoordinator.complete_assignment()
```

**PoC Goal**: Define typed interfaces for worker assignment lifecycle.
**MVP Goal**: Real workers can register, receive assignments, and report completion.

---

## 2. Worker Process Model

### 2.1 Worker Types

| Type | Description | Capabilities |
|------|-------------|--------------|
| `OPENCLAW` | OpenClaw agent instance | validate, orchestrate |
| `HERMES` | Hermes FoundUp builder | build, extract |
| `CLAUDE_0102` | Claude agent (0102) | all |
| `QWEN` | Qwen local model | validate, triage |
| `GEMMA` | Gemma local model | validate, classify |

### 2.2 Worker Lifecycle

```
                    ┌──────────────┐
                    │  UNREGISTERED │
                    └──────┬───────┘
                           │ register_worker()
                           ▼
                    ┌──────────────┐
           ┌────────│   IDLE       │◄────────┐
           │        └──────┬───────┘         │
           │               │ dispatch()      │ complete()
           │               ▼                 │
           │        ┌──────────────┐         │
           │        │   ASSIGNED   │─────────┤
           │        └──────┬───────┘         │
           │               │ heartbeat()     │
           │               ▼                 │
           │        ┌──────────────┐         │
           │        │  PROCESSING  │─────────┘
           │        └──────┬───────┘
           │               │ timeout/error
           │               ▼
           │        ┌──────────────┐
           └────────│   FAILED     │
                    └──────┬───────┘
                           │ deregister()
                           ▼
                    ┌──────────────┐
                    │  TERMINATED  │
                    └──────────────┘
```

### 2.3 Trust Levels

| Level | Description | Allowed Actions |
|-------|-------------|-----------------|
| `UNTRUSTED` | New/unknown worker | Read-only operations |
| `VERIFIED` | Identity confirmed | Validation, analysis |
| `TRUSTED` | Track record established | Build, modify |
| `SYSTEM` | System-level worker | All operations |

---

## 3. Core Interfaces

### 3.1 AssignmentDispatcher

```python
class AssignmentDispatcher:
    """
    Dispatches SwarmWorkerQueue assignments to worker processes.
    
    WSP 97: All dispatch is simulated. No real processes are started.
    """
    
    def register_worker(
        self,
        registration: WorkerRegistration,
    ) -> WorkerProcess:
        """Register a worker process with capabilities."""
    
    def deregister_worker(
        self,
        worker_id: str,
    ) -> WorkerDeregistration:
        """Deregister a worker, releasing any assignments."""
    
    def dispatch_assignment(
        self,
        request: AssignmentDispatchRequest,
    ) -> AssignmentDispatchResult:
        """
        Dispatch an assignment to a registered worker.
        
        WSP 97: Returns SIMULATED_DISPATCH or SPECIFIED_NOT_IMPLEMENTED.
        Does NOT start a real process.
        """
    
    def receive_heartbeat(
        self,
        event: WorkerHeartbeatEvent,
    ) -> WorkerProcess:
        """Receive heartbeat from worker, update last_seen."""
    
    def receive_completion(
        self,
        event: WorkerCompletionEvent,
    ) -> AssignmentDispatchResult:
        """
        Receive completion report from worker.
        
        WSP 97: Cannot set real_execution_performed=True.
        """
    
    def list_workers(
        self,
        status: WorkerProcessStatus | None = None,
    ) -> list[WorkerProcess]:
        """List registered workers, optionally filtered by status."""
```

### 3.2 WorkerProcess

```python
@dataclass
class WorkerProcess:
    worker_id: str                    # Unique worker identifier
    runtime_type: WorkerRuntimeType   # OPENCLAW, HERMES, CLAUDE_0102, etc.
    capabilities: list[str]           # ["validate", "build", "test"]
    trust_level: WorkerTrustLevel     # UNTRUSTED, VERIFIED, TRUSTED, SYSTEM
    status: WorkerProcessStatus       # IDLE, ASSIGNED, PROCESSING, FAILED, TERMINATED
    
    registered_at: datetime
    last_seen_at: Optional[datetime]
    current_assignment_id: Optional[str]
    
    # Identity verification (simulated)
    identity_verified: bool = False
    identity_method: Optional[str] = None  # "api_key", "jwt", "mtls", etc.
    
    # WSP 97 Truth Fields
    simulated: bool = True            # Always True in scaffold
    # No real_execution_performed field exists
```

### 3.3 WorkerRegistration

```python
@dataclass
class WorkerRegistration:
    worker_id: str                    # Proposed worker ID
    runtime_type: WorkerRuntimeType   # Worker runtime type
    capabilities: list[str]           # Capabilities
    identity_claim: Optional[str]     # Identity claim (API key, JWT, etc.)
    requested_trust_level: WorkerTrustLevel  # Requested trust level
```

### 3.4 WorkerDeregistration

```python
@dataclass
class WorkerDeregistration:
    worker_id: str
    deregistered_at: datetime
    reason: str
    assignments_released: list[str]   # Assignment IDs released
    success: bool
```

### 3.5 AssignmentDispatchRequest

```python
@dataclass
class AssignmentDispatchRequest:
    assignment_id: str                # From StepAssignment
    entry_id: str                     # From SwarmWorkerQueueEntry
    worker_id: str                    # Target worker
    step_id: str                      # BuildStep ID
    step_action: BuildStepAction      # Action to perform
    owned_files: list[str]            # Files to work on
    timeout_seconds: int = 300        # Assignment timeout
```

### 3.6 AssignmentDispatchResult

```python
@dataclass
class AssignmentDispatchResult:
    success: bool
    dispatch_status: AssignmentDispatchStatus  # SIMULATED_DISPATCH, NOT_IMPLEMENTED, etc.
    assignment_id: str
    worker_id: str
    reason: str
    dispatched_at: Optional[datetime]
    
    # WSP 97 Truth Fields
    simulated: bool = True            # Always True in scaffold
    real_process_started: bool = False  # Always False in scaffold
```

### 3.7 WorkerHeartbeatEvent

```python
@dataclass
class WorkerHeartbeatEvent:
    worker_id: str
    assignment_id: Optional[str]
    heartbeat_at: datetime
    status: WorkerProcessStatus
    progress_percent: Optional[int]   # 0-100 if applicable
```

### 3.8 WorkerCompletionEvent

```python
@dataclass
class WorkerCompletionEvent:
    worker_id: str
    assignment_id: str
    completed_at: datetime
    success: bool
    evidence_refs: list[str]
    error_message: Optional[str]
    
    # WSP 97 Truth Fields
    simulated: bool = True            # Always True in scaffold
    # Cannot set real_execution_performed=True
```

---

## 4. Enums

### 4.1 WorkerProcessStatus

```python
class WorkerProcessStatus(str, Enum):
    IDLE = "idle"              # Registered, awaiting assignment
    ASSIGNED = "assigned"      # Assignment dispatched
    PROCESSING = "processing"  # Actively processing
    FAILED = "failed"          # Failed/error state
    TERMINATED = "terminated"  # Deregistered
```

### 4.2 WorkerRuntimeType

```python
class WorkerRuntimeType(str, Enum):
    OPENCLAW = "openclaw"      # OpenClaw agent
    HERMES = "hermes"          # Hermes builder
    CLAUDE_0102 = "claude_0102"  # Claude 0102 agent
    QWEN = "qwen"              # Qwen local model
    GEMMA = "gemma"            # Gemma local model
    GENERIC = "generic"        # Generic/unknown
```

### 4.3 AssignmentDispatchStatus

```python
class AssignmentDispatchStatus(str, Enum):
    SIMULATED_DISPATCH = "simulated_dispatch"   # Dispatch simulated
    SPECIFIED_NOT_IMPLEMENTED = "specified_not_implemented"  # Interface only
    WORKER_NOT_FOUND = "worker_not_found"
    WORKER_BUSY = "worker_busy"
    CAPABILITY_MISMATCH = "capability_mismatch"
    DISPATCH_FAILED = "dispatch_failed"
```

### 4.4 WorkerTrustLevel

```python
class WorkerTrustLevel(str, Enum):
    UNTRUSTED = "untrusted"    # New/unknown
    VERIFIED = "verified"      # Identity confirmed
    TRUSTED = "trusted"        # Track record
    SYSTEM = "system"          # System-level
```

---

## 5. Dispatch Protocol

### 5.1 Polling Model (Phase 1)

Workers poll for assignments:

```
Worker                          AssignmentDispatcher
   │                                    │
   │──── register_worker() ────────────>│
   │<─── WorkerProcess (IDLE) ──────────│
   │                                    │
   │──── poll for assignment ──────────>│ (via SwarmWorkerQueue)
   │<─── AssignmentDispatchRequest ─────│
   │                                    │
   │──── heartbeat() ──────────────────>│
   │<─── WorkerProcess (PROCESSING) ────│
   │                                    │
   │──── complete() ───────────────────>│
   │<─── AssignmentDispatchResult ──────│
   │                                    │
```

### 5.2 Push Model (Future)

Dispatcher pushes assignments to workers:

```
AssignmentDispatcher            Worker
   │                               │
   │──── dispatch_assignment() ───>│
   │<─── ACK ──────────────────────│
   │                               │
   │<─── heartbeat() ──────────────│
   │──── ACK ─────────────────────>│
   │                               │
   │<─── complete() ───────────────│
   │──── AssignmentDispatchResult ─│
   │                               │
```

### 5.3 Heartbeat Protocol

| Parameter | Default | Description |
|-----------|---------|-------------|
| Heartbeat Interval | 30s | Worker sends heartbeat |
| Heartbeat Timeout | 90s | Missed heartbeats = failure |
| Max Missed | 3 | Consecutive misses before failure |

---

## 6. Identity Verification

### 6.1 Verification Methods (Simulated)

| Method | Description | Trust Level |
|--------|-------------|-------------|
| `api_key` | API key validation | VERIFIED |
| `jwt` | JWT token validation | VERIFIED |
| `mtls` | Mutual TLS certificate | TRUSTED |
| `internal` | Internal system process | SYSTEM |
| `none` | No verification | UNTRUSTED |

### 6.2 Verification Flow

```python
# Simulated verification (scaffold only)
def verify_worker_identity(registration: WorkerRegistration) -> bool:
    """
    Verify worker identity claim.
    
    WSP 97: Always returns True in scaffold.
    Real verification NOT IMPLEMENTED.
    """
    return True  # Simulated
```

---

## 7. Failure Handling

### 7.1 Failure Types

| Failure | Response |
|---------|----------|
| Worker timeout | Release assignment, mark failed |
| Heartbeat miss | Warning → retry → failure |
| Completion error | Record error, mark failed |
| Worker crash | Detect via heartbeat, requeue |

### 7.2 Retry Semantics

| Parameter | Default | Description |
|-----------|---------|-------------|
| Max Retries | 3 | Per assignment |
| Retry Delay | 30s | Before retry |
| Backoff Multiplier | 2.0 | Exponential backoff |

---

## 8. Audit Trail

### 8.1 Events Recorded

| Event | Data |
|-------|------|
| `worker_registered` | worker_id, runtime_type, capabilities |
| `worker_deregistered` | worker_id, reason |
| `assignment_dispatched` | assignment_id, worker_id, step_id |
| `heartbeat_received` | worker_id, assignment_id, progress |
| `completion_received` | assignment_id, success, evidence_refs |
| `worker_failed` | worker_id, reason |

### 8.2 Evidence Chain

```
WorkerCompletionEvent.evidence_refs
    │
    ▼
AssignmentDispatchResult (recorded)
    │
    ▼
SwarmWorkerQueueEntry.evidence_refs
    │
    ▼
StepAssignment.evidence_refs
    │
    ▼
EvidenceBundle (aggregated)
```

---

## 9. Security Boundaries

### 9.1 Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Worker → Dispatcher | Worker must register with valid identity |
| Dispatcher → Queue | Dispatcher validates assignment ownership |
| Assignment → Files | File access limited to owned_files |

### 9.2 No Raw Chat Execution

**Critical**: Workers receive typed `AssignmentDispatchRequest`, NOT raw chat.

```python
# CORRECT
request = AssignmentDispatchRequest(
    assignment_id="a_001",
    step_action=BuildStepAction.VALIDATE_GENESIS,
    owned_files=["modules/foundups/voteballots/README.md"],
)

# FORBIDDEN - No raw chat
# request.raw_instruction = "Please validate the genesis..."
```

---

## 10. WSP 97 Truth Boundaries

This scaffold enforces the following truth fields:

| Field | Value | Location |
|-------|-------|----------|
| `WorkerProcess.simulated` | True | Always |
| `AssignmentDispatchResult.simulated` | True | Always |
| `AssignmentDispatchResult.real_process_started` | False | Always |
| `WorkerCompletionEvent.simulated` | True | Always |
| `real_execution_performed` | N/A | Field does not exist |
| `cabr_ready` | N/A | Field does not exist |
| `payout_ready` | N/A | Field does not exist |

**No CABR/reward/payout/token fields exist in this contract.**

---

## 11. Integration Points

### 11.1 SwarmWorkerQueue Integration

```python
# Queue entry dequeued
entry = queue.dequeue_for_worker(request)

# Create dispatch request
dispatch_request = AssignmentDispatchRequest(
    assignment_id=entry.assignment_id,
    entry_id=entry.entry_id,
    worker_id=entry.worker_id,
    step_id=entry.step_id,
    step_action=entry.step_action,
    owned_files=entry.owned_files,
)

# Dispatch (simulated)
result = dispatcher.dispatch_assignment(dispatch_request)

# Result is SIMULATED_DISPATCH (no real process)
assert result.dispatch_status == AssignmentDispatchStatus.SIMULATED_DISPATCH
assert result.real_process_started is False
```

### 11.2 BuildPlanExecutor Integration

```python
# Worker completes, reports back
completion = WorkerCompletionEvent(
    worker_id="hermes_001",
    assignment_id="a_001",
    success=True,
    evidence_refs=["evidence/step1/validated"],
)

# Dispatcher receives completion
result = dispatcher.receive_completion(completion)

# Flow to SwarmCoordinator
coordinator.complete_assignment(
    completion.assignment_id,
    completion.evidence_refs,
)
```

---

## 12. Example (SPEC_EXAMPLE_NOT_EXECUTED)

```python
# Full worker assignment lifecycle (simulated)

from modules.foundups.agent.src.worker_assignment_protocol import (
    AssignmentDispatcher, WorkerRegistration, WorkerRuntimeType,
    WorkerTrustLevel, AssignmentDispatchRequest, WorkerHeartbeatEvent,
    WorkerCompletionEvent, AssignmentDispatchStatus
)
from modules.foundups.agent.src.build_plan import BuildStepAction

# Create dispatcher
dispatcher = AssignmentDispatcher()

# Register worker
registration = WorkerRegistration(
    worker_id="hermes_vb_001",
    runtime_type=WorkerRuntimeType.HERMES,
    capabilities=["build", "extract"],
    identity_claim="api_key_hermes_001",
    requested_trust_level=WorkerTrustLevel.VERIFIED,
)
worker = dispatcher.register_worker(registration)
assert worker.status == WorkerProcessStatus.IDLE
assert worker.simulated is True

# Dispatch assignment (simulated)
request = AssignmentDispatchRequest(
    assignment_id="a_vb_001",
    entry_id="qe_vb_001",
    worker_id="hermes_vb_001",
    step_id="step_create_module",
    step_action=BuildStepAction.CREATE_MODULE,
    owned_files=["modules/foundups/voteballots/src/"],
)
result = dispatcher.dispatch_assignment(request)
assert result.dispatch_status == AssignmentDispatchStatus.SIMULATED_DISPATCH
assert result.real_process_started is False

# Heartbeat
heartbeat = WorkerHeartbeatEvent(
    worker_id="hermes_vb_001",
    assignment_id="a_vb_001",
    heartbeat_at=datetime.now(timezone.utc),
    status=WorkerProcessStatus.PROCESSING,
    progress_percent=50,
)
worker = dispatcher.receive_heartbeat(heartbeat)
assert worker.status == WorkerProcessStatus.PROCESSING

# Completion
completion = WorkerCompletionEvent(
    worker_id="hermes_vb_001",
    assignment_id="a_vb_001",
    completed_at=datetime.now(timezone.utc),
    success=True,
    evidence_refs=["evidence/voteballots/module_created"],
)
result = dispatcher.receive_completion(completion)
assert result.success is True
assert result.simulated is True
```

**NOTE**: This example is specification only. No real execution occurs.

---

## 13. Future Extensions (Out of Scope)

The following are explicitly out of scope for OC17:

- Real process start (subprocess, API call)
- Real Claude/OpenClaw/Hermes invocation
- Real identity verification (cryptographic)
- Cross-machine worker coordination
- Worker health monitoring daemon
- RedDog/pfMALL UI integration
- CABR/rewards/payouts

These will be addressed in future OC slices.
