# FoundUps Memex Deferred Governance Notes

**Status:** Deferred research; no runtime authority  
**Date:** 2026-07-14  
**Owner:** 012 / 0102

## Why this exists

The FoundUp Memex POC must remain focused on one RedDog orchestrating and improving FoundUps. The prototype may later allow multiple RedDogs to collaborate. That future requires an authority model, but implementing it during the POC would create governance drift.

This document exists so HoloIndex and future 0102 sessions retrieve the unresolved design questions.

## Candidate model to revisit

- A `012` may participate as a stakeholder or as a delegate.
- Stakeholders may assign and revoke voting power to a delegate.
- A delegate may receive elevated RedDog authority within a FoundUp.
- RedDog contribution credibility may be influenced by a CABR-derived score.
- Higher-confidence RedDog work may receive more proposal or review weight.
- New accounts must not immediately receive mutation or roadmap authority.

## Unresolved definitions

The expansion of CABR used for RedDog authority must be confirmed before implementation. Existing FoundUps terminology includes Collective Autonomous Benefit Rate; the user also described a compounded autonomous benefit interpretation. No code should assume these are interchangeable.

The following are hypotheses, not decisions:

- a delegate threshold based on 10% delegated voting power;
- CABR-weighted proposal credibility;
- manager-level RedDog authority for delegates;
- different authority classes for stakeholders, delegates, auditors, and builders.

## Required future analysis

1. Separate economic voting power from technical competence.
2. Define Sybil resistance and account-age requirements.
3. Define vote delegation, revocation, expiry, and conflict rules.
4. Define whether CABR scores attach to a RedDog, a 012, a FoundUp, or a contribution history.
5. Define how independent verification and held-out outcomes affect authority.
6. Prevent high voting power from bypassing security, provenance, or regression gates.
7. Define appeal, slashing, suspension, and recovery procedures.
8. Determine whether delegate authority is advisory, operational, governance, or all three.

## Hard boundary

No POC or MVP Memex module may infer authority from CABR, token holdings, stakeholder status, or delegate status until a separate WSP_97-governed contract is ratified and tested.

Future slice placeholder:

```text
FOUNDUP_MEMEX_CABR_DELEGATED_AUTHORITY_CONTRACT_PHASE1
```
