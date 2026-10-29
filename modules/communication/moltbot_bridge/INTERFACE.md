## Denied WSP preflight

`OpenClawDAE.process()` delegates to `openclaw_process_loop.process_message()`.
If `_wsp_preflight(intent)` returns false, emit `wsp_preflight` with result
`blocked` and return `[SECURITY BLOCK] Execution prevented by WSP preflight: ...`.
Preserve the original intent category/domain. Do not resolve permissions, build
or execute a plan, invoke conversation fallback, or validate/store a result.
This covers actual planner rejection of unauthorized COMMAND/SYSTEM and SCHEDULE
without WRE. An authorized COMMAND without WRE retains its existing advisory
path. Earlier continuity, classification, reporting and skill-safety work is not
rolled back; this is not a claim of zero effects before preflight.

**OpenClaw bridge interface directory.**

The linked pages retain the complete contracts and their dated qualification
boundaries. This split changes navigation only, not API semantics or status.
Existing section headings remain below so previously published section links
continue to resolve. Follow each contract link for its complete text.

- [Grant Authority](docs/interfaces/GRANT_AUTHORITY.md)
- [Effect And Process Lifecycle](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md)
- [Repository And Conversation](docs/interfaces/REPOSITORY_AND_CONVERSATION.md)
- [Public Api](docs/interfaces/PUBLIC_API.md)
- [Auth And Operations](docs/interfaces/AUTH_AND_OPERATIONS.md)

## Installed HIGH source integration — 2026-10-23

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-001).

## Selected-clip adapter receipts — 2026-10-22

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-002).

## Installed HIGH service connection — 2026-10-20

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-003).

## Non-initial installed metadata checkpoint — 2026-10-20

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-004).

## Protected consensus nonce supply — 2026-10-20

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-005).

### Historical nonce-only import/composition status — 2026-10-20

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-006).

## Exact parent-consent connection — 2026-10-19

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-007).

## Issuer-only root LOAD — 2026-10-15

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-008).

## Callable LOW grant service — 2026-10-15

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-009).

## Grant bootstrap binding and LOW RPC — 2026-10-15

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-010).

## Initial handshake configuration — 2026-10-15

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-011).

## Initial runtime manifest enrollment — 2026-10-15

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-012).

## Protected initial writer authority — 2026-10-14

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-013).

## Initial high-water bootstrap v2 — 2026-10-14

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-014).

## Initial generation anchor bootstrap — 2026-10-14

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-015).

## Deferred proposal policy activation (implementation checkpoint)

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-016).

## Current-generation Memex consumption

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-017).

## Retained proposal verification inputs

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-018).

## Current-generation model consumption

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-019).

## Protected model verification inputs (owner v8)

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-020).

## Resident fresh peer use — 2026-10-07

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-021).

## Peer healthcheck prerequisites — 2026-10-07

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-022).

## Principal use-time generation binding — 2026-10-07

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-023).

## Resident final-decision effect join — 2026-10-07

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-024).

## Single-effect approval to grant — 2026-10-07 reviewed candidate

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-025).

## Outer consensus binding at grant signing — 2026-10-07 candidate

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-026).

## Reviewer runtime artifact adapter — 2026-10-07

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-027).

## Effect issuer grant handoff — merged PR2087, 2026-10-07

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-028).

## Provider issuance handoff — 2026-10-06 (historical PR2084)

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-029).

## Leased current-generation binding — 2026-10-06

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-030).

## Deferred startup dependencies (unmerged integration, 2026-10-06)

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-031).

## Exact permission evidence type — 2026-10-05

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-032).

## Explicit local credential provider — 2026-10-05

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-033).

## Bootstrap grant-admission handoff — 2026-10-05

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-034).

## Authenticated effect consent — 2026-10-04

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-035).

## Supplied effect-sovereign evidence API — 2026-10-04

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-036).

## Current-generation review-set API — 2026-10-04

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-037).

## Bounded effect-review quorum API — 2026-10-04

[Read this contract](docs/interfaces/GRANT_AUTHORITY.md#contract-038).

## Single-effect proof handoff design — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-039).

### Conditional effect-review verification API — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-040).

### Connected current reviewer verification API — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-041).

### Authenticated effect-authority qualification — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-042).

#### Reviewer-key designation contract — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-043).

### Pure effect-context correlation API — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-044).

### Inert effect-approval context API — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-045).

### Decision and evidence

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-046).

### Digest and carrier contract

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-047).

### Existing ownership and lifecycle

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-048).

### Layer gates and acceptance

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-049).

## Effect-lease consensus qualification — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-050).

## Canonical unsigned effect request preparation

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-051).

## Effect-lease admission map — 2026-10-01

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-052).

## Process visibility qualification boundary — 2026-09-27

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-053).

## Connected socket ownership observation — 2026-09-27

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-054).

## Socket characterization boundary — 2026-09-27

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-055).

## External supervision source contract — 2026-09-27

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-056).

### Three roles and the current source constraint

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-057).

### Source and ownership

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-058).

### Authenticated handoff and canonical consumption (specified, not wired)

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-059).

### One-attempt lifetime

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-060).

### Socket ownership prerequisite — source defect, not a live incident

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-061).

## Healthcheck requester selection — 2026-09-27

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-062).

### Resident handoff ownership (specified, not wired)

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-063).

## Lifecycle default-dependency requirement — 2026-09-27

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-064).

# OpenClaw Bridge Interface

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-065).

## Governed use-time supplier admission

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-066).

## YouTube scheduling command repair (2026-09-22)

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-067).

## Public RedDog Lick PoC

[Read this contract](docs/interfaces/EFFECT_AND_PROCESS_LIFECYCLE.md#contract-068).

## HoloIndex runtime interface

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-069).

## Receipt-bound artifact generation models

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-070).

## RedDog advisory bridge support

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-071).

## RedDog architect FIX promotion HoloIndex proof

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-072).

## Governed repository-state intake

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-073).

## Exact-Git grant-authority effect admission

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-074).

## Principal Memex live resident source

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-075).

## Exact-request signer admission

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-076).

## Authenticated RedDog conversation scope

[Read this contract](docs/interfaces/REPOSITORY_AND_CONVERSATION.md#contract-077).

## Public API

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-078).

### Architect proposal validity and execution readiness

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-079).

### Verified-outcome authority, signing and memory

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-080).

### Resident queue exact-SHA commit stage

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-081).

### Independent assurance capacity admission

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-082).

### Generic provider-call evidence

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-083).

### FoundUpJob intake and create_foundup lineage

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-084).

### Durable Resident Architect Cycle

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-085).

### Canonical RedDog execution-valve readiness

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-086).

### RedDog HoloIndex Query Adapter

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-087).

### FusionAdapter (advisory Fusion worker-panel, CONTRACT-ONLY)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-088).

#### WSP_97 Truth Boundary Checklist (HERMES_FUSION_ADAPTER_CONTRACT_PHASE1)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-089).

### Fusion Redaction Gate (CONTRACT-ONLY precondition; does NOT enable live modes)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-090).

#### WSP_97 Truth Boundary Checklist (HERMES_FUSION_REDACTION_GATE_PHASE1)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-091).

### Fusion ALIAS live path (VALVE-GATED OFF by default; first live OpenRouter integration)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-092).

#### WSP_97 Truth Boundary Checklist (HERMES_FUSION_ALIAS_MODE_PHASE2)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-093).

### WebhookReceiver

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-094).

### Message Format (Inbound from OpenClaw)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-095).

### Response Format (Outbound to OpenClaw)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-096).

### Standalone Action CLI (Direct Agent Invocation)

[Read this contract](docs/interfaces/PUBLIC_API.md#contract-097).

## Environment Variables

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-098).

## Auth Headers

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-099).

### OpenClaw DAE and ExecutionBundle

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-100).

### Intent Categories

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-101).

### Generic DAE Runtime Control

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-102).

### OpenClaw Supervisor Contract

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-103).

### PQN Runtime Control

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-104).

### PQN Theory-Archive Simulation Control

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-105).

### FOUNDUP Route Contract (FAM Adapter)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-106).

#### Catalog Commands (p.fMALL Integration)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-107).

#### Launch Commands

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-108).

### Autonomy Tiers (Graduated)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-109).

### WSP 73 Partner-Principal-Associate

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-110).

### Security

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-111).

### Skill Safety Environment

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-112).

### Rate Limiting (Webhook)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-113).

### SOURCE Tier Permission Check

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-114).

### COMMAND Graceful Degradation

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-115).

## WSP Compliance

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-116).

## WSP 97 Internal Module Boundaries

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-117).

## Runtime Supervision Commands

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-118).

## Skill Evolution Loop

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-119).

### Phase 1: Report Surface (Read-Only)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-120).

### Phase 2: Mutation Surface (Bounded, Gated)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-121).

### Supervisor Integration

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-122).

### RedDog Governed Work-Order Policy Gate (no execution)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-123).

### RedDog Signed Receipt Chain (verification only)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-124).

### RedDog OpenClaw Live Enqueue (valve-gated queue-write seam)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-125).

### RedDog Work-Order Receipt (Hermes-compatible audit trail, no execution)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-126).

### RedDog Work-Order Runtime Invocation Dry-Run (no execution)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-127).

### RedDog WRE Executor Dry-Run Planner (no mutation)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-128).

### RedDog WRE Worktree Create (worktree only, no task execution)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-129).

### RedDog WRE Worktree Operational Spine (worktree-create only)

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-130).

### RedDog Recipient Transaction Preflight

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-131).

### RedDog Correspondence Sender Boundary

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-132).

### Moshpit projection layer

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-133).

### RedDog Correspondence Continuity State

[Read this contract](docs/interfaces/AUTH_AND_OPERATIONS.md#contract-134).
