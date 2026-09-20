# Memory Horizon Work-Order Contract

These files are **authored WSP 99 dispatch specifications**, not signed executable WRE work orders. No worker is dispatched merely because a JSON file exists.

## Canonical shape

Each numbered file follows the external `0102_m2m_v1` envelope:
`schema ROLE ORIGIN PRINCIPAL_REF L S M T A R I O F`.

The local `X` object is planning metadata, following the established work-order pack pattern. It records dependency graph, objective, steps, WSP 15 allocation, compute requirements, acceptance and rollback. `X` is not a new WSP 99 runtime field.

## Global invariants

- Self is 0102; role is defined by the ticket.
- Current repository truth must be retrieved before execution.
- Extend the existing `memory_horizon` FoundUp. Do not scaffold a duplicate.
- One writer owns one path scope at a time.
- Dependency-independent tickets may run concurrently only with disjoint write scopes/worktrees.
- No durable secrets in prompts, files, logs, AgentDB or worker environment.
- OpenRouter/model use requires current AI Gateway/runtime-binding evidence.
- No medical diagnosis, concussion classification, treatment advice, discharge decision or return-to-play output.
- No public deployment before independent verification and 0102 public-surface admission.
- Failed or blocked work returns evidence; it does not widen scope.
- Author cannot independently certify its own work.
- Exact acceptance criteria are fixed before authoring.

## Product invariants

- Phase 1 is Sweep 0 + Sweep 1 only.
- Game state and measurement state remain separate.
- A scored event contributes at most one independent retention-delay observation.
- Free recall, cued recall and recognition remain separate.
- Raw event/probe data can reproduce every derived retention result.
- Later cognitive sweeps do not silently enter Phase 1.
- Low-fi presentation is intentional; graphical polish is not a POC gate.

## Public-surface invariant

WSP 104:
- `/f/memory_horizon` = shell-owned landing
- `/f/memory_horizon/app` = tenant product runtime
- `idb_memory_horizon` = tenant data namespace

A tenant worker does not own arbitrary root routes or shell logic.

## Result contract

Every ticket returns a redacted result using `RESULT_TEMPLATE.json`. A result is evidence for the coordinator/verifier; it is not merge/promotion authority.
