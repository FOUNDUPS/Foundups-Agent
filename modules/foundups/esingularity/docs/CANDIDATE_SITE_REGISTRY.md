# YUMORI / eSingularity — Candidate Site Registry

Last audited: 2026-09-29 JST

## Authority and workflow

This repository record is the canonical project-status and site-assumption authority. The repository economic model at `src/yumori_economic_model.py` is the calculation/sizing authority. The Drive FIN workbook is the formula-driven working projection, interview, and audit surface.

**Do not choose MW first.** Node size is derived from customer/service demand, the revenue required to support the operating/finance case, equipment power characteristics, PUE, and finally the utility-confirmed site capacity. Until the utility confirms a deliverable capacity, school-site kW/MW remains **UNVERIFIED**.

Current Drive working model: **FIN — YUMORI Three-Site Portfolio, Demand-Led Financial Model & Grant Audit — 2026-09-29** (`1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0`).

Current decision tabs include `Service Catalog`, `Demand & Capacity`, `Node Sizing`, and one candidate-site tab per site. The older integrated XLSX remains reference-only.

## Current emphasis and flexible inclusion

The program retains all three candidate sites. The present feasibility focus is
the two former schools: Hanyu as the initial compute/economic candidate and
Shimousaka as the expansion, education, research and community candidate.
Sukatto remains an ancillary, conditional reuse option while its demolition and
reuse pathway is being considered; this is project positioning, not a claim that
demolition is suspended or a new City review has been opened.

School investigation and implementation do not depend on Sukatto. School order
may change with verified demand, power, communications, building and finance
evidence. Sukatto may join or change priority only after the relevant City/council
decisions, lawful asset procedure, rights and independent feasibility support it.
A favorable technical comparison alone does not include or promote Sukatto.

The immediate request is City interest in exploring feasibility and an appropriate
coordinating office. A DX working group, prefectural coordination or investor-led
project vehicle are options to discuss, not established bodies or commitments.
The preparatory committee facilitates; no operator, board, funder or customer is
appointed by the proposal or by automated research.

## Site 1 — 旧すかっとランド九頭竜 / Sukatto Land Kuzuryu

- Portfolio Priority: **Priority 3 / tertiary optional adaptive-reuse node**.
- Role: onsen + community + education + innovation + AI交番 / thermal offtake; compute only if justified. Sukatto acquisition/reuse is **not a prerequisite for Hanyu launch**.
- Compute capacity: **not preset**.
- Sizing basis: demand + financial viability + verified utility/fiber/site limits.
- Expansion: stage-gated only when demand, heat use, grid/fiber, land, cooling, financing, permits, and public/community decisions support it.
- Financial treatment: maintain a separate reuse scenario; do not treat avoided demolition cost as project cash or committed funding.
- Status: pre-feasibility / PPP-PFI reuse proposal.

## Site 2 — 旧下宇坂小学校 / Former Shimousaka Elementary School

- Portfolio Priority: **Priority 2 / secondary node**.
- Role: second-candidate / future expansion school node, independently costed.
- Site advantage: materially larger campus and potential room for future education, community, disaster-resilience, incubation, and compute functions.
- Compute capacity: **not preset and not utility-confirmed**.
- Sizing basis: add capacity only after customer demand and power/fiber/site conditions justify it.
- BESS-in-gym, fiber, building reuse and interconnection remain concepts requiring engineering and operator confirmation.
- Status: pre-feasibility.
- Official asset evidence: Fukui City's current closed-school reuse page (updated 2026-09-15) lists 旧下宇坂小学校 and publishes the campus/site plan plus school/gym/pool-management floor plans. Treat these as feasibility basemaps, not final engineering/design drawings: https://www.city.fukui.lg.jp/kyoiku/school/school/haiko-rikatsuyou.html

## Site 3 — 旧羽生小学校 / Former Hanyu Elementary School

- Address used for the 2026-09-26 field survey: 福井市大宮町12-31.
- Portfolio Priority: **Priority 1 / primary economic-engine candidate**.
- Role: **initial-priority, grid-first school node candidate**, conditional on utility, fiber, demand, building, legal-use and financing evidence.
- Field evidence on 2026-09-26: major substation/switchyard equipment, multiple high-voltage transmission corridors, and utility telecom/microwave equipment are visible in the immediate landscape.
- Compute capacity: **UNVERIFIED**. Proximity does not establish deliverable load capacity, connection voltage, redundancy, cost, schedule, or commercial/dark-fiber availability.
- Sizing basis: customer/service demand -> revenue/resource demand -> GPU/CPU/storage/network requirements -> IT kW -> facility kW -> compare with utility-confirmed capacity.
- Required next evidence: Hokuriku Electric Power Transmission & Distribution connection response; two-route carrier/fiber study; building/MEP/structural, cooling/water, fire, seismic, flood/landslide, geotechnical, acoustic and access studies; bankable customer/offtake evidence.
- Status: pre-feasibility. Priority is conditional and must be revised if the formal grid/fiber/site evidence does not support it.
- Official asset evidence: the same current Fukui City reuse page lists 旧羽生小学校 and publishes the combined campus/floor-plan set for the school/gym/pool-management buildings. Treat it as feasibility evidence only; it does not establish grid, fiber, legal-use, retrofit or permitting suitability: https://www.city.fukui.lg.jp/kyoiku/school/school/haiko-rikatsuyou.html

## Demand-led financial-model contract

1. **Demand is the sizing input; MW is an output.**
2. Use `Service Catalog` as the product shelf and `Demand & Capacity` as the order-discovery layer.
3. Convert entered orders to annual revenue and resource demand, then to IT/facility kW.
4. Separately calculate a **financial-floor equivalent**: the sold capacity required to support the current Opex / finance scenario. This is a viability warning, **not a build target**.
5. Utility-confirmed capacity is a hard external gate. Until confirmed, site capacity stays UNVERIFIED.
6. Never copy a Site 1 cost, tariff, grant, utility capacity or construction schedule into Site 2 or Site 3 merely to fill a blank.
7. Only `AWARDED` grants may reduce base-case financing need.
8. Customer interviews and LOIs are evidence stages, not bankable revenue. Binding minimum-purchase / take-or-pay, prepayment, or live usage carry stronger underwriting value.
9. Re-run site-specific CapEx, debt service, IRR, DSCR and payback after a real demand-backed phase size and utility connection basis exist.
10. After a primary source, customer contract, or operator response changes a site fact, update this registry first, then reconcile the Drive workbook and public-safe projections.

## Current service catalog

The repository model and Drive workbook carry 24 candidate commercial offers spanning raw GPU compute, reserved/dedicated capacity, inference, model hosting, training/fine-tuning, evaluation, agent runtime, CPU/HPC, managed platforms, storage, backup, data staging, private networking, egress, colocation, disaster recovery, MLOps, Physical AI, sponsored education/community compute, and heat offtake.

Only inherited raw-compute scenarios currently have numerical price assumptions. Most managed/storage/network/facility offers remain `TBD` until feasibility interviews or market quotes establish a defensible billing unit and price.

## Field-survey artifact

Document 07 and its embedded field photographs are the current site-evidence/addendum layer. The photographs support observed site context; they do not prove utility capacity, connection rights, fiber availability, land rights, or engineering suitability.

## Portfolio identity, sequencing and independent gates

| Portfolio priority | Stable canonical identity | Role | Required gate |
| --- | --- | --- | --- |
| 1 | Site 3 — Hanyu | Minimum viable demand-backed compute node | Utility response, fiber route, building feasibility, demand, independent CapEx, finance case, legal/use route |
| 2 | Site 2 — Shimousaka | Expansion campus / second compute node | Additional actual/contracted demand, independent grid/fiber and engineering, acceptable lender DSCR/finance metrics |
| 3 | Site 1 — Sukatto | Optional adaptive reuse, thermal/community/education node | Lawful City route, access/use rights, rehabilitation economics, asbestos/MEP, engineering, thermal-use economics and financing |

Hanyu expansion is a separate Gate 2 budget, never included twice in initial-node
CapEx. Grid proximity sets investigation priority only. Formal evidence can justify
changing priority, including investigating Shimousaka first if Hanyu fails; stable
site IDs do not change. No all-site completion condition or automatic Sukatto
cross-default is assumed. A failed or excluded Sukatto case leaves Hanyu operable.

Fukui City's current school call lists Hanyu and Shimousaka, not Sukatto. Use one
umbrella concept plus asset-specific annexes and the City's correct procedures.
The City's subsequent correspondence directs one prior-consultation form when
treating the two schools as one proposal; the combined Form 1 has been submitted.
This is not approval of eligibility, the project, asset use or a combined contract.
Sukatto needs a separately designated PPP/PFI receiving route; PFI Act Article 6
is an option pending City determination. Source:
https://www.city.fukui.lg.jp/sisei/plan/reform/p073300.html (checked 2026-09-29 JST).
The minimum physical first phase still needs a lawful whole-property use plan.

## FY2026 school asset-proposal procedure — verified 2026-10-01

- Current official source: https://www.city.fukui.lg.jp/sisei/plan/reform/p073300.html (last updated 2026-09-15).
- Listed properties are **旧下宇坂小学校** and **旧羽生小学校**. Sukatto is not in this call.
- Prior consultation is mandatory. The City states a **2026-11-30** cutoff for prior consultation/site survey and a **2026-12-15** proposal-document deadline.
- The current official page links the City form bundle. The official Word artifact remains the submission master; do not recreate a look-alike.
- Subsequent City guidance resolves the prior-consultation filing unit: use one Form 1 for the integrated two-school proposal. A combined Form 1 has been submitted. Final proposal/contract structure and eligibility remain separate questions.
- Utility/carrier inquiries are feasibility evidence and annex material, not separate City asset-proposal properties.
- Keep this `ASSET_PROPOSAL` lane separate from Sukatto's `PPP_PFI` lane.

The portfolio self-funding test in FIN and `run_portfolio_model()` is a hypothesis,
not a guarantee that a first data center pays for all assets. Current output:
**INSUFFICIENT EVIDENCE**. No site-specific CapEx or available capacity is invented.
