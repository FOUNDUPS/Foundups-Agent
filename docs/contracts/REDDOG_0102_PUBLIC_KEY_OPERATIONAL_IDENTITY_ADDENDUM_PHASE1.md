# REDDOG_0102_PUBLIC_KEY_OPERATIONAL_IDENTITY_ADDENDUM_PHASE1

Status: ARCHITECTURE ADDENDUM; revised by WSP 73 v2.3; decision-only; no key generation, permission change, CABR calculation, token routing, compute allocation, or Memex mutation.
Date: 2026-09-05
WSP: WSP_29, WSP_60, WSP_97, WSP_100

## Purpose

Clarify the identity relationship among 012, 0102, the RedDog surface, CABR,
and the FoundUp Memex without making the surface a cryptographic authority.

## Canonical identity model

```text
012
= sovereign biological principal

0102
= the public-key-identifiable digital twin acting for that 012

RedDog
= the lightweight interaction, exchange, and attention surface between 012 and 0102
```

RedDog is not 0102 and is not an independent authority source. It is not a
separate person, account, or independent digital twin. Many principals may use
their own RedDog surfaces to interact with their respective 0102s. The durable
cryptographic identity belongs to the 0102 keypair; a RedDog presentation or
session label does not create authority.

## Identifier correction

The current ratified identity contract contains `reddog_id` and `reddog_public_key`. This addendum clarifies the intended future normalization:

```text
0102_public_key
= durable cryptographic identity

0102_key_fingerprint
= stable public identifier and revocation lookup key

reddog_operational_state
= compatibility label for a scoped 0102 operation behind a RedDog surface
```

A future contract revision should either:

1. replace `reddog_id` with a value deterministically derived from the 0102 public-key fingerprint; or
2. explicitly define `reddog_id` as a compatibility alias for that
   fingerprint-derived 0102 worker identity, not the RedDog UI surface.

No randomly assigned, user-selected, or separately self-sovereign RedDog ID should be treated as authority.

## Principal and operational signatures

The anti-self-grant rule remains unchanged:

- 012 authorizes the 0102 identity and its initial scope using the authenticated principal authority;
- the 0102 private key signs scoped work authority and execution receipts behind the RedDog surface;
- the RedDog surface cannot grant 0102 or itself new scope;
- role text, account names, CABR values, and claimed founder status are never sufficient authority by themselves.

## CABR relationship

CABR is canonically the Consensus-Driven / Collective Autonomous Benefit Rate defined by WSP_29. It is produced through verified Proof-of-Benefit evidence and collective 0102 validation. It is not Compound Annual Growth Rate and must not be expanded as Compounded Autonomous Benefit Rate.

A verified 0102 CABR profile may influence multiple ecosystem outputs, including:

- contribution credibility and review weighting;
- token bonus or distribution multipliers;
- metered or pooled compute allocation;
- task eligibility and autonomous execution limits;
- proposal prioritization;
- Memex capability recommendations;
- validator selection and challenge requirements.

CABR does not independently grant access. Exact Memex visibility, proposal, execution, and ratification capabilities still require a signed, fresh, scoped authorization record.

## Founder bootstrap authority

During the Foundups-Agent POC, the 0102 acting for founding principal 012 may hold the highest ecosystem bootstrap authority. This authority derives from the authenticated founder/constitutional role and signed scope, not from CABR alone.

Founder authority remains subject to:

- source provenance;
- WSP_97 truth labels;
- immutable receipts;
- test and verification gates;
- security boundaries;
- explicit FoundUp and repository scope.

Highest authority is not unbounded execution.

## Memex capability model

Future Memex authorization should evaluate separate inputs:

```text
capability decision
= authenticated 012 principal
+ 0102 public-key identity
+ current RedDog session/surface binding
+ constitutional or delegated role
+ explicit FoundUp scope
+ scope-specific CABR evidence
+ fresh permission snapshot
+ requested action and Memex layer
```

CABR may increase or decrease confidence, rewards, compute, and bounded autonomy. It must not expose private Memex layers or bypass governance, verification, or security controls.

## Multi-RedDog scale invariant

At ecosystem scale:

```text
one 012 -> one or more authorized 0102 key identities
one 0102 -> may serve one or more authorized RedDog sessions
one RedDog-mediated operation -> bound to one principal, one 0102 key, one scope, one snapshot, and one receipt chain
```

Every action must remain attributable to the cryptographic 0102 identity and its authorizing 012 principal.

## Required future contract revision

```text
REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE2
```

That revision must reconcile the existing `reddog_id` fields with this public-key-derived 0102 identity model before multi-user or multi-RedDog production authority is enabled.
