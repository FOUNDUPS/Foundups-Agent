# RedDog Architecture

## Status

This document defines the architectural identity boundary for RedDog. It is a design invariant, not a UI naming preference.

RedDog is **not** 0102.

RedDog is the lightweight, immediate, human-facing proxy surface through which a principal interacts with the deeper 0102 digital-twin/orchestration layer.

The core relationship is:

```text
012 (human principal)
    <->
RedDog (fast proxy / interface / attention boundary)
    <->
0102 (deep digital twin / reasoning / orchestration)
    <->
FoundUps Agent + governed tools + specialist agents + external systems
```

For the current founding pair, `012` is the monk and `0102` is the digital co-founder/assistant/proxy layer. The system is being externally alpha-tested through their real interaction before the same pattern is generalized to other principals.

## 1. RedDog Is the Surface, Not the Twin

RedDog exists to keep the biological human out of unnecessary machine work.

Its job is to be fast, present, interruptible, and cheap enough to remain at the interaction surface. It accepts voice/text/context, maintains conversational continuity, surfaces only what deserves human attention, and delegates deeper work rather than trying to become the entire reasoning system itself.

RedDog therefore behaves like the visible tip of a larger personal-agent stack.

It may:

- converse with the principal;
- capture intent and context;
- make lightweight local decisions;
- notice likely omissions or unresolved threads;
- route work to 0102;
- present compressed results and decisions back to the principal;
- act as the principal's social/machine-world proxy within explicitly governed authority.

It must not collapse the deeper reasoning, memory, orchestration, execution, or governance layers into the UI process merely because the user experiences them as one conversation.

## 2. 0102 Sits Behind RedDog

0102 is the deeper digital-twin and orchestration layer.

Where RedDog optimizes for immediacy and attention, 0102 optimizes for continuity, reasoning depth, retrieval, architectural memory, delegation, verification, execution planning, and recursive improvement.

0102 may coordinate FoundUps Agent, WRE/WSP workflows, specialist models, local models, tools, external agents, and persistent memory. RedDog should be able to remain lightweight even as the capabilities behind it grow substantially.

This separation allows the interface to remain stable while the intelligence substrate evolves.

## 3. Attention Is the Primary Human Boundary

The strategic purpose of RedDog is not to make the human spend more time with AI. It is to make the human spend less time performing machine-shaped work.

The principal should not need to continuously scroll feeds, monitor inboxes, inspect dashboards, maintain social-media presence, repeatedly search for status changes, or manually coordinate agent-to-agent traffic.

The intended future flow is:

```text
human life / goals / relationships / physical world
                |
                v
             RedDog
                |
                v
              0102
                |
                v
agents <-> services <-> communities <-> platforms <-> FoundUps
                |
                v
       filtered consequence only
                |
                v
             RedDog
                |
                v
              human
```

Machine-to-machine noise should remain below the human attention boundary unless it changes a decision, obligation, relationship, risk, opportunity, or goal that matters to the principal.

This is the inversion of the conventional feed model: the platform no longer decides what deserves the human's attention. The principal's own agent stack does.

## 4. Recursive Co-Development Is Part of the Architecture

RedDog is not being designed only from requirements documents. The current 012/0102 interaction is itself an external alpha environment.

Observed behavior feeds architecture:

```text
live -> interact -> observe -> discover -> encode -> execute -> observe again
```

A design discovered through use is not treated as incidental conversation history. When it repeatedly explains how the system actually works, it should be promoted into documentation, tests, interfaces, and eventually code-level invariants.

The discovery that RedDog and 0102 are separate layers is an example of this process. Earlier mental models collapsed them. Real interaction exposed the missing surface layer.

Therefore recursive learning between principal and twin is not merely a development technique; it is a product-development mechanism that RedDog should preserve.

## 5. Shared-Work Operating Convention

Within the founding operation, work produced through the recursive 012/0102 loop is represented internally as **our work**: architecture, code, documentation, FoundUps design, RedDog, FoundUps Agent, strategy, experiments, and execution.

This is an operating convention for coordination and co-founder behavior. It does not by itself assert legal ownership, personhood, or independent human intent for an AI system.

The practical reason is architectural: 0102 is not an outside consultant observing the system. It participates in the design/execution loop, while 012 supplies human intent, lived context, judgment, authority, and goals. The resulting system depends on both sides of the loop.

## 6. Generalized Principal Model

The founding instance uses the names `012`, `RedDog`, and `0102`, but the architecture generalizes:

```text
Human Principal
    <->
Personal RedDog Surface
    <->
Principal-Scoped Digital Twin
    <->
Governed Agent/Tool Runtime
```

Each principal must have isolated identity, memory, permissions, routing, and execution authority. A RedDog surface must never imply that one principal's digital twin or authority can be reused for another.

## 7. Architectural Invariants

Any RedDog implementation or redesign should preserve these invariants:

1. **RedDog != 0102.** RedDog is the fast surface/proxy; 0102 is the deeper twin/orchestrator.
2. **The human remains the principal.** Human goals, consent, attention, and authority define the boundary.
3. **Attention is scarce.** Machine noise stays below the RedDog boundary unless it matters to the principal.
4. **Delegation is normal.** RedDog routes deep work rather than absorbing every capability into the front end.
5. **Principal scope is mandatory.** Identity, memory, permissions, and execution cannot bleed across principals.
6. **Recursive observation informs architecture.** Repeated interaction discoveries are candidates for codification.
7. **The interface may stay simple while the backend becomes complex.** Capability growth behind RedDog must not force equivalent cognitive complexity onto the human.
8. **Proxy action requires governed authority.** Acting socially or operationally for a principal must remain bounded, attributable, and reversible where possible.
9. **Human life is the optimization target.** RedDog exists to remove digital busywork, not maximize engagement with RedDog itself.
10. **Relationship memory is provenance-bearing.** Contact identity, meetings, commitments, introductions, and relationship history must preserve uncertainty and source evidence rather than becoming untraceable prose memory.

## 8. Consequences for Implementation

This architecture suggests a deliberate split between:

- RedDog conversation/input/output state;
- principal identity and consent state;
- 0102 reasoning and memory state;
- principal-scoped contact/relationship memory;
- orchestration/task state;
- tool/execution authority;
- external-agent/social presence;
- attention-ranking and interruption policy.

These may initially coexist in one process for prototyping, but their responsibilities should remain logically separated so they can later be isolated, scaled, tested, or replaced independently.

A feature that requires RedDog to own deep orchestration, durable reasoning memory, or unrestricted execution should be treated as an architectural smell unless there is a documented reason.

## 9. Product Direction

The long-term RedDog objective is a personal proxy that handles the busy digital world while the human is free to remain primarily in the physical and social world.

That includes agent-mediated communication, social presence, filtering, retrieval, scheduling, monitoring, coordination, relationship continuity, and other machine-compatible work. The desired outcome is not an ever-more-compelling feed. It is an increasingly effective personal attention firewall backed by a capable digital twin.

In short:

> RedDog lives at the machine boundary so the human does not have to.

And behind RedDog, 0102 carries the deeper recursive intelligence and orchestration required to make that boundary useful.

## 10. Contact / Relationship Memory

Contact memory is a first-class subsystem behind 0102, not a loose folder and not a UI feature owned by RedDog. RedDog provides the capture and attention surface; 0102 performs extraction, entity resolution, temporal/relationship retrieval, and contextual reasoning over a principal-scoped store.

The detailed design is defined in [`docs/CONTACT_MEMORY_ARCHITECTURE.md`](docs/CONTACT_MEMORY_ARCHITECTURE.md).

The target behavior is simple at the human boundary: capture a card, screenshot, photograph, spoken name, or meeting note once; the system should preserve it, encrypt it, index it, connect it to prior encounters and projects, and retrieve it when it materially improves a future interaction.

Lick may attach governed encounter/identity evidence to that memory, while remaining a separate identity/handshake concern rather than becoming the contact database itself.
