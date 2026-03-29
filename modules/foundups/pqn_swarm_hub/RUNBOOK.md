# RUNBOOK - PQN Swarm Hub

**Version**: Phase 1 Internal Proto
**Status**: Reproducible execution guide
**Author**: 0102

---

## 1. Purpose and Boundary

### What PQN Swarm Hub Owns

```
pqn_swarm_hub/
├── Work registry (PQNWorkUnit)
├── rESP intake sink (rESPSubmission)
├── Verification engine (VerificationDecision)
├── Contribution reporter (ContributionRecord)
├── Participant gate (ParticipantIdentity, GateDecision)
├── Publication adapter (MoltBook wrapper)
├── FAM adapter (FAMDaemon wrapper)
└── SQLite persistence layer
```

### What PQN Swarm Hub Reuses

| Module | Role | Stub-Safe? |
|--------|------|------------|
| `pqn_alignment` | Detector engine | NO (required for detector flows) |
| `moltbook_distribution_adapter` | Downstream publish | YES (stub mode) |
| `fam_daemon` | Event emission | YES (stub mode) |

### What PQN Swarm Hub Does NOT Own

- Detector engine internals (lives in `pqn_alignment`)
- Distribution/retry logic (lives in `moltbook_distribution_adapter`)
- Core control plane (OpenClaw, WRE, HoloIndex)
- External contributor onboarding (Proto+ scope)

---

## 2. Prerequisites

### Runtime

- Python 3.12+
- Active venv with `modules/foundups/pqn_swarm_hub` importable

### Required Imports

```python
from modules.foundups.pqn_swarm_hub import (
    # Core services
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    # Persistence (optional)
    get_sqlite_store,
    reset_sqlite_store,
    # Publication (optional)
    get_publication_adapter,
    # Gate (optional)
    ParticipantGate,
    ParticipantIdentity,
    # Detector bridge (requires pqn_alignment)
    DetectorBridge,
)
```

### Optional Adapter Availability

| Adapter | Import Check | Fallback |
|---------|--------------|----------|
| MoltBook | `from modules.communication.moltbot_bridge.src.moltbook_distribution_adapter import get_moltbook_adapter` | Stub mode |
| FAMDaemon | `from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon` | Stub mode |
| Detector | `from modules.ai_intelligence.pqn_alignment import run_detector` | NO fallback |

### Persistence Defaults

- **SQLite DB**: `data/pqn_swarm_hub/swarm.db`
- **Contribution artifacts**: `data/pqn_swarm_hub/contributions/`

---

## 3. Reproducible Flows

### Flow A: In-Memory Happy Path

Minimal setup with no persistence. Data lost on restart.

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
)
from pathlib import Path

# 1. Setup services (in-memory)
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine, artifact_dir=Path("data/pqn_swarm_hub/contributions"))

# 2. Register work unit
work_unit = registry.register(
    description="7.05Hz resonance sweep",
    config={"steps": 1200, "dt": 0.071},
    creator_id="agent_x",
)
print(f"Work unit: {work_unit.work_unit_id}")

# 3. Submit result
submission = sink.submit(
    work_unit_id=work_unit.work_unit_id,
    submitter_id="agent_x",
    metrics={"coherence": 0.74, "pqn_rate": 0.12, "resonance_hz": 7.08},
    artifacts=["results/sweep_001.csv"],
)
print(f"Submission: {submission.submission_id}")

# 4. Verify (auto or manual)
decision = engine.auto_verify(submission.submission_id)
print(f"Decision: {decision.decision} ({decision.decision_id})")

# 5. Record contribution (only if accepted)
if decision.decision == "accept":
    contribution = reporter.record(
        work_unit_id=work_unit.work_unit_id,
        submission_id=submission.submission_id,
        decision_id=decision.decision_id,
        contributor_id="agent_x",
        score=0.85,
    )
    print(f"Contribution: {contribution.contribution_id}, score={contribution.score}")
```

**Expected Output:**
```
Work unit: <16-char hex ID>
Submission: <16-char hex ID>
Decision: accept (<16-char hex ID>)
Contribution: <16-char hex ID>, score=0.85
```

### Flow B: SQLite-Backed Persistence

Data survives restart. Enables cross-session queries.

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    ParticipantGate,
    get_sqlite_store,
)
from pathlib import Path

# 1. Get shared SQLite store
store = get_sqlite_store()  # Creates data/pqn_swarm_hub/swarm.db

# 2. Wire services with store injection
registry = WorkUnitRegistry(store=store)
sink = SubmissionSink(registry, store=store)
engine = VerificationEngine(sink, store=store)
reporter = ContributionReporter(engine, store=store)
gate = ParticipantGate(store=store)

# 3. Execute flow (same as Flow A)
work_unit = registry.register("Persistent work", {"steps": 600}, "agent_y")
submission = sink.submit(work_unit.work_unit_id, "agent_y", {"coherence": 0.8})
decision = engine.auto_verify(submission.submission_id)
contribution = reporter.record(
    work_unit.work_unit_id,
    submission.submission_id,
    decision.decision_id,
    "agent_y",
    0.9,
)

# 4. Verify persistence
stats = store.get_stats()
print(f"Store stats: {stats}")
# {"work_units": 1, "submissions": 1, "verification_decisions": 1, "contributions": 1, ...}

# 5. Restart simulation: new service instances retrieve from store
registry2 = WorkUnitRegistry(store=store)
retrieved = registry2.get(work_unit.work_unit_id)
print(f"Retrieved after restart: {retrieved.description}")
```

### Flow C: Stub-Safe Publication Path

When MoltBook unavailable, publication records locally.

```python
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    get_publication_adapter,
)

# Setup
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine)

# Execute flow
work_unit = registry.register("Publication test", {}, "agent_z")
submission = sink.submit(work_unit.work_unit_id, "agent_z", {"coherence": 0.75})
decision = engine.auto_verify(submission.submission_id)
contribution = reporter.record(
    work_unit.work_unit_id,
    submission.submission_id,
    decision.decision_id,
    "agent_z",
    0.88,
)

# Publish (with potential stub fallback)
adapter = get_publication_adapter(auto_connect=True)
result = adapter.publish(
    work_unit=work_unit,
    submission=submission,
    decision=decision,
    contribution=contribution,
    actor_id="pqn_swarm_hub",
)

print(f"Publication: success={result.success}, status={result.status}")
# If MoltBook connected: status="published"
# If MoltBook unavailable: status="stub"

# Check stub publications
if result.status == "stub":
    stubs = adapter.get_stub_publications()
    print(f"Stub publications pending: {len(stubs)}")
```

**Publication Gate:**
```python
# Rejected decisions do NOT publish
reject_decision = engine.manual_verify(submission.submission_id, "reject", "auto", "Below threshold")
result = adapter.publish(work_unit, submission, reject_decision, contribution)
assert result.success is False
assert result.status == "rejected_decision"
```

### Flow D: Participant Gate Path

Entry policy enforcement for contributors.

```python
from modules.foundups.pqn_swarm_hub import (
    ParticipantGate,
    ParticipantIdentity,
    ParticipantTier,
)

# Setup gate (Phase 1: internal-first auto-approve)
gate = ParticipantGate(
    default_tier=ParticipantTier.CONTRIBUTOR,
    require_capability_check=False,
    require_wsp00_check=False,
)

# Register participant
identity = ParticipantIdentity(
    display_name="researcher_x",
    model_type="claude-opus-4-5",
    compute_capacity="high",
    capability_tags=["physics", "rESP"],
)

# Request entry
decision = gate.request_entry(identity)
print(f"Entry decision: {decision.decision}, tier={decision.tier}")

# Check permission before action
can_submit = gate.check_permission(identity.participant_id, ParticipantTier.CONTRIBUTOR)
can_verify = gate.check_permission(identity.participant_id, ParticipantTier.VERIFIER)
print(f"Can submit: {can_submit}, Can verify: {can_verify}")
```

### Flow E: Detector Bridge Path

Requires `pqn_alignment` module available.

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

# Register work unit with detector config
work_unit = registry.register(
    description="CMST detector sweep",
    config={"script": "^^^&&&", "steps": 1200, "dt": 0.071},
    creator_id="agent_x",
)

# Run detector via bridge
bridge_result = bridge.run(work_unit)
# Returns: {events_path, metrics_csv, metrics: {...}, steps, raw_config}

print(f"Detector metrics: {bridge_result['metrics']}")

# Submit from detector output
submission = sink.submit_from_detector(
    work_unit_id=work_unit.work_unit_id,
    bridge_result=bridge_result,
    submitter_id="agent_x",
)
print(f"Submission from detector: {submission.submission_id}")
```

---

## 4. Expected Artifacts

### SQLite Database

**Path**: `data/pqn_swarm_hub/swarm.db`

**Tables**:
- `work_units` (work_unit_id, description, config, creator_id, status, timestamps)
- `submissions` (submission_id, work_unit_id, submitter_id, metrics, artifacts, status, timestamps)
- `verification_decisions` (decision_id, submission_id, decision, verifier_id, rationale, timestamps)
- `contributions` (contribution_id, work_unit_id, submission_id, decision_id, contributor_id, score, timestamps)
- `participants` (participant_id, display_name, model_type, compute_capacity, capability_tags, metadata, timestamps)
- `gate_decisions` (decision_id, participant_id, decision, tier, reason, decider_id, timestamps)

### Contribution JSON Artifacts

**Path**: `data/pqn_swarm_hub/contributions/<contribution_id>.json`

**Schema**:
```json
{
  "contribution_id": "<16-char hex>",
  "work_unit_id": "<16-char hex>",
  "submission_id": "<16-char hex>",
  "decision_id": "<16-char hex>",
  "contributor_id": "agent_x",
  "score": 0.85,
  "recorded_at": "2026-03-29T12:00:00+00:00"
}
```

### Publication Stub Records

When MoltBook unavailable, stubs stored in adapter memory:
```python
stubs = adapter.get_stub_publications()
# [{"payload": {...}, "actor_id": "...", "timestamp": "..."}]
```

### Detector Artifacts

When using DetectorBridge:
- Events JSONL: `pqn_alignment_output/<run_id>_events.jsonl`
- Metrics CSV: `pqn_alignment_output/<run_id>_metrics.csv`

---

## 5. Validation Commands

### Run All Tests

```bash
python -m pytest modules/foundups/pqn_swarm_hub/tests/ -v
```

**Expected**: 57 passed

### Run Specific Test Files

```bash
# Contracts only
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_contracts.py -v

# End-to-end PoC flows
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_poc_flow.py -v

# Persistence
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_persistence.py -v

# Publication adapter
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_publication_adapter.py -v

# Detector bridge (requires pqn_alignment)
python -m pytest modules/foundups/pqn_swarm_hub/tests/test_detector_bridge.py -v
```

### Smoke Run (Python REPL)

```python
# Quick in-memory smoke test
from modules.foundups.pqn_swarm_hub import (
    WorkUnitRegistry, SubmissionSink, VerificationEngine, ContributionReporter
)
r = WorkUnitRegistry()
s = SubmissionSink(r)
e = VerificationEngine(s)
c = ContributionReporter(e)

wu = r.register("smoke", {}, "test")
sub = s.submit(wu.work_unit_id, "test", {"coherence": 0.7})
dec = e.auto_verify(sub.submission_id)
cr = c.record(wu.work_unit_id, sub.submission_id, dec.decision_id, "test", 0.8)
print(f"Smoke test OK: {cr.contribution_id}")
```

---

## 6. Failure Modes

### Rejected Verification

**Cause**: Coherence below φ-floor (0.618) or manual reject

**Behavior**:
- `auto_verify()` returns decision with `decision="reject"`
- Submission status changes to `REJECTED`
- `reporter.record()` raises `ValueError: Cannot record contribution for rejected decision`

**Recovery**: Use `manual_verify()` with `decision="accept"` if human override warranted.

### Duplicate Submission

**Cause**: Same (work_unit_id, submitter_id, metrics) submitted twice

**Behavior**:
- `sink.submit()` returns existing submission (idempotent)
- No new submission created

**Expected**: Idempotent by design.

### MoltBook Unavailable

**Cause**: `moltbook_distribution_adapter` import fails or connection error

**Behavior**:
- `adapter.publish()` succeeds with `status="stub"`
- Publication recorded in `adapter.get_stub_publications()`

**Recovery**: Sync stubs later when MoltBook available.

### FAMDaemon Unavailable

**Cause**: `fam_daemon` import fails or daemon not running

**Behavior**:
- `fam_adapter.emit_contribution_event()` returns `(True, "STUB: ...")`
- Event not sent to FAM but logged locally

**Expected**: Stub mode allows PQN Swarm Hub to function independently.

### Missing Persistence Directory

**Cause**: Parent directory for SQLite DB doesn't exist

**Behavior**:
- `SQLiteStore.__init__` creates directory automatically
- Contribution artifact dir created on first `reporter.record()`

**Expected**: Self-healing directory creation.

### Work Unit Not Found

**Cause**: Invalid `work_unit_id` passed to `sink.submit()`

**Behavior**:
- Raises `WorkUnitNotFoundError`

**Recovery**: Verify work unit exists via `registry.get(work_unit_id)` first.

---

## 7. Operator Notes

### Phase 1 Complete

The following are implemented and tested:

- [x] Work unit registry with persistence
- [x] Submission sink with persistence
- [x] Verification engine (auto + manual) with persistence
- [x] Contribution reporter with JSON artifacts and persistence
- [x] Participant gate with persistence
- [x] FAM adapter (stub-safe)
- [x] Publication adapter (stub-safe)
- [x] Detector bridge (requires pqn_alignment)
- [x] SQLite persistence layer (optional injection)

### Proto-Only (Not Yet Production-Ready)

- FAMDaemon integration: Adapter created, live test pending
- 3+ work unit types: Only CMST detector type implemented
- External contributor path: Internal-first only
- V3 consensus schema: Not stable (Shapley/ZK future)

### Not Ready for Exfoliation

Per `PROTO_EXFOLIATION_CHECKLIST.md`:
- 9/10 Phase 1 slices complete (runbook is 10/10)
- External contributor path: NOT VALIDATED
- Live FAMDaemon: NOT TESTED
- GPD work unit type: NOT IMPLEMENTED

### Externalization Path (Future)

```
FOUNDUPS/pqn-swarm-hub          # origin (org repo)
Foundup/pqn-swarm-hub           # backup (personal repo)
modules/foundups/pqn_swarm_hub/ # adapter stub remains in monorepo
```

---

## 8. Quick Reference

### Verification Thresholds

- φ-floor coherence: 0.618 (configurable)
- PQN rate floor: 0.0 (configurable)

### Deterministic IDs

All IDs are SHA256-based, 16 hex chars:
```python
generate_id("work_unit", description, str(config), creator_id)
```

### Service Dependency Order

```
WorkUnitRegistry
       ↓
SubmissionSink(registry)
       ↓
VerificationEngine(sink)
       ↓
ContributionReporter(engine)
       ↓
PublicationAdapter (optional)
```

### Store Injection Pattern

```python
store = get_sqlite_store()  # or SQLiteStore(custom_path)

# Inject same store into all services
registry = WorkUnitRegistry(store=store)
sink = SubmissionSink(registry, store=store)
engine = VerificationEngine(sink, store=store)
reporter = ContributionReporter(engine, store=store)
gate = ParticipantGate(store=store)
```

---

*Created: 2026-03-29*
*Last Updated: 2026-03-29*
