# LinkedIn editorial tree audit — 2026-09-22 UTC

Repository basis: `0dd4f2bbd0a69760df42c3d7a9af1920559cbf87` plus the
instruction changes in this slice. This is a code/skill audit, not a live LinkedIn
inventory. All current live publication/group states are `NOT_CHECKED_LIVE`.

## Coverage and findings

| Node | Existing owner | Finding / next action |
| --- | --- | --- |
| Master | linkedin_engagement; Work operate-0102-linkedin | Full/narrow routes exist; explicit scoped Red Dog/0102 return packet added |
| Inbox | linkedin_inbox | History, duplicate and uncertain-send handling present; delivery must use verified live surface |
| Connections | linkedin_connections | Existing policy reused; messages and acceptance remain distinct |
| Notifications | linkedin_notifications | Relevant replies route to inbox/feed owners with bounded coverage |
| Feed | linkedin_agentic_reply | Existing owner; no newsletter created from every interaction |
| Newsletter inventory | linkedin_newsletters | Three dedicated children present; added audit fields, additional-series discovery and separate editorial/delivery states |
| FoundUps / Eat the Startup | linkedin_foundups_newsletter | Own corpus and publisher discovery; next issue needs latest live coverage and a source-backed brief |
| ROC / Return on Compute | linkedin_roc_newsletter | Historical article exists; series unverified in publishing map. Continue research/local draft while placement is blocked |
| Japan Hyperscaler Report | linkedin_jhr_newsletter | Canonical report source and significance gate present; reconcile repo/site/LinkedIn issues before numbering |
| New issue / new series | newsletter router assets | Missing reusable templates supplied; new series must pass duplicate/identity checks |
| Group Good/Bad/Ugly | openclaw_group_news | Research/post/follow-up skill exists; added structured public intelligence return to appropriate newsletter lane |
| Group members/posts | linkedin_group_moderation | Separate moderation owner; editorial work implies no membership action |
| Targeting / publishing | linkedin_article_targeting / linkedin_publishing | Reused identity, exact revision, scheduling and read-back owners |
| Outreach | linkedin_outreach | Existing bounded relevance/history/recipient workflow |
| Continuity | linkedin_continuity | Existing private receipt contract reused; no new memory authority |

Legacy `src/SKILLz.md` is a git-to-social prototype, not the LinkedIn master.
Browser discovery/posting helpers remain implementation tools. The separate
antifaFM campaign is outside this workflow. No duplicate orchestrator is added.

## Editorial backlog: what is actually evidenced

| Lane | Repository evidence | What it does not establish | Next action / owner |
| --- | --- | --- | --- |
| Eat the Startup | Dedicated skill and historical publishing map; no next-edition artifact found in inspected LinkedIn content/docs | No claim that a draft is absent from LinkedIn or private stores | Red Dog inventories live editions/drafts; 0102 develops a founder-focused brief from uncovered merged work |
| ROC | `src/content/articles/ROI_to_RoC_Paradigm_Shift.md`, historical PR #202 | Not proof of the next issue, a newsletter series, or current publication state | Red Dog verifies actual series/articles; 0102 develops the next ROC argument without waiting on placement |
| JHR | `modules/foundups/esingularity/jhr/reports/JHR_001_2026-09_JAPAN_HYPERSCALER_REPORT.md` and canonical JHR README | Not proof that 001 is latest or that a next LinkedIn issue is written/live | Reconcile three surfaces, refresh evidence, apply significance gate, then draft or NO_REPORT |
| Good/Bad/Ugly | Dedicated skill with research and post structure | No current group post/draft/reply audit performed | Group owner checks recent discussion and drafts; develop one useful sourced topic if warranted |

Templates and routing are now available for collaborative development. This slice
does not write or publish those editions. A future audit must inspect authorized
draft storage as well as live LinkedIn and report bounded retrieval gaps.

## WSP 97 decision and limits

- Retrieval: current-main module docs, skill inventory, nearest tests, templates,
  publishing map, JHR owner and adapter/executor inspected. Holo lexical bundle
  returned module docs but weak keyword matches: freshness UNKNOWN, index gap true;
  direct file reads supplied evidence. No reindex or semantic acceptance claimed.
- WSP 00 canonical script lacked torch; tracker reported its cached gate compliant.
  No fresh detector witness or model-state transformation is claimed.
- Micro: missing brief/template/handoff; ROC delivery blocker over-scoped.
  Macro: retain existing master, source owners, publisher and continuity contracts.
- WSP 15 allocation: C2 + I4 + D3 + Impact4 = 13/P1; bounded instruction work.
- Alternatives: a new runtime coordinator/database would duplicate existing owners;
  generic post templates lack series, revisions and publication evidence. Reuse the
  newsletter router with shared assets and explicit receipt fields.
- Plane: instruction/docs; WRE runtime attachment not applicable. No launch,
  scheduler, model binding or human-gate change. Local caller owns failures.
- Verification: extend existing offline routing/link checks; independent scenario
  walkthrough; validate installed Work master; PR checks before authorized squash.

Current-main wrapper/direct-like/session previews and connection policy/note-order
repairs supersede older gap descriptions. Their scoped inert tests are not live
account qualification. Simulated messaging, remaining legacy group/live routes
and end-to-end durable orchestration still require separate runtime evidence.
