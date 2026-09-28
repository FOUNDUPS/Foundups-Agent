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

`FIN — YUMORI Phase 1 Financial Model & Grant Audit — 2026-09-12`

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
