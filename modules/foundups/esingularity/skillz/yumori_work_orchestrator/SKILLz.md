---
name: yumori_work_orchestrator
description: Convert 012/Red Dog YUMORI planning conversations into a verified, deduplicated, WSP 15-ranked backlog and bounded ChatGPT Work / RedDog handoff, including a governed capital-network expansion workflow.
version: 0.2.0
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
