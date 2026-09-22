---
name: linkedin_roc_newsletter
description: Research, draft, maintain and publish the personal ROC Return on Compute LinkedIn newsletter or article lane without confusing it with FoundUps engineering or JHR infrastructure reporting
version: 1.0.0
author: 0102
agents: [qwen]
intent_type: CONTENT_GENERATION
promotion_state: prototype
category: workflow
evals: []
---
# ROC — Return on Compute newsletter

Read the [newsletter router](../linkedin_newsletters/SKILLz.md) and [master
routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md). This skill owns only
the personal ROC / Return on Compute lane. ROC never means “Return on View.”

## Identity and corpus discovery

1. Inspect the live personal profile, newsletter list, published articles, drafts
   and schedules. The audited publishing map has ROC-related personal articles but
   does **not** identify a verified ROC newsletter series. Do not invent a series,
   URL, subscriber count or cadence, and do not silently substitute a normal article.
2. Retrieve the historical baseline from PR #202 and
   `src/content/articles/ROI_to_RoC_Paradigm_Shift.md`, plus later canonical ROC
   definitions in current FoundUps economic documents. Treat the historical article
   as corpus evidence, not current factual verification or an automatic next edition.
3. Read all published ROC pieces and unfinished drafts before selecting a subject.
   Use recent conversations only as private idea leads; never expose private text.

## Research and editorial contract

Develop a falsifiable compute-economics argument about the shift from capital/labor
metrics toward compute coordinated with memory, agents and execution. Define the
metric used in that edition: economic thesis, simulator formula or another bounded
measure. Do not slide between definitions without disclosure.

Verify volatile claims—markets, wars, energy prices, employment forecasts, laws,
company actions and quoted public figures—from current primary sources. Attribute
FoundUps/012 theses as authored arguments. Do not repeat dramatic predictions from
the historical corpus as established facts. Distinguish empirical result, model
output, scenario, inference and rhetoric. Engage ROI fairly; do not force ROC into
an unrelated news event merely because the acronym fits.

Use the personal 012/0102 corpus voice selected for the exact draft. Preserve
FoundUps.com as supporting platform evidence when relevant, not a compulsory CTA.
Before publication verify whether the destination is the actual ROC newsletter,
a personal article or a different series, and obtain approval for that exact surface.

## Completion

Track the shared newsletter stages. Route exact approved content through
`linkedin_publishing`; verify saved draft, schedule and live permalink independently.
Record which ROC definition and sources were used, counterarguments addressed and
the next open question. No verified series identity means `BLOCKED_IDENTITY`, not
permission to create or publish elsewhere.
