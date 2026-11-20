"""Real ASGI router with synthetic responder; no live provider or network call."""
import asyncio
import ast
import json
from pathlib import Path
import sys

import httpx
import pytest
from fastapi import FastAPI

p = sys.modules["_reddog_public_boundary_tests.reddog_public_policy"]
s = sys.modules["_reddog_public_boundary_tests.reddog_public_session_gate"]
NOW = 1800000000
ORIGIN = "https://foundups.com"
BASE = "/api/reddog/public/foundups/"
HOST_OWNER = "f" * 64
ADMITTED_MODEL = "google/gemma-4-26b-a4b-it:free"
CONSENT = {"consent": True, "consent_version": p.CONSENT_VERSION, "actor_claim": "human"}


def host(api, store, respond=None, policy=None):
    _, connect = store
    gate = s.PublicSessionGate(connect, policy, host_owner=HOST_OWNER)
    gate.initialize()
    gate.register_host(now=NOW)
    seen = []
    async def reply(turn):
        seen.append(turn)
        return "Public response."
    app = FastAPI()
    app.include_router(api.router)
    binding = api.PublicSurfaceBinding(gate, respond or reply, b"z"*32, lambda: NOW)
    app.state.reddog_public = binding
    return app, binding, seen


def client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://gateway.example",
                             headers={"Origin": ORIGIN})


def payload(session, message="Hello"):
    return dict(nonce=session["nonce"], revision=session["revision"], message=message)


def auth(session):
    return {"Authorization": "Bearer " + session["token"]}


def test_no_binding_is_unavailable_not_private_fallback(api_module):
    async def run():
        app = FastAPI()
        app.include_router(api_module.router)
        async with client(app) as c:
            result = await c.post(BASE+"encounter", json=CONSENT)
            assert result.status_code == 503
            assert result.json() == {"error": "public_surface_unavailable"}
    asyncio.run(run())


def test_http_binding_requires_configured_host_lease(api_module, store):
    gate, _ = store
    async def responder(_):
        return "Public response."
    with pytest.raises(p.PublicAdmissionError, match="public_configuration_invalid"):
        api_module.PublicSurfaceBinding(gate, responder, b"z"*32, lambda: NOW)


def test_public_round_trip_claims_and_tokens_never_dispatch_private_work(api_module, store):
    async def run():
        app, binding, seen = host(api_module, store)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            assert not session["lick"]["identity_verified"]
            response = await c.post(BASE+"turn", headers=auth(session), json=payload(session, "tSingularity"))
            assert response.status_code == 200 and response.json()["remaining_turns"] == 9
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["access-control-allow-origin"] == ORIGIN
            assert seen[0].disclosure == "public" and seen[0].effect_ceiling == "NONE"
            assert seen[0].max_output_tokens == 256 and seen[0].deadline_epoch <= NOW+15
            replay = await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            assert replay.status_code == 409 and len(seen) == 1
            await asyncio.sleep(0)
            assert not binding.tasks
    asyncio.run(run())


@pytest.mark.parametrize("origin", ["null", "https://evil.example", "http://foundups.com", "https://foundups.com.evil.example"])
def test_cors_denies_unknown_origins_without_reflection(api_module, store, origin):
    async def run():
        app, _, seen = host(api_module, store)
        async with client(app) as c:
            for method in [c.post, c.options]:
                response = await method(BASE+"encounter", headers={"Origin": origin})
                assert response.status_code == 403
                assert "access-control-allow-origin" not in response.headers
            assert not seen
    asyncio.run(run())


def test_preflight_is_narrow(api_module, store):
    async def run():
        app, _, _ = host(api_module, store)
        async with client(app) as c:
            response = await c.options(BASE+"turn")
            assert response.status_code == 200
            assert response.headers["access-control-allow-methods"] == "POST"
            assert "access-control-allow-credentials" not in response.headers
            assert (await c.options(BASE+"private")).status_code == 404
            assert (await c.post(BASE+"private")).status_code == 404
    asyncio.run(run())


def test_exact_hpc_origin_is_allowed_but_session_cannot_cross_origins(api_module, store):
    async def run():
        app, _, seen = host(api_module, store)
        async with client(app) as c:
            hpc = {"Origin": "https://hpc.foundups.com"}
            preflight = await c.options(BASE+"turn", headers=hpc)
            assert preflight.status_code == 200
            assert preflight.headers["access-control-allow-origin"] == hpc["Origin"]
            session = (await c.post(BASE+"encounter", headers=hpc, json=CONSENT)).json()
            crossed = await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            assert crossed.status_code == 403 and not seen
            accepted = await c.post(BASE+"turn", headers=hpc | auth(session), json=payload(session))
            assert accepted.status_code == 200 and len(seen) == 1
    asyncio.run(run())


@pytest.mark.parametrize("body,status", [('{bad', 400), ('{"consent":true,"consent":false}', 400), ('x'*12300, 413)])
def test_body_bounds_and_duplicate_key_rejection(api_module, store, body, status):
    async def run():
        app, _, seen = host(api_module, store)
        async with client(app) as c:
            response = await c.post(BASE+"encounter", content=body, headers={"Content-Type": "application/json"})
            assert response.status_code == status and not seen
            assert (await c.post(BASE+"encounter", content="x")).status_code == 415
    asyncio.run(run())


def test_auth_and_client_supplied_privilege_fail_closed(api_module, store):
    async def run():
        app, _, seen = host(api_module, store)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            assert (await c.post(BASE+"turn", json=payload(session))).status_code == 403
            response = await c.post(BASE+"turn", headers=auth(session), json=payload(session) | {"principal_id": "012"})
            assert response.status_code == 400 and not seen
    asyncio.run(run())


def test_public_quota_and_proxy_header_cannot_reset_it(api_module, store):
    async def run():
        app, _, seen = host(api_module, store, policy=p.PublicPolicy(subject_sessions_daily=1, session_turns=1))
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            response = await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            session.update(response.json())
            capped = await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            assert capped.status_code == 429 and capped.headers["retry-after"] == "60"
            rotated = await c.post(BASE+"encounter", json=CONSENT, headers={"X-Forwarded-For": "1.2.3.4"})
            assert rotated.status_code == 429 and len(seen) == 1
    asyncio.run(run())


@pytest.mark.parametrize("reply", [None, "", "x"*4001, "bad\u202etext"])
def test_invalid_provider_output_is_bounded_and_consumes_quota(api_module, store, reply):
    async def run():
        async def responder(_):
            return reply
        app, _, _ = host(api_module, store, responder)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            response = await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            assert response.status_code == 502
            assert response.json()["resume"]["remaining_turns"] == 9
    asyncio.run(run())


def test_timeout_retains_slot_until_uncooperative_responder_actually_finishes(api_module, store):
    async def run():
        release = asyncio.Event()
        async def responder(_):
            try:
                await release.wait()
            except asyncio.CancelledError:
                await release.wait()
            return "Late result"
        app, binding, _ = host(api_module, store, responder, p.PublicPolicy(request_seconds=1))
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            response = await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            assert response.status_code == 504
            session.update(response.json()["resume"])
            busy = await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            assert busy.status_code == 409 and len(binding.tasks) == 1
            release.set()
            await asyncio.gather(*tuple(binding.tasks))
            await asyncio.sleep(0)
            assert not binding.tasks
    asyncio.run(run())


def test_withdrawal_while_responding_discards_late_reply(api_module, store):
    async def run():
        release, started = asyncio.Event(), asyncio.Event()
        async def responder(_):
            started.set()
            await release.wait()
            return "MUST_NOT_BE_DELIVERED"
        app, _, _ = host(api_module, store, responder)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            pending = asyncio.create_task(c.post(BASE+"turn", headers=auth(session), json=payload(session)))
            await started.wait()
            withdrawn = await c.post(BASE+"withdraw", headers=auth(session))
            assert withdrawn.status_code == 200 and withdrawn.json()["withdrawn"]
            release.set()
            result = await pending
            assert result.status_code == 410 and "MUST_NOT_BE_DELIVERED" not in result.text
    asyncio.run(run())


def test_wrong_binding_and_database_failure_are_fixed_unavailable(api_module, store):
    async def run():
        app, binding, _ = host(api_module, store)
        async with client(app) as c:
            app.state.reddog_public = object()
            assert (await c.post(BASE+"encounter", json=CONSENT)).status_code == 503
            app.state.reddog_public = binding
            binding.gate._connect = lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_ERROR"))
            response = await c.post(BASE+"encounter", json=CONSENT)
            assert response.status_code == 503 and "PRIVATE_ERROR" not in response.text
    asyncio.run(run())


def test_lost_response_status_recovers_next_nonce_without_duplicate_call(api_module, store):
    async def run():
        app, _, seen = host(api_module, store)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            assert (await c.post(BASE+"turn", headers=auth(session), json=payload(session))).status_code == 409
            response = await c.post(BASE+"status", headers=auth(session), json={})
            snapshot = response.json()
            assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
            assert len(seen) == 1 and snapshot["revision"] == 1 and snapshot["remaining_turns"] == 9
            assert not snapshot["in_flight"] and "reply" not in snapshot and "token" not in snapshot
            session.update(snapshot)
            assert (await c.post(BASE+"turn", headers=auth(session), json=payload(session))).status_code == 200
            assert len(seen) == 2
    asyncio.run(run())


@pytest.mark.parametrize("body", [None, [], {"principal_id": "012"}, {"knowledge_answer": "tSingularity"}, {"nonce": "a"*64}])
def test_status_rejects_client_identity_or_state_fields(api_module, store, body):
    async def run():
        app, _, seen = host(api_module, store)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            response = await c.post(BASE+"status", headers=auth(session) | {"Content-Type": "application/json"}, content=json.dumps(body))
            assert response.status_code == 400 and response.json() == {"error": "public_status_shape_invalid"}
            assert not seen
    asyncio.run(run())


def test_status_needs_bearer_and_does_not_extend_expiry(api_module, store):
    async def run():
        app, binding, seen = host(api_module, store)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            assert (await c.post(BASE+"status", json={})).status_code == 403
            assert (await c.options(BASE+"status")).status_code == 200
            binding.gate.renew_host(now=NOW+59)
            binding.gate.renew_host(now=NOW+118)
            binding.clock = lambda: NOW+119
            response = await c.post(BASE+"status", headers=auth(session), json={})
            assert response.status_code == 200 and response.json()["idle_expires_at"] == NOW+120
            binding.clock = lambda: NOW+120
            expired = await c.post(BASE+"status", headers=auth(session), json={})
            assert expired.status_code == 410 and "nonce" not in expired.json()
            assert not seen
    asyncio.run(run())


def test_status_does_not_cross_surface_or_peer(api_module, store):
    async def run():
        app, _, seen = host(api_module, store)
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            response = await c.post("/api/reddog/public/esingularity/status", headers=auth(session) | {"Origin": "https://esingularity.ai"}, json={})
            assert response.status_code == 403 and "nonce" not in response.json()
        transport = httpx.ASGITransport(app=app, client=("127.0.0.2", 12345))
        async with httpx.AsyncClient(transport=transport, base_url="https://gateway.example") as c:
            response = await c.post(BASE+"status", headers=auth(session) | {"Origin": ORIGIN}, json={})
            assert response.status_code == 403 and "nonce" not in response.json()
        assert not seen
    asyncio.run(run())


def test_http_status_uses_actual_database_manager(api_module, database_store):
    async def run():
        gate, manager, _ = database_store
        app, _, seen = host(api_module, (gate, manager.get_connection))
        async with client(app) as c:
            session = (await c.post(BASE+"encounter", json=CONSENT)).json()
            await c.post(BASE+"turn", headers=auth(session), json=payload(session))
            response = await c.post(BASE+"status", headers=auth(session), json={})
            assert response.status_code == 200 and response.json()["remaining_turns"] == 9
            assert len(seen) == 1
            assert (await c.post(BASE+"withdraw", headers=auth(session))).status_code == 200
            denied = await c.post(BASE+"status", headers=auth(session), json={})
            assert denied.status_code == 403 and "nonce" not in denied.json()
    asyncio.run(run())


def _provider_turn(message="What is HPC?", foundup_id=None):
    return s.PublicTurn(message, "foundups", "r"*64, 1, "n"*64, 9, 128, NOW+15,
                        foundup_id=foundup_id)


def _provider_response(content="HPC is a public catalog entry.", **extra):
    message = {"content": content, "role": "assistant"} | extra.pop("message", {})
    return {"model": ADMITTED_MODEL, "choices": [{"message": message}]} | extra


def _provider(openrouter_module, handler, clock=lambda: NOW):
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    root = Path(__file__).resolve().parents[5]
    config = openrouter_module.PublicOpenRouterConfig("server-secret", ADMITTED_MODEL)
    grounder = openrouter_module.PublicCatalogGrounder.from_repo(root)
    return openrouter_module.PublicOpenRouterResponder(config, client, grounder, clock), client


def test_openrouter_uses_host_model_caps_and_public_hpc_catalog(openrouter_module):
    async def run():
        seen = {}
        def handler(request):
            seen["headers"] = request.headers
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=_provider_response())
        responder, upstream = _provider(openrouter_module, handler)
        try:
            assert await responder(_provider_turn()) == "HPC is a public catalog entry."
        finally:
            await upstream.aclose()
        body = seen["body"]
        assert body["model"] == ADMITTED_MODEL and body["max_tokens"] == 128
        assert body["provider"] == {"require_parameters": True, "data_collection": "deny", "allow_fallbacks": False}
        assert "tools" not in body and "Hasan Piker Coalition" in body["messages"][1]["content"]
        assert "Do not volunteer follow-up" in body["messages"][0]["content"]
        assert seen["headers"]["authorization"] == "Bearer server-secret"
        assert seen["headers"]["http-referer"] == ORIGIN
    asyncio.run(run())


def test_openrouter_exact_foundup_scope_handles_generic_question_only(openrouter_module):
    async def run():
        seen = {}
        def handler(request):
            seen.update(json.loads(request.content))
            return httpx.Response(200, json=_provider_response())
        responder, upstream = _provider(openrouter_module, handler)
        try:
            await responder(_provider_turn("What is this?", "hpc"))
        finally:
            await upstream.aclose()
        context = seen["messages"][1]["content"]
        assert "Hasan Piker Coalition" in context
        assert "HoloIndex" not in context and "eSingularity" not in context
    asyncio.run(run())


def test_openrouter_unknown_foundup_scope_never_falls_back_to_other_entities(openrouter_module):
    async def run():
        seen = {}
        def handler(request):
            seen.update(json.loads(request.content))
            return httpx.Response(200, json=_provider_response("Unknown."))
        responder, upstream = _provider(openrouter_module, handler)
        try:
            await responder(_provider_turn("Tell me about HPC", "private_foundup"))
        finally:
            await upstream.aclose()
        context = seen["messages"][1]["content"]
        assert "UNKNOWN:" in context
        assert "Hasan Piker Coalition" not in context and "HoloIndex" not in context
    asyncio.run(run())


def test_openrouter_config_repr_and_payload_never_expose_key(openrouter_module):
    config = openrouter_module.PublicOpenRouterConfig("never-print-this", ADMITTED_MODEL)
    assert "never-print-this" not in repr(config)
    with pytest.raises(p.PublicAdmissionError) as caught:
        openrouter_module.PublicOpenRouterConfig("", ADMITTED_MODEL)
    assert "never-print-this" not in str(caught.value)


@pytest.mark.parametrize("model", ["arbitrary/model", "openrouter/auto", "openrouter/fusion",
                                   "nvidia/nemotron-3.5-lightning"])
def test_openrouter_rejects_unreviewed_or_aggregate_model_routes(openrouter_module, model):
    with pytest.raises(p.PublicAdmissionError, match="public_provider_model_denied"):
        openrouter_module.PublicOpenRouterConfig("server-secret", model)


def test_openrouter_accepts_exact_public_glm_evaluation_candidate(openrouter_module):
    config = openrouter_module.PublicOpenRouterConfig("server-secret", "z-ai/glm-5.2")
    assert config.model == "z-ai/glm-5.2"


@pytest.mark.parametrize("mode", ["redirect", "tool", "model", "oversize"])
def test_openrouter_denies_redirect_tools_model_substitution_and_large_body(openrouter_module, mode):
    async def run():
        def handler(_request):
            if mode == "redirect":
                return httpx.Response(307, headers={"Location": "https://evil.example"})
            if mode == "tool":
                return httpx.Response(200, json=_provider_response(message={"tool_calls": [{"id": "x"}]}))
            if mode == "model":
                return httpx.Response(200, json=_provider_response(model="fallback/model"))
            return httpx.Response(200, content=b"x"*(openrouter_module.MAX_PROVIDER_BYTES+1))
        responder, upstream = _provider(openrouter_module, handler)
        try:
            with pytest.raises(p.PublicAdmissionError, match="public_provider_failed"):
                await responder(_provider_turn())
        finally:
            await upstream.aclose()
    asyncio.run(run())


def test_openrouter_cancellation_reaches_upstream(openrouter_module):
    async def run():
        started, cancelled = asyncio.Event(), asyncio.Event()
        async def handler(_request):
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise
        responder, upstream = _provider(openrouter_module, handler)
        task = asyncio.create_task(responder(_provider_turn()))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelled.is_set()
        await upstream.aclose()
    asyncio.run(run())


def test_openrouter_deadline_cancels_upstream_with_fixed_error(openrouter_module):
    async def run():
        cancelled = asyncio.Event()
        async def handler(_request):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise
        responder, upstream = _provider(openrouter_module, handler, lambda: NOW+14.99)
        try:
            with pytest.raises(p.PublicAdmissionError, match="public_provider_timeout") as caught:
                await responder(_provider_turn())
            assert caught.value.status == 504 and cancelled.is_set()
        finally:
            await upstream.aclose()
    asyncio.run(run())


def test_openrouter_failure_drops_sensitive_transport_exception_chain(openrouter_module):
    async def run():
        def handler(request):
            raise httpx.ConnectError("server-secret https://private.invalid", request=request)
        responder, upstream = _provider(openrouter_module, handler)
        try:
            with pytest.raises(p.PublicAdmissionError) as caught:
                await responder(_provider_turn())
            error = caught.value
            assert error.__cause__ is None and error.__context__ is None
            assert "server-secret" not in repr(error) and "private.invalid" not in repr(error)
        finally:
            await upstream.aclose()
    asyncio.run(run())


def test_openrouter_responder_runs_through_public_surface_binding(api_module, openrouter_module, store):
    async def run():
        seen = {}
        def handler(request):
            seen["referer"] = request.headers["http-referer"]
            return httpx.Response(200, json=_provider_response("Bounded public reply."))
        responder, upstream = _provider(openrouter_module, handler)
        app, _, _ = host(api_module, store, responder)
        try:
            async with client(app) as c:
                hpc = {"Origin": "https://hpc.foundups.com"}
                session = (await c.post(BASE+"encounter", headers=hpc, json=CONSENT)).json()
                body = payload(session, "What is this?") | {"foundup_id": "hpc"}
                result = await c.post(BASE+"turn", headers=hpc | auth(session), json=body)
            assert result.status_code == 200
            assert result.json()["reply"] == "Bounded public reply."
            assert result.json()["effect_ceiling"] == "NONE"
            assert seen["referer"] == "https://foundups.com"
        finally:
            await upstream.aclose()
    asyncio.run(run())


def test_public_runtime_stays_within_wsp62_bounds(api_module, openrouter_module):
    for module in [p, s, api_module, openrouter_module]:
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert len(source.splitlines()) < 400
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 30, node.name
