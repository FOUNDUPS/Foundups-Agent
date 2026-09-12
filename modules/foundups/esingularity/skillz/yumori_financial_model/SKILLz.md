---
name: yumori_financial_model
description: Audit, recalculate, scenario-test, feasibility-test, and export the YUMORI/eSingularity financial model from repository-owned equations without treating generated spreadsheets or legacy outputs as calculation authority.
version: 0.2.0
intent_type: ANALYSIS
promotion_state: prototype
category: workflow
agents:
  - qwen
  - gemma
wsp_chain:
  - WSP 00
  - WSP 15
  - WSP 22
  - WSP 50
  - WSP 84
  - WSP 95
  - WSP 97
  - WSP 109
evals:
  - name: repo_is_calculation_authority
    expected: python_model_precedes_spreadsheet_output
  - name: legacy_truth_boundary
    expected: legacy_outputs_that_fail_reconciliation_are_flagged_not_copied
  - name: regional_value_separation
    expected: visitor_spend_is_never_project_revenue_or_tax_revenue
  - name: finance_reconciliation
    expected: revenue_power_depreciation_debt_fcfe_irr_and_npv_are_equation_driven
  - name: customer_cash_boundary
    expected: annual_revenue_nominal_contract_value_and_actual_upfront_cash_are_distinct
  - name: debt_capacity_boundary
    expected: deployed_debt_is_lesser_of_remaining_gap_and_dscr_supported_capacity
  - name: bounded_retrieval
    expected: large_repo_artifacts_are_searched_then_read_in_small_relevant_windows
  - name: reddog_boundary
    expected: reddog_discovers_and_routes_but_does_not_invent_financial_results
retirement_date: null
---
# YUMORI / eSingularity Financial Model

## Three Skill Questions

1. **Do we need it?** Yes. Financial-model audit, feasibility funding, customer/offtake validation, scenario changes, public-number reconciliation, and spreadsheet regeneration recur and materially affect campaign credibility.
2. **Can we live without it?** Poorly. Reconstructing formulas from chat or from presentation workbooks creates drift and silently reintroduces stale numbers.
3. **Can we afford not to have it?** No. Incorrect IRR, power, debt, tax, revenue, customer cash, or public-impact claims create material decision and credibility risk.

Decision: maintain one module-owned prototype Skillz. Do not split separate IRR, spreadsheet, demand, funding, or audit Skillz unless a future workflow independently passes the Three Skill Questions.

## Purpose

Route core financial-model work to:

`modules/foundups/esingularity/src/yumori_financial_model.py`

Route feasibility-funding and customer/offtake evidence work to:

`modules/foundups/esingularity/src/yumori_feasibility_finance.py`

The repository owns assumptions, equations, reconciliation rules, and tests. Excel/PDF/Drive/web outputs are generated or publication surfaces. The feasibility module is an adjacent evidence/capital gate; it does not replace the canonical Phase-1 P&L engine.

## Positive triggers

Use this Skillz when asked to:
- audit the YUMORI / eSingularity financial workbook;
- compare a legacy/static financial model with a new model;
- change capacity, utilization, pricing, power, PUE, CapEx, debt, tax, staffing, or other financial assumptions;
- calculate or reconcile revenue, EBITDA, FCFE, NPV, IRR, DSCR, debt schedules, depreciation, or power expense;
- assess NCDS-style feasibility funding, pre-debt funding targets, customer deposits/prepayments, or remaining project funding gaps;
- distinguish customer annual revenue, nominal multi-year contract value, take-or-pay evidence, and actual upfront construction cash;
- size debt from CFADS / DSCR / rate / term and cap deployed debt at the remaining funding requirement;
- evaluate 1–5 MW planning capacity and customer/offtake evidence without double-counting the same physical GPU pool;
- regenerate or export the YUMORI financial workbook;
- explain why a financial output changed;
- reconcile numbers shown on eSingularity/YUMORI public surfaces with the code model.

## Non-triggers

Do not use this for unrelated personal finance, generic accounting education, or one-off arithmetic with no YUMORI/eSingularity model relationship.

## Truth hierarchy

```text
verified external evidence / signed commercial terms
  -> repository assumptions + source/status labels
  -> repository Python equations + tests
  -> generated workbook / model JSON
  -> public website / PDF summary
  -> chat recollection
```

A spreadsheet cell is not authoritative merely because it exists. A model output is not a verified fact merely because an equation produced it.

## WSP 97 operating procedure

1. Retrieve governing WSPs and the exact eSingularity finance code before stating current model facts.
2. Retrieve the smallest relevant workbook/source evidence before changing assumptions.
3. Run a micro pass on the exact equation/assumption being changed.
4. Run a macro pass on P&L, cash flow, debt, public-value ledgers, feasibility funding, customer/offtake, and public copy affected downstream.
5. Run the dialectic sweep: existing formula, competing interpretation, missing evidence, strongest downside case.
6. Change repository assumptions/equations first.
7. Run focused model tests and validation checks.
8. Generate/re-generate publication artifacts from the code result.
9. Compare output to the prior workbook and record material deltas.
10. Update eSingularity documentation/ModLog when the canonical model changes.

## Bounded retrieval rule

Large ModLogs, audits, work ledgers, trees, and workbooks must not be dumped wholesale into agent context by default.

- Search/index first.
- Read the smallest useful line/range window, normally 80-200 lines or a specific spreadsheet range.
- Continue only when the current window points to additional required evidence.
- For spreadsheet audits, inspect named sheets/ranges/formulas rather than exporting every cell into context.
- A deliberate larger read requires a known bounded file size and a reason that the whole artifact is necessary.

This is a reliability rule: progressive disclosure reduces retrieval failures and keeps WSP 97 evidence traceable.

## Ledger boundaries

Keep five ledgers distinct:
1. **Project/SPV** - compute/thermal revenue, COGS, SG&A, depreciation, debt, tax, FCFE.
2. **City fiscal** - demolition preparation, demolition, city contribution/exposure, avoided/shifted burden.
3. **Regional economy** - visitor spending, local procurement, payroll, company formation, supplier effects.
4. **Energy/thermal** - electricity, PUE, recoverable/usable heat, avoided local fuel/electricity.
5. **Option value** - value lost by irreversible demolition before the preceding ledgers are tested.

Never add visitor-spending reference values into project-company revenue or tax receipts.

## Customer/offtake accounting boundary

The same physical GPU pool may support several products, but capacity must never be double-counted.

For each customer/offtake record distinguish:
- annual contracted operating revenue;
- nominal multi-year contract value;
- take-or-pay / minimum-purchase evidence;
- deposit/prepayment percentage;
- **actual upfront cash received/committed before operations**.

Normal university or corporate compute purchases do not become construction capital. Nominal contract value does not reduce the funding gap. Only explicit actual upfront cash from `VERIFIED` or `COMMITTED` records enters the pre-debt construction funding calculation.

## Feasibility funding boundary

The current NCDS-style feasibility calculation lives in `yumori_feasibility_finance.py` and is intentionally not yet wired into the canonical P&L/debt schedule.

Pre-debt cash includes only explicit committed cash sources:
- city cash support;
- prefecture committed cash;
- national awarded support;
- verified/committed customer upfront cash;
- private quiet-phase capital commitments;
- public campaign capital commitments.

The following are reported separately and do **not** automatically reduce the cash funding gap:
- city in-kind support;
- candidate/potential grants or support;
- ordinary annual customer revenue;
- nominal multi-year contract value;
- non-cash take-or-pay evidence.

Debt rule:

`deployed debt = MIN(remaining funding requirement, DSCR-supported amortizing debt capacity)`

If a gap remains after debt, the model must expose the gap rather than forcing the financing to close.

## Reconciliation invariants

- Tier revenue = integer GPUs x 8,760 hours x utilization x price.
- Power expense = stated IT kW x utilization x PUE x 8,760 x tariff unless a later engineering model explicitly replaces it.
- Depreciation stops when the useful life ends.
- Debt interest and principal reconcile to the stated financing method/terms.
- FCFE reconciles to CFO - maintenance CapEx - principal repayment.
- Equity IRR is solved from the actual equity cash-flow sequence; never hard-code the displayed result.
- Sources equal uses at initial funding.
- Customer annual revenue, nominal contract value, and actual upfront cash never share one field or arithmetic role.
- Potential support and in-kind support never silently become cash funding.
- Every modelled result remains modelled until validated by external evidence.

## Legacy workbook rule

The preset workbook is evidence of the intended structure and assumptions, not calculation authority. Preserve useful assumptions and layout, but record and correct arithmetic contradictions. `audit_legacy_model()` is the current deterministic reconciliation surface.

## RedDog / Rolodex behavior

RedDog should discover this Skillz for YUMORI/eSingularity finance, feasibility-funding, customer/offtake, and workbook requests and hand the work to the governed calculation path. RedDog may summarize a validated result returned by the model; it must not infer, interpolate, or invent missing financial values.

This prototype grants no authority to publish new financial claims, commit financing, represent grants as awarded, treat demand leads as customer commitments, or treat nominal contracts as received construction cash.
