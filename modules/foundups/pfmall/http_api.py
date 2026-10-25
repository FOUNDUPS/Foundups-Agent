#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
p.fMALL HTTP read surface plus explicitly configured draft-proposal intake.

Thin transport layer delegating to pfmall/api.py. No business logic,
no catalog mutation. Reads stay public; proposals require server-selected Clerk
verification and return a draft only. No default policy or credential loading.

Run:
    uvicorn modules.foundups.pfmall.http_api:app --port 8100

JSON Endpoints:
    GET /pfmall/health
    GET /pfmall/catalog
    GET /pfmall/catalog?category=<category>
    GET /pfmall/foundups/{foundup_id}
    GET /pfmall/resolve-route?path=<path>
    POST /pfmall/proposals  (default503; explicit server policy, draft only)

Shell UI:
    GET /pfmall/ui/              -> Catalog view
    GET /pfmall/ui/detail.html   -> FoundUp detail view
    GET /pfmall/ui/handoff.html  -> Route handoff view
    GET /pfmall/static/...       -> CSS/assets

FoundUp Route Handoff:
    GET /f/{foundup_id}          -> Redirects to handoff UI
    GET /f/{foundup_id}/{path}   -> Redirects to handoff UI
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from modules.foundups.pfmall.api import (
    get_default_shell,
    get_foundup,
    list_foundups,
    resolve_foundup_route,
)

from modules.foundups.pfmall.listing_discovery import (
    GOTJUNK_ID,
    ListingProviderUnavailable,
    search_gotjunk_public_listings,
)

logger = logging.getLogger("pfmall_http")

app = FastAPI(
    title="p.fMALL Catalog API",
    description="Public catalog reads and explicitly configured authenticated draft proposals.",
    version="0.1.0",
)

# Static files and shell UI
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/pfmall/static", StaticFiles(directory=str(_STATIC_DIR)), name="pfmall_static")
app.mount("/pfmall/ui", StaticFiles(directory=str(_STATIC_DIR), html=True), name="pfmall_ui")

_PROPOSAL_READ_SECONDS = 5
_PROPOSAL_MAX_BYTES = 16 * 1024


def _proposal_wire_headers(request: Request) -> dict | None:
    names = ("authorization", "origin", "content-type", "content-encoding", "content-length")
    if any(len(request.headers.getlist(name)) > 1 for name in names):
        return None
    content_type = request.headers.get("content-type", "").lower().replace(" ", "")
    if content_type not in ("application/json", "application/json;charset=utf-8"):
        return None
    if request.headers.get("content-encoding", "identity").lower() != "identity":
        return None
    length = request.headers.get("content-length")
    if length is not None and (not length.isascii() or not length.isdecimal()
                               or len(length) > 8 or int(length) > _PROPOSAL_MAX_BYTES):
        return None
    return dict(request.headers)


async def _read_proposal_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > _PROPOSAL_MAX_BYTES:
            raise ValueError("invalid_request")
        body.extend(chunk)
    return bytes(body)


@app.post("/pfmall/proposals")
async def foundup_proposal(request: Request) -> JSONResponse:
    """Local component only: no durable admission, repository control or issuance."""
    response_headers = {"Cache-Control": "no-store"}
    policy = getattr(app.state, "clerk_intake_policy", None)
    if policy is None:
        return JSONResponse({"detail": "intake_unavailable"}, status_code=503, headers=response_headers)
    from modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake import (
        ClerkIntakePolicy, intake_clerk_request,
    )
    if type(policy) is not ClerkIntakePolicy:
        return JSONResponse({"detail": "intake_unavailable"}, status_code=503, headers=response_headers)
    headers = _proposal_wire_headers(request)
    if headers is None:
        return JSONResponse({"detail": "invalid_request"}, status_code=400, headers=response_headers)
    try:
        body = await asyncio.wait_for(_read_proposal_body(request), _PROPOSAL_READ_SECONDS)
    except (ValueError, TimeoutError, RuntimeError, ClientDisconnect):
        return JSONResponse({"detail": "invalid_request"}, status_code=400, headers=response_headers)
    result = await run_in_threadpool(intake_clerk_request, headers, body, policy=policy)
    data = ({"status": "DRAFT_ONLY", "genesis_envelope": result.envelope}
            if result.status == "created" else {"detail": result.reason})
    return JSONResponse(data, status_code=result.http_status, headers=response_headers)


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
# Public-only item discovery; no client-asserted identity or private browsing
# ---------------------------------------------------------------------------

@app.get("/pfmall/listings/search")
def public_listing_search(
    foundup_id: str = Query(GOTJUNK_ID),
    q: str = Query("", max_length=80),
    category: Optional[str] = Query(None, max_length=32),
    owner_uid: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
) -> Dict[str, Any]:
    """Search separately approved public listings using a server-owned provider.

    Existing client Firestore/IndexedDB data is not an approved index.
    Until deployment configures a trusted provider, this route returns 503.
    """
    if foundup_id != GOTJUNK_ID or owner_uid is not None:
        raise HTTPException(status_code=403, detail="Private or cross-FoundUp listing search denied")
    if get_foundup(GOTJUNK_ID) is None:
        raise HTTPException(status_code=503, detail="Listing authority unavailable")
    provider = getattr(app.state, "listing_evidence_provider", None)
    try:
        rows = search_gotjunk_public_listings(provider, query=q, category=category, limit=limit)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid search parameters") from None
    except ListingProviderUnavailable:
        raise HTTPException(status_code=503, detail="Listing provider unavailable") from None
    return {"foundup_id": GOTJUNK_ID, "results": rows}


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


# ---------------------------------------------------------------------------
# FoundUp Route Handoff (/f/{foundup_id} -> shell handoff UI)
# ---------------------------------------------------------------------------

@app.get("/f/{foundup_id:path}")
def foundup_route_handoff(foundup_id: str) -> RedirectResponse:
    """Redirect /f/{foundup_id}[/path] to the shell handoff UI.

    This is the real hosted route for FoundUp navigation. The shell
    owns this route and redirects to its handoff page, which resolves
    the route via the API and shows launch readiness posture.
    """
    # Strip any sub-path to get the bare foundup_id
    bare_id = foundup_id.split("/")[0]
    return RedirectResponse(
        url=f"/pfmall/ui/handoff.html?id={bare_id}",
        status_code=307,
    )
