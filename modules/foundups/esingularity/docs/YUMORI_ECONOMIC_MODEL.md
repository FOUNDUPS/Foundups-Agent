# YUMORI economic model — repository authority

Last audited: 2026-09-29 JST

## Rule

The repository calculation model is the economic/sizing authority. The Google FIN workbook is a formula-driven working projection and interview surface. A Drive formula may not override a repository truth boundary or a primary-source utility/customer fact.

Canonical code:

- `src/yumori_economic_model.py`
- `tests/test_yumori_economic_model.py`
- site assumptions: `docs/CANDIDATE_SITE_REGISTRY.md`

## Two calculation layers

### 1. Demand-led node sizing — current decision model

Do **not** choose MW first.

The current chain is:

```text
customer/service orders
  -> annual revenue + GPU-hours
  -> demand-backed GPU count
  -> IT kW
  -> facility kW through PUE
  -> compare to utility-confirmed capacity
```

The model also computes a separate **financial-floor equivalent**: the sold GPU-hours / facility kW that would be required to support the current non-electric cash Opex plus target DSCR under the current pricing/electricity/debt reference.

That financial-floor capacity is a viability warning, **not a build target**. If demand is below the floor, the answer is to secure more bankable demand or improve economics, not to build speculative capacity.

No deliverable kW/MW is currently confirmed for Sukatto, Shimousaka, or Hanyu.

### 2. Five-year functional workbook parity — legacy audit scenario

`run_yumori_economic_model()` preserves the existing functional FIN workbook assumptions for audit continuity:

- 384 GPUs
- 850 kW IT load
- 65/85/92/95/95% utilization
- three legacy GPU-hour pricing tiers
- current base CapEx / debt / Opex assumptions
- zero committed grants unless awarded evidence exists

These values are **not current node-sizing authority**.

Default parity outputs:

- total CapEx: ¥2.085B
- equity plug: ¥550M
- Year-1 gross revenue: ¥808.630528M
- Year-1 EBITDA: ¥599.427112M
- minimum DSCR: ~1.2896x
- five-year cumulative FCFE: ~¥1.732493B
- equity IRR: ~40.93%

## Product/service catalog

The code carries a 24-row candidate commercial catalog. Only the inherited raw-compute scenarios currently have numerical price assumptions; most managed/storage/network/facility products stay `TBD` until feasibility interviews or market quotes establish units and pricing.

The catalog deliberately separates **physical capacity** from **commercial packaging**. The same GPU pool can be sold under multiple offers, but product rows must never be added together as if each row represented separate physical GPUs.

Candidate offers include on-demand GPU, reserved enterprise capacity, academic capacity, sovereign nodes, cluster reservations, inference, model hosting, fine-tuning/training, evaluation, agents, CPU/HPC, platform services, storage, backup, data staging, private networking, egress, colocation, disaster recovery, MLOps, Physical AI, sponsored education/community compute, and heat offtake.

## Current workbook projection

Drive workbook:

`FIN — YUMORI Three-Site Portfolio, Demand-Led Financial Model & Grant Audit — 2026-09-29`

`1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0`

Investor review path: the eSingularity.ai finance section links this calculation
note and the access-controlled current FIN. FIN remains a working model with
owner-only observed Drive permissions. The `Sensitivity` current-case initial
Hanyu financing gap uses the corresponding low/base/high Hanyu CapEx, while
the legacy sensitivity rows are retained as a separately labeled reference.
The Dashboard's legacy catalog financial floor is a separate sizing diagnostic;
it is not a Hanyu portfolio financing output.

Current decision tabs:

- `Service Catalog`
- `Demand & Capacity`
- `Node Sizing`
- Site 1 — Sukatto
- Site 2 — Shimousaka
- Site 3 — Hanyu

The older integrated XLSX remains reference-only.

## Evidence boundary

- Grid proximity is not deliverable capacity.
- Interview interest is not revenue.
- LOI is evidence, not cash.
- Only a binding order / minimum-purchase / live use supports bankable demand.
- A price marked `VERIFY` or `TBD` is not an offer or forecast.
- Financial-floor kW is not permission to build.
- Re-run CapEx and debt terms after a real phase size is selected.


## Heat-recovery calculation

Heat is not booked as revenue merely because servers reject heat. The code values only the minimum of recoverable/deliverable heat and actual thermal demand:

`IT load -> recovered heat -> delivered heat -> usable heat capped by demand -> annual thermal value`.

This is intended for Sukatto/onsen feasibility and similar local heat users. Recovery fraction, delivery efficiency, thermal demand, availability and avoided heat cost all remain engineering/evidence inputs.

## Japan AI infrastructure evidence ledger

`jhr/data/japan_ai_infrastructure_flows.json` preserves a small official-source seed of Japan AI-infrastructure relationships used by JHR research. Undisclosed deal amounts remain null.

`analyze_infrastructure_flows()` computes only reproducible network indicators from that ledger. Its output is explicitly a partial dependency diagnostic, not a Japan market score, investment ranking, election/policy recommendation, or forecast.

## Three-site portfolio extension — 2026-09-29

`run_portfolio_model()` is exposed from the canonical economic module and implemented
in `src/yumori_portfolio_model.py`. It does not alter legacy parity, the 24-service
catalog, demand sizing or heat-demand caps.

| Priority | Canonical identity | Initial cost lines | Role |
| --- | --- | --- | --- |
| 1 | Site 3 — Hanyu | 19 independently estimated components | Initial compute / economic-engine candidate |
| 2 | Site 2 — Shimousaka | 19 independent components, no copied Hanyu assumptions | Expansion campus |
| 3 | Site 1 — Sukatto | 12 adaptive-reuse components | Optional thermal/community/education/innovation node |

School cost scopes include survey, retrofit, receiving/interconnection, transformer,
utility contribution, modular DC, compute, cooling, UPS, BESS, fiber, fire, security,
seismic, mechanical, contingency, design/permitting, justified community retrofit
and site-use rights. Sukatto separates rights, rehabilitation, asbestos, MEP, onsen,
thermal loop, community, education, optional compute, design, contingency and survey.
Turnkey quotes and their components must not overlap. Excluded work needs explicit
zero and a scope basis; missing is `None` / `TBD`, not zero.

At the initial rebaseline, before the costed planning pass below, Hanyu expansion was a separate additional budget. There were **51 missing capital
inputs** at this audit: 50 site cost lines plus expansion. Each five-year cash
scenario has **55 missing annual inputs**: revenue, electricity, operations,
maintenance, cash tax, working-capital increase, renewal CapEx, debt service,
reserve contribution, investor due and community cash commitment. Downside/base/
upside have independent inputs; no unsupported percentage or lending terms are set.
Optional scenario equity is additionally needed for investor recovery. Later-site
cash forecasts are separately missing for their payback calculations.

Initial empty-input result was **INSUFFICIENT EVIDENCE** in code and all three FIN scenarios. The later costed pass below supplies MODEL ONLY assumptions without promoting evidence readiness.
At that initial checkpoint, Hanyu, Shimousaka, Sukatto and total portfolio CapEx were **TBD**. Entered subtotal
is zero solely because no site amounts have been entered; it is not a cost estimate.
Funding gap, cash available for reinvestment and paybacks remain indeterminate.
No grant or financing commitment is recorded in the new portfolio sources.

### Cash waterfall and capital allocation

1. Revenue less electricity, operations, maintenance and committed community cash
   produces EBITDA. Wider community economic impact is not project cash.
2. Subtract cash tax, working-capital increase and renewal CapEx for unlevered cash /
   CFADS. Tax and financing inputs require their own schedules/quotes; they are not
   inferred from the legacy financing model.
3. Subtract principal plus interest to calculate free cash after debt; then subtract
   reserve contributions. Carry cash deficits forward.
4. Pay current investor dues plus arrears only from available cash; carry unpaid
   obligations forward. Investor distributions and retained cash are disjoint.
5. At the end of the five-year test, allocate residual cash once: Hanyu expansion,
   then Shimousaka, then optional Sukatto. Partial phase funding remains held unless
   an explicit smaller tranche is costed. Economic allocations and permission to
   deploy are separate results.

`YES UNDER CURRENT MODEL ASSUMPTIONS` requires complete cost/cash inputs, enough
residual cash for all selected later **gross** development costs, no cash deficit
requiring an interim bridge, and no ending investor arrears. Positive but inadequate
cash gives `PARTIAL SELF-FUNDING`; no surplus, deficits or unpaid investor dues give
`NO — ADDITIONAL CAPITAL REQUIRED`. Missing data gives `INSUFFICIENT EVIDENCE`.
A YES does not finance Hanyu's initial investment, establish utility capacity or
satisfy a deployment gate. The model reports initial Hanyu outside capital separately.

Committed debt/equity and AWARDED grants reduce only their assigned site's funding
gap. Unawarded caps/scenarios do not. Excluded-site restricted sources do not transfer.
The residual-capital screen includes initial Hanyu gap, remaining future gap after
retained cash, peak interim liquidity and unpaid investor obligations. The peak
bridge is a timing requirement, not an additional construction cost; a dated
sources/uses and drawdown plan must resolve repayment and award reimbursement timing.
No construction-date scheduling, terminal asset value or post-Year-5 extrapolation
is implied by this screening model.

Site and priority-phase payback use independent unlevered cash against gross initial
site CapEx, with within-year interpolation. Investor recovery uses actual modeled
investor distributions against scenario paid-in equity. Full-portfolio payback
requires all included sites' aligned cash forecasts; it remains unresolved when
expansion is included without its own cash forecast. These are different measures.

### Deployment gates and evidence

Hanyu requires utility-confirmed capacity for positive demand-derived load, fiber,
building, demand, CapEx, finance and legal/use evidence. Gate 2 also requires demand
beyond the first phase, site-specific engineering and acceptable lender metrics.
Gate 3 additionally requires Sukatto rights, rehabilitation/asbestos/MEP and thermal
use economics. `PASS` is an evidence judgment requiring a reference, not merely a
spreadsheet switch. Removing or failing Sukatto cannot change Hanyu's own gate.

### Existing FIN projection map

| Existing tab | Portfolio extension |
| --- | --- |
| Dashboard | Current headline rows 4–10; priorities 36–39; scenarios 46–49; old summary retained 80–86 |
| Site 3 / Site 2 / Site 1 | Priority/inclusion 11–12; independent costs 15–33 or 15–26; completeness 35–39; gates 40–50; site/phase payback 52–56 |
| CapEx | Portfolio sources-of-cost roll-up 20–28; expansion C25; complete total C26 |
| Financing | Site-restricted commitments 32–42; award allocations 45–60; evidence/timing controls 62–65; gated allocation 68–72 |
| 5Y Model | Downside 35–73; base 80–118; upside 125–163; independent whole-portfolio recovery 171–174 |
| Sensitivity | Three independently calculated current scenarios 12–21 |
| Audit & Checks | Portfolio boundaries 34–47 |
| Grants & Subsidies | Existing program rows extended in S:Z with component/site/applicant/application-unit mapping |

Existing service/demand/node-sizing and Regional Impact layers remain separate.
No additional tabs, workbook or grant registry were created. Legacy ¥2.085B CapEx
remains an audit reference only, never a site quote or portfolio cost.

See [WSP 97 rebaseline receipt](YUMORI_PORTFOLIO_REBASELINE_20260929.md) for native
readbacks, tests and PR/main disposition.

## Costed planning cases — 2026-09-29

**MODEL ONLY — not quotes, confirmed demand, available utility capacity or secured financing.**
All amounts below are nominal JPY millions, excluding consumption tax. The high case is not a guaranteed upper bound. Selected fit-out areas are hypothetical phase scope, not measured building areas. Additional Hanyu expansion is explicitly excluded (zero) pending a separate costed tranche.

### Priority 1 — Hanyu (Site 3)

| Component | Quantity / unit | Low ¥m | Base ¥m | High ¥m | Scope / status |
| --- | --- | ---: | ---: | ---: | --- |
| survey_engineering | 1 allowance | 3.000 | 5.000 | 8.000 | MODEL ONLY; Initial surveys only; detailed design is separate |
| building_retrofit | 400 m2 selected fit-out | 20.000 | 32.000 | 52.000 | MODEL ONLY; Assumed limited phase area; not measured school area; exclude structural, MEP and container |
| electrical_receiving | 1 allowance | 8.000 | 12.000 | 20.000 | MODEL ONLY; Internal incoming cables, metering and installation; exclude switchgear and utility work |
| transformer_switchgear | 1 allowance | 12.000 | 20.000 | 35.000 | MODEL ONLY; Receiving transformer/switchgear equipment only |
| utility_contribution | 1 allowance | 10.000 | 30.000 | 80.000 | MODEL ONLY; Unquoted utility allowance; actual scope and upper exposure unresolved |
| modular_dc | 1 allowance | 10.000 | 18.000 | 30.000 | MODEL ONLY; Shell, racks and fit-out only; exclude compute/cooling/UPS |
| compute_hardware | 7 8-GPU server | 245.000 | 315.000 | 420.000 | MODEL ONLY; Procurement allowance; CPU/RAM/local storage included, fabric in fiber_network; NVIDIA source supports specs only |
| cooling_cdu_heat_rejection | 1 allowance | 10.000 | 18.000 | 30.000 | MODEL ONLY; Complete cooling scope; no additional turnkey cooling counted |
| ups | 1 allowance | 5.000 | 8.000 | 14.000 | MODEL ONLY; Short ride-through UPS, not multi-hour autonomy |
| bess | 100 kWh allowance | 4.000 | 6.000 | 9.000 | MODEL ONLY; Independent battery allowance, no confirmed gym siting or grid revenue |
| fiber_network | 1 allowance | 5.000 | 10.000 | 25.000 | MODEL ONLY; Carrier installation and network/storage fabric; recurring charges in Opex |
| fire_suppression | 1 allowance | 3.000 | 5.000 | 9.000 | MODEL ONLY; Dedicated compute-phase fire detection/suppression |
| security | 1 allowance | 2.000 | 3.000 | 5.000 | MODEL ONLY; Access/CCTV fit-out, recurring service in Opex |
| seismic_building | 1 allowance | 5.000 | 15.000 | 40.000 | MODEL ONLY; Unsurveyed strengthening allowance; failure may invalidate phase |
| mechanical | 1 allowance | 3.000 | 5.000 | 10.000 | MODEL ONLY; Non-DC plumbing/ventilation only, excludes cooling |
| contingency | non-compute direct subtotal | 16.200 | 50.500 | 159.200 | MODEL ONLY; Percentage of all non-compute direct lines, including fees; no contingency on contingency |
| design_permitting | 1 allowance | 6.000 | 10.000 | 16.000 | MODEL ONLY; Detailed design and permits, excludes initial surveys |
| education_community | 1 allowance | 0.000 | 0.000 | 0.000 | MODEL ONLY; Excluded from minimum compute phase; future scope needs separate budget |
| site_use_rights | 1 allowance | 2.000 | 5.000 | 15.000 | MODEL ONLY; Lease/deposit/legal mobilization assumption, not a City price; annual rent in Opex |
| **Total** | | **369.200** | **567.500** | **977.200** | Planning subtotal |

### Priority 2 — Shimousaka (Site 2)

| Component | Quantity / unit | Low ¥m | Base ¥m | High ¥m | Scope / status |
| --- | --- | ---: | ---: | ---: | --- |
| survey_engineering | 1 allowance | 4.000 | 7.000 | 12.000 | MODEL ONLY; Independent Shimousaka survey |
| building_retrofit | 800 m2 selected fit-out | 48.000 | 80.000 | 128.000 | MODEL ONLY; Assumed phase area, not measured campus area; excludes structural/MEP/container |
| electrical_receiving | 1 allowance | 10.000 | 18.000 | 30.000 | MODEL ONLY; Independent site cabling/install allowance |
| transformer_switchgear | 1 allowance | 15.000 | 25.000 | 45.000 | MODEL ONLY; Independent receiving equipment; no Hanyu grid inference |
| utility_contribution | 1 allowance | 15.000 | 45.000 | 120.000 | MODEL ONLY; Independent unquoted utility allowance; no known upper bound |
| modular_dc | 1 allowance | 12.000 | 22.000 | 38.000 | MODEL ONLY; Shell/racks only |
| compute_hardware | 5 8-GPU server | 190.000 | 240.000 | 325.000 | MODEL ONLY; Independent later procurement allowance, excludes fabric/cooling |
| cooling_cdu_heat_rejection | 1 allowance | 12.000 | 22.000 | 38.000 | MODEL ONLY; Dedicated cooling scope |
| ups | 1 allowance | 6.000 | 10.000 | 17.000 | MODEL ONLY; Short ride-through only |
| bess | 150 kWh allowance | 6.750 | 9.750 | 15.000 | MODEL ONLY; Independent storage scope; no grid-service revenue |
| fiber_network | 1 allowance | 8.000 | 18.000 | 40.000 | MODEL ONLY; Installation/fabric; no known carrier route |
| fire_suppression | 1 allowance | 4.000 | 8.000 | 14.000 | MODEL ONLY; Independent compute/campus scope |
| security | 1 allowance | 3.000 | 5.000 | 8.000 | MODEL ONLY; Access/CCTV |
| seismic_building | 1 allowance | 10.000 | 30.000 | 80.000 | MODEL ONLY; Unsurveyed independent strengthening allowance |
| mechanical | 1 allowance | 6.000 | 12.000 | 24.000 | MODEL ONLY; Non-DC building services; excludes cooling |
| contingency | non-compute direct subtotal | 28.613 | 91.938 | 282.800 | MODEL ONLY; Percentage of all non-compute direct lines, including fees; no contingency on contingency |
| design_permitting | 1 allowance | 10.000 | 18.000 | 30.000 | MODEL ONLY; Independent detailed design and permits |
| education_community | 300 m2 limited fit-out | 18.000 | 30.000 | 48.000 | MODEL ONLY; Optional assumed education/incubation tranche; no full-campus renovation |
| site_use_rights | 1 allowance | 3.000 | 8.000 | 20.000 | MODEL ONLY; Lease/deposit/legal mobilization; annual rent separate |
| **Total** | | **409.363** | **699.688** | **1,314.800** | Planning subtotal |

### Priority 3 — Sukatto (Site 1)

| Component | Quantity / unit | Low ¥m | Base ¥m | High ¥m | Scope / status |
| --- | --- | ---: | ---: | ---: | --- |
| lawful_acquisition_lease_use | 1 allowance | 10.000 | 30.000 | 100.000 | MODEL ONLY; Lease/deposit/legal mobilization scenario, not property valuation or City offer |
| building_rehabilitation | 3000 m2 phased rehabilitation | 180.000 | 300.000 | 540.000 | MODEL ONLY; Selected-area scenario; envelope/structure/interiors only; not whole-building quote |
| asbestos | 1 allowance | 15.000 | 60.000 | 180.000 | MODEL ONLY; Unsurveyed treatment allowance; actual scope may exceed high case |
| mep_renewal | 3000 m2 services renewal | 150.000 | 270.000 | 450.000 | MODEL ONLY; Electrical/plumbing/general HVAC only; bath plant and thermal pilot separate |
| onsen_restoration | 1 allowance | 150.000 | 250.000 | 450.000 | MODEL ONLY; Bath plant, pools and onsen-specific works; water/access rights unverified |
| thermal_loop_heat_reuse | 1 allowance | 20.000 | 40.000 | 80.000 | MODEL ONLY; Local heat-exchange/heat-pump pilot allowance; no intersite pipe, no heat revenue |
| public_community | 1 allowance | 20.000 | 50.000 | 100.000 | MODEL ONLY; Furniture/community fit-out, excludes building and MEP works |
| education_innovation | 1 allowance | 15.000 | 40.000 | 90.000 | MODEL ONLY; Equipment and specialist fit-out only |
| optional_compute | 1 allowance | 0.000 | 0.000 | 0.000 | MODEL ONLY; Compute excluded until independent demand/power economics justify it |
| design_permitting | 1 allowance | 30.000 | 60.000 | 100.000 | MODEL ONLY; Detailed design/permits, separate from initial surveys |
| contingency | non-compute direct subtotal | 119.600 | 334.500 | 1,060.000 | MODEL ONLY; Percentage of all non-compute direct lines, including fees; no contingency on contingency |
| survey_engineering | 1 allowance | 8.000 | 15.000 | 30.000 | MODEL ONLY; Initial structure/asbestos/MEP/thermal investigations |
| **Total** | | **717.600** | **1,449.500** | **3,180.000** | Planning subtotal |

### Hanyu cash and portfolio funding screen

| Case | Portfolio CapEx ¥m | Hanyu CapEx ¥m | Y1 revenue ¥m | Y1 EBITDA ¥m | 5y investor paid ¥m | Retained ¥m | Capital + liquidity screen ¥m | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| downside | 5,472.000 | 977.200 | 13.600 | -66.702 | 0.000 | 0.000 | 7,323.888 | NO — ADDITIONAL CAPITAL REQUIRED |
| base | 2,716.688 | 567.500 | 88.000 | 19.013 | 0.000 | 0.000 | 3,309.877 | NO — ADDITIONAL CAPITAL REQUIRED |
| upside | 1,496.162 | 369.200 | 200.000 | 129.959 | 230.750 | 250.206 | 1,245.956 | PARTIAL SELF-FUNDING |

The screen includes initial uncommitted Hanyu capital, the remaining later-site capital after retained cash, peak liquidity and unpaid investor obligations. It is not an accounting cost total or a dated financing drawdown. Scenario debt/equity are hypothetical obligations and do not reduce the committed financing gap. Initial Hanyu capital is still required even in a successful later-site self-funding case.

### Formula and scope audit

- Demand scenario → discrete 8-GPU servers → IT power → PUE → required facility power. Hanyu: assumed peak 360,000 GPUh at 75% design utilization gives 7 servers / 56 GPUs / 104.49 kW required facility load. Shimousaka: independent 200,000 GPUh at 70% gives 5 servers / 40 GPUs / 85.55 kW. These are calculated planning loads, never utility-confirmed capacity or build decisions.
- Hanyu downside/base/upside prices are ¥340/550/800 per GPU-hour ex tax, with annual changes −5%/−3%/0%. Quantities, prices, electricity and funding terms remain editable MODEL ONLY inputs. Price × sold hours is the only compute revenue; no duplicate managed-service revenue is added.
- Electricity includes idle consumption, PUE, energy-price escalation and peak demand charges. Staffing/carrier/rent/insurance/admin are in fixed Opex; variable platform costs, maintenance and community cash are separate.
- Straight-line debt principal plus declining interest, positive-income tax proxy after depreciation/interest, incremental working capital, Year-5 hardware renewal, reserves, investor preferred return and capital repayment are explicit. Negative operating cash and investor arrears carry forward. No loss-carryforward tax benefit, terminal resale proceeds or released working capital is credited.
- Investor dues assume repayment over five years plus the scenario annual preferred return on initial equity; this is a stress-test obligation, not an agreed term sheet. Paid distributions and retained cash cannot be counted twice.
- Contingency applies once to all non-compute direct costs, including fees. Container shell, receiving cables, transformer, utility works, cooling and compute have mutually exclusive scopes. No legacy Sukatto CapEx is copied into the schools.
- Later-site cash is independently modeled for standalone phase payback. Sukatto visits/spend are hypothetical, not historical demand transferred into a forecast. Its combined variable Opex includes energy; no intersite heat sales, BESS sales or demolition savings are booked.
- Paybacks use supplied operating-year cash only; no recovery within five years is reported as not recovered, not extrapolated. A simultaneous operating-year portfolio comparison is not a construction schedule. Hanyu self-funding never uses later-site cash.
- Confirmed demand, utility/fiber, survey quantities, legal/use terms, tax/VAT treatment, construction timing, lending and offtake remain unresolved. Deployment gates stay HOLD; evidence result stays INSUFFICIENT EVIDENCE despite complete numeric assumptions.

### Primary comparator sources (checked 2026-09-29)

- [S1](https://ai.sakura.ad.jp/gpu/koukaryoku-dok/): Published H100 1008 JPY/GPU-hour and 8-GPU 2988 JPY/node-hour, tax inclusive; ex-tax equivalents 916.36 and 339.55 per GPU-hour. Different beta/SLA offerings; not project demand or realized price.
- [S2](https://docs.nvidia.com/dgx/dgxh100-user-guide/introduction-to-dgxh100.html): 8-GPU DGX H100/H200: maximum system input 10.2 kW; specification comparator only, not selected hardware or procurement cost.
- [S3](https://www.rikuden.co.jp/jiyuka/ryokin2.html): High-voltage A published 1876 JPY/kW-month and 27.53 JPY/kWh including tax, excluding renewable levy; actual classification, fuel adjustments and connection unverified.

Source of inputs: `data/yumori_planning_assumptions.json`. Calculation: `run_planning_scenario()` exposed by the canonical economic module. Native FIN projection: `python -m modules.foundups.esingularity.src.yumori_fin_projection <output-directory>`. Generated native requests require current metadata/range verification before authorized connector writes. No new workbook or alternate model is created.

### Verification and execution receipt

- Reused existing site tabs, all 18 workbook tabs and the grant/commitment ledger. No new workbook or grant registry. No City procedure or grant-status changes in this slice.
- 70 module tests and 18 routing tests pass. Native FIN readback matched all 165 annual cash input cells, 9 headline numerical outputs, three scenario verdicts and ten later-site cash years against Python, with no errors in the changed ranges.
- Independent LibreOffice forced full recalculation (OOXMLRecalcMode=0) reproduced the portfolio results and a disposable changed-input fixture: Hanyu fit-out area 400→600 m², base Year-1 demand 160,000→100,000 GPUh, and Sukatto excluded. Ordinary conversion can retain stale dependency caches; those caches were rejected. The unchanged legacy Dashboard E85 Google array-IRR formula is a LibreOffice compatibility exception; its native cached result remains intact. It is not used by the portfolio model.
- Native addTable metadata creation returned a connector internal error on the bounded call and minimal retry. The populated, formatted native cell tables and formulas are preserved; no unsupported table-object claim is made.
- Cost quotes and actual feasibility remain outstanding. WSP 97 PR/merge and operational receipts are recorded in the dedicated follow-up PR and canonical Moshpit event.

The costed cash schedule uses the existing `unlevered_cash_jpy` API field as **CFADS / cash before debt service**. Its cash-tax proxy deducts modeled interest, so this is not a financing-independent unlevered valuation. Site cost recovery uses this disclosed tax scenario; investor recovery uses actual modeled distributions. No unlevered IRR or enterprise valuation is claimed.

Follow-up delivery: [PR #1962](https://github.com/FOUNDUPS/Foundups-Agent/pull/1962). Final merge/main and native receipts are recorded in the PR and canonical Moshpit.
