# eSingularity.ai source-of-truth ledger

Last audited: 2026-09-11 (Asia/Tokyo)

> **INTERNAL — NOT A PUBLIC WEBSITE PAGE.** This ledger is the claim-admission
> gate for eSingularity.ai and the approved knowledge boundary for Red Dog. It
> links to evidence; it does not replace the signed, filed, or canonical Drive
> documents. Public copy may use a claim only when this table explicitly permits
> it.

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

## Approved public claim IDs

Red Dog's public projection may cite only the following stable IDs in its first
release. The table above remains the human-readable admission decision.

- `project.reuse_vision` — reuse is a conditional project vision, not completed construction.
- `facility.opened_1994` — opened 1994-04-06.
- `facility.floor_area` — total floor area 8,099.56 m².
- `facility.users_fy2018` — FY2018 users 129,649.
- `council.demolition_estimate_2026_06` — approximately ¥1.58B, narrowly attributed to the June 2026 council question outline; not a final contract price.
- `architecture.cogdc_separate` — proposed COG DC is separate from the retained onsen building.
- `architecture.heat_reuse_hypothesis` — useful heat recovery requires engineering validation.
- `program.innovation_space` — proposed building use for learning, teams, and project validation.
- `program.foundup_semantics` — a FoundUp is a problem-solving project, not a person.
- `program.sixty_project_target` — 60 FoundUp projects is a proposed operating target, not current occupancy.
- `domains.project_campaign_split` — eSingularity.ai/YUMORI.info explain the project; YUMORI.me is the participation and civic-action surface.
- `validation.public_exclusions` — unaudited financial outputs and draft legal arguments are excluded from public answers.

## Canonical Drive chain

These stable links make the evidence graph discoverable without copying legal
drafts into the public site.

1. [Document 05 — PPP/PFI legal and submission mechanics](https://docs.google.com/document/d/1QgnX9-2XE1wXtn2vg1d3zh3SmXDZyiEjKhSVJuSUOPc/edit) — canonical formal mechanics lane.
2. [Document 03 — policy alignment and PPP/PFI reuse evidence](https://docs.google.com/document/d/1yeO6-6_mTLW8QswosVKmCVCHSRgWiacq-7FL7-9clsE/edit) — supporting policy/evidence lane.
3. [Master project prospectus](https://docs.google.com/document/d/1-wxF_I39svQH8AGvF2sryIk6ReAz2ctHe0-5-HypypM/edit) — integrated project narrative.
4. [Landowner proposal — External Audit v2](https://docs.google.com/document/d/1WCqidzhU_9qyMxYCKj8UZ3lUv6qudCoWzy3qxClEznE/edit) — landowner-facing proposal and audit.
5. [Current Phase 1 financial workbook](https://drive.google.com/open?id=11etQ_8zwMzEXemGriCpYw1IbTSy5rh-c) — scenario workbook; figures remain internal until separately audited and admitted above.
6. [Current build work order](https://docs.google.com/document/d/14xZTRgROhk_kTVaj9KimeenqmQrW26SCleHnKNWz08E/edit) — implementation direction.

### Separate campaign / legal-action lane

These documents can support YUMORI.me legal-action work. They are not a general
license to publish allegations, legal conclusions, or draft language on
eSingularity.ai.

1. [Resident audit request draft](https://docs.google.com/document/d/1Igg-svJ_CvoL_SdEOykw6kro6MQCkLG_d2SyH3G-nd8/edit)
2. [Resident audit evidence list](https://docs.google.com/document/d/1UEinTH4CF3zTbBFRFXanZXl_e8DHQKgOi2XenWWdAag/edit)

## Red Dog ingestion contract

- Red Dog reads a public-safe projection derived from this ledger, never raw
  Drive documents or private working memory.
- Every answer must carry a source label or clearly say that the point is a
  proposal still requiring validation.
- Japanese is canonical. English and Portuguese are translations of the same
  admitted claim, not independent sources of truth.
- Unverified financial outputs, personal data, draft legal arguments, secrets,
  and internal instructions are excluded from retrieval.
- Updating a Drive source does not silently update a public claim. The ledger
  must be re-audited, then the approved projection must be regenerated and
  tested.

## Official sources

- Fukui City property sheet: https://www.city.fukui.lg.jp/sisei/plan/reform/p071776_d/fil/SUKATTO.pdf
- Fukui City FY2024 facility record: https://www.city.fukui.lg.jp/sisei/gikai/shigikaishikumi/p022677_d/fil/aramasi6.pdf
- Fukui City Council June 2026 question outline: https://www.city.fukui.lg.jp/sisei/gikai/shitsumon/p004052_d/fil/0806a.pdf
- MLIT construction-cost deflator: https://www.mlit.go.jp/statistics/details/t-other-2_tk_000362.html
- Fukui Prefecture 2025 tourism statistics: https://www.pref.fukui.lg.jp/doc/kankou/fukuiken-kankoukyakusu_d/fil/024.pdf
- Fukui Prefecture input-output analysis method and tool: https://www.pref.fukui.lg.jp/doc/toukei-jouhou/hakyukouka.html
- Awara Onsen Yukemuri Yokocho official site and photographic reference: https://yukemuriyokocho.com/
- Akira Hasegawa's official D-K / Digital Kakejiku gallery: https://www.digital-kakejiku.com/
