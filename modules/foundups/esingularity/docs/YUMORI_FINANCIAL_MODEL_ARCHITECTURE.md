# YUMORI Live Financial Model Architecture

## Authority

The eSingularity FoundUp repository is the canonical implementation/history layer for the YUMORI financial model.

- Python owns assumptions, equations, reconciliation and validation.
- Tests own repeatable mathematical acceptance checks.
- Excel/PDF/Drive/web surfaces are generated, collaboration, or publication artifacts.
- A generated workbook is not allowed to silently become a second calculation authority.

Canonical operating engine:

`modules/foundups/esingularity/src/yumori_financial_model.py`

Adjacent feasibility/evidence engine:

`modules/foundups/esingularity/src/yumori_feasibility_finance.py`

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

## Feasibility evidence layer

`yumori_feasibility_finance.py` is deliberately adjacent to the canonical operating model rather than embedded into it prematurely. It captures the NCDS-style evidence/capital sequence while preserving the existing P&L/debt outputs until the evidence contract is independently validated.

### Customer/offtake contract

Each customer record can distinguish:

- organization and customer type;
- product;
- requested GPUs/nodes and hours/month or reserved capacity;
- start date and contract term;
- current provider/current price and proposed YUMORI price;
- annual contracted value;
- nominal multi-year contract value;
- take-or-pay/minimum commitment;
- deposit/prepayment percentage;
- actual upfront cash;
- procurement constraints;
- evidence status and source.

Critical accounting boundary:

- normal operating contracts are revenue/underwriting evidence;
- nominal multi-year contract value is not construction cash;
- take-or-pay improves bankability but is not automatically cash;
- only explicit actual upfront cash on VERIFIED/COMMITTED records reduces the pre-debt construction funding gap.

### Feasibility funding contract

The current pure calculation surface measures:

- Phase-1 project cost;
- committed City cash support;
- City in-kind support reported separately;
- committed Prefecture cash;
- awarded national support;
- verified/committed customer upfront cash;
- private quiet-phase capital commitments;
- public campaign capital commitments;
- potential public support reported separately;
- pre-debt cash total and funding percentage;
- adjustable pre-debt target (default 80%);
- remaining funding gap;
- CFADS, DSCR requirement, interest rate and loan term;
- DSCR-supported amortizing debt capacity;
- deployed debt = MIN(remaining funding requirement, supportable debt);
- remaining unfunded gap after debt.

If a gap remains, the model exposes it. It does not force a financial close.

### Capacity planning boundary

Planning relationship:

- 1 MW ~= 384 GPUs ~= 48 x 8-GPU nodes;
- 5 MW ~= 1,920 GPUs ~= 240 x 8-GPU nodes.

This is a planning relationship, not a grid/procurement commitment. Multiple products may monetize one physical GPU pool, but the same capacity must never be counted twice.

## Workbook export contract

A generated live workbook should preserve the useful prior structure while making the calculation chain visible.

Current stable tabs:

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

Future feasibility sheets should be appended by domain name rather than renumbering existing stable sheets blindly, for example:

- NCDS Feasibility Funding
- 1–5 MW Pricing & Offtake

The workbook should contain formulas mirroring the Python equations with cached Python-calculated outputs. Editable inputs remain visually distinct. Externally sourced inputs carry source notes/comments.

## Bounded evidence retrieval

Large ModLogs, audit files, work ledgers, repository trees and workbooks must not be dumped wholesale into agent context by default.

1. Search/index first.
2. Read the smallest relevant line/range window (normally 80-200 text lines or one targeted spreadsheet range).
3. Continue only when the current window points to additional required evidence.
4. For spreadsheets inspect named sheets/ranges/formulas instead of loading all cells into context.
5. A larger read requires a known bounded file size and an explicit reason.

This progressive-disclosure rule prevents retrieval failures while preserving WSP 50/WSP 97 traceability.

## Validation and integration gates

- The canonical operating model and exporter already have focused tests on their finance implementation branch.
- The feasibility/offtake layer has focused contract tests for revenue/nominal/upfront-cash separation, committed-vs-potential funding, 80% pre-debt target, DSCR debt capacity, and capacity scaling.
- The feasibility layer is not yet allowed to alter the canonical P&L/debt model.
- Integration into exporter or operating statements requires a separate bounded sprint with reconciliation tests.
- Exact-head CI must be reported honestly; absence of a CI run is not a green test result.

## History

Material changes use a bounded PR. Review history remains in the PR. Finance work was audit-first consolidated into the existing eSingularity/YUMORI branch rather than maintained as a parallel source of truth. Once exact-head validation passes, the completed slice should be squash-merged so the FoundUp has one discoverable change on its main lineage.
