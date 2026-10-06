"""Open-source Lick PoC: consent, continuity, expiry, withdrawal, no authority."""
import asyncio
import json
import sys

import httpx
import pytest
from fastapi import FastAPI


p = sys.modules["_reddog_public_boundary_tests.reddog_public_policy"]
s = sys.modules["_reddog_public_boundary_tests.reddog_public_session_gate"]
NOW = 1_800_000_000
HOST_OWNER = "e" * 64
COMMON = dict(surface="autopost", origin="https://autopost.foundups.com", subject="a" * 64)
REQUEST = {
    "consent": True,
    "consent_version": p.LICK_CONSENT_VERSION,
    "actor_claim": "human",
    "profile_mode": "named",
    "display_name": "Guest Builder",
    "retention": "session",
}


def test_challenge_gates_turn_and_receipt_grants_no_authority(store):
    gate, _ = store
    pending = gate.open_lick_encounter(**COMMON, body=REQUEST, now=NOW)
    assert pending["state"] == "challenge_pending"
    assert pending["identity_state"] == "provisional"
    assert pending["authority_granted"] == "none"

    with pytest.raises(p.PublicAdmissionError, match="challenge_required"):
        gate.reserve_turn(**COMMON, token=pending["token"], now=NOW, body={
            "nonce": "0" * 64, "revision": 0, "message": "Hello",
        })

    ready = gate.complete_lick_challenge(
        **COMMON, token=pending["token"], body={"challenge": pending["challenge"]}, now=NOW,
    )
    receipt = ready["lick_receipt"]
    assert ready["state"] == "ready"
    assert receipt["profile"]["display_name"] == "Guest Builder"
    assert receipt["profile"]["identity_state"] == "provisional"
    assert receipt["proofs"] == [
        {"kind": "randomized_challenge_continuity", "result": "completed"},
    ]
    assert receipt["identity_verified"] is False
    assert receipt["human_presence_proven"] is False
    assert receipt["biometrics_collected"] is False
    assert receipt["signed"] is False
    assert receipt["authority_granted"] == "none"

    turn = gate.reserve_turn(**COMMON, token=pending["token"], now=NOW, body={
        "nonce": ready["nonce"], "revision": ready["revision"], "message": "Hello",
    })
    assert turn.effect_ceiling == "NONE"


def test_challenge_is_single_use_and_wrong_value_does_not_consume_it(store):
    gate, _ = store
    pending = gate.open_lick_encounter(**COMMON, body=REQUEST, now=NOW)
    with pytest.raises(p.PublicAdmissionError, match="challenge_rejected"):
        gate.complete_lick_challenge(
            **COMMON, token=pending["token"], body={"challenge": "b" * 64}, now=NOW,
        )
    gate.complete_lick_challenge(
        **COMMON, token=pending["token"], body={"challenge": pending["challenge"]}, now=NOW,
    )
    with pytest.raises(p.PublicAdmissionError, match="challenge_rejected"):
        gate.complete_lick_challenge(
            **COMMON, token=pending["token"], body={"challenge": pending["challenge"]}, now=NOW,
        )


@pytest.mark.parametrize("extra", [
    {"voiceprint": "sample"}, {"face": "sample"}, {"heartbeat": 72},
    {"device_credential": "secret"}, {"role": "admin"},
])
def test_biometric_and_privilege_fields_are_rejected(store, extra):
    gate, _ = store
    with pytest.raises(p.PublicAdmissionError, match="shape_invalid"):
        gate.open_lick_encounter(**COMMON, body=REQUEST | extra, now=NOW)


def test_guest_mode_requires_no_name_and_withdraws_without_profile_residue(store):
    gate, connect = store
    pending = gate.open_lick_encounter(
        **COMMON,
        body=REQUEST | {"profile_mode": "guest", "display_name": None, "actor_claim": "unspecified"},
        now=NOW,
    )
    gate.complete_lick_challenge(
        **COMMON, token=pending["token"], body={"challenge": pending["challenge"]}, now=NOW,
    )
    result = gate.withdraw(**COMMON, token=pending["token"], now=NOW)
    assert result["withdrawn"] and result["authority_granted"] == "none"
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM reddog_lick_open_v1").fetchone()[0] == 0


def test_in_flight_withdrawal_removes_profile_after_completion(store):
    gate, connect = store
    pending = gate.open_lick_encounter(**COMMON, body=REQUEST, now=NOW)
    ready = gate.complete_lick_challenge(
        **COMMON, token=pending["token"], body={"challenge": pending["challenge"]}, now=NOW,
    )
    turn = gate.reserve_turn(**COMMON, token=pending["token"], now=NOW, body={
        "nonce": ready["nonce"], "revision": 0, "message": "Hello",
    })
    assert gate.withdraw(**COMMON, token=pending["token"], now=NOW)["in_flight_retained_until_completion"]
    assert gate.finish_turn(token=pending["token"], reservation_id=turn.reservation_id, now=NOW)
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM reddog_lick_open_v1").fetchone()[0] == 0


def test_expiry_blocks_challenge_completion(store):
    gate, _ = store
    pending = gate.open_lick_encounter(**COMMON, body=REQUEST, now=NOW)
    with pytest.raises(p.PublicAdmissionError, match="expired"):
        gate.complete_lick_challenge(
            **COMMON, token=pending["token"], body={"challenge": pending["challenge"]},
            now=NOW + gate.policy.session_seconds,
        )


def test_database_contains_no_raw_challenge_token(store):
    gate, connect = store
    pending = gate.open_lick_encounter(**COMMON, body=REQUEST, now=NOW)
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM reddog_lick_open_v1")]
    serialized = json.dumps(rows)
    assert pending["challenge"] not in serialized
    assert pending["token"] not in serialized


def test_http_lick_round_trip(api_module, store):
    async def run():
        _, connect = store
        gate = s.PublicSessionGate(connect, host_owner=HOST_OWNER)
        gate.initialize()
        gate.register_host(now=NOW)
        async def respond(_turn):
            return "Public response."
        app = FastAPI()
        app.include_router(api_module.router)
        app.state.reddog_public = api_module.PublicSurfaceBinding(
            gate, respond, b"z" * 32, lambda: NOW,
        )
        headers = {"Origin": COMMON["origin"]}
        base = "/api/reddog/public/autopost/"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://gateway.example",
            headers=headers,
        ) as client:
            pending_response = await client.post(base + "lick", json=REQUEST)
            assert pending_response.status_code == 200
            pending = pending_response.json()
            ready_response = await client.post(
                base + "challenge",
                headers={"Authorization": "Bearer " + pending["token"]},
                json={"challenge": pending["challenge"]},
            )
            assert ready_response.status_code == 200
            assert ready_response.json()["lick_receipt"]["authority_granted"] == "none"
            replay = await client.post(
                base + "challenge",
                headers={"Authorization": "Bearer " + pending["token"]},
                json={"challenge": pending["challenge"]},
            )
            assert replay.status_code == 409
    asyncio.run(run())
