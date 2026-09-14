# Can You Detect AI? - POC Scope

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
