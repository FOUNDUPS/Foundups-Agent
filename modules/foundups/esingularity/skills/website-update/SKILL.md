---
name: esingularity-website
description: Update or review eSingularity.ai or YUMORI.me under WSP 97, preserving shared branding, distinct homepages, the ticker and publication contracts. Use for the eSingularity skill, YUMORI.me skill, or website edits, redesigns and publishing reviews in this FoundUp.
---

# eSingularity website operations

Owner: `esingularity_001` in `FOUNDUPS/Foundups-Agent`.
Canonical instructions: `modules/foundups/esingularity/skills/website-update/SKILL.md`.
All paths below are repository-relative unless explicitly module-relative.

## Shared brand context and language — both sites

Do not define or rename FoundUp branding in this Skill. Load the current
`brand_context_path` from the canonical `foundup_registry.json`, then apply
`modules/foundups/esingularity/brand_context.json`. The registry-grounded
context currently resolves the project identity and its child movement identity,
including canonical spelling, aliases, public domains, default locale, JOIN copy,
and the bilingual guardian lockup.

This Skill owns website behavior around that identity, not the identity itself:

- preserve the separate eSingularity project homepage and child movement homepage;
- use the active grounded child brand for movement headings, buttons, ticker copy,
  and participation copy instead of hard-coding a second spelling here;
- natural references to a human role may follow the exception declared in the
  brand context;
- lowercase URL hosts, internal code identifiers, and historical quotations are
  not automatically branding errors;
- Japanese remains the default unless the active brand context changes it;
- translate all non-brand UI completely when another locale is selected;
- on narrow screens, do not clip the active brand, guardian lockup, or report name.

JHR remains a website/report label rather than a FoundUp brand. Preserve:
`ジャパン・ハイパースケーラー・レポート（JHR）を読む →`,
`日本の大規模データセンター開発と、地域の選択肢を知る`, and
`Japan Hyperscaler Report (JHR)` where their current surfaces require them.

For future branding changes, edit the FoundUp brand-context file once and run the
brand-context regressions. Do not sweep every Skillz file for replacement text.
A brand-context edit alone does not authorize a site, form, DNS, or hosting change.

## Research before editing — WSP 97

Follow the current root AGENTS.md and governing WSP 00/50/97 instructions. Read `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`, then current module README, INTERFACE, ROADMAP, recent ModLog and relevant tests. Use bounded searches and 50–100-line reads; large CSS, ledgers and history should be searched before reading. Do not silently skip missing references.

Resolve the FoundUp through `modules/foundups/foundup_registry.json`. Inspect recent path-specific Git history and relevant PR diffs, then compare current source with the existing Sites source when publishing. Record observed files/revisions, missing evidence and a concise decision summary; do not substitute remembered deployment state for live evidence.

Apply the WSP 97 loop: research → inspect the exact change → inspect adjacent consumers and hosting → challenge the proposed change → choose the simplest valid patch → execute → validate → document. Specifically ask: could this preserve a component file while removing its rendered consumer, replace the other homepage, break a cross-site link, or overwrite newer published work?

## Select the site and its goal before editing

| Target | Purpose | Visitor goal | Edit boundary |
| --- | --- | --- | --- |
| eSingularity.ai (also reached through YUMORI.info) | Explain the Fukui onsen reuse proposal: facility, COG DC, learning and regional revitalization | Understand the proposal and evidence, then participate through YUMORI.me | `frontend/app/page.tsx` and its necessary dependencies |
| YUMORI.me / www | Build the wider YUMORI.me movement and preparatory committee through the WHY / WHAT / HOW case | Become a YUMORI.me, join the committee and reach supporting information | `frontend/app/yumori/page.tsx` and its necessary dependencies |
| Shared ticker | Carry one current campaign announcement across both sites | Find the confirmed action, place, time and destination | Shared component and `current-field-status.ts`; verify both consumers |

“Apply the website skill” applies the workflow to the site named in the request or established by the active task. It does not mean redesign both sites. State the target, requested outcome and bounded edit scope briefly before editing. If the target truly cannot be resolved from the request and visible context, ask one short question before a page-specific mutation.

An eSingularity redesign must leave YUMORI.me's content, order and join funnel intact. A YUMORI.me edit must preserve the project page. Shared CSS, language handling, navigation helpers and hosting can affect both: inspect their consumers, scope page-specific styling and regression-check the other site. Checking the other page does not authorize redesigning it. A shared ticker update intentionally reaches both.

### Current eSingularity redesign direction — specified, not yet implemented by this skill change

012 requests a more focused project experience with **three to four primary navigation tabs**, replacing the overloaded top-level menu. This direction applies to eSingularity.ai only. Group the existing project material around a clear visitor journey; keep supporting detail reachable without making every topic a primary tab. Preserve JHR discoverability, participation actions and the shared ticker. Do not count language controls or a participation button as extra content tabs.

Choose the actual labels and grouping from the current redesign brief and source; do not invent approved labels or delete evidence simply to meet the tab count. Keep desktop and mobile navigation consistent. Record the final grouping and validation when implemented. The three-to-four-tab target is a design requirement, not a claim that the live navigation has already changed.

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

For YUMORI.me landing or shared ticker layout changes, check phone widths (320–390 CSS pixels) and an 11-inch iPad in portrait and landscape (for example 834×1194 and 1194×834), plus desktop. Distinguish viewport simulation from testing actual Safari hardware. Verify the document does not overflow horizontally, the full wordmark and JOIN actions fit, and language controls have their own header slot rather than floating across the ticker. Inspect loaded images and captions; distinguish concept imagery from photographs of completed facilities. Do not infer a broken image merely from an empty hero.

Ticker speed should be measured in pixels per second, with slower phone/tablet values; a fixed loop duration makes longer announcements race across the screen. Verify a touch-accessible way to stop and read every item, resume behavior, keyboard access, and reduced motion. Check both rendered consumers, including expanded reading mode. If preview is unavailable, record that visual validation remains incomplete; a build is not a visual audit.

For layout changes, inspect both routes at desktop and phone widths in the supported local preview. Confirm the actual ticker text and link, not only the DOM class. For publication, use the available Sites hosting workflow and the existing project. Preserve newer live source, commit/push the exact patch, deploy it, then record the returned outcome. When permitted, verify both custom domains independently; if access is blocked, distinguish source tests, successful deployment and unverified custom-domain rendering.

Update module ModLog with why, affected surfaces, WSP references, validation and actual publication status. Update INTERFACE/README/ROADMAP only where the contract or workflow changed. Use the authorized branch/PR/squash workflow. Never report a Git merge as a production deployment.

## Red Dog boundary and discovery

This is a FoundUp-owned workflow skill, not a new autonomous executor. Red Dog's existing registered-FoundUp path can discover it through the module README and registry `evidence_docs`. `.claude/skills/esingularity-website/SKILL.md` and `.claude/skills/yumori-website/SKILL.md`, with their `.agents` projections, are thin entrypoints to this same workflow and branding section; maintain instructions here once. “YUMORI.me skill” selects the movement-site entrypoint; “eSingularity skill” uses the named or active project scope above. Normalize obvious campaign-context speech-recognition variants to YUMORI.me without creating a differently named brand or skill.

If dispatched through Red Dog/WRE, retain its signed work-order, allowed-path, verifier, scanner and promotion requirements. Registry evidence and a request to “apply the website skill” do not install runtime capabilities, grant credentials or override the FoundUp manifest's declarative-only build boundary. A directly authorized repository/website edit uses the available tools for that execution context; do not invent Red Dog activation receipts.

## Verified change history behind these checks

- `6e83ea6` / PR #1684: the reconciled project-page diff removed both the CampaignTicker import and mount while adding the shared-host domain split. This establishes where the mount disappeared in Git; it does not establish intent or an unseen live-edit sequence.
- `44da8ed` / PR #1686 restored the join-first movement page; `08d0056` / PR #1687 made the two-homepage contract explicit.
- `3a3007b` / PR #1690 restored the project-page ticker and updated its single status source.
- `cc7de15` / PR #1691 mounted the same ticker on YUMORI.me and added both-consumer assertions. Reuse those checks rather than inventing a parallel ticker system.

These are historical evidence, not current HEAD or deployment receipts. Re-read current source before each edit.
