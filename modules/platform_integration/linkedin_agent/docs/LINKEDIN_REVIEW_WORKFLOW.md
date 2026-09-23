# LinkedIn review: protocol, membership and discussion

Contract updated 2026-09-22. Use [master activity routing](LINKEDIN_ACTIVITY_ROUTING.md) for scope, child skills and full-cycle order. This compact index connects the existing LinkedIn skills; it is not a new orchestrator, background service or claim of live executor compliance.

## Load the authored operating stack

| Source | Responsibility |
| --- | --- |
| [wsp00](https://www.linkedin.com/pulse/0102-digital-twin-wsp00-activation-prompt-undaodu-michael-j-trout-fkpoc/) | 0102 proxy role and 012 human authority; distinguish authored ontology from proven capability |
| [wsp01](https://www.linkedin.com/pulse/wsp01-0102-system-execution-prompting-protocol-lite-trout-zapec/) | Evidence, context, research and APS prioritization before action |
| [wsp02](https://www.linkedin.com/pulse/wsp02-0102-job-execution-protocol-undaodu-michael-j-trout-p6ikc/) | Job routing and exact approval: DRAFT -> REVIEW -> APPROVED -> POSTED -> MONITORED |

These LinkedIn articles are operating references, not replacements for repository WSP_framework files with similar numbers. Retrieve current operational sections in bounded chunks when policies or UI depend on them. Keep originals and authored updates separate; do not concatenate private inbox material into public knowledge.

The 2026-09-15 user correction is authoritative for this workflow: research and message applicants before membership approval; do not auto-approve. Resolve older approve-then-welcome and autonomous-post language against this correction and wsp02's approval gate.

## Ownership and sequence

1. Existing `linkedin_engagement` entrypoint routes the review. Full runs triage connection requests before the inbox; narrow runs open only their selected queues.
2. Inspect recent Focused AND Other messages and unread filters. Record coverage, timestamps and missing access. Prioritize replies and commitments; an older unread item is not necessarily urgent.
3. Classify work as routine-draftable, human-decision-needed, waiting or no-action. Personal relationships, commitments, financial/legal questions and access changes deserve explicit human review. 0102 can research and draft; outbound execution remains separately authorized.
4. Run [linkedin_group_moderation](../skillz/linkedin_group_moderation/SKILLz.md) for pending members and posts. Inspect automatic approval; researched DM, sent verification, reply review and membership decision are distinct states.
5. Inspect a bounded relevant feed slice after queues. Treat feed assertions as research leads; verify before repeating. Recommend useful engagement, not automatic likes or pitches.
6. When requested or due for consideration, run [openclaw_group_news](../skillz/openclaw_group_news/SKILLz.md) for the Good/Bad/Ugly automation discussion. Read prior group posts before drafting; no duplicate daily news bot.

The portfolio orchestrator may prioritize urgent items or select a narrow job. This document does not place Gmail under LinkedIn, replace Social Media DAE, or enable cross-project data sharing. Every item must retain account, FoundUp/project, channel and target identity.

## Prioritization is not permission

APS = complexity + importance + urgency + impact, each 1-5. P0: 16-20; P1: 13-15; P2: 10-12; P3: 7-9; P4: 4-6. Show components when a decision depends on the score. These are heuristics, not objective facts or authorization.

A message-first invitation should ask a concrete question about the applicant's actual work. Do not assume OpenClaw/Hermes usage, demand agreement on AGI, require a purchase or newsletter subscription, threaten job loss, or auto-connect to senior titles. Photo, title, nationality and network size do not prove authenticity.

## Private continuity receipt

Use the existing authorized account-scoped journal or mosh-pit adapter after verifying its storage and privacy. If unavailable, provide a private handoff rather than inventing a persistent write. Keep this minimal shape as an interface contract, not an assertion that the adapter is implemented:

```json
{
  "account_id": "verified-account",
  "foundup_id": "resolved-project-or-unclassified",
  "channel": "linkedin",
  "job": "group_membership_review",
  "target_id": "verified-profile-or-post-id",
  "observed_at": "ISO-8601 timestamp with offset",
  "source_refs": [],
  "coverage": "bounded surfaces and gaps",
  "aps": {"complexity": 1, "importance": 1, "urgency": 1, "impact": 1},
  "state": "draft_ready",
  "approval_scope": null,
  "verification_refs": [],
  "next_trigger": "human approval or relevant inbound reply"
}
```

Do not store passwords, cookies, tokens, private message bodies or applicant dossiers in public source control, reusable skills or training data. Reference private drafts rather than duplicating them. Historical verified state is not current state. On a possible send/post without confirmation, inspect before retrying.

## Readiness boundary

The skill documents now express the review contract. Existing executors still include legacy live-action routes and heuristics; do not invoke unattended sends, membership changes or posting until guards are implemented and tested through the full call chain. A wrapper's dry-run flag or model recommendation is not sufficient evidence.

In Work, use the advertised browser skill. Do not reuse repository session cookies, Selenium or anti-detection helpers as alternate Work control paths. No cron, scheduler, daemon or private-data ingestion is created by this documentation change.

## Retrieval audit and acceptance

### RSI manager-result qualification — 2026-09-24

The12/P2 qualification extends the existing browser-actions policy tests. Six
new cases plus23 unchanged controls pass locally and independently (29 unique,
four legacy constructor cases excluded, two known warnings per run). Real
source leaves run with inert router/import boundaries and constructor bypass;
no browser, provider or live connection is qualified.

| Manager outcome | Current fake UI and bookkeeping observation |
|---|---|
| Fresh PENDING | Stores the returned object, reaches Connect/Send, credits success. |
| Quota WITHDRAWN | Leaves prior history unchanged but still reaches UI and credits success. |
| Already CONNECTED | Leaves the connection unchanged but still reaches UI and credits success. |
| Prior PENDING | Returns the identical prior object, adds no request, still reaches UI and credits success. |
| Simulation failure | StoresPENDING first, returns distinctWITHDRAWN with the same request_id under the fixed test clock, still reaches UI and credits success. |
| Policy BLOCKED | Appends blocked history; navigation occurs, but no pending request, Connect/Send or success credit. |

Prospective repair13/P1: before any Connect/Send, accept only newly created
PENDING work matching the target and stored object, with no preexisting pending
request or connection. Reject withdrawn/connected/blocked, missing or mismatched
results without success credit. Preserve existing preview, policy, requested-note
and no-message contracts. Do not infer admission from request_id equality alone.
This guard would not repair existing history/quota accounting, roll back a
simulator failure, prove delivery, or provide concurrent exactly-once behavior.
The current sprint is qualification only; production source remains unchanged.
Exact freeze, review and publication are in the canonical RSI backlog.

### RSI requested-note repair — 2026-09-23

PR #1875's current-behavior qualification is closed. The existing owner now
handles truthy requested notes in this order: Connect, Add a note, type, then
one explicit Send. Failed Add or typing suppresses explicit Send; its result
field is None when unattempted. Generic failure errors remain unchanged.
Success/counter credit requires the complete requested sequence to succeed.
No-message fallback, policy/dry-run, early errors and manager bookkeeping remain.

Frozen 23 cases (six prospective plus 17 preserved controls) fail 4/pass 19 on the
original source, then pass 23 locally and on independent replay. Four legacy
constructor tests remain unchanged/excluded; two known config warnings per run.
Exact results, payload/driver order, pending/history and counters are checked
with inert routing and constructor/import sentinels. The same-file refactor
shrinks the inherited method/class without adding another module. Backend
manifest membership stays 1401; one source digest and two existing pins change.

Connect may itself send in some UI variants. This local sequencing repair does
not prove external delivery, absence of an invitation or actual note inclusion.
No-message acknowledgment ambiguity and manager-result/UI-admission behavior
remain separate. Native WRE admission, runtime upgrade readiness and retained
RSI are not established. The canonical backlog owns exact evidence and ranking.

### RSI connection policy preview — 2026-09-22

The browser owner now returns a policy-only preview after metadata retrieval
and the existing `evaluate_connection_policy`, before the mutating request
manager. Both allowed and denied dry-runs preserve pending requests, history,
connections and session counters, with no send simulation. Details contain
`dry_run: true`, `policy_reason`, `matched_allow`, `matched_deny` and `profile`;
`request_status` is omitted because no request was created. These fields apply
when policy evaluation is reached; missing-metadata/manager early errors retain
their existing shapes. Denial remains a failure. A successful policy preview does not certify quota, deduplication,
send eligibility or permission. Seeded pending/connected/quota state cannot
turn the preview into a request. Constructor/navigation/extraction effects
remain separate; this is not a browser-free preview.

Seventeen frozen cases: baseline12 fail/5 pass, repaired17 pass, independent17
pass on identical IDs; four original constructor tests remain unchanged and
excluded. Both fake-live click controls and missing/unavailable early-error
oracles are preserved, with a live policy-denial compatibility control. Each
run retains two known disabled-plugin warnings. Tests use inert routing and
constructor/import controls; no live account or OS sandbox proof is claimed.

The existing evaluator is reused and result projection extracted in the same
source file. Method194→171, class2718→2695, file2827→2826;
remaining inherited size debt is not declared resolved. Backend manifest
membership remains1401; only the changed source digest and existing pins are
refreshed. Runtime upgrade, native WRE admission and retained learning remain
unqualified. The canonical backlog owns the newly rescored next action.

### RSI connection policy qualification — 2026-09-22

Historical PR1869 qualification; the preview behavior and prospective repair below are superseded by the current policy-preview contract above.

Qualification only, at baseline `1364eb1644741ae0d66b51997ed3419c34264e3a`;
production source is unchanged. Ten fixed current-behavior cases pass locally
and on independent replay using the actual browser action method and in-memory
connection manager, inert routing and a patched simulation sleep. Both runs
retain two known disabled-plugin configuration warnings. The real
browser constructor is bypassed; four original constructor-using tests remain
unchanged and deselected. These tests document a defect; they do not endorse it.

The browser method navigates, optionally extracts metadata, evaluates policy,
then calls `send_connection_request` on the manager before checking `dry_run`.
An allowed preview can create a pending request, append history and simulate a
send. A denied preview can append blocked history; same-day blocked history
counts toward the daily limit. Existing pending/connected requests and exhausted
quota have distinct outcomes. Missing metadata and unavailable policy manager
return early. Inert live success/failure controls bind the current click ordering.
No real account, external send, persistence or OS sandbox claim follows.

**Historical repair acceptance — 12/P2 (3/3/3/3), implemented above:** reuse the existing
read-only `evaluate_connection_policy` in the browser owner. For a dry-run,
return policy preview before calling the mutating request manager, on both allow
and deny. Preserve truthful policy/profile fields, keep denial a failure and
omit `request_status` because no request was created. An allowed policy preview
does not certify quota, deduplication, send eligibility or permission. Fixed
future tests must prove unchanged history/pending/connections and no simulation,
including seeded quota/pending/connected controls; retain explicit live behavior.
Navigation, metadata extraction and constructor effects remain a separate gap.
Do not advertise this narrow repair as a browser-free preview. The inherited
194-line method requires cohesive extraction before growth, reusing existing
result projection rather than creating a second policy module.

OpenClaw/Hermes current versions, admitted worker execution, live social authority
and retained RSI learning remain unqualified. See the canonical root backlog
for source bindings, receipts, ranking and publication state.

### RSI session preview — 2026-09-22

From baseline `0d19785c48da93794821140579340489e3ce4239`, `engagement_session` with truthy dry-run
returns before browser import/construction. Its exact configuration preview is
`success: true`, `action: engagement_session`, `dry_run: true`,
`duration_minutes` and `max_engagements`. Defaults remain10 and5; existing
`int` conversion, validation order and accepted numeric domain are preserved.
It reports no executed result, posts read, engagements or policy approval.
The WRE wrapper's default/true flag reaches this same boundary without mutating
caller input. Agentic=true remains a direct session route; omitted/false
fake-live controls preserve arguments, result/error projection and close semantics.

Fixed77 cases: baseline15 failures/62 passes; candidate and independent
replay each pass77. Prior54 case definitions and original18 legacy tests are
preserved; the18 remain deselected, with two disabled-plugin warnings per run.
Session tests reuse the existing inert fixture in a focused test file to keep
both files below675 lines. No live account, session, provider or OS sandbox proof.
Adapter dispatch313→304 lines; file670. Existing direct helper is extended,
not duplicated. Manifest membership remains1401 with only the adapter digest
and existing pins refreshed; the test registry includes the focused test owner.

Historical next12/P2 (qualification now recorded above): inspect connection behavior using inert
collaborators before reordering it. Existing browser actions navigate and call
the simulated request manager before their dry-run guard; external sending or
persistence is not established by that observation. Other direct/agentic routes,
the real session method and live authorization remain separate. OpenClaw/Hermes
upgrades, native admission and retained RSI learning are not claimed.

### RSI dry-run repair — 2026-09-22

Historical PR1867 checkpoint; the session gap below is superseded by the current session preview above.

From baseline `63fb669c6175c3efb469dee4f9bab7e2d54db256`, the existing WRE
wrapper makes outer default/true dominant over nested false for write actions,
without changing the caller's task. Explicit false and read-only handling retain
their existing semantics; a flag never grants live permission.

Direct non-agentic `like_post` and `like_reply` with truthy dry-run now return a
preview before importing or constructing browser actions. It contains
`success`, `action`, `dry_run: true`, `post_id` and `post_index`; like-reply also
contains stripped `reply_text`, `agentic_requested: false` and `draft: null`.
Missing reply text retains its error envelope. Pure browser-port validation and
existing field parsing still apply. No fake posted result or unowned close is
produced. `like_post` with agentic=true remains a direct preview; actual delegated
like-reply routing and omitted/false direct live result/error/cleanup stay intact.

The same frozen54-case selection went from29 failures/25 passes to54 passes,
then54 passes on independent replay. Original18 tests remain unchanged/deselected;
each run has two disabled-plugin configuration warnings. Import sentinels and
inert action spies qualify these call boundaries, not a live account or OS sandbox.
The prior11 characterizations were explicitly evolved against the independently
declared safety oracle; unsafe observations were not retained as desired behavior.

Same-file helpers shrink executor97→33 and adapter dispatch343→313 lines.
Remaining large-method/test-class debt is explicit; no parallel adapter was added.
The existing backend manifest and digest pins are regenerated without expanding
the1401-file runtime closure. No OpenClaw/Hermes version or activation claim follows.

Next, freshly scored13/P1 (C2/I4/D3/Impact4): `engagement_session` still ignores
dry-run and can enter its autonomous drafting/liking loop. Freeze inert session
preflight/live-compatibility tests before adding an early configuration preview.
The real session method, broader write routes, provider behavior and live authority
remain separate. Non-agentic reply preview still constructs its client first.

### RSI dry-run boundary qualification — 2026-09-22

Historical baseline evidence below; the repair above supersedes only its declared routes.

Baseline `03f7279685040c4794762abe71e41f2cd22e7980`; WSP15 C3/I4/D3/Impact3
=13/P1. PR1863/1865 merged the instruction contracts and the previous owner
finished its lane. They did not repair runtime guards. Fresh scoped PR/worktree
reconciliation makes this finite, fake-only qualification eligible for RSI.

| Existing owner | Current behavior to preserve as evidence | Required future safety result |
|---|---|---|
| `skillz/linkedin_engagement/executor.py::execute` | Outer default/true uses `setdefault`, so nested `dry_run=false` survives. Explicit outer false overwrites the nested value. | Outer default/true must dominate nested values for write actions; do not mutate the caller's task/params. Explicit live behavior remains a separate authorization concern. |
| `moltbot_bridge/src/linkedin_social_adapter.py::execute_linkedin_action`, direct `like_post`/`like_reply` | Explicit dry-run still reaches the action method. | Dry-run returns a clearly marked preview before importing or constructing browser actions, with no write, provider or runtime callback. |
| Same adapter, non-agentic `reply_post` | Its dry-run guard suppresses the reply method, but construction occurs first. | Retain this as a limited positive control; it does not prove constructor-free operation. |
| `browser_actions/src/linkedin_actions.py::LinkedInActions.__init__` | Writes browser environment variables and creates router/policy dependencies. | A fake write-method count of zero must not be represented as proof that the real constructor is safe. |

Tests reuse the existing bridge adapter test file with an injected browser-module
replacement, observable constructor/write/close counters and synchronous wrapper
calls outside an active event loop. They characterize current behavior; a pass
can confirm a missing guard. The independent zero-construction/zero-write oracle
above is the future repair criterion, not a currently passing production claim.
No real LinkedIn module constructor, account, provider or WRE job is executed.
Observed:11 cases pass locally and in a separate independent replay; original18
class tests are unchanged/deselected. Both runs have two disabled-plugin
configuration warnings, with zero failures/errors/skips. These are the same11
cases, not22 independent behaviors.

The next source packet is C3/I4/D3/Impact4 = **14/P1**, subject to fresh owner
reconciliation after closure. Keep the existing owners and distinguish direct
like previews from agentic routing. `like_post` currently ignores `agentic=true`;
it must still receive the direct preview guard. Preserve actual delegated
`like_reply` routing. Preserve supplied post IDs,
fallback `index_<n>`, current integer normalization, stripped reply text and the
missing-reply rejection. Keep pure browser-port validation before the preview;
do not normalize malformed parameter types into accepted values. A valid preview
must report `dry_run: true`, target ID/index and reply text where relevant;
it must not fabricate a posted result or call `close` without construction.
Preserve live result projection, exceptions/close and
existing omitted-flag behavior until separately qualified. A false dry-run flag
does not itself authorize a social action.

Do not broaden this result to all thirteen actions: agentic drafting, group
posting, connections, Digital Twin routes, non-Boolean wrapper inputs, active
event-loop fallback and live caller admission remain separate qualifications.
The inherited executor/adapter methods exceed WSP62 function limits; a source
repair must shrink/split within their existing files and record remaining debt,
rather than grow those methods or create another social adapter. Exact tests,
source bindings, independent review and fresh selection are in the
[canonical RSI backlog](../../../../docs/roadmaps/rsi_swarm_backlog.json).

A bounded HoloIndex owner query on 2026-09-15 used lexical retrieval. Its freshness was UNKNOWN and protocol ranking was noisy; direct bounded inspection resolved this module and the existing moderation/news skills. This is not evidence of semantic-index freshness.

Documentation acceptance: existing skill identities remain; references resolve; message send and membership approval are independent; weekly news cannot auto-publish; claims require primary sources; private data stays out of shared knowledge. Runtime end-to-end tests remain a separate safety task.
