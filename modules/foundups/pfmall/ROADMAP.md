# p.fMALL Roadmap

## Isolated proposal host bootstrap candidate — 2026-10-26

The source candidate supplies a separate ASGI factory around the existing draft
handler and verifier, with explicit bounded server policy loading and per-app
policy. Only proposal and minimal health routes are exposed. Local814 cases pass,
including all786 originals and28 test-first host cases; independent/publication
review remains required. This is not a deployed host or live Clerk qualification.
Next serving layer: package/qualify the actual server and minimal source closure,
then administer policy/cloud limits and prove a real session before browser wiring.
Keep the existing six Node functions and shared ignored source untouched.

## Authenticated member draft component — 2026-10-26

Locally implemented under15/P1 allocation: explicitly configured Clerk bearer
verification at `POST /pfmall/proposals`, delegated to the existing genesis
preflight/mapper. Default503; no client flags/cookies/UID authority. Qualification
and publication are tracked in tests/TestModLog and the dedicated PR. This is
not a deployed public claim host or durable project admission.

Next: bind independently administered provider/issuer/origin/public key and prove
one real member session in the selected deployed host; define current-session/
revocation and abuse policy. Then issue a fresh repository challenge and persist
its consumption plus immutable receipt atomically in the selected intake owner.
Preserve draft versus membership/claim/issuer/work/token authority separation.
Do not attach an inactive browser form or infer live authority from offline RSA.

## FX1 public discovery — 2026-10-25

- Implemented locally: homepage FX navigation to the existing public `/f/`
  renderer, explicit declared-ticker framing and optional symbol search. No
  registry, member catalog, router or trading surface is created.
- Existing route/gateway test owners pass; details and limits are in
  [tests/TestModLog.md](tests/TestModLog.md). Browser/deployment acceptance,
  external project admission/claims, token confirmation and venue/liquidity
  remain independent future layers.

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

## Responsive HPC PoC — shared WikiTube theater and phone grid (2026-11-11; acceptance open)

012's clarified PoC requires **one shared Mall with two responsive presentations**.
Desktop uses the centered main video, search directly below it, and horizontal
thumbnail strip beneath search. Phone uses the compact three-column video grid,
fixed header and bottom thumb controls. This is not permission to build another
HPC shell, change every FoundUp's layout, or call a density-only patch complete.
The detailed contract and planning allocation are in [HPC H1](../hpc/ROADMAP.md#h1--responsive-wikitube-style-discovery-and-shared-thumb-dock-specified-012-request-2026-11-11).

### Required planning gate

Before another product/build mutation, reconcile the current root/module roadmaps,
owning INTERFACE, actual code, tests and active PRs with the request. Record its
stage, owner, fit/drift decision, superseded requirement, acceptance and recovery
path. Apply the existing [strategic diligence skill](../../ai_intelligence/ai_overseer/skillz/strategic_diligence_gate/SKILLz.md)
for cross-module/high-impact decisions; do not create a duplicate build skill.

WSP 97 section 1.2.1 asks **Do I need it? Can I afford it? Can I live without it
now?** These questions project WSP 15's C + I + D + Impact scoring. WSP 30, not
WSP 15 alone, supplies staged build orchestration. Record scores and verification
cost before implementation; no unauthenticated planning record grants execution
or merge authority. H1 records documentation 14/P1, responsive repair 17/P0, and
scoped search 13/P1, with rationale. These are task-scoped planning priorities,
not reprioritization of unrelated system work.

### Reuse and current gaps

- Inspect `public/member/` field, player, existing theater/queue rendering,
  scoped catalog, query and state APIs before proposing markup or another player.
  WikiTube TV source/history remains a retrieval target, not a verified current
  integration. Do not repeat an unsourced historical deployment address.
- PR #2357 used three columns at every width. The original CSS-only #2359
  draft reproduced a six-column display with three-column player placement.
  The merged #2359 repair mounts the existing stage and queue as a desktop
  theater and preserves the phone layout and shared media session.
- Desktop requests first-video startup playback and sequential queue advancement.
  Preserve provider controls, one active player, and truthful blocked-autoplay
  recovery. A thumbnail, iframe load or API availability flag is not playback.
- Phone tap replaces the selected tile with the shared player in its original
  row. Nearby tiles reflow and the original tile returns on close. Measure
  the provider viewport and keep controls clear of the iframe.
- Scoped search repopulates the existing queue/field. It supersedes hidden-search
  presentation only within the active permitted catalog; global/remote search is
  later work and never bypasses authorization.

### Ordered slices and acceptance

| Slice | Stage / work | Promotion evidence |
| --- | --- | --- |
| PFWD-0 | Reconcile current owners, source history and acceptance | Roadmap/contract references, source SHAs, existing-test inventory and bounded recovery plan; documentation is not runtime success. |
| PFWD-1A | PoC: desktop theater plus preserved phone grid | PC and phone composition, correct click target/player, one iframe/audio session, original-ID return, resize/rotation and other-FoundUp regressions. |
| PFWD-1B | PoC: scoped search and phone dock | Search between desktop main video and bottom tiles; phone thumb access, scoped install identity and optional local dictation. Verify loaded-catalog filtering, empty results, queue advancement, safe areas, keyboard and standalone launch. |
| PFWD-1C | PoC entry and membership | Dedicated public HPC host, invited FoundUps member access and scoped sign-in return. Verify each entry independently. |
| PFWD-2 | Prototype: resident speech and agent controls | Red Dog hold-to-talk via authenticated resident ingress, admitted device-compatible selection, cancellation, permission denial and bounded action receipts. |
| PFWD-3 | Prototype: AutoPost handoff | Existing capture owner, explicit permission, approved route/origin and return state; no copied camera stack. |
| PFWD-4 | MVP hardening | Measured large-catalog performance, privacy/abuse review, provider/device recovery and release evidence beyond the PoC acceptance matrix. |

Do not defer ordinary desktop/phone playback verification to PFWD-4: it is a
PFWD-1 PoC acceptance gate. Extend the existing browser fixtures; phone emulation
is not physical iPhone standalone evidence. Preserve shared search, channel
expansion, protected operations and other projections.

HPC is the first scoped phone dock consumer. The left `+` opens Home,
disclosure and device-model availability. The search mic supports local
recognition when available or opens the input for keyboard dictation. The
right Red Dog button opens the public briefing. Resident hold-to-talk and
actual model loading belong to PFWD-2. AutoPost capture belongs to PFWD-3.

The existing [media incident](MEDIA_PLAYBACK_INCIDENT_HPC.md) owns provider-error,
bot-challenge, origin/referrer and availability evidence. Fix application defects
without inventing authentication bypasses or claiming an unobserved iPhone pass.
Report commit, qualified merge, main verification, deployment and PC sync as
separate outcomes. This roadmap/skill update changes no runtime or live site.

## Desktop poster browsing PoC

012's desktop reference calls for a dense wall of mixed FoundUp cards and
a full viewer with WikiTube-style playback. This section covers the
ordinary invited Mall. HPC's scoped desktop theater and phone grid use
[H1 acceptance](../hpc/ROADMAP.md).

The [navigation contract](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#46-desktop-poster-browsing)
maps the member entry, tile field, state, quick view and full player owners.

1. **Implemented.** Use the existing grid on fresh wide fine-pointer entry.
   Restore saved layout and position through the existing state owner.
   Video lanes, app cards, repositories and services use the same catalog.
2. **Implemented.** Open the shared full player from video posters. Keep
   one active player with the selected lane's queue and provider controls.
   Close returns to the selected tile. Card selection opens quick view and
   listings use their detail view.
3. **Specified.** Qualify muted hover for a rights-cleared first-party clip in a separate
   test. Start with one preview and measure playback requests and bytes.
   The [media contract](../docs/PFMALL_MEDIA_DELIVERY_CONTRACT.md#84-desktop-previews-and-bandwidth)
   defines the provider viewport and preview constraints.

The desktop browse slice is WSP 15 priority 13/P1 (C2, I4, D3, Impact4).
The [member browser test](../../../public/member/tests/README.md#member-poster-grid)
covers fresh and saved layout, mixed card selection, keyboard and Ctrl+wheel
navigation, one active player, focus and scroll return, and provider dimensions.
Release qualification requires a real invited session and a deployed asset match.
