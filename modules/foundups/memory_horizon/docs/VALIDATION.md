# Memory Horizon - Validation Status

## Current status

DOCUMENTATION_ONLY. SPECIFIED_NOT_IMPLEMENTED.

## Intake checks

- Stable ID selected: `memory_horizon`.
- No existing main-branch registry entity with that ID was found before branch creation.
- Entity type: `skeleton_candidate`.
- Manifest, README, interface, roadmap and ModLog supplied.
- Catalog/portfolio decision: not listed.
- DNS decision: proposed host documented only; no activation.
- Medical boundary explicit.
- Bounded POC issue: #1821.

## POC validation plan

### Deterministic synthetic tests
- event IDs unique
- exact event/probe linkage
- retired-event rejection
- cue/recognition not double-counted
- scheduler reproducibility with seed
- browser background timing anomaly flag
- export round-trip reconstruction

### UX/device tests
- current iPhone Safari
- Android Chrome
- desktop Chrome/Firefox
- large text
- interrupted/backgrounded session

### Research-method checks
- alternate forms
- practice effects
- event-difficulty balance
- missing/abandoned probes
- free/cued/recognition separation

## Truth boundary

Passing software tests proves only that the POC records what its code says it records. It does not establish validity as a measure of concussion, post-traumatic amnesia, dementia, neurological recovery or any medical condition.
