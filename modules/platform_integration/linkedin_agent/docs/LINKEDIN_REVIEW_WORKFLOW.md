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

### RSI dry-run boundary qualification — 2026-09-22

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
