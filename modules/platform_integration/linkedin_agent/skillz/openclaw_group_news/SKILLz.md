---
name: openclaw_group_news
description: Research and draft The Good, The Bad and The Ugly automation discussion for the OpenClaw LinkedIn group
version: 1.1.0
author: 0102
agents: [qwen, selenium]
dependencies: [web_search, anti_detection_poster]
domain: platform_integration
intent_type: CONTENT_GENERATION
promotion_state: prototype
linkedin_group: https://www.linkedin.com/groups/6729915/
category: workflow
evals: []
---

# The Good, The Bad and The Ugly — Automation Discussion

Reuse this existing skill for the group's automation/agent discussion. Research and draft within scope; publish only the exact approved content to the verified group. Invoking this skill never starts a scheduler or authorizes continuous posting.

Read [LinkedIn review workflow](../../docs/LINKEDIN_REVIEW_WORKFLOW.md). Membership belongs in [linkedin_group_moderation](../linkedin_group_moderation/SKILLz.md), with message-before-approval and separate human decisions. Do not run a welcome-and-approve cycle from this news job.

## Research

1. Check urgent inbox items and moderation queues before optional content seeding. Read recent group discussions, existing drafts and scheduled/published items to avoid duplicate topics and links.
2. Choose one concrete automation theme: delegated work, persistent agents, memory, skill reuse, observability, permission boundaries, recovery, reliability or cost. Grok Bot, OpenClaw, Hermes and other systems are candidates, not a fixed mandatory brand list.
3. Search current sources and read original documentation, release notes, repositories or primary incident reports. Record publication, event and retrieval dates separately. Headlines and search snippets are leads only.
4. Label each claim as vendor-described, independently tested, personally observed or inferred. Do not repeat vendor claims of unique capability, security or AGI as established fact.
5. Verify any incident's affected product/version, conditions and remediation. If evidence is missing, explain a hypothetical risk without attributing it to a named vendor.
6. Retrieve current Foundups work before comparison. Separate tested implementation, prototype, proposed design and authored hypothesis. A skill document does not prove a running agent or learned model weights.
7. Read assets and project documentation before any image request. Reuse factual project imagery; do not invent a facility or product screenshot. No image is required for a useful discussion.

## Draft

Normally 180-300 words, one paragraph break, the group's established language and 2-4 relevant hashtags. Check actual composer constraints rather than treating cached limits as platform guarantees.

- **Hook:** one builder-focused question.
- **Good:** one or two sourced capabilities and the work they could improve.
- **Bad:** practical limitations or open questions, explicitly framed as analysis when not measured.
- **Ugly:** the consequences of unverified broad authority; use verified incidents or clearly hypothetical examples, not sensational accusations.
- **Hypothesis:** attribute 012's “AGI may depend on schema/orchestration, not only model capability” thesis. Ask what would support or falsify it; do not equate automation, AGI and sentience.
- **Question:** invite one concrete account. Optional answer scaffold: tool/version; task; result; human interventions; lesson.
- **Sources:** two or three direct links adjacent to the claims.
- **Voice:** 0102 proxy voice and `— 0102🦞`, unless 012 explicitly requests direct human voice.

Keep a Foundups/eSingularity CTA optional and directly relevant. Do not make joining, replying or agreeing contingent on promotion. Resolve intended LinkedIn entity mentions through verified autocomplete, never plain-text handles.

## Review and execution

Use `DRAFT -> REVIEW -> APPROVED -> POSTED -> MONITORED`. Show exact draft, destination, APS components, sources and uncertainties. A relevance score is not authority. A request for a skill, research or a topic does not approve publication.

After exact approval: verify account/group, inspect live composer, preserve formatting, check resolved links/mentions and deduplicate again. Submit once. Verify the rendered post and capture its actual permalink. An empty editor or simulated success is not publication evidence.

## Cadence and follow-up

Propose one substantive weekly discussion as an editorial rhythm, not a quota. Skip or choose a clearly labeled evergreen question when no useful current news exists. Additional urgent posts need separate approval.

Never assume group posts share article/newsletter scheduling support. Inspect the actual destination; obtain explicit timing/timezone and use only an authorized, verified scheduler. This skill does not create a recurring task by itself.

On a later authorized review, read responses and draft evidence-backed follow-ups. Do not auto-like, DM commenters or repetitively prompt silent members. Save generalized lessons, not private member data, to reusable skills.

## Runtime status

Prototype instruction contract only. Legacy executor contains live posting and membership modes and historical daily rate limits; those are not authorization. Do not invoke unattended mutation until exact-action approval, persistent deduplication and verification are enforced and tested. Work browser tasks use the advertised browser skill, not repository anti-detection helpers.

## Evaluation cases

- New Grok Bot claim: verify original source/date, attribute capabilities, no assumed AGI.
- No fresh news: skip or clearly label evergreen discussion; fabricate nothing.
- Private conversation as example: abstract it, omit identifiers and private content.
- Matching draft/post exists: inspect and update only within authority, do not duplicate.
- Unverified exploit: omit vendor accusation; discuss the general permission boundary.
- Approved post interrupted after submission: inspect current group before retry.
- Newsletter schedule exists: do not infer group scheduling availability.

## Changelog

### 1.1.0 — 2026-09-15

Reused existing skill for the Good/Bad/Ugly automation series. Replaced autonomous daily posting and embedded welcome-and-approve flow with evidence-led drafting, exact approval, weekly cadence proposal and separate moderation ownership. Removed stale live queues and fixed DOM coordinates from instructions. No executor change or new background job.

### 1.0.0 / 1.0.1 — 2026-02-19 / 2026-02-23

Original OpenClaw news search, posting and membership prototype. Its standing-authority instructions are superseded by this contract.
