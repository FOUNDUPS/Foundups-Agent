# Move2Japan: POC, prototype and MVP

Current authority: 012's 2026-10-17 JST website instruction. This updates the
build order captured in the 2026-03-07 voice conversation while retaining the
broader relocation vision. The current primary domain is **move2japan.info**.

## POC: searching real houses

**Proof sought:** People who do not read Japanese can find actual houses,
understand the available facts and reach the original listing/contact.

The first slice is a public English property catalog at `/move2japan/` with five
attributed Fukui observations. The page reuses Foundups Mall's tile field,
detail planes and gesture code. Houses are records within Move2Japan, not new
FoundUps, and opening a house does not start a video.

Acceptance requires useful search/filtering, the correct selected detail,
original-source links, observation dates, clear unknowns and source-listed
availability boundaries. Source photographs stay at the source until media
reuse is authorized. Source implementation, validation and live deployment are
recorded separately.

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
