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

### Accountability integration and bounded public PoC

The Oversight source provides a legislative roadmap with named decision owners,
model documents and separate paths for congressional action and optional state
referrals. Its public diagram opens connected authority and investigation maps
with committee rules, decision gates, and fictional walkthroughs. Its senator
lookup offers public office numbers and optional local
state suggestions. The staff reference includes agent-readable source indexes.
Vote's new funding evidence page presents reviewed excerpts from original
FEC filings and links separate official roll calls. Contact Congress builds a
visitor-selected list from a dated House/Senate directory snapshot. The
[release accounting](docs/RELEASE_ACCOUNTING.md#accountability-integration)
tracks source, verification and publication separately.

The broader public candidate lookup and live FEC pipeline remain gated. The
existing `voteballots` manifest and Mall route still own that future admission.

The public Vote landing, Oversight Blueprint and Coalition pages are live. The
candidate/evidence app is an internal PoC. The original registry and manifest
labels predate the implemented chain. See the
[release accounting and Launch Pad](docs/RELEASE_ACCOUNTING.md) for evidence,
launch gates and the next product decisions.

### 2026-11-07: Oversight workstream and public front door

Oversight Blueprint is a Vote workstream under the existing `voteballots`
FoundUp, classified as an `EXISTING_FOUNDUP_UPDATE`. It does not introduce a
second tenant, token, registry entity or agent authority. WSP 109 permits a
future derivative FoundUp, but independent governance/runtime needs have not
been established for this workstream.

- [Preserved Oversight source and release procedure](oversight/README.md):
  all 155 public Site files, documents, data and instruction bundles are
  preserved with exact file identities from Sites source `c66d22af`.
- [Vote landing source](web/README.md): an informational PWA front door, separate
  from the unlaunched candidate/evidence application described below.
- [Coalition tab audit](docs/COALITION_TAB_AUDIT.md): independent public principles
  and a private, downloadable application draft. No creator participation,
  enrollment, account ownership or official status is implied or verified by
  preparing a draft. OAuth, intake and membership permissions are not live.

The preferred public address map is:

| Address | Role |
|---|---|
| <https://vote.mtrout.com/> | Vote's informational public landing |
| <https://vote.mtrout.com/coalition> | Coalition charter and local application draft |
| <https://oversight.mtrout.com/> | Oversight Blueprint, a workstream within Vote |
| <https://maga.mtrout.com/> | Retained alias for the same Oversight workstream |

Public DNS and strict hostname/certificate checks returned the correct page
with HTTP 200 for all three addresses on both public endpoints on 7 November
2026 at 00:45 UTC. The original Sites addresses remain available. Previously
configured `vote.foundups.com` and `oversight.vote.foundups.com` aliases are
retained, but are not the preferred public map; this correction removes none
of those aliases. A configured hostname is reported live only after public
DNS, TLS and correct-page verification.

The canonical shell routes remain `/f/voteballots` and `/f/voteballots/app`,
with `idb_voteballots` unchanged. Separate-origin public PWAs do not share Mall
authentication, storage or service-worker scope. Imported instruction files
are authored content; they are not admitted or running OpenClaw/WRE skills.

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
- public Vote candidate/evidence app is not launched; an informational landing
  does not satisfy that application launch gate
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

## Planned Feature - Political Claim Verification / Bullshit Meter
The 2026-10-30 intake adds a staged claim-verification capability to the existing Vote FoundUp:

1. **CV1**: asynchronous transcript analysis, ten-speech internal evaluation, CLI/review dashboard, and primary-source evidence trees.
2. **CV2**: statistical/methodological and funding/incentive audits.
3. **CV3**: caption/video evidence overlays through reusable extension/media components.
4. **CV4**: streaming ASR and a live meter with explicit pending/unknown states.

The requested 300-850 score and color bands are experimental proposals. Unknown evidence remains unscored; factual contradiction, uncertainty, funding conflict, and intent are separate. The feature is **planned / not implemented**. Internal evaluation may run alongside public PoC preparation, while public/member exposure retains its existing gates.

- [Canonical feature specification](docs/POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md)
- [Original 012 specification](docs/intake/CLAIM_VERIFICATION_SOURCE_20261030.md)

The current mock-data funding chain, live-data limitation, and public-not-launched status remain unchanged.

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
