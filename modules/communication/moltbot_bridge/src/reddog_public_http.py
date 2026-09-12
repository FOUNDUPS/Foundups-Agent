"""Opt-in public-only router; never dispatches to the private OpenClaw webhook.

The existing host must install PublicSurfaceBinding in app.state.reddog_public.
Without an independently reviewed public responder and lease-backed accounting,
all routes fail closed. No environment flag or client answer enables the host.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import time
from typing import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .reddog_public_policy import PublicAdmissionError, checked_surface, checked_text
from .reddog_public_session_gate import PublicSessionGate, PublicTurn


router = APIRouter(prefix="/api/reddog/public")
MAX_BODY_BYTES = 12288


@dataclass
class PublicSurfaceBinding:
    gate: PublicSessionGate
    respond: Callable[[PublicTurn], Awaitable[str]]
    subject_key: bytes = field(repr=False)
    clock: Callable[[], int] = field(default=lambda: int(time.time()), repr=False)
    tasks: set = field(default_factory=set, init=False, repr=False)

    def __post_init__(self):
        if (type(self.gate) is not PublicSessionGate or self.gate.host_owner is None
                or not callable(self.respond)
                or type(self.subject_key) is not bytes or len(self.subject_key) < 32
                or not callable(self.clock)):
            raise PublicAdmissionError("public_configuration_invalid", 503)


def _binding(request: Request) -> PublicSurfaceBinding:
    binding = getattr(request.app.state, "reddog_public", None)
    if type(binding) is not PublicSurfaceBinding:
        raise PublicAdmissionError("public_surface_unavailable", 503)
    return binding


def _peer(binding: PublicSurfaceBinding, request: Request) -> str:
    # Forwarded headers are untrusted. A separately verified ingress adapter is
    # required behind a proxy; no client-supplied principal or visitor ID is used.
    if request.client is None or not request.client.host:
        raise PublicAdmissionError("public_peer_unavailable", 503)
    return hmac.new(binding.subject_key, request.client.host.encode(), hashlib.sha256).hexdigest()


def _token(request: Request) -> str:
    value = request.headers.get("authorization", "")
    if not value.startswith("Bearer "):
        raise PublicAdmissionError("public_session_denied", 403)
    return value[7:]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


async def _body(request: Request) -> dict:
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise PublicAdmissionError("public_content_type_invalid", 415)
    async def read():
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > MAX_BODY_BYTES:
                raise PublicAdmissionError("public_body_too_large", 413)
            data.extend(chunk)
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    try:
        return await asyncio.wait_for(read(), timeout=2)
    except PublicAdmissionError:
        raise
    except asyncio.TimeoutError as exc:
        raise PublicAdmissionError("public_body_timeout", 408) from exc
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PublicAdmissionError("public_json_invalid") from exc


def _response(body: dict, status: int, origin: str = "") -> JSONResponse:
    headers = {"Cache-Control": "no-store", "Vary": "Origin"}
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    if status == 429:
        headers["Retry-After"] = "60"
    return JSONResponse(body, status_code=status, headers=headers)


def _completed(binding: PublicSurfaceBinding, token: str, turn: PublicTurn, task):
    binding.tasks.discard(task)
    try:
        if not task.cancelled():
            task.exception()  # Consume exceptions without logging conversation data.
        binding.gate.finish_turn(token=token, reservation_id=turn.reservation_id, now=binding.clock())
    except Exception:
        pass  # Accounting failure retains the persistent busy slot: fail closed.


async def _reply(binding: PublicSurfaceBinding, turn: PublicTurn, token: str) -> dict:
    async def invoke():
        return await binding.respond(turn)
    remaining = turn.deadline_epoch - binding.clock()
    if remaining <= 0:
        binding.gate.finish_turn(token=token, reservation_id=turn.reservation_id, now=binding.clock())
        raise PublicAdmissionError("public_reply_timeout", 504)
    task = asyncio.create_task(invoke())
    binding.tasks.add(task)
    task.add_done_callback(lambda done: _completed(binding, token, turn, done))
    try:
        done, _ = await asyncio.wait({task}, timeout=min(remaining, binding.gate.policy.request_seconds))
        if not done:
            task.cancel()
            raise PublicAdmissionError("public_reply_timeout", 504)
        if task.cancelled():
            raise PublicAdmissionError("public_reply_failed", 502)
        try:
            text = checked_text(task.result(), binding.gate.policy.reply_chars)
        except Exception as exc:
            raise PublicAdmissionError("public_reply_failed", 502) from exc
        if not binding.gate.delivery_allowed(token=token, revision=turn.revision, now=binding.clock()):
            raise PublicAdmissionError("public_delivery_invalidated", 410)
        return {"reply": text, "revision": turn.revision, "nonce": turn.next_nonce,
                "remaining_turns": turn.remaining_turns, "disclosure": "public",
                "effect_ceiling": "NONE"}
    except asyncio.CancelledError:
        task.cancel()
        raise


@router.options("/{surface}/{operation}")
async def preflight(surface: str, operation: str, request: Request):
    origin = request.headers.get("origin", "")
    try:
        checked_surface(surface, origin)
        if operation not in {"encounter", "lick", "challenge", "turn", "status", "withdraw"}:
            raise PublicAdmissionError("public_operation_invalid", 404)
    except PublicAdmissionError as exc:
        return _response({"error": exc.code}, exc.status)
    result = _response({}, 200, origin)
    result.headers["Access-Control-Allow-Methods"] = "POST"
    result.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return result


async def _non_turn(binding: PublicSurfaceBinding, common: dict,
                    operation: str, request: Request) -> dict:
    if operation == "encounter":
        body = await _body(request)
        return binding.gate.open_encounter(**common, body=body, now=binding.clock())
    if operation == "lick":
        body = await _body(request)
        return binding.gate.open_lick_encounter(**common, body=body, now=binding.clock())
    if operation == "challenge":
        body = await _body(request)
        return binding.gate.complete_lick_challenge(
            **common, token=_token(request), body=body, now=binding.clock())
    if operation == "status":
        token = _token(request)
        body = await _body(request)
        if type(body) is not dict or body:
            raise PublicAdmissionError("public_status_shape_invalid")
        return binding.gate.session_status(**common, token=token, now=binding.clock())
    if operation == "withdraw":
        return binding.gate.withdraw(**common, token=_token(request), now=binding.clock())
    raise PublicAdmissionError("public_operation_invalid", 404)


@router.post("/{surface}/{operation}")
async def public_request(surface: str, operation: str, request: Request):
    origin, safe_origin, turn = request.headers.get("origin", ""), "", None
    try:
        checked_surface(surface, origin)
        safe_origin = origin
        binding = _binding(request)
        common = dict(surface=surface, origin=origin, subject=_peer(binding, request))
        if operation == "turn":
            token = _token(request)
            body = await _body(request)
            turn = binding.gate.reserve_turn(**common, token=token, body=body, now=binding.clock())
            result = await _reply(binding, turn, token)
        else:
            result = await _non_turn(binding, common, operation, request)
        return _response(result, 200, safe_origin)
    except PublicAdmissionError as exc:
        return _error(exc.code, exc.status, safe_origin, turn)
    except Exception:
        return _error("public_service_unavailable", 503, safe_origin, turn)


def _error(code: str, status: int, origin: str, turn: PublicTurn | None):
    body = {"error": code}
    if turn is not None:
        body["resume"] = {"revision": turn.revision, "nonce": turn.next_nonce,
                          "remaining_turns": turn.remaining_turns}
    return _response(body, status, origin)