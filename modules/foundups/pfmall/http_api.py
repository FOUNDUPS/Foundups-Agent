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
    GET /pfmall/tile-graph?scope=public_mall|012_architect  (admitted member/architect gated; default 503)
    GET /pfmall/source-files?scope=public_mall|012_architect  (admitted member/architect gated; default 503)
    GET /pfmall/source-content?path=<path>&scope=public_mall|012_architect  (admitted member/architect gated; default 503)
    POST /pfmall/tile-graph/patches  (default503; explicit server policy + atomic SQLite WAL)
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
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import logging
import re
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import ClientDisconnect

from modules.foundups.pfmall.api import (
    get_default_shell,
    get_foundup,
    list_foundups,
    resolve_foundup_route,
)
from modules.foundups.pfmall.fractal_tile_graph import (
    PRIVATE_METADATA_ONLY_PATHS,
    _FORBIDDEN_LEAK_RE,
    _PUBLIC_FORBIDDEN_SUBSTRINGS,
    build_repo_fractal_tile_graph,
    project_public_tile_graph,
    scan_wsp71_leaks,
)
from modules.foundups.pfmall.listing_discovery import (
    GOTJUNK_ID,
    ListingProviderUnavailable,
    search_gotjunk_public_listings,
)
from modules.foundups.pfmall.tile_graph_store import (
    TileGraphAuthPolicy,
    TileGraphStore,
    validate_patch_structure,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_bounded_child_process import (
    CHILD_STDOUT_MAX_BYTES,
    bounded_child_runner,
)

logger = logging.getLogger("pfmall_http")

app = FastAPI(
    title="p.fMALL Catalog API",
    description="Public catalog reads and explicitly configured authenticated draft proposals.",
    version="0.1.0",
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Static files and shell UI
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/pfmall/static", StaticFiles(directory=str(_STATIC_DIR)), name="pfmall_static")
app.mount("/pfmall/ui", StaticFiles(directory=str(_STATIC_DIR), html=True), name="pfmall_ui")

_PROPOSAL_READ_SECONDS = 5
_PROPOSAL_MAX_BYTES = 16 * 1024
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PUBLIC_ROOT = (_REPO_ROOT / "public").resolve()
_MODULE_PROJECTIONS_DIR = Path(__file__).resolve().parent / "projections"
_DEFAULT_PUBLIC_GRAPH_PATH = _MODULE_PROJECTIONS_DIR / "fractal_tile_graph.public.json"
_DEFAULT_PUBLIC_SOURCE_FILES_PATH = _MODULE_PROJECTIONS_DIR / "fractal_source_files.public.json"
_CACHED_PUBLIC_TILE_GRAPH: Optional[Tuple[bytes, str]] = None
_ASSET_BYTE_CACHE: Dict[Tuple[Path, str], Tuple[Tuple[int, int], bytes, str]] = {}
_ASSET_CACHE_LOCK = threading.Lock()


def _wire_headers(request: Request, *, allow_if_match: bool = False) -> dict | None:
    names = ["authorization", "origin", "x-forwarded-proto", "content-type", "content-encoding", "content-length"]
    if allow_if_match:
        names.append("if-match")
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


def _proposal_wire_headers(request: Request) -> dict | None:
    return _wire_headers(request, allow_if_match=False)


def _etag_matches(header_value: Optional[str], current_etag: str) -> bool:
    if not header_value:
        return False
    for raw_part in header_value.split(","):
        token = raw_part.strip()
        if token == "*":
            return True
        if token.startswith("W/"):
            token = token[2:].strip()
        if len(token) >= 2 and token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        if token == current_etag:
            return True
    return False


def _unique_json_pairs(pairs: list) -> dict:
    obj: Dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate_json_key")
        obj[key] = value
    return obj


_MEMBER_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization, Origin",
}


def _is_inside_public_root(path: Path) -> bool:
    resolved = Path(path).resolve()
    return resolved == _PUBLIC_ROOT or _PUBLIC_ROOT in resolved.parents


def _load_member_json_bytes(
    path: Path,
    *,
    etag_field: Optional[str] = None,
) -> Tuple[bytes, str]:
    resolved = Path(path).resolve()
    if _is_inside_public_root(resolved):
        raise ValueError("member_asset_inside_public_root")
    stat = resolved.stat()
    stat_key = (stat.st_mtime_ns, stat.st_size)
    cache_key = (resolved, etag_field or "")
    with _ASSET_CACHE_LOCK:
        cached = _ASSET_BYTE_CACHE.get(cache_key)
        if cached is not None and cached[0] == stat_key:
            return cached[1], cached[2]
    raw_bytes = resolved.read_bytes()
    etag = ""
    if etag_field:
        doc = json.loads(raw_bytes.decode("utf-8"))
        val = doc.get(etag_field)
        if isinstance(val, str) and val:
            etag = val
    if not etag:
        etag = hashlib.sha256(raw_bytes).hexdigest()
    with _ASSET_CACHE_LOCK:
        _ASSET_BYTE_CACHE[cache_key] = (stat_key, raw_bytes, etag)
    return raw_bytes, etag


def _get_static_public_tile_graph_bytes() -> Tuple[bytes, str]:
    global _CACHED_PUBLIC_TILE_GRAPH
    if _DEFAULT_PUBLIC_GRAPH_PATH.is_file():
        return _load_member_json_bytes(_DEFAULT_PUBLIC_GRAPH_PATH, etag_field="public_graph_etag")
    if _CACHED_PUBLIC_TILE_GRAPH is None:
        graph = project_public_tile_graph(build_repo_fractal_tile_graph(_REPO_ROOT))
        raw_bytes = json.dumps(graph, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        _CACHED_PUBLIC_TILE_GRAPH = (raw_bytes, graph["public_graph_etag"])
    return _CACHED_PUBLIC_TILE_GRAPH


def _valid_proxy_host_entry(value: object) -> bool:
    return (
        type(value) is str
        and value.isascii()
        and 1 <= len(value) <= 255
        and not any(c.isspace() for c in value)
        and "," not in value
        and "/" not in value
    )


@dataclass(frozen=True, slots=True)
class TrustedProxyPolicy:
    """Explicit opt-in configuration for trusting reverse-proxy forwarding headers."""

    trust_proxy_headers: bool = False
    trusted_proxy_hosts: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.trust_proxy_headers) is not bool:
            raise ValueError("invalid_trusted_proxy_policy")
        if (
            type(self.trusted_proxy_hosts) is not tuple
            or not all(_valid_proxy_host_entry(host) for host in self.trusted_proxy_hosts)
            or len(set(self.trusted_proxy_hosts)) != len(self.trusted_proxy_hosts)
        ):
            raise ValueError("invalid_trusted_proxy_policy")


def _resolve_trusted_proxy_hosts(request: Request) -> Optional[Tuple[str, ...]]:
    """Return allowed trusted proxy peer hosts only when explicitly enabled; otherwise None."""
    trust_attr = getattr(request.app.state, "trust_proxy_headers", None)
    if trust_attr is False:
        return None

    proxy_policy = getattr(request.app.state, "trusted_proxy_policy", None)
    if proxy_policy is not None:
        if type(proxy_policy) is not TrustedProxyPolicy or not proxy_policy.trust_proxy_headers:
            return None
        return proxy_policy.trusted_proxy_hosts or None

    if type(trust_attr) is not bool or not trust_attr:
        return None

    raw_hosts = getattr(request.app.state, "trusted_proxy_hosts", None)
    if raw_hosts == "*":
        return ("*",)
    if type(raw_hosts) not in (tuple, list, set, frozenset):
        return None
    hosts = tuple(raw_hosts)
    if not hosts or not all(_valid_proxy_host_entry(host) for host in hosts):
        return None
    return hosts


def _is_trusted_proxy_peer(request: Request, trusted_hosts: Tuple[str, ...]) -> bool:
    if "*" in trusted_hosts:
        return True
    client = getattr(request, "client", None)
    client_host = getattr(client, "host", None)
    if type(client_host) is not str or not client_host:
        return False
    if client_host in trusted_hosts:
        return True
    try:
        peer_ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    for entry in trusted_hosts:
        try:
            if ipaddress.ip_address(entry) == peer_ip:
                return True
        except ValueError:
            continue
    return False


def _effective_request_scheme(request: Request) -> Optional[str]:
    """Reconstruct effective scheme, honoring X-Forwarded-Proto only from an explicitly trusted proxy."""
    base_scheme = (request.url.scheme or "").strip().lower()
    trusted_hosts = _resolve_trusted_proxy_hosts(request)
    if trusted_hosts is None or not _is_trusted_proxy_peer(request, trusted_hosts):
        return base_scheme or None

    raw_forwarded_proto = request.headers.get("x-forwarded-proto")
    if raw_forwarded_proto is None:
        return base_scheme or None

    first_hop = raw_forwarded_proto.split(",", 1)[0].strip().lower()
    if first_hop not in ("http", "https"):
        return None
    return first_hop


async def _verify_member_get_session(request: Request, clerk_policy: Any):
    from modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake import (
        LaunchRequestIntakeContext,
        _verify_session,
    )

    if any(len(request.headers.getlist(name)) > 1 for name in ("authorization", "origin", "x-forwarded-proto", "host")):
        return None
    verify_headers = dict(request.headers)
    if "origin" not in {k.lower() for k in verify_headers}:
        sec_fetch_values = request.headers.getlist("sec-fetch-site")
        referer_values = request.headers.getlist("referer")
        sec_fetch_site = sec_fetch_values[0].strip().lower() if len(sec_fetch_values) == 1 else ""
        referer = referer_values[0] if len(referer_values) == 1 else None
        effective_scheme = _effective_request_scheme(request)
        if sec_fetch_site == "same-origin" and referer and effective_scheme and request.url.netloc:
            ref = urlsplit(referer)
            if ref.scheme and ref.netloc:
                inferred_origin = f"{ref.scheme.lower()}://{ref.netloc}"
                request_origin = f"{effective_scheme}://{request.url.netloc}"
                if inferred_origin == request_origin and inferred_origin in clerk_policy.authorized_parties:
                    verify_headers["origin"] = inferred_origin
                else:
                    return LaunchRequestIntakeContext()
        else:
            return LaunchRequestIntakeContext()
    return await run_in_threadpool(_verify_session, verify_headers, clerk_policy)


def _is_admitted_member(
    request: Request,
    actor_id: str,
    auth_policy: TileGraphAuthPolicy,
) -> bool:
    if auth_policy.is_admitted_member(actor_id):
        return True
    verifier = getattr(request.app.state, "member_admission_verifier", None)
    if callable(verifier):
        try:
            return bool(verifier(actor_id, request))
        except Exception:
            return False
    return False


async def _authorize_member_scope_get(
    request: Request,
    scope: str,
    *,
    unavailable_detail: str,
) -> Optional[Response]:
    """Enforce fail-closed auth and admission policy on protected member reads."""
    if scope not in ("public_mall", "012_architect"):
        return JSONResponse({"detail": "invalid_scope"}, status_code=400, headers=_MEMBER_PRIVATE_HEADERS)

    clerk_policy = getattr(request.app.state, "clerk_intake_policy", None)
    auth_policy = getattr(request.app.state, "tile_graph_policy", None)
    if clerk_policy is None or auth_policy is None:
        return JSONResponse({"detail": unavailable_detail}, status_code=503, headers=_MEMBER_PRIVATE_HEADERS)

    from modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake import ClerkIntakePolicy

    if type(clerk_policy) is not ClerkIntakePolicy or type(auth_policy) is not TileGraphAuthPolicy:
        return JSONResponse({"detail": unavailable_detail}, status_code=503, headers=_MEMBER_PRIVATE_HEADERS)

    ctx = await _verify_member_get_session(request, clerk_policy)
    if ctx is None:
        return JSONResponse({"detail": "invalid_request"}, status_code=400, headers=_MEMBER_PRIVATE_HEADERS)
    if not ctx.authenticated:
        return JSONResponse({"detail": "not_authorized"}, status_code=401, headers=_MEMBER_PRIVATE_HEADERS)

    if scope == "012_architect":
        if not auth_policy.is_architect(ctx.requester_handle):
            return JSONResponse({"detail": "forbidden"}, status_code=403, headers=_MEMBER_PRIVATE_HEADERS)
    else:
        admitted = await run_in_threadpool(_is_admitted_member, request, ctx.requester_handle, auth_policy)
        if not admitted:
            return JSONResponse(
                {"detail": "member_admission_required"},
                status_code=403,
                headers=_MEMBER_PRIVATE_HEADERS,
            )
    return None


def _respond_etag_json_bytes(
    request: Request,
    raw_bytes: bytes,
    etag: str,
) -> Response:
    headers = {"ETag": f'"{etag}"', **_MEMBER_PRIVATE_HEADERS}
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    return Response(content=raw_bytes, media_type="application/json", status_code=200, headers=headers)


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
    policy = getattr(request.app.state, "clerk_intake_policy", None)
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


@app.get("/pfmall/tile-graph")
async def get_tile_graph(
    request: Request,
    scope: str = Query("public_mall"),
) -> Response:
    """Serve the dual-scope Fractal Tile Graph strictly behind server-side admission."""
    unavailable = "tile_graph_architect_unavailable" if scope == "012_architect" else "member_tile_graph_unavailable"
    gate = await _authorize_member_scope_get(
        request,
        scope,
        unavailable_detail=unavailable,
    )
    if gate is not None:
        return gate

    store = getattr(request.app.state, "tile_graph_store", None)
    if scope == "012_architect":
        if type(store) is not TileGraphStore:
            return JSONResponse(
                {"detail": "tile_graph_architect_unavailable"},
                status_code=503,
                headers=_MEMBER_PRIVATE_HEADERS,
            )
        graph = await run_in_threadpool(store.get_architect_graph)
        etag = graph["graph_etag"]
        if _etag_matches(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, headers={"ETag": f'"{etag}"', **_MEMBER_PRIVATE_HEADERS})
        return JSONResponse(graph, status_code=200, headers={"ETag": f'"{etag}"', **_MEMBER_PRIVATE_HEADERS})

    if type(store) is TileGraphStore:
        graph = await run_in_threadpool(store.get_public_graph)
        etag = graph["public_graph_etag"]
        if _etag_matches(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, headers={"ETag": f'"{etag}"', **_MEMBER_PRIVATE_HEADERS})
        return JSONResponse(graph, status_code=200, headers={"ETag": f'"{etag}"', **_MEMBER_PRIVATE_HEADERS})

    try:
        raw_bytes, etag = await run_in_threadpool(_get_static_public_tile_graph_bytes)
    except Exception:
        return JSONResponse(
            {"detail": "member_tile_graph_unavailable"},
            status_code=503,
            headers=_MEMBER_PRIVATE_HEADERS,
        )
    return _respond_etag_json_bytes(request, raw_bytes, etag)


@app.get("/pfmall/source-files")
async def get_source_files(
    request: Request,
    scope: str = Query("public_mall"),
) -> Response:
    """Serve the revision-pinned source file index strictly behind server-side admission."""
    unavailable = "architect_source_files_unavailable" if scope == "012_architect" else "member_source_files_unavailable"
    gate = await _authorize_member_scope_get(request, scope, unavailable_detail=unavailable)
    if gate is not None:
        return gate

    if scope == "012_architect":
        asset_path = getattr(request.app.state, "architect_source_files_path", None)
        if not isinstance(asset_path, Path) or _is_inside_public_root(asset_path) or not asset_path.is_file():
            return JSONResponse(
                {"detail": "architect_source_files_unavailable"},
                status_code=503,
                headers=_MEMBER_PRIVATE_HEADERS,
            )
    else:
        custom_path = getattr(request.app.state, "member_source_files_path", None)
        asset_path = custom_path if custom_path is not None else _DEFAULT_PUBLIC_SOURCE_FILES_PATH
        if not isinstance(asset_path, Path) or _is_inside_public_root(asset_path) or not asset_path.is_file():
            return JSONResponse(
                {"detail": "member_source_files_unavailable"},
                status_code=503,
                headers=_MEMBER_PRIVATE_HEADERS,
            )

    try:
        raw_bytes, etag = await run_in_threadpool(_load_member_json_bytes, asset_path)
    except Exception:
        return JSONResponse({"detail": unavailable}, status_code=503, headers=_MEMBER_PRIVATE_HEADERS)
    return _respond_etag_json_bytes(request, raw_bytes, etag)


_SOURCE_CONTENT_MAX_LINES = 400
_SOURCE_CONTENT_MAX_BYTES = CHILD_STDOUT_MAX_BYTES
_SOURCE_BLOB_MAX_BYTES = CHILD_STDOUT_MAX_BYTES
_SOURCE_READ_TIMEOUT_SECONDS = 5.0
_GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_REGULAR_BLOB_MODES = frozenset({"100644", "100755"})
_BINARY_SOURCE_EXTENSIONS = frozenset({
    ".exe", ".dll", ".so", ".dylib", ".bin", ".pyd", ".pyc", ".pyo",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff", ".svgz",
    ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".mov", ".avi", ".flac",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".whl", ".pdf",
    ".sqlite", ".sqlite3", ".db", ".woff", ".woff2", ".ttf", ".otf", ".eot",
})


def _normalize_repo_source_path(raw_path: str, scope: str) -> Tuple[Optional[str], Optional[str]]:
    """Validate and normalize a repository-relative POSIX path fail-closed."""
    if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
        return None, "invalid_source_path"
    if "\\" in raw_path or raw_path.startswith("/"):
        return None, "forbidden_source_path"
    if _FORBIDDEN_LEAK_RE.search(raw_path):
        return None, "forbidden_source_path"
    parts = raw_path.split("/")
    if any(seg in ("", ".", "..") for seg in parts):
        return None, "forbidden_source_path"
    norm = "/".join(parts)
    low = norm.lower()
    if norm in PRIVATE_METADATA_ONLY_PATHS or "roi_to_roc_paradigm_shift.md" in low:
        return None, "forbidden_source_path"
    if scope == "public_mall":
        if any(sub.lower() in low for sub in _PUBLIC_FORBIDDEN_SUBSTRINGS):
            return None, "forbidden_source_path"
    return norm, None


def _collect_admitted_source_paths(
    request: Request,
    scope: str,
) -> Tuple[Optional[Set[str]], Dict[str, str], Optional[str]]:
    """Collect admitted repo paths and pinned revisions strictly from the active *scope*."""
    admitted: Set[str] = set()
    path_revisions: Dict[str, str] = {}
    default_rev: Optional[str] = None
    have_authority = False

    if scope == "012_architect":
        sf_path = getattr(request.app.state, "architect_source_files_path", None)
    else:
        custom_sf = getattr(request.app.state, "member_source_files_path", None)
        sf_path = custom_sf if custom_sf is not None else _DEFAULT_PUBLIC_SOURCE_FILES_PATH

    if isinstance(sf_path, Path) and not _is_inside_public_root(sf_path) and sf_path.is_file():
        have_authority = True
        raw_bytes, _ = _load_member_json_bytes(sf_path)
        sf_doc = json.loads(raw_bytes.decode("utf-8"))
        sf_rev = str(sf_doc.get("source_revision") or "").strip()
        if _GIT_SHA_RE.fullmatch(sf_rev):
            default_rev = sf_rev
        for tile_entry in (sf_doc.get("tiles") or {}).values():
            if not isinstance(tile_entry, dict):
                continue
            prefix = str(tile_entry.get("path_prefix") or "")
            for rel in tile_entry.get("files") or []:
                full_p = (prefix + str(rel)).lstrip("/")
                if full_p:
                    admitted.add(full_p)

    graph_doc: Optional[Dict[str, Any]] = None
    store = getattr(request.app.state, "tile_graph_store", None)
    if type(store) is TileGraphStore:
        have_authority = True
        graph_doc = store.get_architect_graph() if scope == "012_architect" else store.get_public_graph()
    elif scope == "public_mall" and _DEFAULT_PUBLIC_GRAPH_PATH.is_file():
        have_authority = True
        raw_bytes, _ = _load_member_json_bytes(_DEFAULT_PUBLIC_GRAPH_PATH, etag_field="public_graph_etag")
        graph_doc = json.loads(raw_bytes.decode("utf-8"))

    if isinstance(graph_doc, dict):
        if default_rev is None:
            census_rev = str((graph_doc.get("source_revisions") or {}).get("census_source_revision") or "").strip()
            git_rev = str(graph_doc.get("git_revision") or "").strip()
            if _GIT_SHA_RE.fullmatch(census_rev):
                default_rev = census_rev
            elif _GIT_SHA_RE.fullmatch(git_rev):
                default_rev = git_rev
        for tile in (graph_doc.get("tiles") or {}).values():
            if not isinstance(tile, dict):
                continue
            if scope == "public_mall":
                if tile.get("visibility_scope") != "public":
                    continue
                if (tile.get("lifecycle") or {}).get("state") == "RED":
                    continue
            meta = tile.get("metadata") or {}
            if meta.get("metadata_only") is True:
                continue
            raw_rp = (tile.get("action_target") or {}).get("repo_path")
            if not isinstance(raw_rp, str) or not raw_rp:
                continue
            clean_rp = raw_rp.partition("#")[0].strip().rstrip("/")
            if not clean_rp:
                continue
            admitted.add(clean_rp)
            si_rev = str((meta.get("source_inspection") or {}).get("source_revision") or "").strip()
            if _GIT_SHA_RE.fullmatch(si_rev) and clean_rp not in path_revisions:
                path_revisions[clean_rp] = si_rev

    if not have_authority:
        return None, {}, None
    return admitted, path_revisions, default_rev


def _read_git_pinned_source_lines(
    repo_root: Path,
    revision: str,
    rel_path: str,
    start_line: Optional[int],
    end_line: Optional[int],
) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[int, str]]]:
    """Admit regular text/blob + <=16KiB size via bounded_child_runner, then slice lines."""
    if not _GIT_SHA_RE.fullmatch(revision or ""):
        return None, (503, "source_revision_unavailable")

    ext = Path(rel_path).suffix.lower()
    if ext in _BINARY_SOURCE_EXTENSIONS:
        return None, (403, "binary_source_forbidden")

    try:
        ls_res = bounded_child_runner(
            ["git", "-C", str(repo_root), "ls-tree", revision, "--", rel_path],
            timeout=_SOURCE_READ_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return None, (504, "source_read_timeout")
    except OSError:
        return None, (503, "source_reader_unavailable")
    if ls_res.returncode != 0 or ls_res.output_oversized or ls_res.output_read_failed:
        return None, (404, "source_blob_not_found")
    ls_line = ls_res.stdout.decode("utf-8", errors="replace").strip().splitlines()
    if len(ls_line) != 1:
        return None, (404, "source_blob_not_found")
    meta_part, _, entry_path = ls_line[0].partition("\t")
    meta_fields = meta_part.split()
    if len(meta_fields) != 3 or entry_path != rel_path:
        return None, (404, "source_blob_not_found")
    obj_mode, obj_type, _obj_sha = meta_fields
    if obj_type != "blob" or obj_mode not in _REGULAR_BLOB_MODES:
        return None, (403, "non_regular_blob_forbidden")

    try:
        size_res = bounded_child_runner(
            ["git", "-C", str(repo_root), "cat-file", "-s", f"{revision}:{rel_path}"],
            timeout=_SOURCE_READ_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return None, (504, "source_read_timeout")
    except OSError:
        return None, (503, "source_reader_unavailable")
    if size_res.returncode != 0 or size_res.output_oversized or size_res.output_read_failed:
        return None, (404, "source_blob_not_found")
    try:
        blob_size = int(size_res.stdout.decode("ascii", errors="strict").strip())
    except ValueError:
        return None, (404, "source_blob_not_found")
    if blob_size < 0 or blob_size > _SOURCE_BLOB_MAX_BYTES:
        return None, (413, "source_blob_too_large")

    try:
        show_res = bounded_child_runner(
            ["git", "-C", str(repo_root), "show", f"{revision}:{rel_path}"],
            timeout=_SOURCE_READ_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return None, (504, "source_read_timeout")
    except OSError:
        return None, (503, "source_reader_unavailable")
    if show_res.output_oversized:
        return None, (413, "source_blob_too_large")
    if show_res.output_read_failed or show_res.returncode != 0:
        return None, (404, "source_blob_not_found")

    raw_bytes = show_res.stdout

    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw_bytes.decode("utf-16", errors="replace")
    else:
        if b"\x00" in raw_bytes[:8192] or b"\x00" in raw_bytes:
            return None, (403, "binary_source_forbidden")
        try:
            text = raw_bytes.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            return None, (403, "binary_source_forbidden")

    lines = text.splitlines()
    total_lines = len(lines)
    eff_start = 1 if start_line is None else start_line
    if eff_start < 1:
        return None, (400, "invalid_line_range")
    if total_lines == 0:
        if end_line is not None and end_line < eff_start:
            return None, (400, "invalid_line_range")
        return {
            "ok": True,
            "path": rel_path,
            "revision": revision,
            "start_line": 1,
            "end_line": 0,
            "total_lines": 0,
            "truncated": False,
            "content": "",
        }, None

    if eff_start > total_lines:
        return None, (400, "line_range_out_of_bounds")
    req_end = min(total_lines, eff_start + _SOURCE_CONTENT_MAX_LINES - 1) if end_line is None else end_line
    if req_end < eff_start:
        return None, (400, "invalid_line_range")

    eff_end = min(req_end, total_lines, eff_start + _SOURCE_CONTENT_MAX_LINES - 1)
    truncated = (req_end > eff_end) or (end_line is None and total_lines > eff_end)
    sliced = lines[eff_start - 1 : eff_end]
    content = "\n".join(sliced)

    encoded = content.encode("utf-8")
    if len(encoded) > _SOURCE_CONTENT_MAX_BYTES:
        truncated = True
        while len(sliced) > 1 and len("\n".join(sliced).encode("utf-8")) > _SOURCE_CONTENT_MAX_BYTES:
            sliced.pop()
            eff_end -= 1
        content = "\n".join(sliced)
        encoded = content.encode("utf-8")
        if len(encoded) > _SOURCE_CONTENT_MAX_BYTES:
            content = encoded[:_SOURCE_CONTENT_MAX_BYTES].decode("utf-8", errors="ignore")

    if scan_wsp71_leaks(content):
        return None, (403, "source_content_redacted_wsp71")

    return {
        "ok": True,
        "path": rel_path,
        "revision": revision,
        "start_line": eff_start,
        "end_line": eff_end,
        "total_lines": total_lines,
        "truncated": truncated,
        "content": content,
    }, None


@app.get("/pfmall/source-content")
async def get_source_content(
    request: Request,
    path: str = Query(...),
    start_line: Optional[int] = Query(None),
    end_line: Optional[int] = Query(None),
    scope: str = Query("public_mall"),
) -> Response:
    """Serve bounded, revision-pinned repository source/chapter lines behind admission."""
    unavailable = "architect_source_content_unavailable" if scope == "012_architect" else "member_source_content_unavailable"
    gate = await _authorize_member_scope_get(request, scope, unavailable_detail=unavailable)
    if gate is not None:
        return gate

    norm_path, path_err = _normalize_repo_source_path(path, scope)
    if path_err is not None or norm_path is None:
        return JSONResponse({"detail": path_err or "forbidden_source_path"}, status_code=403, headers=_MEMBER_PRIVATE_HEADERS)

    if start_line is not None and start_line < 1:
        return JSONResponse({"detail": "invalid_line_range"}, status_code=400, headers=_MEMBER_PRIVATE_HEADERS)
    if end_line is not None and end_line < 1:
        return JSONResponse({"detail": "invalid_line_range"}, status_code=400, headers=_MEMBER_PRIVATE_HEADERS)
    if start_line is not None and end_line is not None and end_line < start_line:
        return JSONResponse({"detail": "invalid_line_range"}, status_code=400, headers=_MEMBER_PRIVATE_HEADERS)

    admitted_paths, path_revisions, default_rev = await run_in_threadpool(
        _collect_admitted_source_paths, request, scope
    )
    if admitted_paths is None:
        return JSONResponse({"detail": unavailable}, status_code=503, headers=_MEMBER_PRIVATE_HEADERS)
    if norm_path not in admitted_paths:
        return JSONResponse({"detail": "source_path_not_admitted"}, status_code=404, headers=_MEMBER_PRIVATE_HEADERS)

    revision = path_revisions.get(norm_path) or default_rev or ""
    repo_root = getattr(request.app.state, "source_content_repo_root", None) or _REPO_ROOT
    payload, err = await run_in_threadpool(
        _read_git_pinned_source_lines,
        Path(repo_root),
        revision,
        norm_path,
        start_line,
        end_line,
    )
    if err is not None:
        return JSONResponse({"detail": err[1]}, status_code=err[0], headers=_MEMBER_PRIVATE_HEADERS)
    return JSONResponse(payload, status_code=200, headers=_MEMBER_PRIVATE_HEADERS)


@app.post("/pfmall/tile-graph/patches")
async def patch_tile_graph(request: Request) -> JSONResponse:
    """Apply an authenticated, optimistic-concurrency atomic patch to the Tile Graph."""
    response_headers = {"Cache-Control": "no-store"}
    clerk_policy = getattr(request.app.state, "clerk_intake_policy", None)
    store = getattr(request.app.state, "tile_graph_store", None)
    auth_policy = getattr(request.app.state, "tile_graph_policy", None)
    if clerk_policy is None or store is None or auth_policy is None:
        return JSONResponse({"detail": "tile_graph_patch_unavailable"}, status_code=503, headers=response_headers)

    from modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake import (
        ClerkIntakePolicy,
        _verify_session,
    )
    if (
        type(clerk_policy) is not ClerkIntakePolicy
        or type(store) is not TileGraphStore
        or type(auth_policy) is not TileGraphAuthPolicy
    ):
        return JSONResponse({"detail": "tile_graph_patch_unavailable"}, status_code=503, headers=response_headers)

    headers = _wire_headers(request, allow_if_match=True)
    if headers is None:
        return JSONResponse({"detail": "invalid_request"}, status_code=400, headers=response_headers)

    try:
        body = await asyncio.wait_for(_read_proposal_body(request), _PROPOSAL_READ_SECONDS)
    except (ValueError, TimeoutError, RuntimeError, ClientDisconnect):
        return JSONResponse({"detail": "invalid_request"}, status_code=400, headers=response_headers)

    try:
        patch_dict = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_json_pairs)
    except Exception:
        return JSONResponse({"detail": "invalid_request"}, status_code=400, headers=response_headers)

    struct_err = validate_patch_structure(patch_dict)
    if struct_err is not None:
        return JSONResponse({"detail": struct_err}, status_code=400, headers=response_headers)

    if_match = request.headers.get("if-match")
    if if_match is not None:
        raw_if = if_match.strip()
        if raw_if.startswith("W/") or "," in raw_if:
            return JSONResponse({"detail": "if_match_invalid"}, status_code=400, headers=response_headers)
        if len(raw_if) >= 2 and raw_if.startswith('"') and raw_if.endswith('"'):
            raw_if = raw_if[1:-1]
        if raw_if != patch_dict["base_graph_etag"]:
            return JSONResponse({"detail": "if_match_mismatch"}, status_code=400, headers=response_headers)

    ctx = await run_in_threadpool(_verify_session, headers, clerk_policy)
    if not ctx.authenticated:
        return JSONResponse({"detail": "not_authorized"}, status_code=401, headers=response_headers)

    result = await run_in_threadpool(
        store.apply_patch,
        patch_dict,
        actor_id=ctx.requester_handle,
        policy=auth_policy,
    )
    if result.status in ("committed", "idempotent_replay") and result.receipt is not None:
        headers_out = {
            **response_headers,
            "ETag": f'"{result.receipt["new_graph_etag"]}"',
        }
        return JSONResponse(
            {"status": result.status, "receipt": result.receipt},
            status_code=result.http_status,
            headers=headers_out,
        )

    err_body: Dict[str, Any] = {"detail": result.detail or "patch_rejected"}
    if result.current_graph_etag is not None:
        err_body["current_graph_etag"] = result.current_graph_etag
    return JSONResponse(err_body, status_code=result.http_status, headers=response_headers)


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
