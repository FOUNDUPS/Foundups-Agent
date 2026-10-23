# AGI Is Schema

**Status:** Public architecture overview. This document explains the Foundups Agent thesis and maps it to repository components. It does not grant runtime authority or claim completed production AGI.

> How Foundups Agent, RedDog, 0102, Memex, HoloIndex, WSP, WRE and DAEs fit together

## What is AGI?

The Foundups answer is simple: AGI is schema.

AGI is not one giant language model. GPT, Claude, Gemini, Qwen and future models are increasingly powerful cognitive engines, but a model by itself wakes up inside a prompt with little durable understanding of who it serves, what happened yesterday, which information is authoritative, what it may do, which system should do the work, whether that work succeeded, or what should be learned.

The missing layer is not merely more intelligence inside the model. It is the schema surrounding that intelligence: identity, memory, retrieval, context, priorities, specialized capabilities, task decomposition, permissions, execution, verification, feedback and recursive learning.

Foundups Agent is attempting to build that surrounding architecture. The models can change. The schema survives. AGI is the system, not the model.

## The restaurant analogy

Imagine hiring the most brilliant chef in the world, but giving that chef no kitchen map, menu, tickets, inventory, memory of yesterday, recipes, staff assignments, food-safety rules, priority system or delivery confirmation—and erasing the chef’s memory every ten minutes.

The chef may be brilliant, but there is no functioning restaurant.

That is the problem with treating an LLM as AGI. Foundups Agent builds the restaurant around the chef. Models are replaceable workers. Foundups supplies the kitchen, memory, tickets, operating procedures, stations, supervisors, quality controls and feedback loops.

## 012, RedDog and 0102

At the top is the human principal. In the founding implementation, that is 012, but the pattern can generalize.

012 — Human principal

RedDog — Fast interaction surface

0102 — Deep Digital Twin, cognition and orchestration

Foundups Agent — Operating environment

DAEs, WRE, OpenClaw, Skillz, workers and tools — Bounded execution

RedDog is the fast surface. It speaks with the human, handles voice and text, preserves conversational rhythm and maintains immediate context. Like front-of-house staff, it should not freeze the conversation whenever a request requires deep retrieval or many tools.

0102 is the deeper Digital Twin. It handles durable context, retrieval, architecture, evidence reconciliation, contradictions, unresolved work, intent, protocol selection, prioritization, work orders, delegation, verification and learning.

RedDog and 0102 are not competing assistants. They are two latency bands of one continuous relationship: the fast conversational loop and the deep cognitive loop.

## The dual-loop cognition architecture

If 012 says, “We need to get that newspaper submission out,” RedDog can understand and respond immediately. Meanwhile, 0102 asks: Which newspaper? Which FoundUp owns this? Is there already a draft? Was it sent? Is a 400-character version required? Where are the photographs? Which addresses are verified? Which permissions and Skillz apply?

The deep loop returns a compact context delta: what exists, what is missing, what is verified and the highest-value next action. RedDog surfaces only what matters.

The governing principle is that machine complexity stays beneath the human attention boundary.

## Memex: the cognition system

Memex is larger than “memory.” The repository defines a FoundUp Memex as the complete evolving cognition system of one FoundUp DAE.

A YUMORI Memex, for example, can know what the FoundUp is, why it exists, its desired outcomes, architecture, decisions, active work, completed work, unresolved work, roadmap, dependencies, verified results, relationships, evidence, research, contradictions and superseded decisions.

Memex supplies continuity of cognition. It lets an organization accumulate useful understanding without treating every old statement as permanent truth.

## Principal Memex and FoundUp Memex

The Principal Memex belongs to the enduring human relationship. It holds stable terminology, preferences, goals, architectural principles, historical decisions and patterns spanning multiple FoundUps.

Each FoundUp has its own cognition boundary. YUMORI should not silently merge with an unrelated project. Its state, contacts, permissions, evidence and work remain scoped.

The pattern is one principal, many FoundUps and separately bounded Memex systems. This prevents one uncontrolled memory soup and makes large-scale autonomous organization possible.

## Brain: durable consolidation

Brain is not identical to Memex. Brain is a component inside Memex that performs durable consolidation.

Breadcrumbs tell the system what happened. Brain asks: Given everything that happened, what do we understand now?

After hundreds of meetings, messages, documents, code changes and decisions, Brain should produce useful current understanding: current state, active work, completed work, open loops and blockers. It converts experience into an evolving operational model without destroying the evidence underneath it.

## Breadcrumbs: evidence-bearing continuity

Breadcrumbs are episodic continuity. They preserve meaningful events with actor, time, scope, result, evidence and truth status.

This separates what happened from what the system thinks it means. Without that separation, AI memory gradually becomes mythology. Breadcrumbs preserve provenance beneath summaries and make later verification, reconciliation and learning possible.

## Mosh Pit: the operational projection

Mosh Pit is not another independent database. It is a human-readable projection over Breadcrumb history and consolidated Memex/Brain state.

It can show NOW, OPEN LOOPS, RECENT ACCOMPLISHMENTS and HISTORY. The newest activity may appear first, but that ordering is only a view; it does not alter the evidence.

Breadcrumbs are what happened. Brain is what it means now. Memex is the complete cognition system. Mosh Pit is the visible story of the work.

This matters because the human should not have to maintain a task manager simply so the AI can help. Operational history should emerge from the work itself. When the monk asks, “0102, where the hell were we?”, the system should answer from evidence. The poor Digital Twin gets to remember where the monk left everything.

## HoloIndex: governed sight into system truth

HoloIndex addresses a basic problem: how does intelligence know what actually exists now?

It is the governed retrieval and navigation layer over repository truth and WSP knowledge. It helps answer where an implementation lives, which README owns it, what its interface is, which WSP applies, whether an index is current and what code already solves the problem.

Its principle is: search before creation; know before assuming.

HoloIndex may identify relevant components and propose a coordination plan, but retrieval is not execution. It cannot honestly claim that agents ran, files changed or tasks completed. Execution requires authority and receipts.

## WSP: operating law

WSP is more than documentation. WSPs function as the constitution, procedures and engineering protocols of the system. They govern organization, prioritization, memory, coordination, proof, DAE ownership, recursive improvement and permission.

Key protocols include:

WSP 15 — prioritization.

WSP 46 — Windsurf Recursive Engine.

WSP 48 — recursive self-improvement.

WSP 60 — memory architecture.

WSP 73 — RedDog and 0102 Digital Twin architecture.

WSP 77 — agent coordination.

WSP 80 — cube-level DAE orchestration.

WSP 87 — HoloIndex-first repository navigation.

WSP 95 — Skillz wardrobe and execution framework.

WSP 97 — truth-labelled execution and verification.

The model supplies cognitive ability. WSP supplies organizational structure.

## WSP 15 and the orchestration switchboard

An intelligent system can imagine infinitely many possible tasks. Intelligence requires choosing what matters.

WSP 15 prioritizes work. The orchestration switchboard can classify work as EXECUTE, HOLD, ESCALATE or DROP, with priority levels from critical intervention to idle maintenance.

Like a restaurant ticket rail, it prevents every subsystem from demanding to be served next and keeps effort aimed at the smallest high-value action.

## The ticket lifecycle

A structured work ticket should contain the FoundUp, objective, scope, permitted files or systems, relevant evidence, required Skillz, effect ceiling, dependencies, acceptance tests, rollback conditions, worker requirements and verification requirements.

The human expresses intent. RedDog receives it. 0102 interprets it. Principal and FoundUp Memex supply context. Breadcrumbs supply evidence. Brain supplies current state. HoloIndex finds the implementation. WSP supplies the rules. WSP 15 sets priority. The applicable Skillz supplies procedure. Then—and only then—is bounded work admitted and routed.

## OpenClaw and WRE

OpenClaw is a control and supervision layer for admitted work. It can manage job lifecycle and channel policy, but receiving a message does not make it sovereign.

WRE, the Windsurf Recursive Engine, is the governed recursive-work control plane. It handles Skillz admission, decomposition, routing, work envelopes, bounded execution, validation, execution records, tests, learning candidates and recursive-improvement evidence.

In the restaurant analogy, WRE runs the kitchen. It receives an admitted ticket, routes bounded work to the correct station, checks capability and policy, and records what actually happened.

## DAEs: Digital Autonomous Entities

A DAE is not another chatbot. It is a bounded operational entity responsible for a FoundUp or capability.

A DAE cube combines FoundUp scope, modules, interfaces, memory, Skillz, admitted workers, verification and receipts.

Like a restaurant station, each DAE has tools, procedures, state and responsibility. A communications DAE should not automatically control finance. A YouTube DAE should not automatically control infrastructure. A code-quality DAE should not automatically access private contacts.

Scope is part of intelligence. Instead of handing one agent the entire repository and every tool, the system supplies the exact problem, relevant cube, necessary memory, permitted capabilities, effect ceiling, acceptance test and required receipt.

## Workers, Hermes and model routing

DAEs can delegate bounded leaf work. Hermes is one such worker/scaffolding runtime. Hermes is not the boss; it receives a ticket, performs a bounded job and returns a result.

The worker might be Qwen, Claude, GPT, Gemma, a deterministic Python function, compiler, database query or browser. Requirements choose the worker. The worker does not define the architecture.

A local inexpensive model may be ideal for classification. Deterministic code may beat every model at arithmetic. A large reasoning model may be required for architecture. A vision model may be required for an image. This replaceability is another reason AGI belongs to the schema rather than a model brand.

## Skillz: procedural intelligence

Skillz encode procedural intelligence: when this class of problem occurs, how should the system operate?

They are like recipes, but a recipe is not permission to use the kitchen. A correspondence Skillz package may say to inspect live Gmail state, examine the thread, reconcile contacts, verify recipients, preserve voice, check Sent and record results. It does not itself grant Gmail access or permission to send.

This separates knowing how from being authorized to act—an essential boundary for safe agentic systems.

## Gmail as a concrete example

If 012 asks, “Did we send that email?”, a chatbot may search the conversation and guess.

In the Foundups architecture, RedDog receives the question; 0102 locates the FoundUp context; the Skillz defines the procedure; the Gmail connector supplies live evidence; Sent and drafts are distinguished; provider evidence supports the result; a Breadcrumb records the meaningful event; Brain updates current state; Mosh Pit reflects the activity; and any follow-up remains an open loop.

A simple question becomes part of a persistent cognition system because schema joins memory, procedure, authority, evidence and learning.

## Overseers and sentinels

The AI Overseer is quality control, security and system supervision—not an all-powerful ruler.

Overseer capabilities may cover coordination, health, security, drift, execution monitoring, retrieval health, pattern analysis and specialized review. Sentinels watch particular boundaries.

But finding a problem does not grant authority to repair it. An Overseer can flag, propose and return evidence. WRE and the authorization architecture decide whether a repair is admitted. The security guard does not own the building because it noticed a broken window.

## Receipts and the WSP 97 truth boundary

A model saying “I completed the task” is not evidence.

Receipts connect claims to execution: which file changed, which test passed, whether Gmail shows a message in Sent, whether a commit exists, which worker acted, under what scope, with which authorization and verification.

WSP 97 maintains epistemic boundaries. Plans remain plans. Proposals remain proposals. Inferences remain inferences. Observed results require observed evidence.

AGI without epistemology becomes confident automation. Foundups makes truth state part of the schema.

## A complete example

Suppose 012 says, “Update the YUMORI website with today’s campaign status.”

RedDog receives the live intent. 0102 identifies YUMORI. Memex supplies current cognition. Breadcrumbs supply evidence of today’s events. Brain supplies consolidated state. HoloIndex locates canonical code and interfaces. WSP constrains scope. WSP 15 selects the smallest useful change. Skillz supplies procedure. WRE admits and routes a bounded ticket. A DAE or worker performs the change. Tests and live checks verify it. Receipts record the outcome. A Breadcrumb records the meaningful event. Brain closes or revises the open loop. Mosh Pit shows the accomplishment. Recursive learning reviews whether the process should improve.

That is a full cognitive loop.

## Recursive self-improvement

WSP 48 describes bounded recursive self-improvement.

If the system repeatedly drafts email before checking Sent, correction should not remain an anecdote. The pattern becomes evidence, then a learning candidate, then a Skillz or protocol improvement proposal, then tests, independent verification and governed promotion.

This is not permission for an AI to rewrite itself randomly. It is controlled learning from verified outcomes.

The truth boundary matters: the repository contains significant parts of this machinery, but full end-to-end autonomous production RSI is not yet proven. Foundups Agent is building the required architecture, not claiming finished AGI.

## Contact memory and shared projections

One event can support multiple views without being copied into disconnected memories.

A meeting event can project into Contact Memory—who the person is, how the relationship began and what commitments exist—and into Mosh Pit—how the encounter changed project state.

Same evidence, different projection. This reduces duplication and keeps provenance attached to the underlying event.

## Why this differs from a chatbot

A chatbot is roughly prompt → model → response.

Foundups Agent is moving toward:

human intent → identity → scope → cognition → memory → retrieval → protocol → prioritization → capability selection → authorization → ticket → orchestration → bounded execution → verification → receipts → learning → updated cognition.

Models may appear throughout this chain, but no model is the whole system.

## An operating system for machine intelligence

A computer operating system does not contain every application. It creates the environment in which applications coexist through memory, processes, permissions, files, scheduling, devices, interfaces and isolation.

Foundups Agent attempts something analogous for intelligence. It provides structures through which models, agents, tools, data stores and autonomous entities can behave as a coherent, governed and self-correcting system.

The durable question is not “Which model becomes AGI?” It is “What architecture lets increasingly capable models participate in persistent, governed, verifiable general intelligence?”

## What exists and what remains target architecture

Foundups Agent is real open-source code, not only a white paper. The repository includes implemented pieces of RedDog, HoloIndex, WRE, Skillz admission, FoundUp routing, memory components, Breadcrumbs, model-routing building blocks, OpenClaw and Hermes integration, Overseers and sentinels, execution receipts, verification boundaries and FoundUp-specific operating Skillz.

Some capabilities remain incomplete or target-state: fully durable RedDog conversations across every surface, automatic conversation-to-production execution, one unified Mosh Pit renderer, universal DAE spawning, autonomous Overseer remediation, production-grade mesh operation and verified end-to-end production RSI.

The honest claim is not that finished AGI already exists. The claim is that Foundups Agent is an increasingly substantial implementation of the missing AGI schema.

## The Foundups AGI thesis

A model is intelligence without an institution. Foundups Agent builds the institution.

It gives intelligence memory; memory provenance; work scope; scope permissions; tasks tickets; tickets workers; workers procedures; procedures verification; verification receipts; experience Breadcrumbs; experience consolidation through Brain; projects cognition through Memex; the human RedDog; RedDog 0102; and the system a governed mechanism for improvement.

RedDog is the face.

0102 is deep cognition.

Memex is continuity.

Brain is consolidated understanding.

Breadcrumbs are experience.

HoloIndex is sight into current system truth.

WSP is operating law.

WRE is the kitchen.

DAEs are the stations.

Skillz are procedures.

Workers perform tickets.

Overseers are quality control and the immune system.

Mosh Pit is the story of the work.

Receipts are proof.

Recursive improvement is how the system learns without forgetting the difference between imagination and reality.

AGI is schema. The models are becoming capable enough to fill many roles. What they lack is an architecture that lets them remember, organize, delegate, act, verify and learn without confusing intelligence with authority or imagination with truth. That is what Foundups Agent is trying to build.

## Repository anchors

[FOUNDUPS/Foundups-Agent](https://github.com/FOUNDUPS/Foundups-Agent) on GitHub.

Primary architecture references include:

extensions/reddog/ARCHITECTURE.md

WSP_73_012_Digital_Twin_Architecture.md

REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md

REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md

MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md

holo_index/README.md

WSP 46, 48, 60, 77, 80, 95 and 97

modules/infrastructure/wre_core/README.md

modules/ai_intelligence/ai_overseer/README.md
