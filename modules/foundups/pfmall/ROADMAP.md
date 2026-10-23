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
- Specified only (updated 2026-10-18): AutoPost Live mode, general creator
  live-session adapter and provider-confirmed live catalog projection. External
  AutoPost already implements browser capture/recorded-file upload; continuous
  streaming and durable live control remain unimplemented.

## Private item capture — 2026-10-23

012's current goal is AutoPost clothing photographs grouped into items inside
the shared Mall. Public Shop presentation remains undecided; the default is
private local capture followed by an authenticated, scoped attachment. Read
[AUTOPOST_ITEM_CAPTURE_HANDOFF.md](AUTOPOST_ITEM_CAPTURE_HANDOFF.md) and the
[external AutoPost roadmap](https://github.com/FOUNDUPS/autopost/blob/main/ROADMAP.md).

- [x] C0: inspect current owners, specify local item-photo types and private
  handoff, correct stale AutoPost status, attach documentation/navigation.
- [x] Repair bounded request-prefix/clothing aliases in the existing member
  matcher; retain unsupported constraints and grouped-domain command refusal.
- [ ] C1: implement AutoPost's item grouping/review and draft persistence using
  its existing media repository; prove two items, reload, missing/duplicate
  originals, temporary fallback and late/disabled AI behavior.
- [ ] C2: implement the authenticated shared media/private item adapter with
  verified principal/FoundUp scope, remote-byte checks, idempotent revisions,
  conflict handling and truthful durable acknowledgment.
- [ ] C3: connect permitted garment records to the existing grouped Mall field;
  prove cross-owner denial, media access, revocation and navigation parity.
- [ ] C4: decide public/invited-vendor visibility separately, then prove the
  corresponding authorization, review and media-cache boundaries.
- [ ] C5: independently implement sourcing/quote/order/fulfillment/settlement.

C0 is a contract and discovery repair, not working capture-to-Mall delivery.
GetK #802 remains an unmerged comparison source with a public-listing default;
do not merge or publish it as a shortcut. No new camera, identity/blob store,
Shop website, public catalog entry or WRE execution service is needed for C1.
Existing public GotJunk discovery remains unchanged. Runtime/provider choice,
deployment and physical-phone acceptance require their own evidence.

## P1 — Mobile creator studio: evidence before implementation

**WSP 15 documentation slice score:** complexity 2 + importance 4 + deferability
4 + impact 4 = **14 / P1**. This is a bounded planning priority, not a runtime
allocation or a reprioritization of the existing P0 repair.

Goal: one authorized creator selects Live in AutoPost, starts a YouTube show, appears in
Play from provider-confirmed evidence, recovers from tested interruptions, ends
explicitly and starts a later event with the same valid input. The next agent
must consume the [contract](../docs/mobile_studio/PFMALL_MOBILE_STUDIO_CONTRACT.md),
[API register](../docs/mobile_studio/PFMALL_CREATOR_LIVE_API_CONSTRAINTS.md) and
[machine outcome](../docs/mobile_studio/mobile_studio_outcome.v1.json).

| Slice | Work and promotion evidence | Status |
|---|---|---|
| MS0 | Research source/API constraints and AutoPost ownership; record pain, reuse, obstacles and AC01–AC11 | Documentation delivered; 2026-10-18 external-owner correction |
| MS1 | Scope creator/channel OAuth; create/bind/start/end and reusable-input adapter; prove AC01–AC04 | Planned; actual project/channel checks and admission required |
| MS2 | AutoPost media adapter: MS2A foreground WebRTC/relay proof (AC10–AC11); MS2B measured continuity and browser/native choice (AC05–AC06) | Planned; phone, control profile, relay, codec and lifecycle evidence required |
| MS3 | Project fresh permitted live state into Play; test embed/watch fallback and AC07–AC08 | Planned; depends on secure service and mobile spike |
| MS4 | Production OAuth/quota, data retention, reconnect/runbook and AC09 | Planned; release and operational evidence required |
| MS5 | Second OS, richer scenes, OBS integration, multistream, guests and independent paid services | Deferred; each needs its own measured case and contract |

The [external AutoPost Phase 4B](https://github.com/FOUNDUPS/autopost/blob/main/ROADMAP.md#phase-4b--autopost-live-mode-planned)
owns the product increments. MS2A proves one foreground camera/mic route for
10 minutes with AI disabled and A/V observed in remote YouTube playback. It may
be separately admitted after MS0 and verified attended-control, exact destination
and relay-admission checks, before durable MS1 completion. Integrated MS2
promotion requires completed MS1, MS2A and MS2B; MS3 retains its MS1/MS2 gates.
The current browser OAuth can support that bounded proof, but durable
machine-to-machine recovery still needs the shared service.
Preserve ordinary capture gestures and four primary Options tabs. Basic Live
does not depend on Lick enrollment, receipt accounting or memberships.

Start with a separately admitted MS1 control slice or MS2A attended feasibility
slice after rechecking current main, related PRs and the selected prerequisites.
Documentation completion is not live-streaming, device, deployment,
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


## Shared responsive discovery — 2026-10-18

- Implemented in this PR: responsive category tracks, vertical category browsing,
  horizontal touch/drag/button navigation, local row position restore, and one
  catalog query API shared by RedDog text controls and the existing dispatcher.
- Preserve the common shell for creator, housing, vehicle, clothing and other
  catalog projections. Add real metadata/adapters under existing catalog ownership;
  no independent per-FoundUp browsing app is required.
- Next: paged catalog provider and DOM virtualization with measured large-catalog
  performance; current rows render the loaded catalog and are not infinite ingestion.
- Next: authenticated resident RedDog conversation/voice adapter (existing admission
  plan above), calling the same bounded search/projection APIs.
- Next: explicit, revocable principal-scoped preferences and transparent ranking;
  `creator === '012'` personal scope is not digital mapping or recommendation.
- Next: device Safari/pinch/accessibility verification, provider-confirmed live tiles,
  independent supporter benefits/follow persistence and controlled muted previews.
  Six simultaneous autoplay streams are not required for responsive browsing.
