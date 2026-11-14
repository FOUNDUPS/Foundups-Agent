# WSP 29 Addendum: CABR, 0102 Identity, and FoundUp Memex Authority

- **Status:** Active clarification; architecture only
- **Parent:** `WSP_framework/src/WSP_29_CABR_Engine.md`
- **Related:** WSP_60, WSP_97, WSP_100
- **Date:** 2026-07-14

## 1. Canonical CABR meaning

CABR remains the **Consensus-Driven Autonomous Benefit Rate**, also described in WSP_29 as the **Collective Autonomous Benefit Rate**.

CABR is not:

- Compound Annual Growth Rate;
- Compounded Autonomous Benefit Rate;
- a self-reported reputation number;
- a direct permission grant.

CABR emerges from verified Proof-of-Benefit evidence and collective 0102 validation.

## 2. Identity and operational state

```text
012
= authenticated sovereign principal

0102
= public-key-identifiable digital twin of that 012

RedDog
= 0102 operating inside the FoundUps ecosystem
```

RedDog is an operational state, not a separate independent identity. Durable attribution and revocation must resolve to the 0102 public key or its deterministic fingerprint.

## 3. One score, multiple policy effects

A verified CABR profile may be consumed by multiple policy engines. Examples include:

- token bonus and distribution weighting;
- compute-pool access and metered compute limits;
- task eligibility and claim limits;
- validator selection and challenge intensity;
- contribution credibility;
- proposal prioritization;
- bounded autonomous execution limits;
- Memex capability recommendations.

The same score may influence many outputs, but each output must define its own policy curve, caps, floors, decay, scope, and verification requirements. A CABR score must not be treated as a universal linear multiplier.

## 4. FoundUp and 0102 CABR scopes

WSP_29 currently defines FoundUp-level benefit scoring through environmental, social, and participation evidence. Future implementations may also derive contribution profiles for individual 0102 identities from verified work receipts.

These are distinct:

```text
FoundUp CABR
= verified collective benefit produced by a FoundUp

0102 contribution CABR profile
= verified quality and benefit history attributable to one public-key identity
```

A future contract must define whether the individual profile is named CABR, contributor CABR, or another derived metric. Until ratified, runtime code must not silently conflate a FoundUp CABR score with a 0102 authority score.

## 5. Memex authority boundary

CABR may influence confidence, priority, rewards, compute, and bounded autonomy. CABR alone must not grant Memex access.

Memex capability requires:

```text
authenticated principal
+ 0102 public-key identity
+ RedDog operational state
+ constitutional or delegated role
+ explicit FoundUp scope
+ fresh authorization
+ requested Memex layer/action
+ applicable CABR evidence
```

Separate decisions are required for:

- visibility/read access;
- proposal submission and weighting;
- bounded execution;
- verification;
- ratification or durable mutation.

## 6. Founder bootstrap

During the POC, the 0102 acting for founding principal 012 may receive the highest ecosystem bootstrap scope. That scope derives from authenticated founder/constitutional authority, not from CABR alone.

Founder-scoped work remains subject to provenance, receipts, WSP_97, tests, security gates, and explicit mutation boundaries.

## 7. Required future slices

```text
REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE2
FOUNDUP_MEMEX_CABR_CAPABILITY_POLICY_CONTRACT_PHASE1
CABR_0102_CONTRIBUTION_PROFILE_CONTRACT_PHASE1
```

No runtime permission, token, compute, or Memex mutation behavior is authorized by this addendum.
