# Vote/Ballots FoundUp - Roadmap

**Status**: Public Vote, Oversight and Coalition pages live. Candidate/evidence PoC remains internal.

**Current module version**: 0.6.0  
**Truth authority**: WSP 97 + `VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1.md`

---

## Separate Poly roadmaps — 2026-11-12 documentation reconciliation

| Workstream | Canonical roadmap | Relationship / gate |
| --- | --- | --- |
| Poly Vote | [Own module roadmap](polyvote/ROADMAP.md) | Child module within Vote; verified-office nominations/preferences; no separate FoundUp registration |
| Poly Voice | [Own FoundUp roadmap](../polyvoice/ROADMAP.md) | Separate planned FoundUp; local private meeting records and optional commitment receipts |
| Vote / Voice integration | [Current ownership index](docs/VOTE_VOICE_INTEGRATION.md) | Parent dependencies and consented handoffs only; detailed Poly acceptance stays with each owner |

This is documentation authoring, not a passed implementation gate. Preserve
HPC's active stabilization work and acceptance unchanged; later Vote/Voice/Poly
implementation must use the accepted shared Mall rather than compete with it.
The [source/reconciliation receipt](docs/POLY_RECONCILIATION_20261112.md) records
superseded ownership and public-JSON wording, preserved source history and
retrieval limits. General community-ballot research in Phase 4 is not an
implemented Poly Vote office-verification or anonymity system.

## Current State

### MAGA/Oversight Phase One

The [landing contract](oversight/README.md#phase-one-landing-contract) owns
the four-entry design and the single-site address model. The 2026-11-09 slice
reconciles documentation against the deployed Sites and Mall contracts. The
next authorized implementation can simplify the existing landing after
reviewing this handoff. A working Voice destination is a separate release gate.
Voice stakeholder participation, Mall cards, calling workflows and expanded
funding-disclosure UI are later work. The current staff review, routes and
source-preservation requirements remain part of the landing acceptance criteria.

### Accountability integration and 2028 sequence

The current source provides a human and agent-readable legislative roadmap with
decision owners, templates, congressional outputs and a separate optional state
referral. The connected maps make those gates navigable. The authority map has
five featured 119th Congress committees and selected subcommittees. The
investigation map has three fictional walkthroughs. State routing has worked
New York and Washington examples and a general verification path for other
jurisdictions. Refresh the authority records when a new Congress adopts its
rules. Oversight offers a native-dialer senator lookup with manual state
selection and an optional local suggestion. Vote provides two source-backed
officeholder cards and a separate congressional contact list. The next staff
qualification is a walkthrough from scope memo to recorded disposition using
fictional material. Recheck directory coverage at the congressional transition
and retain the official lookup fallback. See the [acceptance record](docs/RELEASE_ACCOUNTING.md#standalone-oversight-staff-site).
For 2028, expand the fixed funding excerpt set only after defining coverage,
amendment/refund handling and freshness rules. Then qualify live retrieval,
one public race-to-evidence journey and the existing tenant mount. Preserve
independent review and the existing correction and abstention gates before
any claim scores or ballot experiments.

### Current publication and Vote application gates

The [dated release audit](docs/RELEASE_ACCOUNTING.md#2026-11-09-documentation-audit)
records Vote Sites v3 and Oversight Sites v10. Coalition prepares local drafts.
Verified enrollment and editorial tools are future capabilities.
The [release accounting and Launch Pad](docs/RELEASE_ACCOUNTING.md) record
GitHub/PC reconciliation, DNS, HTTPS, browser checks and each capability's gates.

For the candidate/evidence track, reconcile registry labels in Phase 0. The
cycle-validation defect noted in the November 1 checkpoint was fixed in
[PR #2319](https://github.com/FOUNDUPS/Foundups-Agent/pull/2319). Use the Vote
product's Phase 1 to prove one public evidence
journey with authoritative sources, freshness and explicit data gaps. Oversight
reader review and Coalition intake are parallel product decisions with separate
acceptance gates. The published sites and preserved instruction bundles are
presentation and authored content. Tenant activation and runtime qualification
each have their own gates.


### 2026-11-01 bounded RSI fixture checkpoint

**Native cycle-validation follow-up:** the [OpenClaw qualification](../../../docs/operations/RSI_SWARM_DISPATCH.md#native-openclaw-vote-qualification--2026-11-01)
ran three local and two paid author jobs against the existing request validator.
The paid candidate passes25 frozen cases but accepts integer subclasses, contrary
to the original exact-int requirement; the bounded repair returned identical bytes.
No candidate was applied at that checkpoint. The validator then mishandled
falsy and non-integer cycle hints. PR #2319 later shipped the exact-input guard.
Retain the counterexample as a regression case for any future worker trial.

The funding-source indirect-reference repair passes322 module tests and an
independent review. One local worker proposal was rejected before production application;
the coordinator authored the accepted source repair. See tests/TestModLog and
canonical RSI dispatch. This does not open the public surface or complete RSI.

**Aggregate follow-up (11/P2, C2/I3/D3/Impact3):** the next local Qwen proposal
was an unchanged block in the wrong envelope and was rejected. The coordinator
extended the existing provenance helper to aggregate totals. Independent review
then exposed the connected quick-answer bug: it labeled totals using child-source
overall confidence. The consumer now uses the unique total claim and caps answer/
shell metadata; absent/ambiguous/invalid claims remain UNKNOWN. Frozen scorer and
display oracles, fixture corrections and exact results are in tests/TestModLog.
This closes a bounded internal defect, not public activation, native author
admission or a demonstrated learning gain. Further model attempts require a
newly qualified task/model route; repeating this failed configuration is not RSI.

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
- public candidate/evidence application activation
- live public data wiring beyond current safe/mock boundaries
- locality/race/candidate roster UX
- registry/manifest status reconciliation
- Mall/portfolio promotion
- prototype features, including the newly specified political claim-verification / Bullshit Meter track
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
Docs/audit first. Runtime registry/manifest promotion occurs only in its own tested slice. Bounded internal CV1 claim-verification evaluation may be planned and executed alongside Phases 0/1 after its reuse/architecture gate; this does not activate a public scorecard or replace the public PoC.

---

## Phase 1 - Public PoC: Ballot Intelligence Funnel

**Goal**: make the public FoundUp landing immediately useful without requiring member access.

### Primary User Experience
- [x] publish the informational Vote front door and workstream links
- [ ] activate the public candidate/evidence entry and tenant app under WSP 102/104
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

### Political Claim Verification Track - Bullshit Meter (2026-10-30)

**Status**: planned / not implemented. Full requirements and original-source reconciliation: [feature design](docs/POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md).

| Track | Requested rollout phase | Planned deliverable |
|---|---|---|
| CV1 | Asynchronous Transcript Engine | Internal CLI/review dashboard; ten source-backed historical speeches across 2-5 figures; atomic claim extraction; primary-source retrieval; reviewed evidence JSON and experimental score or explicit abstention |
| CV2 | Methodological & Funding Graph Integration | Sampling/statistical audits, method-aware uncertainty, sourced funding relationships, historical contradiction/recurrence, evaluated scoring policy |
| CV3 | Browser Extension & Asynchronous Video Overlay | Caption-aligned evidence tags and clickable sources using existing extension/media components where suitable |
| CV4 | Real-Time Debate & Broadcast Meter | Streaming ASR plus cache/research with independently measured latency, provisional/final states, and review/abstention |

- [ ] CV1: reuse/schema decision, frozen ten-speech corpus, exact quote/offset preservation, claim/exclusion JSON and primary evidence graph.
- [ ] CV1: independent reviewed labels and extraction/retrieval/verdict evaluation, including unknown and historical-context cases.
- [ ] Scoring gate: explicit formula, deduplication, severity/recency policy, coverage, uncertainty, correction history, and calibration before publishing 300-850 scores or color bands.
- [ ] CV2: audit methods and funding without treating financial association as falsehood or recurrence as proof of intent.
- [ ] CV3: validate caption alignment, source freshness, permissions and correction propagation.
- [ ] CV4: benchmark ASR, cache lookup, novel research, review and display separately; a sub-500-ms target is not an end-to-end verified-truth guarantee.
- [ ] Public activation: satisfy public PoC/prototype gates and applicable V5/V6/V8 reopen criteria; V1/V2/V3/V7 apply if live FEC/public/runtime promotion is included.

The public candidate/race/funding PoC remains Phase 1. CV1 is an internal evaluation track; the ten speeches and scores have not yet been produced. Unknown/uncheckable claims must remain unscored. PostgreSQL/pgvector is proposed, subject to current shared-storage/retrieval reuse. Existing phases below retain their scope and sequence.

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

## Voice handoff and qualification gates

[Voice intake issue #2330](https://github.com/FOUNDUPS/Foundups-Agent/issues/2330) owns the proposed separate FoundUp. The [Vote/Voice integration candidate](https://github.com/FOUNDUPS/Foundups-Agent/pull/2337) is a separate specification under review.

| Evidence state | Capability |
| --- | --- |
| Implemented and tested | Vote's [Contact Congress](https://vote.mtrout.com/contact) uses a dated official House and Senate contact snapshot, state/territory and chamber selection, a private in-page list, official source links and explicit native dialer entry. Vote's Node fixtures cover roster validation and queue handling. HPC uses that destination and restores its Mall scroll on browser Back. |
| Implemented outside Voice, civic integration unverified | OpenClaw CLI microphone capture and speech recognition, the communication voice engine, and the separate ElevenLabs/Twilio single-call adapter with offline tests. Their existing receipts cover those components. Civic handset playback, call control and provider behavior require dedicated evidence. |
| Specified | Voice issue discovery, scoped Vote evidence handoff, native dialing first, and explicit consent for optional speech or provider assistance. |
| Missing | A registered Voice tenant and typed entry/return contract, civic speech UI, verified provider call initiation/termination and recovery, recording consent and retention, and abuse and privacy controls for production use. |

- Qualify Voice intake, jurisdiction coverage and an official-source refresh path. Preserve office and role evidence when an office cannot be verified.
- Prove issue → evidence → manual contact in the shared Mall. Establish a versioned handoff with explicit consent, minimal data and a bounded return route.
- Test optional speech recognition independently for microphone consent, denied permission, local failure, and recovery. Preserve review and correction before any external action.
- Before provider calling, verify initiation and hang-up under human control, interruption, retries, failure recovery, and explicit privacy and recording consent. Recording defaults off. Qualify provider rules, abuse limits and retention separately.

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
