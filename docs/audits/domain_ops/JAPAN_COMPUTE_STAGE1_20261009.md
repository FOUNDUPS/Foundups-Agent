# Foundups Japan Compute — stage-one landing decision and audit

Date: 2026-10-09 JST. Source baseline: b4f1a97bb2992e391634f83f949da6ee314c11a7.
Status: source implementation for review; NOT a production deployment receipt.

## Decision

One website, not a new platform. Foundups.com is the umbrella. Its new front door explains Foundups Japan Compute, with AI Koban as the local compute-node concept. Navigation: AI Koban / Innovate / EDUIT / Capital. Innovate preserves the existing closed-alpha application. EDUIT is a planned education workload, not current booked demand. Capital is a proposed project-financing structure, not an incorporated/licensed-manager claim or securities offer.

Reuse eSingularity.ai as the project/feasibility authority and YUMORI.me as the civic/community surface. Do not rebrand, replace or clone those sites. Do not create a second EDUIT module, investor database, CRM, fund, payment flow or backend. First qualify demand; then validate a small deployment; replicate only after measured operating economics justify it. The national ambition is privately initiated, not government-designated.

## Corrected findings

- MEXT confirms 7,612 surviving school facilities from FY2004–FY2023 closures, of which 1,951 were unused as of 2024-05-01. This is not the count of all vacant Japanese facilities or of feasible data-center sites. Do not multiply it by arbitrary per-site revenue and call that an addressable-market forecast.
- The earlier claim of a September 2026 MEXT recruitment list was not verified in this audit; omit it.
- Reuters' report was first published October 6 UTC and updated October 7, 2026. It concerns proposed SpaceX financing, not a verified public Musk one-page offer. No evidence of investor payback in under one year was found. No Musk comparison, investment-return calculator or payback claim is published on this page.
- Earlier institutional names were research candidates, not qualified investor leads or confirmed backers. No logos, names or implied endorsements are published. No outreach is performed in this slice, and no completed investor-Rolodex claim is made.
- The preceding response located Drive artifacts but did not audit their full content. This slice reads the repository economic authority and EDUIT owner documentation; it does not claim a completed FIN-workbook recalculation or investor-pitch audit.
- Repository economic authority is demand-led. Legacy 384-GPU/1-MW-style projections are audit scenarios, not the current construction plan. No candidate site has confirmed deliverable kW/MW.
- EDUIT/Play EDUIT is SPECIFIED_NOT_IMPLEMENTED. Internal agent and education aspirations are not contracted external revenue.
- The existing Foundups alpha explicitly excludes accredited investors and entity representatives. Infrastructure inquiries must not be sent through that gate. Reuse the public info@foundups.com mail route instead; no email is sent by this implementation.

## Evidence read

- `AGENTS.md`: incremental execution and existing-owner retrieval.
- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`: retrieve, micro/macro review, alternatives, smallest bounded execution.
- `public/index.html` at baseline, blob `0d0e9ef375458e37e8aec67f4d2211d639c2016a`: existing static landing, alpha access gate, local asset references, Clerk/Firebase/member routing and public contact address. Focused ranges were read; copying uses the full original Git blob, not reconstructed snippets.
- `firebase.json`: existing Firebase Hosting, public directory, `/f/**` routing, static headers and fallback.
- `modules/foundups/esingularity/README.md`: domain ownership and project-status boundaries.
- `modules/foundups/esingularity/docs/YUMORI_ECONOMIC_MODEL.md`: demand sizing, no bankable-demand or confirmed-power shortcut.
- `modules/foundups/eduit/README.md`: independent education FoundUp and planned runtime.
- MEXT: https://www.mext.go.jp/a_menu/shotou/zyosei/yoyuu_00002.htm
- Reuters: https://www.reuters.com/business/media-telecom/spacex-seeks-40-billion-buy-nvidia-chips-ft-reports-2026-10-06/
- Live baseline: https://foundups.com/

Retrieval mode: scoped GitHub connector lexical search plus exact source reads; no local HoloIndex/Qwen/Gemma runtime was available in this tool session. Search noise was reduced by repository scope, owner README and explicit source paths. No semantic freshness acceptance or autonomous-worker execution is claimed. WSP 97 execution-plane classification: presentation-layer change; no new WRE attachment or agent runtime required.

## Source implementation

- New `public/index.html`: Japanese-first, English-switchable static presentation.
- Existing application copied to `public/innovate.html` by original blob SHA. No product/auth/eligibility logic is rewritten in this slice. Its internal navigation and canonical metadata are still legacy; return navigation/SEO are release-review items rather than silently rewritten application code.
- `public/js/japan-compute.js`: language controls and preservation of known legacy product query/hash entry links. No analytics, auth, CRM or payment integration.
- Preserve `/f/**`, member, SSO, legal and existing assets. Any hosting fallback change must preserve the prior application route rather than serving the new marketing page for application callbacks.
- Marketing language distinguishes planned entities, candidate sites, education scope, funding proposals and actual operations. It intentionally offers no financial return.

## Verification and publication gates

Isolated Chromium rendering checked at widths 360, 768 and 1440: Japanese/English content, control state and horizontal overflow; no JavaScript page errors. Static checks cover unique IDs, section anchors, one H1, expected navigation, no forms and no iframe. Node regression checks cover language metadata, URL preservation, known legacy query/hash routing and fixed same-origin navigation.

These are presentation tests, not live authentication/backend tests. The preserved application must be read back by SHA. The full-checkout regression command must validate its baseline blob. Before publication verify the original member/SSO/invite flows at the new entry path, incoming legacy routes, PWA/service-worker behavior, return navigation and canonical metadata. Check official-domain publication through the existing Firebase deployment owner. No deployment credential or confirmed executable Firebase publishing action was available in this session. Do not migrate hosting or install a new site builder to bypass that gap.

## Next small slice

Complete the release-path checks and use the existing Firebase owner to publish this reviewed layer. After production verification, qualify a small first batch of site/customer/capital introductions in the existing governed CONTACTS workbook. Do not expand the backend or present fund terms before the first demand/engineering/legal evidence gates pass.
