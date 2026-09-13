---
name: esingularity-website
description: Update or review the eSingularity.ai and YUMORI.me websites under WSP 97 while preserving their distinct homepages, shared ticker and publication contracts. Use for “apply the website skill” in this FoundUp, website edits, redesigns and publishing reviews.
---

# eSingularity website operations

Owner: `esingularity_001` in `FOUNDUPS/Foundups-Agent`.
Canonical instructions: `modules/foundups/esingularity/skills/website-update/SKILL.md`.
All paths below are repository-relative unless explicitly module-relative.

## Research before editing — WSP 97

Follow the current root AGENTS.md and governing WSP 00/50/97 instructions. Read `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`, then current module README, INTERFACE, ROADMAP, recent ModLog and relevant tests. Use bounded searches and 50–100-line reads; large CSS, ledgers and history should be searched before reading. Do not silently skip missing references.

Resolve the FoundUp through `modules/foundups/foundup_registry.json`. Inspect recent path-specific Git history and relevant PR diffs, then compare current source with the existing Sites source when publishing. Record observed files/revisions, missing evidence and a concise decision summary; do not substitute remembered deployment state for live evidence.

Apply the WSP 97 loop: research → inspect the exact change → inspect adjacent consumers and hosting → challenge the proposed change → choose the simplest valid patch → execute → validate → document. Specifically ask: could this preserve a component file while removing its rendered consumer, replace the other homepage, break a cross-site link, or overwrite newer published work?

## Invariants for every website change

| Surface | Owner / check |
| --- | --- |
| eSingularity.ai project homepage | `frontend/app/page.tsx` |
| YUMORI.me / www movement homepage | `frontend/app/yumori/page.tsx`, selected by host-restricted rewrite in `frontend/next.config.ts` |
| Shared ticker | `frontend/components/CampaignTicker.tsx`, rendered exactly once per homepage; the second scrolling set inside it is intentional |
| Shared announcement | `frontend/content/current-field-status.ts`; never copy event text into either page |
| Project information alias | YUMORI.info externally redirects to eSingularity.ai; do not repurpose its forwarding |
| Publication | One existing Sites project declared in `frontend/.openai/hosting.json` |

Paths in the table are relative to `modules/foundups/esingularity`.

The project page mounts `<CampaignTicker />`; the movement page mounts `<CampaignTicker movement />`. Preserve both mounts even when changing only the hero, navigation, language, deck or imagery. The movement option keeps the ticker in document flow and sends project fragment links to eSingularity.ai. Inspect CSS visibility, clipping, stacking, header offsets and mobile layout when the surrounding layout changes. An import or a passing build alone does not prove a visible ticker.

Both pages retain their separate purposes and join actions. Preserve JHR access, current signup/LINE destinations, Japanese-first language behavior, assets and relevant public claim boundaries from INTERFACE. A shared component does not authorize replacing the movement page with the project page. Explicit requested changes may evolve these contracts; update their owning documentation and checks together rather than silently removing them.

For announcement-only edits, use `.claude/skills/esingularity-ticker/SKILL.md` (Codex projection: `.agents/skills/esingularity-ticker/SKILL.md`). Keep event date, location, end time and link consistent; do not renew an expired invitation unless 012 confirms it. The current ticker has no automatic expiry: flag stale LIVE copy during a website review rather than inventing a new appearance.

## Verification and publication

Run from repository root:

```bash
python -m pytest modules/foundups/esingularity/tests/test_jhr_public_contract.py -q
node --experimental-strip-types --test modules/foundups/esingularity/tests/test_domain_routing.mjs
```

The first test file includes the single-source/both-homepage ticker contract. For homepage edits, also run the relevant existing `test_yumori_national_landing.py` and ticker/deck checks in `test_contracts.py`; run focused lint and the frontend build for executable changes. A documentation-only edit needs skill/link validation, not a website rebuild or redeployment.

If pytest is unavailable, its dependency-free test functions can be invoked directly with `runpy`; label that accurately. Existing suite failures must be compared with the base revision and recorded. Do not remove a ticker assertion merely to make a redesign pass, treat all red CI as harmless, or bypass required merge gates.

For layout changes, inspect both routes at desktop and phone widths in the supported local preview. Confirm the actual ticker text and link, not only the DOM class. For publication, use the available Sites hosting workflow and the existing project. Preserve newer live source, commit/push the exact patch, deploy it, then record the returned outcome. When permitted, verify both custom domains independently; if access is blocked, distinguish source tests, successful deployment and unverified custom-domain rendering.

Update module ModLog with why, affected surfaces, WSP references, validation and actual publication status. Update INTERFACE/README/ROADMAP only where the contract or workflow changed. Use the authorized branch/PR/squash workflow. Never report a Git merge as a production deployment.

## Red Dog boundary and discovery

This is a FoundUp-owned workflow skill, not a new autonomous executor. Red Dog's existing registered-FoundUp path can discover it through the module README and registry `evidence_docs`. `.claude/skills/esingularity-website/SKILL.md` and its `.agents` projection are thin entrypoints; maintain instructions here once.

If dispatched through Red Dog/WRE, retain its signed work-order, allowed-path, verifier, scanner and promotion requirements. Registry evidence and a request to “apply the website skill” do not install runtime capabilities, grant credentials or override the FoundUp manifest's declarative-only build boundary. A directly authorized repository/website edit uses the available tools for that execution context; do not invent Red Dog activation receipts.

## Verified change history behind these checks

- `6e83ea6` / PR #1684: the reconciled project-page diff removed both the CampaignTicker import and mount while adding the shared-host domain split. This establishes where the mount disappeared in Git; it does not establish intent or an unseen live-edit sequence.
- `44da8ed` / PR #1686 restored the join-first movement page; `08d0056` / PR #1687 made the two-homepage contract explicit.
- `3a3007b` / PR #1690 restored the project-page ticker and updated its single status source.
- `cc7de15` / PR #1691 mounted the same ticker on YUMORI.me and added both-consumer assertions. Reuse those checks rather than inventing a parallel ticker system.

These are historical evidence, not current HEAD or deployment receipts. Re-read current source before each edit.
