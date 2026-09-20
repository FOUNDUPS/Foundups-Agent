# Memory Horizon Companion - Assistive Memory Architecture

Status: DEFERRED_RESEARCH / SPECIFIED_NOT_IMPLEMENTED.

## Concept

Memory Horizon Companion is the assistive counterpart to the measurement game.

The measurement game asks: **how long is new episodic information being retained?**

The Companion asks: **when memory fails in ordinary life, can the system restore the missing context with the smallest useful cue?**

Working metaphor: a **memory seeing dog** — an external companion that notices what happened, preserves a compact private breadcrumb, and helps the wearer re-orient when recall fails.

## Canonical example

```text
19:12:04  wearer hands phone to father
           |
           v
event extractor
  object_transfer(
    object=phone,
    from=wearer,
    to=father,
    timestamp=19:12:04,
    confidence=0.94,
    evidence=[audio, visual/context]
  )
           |
           v
episodic breadcrumb ledger

19:14:10  wearer: "Where is my phone?"
           |
           v
retriever searches recent phone events
           |
           v
graded cue:
  Level 1: "You handed it to someone a couple of minutes ago."
  Level 2: "You handed it to your father."
  Level 3: "Your father has your phone."
```

The system should not confidently invent an answer. If evidence is weak or contradictory, it says it does not know.

## Closed-loop model

```text
CAPTURE
  -> EVENTIZE
  -> BREADCRUMB
  -> RETRIEVAL FAILURE / QUERY
  -> RETRIEVE
  -> MINIMAL CUE
  -> USER RESPONSE
  -> OUTCOME RECEIPT
  -> optional longitudinal measurement
```

This is different from a passive recorder. The important loop is the transition from lived event to later retrieval failure to assistance outcome.

## FoundUps memory mapping

The repository already has a useful conceptual analogue under WSP 60:

- **Episodic memory / Breadcrumbs** -> what happened, when, and with what evidence.
- **Brain / Memex** -> consolidated understanding and durable context.
- **HoloIndex-like retrieval** -> search the relevant evidence without replaying everything.
- **Working memory** -> immediate current situation.
- **RedDog attention boundary / nudge** -> stay silent until surfacing information changes the human's next action.

This is an architectural analogy, not evidence that the existing RedDog runtime can already ingest human life events.

## Sensor architecture

### P0 - phone/headset

Use microphone, device motion and explicit user markers. Lowest hardware burden, but many physical actions cannot be reliably inferred from audio alone.

### P1 - camera + audio wearable

A chest/head-worn camera or smart-glasses-class device can infer object transfers, locations and task completion. Prefer **on-device event extraction** with raw image/video deletion after the compact event is formed.

### P2 - sensor fusion

Potential future inputs:
- audio
- first-person visual frames
- phone/Bluetooth proximity
- location with explicit permission
- inertial signals
- object tags / UWB / BLE
- calendar/task context
- optional caregiver annotations

Each sensor contributes evidence; no single sensor automatically becomes truth.

## Event model

A lived breadcrumb should be compact and provenance-bearing:

```json
{
  "event_id": "evt_...",
  "event_type": "object_transfer",
  "subject": "wearer",
  "object": "phone",
  "actor_from": "wearer",
  "actor_to": "father",
  "timestamp": "2026-09-20T19:12:04+09:00",
  "location_scope": "optional/private",
  "confidence": 0.94,
  "evidence_refs": ["ephemeral:audio:...", "ephemeral:vision:..."],
  "raw_media_retained": false
}
```

Event truth must remain revisable when later evidence contradicts it. Derived summaries must not replace source provenance.

## Retrieval-failure triggers

The safest initial trigger is explicit query:
- "Where is my phone?"
- "Did I take my medicine?"
- "Who did I give this to?"
- "Did I lock the door?"

Later research may consider implicit triggers such as repeated searching or repeated questions, but those are much more error-prone and privacy-sensitive.

## Graded cueing

Do not jump directly to the complete answer when a weaker prompt could restore the user's own memory.

Suggested sequence:
1. context cue
2. person/place/category cue
3. explicit factual answer
4. show/replay source only if separately allowed

Record which cue level was sufficient. With explicit research consent, this can become a naturalistic longitudinal signal about retrieval support required over time.

## Differentiation

### MIT MemPal

MemPal is the closest published comparator found during intake research. It uses a wearable camera, automatically logs actions without storing image data, answers queries such as "where is my phone?", and provides safety reminders. Memory Horizon must therefore not claim novelty for basic wearable object recall.

Potential differentiators:
- shared event/probe data model between controlled game measurement and real-world assistance
- explicit event-to-retrieval-failure timing
- graded cueing rather than only answer retrieval
- contamination-aware longitudinal memory measurement
- provenance/confidence exposed to the user/researcher
- integration with FoundUps-style Breadcrumb/Brain/Memex concepts
- local-first/open research implementation target

### SenseCam / lifelogging

SenseCam research provides evidence that wearable-captured images can cue autobiographical recall in some populations. Memory Horizon Companion adds real-time event extraction and just-in-time retrieval rather than requiring later manual review.

### General AI wearables

Products that record/summarize conversations establish hardware/user demand for ambient memory, but conversation transcription alone does not reliably model physical actions, event provenance or retrieval failure.

## Privacy invariants

1. Wearer can visibly mute capture.
2. Capture state must be legible.
3. Prefer on-device processing.
4. Raw audio/video should be ephemeral by default.
5. Persist compact events, not continuous life recordings, unless separately authorized.
6. Bystander speech/identity should be minimized.
7. No face recognition by default.
8. Principal-scoped encryption and deletion controls.
9. Every inferred event carries confidence/provenance.
10. The system can answer "I don't know."
11. No covert recording mode.
12. Medical and safety-critical actions require separate validation and policy.

## Relationship to clinical use

The Companion may eventually support people with memory impairment, but it is not a treatment, diagnostic device or substitute for clinical supervision. Medication, driving, emergency and return-to-sport decisions must never be inferred from this architecture without appropriate validation and regulatory authorization.

## Delivery sequence

1. Prove #1821 event/probe/timing data model in the game.
2. Prototype explicit manual breadcrumbs on a phone.
3. Add voice query retrieval over those breadcrumbs.
4. Add on-device audio event extraction.
5. Add optional camera/smart-glasses event extraction.
6. Test graded cueing and confidence behavior.
7. Run non-clinical usability/privacy study.
8. Only then design population-specific clinical research.

Deferred work issue: #1823, `MEMORY_HORIZON_COMPANION_PHASE1`.
