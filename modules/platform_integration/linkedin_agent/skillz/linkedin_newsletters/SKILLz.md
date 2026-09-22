---
name: linkedin_newsletters
description: Master LinkedIn newsletter router that dispatches FoundUps Eat the Startup, ROC Return on Compute and Japan Hyperscaler Report to separate lane skills
version: 1.3.0
author: 0102
agents: [qwen]
intent_type: CONTENT_GENERATION
promotion_state: prototype
category: workflow
evals: []
---
# LinkedIn newsletter router

Read [research verification](references/research-verification.md) before research
or editorial prioritization. Use Google Docs as the working manuscript when
developing an issue; keep session learning separate from model training.

Read the [master routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md).
Read the [editorial orchestration contract](references/editorial-workflow.md) for
Red Dog -> 0102 handoffs, evidence-backed audits, collaborative issue development
and new-series onboarding. Reuse the [issue brief](assets/issue-brief.md) and
[new newsletter child template](assets/newsletter-skill-template.md).
Use [article targeting](../linkedin_article_targeting/SKILLz.md) and current live
publisher/series identity, never a guessed newsletter URL or historic count. Select
one or all of these dedicated lanes:

| Request | Dedicated skill | Boundary |
| --- | --- | --- |
| FoundUps, Eat the Startup, or contextually clear “BoundUps” | [linkedin_foundups_newsletter](../linkedin_foundups_newsletter/SKILLz.md) | Verified Foundups-Agent implementation translated into founder benefit |
| ROC or Return on Compute | [linkedin_roc_newsletter](../linkedin_roc_newsletter/SKILLz.md) | Personal compute-economics corpus and current evidence |
| Japan Hyperscaler Report or JHR | [linkedin_jhr_newsletter](../linkedin_jhr_newsletter/SKILLz.md) | Significance-gated Japan infrastructure reporting |

A named newsletter request loads only its lane. A full LinkedIn/newsletter audit
loads all three and reports each independently. “BoundUps” is not a canonical
identity; normalize it to FoundUps only when context is clear, never create a new
series. Each lane may produce `NO_ACTION`, and JHR may produce `NO_REPORT`.
“Run [newsletter]” means inspect live state and evidence, then advance to the next
truthful stage allowed by current authority; it never implies publish, schedule,
series creation or a language choice. Report the missing choice only when it blocks
the next requested stage.

An audit is inventory/reporting; development is a separate selected mode. Discover
additional accessible series and flag UNMAPPED_SERIES rather than treating three
known lanes as an exhaustive live account inventory. Report NOT_CHECKED_LIVE for a
repository-only audit. Preserve artifact revisions and return receipts to Red Dog.

For each selected lane inspect latest issue, published subjects, drafts, subscriber
state and schedules; label unavailable surfaces. A full cycle covers all three.
When development is requested, develop the next issue from evidence and conversations without
exposing private correspondence. Group intelligence becomes a sourced idea, not
an automatically published article. Do not assume a suggested title is final.

Track editorial `IDEA -> RESEARCHED -> DRAFTED -> REVIEWED -> APPROVED` and
delivery separately: `NOT_PLACED`, `DRAFT_SAVED_VERIFIED`, `SCHEDULED_VERIFIED`,
`PUBLISHED`, `VERIFIED_LIVE`, `UNKNOWN_SUBMISSION` or `BLOCKED_IDENTITY`.
Research primary sources, check claims/links, review exact copy and destination,
then route approved publication through publishing. Use factual project imagery
only after source/asset inspection. Verify draft persistence and publication
separately. Report stage, evidence, missing work and next owner for every lane;
never report a newsletter completed because its draft exists.
Report editorial progress separately from delivery: an unresolved publisher/series
can yield DRAFTED / BLOCKED_IDENTITY without stopping useful local drafting.
