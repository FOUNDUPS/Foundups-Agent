# BuildPlan Swarm Coordination Contract

**Status**: Architecture Specification (ADR)
**Owner**: 0102
**Slice**: `OC13_SWARM_COORDINATION_CONTRACT_AND_TEST_PHASE1`
**WSP References**: WSP 11 (Interface Protocol), WSP 50 (Pre-Action Verification), WSP 77 (Agent Coordination), WSP 97 (Truth Boundaries)

---

## WSP 97 Truthfulness Statement

This document is an **architecture specification only**. No real parallel execution is implemented.

| Claim | Status |
|-------|--------|
| SwarmCoordinator interface defined | `SPECIFIED_SCAFFOLD_ONLY` |
| Worker registration | `SCAFFOLD_SIMULATED` |
| Step assignment | `SCAFFOLD_SIMULATED` |
| File ownership claims | `SCAFFOLD_SIMULATED` |
| Lease expiration | `SCAFFOLD_SIMULATED` |
| Conflict detection | `SCAFFOLD_SIMULATED` |
| Evidence aggregation | `SCAFFOLD_SIMULATED` |
| Real parallel worker execution | `NOT_IMPLEMENTED` |
| CABR/payout/reward | `NOT_IMPLEMENTED` |

**Canonical Rule**: Swarm coordination is simulated. No real agents are started.

---

## 1. Purpose

The BuildPlan Swarm Coordination Contract defines how multiple OpenClaw/Hermes/worker agents can safely claim bounded BuildSteps without conflicts.

**Architecture Position**:
```
BuildPlan (from FoundUpJob)
    │
    ▼
SwarmCoordinator
    │
    ├── Worker Registration
    ├── Step Assignment
    ├── File Ownership Claims
    ├── Lease Management
    ├── Conflict Detection
    └── Evidence Aggregation
```

**PoC Goal**: One OpenClaw can simulate a BuildPlan.
**MVP Goal**: Many OpenClaw/Hermes/worker agents can claim bounded BuildSteps safely.

---

## 2. Core Interfaces

### 2.1 SwarmCoordinator

```python
class SwarmCoordinator:
    """Multi-agent step assignment and file ownership coordination."""
    
    def register_worker(self, worker: WorkerIdentity) -> None:
        """Register a worker in the swarm."""
    
    def assign_step(
        self,
        step: BuildStep,
        worker_id: str,
        owned_files: list[str],
    ) -> StepAssignment:
        """Assign a step to a worker with file ownership."""
    
    def claim_files(
        self,
        worker_id: str,
        files: list[str],
        step_id: str,
    ) -> list[FileOwnershipClaim]:
        """Claim file ownership for a step."""
    
    def release_files(
        self,
        worker_id: str,
        files: list[str],
    ) -> None:
        """Release file ownership."""
    
    def detect_conflicts(self) -> list[ConflictReport]:
        """Detect file ownership conflicts."""
    
    def renew_lease(self, lease_id: str) -> Lease:
        """Renew a worker's lease."""
    
    def expire_leases(self, now: datetime) -> list[str]:
        """Expire stale leases and release their claims."""
    
    def aggregate_evidence(self) -> EvidenceBundle:
        """Aggregate evidence from all assignments."""
    
    def summarize(self) -> SwarmExecutionSummary:
        """Summarize swarm execution state."""
```

### 2.2 WorkerIdentity

```python
@dataclass
class WorkerIdentity:
    worker_id: str              # Unique worker identifier
    worker_type: str            # "openclaw" | "hermes" | "0102"
    capabilities: list[str]     # ["validate", "build", "test"]
    registered_at: datetime
    lease: Optional[Lease]
```

### 2.3 StepAssignment

```python
@dataclass
class StepAssignment:
    assignment_id: str
    step_id: str
    worker_id: str
    owned_files: list[str]
    status: AssignmentStatus    # ASSIGNED | IN_PROGRESS | COMPLETED | FAILED
    assigned_at: datetime
    completed_at: Optional[datetime]
    evidence_refs: list[str]
    simulated: bool = True      # WSP 97: Always True in scaffold
```

### 2.4 FileOwnershipClaim

```python
@dataclass
class FileOwnershipClaim:
    claim_id: str
    file_path: str
    worker_id: str
    step_id: str
    claimed_at: datetime
    expires_at: datetime        # Lease expiration
    released: bool = False
```

### 2.5 Lease

```python
@dataclass
class Lease:
    lease_id: str
    worker_id: str
    issued_at: datetime
    expires_at: datetime
    status: LeaseStatus         # ACTIVE | EXPIRED | RELEASED
    renewal_count: int = 0
```

### 2.6 ConflictReport

```python
@dataclass
class ConflictReport:
    conflict_id: str
    file_path: str
    claimants: list[str]        # Worker IDs claiming same file
    severity: ConflictSeverity  # WARNING | ERROR | FATAL
    detected_at: datetime
    resolution: Optional[str]
```

### 2.7 EvidenceBundle

```python
@dataclass
class EvidenceBundle:
    bundle_id: str
    plan_id: str
    total_assignments: int
    completed_assignments: int
    evidence_refs: list[str]    # Aggregated from all assignments
    aggregated_at: datetime
    # WSP 97: No pAVS/CABR finality claims
    verification_complete: bool = False
    cabr_ready: bool = False
```

### 2.8 SwarmExecutionSummary

```python
@dataclass
class SwarmExecutionSummary:
    plan_id: str
    total_workers: int
    total_assignments: int
    completed_assignments: int
    failed_assignments: int
    active_conflicts: int
    all_simulated: bool = True              # WSP 97: Always True
    build_complete: bool                    # Only True if all assignments simulated-complete
    real_execution_performed: bool = False  # WSP 97: Always False
```

---

## 3. Coordination Rules

### 3.1 File Ownership Rules

| Rule | Description |
|------|-------------|
| R1 | Two workers cannot own the same file at the same time |
| R2 | A worker cannot claim files outside the BuildPlan target scope |
| R3 | Lease expiration releases file claims |
| R4 | Released files can be re-claimed by another worker |

### 3.2 Assignment Rules

| Rule | Description |
|------|-------------|
| R5 | Assignments are simulated only (no real file edits) |
| R6 | No worker actually edits files |
| R7 | No real agent process starts |
| R8 | Evidence aggregation records refs only; no pAVS/CABR finality |

### 3.3 Summary Rules

| Rule | Description |
|------|-------------|
| R9 | `build_complete` can only be True if all assignments are simulated-complete |
| R10 | `real_execution_performed` is always False |

---

## 4. Lease Lifecycle

```
Worker Registration
    │
    ▼
Lease Issued (ACTIVE)
    │
    ├─> renew_lease() ─> Reset expires_at
    │
    ├─> expire_leases() ─> Status = EXPIRED, release claims
    │
    └─> Worker completes ─> Status = RELEASED
```

**Lease Duration**: Default 300 seconds (configurable).
**Renewal**: Extends lease by default duration, increments renewal_count.
**Expiration**: Releases all file claims held by the worker.

---

## 5. Conflict Detection

### 5.1 Conflict Severity Levels

| Severity | Trigger | Action |
|----------|---------|--------|
| WARNING | Same file claimed by 2 workers, different steps | Log, allow override |
| ERROR | Same file claimed by 2 workers, same step | Block second claim |
| FATAL | File outside target scope | Block claim entirely |

### 5.2 Conflict Resolution

- **Automatic**: First claimant wins for same-step conflicts.
- **Manual**: Cross-step conflicts logged for human review.
- **Scope Violation**: Rejected immediately.

---

## 6. Evidence Aggregation

Evidence is collected from all completed assignments and bundled for summary.

```python
bundle = coordinator.aggregate_evidence()

# bundle.evidence_refs contains all refs from all assignments
# bundle.verification_complete = False (WSP 97)
# bundle.cabr_ready = False (WSP 97)
```

**No pAVS/CABR finality**: Evidence bundle records refs only. Final verification and payout are out of scope for this scaffold.

---

## 7. Step Dependency Handling

Steps with dependencies are assigned in topological order.

```
Step 1: VALIDATE_GENESIS (no dependencies)
    │
    ▼
Step 2: VALIDATE_MANIFEST (depends on Step 1)
    │
    ▼
Step 3: CREATE_MODULE (depends on Step 2)
```

A worker cannot be assigned a step until all dependencies are completed (simulated).

---

## 8. Integration with BuildPlanExecutor

```python
# Swarm coordinates, Executor simulates
coordinator = SwarmCoordinator(plan=plan)
executor = BuildPlanExecutor(dry_run=True)

for step in plan.steps:
    assignment = coordinator.assign_step(step, worker_id, files)
    result = executor.simulate_step(plan, step)
    coordinator.complete_assignment(assignment.assignment_id, result.evidence_refs)

summary = coordinator.summarize()
# summary.build_complete = True only if all simulated-complete
# summary.real_execution_performed = False (always)
```

---

## 9. WSP 97 Truth Boundaries

This scaffold enforces the following truth fields:

| Field | Value | Location |
|-------|-------|----------|
| `StepAssignment.simulated` | True | Always |
| `EvidenceBundle.verification_complete` | False | Always |
| `EvidenceBundle.cabr_ready` | False | Always |
| `SwarmExecutionSummary.all_simulated` | True | Always |
| `SwarmExecutionSummary.real_execution_performed` | False | Always |

**No CABR/reward/payout/token fields exist in this contract.**

---

## 10. VoteBallot Example (SPEC_EXAMPLE_NOT_EXECUTED)

```python
# VoteBallot BuildPlan split into multiple simulated assignments

job = create_job(
    tenant_id="foundups",
    requested_action="build_foundup",
    foundup_id="voteballots",
)
plan = create_build_plan_from_job(job)

# Create swarm with 3 workers
coordinator = SwarmCoordinator(plan=plan)
coordinator.register_worker(WorkerIdentity(
    worker_id="worker_001",
    worker_type="openclaw",
    capabilities=["validate"],
))
coordinator.register_worker(WorkerIdentity(
    worker_id="worker_002",
    worker_type="hermes",
    capabilities=["build", "test"],
))
coordinator.register_worker(WorkerIdentity(
    worker_id="worker_003",
    worker_type="0102",
    capabilities=["validate", "build", "test"],
))

# Assign steps to workers
assignment_1 = coordinator.assign_step(
    plan.steps[0],
    "worker_001",
    ["modules/foundups/voteballots/README.md"],
)
assignment_2 = coordinator.assign_step(
    plan.steps[1],
    "worker_002",
    ["modules/foundups/voteballots/src/"],
)

# Simulate execution
executor = BuildPlanExecutor(dry_run=True)
for step in plan.steps:
    result = executor.simulate_step(plan, step)
    # Record evidence

summary = coordinator.summarize()
# summary.total_workers = 3
# summary.build_complete = True (all simulated-complete)
# summary.real_execution_performed = False (WSP 97)
```

**NOTE**: This example is specification only. No real execution occurs.

---

## 11. Future Extensions (Out of Scope)

The following are explicitly out of scope for OC13:

- Real parallel worker execution
- Starting actual agent processes
- RedDog/pfMALL UI integration
- CABR/rewards/payouts
- pAVS verification finality
- Cross-machine coordination

These will be addressed in future OC slices.
