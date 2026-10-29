# Vote/Ballots - Solution Definition

## Core Solution
VOTE is an existing FoundUp mode that turns public election and political-finance information into a simple evidence-first civic interface. The public PoC is the open FoundUp landing/funnel surface: locate the user's election context, show the relevant candidate/race cards, expose funding/influence evidence, and allow a user to scan or capture political material so RedDog can resolve the subject and fetch its public history. Deeper capabilities remain gated through the existing pfMALL/member path and mature through staged prototype slices into discovery, resilience/alerts, non-binding cryptographic preference voting, registration assurance, and eventually reusable FoundUp SmartDAO governance primitives.

## Key Capabilities
1. **Public ballot intelligence** - locality/context resolution, candidate/race cards, funding and influence summaries, evidence provenance, trail-stop markers.
2. **Capture-to-research** - reuse the ecosystem's capture/scan patterns so a user can photograph or capture a political object/ad and invoke the same evidence pipeline rather than creating a Vote-specific camera stack.
3. **Deep candidate record** - voting history, public actions, public communications, neutral evidence-backed scorecard dimensions, and confidence drill-down.
4. **Discovery** - surface useful/rising channels and civic content inside the existing pfMALL viewing shell based on explicit user interactions and interests, without political microtargeting.
5. **Resilience** - later gated locality/map/alert/evidence features reuse GotJunk/Liberty Alert patterns where architecture permits.
6. **Parallel ballot** - later gated, non-binding preference ballot with cryptographic auditability; explicitly not an official election ballot unless a separate certification/legal gate is satisfied.
7. **Registration assurance** - later gated, consented checks against official-source adapters with user-visible status and remediation prompts; no silent record changes or autonomous official submissions in the initial prototype.
8. **SmartDAO governance reuse** - voting-verification, mandate, and support-signal primitives migrate into shared FoundUps governance infrastructure rather than remaining Vote-only logic.
9. **Political claim verification / Bullshit Meter** - planned source-grounded speech verification, method/conflict audits, transparent experimental scoring, and later video/live evidence overlays.

## Political Claim Verification and Scoring - Planned
The **Bullshit Meter** extends the candidate evidence experience with four stages: **CV1** asynchronous transcript/claim verification and an internal CLI/review dashboard; **CV2** methodology/funding graph and historical consistency audits; **CV3** caption/video overlays; **CV4** streaming ASR and a live meter with explicit pending/unknown states.

The pipeline retains exact source words, extracts atomic checkable claims, routes research to the relevant primary institution/document, audits methods and conflicts, and produces a clickable/exportable JSON evidence tree. Factual verdict, evidence confidence, context, funding conflicts, and intent remain separate. The proposed 300-850 scale is experimental until its equation, weights, coverage, and calibration pass review.

The first evaluation is ten historical speeches across 2-5 public figures. PostgreSQL/pgvector and the six requested entity tables are candidate architecture choices subject to existing storage/retrieval reuse. No new repository or database is created by this intake. See the [canonical feature design](../POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) for the full pipeline, data model, source qualifications, UI, and acceptance criteria.

## Public PoC Flow
1. User enters the public VOTE FoundUp landing surface.
2. Local/context resolver determines the election scope using the minimum data required and user permission where applicable.
3. The page renders the relevant races/candidate cards.
4. Each card shows a minimal evidence-backed funding/influence summary and WSP 97 truth state.
5. User can open a candidate for receipts/deeper evidence.
6. User can invoke conversational research or capture/scan input; RedDog routes the signal into VOTE research.
7. Attempting to enter deeper prototype capabilities routes through the existing pfMALL/member/invite gate.

## Reuse-First Architecture
Before each implementation slice, run HoloIndex with the intake retrieval queries and classify every capability as:
- REUSE_AS_IS
- EXTEND_EXISTING
- EXTRACT_SHARED_COMPONENT
- NEW_VOTE_SPECIFIC

Priority reuse targets already evidenced in the repository:
- existing Vote FEC/entity/funding/confidence/quick-answer/shell chain
- pfMALL `/f/{foundup_id}` public landing and `/app` boundary
- AutoPost capture-controller/reusable capture-engine work
- GotJunk map/geolocation/PWA patterns
- Liberty Alert GeoPoint/Alert/MeshNetwork/AlertBroadcaster patterns
- existing blockchain/governance/tokenization protocols and modules

## Differentiation
VOTE does not begin by asking a voter to trust a recommendation. It begins by showing the evidence boundary. The same FoundUp then lets a participant move voluntarily from public research into deeper authenticated participation, while the underlying verification and governance primitives are built to be reused by FoundUp SmartDAOs.

## Technical Approach
- Preserve the existing Vote PoC chain as the structured evidence core.
- Add the public UI as the next explicit reopen slice under the existing V2 public-route criterion.
- Build locality/candidate-card adapters around existing shell contracts rather than altering the core funding evidence semantics.
- Consume shared capture/map/alert components through explicit contracts; extract shared components only when two or more real consumers justify extraction.
- Keep the cryptographic parallel ballot behind the prototype gate and connect it to existing governance/blockchain abstractions after audit.
- Keep registration assurance jurisdiction-adapter based, consented, and compliance-gated.
- Use Hermes/OpenClaw/AI Overseer/WRE/HoloIndex according to current codebase authority; do not hard-code alternate orchestration ownership.

- Permit bounded internal CV1 evaluation alongside public PoC preparation; public claim-score and overlay activation remain subject to the existing prototype gate.
- Reuse existing transcript/ASR, YouTube indexing, source retrieval, provenance, extension/media and WRE components after current-code discovery. Funding-confidence labels do not already implement general factual verification.
