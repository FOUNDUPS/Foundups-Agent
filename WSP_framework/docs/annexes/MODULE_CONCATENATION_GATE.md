# MODULE_CONCATENATION_GATE (Derived Operational Annex)

- **Type**: Non-canonical operational reference
- **Canonical Source**: `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` (Section 1.4)
- **Last Synced**: 2026-07-17
- **Edit Rule**: Update canonical WSP 97 first when policy changes; keep implementation examples evidence-backed
- **Scope**: Cross-module integration decisions for FoundUps/OpenClaw system growth

## Purpose

- Define how new modules concatenate into the FoundUps/OpenClaw system without creating god modules, parallel control planes, or fragmented memory.
- Canonicalize the integration rule: internal modules concatenate through stable contracts, not through one giant API and not through ad hoc wiring.

## Decision

- External boundaries may use APIs, webhooks, MCP, or CLIs.
- Internal boundaries should prefer module-local adapters plus shared system contracts.
- New modules must integrate into an existing execution plane unless a full WSP 97 review proves a new plane is required.

## Core Rule

```text
New module
-> classify plane
-> bind to shared contracts
-> prove continuity/state/execution fit
-> smoke test real concatenation
-> only then promote to normal runtime
```

## Shared Contracts

### 1. Launch Contract

- Responsibility: startup environment, venv correctness, broker lifecycle, crash containment.
- Typical surfaces:
  - `main.py`
  - `modules/infrastructure/dae_daemon/src/dae_launch_broker.py`
  - `modules/infrastructure/dae_daemon/src/dae_registry.py`
- Example: import-time crash loops are a launch-plane problem and should be contained there before supervision retries.

### 2. Ingress Contract

- Responsibility: normalize external requests into canonical intent/context.
- Typical surfaces:
  - CLI entry
  - webhook ingress
  - OpenClaw route normalization
- Rule: new modules should enter through an owned adapter, not by expanding random branch logic across the system.

### 3. Continuity Contract

- Responsibility: preserve lineage across runtime surfaces.
- Canonical surface:
  - `modules/communication/moltbot_bridge/src/continuity_context.py`
- Rule: work crossing surfaces must create or inherit continuity deterministically.

### 4. State Contract

- Responsibility: durable system memory for cross-surface coordination.
- Canonical surface:
  - `modules/infrastructure/database/src/agent_db.py`
- Valid durable writes:
  - `agents_breadcrumbs`
  - `agents_autonomous_tasks`
  - `agents_coordination_events`
- Rule: if a module affects autonomous behavior, it must write to one of these instead of inventing local hidden state.

### 5. Execution Contract

- Responsibility: runnable skill or adapter execution path.
- Canonical surfaces:
  - `modules/infrastructure/wre_core/skillz/wre_skills_discovery.py`
  - `modules/infrastructure/wre_core/skillz/wre_skills_loader.py`
- Rule:
  - repeatable verbs belong in module-local `skillz/`
  - non-repeatable or platform-owned logic stays in the owning adapter/module

### 6. Supervision Contract

- Responsibility: health, retries, circuit breaking, idle follow-up, autonomous loop safety.
- Canonical surfaces:
  - `modules/communication/moltbot_bridge/src/openclaw_supervisor.py`
  - `modules/infrastructure/supervisor/src/supervisor_24x7.py`
  - `modules/infrastructure/dae_daemon/src/dae_launch_broker.py`
- Rule: modules that run continuously or autonomously must define which supervisor/broker boundary owns their failure mode.

## Module Type Classification

| Module Type | Primary Owner | Concatenation Pattern |
|---|---|---|
| Library/helper | owning module | local import only; no new runtime contract |
| Adapter/integration | owning platform/domain module | ingress adapter + continuity + breadcrumbs |
| DAE/runtime service | daemon/broker + owner module | launch contract + supervision contract + continuity |
| WRE skill provider | owner module + WRE | module-local `skillz/` + loader/discovery hygiene |
| Monitor/research producer | idle/self-research + owner module | writes autonomous tasks/breadcrumbs, not direct execution coupling |

## Required Preflight Questions

- What execution plane does this module belong to?
- What is the ingress?
- What continuity does it create or inherit?
- What durable records does it write?
- Is it an adapter, a daemon, a skill provider, or a monitor?
- What failure mode owns it: broker, supervisor, idle, or local caller?
- What smoke test proves real concatenation?

## WSP 97-Lite Gate

- Use this gate whenever a slice crosses module boundaries.
- Do not run the entire extended WSP 97 analysis when the canonical operator loop classifies the work as a bounded, existing-plane integration.

Pass conditions:

- no new memory authority
- no new scheduler authority
- no duplicate execution plane
- continuity path is explicit
- breadcrumb/task/event path is explicit
- failure ownership is explicit

Escalate to full architecture review under WSP 97 if any of these are true:

- new control plane
- new memory source of truth
- new scheduler/source of truth
- human gate removal
- external dependency that changes runtime authority

## Anti-God-Module Rules

- Do not dump new domain logic into `modules/communication/moltbot_bridge/src/openclaw_execution_routes.py` unless it is true cross-domain routing.
- Do not dump new orchestration logic into `modules/communication/moltbot_bridge/src/openclaw_supervisor.py` unless it is true cross-surface supervision.
- Put surface-specific wiring in the owning module.
- Put shared envelopes in shared infrastructure.
- Put repeatable actions in `skillz/`, not in hand-built branches.

## Integration Acceptance

- A real caller can enter the module through its proper ingress.
- The work has continuity or is explicitly local-only.
- Durable state is queryable through the canonical system surfaces.
- The module fails closed or is properly supervised.
- A narrow production-style smoke test proves the concatenation.

## Architectural Stance

- FoundUps does not scale by adding more direct couplings.
- It scales by adding more modules that bind to the same contracts.
- This is how the system stays resilient, flexible, and adaptive while the wardrobe and rolodex grow.
