# YUMORI / eSingularity — Candidate Site Registry

Last audited: 2026-09-28 JST

## Authority and workflow

This repository record is the canonical project-status and site-assumption authority. The repository economic model at `src/yumori_economic_model.py` is the calculation/sizing authority. The Drive FIN workbook is the formula-driven working projection, interview, and audit surface.

**Do not choose MW first.** Node size is derived from customer/service demand, the revenue required to support the operating/finance case, equipment power characteristics, PUE, and finally the utility-confirmed site capacity. Until the utility confirms a deliverable capacity, school-site kW/MW remains **UNVERIFIED**.

Current Drive working model: **FIN — YUMORI Phase 1 Financial Model & Grant Audit — 2026-09-12** (`1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0`).

Current decision tabs include `Service Catalog`, `Demand & Capacity`, `Node Sizing`, and one candidate-site tab per site. The older integrated XLSX remains reference-only.

## Site 1 — 旧すかっとランド九頭竜 / Sukatto Land Kuzuryu

- Role: regional human-facing hub: onsen + community + education + innovation + AI交番 / COGDC adaptive reuse.
- Compute capacity: **not preset**.
- Sizing basis: demand + financial viability + verified utility/fiber/site limits.
- Expansion: stage-gated only when demand, heat use, grid/fiber, land, cooling, financing, permits, and public/community decisions support it.
- Financial treatment: maintain a separate reuse scenario; do not treat avoided demolition cost as project cash or committed funding.
- Status: pre-feasibility / PPP-PFI reuse proposal.

## Site 2 — 旧下宇坂小学校 / Former Shimousaka Elementary School

- Role: second-candidate / future expansion school node.
- Site advantage: materially larger campus and potential room for future education, community, disaster-resilience, incubation, and compute functions.
- Compute capacity: **not preset and not utility-confirmed**.
- Sizing basis: add capacity only after customer demand and power/fiber/site conditions justify it.
- BESS-in-gym, fiber, building reuse and interconnection remain concepts requiring engineering and operator confirmation.
- Status: pre-feasibility.

## Site 3 — 旧羽生小学校 / Former Hanyu Elementary School

- Address used for the 2026-09-26 field survey: 福井市大宮町12-31.
- Role: **initial-priority, grid-first school node candidate**, conditional on formal utility and carrier confirmation.
- Field evidence on 2026-09-26: major substation/switchyard equipment, multiple high-voltage transmission corridors, and utility telecom/microwave equipment are visible in the immediate landscape.
- Compute capacity: **UNVERIFIED**. Proximity does not establish deliverable load capacity, connection voltage, redundancy, cost, schedule, or commercial/dark-fiber availability.
- Sizing basis: customer/service demand -> revenue/resource demand -> GPU/CPU/storage/network requirements -> IT kW -> facility kW -> compare with utility-confirmed capacity.
- Required next evidence: Hokuriku Electric Power Transmission & Distribution connection response; two-route carrier/fiber study; building/MEP/structural, cooling/water, fire, seismic, flood/landslide, geotechnical, acoustic and access studies; bankable customer/offtake evidence.
- Status: pre-feasibility. Priority is conditional and must be revised if the formal grid/fiber/site evidence does not support it.

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
