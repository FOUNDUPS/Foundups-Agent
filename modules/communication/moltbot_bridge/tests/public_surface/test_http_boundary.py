"""Real ASGI router with synthetic responder; no live provider or network call."""
import asyncio
import json
import sys

import httpx
import pytest
from fastapi import FastAPI

p = sys.modules["_reddog_public_boundary_tests.reddog_public_policy"]
s = sys.modules["_reddog_public_boundary_tests.reddog_public_session_gate"]
NOW = 1800000000
ORIGIN = "https://foundups.com"
BASE = "/api/reddog/public/foundups/"
CONSENT = {"consent": True, "consent_version": p.CONSENT_VERSION, "actor_claim": "human"}


def host(api, store, respond=None, policy=None):
    gate, connect = store
    if policy:
        gate = s.PublicSessionGate(connect, policy)
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
