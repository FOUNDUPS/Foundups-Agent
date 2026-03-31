#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
p.fMALL HTTP Read Surface — minimal read-only FastAPI endpoints + shell UI.

Thin transport layer delegating to pfmall/api.py. No business logic,
no mutation, no auth. Read-only JSON surface + static shell UI.

Run:
    uvicorn modules.foundups.pfmall.http_api:app --port 8100

JSON Endpoints:
    GET /pfmall/health
    GET /pfmall/catalog
    GET /pfmall/catalog?category=<category>
    GET /pfmall/foundups/{foundup_id}
    GET /pfmall/resolve-route?path=<path>

Shell UI:
    GET /pfmall/ui/              -> Catalog view
    GET /pfmall/ui/detail.html   -> FoundUp detail view
    GET /pfmall/ui/handoff.html  -> Route handoff view
    GET /pfmall/static/...       -> CSS/assets
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from modules.foundups.pfmall.api import (
    get_default_shell,
    get_foundup,
    list_foundups,
    resolve_foundup_route,
)

logger = logging.getLogger("pfmall_http")

app = FastAPI(
    title="p.fMALL Catalog API",
    description="Read-only p.fMALL catalog, tile lookup, and route resolution.",
    version="0.1.0",
)

# Static files and shell UI
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/pfmall/static", StaticFiles(directory=str(_STATIC_DIR)), name="pfmall_static")
app.mount("/pfmall/ui", StaticFiles(directory=str(_STATIC_DIR), html=True), name="pfmall_ui")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/pfmall/health")
def health() -> Dict[str, Any]:
    """Health check. Returns shell boot status and catalog count."""
    shell = get_default_shell()
    return {
        "status": "ok",
        "booted": shell.is_booted,
        "catalog_count": shell.catalog.count,
    }


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@app.get("/pfmall/catalog")
def catalog(category: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """List FoundUp tiles, optionally filtered by category."""
    return list_foundups(category=category)


# ---------------------------------------------------------------------------
# Single FoundUp
# ---------------------------------------------------------------------------

@app.get("/pfmall/foundups/{foundup_id}")
def foundup_detail(foundup_id: str) -> Dict[str, Any]:
    """Get a single FoundUp tile by ID."""
    result = get_foundup(foundup_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"FoundUp not found: {foundup_id}")
    return result


# ---------------------------------------------------------------------------
# Route Resolution
# ---------------------------------------------------------------------------

@app.get("/pfmall/resolve-route")
def resolve_route(path: str = Query(..., description="URL path to resolve")) -> Dict[str, Any]:
    """Resolve a URL path through the p.fMALL shell router."""
    return resolve_foundup_route(path)
