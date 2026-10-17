# Move2Japan FoundUp — System Architecture (012 Architecture Vision)

_Source: 012 voice-mode conversation, captured 2026-03-07_

> Historical March architecture. The current house-first build order and
> implementation boundaries are in [the roadmap](../ROADMAP.md) and
> [housing audit](08_HOUSING_DISCOVERY_REBASELINE.md). URL spellings below were
> corrected on 2026-10-17; the proposed secondary PWA is not a verified deployed
> service. The full journey/profile remains planned beyond implemented BC0.

## Primary Surfaces

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

## Core Modules

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

## State Model

Canonical stakeholder states:

```
Intent → Passport → Pathway Discovery → Income Plan → Visa Plan
  → Location Plan → Housing Plan → Document Prep → Ready to Move
  → In Japan → Settling In
```

---

## Minimum Required Profile Fields

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

## Gating Logic

| Condition                  | System Behavior                       |
| -------------------------- | ------------------------------------- |
| No passport                | Emphasize passport workflow           |
| No income plan             | Do not over-focus on housing purchase |
| No timeline                | Prioritize readiness clarification    |
| High urgency               | Switch to fast-track guidance         |
| High intent + high ability | Offer personal assistant tier         |

---

## Architecture Principle

> The chat is not the product. The chat is the top of funnel plus continuity layer. The roadmap engine plus memory layer is the product core.
