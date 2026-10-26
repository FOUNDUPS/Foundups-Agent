# Vote/Ballots - Manifest Draft / Reconciliation Proposal

## Classification
This is an EXISTING_FOUNDUP_UPDATE, not a new FoundUp intake.

WSP 109's current entity decision tree indicates VOTE should be re-evaluated as `entity_type: foundup` because it is consumer-facing, has an existing VOTE token symbol/economics declaration, and has source/test implementation in the monorepo. Current registry classification `skeleton_candidate` predates the merged six-slice PoC implementation and must not be changed without a dedicated reconciliation/test slice.

## Current Truth
| Field | Current |
|---|---|
| foundup_id | `voteballots` |
| module_path | `modules/foundups/voteballots` |
| registry entity_type | `skeleton_candidate` |
| registry implementation_status | `SPECIFIED` |
| registry poc_status | `idea` |
| manifest `_wsp97_implementation_state` | `SPECIFIED_NOT_IMPLEMENTED` |
| internal PoC chain | 6/6 implementation slices merged; 303 tests recorded |
| public entry_url | empty |
| public Vote app | not launched |
| mall catalog | not listed |
| portfolio projection | not listed |
| token symbol | `VOTE` |

## Proposed Post-Reconciliation Registry/Manifest Intent
These are draft target semantics, not changes made by this intake.

| Field | Proposed intent |
|---|---|
| foundup_id | preserve canonical current id unless WSP 57 audit requires change |
| display_name | VOTE / VoteBallots per current naming authority |
| entity_type | re-evaluate `foundup` under WSP 109 |
| module_path | preserve current module path |
| stage | PoC until public PoC launch gate passes; prototype only after prototype gate |
| implementation_status | reflect internal implemented PoC without claiming public launch |
| token_status | preserve current authoritative token state |
| poc_status | reconcile internal implementation vs public-surface semantics explicitly |
| public_surface_status | discoverable until public landing activation passes |
| public_url_or_route | canonical WSP 104 route, not a new parallel route |
| next_slice | `VOTE_PUBLIC_POC_REOPEN_AND_STATUS_RECONCILIATION_PHASE1` or architect-selected equivalent |

## Capability Direction
### Public PoC
- locality/race/candidate surface
- funding/influence evidence
- candidate detail/source trail
- RedDog conversational routing
- capture/scan research entry via reusable capture contract

### Gated Prototype
- deeper candidate record and neutral scorecard
- discovery
- non-binding cryptographic parallel ballot
- registration assurance
- voter-resilience/locality/alert capabilities

### Later Shared Governance
- extract validated preference/mandate/voting-verification primitives for FoundUp SmartDAOs

## No Promotion Claims
This draft does NOT:
- set `entry_url`
- activate a public route
- promote Mall/portfolio listing
- claim an official election ballot
- enable blockchain execution
- activate CABR/payout/governance
- change registry or manifest runtime data

## Required Reconciliation Slice
Before any registry/manifest mutation, architect must retrieve and validate:
1. `VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1`
2. current registry entry
3. current foundup manifest
4. current module source/test inventory
5. WSP 109 entity classification contract
6. WSP 102/104 public surface contracts
7. current catalog/portfolio projections

Then update tests/docs atomically with the chosen status semantics.
