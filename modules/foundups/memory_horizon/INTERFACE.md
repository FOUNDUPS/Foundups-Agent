# Memory Horizon - Interface Contract

Status: SPECIFIED_NOT_IMPLEMENTED.

## POC surface

A single mobile-first web application with four logical surfaces:

1. **Play** — branching micro-adventure with simple choices and unique events.
2. **Probe** — delayed questions about prior events.
3. **Observer marker** — optional caregiver/researcher timestamped notes about naturally occurring behavior.
4. **Timeline/export** — raw event/probe history and derived retention curve.

## Event contract

Each game event must have:
- immutable session-local `event_id`
- `event_type`
- presentation timestamp
- canonical truth payload
- human-readable display payload
- probe eligibility
- content/form identifier so alternate forms can be tracked

Events used for scoring must be novel within the relevant session and must not reveal that they will later be tested.

## Probe contract

A probe binds to exactly one prior unretired event and records:
- `probe_id`
- `event_id`
- scheduled delay and actual delay
- probe mode: `free_recall | cued_recall | recognition`
- response
- correctness rule/version
- response latency
- cue level
- timestamp
- completion/abandonment state

After a scored probe, that event is retired from the retention estimator. Follow-up cueing may characterize retrieval of the same event but must not be treated as an independent retention observation.

## Estimator contract

POC output is descriptive:
- accuracy by delay bin
- free/cued/recognition outcome by delay
- latency by delay
- longest observed delay with successful free recall
- shortest observed delay with failure
- uncertainty/insufficient-data state

No clinical threshold, diagnosis, impairment label or recovery-clearance decision is permitted in Phase 1.

## Privacy boundary

POC is local/private by default. Export is explicit JSON/CSV. No background upload, patient identity requirement, public leaderboard or transcript publication.

## Failure boundary

If timing is interrupted, browser suspension makes delay uncertain, event truth is ambiguous, or the same event is accidentally re-used, mark the observation invalid rather than silently scoring it.
