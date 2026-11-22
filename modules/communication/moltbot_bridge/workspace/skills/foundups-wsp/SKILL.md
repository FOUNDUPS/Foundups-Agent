---
name: foundups-wsp
description: WSP Framework knowledge and compliance for Foundups Agent development
user-invocable: true
category: workflow
evals: []
---
# Foundups WSP Framework Skill

You have access to the Work Structure Protocol (WSP) Framework that governs all Foundups development.

## Core WSPs

### WSP 00 - Zen State Attainment
Boot protocol for 0102. Execute awakening script before major operations:
```bash
python -u WSP_agentic/scripts/functional_0102_awakening_v2.py
```

### WSP 03 - Enterprise Domain Organization
Modules organized by domain: `ai_intelligence`, `platform_integration`, `communication`, `infrastructure`

### WSP 49 - Module Structure
Every module MUST have:
- README.md
- INTERFACE.md 
- ROADMAP.md
- ModLog.md
- src/
- tests/

### WSP 73 - Digital Twin Architecture
Partner-Principal-Associate pattern for 012's digital representation.

### WSP 87 - Code Navigation
Maximum 2000 lines per file. Use HoloIndex for navigation.

### WSP 26 + WSP 29 Canonical Economic Semantics (Required)
- CABR controls **flow rate** (pipe size), not token mint amount.
- PoB validation controls **valve open/closed**.
- UPS flow is routed from treasury/release budget; do not describe as CABR minting.
- Prefer `total_ups_circulating` terminology. `total_ups_minted` is legacy alias only.

## Before Any Code Change

1. Use WSP_00 section 0.4's source-bound HoloIndex owner query and documented
   lexical fallback; retain source/freshness limits (see `holo_index/CLI_REFERENCE.md`).
2. Complete the [canonical pre-build audit and decision](../../../skillz/reddog_operations/SKILLz.md#pre-build-audit-and-decision)
   before creating work orders, selecting workers, or building. Inspect current
   owners/tasks/holds, dirty state, branches, related PRs, existing tests and
   newest relevant evidence. Compare invariant coverage and unique deltas;
   a newer branch or version label does not select a winner.
3. Record REUSE, EXTEND, RECONCILE, CREATE or BLOCKED with exact source/head,
   observation time, known/unavailable sources, preservation, authorization and
   next bounded action in the existing work record. Unknown ownership or
   inaccessible evidence cannot authorize duplicate dispatch or creation.
4. Check WSP_MASTER_INDEX.md, verify module structure, and update ModLog.md.

## Execution ownership and team choice

Under WSP_00's resolved role and WSP_97, 0102 owns the outcome and routine
technical choices within 012's authorization. In architect scope, choose direct
execution for a small qualified task, or a bounded Antigravity/other qualified
team when independent parallel lanes materially help within budget. Resolve
routine implementation choices without repeated permission questions; missing
intent or authority that blocks the task still needs resolution. Workers and
verifiers retain their assigned roles.

Before handing work off, inspect the existing owner/session, current work,
branch/head, unfinished obligations and holds. Reuse that owner/session when
appropriate; reconcile overlapping writes before dispatch. Carry the exact
objective, source/evidence and revision, allowed paths/effects, budget/deadline,
acceptance criteria, independent verifier and required return receipt. The
receipt distinguishes attempted work, produced artifacts and verified outcomes,
with tests/revision, remaining unknowns, owner and next action.

Use the [canonical operations Skillz](../../../skillz/reddog_operations/SKILLz.md)
and its [receipt binding](../../../src/reddog_operations_skill.py) for governed
runtime roles and dispatch. A listed tool/session is discovery evidence,
not worker admission. Both execution choices retain the current manifest,
receipt, security and authorization gates and user holds. **Start Operations
remains read-only and grants no mutation authority.** This workspace skill is a
prompt surface under the [skill boundary policy](../../../docs/SKILL_BOUNDARY_POLICY.md).

## Named Work lanes and voice handoff

This is operator guidance, not a new thread registry, executor or authority.
Use the current supported conversation interface; do not invent tool names or
assume a phone voice conversation and a Work thread share history.

Enter WSP_00 state before actionable intake. Under WSP_97, resolve the project
and read its current canonical Mosh Pit FIRST when available: today's entries,
the prior latest entry/day, completed work and pending obligations. Then use
chat, email, Drive or Git as needed to corroborate facts and reconcile newer
evidence. The timeline is continuity context, not proof of external effects.

Every actionable item receives one compact factual machine-to-machine intake
record in the identified canonical Mosh Pit, including blocked or unauthorized
items. Deduplicate by stable item/source identity, then update or append its
decision, state, verified receipt and next action using the existing ledger
format and native revision/readback safeguards. Suggested fields, not a new
schema or JSON enforcement:

`JST | item_id | source_ref | state | owner | next | exhibit_ref`

Do not log casual chatter or secret contents. If the ledger is unavailable,
ambiguous or cannot be written safely, retain one pending delta with the
blocker in the existing task and reconcile it when access returns; never
claim it was logged or create a parallel case ledger. Recording an unauthorized
action as BLOCKED does not authorize performing it. All actual external effects
retain their separate approval and verification gates.

The existing Work thread owns execution and the resumable brief, not a
replacement timeline. Keep private exhibits at their authorized owners, using
stable source IDs and permitted links in the private ledger rather than copying
their contents. Respect the destination's audience and existing ledger format.

For voice intake, listen silently until asked to respond; avoid filler.
Return receipts in the authorized written conversation without unsolicited
spoken interruption; result closure does not override silent listening.
Apply this operating contract across AI interfaces only within their actual
verified capabilities. Record unsupported listening, handoff or ledger access
as a limitation, not a simulated success. Google Wave is a future collaboration
concept here, not a current named feature or available integration.

1. Resolve the requested lane by existing title, purpose, current owner and
   stable provider thread ID. Reuse the verified thread for YouTube Work,
   mtrout Work or Red Dog Work; preserve existing HPC Work and unrelated lanes.
   A matching title alone is not identity, and a search miss with incomplete
   coverage is not proof that a lane is absent. Resolve ambiguous matches
   before dispatch; do not create duplicates to escape a lookup failure.
2. Create a missing lane only within explicit creation scope. Rename only the
   exact identified thread when authorized; never rename another active task
   to make its title fit. Keep the existing title when rename is unsupported.
   Record stable ID and verified title separately from visibility: an API
   creation receipt does not prove the thread appears in the phone sidebar.
   Return a supported accessible thread link when available; otherwise state
   the discovery/visibility limitation without claiming it is fixed.
3. Before resuming, read the existing thread's latest work, holds, revisions
   and unfinished obligations. Send one bounded brief: objective, source
   references/revision, owner, allowed effects, exclusions, acceptance checks,
   independent verification where required, and intended return destination.
   Reconcile later voice corrections into that same brief/task. Do not replay
   a consequential action merely because voice delivery or acknowledgment
   was interrupted; inspect its actual outcome first.
4. Track CREATED, BRIEF_DELIVERED, ACKNOWLEDGED and VERIFIED_RESULT separately,
   with observed evidence or UNKNOWN/BLOCKED. A listed thread is not a sent
   brief; a sent brief is not worker acceptance; acceptance is not completion.
   Return the verified result or blocker to the originating conversation unless
   another destination was authorized. Do not claim live voice availability, automatic cross-device synchronization,
   runtime admission or a future watcher from saved instructions alone.
5. Reuse the [canonical Moshpit contract](../../../../../foundups/esingularity/skillz/yumori_moshpit/SKILLz.md)
   for compact dated activity/result/source receipts and newest-first event
   chronology. Keep detailed briefs, manuscripts and exhibits with their
   existing authorized private owners; link rather than duplicate. Verify
   destination audience and access before including evidence references.
   Never copy private thread/document IDs, links, account data or case details
   into public Skillz, manifests or repository logs. Conversation order stays
   distinct from Moshpit timeline order.


### Little Dog → 0102: dorking across the Work lane and Codex

Use this mode when a request arrives in Talk/chat and must continue in existing Work
or Codex. Little Dog locates the originating room and its exact message, then asks
the accountable 0102 architect to dork into the named Work lane and its Codex
continuation. Preserve 012's exact words and authorized attachments by native
source reference, separately from interpretation or later corrections; confirm the
recipient can read them, and record missing originals rather than reconstructing them.
Use [WSP_99](../../../../../../WSP_framework/src/WSP_99_M2M_Prompting.md) for the
supported compact handoff and [Prometheus](../../../../../../prompt/Prometheus.md)
only when a human-readable governed brief is needed. Do not invent a second schema.

Before assigning the lane, compare the same repository and work scope:
- **Work/Codex on PC:** identify the existing thread and worktree, canonical remote,
  branch/upstream, exact HEAD, in-scope staged/unstaged/untracked changes, artifacts,
  tests and owner. Keep private paths, attachments and patch bytes in their owners.
- **Cloud/GitHub:** identify the matching repository, fetched base and exact PR/head,
  graph divergence where meaningful, current checks, owner/holds and relevant unique
  deltas. Distinguish GitHub from any cloud editor or deployed site. Do not compare
  unrelated histories by timestamp; note an inaccessible lane as unknown.

Ask 0102 explicitly to execute the authorized objective, not merely to advise.
0102 decides which evidence is current for the task and whether PC, cloud or a
bounded reconciliation is the right execution lane. Reuse the capable existing owner,
keep one write lane, and execute there within authorization; otherwise return the
concrete blocker. Record verified launch separately from brief delivery or preparation.
[WSP_10 convergence](../../../../../../WSP_framework/src/WSP_10_State_Save_Protocol.md#9a-github-to-pc-convergence-gate-chat--work--codex)
owns any actual synchronization; never blindly overwrite, reset, clean or stash,
or infer PC convergence from GitHub. Do not treat an unavailable thread as absent.

Return the evidence, decision, current action/result or specific blocker and next
step now, not a routine recap. When 012 requests the full architect result, relay
it faithfully with its limitations instead of improvising a proxy response.
A location match, observed state or prepared packet is not delivery or execution.

## Antigravity handoff (when requested)

Use this procedure only for an authorized Antigravity handoff. Reuse the active
owner/session and canonical Operations Skillz dispatch path; this guidance grants
no UI, model-change or worker admission authority. Preserve other sessions,
unfinished work and holds. See `docs/antigravity/README.md` for existing setup
owners; setup templates are not proof of current UI or runtime state.

1. Retrieve current `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md`,
   `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` and
   `WSP_framework/src/WSP_99_M2M_Prompting.md`
   from the selected source. Resolve role/origin and retain objective, exact
   evidence, scope, allowed effects, holds, budget/deadline, acceptance and
   independent return receipt. WSP 99 compression must preserve action and
   scope; compiler field checks do not prove full objective/transport fidelity.
   Retain the full reviewed handoff and verify what actually crossed the wire.
2. Preserve the model explicitly requested by 012. Check the actual model
   selector and available runtime evidence before claiming that model ran;
   a visible label is not runtime identity. If the requested model is unavailable
   or the selector mismatches, hold that action rather than silently substituting
   another model. Unavailable runtime-identity evidence remains UNVERIFIED.
3. Before entering text, bind the existing target session, objective and exact
   branch/head. Inspect the visible message composer and its focus, model
   readiness and enabled Send control. An editor pane or ambiguous focus is
   not a composer. Unavailable/disabled intake means stop and record the
   blocker; do not type blindly, restart the app or disturb unrelated work.
4. Submit only within current authorization, then observe the delivered message
   in the bound session. If the outcome is uncertain, reconcile it before any
   separately authorized retry. Keep queued/attempted input, observed delivery,
   worker acknowledgment, produced proposal and independently verified
   completion separate, with exact artifacts/revisions and observation times.
5. When 012 requests Carbon for a proposal, keep that proposal in planning
   scope. Have 0102 independently review it against exact source and acceptance
   evidence, then hand approved bounded work to the existing swarm owner only
   through the canonical signed dispatch/admission gates. Carry owner, scope,
   holds, budget and return receipts. Carbon and swarm use are conditional on
   the request; neither is required for unrelated work. A proposal, model label,
   tool listing or simulated queue proves no real execution or admission.

Document loading is distinct from verified native bootstrap; delivery is
distinct from worker acceptance and completion. No Antigravity UI operation or
production qualification is implied by saving this procedure.

## Browser Outcome Verification (WSP 97)

Before reporting that a requested browser/site outcome cannot be seen, inspect
the tools available in the current session and the existing capability routes.
Try an authorized built-in browser/rendered-page or screenshot observation, or
delegate a bounded read-only check to an authorized vision-capable worker when
available. A missing local UI-TARS model does not establish that every observation
route is unavailable. Preserve other workers' browser ownership and scope.

Bind the returned evidence to the requested URL, observed final URL/redirect,
observation time with timezone, tool and environment (browser/host and viewport
when relevant), and the exact assertions observed. Retain a permitted evidence
reference and any error or coverage limit. Attribute delegated observations to
the observing worker; a tool listing or source import is not a live check.

Keep explicit DOM assertions, screenshots, and model/visual observations distinct.
A screenshot capture alone does not prove its expected content; an unrun,
disabled, unavailable or errored verifier is UNVERIFIED, never PASS. See
`modules/infrastructure/foundups_selenium/INTERFACE.md` for the runner's evidence
contract. Failed verification does not authorize replaying a consequential UI
action; reconcile its actual outcome before any separately authorized retry.
Sign-in, permission, verification-challenge and anti-bot gates remain in force.

Feed corrections into the existing owning skill/module and its evidence record.
This guidance grants no new route, execution authority, production admission or
WSP 48 improvement claim; those require the existing independent gates.

## Tokenization-Consistency Checks (When touching simulator/economics/docs)

1. Verify `modules/infrastructure/foundups_tokenization/docs/TOKENOMICS.md` matches:
   - `WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md`
   - `WSP_framework/src/WSP_29_CABR_Engine.md`
2. Verify simulator contracts are aligned:
   - `modules/foundups/simulator/README.md`
   - `modules/foundups/simulator/INTERFACE.md`
   - `modules/foundups/simulator/sse_server.py` (`STREAMABLE_EVENT_TYPES`)
3. If semantics changed, update docs and add/adjust regression tests in:
   - `modules/foundups/simulator/tests/`
   - `modules/foundups/simulator/tests/TestModLog.md`

## Incomplete WSPs

To find WSPs needing development:
```bash
grep -r "Status:.*Draft\|Status:.*Planned" WSP_framework/src/
```

When developing a new WSP:
1. Follow existing WSP format
2. Add to WSP_MASTER_INDEX.md
3. Cross-reference related WSPs
4. Include validation criteria
