# Vote/Ballots FoundUp - Roadmap

**Status**: Internal PoC chain complete; public PoC reopen pending  
**Current module version**: 0.6.0  
**Truth authority**: WSP 97 + `VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1.md`

---

## Current State

The original design roadmap is stale.

### Complete
- FEC adapter PoC slice
- candidate entity resolution
- funding summary
- confidence scoring
- quick answer
- shell payload integration
- 6/6 implementation slices merged
- 303 Vote tests recorded passing in the canonical closure snapshot

### Not Complete
- public Vote landing/app activation
- live public data wiring beyond current safe/mock boundaries
- locality/race/candidate roster UX
- registry/manifest status reconciliation
- Mall/portfolio promotion
- prototype features
- official or non-binding blockchain ballot execution

---

## Phase 0 - Truth / Status Reconciliation

**Goal**: reopen Vote without inheriting stale labels or duplicating infrastructure.

### Required
- [ ] HoloIndex retrieval with the exact queries in `docs/intake/INTAKE_SOURCE.md`
- [ ] verify current six-slice code/tests against closure snapshot
- [ ] reconcile README/module state vs manifest/registry `SPECIFIED_NOT_IMPLEMENTED` / `idea` labels
- [ ] audit current public catalog/portfolio state
- [ ] run WSP 109 duplicate/reuse preflight
- [ ] classify AutoPost/GotJunk/Liberty Alert/blockchain reuse surfaces

### Boundary
Docs/audit first. Runtime registry/manifest promotion occurs only in its own tested slice.

---

## Phase 1 - Public PoC: Ballot Intelligence Funnel

**Goal**: make the public FoundUp landing immediately useful without requiring member access.

### Primary User Experience
- [ ] activate canonical public Vote landing under WSP 102/104
- [ ] locality/context resolver with permission + manual fallback
- [ ] relevant race/candidate roster
- [ ] candidate cards with minimal funding/influence evidence
- [ ] confidence + provenance + trail-stop state
- [ ] candidate evidence drill-down
- [ ] RedDog conversational handoff
- [ ] capture/scan research entry using reusable capture contract where available
- [ ] existing pfMALL/member/invite gate for deeper capabilities

### Existing Core Reused
- FEC adapter
- entity resolution
- funding summary
- confidence scoring
- quick answer
- shell payload contract

### Reopen Criteria
- V1 if live FEC/API behavior is activated
- V2 for public route/entry activation
- V3 only when registry/catalog promotion is justified
- V8 if shell payload contract changes

### Success Condition
A public user can reach Vote, identify the relevant election/candidate context or receive an explicit data-gap state, inspect funding evidence, and follow the receipts without encountering a member gate.

### Explicit Non-Goals
- official ballot casting
- blockchain vote execution
- registration remediation
- influencer analytics/amplification
- resilience rings or mesh logistics
- candidate recommendation / targeted persuasion

---

## Phase 2 - Prototype A: Candidate Record + Scorecard

**Goal**: deepen candidate understanding after public PoC works.

- [ ] voting/legislative history adapters where applicable
- [ ] public actions and public communications evidence
- [ ] neutral scorecard/radar dimensions with receipts
- [ ] funding exposure
- [ ] influence/capture risk
- [ ] governance record
- [ ] communication risk
- [ ] user-selected issue/constituent alignment
- [ ] evidence strength

Every score axis must expose source evidence and confidence. No automatic endorsement/ranking.

---

## Phase 3 - Prototype B: Discovery

**Goal**: make pfMALL the place to discover civic channels/voices/content.

- [ ] rising/local/issue-specific channel discovery
- [ ] video/content browsing inside the existing shell
- [ ] RedDog conversational discovery
- [ ] explicit user feedback loops
- [ ] channel evidence/usefulness metadata

No political microtargeting or conversion optimization.

---

## Phase 4 - Prototype C: Non-Binding Cryptographic Parallel Ballot

**Goal**: create a predecessor/proving ground for auditable voting and governance primitives.

- [ ] audit WSP 96/WSP 100/current blockchain modules through HoloIndex
- [ ] define participant/credential contract
- [ ] define privacy boundary between identity and selection
- [ ] prevent duplicate/unauthorized preference signals within experiment rules
- [ ] generate cryptographically auditable receipt/tally evidence
- [ ] clearly label all signals NON-BINDING / NOT AN OFFICIAL ELECTION BALLOT
- [ ] expose aggregate direction without exposing individual choices
- [ ] threat-model coercion, linkage, replay, Sybil, key loss, and recovery

Do not build a new blockchain by default. Reuse the canonical FoundUps governance/blockchain substrate if the audit proves it suitable.

---

## Phase 5 - Prototype D: Registration Assurance

**Goal**: let consenting participants know when authoritative registration data may require attention.

- [ ] jurisdiction/official-source adapter architecture
- [ ] opt-in identity and privacy model
- [ ] minimal retained personal data
- [ ] periodic status checks with user-controlled cadence/policy
- [ ] CURRENT / ATTENTION_REQUIRED / UNKNOWN evidence states
- [ ] source + timestamp shown to user
- [ ] compliance review before any official communication/remediation automation

No silent registration changes and no autonomous official submission/mailing in the initial prototype.

---

## Phase 6 - Prototype E: Voter Resilience

**Goal**: expose voting-access friction and later support protected local resilience workflows.

Reuse candidates already evidenced:
- GotJunk map/geolocation/PWA scaffolding
- Liberty Alert GeoPoint / alert / MeshNetwork / AlertBroadcaster
- existing gate/auth patterns

Potential staged capabilities:
- [ ] public locality/friction evidence cards
- [ ] verified/inferred/unknown anomaly ledger
- [ ] gated alerts
- [ ] gated local support/coordination after compliance/security review

Do not duplicate GotJunk/Liberty Alert primitives without a reuse decision.

---

## Phase 7 - SmartDAO Governance Extraction

**Goal**: move proven generic governance primitives out of Vote-specific ownership.

- [ ] support / mandate signal contract
- [ ] reusable cryptographic vote-verification interface
- [ ] governance event/audit contract
- [ ] SmartDAO integration under current escalation/governance protocols
- [ ] tokenization/valuation hooks only after governing WSP gates

VOTE remains the civic proving FoundUp. Shared governance code belongs in the architecture selected by current WSP/codebase authority.

---

## Cross-Cutting Work

### Compliance / Trust
- political/election compliance preflight before jurisdiction-sensitive releases
- privacy and security review for identity/location/registration/ballot data
- WSP 97 truth-state enforcement
- no targeted persuasion or microtargeting

### Reuse Discipline
Before each slice:
1. HoloIndex retrieval using explicit query parameters
2. registry/module/catalog/portfolio check where relevant
3. direct code validation
4. REUSE / EXTEND / EXTRACT_SHARED / NEW decision
5. WSP 15 prioritization
6. atomic implementation/test slice

---

## Canonical Intake Packet

See `docs/intake/`:
- `OUTCOME.md`
- `SOLUTION.md`
- `PAIN.md`
- `POC_SCOPE.md`
- `PROTOTYPE_GATE.md`
- `SKILLS_MAP.md`
- `FOUNDUP_MANIFEST_DRAFT.md`
- `INTAKE_SOURCE.md`
