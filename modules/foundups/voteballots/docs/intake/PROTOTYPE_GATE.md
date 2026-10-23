# Vote/Ballots - Prototype Gate

## POC -> Prototype Criteria
- [ ] Canonical public Vote landing is reachable and truthfully reports its readiness state.
- [ ] Candidate/race context and funding evidence work end-to-end with authoritative/public-source provenance or explicit UNKNOWN states.
- [ ] Existing Vote 6-slice PoC implementation status is reconciled against stale registry/manifest/README labels.
- [ ] pfMALL/member/invite/OAuth gate is verified from current code and reused; no parallel auth system.
- [ ] HoloIndex reuse audit completed for AutoPost capture, GotJunk map/geolocation, Liberty Alert alert/mesh primitives, and existing blockchain/governance modules.
- [ ] Privacy/security review completed for any user location, identity, registration-status, or cryptographic ballot data.
- [ ] Election/political compliance audit completed before registration assurance, public political communications, fundraising/distribution, or coordinated-action features.
- [ ] WSP 97 truth boundary tests pass for all public claims.

## Prototype Scope Expansion
Prototype work is staged. Do not merge the following into one feature blob.

### Prototype Slice A - Candidate Record + Neutral Scorecard
- voting/legislative history where applicable
- public actions and public communications
- neutral evidence-backed dimensions such as funding exposure, influence/capture risk, governance record, communication risk, constituent/issue alignment selected by the user, and evidence strength
- radar/spider visualization as a summary only; every axis drills into receipts and confidence
- no automated candidate ranking or instruction on how to vote

### Prototype Slice B - Discovery
- channel/voice/content discovery inside pfMALL
- rising/local/issue-specific content surfaces
- RedDog conversational navigation
- explicit user feedback: more/less/useful/not useful
- no political microtargeting or conversion optimization

### Prototype Slice C - Non-Binding Cryptographic Parallel Ballot
Purpose: test voting-verification primitives before SmartDAO/public-election use.

Requirements:
- authenticated/eligible-for-this-experiment participant class determined by current identity architecture
- one-person/one-allowed-signal rules defined for the experiment
- ballot choice separated from public identity wherever architecture permits
- cryptographic receipt/auditability without exposing an individual's selection publicly
- immutable or tamper-evident tally evidence using the canonical existing blockchain/governance abstraction after audit
- explicit UI label: NON-BINDING VOTE SIGNAL / NOT AN OFFICIAL ELECTION BALLOT
- no claim that parallel-ballot totals equal the electorate or predict official results

### Prototype Slice D - Registration Assurance
Purpose: detect when a consenting user's official-source registration record may require attention.

Requirements:
- opt-in only
- official-source adapters only
- minimal personal-data handling
- periodic check cadence controlled by user/policy
- status states such as CURRENT / ATTENTION_REQUIRED / UNKNOWN, defined by adapter evidence
- user-visible source and timestamp
- no silent registration change
- no autonomous official filing, mailing, or submission until a separate compliance-approved workflow exists

### Prototype Slice E - Voter Resilience / Locality
- reuse GotJunk map/geolocation and Liberty Alert patterns where valid
- public friction/evidence visibility may remain open
- active coordination/logistics remain behind the gate
- user-submitted anomalies require verification/moderation states
- mesh/ring capabilities may reuse existing alert/broadcast primitives after security review

## SmartDAO Destination
Once parallel-ballot and support-signal primitives are verified, extract/reuse the generic governance interfaces for FoundUp SmartDAOs under the existing governance/escalation protocols. VOTE remains the civic test FoundUp; it must not become the sole owner of generic governance code.

## Risk Gates
- [ ] Privacy validated
- [ ] Security reviewed
- [ ] Compliance checked for each jurisdiction-sensitive capability
- [ ] Identity/ballot separation threat model reviewed
- [ ] Sybil/double-signal resistance tested
- [ ] Recovery/revocation model defined for credentials without revealing ballot choice
- [ ] Registration assurance source authority validated
- [ ] Shared-component ownership decided before extraction
- [ ] No targeted-persuasion regression
- [ ] No official-election claim without separate certification/legal authority

## Required HoloIndex Queries Before Prototype Planning
1. `Vote voting history candidate scorecard radar evidence confidence`
2. `pfMALL discovery video channel recommendation RedDog feedback`
3. `WSP 96 governance voting blockchain consensus WSP 100 SmartDAO escalation`
4. `blockchain integration voting receipt identity privacy zero knowledge credential`
5. `registration status election adapter privacy identity official source`
6. `GotJunk map Liberty Alert MeshNetwork AlertBroadcaster resilience`
7. `FEC political compliance disclaimers coordination public communication`
