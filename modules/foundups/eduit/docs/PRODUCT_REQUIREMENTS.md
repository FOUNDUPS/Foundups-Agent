# Product requirements — EDUIT Discovery

Status: specification. Requirements below are present-day design decisions unless
explicitly marked historical. They do not certify educational or scientific efficacy.

## Purpose and users

Give learners access to useful learning through play, then investigate evidence of
strengths that conventional access barriers may leave unnoticed. Serve the learner
first: discovery must never determine whether someone deserves access to learning.
Learners, guardians, educators/research reviewers, vetted opportunity providers,
and curriculum operators have separate roles.

## Functional requirements and acceptance

| ID | Requirement | Minimum acceptance evidence |
| --- | --- | --- |
| R01 | Browser-first on supported phone, tablet, and computer browsers | Documented device/browser matrix; touch and keyboard completion; unsupported features degrade visibly |
| R02 | Low-text, accessible onboarding | Demonstration, optional audio/captions, practice before assessment, no reading-speed penalty by default |
| R03 | One objective-linked game as first POC | Deterministic seeded replay, correct scoring, bounded difficulty, visible pause/stop |
| R04 | Separate placement, practice, and measurement | Distinct modes/events; placement cannot generate a talent classification |
| R05 | Adapt within approved content bounds | Explainable level changes; learner may skip/change difficulty; no live generated code |
| R06 | Offline continuation | Approved cached game runs offline after initial provisioning; progress is not lost on retry |
| R07 | Consent-aware profiles | Guest play does not silently create a cloud identity; distinct learning/research/referral permissions |
| R08 | Strengths evidence with uncertainty | Domain/task/version/context shown; insufficient evidence and abstention supported |
| R09 | Human-reviewed opportunities | No external learner disclosure without current permission; review/appeal and delivery receipt |
| R10 | Governed game improvement | Candidate, frozen baseline, held-out evaluation, separate reviewer, signed release and rollback |
| R11 | Tenant and role isolation | Cross-tenant/cohort/learner access denied; shell receives no child-level evidence |
| R12 | Benefit and operating-cost tracking | Learning/transfer/retention outcomes plus serving, review, support, storage and accessibility costs; no fabricated forecasts |

## First implementation slice

Synthetic/local sessions only. Build a simple visual pattern-rule game with accessible
alternatives, a bounded placement mode, practice feedback, and a replayable local event
record. No accounts, biometrics, chat between users, scholarship integrations, token
payments, or self-modifying production code in that slice. This tests the software
loop, not whether a person is a genius.

## Pilot progression

First qualify functional behavior using synthetic data and adult usability review.
A later supervised school-age pilot requires approved protocol, caregiver authority,
learner assent appropriate to the context, educator review, and a privacy/deletion plan.
Exact age bands, locales, recruitment, sample size, and referral thresholds must be
set by the study protocol before collecting participant data. Infant/Baby0 use is a
separate research track, not implicitly enabled by a general EDUIT account.

## Discovery promise

Long-term target: identify previously overlooked domain-specific potential and improve
access to opportunity. Not promised: IQ measurement, fixed genius labels, guaranteed
scholarships, fluency by an age, clinical diagnosis, or validated prediction from one game.
Famous names are founder analogies, not assessment categories.

## Nonfunctional requirements

Explicit storage/network limits; idempotent synchronization; content/version pinning;
observable error states; content licensing and attribution; accessible input alternatives;
export/deletion handling; no advertising or engagement-maximizing reward mechanisms
in the child learning loop. Performance budgets become measured gates in the POC
on the agreed reference device rather than claims that every device is supported.
