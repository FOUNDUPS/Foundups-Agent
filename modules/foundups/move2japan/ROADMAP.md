# Move2Japan roadmap

Rebaseline: 2026-10-17 JST, from 012's direct website instruction. The public
product starts with English house search at **move2japan.info**. This supersedes
the March ordering that put the full passport-led journey before housing.

The broader relocation objective remains: discovery, purchase/landing support
through appropriate partners, and settlement. Build and verify one useful layer
at a time. Implementation, deployment and business validation are separate gates.

## Existing groundwork

- BC0 conversation handling and SQLite stakeholder memory exist, with tests.
- The Foundups Mall tile field, detail plane and gesture components exist.
- The shared Foundups account entry exists at `https://foundups.com/member/`.
  It admits invited accounts; it does not establish a paid membership.
- The canonical `move2japan` registry entry describes the YouTube intake as an
  access service. Its token status remains `TOKEN_DEFERRED`.

See [the source/reuse audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md). The old
roadmap's blanket "POC not started" label did not reflect implemented BC0.

## POC: find real houses in English

**Question:** Can a visitor find actual Japanese houses without reading Japanese?

**Implementation slice:** `public/move2japan/` uses the exact shared Mall tile,
detail-plane and gesture components with five attributed Fukui source records.
Properties have listing IDs within the existing Move2Japan context. The catalog
contains only public factual observations; source photos and tours remain linked.

**Acceptance gates:**

- Search/filter real house records and open the selected property's detail.
- Show price and source facts with their original meaning; retain unknowns.
- Show the source and checked date, with current availability unconfirmed.
- Provide working source/contact handoff and visible keyboard/touch controls.
- Preserve the shared Mall behavior and existing YouTube catalog.
- Pass focused data and behavioral checks, then verify the served page.

**Status:** POC source implemented and independently reviewed. An owner-private
[review version](https://move2japan.undaodu.chatgpt.site) was successfully
published on 2026-10-17 JST. The final combined local run recorded 412 passed and
one unchanged BC0 classifier failure; the shared property interaction replay
passed. Browser rendering remains unverified because the managed preview
environment could not start. Exact evidence is in the
[implementation audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md) and
[test log](tests/TestModLog.md). `move2japan.info` domain cutover and a public
served-page check remain open gates.

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
| `move2japan.info` hosting/forwarding | Verified domain configuration and live page response |
| BC0 old domain strings | Valid website/account destinations before a scoped livechat change |
| Registry/product admission | Explicit reconciliation of existing access-service entry; no duplicate ID |
| `move2japan.foundups.com` | Proposed only; provisioning and auth redirect configuration unverified |
| Source feeds, images and refresh | Authorized reuse, refresh cadence and withdrawn-listing handling |
| Publisher upload provider | Verified principal mapping, permission checks and durable storage |
| Shared paid membership | Settled billing events, server authority and benefit/revocation contract |
| Token participation | Existing FoundUps policy and verified implementation; assignment remains deferred |

Related: [stage definitions](docs/04_POC_PROTOTYPE_MVP.md),
[premium model](docs/03_PREMIUM_MODEL.md),
[funnel architecture](docs/07_FUNNEL_ARCHITECTURE.md).
