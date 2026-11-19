---
name: linkedin_inbox
description: Read LinkedIn inbox history, triage replies and execute an exact approved message batch without duplicates
version: 1.0.0
author: 0102
agents: [qwen]
intent_type: COMMUNICATION
promotion_state: prototype
category: workflow
evals: []
---
# LinkedIn inbox

Read the [master routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md).
This is an instruction-only activity; do not use simulated messaging as delivery.

1. Resolve the signed-in account and requested scope: named thread, approved batch
   or inbox review. Retrieve the private last-checked checkpoint and coverage gaps.
2. For inbox review inspect Focused, Other and unread filters; include answered
   versus unanswered and prior outreach replies, not just unread counts. Bound
   pagination/time range and report gaps; absence from a search is not no history.
3. Resolve each profile and read the full relevant thread, including prior 0102
   messages. Opening the actual composer can reveal history that search missed.
4. Classify no action, ordinary response, information request, waiting or human
   decision. Priority and permission are separate; do not escalate just for rank.
5. Draft in the established language/voice, with one relevant substantive point.
   Resolve links and factual claims; disclose 0102. Do not download attachments.
6. For an exact approved batch, match recipient/profile and draft, then re-read
   the live thread immediately before sending. Do not seek the same approval again.
   Hold an obsolete or repetitive draft when new history/replies change context.
7. Send once through the allowed UI. Verify the rendered outgoing entry and
   timestamp; distinguish sent from seen/replied. On timeout after possible send,
   read back first; if uncertain, mark unknown and stop, never blindly retry.
8. Return sent / held-duplicate / waiting / needs-review / failed / unknown with
   private verification references and next owner to continuity. Do not mutate
   connections, group membership or unrelated queues from a message-only task.

Acceptance cases: approved unchanged reply -> send and verify; already asked the
same question -> hold; new inbound reply -> revise; empty composer after timeout
-> inspect history, not resend; missing Other access -> report incomplete coverage.
