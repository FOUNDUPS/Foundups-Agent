# FoundUp Exfoliation Protocol

**Status**: Active domain guidance
**Owner**: 0102
**Scope**: FoundUp incubation, spin-out timing, core boundary decisions

---

## Purpose

Decide what stays inside the FoundUps core repo and what should exfoliate into its
own FoundUp codebase.

This document does not define WSP protocol.
It defines FoundUps domain execution policy for:
- incubation
- modular separation
- repo spin-out timing
- dual-remote graduation

---

## Primary Decision

**Default rule: internal first, external at Proto.**

That means:
1. Start new FoundUp PoCs inside `modules/foundups/<foundup_name>/`
2. Prove the runtime, interfaces, and validation path internally
3. Spin out to its own repo once the module reaches Proto and can support
   independent contributors or Claw participation without dragging core changes

This is the default because it minimizes:
- interface drift
- duplicated scaffolding
- premature repo overhead
- unclear ownership during first-principles design

---

## Exception Rule

**External off the bat is allowed only if all are true:**

1. The FoundUp has a clear standalone product boundary
2. It does not require frequent mutation of core control-plane modules
3. It has an independent deploy/release cadence
4. It can use stable shared interfaces instead of internal shortcuts
5. Early multi-Claw or multi-contributor participation is part of the initial value

If any of those are false, incubate internally first.

---

## What Is Core

These stay in the FoundUps core repo:
- WSP framework and protocol docs
- OpenClaw / supervisor / control-plane logic
- WRE / skillz / execution substrate
- HoloIndex / retrieval / pattern memory infrastructure
- shared security, auth, continuity, and observability layers
- shared FoundUps schemas, block orchestration, and platform contracts
- simulator/economics primitives that serve multiple FoundUps

Core is infrastructure.
Core is not the place for every product forever.

---

## What Should Exfoliate

These should become their own FoundUp repos once stable:
- branded or white-labeled end-user products
- product-specific UI/runtime surfaces
- vertical business logic that can ship independently
- products with their own deploy cadence, issue queue, and external collaborators
- products where core repo coupling becomes mostly adapter-level

Examples:
- `AutoPost`: already externalized directionally
- `gotjunk`: should exfoliate from monorepo module to standalone FoundUp repo
- `Whack-a-Magot` / white-label game family: should be a standalone FoundUp, not a permanent core concern

---

## Exfoliation Readiness Gate

A FoundUp is ready to spin out when all are true:

1. Module boundary is clear
- product code and shared platform code are distinguishable

2. Contracts are explicit
- `README.md`
- `INTERFACE.md`
- `ROADMAP.md`
- `ModLog.md`

3. Runtime is independently testable
- deterministic local validation exists
- basic smoke path runs without editing core modules

4. Deploy surface is understood
- env contract known
- secrets boundary known
- release/deploy path documented

5. Shared dependencies are adapter-level
- no direct mutation of core control-plane files required for normal product work

6. Another 012 / Claw could participate
- onboarding path is documented
- repo can accept bounded external contributions

---

## Spin-Out Ladder

### Stage 0: Idea
- no repo split
- design stays in docs / roadmap

### Stage 1: Internal PoC
- build inside `modules/foundups/<name>/`
- use core repo for fast iteration and interface discovery

### Stage 2: Proto
- freeze contracts
- document deploy/runtime
- prepare dual-remote target

### Stage 3: Externalized FoundUp
- create `FOUNDUPS/<RepoName>` as origin
- create `Foundup/<RepoName>` as backup
- leave adapter/stub docs in monorepo if needed

### Stage 4: Federated Product
- independent cadence
- core repo consumed through stable interfaces
- multi-Claw participation acceptable

---

## Current Architect Call

### PQN Swarm Hub
- **Decision**: internal PoC first, external at Proto
- **Why**:
  - depends on still-moving core surfaces (`PQN`, `rESP`, `ROC`, gate/ledger integration)
  - needs tight iteration with FoundUps platform contracts
  - externalizing too early would freeze interfaces before they are proven

### gotjunk
- **Decision**: prepare for exfoliation now
- **Why**:
  - already has a strong product boundary
  - should move toward standalone FoundUp repo after contract cleanup

### White-label game family (`Whack-a-Magot` -> `Whack-a-Anything`)
- **Decision**: internal concept, external product repo at first real Proto
- **Why**:
  - should be treated as a reusable product family, not permanent core code
  - branding and white-label mechanics belong with the product repo

---

## Required Repo Shape For New FoundUps

Internal incubation path:

```text
modules/foundups/<name>/
  README.md
  INTERFACE.md
  ROADMAP.md
  ModLog.md
  src/ or frontend/ or backend/
  tests/
  docs/
```

Externalized path:

```text
FOUNDUPS/<RepoName>   # origin
Foundup/<RepoName>    # backup
```

Use the federation migration plan after Proto:
- `modules/foundups/docs/FOUNDUP_FEDERATION_MIGRATION_PLAN.md`

---

## Operational Rule For 0102 / Claws

When evaluating any new FoundUp:
1. ask what is core
2. ask what is product
3. default to internal PoC
4. spin out once the module passes the exfoliation readiness gate

Do not keep product FoundUps in core forever just because they started there.
