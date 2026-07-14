# RedDog and FoundUps Second Brain Architecture

**Date:** 2026-07-14  
**Status:** Proposed architecture baseline  
**Owner:** 0102 / RedDog  
**Scope:** Personal digital twin memory, FoundUp organizational memory, adaptive roadmap cognition, and cross-brain context assembly

## Purpose

RedDog currently retrieves repository knowledge, continuity, work state, and execution evidence from several independent sources. Those sources are necessary but do not by themselves form a second brain.

A second brain is the governed lifecycle that captures evidence, forms durable knowledge, connects it over time, retrieves it for a bounded task, learns from outcomes, and revises beliefs or plans without rewriting history.

The architecture establishes three distinct roles:

```text
012 Brain
= sovereign personal digital-twin memory

FoundUp Brain
= sovereign organizational memory for one FoundUp

RedDog
= cognitive operating system that assembles snapshot-bound context,
  dispatches agents, records outcomes, and proposes controlled memory evolution
```

RedDog is not the owner of every memory. It is the router and operational executive across separately scoped brains.

## Relationship to Existing Memory Systems

This architecture extends, and does not replace, the accepted boundary in:

- `docs/adr/ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md`

The existing roles remain intact:

| Source | Role | Authority |
|---|---|---|
| HoloIndex | Repository, code, WSP, contract, and architecture retrieval | Canonical repo truth |
| OpenClaw / continuity memory | Session notes, preferences, recent decisions, and daily continuity | Non-canonical context |
| AI Overseer / execution memory | Automation patterns, outcomes, and execution state | Operational evidence |
| Work state | Current task, branch, issue, PR, and active execution state | Current-state evidence |
| Breadcrumbs | Recent continuity trail | Non-canonical continuity |
| 012 Brain | Versioned model of 012 knowledge, beliefs, decisions, and preferences | Sovereign personal memory |
| FoundUp Brain | Mission, roadmap, decisions, experiments, and institutional knowledge | Sovereign organizational memory |

These sources must remain separately receipted. They must not be collapsed into one freshness flag, one authority flag, or one undifferentiated vector index.

## Core Invariants

1. **Repo truth remains canonical for repository facts.**
2. **Personal memory and FoundUp memory remain separately owned and scoped.**
3. **Raw source evidence is preserved; summaries never replace sources.**
4. **All operational answers and actions bind to `snapshot_id`.**
5. **Agents do not directly rewrite durable memory.**
6. **Agents submit evidence-backed memory mutations.**
7. **Roadmaps are versioned hypotheses, not static documents.**
8. **Contradictions, supersession, confidence, and temporal validity are explicit.**
9. **Private continuity is not silently indexed into canonical repository retrieval.**
10. **Memory retrieval must expose source, authority, freshness, and provenance.**

## Brain Topology

```text
FoundUps Ecosystem Brain
|
+-- 012 Brain
|   +-- identity and terminology
|   +-- beliefs and evolving positions
|   +-- decisions and rationale
|   +-- preferences and operating constraints
|   +-- experiences and creative history
|   +-- predictions and outcomes
|
+-- RedDog Operational Brain
|   +-- current snapshot
|   +-- task and branch state
|   +-- source routing
|   +-- agent assignments
|   +-- execution receipts
|   +-- short-lived working memory
|
+-- FoundUp Brains
    +-- mission and outcome
    +-- pain and solution model
    +-- roadmap and dependencies
    +-- architecture and modules
    +-- decisions and rejected alternatives
    +-- experiments and measured outcomes
    +-- external technology and market signals
```

## Memory Classes

Every brain implementation must support six memory classes.

### 1. Source memory

Immutable or minimally transformed evidence:

- conversations
- transcripts
- videos
- documents
- commits and diffs
- research papers
- web captures
- tool receipts
- agent outputs

### 2. Semantic memory

Extracted knowledge and propositions. Every semantic record must point to source receipts.

### 3. Episodic memory

Events and outcomes: what was attempted, accepted, rejected, failed, changed, or learned.

### 4. Procedural memory

How work is performed: WSP procedures, validation sequences, security gates, coding conventions, and operating playbooks.

### 5. Working memory

The bounded context for the current task. Working memory is snapshot-scoped and disposable.

### 6. Prospective memory

Future review triggers and conditional obligations: revisit an assumption, monitor a dependency, re-run an evaluation, or reconsider a roadmap item when a condition changes.

## Snapshot-Bound Context

Before answering or acting, RedDog assembles an operational context snapshot.

Required source receipts:

```text
repo_state
work_state
continuity_or_breadcrumbs
012_brain
relevant_foundup_brain
workspace_memory
holoindex
external_research_when_needed
```

Every downstream artifact must bind to:

```text
snapshot_id
```

Examples:

```text
RedDog answer -> snapshot_id
Audit report -> snapshot_id
Agent assignment -> snapshot_id
Roadmap proposal -> snapshot_id
Memory mutation -> snapshot_id
```

A snapshot must preserve source-specific authority, freshness, and retrieval status. A failed or stale source must be reported explicitly rather than silently omitted.

## Memory Mutation Contract

Agents may propose memory changes but cannot directly mutate durable memory.

Required mutation operations:

```text
create
reinforce
amend
supersede
contradict
archive
forget
```

Minimum mutation envelope:

```yaml
memory_mutation_id:
target_brain:
operation:
subject:
proposed_content:
source_receipts: []
confidence:
valid_from:
valid_until:
reason:
agent_id:
snapshot_id:
approval_policy:
```

Mutation evaluation must check:

- provenance
- target-brain ownership
- authority conflicts
- temporal validity
- privacy classification
- prompt-injection risk
- contradiction and supersession relationships
- approval requirements

## Adaptive Roadmap Engine

A FoundUp roadmap is a versioned reasoning system:

```text
mission
-> desired outcomes
-> required capabilities
-> current gaps
-> candidate initiatives
-> dependencies and risks
-> evidence
-> priority
-> execution
-> measured result
-> revised roadmap
```

Minimum roadmap item:

```yaml
roadmap_item_id:
foundup_id:
objective:
hypothesis:
expected_benefit:
evidence: []
dependencies: []
cost:
risk:
confidence:
status:
owner_agent:
last_reviewed:
review_trigger:
supersedes:
snapshot_id:
```

Agents may propose roadmap deltas after detecting new technology, changed evidence, failed assumptions, legal constraints, or execution outcomes. They may not silently alter mission or accepted strategy.

Required flow:

```text
signal detected
-> relevance assessment
-> evidence collection
-> impact analysis
-> roadmap delta proposal
-> governance gate
-> accepted / rejected / deferred
-> recorded rationale
```

## Retrieval and Authority Rules

1. Retrieve canonical repository truth through HoloIndex first when the task concerns code, WSPs, contracts, or repo architecture.
2. Retrieve relevant 012 or FoundUp memory only within the task's authorization scope.
3. Label all injected context by source class.
4. Prefer current authoritative state over old summaries.
5. Preserve contradictory historical records rather than deleting them unless an explicit forgetting policy applies.
6. Report inference as inference; do not present inferred digital-twin behavior as a direct statement by 012.

Required distinction for 012 Brain output:

```text
direct statement by 012
approved operating rule
historical pattern
RedDog inference
autonomous decision
```

## Security and Privacy

The second brain expands the prompt-injection and privacy attack surface.

Required controls:

- source classification before persistence
- private-by-default continuity handling
- evidence-backed mutation gate
- no direct write from imported documents or web content
- redaction before cross-layer logging or indexing
- scoped agent access
- audit trail for reads and mutations
- explicit deletion, archival, and retention policies
- separation of personal, FoundUp, and ecosystem memory

## HoloIndex Boundary

HoloIndex remains specialized repository and architecture cognition.

```text
HoloIndex
= canonical semantic retrieval over repository truth

Second Brain
= governed memory lifecycle across personal, organizational,
  episodic, procedural, prospective, and working memory

RedDog
= context router and operational executive
```

HoloIndex is one source within snapshot assembly. It is not the entire second brain.

## Implementation Roadmap

```text
1. REDDOG_SECOND_BRAIN_MEMORY_CONTRACT_PHASE1
2. REDDOG_SOURCE_PROVENANCE_AND_TEMPORAL_MEMORY_PHASE1
3. REDDOG_012_DIGITAL_TWIN_EPISTEMIC_GRAPH_PHASE1
4. FOUNDUP_BRAIN_RUNTIME_AND_MEMORY_ISOLATION_PHASE1
5. FOUNDUP_ADAPTIVE_ROADMAP_ENGINE_PHASE1
6. REDDOG_CROSS_BRAIN_CONTEXT_ROUTER_PHASE1
7. REDDOG_MEMORY_CONSOLIDATION_CONTRADICTION_AND_FORGETTING_PHASE1
8. REDDOG_MEMORY_EVALUATION_AND_REGRESSION_HARNESS_PHASE1
9. FOUNDUPS_COLLECTIVE_MEMORY_EXCHANGE_PHASE1
```

## Phase-1 Acceptance

The architecture baseline is discoverable when:

1. this document is indexed by HoloIndex;
2. the companion ADR is present and linked;
3. the architecture registry entry resolves to this canonical path;
4. implementation prompts reference these invariants;
5. future memory and roadmap changes cite `snapshot_id` and source receipts;
6. no duplicate document claims to be the canonical Second Brain architecture.

## Canonical Search Terms

```text
second brain
012 brain
digital twin
FoundUp brain
sovereign memory
adaptive roadmap
memory mutation
snapshot_id
temporal memory
prospective memory
cross-brain context router
source receipts
```
