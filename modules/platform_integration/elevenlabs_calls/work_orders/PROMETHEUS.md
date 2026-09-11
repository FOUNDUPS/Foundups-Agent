# Prometheus principal brief — Japanese message calls

Principal: 012. Machine actor: 0102. Objective: “I tell you to make a call; you
call the intended person in Japanese and leave my message.” Deliver a working,
tested prototype first, then a sound-quality proof of concept. No MVP expansion.

## Existing implementation and provenance

Repository: FOUNDUPS/Foundups-Agent. Draft PR: #1674. Baseline:
`196976aea3516426552238e70be54e015c397999`. The existing ElevenLabs/Twilio module already
implements prepared requests, Japanese agent provisioning, optional spoken trigger,
status and durable duplicate suppression. Historical scoped result: 91 passed,
100% new-adapter coverage. Those tests mock provider/model boundaries. No provider
account was provisioned and no real call or mailbox test was performed.

## Plan and recursive review

Coordinator normalizes this brief into the eight M2M orders, binds dependencies
and exact owners, then supplies CONTRACT plus one order to each assigned worker.
Verifier evaluates evidence against acceptance; coordinator returns a narrow repair
order for an observed failure. Never replace missing evidence with a confidence
claim. Use the existing architecture and runtime authority, not another dialer or
orchestrator. WSP 21 and 99 govern the prompt contracts; the Prometheus annex is
non-operational inspiration and grants no execution authority.

The minimal CLI path is 01 → 02 → 03. Full assistant invocation adds 04 → 05 →
06 → 08. Sound experiments 07 follow 03 and do not block prototype closure.

## WSP 97 authoring evidence — 2026-09-11

- Retrieve: inspected AGENTS.md, WSP 21/99, Prometheus annex, `prompt/Prometheus.md`,
  `prompt/swarm/0102_M2M_SCHEMA.yaml`, existing runtime work-order owners and module
  README/ROADMAP/ModLog. WSP 00 software check passed. Holo owner query returned
  `MISSING_GENERATION_BINDING`, freshness `UNKNOWN`, missing freshness receipt;
  repository lexical evidence supplied the ownership fallback. No reindex claim.
- Research: canonical WSP 99 compact envelope and WSP 21 delivery requirements
  control; do not invent a signed runtime format or claim an installed phone tool.
- Micro-pass: prepared requests work offline; provisioning, live message delivery
  and real microphone inference remain separate unverified boundaries.
- Macro-pass: shared voice ownership stays in CLI/voice_command_ingestion; one
  carrier adapter stays here; runtime authority stays with RedDog/WRE.
- Hard-think: profile configuration cannot prove a call arrives in Japan or that
  voicemail playback is complete. Require direct live evidence.
- Dialectic sweep: compare rebuilding a voice stack with reusing the existing
  adapter; reuse wins. Separate planned dispatch from actual authorized execution.
- First principles: bind intent → contact/message → one durable request → call →
  observed result. Sound quality is an experiment after delivery works.
- Execute: author eight work specifications, shared contract, result template and
  index; validate JSON structure, dependency graph and repository references, then
  run existing commit gates. This authoring slice does not change live acceptance.

WSP 15 authoring allocation: complexity 2, importance 4, deferability 4, impact 4:
14 / P1. Per-assignment token budgets are in `X.token_budget`. Actual execution
state, coherence measurements and token consumption are not invented here.
