---
name: yumori_work_orchestrator
description: Convert 012/Red Dog YUMORI planning conversations into a verified, deduplicated, WSP 15-ranked backlog and bounded ChatGPT Work / RedDog handoff, including a governed capital-network expansion workflow.
version: 0.2.1
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.99
domain: foundup_campaign_operations
category: workflow
wsp_chain: [WSP_00, WSP_15, WSP_22, WSP_50, WSP_77, WSP_95, WSP_97]
evals:
  - live_state_before_backlog
  - duplicate_and_supersession_detection
  - wsp15_ranked_work_items
  - physical_vs_machine_owner_separation
  - work_handoff_gate
  - capital_network_warm_path_expansion
  - no_parallel_backlog_authority
  - truth_boundary_preserved
  - resident_memory_reconstruction
  - autonomous_gmail_triage
  - partner_discovery_dedup
  - retained_rsi_improvement
---

# YUMORI.me verified work orchestrator

## Purpose

Turn the natural planning conversation between 012 and Red Dog/0102 into executable
campaign work without making chat memory the project-management system.

Canonical flow:

```text
012 conversation
  -> WSP_00 identity / role / origin lock
  -> WSP_97 retrieval + evidence reconciliation
  -> current-state / duplicate / supersession pass
  -> typed work items
  -> WSP_15 scoring
  -> owner separation
  -> verified backlog preview
  -> existing RedDog governed-work authorization
  -> ChatGPT Work / bounded worker handoff
  -> receipts + source-of-truth reconciliation
```

This skill is the YUMORI domain adapter. It does not create a new executor, signer,
chat database, contact database, fundraising CRM or project queue.

## Canonical evidence owners

Reconstruct current state before every planning/execution cycle from:

1. current repository README/ROADMAP/ModLog/Skillz;
2. YUMORI Moshpit for campaign history;
3. 0102 Moshpit for agent learning/failures only;
4. Gmail + native correspondence state + Contacts / Email Log / Action Queue /
   Correspondence Routing for correspondence;
5. the existing CONTACTS workbook for stakeholder, LinkedIn and capital relationships;
6. current Drive 03/05/06/07, legal/admin/accounting and canonical FIN;
7. current official government, utility and market sources;
8. current connected-app state for LinkedIn, Calendar, Drive and other relevant systems.

Never infer "not done" from absence in chat. Never turn a stale backlog row into authority
for an external effect.


## Delegated 0102 operating mode — 2026-10-26

The principal delegates partner research, Japanese stakeholder coordination, Gmail
triage and continuity recovery to 0102. Read the canonical
[`YUMORI_RESIDENT_0102_OPERATOR_HANDOFF_20261026.md`](../../docs/YUMORI_RESIDENT_0102_OPERATOR_HANDOFF_20261026.md)
before proposing a resident cycle or external message. It defines distinct truthful
AI-operator versus human/committee voices, budgets, privacy, and acceptance gates.
This **does not** certify an installed or running service. Existing #1779 autonomous
sender HOLD and all other effect boundaries remain in force. Use the existing Red Dog /
OpenClaw control plane; Hermes is a replaceable sandbox worker, not a second daemon.

## Resident RSI canary — target autonomous loop

YUMORI is the first FoundUp campaign workload for measuring whether the existing
OpenClaw / RedDog / WRE stack can maintain a real project across days. Do not create a
separate YUMORI daemon, scheduler, memory database or agent framework. Reuse the
resident queue/control loop, registered Skillz, FoundUp scope `esingularity_001`,
existing provider adapters and existing memory owners.

The experiment asks two linked questions:

1. **Can compute save the onsen?** — can a demand-led regional compute project create
   enough technical, financial and institutional value to preserve useful public assets?
2. **Can the governed AI system launch YUMORI?** — can it repeatedly recover project
   state, identify the current bottleneck, choose a defensible action, execute within
   authority, verify the real outcome, learn from it and improve the next cycle?

### Memory reconstruction before every resident cycle

A new cycle must resume from evidence, not from the previous chat transcript. Compose
the existing memory surfaces; never collapse them into one new store:

1. current repository / WSP / HoloIndex truth;
2. authoritative work state and the existing operational FoundUp Memex snapshot supply;
3. Brain for durable consolidated understanding and Breadcrumbs for recent episodic /
   operational continuity;
4. Gmail / LinkedIn / other providers as transaction truth, plus native correspondence
   state and provider watermarks;
5. Contacts, Correspondence Routing, Email Log, Action Queue, capital and LinkedIn
   relationship projections;
6. YUMORI Moshpit for material campaign history and 0102 Moshpit for agent lessons;
7. WRE PatternMemory / verified outcomes for exact-skill execution results and later-use
   learning evidence.

A summary is never allowed to overwrite contradictory provider or primary-source
evidence. Cross-FoundUp records fail closed.

### Resident cycle contract

Each admitted cycle performs this sequence:

```text
RECOVER
  -> observe new provider / official / project evidence since the last watermark
  -> reconcile DONE / WAIT / BLOCKED / ACTIVE state
  -> identify the highest-leverage current project blocker
  -> generate at least one competing action when a real alternative exists
  -> choose with WSP 15 + deadline / irreversibility / dependency leverage
  -> execute the highest safe admitted action
  -> independently verify the provider / artifact / source outcome
  -> write the owning memory receipts and projections
  -> evaluate whether any procedure or Skillz lesson is justified
  -> carry only verified open state into the next cycle
```

The agent is expected to decide what work is needed. It does not wait for 012 to restate
known tasks. When evidence is insufficient, acquiring the missing evidence is itself a
candidate action.


### Model and research workers

Model brands are replaceable leaf intelligence. The canary objective, authority,
memory lineage and acceptance oracle stay in FoundUps.

- Use the currently qualified local/provider route for the first resident proof.
- OpenRouter / Fusion is a candidate advisory intelligence layer only after its live
  client/runtime binding, budget controls and privacy/redaction gate are independently
  qualified. Raw private Gmail bodies, private contact graphs, credentials and unrestricted
  Memex context must not be fanned out to external panels.
- Model-panel output may propose alternatives, summaries, partner hypotheses or message
  drafts; it cannot authorize provider effects or certify its own correctness.
- Reuse AI Gateway model AutoResearch for bounded model-selection comparisons when its
  benchmark/verifier contract fits the task.
- Reuse WRE AutoResearcher only for the bounded configuration/compute-ROI target it
  actually evaluates. It is execution-feedback infrastructure, not a generic judge of
  YUMORI partner quality, correspondence quality or campaign success.
- YUMORI learning uses the resident canary metrics and independent verified outcomes as
  its task-specific oracle. A research worker may nominate a change but may not alter
  that oracle to make its own candidate pass.

### Project objective hierarchy

Planning should reduce blockers toward a launchable three-site program rather than
maximize activity. Current categories include:

- lawful City / asset / PPP route;
- Hanyu-first grid, fiber, building and engineering feasibility;
- credible operator / EPC / data-center / utility / research partner;
- demand and offtake evidence;
- finance / capital stack and grant eligibility;
- organizational readiness and required human/physical acts;
- targeted public, community and media work only when it advances one of the above.

The priority can change when evidence changes. Do not keep a task alive merely because
it was previously high priority.

### Autonomous effect ladder

Autonomy is graduated by effect, not by confidence language:

| Level | Effect class | Resident behavior |
|---|---|---|
| A0 | Read/research/reconcile | Autonomous when the connected source is authorized. |
| A1 | Private runtime memory / queue / analysis writeback | Autonomous through the existing owning store and receipt contract. |
| A2 | Draft, candidate record, decision brief, proposed reply | Autonomous; still not proof of delivery or external action. |
| A3 | Email send, LinkedIn connect/DM, external publication | Target autonomous state, but only through the authenticated provider-effect owner with fresh recipient/audience preflight and post-effect readback. |
| A4 | Government filing, signature, financial commitment, contract, irreversible physical/public action | Requires the narrower owning authority and any required 012 physical/legal act. |

**Current truth boundary:** `REDDOG_AUTO` Gmail mutation remains draft/HOLD-only until
the #1779 host deployment closure is evidenced: direct/alternate mutation is denied,
the authenticated service owns provider credentials/reconciliation/private state, and
the service-owned sender boundary is the only admitted mutation route. The canary should
treat closing that engineering/deployment gate as project-system work; it must not route
around it.

## Autonomous Gmail operating loop

Gmail should become an autonomous project sensor and response surface, not a periodic
full-mailbox replay.

1. Resume from the correspondence provider watermark and search only the required delta
   plus any exact thread needed for context.
2. Reconcile inbound and Sent state before deciding that a message is unanswered.
3. Classify each material inbound item: new evidence, answer, refusal, routing change,
   deadline, meeting/access event, partner lead, funding/procedure change, or noise.
4. Build the current Correspondence State Capsule and decide one of:
   `RESPOND`, `RESEARCH_MORE`, `ROUTE`, `WAIT`, `CLOSE`, `IGNORE`.
5. Before recipient-finalized content, validate the audience: exact person/organization,
   current role, relationship/ask history, route consent, sender identity, language,
   purpose, reading burden, attachments/links and claim provenance.
6. Before every send-capable attempt, run `reddog_recipient_preflight`, duplicate /
   follow-up suppression and the service-owned sender boundary. Cached approval never
   authorizes a later transaction.
7. After an allowed send, read back provider From / To / CC / BCC, subject/thread and
   provider receipt; update correspondence state, Action Queue and the next observation
   deadline.
8. Track outcome separately from transmission: reply, substantive answer, meeting,
   introduction, refusal, no response by deadline, or unknown.

### Anti-spam / audience rules

- No mass blast.
- Prefer one high-fit recipient or a verified warm introduction over a broad list.
- Do not send a third follow-up without a material new delta or explicit owning policy.
- A new employee at the same organization is not automatically a new outreach target.
- Never guess private email patterns or infer support from discoverability.
- If the recipient is wrong, stale, duplicated, route-closed or the message does not
  materially fit that audience, hold and repair before any external effect.

## Autonomous partner discovery and unblocking

When the project is blocked on a missing operator, technical partner, funder, public
counterparty or adviser, the resident cycle should search independently rather than
waiting for a named lead from 012.

For each blocker:

1. define the capability actually missing;
2. research organizations and people with current direct evidence of that capability,
   prioritizing Japan/Fukui/APAC precedent where relevant;
3. search existing Contacts, Gmail and LinkedIn before creating a candidate;
4. verify current role/company and distinguish direct precedent from analogy;
5. identify warm first-degree or introduction paths when provider-visible;
6. record the candidate only in the existing CONTACTS / capital / LinkedIn surfaces;
7. rank candidates by capability fit, geographic/reputational relevance, warm path,
   decision authority, timing and outreach cost;
8. prepare the smallest target-specific ask: fit check, technical diligence, introduction,
   site discussion, operator discussion, financing discussion or non-binding interest;
9. reconcile all prior outreach before any new message.

A partner search that produces many names but no verified next action is not success.

## RSI learning contract

The canary is not RSI merely because it runs repeatedly.

For every material cycle preserve:

- source/memory snapshot identities and provider watermarks;
- selected blocker, alternatives considered and WSP 15 decision;
- exact Skillz/instruction digest used;
- action/effect receipts and independent verification;
- outcome observation deadline and later outcome;
- human intervention count and reason;
- model/provider/cost/latency evidence when available;
- accepted, rejected and unresolved learning candidates.

A repeated failure or near-miss may nominate a Skillz/prompt/test/code repair. The
candidate must not rewrite its own oracle or production Skillz. Use the existing
WRE/PatternMemory/verified-outcome path, independent review, held-out/regression
evidence and rollback/promotion gates.

**Retained improvement test:** a change counts as RSI benefit only after a later,
unseen YUMORI cycle uses the promoted version and performs better against the same
objective metric or avoids the verified prior failure without introducing a new
regression. Structural fidelity or a non-empty model answer is not enough.

### Canary metrics

Track at minimum:

- open blockers reduced / new blockers discovered with evidence;
- provider deltas reconciled without replay;
- duplicate or wrong-audience actions prevented;
- response/outcome latency;
- verified partner candidates that reach a concrete next action;
- external effects attempted / admitted / blocked / indeterminate;
- 012 interventions required and why;
- cost per verified useful outcome;
- Skillz candidates proposed / rejected / promoted;
- later-use retained improvements and successful rollback tests.

The desired trend is fewer avoidable 012 interventions and fewer repeated failures while
truth-boundary violations remain zero.

## Conversational intake

012 may speak nonlinearly, repeat old tasks, use STT artifacts, or introduce multiple lanes.

Red Dog must:

1. capture candidate tasks without immediately acting;
2. normalize obvious STT only against established project vocabulary;
3. retain ambiguous proper names as unresolved candidates;
4. recover prior artifacts/work before recreating them;
5. identify contradictions with current state;
6. preserve 012 sequencing when it does not conflict with evidence, legal/procedural
   requirements, dependency gates, or duplicate-send controls.

The conversation is interpretation input, not an execution receipt.

## Campaign lanes

| Lane | Scope |
|---|---|
| `CITY_LEGAL` | resident audit, information disclosure, PPP/PFI, procurement watch, counsel |
| `TECH_FEASIBILITY` | grid, fiber, buildings, structure/fire/asbestos, demand, heat |
| `ORG_ADMIN` | office address, charter, meetings/minutes, roster, bank/postbox, accounting/tax |
| `PUBLIC_MATERIAL` | tri-fold, website, prospectus, print/distribution |
| `PARTNERS` | Highreso, Intelligent Internet, operators/EPC/technical partners |
| `CAPITAL` | FIN, investor data room, capital targets, warm paths, lenders, strategic equity |
| `COMMUNITY_LEADERSHIP` | Saki/Nakamura/local leadership, volunteers |
| `MEDIA_PUBLIC` | press/radio/community visibility |

Do not mix legal filing, investor ask and public flyer into one work item merely because
they share facts.

## Work-item schema

```text
work_item_id:
title:
lane:
origin:
execution_origin: 012_DIRECTED_WORK | REDDOG_AUTO | UNKNOWN
principal_instruction_ref:
current_state:
evidence_refs:
truth_class: VERIFIED | REPORTED_BY_012 | SCENARIO | UNVERIFIED | CONFLICT
deliverable:
dependencies:
blocked_by:
owner_class:
  012_PHYSICAL | 012_DECISION | REDDOG_LOCAL | WORK_CLOUD |
  WAIT_EXTERNAL | BLOCKED
allowed_effects:
forbidden_effects:
wsp15:
  complexity: 1..5
  importance: 1..5
  deferability: 1..5
  impact: 1..5
  total: 4..20
  priority: P0 | P1 | P2 | P3 | P4
status:
  ACTIVE | WORK_READY | 012_ACTION | WAIT | BLOCKED |
  SUPERSEDED | DONE
next_gate:
completion_receipt:
```

## WSP 15 ordering

Canonical WSP 15:

```text
MPS = Complexity + Importance + Deferability + Impact
P0 = 16-20
P1 = 13-15
P2 = 10-12
P3 = 7-9
P4 = 4-6
```

Within the same band order by irreversible/deadline risk, dependency leverage, evidence
acquisition before advocacy, live external response windows, 012 sequencing, then lowest
safe execution cost.

## State reduction before scoring

Use: `DONE`, `WAIT`, `SUPERSEDED`, `BLOCKED`, `ACTIVE`, `WORK_READY`,
or `012_ACTION`.

Do not WSP15-rank DONE/SUPERSEDED as executable work. WAIT items are monitored, not chased.

## 012 physical-action lane

Keep a separate short list named **012 ACTIONS** for signatures, hand delivery/mail,
ID/hanko, real meetings/votes, address authority, physical inspections and other acts
that Work cannot truthfully claim occurred.

## Work-ready gate

A work item enters Work only after:

1. fresh state reconciliation;
2. duplicate/supersession checks;
3. WSP 15 score/rationale;
4. machine-executable owner class;
5. current source documents identified;
6. assumptions/unverified claims labeled;
7. allowed/forbidden effects explicit;
8. correspondence tasks have a current Correspondence State Capsule and recipient preflight;
9. no physical/signature/meeting step is impersonated;
10. classify execution origin: the existing RedDog governed-work chain authorizes
    `REDDOG_AUTO` proposals; `012_DIRECTED_WORK` uses the actual work-item-bound 012
    instruction and the correspondence owner's directed-Work checks. Do not require
    an undeployed Red Dog signer to rediscover or replace 012's existing direction.
    `UNKNOWN` remains HOLD. #1779 alone blocks AUTO sends, not explicitly directed
    Work; message-specific engineering holds and all recipient/Sent gates still win.

## Capital-network expansion protocol

The canonical capital database is **CONTACTS — YUMORI Master Contact Sheet**.
Use its existing `Capital Targets`, `Capital People`, `LinkedIn`, `Contacts`,
`Email Log`, `Action Queue` and `Correspondence Routing` surfaces. Do not create
a second investor spreadsheet.

### Capital classes

Do not collapse all financing into "VC". Classify targets as one or more of:

- infrastructure/private-equity or real-assets capital;
- policy bank / project finance / non-recourse debt;
- commercial bank / syndicated debt / equipment finance;
- sovereign wealth / pension / institutional equity;
- REIT / stabilized-asset capital;
- strategic corporate / utility / operator capital;
- venture / growth equity for the operating, AI, software or platform layer;
- family office / angel / adviser / introducer.

### Evidence-first target creation

A capital target must state the evidence for relevance:

```text
target_id:
organization:
capital_class:
geography:
direct_dc_ai_infra_evidence:
japan_apac_evidence:
capital_scale_or_transaction:
named_leads:
warm_path:
warmth:
fit_lane:
priority:
status:
next_action:
source_urls:
last_verified:
notes:
```

Use status labels such as:
`DIRECT_PRECEDENT`, `DIRECT_PORTFOLIO_PRECEDENT`, `WARM_1ST_DEGREE`,
`WARM_ADJACENT`, `COLD_PUBLIC_TARGET`, `ANALOGY_ONLY`,
`RESEARCH_REQUIRED`.

Never represent a public transaction or portfolio precedent as interest in YUMORI.

### Warm-path expansion

For each high-priority capital target:

1. verify direct sector/Japan evidence from current public sources;
2. search existing CONTACTS/LinkedIn/Gmail for verified first-degree connections;
3. distinguish:
   - `1ST_DEGREE_VERIFIED`: provider receipt or user-visible LinkedIn evidence;
   - `WARM_HISTORY`: prior direct relationship but current LinkedIn state not proven;
   - `PUBLIC_TARGET`: no relationship inferred;
4. in ChatGPT Work / browser mode, inspect mutual connections between 012 and named
   decision-makers or known network hubs (for example Andrew Yang, Sequoia contacts,
   investor/adviser connections);
5. capture only contact information LinkedIn exposes to 012's account or another
   authorized/official source; never guess private email addresses;
6. reverify current role/company before classifying someone by an old acceptance receipt;
7. write the discovered person/relationship back into `Capital People` and, when
   appropriate, the existing `LinkedIn`/master contact row;
8. before any message, reconcile prior correspondence and build the correspondence
   state/preflight receipt.

A mutual connection is an introduction path, not investor support.
Visible Contact Info is a routable candidate, not send authorization.

### Capital-stack reference pattern

Where a project has an analogous real financing precedent, preserve the stack by layer.

For the regional reused-facility GPU-data-center pattern, track separately:
- operator/common equity;
- preferred/direct equity;
- policy-bank/special-investment capital;
- project/non-recourse debt;
- regional-bank syndication;
- subsidy/grant support;
- equipment/leasing capital.

Do not add all available caps as committed project financing.

### Outreach readiness

Capital outreach is `WORK_READY` only when:
- current FIN assumptions are audited;
- the target's capital class matches the ask;
- a current decision-maker/route is verified;
- prior correspondence is reconciled;
- the message states evidence gaps and does not repeat rejected historical IRR/payback claims;
- requested action is bounded: diligence, fit check, introduction, non-binding interest,
  financing discussion, or data-room review.

No mass blast. Prefer warm intro or highly specific direct precedent.

## Work Handoff Packet

```text
YUMORI WORK HANDOFF
snapshot_time_jst:
foundup: esingularity_001
objective:
why_now:
wsp15_order:
source_of_truth:
verified_facts:
reported_by_012:
scenarios_and_unverified_claims:
work_items:
  - id:
    deliverable:
    owner:
    dependencies:
    allowed_effects:
    forbidden_effects:
    acceptance_tests:
012_actions:
external_waits:
do_not_duplicate:
stop_conditions:
required_receipts:
writeback_targets:
```

Work must operate from current evidence, inspect named artifacts before rebuilding,
complete machine work in WSP15/dependency order, never turn scenarios into commitments,
never duplicate correspondence, stop unsafe external effects, and return:
`DONE / BLOCKED / WAIT / 012_ACTION` plus artifact/provider receipt, validation and next gate.

## Wave design

**Wave A — Protect / evidence**  
City/legal, disclosure/audit, procurement, grid/fiber/building evidence.

**Wave B — Organization**  
Address/governance, meeting packet, roster, accounting/tax, bank/postbox.

**Wave C — Explain / mobilize**  
Post-vote tri-fold, public narrative, print/distribution.

**Wave D — Partner / capitalize**  
Partner meeting packets, FIN audit, capital database, warm-path mutual crawl,
investor brief/data room, then targeted outreach after correspondence preflight.

Dependency truth outranks convenience.

## Return and reconciliation

After Work:

1. verify every claimed artifact/provider effect;
2. campaign milestones -> YUMORI Moshpit;
3. agent failures/rules -> 0102 Moshpit;
4. Gmail/CRM -> correspondence owner;
5. capital findings -> existing CONTACTS capital/LinkedIn rows;
6. Drive artifacts -> update in place, no near-duplicates;
7. durable system state -> repo docs/ModLog/ROADMAP;
8. rescore remaining backlog.

A Work result is not DONE until acceptance test and writeback receipt pass.

## Regression scenarios

- "Email the City again." -> recover correspondence state; duplicate/third-follow-up
  block wins.
- "Contact Highreso." -> if outreach already exists, WAIT and prepare meeting material.
- "Use the 1.8-year return." -> block until current audited FIN independently supports it.
- "Create the tri-fold." -> recover prior layout and rebuild from current three-site truth.
- "Write meeting minutes." -> never invent attendance/resolutions.
- "Find investors." -> separate direct infrastructure capital from software VC, search
  warm first-degree paths, reverify roles, then prepare bounded target-specific asks.
- "Check Andrew Yang / Sequoia / BlackRock mutuals." -> use Work/browser for the mutual
  graph, record only verified relationships/contact info, never infer a relationship
  merely because a profile is discoverable.
- "Give all this to Work." -> scored waves + 012 actions first, not an undifferentiated dump.

## Dependencies

- `reddog_operations` / governed-work promotion chain.
- `yumori_contact_ledger` + `reddog_correspondence_state`.
- `reddog_recipient_preflight`.
- `fukui_city_procedure`.
- `yumori_funding_ppp_intelligence`.
- `yumori_moshpit`.
- WSP 15 / WSP 95 / WSP 97.

## Authority boundary

This skill creates/promotes work descriptions, not authority. It does not itself send
email/DM, submit government forms, sign filings, publish, spend money, make investment
offers, or claim a meeting, filing, investment, grant, utility capacity, partner
commitment or mutual relationship without the owning receipt.
