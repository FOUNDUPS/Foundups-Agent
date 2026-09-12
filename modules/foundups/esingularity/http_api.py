"""eSingularity / YUMORI finance HTTP surface.

Thin FastAPI transport for the repository-owned finance model.  This module
contains no financial equations and no persistent mutation.  It delegates to:

- ``yumori_financial_catalog`` for products/market/funding evidence,
- ``yumori_financial_snapshot`` for the canonical read projection,
- ``yumori_financial_service`` for bounded dynamic scenarios.

Intended deployment topology:

    eSingularity frontend (Node/Cloudflare/OpenAI Sites)
        -> HTTPS finance endpoint
        -> this thin transport
        -> canonical Python model/service

The frontend must not reproduce financial equations in TypeScript.

Run locally from repository root:
    uvicorn modules.foundups.esingularity.http_api:app --port 8112

WSP: 3, 15, 22, 50, 84, 95, 97, 109.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException

from .src.yumori_financial_catalog import build_public_catalog_snapshot
from .src.yumori_financial_service import calculate_scenario, scenario_input_contract
from .src.yumori_financial_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    build_finance_snapshot,
)

app = FastAPI(
    title="eSingularity / YUMORI Finance API",
    description=(
        "Read-only model projections and non-persistent scenario calculations "
        "from repository-owned Python equations."
    ),
    version="0.1.0",
)


@app.get("/esingularity/finance/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "foundup_id": "esingularity_001",
        "snapshot_schema": SNAPSHOT_SCHEMA_VERSION,
        "calculation_authority": (
            "modules/foundups/esingularity/src/yumori_financial_model.py"
        ),
        "persistent_mutation": False,
    }


@app.get("/esingularity/finance/catalog")
def catalog() -> Dict[str, object]:
    """Products, YUMORI target prices, market benchmarks, and funding evidence."""
    return build_public_catalog_snapshot()


@app.get("/esingularity/finance/snapshot")
def snapshot() -> Dict[str, object]:
    """Return the current default repo-model projection.

    Feasibility funding intentionally remains NOT_RUN unless explicit project
    funding/CFADS inputs are supplied through a governed internal workflow.
    """
    return build_finance_snapshot()


@app.get("/esingularity/finance/scenario-contract")
def scenario_contract() -> Dict[str, object]:
    """Expose the bounded set of dynamic fields accepted by POST /scenario."""
    return scenario_input_contract()


@app.post("/esingularity/finance/scenario")
def scenario(
    overrides: Dict[str, object] = Body(default_factory=dict),
) -> Dict[str, object]:
    """Calculate a non-persistent model-only scenario from whitelisted inputs."""
    try:
        return calculate_scenario(overrides)
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
