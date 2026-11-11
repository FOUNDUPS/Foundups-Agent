# Move2Japan FoundUp — System Architecture

_Current source boundary: 2026-10-18 UTC. The March 2026 architecture vision is
retained below as historical planning._

## Current shared-Mall product

Move2Japan is selected inside `public/member/index.html` by
`/member/?foundup=move2japan`. The existing Mall owns boot, account/RedDog,
geographic field/detail planes, gestures, state and the `/member/` PWA. The
housing adapter supplies the domain templates, filters and eight public Fukui
source observations. `/move2japan/` now redirects into that shell.

| Boundary | Current implementation |
| --- | --- |
| Public registration | Same `move2japan` tenant, discoverable incubating FoundUp, declarative manifest; `/f/move2japan` and public portfolio link to Browse houses |
| Product selection | Exactly one `foundup=move2japan` selects public housing inside `/member/`; no independent application boot |
| Guest discovery | Public catalog and filters load independently of Clerk/Firebase availability |
| Existing account | Read-only Clerk plus invite and username admission; existing RedDog member presentation, cleared on sign-out/account changes |
| Account return | Explicit existing account flow, then one-use 15-minute return to fixed public product and safe filters |
| State and cache | Separate video/product positions; fixed public shell/catalog cache paths retain original source dates |
| Protected app | `/f/move2japan/app` participation gate remains; publisher service is a prototype target |
| Paid service and tokens | Actual paid benefit delivery remains the MVP gate; `TOKEN_DEFERRED`, no issuance or paid entitlement |

The earlier separate PWA at `move2japan.foundups.com` is superseded as the product
architecture. `move2japan.info` is the intended public brand/domain and requires
verified forwarding to the shared product. The same private Site is a review
mirror only. Its successful 2026-10-17 publication belongs to the superseded
standalone composition, not this source revision.

Production Firebase Hosting has not been deployed in this session. The target is
project `gen-lang-client-0061781628`, site `foundupscom`; authenticated hosting
access is unavailable here. Browser and served-page receipts remain separate.
Current build order and evidence: [roadmap](../ROADMAP.md),
[interface](../INTERFACE.md), [housing audit](08_HOUSING_DISCOVERY_REBASELINE.md).

## Historical March surface plan — superseded

Source: 012 voice-mode conversation, captured 2026-03-07. The full journey and
expanded profile remain planned beyond implemented BC0. These surface and
service descriptions are retained as history, not current deployment claims.

### 1. YouTube Live Chat

- **Purpose**: Capture intent, trigger first interaction, offer immediate help, route to signup
- **Trigger**: `!move2japan`
- **Integration**: YT DAE (Domain Autonomous Agent)

### 2. Proposed Move2Japan Web Hub — `move2japan.foundups.com`

- **Purpose**: Persistent stakeholder account, roadmap tracking, checklists, content hub, updates, premium upsells, agent interaction history
- **Type**: Progressive Web App (PWA)

### 3. Agent Layer

- **Purpose**: Ask next-best question, remember prior state, personalize guidance, trigger follow-ups, unlock next stage only when relevant

### 4. Human Partner Layer

- **Purpose**: High-trust tasks — legal, accounting, real estate support, English-speaking brokers, relocation specialists

---

## Retained future journey modules

### A. Intent Capture Module

- **Inputs**: Live chat trigger, site CTA, lead forms, newsletter signup
- **Outputs**: Stakeholder record, source attribution, current stage = Intent

### B. Stakeholder Memory Module

**Stores**: Chat identity, email, progress stage, answers to key questions, preferences, urgency, premium status, partner referral status
**Must support**: Cross-channel identity resolution, resumable conversations, agent-readable summaries

### C. Roadmap Engine

**Controls**: Base camp progression, checklist state, prerequisite gates, unlock conditions, reminders
**Example**: Passport not complete → job and visa planning stay mostly locked.

### D. Conversation Orchestrator

**Determines**: What question to ask next, whether to stay in chat or route to site, when to offer signup, when to upsell premium, when to escalate to human

### E. Knowledge Engine

**Contains**: Visa overviews, passport prep, job pathways, housing options, city comparisons, relocation timelines, document checklists, policy updates
**Needs**: Freshness review, source traceability, admin update workflow

### F. Dream Life Discovery Module

**Purpose**: Translate abstract desire into concrete relocation path.
**Questions**: Why Japan? What kind of daily life? What climate and city size? Optimizing for cost, work, family, dating, creativity, safety, culture?
**Outputs**: Recommended regions, recommended migration path, recommended job/housing strategy

### G. Job Pathway Module

**Tracks**: Education, language level, industry, remote compatibility, sponsorship likelihood, salary targets, timeline
**Premium path**: Personal job-finding agent

### H. Housing Module

**Purpose**: Guide first landing housing, then ideal housing.
**Later automate**: Search aggregation, partner referrals, shortlist generation, intake for brokers

### I. Form/Document Automation Module (Future Premium)

- Prefill applications
- Translate required fields
- Generate document checklists
- Draft emails in Japanese
- Remind stakeholder what is missing

### J. News and Policy Update Module

**Purpose**: Act like an internal Substack/news desk.
**Agents publish**: Visa changes, policy shifts, work trends, housing news, relocation warnings, city spotlights

### K. Monetization Module

**Supports**: Free, premium, concierge, referral revenue, brokerage commission split

### L. Analytics Module

**Measures**: Trigger volume, signup conversion, stage completion, drop-off by stage, premium conversion, partner conversion, time-to-progress

---

## Planned full-journey state model

Target stakeholder states beyond the current BC0 persistence:

```
Intent → Passport → Pathway Discovery → Income Plan → Visa Plan
  → Location Plan → Housing Plan → Document Prep → Ready to Move
  → In Japan → Settling In
```

---

## Planned expanded profile fields

| Field             | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| stakeholder_id    | Unique identifier                                            |
| source_channel    | YouTube chat, web, email, referral                           |
| chat_handle       | Platform handle                                              |
| email             | Contact email                                                |
| current_stage     | State model value                                            |
| passport_status   | yes / no / expired / in_progress / unknown                   |
| move_timeline     | Timeline estimate                                            |
| move_reason       | Work, student, spouse, entrepreneur, remote, retiree, escape |
| employment_status | Current employment                                           |
| language_level    | Japanese proficiency                                         |
| target_region     | Preferred Japan region                                       |
| premium_interest  | Premium interest flag                                        |
| notes_summary     | Agent-generated summary                                      |

---

## Optional personal-journey gating

These guidance gates do not block public house discovery.

| Condition                  | System Behavior                       |
| -------------------------- | ------------------------------------- |
| No passport                | Emphasize passport workflow           |
| No income plan             | Do not over-focus on housing purchase |
| No timeline                | Prioritize readiness clarification    |
| High urgency               | Switch to fast-track guidance         |
| High intent + high ability | Offer personal assistant tier         |

---

## Historical March architecture principle

> The chat is not the product. The chat is the top of funnel plus continuity layer. The roadmap engine plus memory layer is the product core.
