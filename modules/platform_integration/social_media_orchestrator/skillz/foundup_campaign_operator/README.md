# foundup_campaign_operator (SKILLz PLACEHOLDER)

**execution_status**: PLACEHOLDER_NO_EXECUTION
**WSP**: WSP 95 (Wardrobe placement), WSP 109 (intake evidence), WSP 97 (truth boundary)
**Authority**: NOT authorized. No executor exists. Loading this skill fails closed.
**Contract / audit**: `docs/audits/architecture/FOUNDUP_CAMPAIGN_OPERATOR_SKILLZ_PLACEHOLDER_PHASE1.md`

---

## What this is

This folder **reserves** the canonical module-local wardrobe location for a future
**FoundUp Campaign Operator SKILLz**. It is a placeholder contract only.

It is placed here (next to the existing `antifafm_linkedin_post/` SKILLz) because WSP 95
states "skills belong WITH the modules they serve": the campaign operator serves social
distribution / orchestration. Placement rationale and the rejected alternatives (repo-root
`skillz/`, the not-yet-existent `modules/foundups/skillz/`, and `.claude/skills/`) are in
the audit doc above.

## What this is NOT (hard boundary)

- No `SKILLz.md` and no `executor.py` -- intentionally absent until authorization.
- No live campaign execution, no scheduling, no runtime executor.
- No Runway (or any external creative engine) API; no availability assumption.
- No AutoPost execution, no posting, no account auth, no secrets, no browser automation.

The WRE skills loader resolves skills by name to `SKILLz.md` / `SKILL.md` only and never
loads `README.md`. With no `SKILLz.md` present, any attempt to load
`foundup_campaign_operator` raises `FileNotFoundError` -- the intended fail-closed state
for an unauthorized placeholder.

## Intended arc (future, not built here)

```
WSP 109 FoundUp intake -> campaign brief -> creative package request
  -> optional external creative engine -> AutoPost / social distribution -> analytics feedback
```

## Governance (recommend -> gate -> route -> execute -> publish)

1. RedDog recommends (`CampaignWorkOrder`, authority_tier: recommend_only).
2. OpenClaw gates (`PolicyGateReceipt`: POLICY_ACCEPT / POLICY_REJECT /
   POLICY_ACCEPT_WITH_RETRIEVAL_GAP; no_execution_performed: true).
3. Hermes routes an authorized order to the executor module_path.
4. WRE / SKILLz executes only after future authorization (012 / DAO go).
5. AutoPost / social modules publish only behind policy.

## Contract summary

See the audit doc for the full non-executing `CampaignBrief` / `CampaignWorkOrder` schema
(foundup_id, WSP_109 evidence refs, target audience, pain/outcome/solution, CTA, platform
matrix, creative asset requests, brand voice, compliance constraints, KPI targets,
analytics feedback).

## Promotion path

`FOUNDUP_CAMPAIGN_OPERATOR_SKILLZ_AUTHORING_PHASE1` (GATED on 012 / DAO authorization) is
the first slice that may add `SKILLz.md` + `executor.py` and make this skill loadable.
