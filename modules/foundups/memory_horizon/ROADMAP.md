# Memory Horizon - Roadmap

Status: planning_reference; SPECIFIED_NOT_IMPLEMENTED; TOKEN_DEFERRED.

## Layered delivery

| Stage | Deliverable | Advancement gate |
|---|---|---|
| Intake | WSP 109 packet, research, data contract | Scope and medical boundary explicit |
| POC 0 | Deterministic browser simulation | Synthetic sessions prove event/probe/timing/export integrity |
| POC 1 | Minimal branching game | >=12 unique events; delayed probes interleave with play; mobile browser works |
| POC 2 | Adaptive retention engine | Delay selection is transparent; probe contamination controls pass |
| POC 3 | Observer timeline | Caregiver/researcher markers merge without altering test answers |
| Prototype | Alternate forms, session comparison, research dashboard | Practice effects characterized; reliability study designed |
| Validation | Prospective human-subject research against reference instruments | Ethics/IRB equivalent, preregistered endpoints, clinician/research partners |
| MVP research tool | Multi-session studies, controlled data collection | Privacy/security review; published method; non-diagnostic claims |
| Medical pathway | Only if independently justified | Regulatory strategy, clinical validation and quality system |

## POC implementation sequence

1. Static single-session game state.
2. Event generator with deterministic seed.
3. Scheduler for 30 s / 1 / 2 / 4 / 8 minute candidate delays.
4. Free recall first; optional cue; then recognition.
5. Event retirement and contamination guard.
6. Adaptive delay selection using transparent rules.
7. Observer markers.
8. JSON/CSV export and visual timeline.
9. Mobile Safari/Chrome acceptance.
10. Synthetic regression fixtures and documentation.

## Milestones

- **M0 Intake** — this packet plus registry/manifest candidate.
- **M1 Playable** — complete a 10-minute session without backend.
- **M2 Measurable** — export reconstructs every event/probe relationship.
- **M3 Adaptive** — delays move up/down based on prior independent events.
- **M4 Repeatable** — alternate forms permit repeated sessions with reduced practice contamination.
- **M5 Research-ready** — protocol, consent model, data dictionary and analysis plan reviewed.
- **M6 Clinically studied** — external prospective validation; no medical claims before this gate.

## Public surface

Proposed future host: `memory.foundups.com`. DNS/public activation is a separate slice. The first POC can live as an internal/static preview under the FoundUps development surface.

## Next work

Issue #1821: `MEMORY_HORIZON_POC_PHASE1`.
