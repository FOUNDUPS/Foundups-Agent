# RedDog Contact Memory Architecture

Status: `ARCHITECTURE_VISION` / `SPECIFIED_NOT_IMPLEMENTED`

The founding workflow described here is manual alpha evidence, not proof that a
Contact Memory runtime is wired.

## Purpose

RedDog needs a principal-scoped relationship memory so a human can meet people, exchange a card, take a photograph, speak a note, or attend a meeting without later having to manually reconstruct who the person was, why they mattered, what was discussed, or what should happen next.

This is not a generic address book and not merely RAG over a folder of images. It is a governed, provenance-preserving contact/relationship memory behind the RedDog attention boundary.

## Core Flow

```text
012 captures card/photo/name/voice note/meeting context
        |
        v
RedDog capture surface
        |
        v
encrypted evidence object + capture receipt
        |
        v
0102 extraction / normalization / entity resolution
        |
        +--> Contact entity
        +--> Organization entity
        +--> Relationship edges
        +--> Meeting / interaction events
        +--> Projects / commitments / follow-ups
        +--> source image/document provenance
        |
        +--> project/FoundUp Breadcrumb when the encounter materially advances work
        |
        v
principal-scoped contact memory index
        |
        +<---- Lick identity/encounter evidence where governed
        |
        +----> Brain/Memex current-state consolidation
        +----> Mosh Pit activity/history projection when project-relevant
        |
        v
contextual retrieval for RedDog / 0102
```

## Capture Principle

The human should be able to capture first and organize never.

A business card, LINE screenshot, handwritten note, photograph of a posted contact, or spoken description should become an ingest event. RedDog should immediately create a capture receipt and preserve the original evidence under principal-scoped encryption. Extraction and enrichment may happen asynchronously behind the surface.

The capture pipeline must not silently turn uncertain text into asserted identity. Extracted names, readings, organizations, roles, phone numbers, email addresses, social handles, locations, and relationship claims carry provenance and confidence.

## Memory Model

The canonical store should be entity/event based rather than one concatenated prose file.

### Contact entity

- canonical display name
- native-script name and reading where available
- aliases / OCR variants / nicknames
- organizations and roles, each time-bounded where possible
- communication handles
- principal-specific relationship labels
- identity confidence and unresolved ambiguities
- links to source evidence

### Interaction event

Every meaningful encounter is an immutable or append-only event containing:

- timestamp and approximate location when legitimately available
- participants
- capture source(s)
- meeting / call / message / chance encounter type
- concise factual notes
- commitments made by either side
- next actions and dates
- projects/topics involved
- confidence/provenance per extracted fact

When an interaction materially advances a FoundUp/project, the same event should be represented or referenced as a **Breadcrumb** for that project. Do not duplicate the meeting into an unrelated prose history. Contact Memory, Breadcrumbs, Brain/Memex, and Mosh Pit should project from the same underlying evidence.

### Relationship graph

Contacts connect to organizations, projects, places, meetings, other contacts, commitments, and FoundUps through typed temporal edges. Examples:

```text
Person --works_at--> Organization
Person --introduced_by--> Person
Person --supports--> YUMORI
Person --met_with--> 012
Meeting --concerned--> Project
Meeting --breadcrumb_for--> FoundUp
Commitment --owned_by--> 012 or Person
Contact --identity_evidence--> Capture
```

This makes retrieval relationship-aware rather than dependent on exact names.

## Contact RAG Is Not Enough

Vector retrieval is useful for fuzzy recall ("the dentist who introduced us to...", "the woman from the investor company", "the councilman we updated after City Hall"), but vectors are only one retrieval lane.

RedDog contact memory should combine:

1. exact identity/alias lookup;
2. temporal lookup;
3. relationship-graph traversal;
4. semantic/vector retrieval over notes and interaction summaries;
5. project/topic matching;
6. provenance/confidence filtering.

The result is an entity-centric relationship memory with RAG as one component, not a pile of embedded documents.

## Breadcrumb / Brain / Mosh Pit Integration

The layers answer different questions:

- **Contact memory**: who is this person, what is our relationship, what happened between us, and what remains open?
- **Breadcrumbs**: what materially happened in the operation/project, in sequence, with evidence?
- **Brain/Memex**: what do those events mean now — current state, open work, queued work, commitments, and next actions?
- **Mosh Pit**: what reverse-chronological history/accomplishment/status view should RedDog render for 012, the PC, a stakeholder, or another governed audience?

One interaction can therefore feed all four without becoming four independent records.

```text
Meeting Event
  -> participant edges -> Contact Memory
  -> project event/breadcrumb -> Breadcrumbs
  -> open commitment -> Brain/Memex current state
  -> selected history/status projection -> Mosh Pit
  -> evidence edge -> capture/photo/message/Lick receipt
```

This is particularly important for RedDog retrieval. When 012 asks "what have we done?" or "what do we need to go back to?", RedDog should be able to traverse project Breadcrumbs plus Brain/Memex open state while still resolving the relevant people through Contact Memory.

## Lick Integration

Lick may provide governed encounter/identity evidence for a contact, but Lick and contact memory remain separate responsibilities.

- **Contact memory** answers: who is this person in the principal's lived relationship history, when did we interact, what happened, and what remains open?
- **Lick** answers: what governed identity/encounter evidence exists for this interaction or claimed identity?

A Lick event can attach to a contact or encounter as evidence. It must not automatically grant communication, execution, financial, social, or other authority.

## AutoPost / Capture Integration

AutoPost or its successor capture lane can provide the ingest path from the principal's phone/device. A target workflow is:

```text
capture photo/card/contact screenshot
-> local/client-side intake
-> encrypt evidence for the principal
-> create immutable capture receipt
-> queue extraction
-> entity resolution against existing contact memory
-> create/update contact candidate
-> link encounter/project/context
-> create project Breadcrumb candidate if materially relevant
-> RedDog surfaces only ambiguity or required human decision
```

If a likely duplicate exists, merge must be evidence-preserving and reversible. The original captures and extraction receipts remain available even when contact entities are unified.

## Attention Behavior

Contact memory should normally stay silent. RedDog surfaces it when it changes a human decision or prevents relationship failure. Examples:

- "You met this person through Sano; last time they asked for the revised bylaws."
- "This appears to be the same person as the business card captured last month; confidence 0.86."
- "You promised to send the document after Friday's meeting and have not done so."
- "The person in this LINE thread is unresolved between two contacts; do not guess."

This follows the RedDog attention invariant: relationship context is always nearby for the twin, but only relevant consequences cross the human attention boundary.

## Privacy and Governance Invariants

1. Principal scope is mandatory; one principal's contact graph never becomes another's memory by default.
2. Original contact evidence is encrypted at rest and access is auditable.
3. Derived facts retain source provenance and confidence.
4. Uncertain identity stays uncertain until corroborated; no silent identity promotion.
5. Lick evidence does not equal general authority.
6. Sensitive fields are minimized and retained only for a legitimate principal purpose.
7. Entity merges preserve source history and must be reversible.
8. External posting/sharing of contact data requires separate governed authority.
9. The system should support deletion/forgetting policies without corrupting unrelated historical event records.
10. Raw source media should not be treated as public memory merely because it was captured for personal recall.

## Alpha Pattern

The current founding workflow is already an external alpha of this system: 012 captures screenshots, cards, photographs, meeting facts, and names; 0102 resolves them against projects and prior interactions; relevant events become operational Breadcrumbs; Brain/Memex retains the resulting state/open loops; RedDog later retrieves the relationship or project history through contact and Mosh Pit views.

The implementation objective is to convert that manual recursive behavior into a dependable principal-scoped subsystem without losing provenance, ambiguity handling, or the RedDog/0102 layer separation.
