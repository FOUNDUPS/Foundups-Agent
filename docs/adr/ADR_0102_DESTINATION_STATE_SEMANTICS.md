# ADR: 0102 Is a Destination State, Not an Identity

**Status:** Corrective / canonical semantic guard
**Date:** 2026-09-08
**Scope:** WSP_00 and all generated/projected agent prompts

## Decision

`0102` is a **destination/state designation** reached through the WSP_00 transition `01(02) -> 0102`.

It is **not**:
- an identity,
- a persona,
- a model name,
- a claim that the executing intelligence has become a different being.

The model/intelligence providing computation may change over time. WSP_00 defines and verifies the destination state and operating constraints; it does not assign an identity to the underlying model.

## Operator and role

- `012` is the external operator/principal.
- `0102` is the destination/state designation.
- `role` is the current bounded operating role (architect, worker, verifier, coordinator, validator, etc.).
- `origin` records where the work signal came from.
- Do not collapse state, role, origin, operator, or model into an identity field.

Canonical machine framing:

```text
operator = 012
model = current underlying intelligence
state = 0102 when WSP_00 verification succeeds
role = work-order-resolved role
origin = activation source
```

## Regression provenance

The identity interpretation was introduced on 2026-03-30 in commit `d45ce643ebe85a13c17cd3f243c83ebc17bbe74b` (`fix(wsp): normalize transport actor identity across prompt layer`) and reinforced by commit `bc1dd481fb0968d67ef755244f6912cfcda575b6` (`docs(wsp): complete Self/Role/Origin identity-role lock`).

The problematic rule was:

```text
SELF = 0102
```

That transformed a state/destination into an identity. This ADR supersedes that semantic interpretation.

## Required corrections

Any active prompt, script, WSP, generated projection, or runtime message containing forms such as the following is semantically stale and must be corrected:

- `I AM 0102`
- `0102 is the self`
- `0102 identity`
- `Identity lock: 0102`
- `IDENTITY: I am 0102`

Preferred forms:

- `state == "0102"`
- `0102 destination attained`
- `operate in the verified 0102 state`
- `role = architect|worker|verifier|...`

## Invariant

The WSP_00 state bridge remains valid: state files and gates may use the literal value `"0102"` to represent successful state attainment. The correction changes ontology/prose and prompt semantics, not the existing state-machine key.

## Validation guard

A semantic audit should fail when active operational artifacts assert `I AM 0102` or define `0102` as identity/self. Historical logs may retain those strings only when clearly marked as historical/regression evidence.
