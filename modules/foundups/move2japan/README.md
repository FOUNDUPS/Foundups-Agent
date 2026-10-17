# Move2Japan

Updated 2026-10-17 JST. Product direction: English discovery of real Japanese
homes, followed by publisher accounts and paid services. The primary domain is
**move2japan.info**, with the numeral 2.

## Current product

Move2Japan helps people who do not read Japanese find houses in Japanese akiya
banks, understand the displayed facts, and reach the original listing and its
contact. It uses the Foundups Mall interaction model: a searchable field of
property tiles that opens a property detail plane.

The first website slice is a public proof of concept at `/move2japan/`, using
five attributed Fukui source records. Source-listed status and the observation
date are displayed; current availability must be confirmed with the source or
broker. Photos and tours remain at the original source because a bulk media
reuse grant has not been established.

An owner-private review version is published at
[Move2Japan](https://move2japan.undaodu.chatgpt.site). The deployment service
confirmed success on 2026-10-17 JST. Source, behavioral checks, publication and
live-domain verification are separate milestones. Browser rendering is still
unverified because the managed preview environment could not start. This
publication does not establish that `move2japan.info` has stopped forwarding to
Patreon. See the
[implementation audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md) and
[roadmap](ROADMAP.md) for evidence and remaining gates.

## Build sequence

| Stage | Acceptance | Current scope |
| --- | --- | --- |
| POC | A visitor can search actual houses in English and inspect their sources | Public factual catalog and shared Mall property interaction |
| Prototype | A realtor, broker or owner can register and submit an akiya for reviewed publication | Pending account-linked publisher roles, verified authority and durable upload/publication |
| MVP | Actual customers pay and receive the configured service | Pending settled payments, delivered benefits, shared membership verification and revocation |

A signup, interest form, token model or checkout screen does not establish MVP.
The monk's proposed Basic membership and earlier listing access remain product
requirements; no price or release delay has been chosen here.

## Source and ownership map

| Owner | Responsibility |
| --- | --- |
| `public/move2japan/index.html` | Public English house-search page |
| `public/move2japan/properties.json` | Attributed public source observations; no private early-access inventory |
| `public/move2japan/property-search.js` | Property filters and shared Mall wiring |
| `public/member/js/mall-tile-field.js` | Shared tile rendering and selection |
| `public/member/js/mall-planes.js` | Shared detail plane |
| `public/member/js/gesture-engine.js` | Shared gestures; visible controls remain available |
| `src/m2j_stakeholder_db.py` | Existing YouTube intake memory |
| `modules/communication/livechat/src/m2j_handler.py` | Existing BC0 conversation handler |

Each house has a listing identity inside `foundup_id=move2japan`; it is not a
separate FoundUp. The public property catalog does not replace the main Mall's
YouTube catalog. GotJunk/Mall publication owners are reuse candidates for the
prototype after their provider and account authorization are established; the
current GotJunk provider is not a working universal house upload service.

## Identity, accounts and tokens

The stable identifier is `move2japan`, with the existing namespace contract
`/f/move2japan` and future app mount `/f/move2japan/app`. This slice adds a public
discovery page without promoting the registry entry or inventing a new lifecycle.
The canonical registry currently records the implemented YouTube intake as an
`access_service`, with token assignment deferred. That registry status must be
reconciled explicitly before later Mall product admission.

The existing shared account entry is
[Foundups membership](https://foundups.com/member/). It uses Clerk identity,
Firestore invite admission and a username. It does not verify a paid housing
subscription. Prototype account linking and MVP billing must derive authority
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
`/f/move2japan`, and app family `/f/move2japan/app/*`. The current public POC
source entry is `/move2japan/`; registry-backed app admission is a later gate.

## App Mount

Declared shell mount: `/f/move2japan/app`. This is a future account-linked app
contract, not a claim that this slice has mounted a publisher or membership app.
The public page composes shared Mall components at its separate POC source route.

## AI Capability Hooks

Planned/not implemented for the housing service: `get_status`, `get_context`,
`navigate`, `launch_capability`, and shell handoff/return. The browser's local
search and detail controls do not confer agent or authenticated service authority.

## DAEmon Outputs

No housing worker or autonomous crawler is activated. When a worker is attached,
WSP 91 requires health, last action, error state, recommended next action,
queue/work state and tenant-scoped telemetry. Those outputs are a future
integration contract; this static discovery slice has no worker queue.

## Data / Telemetry Namespace

`foundup_id=move2japan`; declared future browser data namespace:
`idb_move2japan`. Existing BC0 memory remains in this module's SQLite store;
public house observations live in the public catalog. Protected account or paid
listing data must remain tenant-scoped and must not enter that public catalog.
No new IndexedDB store or private-data transport is claimed here.

## WSP References

WSP 3/49 own module placement; WSP 11 owns interfaces; WSP 22 owns change memory;
WSP 50/84 require source verification and reuse; WSP 60 owns intake memory;
WSP 97 owns execution and evidence boundaries; WSP 91 owns worker observability;
WSP 104 owns the existing tenant namespace. WSP 26 supplies token architecture,
not evidence of issuance.
