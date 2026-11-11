# foundup_campaign_operator

## AntifaFM pilot — 2026-10-18

012 authorized implementation of this existing campaign owner for AntifaFM.
`SKILLz.md` and the existing SOCIAL router now provide explicit operations: offline
preview, verified account check, contextual listener-reply drafts, and verified
own-account X publication. See [the current runbook](../../docs/ANTIFAFM_CAMPAIGN.md).

The skill remains `promotion_state: prototype` and is absent from the production
registry. Installation does not activate the 15-minute social cadence.
Publication defaults off; replies remain drafts.

## Original reservation

This is the module-local location reserved on 2026-06-13 under WSP 95/109/97.
The historical [placeholder audit](../../../../../docs/audits/architecture/FOUNDUP_CAMPAIGN_OPERATOR_SKILLZ_PLACEHOLDER_PHASE1.md)
records the original recommendation → gate → route → execute → publish contract.
This prompt-driven pilot still has no native WRE executor; its canonical
campaign implementation is called through the existing SOCIAL route.

The wider FoundUp intake → creative package → optional creative engine →
AutoPost → analytics arc remains future work. This pilot adds neither a creative
engine nor AutoPost/Facebook/Moltbook transports.
