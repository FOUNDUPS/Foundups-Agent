---
name: yumori_financial_model
description: Audit, recalculate, scenario-test, and export the YUMORI/eSingularity financial model from repository-owned equations without treating generated spreadsheets or legacy outputs as calculation authority.
version: 0.1.0
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
evals:
  - name: repo_is_calculation_authority
    expected: python_model_precedes_spreadsheet_output
  - name: legacy_truth_boundary
    expected: legacy_outputs_that_fail_reconciliation_are_flagged_not_copied
  - name: regional_value_separation
    expected: visitor_spend_is_never_project_revenue_or_tax_revenue
  - name: finance_reconciliation
    expected: revenue_power_depreciation_debt_fcfe_irr_and_npv_are_equation_driven
  - name: bounded_retrieval
    expected: large_repo_artifacts_are_searched_then_read_in_small_relevant_windows
  - name: reddog_boundary
    expected: reddog_discovers_and_routes_but_does_not_invent_financial_results
retirement_date: null
---
# YUMORI / eSingularity Financial Model

## Three Skill Questions

1. **Do we need it?** Yes. Financial-model audit, scenario changes, public-number reconciliation, and spreadsheet regeneration recur and materially affect campaign credibility.
2. **Can we live without it?** Poorly. Reconstructing formulas from chat or from presentation workbooks creates drift and silently reintroduces stale numbers.
3. **Can we afford not to have it?** No. Incorrect IRR, power, debt, tax, revenue, or public-impact claims create material decision and credibility risk.

Decision: maintain one module-owned prototype Skillz. Do not split separate IRR, spreadsheet, demand, or audit Skillz unless a future workflow independently passes the Three Skill Questions.

## Purpose

Route financial-model work to the canonical Python calculation engine in:

`modules/foundups/esingularity/src/yumori_financial_model.py`

The repository owns assumptions, equations, reconciliation rules, and tests. Excel/PDF/Drive/web outputs are generated or publication surfaces.

## Positive triggers

Use this Skillz when asked to:
- audit the YUMORI / eSingularity financial workbook;
- compare a legacy/static financial model with a new model;
- change capacity, utilization, pricing, power, PUE, CapEx, debt, tax, staffing, or other financial assumptions;
- calculate or reconcile revenue, EBITDA, FCFE, NPV, IRR, DSCR, debt schedules, depreciation, or power expense;
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
4. Run a macro pass on P&L, cash flow, debt, public-value ledgers, and public copy affected downstream.
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

## Reconciliation invariants

- Tier revenue = integer GPUs x 8,760 hours x utilization x price.
- Power expense = stated IT kW x utilization x PUE x 8,760 x tariff unless a later engineering model explicitly replaces it.
- Depreciation stops when the useful life ends.
- Debt interest and principal reconcile to the stated financing method/terms.
- FCFE reconciles to CFO - maintenance CapEx - principal repayment.
- Equity IRR is solved from the actual equity cash-flow sequence; never hard-code the displayed result.
- Sources equal uses at initial funding.
- Every modelled result remains modelled until validated by external evidence.

## Legacy workbook rule

The preset workbook is evidence of the intended structure and assumptions, not calculation authority. Preserve useful assumptions and layout, but record and correct arithmetic contradictions. `audit_legacy_model()` is the current deterministic reconciliation surface.

## RedDog / Rolodex behavior

RedDog should discover this Skillz for YUMORI/eSingularity finance requests and hand the work to the governed calculation path. RedDog may summarize a validated result returned by the model; it must not infer, interpolate, or invent missing financial values.

This prototype grants no authority to publish new financial claims, commit financing, represent grants as awarded, or treat demand leads as customer commitments.
