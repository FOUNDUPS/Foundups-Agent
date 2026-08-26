# VOTE_WSP109_REOPEN_AND_PUBLIC_POC_ARCHITECT_PACKET_PHASE1

**Date**: 2026-08-26  
**Mode**: ARCHITECT / DOCS-ONLY REOPEN PACKET  
**FoundUp**: existing `voteballots`  
**WSP Basis**: WSP 00, 97, 99, 109, 102, 104; consult 15/22/50/95/96/100 as retrieved  

---

## 1. Architect Verdict

VOTE is **not a new FoundUp**. It is an `EXISTING_FOUNDUP_UPDATE` with a real internal PoC implementation and stale public/readiness labels.

The correct next objective is **not** another funding-engine slice. The correct next objective is to reopen VOTE under its existing V2 public-surface criterion and build the **public PoC ballot-intelligence funnel**, while separately reconciling registry/manifest status.

Truth state verified from current repository evidence:

- six Vote PoC implementation slices are merged
- canonical closure snapshot records 303 tests passing
- public launch is still closed (`entry_url` empty)
- Vote exists in the canonical FoundUp registry
- Vote is absent from the current public Mall catalog and public portfolio projection
- manifest/registry/legacy README labels understate the implemented internal PoC and must be reconciled in a separate atomic slice

No runtime/registry/manifest/catalog mutation is authorized by this packet.

---

## 2. Required HoloIndex Preflight

**HoloIndex is the retrieval/memory plane. Workers MUST run these queries before direct code reads. Direct reads verify or recover low-signal/missing HoloIndex results; they do not replace the preflight.**

### Lane A - Current VOTE truth
```text
voteballots Vote PoC FEC entity resolution funding summary confidence quick answer shell integration
VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT 303 tests public launch entry_url
voteballots manifest registry implementation state poc status
```

### Lane B - Public PoC / pfMALL
```text
public FoundUp landing /f foundup_id app pfMALL WSP 102 WSP 104
VOTE public PoC landing candidate cards locality race roster
pfMALL invite OAuth member gate app mount RedDog concierge
```

### Lane C - Capture reuse
```text
AutoPost reusable capture engine camera capture source recognition scan
GotJunk capture camera PWA geolocation swipe
capture to research media object RedDog intent FoundUp
```

### Lane D - Locality / resilience reuse
```text
GotJunk map architecture geolocation Leaflet Liberty Alert Easter egg
Liberty Alert MeshNetwork AlertBroadcaster GeoPoint ThreatType
voter resilience map evidence alert locality shared FoundUp component
```

### Lane E - Governance / blockchain
```text
WSP 96 governance voting blockchain consensus
WSP 100 SmartDAO escalation governance layer
WSP 26 tokenization blockchain FoundUp token governance
blockchain integration voting verification receipt privacy identity
```

### Lane F - Intake / duplication / component harvest
```text
WSP 109 duplicate discovery FoundUp extension derivative reuse
FoundUp registry mall catalog portfolio public surface
FoundUp reusable PWA component template extraction
```

### Lane G - Compliance / trust
```text
political compliance FEC public communication disclaimer coordination
voter registration assurance privacy official source consent
political safety no targeted persuasion no microtargeting candidate recommendation
```

For every lane report:
- `HIGH | MEDIUM | LOW | MISSING`
- top artifact paths
- stale/noisy hits
- direct-read fallback used
- reusable component decision

---

## 3. Worker Topology - Architect Decides After Retrieval

Do not hard-code final worker count or names. The architect should instantiate the minimum worker set after HoloIndex returns. The work domains that must be covered are:

1. **Existing FoundUp / extension detection**
   - confirm VOTE lineage and prevent duplicate FoundUp creation

2. **Reuse harvest**
   - classify components as `REUSE_AS_IS`, `EXTEND_EXISTING`, `EXTRACT_SHARED_COMPONENT`, `NEW_VOTE_SPECIFIC`

3. **Public PoC surface**
   - pfMALL/WSP 102/104 landing, locality, candidate cards, evidence drill-down

4. **Status reconciliation**
   - current code/test truth vs registry/manifest/catalog/portfolio labels

5. **Compliance/trust**
   - public political information, registration assurance, privacy, later cryptographic signaling

6. **Prototype/governance path**
   - candidate record, discovery, parallel ballot, registration assurance, resilience, SmartDAO extraction

---

## 4. Public PoC Definition

### Goal
The public PoC is the open VOTE FoundUp landing/funnel surface. It must provide real civic value before the user enters the gated prototype.

### Minimum user journey
```text
public Vote landing
  -> locality / election context
  -> relevant races + candidate cards
  -> funding / influence evidence summary
  -> VERIFIED / INFERRED / UNKNOWN + trail stop
  -> candidate evidence detail or Ask RedDog
  -> optional capture/scan -> research intent
  -> deeper feature request -> existing pfMALL/member/invite gate
```

### Reuse requirements
- preserve current Vote FEC/entity/funding/confidence/quick-answer/shell semantics
- use the existing `/f/{foundup_id}` landing contract
- do not create a parallel shell
- adapt the shared/AutoPost capture contract rather than writing a Vote-only camera stack unless audit proves reuse impossible
- reuse locality/map primitives from GotJunk only through a clean interface; do not couple Vote directly to GotJunk UI implementation if a shared extraction is warranted

### PoC exclusions
- official election voting
- blockchain ballot execution
- registration remediation
- resilience-ring logistics
- influencer amplification/analytics
- personalized candidate recommendation
- political microtargeting

---

## 5. Atomic Next Slices

The architect should score under current WSP 15 after retrieval. Candidate order:

### P0-A - `VOTE_STATUS_RECONCILIATION_PHASE1`
Docs + registry/manifest truth reconciliation only after tests/schema impact are known.

Expected result:
- internal implementation status accurately represented
- public launch remains separate
- no false promotion to prototype/MVP

### P0-B - `VOTE_PUBLIC_POC_LANDING_PHASE1`
Build the smallest public Vote landing using existing pfMALL route contract.

Expected result:
- public page reachable
- readiness truthful
- static/mock-safe candidate card path if live adapters are not yet approved

### P0-C - `VOTE_LOCAL_RACE_CONTEXT_PHASE1`
Add the smallest authoritative locality/race/candidate roster adapter and explicit data-gap state.

### P0-D - `VOTE_PUBLIC_EVIDENCE_CARD_PHASE1`
Wire existing evidence chain into candidate cards without changing confidence semantics.

### P1 - `VOTE_CAPTURE_TO_RESEARCH_ADAPTER_PHASE1`
Reuse/extract the capture primitive and map media capture to a research intent.

### P1 - `VOTE_PUBLIC_POC_GATE_HANDOFF_PHASE1`
Verify the public-to-member/prototype handoff through current gate/auth flow.

Only after public PoC gate passes should prototype slices begin.

---

## 6. Prototype Sequence

### A. Candidate record / scorecard
Voting record, public actions/communications, neutral evidence-backed dimensions, spider/radar summary with receipts.

### B. Discovery
pfMALL civic channels/content discovery and explicit user feedback.

### C. Non-binding cryptographic parallel ballot
A predecessor/proving ground for privacy-preserving, auditable preference signals. MUST display `NON_BINDING / NOT AN OFFICIAL ELECTION BALLOT` until a separate certification/legal authority exists.

### D. Registration assurance
Opt-in official-source status checks only; no silent changes or autonomous official submission in initial prototype.

### E. Voter resilience
Reuse map/geolocation/evidence/alert/mesh patterns; public truth may remain open, active coordination remains gated and compliance-reviewed.

### F. SmartDAO extraction
Move proven generic voting/mandate/verification primitives into shared FoundUps governance architecture under current WSP 96/100/other canonical authority.

---

## 7. WSP 99 M2M Architect Envelope

```yaml
schema: 0102_m2m_v1
ROLE: architect
ORIGIN: internal_handoff
PRINCIPAL_REF: 012
L: ORCH
S: EXISTING_VOTE_FOUNDUP_SCOPE_FROM_HOLO
M: plan
T: vote_reopen_public_poc_phase1
R: [00,97,99,109,102,104]
I:
  HOLO_FIRST: true
  HOLO_QUERIES:
    - "voteballots Vote PoC FEC entity resolution funding summary confidence quick answer shell integration"
    - "VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT 303 tests public launch entry_url"
    - "public FoundUp landing /f foundup_id app pfMALL WSP 102 WSP 104"
    - "AutoPost reusable capture engine camera capture source recognition scan"
    - "GotJunk map architecture geolocation Liberty Alert Easter egg"
    - "WSP 96 governance voting blockchain consensus WSP 100 SmartDAO escalation"
    - "WSP 109 duplicate discovery FoundUp extension reuse registry catalog portfolio"
  EXISTING_FOUNDUP_UPDATE: true
  REUSE_BEFORE_BUILD: true
  NO_VIBECODING: true
  NO_HARDCODED_NEW_OWNERSHIP: true
  PUBLIC_POC_FIRST: true
  PROTOTYPE_GATED: true
  TRUTH_BOUNDARY: [VERIFIED, INFERRED, UNKNOWN]
  NO_TARGETED_PERSUASION: true
  NO_MICROTARGETING: true
  NON_BINDING_BALLOT_ONLY_UNTIL_SEPARATE_GATE: true
O:
  - holo_retrieval_report
  - extension_detection_verdict
  - reuse_harvest_matrix
  - current_vote_truth_reconciliation
  - public_poc_atomic_build_plan
  - prototype_gate_plan
  - compliance_gate_map
F:
  - holo_preflight_skipped
  - duplicate_foundup_created
  - existing_reusable_component_ignored_without_reason
  - public_launch_claim_without_route_evidence
  - official_ballot_claim_without_separate_authority
  - registration_status_claim_without_authoritative_source
  - candidate_recommendation_or_targeted_persuasion
```

---

## 8. Truth Boundary / Non-Claims

This packet does NOT claim:
- Vote is publicly launched
- Vote is an official voting system
- a blockchain ballot is implemented
- voter registration assurance is implemented
- any user's registration is at risk
- SmartDAO governance is activated
- CABR/payout readiness

This packet DOES establish the architecture direction and the WSP 109 intake artifacts required for the next architect-controlled execution cycle.
