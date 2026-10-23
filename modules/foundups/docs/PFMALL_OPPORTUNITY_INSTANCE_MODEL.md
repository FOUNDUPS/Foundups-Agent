# p.fMALL Opportunity Instance Model

**Status**: Planning reference  
**Parent**: `FOUNDUPS_MASTER_ARCHITECTURE.md`  
**Date**: 2026-08-25  
**WSP references**: WSP 97, WSP 104

## Purpose

Extend p.fMALL discovery without changing the canonical five-layer FoundUps funnel.

p.fMALL already discovers FoundUps. This model adds a second discovery object: a concrete **opportunity instance** associated with a FoundUp.

Examples:

- a community data-center FoundUp may contain candidate site instances;
- FoundUp House may contain individual akiya/property instances;
- GetK may contain individual vehicle instances.

These examples are illustrative. This document does not register or implement those FoundUps.

## Core distinction

A **FoundUp** is the reusable venture/product/community system.

An **opportunity instance** is one concrete candidate or project state evaluated under that FoundUp.

```text
p.fMALL
  |
  +-- FoundUp
        |
        +-- opportunity instance A
        +-- opportunity instance B
        +-- opportunity instance C
```

An opportunity instance does not become a separate FoundUp merely because it has its own location, asset, stakeholders, evidence, or execution state.

## Relationship to the canonical funnel

The existing funnel remains unchanged:

```text
DISCOVERY -> WELCOME -> COMMUNITY -> GATE -> INTERIOR
```

Opportunity instances extend **Discovery**. They do not create a sixth lifecycle layer.

A public p.fMALL projection may show that an opportunity exists and what kinds of contribution are needed. Detailed evidence, privileged project state, governance, and execution remain inside the owning FoundUp's governed surfaces.

## Public projection boundary

A future opportunity projection should expose only public-safe fields such as:

```yaml
opportunity_id: string
foundup_id: string
status: discovery | feasibility | validated | active | rejected | archived
public_summary: string
asset_type: string
location_scope: public-safe descriptor
open_contribution_needs:
  - research
  - compute
  - field_verification
  - domain_review
next_public_action: optional string
```

The public projection must not expose raw project ledgers, private stakeholder records, personally identifying information, negotiation details, credentials, or security-sensitive infrastructure information.

The authoritative opportunity record belongs to the FoundUp/project-state layer; p.fMALL receives a bounded projection.

## Contribution model

An opportunity may request contributions before it becomes a mature project, including:

- research;
- compute;
- document discovery;
- site or asset identification;
- photographs and measurements;
- field verification;
- community interviews;
- ownership verification;
- utility/infrastructure research;
- professional review;
- stakeholder introductions.

Accepted work should be able to produce provenance/evidence receipts suitable for later FoundUps verification, validation, and valuation. This document does not define rewards or token economics.

## RedDog boundary

This model does **not** redefine RedDog.

Canonical RedDog identity, conversation, authority, and p.fMALL client behavior remain governed by `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` and the RedDog module contracts.

The relevant existing invariant is that p.fMALL/FoundUp surfaces may act as thin clients for the same RedDog identity/session, while durable cognition and governed execution remain behind authenticated backend boundaries.

Opportunity discovery can therefore become conversational through RedDog without moving execution authority into the browser or creating a second RedDog runtime.

## Shared execution capability

The progressive project-guidance behavior discussed for real-world FoundUps is treated as shared execution capability, not as a separate p.fMALL FoundUp by default.

At architecture level:

```text
opportunity/project state
        |
        v
RedDog / 0102 reasoning surface
        |
        v
OpenClaw / governed work plane
        |
        v
WRE / SKILLz / bounded workers
        |
        v
evidence receipt
        |
        v
project-state update
```

Exact runtime ownership remains governed by the existing RedDog, Digital Twin, OpenClaw, WRE, and FoundUp contracts. This document grants no new execution authority.

## Data-center PoC relevance

A community/micro data-center is a useful proof environment for the opportunity-instance model because one candidate site can require many independent evidence domains, including:

- site/building characteristics;
- usable area and expansion potential;
- ownership and site-control pathway;
- electrical service/grid headroom;
- fiber/network access;
- cooling/water options;
- heat reuse;
- acoustic/environmental constraints;
- community feasibility;
- municipal requirements;
- academic/enterprise demand;
- grants, financing, construction, and operations.

This is a PoC pattern, not a requirement that shared p.fMALL or RedDog infrastructure become data-center-specific.

## Non-claims

- No opportunity-instance runtime schema is implemented here.
- No catalog mutation is performed here.
- No new FoundUp is registered here.
- No RedDog identity or authority contract is changed here.
- No WRE/SKILLz execution path is added here.
- No token/reward/wallet behavior is added here.

## Follow-on slices

Any implementation must use its own WSP 97 research-first branch and PR.

1. `PFMALL_OPPORTUNITY_INSTANCE_SCHEMA_PHASE1` — typed public-safe projection contract.
2. `FOUNDUP_PROJECT_STATE_CONTRACT_PHASE1` — determine whether an existing project/evidence state contract already covers opportunity records before adding one.
3. `COMMUNITY_DATACENTER_FOUNDUP_INTAKE_PHASE1` — research first, then decide whether the community/micro data-center concept is a distinct FoundUp.
4. `FOUNDUP_HOUSE_RECONCILIATION_PHASE1` — reconcile existing discussion/repo evidence before onboarding.
5. `GETK_RECONCILIATION_PHASE1` — reconcile discussion/repo evidence before onboarding.
