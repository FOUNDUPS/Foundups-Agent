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
