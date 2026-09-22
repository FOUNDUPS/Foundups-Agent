---
name: linkedin_connections
description: Review LinkedIn connection requests against existing policy and profile evidence with independent message and connection decisions
version: 1.0.0
author: 0102
agents: [qwen]
intent_type: DECISION
promotion_state: prototype
category: workflow
evals: []
---
# LinkedIn connections

Read the [master routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md) and
reuse [connection_manager.py](../../src/engagement/connection_manager.py).
Do not replace its policy with a new title-regex system or call its live methods
merely to inspect policy.

Inspect each pending request, prior thread, real business, relevant activity and
relationship. Founders/CXOs, senior technical/research leaders and relevant
compute/infrastructure principals are positive fit signals. Generic marketing,
BD, recruiting and outsourced lead-gen pitches are negative fit signals; context
matters and job title alone does not establish fraud. Use available profile
intelligence for ambiguity, label missing evidence and never treat model output
as authorization or identity proof.

Recommend accept, reject, contextual question or needs review. Where useful,
draft a natural 0102 question about what they are actually building in AI,
compute or infrastructure. Do not mechanically send a rejection template.
Apply exact approval separately to messages and accept/reject operations. Route
DM execution through [linkedin_inbox](../linkedin_inbox/SKILLz.md); verify each
connection-state change from the live queue/profile. No auto-connect to group
members. Return reviewed/accepted/rejected/messaged/held counts and evidence.
