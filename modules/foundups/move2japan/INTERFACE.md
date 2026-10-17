# Move2Japan interface (WSP 11)

Updated 2026-10-17 JST. Current website priority: English public house discovery.
[The implementation audit](docs/08_HOUSING_DISCOVERY_REBASELINE.md) records source
and reuse evidence; [the roadmap](ROADMAP.md) owns the staged acceptance gates.

## Public property discovery

Source owners: `public/move2japan/index.html`, `properties.json`,
`property-search.js` and `move2japan.css`. The page composes the existing shared
Mall tile field, detail plane and gesture components from `public/member/`.
It does not introduce an authenticated publisher or payment API.

### Catalog contract

The envelope uses `schema_version=move2japan_property_catalog.v1`,
`catalog_kind=curated_public_source_observations`, `foundup_id=move2japan`, an
`observed_on` date, coverage description and a `properties` array. It is a
bounded public source snapshot, not a continuously live or complete inventory.

| Record fields | Meaning |
| --- | --- |
| `foundup_id`, `source_type` | Existing tenant `move2japan`; `property_listing` presentation |
| `listing_id`, `source_item_id` | Stable property identity and original source record ID; never a new FoundUp ID |
| `name`, `summary`, `tags` | Original English factual discovery copy; not an assertion of suitability |
| `transaction`, `price_jpy` | Source transaction type and stated JPY amount; no inferred total purchase cost |
| `prefecture`, `municipality`, `address_ja` | Source location; no invented parcel coordinates |
| `land_area_m2`, `building_area_m2`, `building_area_label_ja` | Original area meaning retained; `建築面積` is not silently converted to usable floor area |
| `floors`, `construction_date`, `repair_level` | Source facts; missing dates/condition remain null or unknown |
| `source_name`, `source_url`, `last_checked`, `source_updated_at` | Provenance and observation date; an unknown source update time remains null |
| `availability`, `broker_availability_confirmed` | `source_listed` is a source observation, not broker-confirmed availability |
| `virtual_tour_at_source`, `media_permission` | Tours remain at source; a public listing does not itself grant media reuse |

The initial five records are Fukui bank observations. Restricted offers, member
release data, personal account records and uploaded files do not belong in this
public catalog. Future private feeds must authorize and filter before sending
records to the browser.

### Presentation and navigation

- Search/filter this public catalog and open the selected listing in the shared
  Mall detail plane. Multiple houses share `foundup_id=move2japan`; selection
  must retain the particular listing identity.
- Render source facts with escaped text/attributes. Source navigation uses HTTPS
  URLs without embedded credentials; unsupported/unsafe input must not become
  executable markup or an active link.
- Keep visible controls alongside gestures and preserve keyboard navigation.
- Link to the original source for photos, tours, detailed conditions and inquiry.
- Do not initiate payment, reservation, brokerage or a property publication by
  opening a tile or following a discovery action.

The main Mall YouTube catalog and existing canonical registry are not replaced
or promoted by this public page.

## Shared account boundary

Account entry: `https://foundups.com/member/`. Current owner:
`public/member/index.html` (`initClerkAuth`, invite check, username and Mall init).
It proves no paid Move2Japan benefit. Website discovery remains public.

Prototype requires a verified account link and publisher authority. A YouTube
channel ID, Clerk principal and GotJunk/Firebase UID are separate identifiers;
do not infer identity equality from display names or email text. Browser
`postMessage`, local storage and displayed balances cannot grant protected access.

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
| `target_region`     | string  | Preferred region in Japan                                    |
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
