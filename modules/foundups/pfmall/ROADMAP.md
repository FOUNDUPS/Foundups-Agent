# p.fMALL Roadmap

## Current baseline

- Implemented: manifest discovery/validation, catalog and tile projection,
  route resolution, optional advisory overlays, a read-only Python/FastAPI
  surface, static shell UI, member catalog export, presentation policy, and
  verification-gap guarding.
- Implemented in `public/member/`: admitted-member PWA, video Mall,
  shell-local FAQ concierge, and bounded browser control dispatcher.
- Not implemented: authenticated resident RedDog conversation adapter,
  browser-to-OpenClaw policy admission, or browser-to-Hermes execution.
- Specified only (2026-10-17): mobile creator studio, general creator live-session
  adapter and provider-confirmed live catalog projection. The existing YouTube
  broadcaster remains channel-specific; no native phone media engine was added.

## P1 — Mobile creator studio: evidence before implementation

**WSP 15 documentation slice score:** complexity 2 + importance 4 + deferability
4 + impact 4 = **14 / P1**. This is a bounded planning priority, not a runtime
allocation or a reprioritization of the existing P0 repair.

Goal: one authorized creator starts a phone-produced YouTube show, appears in
Play from provider-confirmed evidence, recovers from tested interruptions, ends
explicitly and starts a later event with the same valid input. The next agent
must consume the [contract](../docs/mobile_studio/PFMALL_MOBILE_STUDIO_CONTRACT.md),
[API register](../docs/mobile_studio/PFMALL_CREATOR_LIVE_API_CONSTRAINTS.md) and
[machine outcome](../docs/mobile_studio/mobile_studio_outcome.v1.json).

| Slice | Work and promotion evidence | Status |
|---|---|---|
| MS0 | Research current source/API constraints; record pain, reuse, obstacles and AC01–AC09 | Documentation delivered by this slice |
| MS1 | Scope creator/channel OAuth; create/bind/start/end and reusable-input adapter; prove AC01–AC04 | Planned; actual project/channel checks and admission required |
| MS2 | Select one phone platform; preview/capture/encode/record/direct RTMPS; prove AC05–AC06 | Planned; device and native dependency decision required |
| MS3 | Project fresh permitted live state into Play; test embed/watch fallback and AC07–AC08 | Planned; depends on secure service and mobile spike |
| MS4 | Production OAuth/quota, data retention, reconnect/runbook and AC09 | Planned; release and operational evidence required |
| MS5 | Second OS, richer scenes, relay, guests and independent paid services | Deferred; each needs its own measured case and contract |

Start with a separately admitted MS1 slice after rechecking current main and
related PRs. Documentation completion is not live-streaming, device, deployment,
membership or payout evidence. Each implementation PR updates the affected
README, INTERFACE, ROADMAP and ModLog before promotion. Keep unrelated roadmap
priorities and active member-runtime PRs intact.

## P0 — Tier-0 retrieval repair

- [x] Add root `README.md` and `INTERFACE.md` with current authority truth.
- [x] Add a real-repository Holo regression for the registered PFMall module.
- [ ] After merge, rebuild and activate one exact-main Holo generation, then
  prove an owner query is `CURRENT`, gap-free, read-only, and digest-stable.

## P1 — Resident RedDog adapter

- [ ] Bind the Mall client to the authenticated resident conversation ingress;
  do not treat `pfmall-control-dispatcher.js` as that transport.
- [ ] Define durable replay/idempotency and new-conversation creation before
  any mutation-bearing request is admitted.
- [ ] Translate only bounded, authenticated RedDog projections into existing
  Mall presentation commands.
- [ ] Preserve OpenClaw as policy/control supervisor, WRE as execution and
  verification authority, and Hermes as a bounded admitted leaf worker; none
  of those authorities belongs in the browser.

## P1 — Runtime convergence and deployment hardening

- [ ] Resolve the inherited original pre-rebase `f06ca1f` module-suite
  baseline: 19 failing node IDs / 588 passing. The failures cover catalog
  enum/projection drift, stale member-entry/concierge expectations, a
  hard-coded `O:` fixture, and absent tracked media directories. This Tier-0
  slice reproduced all 19 at that baseline and does not repair or quarantine
  them. Its exact post-#1538 Git parent is `69b7f073`.
- [ ] Reconcile the Python catalog projection and `public/member/` catalog
  generation so one canonical source owns each field.
- [ ] Put authentication/rate limits in front of the FastAPI surface before any
  production exposure containing non-public data.
- [ ] Convert aspirational isolation/sentinel clauses into implemented,
  evidence-backed gates one bounded layer at a time.

## P2 — Structural remediation

- [ ] Plan a separate, import-compatible migration from flat root Python files
  to `src/` per WSP 49.
- [ ] Add module-local dependency and memory contracts per WSP 12/60.
- [ ] Run FMAS and complete dependency/import analysis before any move. No
  deletion or broad restructuring is part of the Tier-0 repair.
