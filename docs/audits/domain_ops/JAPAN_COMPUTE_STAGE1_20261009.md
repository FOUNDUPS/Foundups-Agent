# Foundups Japan Compute — stage-one landing decision and audit

## Latest revision — investor audience, 2026-10-09 JST

Source baseline for this revision: draft PR #2113 at `c43816288b093dea2601a7f58007b7d89b18dfb6`. This entry supersedes the earlier public copy, not the existing project economic authority. Status remains DRAFT / NOT MERGED / NOT DEPLOYED.

### Audience correction

012 identified that “Japan-wide possibility” and “Discuss a partnership” did not address the investor audience. The page now leads with “Who owns the compute?” and immediately asks who uses/pays, whether access is affordable, and where investor return comes from. The primary action is **Read the investment brief**, which leads to actual on-page material, not a meeting request or nonexistent prospectus. The secondary action is **Review the economics**. Capital enquiries remain outside Innovate's alpha admission gate.

The proposed ownership story distinguishes the project SPV, equipment, building rights, operator and customer. No customer-data ownership is implied. Foundups Capital Group / Japan remain proposed structures. The page is pre-offering development information, not a statutory prospectus; naming a page does not settle applicable solicitation/registration requirements. No funds, subscriptions, signatures or investment commitments are collected.

### National arithmetic and source boundary

MEXT was re-read on 2026-10-09: 8,850 school closures during FY2004–FY2023; 7,612 surviving facilities; 1,951 unused, as of 2024-05-01. The approximately 10% unused-school illustration uses 195 sites. The principal's rounded 8,000 × 10% idea is preserved as a separate **800-site ambition**, explicitly not 10% of the unused inventory; 800/1,951 is approximately 41%. Neither selection is a verified pipeline, conversion probability or deployment target.

The existing `modules/foundups/esingularity/data/yumori_planning_assumptions.json` (blob `9bfaf15a6809c9de1f08a36bfc05d7a18609c559`) already contains a costed Hanyu hypothesis. Do not substitute the older 384-GPU scenario or create a competing financial engine.

Reference arithmetic: `ceil(360000 / (8760 × 0.75 × 8)) = 7` eight-GPU servers; 56 GPUs; `(7 × 10.2 + 6) = 77.4 kW` maximum IT load; `77.4 × 1.35 = 104.49 kW` maximum facility load. NVIDIA's 8-GPU / 10.2 kW specification was independently rechecked; other IT, PUE, demand and hardware selection remain planning assumptions, not measured engineering results. This is a physical capacity illustration, not a claim that distributed GPUs form one tightly coupled training cluster.

| Repeated reference sites | GPUs | IT MW | Facility MW | Initial base capex, JPY bn | Base year-one gross revenue, JPY bn |
|---|---:|---:|---:|---:|---:|
| 1 | 56 | 0.0774 | 0.10449 | 0.5675 | 0.088 |
| 195 | 10,920 | 15.093 | 20.37555 | 110.6625 | 17.16 |
| 800 | 44,800 | 61.92 | 83.592 | 454.0 | 70.40 |

Base initial capex uses seven servers at JPY45m plus JPY202m non-compute allowances and 25% contingency on those allowances: JPY567.5m. Base year-one revenue is 160,000 GPU-hours × JPY550 = JPY88m. Multiplication assumes identical sites and operating-year alignment; national central costs, rollout schedules and site differences are not modelled. Money excludes consumption tax. Revenue is not profit or investor distributions.

### Financial finding — retain the adverse result

An independent arithmetic cross-check transcribed the retrieved Hanyu cost inputs and the formulas in `src/yumori_planning_scenarios.py`; it did not execute the full canonical portfolio engine, edit FIN, validate customer demand or refresh supplier quotes. All three cases remain MODEL ONLY.

| One-site, year-one metric (JPY m) | Downside | Base | Upside |
|---|---:|---:|---:|
| Initial capex | 977.2 | 567.5 | 369.2 |
| Gross revenue | 13.6 | 88.0 | 200.0 |
| Cash after operating costs, tax, working capital, debt service and reserves; before investor distributions | -213.9621 | -64.8373 | 52.3744 |

Cost reproduction: low/base/high non-compute allowances total JPY108m / 202m / 398m; hardware allowances are seven × JPY35m / 45m / 60m; non-compute contingency is 15% / 25% / 40%. Year-one sold hours and prices are 40,000 × 340; 160,000 × 550; 250,000 × 800. All cases assume 50% debt and five-year principal repayment; interest is 8% / 6% / 4%. Electricity retains the existing idle-load/occupancy proxy, assumed energy tariff and peak demand charges; these are not measured consumption or confirmed tariffs. Include recurring operations, 2%-of-capex maintenance, community cost, positive-income tax, working capital and 1%-of-capex reserve as in the retrieved formulas.

The base case has a year-one funding shortfall and a year-five shortfall when the model's 50%-of-compute-cost renewal is charged. A positive upside year-one cash balance is not an offered dividend, established IRR, or proof of sustainable renewal economics. No sub-year-payback assertion is made. The next commercial task is to improve and independently validate one asset's economics, not multiply a deficit by 800 or conceal it beneath gross revenue.

Sakura's current H100 reference was rechecked: JPY990/hour and JPY385,000/month, tax inclusive, with billing caps and separately contracted boot disk. No market-wide cheapest-price claim is made. Compare matched workloads, GPU type, term, storage/network/support and tax; low building cost does not prove affordable delivered compute. EDUIT remains planned and cannot supply booked external revenue. No grant, free education allocation or uncontracted heat sale is treated as secured revenue.

### Verification of this revision

- Existing Node test owner extended, rather than replaced with a new test subsystem. Thirteen source/DOM-fixture/copy/arithmetic checks passed; one additional hosting-contract check passed against a reconstructed minimal configuration fixture, **not a full downloaded Firebase config or hosted deployment**. The optional full Innovate blob check was not run locally because that file was not mounted; its `--require-preserved` fail-closed behavior remains intact.
- Six offline Chromium cases (Japanese/English × 360/768/1440 pixels) passed language/ARIA state, visible content and no horizontal body overflow or JavaScript page errors. Desktop economics and Japanese mobile hero screenshots were visually inspected; the mobile Japanese headline was shortened to avoid splitting 計算基盤.
- Browser navigation to local HTTP was blocked by browser policy. It was not bypassed. Verification used offline `set_content` with the authored HTML and injected unchanged local JS; this proves presentation behavior only, not hosted routing or authentication. The known legacy query/hash paths were tested in the Node fixture.
- No auth, member, SSO, payment, domain, hosting, investor database, contact or economic-owner files are changed by this audience revision. Original release gates below remain open. No website publication or external outreach occurred.

Primary sources: https://www.mext.go.jp/a_menu/shotou/zyosei/yoyuu_00002.htm ; https://docs.nvidia.com/dgx/dgxh100-user-guide/introduction-to-dgxh100.html ; https://cloud.sakura.ad.jp/products/server/gpu/ ; https://www.fsa.go.jp/common/shinsei/fund.html . Source inputs/formulas are linked to the immutable baseline in the page.

---

## Historical stage-one record — retained for continuity

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
