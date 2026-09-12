# YUMORI NCDS Feasibility Finance — Phase 1

**Date:** 2026-09-12  
**Owner:** `modules/foundups/esingularity/`  
**Status:** Evidence/accounting contract implemented; canonical P&L integration intentionally deferred.

## Audit-first decision

Before implementation, the current eSingularity finance branches, Python engine, exporter, tests, Skillz/Rolodex, roadmap and FIN.YUMORI workbooks were compared under WSP 97.

The stronger existing implementation was preserved:

- `src/yumori_financial_model.py` — canonical operating/financial calculation engine;
- `src/yumori_financial_export.py` — generated XLSX projection;
- model/export tests;
- `skillz/yumori_financial_model/` — RedDog/WRE discovery contract;
- finance audit/architecture docs.

A smaller duplicate `src/finance/` engine was removed during branch consolidation. The current slice does not create another P&L engine.

## New Phase-1 surface

`src/yumori_feasibility_finance.py`

Purpose: represent customer/offtake evidence and an NCDS-style funding waterfall **without changing the canonical Phase-1 P&L/debt outputs yet**.

## Customer/offtake accounting rules

A customer record distinguishes:

- annual contracted operating revenue;
- nominal multi-year contract value;
- take-or-pay/minimum commitment;
- deposit/prepayment percentage;
- actual upfront cash;
- procurement constraints;
- evidence status/source.

Critical invariant:

> Ordinary university/corporate compute purchases are operating revenue and underwriting evidence, not construction capital.

Nominal contract value does not become cash. A take-or-pay agreement may improve bankability but does not become cash. Only explicit actual upfront cash from `VERIFIED` / `COMMITTED` records enters pre-debt construction funding.

Evidence statuses:

- `VERIFIED`
- `COMMITTED`
- `POTENTIAL`
- `MODEL ONLY`

Potential/model-only rows do not enter committed funding.

## NCDS-style pre-debt funding waterfall

Pre-debt construction cash includes:

1. City committed cash support;
2. Prefecture committed cash support;
3. national awarded support;
4. verified/committed customer upfront cash;
5. private quiet-phase capital commitments;
6. public campaign capital commitments.

Reported separately, not counted as pre-debt cash:

- City in-kind support;
- potential/candidate public support;
- annual customer operating revenue;
- nominal multi-year contract value;
- non-cash take-or-pay evidence.

Default target:

`pre_debt_target_pct = 80%`

The target is adjustable and is a feasibility assumption, not a rule that financing must satisfy in every structure.

## Debt capacity

Maximum annual debt service:

`CFADS / required DSCR`

Supportable amortizing principal is solved from maximum annual debt service, interest rate and term.

Deployed debt:

`MIN(remaining funding requirement, DSCR-supported debt capacity)`

If a residual gap remains, the model exposes it. The project must increase committed capital/prepayments, improve cash flow, reduce/resize CapEx, restructure financing, or stop. Debt is not forced to equal the funding gap.

## Capacity planning

Current planning relationship:

- 1 MW ~= 384 GPUs ~= 48 x 8-GPU nodes;
- 5 MW ~= 1,920 GPUs ~= 240 x 8-GPU nodes.

This is a planning relationship only. It does not establish grid availability, procurement, actual GPU power density or build permission.

The same physical capacity may be monetized through multiple products, but the physical GPU pool must not be double-counted.

## Focused test contract

`tests/test_yumori_feasibility_finance.py` covers:

- 1 MW / 5 MW planning scale;
- annual revenue vs nominal contract value vs actual upfront cash;
- deposit percentage does not manufacture cash;
- POTENTIAL / MODEL ONLY demand does not enter committed funding;
- City in-kind and potential grants do not reduce the cash gap;
- 80% pre-debt target;
- DSCR-supported debt capacity;
- deployed debt capped by `MIN(gap, capacity)`;
- remaining gap when debt capacity is insufficient;
- fail-closed invalid inputs.

Independent arithmetic check performed during the slice:

- CFADS ¥300M;
- required DSCR 1.5x;
- maximum annual debt service ¥200M;
- 6% / 10-year supportable amortizing principal ~= ¥1.472B.

This arithmetic check is not a substitute for exact-head repository pytest/CI.

## Deferred intentionally

Not part of this Phase-1 evidence layer:

- feeding customer contracts directly into canonical revenue;
- deriving required MW automatically from the customer pipeline;
- replacing legacy CapEx with vendor quotes;
- changing the existing debt schedule;
- adding the NCDS/offtake sheets to the XLSX exporter;
- treating candidate grants as committed;
- treating LOIs as booked revenue or cash;
- claiming a bankable financial close.

Those require later bounded sprints and reconciliation tests.

## Next safe sprint

Project the tested evidence layer into generated workbook sheets while preserving the Python engine as authority. Use domain names rather than renumbering existing sheets blindly; the current workbook already uses `13. Audit Checks`.

Candidate appended sheets:

- `NCDS Feasibility Funding`
- `1–5 MW Pricing & Offtake`

Do not connect those sheets to canonical P&L/debt outputs until the evidence-to-operating-model integration has its own tests and explicit approval boundary.
