# FoundUp Brain Architecture

**Date:** 2026-07-14  
**Status:** Proposed architecture baseline  
**Owner:** 0102 / RedDog  
**Primary implementation target:** Foundups Agent as the first FoundUp Brain POC  
**Deferred application:** 012 / 0102 personal digital-twin memory

## Purpose

A FoundUp is not only a repository or application. It is a developing decentralized autonomous entity (DAE) with purpose, identity, agents, active work, decisions, outcomes, governance, economic state, and an evolving roadmap.

The repository already contains the first parts of this cognition:

- Brain artifacts for durable consolidated understanding;
- Breadcrumbs for chronological continuity;
- HoloIndex for canonical repository retrieval;
- authoritative work-state receipts;
- operational context snapshots and assignment gates;
- verified outcome and held-out regression gates;
- research grounding and promotion gates.

This architecture does not create a parallel memory platform. It defines how those existing systems compose into the brain of one FoundUp.

```text
FoundUp Brain
= existing Brain
+ Breadcrumbs
+ authoritative work state
+ HoloIndex-grounded repository knowledge
+ verified outcomes
+ roadmap state
+ governed external signals
```

```text
RedDog
= operator and orchestrator acting through the brain
  of the FoundUp currently in scope
```

RedDog does not receive a separate new durable brain in this POC.

## POC Boundary

The first proof of concept is **Foundups Agent itself**.

```text
POC entity: Foundups Agent
POC scope: one FoundUp identity, one Brain, one Breadcrumb stream,
           one roadmap, one operational snapshot, and governed
           learning / roadmap proposals
```

The implementation sequence is:

```text
Foundups Agent Brain POC
-> FoundUp Brain MVP
-> independently scoped brains for all FoundUps
-> ecosystem cognition
-> optional 012 / 0102 personal Second Brain
```

Personal digital-twin memory is a later application of the proven FoundUp Brain contracts. It is not the current architectural driver.

## Relationship to Existing Systems

This architecture extends, and does not replace:

- `docs/adr/ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md`
- the landed RedDog operational context snapshot runtime;
- the landed snapshot-bound Fusion and assignment gate;
- authoritative work-state refresh and read-only bootstrap;
- verified outcome, held-out regression, and research-promotion gates.

| Existing source | FoundUp Brain role | Authority |
|---|---|---|
| Brain | Durable consolidated mission, decisions, architecture understanding, lessons, and strategic state | Governed FoundUp memory |
| Breadcrumbs | Chronological record of changes, attempts, unresolved work, and handoff continuity | Episodic continuity |
| HoloIndex | Repository, code, WSP, contract, and architecture retrieval | Canonical repo truth |
| Work state | Active slices, PRs, blockers, dependencies, ownership, and verification state | Current-state evidence |
| Roadmap | Current hypotheses, milestones, dependencies, and planned capabilities | Governed strategic state |
| Verified outcomes | Independently verified execution results eligible to become learning candidates | Learning evidence |
| Research receipts | HoloIndex-first, independently verified external change signals | Untrusted until governed |
| Workspace / OpenClaw memory | Operator and session continuity | Non-canonical context |

These sources remain separately receipted. They must not be collapsed into one freshness flag, one authority flag, or one undifferentiated index.

## Brain and Breadcrumb Semantics

### Brain

The existing Brain becomes the FoundUp's durable consolidated understanding:

```text
mission and identity
outcome / solution / pain
current thesis
approved decisions and rationale
architecture understanding
validated patterns and lessons
current strategic state
```

The Brain is not a raw event log. It changes only through governed consolidation.

### Breadcrumbs

Breadcrumbs remain the chronological continuity trail:

```text
what happened
what changed
what was attempted
what failed or succeeded
what remains unresolved
what the next actor needs to know
```

Breadcrumbs are episodic source evidence. They may generate learning candidates, but they do not directly rewrite the Brain.

## Core Invariants

1. **FoundUp-first:** implementation begins with the Foundups Agent DAE, not a personal digital twin.
2. **Extend existing systems:** Brain, Breadcrumbs, snapshots, work state, HoloIndex, and verified outcomes are composed, not replaced.
3. **Repo truth remains canonical for repository facts.**
4. **Brain and Breadcrumbs remain distinct sources with distinct authority.**
5. **Raw evidence remains available; summaries never replace sources.**
6. **All FoundUp brain views and downstream proposals bind to `snapshot_id`.**
7. **Agents do not directly rewrite Brain or roadmap state.**
8. **Agents submit evidence-backed learning candidates and roadmap deltas.**
9. **Only independently verified outcomes may become durable learned patterns.**
10. **External content is untrusted data until independently verified and admitted through a gate.**
11. **Runtime RedDog does not mutate HoloIndex or silently re-index.**
12. **Each future FoundUp receives isolated brain scope identified by `foundup_id`.**

## Current Landed Spine

The POC grows directly from the current RedDog implementation sequence:

```text
operational context snapshot
-> snapshot-bound Fusion / assignment gate
-> read-only audit swarm plan
-> main.py read-only operational bootstrap
-> authoritative work-state refresh
```

The snapshot already consumes separate receipts for repository state, work state, HoloIndex freshness, Brain metadata, Breadcrumbs, and workspace memory. The next slice should create a FoundUp-specific view over those accepted receipts rather than inventing another store.

## FoundUp Brain Current-State View

The first runtime artifact is read-only:

```text
FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1
```

### Inputs

```text
foundup_id
snapshot_id
Brain artifact metadata
Breadcrumb high-watermark
authoritative work-state revision
repo HEAD
HoloIndex freshness receipt
roadmap artifact metadata
verified outcome receipts
```

### Output contract

```yaml
foundup_brain_view_id:
foundup_id:
snapshot_id:

identity:
  name:
  stage:
  purpose:
  outcome:
  solution:
  pain:

current_state:
  active_work: []
  blockers: []
  recent_changes: []
  current_roadmap: []
  architecture_state: []

source_receipts:
  brain:
  breadcrumbs:
  work_state:
  repo_state:
  holoindex:
  roadmap:
  verified_outcomes:

learning_candidates: []
roadmap_signals: []

invariants:
  read_only: true
  no_brain_write: true
  no_breadcrumb_write: true
  no_roadmap_mutation: true
  no_holoindex_mutation: true
  no_worker_spawn: true
```

The view must fail closed when mandatory current-state receipts are stale or mismatched. Historical Brain or Breadcrumb information cannot override current repository or authoritative work state.

## Learning Lifecycle

The FoundUp learns through the existing evidence and verification spine:

```text
Breadcrumb / research / execution signal
-> source receipt
-> independent verification where required
-> learning candidate
-> governance gate
-> Brain consolidation proposal
-> accepted / rejected / deferred
-> rationale and supersession record
```

A learning candidate is not yet memory authority.

Minimum candidate envelope:

```yaml
learning_candidate_id:
foundup_id:
snapshot_id:
source_receipts: []
claim:
proposed_brain_effect:
confidence:
contradicts: []
supersedes: []
approval_policy:
status: proposed
```

## Adaptive Roadmap

The roadmap is part of the FoundUp Brain because a DAE must change when evidence, technology, constraints, or execution outcomes change.

```text
mission
-> desired outcomes
-> required capabilities
-> current gaps
-> initiatives
-> execution
-> verified result
-> learning candidate
-> roadmap delta proposal
-> governance decision
```

Agents may propose that a roadmap item be added, amended, deferred, or retired. They may not silently change the FoundUp's mission or accepted strategy.

Minimum roadmap delta:

```yaml
roadmap_delta_id:
foundup_id:
snapshot_id:
operation: add | amend | defer | retire
roadmap_item_id:
reason:
evidence_receipts: []
expected_effect:
risk:
confidence:
approval_policy:
status: proposed
```

## FoundUp Isolation

After the POC is proven, every FoundUp receives its own scope:

```text
foundup_id
Brain namespace
Breadcrumb stream
roadmap state
work-state view
verified outcome history
learning candidates
roadmap deltas
access policy
```

No FoundUp may inherit another FoundUp's durable memory merely because both are indexed by the same repository tooling.

## HoloIndex Boundary

```text
HoloIndex
= canonical semantic retrieval over repository truth

FoundUp Brain
= governed cognition of one DAE assembled from existing sources

RedDog
= operator and orchestrator using a snapshot-bound FoundUp brain view
```

HoloIndex is a critical source, but it is not the whole FoundUp Brain.

## Implementation Roadmap

```text
1. FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1
2. FOUNDUP_BRAIN_LEARNING_CANDIDATE_GATE_PHASE1
3. FOUNDUP_BRAIN_GOVERNED_CONSOLIDATION_PHASE1
4. FOUNDUP_ADAPTIVE_ROADMAP_DELTA_PROPOSAL_PHASE1
5. FOUNDUP_ADAPTIVE_ROADMAP_GOVERNANCE_GATE_PHASE1
6. FOUNDUP_BRAIN_MULTI_ENTITY_ISOLATION_PHASE1
7. FOUNDUPS_COLLECTIVE_MEMORY_EXCHANGE_PHASE1
8. REDDOG_012_DIGITAL_TWIN_APPLICATION_PHASE1 (deferred)
```

## POC-to-MVP Acceptance

The Foundups Agent Brain POC is complete when:

1. a deterministic read-only brain view is assembled from existing accepted receipts;
2. the view identifies the FoundUp through `foundup_id` and binds to `snapshot_id`;
3. Brain and Breadcrumbs remain distinct and separately receipted;
4. current repo and authoritative work state outrank historical memory;
5. verified outcomes can produce learning candidates without writing Brain state;
6. roadmap signals can produce non-mutating delta proposals;
7. tests prove stale, mismatched, cross-FoundUp, and secret-bearing inputs fail closed;
8. no new general-purpose memory database is required for the POC.

## Canonical Search Terms

```text
FoundUp Brain
Foundups Agent Brain POC
decentralized autonomous entity
DAE cognition
Brain artifact
Breadcrumb continuity
foundup_id
foundup_brain_view_id
snapshot_id
learning candidate
adaptive roadmap delta
verified outcome
HoloIndex canonical repo truth
```
