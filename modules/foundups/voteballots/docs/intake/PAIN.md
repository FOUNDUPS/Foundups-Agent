# Vote/Ballots - Pain Definition

## Primary Pain Point
A voter must currently reconstruct civic truth across fragmented systems: candidate records, campaign-finance filings, attack-ad sponsors, public statements, election administration, registration status, and platform-driven political content. The information exists in pieces, but the user has no single evidence-first interface that shows what is verified, what is inferred, what remains unknown, and what action requires authenticated participation.

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

## Pain Severity
- Frequency: recurring during election cycles; continuous for political-media discovery and funding transparency
- Impact: high when evidence, eligibility status, or access conditions are unclear
- Alternatives: fragmented; users can research manually but must cross many public/private sources and interfaces

## Target User
- Public visitor seeking fast candidate/funding truth
- Voter seeking deeper evidence and official-source status assurance
- Authenticated participant testing non-binding preference signaling
- Later FoundUp SmartDAO participant using shared governance-verification primitives

## Pain Evidence
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
