# Move2Japan

Updated 2026-10-18 UTC. Move2Japan is a product inside the existing Play Foundups
Mall at **`/member/?foundup=move2japan`**. It starts with English discovery of real
Japanese homes, followed by publisher accounts and paid services. The intended
public brand/domain is **move2japan.info**, with the numeral 2.

## Current product

Move2Japan helps people who do not read Japanese find houses in Japanese akiya
banks, understand the displayed facts, and reach the original listing and its
contact. The existing `public/member/index.html` owns its boot, shell, account
entry, middle field and bottom RedDog anchor. The strict `foundup=move2japan`
selection mounts housing content in that shell. Left/right browses houses within
an area; up/down changes areas. The same shared detail plane opens the selected
house. `/move2japan/` is a redirect alias, with domain data and styles still kept
under `public/move2japan/`.

The public product contains eight attributed Fukui
records across five municipalities. Three municipalities have multiple houses.
Filters cover country, prefecture, city/town, suburb/locality, recorded land
status and price; the available source collection is still limited to Fukui,
Japan. The shared RedDog plane contains those filters and collection information.
Guests can browse without Clerk or Firestore being available. Existing admitted
members can use their shared identity and RedDog account sections in the same
plane; the public product reads existing admission and creates no new account,
invite, publisher role or paid benefit.

Source-listed status and the observation date are displayed; current availability
must be confirmed with the source or broker. A negotiable price remains null,
and unknown land information remains unknown. The collection has seven records
with a stated land area and one with unknown land; it contains no confirmed
no-land record. Photos and tours remain at the original source because a bulk
media reuse grant has not been established.

**Current source status:** The existing registry entry is now a discoverable,
incubating FoundUp with a public POC. `/f/move2japan` and the public portfolio link
to **Browse houses** inside `/member/?foundup=move2japan`. The protected
`/f/move2japan/app` gate remains separate. Product navigation state, the member
PWA service worker and a bounded account-return handoff belong to shared Mall
owners. Exact current verification scope belongs to the
[implementation audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md) and
[test log](tests/TestModLog.md).

**Production delivery remains open:** This integration has not been deployed to
Firebase Hosting. The established target is project `gen-lang-client-0061781628`,
site `foundupscom`; an authenticated deployment context is unavailable in this
session. Browser interaction/visual checks and the `move2japan.info` forwarding
cutover require separate receipts. A private review mirror does not establish
production hosting or cross-domain account access.

### Superseded review receipt — 2026-10-17

The earlier eight-house composition imported shared components at its own
`/move2japan/` page. It did not complete the registry, PWA boot and account
integration now required by 012. Its 696-pass/one-unchanged-BC0-failure automated
result belongs to that revision. That source was published to the owner-private
[review Site](https://move2japan.undaodu.chatgpt.site) on 2026-10-17 at 01:04:36 UTC
(10:04 JST), replacing the superseded five-house landing/grid candidate. The
service returned `succeeded` for Site source commit
`77db7957ce7527a0f614de545317ac03842c876b`. The historical repository delivery
reference is [PR #2151](https://github.com/FOUNDUPS/Foundups-Agent/pull/2151).
Browser QA was blocked by the managed preview environment. Preserve these
receipts as history; they do not verify the current integrated shell or its
production release. The same private Site is a review mirror only.

## Build sequence

| Stage | Acceptance | Current scope |
| --- | --- | --- |
| POC | A visitor can search actual houses in English inside the Mall and inspect their sources | Eight-record public catalog, registered discovery entry, shared shell/account/state owners implemented in source; production/browser/domain gates remain |
| Prototype | A realtor, broker or owner can register and submit an akiya for reviewed publication | Pending account-linked publisher roles, verified authority and durable upload/publication |
| MVP | Actual customers pay and receive the configured service | Pending settled payments, delivered benefits, shared membership verification and revocation |

A signup, interest form, token model or checkout screen does not establish MVP.
The monk's proposed Basic membership and earlier listing access remain product
requirements; no price or release delay has been chosen here.

## Source and ownership map

| Owner | Responsibility |
| --- | --- |
| `public/member/index.html` | Actual Mall boot, product templates, shared account admission and houses-first shell selection |
| `public/move2japan/index.html` | Redirect alias to the selected Mall product; no independent application boot |
| `public/move2japan/properties.json` | Eight attributed v2 public source observations; no private early-access inventory |
| `public/move2japan/property-search.js` | Strict product-route selection, domain template mount, validated housing facts, filters and geographic projection |
| `public/member/js/mall-tile-field.js` | Shared grouped field, directional navigation, tile rendering and selection |
| `public/member/js/mall-planes.js` | Shared detail plane; adjacent house navigation stays within the active area |
| `public/member/js/account-concierge.js` | Shared product-discovery and admitted account presentation in one RedDog plane |
| `public/member/js/mall-state-restore.js` | Separate video/product presentation state and one-use account-return filters |
| `public/member/member-sw.js` | Existing `/member/` PWA shell and explicit public catalog cache paths |
| `modules/foundups/foundup_registry.json`, `foundup_manifest.json` | Existing tenant registration and declarative public POC entry |
| `modules/foundups/public_catalog_projector/`, `public/f/` | Allowlisted public projection and canonical discovery/participation route distinction |
| `public/member/css/member.css`, `mall-tile-field.css`, `mall-planes.css`, `account-concierge.css` | Shared scaffold, field, details and search-plane styles |
| `public/member/js/gesture-engine.js` | Shared gestures; visible controls remain available |
| `src/m2j_stakeholder_db.py` | Existing YouTube intake memory |
| `modules/communication/livechat/src/m2j_handler.py` | Existing BC0 conversation handler |

Each house has a listing identity inside `foundup_id=move2japan`; it is not a
separate FoundUp. The public property catalog does not replace the main Mall's
YouTube catalog. GotJunk/Mall publication owners are reuse candidates for the
prototype after their provider and account authorization are established; the
current GotJunk provider is not a working universal house upload service.

The housing adapter passes `initialize(records, {groups})` and
`updateCatalog(records, {groups})` to the shared field. Each group has `key`,
`label`, `subtitle` and `itemIds` containing listing IDs. This adds a geography
projection to the existing renderer; it does not create a separate marketplace
grid or reinterpret a YouTube creator/channel as a house location.

## Identity, accounts and tokens

The stable identifier is `move2japan`, with canonical public landing
`/f/move2japan` and protected app namespace `/f/move2japan/app`. The existing
registry record is reconciled from its earlier hidden access-service state to
`entity_type=foundup`, `stage=incubating`, `public_surface_status=discoverable`,
`poc_status=poc` and `mall_entry_status=discoverable_only`. Its declarative
manifest and `poc_url` select the actual Mall product. Public discovery does not
grant admission to the protected app or establish a publisher service.

The existing shared account entry is
[Foundups account](https://foundups.com/member/). In the product, existing Clerk
identity, Firestore invite admission and username are read without consuming
invites or writing user records. A guest's explicit account action opens the
existing flow at `/member/?account=1`; a one-use, 15-minute return record restores
safe house filters after that flow admits the account. Sign-out or an account
switch clears the previous identity presentation. These checks do not verify a
paid housing subscription. Prototype account linking and MVP billing must derive authority
from verified services, not a browser flag, local storage, a displayed UPS
balance or a YouTube membership estimate.

Tokenization remains connected to the existing FoundUps architecture with
`TOKEN_DEFERRED`. No Move2Japan token, allocation, wallet gate, property title or
economic entitlement is created by this POC. Service access and token ownership
must remain distinct. See [the premium model](docs/03_PREMIUM_MODEL.md).

## Existing relocation journey

The March 2026 relocation design remains a later product layer. BC0 intent,
urgency and passport conversation plus SQLite memory are implemented. BC1 and
BC2 have skill stubs; the complete web journey is not implemented. Public house
search does not require a passport questionnaire or progress through these camps.

| Base camp | Purpose |
| --- | --- |
| BC0 | Intent, urgency and passport triage |
| BC1 | Identity and readiness |
| BC2 | Migration pathway |
| BC3 | Income and economic viability |
| BC4 | Location fit |
| BC5 | Housing pathway |
| BC6 | Paperwork and execution |
| BC7 | Landing and settlement |

The existing livechat code and runtime are unchanged in this slice. Some
livechat response strings still contain the old domain spelling; their migration
needs a verified website/account destination and is tracked in the roadmap.

## Documentation

- [Interface](INTERFACE.md): current property and intake boundaries, future contracts.
- [Roadmap](ROADMAP.md): current POC, prototype and paying-customer gates.
- [Premium model](docs/03_PREMIUM_MODEL.md): account, benefit and token boundaries.
- [Stage definitions](docs/04_POC_PROTOTYPE_MVP.md): the monk's current acceptance criteria.
- [Funnel architecture](docs/07_FUNNEL_ARCHITECTURE.md): public discovery and shared account routes.
- [Source and reuse audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md): source observations and implementation controls.
- [ModLog](ModLog.md) and [tests](tests/README.md): change and verification memory.

`docs/01_OVERVIEW.md`, `02_SYSTEM_ARCHITECTURE.md`,
`05_BASECAMP_ZERO_SPEC.md` and `06_BLINDSPOTS.md` retain the earlier relocation
vision. Their staged chatbot design does not override the current house-search
priority or prove that planned services are deployed.

## Route Namespace

Canonical contract:
[FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md](../docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md).
WSP 104 preserves `foundup_id=move2japan`, routing prefix/landing
`/f/move2japan`, and app family `/f/move2japan/app/*`. The registered public POC
entry is `/member/?foundup=move2japan`; `/move2japan/` redirects there. Exactly
one `foundup=move2japan` value selects the product. Unknown or duplicate values
cannot turn another tenant into a public product.

## App Mount

Declared protected app mount: `/f/move2japan/app`. Its participation gate is
preserved. The public house POC mounts directly inside the existing `/member/`
shell; it does not need publisher/app admission. A reviewed publisher interior
is still a prototype target.

## AI Capability Hooks

Machine-callable `get_status`, `get_context`, `navigate` and `launch_capability`
remain unimplemented for the housing service. Shared browser navigation,
geographic position restore and bounded account return now exist. These local
presentation controls do not confer agent or authenticated service authority.

## DAEmon Outputs

No housing worker or autonomous crawler is activated. When a worker is attached,
WSP 91 requires health, last action, error state, recommended next action,
queue/work state and tenant-scoped telemetry. Those outputs are a future
integration contract; this static discovery slice has no worker queue.

## Data / Telemetry Namespace

`foundup_id=move2japan`; declared future browser data namespace:
`idb_move2japan`. Shared shell presentation state uses
`pfmall_product_move2japan_state_v1`, separate from video state; the bounded
account-return record uses session storage. Existing BC0 memory remains in this
module's SQLite store; public house observations live in the public catalog.
The service worker caches only the public snapshot with its original observation
dates. Protected account or paid
listing data must remain tenant-scoped and must not enter that public catalog.
No new IndexedDB store or private-data transport is claimed here.

## WSP References

WSP 3/49 own module placement; WSP 11 owns interfaces; WSP 22 owns change memory;
WSP 50/84 require source verification and reuse; WSP 60 owns intake memory;
WSP 00 owns role and execution readiness; WSP 97 owns execution and evidence
boundaries; WSP 91 owns worker observability;
WSP 104 owns the existing tenant namespace. WSP 26 supplies token architecture,
not evidence of issuance.
