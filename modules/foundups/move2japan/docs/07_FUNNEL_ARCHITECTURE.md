# Move2Japan website, account and journey routes

Rebaseline: 2026-10-18 UTC. The brand and primary domain use the numeral 2:
**Move2Japan**, **move2japan.info**. The earlier marketing-first dual-domain
plan is superseded by useful public house discovery as the first website layer.
The first five-house grid and the subsequent separate page importing Mall
components are also superseded. The current source selects eight source-listed
houses inside the actual existing Mall boot, account and PWA.

## Surface map

| Surface | Role | Evidence/status |
| --- | --- | --- |
| `move2japan.info` | Primary public brand/domain for English house discovery | 012 reports current Patreon forwarding; replacement requires live deployment evidence |
| `/member/?foundup=move2japan` | Registered public product inside the existing Mall | Actual member index boot, eight-house v2 snapshot, geographic rows, shared RedDog/account/state/PWA; source implementation, production release pending |
| `/move2japan/` | Transitional redirect alias | Fixed product destination; supported public filter values are carried across; no independent boot |
| `/f/move2japan` | Canonical public FoundUp landing | Same registry tenant reconciled to discoverable incubating FoundUp; Browse houses also appears in the public portfolio |
| `/f/move2japan/app` | Protected participation route | Existing gate preserved; `discoverable_only` browsing does not admit the publisher interior |
| `/member/?account=1` | Existing shared account flow | Full Clerk/invite/username admission, then bounded product return; no paid housing entitlement |
| `/member/?creator=move2japan` | Existing Move2Japan video lane | Member flow and original video catalog retained |
| `https://move2japan.undaodu.chatgpt.site` | Existing owner-private review mirror | 2026-10-17 publication belongs to superseded composition; no production/account-hosting authority |
| `move2japan.foundups.com` | Historical separate PWA proposal | Superseded as an independent product architecture |

The primary domain can lead to the shared product surface once hosting and
forwarding are verified. Do not infer DNS ownership, a working subdomain or
cross-domain sign-in from a route string. A separate domain does not require a
second membership database. Production Hosting is a separate release to the
existing Firebase project `gen-lang-client-0061781628`, site `foundupscom`.
No authenticated hosting context is available in this session, and this
integration has not been deployed there. Verify the served public catalog,
canonical entry, member shell and domain forwarding after release.

## Public visitor flow

1. Arrive from Move2Japan's YouTube channel, search, canonical `/f/move2japan`
   Browse houses action or a shared product/filter link.
2. Land directly in the house field, without an account or passport questionnaire.
   Browse left/right within an area and up/down between geographic rows.
3. Open the same RedDog plane from the bottom anchor or Filter shortcut. Narrow
   country/prefecture/city/locality, land status and price, or switch rows from
   city/town to suburb/locality. Current coverage remains Fukui, Japan.
4. Open the selected house in the shared detail plane. Inspect its facts, source,
   checked date and unknowns; adjacent detail navigation remains within its area.
5. Follow the original source/contact for availability, photos and inquiry.

Public discovery remains useful by itself. The existing YouTube videos and BC0
relocation conversation remain acquisition/support paths; the property page does
not replace them or make every property a video entry.

The existing `public/member/index.html` prepares the domain templates before its
shared controllers initialize. Domain filters supply `{groups}` to the shared
field and register the form through `redDog.registerDiscoveryAdapter()` in
`product-discovery` mode. The same RedDog plane owns public search and existing
admitted member presentation. Public data loads independently of account SDKs.
State and the `/member/` service worker remain shared owners; there is no second
auth flow or newly implemented resident-agent transport.

## Account and publisher flow

For an existing session, the product reads the Clerk account's Firestore invite
and username admission without creating user records or consuming cached invites.
It clears the prior identity on sign-out/account changes and reuses shared
RedDog account sections only after admission. Guests can explicitly open
`/member/?account=1`; after that existing flow admits the account, a one-use,
15-minute return restores safe filters at the fixed public product route.
The handoff does not create a publisher role, activate paid benefits or link a
YouTube stakeholder record.

Prototype work will establish verified account linking, publisher role/authority,
durable submission and review. Reuse the existing GotJunk/Mall publication
components after the provider and identity boundaries are evidenced. Owner,
representative and licensed agency roles must remain distinguishable.

## Paid service flow

MVP connects a configured shared plan to a settled customer payment and delivered
Move2Japan benefit. Server verification must precede restricted data release;
invitation status, local storage, a displayed UPS balance or an estimated
YouTube membership tier cannot grant that access.

The proposed Basic/member delay model, price and plan mapping remain unconfigured.
See [the premium model](03_PREMIUM_MODEL.md). Do not present a purchase button,
exclusive inventory promise or completed paid membership flow before that
contract and actual service exist.

## Retained relocation journey and historical copy

The March route was YouTube BC0, optional newsletter capture, a planned
stakeholder PWA, then premium guidance. BC0 and its SQLite memory are
implemented; the full newsletter/dashboard/premium journey was not established
by the audit. It remains a later optional service layer.

Some existing livechat code and skill responses still contain `movetojapan`
spellings and advertise planned account/updates destinations. This website slice
does not change or activate that runtime. Migrate those responses in a scoped
follow-up after verifying the destination and accurately describing what it does.

Canonical identity remains `move2japan`; current registry token status remains
`TOKEN_DEFERRED`. The public POC is now registered as a discoverable incubating
FoundUp under that same tenant. This does not establish protected app admission,
token issuance, property ownership or paying-customer MVP.

See [the roadmap](../ROADMAP.md) and
[source/reuse audit](08_HOUSING_DISCOVERY_REBASELINE.md).
