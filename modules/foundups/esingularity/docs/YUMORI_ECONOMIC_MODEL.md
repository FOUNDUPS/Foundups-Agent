# YUMORI economic model — repository authority

Last audited: 2026-09-28 JST

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

Hanyu expansion is a separate additional budget. Thus there are **51 missing capital
inputs** at this audit: 50 site cost lines plus expansion. Each five-year cash
scenario has **55 missing annual inputs**: revenue, electricity, operations,
maintenance, cash tax, working-capital increase, renewal CapEx, debt service,
reserve contribution, investor due and community cash commitment. Downside/base/
upside have independent inputs; no unsupported percentage or lending terms are set.
Optional scenario equity is additionally needed for investor recovery. Later-site
cash forecasts are separately missing for their payback calculations.

Current result is **INSUFFICIENT EVIDENCE** in code and all three FIN scenarios.
Hanyu, Shimousaka, Sukatto and total portfolio CapEx are **TBD**. Entered subtotal
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
