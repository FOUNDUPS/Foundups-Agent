# Vote/Ballots - Intake Source

## Source Type
external_0102_discussion

## Raw Input Summary
VOTE is an existing FoundUp being expanded from political funding transparency into a staged civic decision and governance test surface. The current discussion adds four requirements: (1) the public PoC is the open `/f/{foundup_id}` landing/funnel surface, (2) research may be initiated by natural conversation or capture/scan input, reusing existing FoundUps components where possible, (3) deeper prototype capabilities are gated through the existing pfMALL/member/invite flow, and (4) a future non-binding cryptographic parallel-ballot plus voter-registration assurance path should test governance and voting-verification primitives before any official-election use.

## Existing FoundUp Identity
- Current module: `modules/foundups/voteballots/`
- Current registry id: `voteballots`
- Current token symbol: `VOTE`
- Classification: EXISTING_FOUNDUP_UPDATE

## WSP 97 Truth Snapshot
- Internal Vote PoC chain is implementation-complete: 6/6 slices merged; 303 tests recorded in the governance closure snapshot.
- Public launch is not complete: `entry_url` remains empty and no public Vote app is active.
- Registry/manifest labels are stale relative to the implemented source/test surface and require a separate reconciliation slice before promotion.
- Vote is present in `modules/foundups/foundup_registry.json` but not in `public/member/mall-catalog.json` or `public/f/portfolio_data.json` as of this intake.

## Existing Reuse Signals
- AutoPost: reusable capture-engine audit already exists; use as capture/scan input precedent rather than rebuilding camera intake.
- GotJunk: existing geolocation/map/PWA and hidden-mode/Liberty Alert integration provide reuse candidates for locality, map, alerts, and gated escalation patterns.
- Liberty Alert: existing alert models, GeoPoint, MeshNetwork, and AlertBroadcaster are reuse candidates for later resilience features.
- pfMALL: existing public `/f/{foundup_id}` landing and `/f/{foundup_id}/app` boundary is canonical; do not create a parallel shell.

## Required HoloIndex Retrieval Queries Before Any Build Slice
Run HoloIndex first. Treat direct code reads as validation/fallback, not replacement.

1. `voteballots Vote PoC FEC entity resolution funding summary confidence quick answer shell integration`
2. `VOTE public PoC landing pfMALL /f foundup_id app gate WSP 102 WSP 104`
3. `AutoPost reusable capture engine camera scan recognition listing capture source`
4. `gotjunk map architecture geolocation Liberty Alert Easter egg mesh broadcaster GeoPoint`
5. `FoundUp duplicate discovery reuse extension WSP 109 registry mall catalog portfolio`
6. `WSP 96 governance voting blockchain WSP 100 SmartDAO WSP 26 tokenization`
7. `voter registration assurance civic evidence suppression resilience ballot verification`
8. `political compliance FEC election communication disclaimer coordination privacy`

## Assumptions
- The public Vote surface remains evidence-first and non-persuasive.
- A future in-app ballot is non-binding preference signaling until a legally/certifiably valid election-voting path exists.
- Registration-assurance features use explicit user consent and official-source adapters; no autonomous submission or official correspondence is authorized by this intake.
- Cryptographic voting reuses existing blockchain/governance abstractions where valid instead of introducing a new chain by default.

## Unresolved Questions
- Which existing capture surface should be the canonical shared component: AutoPost-derived capture engine, GotJunk capture, or a shared extracted interface?
- Which locality/map primitives should be extracted from GotJunk versus consumed through an interface?
- What exact gate/invite/OAuth flow is canonical on current main when the prototype work begins?
- Which current blockchain/governance module is the canonical home for non-binding parallel-ballot proofs?
- What compliance skill or audit lane should gate voter-registration assurance and political-communication features?

## Duplicate Discovery Status
EXISTING_FOUNDUP_UPDATE

## Provenance Note
Prepared from 012/0102 design discussion on 2026-08-26 and reconciled against the current Foundups-Agent repository, WSP 109 intake contract, Vote PoC closure evidence, FoundUp registry, pfMALL public-landing audit, AutoPost reusable-capture audit, GotJunk map architecture, and Liberty Alert integration evidence.

---

## 2026-10-30 Update - Political Claim Verification and Scoring Engine

### Source and requested action
Source type: pasted_prompt + spoken_012. The supplied **Bullshit Meter** specification extends Vote with political speech ingestion, atomic factual-claim extraction, primary-source research, statistical/methodological and funding/incentive audits, transparent 300-850 scoring, a clickable evidence graph, and later video/live overlays. The subsequent spoken instruction explicitly requested updating Vote's Outcome, Solution, Pain, roadmap, and related documents.

The complete [original supplied specification](CLAIM_VERIFICATION_SOURCE_20261030.md) is retained. The [integrated feature design](../POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) is the canonical planning document for architecture, qualifications, data model, UI, rollout, and downstream evaluation.

### Classification and scope
- EXISTING_FOUNDUP_UPDATE under `modules/foundups/voteballots/`; no duplicate Vote repository.
- Documentation/intake/roadmap update only. The new engine, database, ten-speech run, scores, overlays, and deployment are not implemented by this slice.
- Preserve the existing public candidate/race/funding PoC and all later governance phases.
- Permit CV1 internal evaluation alongside public PoC preparation; public/member activation retains its release gates.
- CV1: asynchronous transcripts, ten speeches across 2-5 public figures, CLI/review dashboard and evidence JSON. CV2: methods/funding audits. CV3: caption/video overlays. CV4: streaming ASR/live meter.

### Required qualifications
Unknown/uncheckable evidence is unscored; verdict and confidence are separate. Financial association alone does not prove falsity, and recurrence does not prove intent. Polling thresholds are method-aware review signals. The 300-850 range, color bands, conflict multiplier, recurrence penalty, and sub-500-ms target remain proposals requiring the evaluation specified in the feature design.

### Decisions carried into the build packet
Exact corpus and source access, shared storage/transcript/search/extension owners, scoring equation/weights/coverage/calibration, model/runtime selection, and review/latency budgets remain unresolved implementation decisions. The proposed PostgreSQL/pgvector schema includes Politicians, Transcripts, Extracted_Claims, Primary_Sources, Funding_Entities, and Audit_Logs; no database or migration has been created.

### Retrieval assessment for this documentation slice
Current module README, interface/architecture design, roadmap, eight intake files, implementation exports, shell/FEC code, and May closure evidence were read directly from GitHub. Exact module paths reduce generic governance-voting search noise; no existing `Bullshit Meter` code-search match or open Vote PR was found. Semantic HoloIndex execution and local Windows checkout state were not verified. The older interface and runtime manifest/registry labels remain separate from implementation truth; new features remain explicitly planned. Current-code semantic/reuse validation is still required before a build slice.

### Repository-requirement verification and persistent instruction
The follow-up verification read canonical WSP 109 in full, WSP 95 v2.1, WSP 108, the module onboarding protocol, the actual genesis/diligence/pitch Skillz, and WSP 30 stage definitions. The packet was tightened to make PoC -> Prototype -> MVP explicit within Solution and implementation barriers explicit within Pain. MVP remains unspecified rather than invented. Observed registry/manifest values now populate display name, stage, tier, token-status declaration and historical next-slice fields in the draft.

The registry, Vote module, Mall catalog, video catalog and portfolio were inspected; Vote remains an existing module without an activated public app or a Vote entry in those three catalogs/projections. Direct GitHub retrieval was used. No callable HoloIndex runtime tool was available, and no HoloIndex query, WRE skill execution, bootstrap runtime, genesis validation, or launch validation is claimed. Candidate skills and prototype files do not establish production admission.

012's instruction to repeat this repository-first check in future FoundUp work is recorded in the [shared onboarding reference](../../../docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md), linked from the FoundUps domain README. It is persistent project guidance; no ChatGPT account-memory setting or runtime scheduler was changed.
