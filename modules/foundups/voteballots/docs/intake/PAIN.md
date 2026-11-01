# Vote/Ballots - Pain Definition

## Primary Pain Point
A voter must currently reconstruct civic truth across fragmented systems: candidate records, campaign-finance filings, attack-ad sponsors, public statements and their factual accuracy, election administration, registration status, and platform-driven political content. The information exists in pieces, but the user has no single evidence-first interface that shows what is verified, what is inferred, what remains unknown, and what action requires authenticated participation.

## Pain Areas

### 1. Funding opacity
Attack ads and political messaging often surface the allegation before the funding network. PAC, Super PAC, committee, donor, and nonprofit relationships can require multi-hop research that ordinary voters rarely perform in the moment.

### 2. Fragmented candidate context
Candidate finance, legislative/voting history, public actions, public communications, and local impact are separated across different sources and formats. A voter has to assemble the picture manually.

### 3. Platform information asymmetry
Large platforms observe aggregate engagement and narrative movement at scales unavailable to an individual voter. VOTE should counter this asymmetry by exposing evidence and provenance, not by creating another targeted-persuasion system.

### 4. Registration and access uncertainty
A voter may not know that an official registration/access record requires attention until close to an election. The product opportunity is a consented assurance layer that checks official-source status periodically and surfaces a clear user-visible warning when attention is required.

### 5. No safe proving ground for cryptographic civic signaling
There is a large gap between ordinary opinion polling and certified public-election voting. FoundUps can test auditable, privacy-preserving preference signaling first as a clearly non-binding parallel ballot, then reuse validated primitives for FoundUp SmartDAO governance.

### 6. Duplicate infrastructure risk
The ecosystem already contains Vote funding logic, pfMALL routes, AutoPost capture research, GotJunk map/geolocation, Liberty Alert mesh/alert primitives, and blockchain/governance work. Building new Vote-specific versions without retrieval/audit would create duplicated infrastructure and violate the reuse-first FoundUps model.

### 7. Claims travel faster than their evidence
A listener needs to move from a specific political statement to the relevant primary evidence without losing the quote, date, denominator, jurisdiction, or context. A verdict alone does not explain whether the cited study was applicable, the funding was disclosed, the sources were independent, or the assessment can be corrected.

The proposed Bullshit Meter also addresses the verifier's own failure modes: selective corpus choice, opaque scoring, repeated copies of one source, confident interpretation of uncertain transcripts, and confusion between an unsupported claim and a false claim. The product need is an inspectable evidence and correction path, not automatic certainty.

## Obstacles to Implementing the Solution
The adoption pain above remains. The Outcome -> Solution -> Pain framing also requires the barriers between the proposed solution and its outcome:

- **Data and access**: live FEC integration is unfinished; transcripts, datasets and methodology documents need source-specific access, versions and licensing decisions.
- **Verification quality**: transcript ambiguity, temporal/context mismatch, incomplete funding trails, correlated sources and uncalibrated scores must be handled before reliable public assessments.
- **Reuse and integration**: storage, transcript/ASR, search, extension/media and review/correction owners require current-code discovery. Candidate skill names do not establish a working executor.
- **Product readiness**: public Vote activation, manifest/registry label reconciliation and verification of the current pfMALL gate remain open dependencies.
- **Evaluation and operation**: the ten-speech corpus, independent review, score coverage/calibration, corrections and separate ASR/research latency measurements have not been completed.
- **MVP definition**: audience, minimum supported release, acceptance criteria and operating ownership remain unspecified.

These are implementation constraints, not new user-research findings. See [Solution stages](SOLUTION.md) and [the feature evaluation plan](../POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md).

## Pain Severity
- Frequency: recurring during election cycles; continuous for political-media discovery and funding transparency
- Impact: high when evidence, eligibility status, or access conditions are unclear
- Alternatives: fragmented; users can research manually but must cross many public/private sources and interfaces

## Target User
- Public visitor seeking fast candidate/funding truth
- Listener checking factual claims in political speeches, debates, ads, or public posts
- Voter seeking deeper evidence and official-source status assurance
- Authenticated participant testing non-binding preference signaling
- Later FoundUp SmartDAO participant using shared governance-verification primitives

## Pain Evidence
### 2026-10-30 feature intake evidence
012 supplied the [Political Claim Verification and Scoring Engine specification](CLAIM_VERIFICATION_SOURCE_20261030.md) and requested integration into Vote's Outcome, Solution, Pain, and roadmap. This is a product requirement and hypothesis, not evidence from completed user research or a ten-speech evaluation. The [integrated design](../POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) records methodology sources and the necessary scoring qualifications.

### Repository evidence
- Vote PoC funding/evidence chain: implementation-complete 6/6 slices, but not publicly launched.
- FoundUp registry lists `voteballots`, while public Mall catalog/portfolio projection do not currently list it.
- pfMALL already has a public `/f/{foundup_id}` landing contract; Vote has not activated it.
- AutoPost reusable-capture audit and GotJunk/Liberty Alert artifacts prove relevant capture, map, geolocation, alert, and gated-mode patterns already exist.

### Current public-policy context (neutral factual framing)
- A May 12, 2026 U.S. Department of Justice Office of Legal Counsel opinion concluded federal law authorizes the Attorney General to compel states to produce statewide voter-registration lists and permits sharing with DHS for cross-checking: https://www.justice.gov/olc/media/1440346/dl
- DOJ has filed multiple lawsuits seeking statewide voter-registration rolls, including a September 25, 2025 announcement covering six states: https://www.justice.gov/opa/pr/justice-department-sues-six-states-failure-provide-voter-registration-rolls
- On August 24, 2026, the Supreme Court issued an order in Trump v. California concerning challenges to an executive order affecting federal-election administration. The order addressed the litigation posture/standing and did not itself finally adjudicate the legality of every underlying voting restriction: https://www.supremecourt.gov/opinions/25pdf/26a124_hgci.pdf

These sources justify treating registration/access assurance as a current resilience concern. They do not by themselves prove that any specific voter will be removed, challenged, or denied a ballot.

## WSP 97 Boundary
VOTE must not convert political concern into unsupported certainty. Suppression, foreign-funding, coordination, registration-risk, or access-risk claims must remain VERIFIED / INFERRED / UNKNOWN according to source quality and scope.
