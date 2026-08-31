# eSingularity.ai source-of-truth ledger

Last audited: 2026-09-01 (Asia/Tokyo)

Claim classes:

- **A — verified official:** government or official public record.
- **B — verified project model:** a project scenario, not an official fact or promise.
- **C — third-party benchmark:** external comparison that needs a named source and date.
- **D — vision / target:** a proposed future state, conditional by definition.

| Claim | Class | Current source | Verification | Website use |
| --- | --- | --- | --- | --- |
| Original construction cost: ¥4.68B | A | Fukui City, *市政のあらまし* (FY2024 and earlier), `aramasi6.pdf` | Verified | May be shown as historical construction cost, not current market value. |
| Site area: 33,717.36 m², all leased land | A | Fukui City property sheet, `SUKATTO.pdf`, p.2 | Verified | Use exact figure when precision helps; otherwise “約3.37万㎡”. |
| Total floor area: 8,099.56 m² | A | Fukui City property sheet, `SUKATTO.pdf`, p.2 | Verified | May be shown as existing-building scale. |
| Facility opened 1994-04-06 | A | Fukui City, *市政のあらまし* | Verified | May be shown in history. |
| FY2018 users: 129,649 | A | Fukui City, *市政のあらまし* FY2019 | Verified | May be shown with fiscal-year label. |
| Visitor direct-spending screen: ¥129.649M–¥719.033M/year; ¥3.889B–¥21.571B over 30 years | B / calculated from A + official benchmark | 129,649 FY2018 users × ¥1,000 project assumption through Fukui Prefecture's 2025 average day-trip spend of ¥5,546 | Arithmetic verified. The 30-year total holds visits and spend constant, is undiscounted, and is not an I-O analysis. | Label prominently as a project screening scenario, not a forecast. Do not add demolition cost, asset value, compute revenue, or multiplier effects into one total. |
| Public-facility function abolished 2021-06-24 | A | Fukui City property sheet, `SUKATTO.pdf`, p.3 | Verified | Use exact date only when useful. |
| Demolition figure: approximately ¥1.58B | A-limited | Fukui City Council June 2026 general-question outline, `0806a.pdf` | Verified only as a figure raised in a council question; not yet verified as an adopted budget or contractor price | Phrase narrowly and date it. Do not call it an awarded contract, final cost, or project funding source. |
| Indexed 2025 construction-cost reference: about ¥6.8B | C / calculated from A | ¥4.68B × MLIT 2025 non-residential index 121.6 / 1994 index 83.7 = ¥6.799B | Arithmetic verified against MLIT annual deflator dated 2026-06-30 | Label as an indexed construction-cost reference, not appraisal, market value, or certified replacement cost. |
| Equivalent onsen/thermal greenfield: ¥1.28B–¥1.76B | B | Master proposal + Landowner Proposal (External Audit v2) | Project range located; contractor/engineering basis not independently verified | Show only with “project model — requires engineering/contractor validation”. |
| Brownfield recommissioning: ¥195M–¥270M | B | Master proposal + Landowner Proposal (External Audit v2) | Project range located; contractor/engineering basis not independently verified | Same project-model label required. |
| Indicative avoided future CAPEX: approx. ¥1.1B–¥1.5B | B | Difference implied by the two project ranges | Arithmetic direction verified; physical scope remains unverified | Show as indicative comparison, never as cash available to the project. |
| Phase 1: approximately 1 MW | D supported by B | Phase 1 financial workbook + master proposal | Verified as project starting scenario, not permitted/contracted capacity | Present as Phase 1 target/proof stage. |
| 384 GPUs | B / configuration assumption | Phase 1 financial workbook | Verified as current model assumption; procurement configuration can change | Always add “current model assumption / subject to procurement”. |
| ~5 MW total, then ~10 MW, then ~15–20 MW total | D | Current public roadmap required by 2026-08-29 work order | Conditional planning sequence | Use decision gates; do not imply annual doubling or commitments. |
| Long-term 20–30 MW-class site potential | D | Master + landowner proposal + current work order | Planning range only | Always state grid, permits, zoning, civil/flood, cooling, financing, demand, developable area, and community agreement conditions. |
| Revenue, EBITDA, IRR, payback, DSCR | B-unverified | Phase 1 financial workbook | **Failed audit:** displayed cells are hard-coded strings; several arithmetic/depreciation/cash-flow inconsistencies exist | Do not publish on the website. |
| Job counts | B-unverified | Phase 1 financial workbook | Methodology not supplied | Do not publish numeric job estimates. Explain construction/permanent/indirect categories without counts. |
| Grants, tax holidays, free lease, specific lenders | Unverified | Phase 1 financial workbook assumptions | Current eligibility/agreements not verified | Do not publish as available, committed, or guaranteed. |
| Data center is separate from the onsen building | D / core architecture | Master + landowner proposal + current work order | Consistent across current sources | Make visually unmistakable: retained building (onsen + Innovation Center) beside new modular campus. |
| Monday campaign event | Unverified/current | No authoritative date, time, exact location, or public-status source found | Not verified | Keep disabled; do not publish as upcoming until structured fields are confirmed. |
| LINE invitation URL | Verified project asset | Operator-provided `https://line.me/ti/p/baXEozL_Q6` | HTTP 200 on 2026-08-29 | One shared direct link in all languages. |
| Approved LINE QR | Shared visual asset | QR embedded in approved campaign artwork; no standalone Drive image was located | Visual asset found; standalone scan verification still required | Preserve source pixels. Do not regenerate or apply lossy optimization. |

## Authoritative project documents

1. Master proposal — Google Doc `1-wxF_I39svQH8AGvF2sryIk6ReAz2ctHe0-5-HypypM`
2. Landowner proposal (External Audit v2) — Google Doc `1WCqidzhU_9qyMxYCKj8UZ3lUv6qudCoWzy3qxClEznE`
3. Phase 1 financial model — Google Sheet `1-S4NH3WHZV6aUS51GGdTdEAP_mdcMlxFVlazsJI4tJc`
4. Current build work order — Google Doc `14xZTRgROhk_kTVaj9KimeenqmQrW26SCleHnKNWz08E`

## Official sources

- Fukui City property sheet: https://www.city.fukui.lg.jp/sisei/plan/reform/p071776_d/fil/SUKATTO.pdf
- Fukui City FY2024 facility record: https://www.city.fukui.lg.jp/sisei/gikai/shigikaishikumi/p022677_d/fil/aramasi6.pdf
- Fukui City Council June 2026 question outline: https://www.city.fukui.lg.jp/sisei/gikai/shitsumon/p004052_d/fil/0806a.pdf
- MLIT construction-cost deflator: https://www.mlit.go.jp/statistics/details/t-other-2_tk_000362.html
- Fukui Prefecture 2025 tourism statistics: https://www.pref.fukui.lg.jp/doc/kankou/fukuiken-kankoukyakusu_d/fil/024.pdf
- Fukui Prefecture input-output analysis method and tool: https://www.pref.fukui.lg.jp/doc/toukei-jouhou/hakyukouka.html
- Awara Onsen Yukemuri Yokocho official site and photographic reference: https://yukemuriyokocho.com/
- Akira Hasegawa's official D-K / Digital Kakejiku gallery: https://www.digital-kakejiku.com/
