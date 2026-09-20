# Memory Horizon - POC Scope

## Minimum viable POC

A single-player browser micro-adventure that creates unique events, interleaves delayed episodic probes, adapts subsequent delays, records observer markers and exports a transparent retention timeline.

## Included

- Mobile-first browser UI.
- Four or five simple character/classes only if they affect flavor, not difficulty.
- Deterministic seeded event generation for reproducibility.
- >=12 unique scorable events per demo session.
- Event types: choice, object, character, route, action, location.
- Probe types: free recall, cued recall, recognition.
- Candidate delay ladder: 30 s, 1, 2, 4, 8 min; configurable.
- Actual-delay measurement using monotonic/browser timing where practical plus wall-clock timestamps.
- Event retirement after scored probe.
- Caregiver/researcher timestamp markers.
- JSON and CSV export.
- Simple timeline/curve visualization.
- Local/private-by-default storage.

## Excluded

Diagnosis, medical advice, return-to-play decisions, normative impairment thresholds, user accounts, cloud patient records, tokens, rewards, multiplayer, ads, public leaderboards, voice/video, biometrics, AI diagnosis and automatic hospital integration.

## POC acceptance

1. Synthetic deterministic run creates >=12 event/probe pairs without orphan IDs.
2. No retired event contributes a second independent retention sample.
3. Free/cued/recognition stages are separately represented.
4. Actual delay and scheduled delay are both retained.
5. Browser suspension/timing anomalies are flagged.
6. Export recreates the complete session.
7. POC runs on current iPhone Safari and Android Chrome.
8. Safety text makes non-diagnostic status unmistakable.

## Initial UX

The player should be able to start within one tap, understand controls in <30 seconds, and play without knowing which facts will later be tested. Graphics may be text/icons/simple cards. Measurement validity beats polish.

Status: NOT_BUILT.
