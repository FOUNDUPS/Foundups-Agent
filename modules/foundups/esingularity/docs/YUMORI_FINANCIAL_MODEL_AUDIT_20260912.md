# YUMORI Financial Model Audit — 2026-09-12

## Scope

Compared the earlier preset workbook (`FIN_YUMORI_Integrated_Financial_Economic_Model.xlsx`) and the newer workbook (`..._v2.xlsx`) against the actual equations now implemented in `src/yumori_financial_model.py`.

The preset workbook remains useful as the intended presentation/assumption structure. The v2 workbook adds a useful demand/pricing validation tab. Neither workbook makes the core project statements fully formula-driven; therefore the repository Python model is now the calculation authority.

## Workbook structure finding

Preset workbook: 11 tabs.

V2 workbook: the same 11 tabs plus `12. Demand & Pricing`.

The new demand/pricing tab performs useful public benchmark and sensitivity arithmetic, but the main revenue, P&L, cash-flow and debt statement values are still substantially inherited/hard-coded rather than calculated through a single auditable chain.

## Reconciliation findings

### 1. Equity IRR does not reconcile

Preset displayed value: **68.4%**.

Using the preset's displayed sponsor equity of ¥390,000,000 and its displayed five annual FCFE values:

- Y1 ¥161,810,153
- Y2 ¥310,038,357
- Y3 ¥359,762,827
- Y4 ¥357,472,092
- Y5 ¥755,264,092

solves to approximately **66.9041%**, not 68.4%.

Gap: approximately **1.496 percentage points**.

Rule: public IRR must be solved from the actual equity cash-flow sequence and never copied as a hard-coded summary output.

### 2. Electricity expense does not match stated power assumptions

Preset operating assumptions state:

- IT compute allocation: **850 kW**
- PUE: **1.11-1.12**
- tariff: **¥19.50/kWh**

But the preset annual electricity expense sequence mathematically implies approximately **840 kW × utilization × 8,760 × ¥19.50**, before applying any PUE multiplier.

Therefore the expense line does not reconcile to the stated 850 kW IT load and stated PUE range.

Reconciled base equation:

`power_cost = 850 kW × utilization × 1.115 PUE × 8,760 × ¥19.50/kWh`

The 1.115 PUE input is the midpoint of the legacy range and remains an engineering assumption requiring validation.

### 3. Compute depreciation extends beyond stated useful life

Preset states compute hardware is depreciated on a **4-year straight-line** basis, with ¥1.8B compute CapEx.

Correct annual depreciation is ¥450M in Years 1-4 and **¥0 in Year 5**, absent replacement CapEx or another depreciable asset addition.

Preset instead shows ¥450M again in Year 5.

### 4. Compute-debt interest does not reconcile to 6.5% beginning balance

Preset labels the compute debt as 6.5%, but its displayed interest is lower than beginning balance × 6.5%.

Examples:

- Y1 beginning balance ¥1.44B → 6.5% = **¥93.6M**, preset displays **¥84.0M**.
- Y2 beginning balance ¥1.115B → 6.5% = **¥72.475M**, preset displays **¥62.0M**.
- Y3 beginning balance ¥768M → 6.5% = **¥49.92M**, preset displays **¥39.0M**.
- Y4 beginning balance ¥398M → 6.5% = **¥25.87M**, preset displays **¥14.0M**.

The new code model uses formula-driven annuity amortization from principal, rate and term. Financing remains a scenario, not a lender commitment.

### 5. Tier revenue contains hard-coded drift

The stated physical/pricing inputs imply:

`tier revenue = integer tier GPUs × 8,760 × utilization × price per GPU-hour`

Tier A is largely consistent except a ¥960 difference in Years 4-5.

Tier B preset values are below direct equation results by approximately ¥0.267M to ¥0.390M/year.

Tier C preset values are below direct equation results by approximately ¥0.249M to ¥0.364M/year.

The differences are small relative to total revenue but demonstrate that the main revenue schedule was not generated from one canonical equation chain.

### 6. V2 Demand & Pricing is useful but not the core engine

The V2 tab correctly adds:

- public H100 price benchmarks;
- 1 MW technical sanity checks;
- utilization sensitivity;
- a demand interview pipeline;
- explicit warnings that public DX activity is not booked demand.

However its Year-1 compute revenue and blended-price calculations still reference the inherited model outputs. It therefore validates context around the static model rather than replacing the static model with an end-to-end live calculation engine.

## First reconciled code result

Using the retained legacy scenario inputs but correcting the formula chain:

- 5-year gross revenue: approximately **¥5.37449B**
- 5-year EBITDA: approximately **¥4.08910B**
- 5-year FCFE: approximately **¥1.69143B**
- equity IRR: approximately **59.72%**
- equity NPV at 12%: approximately **¥751.41M**

These are **model outputs**, not forecasts, financing commitments, or guaranteed returns.

The largest reasons the reconciled result differs from the preset are:

- power cost now reflects stated IT load and PUE;
- debt interest/principal are formula-driven;
- Year-5 compute depreciation stops after the stated four-year life;
- revenue is calculated from integer GPU counts and tier rates.

## Public-value boundary retained

The model intentionally does not add the following to project revenue:

- visitor-spending reference range;
- academic benefit/subsidy-equivalent value;
- local procurement value;
- jobs/FTE count;
- heat/fuel offset that is not contracted project revenue;
- demolition avoidance/option value.

The visitor-spending range remains a regional screening reference only:

- annual: ¥129.649M to ¥719.033354M
- 30-year undiscounted screen: ¥3.88947B to ¥21.570...B

It is not YUMORI revenue, tax revenue, or a demand forecast.

## Validation state

Local isolated validation of the pure-Python calculation engine: **7 focused tests passed** before repository commit.

Repository/CI exact-head validation remains required after all files in this PR are assembled.

## Next implementation step

Generate the Excel workbook from the repository model so that:

- user-editable assumptions are explicit;
- workbook formulas mirror the Python equations;
- cached values are produced from Python;
- source/status labels remain visible;
- an Audit Checks tab exposes reconciliation and legacy deltas;
- the workbook can be regenerated reproducibly after any assumption change.
