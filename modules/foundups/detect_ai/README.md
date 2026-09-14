# AmIBot

**Working ID:** `detect_ai` | **Owner:** 012 | **Intake:** 0102
**Status:** WSP 109 intake draft; SPECIFIED_NOT_IMPLEMENTED; TOKEN_DEFERRED.

A browser-first social detection game and evaluation FoundUp. Participants consent to an undisclosed human-or-AI partner, chat, lock a classification and confidence estimate, then see the result. Separate leaderboards compare human detectors, agent detectors, and conversational models. A separate Red Dog evaluation measures useful behavior rather than merely appearing human.

## Read order

1. [Outcome](docs/intake/OUTCOME.md)
2. [Solution](docs/intake/SOLUTION.md)
3. [Pain](docs/intake/PAIN.md)
4. [POC scope](docs/intake/POC_SCOPE.md)
5. [Prototype gate](docs/intake/PROTOTYPE_GATE.md)
6. [Skills map](docs/intake/SKILLS_MAP.md)
7. [Manifest draft](docs/intake/FOUNDUP_MANIFEST_DRAFT.md)
8. [Intake source and retrieval limits](docs/intake/INTAKE_SOURCE.md)

Supporting contracts: [benchmark](docs/BENCHMARK_CONTRACT.md), [research](docs/RESEARCH.md), [roadmap](ROADMAP.md), [change log](ModLog.md).

## Execution boundary

This is the intake/documentation node, not a running game or a registered token venture. No runtime manifest, registry/catalog entry, wallet, public route, deployment, or new SKILLz is created by this slice.

012 -> RedDog/0102 intake -> WSP 109 packet -> WRE/architect routing -> bounded workers -> independent verification -> evidence returned to RedDog.

This describes the intended repository workflow, not evidence of running background workers. WRE acceptance and runtime dispatch have not occurred in this session.

Next bounded slice: `DETECT_AI_PREFLIGHT_AND_POC_CONTRACT_PHASE1`. Resolve retrieval gaps, inspect existing module interfaces, and validate the smallest game contract before runtime construction. Proposed product module remains `modules/foundups/detect_ai`; WSP 49 runtime scaffolding is downstream.

## AmIBot research update - 2026-09-15

Display name: **AmIBot**. Tagline: **Can you detect AI?** The original working name is retained only as provenance. Internal ID and path remain `detect_ai` to avoid a second FoundUp, route, or issue.

[Chat, PWA and safety research](docs/CHAT_PWA_SAFETY_RESEARCH.md) is the current technical decision record. Recommendation: an installable browser client with a small server-authoritative Socket.IO service, subject to the existing-owner preflight. Colyseus is the shortlisted alternative, not an additional runtime.

The first playable slice is invite-only, 18+, text-only and clean-chat only. Pre-delivery moderation, report/block/leave and an operator kill switch are pilot gates. Mature/NSFW rooms and their stronger age-assurance integration are deferred and disabled. Phone-hosted model inference is a later opt-in practice experiment, not the trusted benchmark or an always-on background worker.

Documentation is on draft PR #1751; issue #1750 remains the bounded preflight/build-contract handoff. No application has been built or deployed by this research update.
