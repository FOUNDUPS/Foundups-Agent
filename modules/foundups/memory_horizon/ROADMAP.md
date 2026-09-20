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
| MVP research tool | Multi-session studies, controlled data collection | Privacy/security review; published method; non-diagnostic claims |
| Companion P0 | Manual real-world breadcrumbs + voice retrieval | Correct provenance/confidence; local/private by default |
| Companion P1 | On-device audio/context event extraction | Raw-media minimization; false-event rate measured |
| Companion P2 | Optional camera/smart-glasses sensor fusion | Bystander/privacy review; visible capture controls |
| Companion P3 | Graded just-in-time cues | Cue efficacy and error behavior measured without clinical claims |
| Validation | Prospective human-subject research against reference instruments | Ethics/IRB equivalent, preregistered endpoints, clinician/research partners |
| Medical pathway | Only if independently justified | Regulatory strategy, clinical validation and quality system |

The Companion stages remain deferred until the browser event/probe model is proven. They do not enlarge #1821.

## Game-design sweep ladder

The game is our persistent wrapper; measurement complexity grows in controlled sweeps:

0. survival shell/event ledger;
1. episodic retention;
2. temporal/sequence memory;
3. associative/context memory;
4. working memory/interference;
5. attention/inhibition/processing speed;
6. executive switching;
7. adaptive mixed-domain campaign;
8. longitudinal alternate forms.

**Current build boundary: Sweep 0 + Sweep 1 only.** Later sweeps must not enter the POC merely because they are easy to code. Each sweep requires interpretable evidence from the preceding layer. See [GAME_DESIGN_SWEEPS.md](docs/GAME_DESIGN_SWEEPS.md).

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

## Assistive-memory sequence

1. Reuse the proven event schema for manually entered real-world breadcrumbs.
2. Voice query: retrieve the most recent relevant event with confidence/provenance.
3. Graded cue ladder: context -> person/place -> explicit answer.
4. Add on-device audio event extraction.
5. Add optional visual/smart-glasses event extraction with ephemeral raw media.
6. Record retrieval failure -> cue level -> outcome as a closed-loop receipt.
7. Study whether these naturalistic observations add useful longitudinal research signals.
8. Keep medical interpretation behind a separate prospective-validation gate.

Research/architecture: [Assistive Memory Companion](docs/ASSISTIVE_MEMORY_COMPANION.md). Deferred issue: #1823.

## Milestones

- **M0 Intake** — this packet plus registry/manifest candidate.
- **M1 Playable** — complete a 10-minute session without backend.
- **M2 Measurable** — export reconstructs every event/probe relationship.
- **M3 Adaptive** — delays move up/down based on prior independent events.
- **M4 Repeatable** — alternate forms permit repeated sessions with reduced practice contamination.
- **M5 Research-ready** — Sweep 0-1 protocol, consent model, data dictionary and analysis plan reviewed; later cognitive sweeps remain gated.
- **M6 Companion alpha** — manual lived breadcrumbs + evidence-ranked voice retrieval.
- **M7 Wearable alpha** — privacy-preserving event extraction from approved sensors.
- **M8 Clinically studied** — external prospective validation; no medical claims before this gate.

## Public surface

Proposed future host: `memory.foundups.com`. DNS/public activation is a separate slice. The first POC can live as an internal/static preview under the FoundUps development surface.

## Next work

Primary: issue #1821, `MEMORY_HORIZON_POC_PHASE1`.

Deferred after the event model is proven: issue #1823, `MEMORY_HORIZON_COMPANION_PHASE1`.
