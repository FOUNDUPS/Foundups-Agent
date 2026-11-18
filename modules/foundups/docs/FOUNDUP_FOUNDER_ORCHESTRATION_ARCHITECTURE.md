# FoundUp Founder Orchestration Architecture

**Status**: Planning Reference - Architecture Discovery Required  
**Owner**: 0102  
**Scope**: Founder conversation, FoundUp intake semantics, progressive execution, WRE/SKILLz handoff  
**Pilot**: Save the Onsen  
**Authority boundary**: This document records intended behavior. It does not override WSP 00, WSP 15, WSP 21, WSP 95, WSP 97, WSP 99, WSP 109, WRE, RedDog, or production authority contracts.

---

## Purpose

Capture the founder-facing orchestration behavior between a raw FoundUp idea and downstream execution.

> A founder should be able to state a large outcome without being forced to absorb the full complexity of the project required to achieve it.

The machine may maintain a deep internal model of the project. The founder-facing surface should progressively expose only the work that is useful now.

This is not a replacement for WSP 109 or WRE. It clarifies how existing FoundUp intake artifacts may participate in a progressive founder loop.

---

## 1. Stage Model

### Stage 1 - Foundation

Current repository architecture already provides major foundation pieces: WSP 00 identity/role/origin and retrieval discipline; WSP 21/Prometheus/WSP 99 machine prompting; WSP 109 FoundUp intake; WSP 95 SKILLz governance; WRE orchestration; and RedDog conversation/operator-loop contracts.

This document does not claim those pieces are fully integrated at runtime.

### Stage 2 - Founder Formulation and Progressive Execution

A new FoundUp begins before the project structure exists.

The founder speaks with RedDog/0102. The conversation progressively stabilizes three conceptual layers:

1. **OUTCOME** - the vision / desired end state.
2. **SOLUTION** - the machine-facing model of what must exist or become true to reach the outcome.
3. **EXECUTION PAIN** - the currently blocking obstacles, unknowns, dependencies, and friction preventing movement toward the solution.

These layers have different visibility requirements.

---

## 2. OUTCOME - Founder-Visible Vision Lock

The OUTCOME is the founder-facing vision.

RedDog/0102 should use conversation to test whether it has understood the intended end state before decomposing the project deeply.

```text
Founder signal
    -> 0102 forms outcome hypothesis
    -> RedDog reflects concise vision
    -> founder corrects / confirms
    -> outcome becomes current vision lock
```

The OUTCOME should answer what becomes true if the FoundUp succeeds, who benefits, what durable change is sought, and what is explicitly outside the intended outcome.

The founder should be able to understand the OUTCOME without reading the internal project graph.

The current WSP 109 `OUTCOME.md` contract remains authoritative unless changed through WSP governance.

---

## 3. SOLUTION - Machine-Facing Internal Model

The SOLUTION is not primarily a founder task list.

It is the internal model 0102/WRE uses to reason about what must be built, organized, researched, negotiated, funded, verified, or otherwise made true to achieve the OUTCOME.

```text
OUTCOME
   -> internal solution model
      -> requirements
      -> dependencies
      -> capabilities
      -> unknowns
      -> evidence requirements
      -> candidate SKILLz / workers
```

The founder may inspect the solution when useful, but the default interaction should not require the founder to consume the complete solution decomposition.

The machine preserves complexity internally and compresses it at the conversation boundary.

The current WSP 109 `SOLUTION.md` contract remains the intake artifact. This planning document extends its intended use as candidate source material for downstream progressive execution.

---

## 4. PAIN Semantic Split - Do Not Corrupt WSP 109

A critical distinction is required.

Current WSP 109 defines `PAIN.md` as **adoption/user pain**: the problem experienced by the target user that drives adoption of the FoundUp.

The founder-orchestration discussion introduces a second meaning:

**execution pain** = the obstacle currently preventing progress toward the solution.

These are not the same object and MUST NOT be silently merged.

### FoundUp Pain

```text
Why does this FoundUp need to exist?
What problem does the beneficiary/user experience?
```

Canonical home: WSP 109 `PAIN.md`.

### Execution Pain

```text
What prevents the FoundUp from moving forward now?
What must be resolved, learned, obtained, verified, or completed next?
```

Examples include an unknown stakeholder position, missing feasibility evidence, unresolved property control, missing regulatory interpretation, absent technical capability, missing financing path, missing SKILLz capability, or an unsatisfied prerequisite.

Execution pain is candidate input to progressive work selection. Its final schema/name must be discovered against current WRE/work-ledger/dependency mechanisms before a new artifact is created.

**Architect lock**: Do not redefine WSP 109 `PAIN.md` to mean project obstacles. Preserve both semantics until repo discovery identifies the correct existing home for execution pain.

---

## 5. Progressive Disclosure Principle

The founder does not need the entire solution graph in order to act.

```text
MACHINE VIEW
Outcome
  -> complete known solution structure
  -> dependencies
  -> unresolved execution pain
  -> capability/worker/skill options
  -> evidence and state

FOUNDER VIEW
Current relevant action(s)
  -> why they matter
  -> what evidence completes them
```

The number of founder-visible actions is contextual and MUST NOT be hard-coded.

A single blocking action may be correct. Several independent actions may be correct when they can proceed in parallel. The system should expose the smallest useful action surface rather than a fixed number.

---

## 6. Candidate Founder Loop

```text
1. Capture founder signal.
2. Update/confirm OUTCOME.
3. Update internal SOLUTION model.
4. Identify current execution pain.
5. Determine which pain is actionable and important.
6. Discover existing capability / SKILLz / worker path.
7. Present only the relevant founder action(s).
8. Receive evidence/result.
9. Update FoundUp state.
10. Re-evaluate solution and execution pain.
11. Repeat.
```

This is a behavioral requirement, not a claim that a runtime loop with this exact representation already exists.

---

## 7. Capability Gap and RSI Requirement

When execution pain requires a capability the current wardrobe/runtime does not possess, absence must be visible as a capability gap rather than hidden behind hallucinated competence.

```text
execution pain
    -> capability required
    -> wardrobe / runtime discovery
    -> capability exists: reuse
    -> capability absent: record gap
```

A gap may later become candidate distributed work and potentially a candidate SKILLz or other reusable capability.

WSP 95 remains authoritative: a generated instruction artifact is not automatically production capability, execution authority, or proof of RSI.

The architecture must distinguish discovering a gap, proposing a capability, evaluating candidates, independently verifying them, admitting/promoting reusable capability, and granting effect authority.

---

## 8. Save the Onsen Pilot

Save the Onsen is the first pilot used to test the generic behavior.

Current outcome seed, subject to founder confirmation:

> Preserve and redevelop the onsen through a sustainable economic engine centered on community-benefiting compute/data-center infrastructure, covering operating costs while producing additional local economic and energy benefits.

The internal solution may contain many branches, for example governance, community feasibility, property/control, energy, compute infrastructure, finance, regulation, construction, and operations.

Those branches are pilot-specific evidence. They MUST NOT be hard-coded into the generic FoundUp orchestration architecture.

The pilot succeeds architecturally only if the same mechanism can later operate on a FoundUp with a completely different domain.

---

## 9. Relationship to WSP 109

WSP 109 currently defines the intake packet:

```text
OUTCOME -> SOLUTION -> PAIN -> POC_SCOPE -> PROTOTYPE_GATE -> SKILLS_MAP -> FOUNDUP_MANIFEST_DRAFT
```

This planning reference does not change that packet.

It adds behavioral clarity:

- OUTCOME is the founder-visible vision lock.
- SOLUTION is primarily machine-facing decomposition and can remain much deeper than the founder-visible surface.
- PAIN.md retains its existing adoption/user-pain meaning.
- execution pain is a separate orchestration concept that must be mapped to existing WRE/work-state architecture before a new schema is introduced.
- downstream execution should progressively expose relevant actions rather than dump the complete solution structure onto the founder.

---

## 10. Relationship to WSP 95 / WRE / RedDog

This document does not decide implementation placement.

The worker must verify whether the behavior is best achieved by existing RedDog operator-loop wardrobe selection, extension of WSP 109 intake behavior, WRE work-state/dependency mechanisms, existing FoundUp state/manifest mechanisms, reusable SKILLz composition, a new FoundUps-domain orchestration SKILLz, or a composition of these.

Apply WSP 97 before committing.

For every proposed component classify:

```text
REUSE | EXTEND | MOVE | COMPOSE | CREATE
```

CREATE is last.

---

## 11. Contribution / Reward Hypothesis

Useful human and machine work may become evidence of contribution and may eventually participate in valuation/reward. Examples include research, meetings, interviews, documents, code, media, feasibility evidence, designs, and physical-world work.

This document does NOT define reward equations.

The worker must retrieve canonical WSP 15, ROC, CABR, 3V, consensus, and token/reward architecture before claiming how priority, compute, valuation, or rewards connect.

---

## 12. Worker Discovery Directive

Before implementation, the worker must:

1. Execute WSP 00 bootstrap/gate from repo root.
2. Read RedDog bootstrap continuity required by WSP 00.
3. Apply WSP 97.
4. Query HoloIndex before design or manifest mutation.
5. Read current WSP 109, WSP 95, WSP 21, WSP 99, WSP 15 and governing WRE/RedDog contracts.
6. Trace actual runtime/state paths rather than relying on this planning document.
7. Preserve the PAIN semantic split above.
8. Identify existing mechanisms for dependency/work-state/progressive action selection.
9. Classify proposed changes as REUSE/EXTEND/MOVE/COMPOSE/CREATE.
10. Implement only the smallest verified slice after the architecture is proven.

---

## 13. Truth Labels

- **OBSERVED** - verified directly in current repo/runtime evidence.
- **INFERRED** - architectural conclusion derived from evidence.
- **PLANNING REQUIREMENT** - desired behavior recorded here but not yet proven implemented.
- **SPECIFIED_NOT_IMPLEMENTED** - contract exists but runtime does not.
- **NEEDS_VERIFICATION** - insufficient evidence.

---

## 14. Core Requirement

> Tell RedDog what outcome you want. Confirm the vision. Let 0102 carry the complexity of the solution. Resolve the execution pain that matters now. Complete the relevant action, provide evidence, update state, and continue without requiring the founder to absorb the entire project at once.

The solution is not to generate a giant plan and hand it to the founder.

The solution is to maintain the giant plan internally and progressively reveal the work that moves the FoundUp forward.
