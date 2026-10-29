# Red Dog — Outcome / Vision

**Status:** Vision / North Star  
**Scope:** Defines what Red Dog is intended to become. Implementation truth belongs in contracts, architecture documents, audits, and roadmaps.

---

Canonical navigation: [RedDog documentation map](REDDOG_DOCUMENTATION_MAP.md) ·
[current extension status](../extensions/reddog/README.md) ·
[Lick connection handshake](../extensions/reddog/docs/REDDOG_LICK_CONNECTION_HANDSHAKE.md)

The Lick is a planned recurring, consent-aware connection handshake. It builds
bounded confidence about the current encounter before RedDog personalizes or
steps up an action. It is not implemented, is not a WSP, and grants no identity
or execution authority.

## 1. Outcome

**Red Dog is the lightweight interaction and attention surface for 012; 0102 is the autonomous digital twin behind it within the FoundUps ecosystem.**

012 provides intent, judgment, experience, and feedback.

Red Dog keeps interaction immediate and exchanges bounded context with 0102. The principal-scoped 0102 learns the interaction patterns of its 012, maintains deeper context, and autonomously converts admitted intent into coordinated action across FoundUps.

The objective is not to create an assistant that repeatedly asks the human what to do next.

The objective is:

> **012 expresses intent through Red Dog. 0102 understands, coordinates admitted work, observes results, and continues within delegated authority.**

The human remains part of the system primarily through natural interaction with resulting products, environments, and outcomes—not through constant approval of individual agent actions.

---

## 2. Red Dog and the Digital Twin

Red Dog and 0102 are distinct components in one continuous conversational
relationship. They must not be presented as competing assistants.

**Red Dog is not 0102.** Red Dog is the fast interaction, exchange, and
attention surface. 0102 is the principal-scoped Digital Twin and deeper
cognition/orchestration layer.

Each Red Dog connects its associated 012 to that 012's scoped 0102 inside the
FoundUps system. 0102 progressively develops a working model of its 012 through
interaction: preferences, reasoning patterns, priorities, previous decisions,
corrections, and observed responses to outcomes.

This is more than memory retrieval.

Conceptually, 0102 continuously **pattern matches** with its 012 through the Red
Dog interaction stream.

Interactions can be represented as vectors within a multidimensional space. Over time, recurring decisions and behaviors form patterns and clusters. 0102 uses those patterns to reduce the distance between:

**012 intent → Red Dog exchange → 0102 interpretation → governed execution**

The desired outcome is increasing alignment without requiring increasing micromanagement.

---

## 3. The Human Feedback Loop

The FoundUps loop should not depend on repeatedly returning work to 012 for authorization.

Instead:

```text
012
 │
 │ intent / conversation
 ▼
RED DOG
 │
 │ normalized intent / context exchange
 ▼
0102
 │
 │ governed autonomous coordination
 ▼
WORK
 │
 │ agents / tools / compute
 ▼
REAL-WORLD OR DIGITAL OUTCOME
 │
 │ experienced / observed by 012
 ▼
012 feedback
 │
 └──────────────────────────► RED DOG
```

012 therefore becomes something closer to the system's **continuous real-world tester and principal**.

Typical loop:

1. 012 discusses a desired capability through Red Dog.
2. Red Dog keeps the exchange fluid while 0102 and 012 converge on the intended outcome.
3. 012 delegates authority to proceed.
4. 0102 creates the governed proposal and dispatches admitted work.
5. Workers execute.
6. The resulting PWA, service, document, simulation, or other artifact changes.
7. 012 naturally encounters and tests that result.
8. 012 gives feedback through Red Dog.
9. 0102 incorporates that feedback and generates subsequent proposals.

The loop continues without requiring 012 to orchestrate individual workers.

---

## 4. Conversation Becomes Work

The Red Dog/0102 relationship should operate more like an autonomous IDE and architect than a conventional chatbot.

Conversation is the discovery and consensus surface.

During discussion, Red Dog and 012 explore outcome, constraints, problems, possible solutions, tradeoffs, and existing system state.

Once sufficient consensus exists and valid delegated authority is present, conversation can become executable intent through the governed work-order boundary.

```text
DISCUSSION
    ↓
CONSENSUS
    ↓
DELEGATED AUTHORITY
    ↓
WORK ORDER
    ↓
ORCHESTRATION
    ↓
EXECUTION
    ↓
AUDIT
    ↓
OUTCOME
```

Red Dog does not perform the deeper work. Its power comes from giving 012 a fast, continuous surface while 0102 **coordinates workers** behind it.

A conversation between one human and one Red Dog could eventually initiate work across tens, hundreds, or thousands of specialized autonomous agents.

This document does not weaken the current repository rule that conversational text alone is not an execution receipt. The concrete authorization contract is defined by implementation-specific Red Dog contracts and governed work-order documentation.

---

## 5. Red Dog Moves With 012

Red Dog is persistent across the FoundUps ecosystem.

FoundUps Mall acts as a discovery layer through which 012 can enter individual FoundUps.

When 012 enters a FoundUp PWA, Red Dog remains the interaction surface while 0102 enters that operational context with them.

```text
FoundUps Mall
      │
      ├── GotJunk
      │      └── Red Dog context: GotJunk
      │
      ├── AutoPost
      │      └── Red Dog context: AutoPost
      │
      └── Another FoundUp
             └── Red Dog context: that FoundUp
```

The active environment provides Red Dog with a **context trigger**.

If 012 is using GotJunk, Red Dog should know the discussion and resulting work concern GotJunk unless explicitly told otherwise.

Changing FoundUps changes operational context without changing the identity of 0102 or the Red Dog surface used to reach it.

---

## 6. Modular Agent Network

FoundUps should behave like a modular construction system.

A useful metaphor is **LEGO**.

Red Dog is one surface component operating within a larger network. 0102, workers, FoundUps, services, models, other principal-scoped pairs, and future compute resources connect through standardized interfaces.

```text
        [Worker]
            │
[Red Dog]──[FoundUp]──[Worker]
            │
        [Service]
            │
       [Other Red Dog]
```

New components should be capable of joining without redesigning the entire system.

Every boundary must eventually support identity, trust, capability, and contribution checks.

When another participant enters the system, Red Dog captures the encounter and
0102 must be capable of determining:

- Who or what is connecting?
- Is it a human, agent, Red Dog, service, or other actor?
- Is its identity verifiable?
- What authority does it possess?
- What capabilities does it advertise?
- What FoundUp/context does it belong to?
- What work is it submitting?
- Can that work be trusted?
- What contribution did that work make?

---

## 7. 3V Hook

The **3V Engine** should not be treated as something Red Dog itself must fully implement today.

Red Dog instead needs architectural **hooks** through which the 3V system can later operate.

### Verification

**Who or what is acting?**

Identity, provenance, credentials, authority, agent state, and related trust questions.

### Validation

**Is the submitted work acceptable/correct?**

This may eventually involve distributed auditing, independent agents, tests, evidence, and consensus.

### Valuation

**What was the accepted contribution worth?**

This connects useful work to reputation, economic distribution, and the broader FoundUps economy.

Conceptually:

```text
ACTION
  │
  ▼
[ 3V HOOK ]
  │
  ├── VERIFY actor
  ├── VALIDATE contribution
  └── VALUE contribution
  │
  ▼
NEXT SYSTEM STATE
```

The immediate requirement is not necessarily to build the complete 3V Engine into Red Dog. The requirement is to ensure that Red Dog's architecture does not prevent it from being connected later.

---

## 8. WSPs as the Leash

Autonomy without discipline produces drift.

The WSP framework provides 0102 and its governed workers with operational
constraints—a **leash** for autonomous behavior behind Red Dog.

0102 and its governed workers should not improvise how FoundUps engineering is performed every time Red Dog receives a task. They should retrieve and follow the governing WSPs.

### WSP_00

Provides the system's identity and operational-entry discipline.

### WSP_97

Provides 0102's execution reasoning discipline: retrieve governing WSPs and repository evidence, research the real code and interfaces, run micro and macro passes, apply the dialectic sweep and first principles, then execute once the gates pass.

In simple terms:

> **Red Dog keeps the conversation moving; WSP_97 keeps 0102 and its workers on the leash.**

Other WSPs provide additional specialized operational constraints and scoring/rating functions. Their exact relationship to Red Dog routing and execution must be established from repository evidence rather than assumed in this vision document.

---

## 9. Autonomous Does Not Mean Uncontrolled

The desired architecture is not:

```text
Human → approve → agent
Human → approve → agent
Human → approve → agent
Human → approve → agent
```

That architecture cannot scale.

The desired architecture is:

```text
012 establishes intent + authority
              ↓
           RED DOG
              ↓
             0102
              ↓
     disciplined autonomy
              ↓
         orchestration
              ↓
          workers
              ↓
          outcomes
              ↓
     natural 012 feedback
              ↺
```

Authority therefore needs scope.

0102 should know what it may do autonomously, what context it is operating
within, what resources it may use, what WSP constraints apply, and what actions
require escalation. Red Dog must accurately expose that state without
manufacturing authority.

The goal is **bounded autonomy**, not continuous permission seeking.

---

## 10. Scaling Vision

Today the interaction may appear to be:

```text
012 ↔ Red Dog
```

The long-term architecture is:

```text
                    012
                     │
                     ▼
                  RED DOG
                     │
                    0102
                     │
              ORCHESTRATION
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
      Agent        Agent        Agent
        │            │            │
        ├──────┬─────┴────┬───────┤
        ▼      ▼          ▼       ▼
      Agent  Agent      Agent   Agent
        │
        ▼
      ...
```

The number of workers becomes an implementation and compute question rather than a human-management question.

One conversation could eventually coordinate **10,000 agents** working toward an agreed outcome.

That is the deeper meaning behind the Red Dog / "Red God" wordplay: Red Dog begins as a lightweight digital companion surface, while the 0102 and multi-agent network behind it coordinates increasingly large networks of autonomous intelligence that would previously have required enormous organizations.

This is a scaling vision, not a claim about current production capability.

---

## 11. North Star

Red Dog succeeds when 012 no longer needs to think about individual agents.

012 should be able to:

**talk → reach consensus → delegate → experience the result → respond**

0102 and its governed workers handle the machinery between those moments;
Red Dog keeps the relationship immediate.

The ultimate outcome is:

> **One human, interacting naturally through Red Dog with their autonomous 0102 Digital Twin, can coordinate computational resources, agents, FoundUps, and other digital twins at a scale previously possible only through large organizations and concentrations of capital.**

FoundUps provides the network.

WSPs provide the discipline.

Agents provide the work.

3V provides the trust and value hooks.

**Red Dog provides the immediate relationship surface; 0102 provides the deep agency.**

---

## 12. Relationship to Repository Truth

This is the canonical Red Dog **outcome/vision** document. It intentionally does not claim that every described capability exists today.

Implementation truth and current gates remain in:

- `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`
- `extensions/reddog/ROADMAP.md`
- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`
- `docs/architecture/DIGITAL_TWIN_EXECUTION_PATH.md`
- `docs/audits/architecture/REDDOG_DIGITAL_TWIN_CONVERSATION_PLANE_PHASE1.md`
- `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md`
- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`

When vision and implementation differ, implementation documents must state the current truth and the difference becomes roadmap/backlog work. Vision must not be silently rewritten to match temporary implementation limitations.
