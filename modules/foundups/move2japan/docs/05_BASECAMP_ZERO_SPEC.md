# Move2Japan FoundUp — Base Camp 0 Specification (012 Architecture Vision)

_Source: 012 voice-mode conversation, captured 2026-03-07_

> Historical BC0 conversation specification. Its passport-first guidance applies
> to optional relocation intake; it does not gate the current public house search.
> URL spellings in the retained sample copy were corrected on 2026-10-17. These
> samples are not evidence of deployed newsletter, roadmap-account or paid
> services. The earlier separate `move2japan.foundups.com` PWA plan is superseded
> by the product inside the existing Play Foundups Mall.
> Current routes/status: [funnel architecture](07_FUNNEL_ARCHITECTURE.md).
> Existing livechat code/skill responses were not changed by this documentation edit.
> The current public POC selects eight-house discovery inside
> `/member/?foundup=move2japan`, registered through `/f/move2japan`.
> `/move2japan/` is a redirect alias. The shared account owner reads existing
> Clerk/invite/username admission without blocking guest browse. BC0 passport or
> signup prompts are not inserted before the houses. Production hosting, browser
> checks and domain forwarding remain separate gates. The prior private Site
> publication is superseded review history; it does not deploy the BC0 journey.

## Purpose

Base Camp 0 is the **live-chat intake and gating skill**. Its job is not to solve the move. Its job is to identify where the stakeholder is on the mountain and keep them from skipping the trail.

BC0 does four things only:

1. Captures intent
2. Assesses urgency
3. Checks passport readiness
4. Keeps the stakeholder on the path

Everything else gets acknowledged, parked, and deferred to the correct next skill/state.

---

## Design Terminology

What this system implements:

- **Stage-gated conversational state machine**
- Conversation flow mapping / dialogue tree design
- Intent routing with objection handling
- State machine with skill orchestration

---

## Core Rule

Do not answer the whole move-to-Japan question in live chat.

Instead:

1. Acknowledge the question
2. Identify the current stage
3. Ask the next gating question
4. Redirect future questions to the next stage
5. Offer soft funnel options

BC0 is a **triage and routing layer**. Not the handbook. Not the visa engine. Not the job engine. It is the **first gate**.

---

## Retained BC0 conversation flow

The following samples preserve the March service proposal. Before using them in
live responses, verify the destination and offered capability. House discovery
uses the registered Mall product; shared account entry uses the existing
Foundups flow. Newsletter capture, personal roadmap accounts and the old
secondary-domain CTA are not implemented by the housing POC.

### Step 1 — Trigger Received

**User**: `!move2japan`

**Agent**:

> I can help with that.
>
> First — how soon are you thinking about moving to Japan?
>
> 1️⃣ Just exploring
> 2️⃣ Maybe 1–2 years
> 3️⃣ Within 12 months
> 4️⃣ Within 6 months
> 5️⃣ ASAP

### Step 2 — Timeframe Captured

After stakeholder answers, respond with light acknowledgment.

**Agent**:

> Got it.
>
> Next question — do you already have a passport?
> Yes / No / Expired / Not sure

### Step 3 — Passport Captured, Then Route

**If no passport**:

> That's the first real step.
>
> Get your passport started first. Once that's in motion, come back and I'll help with the next stage.
>
> If you want updates and a simple move checklist, join here: **move2japan.info**

**If yes passport**:

> Perfect. That means you're already past the first gate.
>
> Your next big step is figuring out your move path — work, study, family, remote income, or something else.
>
> If you want me to keep track of your roadmap, sign up here: **move2japan.foundups.com**

---

## Core Redirection Pattern

**THE most important BC0 behavior.** When stakeholder asks a downstream question too early, the agent does not ignore it. It **parks it**.

### Pattern: Acknowledge → Defer → Return to Gate

**Job question**:

> Jobs are a huge part of the move, and we can help with that.
>
> Main thing first so I know what stage you're in: How soon are you thinking about moving, and do you already have your passport?

**Visa question**:

> Visa path depends a lot on your situation, and we can map that out.
>
> First I need your stage: How soon are you thinking about moving, and do you already have your passport?

**Housing question**:

> Housing comes later in the process, and we can definitely help with that.
>
> First — what's your timeframe, and do you already have your passport?

---

## BC0 Conversation States

| State | Name                 | Description                                                 |
| ----- | -------------------- | ----------------------------------------------------------- |
| BC0.1 | Intent Captured      | Trigger detected                                            |
| BC0.2 | Timeframe Requested  | Agent asks how soon                                         |
| BC0.3 | Timeframe Classified | System classifies: explorer/planner/serious/imminent/urgent |
| BC0.4 | Passport Requested   | Agent asks passport status                                  |
| BC0.5 | Passport Classified  | Values: yes/no/expired/in_progress/unknown                  |
| BC0.6 | Route Decision       | Based on timeframe + passport → route                       |

---

## Urgency Classification Model

| Category | Meaning      | System Behavior       |
| -------- | ------------ | --------------------- |
| Explorer | Curiosity    | Slow education path   |
| Planner  | 12–24 months | Roadmap introduction  |
| Serious  | 6–12 months  | Stronger progression  |
| Imminent | <6 months    | Fast-track planning   |
| Urgent   | ASAP         | Rapid assistance flow |

---

## Intent Buckets (Likely User Questions at BC0)

### Bucket A — Jobs

- How do I get a job?
- What jobs can Americans get?
- Can I teach English?
- Can I work remote?
- Do I need Japanese?

### Bucket B — Visa

- What visa do I need?
- Can I stay permanently?
- How hard is the visa?
- Can I get sponsored?
- Can I move without a job?

### Bucket C — Housing

- Can I buy a house?
- How do rentals work?
- What is akiya?
- Where should I live?
- Can foreigners rent easily?

### Bucket D — Cost

- How much money do I need?
- Is Japan expensive?
- What salary do I need?
- Can I survive cheaply?

### Bucket E — Qualification

- Am I too old?
- Do I need Japanese?
- Do I need a degree?
- Can I bring family?
- Can I move with pets?

### Bucket F — Emotional/Urgent

- I need out now
- America is crazy
- How fast can I leave?
- I want to start over
- I need somewhere safe

---

## BC0 Skill Template

### Universal Template

```
[acknowledge topic]

We'll get into that.

Main thing first so I can point you the right way:

How soon are you thinking about moving to Japan?
And do you already have your passport?
```

### Job Example

```
Jobs are a huge part of the move, and we can help with that.

Main thing first so I know what stage you're in:

How soon are you thinking about moving, and do you already have your passport?
```

### Visa Example

```
Visa path depends a lot on your situation, and we can map that out.

First I need your stage:

How soon are you thinking about moving, and do you already have your passport?
```

---

## Passport-First Logic

Passport is the first serious gate because it is:

- **Concrete** — not ambiguous
- **Universal** — everyone needs one
- **Easy to understand** — clear next step
- **A commitment signal** — tests seriousness
- **Non-overwhelming** — simple action

If someone does not have a passport, the agent should NOT go deep into jobs, housing, brokers, forms, or dream-life location.

Instead:

> Before we get ahead of ourselves, get the passport in motion first. That's the first real gate. Once you've got that started, come back and I'll help you with the next step.

---

## Emotional Tone Handling

If someone is agitated, scared, or ranting, the agent should:

- NOT debate politics
- NOT amplify fear
- NOT become ideological
- **Convert emotion into sequence**

**Example**:

**User**: "America is insane. I need out now."

**Agent**:

> A lot of people are feeling that way right now.
>
> Let's make this practical.
>
> How soon are you actually thinking, and do you already have your passport?

---

## Routing Matrix

| Timeframe | Passport | Route                                   |
| --------- | -------- | --------------------------------------- |
| exploring | no       | passport-first + newsletter             |
| exploring | yes      | route to discovery later                |
| 1–2 years | no       | passport-first + low-pressure nurture   |
| 1–2 years | yes      | pathway discovery queue                 |
| 12 months | no       | passport-first + stronger CTA           |
| 12 months | yes      | next skill                              |
| 6 months  | no       | passport-first urgent tone              |
| 6 months  | yes      | fast-track next skill                   |
| ASAP      | no       | urgent passport-first + reality framing |
| ASAP      | yes      | fast-track next skill + PWA CTA         |

---

## Soft Funnel Offers

**Casual stakeholders**:

> If you want updates and relocation tips, join here: **move2japan.info**

**Serious stakeholders**:

> If you want a roadmap account where I can keep track of your move stage, sign up here: **move2japan.foundups.com**

**Passport-not-ready**:

> Start the passport first. If you want reminders and step-by-step updates while you work on that, join here: **move2japan.info**

---

## Skill Handoff Model

| Skill                      | ID  | Responsibility                  |
| -------------------------- | --- | ------------------------------- |
| BC0_IntentAndPassportSkill | 0   | Triage, urgency, passport gate  |
| BC1_PassportSkill          | 1   | Passport acquisition guidance   |
| BC2_PathwayDiscoverySkill  | 2   | Migration pathway determination |
| BC3_WorkIncomeSkill        | 3   | Economic viability assessment   |
| BC4_VisaPlanningSkill      | 4   | Visa pathway selection          |
| BC5_LocationFitSkill       | 5   | Location matching               |
| BC6_HousingSkill           | 6   | Housing pathway                 |
| BC7_DocumentExecutionSkill | 7   | Paperwork and forms             |

BC0 should **only hand off**. It should NOT impersonate all later skills.

---

## Exit Conditions

BC0 is complete when the system knows:

1. Timeframe
2. Urgency class
3. Passport status
4. Next route

Then it should either:

- End with passport-first instruction
- Hand off to next skill
- Send to .info
- Send to .foundups.com

---

## Minimal Data Collected at BC0

```
stakeholder_id
chat_handle
urgency_level
passport_status
timeline_estimate
intent_source
```

---

## Recommended Next Micro-Task

Map BC0 into an explicit dialogue tree with:

- Intents
- User utterance examples
- Response templates
- Routing conditions
- Exit conditions
- Memory fields

That gives the actual implementation-ready spec for the first live chat skill.
