# New newsletter child template

Non-executable asset. First verify that no existing lane/series already owns the
request. Copy the block to `skillz/linkedin_<lane>_newsletter/SKILLz.md` only for a
justified new lane; replace all placeholders and validate links from that location.

```markdown
---
name: linkedin_{{lane}}_newsletter
description: Audit, develop and maintain {{series_title}} for {{audience_and_subject}}
version: 1.0.0
author: 0102
agents: [qwen]
intent_type: CONTENT_GENERATION
promotion_state: prototype
category: workflow
evals: []
---
# {{series_title}}

Read [master routing](../../docs/LINKEDIN_ACTIVITY_ROUTING.md),
[newsletter router](../linkedin_newsletters/SKILLz.md), and
[editorial workflow](../linkedin_newsletters/references/editorial-workflow.md).

## Identity and scope

Audience: {{audience}}. Editorial promise: {{unique_promise}}.
Source owner: {{canonical_source_paths}}. Exclusions: {{neighboring_lanes}}.
Publisher / series discovery leads: {{verified_ids_or_unknown}}.
Language / cadence proposal: {{language_and_cadence}}.
Inspect live history, drafts and schedules; never invent identity or duplicate a
series. Missing identity blocks placement, while research/local drafting can proceed.

## Editorial contract

{{lane_specific_sources_significance_claim_rules_and_outline}}
Use the shared issue brief; preserve artifact revision and feedback. Distinguish
evidence, inference and authored thesis. Respect privacy and current naming.

## Completion and integration

Report editorial and delivery states separately with evidence and next owner.
Route exact authorized outward actions through linkedin_publishing; verify saved
draft, scheduled entry and live permalink independently. Creation does not publish
the first issue and cadence does not start a scheduler.
Connect this child in the master, newsletter router and Work routing. Reuse the
existing activity-contract tests. No new executor or memory authority is implied.
```
