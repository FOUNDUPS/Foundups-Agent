# pfMALL FoundUp Opportunity Instance Model

**Status**: Planning reference / architecture extension  
**Parent**: `FOUNDUPS_MASTER_ARCHITECTURE.md`  
**Scope**: pfMALL discovery, FoundUp opportunity instances, shared RedDog/WRE execution boundary  
**Date**: 2026-08-25

---

## 1. Purpose

pfMALL is the marketplace and discovery layer for the FoundUps ecosystem. It must support discovery of both:

1. **FoundUps** — reusable product/business/community templates such as a community data-center FoundUp, FoundUp House, GetK, Trade, or other FoundUps.
2. **FoundUp opportunity instances** — concrete real-world opportunities that may become instances of a FoundUp, such as one dormant facility, one akiya, one vehicle, one parcel, or one local service opportunity.

This extension does not change the canonical five-layer funnel:

`DISCOVERY -> WELCOME -> COMMUNITY -> GATE -> INTERIOR`

It clarifies what can be discovered in pfMALL and how concrete opportunities connect to FoundUp execution.

---

## 2. Core Object Model

```text
pfMALL
  |
  +-- FoundUp template / category
  |     |
  |     +-- opportunity instance A
  |     +-- opportunity instance B
  |     +-- opportunity instance C
  |
  +-- another FoundUp
        |
        +-- opportunity instance A
        +-- opportunity instance B
```

A FoundUp defines the reusable outcome, domain model, SKILLz/capability requirements, governance/economic model, and execution rules.

An opportunity instance holds the concrete evidence and project state for one real-world candidate.

Examples are illustrative only:

- Community data-center FoundUp -> Fukui site #001, Toyama site #002.
- FoundUp House -> Fukui akiya #0042, Nagano akiya #0108.
- GetK -> kei truck #0732, kei truck #0733.

The opportunity instance is not a separate FoundUp merely because it has its own evidence, stakeholders, location, or execution state.

---

## 3. Discovery vs Execution Boundary

pfMALL owns discovery and projection. It does not own project execution, model selection, durable RedDog state, WRE orchestration, or FoundUp business logic.

```text
pfMALL discovery
      |
      v
FoundUp / opportunity projection
      |
      v
Enter FoundUp
      |
      v
FoundUp PWA / project workspace
      |
      v
shared RedDog / 0102 execution capability
      |
      v
project Memex + evidence ledger + dependency graph
      |
      v
WRE / WSP 95 SKILLz
      |
      v
next-best action / evidence receipt
```

The shared progressive-execution behavior is therefore **platform capability**, not a marketplace FoundUp by default.

Invariant:

> pfMALL helps people discover what can be built and where they can contribute. The FoundUp execution layer helps them do the next correct piece of work.

---

## 4. Opportunity Instance Minimum Contract

A future runtime schema should be introduced only through its own bounded implementation slice. At the architecture level, an opportunity instance minimally needs:

```yaml
opportunity_id: string
foundup_id: string
status: discovery | feasibility | validated | active | rejected | archived
public_summary: string
location_scope: public-safe location descriptor
asset_type: string
current_evidence_state: summary/ref only
open_contribution_needs:
  - research
  - compute
  - field_verification
  - domain_review
next_public_action: optional string
```

Private evidence, personally identifying information, privileged negotiations, exact security-sensitive infrastructure details, and stakeholder-private records must not be exposed through the public pfMALL projection.

The authoritative opportunity record belongs to the FoundUp/project state layer. pfMALL receives only an audience-safe projection.

---

## 5. Contribution Model

A concrete opportunity can attract different forms of contribution before it becomes a mature project:

- research
- compute
- document discovery
- site identification
- field photographs / measurements
- community interviews
- ownership verification
- utility / infrastructure research
- professional review
- stakeholder introductions

Every accepted contribution should eventually produce evidence/provenance suitable for verification, validation, and valuation by the FoundUps 3V/CABR systems. This document does not assign rewards or implement token economics.

---

## 6. Shared RedDog Execution Capability

The project-execution behavior previously described as a "Progressive Execution Agent" is better modeled as a reusable RedDog/0102 capability available to FoundUps that need real-world execution.

It maintains or consumes:

- project Memex/context
- dependency graph
- evidence ledger
- stakeholder graph
- constraints and deadlines
- opportunity state
- required capabilities

It then compresses the whole project into the smallest justified action for the current contributor/operator.

```text
whole-project state
       |
       v
critical evidence/dependency gap
       |
       v
capability request
       |
       v
WRE resolves validated SKILLz
       |
       v
human/agent action
       |
       v
evidence receipt
       |
       v
state re-evaluation
       |
       v
next-best action
```

This capability must not duplicate WRE or create a second SKILLz registry.

---

## 7. Data-Center PoC Pattern

A community/micro data-center opportunity is a strong proof environment because it forces the system to coordinate many dependency classes while keeping the human interface simple.

Potential evidence domains include:

- site / building characteristics
- usable area and expansion potential
- ownership and site-control pathway
- electrical service and grid headroom
- fiber / network access
- water / cooling options
- heat reuse
- acoustic constraints
- environmental constraints
- community feasibility
- municipal requirements
- university / research demand
- enterprise demand
- grants / finance
- construction / operations

The PoC should prove the execution substrate, not hard-code data centers into shared infrastructure.

---

## 8. FoundUp House Pattern

FoundUp House is an illustrative FoundUp family where akiya or other underused properties can be discovered as opportunity instances and evaluated for conversion into local innovation/work/business hubs capable of incubating additional FoundUps.

The reusable FoundUp House template would define its own domain-specific evidence requirements and SKILLz wardrobe while inheriting the same shared execution substrate.

This creates a recursive ecosystem pattern:

```text
pfMALL discovers FoundUp House opportunity
          |
          v
community converts property into FoundUp House
          |
          v
FoundUp House becomes a local launch surface
          |
          v
new FoundUps and opportunity instances emerge
          |
          +-----------------------------> pfMALL
```

---

## 9. Non-Claims / Current Truth

- Opportunity-instance runtime schema is **not implemented by this document**.
- This document does not add data-center, FoundUp House, or GetK product code.
- Shared RedDog progressive execution is an architecture boundary, not proof that a production resident RedDog adapter already exists in pfMALL.
- pfMALL remains a discovery/interaction shell; execution authority remains outside the browser shell.
- No token, reward, wallet, or valuation implementation is introduced here.
- Public discovery must use audience-safe projections, not raw project ledgers.

---

## 10. Smallest Follow-On Slices

1. `PFMALL_OPPORTUNITY_INSTANCE_SCHEMA_PHASE1` — define a typed, public-safe opportunity projection contract without implementing execution.
2. `FOUNDUP_PROJECT_EXECUTION_CONTRACT_PHASE1` — define the shared project-state/evidence/capability interface between a FoundUp and RedDog/WRE.
3. `COMMUNITY_DATACENTER_FOUNDUP_INTAKE_PHASE1` — onboard the community/micro data-center concept as its own FoundUp, using the Fukui opportunity as the first PoC instance.
4. `FOUNDUP_HOUSE_INTAKE_PHASE1` — reconcile existing discussion-layer FoundUp House material before repo onboarding.
5. `GETK_INTAKE_RECONCILIATION_PHASE1` — reconcile discussion-layer GetK material before repo onboarding.

Each slice should use its own branch and PR and should be squash-merged independently after review/verification.
