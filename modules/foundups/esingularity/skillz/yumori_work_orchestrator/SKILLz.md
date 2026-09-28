---
name: yumori_work_orchestrator
description: Convert 012/Red Dog YUMORI planning conversations into a verified, deduplicated, WSP 15-ranked campaign backlog and bounded ChatGPT Work / RedDog work handoff without creating a parallel source of truth.
version: 0.1.0
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
  -> WSP_00 identity/role/origin lock
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

This skill is the **YUMORI domain adapter**. It does not create a new work executor,
queue, signer, chat database, or campaign ledger. Red Dog's existing governed work-order,
conversation-work-promotion, AgentDB/WRE, and signed authorization chain remain the
execution owners.

## Canonical evidence owners

A backlog snapshot is disposable. Before every planning or execution cycle, reconstruct
state from the owners below.

1. Current repository + project README/ROADMAP/ModLog/Skillz.
2. Live YUMORI Moshpit for campaign history.
3. 0102 Moshpit for agent failures/rules only.
4. Gmail + native correspondence state + Contacts / Email Log / Action Queue /
   Correspondence Routing for correspondence.
5. Current Drive project spine (03/05/06/07, legal/admin/accounting/current FIN) for
   mutable human working artifacts.
6. Current official City/Prefecture/national/utility sources for procedural facts.
7. Current connected-app state for LinkedIn, Calendar, Drive, etc. when the task depends
   on it.

Never infer "not done" from absence in chat. Never convert a stale backlog row into
authority for an external effect.

## Conversational intake

012 may speak nonlinearly, repeat old tasks, use STT artifacts, or introduce several
lanes in one turn.

Red Dog must:

1. capture every candidate task without immediately acting;
2. normalize obvious STT only against established project vocabulary;
3. retain genuinely ambiguous proper names as unresolved candidates;
4. recover prior artifacts and existing work before proposing recreation;
5. identify contradictions with current state;
6. preserve 012's sequencing preferences when they do not conflict with a safety,
   legal, procedural, or dependency gate.

The planning conversation remains interpretation input. It is not an execution receipt.

## Campaign lanes

Every accepted item receives exactly one primary lane.

| Lane | Scope |
|---|---|
| `CITY_LEGAL` | resident audit, information disclosure, PPP/PFI, procurement milestone watch, counsel |
| `TECH_FEASIBILITY` | grid, fiber, building drawings/access, structure/fire/asbestos, demand, heat |
| `ORG_ADMIN` | office address, charter, real meetings/minutes, member roster, bank/postbox, accounting/tax |
| `PUBLIC_MATERIAL` | tri-fold, website, prospectus, print package, distribution plan |
| `PARTNERS` | Highreso, Intelligent Internet, technical/operating partners |
| `CAPITAL` | financial model, investor data room/teaser, Genki/BBR-type leads, LinkedIn capital outreach |
| `COMMUNITY_LEADERSHIP` | Saki/Nakamura/local leadership, volunteers, distribution coordination |
| `MEDIA_PUBLIC` | press, radio, community visibility after route and message checks |

Do not mix a legal filing, investor ask, and public flyer into one work item merely
because they use the same project facts.

## Work-item schema

```text
work_item_id:
title:
lane:
origin:
current_state:
evidence_refs:
truth_class:
  VERIFIED | REPORTED_BY_012 | SCENARIO | UNVERIFIED | CONFLICT
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

Use canonical WSP 15 without inventing a second priority formula.

```text
MPS = Complexity + Importance + Deferability + Impact
P0 = 16-20
P1 = 13-15
P2 = 10-12
P3 = 7-9
P4 = 4-6
```

Score the **approved work item**, not the attractiveness of its narrative.

Within the same band, order by:

1. irreversible/deadline risk;
2. dependency leverage (work that unlocks several later items);
3. evidence acquisition before advocacy;
4. current external response windows;
5. 012's stated sequencing preference;
6. lowest safe execution cost.

A high Complexity score raises MPS under WSP 15; do not silently "correct" the
canonical formula with an inverse-complexity variant.

## State reduction before scoring

For every candidate, assign one of:

- `DONE`: provider/artifact/receipt proves completion.
- `WAIT`: a valid external action already occurred and the next move belongs to the
  counterparty.
- `SUPERSEDED`: later project state replaces the old task.
- `BLOCKED`: a required fact, route, approval, form, signature, legal decision, or
  dependency is missing.
- `ACTIVE`: work exists and should be scored.
- `WORK_READY`: ACTIVE plus all machine-side inputs needed for bounded execution.
- `012_ACTION`: requires physical presence, handwritten signature, identity document,
  seal, address/standing confirmation, actual meeting/vote, or an explicit principal
  decision.

Do not WSP15-rank DONE/SUPERSEDED as executable work. WAIT items are monitored, not
chased automatically.

## 012 physical-action lane

Red Dog must maintain a separate short list named **012 ACTIONS**.

Examples:

- sign a form in the legally required manner;
- hand-deliver or mail a filing where the official procedure requires it;
- carry ID/hanko/original documents to a bank/post office;
- hold a real committee/general meeting and make real decisions;
- confirm the exact usable office address and authority to use it;
- perform field inspection/photos when machine evidence cannot substitute.

Work may prepare the packet, map, checklist, cover sheet, and print files. It must not
invent that the physical act occurred.

## Work-ready lane

A work item can enter ChatGPT Work / worker handoff only when:

1. its current state was freshly reconciled;
2. duplicate/supersession checks pass;
3. WSP 15 score/rationale exists;
4. owner class is `WORK_CLOUD` or a bounded `REDDOG_LOCAL` task is being promoted;
5. required source documents are identified and current;
6. unverified claims are labeled;
7. the allowed/forbidden effects are explicit;
8. correspondence tasks have a current Correspondence State Capsule and recipient
   preflight requirements;
9. no physical signature/identity/meeting step is being impersonated;
10. the existing RedDog governed-work authorization chain approves the exact work
    proposal/digest.

A conversation saying "do it" is not by itself execution authority.

## Work Handoff Packet

For each execution wave, emit one bounded packet:

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

### Work instruction

The packet prompt must tell Work to:

- operate from current evidence, not old chat wording;
- use current official web sources for current procedure and market facts;
- inspect the named Drive/repository artifacts before rebuilding anything;
- complete all machine-executable items in WSP 15 order;
- create finished artifacts where requested;
- never turn scenarios into commitments;
- never send a duplicate message;
- stop an external effect when recipient/procedure/authority is not verified;
- return a compact receipt for every task: `DONE / BLOCKED / WAIT / 012_ACTION`,
  artifact or provider reference, validation performed, and next gate.

## Wave design

Default to dependency-based waves rather than one giant prompt.

**Wave A — Protect / evidence**
City/legal, information disclosure, audit packet, procurement watch, building/grid/fiber
evidence.

**Wave B — Organization**
Address/governance, real meeting packet, roster, accounting/tax-status checklist,
bank/postbox packet.

**Wave C — Explain / mobilize**
Post-vote tri-fold, current website/prospectus alignment, print proof/quotes,
distribution plan.

**Wave D — Partner / capitalize**
Partner meeting packets, current financial audit, investor English teaser/data room,
targeted LinkedIn/known-investor outreach. Capital outreach follows evidence cleanup;
old IRR/payback figures remain excluded when current audited inputs do not support them.

This order may change after WSP 15 rescoring, but dependency truth outranks convenience.

## Return and reconciliation

After Work/worker completion:

1. verify every claimed artifact/provider effect;
2. write material campaign events to YUMORI Moshpit;
3. write agent failure/rule changes to 0102 Moshpit only;
4. reconcile Gmail/CRM through the correspondence owner;
5. update Drive current artifacts in place rather than proliferating near-duplicates;
6. update repository docs/ModLog/ROADMAP only when durable project/system state changed;
7. rescore the remaining backlog.

A Work result is not DONE until its acceptance test and writeback receipt pass.

## Regression scenarios

- "Email the City again." -> recover correspondence state first; existing WAIT/third
  follow-up block prevents duplicate send.
- "Contact Highreso." -> if current provider state shows outreach already sent, classify
  WAIT and prepare a meeting packet instead of another email.
- "Use the 1.8-year return in an investor deck." -> block until the current audited
  finance model supports it; old scenario is not an investable promise.
- "Create the tri-fold." -> recover prior print artifact/layout, update to current
  post-vote three-site truth, then generate a print proof; do not restart from memory.
- "Set the IKEA house as the committee address." -> create address-change/admin work,
  but require exact address/use authority + real governance approval before presenting
  it as formally adopted.
- "Write meeting minutes." -> record only meetings/resolutions that actually occurred;
  templates may be prepared for future meetings.
- "Give all this to Work." -> produce scored waves and 012 actions first; do not hand
  Work an undifferentiated brain dump.

## Dependencies

- `reddog_operations` and existing governed-work/conversation-promotion chain.
- `yumori_contact_ledger` + `reddog_correspondence_state` for correspondence state.
- `reddog_recipient_preflight` for external recipient authorization.
- `fukui_city_procedure` for municipal filing/process lanes.
- `yumori_funding_ppp_intelligence` for funding/PPP status.
- `yumori_moshpit` for campaign vs agent-memory writeback.
- WSP 15 for ordering, WSP 95 for Skillz reuse, WSP 97 for retrieval/dialectic/execution.

## Authority boundary

This skill creates and promotes **work descriptions**, not authority.

It does not itself:
- send email/DM;
- submit government forms;
- sign filings;
- publish websites or social posts;
- spend money;
- create legal commitments;
- claim a meeting, filing, investment, grant, utility capacity, or partner commitment
  occurred without its owning receipt.
