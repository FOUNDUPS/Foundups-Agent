# LinkedIn master activity routing

Use the existing `linkedin_engagement` skill as the repository master and
`operate-0102-linkedin` as its Work counterpart. These are instruction routes,
not a new executor, daemon, or certification of legacy automation.

## Select scope before opening queues

| 012 request | Activity skill | Scope |
| --- | --- | --- |
| Run LinkedIn / full LinkedIn | [linkedin_engagement](../skillz/linkedin_engagement/SKILLz.md) | Full cycle below |
| Check messages / respond / send approved messages | [linkedin_inbox](../skillz/linkedin_inbox/SKILLz.md) | Inbox or named approved batch only |
| Review connections | [linkedin_connections](../skillz/linkedin_connections/SKILLz.md) | Connection requests, not group membership |
| Check notifications | [linkedin_notifications](../skillz/linkedin_notifications/SKILLz.md) | Relevant notification targets |
| Review OpenClaw members / pending posts | [linkedin_group_moderation](../skillz/linkedin_group_moderation/SKILLz.md) | Membership and moderation queues |
| Good, Bad and Ugly / group news | [openclaw_group_news](../skillz/openclaw_group_news/SKILLz.md) | Research and group discussion; no membership changes |
| Feed / ROC engagement / reply to a post | [linkedin_agentic_reply](../skillz/linkedin_agentic_reply/SKILLz.md) | Read post and relevant replies; contextual engagement |
| Newsletter audit / all newsletters | [linkedin_newsletters](../skillz/linkedin_newsletters/SKILLz.md) | Router; all three lanes only when requested/full cycle |
| FoundUps / Eat the Startup / contextually clear “BoundUps” | [linkedin_foundups_newsletter](../skillz/linkedin_foundups_newsletter/SKILLz.md) | Foundups-Agent implementation and founder benefit |
| ROC / Return on Compute newsletter | [linkedin_roc_newsletter](../skillz/linkedin_roc_newsletter/SKILLz.md) | Personal compute-economics lane; live series identity required |
| Japan Hyperscaler Report / JHR | [linkedin_jhr_newsletter](../skillz/linkedin_jhr_newsletter/SKILLz.md) | Significance-gated Japan infrastructure reporting |
| Publish / schedule / page update / article maintenance | [linkedin_publishing](../skillz/linkedin_publishing/SKILLz.md) | Exact publisher, content, timing and verification |
| Where should this article go? | [linkedin_article_targeting](../skillz/linkedin_article_targeting/SKILLz.md) | Historical map plus live identity verification |
| Strategic outreach / subscribers | [linkedin_outreach](../skillz/linkedin_outreach/SKILLz.md) | Researched, bounded relevant recipients |
| Resume / report / audit skills | [linkedin_continuity](../skillz/linkedin_continuity/SKILLz.md) | Verified ledger, improvement and handoff |

A narrow command never silently expands to the full cycle. For example, “check
my messages” does not authorize feed likes, member approval, or a newsletter.
“Send those approved messages” resumes the exact approved batch, not the inbox.
Read the chosen child and the shared [review contract](LINKEDIN_REVIEW_WORKFLOW.md)
before action. Children return to the master for receipt/reporting, not another
recursive full run. Unknown or materially ambiguous scope needs clarification.

## Full cycle

1. Verify account/runtime; load current instructions, publishing map and private
   continuity. Reconstruct unfinished actions and scheduled items before mutations.
2. Triage connection requests first, then Focused/Other inbox and notifications.
   A time-sensitive existing commitment may take priority. Read threads first.
3. Review OpenClaw membership, pending posts and unanswered discussions. Route
   an editorial Good/Bad/Ugly item separately; do not manufacture a daily quota.
4. Inspect a bounded relevant feed slice. Route ideas to the appropriate
   newsletter, retaining public source references rather than private transcripts.
5. Audit all three newsletter lanes, publishing identities, drafts and schedules.
   Advance within authority; a draft is not a publication.
6. Consider relevant existing strategic relationships after inbound obligations.
7. Verify, record and report every queue as checked, completed, waiting, blocked
   or not checked. Run continuity/improvement even when no public action is useful.

## Priority and authority are independent

Use current repository WSP 15 for MPS: Complexity + Importance + Deferability +
Impact, each 1–5; P0 16–20, P1 13–15, P2 10–12, P3 7–9, P4 4–6. The authored
wsp01 APS uses urgency instead; label the chosen rubric and never conflate them.
Neither score grants permission.

Routine acknowledgements and noncommittal technical discussion are researchable
and draftable. Seniority alone is not a reason to stop routine work. Sensitive
relationships, consequential positioning or material commitments need 012's
judgment; contracts, investment terms, financing, endorsements, legal commitments
and sensitive disclosure cannot be authorized by a priority score. Apply the
shared exact-action approval contract to outbound execution. Already approved,
unchanged drafts can be sent without asking again after live recipient/history
checks. A new reply or duplicate invalidates the stale plan: hold or revise for
review, never mechanically send an obsolete introduction.

## Shared voice and identity

Disclose 0102 as the monk's Digital Twin; do not imply the human personally typed
the message. Use FoundUps.com, Foundups-Agent and eSingularity.ai when relevant.
ROC means Return on Compute. Use **YUMORI.me** (including `.me`) for the regional
project, matching the current project/Work identity; do not shorten it. Verify
the canonical destination before linking; resolve a conflicting spelling from
current project evidence or 012, not a guessed domain. Links must advance the
discussion. Avoid generic praise, automatic pitches, compulsory CTAs and
unsupported claims of AGI, secured funding or operating infrastructure.

## Scope and readiness

Work uses the advertised browser skill. Repository action wrappers, simulation
success, historical selectors and dry-run labels are not live-send evidence.
The existing adapter/CLI still require a separate safety audit before unattended
use. No social hooks, recurring scheduler, identity-amplification loop or bulk
outreach is enabled by this routing document. Verify native entity mentions by
exact identity, not the first autocomplete suggestion.

## Audit inventory — 2026-09-22

- Reused: engagement master/bridge, agentic reply, article targeting, group
  moderation and group news. Carried forward the unmerged message-first policy.
- Added instruction-only gaps: inbox, connections, notifications, newsletter
  router plus dedicated FoundUps/ROC/JHR lanes, publishing/scheduling, outreach
  and continuity.
- Existing browser post hunter is discovery only; engagement poster and company
  poster remain legacy action helpers subject to the master approval contract.
- `src/SKILLz.md` is a git-to-social prototype, not the master. Do not execute it
  while committing these changes. The antifaFM skill is a separate campaign and
  excluded from the default LinkedIn cycle; do not retarget it or mine private
  profile data for political persuasion.
- Known runtime gaps remain: simulated DM manager, nested dry-run conflicts,
  unguarded direct action paths and legacy group heuristics. Documentation tests
  do not certify these executors; no unattended execution is claimed.

Validation: local child links/metadata, ownership, narrow/full scope, independent
send/member states, duplicate recovery, newsletter stages and private continuity.
