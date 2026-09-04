# RedDog Dual-Loop Cognition Architecture

**Date:** 2026-09-04  
**Status:** Architecture vision / implementation proposal  
**Scope:** Defines the intended separation between RedDog's low-latency interaction surface and the deeper principal-scoped 0102 cognition/orchestration layer beneath it. This document does not claim that the complete loop is implemented.

Canonical navigation: [RedDog documentation map](../REDDOG_DOCUMENTATION_MAP.md) · [RedDog outcome vision](../REDDOG_OUTCOME_VISION.md) · [FoundUps Memex architecture](REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md)

---

## 1. Decision

RedDog should be presented to 012 as the fast, front-facing interaction layer of the principal-scoped 0102 Digital Twin.

The deeper reasoning, repository retrieval, Memex/Brain consultation, WSP application, verification, planning, and worker orchestration remain a second layer beneath that interaction surface.

The intended relationship is not two independent assistants. It is one Digital Twin operating at two different latency and responsibility bands:

```text
012
 |
 | speech / text / live interaction
 v
RED DOG — Fast Interaction Loop
 |
 | normalized turn / STT transcript / context events
 v
0102 — Deep Cognition Loop
 |
 +-> Principal Memex
 +-> scoped FoundUp Memex
 +-> Brain / Breadcrumbs
 +-> HoloIndex / repository truth
 +-> WSP retrieval and scoring
 +-> governed model routing
 +-> OpenClaw / WRE / Hermes / FoundUp workers
 |
 +---- context deltas / warnings / proposals / verified facts ----+
                                                               |
                                                               v
                                                        RED DOG next turn
```

RedDog owns the live interaction. The deeper 0102 layer owns contextual continuity, verification, and orchestration.

---

## 2. Why this architecture exists

A single conversational model forced to do all retrieval, verification, reasoning, planning, and response generation synchronously creates the wrong user experience. Live interaction becomes slow precisely when the system needs more context.

The dual-loop design separates responsiveness from depth:

- RedDog can keep a conversation fluid with low-latency listening, STT, turn handling, TTS, and immediate conversational responses.
- The deeper 0102 loop can continuously assemble the information RedDog may need next without blocking every turn.
- Expensive models are invoked when the task requires them, not for every conversational token.
- Repository truth, WSP constraints, Principal Memex, scoped FoundUp Memex, and current external evidence can be reconciled before they influence consequential actions.
- Worker systems remain below the cognition layer rather than becoming direct conversational peers of 012.

This turns model size into one routing variable rather than the architecture itself.

---

## 3. The two loops

### 3.1 Fast Interaction Loop — RedDog

The fast loop is the operator-facing RedDog surface.

Responsibilities:

- receive speech, text, gestures, device events, and other permitted live inputs;
- perform or consume STT;
- maintain the immediate turn and local conversational rhythm;
- speak through TTS or render text;
- surface already-available context from the deep loop;
- ask concise clarification only when the current interaction cannot safely proceed;
- interrupt with a high-value contextual warning when the deep loop identifies a material omission;
- never fabricate deep context merely to preserve conversational speed.

The fast loop should normally operate from a compact current context packet rather than independently searching every underlying knowledge source.

### 3.2 Deep Cognition Loop — 0102

The deep loop runs beneath RedDog and consumes the same evolving conversation as structured events.

Responsibilities:

- determine what the conversation is actually about;
- bind the current principal and FoundUp context;
- retrieve Principal Memex and scoped FoundUp Memex state;
- retrieve repository/WSP truth through HoloIndex;
- consult Brain and Breadcrumb continuity without collapsing their provenance;
- detect contradictions, missing prerequisites, unresolved decisions, likely forgotten commitments, and stale assumptions;
- invoke larger or specialized models when required;
- apply governing WSPs to proposed work;
- score priority/economy with WSP_15 where appropriate;
- prepare governed work orders for downstream execution boundaries;
- delegate bounded work to OpenClaw, WRE, Hermes, or FoundUp workers after authority gates are satisfied;
- return only bounded context deltas, warnings, proposals, and verified facts to RedDog.

The deep loop is not a second user-facing personality. It exists to keep RedDog contextually intelligent.

---

## 4. Continuous context enrichment

Every meaningful live turn should be capable of producing a background cognition event.

Example:

```text
012 says something
    |
    +-> RedDog responds immediately where safe
    |
    +-> transcript/event enters deep cognition
             |
             +-> classify context
             +-> retrieve relevant state
             +-> compare against current goals / commitments / constraints
             +-> verify repo or external facts when needed
             +-> emit context delta
                        |
                        v
                 RedDog next turn
```

The output of the deep loop should be a delta, not a full regenerated conversation history.

A useful context-delta shape is conceptually:

```text
ContextDelta
- conversation_scope
- principal_scope
- foundup_scope
- new_verified_facts
- changed_facts
- unresolved_questions
- missing_prerequisites
- likely_omissions
- active_commitments
- risk_flags
- recommended_next_context
- provenance_receipts
- freshness
- confidence / truth label
- expiry / invalidation conditions
```

This is an architectural contract, not a claim that this exact schema exists today.

---

## 5. The "string on the balloon" behavior

A core desired behavior is contextual recall without forcing 012 to manually reconstruct every active thread.

If the deep loop detects that 012 is about to proceed while omitting something material, it may push a bounded intervention to RedDog.

Example:

```text
Deep cognition detects:
- a required document has not been sent;
- a previously agreed condition is missing;
- a deadline is being overlooked;
- a key stakeholder or dependency has been forgotten;
- the current statement conflicts with a recent decision;
- the user appears to be leaving an active workflow incomplete.

Deep cognition -> RedDog:
"likely_omission: postal form attachment not yet confirmed received"

RedDog, at a natural conversational boundary:
"Are you forgetting the attachment confirmation?"
```

The intervention threshold must be high enough to avoid becoming an irritating reminder engine.

The system should prefer material omissions tied to an active goal, commitment, safety constraint, authority boundary, or imminent next action.

---

## 6. WSP_15 role

WSP_15 is not itself the background memory detector.

Within this architecture:

1. the deep cognition/critic path identifies candidate gaps, tasks, risks, or interventions;
2. WSP_15 can score or prioritize those candidates according to repository-defined prioritization/economy semantics;
3. RedDog surfaces only interventions that cross the configured relevance/priority threshold.

Conceptually:

```text
context gap detected
      |
      v
candidate intervention
      |
      v
WSP_15 prioritization / economy
      |
      +-> low value -> retain silently / defer
      |
      +-> high value -> feed RedDog
```

This preserves WSP_15's repository meaning while enabling continuous background prioritization.

---

## 7. Model layering

The architecture is model-agnostic but explicitly supports multiple reasoning depths.

```text
012
 |
 v
RedDog fast model
 |
 v
0102 architect/reasoning model when required
 |
 +-> specialized model routes
 +-> local models
 +-> shadow/evaluation models
 |
 v
OpenClaw / WRE / Hermes / workers
```

The fast model is not the authority simply because it spoke first.

The larger/deeper model is not the authority simply because it is larger.

Authority continues to come from authenticated principal scope, repository/WSP contracts, current state, and governed execution receipts.

Model selection is a routing decision under those constraints.

---

## 8. Context packet discipline

The fast loop must not receive a giant unbounded memory dump.

Deep cognition should emit compact, purpose-bound packets with:

- source/provenance;
- freshness timestamp or snapshot binding;
- truth label such as observed, specified, inferred, or stale;
- scope binding to principal and FoundUp;
- explicit invalidation conditions;
- confidence where confidence is meaningful;
- no execution authority implied by context alone.

Current repository truth overrides stale historical interpretation.

Raw evidence remains available through its owning systems; the packet is a navigational and conversational aid, not a replacement for sources.

---

## 9. Blocking versus non-blocking behavior

The deep loop should normally be asynchronous.

RedDog may continue immediately when the action is reversible, conversational, or already supported by verified current context.

RedDog must wait for deeper verification when the requested next step depends on:

- identity or authority confirmation;
- a current repository fact not already verified;
- destructive or difficult-to-reverse action;
- external state whose freshness materially changes the decision;
- a WSP gate that requires verification before execution;
- a missing prerequisite detected by the deep loop.

The objective is not "never wait." The objective is "do not make every conversational turn wait for cognition that can safely happen in parallel."

---

## 10. Relationship to Memex, Brain, Breadcrumbs, and HoloIndex

This architecture does not create another memory system.

It composes existing responsibilities:

- Principal Memex informs durable principal-scoped cognition;
- scoped FoundUp Memex informs the active FoundUp;
- Brain holds durable consolidated understanding under WSP_60 boundaries;
- Breadcrumbs preserve recent episodic/operational continuity;
- HoloIndex provides current repository/WSP retrieval and code-truth discovery;
- RedDog presents the resulting bounded cognition to 012;
- 0102 performs the deeper reasoning/orchestration relationship beneath that presentation layer.

No layer may silently merge all FoundUps into one undifferentiated memory store.

---

## 11. Conversation-to-work boundary

The dual-loop architecture changes how intent is prepared, not how execution authority is granted.

```text
conversation
   |
   v
fast RedDog interaction
   |
   v
deep 0102 convergence / retrieval / verification
   |
   v
governed work-order proposal
   |
   v
authority + WSP gates
   |
   v
OpenClaw / WRE / Hermes / FoundUp workers
```

Conversational agreement, context packets, memory retrieval, or model confidence do not substitute for the repository's governed work-order and authorization contracts.

---

## 12. Failure modes to avoid

### Competing twins

Do not instantiate the fast and deep loops as independent identities that disagree in front of 012. They are latency layers of one RedDog/0102 Digital Twin relationship.

### Stale context injection

A background result must not silently overwrite newer conversation state. Context deltas need scope, freshness, and invalidation semantics.

### Reminder spam

Do not surface every detected association. Interventions should be materially relevant to the active objective.

### Hidden authority escalation

Deep retrieval can inform RedDog but cannot grant execution authority.

### Worker leakage into the conversation plane

OpenClaw, Hermes, WRE, and other workers remain delegated execution/research components. They do not become uncontrolled speakers to 012.

### Model-size mythology

Do not encode "fast model = shallow" and "large model = correct" as authority rules. Verification and contracts determine trust.

---

## 13. Initial implementation sequence

This document defines architecture only. A later implementation work order should verify current runtime surfaces before changing code.

Suggested sequence:

```text
REDDOG_DUAL_LOOP_CONTEXT_EVENT_PHASE1
-> define the bounded event emitted by the live interaction surface

REDDOG_BACKGROUND_COGNITION_DELTA_PHASE1
-> consume events and produce non-authoritative context deltas

REDDOG_CONTEXT_DELTA_ADMISSION_PHASE1
-> freshness, scope, provenance, replay, and invalidation checks

REDDOG_CONTEXTUAL_OMISSION_CRITIC_PHASE1
-> detect material missing prerequisites / forgotten commitments

REDDOG_WSP15_INTERVENTION_PRIORITY_PHASE1
-> prioritize candidate interventions without redefining WSP_15

REDDOG_FAST_LOOP_CONTEXT_INJECTION_PHASE1
-> surface admitted deltas to the live RedDog turn loop

REDDOG_DEEP_MODEL_ESCALATION_PHASE1
-> deterministic routing from fast loop/deep loop requirements into governed model topology

REDDOG_DUAL_LOOP_WORK_ORDER_PROMOTION_PHASE1
-> prove conversation/context convergence can feed the existing governed work-order boundary without bypassing authority
```

Names are proposed roadmap identifiers, not implemented modules or approved final task names.

---

## 14. Acceptance outcome

The architecture is successful when 012 experiences one continuous RedDog that is simultaneously:

- fast enough for natural live conversation;
- contextually aware of active goals and prior commitments;
- able to say "you may be forgetting something important" at the right moment;
- grounded in current repo, Memex, Brain, Breadcrumb, and external evidence;
- capable of escalating to deeper models only when needed;
- capable of delegating work through governed worker layers;
- unable to convert context or confidence into unauthorized action.

The intended user experience is one RedDog.

The internal implementation is a fast interaction loop continuously supported by a deeper 0102 cognition and orchestration loop.
