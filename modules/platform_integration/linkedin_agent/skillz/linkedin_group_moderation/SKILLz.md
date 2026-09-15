---
name: linkedin_group_moderation
description: Review LinkedIn group requests and posts with researched message-first outreach and explicit human approval
version: 1.1.0
author: 0102
agents: [qwen, selenium]
dependencies: [browser_actions, anti_detection_poster]
domain: platform_integration
intent_type: MODERATION
promotion_state: prototype
linkedin_group: https://www.linkedin.com/groups/6729915/
linkedin_admin: https://www.linkedin.com/groups/6729915/manage/membership/requested/
category: workflow
evals: []
---

# LinkedIn Group Moderation

Research and draft autonomously within scope; send, approve, deny, connect or change access only with exact user authorization. This instruction contract does not certify the legacy executor as compliant.

Read [LinkedIn review workflow](../../docs/LINKEDIN_REVIEW_WORKFLOW.md) first. Load wsp00 -> wsp01 -> wsp02 and verify the signed-in account and group. The master review order is messages (Focused + Other) -> group queues -> relevant feed. A selected job or urgent item can override order.

## Membership preflight

Inspect automatic member approval on the live Requests page. The intended mode is **Members require admin approval to join**. Report drift; change only with explicit authorization. After an authorized change, save and reopen the page to verify persistence. A historical Off observation is not a current guarantee.

## Message before membership approval

1. Resolve each applicant from the exact pending row and profile URL.
2. Search prior conversations first; read any match. A no-match search is bounded evidence, not proof of no prior relationship.
3. Read actual profile work, experience and recent activity. Distinguish original posts from reposts. Use established writing/conversation for language. Limited activity means uncertainty.
4. Screen risk from corroborated evidence. Never approve or deny solely because of photo, avatar, title, connection count, nationality or location. Do not automatically connect to executives.
5. Draft one relevant question grounded in their work: an automation use case, OpenClaw/Hermes experience, a human approval boundary or evidence for AGI. Introduce 0102 as 012's AI proxy; do not pretend the human personally wrote it.
6. Explain the group's purpose without fear-based job-loss pitches, link piles or compulsory newsletter subscriptions. A join request permits relevant discussion, not blanket marketing consent.
7. Submit exact recipient, profile evidence, APS components, full draft and recommendation for 012 review. Authorization to send is separate from permission to accept/deny.
8. After message approval, inspect the live row menu, select the labeled Message action, reconfirm recipient, send once and verify the actual conversation entry. Never use a guessed menu ordinal.
9. Leave the application pending for engagement and 012's separate membership decision. If pre-approval messaging is unavailable, stop at draft; never approve just to unlock a DM.
10. Silence, agreement or disagreement is not an automatic disposition. Propose any follow-up or membership action for review.

States: `unreviewed -> researched -> draft_ready -> approved_to_message -> sent_verified -> awaiting_reply -> membership_decision_pending -> approved|declined`. On interruption after a possible send, inspect history before retrying. Sending or receiving a reply never automatically accepts the request.

## Pending posts

Read the complete submission and linked evidence within safe browsing rules. Recommend `approve`, `request_revision`, `hold` or `reject` against actual group rules. Explain why. Product news can be relevant while a subscription pitch needs a discussion-oriented rewrite.

Do not auto-delete promotion or post accusatory callouts. Do not invent security allegations. Check displayed expiry and record uncertainty. Require exact approval for moderation, comments and author messages.

## Weekly discussion

Use [openclaw_group_news](../openclaw_group_news/SKILLz.md) for The Good, The Bad and The Ugly automation discussion. This is not a newsletter editor or an approve-and-post follow-on action.

## Runtime boundary and continuity

Use the approved runtime for the current surface. In ChatGPT Work, use its browser skill, not repository Selenium/session files or anti-detection helpers. Inspect fresh DOM and recover within that tool's documented limits; never bypass platform controls.

The existing executor and membership DAE retain legacy triage and live-action paths. Do not launch their live modes under this contract until approval tokens, delivery verification, deduplication and fail-closed guards are implemented and tested. A dry-run label alone does not prove absence of side effects.

Keep private receipts of source IDs, timestamps/timezone, coverage, approvals, verified state changes, unresolved items and next triggers in the authorized account-scoped journal. Never commit member dossiers or message bodies to public source control. See the shared workflow for minimal receipt fields.

## Validation scenarios

- No photo, substantive builder history: research and draft, no automatic rejection.
- Executive applicant: no automatic acceptance or connection.
- Existing conversation: continue its context, no duplicate cold intro.
- Approved welcome sent: application stays pending.
- No pre-approval DM control: leave pending, report blocker.
- Auto-approval On without authorization to change: report; do not mutate.
- Promotional but relevant post: propose a revision, no automatic deletion.

## Changelog

### 1.1.0 — 2026-09-15

Replaced photo/title shortcuts and fear-based templates with evidence-based message-first review, separate approval states, settings verification and private continuity. Retained skill identity and prototype status; no executor/runtime safety claim.

### 1.0.0 — 2026-03-15

Initial moderation, membership and profile-intelligence workflow. Historical instructions are superseded by the contract above.
