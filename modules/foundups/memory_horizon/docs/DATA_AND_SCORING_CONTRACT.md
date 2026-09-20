# Memory Horizon - Data and Scoring Contract

## Principle

Keep raw observations primary. Derived metrics must be reproducible from exported events and probes.

## Minimal session schema

```json
{
  "session_id": "local-random-id",
  "schema_version": "mh_poc_v1",
  "seed": "deterministic-seed",
  "started_at": "ISO-8601",
  "events": [],
  "probes": [],
  "observer_markers": []
}
```

## Event

Required fields:
`event_id, event_type, presented_at, truth, form_id, probe_eligible, retired_at`.

## Probe

Required fields:
`probe_id, event_id, scheduled_delay_ms, actual_delay_ms, mode, prompt_version, response, correct, latency_ms, cue_level, started_at, completed_at, validity`.

## Observer marker

Required fields:
`marker_id, timestamp, category, note`.

Observer markers are annotations. They never become ground truth for game scoring automatically.

## Contamination rules

1. A scored event contributes at most one independent retention-delay observation.
2. Cue and recognition follow-up on the same event characterize retrieval level but do not become additional independent samples.
3. Once a player has been reminded of the event truth, no later probe of that event estimates original retention.
4. Repeated narrative references that reveal the event truth retire the event.
5. Browser timing anomalies can invalidate a delay observation without deleting the raw record.

## Phase 1 derived metrics

- free-recall accuracy by delay
- cued-recall rescue rate
- recognition rescue rate
- median response latency by mode/delay
- longest successful free-recall delay observed
- earliest free-recall failure observed
- bracketing interval for apparent retention horizon when data allow
- number of valid observations supporting each estimate

No weighted composite or clinical cutoff in Phase 1.

## Adaptive scheduler

Use transparent rules:
- maintain candidate delay bins
- choose new untested event for each probe
- move upward after reliable successes
- sample between success/failure bounds
- occasionally resample nearby bins on new events to estimate noise
- stop claiming a horizon if evidence is sparse or contradictory

The algorithm and version must be exported with each session.
