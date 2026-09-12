"""Single read contract for YUMORI/eSingularity financial projections.

This module does not implement financial equations. It composes the existing
repo-owned authorities into one serializable payload for API, website, workbook,
and audit consumers:

- operating model: ``yumori_financial_model.py``
- feasibility/offtake: ``yumori_feasibility_finance.py``
- physical reservations: ``yumori_capacity_allocation.py``
- public 1-5 MW planning: ``yumori_capacity_economics.py``
- municipal facility history: ``yumori_facility_history.py``
- products/benchmarks/public funding: ``yumori_financial_catalog.py``
- market comparison: ``yumori_price_reconciliation.py``

A caller may request the operating/catalog snapshot without inventing funding
inputs. Feasibility is calculated only when explicit ``FeasibilityFundingInputs``
are provided.

WSP: 3, 15, 22, 50, 84, 95, 97, 109.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Dict, Iterable

from .yumori_capacity_allocation import (
    audit_gpu_capacity,
    require_committed_capacity_valid,
)
from .yumori_capacity_economics import capacity_economics_table
from .yumori_facility_history import build_public_facility_history
from .yumori_feasibility_finance import (
    CustomerOfftake,
    FeasibilityFundingInputs,
    calculate_feasibility_funding,
    capacity_plan,
    summarize_offtake,
)
from .yumori_financial_catalog import (
    FinancialCatalog,
    build_public_catalog_snapshot,
    load_catalog,
)
from .yumori_financial_model import (
    ModelAssumptions,
    calculate_model,
    default_assumptions,
)
from .yumori_price_reconciliation import build_price_reconciliation

SNAPSHOT_SCHEMA_VERSION = "yumori.finance.snapshot.v1"


def _operating_projection(assumptions: ModelAssumptions) -> Dict[str, object]:
    result = calculate_model(assumptions)
    return {
        "status": "MODEL ONLY / VALIDATE INPUTS",
        "model_name": assumptions.model_name,
        "assumptions": asdict(assumptions),
        "years": [asdict(year) for year in result.years],
        "debt_schedules": {
            key: [asdict(row) for row in rows]
            for key, rows in result.debt_schedules.items()
        },
        "summary": {
            "five_year_revenue_jpy": result.five_year_revenue_jpy,
            "five_year_ebitda_jpy": result.five_year_ebitda_jpy,
            "five_year_fcfe_jpy": result.five_year_fcfe_jpy,
            "equity_irr": result.equity_irr,
            "equity_npv_jpy": result.equity_npv_jpy,
            "initial_equity_jpy": result.initial_equity_jpy,
            "visitor_spend_30y_low_jpy": result.visitor_spend_30y_low_jpy,
            "visitor_spend_30y_high_jpy": result.visitor_spend_30y_high_jpy,
        },
        "validation": dict(result.validation),
        "truth_boundary": (
            "Equation-driven scenario output. It is not a forecast, financing "
            "commitment, customer contract, grant award, or verified project return."
        ),
    }


def build_finance_snapshot(
    assumptions: ModelAssumptions | None = None,
    *,
    catalog: FinancialCatalog | None = None,
    customer_offtake: Iterable[CustomerOfftake] = (),
    funding_inputs: FeasibilityFundingInputs | None = None,
) -> Dict[str, object]:
    """Compose the canonical website/API read model.

    ``funding_inputs`` is deliberately optional. If it is omitted, the snapshot
    reports feasibility as NOT_RUN rather than fabricating capital commitments or
    a lender CFADS assumption. Explicit customer records are always audited
    against the current physical GPU inventory.
    """
    a = assumptions or default_assumptions()
    c = catalog or load_catalog()
    records = tuple(customer_offtake)
    capacity_allocation = audit_gpu_capacity(a.total_gpus, records)
    snapshot: Dict[str, object] = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "foundup_id": c.foundup_id,
        "as_of": c.as_of,
        "operating_model": _operating_projection(a),
        "facility_history": build_public_facility_history(),
        "catalog": build_public_catalog_snapshot(c),
        "price_reconciliation": build_price_reconciliation(c),
        "capacity_planning": [asdict(capacity_plan(mw)) for mw in range(1, 6)],
        "capacity_economics": [row.as_dict() for row in capacity_economics_table(a)],
        "capacity_allocation": capacity_allocation.as_dict(),
    }

    if funding_inputs is None:
        snapshot["feasibility"] = {
            "status": "NOT_RUN",
            "reason": (
                "Explicit project-funding and CFADS inputs are required. "
                "The public snapshot does not infer commitments from modelled "
                "grants, nominal contracts, or EBITDA."
            ),
            "customer_record_count": len(records),
        }
        return snapshot

    # Feasibility/funding work may use signed or verified reservations as evidence,
    # so overcommitted physical capacity is a hard failure before any funding result.
    require_committed_capacity_valid(a.total_gpus, records)
    offtake = summarize_offtake(records)
    funding = calculate_feasibility_funding(funding_inputs, offtake)
    snapshot["feasibility"] = {
        "status": "CALCULATED FROM EXPLICIT INPUTS",
        "offtake": asdict(offtake),
        "funding_inputs": asdict(funding_inputs),
        "funding_result": asdict(funding),
        "truth_boundary": (
            "Annual contracted revenue, nominal multi-year value, take-or-pay "
            "evidence, and actual upfront cash remain separate. Only explicit "
            "verified/committed upfront cash enters pre-debt construction funding, "
            "and committed GPU reservations cannot exceed physical inventory."
        ),
    }
    return snapshot


def export_finance_snapshot_json(
    path: str | Path,
    assumptions: ModelAssumptions | None = None,
    *,
    catalog: FinancialCatalog | None = None,
    customer_offtake: Iterable[CustomerOfftake] = (),
    funding_inputs: FeasibilityFundingInputs | None = None,
) -> Path:
    """Write a deterministic UTF-8 JSON projection for web/build consumers."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_finance_snapshot(
        assumptions,
        catalog=catalog,
        customer_offtake=customer_offtake,
        funding_inputs=funding_inputs,
    )
    output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output
