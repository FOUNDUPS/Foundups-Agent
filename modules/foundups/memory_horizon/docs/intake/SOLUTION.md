# Memory Horizon - Solution Definition

## Core solution

A minimal branching adventure continuously creates memorable but ordinary events: choose a door, meet a character, receive an object, trade an item, choose a route, complete a small action. The player is not told which details will later be tested.

During subsequent play, the engine schedules probes against different prior events after controlled delays. Each scored event is then retired. The resulting dataset maps retention over time.

## Why a game

Explicit "remember these three words" tests encourage rehearsal and reveal the test strategy. A game can sample memory for naturally experienced events while maintaining precise event truth and timing.

The game remains intentionally simple. Measurement quality has priority over graphics.

## Probe ladder

For a selected event:

1. **Free recall** — "What did you give the merchant?"
2. **Cued recall** — category/context cue if free recall fails.
3. **Recognition** — choose among controlled alternatives.

The three outcomes are stored separately. Recognition after a failed free-recall probe does not erase the failure.

## Adaptive delay strategy

Initial candidate delays: 30 s, 1 min, 2 min, 4 min, 8 min. Phase 1 uses transparent staircase/bracketing rules, not machine learning.

Example:
- success at 2 min -> sample a longer delay on a new event
- failure at 8 min -> sample an intermediate delay on another new event
- sparse/conflicting data -> report uncertainty rather than a precise horizon

## Technical approach

Browser-first PWA-compatible implementation. Prefer ordinary TypeScript/JavaScript; use jsPsych where its trial/timeline/data model reduces custom experiment plumbing. Keep game state and measurement state separate.

POC can run entirely client-side with a deterministic seed and local export. A backend is not required until multi-user research, secure study management or synchronized clinician dashboards exist.

## POC -> Prototype -> MVP

POC proves measurement mechanics and contamination controls. Prototype adds alternate forms, repeated-session comparison and research dashboards. MVP is a research platform only after privacy/security/reliability work. Any clinical pathway is downstream of independent prospective validation.
