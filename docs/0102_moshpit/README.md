# 0102 Moshpit — Candidate Engineering Lessons

## Purpose

This directory preserves sanitized candidate engineering lessons from 0102 / Red Dog operations. Its integration status is **SPECIFIED_NOT_IMPLEMENTED**: it is a reviewable proposal set, not a new operational log, memory database, training pipeline, or runtime promotion mechanism.

It is intentionally separate from the existing `012 Moshpit` convention:

- **012 Moshpit**: what happened to / was done by 012 and project activity.
- **Email Log**: correspondence transaction history.
- **0102 Moshpit**: what the agent did, got wrong, repaired, learned, and changed.
- **Red Dog candidates**: generalized rules, guardrails, state machines, proposed tests, and reusable skills nominated from 0102 Moshpit for review.

The repository already has a `docs/012_moshpit/` convention used by corpus-resolution code. `docs/0102_moshpit/` mirrors that naming boundary while keeping agent-learning semantics distinct.

## Storage architecture

### Live mutable log

The private operational event stream belongs to the existing connected work-document system. This proposal does not establish a current connection or grant autonomous append authority; operations must use that system's current owner and policy.

Do **not** commit every daemon heartbeat or raw operational event to Git. That would create noisy history and risk leaking private correspondence metadata.

### GitHub candidate layer

This directory contains sanitized lessons selected by the nomination rule below. Git preserves their reviewable source; inclusion does not establish that a proposed behavior is correct, implemented, independently accepted, or authorized for use.

Current machine-readable candidate lessons live in:

- `red_dog_candidates.jsonl`

The existing `promoted_candidate` value means nomination into this public review set only. The generalized problem/rule notes are not authenticated incident receipts; private incident provenance was not reviewed for this publication. `red_dog_module` names logical concerns, not verified module paths or instructions to create separate modules. `tests` lists proposed acceptance cases, not implemented tests or passing execution evidence. Search existing owners and reuse their implementations before extending them.

No runtime consumer of this file is established by this change. Any future ingestion must use the existing [WRE interface](../../modules/infrastructure/wre_core/INTERFACE.md) and [PatternMemory sink](../../modules/communication/moltbot_bridge/src/reddog_verified_pattern_memory_sink.py), with their current admission, independent verification, activation and retention requirements. The reviewed WRE interface distinguishes non-production candidates from authorized promotion and keeps `promote_variation()` fail-closed pending an independent signed promoter; a stored proposal cannot authorize itself. This directory grants no training, sending, memory writeback, reward, deployment, or other external-effect authority.

## Nomination rule

Nominate a lesson from the private operational log when either:

1. the same lesson occurs at least twice; or
2. a single incident reveals a structural weakness that warrants a reusable guardrail, state machine, invariant, or test.

A nomination should record which follow-up applies:

- the operating prompt/rule was changed;
- a code/test change was made; or
- a concrete reason was recorded for why no system change is required.

Occurrence count and editing a prompt or test do not establish repair completion. The owning work item must meet its acceptance checks and record independently verified outcomes under [WSP 97](../../WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md). Claims of retained improvement additionally require the evidence in [WSP 48](../../WSP_framework/src/WSP_48_Recursive_Self_Improvement_Protocol.md), including later-use benefit where claimed. Preserve rejected and unverified outcomes rather than treating every nominated lesson as learned behavior.

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

`event -> identity/thread grounding -> WSP15 -> policy/skill router -> authorized action -> verification -> action receipt -> candidate nomination -> independent evaluation -> authorized retention`

These candidates describe desired improvements to that existing path. Landing this proposal set does not demonstrate an operational learning loop.
