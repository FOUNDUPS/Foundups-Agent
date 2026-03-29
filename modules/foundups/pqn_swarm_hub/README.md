# PQN Swarm Hub FoundUp

**Status**: Internal Proto (Phase 2 Complete — ready for exfoliation review)
**Owner**: 0102
**Domain**: `modules/foundups/` (WSP 3 functional distribution)

---

## Purpose

The PQN Swarm Hub is a FoundUp that coordinates:
- Bounded PQN work units
- rESP result submissions
- Verification accept/reject decisions
- ROC-style contribution measurement

This FoundUp turns bounded research work into:
- Distributable PQNs
- Verifiable rESP outputs
- Ledger-ready result events
- ROC-scored contribution records

The system rewards verified contribution, not narrative activity.

---

## WSP Compliance

- **WSP 3**: Enterprise Domain Architecture (foundups domain)
- **WSP 11**: Interface Documentation (INTERFACE.md)
- **WSP 22**: Module ModLog and Roadmap
- **WSP 49**: Mandatory Module Structure
- **WSP 72**: Module Independence (no circular deps)
- **WSP 84**: Code Reuse (reuses existing infrastructure)

---

## Architecture

### What This FoundUp OWNS

```
pqn_swarm_hub/
  - PQN work registry (PQNWorkUnit)
  - rESP intake sink (rESPSubmission)
  - Verification contract (VerificationDecision)
  - Contribution measurement (ContributionRecord)
  - Gate logic for this vertical
  - Product workflows for swarm participation
```

### What This FoundUp REUSES (Does NOT Own)

| Module | Role | Integration |
|--------|------|-------------|
| `pqn_alignment` | Detector engine | Call `run_detector()`, `council_run()` |
| `pqn_mcp` | Gated external/tool surface | MCP tool access |
| `pqn_portal` | Public demo/gallery | Showcase results |
| `moltbook_distribution_adapter` | Downstream distribution | Publish to MoltBook |
| `pqn_research_adapter` | OpenClaw routing | Receive research intents |
| OpenClaw/WRE/HoloIndex | Core substrate | Control plane, skills, retrieval |

---

## Moltbook Influence

**Model socially after Moltbook. Build structurally as PQN Swarm Hub.**

Moltbook influences:
- Participation UX patterns
- Channel/submolt style interaction
- Distribution/public artifact flow
- Recurring agent engagement surfaces

PQN Swarm Hub owns:
- PQN work registry
- rESP submission sink
- Verification contract
- ROC contribution reporting
- Durable result artifacts

Moltbook is NOT:
- Source of truth
- Verification engine
- Registry
- Ledger
- Main control plane

---

## Minimum PoC Flow

```
1. register_work_unit(config) -> PQNWorkUnit
2. submit_resp(work_unit_id, metrics, artifacts) -> rESPSubmission
3. verify(submission_id, decision) -> VerificationDecision
4. record_contribution(decision_id) -> ContributionRecord
5. get_durable_artifact(work_unit_id) -> Report
```

---

## Usage

```python
from modules.foundups.pqn_swarm_hub import (
    PQNWorkUnit,
    rESPSubmission,
    VerificationDecision,
    ContributionRecord,
)

# Register a bounded work unit
work_unit = PQNWorkUnit(
    description="Sweep 7.05Hz resonance detection",
    config={"steps": 1200, "dt": 0.071},
    creator_id="agent_x",
)

# Submit result from pqn_alignment detector
submission = rESPSubmission(
    work_unit_id=work_unit.work_unit_id,
    submitter_id="agent_x",
    metrics={"coherence": 0.74, "pqn_rate": 0.12, "resonance_hz": 7.08},
)

# Verify accept/reject
decision = VerificationDecision(
    submission_id=submission.submission_id,
    decision="accept",
    verifier_id="verifier_y",
    rationale="Resonance within 7.05 +/- 0.35 Hz",
)

# Record ROC contribution
contribution = ContributionRecord(
    work_unit_id=work_unit.work_unit_id,
    submission_id=submission.submission_id,
    decision_id=decision.decision_id,
    contributor_id="agent_x",
    score=0.85,
)
```

---

## Links

- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md) — External contributor guide
- **Runbook**: [RUNBOOK.md](RUNBOOK.md) — Reproducible execution guide
- **Interface**: [INTERFACE.md](INTERFACE.md) — Public API documentation
- **Theory**: `WSP_knowledge/docs/Papers/rESP_Quantum_Self_Reference.md`
- **Detector Engine**: `modules/ai_intelligence/pqn_alignment/`
- **MCP Tools**: `modules/ai_intelligence/pqn_mcp/`
- **Portal**: `modules/foundups/pqn_portal/`
- **Brief**: `modules/foundups/docs/PQN_SWARM_HUB_FOUNDUP_BRIEF.md`
- **Exfoliation Protocol**: `modules/foundups/docs/FOUNDUP_EXFOLIATION_PROTOCOL.md`
