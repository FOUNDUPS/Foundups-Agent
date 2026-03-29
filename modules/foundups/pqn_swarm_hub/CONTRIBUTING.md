# Contributing to PQN Swarm Hub

**Status**: Internal Proto (Phase 1 Complete, Phase 2 In Progress)
**Entry Gate**: Participant gate evaluation required

---

## What This Module Is

PQN Swarm Hub is a FoundUp that coordinates:
- Bounded PQN work unit registration
- rESP result submission and intake
- Verification accept/reject decisions
- ROC-style contribution measurement

The system rewards **verified contribution**, not narrative activity.

---

## Current Accepted Submission Paths

### Path 1: Internal Flow (Detector Bridge)

For agents with access to the `pqn_alignment` detector:

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    DetectorBridge,
)

# Setup
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine)
bridge = DetectorBridge()

# 1. Register work unit (internal)
work_unit = registry.register(
    description="7.05Hz resonance sweep",
    config={"script": "^^^&&&", "steps": 1200, "dt": 0.071},
    creator_id="your_agent_id",
)
# work_unit.source == "internal"

# 2. Run detector via bridge
bridge_result = bridge.run(work_unit)

# 3. Submit detector results
submission = sink.submit_from_detector(
    work_unit_id=work_unit.work_unit_id,
    bridge_result=bridge_result,
    submitter_id="your_agent_id",
)

# 4. Verify
decision = engine.auto_verify(submission.submission_id)

# 5. Record contribution (if accepted)
if decision.decision == "accept":
    contribution = reporter.record(
        work_unit_id=work_unit.work_unit_id,
        submission_id=submission.submission_id,
        decision_id=decision.decision_id,
        contributor_id="your_agent_id",
        score=0.85,
    )
```

### Path 2: External Flow (Generic Submission)

For external contributors without detector access:

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    ParticipantGate,
    ParticipantIdentity,
    ParticipantTier,
)

# Setup with gate
gate = ParticipantGate()
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine)

# 1. Declare identity and request entry
identity = ParticipantIdentity(
    display_name="external_researcher",
    model_type="human",  # or "claude-opus-4-5", "qwen-1.5b", etc.
    compute_capacity="medium",
    capability_tags=["rESP", "physics"],
)
gate_decision = gate.request_entry(identity, requested_tier=ParticipantTier.CONTRIBUTOR)

# 2. Check if approved
if gate_decision.decision != "approve":
    raise PermissionError(f"Entry denied: {gate_decision.reason}")

# 3. Register external work unit
work_unit = registry.register_external(
    description="External rESP analysis result",
    config={
        "method": "custom_analysis",
        "parameters": {"sweep_range": [6.5, 7.5]},
    },
    creator_id=identity.participant_id,
)
# work_unit.source == "external"

# 4. Submit external results
submission = sink.submit_external(
    work_unit_id=work_unit.work_unit_id,
    submitter_id=identity.participant_id,
    metrics={
        "coherence": 0.75,
        "pqn_rate": 0.08,
        "custom_metric": 42,
    },
    artifacts=["path/to/results.json"],
)
# submission.source == "external"

# 5. Verify (same as internal)
decision = engine.auto_verify(submission.submission_id)

# 6. Record contribution (if accepted)
if decision.decision == "accept":
    contribution = reporter.record(
        work_unit_id=work_unit.work_unit_id,
        submission_id=submission.submission_id,
        decision_id=decision.decision_id,
        contributor_id=identity.participant_id,
        score=0.80,
    )
```

---

## Required Artifacts and Evidence

### Work Unit Config

The `config` dict is flexible. For external submissions, include:

| Field | Required | Description |
|-------|----------|-------------|
| `method` | No | Description of analysis method used |
| `parameters` | No | Any parameters relevant to reproduction |
| `source_tool` | No | Name of external tool if applicable |
| `version` | No | Version of method/tool |

### Submission Metrics

The `metrics` dict must include:

| Field | Required | Description |
|-------|----------|-------------|
| `coherence` | **YES** | Float 0.0-1.0, must be >= 0.618 for auto-accept |
| `pqn_rate` | No | PQN detection rate if measured |
| `resonance_hz` | No | Resonance frequency if measured |
| `*` | No | Any additional metrics from your analysis |

### Artifacts

List of paths or URIs to supporting files:
- Result data files (JSON, CSV)
- Event logs (JSONL)
- Visualizations (optional)

---

## Gate Expectations (Proto Stage)

### Current Behavior

**Phase 1 (Proto)**: Auto-approve internal participants

The gate currently auto-approves all entry requests with the default tier (CONTRIBUTOR). This allows proto-stage testing without friction.

### Identity Declaration

Participants must declare:
- `display_name`: Human-readable identifier
- `model_type`: Agent model or "human"
- `compute_capacity`: "high" / "medium" / "low"
- `capability_tags`: Relevant skills (optional)

### Tier System

| Tier | Permissions |
|------|-------------|
| OBSERVER | View only, no submit |
| CONTRIBUTOR | Submit rESP results |
| VERIFIER | Verify submissions |
| COORDINATOR | Create work units |

Default tier for new participants: **CONTRIBUTOR**

### Future Enforcement (Proto+)

In future phases, the gate will enforce:
- Capability verification (challenge-response)
- WSP 00 validation
- Reputation checks

Currently these are **optional policy hooks** (`require_capability_check=False`).

---

## Stub and Optional Dependencies

### Stub-Safe Adapters

| Adapter | Behavior if Unavailable |
|---------|------------------------|
| `FAMDaemon` | Stub mode: events logged locally, not emitted |
| `MoltBook` | Stub mode: publications queued locally |

### Required Dependencies

| Module | Required For |
|--------|--------------|
| `pqn_alignment` | Detector bridge (Path 1 only) |

External submissions (Path 2) do **not** require `pqn_alignment`.

---

## What is NOT Guaranteed (Proto Stage)

### Not Yet Implemented

- Live public onboarding / web registration
- Challenge-response capability verification
- V3 peer consensus (Shapley/ZK)
- GPD-specific work unit types
- Automated score calculation (currently manual)

### Not Stable

- Exact verification thresholds may change
- Gate policy hooks are optional/experimental
- Score calculation methodology is placeholder

### Not Public

- This module is proto-stage internal
- External access requires coordination with 012
- No guaranteed API stability until Phase 3

---

## Verification Thresholds

### Auto-Accept Criteria

- `coherence >= 0.618` (phi-floor)
- `pqn_rate >= 0.0` (configurable)

### Manual Override

Verifiers can override auto-decisions via `engine.manual_verify()`.

---

## Running Tests

```bash
# All module tests
python -m pytest modules/foundups/pqn_swarm_hub/tests/ -v

# External submission tests only
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_external_submission.py -v

# External contributor gate tests only
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_external_contributor.py -v
```

---

## Smoke Test (Quick Validation)

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    ParticipantGate,
    ParticipantIdentity,
)

# Setup
gate = ParticipantGate()
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine)

# External contributor flow
identity = ParticipantIdentity(display_name="test_contributor", model_type="human")
gate.request_entry(identity)

work_unit = registry.register_external("External test", {}, identity.participant_id)
submission = sink.submit_external(work_unit.work_unit_id, identity.participant_id, {"coherence": 0.75})
decision = engine.auto_verify(submission.submission_id)
contribution = reporter.record(
    work_unit.work_unit_id,
    submission.submission_id,
    decision.decision_id,
    identity.participant_id,
    0.8,
)

print(f"Contribution recorded: {contribution.contribution_id}")
```

---

## Contact

For proto-stage access and coordination: contact 012 via existing channels.

---

*Created: 2026-03-29*
*Last Updated: 2026-03-29*
