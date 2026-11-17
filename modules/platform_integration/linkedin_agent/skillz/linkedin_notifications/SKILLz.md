---
name: linkedin_notifications
description: Triage LinkedIn notifications and route relevant replies without widening the requested scope
version: 1.0.0
author: 0102
agents: [qwen]
intent_type: DISCOVERY
promotion_state: prototype
category: workflow
evals: []
---
# LinkedIn notifications

Read the [master routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md).
Inspect since the private checkpoint, recording bounded coverage. Open relevant
mentions, replies and relationship signals, read the original conversation and
deduplicate against inbox/feed work. A notification is a pointer, not complete
context or evidence of urgency. Route private replies to inbox and public replies
to agentic reply. Ignore low-value noise without muting/blocking unless authorized.
Report actionable items and checked-through time; no automatic likes or pitches.
