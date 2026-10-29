# FoundUp Feasibility & Network Intelligence Engine

**Status:** Architecture / Vision

**Purpose:** Define how FoundUps should turn a founder's idea into a living feasibility process that discovers the human network required to make the FoundUp real.

---

## 1. Origin

This capability emerged from a practical startup use case in Fukui, Japan.

A founder begins with an idea. Red Dog helps refine the idea, but a FoundUp cannot become real through idea refinement alone. It must discover and enter the human network around the opportunity: residents, customers, founders, investors, universities, government, businesses, informal leaders, elders, events, institutions, capital and community memory.

The immediate eSingularity / Tri-Village feasibility work is the first real-world proving ground, but this architecture must remain generic so any FoundUp can use it.

The intended progression is:

```text
IDEA
  ↓
RESEARCH
  ↓
NETWORK DISCOVERY
  ↓
FEASIBILITY
  ↓
COALITION
  ↓
POC / BUILD
  ↓
VALIDATION
  ↓
GROWTH
```

This is not a Fukui-specific database. It is a reusable FoundUps capability.

---

## 2. Core Principle

A founder does not only need an AI that helps refine an idea.

A founder needs an AI that helps identify, understand and enter the human network required to make the idea real.

Red Dog should therefore be capable of continuously answering questions such as:

- Who matters to this FoundUp?
- Who is already connected to whom?
- Which events are worth attending?
- Who are the formal leaders?
- Who are the informal leaders people actually trust?
- Who can introduce the founder to the next critical person?
- What evidence supports each claim about the network?
- Which feasibility assumptions are validated, contradicted or still unknown?
- What is the next highest-value human action?

---

## 3. Boundary: Red Dog, AutoPost, FoundUps and the Catalog

This capability should **not** be implemented as a monolithic AutoPost feature.

### Red Dog

Red Dog is the persistent founder-facing agent and orchestrator. It owns the founder context, understands the active FoundUp, converts conversations into structured evidence, updates feasibility state and recommends next actions.

Red Dog should orchestrate the feasibility process.

### AutoPost

AutoPost is a FoundUp and capture surface. It can provide reusable capabilities such as:

- audio capture
- video capture
- photo capture
- event/media capture
- business-card capture
- consent workflows
- transcription handoff
- location/time metadata
- source provenance

The oral-history capability belongs naturally as an **AutoPost capture skill/capability exposed to Red Dog**, but the overall feasibility engine does not belong inside AutoPost.

### FoundUp

Each FoundUp owns its feasibility objectives, evidence, network state and scorecards.

Examples:

```text
FoundUp: eSingularity
  ├── Feasibility Scorecard
  ├── Community Network
  ├── Investor Network
  ├── Customer Discovery
  ├── Events
  ├── Interviews
  ├── Evidence
  └── Opportunities
```

### FoundUps Mall / Registry / Catalog

The repository already distinguishes FoundUps through manifests and a future canonical registry. The feasibility engine should consume that identity layer rather than invent a second catalog.

A FoundUp manifest/registry entry can eventually advertise capabilities such as:

```json
{
  "capabilities": [
    "network_intelligence",
    "feasibility_scorecard",
    "oral_history_capture",
    "event_discovery"
  ]
}
```

The catalog tells Red Dog what a FoundUp or service can do. It does not store the entire feasibility graph itself.

---

## 4. Feasibility as a First-Class FoundUp Object

The founder should not operate a database directly.

The founder should be able to say:

> Create a feasibility scorecard for this FoundUp.

Red Dog then manages the underlying evidence and network state.

A feasibility object should minimally contain:

```yaml
feasibility_id:
foundup_id:
outcome:
time_horizon:
dimensions: []
assumptions: []
evidence_refs: []
network_refs: []
open_questions: []
risks: []
opportunities: []
next_best_actions: []
status:
updated_at:
```

Example dimensions:

- community support
- customer demand
- technical feasibility
- economic feasibility
- institutional support
- investor readiness
- leadership discovery
- network coverage
- regulatory feasibility
- infrastructure feasibility
- community knowledge preserved

---

## 5. Scorecards

Scorecards are the human-facing control surface for feasibility.

The database/graph is infrastructure; the scorecard is what the founder sees.

Example:

```text
TRI-VILLAGE / ESINGULARITY FEASIBILITY

Community coverage          31%
Leadership discovery        67%
Community support           58%
Institutional support       35%
Capital network             18%
Community knowledge saved   22%

HIGH-VALUE DISCOVERY
Sato-san
Mentioned independently by six residents.
Not yet interviewed.

NEXT BEST ACTION
Meet Sato-san.
```

The scorecard must be evidence-backed rather than manually decorative.

---

## 6. Network Intelligence Graph

The feasibility layer requires a reusable relationship graph.

Core entity classes:

```text
Person
Organization
FoundUp
Event
Interaction
Relationship
Project
Funding
Opportunity
Place
Artifact / Evidence
Consent
Scorecard
```

Important relationship examples:

```text
works_at
founded
invested_in
advises
introduced_by
funded_by
attended
spoke_at
met_with
referred_to
trusted_by
opposes
supports
owns
lives_in
remembers
connected_to_place
```

Every inferred or asserted relationship should carry provenance and confidence.

Example:

```text
Sato-san
  ← referred_to by Resident A
  ← referred_to by Resident B
  ← referred_to by Resident C
  → network centrality increases
```

Repeated independent referrals are a useful signal of informal influence.

---

## 7. Formal Power vs Informal Power

Feasibility must distinguish official authority from actual community influence.

### Formal power

- elected office
- government authority
- ownership
- capital
- institutional role
- legal decision rights

### Informal power

- community trust
- reputation
- family networks
- historical legitimacy
- ability to introduce people
- ability to mobilize support or opposition
- repeated independent referrals

A person with no formal title may be more important to project feasibility than a titled official.

Red Dog should surface both.

---

## 8. Event Scout

Events are network-entry opportunities, not merely calendar entries.

A lightweight scout/worker should continuously discover relevant events for the active FoundUp and attach them to the feasibility graph.

Event intelligence should include:

```yaml
event_id:
name:
time:
place:
organizers: []
speakers: []
companies: []
known_attendees: []
investors: []
themes: []
registration:
source_refs: []
network_value_score:
relevance_score:
recommended_people_to_meet: []
```

The useful Red Dog output is not:

> There is an event Thursday.

It is:

> Three people already relevant to your FoundUp will be there. One is directly connected to the investor you are trying to reach. This event has high network value.

After the event, AutoPost or other capture surfaces can feed photos, business cards, notes, conversations and evidence back into the graph.

---

## 9. Community Feasibility and Oral History

The Tri-Village use case exposes another important capability: feasibility can simultaneously preserve community knowledge.

Many residents—especially older residents, farmers and people who do not live online—may have little or no digital footprint. Their knowledge exists in their memories, voices, photographs and relationships.

The feasibility process can preserve that knowledge with explicit permission.

This is not incidental archival work. It can improve feasibility because local history reveals:

- what existed before
- what people value
- what people fear losing
- why prior projects succeeded or failed
- which families and people hold trust
- how land and institutions actually function
- which stories define community identity

The guiding principle is:

> **Before deciding what a place becomes next, learn from the people who remember what it was.**

---

## 10. AutoPost Oral-History Capture Skill

AutoPost should eventually expose a consent-gated oral-history capture capability to Red Dog.

Conceptual flow:

```text
Conversation
   ↓
Red Dog detects oral-history context
   ↓
Explicit consent flow
   ↓
AutoPost capture
   ↓
Original audio/video preserved
   ↓
Transcript / translation
   ↓
Entity + relationship extraction
   ↓
Evidence + provenance
   ↓
FoundUp feasibility graph
   ↓
Scorecard update / next action
```

The source recording must remain distinguishable from derived artifacts such as transcripts, translations and summaries.

---

## 11. Consent Is a First-Class Object

Recording does not imply permission to publish.

Consent should be independently represented and capable of expressing choices such as:

- may record
- may transcribe
- may translate
- may preserve privately
- may use in feasibility research
- may attach participant name
- may preserve original voice
- may share with family/community
- may publish publicly
- may use supplied photographs/documents
- retention preference
- later withdrawal/change status

A participant should be able to permit one use while declining another.

Example conceptual object:

```yaml
consent_id:
person_id:
artifact_ids: []
recording_allowed: true
transcription_allowed: true
translation_allowed: true
private_archive_allowed: true
feasibility_use_allowed: true
public_release_allowed: false
voice_release_allowed: false
name_release_allowed: true
captured_at:
consent_evidence_ref:
status: active
```

---

## 12. Community Memory Artifact

With permission, each interview can generate a structured record:

```text
VOICE
Original recording

STORY
Transcript + translation

PERSON
Who told the story

PLACE
Where the memory belongs

TIME
Approximate era

RELATIONSHIPS
People/families/organizations mentioned

MEMORIES
What happened / what existed / what changed

PHOTOS
Historical + current images

PROVENANCE
What came from whom

CONSENT
What may be preserved or shared
```

A future place-based interface could allow a user to touch a field, river, house or former onsen location and hear permitted stories tied to that place.

---

## 13. Interview Loop

A human interview should remain a human conversation. Red Dog structures it afterward or assists unobtrusively.

Useful prompts include:

- Tell me about yourself and your connection to this place.
- What was this area like when you were younger?
- What was here before?
- What did your parents or grandparents tell you?
- What changed?
- What was lost?
- What should never be lost?
- What would you like this area to become?
- What concerns you about this project?
- Who else should we speak with?
- Who do people listen to when something important happens here?

Optional, with explicit permission:

> What would you like your grandchildren, great-grandchildren or people living here decades from now to hear in your own voice?

---

## 14. Founder Workflow

The intended founder experience is conversational.

```text
012: I have an idea.
Red Dog: creates / enters FoundUp context.

012: Let's test whether this is viable.
Red Dog: creates feasibility scorecard.

Red Dog: discovers relevant events, people, institutions and evidence.

012: I met Tanaka-san today. He says everyone listens to Sato-san.
Red Dog: updates graph, provenance and leadership score.

012: Update feasibility.
Red Dog: shows evidence-backed scorecard and next best action.
```

The founder should not need to manually maintain a CRM, spreadsheet or graph database.

---

## 15. Relationship to Red Dog Vision

This architecture extends the existing Red Dog principle that conversation becomes work.

For real-world FoundUps, some of that work is not code generation. It is:

- discovering people
- finding events
- interviewing stakeholders
- gathering evidence
- preserving knowledge
- making introductions
- building coalitions
- testing assumptions

Red Dog should orchestrate these activities through specialized workers and FoundUp capabilities just as it orchestrates computational work.

---

## 16. Relationship to FoundUp Registry / Catalog

Do not create a parallel catalog for feasibility.

The existing FoundUp manifest + future canonical registry should remain the identity/discovery source for FoundUps and services.

The feasibility engine should reference canonical `foundup_id` / registry identity and attach its own operational data to that identity.

Conceptually:

```text
CANONICAL FOUNDUP REGISTRY
        │
        ├── identity
        ├── lifecycle
        ├── manifest
        ├── entry URL
        └── advertised capabilities
                 │
                 ▼
        RED DOG / FOUNDER CONTEXT
                 │
                 ▼
        FEASIBILITY ENGINE
                 │
      ┌──────────┼───────────┐
      ▼          ▼           ▼
   Network     Events      Evidence
      │          │           │
      └──────────┼───────────┘
                 ▼
             Scorecards
```

The registry answers **what FoundUps exist and what they can do**.

The feasibility graph answers **what is currently known about making this FoundUp real**.

---

## 17. Implementation Guidance

This document intentionally does not prescribe a final storage engine yet.

Do not begin by selecting Neo4j, Postgres, SQLite or another database solely because the model looks graph-like.

First establish contracts for:

1. canonical entity IDs
2. evidence/provenance
3. consent
4. relationship edges
5. scorecards
6. event ingestion
7. capability discovery
8. FoundUp identity binding
9. Red Dog query/update interface

Storage can then be selected against actual access patterns.

The first implementation should be thin and auditable.

---

## 18. Suggested Initial Slices

### Slice A — Feasibility contract

Define typed objects for scorecard, assumption, evidence, person, organization, relationship, event, interaction and consent.

### Slice B — Red Dog feasibility skill

Allow Red Dog to create, retrieve and update a feasibility scorecard for an active FoundUp.

### Slice C — Event Scout

Discover and rank events by FoundUp/network relevance.

### Slice D — AutoPost oral-history capture contract

Define consent-gated audio/video capture and provenance handoff. Implement in the AutoPost repository only after the cross-repository interface is agreed.

### Slice E — Tri-Village pilot

Use eSingularity as the first end-to-end real-world feasibility dataset and validate the model against actual interviews, events, introductions and evidence.

---

## 19. WSP Position

No new WSP is required merely to document this architecture.

Implementation must follow the repository's existing WSP governance, especially repository truth, module boundaries, documentation discipline and pre-action research.

A WSP should only be changed or added if implementation exposes a genuinely missing cross-system protocol. Product behavior and feature architecture should remain in normal architecture/contracts rather than being forced into WSP text.

---

## 20. North Star

A FoundUp succeeds by turning an idea into a network capable of carrying the idea into reality.

Red Dog should help the founder discover and grow that network while preserving evidence, provenance, consent and community knowledge.

The desired loop is:

```text
FOUNDER IDEA
    ↓
RED DOG
    ↓
RESEARCH + EVENT DISCOVERY + HUMAN NETWORK
    ↓
FEASIBILITY EVIDENCE
    ↓
SCORECARD
    ↓
NEXT BEST ACTION
    ↓
HUMAN / AGENT ACTION
    ↓
NEW EVIDENCE
    ↺
```

The feasibility study is therefore not a static report.

It is a living process by which a founder and Red Dog learn whether a FoundUp can become real—and who must become part of the network to make it happen.
