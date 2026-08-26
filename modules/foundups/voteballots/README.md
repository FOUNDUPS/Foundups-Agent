# Vote/Ballots FoundUp

**Status**: Internal PoC implementation complete; public PoC not launched  
**Module Version**: 0.6.0 (`src/__init__.py`)  
**FoundUp ID**: `voteballots`  
**Token Symbol**: `VOTE`  
**Owner**: 0102

---

## Purpose

VOTE is an evidence-first civic FoundUp. It begins with political transparency: show the relevant candidate/race context, expose disclosed funding and influence evidence, preserve provenance, and make the WSP 97 truth boundary visible (`VERIFIED / INFERRED / UNKNOWN`).

VOTE then expands behind the existing pfMALL/member gate into deeper candidate records, discovery, non-binding cryptographic preference signaling, registration assurance, voter-resilience capabilities, and eventually reusable voting/mandate primitives for FoundUp SmartDAOs.

**Political safety boundary**: public and member research surfaces provide evidence and user-controlled comparison. VOTE does not perform targeted political persuasion, microtargeting, or automated candidate endorsement.

---

## Current Truth State

The original README/manifest/registry labels predate the implemented PoC chain and are partially stale.

### Implemented Internal PoC Chain

Six implementation slices are merged:

1. FEC adapter
2. candidate entity resolution
3. funding summary
4. WSP 97 confidence scoring
5. quick-answer generation
6. local shell payload integration

Canonical closure evidence: `docs/audits/architecture/VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1.md` records **6/6 slices merged and 303 tests passing**.

### Not Yet Publicly Activated

- `entry_url` remains empty
- public Vote app is not launched
- current shell integration is a local payload contract only
- Vote is present in the canonical FoundUp registry but is not currently listed in `public/member/mall-catalog.json` or `public/f/portfolio_data.json`
- registry/manifest implementation labels require a dedicated reconciliation slice before promotion

**Implementation-complete does not mean public-launched.**

---

## Public PoC - Next Product Surface

The public PoC is the open FoundUp landing/funnel surface, not the gated prototype.

Minimum experience:

1. Open the canonical public Vote FoundUp landing.
2. Resolve election locality/context with permission and a manual fallback.
3. Show relevant race/candidate cards.
4. Show a minimal funding/influence summary with provenance and trail-stop markers.
5. Tap into evidence detail or ask RedDog.
6. Optionally invoke capture/scan research through a reusable capture contract rather than a new Vote-specific camera stack.
7. Route deeper features through the existing pfMALL/member/invite gate.

Candidate-card PoC minimum:
- candidate / office / race
- funding exposure summary
- major disclosed funding sources available from current evidence
- evidence strength/confidence
- trail termination
- details / ask RedDog action

See `docs/intake/POC_SCOPE.md`.

---

## Prototype Direction

After the public PoC passes its gate, prototype slices may add:

- voting/legislative history and deeper candidate public record
- neutral evidence-backed radar/spider scorecard
- pfMALL discovery of channels/voices/content
- non-binding cryptographic parallel ballot for preference-signal testing
- opt-in official-source registration assurance
- voter-resilience locality/map/evidence capabilities using existing GotJunk/Liberty Alert patterns where valid

The in-app parallel ballot must be explicitly labeled **non-binding / not an official election ballot** unless a separate legal/certification gate is satisfied.

See `docs/intake/PROTOTYPE_GATE.md`.

---

## Reuse-First Architecture

Before new implementation, workers must retrieve through HoloIndex and validate against current code. Priority reuse targets:

- VOTE existing FEC/entity/funding/confidence/answer/shell chain
- pfMALL public `/f/{foundup_id}` and gated `/app` model
- AutoPost reusable capture-engine work
- GotJunk PWA/geolocation/map patterns
- Liberty Alert GeoPoint/alert/mesh/broadcast primitives
- existing FoundUps blockchain, tokenization, governance, and SmartDAO protocols

Do not create parallel shells, capture engines, maps, auth layers, or blockchain systems without proving reuse is insufficient.

Required retrieval queries are recorded in `docs/intake/INTAKE_SOURCE.md` and `docs/intake/SKILLS_MAP.md`.

---

## Route Namespace

Canonical routing follows WSP 104:

| Field | Value |
|---|---|
| `foundup_id` | `voteballots` |
| `routing_prefix` | `/f/voteballots` |
| Landing route | `/f/voteballots` |
| App mount | `/f/voteballots/app` |

The route contract exists. Public activation remains a separate governed slice.

---

## WSP 97 Truth Boundary

All material outputs preserve explicit evidence states:

- `VERIFIED_FACT`
- `HIGH_CONFIDENCE_INFERENCE`
- `LOW_CONFIDENCE_INFERENCE`
- `UNKNOWN`

Rules:
1. hidden/dark funding is never stated as verified fact without evidence
2. direct disclosure is separated from inferred alignment
3. influence categories are not flattened into one accusation
4. evidence trail termination is shown
5. high-impact/low-confidence claims trigger review
6. no new candidate recommendation or targeted-persuasion behavior is introduced by the evidence pipeline

---

## WSP 109 Canonical Intake Packet

`docs/intake/` now contains the WSP 109 update packet:

- `INTAKE_SOURCE.md`
- `OUTCOME.md`
- `SOLUTION.md`
- `PAIN.md`
- `POC_SCOPE.md`
- `PROTOTYPE_GATE.md`
- `SKILLS_MAP.md`
- `FOUNDUP_MANIFEST_DRAFT.md`

This is an **EXISTING_FOUNDUP_UPDATE**, not a new FoundUp.

---

## Architecture / Interfaces

- `INTERFACE.md` - current public/data contract specification
- `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md` - detailed AI architecture
- `ROADMAP.md` - current staged roadmap
- `ModLog.md` - implementation history
- `tests/README.md` - test inventory

---

## Governing WSPs / Contracts

Relevant current authorities include:
- WSP 97 - system execution / truth discipline
- WSP 99 - machine-to-machine worker prompting
- WSP 102 - FoundUps web design / shell boundary
- WSP 104 - FoundUp route namespace / tenant isolation
- WSP 109 - FoundUp intake and duplicate-discovery protocol
- WSP 96 - governance/consensus research path
- WSP 100 - DAE -> SmartDAO escalation

Final ownership/naming must always defer to current codebase/WSP authority at execution time.
