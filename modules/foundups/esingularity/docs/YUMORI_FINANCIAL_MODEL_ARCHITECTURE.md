# YUMORI Live Financial Model Architecture

## Authority

The eSingularity FoundUp repository is the canonical implementation/history layer for the YUMORI financial model.

- Python owns assumptions, equations, reconciliation and validation.
- Tests own repeatable mathematical acceptance checks.
- Excel/PDF/Drive/web surfaces are generated, collaboration, or publication artifacts.
- A generated workbook is not allowed to silently become a second calculation authority.

Canonical engine:

`modules/foundups/esingularity/src/yumori_financial_model.py`

Prototype RedDog/WRE discovery contract:

`modules/foundups/esingularity/skillz/yumori_financial_model/SKILLz.md`

## WSP 97 placement result

The model belongs inside `modules/foundups/esingularity/` because it exists to operate and explain the economics of this FoundUp. It is not a generic finance subsystem and not a parallel YUMORI repository.

The implementation follows:

`retrieve WSP -> retrieve evidence -> research -> micro pass -> macro pass -> hard think -> dialectic sweep -> first principles -> execute`

The legacy workbook was inspected before equations were written. Existing RedDog/WRE Rolodex precedent was recovered from the YUMORI contact-ledger Skillz before adding a finance Skillz.

## Ledger separation

The model keeps these ledgers distinct:

1. Project/SPV - revenue, COGS, SG&A, depreciation, debt, tax, FCFE, IRR/NPV.
2. City fiscal - demolition preparation, demolition estimate, city contribution/exposure and risk transfer.
3. Regional economy - visitor spending, local procurement, payroll/jobs and supplier effects.
4. Energy/thermal - electricity/PUE and potentially usable/recoverable heat.
5. Option value - what is lost when irreversible demolition occurs before the preceding ledgers are tested.

Visitor-spending reference values never enter project-company revenue, FCFE or tax calculations.

## Current reconciled base case

The first reconciled code model retains the preset workbook's scenario assumptions unless a contradiction requires a mathematical correction.

Material corrections include:

- revenue is calculated from integer GPU allocation x 8,760 x utilization x tier price;
- power cost uses stated 850 kW IT load x utilization x PUE x hours x tariff;
- PUE base input is 1.115, the midpoint of the legacy 1.11-1.12 range, pending engineering validation;
- compute depreciation ends after the stated four-year useful life;
- debt schedules use formula-driven annuity amortization from principal/rate/term rather than unrelated hard-coded principal/interest lines;
- equity IRR is solved from the actual equity cash-flow sequence;
- NPV is calculated from an explicit discount-rate input.

These are still MODELLED / LEGACY-SCENARIO assumptions, not bankable forecasts or committed financing.

## Workbook export contract

A generated live workbook should preserve the useful prior structure while making the calculation chain visible.

Recommended tabs:

- 0. Model Inputs
- 1. Executive Summary
- 2. Capital Stack & Sources
- 3. Operating Assumptions
- 4. Revenue Model
- 5. OpEx & COGS Breakdown
- 6. Income Statement (P&L)
- 7. Cash Flow & FCFE
- 8. Debt Schedule & DSCR
- 9. Regional Economic Impact
- 10. Impact Assumptions
- 11. 60-Day Validation
- 12. Demand & Pricing
- 13. Audit Checks

The workbook should contain formulas mirroring the Python equations with cached Python-calculated outputs. Editable inputs remain visually distinct. Externally sourced inputs carry source notes/comments.

## Bounded evidence retrieval

Large ModLogs, audit files, work ledgers, repository trees and workbooks must not be dumped wholesale into agent context by default.

1. Search/index first.
2. Read the smallest relevant line/range window (normally 80-200 text lines or one targeted spreadsheet range).
3. Continue only when the current window points to additional required evidence.
4. For spreadsheets inspect named sheets/ranges/formulas instead of loading all cells into context.
5. A larger read requires a known bounded file size and an explicit reason.

This progressive-disclosure rule prevents retrieval failures while preserving WSP 50/WSP 97 traceability.

## History

Material changes use a bounded PR. Review history remains in the PR. Once exact-head validation passes, the slice should be squash-merged so the FoundUp has one discoverable completed change on its main lineage.
