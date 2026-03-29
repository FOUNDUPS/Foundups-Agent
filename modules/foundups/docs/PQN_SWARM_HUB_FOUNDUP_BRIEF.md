# PQN Swarm Hub FoundUp Brief

**Status**: Execution brief
**Owner**: 0102
**WSP framing**: WSP-guided FoundUp planning, WSP 97 execution discipline

---

## Purpose

Define the FoundUp-level execution brief for a PQN Swarm Hub that coordinates:
- GPD
- PQN work units
- rESP result structures
- ROC contribution measurement

This is not a protocol rewrite.
This is a FoundUp planning brief for repo-grounded execution.

---

## Architect Decision

**PoC placement: internal first, external at Proto.**

Build the first executable version inside the monorepo under `modules/foundups/`.
Spin it out only after:
- gate/registry contracts stabilize
- rESP sink and verification contracts are explicit
- ROC contribution reporting is testable
- another 012 / Claw can participate through stable boundaries

This FoundUp is too coupled to still-moving platform contracts to start external off
the bat.

---

## Product Thesis

The PQN Swarm Hub is a FoundUp that turns bounded research work into:
- distributable PQNs
- verifiable rESP outputs
- ledger-ready result events
- ROC-scored contribution records

The system should reward verified contribution, not narrative activity.

---

## Boundary

### Belongs in this FoundUp
- PQN registry and routing surfaces
- gate logic for participant entry into this vertical
- rESP intake/sink for this vertical
- contribution measurement/reporting for this vertical
- product-facing workflows for swarm participation

### Does not belong here
- core WSP definitions
- core OpenClaw/WRE/HoloIndex ownership
- platform-wide auth/security substrate
- shared PatternMemory/HoloIndex implementation
- generic ledger core if it serves all FoundUps

This FoundUp consumes core infrastructure.
It does not redefine core infrastructure.

---

## Proposed Internal Module Shape

```text
modules/foundups/pqn_swarm_hub/
  README.md
  INTERFACE.md
  ROADMAP.md
  ModLog.md
  docs/
  src/
  tests/
```

Suggested internal slices:
- `gate`
- `registry`
- `resp_sink`
- `verification`
- `roc_reporting`
- `queue_integration`

---

## Execution Model

Flow:

1. ingest bounded research task
2. convert to PQN
3. distribute to participants
4. collect rESP outputs
5. verify by matching/review rules
6. commit verified result to durable artifact/ledger surface
7. score contribution with ROC-aligned reporting

The system is bounded and structural.
It is not freeform idea chat.

---

## Phase Plan

### Phase 0: Internal PoC
- define PQN object model for this FoundUp
- define rESP intake contract
- define minimal verification policy
- define ROC reporting shape
- produce deterministic reports

### Phase 1: Internal Proto
- wire to shared queue/review/index surfaces
- add participant gate
- prove reproducible runbook
- document adapter boundaries to shared infrastructure

### Phase 2: Externalization Readiness
- lock interfaces
- verify standalone deploy path
- prepare dual-remote repo setup
- document monorepo stub/adapter strategy

### Phase 3: Spin-Out
- create `FOUNDUPS/PQNSwarmHub`
- create `Foundup/PQNSwarmHub`
- migrate product code
- leave monorepo bridge/docs only where needed

---

## Initial Acceptance Criteria

The PoC is successful when:
- at least one PQN can be registered
- at least one rESP can be submitted in a structured format
- verification can distinguish accepted vs rejected output
- a durable result artifact is written
- ROC-style contribution reporting exists for accepted work

---

## Candidate FoundUp Portfolio Guidance

Use this FoundUp as a model for future exfoliation decisions:
- product-specific swarm/research hub -> FoundUp
- general-purpose platform substrate -> core

Examples:
- `AutoPost`: product FoundUp
- `gotjunk`: product FoundUp
- `Whack-a-Anything`: product FoundUp family
- OpenClaw/WRE/HoloIndex/continuity/security: core

---

## Required Next Slice

If approved, the next proper 0102 slice is:

- `pqn_swarm_hub_internal_poc_scaffold`

Goal:
- scaffold the internal FoundUp module
- define contracts first
- do not externalize yet
