# Move2Japan interface (WSP 11)

Updated 2026-10-18 UTC. Current website priority: English public house discovery
inside the existing Play Foundups Mall.
[The implementation audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md) records source
and reuse evidence; [the roadmap](ROADMAP.md) owns the staged acceptance gates.

## Public property discovery

Shell owner: `public/member/index.html`, selected by
`/member/?foundup=move2japan`. Domain owners remain
`public/move2japan/properties.json`, `property-search.js` and `move2japan.css`.
The product uses the existing Mall boot, account controller, field/detail planes,
gesture engine, state owner and PWA service worker. `public/move2japan/index.html`
only redirects old public links into that shell. The canonical public landing
is `/f/move2japan`; **Browse houses** selects the member-shell product without
granting `/f/move2japan/app` admission.

The earlier standalone compositions and their private Site receipts are
superseded history. Current source checks are recorded in the audit/test log;
Firebase production hosting and browser review remain separate delivery gates.
No authenticated publisher or payment API is introduced here.

### Catalog contract

The envelope uses `schema_version=move2japan_property_catalog.v2`,
`catalog_kind=curated_public_source_observations`, `foundup_id=move2japan`, an
`observed_on` date, coverage description and a `properties` array. It is a
bounded public source snapshot, not a continuously live or complete inventory.

| Record fields | Meaning |
| --- | --- |
| `foundup_id`, `source_type` | Existing tenant `move2japan`; `property_listing` presentation |
| `listing_id`, `source_item_id` | Stable property identity and original source record ID; never a new FoundUp ID |
| `name`, `summary`, `tags` | Original English factual discovery copy; not an assertion of suitability |
| `transaction`, `price_jpy`, `price_status` | Sale; integer JPY for `asking`, null for `negotiable` or `unknown`. No inferred total purchase cost or zero-price substitute |
| `country_code`, `country`, `prefecture` | Current adapter accepts `JP`, `Japan`, `Fukui`; the UI does not imply broader source coverage |
| `municipality`, `municipality_ja`, `locality`, `locality_ja`, `address_ja` | Source-backed city/town and suburb/locality labels; Japanese locality retained for matching. No invented coordinates |
| `land_area_m2`, `land_status` | `with_land` requires a positive reported area; `no_land` requires explicit zero; `unknown` requires null. These describe source data, not ownership terms |
| `building_area_m2`, `building_area_label_ja` | Original area meaning retained; `建築面積` is not silently converted to usable floor area |
| `floors`, `construction_date`, `layout`, `repair_level`, `source_notes` | Source facts and conflicts. Missing dates/condition remain null or unknown; repair states are `major`, `some`, `none_reported`, `unknown` |
| `source_name`, `source_url`, `last_checked`, `source_updated_at` | Provenance and observation date; an unknown source update time remains null |
| `availability`, `broker_availability_confirmed` | `source_listed` is a source observation, not broker-confirmed availability |
| `virtual_tour_at_source`, `media_permission` | Tours remain at source; a public listing does not itself grant media reuse |

The current eight source IDs are `87`, `85`, `83`, `77`, `76`, `25`, `79`, `88`.
Wakasa, Sakai and Eiheiji each have two records; Fukui City and Awara have one
each. One price is negotiable/null. Seven records have a positive reported land
area and one has unknown land information; the current collection has no
confirmed no-land record. Source pages were checked on 2026-10-17.

`normalizeCatalog()` validates source identity, exact Fukui source URLs, dates,
price/land consistency and the v2 envelope, then returns an explicit public
allowlist. Raw observation metadata such as `source_updated_at`,
`broker_availability_confirmed` and `media_permission` records audit boundaries;
it is not an account or publication grant. Restricted offers, member-release
data, personal account records and uploaded files do not belong in this public
catalog. Future private feeds must authorize before returning records.

### Housing projection API

`property-search.js` exports the following under CommonJS for checks and under
`window.Move2JapanSearch` for the browser:

| Function | Contract |
| --- | --- |
| `isShellProductRoute(location)` | Accept `/member/` or `/member/index.html` with exactly one `foundup=move2japan`; unknown or duplicate tenant selectors do not select public housing |
| `prepareShell(window)` | Mount the member index's domain templates into its existing field/plane before shared controllers initialize; set `product-discovery` mode and fixed account/Mall/video links |
| `normalizeCatalog(data)` | Validate v2 and return normalized public properties; reject invalid/duplicate source identity |
| `searchProperties(properties, filters)` | Filter by query, country, prefecture, city (`area` legacy alias), locality, maximum price, land status, large plots and source tours; sort the result |
| `locationOptions(properties, filters)` | Derive available country/prefecture/city/locality options from the supplied source records and parent selections |
| `groupProperties(properties, groupBy)` | Produce shared Mall groups by `city` or `locality`, with ordered listing IDs |
| `mount(window, catalogUrl)` | Register the domain form with shared RedDog, load the public snapshot, bind filters/URL state, update the field and restore product presentation state |

Query terms are matched against English/Japanese discovery text. A maximum price
excludes negotiable/unknown-price houses rather than treating null as zero.
Known prices precede unpriced records in either price-sort direction. The
optional 500 m² minimum is independent of the three-state land filter.

The canonical selection is `foundup=move2japan`; it is retained when filters are
written. No additional `view` selector or arbitrary product URL is required.
Filter URL parameters are `q`, `country`, `prefecture`, `city`, `locality`, `max`,
`land`, `sort`, `group`, `large` and `tour`. The old `area` parameter is accepted
as a city alias and removed when writing the current URL. Unsupported geography
is retained as an unavailable selection and yields no matches; it is not silently
broadened to the whole collection.

### Presentation and navigation

- The shared top account anchor, middle field and bottom RedDog anchor are the
  landing scaffold. The field shows houses immediately; collection/help copy
  lives in the search plane.
- Call `mallTileField.initialize(records, {groups})` and
  `updateCatalog(records, {groups})` with groups shaped as
  `{key, label, subtitle, itemIds}`. `itemIds` are listing IDs. Group keys retain
  the full country/prefecture/municipality/locality hierarchy; they are not new
  FoundUp identities.
- Left/right navigates houses within an area; up/down changes areas. City/town
  rows are the default; suburb/locality rows are available. Snap is the entry
  mode, with native touch scrolling, desktop drag, arrow keys and visible row
  controls owned by the shared field. Scroll/focus state uses group/listing IDs.
- Open the selected listing in the shared detail plane. Adjacent details stay
  within the active area. Multiple houses share `foundup_id=move2japan`;
  selection and return focus retain the particular listing identity.
- Render source facts with escaped text/attributes. Source navigation uses HTTPS
  URLs without embedded credentials; unsupported/unsafe input must not become
  executable markup or an active link.
- Keep visible controls alongside gestures and preserve keyboard navigation.
- Link to the original source for photos, tours, detailed conditions and inquiry.
- Do not initiate payment, reservation, brokerage or a property publication by
  opening a tile or following a discovery action.

The main Mall YouTube catalog is retained. The product's **Videos** action opens
`/member/?creator=move2japan` through existing member admission. The canonical
registry's same `move2japan` ID now describes the public POC as a discoverable,
incubating FoundUp with `mall_entry_status=discoverable_only`; it does not
declare a publisher interior ready.

### Product RedDog adapter

The member shell prepares `#accountPlane[data-reddog-mode="product-discovery"]`
before loading `account-concierge.js`. Its `[data-reddog-discovery]` host contains the
existing `#propertySearchPanel`; `[data-reddog-close]` closes the plane.
`#accountPlane` and `#accountPlaneScrim` are siblings outside `.mall-shell`.
The domain calls:

```javascript
window.redDog.registerDiscoveryAdapter({
  element: document.getElementById('propertySearchPanel'),
  focusElement: document.getElementById('propertyQuery')
});
```

The shared controller retains the mounted form and its listeners. Top Filter,
no-results Edit filters (`data-reddog-open-discovery`) and `#redDogBtn` open the
same plane. It works before catalog completion, traps modal focus, preserves
background inert state, closes with Escape/Close/scrim and restores opener focus.
Form scrolling does not dismiss it; an optional `.account-plane-handle` uses the
shared swipe-up close gesture. Guests receive public filters and an explicit
account link. The existing shared account presentation becomes available after
the shell supplies its verified admission result; its API guards are checked
again when called and are revoked on sign-out/account change. Global video-field
actions cannot replace the housing field. The adapter adds no resident-agent
transport, publisher authority or payment service.

## Shared account boundary

Account entry: `https://foundups.com/member/`; explicit product handoff uses
`/member/?account=1`. Current owner is `public/member/index.html`.
`initClerkAuth`, invite validation and username requirements continue to own the
ordinary member path. Public houses mount before account imports, so a guest,
missing SDK, unavailable Firebase service or missing admission cannot block
discovery or silently create a user record.

For an existing Clerk session, `syncProductIdentity()` reads that account's
Firestore record. Admission requires the existing invite predicate and a
username. The public path does not create a waitlist record, consume a cached
invite or write user data. It updates existing RedDog identity/invite display
only after admission and rechecks on session/visibility changes. Old asynchronous
results cannot restore a previous account's identity. No paid Move2Japan benefit
is derived from this admission.

Prototype requires a verified account link and publisher authority. A YouTube
channel ID, Clerk principal and GotJunk/Firebase UID are separate identifiers;
do not infer identity equality from display names or email text. Browser
`postMessage`, local storage and displayed balances cannot grant protected access.

### Shared navigation state and PWA boundary

`mall-state-restore.js` selects a fixed product namespace,
`pfmall_product_move2japan_state_v1`, separate from the existing video state.
`getGeographicState()`/`restoreGeographicState()` use the current tenant,
geographic keys and listing IDs. Unknown rows/listings cannot redirect selection
to another tenant; scroll offsets and remaining row positions are clamped to the
rendered catalog. An empty or failed catalog load does not erase prior state.

An explicit account link stores only allowlisted filter values in a one-use,
15-minute `pfmall_product_return_v1` session record. After the ordinary member
path completes Clerk, invite and username admission, `consumeProductReturn()`
returns only `/member/?foundup=move2japan` plus sanitized filters and `#account`.
There is no caller-supplied return origin or authorization claim. Storage failure
does not block browsing or admission.

`member-sw.js` retains the `/member/` scope. Product query navigations fetch/cache
the fixed public `/member/` document without query keys. The public property
snapshot uses the exact `/move2japan/properties.json` path, network-first with
cached source bytes unchanged, including observation dates. If neither source
nor cache is available, it reports unavailable data. Authentication, arbitrary
member APIs, query-bearing data assets and cross-origin responses are not added
to the cache allowlist. Protected or early-release records must never enter this
public cache.

## Existing BC0 persistence

Owner: `src/m2j_stakeholder_db.py`, class `M2JStakeholderDB`.
Default data path: `memory/m2j_stakeholders.db` inside this module, created at
runtime. The tracked source does not establish live stakeholder counts.

| Public method | Existing purpose |
| --- | --- |
| `get_stakeholder(stakeholder_id)` | Retrieve a record by YouTube channel ID |
| `create_stakeholder(stakeholder_id, chat_handle, intent_source)` | Insert a minimal record |
| `update_stakeholder(stakeholder_id, updates)` | Update intake fields and `last_seen` |
| `get_or_create(stakeholder_id, chat_handle, intent_source)` | Resume or create intake memory |
| `get_stats()` | Aggregate stored count, stage and urgency |

The actual SQLite fields are `stakeholder_id`, `chat_handle`, `urgency_level`,
`passport_status`, `current_stage`, `timeline_estimate`, `intent_source`,
`bc0_state`, `move_reason`, `language_level`, `target_region`, `first_seen`,
`last_seen` and `notes`. Email, paid plan and expanded roadmap fields below are
future requirements, not existing columns or authentication authority.

`modules/communication/livechat/src/m2j_handler.py` owns BC0.1-BC0.6 handling;
its runtime and stored conversations are unchanged by the website slice.

## Future publisher and paid-service contracts

Prototype must provide authenticated owner/representative/broker roles,
property/advertising/media authority, review, durable upload/publication and
withdrawal. Reuse the existing GotJunk/Mall owners once the production provider
and principal mapping are verified. No public submission endpoint is claimed.

MVP must bind settled customer payment to a configured shared account plan and
actually deliver its benefit. Server-derived access, replay handling, refunds,
expiry and revocation are required. There is no price, release delay or new token
assignment in this contract. See [membership and premium](docs/03_PREMIUM_MODEL.md).

## Status of the retained journey specification

The remaining sections retain the March relocation model. BC0 and minimal SQLite
memory exist; the complete cross-channel roadmap, expanded profile, document
services and paid orchestration remain planned. The guidance gates below apply
to an optional personal journey and never block public property discovery.

## Retained relocation service plan

### A. Intent Capture Module

- **Inputs**: Live chat trigger (`!move2japan`), site CTA, lead forms, newsletter signup
- **Outputs**: Stakeholder record, source attribution, initial stage = Intent

### B. Stakeholder Memory Module

- **Purpose**: Cross-channel identity resolution, resumable conversations, agent-readable summaries
- **Stores**: Chat identity, email, progress stage, key answers, preferences, urgency, premium status

### C. Roadmap Engine

- **Purpose**: Stage-gated progression with unlock logic
- **Controls**: Base camp progression, checklist state, prerequisite gates, unlock conditions, reminders

### D. Conversation Orchestrator

- **Purpose**: Determines next question, routing (chat vs site), signup timing, upsell timing, human escalation

### E. Knowledge Engine

- **Purpose**: Structured content for visa, passport, jobs, housing, city selection, documents, policy updates
- **Requirements**: Freshness review, source traceability, admin update workflow

### F. Dream Life Discovery Module

- **Purpose**: Translate abstract desire into concrete relocation path
- **Outputs**: Recommended regions, migration path, job/housing strategy

### G. Job Pathway Module

- **Purpose**: Income viability — education, language, industry, remote compatibility, sponsorship likelihood

### H. Housing Module

- **Purpose**: First landing housing → ideal housing → search aggregation → partner referrals

### I. Form/Document Automation Module (Premium)

- **Purpose**: Prefill applications, translate fields, generate checklists, draft Japanese emails

### J. News & Policy Update Module

- **Purpose**: Internal Substack — visa changes, policy shifts, work trends, housing news

### K. Monetization Module

- **Supports**: Free, premium, concierge, referral revenue, brokerage commission, partner commissions

### L. Analytics Module

- **Measures**: Trigger volume, signup conversion, stage completion, drop-off, premium conversion, time-to-progress

---

## Planned full-journey state model

Target stakeholder states for the later full journey (not the current SQLite stage enum):

```
Intent → Passport → Pathway Discovery → Income Plan → Visa Plan
  → Location Plan → Housing Plan → Document Prep → Ready to Move
  → In Japan → Settling In
```

---

## Planned expanded stakeholder profile

| Field               | Type    | Description                                                  |
| ------------------- | ------- | ------------------------------------------------------------ |
| `stakeholder_id`    | string  | Unique identifier                                            |
| `source_channel`    | enum    | youtube_chat, web, email, referral                           |
| `chat_handle`       | string  | YouTube/platform handle                                      |
| `email`             | string  | Contact email                                                |
| `current_stage`     | enum    | State model value                                            |
| `passport_status`   | enum    | yes, no, expired, in_progress, unknown                       |
| `move_timeline`     | enum    | exploring, 12_24_months, 12_months, 6_months, asap           |
| `urgency_level`     | enum    | explorer, planner, serious, imminent, urgent                 |
| `move_reason`       | string  | work, student, spouse, entrepreneur, remote, retiree, escape |
| `employment_status` | string  | Current employment situation                                 |
| `language_level`    | string  | Japanese proficiency                                         |
| `target_region`     | string  | Preferred Japan region                                       |
| `premium_interest`  | boolean | Has expressed premium interest                               |
| `notes_summary`     | text    | Agent-generated summary                                      |

---

## Optional relocation-guidance gating

| Condition                  | System Behavior                                      |
| -------------------------- | ---------------------------------------------------- |
| No passport                | Emphasize passport workflow, defer downstream stages |
| No income plan             | Do not over-focus on housing purchase                |
| No timeline                | Prioritize readiness clarification                   |
| High urgency               | Switch to fast-track guidance                        |
| High intent + high ability | Offer personal assistant tier                        |

---

## Base Camp 0 Routing Matrix

| Timeframe | Passport | Route                                   |
| --------- | -------- | --------------------------------------- |
| exploring | no       | passport-first + newsletter             |
| exploring | yes      | route to discovery later                |
| 1–2 years | no       | passport-first + low-pressure nurture   |
| 1–2 years | yes      | pathway discovery queue                 |
| 12 months | no       | passport-first + stronger CTA           |
| 12 months | yes      | next skill                              |
| 6 months  | no       | passport-first urgent tone              |
| 6 months  | yes      | fast-track next skill                   |
| ASAP      | no       | urgent passport-first + reality framing |
| ASAP      | yes      | fast-track next skill + PWA CTA         |

---

## Skill Handoff Model

| Skill                      | ID  | Responsibility                  |
| -------------------------- | --- | ------------------------------- |
| BC0_IntentAndPassportSkill | 0   | Triage, urgency, passport gate  |
| BC1_PassportSkill          | 1   | Passport acquisition guidance   |
| BC2_PathwayDiscoverySkill  | 2   | Migration pathway determination |
| BC3_WorkIncomeSkill        | 3   | Economic viability assessment   |
| BC4_VisaPlanningSkill      | 4   | Visa pathway selection          |
| BC5_LocationFitSkill       | 5   | Location matching               |
| BC6_HousingSkill           | 6   | Housing pathway                 |
| BC7_DocumentExecutionSkill | 7   | Paperwork and forms             |
