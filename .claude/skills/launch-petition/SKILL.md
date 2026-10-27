---
name: launch-petition
description: Prepare, launch, resume or update a petition campaign in Foundups-Agent, adopting an existing Change.org or Action Network link or planning human-assisted account setup, evidence checks, supporter updates and social distribution. Use when 012 tells RedDog to launch a petition.
---
# Launch a petition

Follow WSP 00/97 and the existing Social Media Orchestrator campaign owner:
[FoundUp Campaign Operator](../../../modules/platform_integration/social_media_orchestrator/skillz/foundup_campaign_operator/SKILLz.md).
Use its [petition workflow](../../../modules/platform_integration/social_media_orchestrator/skillz/foundup_campaign_operator/references/petition-workflow.md).

Start with `social campaign petition action=preview`, or adopt the provided
public link using `action=plan petition_url=<public_link>`. Follow the
[petition runbook](../../../modules/platform_integration/social_media_orchestrator/docs/PETITION_CAMPAIGN.md).
This route produces a plan only; it does not create accounts or publish posts.
Preserve the distinction between prepared copy, a saved platform draft, a
verified public petition and a delivered social post. Resume the existing
campaign record and platform action instead of creating duplicates.
