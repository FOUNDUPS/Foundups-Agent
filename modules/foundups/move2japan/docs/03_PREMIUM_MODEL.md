# Move2Japan membership and premium model

Rebaseline: 2026-10-18 UTC. Authority: 012's shared-Mall house-discovery instruction and
paying-customer definition of MVP. The March 2026 premium/concierge concept is
retained below as future service scope, not an implemented subscription catalog.

## Current offering and next benefits

The POC source offers eight attributed house records inside the existing
`/member/?foundup=move2japan` Mall shell: geographic rows, location/land filters
and the shared RedDog plane. The canonical `/f/move2japan` public entry links
there. `/move2japan/` is now an alias; the former independent composition and
its 2026-10-17 private publication are superseded history. Production hosting
and browser validation remain separate gates. The public product reads existing
shared-account admission and does not sell a membership or serve private early
listings.

| Surface or benefit | State |
| --- | --- |
| Public geographic house discovery and original-source links | Registered POC in the actual Mall shell; guest browse does not require account services |
| Shared Foundups account | Existing Clerk/invite/username admission, read without account/invite writes in the product; explicit account handoff reuses `/member/?account=1` |
| Owner/realtor publication | Prototype target; account and publisher authority pending |
| Basic/member earlier discovery or alerts | Proposed benefit; plan mapping, price and delay unconfigured |
| Partner-authorized exclusive offers | Future, only where an actual partner grants the offer |
| Paid Move2Japan subscription and delivered benefit | Required for MVP; not established |

The monk's "Basic member" wording is a product requirement. It must map to the
verified shared Foundups membership service when implemented. Do not copy a
price from the simulator or infer that a shared invite grants paid access.

## Reuse boundaries

`public/member/index.html` owns both public product selection and the existing
member flow. Guest housing data loads independently. For an existing session,
the product reads Clerk identity and Firestore invite/username state, clears
stale identity on sign-out/account changes, and enables the existing shared
RedDog account presentation only after that admission. It does not create a
waitlist record, consume an invite or verify a settled subscription. A bounded,
one-use return restores safe housing filters after explicit account admission.

`registerDiscoveryAdapter({element, focusElement})` mounts the domain-owned form
in the same RedDog plane. Dialog state, filters, recorded land/price facts and
the public `foundup` query confer no account, purchase or service entitlement.
Protected publisher and billing services still require a verified principal
binding and their own server-derived authority.

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

Preserve `foundup_id=move2japan` and `TOKEN_DEFERRED`. Reclassifying the same
registry record as a discoverable, incubating FoundUp with a public POC does not
issue a token or admit its protected `/f/move2japan/app` interior.
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
