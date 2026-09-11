"""Lease-backed orphan recovery for the distinct public-host lifecycle contract."""
import hashlib
import json

import pytest
import sys
p = sys.modules["_reddog_public_boundary_tests.reddog_public_policy"]
s = sys.modules["_reddog_public_boundary_tests.reddog_public_session_gate"]

NOW = 1800000000
HOST_A = "1" * 64
HOST_B = "2" * 64
COMMON = dict(surface="foundups", origin="https://foundups.com", subject="a" * 64)
LICK_COMMON = dict(surface="autopost", origin="https://autopost.foundups.com", subject="a" * 64)
CLAIM = dict(consent=True, consent_version=p.CONSENT_VERSION, actor_claim="unspecified")
LICK = {
    "consent": True, "consent_version": p.LICK_CONSENT_VERSION,
    "actor_claim": "human", "profile_mode": "named",
    "display_name": "Guest Builder", "retention": "session",
}


def host(connect, owner, now=NOW):
    gate = s.PublicSessionGate(connect, host_owner=owner)
    gate.initialize()
    gate.register_host(now=now)
    return gate


def encounter(gate, now=NOW):
    return gate.open_encounter(**COMMON, body=CLAIM, now=now)


def turn(gate, session, now=NOW, common=COMMON):
    body = {"nonce": session["nonce"], "revision": session["revision"], "message": "Hello"}
    return gate.reserve_turn(**common, token=session["token"], body=body, now=now)


def status(gate, session, now, common=COMMON):
    return gate.session_status(**common, token=session["token"], now=now)


def test_configured_host_must_register_before_public_use(store):
    _, connect = store
    gate = s.PublicSessionGate(connect, host_owner=HOST_A)
    gate.initialize()
    with pytest.raises(p.PublicAdmissionError, match="host_lease_expired"):
        encounter(gate)
    assert gate.register_host(now=NOW) == NOW + s.HOST_LEASE_SECONDS
    assert encounter(gate)["revision"] == 0


@pytest.mark.parametrize("owner", ["", "012", "g" * 64, None])
def test_invalid_or_missing_host_cannot_claim_recovery(store, owner):
    _, connect = store
    if owner is None:
        gate = s.PublicSessionGate(connect)
        gate.initialize()
        with pytest.raises(p.PublicAdmissionError, match="unconfigured"):
            gate.register_host(now=NOW)
        return
    with pytest.raises(p.PublicAdmissionError, match="configuration_invalid"):
        s.PublicSessionGate(connect, host_owner=owner)


def test_host_owner_token_is_one_use_and_cannot_resurrect(store):
    _, connect = store
    first = host(connect, HOST_A)
    with pytest.raises(p.PublicAdmissionError, match="owner_reused"):
        first.register_host(now=NOW + 1)
    expired = NOW + s.HOST_LEASE_SECONDS + 1
    with pytest.raises(p.PublicAdmissionError, match="owner_reused"):
        first.register_host(now=expired)
    with pytest.raises(p.PublicAdmissionError, match="lease_expired"):
        first.renew_host(now=expired)
    replacement = host(connect, HOST_B, expired)
    assert replacement.renew_host(now=expired + 1) == expired + 1 + s.HOST_LEASE_SECONDS


def test_host_token_is_hashed_and_busy_slot_is_owner_bound(store):
    _, connect = store
    gate = host(connect, HOST_A)
    session = encounter(gate)
    result = turn(gate, session)
    with connect() as conn:
        lease = dict(conn.execute("SELECT * FROM reddog_public_host_lease_v1").fetchone())
        row = dict(conn.execute("SELECT busy,busy_owner FROM reddog_public_session_v1").fetchone())
    assert HOST_A not in json.dumps([lease, row])
    expected = hashlib.sha256(HOST_A.encode("ascii")).hexdigest()
    assert lease["owner_hash"] == row["busy_owner"] == expected
    assert row["busy"] == result.reservation_id


def test_live_owner_renewal_blocks_foreign_recovery(store):
    _, connect = store
    first = host(connect, HOST_A)
    session = encounter(first)
    turn(first, session)
    assert first.renew_host(now=NOW + 30) == NOW + 30 + s.HOST_LEASE_SECONDS
    second = host(connect, HOST_B, NOW + 61)
    assert second.reclaim_orphaned_turns(now=NOW + 61) == 0
    assert status(second, session, NOW + 61)["in_flight"] is True


def test_expired_owner_recovery_preserves_nonce_revision_quota_and_tombstone(store):
    _, connect = store
    first = host(connect, HOST_A)
    session = encounter(first)
    original = dict(session)
    reserved = turn(first, session)
    recovery_now = NOW + s.HOST_LEASE_SECONDS + 1
    second = host(connect, HOST_B, recovery_now)
    assert second.reclaim_orphaned_turns(now=recovery_now) == 1
    with pytest.raises(p.PublicAdmissionError, match="owner_reused"):
        first.register_host(now=recovery_now)
    snapshot = status(second, session, recovery_now)
    assert snapshot["in_flight"] is False
    assert snapshot["revision"] == reserved.revision == 1
    assert snapshot["nonce"] == reserved.next_nonce
    with pytest.raises(p.PublicAdmissionError, match="replay"):
        turn(second, original, recovery_now)
    resumed = turn(second, session | snapshot, recovery_now)
    assert resumed.revision == 2
    with connect() as conn:
        used = conn.execute("SELECT used FROM reddog_public_budget_v1 WHERE bucket='turns:global'").fetchone()[0]
        leases = conn.execute("SELECT COUNT(*) FROM reddog_public_host_lease_v1").fetchone()[0]
    assert used == 2 and leases == 2


def test_expired_owner_cannot_finish_or_deliver_after_recovery(store):
    _, connect = store
    first = host(connect, HOST_A)
    session = encounter(first)
    reserved = turn(first, session)
    recovery_now = NOW + s.HOST_LEASE_SECONDS + 1
    second = host(connect, HOST_B, recovery_now)
    assert second.reclaim_orphaned_turns(now=recovery_now) == 1
    with pytest.raises(p.PublicAdmissionError, match="host_lease_expired"):
        first.finish_turn(token=session["token"], reservation_id=reserved.reservation_id,
                          now=recovery_now)
    assert not first.delivery_allowed(token=session["token"], revision=reserved.revision,
                                      now=recovery_now)


def test_configured_host_gates_lick_start_and_challenge(store):
    _, connect = store
    gate = s.PublicSessionGate(connect, host_owner=HOST_A)
    gate.initialize()
    with pytest.raises(p.PublicAdmissionError, match="host_lease_expired"):
        gate.open_lick_encounter(**LICK_COMMON, body=LICK, now=NOW)
    gate.register_host(now=NOW)
    pending = gate.open_lick_encounter(**LICK_COMMON, body=LICK, now=NOW)
    expired = NOW + s.HOST_LEASE_SECONDS + 1
    with pytest.raises(p.PublicAdmissionError, match="host_lease_expired"):
        gate.complete_lick_challenge(
            **LICK_COMMON, token=pending["token"],
            body={"challenge": pending["challenge"]}, now=expired,
        )


def test_lick_profile_survives_orphan_recovery_without_rechallenging(store):
    _, connect = store
    first = host(connect, HOST_A)
    pending = first.open_lick_encounter(**LICK_COMMON, body=LICK, now=NOW)
    ready = first.complete_lick_challenge(
        **LICK_COMMON, token=pending["token"],
        body={"challenge": pending["challenge"]}, now=NOW,
    )
    reserved = turn(first, pending | ready, common=LICK_COMMON)
    recovery_now = NOW + s.HOST_LEASE_SECONDS + 1
    second = host(connect, HOST_B, recovery_now)
    assert second.reclaim_orphaned_turns(now=recovery_now) == 1
    snapshot = status(second, pending, recovery_now, common=LICK_COMMON)
    resumed = turn(second, pending | snapshot, recovery_now, common=LICK_COMMON)
    assert (reserved.revision, resumed.revision) == (1, 2)
    with connect() as conn:
        lick = conn.execute("SELECT challenge_complete FROM reddog_lick_open_v1").fetchone()
    assert lick["challenge_complete"] == 1


def test_prelease_busy_slot_remains_fail_closed_after_schema_migration(store):
    _, connect = store
    with connect() as conn:
        conn.execute("DROP TABLE reddog_lick_open_v1")
        conn.execute("DROP TABLE reddog_public_session_v1")
        conn.execute("""CREATE TABLE reddog_public_session_v1 (
            token_hash TEXT PRIMARY KEY, encounter TEXT NOT NULL,
            surface TEXT NOT NULL, origin TEXT NOT NULL, subject TEXT NOT NULL,
            actor_claim TEXT NOT NULL, created INTEGER NOT NULL,
            last_seen INTEGER NOT NULL, revision INTEGER NOT NULL,
            nonce TEXT NOT NULL, busy TEXT, closed INTEGER NOT NULL DEFAULT 0)""")
        conn.execute("""INSERT INTO reddog_public_session_v1 VALUES
            (?,?,?,?,?,?,?,?,?,?,?,0)""",
            ("a" * 64, "enc", "foundups", "https://foundups.com", "b" * 64,
             "unspecified", NOW, NOW, 1, "c" * 64, "d" * 64))
        conn.commit()
    gate = s.PublicSessionGate(connect, host_owner=HOST_B)
    gate.initialize()
    gate.register_host(now=NOW + 1)
    assert gate.reclaim_orphaned_turns(now=NOW + 1) == 0
    with connect() as conn:
        row = conn.execute("SELECT busy,busy_owner FROM reddog_public_session_v1").fetchone()
    assert row["busy"] == "d" * 64 and row["busy_owner"] is None


def test_actual_database_manager_recovery_survives_restart(database_store):
    _, manager, module = database_store
    first = host(manager.get_connection, HOST_A)
    session = encounter(first)
    reserved = turn(first, session)
    module.DatabaseManager.reset_for_tests()
    restarted = module.DatabaseManager()
    recovery_now = NOW + s.HOST_LEASE_SECONDS + 1
    second = host(restarted.get_connection, HOST_B, recovery_now)
    assert second.reclaim_orphaned_turns(now=recovery_now) == 1
    snapshot = status(second, session, recovery_now)
    assert (snapshot["revision"], snapshot["nonce"], snapshot["in_flight"]) == (
        reserved.revision, reserved.next_nonce, False)
    assert restarted.execute_query(
        "SELECT used FROM reddog_public_budget_v1 WHERE bucket='turns:global'"
    ) == [{"used": 1}]


def test_sqlite_migration_adds_owner_column_and_host_table(store):
    _, connect = store
    with connect() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(reddog_public_session_v1)")}
        table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reddog_public_host_lease_v1'").fetchone()
    assert "busy_owner" in columns and table["name"] == "reddog_public_host_lease_v1"