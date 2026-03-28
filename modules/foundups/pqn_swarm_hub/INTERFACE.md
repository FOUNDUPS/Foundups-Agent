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

- `register_work_unit(description, config, creator_id) -> PQNWorkUnit`
- `get_work_unit(work_unit_id) -> Optional[PQNWorkUnit]`
- `list_work_units(status_filter, limit) -> List[PQNWorkUnit]`
- `cancel_work_unit(work_unit_id, actor_id) -> bool`

### rESP Submission Sink

- `submit_resp(work_unit_id, submitter_id, metrics, artifacts) -> rESPSubmission`
- `get_submission(submission_id) -> Optional[rESPSubmission]`
- `list_submissions(work_unit_id, status_filter, limit) -> List[rESPSubmission]`

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

### Detector Engine (pqn_alignment)

```python
from modules.ai_intelligence.pqn_alignment import run_detector

# Execute detector for a work unit
result = run_detector({
    "script": work_unit.config.get("script", "^^^&&&"),
    "steps": work_unit.config.get("steps", 1200),
    "dt": work_unit.config.get("dt", 0.071),
})

# Submit result to this FoundUp
submission = submit_resp(
    work_unit_id=work_unit.work_unit_id,
    submitter_id=agent_id,
    metrics=result["metrics"],
    artifacts=[result["events_path"], result["metrics_csv"]],
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
