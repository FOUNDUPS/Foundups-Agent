# Move2Japan roadmap

Rebaseline: 2026-10-18 UTC, from 012's direct website instruction and explicit
requirement to integrate inside the current Play Foundups Mall. The public
product starts with English house search at `/member/?foundup=move2japan`, with
**move2japan.info** as its intended public brand/domain. This supersedes
the March ordering that put the full passport-led journey before housing.
012's subsequent correction rejects the first marketing-led card grid: the POC
must use the existing Mall boot, shell, registry, account and PWA owners, with
houses immediately visible and left/right within an area, up/down between areas.
The former `/move2japan/` application composition is now a redirect alias.

The broader relocation objective remains: discovery, purchase/landing support
through appropriate partners, and settlement. Build and verify one useful layer
at a time. Implementation, deployment and business validation are separate gates.

## Existing groundwork

- BC0 conversation handling and SQLite stakeholder memory exist, with tests.
- The Foundups Mall tile field, detail plane and gesture components exist.
- The shared Foundups account entry exists at `https://foundups.com/member/`.
  It admits invited accounts; it does not establish a paid membership.
- The same canonical `move2japan` registry entry now describes a discoverable,
  incubating FoundUp with a public POC and declarative manifest. `/f/move2japan`
  and the public portfolio provide **Browse houses** inside the Mall. Its
  `discoverable_only` status preserves the protected app gate; `TOKEN_DEFERRED`
  remains unchanged.

See [the source/reuse audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md). The old
roadmap's blanket "POC not started" label did not reflect implemented BC0.

## POC: find real houses in English

**Question:** Can a visitor find actual Japanese houses without reading Japanese?

**Current source implementation:** `public/member/index.html` selects the
registered public housing product with exactly one `foundup=move2japan` value.
The domain adapter mounts that shell's housing templates into the existing
field and shared RedDog plane. Guest browsing does not wait for account services;
existing member identity is read through the full Clerk/invite/username admission
boundary. Shared state and `/member/` PWA owners preserve product navigation and
the explicit account return. Eight attributed Fukui records occupy geographic rows across
five municipalities, including multiple houses in Wakasa, Sakai and Eiheiji.
Country/prefecture/city/locality filters and city/locality grouping control the
projection. Land status and nullable asking/negotiable prices retain source
unknowns. Properties keep listing IDs within `foundup_id=move2japan`; photos and
tours remain at the source.

**Acceptance gates:**

- Show houses in the first Mall viewport; keep account and RedDog anchors usable.
- Navigate left/right within a geographic row and up/down between rows, with
  native touch, desktop drag, visible controls and directional keyboard access.
- Filter by country, prefecture, city/town, suburb/locality, recorded land status
  and price. Keep unsupported coverage and empty results explicit.
- Open search from the same RedDog/Filter controller; preserve modal focus and
  form scrolling while the field updates behind it.
- Search/filter real records and open the correct selected house; adjacent detail
  navigation stays in its area. Preserve row position and stable listing focus.
- Show price and source facts with their original meaning; retain unknowns.
- Show the source and checked date, with current availability unconfirmed.
- Provide working source/contact handoff and visible keyboard/touch controls.
- Preserve the shared Mall behavior and existing YouTube catalog.
- Keep public product discovery registered at `/f/move2japan`, with the protected
  `/f/move2japan/app` gate distinct from browsing.
- Preserve separate video/product navigation state and restore safe filters after
  explicit shared-account admission. Sign-out/account changes clear stale identity.
- Cache only public shell/catalog paths and retain original observation dates
  during an offline fallback; unavailable data must remain visibly unavailable.
- Pass focused data and behavioral checks, then verify the served page.

**Status:** Shared-Mall integration is implemented in source and has focused
independent reviews. Current revision-specific checks and concurrent-main
reconciliation belong to the
[implementation audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md) and
[test log](tests/TestModLog.md). Firebase production hosting is not deployed in
this session; its established target is project `gen-lang-client-0061781628`,
site `foundupscom`. Authenticated deployment access is unavailable here. Browser
interaction/visual checks, a served-page check and `move2japan.info` forwarding
cutover remain distinct open gates.

**Superseded history:** The first five-house grid had a 412-pass/one-failure
receipt. The subsequent eight-house standalone composition had a
696-pass/one-unchanged-BC0-failure receipt and was privately published on
2026-10-17 at 01:04:36 UTC from Site commit
`77db7957ce7527a0f614de545317ac03842c876b`, tracked by historical
[PR #2151](https://github.com/FOUNDUPS/Foundups-Agent/pull/2151). Those receipts
predate the actual registered Mall product and do not verify it. The same
[private Site](https://move2japan.undaodu.chatgpt.site) is a review mirror only.

No publisher signup, managed uploads, paid inventory or crawler is claimed by
this slice. Source refresh and removal handling must be established before
presenting the catalog as a continuously current national service.

## Prototype: authorized publishers can submit houses

**Question:** Can an owner or realtor/broker register and publish a legitimate
akiya through a reviewed workflow?

**Status:** Pending.

**Required work:**

- Reuse the shared Foundups account, with a verified identity/authorization
  boundary between Clerk membership and any GotJunk/Firebase publisher provider.
- Add publisher roles for owner, authorized representative and agency/broker;
  verify ownership/authority and applicable brokerage registration separately.
- Reuse existing GotJunk/Mall listing and upload owners after provider proof;
  do not create a second unrelated publishing stack.
- Support durable drafts and uploads, media/advertising rights, moderation,
  reviewed publication, correction and withdrawal.
- Carry original source, publisher, review and availability evidence per listing.
- Provide a clear handoff to the responsible publisher or verified partner.

**Acceptance:** A real authorized publisher signs in, submits a property and
permitted media, receives review, and can update or withdraw the resulting public
listing. A mock form, local draft or unverified broker badge does not pass.

## MVP: paying customers receive a service

**Question:** Will customers pay for a specific delivered Move2Japan benefit?

**Status:** Pending until actual customer payment and delivery are evidenced.

**Required work:**

- Define the Basic/member offering, pricing and any release delay through the
  verified shared Foundups billing model. This roadmap invents none of them.
- Bind a settled payment to the shared account, plan, period and offered benefit.
- Derive current entitlements server-side before releasing restricted records.
- Deliver the configured benefit, such as earlier curated discovery/alerts or
  partner-authorized exclusive offers, and record delivery.
- Handle payment replay, cancellation, refunds, expiry and access revocation.
- Reconcile real paying-customer and benefit-delivery evidence.

**Acceptance:** An actual customer pays for the configured service and receives
it, with reconciled payment and entitlement state. Free accounts, trial users,
premium interest, simulated balances and tokens do not establish MVP.

Public akiya bank inventory is not exclusive simply because Move2Japan finds it.
Any earlier-discovery benefit must distinguish source publication, discovery,
verification, member release and public release. Restricted inventory must never
ship in public JSON or a service-worker cache and rely on client-side hiding.

## Later relocation layers

Retain the BC0-BC7 intent-to-settlement design for optional guidance: readiness,
immigration/job pathways, income planning, location matching, landing housing,
document support, and settlement. Add concierge and city/family/education paths
when the corresponding source, partner and account capabilities are evidenced.
The existing passport-first conversation does not gate public house search.

## Known follow-ups and integration gates

| Item | Required evidence |
| --- | --- |
| Foundups production release | Authenticated release to Firebase project `gen-lang-client-0061781628`, site `foundupscom`, then served-page and browser checks |
| `move2japan.info` hosting/forwarding | Verified domain configuration and live page response |
| BC0 old domain strings | Valid website/account destinations before a scoped livechat change |
| Public registry/product discovery | Reconciled in source under the same ID; validate the generated public projection with the release |
| Protected publisher/app admission | Separate account/publisher capability and authorization evidence; public `discoverable_only` is not admission |
| Earlier `move2japan.foundups.com` proposal | Superseded as an independent PWA plan; any future alias must lead to the shared product and preserve account boundaries |
| Source feeds, images and refresh | Authorized reuse, refresh cadence and withdrawn-listing handling |
| Publisher upload provider | Verified principal mapping, permission checks and durable storage |
| Shared paid membership | Settled billing events, server authority and benefit/revocation contract |
| Token participation | Existing FoundUps policy and verified implementation; assignment remains deferred |

Related: [stage definitions](docs/04_POC_PROTOTYPE_MVP.md),
[premium model](docs/03_PREMIUM_MODEL.md),
[funnel architecture](docs/07_FUNNEL_ARCHITECTURE.md).
