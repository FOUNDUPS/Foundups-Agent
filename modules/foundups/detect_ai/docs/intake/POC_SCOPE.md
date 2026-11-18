# AmIBot - POC Scope

## Minimum Viable POC
An invite-only, text-only browser game that can run a real human-human round and a human-model round through the same visible interface, record a locked guess and confidence, and reveal the correct server-held assignment. Start with one approved small Qwen-class checkpoint; adding one approved hosted baseline is optional only after the core loop works.

## Included in POC
- Declared adult pilot cohort; consent notice; anonymous public landing and invite-gated play.
- Real human availability, randomized focal-round assignment and explicit practice fallback.
- One server-authoritative state machine, message limits, timeout handling and report/leave controls.
- One approved model adapter with server-held credentials, budget cap, pinned configuration and no external tools.
- Locked verdict and probability; simple nontransferable points; private provisional results.
- Minimal consent and outcome records; no general public transcript export.

## Explicitly Excluded from POC
Transferable tokens, wallets, betting, chain writes, token conversion promises, public monetization, agent judges, many model adapters, voice/video, automatic training, Discord-specific runtime, production claims, and a new orchestration system.

## Success Criteria
Proposed pilot gate: at least 20 consenting adults and 100 valid focal rounds with at least 40 in each assignment class; log recruitment, assignments, completion and exclusion counts. This demonstrates the flow, not statistical superiority.

Tests must prove: client cannot read truth/model metadata before permitted reveal; verdict is immutable; duplicate submissions cannot double-score; unauthorized session access is denied; missing humans never silently become AI; safety/disconnect outcomes are explicit; credentials stay server-side; unsafe content is reportable; timeout/abandonment statistics remain visible.

Proposed usability target: at least 80% completion among matched pilot rounds, with queue delay and p95 response time reported separately. Thresholds may be revised prospectively from pilot evidence, never after viewing competitive results to manufacture a win.

## Trust Wedge
Free participation, honest identity reveal, clear score explanations and a published method. No wallet, token purchase or private-archive upload is required.

Status: NOT_BUILT. A mocked or transcript-only demo does not satisfy the live-match POC gate.

## Additional mandatory POC acceptance - AmIBot

Implement and test human-human clean chat first, then the human/AI game, then the combined phone experience. Use a documented adult-only invite-admission process and a staffed pilot window. Do not substitute a self-declared birthday for verified age or label clean stranger chat child-safe.

Before any participant receives a message: authenticate the session; check round membership and policy; apply server-side rate/length checks, profanity rules and a tested contextual safety check (or pre-delivery human review in a tightly bounded pilot). Apply this to human and AI messages alike. Hold/reject uncertain or unavailable moderation; never stream unchecked model tokens. Report, block, immediate leave, blocked-pair exclusion and an operator kill switch must function.

PWA acceptance: install on tested iPhone and Android devices; keep composer and leave/report controls visible above the keyboard; handle network changes and app suspension; restore server state or terminate explicitly; do not cache chats/auth/age proofs or replay expired messages. Updating the service worker must not force a live round reload. Offline mode is the shell/help only, not random chatting.

No mature room, public under-18 access, local-model ranked trial, uploads, video/voice, automatic training or economic rewards in the POC. Full source, safety and real-device tests remain NOT_RUN.
