# INTERFACE - PQN Swarm Hub FoundUp

## Control-Plane Boundary

Canonical split:
- `OpenClaw (0102)` = conversational research control plane
- `pqn_swarm_hub` = work registry, verification, contribution measurement
- `pqn_alignment` = detector-first execution engine
- `pqn_mcp` = gated external/tool surface
- `pqn_portal` = public demo/gallery
- `moltbook_distribution_adapter` = downstream distribution

This module is the FoundUp-level registry and verification layer.
It does NOT own the detector engine or the social distribution layer.

---

## PoC Contracts

### PQNWorkUnit

Bounded research task registration.

```python
@dataclass
class PQNWorkUnit:
    work_unit_id: str          # Deterministic ID
    description: str           # Human-readable description
    config: Dict[str, Any]     # CMST detector config (steps, dt, seed, etc.)
    creator_id: str            # Agent/user who created this work unit
    status: WorkUnitStatus     # pending, in_progress, completed, cancelled
    source: str                # Origin: "internal" (detector) or "external"
    created_at: datetime
    updated_at: datetime
```

### rESPSubmission

Structured rESP result intake.

```python
@dataclass
class rESPSubmission:
    submission_id: str         # Deterministic ID
    work_unit_id: str          # Reference to parent work unit
    submitter_id: str          # Agent/user who submitted
    metrics: Dict[str, Any]    # {coherence, pqn_rate, paradox_rate, resonance_hz}
    artifacts: List[str]       # Paths or URIs to result artifacts
    status: SubmissionStatus   # pending_verification, accepted, rejected
    source: str                # Origin: "internal" (detector) or "external"
    submitted_at: datetime
```

### VerificationDecision

Accept/reject outcome.

```python
@dataclass
class VerificationDecision:
    decision_id: str           # Deterministic ID
    submission_id: str         # Reference to submission
    decision: Literal["accept", "reject"]
    verifier_id: str           # Agent/user who made decision
    rationale: str             # Why accepted/rejected
    decided_at: datetime
```

### ContributionRecord

ROC-style contribution output.

```python
@dataclass
class ContributionRecord:
    contribution_id: str       # Deterministic ID
    work_unit_id: str          # Reference to work unit
    submission_id: str         # Reference to submission
    decision_id: str           # Reference to verification decision
    contributor_id: str        # Who earned the contribution
    score: float               # 0.0-1.0 contribution score
    recorded_at: datetime
```

---

## Public API Functions

### Work Unit Registry

- `register(description, config, creator_id, source="internal") -> PQNWorkUnit`
- `register_external(description, config, creator_id) -> PQNWorkUnit` - Convenience for source="external"
- `get(work_unit_id) -> PQNWorkUnit` - Raises WorkUnitNotFoundError
- `list(status_filter, limit) -> List[PQNWorkUnit]`
- `transition(work_unit_id, new_status) -> PQNWorkUnit`

### rESP Submission Sink

- `submit(work_unit_id, submitter_id, metrics, artifacts, source="internal") -> rESPSubmission`
- `submit_external(work_unit_id, submitter_id, metrics, artifacts) -> rESPSubmission` - Convenience for source="external"
- `submit_from_detector(work_unit_id, bridge_result, submitter_id) -> rESPSubmission` - Phase 1 detector integration
- `get(submission_id) -> Optional[rESPSubmission]`
- `list(work_unit_id, status_filter, limit) -> List[rESPSubmission]`
- `update_status(submission_id, new_status) -> rESPSubmission`

### Detector Bridge (Phase 1)

- `DetectorBridge.run(work_unit) -> Dict[str, Any]` - calls pqn_alignment.run_detector() and parses artifacts

### Verification

- `verify_submission(submission_id, decision, verifier_id, rationale) -> VerificationDecision`
- `get_decision(decision_id) -> Optional[VerificationDecision]`
- `list_decisions(submission_id) -> List[VerificationDecision]`

### Contribution Reporting

- `record_contribution(work_unit_id, submission_id, decision_id, contributor_id, score) -> ContributionRecord`
- `get_contribution(contribution_id) -> Optional[ContributionRecord]`
- `list_contributions(contributor_id, limit) -> List[ContributionRecord]`
- `get_contributor_stats(contributor_id) -> Dict[str, Any]`

---

## Integration Points

### Detector Engine via DetectorBridge (Phase 1)

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    DetectorBridge,
)

# Setup
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
bridge = DetectorBridge()

# Register work unit
work_unit = registry.register(
    description="7.05Hz resonance sweep",
    config={"script": "^^^&&&", "steps": 1200, "dt": 0.071},
    creator_id="agent_x",
)

# Run detector via bridge (calls pqn_alignment.run_detector internally)
bridge_result = bridge.run(work_unit)
# Returns: {events_path, metrics_csv, metrics: {coherence, pqn_rate, ...}, steps, raw_config}

# Submit from detector output
submission = sink.submit_from_detector(
    work_unit_id=work_unit.work_unit_id,
    bridge_result=bridge_result,
    submitter_id="agent_x",
)
```

### Raw Detector (without bridge)

```python
from modules.ai_intelligence.pqn_alignment import run_detector

# Direct detector call returns (events_path, metrics_csv) tuple
events_path, metrics_csv = run_detector(work_unit.config)
# Must parse artifacts manually to extract metrics
```

### External Submission (Phase 2)

For externally-sourced rESP-style results (non-detector):

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
)

# Setup services
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine)

# 1. Register external work unit
work_unit = registry.register_external(
    description="External GPD result",
    config={
        "tool": "gpd",
        "version": "2.0",
        "parameters": {"sweep_range": [6.5, 7.5]},
    },
    creator_id="external_contributor_001",
)
# work_unit.source == "external"

# 2. Submit external results
submission = sink.submit_external(
    work_unit_id=work_unit.work_unit_id,
    submitter_id="external_contributor_001",
    metrics={
        "coherence": 0.75,
        "pqn_rate": 0.08,
        "custom_metric": 42,
    },
    artifacts=["external/gpd_output.json"],
)
# submission.source == "external"

# 3. Verify (same as internal)
decision = engine.auto_verify(submission.submission_id)

# 4. Record contribution (same as internal)
if decision.decision == "accept":
    contribution = reporter.record(
        work_unit_id=work_unit.work_unit_id,
        submission_id=submission.submission_id,
        decision_id=decision.decision_id,
        contributor_id="external_contributor_001",
        score=0.82,
    )
```

### Downstream Distribution (moltbook_distribution_adapter)

```python
from modules.communication.moltbot_bridge.src.moltbook_distribution_adapter import (
    get_moltbook_adapter,
)

# Publish verified contribution to MoltBook
adapter = get_moltbook_adapter()
adapter.publish_research(
    research_id=contribution.contribution_id,
    topic=f"PQN Work Unit {work_unit.work_unit_id}",
    content=f"Contribution score: {contribution.score}",
    metadata={"metrics": submission.metrics},
)
```

---

## Deterministic ID Generation

All IDs are deterministic for idempotency:

```python
def generate_id(entity_type: str, *args: str) -> str:
    seed = f"{entity_type}:{':'.join(args)}"
    return hashlib.sha256(seed.encode()).hexdigest()[:16]
```

---

## Error Handling

### WorkUnitNotFoundError
- Raised when work_unit_id does not exist

### SubmissionNotFoundError
- Raised when submission_id does not exist

### InvalidStatusTransitionError
- Raised when attempting invalid status transition

### DuplicateSubmissionError
- Raised when submitting duplicate result (idempotent - returns existing)

### FAMAdapterError
- Raised when FAM adapter operation fails

---

## Phase 1 Contracts (New)

### ParticipantIdentity

Gate entry identity metadata.

```python
@dataclass
class ParticipantIdentity:
    participant_id: str         # Deterministic ID
    display_name: str           # Human-readable name
    model_type: str             # e.g., "claude-opus-4-5", "qwen-1.5b", "human"
    compute_capacity: str       # "high", "medium", "low"
    capability_tags: List[str]  # ["physics", "verification", ...]
    metadata: Dict[str, Any]    # Additional context
    registered_at: datetime
```

### GateDecision

Gate entry decision record.

```python
@dataclass
class GateDecision:
    decision_id: str            # Deterministic ID
    participant_id: str         # Reference to participant
    decision: str               # "approve" | "reject" | "suspend"
    tier: ParticipantTier       # Assigned tier level
    reason: str                 # Rationale
    decider_id: str             # "auto" | verifier ID
    decided_at: datetime
```

### ParticipantTier (Enum)

Per WSP 15 scoring:
- `OBSERVER`: Can view, no submit
- `CONTRIBUTOR`: Can submit rESP
- `VERIFIER`: Can verify submissions
- `COORDINATOR`: Can create work units

---

## Phase 1 API Functions (New)

### Participant Gate

- `ParticipantGate.request_entry(identity, requested_tier) -> GateDecision`
- `ParticipantGate.check_permission(participant_id, required_tier) -> bool`
- `ParticipantGate.get_participant(participant_id) -> Optional[ParticipantIdentity]`
- `ParticipantGate.get_status(participant_id) -> Optional[ParticipantStatus]`
- `ParticipantGate.get_tier(participant_id) -> Optional[ParticipantTier]`
- `ParticipantGate.list_approved(tier_filter) -> List[ParticipantIdentity]`
- `ParticipantGate.suspend(participant_id, reason, actor_id) -> GateDecision`
- `ParticipantGate.reinstate(participant_id, reason, actor_id) -> GateDecision`
- `ParticipantGate.register_capability_hook(hook) -> None`
- `ParticipantGate.register_wsp00_hook(hook) -> None`

### FAM Adapter

- `FAMAdapter.connect() -> bool`
- `FAMAdapter.emit_contribution_event(contribution, actor_id) -> Tuple[bool, str]`
- `FAMAdapter.emit_verification_event(decision, work_unit_id, actor_id) -> Tuple[bool, str]`
- `FAMAdapter.get_status() -> Dict[str, Any]`
- `FAMAdapter.is_connected -> bool`
- `get_fam_adapter(auto_connect) -> FAMAdapter` (singleton)

---

## Phase 1 Integration Points (New)

### Participant Gate Usage

```python
from modules.foundups.pqn_swarm_hub import (
    ParticipantGate,
    ParticipantIdentity,
    ParticipantTier,
)

# Setup gate
gate = ParticipantGate(
    default_tier=ParticipantTier.CONTRIBUTOR,
    require_capability_check=False,  # Phase 1: internal-first
    require_wsp00_check=False,
)

# Request entry
identity = ParticipantIdentity(
    display_name="researcher_x",
    model_type="claude-opus-4-5",
    compute_capacity="high",
    capability_tags=["physics", "rESP"],
)

decision = gate.request_entry(identity)
# Phase 1: Auto-approves internal participants

# Check permission before work unit creation
if gate.check_permission(identity.participant_id, ParticipantTier.COORDINATOR):
    work_unit = registry.register(...)
```

### FAM Adapter Usage

```python
from modules.foundups.pqn_swarm_hub import get_fam_adapter

# Get adapter (lazy connection)
adapter = get_fam_adapter(auto_connect=True)

# Emit contribution event to FAMDaemon
success, msg = adapter.emit_contribution_event(
    contribution=contribution_record,
    actor_id="pqn_swarm_hub",
)

# Check status
status = adapter.get_status()
# {"connected": True/False, "daemon_running": True/False, ...}
```

---

## Adapter Boundary (HARD)

Per WSP 97 directive:

**ALLOWED**:
- `emit_contribution_event(ContributionRecord)`
- `emit_verification_event(VerificationDecision, work_unit_id)`

**NOT ALLOWED**:
- Direct mutation of FAM event store
- Direct access to core control-plane modules
- Importing FAM internals beyond `get_fam_daemon`

Adapter falls back to stub mode if FAMDaemon unavailable.

---

## Phase 1 Persistence (New)

### SQLiteStore

Thread-safe SQLite persistence for all contracts.

```python
from modules.foundups.pqn_swarm_hub import (
    SQLiteStore,
    get_sqlite_store,
    reset_sqlite_store,
)

# Get singleton store (creates db in data/pqn_swarm_hub/swarm.db)
store = get_sqlite_store()

# Or create custom store
store = SQLiteStore(
    db_dir=Path("custom/path"),
    db_filename="custom.db",
)
```

### Service Integration with Persistence

All services accept optional `store` parameter for persistence:

```python
from modules.foundups.pqn_swarm_hub import (
    get_sqlite_store,
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    ParticipantGate,
)

# Get shared store
store = get_sqlite_store()

# Wire services with persistence
registry = WorkUnitRegistry(store=store)
sink = SubmissionSink(registry, store=store)
engine = VerificationEngine(sink, store=store)
reporter = ContributionReporter(engine, store=store)
gate = ParticipantGate(store=store)

# All operations now persist to SQLite
wu = registry.register("Work unit", {}, "agent_x")
# Survives restart - can retrieve with new service instances
```

### Backward Compatibility

Omit `store` parameter for in-memory only (Phase 0 behavior):

```python
registry = WorkUnitRegistry()  # In-memory only
sink = SubmissionSink(registry)  # In-memory only
```

### Store Stats

```python
stats = store.get_stats()
# {"work_units": N, "submissions": N, "verification_decisions": N, ...}
```

---

## Phase 1 Publication Adapter (New)

### PublicationResult

Result of a publication attempt.

```python
@dataclass
class PublicationResult:
    success: bool               # Whether publication succeeded
    post_id: Optional[str]      # MoltBook post ID if published
    channel: Optional[str]      # "pqn_research", "stub", etc.
    status: str                 # "published", "failed", "rejected_decision", "stub"
    message: str                # Human-readable result message
    timestamp: datetime         # When publication was attempted
    duplicate: bool             # True if already published (idempotent)
```

### Publication Adapter API

- `PublicationAdapter.connect() -> bool` - Connect to MoltBook (returns False if unavailable)
- `PublicationAdapter.publish(work_unit, submission, decision, contribution, actor_id) -> PublicationResult`
- `PublicationAdapter.is_connected -> bool` - Check connection status
- `PublicationAdapter.get_stub_publications() -> List[Dict]` - Get stub publications for later sync
- `PublicationAdapter.clear_stub_publications() -> int` - Clear stubs after sync
- `PublicationAdapter.get_status() -> Dict[str, Any]` - Adapter status
- `get_publication_adapter(auto_connect) -> PublicationAdapter` - Singleton

### Publication Adapter Usage

```python
from modules.foundups.pqn_swarm_hub import (
    get_publication_adapter,
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
)

# Setup services
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine)

# Execute flow
work_unit = registry.register("7.05Hz sweep", {"steps": 1200}, "agent_x")
submission = sink.submit(work_unit.work_unit_id, "agent_x", {"coherence": 0.85})
decision = engine.manual_verify(submission.submission_id, "accept", "auto", "Meets φ-floor")
contribution = reporter.record(
    work_unit.work_unit_id,
    submission.submission_id,
    decision.decision_id,
    "agent_x",
    0.95,
)

# Publish to MoltBook
adapter = get_publication_adapter(auto_connect=True)
result = adapter.publish(
    work_unit=work_unit,
    submission=submission,
    decision=decision,
    contribution=contribution,
    actor_id="pqn_swarm_hub",
)

if result.success:
    print(f"Published: {result.post_id}")
else:
    print(f"Failed: {result.message}")
```

### Publication Gate: Only Accepted Decisions

```python
# Rejected decisions do NOT publish
reject_decision = engine.manual_verify(sub_id, "reject", "auto", "Below threshold")
result = adapter.publish(work_unit, submission, reject_decision, contribution)

assert result.success is False
assert result.status == "rejected_decision"
# MoltBook NOT called
```

### Stub Fallback (MoltBook Unavailable)

```python
# If MoltBook unavailable, adapter records locally
adapter = get_publication_adapter()  # Not connected

result = adapter.publish(work_unit, submission, decision, contribution)
assert result.success is True  # Stub succeeds
assert result.status == "stub"
assert result.channel == "stub"

# Retrieve stubs for later sync
stubs = adapter.get_stub_publications()
# [{"payload": {...}, "actor_id": "...", "timestamp": "..."}]

# Clear after syncing
adapter.clear_stub_publications()
```
