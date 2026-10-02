# 0102 Moshpit — Agent Learning & Action Log

## Purpose

`0102 Moshpit` is the operational learning layer for 0102 / Red Dog.

It is intentionally separate from the existing `012 Moshpit` convention:

- **012 Moshpit**: what happened to / was done by 012 and project activity.
- **Email Log**: correspondence transaction history.
- **0102 Moshpit**: what the agent did, got wrong, repaired, learned, and changed.
- **Red Dog candidates**: generalized rules, guardrails, state machines, tests, and reusable skills promoted from 0102 Moshpit.

The repository already has a `docs/012_moshpit/` convention used by corpus-resolution code. `docs/0102_moshpit/` mirrors that naming boundary while keeping agent-learning semantics distinct.

## Storage architecture

### Live mutable log

The live 0102 Moshpit is maintained in the connected work-document system because autonomous runs need a low-friction append target. It is the operational event stream.

Do **not** commit every daemon heartbeat or raw operational event to Git. That would create noisy history and risk leaking private correspondence metadata.

### GitHub promoted layer

This directory contains only sanitized lessons that have passed the promotion rule. Git is the durable, reviewable source for lessons intended to become Red Dog behavior.

Current machine-readable promoted lessons live in:

- `red_dog_candidates.jsonl`

Future code should ingest promoted candidates from this directory only after validation/tests, not scrape raw private operational logs.

## Promotion rule

Promote a lesson from the live 0102 Moshpit when either:

1. the same lesson occurs at least twice; or
2. a single incident reveals a structural weakness that warrants a reusable guardrail, state machine, invariant, or test.

A repair is not complete until one of these is true:

- the operating prompt/rule was changed;
- a code/test change was made; or
- a concrete reason was recorded for why no system change is required.

## Event schema for the live log

A meaningful learning event should capture:

- JST timestamp
- workflow/system
- trigger/evidence
- WSP15 importance
- classification (`AUTO`, `DRAFT`, `ESCALATE`, `INTERNAL`)
- action taken
- verification result
- error / near-miss
- root cause
- generalized rule learned
- prompt / skill / code change made
- next test / expected event
- stable internal references where appropriate

Routine successful checks and no-op runs should not be logged.

## Privacy boundary

Never publish to this directory:

- private email addresses
- BCC lists
- full email bodies
- account-security details
- personal financial data
- private message/thread identifiers when not required for public engineering understanding
- unrelated personal information

Public Git should contain generalized engineering lessons only.

## Red Dog direction

The long-term goal is an event-driven DAE-style monitor:

`event -> identity/thread grounding -> WSP15 -> policy/skill router -> action -> verification -> action receipt -> learning -> promotion`

The 0102 Moshpit is the learning membrane between autonomous operations and stable Red Dog code.
