# Move2Japan membership and premium model

Rebaseline: 2026-10-17 JST. Authority: 012's house-discovery instruction and
paying-customer definition of MVP. The March 2026 premium/concierge concept is
retained below as future service scope, not an implemented subscription catalog.

## Current offering and next benefits

The POC offers public English discovery of attributed house records using
Foundups Mall. It does not sell a membership or serve private early listings.

| Surface or benefit | State |
| --- | --- |
| Public property search and original-source links | POC implementation slice |
| Shared Foundups account | Existing Clerk/invite/username flow at `https://foundups.com/member/` |
| Owner/realtor publication | Prototype target; account and publisher authority pending |
| Basic/member earlier discovery or alerts | Proposed benefit; plan mapping, price and delay unconfigured |
| Partner-authorized exclusive offers | Future, only where an actual partner grants the offer |
| Paid Move2Japan subscription and delivered benefit | Required for MVP; not established |

The monk's "Basic member" wording is a product requirement. It must map to the
verified shared Foundups membership service when implemented. Do not copy a
price from the simulator or infer that a shared invite grants paid access.

## Reuse boundaries

`public/member/index.html` checks Clerk identity and Firestore invite/username
state. It does not verify a settled subscription. Move2Japan should reuse that
account entry and establish a verified principal binding for protected services.

The existing systems have distinct roles:

- `modules/foundups/simulator/economics/subscription_tiers.py` models economics;
  its tier names, allowances and prices are not live billing evidence.
- FAM's `ComputeAccessService` and persistence ledger meter build execution.
  They are not a house-listing subscription or payment-provider verifier.
- `modules/communication/chat_rules/src/membership_manager.py` handles YouTube
  memberships, including estimated/default fallback tiers. Those estimates
  cannot grant paid website benefits.
- The canonical FoundUps entitlement documents describe a target wallet/stake
  gate and explicitly distinguish it from current public/community access.

The YouTube stakeholder ID, Clerk account ID and GotJunk/Firebase UID are not
interchangeable. Link them only through a verified account flow; a matching name
or email text does not prove they belong to the same principal.

## MVP payment and benefit contract

Before charging for restricted access, establish:

1. A configured plan, price, scope and clear service description.
2. A verified billing event tied to the shared account and service period.
3. Idempotent processing and reconciliation of settled payment state.
4. Server-derived current entitlement before data is released.
5. Recorded delivery of the promised benefit.
6. Refund, cancellation, expiry and revocation behavior.

MVP is reached only when actual customers pay and receive the configured
offering. Account creation, a trial, a checkout page, premium interest or a
simulated credit balance cannot substitute for that evidence.

## Earlier discovery and exclusive offers

The proposed delay model must retain separate timestamps for source publication,
first discovery, verification, member release and public release. Missing source
times remain unknown. No release delay is chosen in this document.

Early access must be enforced before restricted records leave the service.
Do not put early listings into public JSON, browser storage or a public
service-worker cache and hide them with CSS or a membership flag.

A publicly available akiya-bank listing is public inventory. A paid service may
deliver earlier curated discovery, translation or alerts. The word "exclusive"
requires an actual partner-authorized offer, not a claim over public information.

## Tokenization

Preserve `foundup_id=move2japan` and the existing `TOKEN_DEFERRED` registry state.
This slice creates no token symbol, supply, distribution, staking or wallet
entitlement. Future integration follows WSP 26 and the existing FoundUps owners.

Keep these concepts distinct:

- Service membership grants a configured service benefit when verified.
- Compute credits account for metered work under their existing policy.
- FoundUp tokens concern the venture's defined economic participation.
- A property listing does not convey ownership or an interest in the property.

A token balance or browser claim must not be treated as a paid service
entitlement. Existing token factory adapters and simulation output are not proof
of Move2Japan token issuance.

## Retained March service concepts

Future premium guidance can include a persistent roadmap, location/job support,
checklists, reminders and document preparation. Future concierge can include a
personal move agent, translation, housing assistance, broker introductions and
human escalation. Enterprise/partner services may support employers,
universities, municipalities and relocation agencies.

Subscription, one-time service fees and referral arrangements remain candidate
revenue streams. Any brokerage/partner share requires its own verified authority
and agreement; this document does not establish one.

Sources within the repository:
[current audit](08_HOUSING_DISCOVERY_REBASELINE.md),
[roadmap](../ROADMAP.md),
[FoundUps architecture](../../docs/FOUNDUPS_MASTER_ARCHITECTURE.md),
[entitlement tiers](../../docs/FOUNDUPS_ENTITLEMENT_TIERS.md).
