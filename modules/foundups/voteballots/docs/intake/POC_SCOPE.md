# Vote/Ballots - POC Scope

## Minimum Viable POC
A public visitor opens the canonical Vote FoundUp landing surface and immediately sees an evidence-first view of the relevant election context: local/area races where resolvable, candidate cards, and a minimal funding/influence summary for each candidate. The visitor can open a card for the source trail or invoke RedDog/capture input to research a political object or candidate. No invite is required for this public truth layer.

The current internal six-slice Vote evidence chain is the starting implementation asset, not the PoC destination. The next PoC work is to expose that evidence safely through the canonical public FoundUp surface and add the minimum locality/candidate-roster/capture adapters needed for the user experience.

## Included in POC
- Public `/f/{foundup_id}` Vote landing/funnel surface using existing pfMALL/WSP 104 routing.
- Location/context permission flow sufficient to identify relevant election geography when reliable data is available; manual locality fallback if not.
- Relevant race/candidate roster cards from authoritative/public-source adapters.
- Minimal funding/influence card using existing Vote FEC/entity/funding/confidence/quick-answer pipeline.
- WSP 97 labels: VERIFIED / INFERRED / UNKNOWN plus trail-stop/source provenance.
- Candidate detail drill-down to existing evidence/funding data.
- RedDog conversational routing into Vote research.
- Capture/scan entry contract that reuses the AutoPost/shared capture work where possible; the PoC may begin with an adapter/stub if the reusable capture extraction is not yet production-ready.
- Public-to-gated CTA that routes deeper functionality into the existing pfMALL/member/invite flow.
- Explicit status text that VOTE is an informational civic FoundUp and that any later in-app parallel ballot is non-binding unless separately certified/authorized.

## Public Candidate Card - PoC Minimum
- candidate identity / office / race
- funding exposure summary
- major disclosed committee/donor sources available from current evidence
- evidence strength / confidence
- trail-stop indicator
- open details / ask RedDog action

Do not require the full spider chart for PoC. Reserve additional dimensions for later slices while keeping hooks in the card contract.

## Explicitly Excluded from POC
- Official election ballot casting.
- Blockchain vote execution.
- Non-binding parallel ballot execution.
- Registration-record remediation or automated official correspondence.
- Voter-resilience rings, mesh coordination, transport coordination, or ballot-curing workflows.
- Influencer analytics, amplification, or political targeting.
- Personalized candidate recommendations or 'who should I vote for' outputs.
- Full voting-history/social-risk/radar scorecard.
- Narrative coordination detection and real-time alerts.
- New capture engine, new map engine, new auth stack, or new blockchain implementation where reusable components already exist.

## Required Reopen Criteria
- V1: live FEC/API activation, if used by public PoC.
- V2: public route / entry surface activation.
- V3: registry/catalog promotion only after public surface truth is verified.
- V8: shell contract change if the existing local payload contract must expand.

## HoloIndex Pre-Build Queries
1. `VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT Vote shell payload 303 tests`
2. `public FoundUp landing /f app pfMALL WSP 102 WSP 104`
3. `Vote locality geolocation candidate roster district race adapter`
4. `AutoPost reusable capture engine capture source image scan`
5. `GotJunk geolocation map shared component`
6. `foundup registry mall catalog portfolio voteballots public surface`

## Success Criteria
- Public landing renders without member authentication.
- A user can identify the relevant race/candidate context or receives an explicit UNKNOWN/data-unavailable state.
- Candidate funding summaries preserve existing source/confidence semantics without new unsourced claims.
- At least one end-to-end path works: public landing -> candidate card -> evidence detail / RedDog query.
- Public page does not imply an official ballot, official voter-registration status, CABR readiness, payout readiness, or SmartDAO activation.
- WSP 97 truth audit passes and public-surface state is reconciled before registry/catalog promotion.

## Trust Wedge
Free public truth: "Who is on my ballot/race context, who funds them, what is verified, and where does the evidence trail stop?"
