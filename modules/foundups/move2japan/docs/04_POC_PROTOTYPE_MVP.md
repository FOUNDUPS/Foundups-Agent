# Move2Japan: POC, prototype and MVP

Current authority: 012's website instruction and 2026-10-18 shared-Mall
integration correction. This updates the
build order captured in the 2026-03-07 voice conversation while retaining the
broader relocation vision. The current primary domain is **move2japan.info**.

## POC: searching real houses

**Proof sought:** People who do not read Japanese can find actual houses,
understand the available facts and reach the original listing/contact.

The current public English catalog mounts inside the existing
`/member/?foundup=move2japan` shell with eight attributed Fukui observations.
`/f/move2japan` and the public portfolio link to this product; `/move2japan/`
only redirects. Account access, the middle house field, bottom RedDog anchor,
state and PWA service worker belong to the existing Mall. Both the first
five-house grid and the subsequent separate page importing Mall components are
superseded by this integration.

Acceptance requires:

- Registered public discovery inside the actual Mall boot, preserving the
  separate protected-app gate. Guest browsing remains available without Clerk
  or Firestore; existing account admission is read through the shared owner.
- Houses visible immediately, with left/right within an area and up/down between
  areas. Multiple source houses in Wakasa, Sakai and Eiheiji make within-area
  browsing concrete.
- Country, prefecture, city/town, suburb/locality, land-status and price filters
  in the same public RedDog plane. City/locality rows are projections of the
  shared field, not separate FoundUps or replacement channel identities.
- Correct selected detail and adjacent navigation within its area, with touch,
  desktop drag, visible controls and keyboard access.
- Stable row/listing focus through result updates and modal search that preserves
  form scrolling, Escape and focus return.
- Separate product/video state, bounded account return and public-only PWA
  caching that preserves source observation dates. Account changes clear stale
  identity without granting publisher or paid-service rights.
- Original-source links, observation dates, clear unknowns and source-listed
  availability boundaries. A negotiable price stays null; unknown land stays
  unknown. Source photographs remain at the source until reuse is authorized.

**Status:** Integration implemented in source, with focused independent reviews.
The audit and test log own revision-specific verification and any concurrent-main
reconciliation. Firebase production hosting, browser interaction/visual checks
and primary-domain forwarding remain separate open gates. The 2026-10-17 private
Site publication, historical PR #2151 and 696-pass/one-BC0-failure receipt belong
to the superseded separate composition. The private Site is a review mirror;
its publication does not establish a production release or paying-customer MVP.

The existing BC0 chat and SQLite memory are completed groundwork. They remain
available for optional relocation guidance and do not gate public house search.

## Prototype: people can publish their akiya

**Proof sought:** A real owner, authorized representative or realtor/broker can
sign in, submit a property and permitted media, receive review, and update or
withdraw the resulting publication.

Reuse the shared Foundups identity and existing GotJunk/Mall publication owners
after their provider and authorization contracts are proved. Add publisher
roles, property/advertising authority, applicable broker verification, durable
uploads and moderation. Preserve provenance and distinguish owners from
licensed agencies.

**Status:** Pending. A mock submission screen or browser-only draft is not a
completed prototype.

## MVP: customers actually pay

**Proof sought:** Actual customers pay for and receive a configured offering.

The proposed Basic/member benefit may be earlier curated discovery, alerts or
partner-authorized offers. Its price, release delay and shared-plan mapping
remain to be established. Payment must be settled and reconciled to the shared
account, and the promised benefit must be delivered under current server-verified
entitlement. Cancellation, refund, expiry and revocation must work.

**Status:** Pending. Signups, a free trial, premium interest, token balances and
a checkout button do not meet the paying-customer definition.

Restricted records must not be distributed in a public static catalog and merely
hidden in the browser. Public bank inventory must not be described as exclusive
without a real partner agreement.

## Later relocation support

The March plan remains useful for optional personal guidance: BC0 intake,
readiness, migration and income pathways, location matching, housing handoff,
paperwork, arrival and settlement. City, family, education, concierge and partner
features follow verified demand and capabilities. These do not need to be built
before a visitor can search a house.

## Evidence map

| Question | Owning document |
| --- | --- |
| What is implemented and what is next? | [Roadmap](../ROADMAP.md) |
| Which sources and Mall owners are reused? | [Housing audit](08_HOUSING_DISCOVERY_REBASELINE.md) |
| How do accounts, billing and tokens relate? | [Premium model](03_PREMIUM_MODEL.md) |
| Which domain and route should be used? | [Funnel architecture](07_FUNNEL_ARCHITECTURE.md) |
| What were the original BC0 and wider journey plans? | `01_OVERVIEW.md`, `02_SYSTEM_ARCHITECTURE.md`, `05_BASECAMP_ZERO_SPEC.md` |
