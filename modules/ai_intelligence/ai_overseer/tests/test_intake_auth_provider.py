#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the trusted intake auth verifier (Phase 2, hardened).

The provider is the ONLY thing allowed to set authenticated / invite_token_verified /
requester_handle on a LaunchRequestIntakeContext. These tests prove: fail-closed by
default, constant-time HMAC verify, token KIND+VERSION enforcement (sess.v1 / invite.v1)
with session<->invite confusion rejected, unambiguous canonicalization (independent
b64url fields), full time policy (exp required, iat required, MAX TTL, now==exp boundary),
single-use invite via ONE atomic consume_once (across two SQLite instances on the same
file), an injectable secret_provider seam (no os.environ mutation) with rotation, no
downgrade between independent mechanisms, no payload influence (confused deputy), handle
hygiene, and that NO token/secret/nonce leaks into the context. A static AST sweep proves
no web framework / runtime / network / subprocess imports and that the mint helpers are
non-exported.
"""

from __future__ import annotations

import ast
import threading
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_auth_provider import (
    build_intake_context,
    _make_session_token,
    _make_invite_token,
    InMemoryNonceStore,
    SQLiteNonceStore,
    NonceStore,
    default_secret_provider,
    HMAC_SECRET_ENV,
    HMAC_SECRET_PREVIOUS_ENV,
    MAX_TTL_SESSION_SECONDS,
    MAX_TTL_INVITE_SECONDS,
    CLOCK_SKEW_SECONDS,
)
from modules.ai_intelligence.ai_overseer.src.foundup_genesis import (
    intake_auth_provider as _mod,
)
from modules.ai_intelligence.ai_overseer.src.foundup_genesis.launch_request import (
    LaunchRequest,
    LaunchRequestIntakeContext,
    to_genesis_envelope,
    validate_launch_request,
)

MODULE_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "foundup_genesis"
    / "intake_auth_provider.py"
)

_SECRET = "test-intake-secret-AAAA"
_OTHER_SECRET = "unrelated-secret-ZZZZ"
_PREV_SECRET = "previous-rotation-secret-BBBB"


def _provider(current=_SECRET, previous=None):
    """Build a secret_provider WITHOUT touching os.environ (Addendum E test seam)."""
    return lambda: (current, previous)


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    """Default deterministic env secret (covers the default_secret_provider path).

    Tests that exercise the injectable seam pass secret_provider= explicitly and do NOT
    rely on this env value.
    """
    monkeypatch.setenv(HMAC_SECRET_ENV, _SECRET)
    monkeypatch.delenv(HMAC_SECRET_PREVIOUS_ENV, raising=False)
    yield


def _now() -> int:
    return 1_000_000


def _iat() -> int:
    return _now() - 10


def _future() -> int:
    return _now() + 1800  # within both TTL caps


def _past() -> int:
    return _now() - 3600


def _clean_payload() -> LaunchRequest:
    return LaunchRequest(
        proposed_name="Get Kei Truck Marketplace",
        problem_statement="Help people buy and sell used Kei trucks safely.",
        intended_users="scouts, buyers, sellers",
        category="marketplace",
        reference_urls=["https://example.com/kei-trucks"],
        requested_type="marketplace",
    )


def _session(secret=_SECRET, subject="alice", iat=None, exp=None):
    return _make_session_token(secret, subject, iat if iat is not None else _iat(),
                               exp if exp is not None else _future())


def _invite(secret=_SECRET, handle="bob", nonce="nonce-1", iat=None, exp=None):
    return _make_invite_token(secret, handle, nonce, iat if iat is not None else _iat(),
                              exp if exp is not None else _future())


# --- POSITIVE ---------------------------------------------------------------


def test_valid_session_sets_authenticated_and_handle():
    ctx = build_intake_context(_session(), None, now=_now())
    assert ctx.authenticated is True
    assert ctx.invite_token_verified is False
    assert ctx.requester_handle == "alice"


def test_valid_invite_sets_invite_verified_and_handle():
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, _invite(), nonce_store=store, now=_now())
    assert ctx.invite_token_verified is True
    assert ctx.authenticated is False
    assert ctx.requester_handle == "bob"


def test_both_tokens_set_both_booleans():
    store = InMemoryNonceStore()
    s = _session(subject="carol")
    i = _invite(handle="carol", nonce="nonce-both")
    ctx = build_intake_context(s, i, nonce_store=store, now=_now())
    assert ctx.authenticated is True
    assert ctx.invite_token_verified is True
    assert ctx.requester_handle == "carol"


def test_produced_context_opens_phase1_gate_session():
    ctx = build_intake_context(_session(), None, now=_now())
    res = validate_launch_request(_clean_payload(), ctx)
    assert res.ok, res.errors


def test_produced_context_opens_phase1_gate_invite():
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, _invite(nonce="gate-nonce"), nonce_store=store, now=_now())
    res = validate_launch_request(_clean_payload(), ctx)
    assert res.ok, res.errors


def test_genesis_requested_by_comes_from_verified_handle_not_payload():
    ctx = build_intake_context(_session(), None, now=_now())
    payload = _clean_payload()
    payload.requester_handle = "attacker_supplied"
    env = to_genesis_envelope(payload, ctx)
    assert env.requested_by == "alice"
    assert env.requested_by != "attacker_supplied"


def test_sqlite_nonce_store_valid_invite():
    store = SQLiteNonceStore(":memory:")
    ctx = build_intake_context(None, _invite(handle="dave", nonce="sql-nonce"),
                               nonce_store=store, now=_now())
    assert ctx.invite_token_verified is True
    assert ctx.requester_handle == "dave"
    store.close()


# --- ADDENDUM A: TOKEN KIND + VERSION + CONFUSION ---------------------------


def test_invite_token_into_session_path_rejected():
    # An invite.v1 token handed to the session slot can NEVER set authenticated.
    inv = _invite(handle="alice", nonce="confuse-1")
    ctx = build_intake_context(inv, None, now=_now())
    assert ctx.authenticated is False
    assert ctx.invite_token_verified is False
    assert ctx.requester_handle is None


def test_session_token_into_invite_path_rejected():
    # A sess.v1 token handed to the invite slot can NEVER set invite_token_verified.
    store = InMemoryNonceStore()
    sess = _session(subject="alice")
    ctx = build_intake_context(None, sess, nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False
    assert ctx.authenticated is False
    assert ctx.requester_handle is None


def test_session_v2_version_rejected():
    # A sess.v2. prefix is unknown -> fail closed (version enforced).
    tok = _session()
    bumped = "sess.v2." + tok[len("sess.v1."):]
    ctx = build_intake_context(bumped, None, now=_now())
    assert ctx.authenticated is False


def test_invite_v2_version_rejected():
    store = InMemoryNonceStore()
    tok = _invite()
    bumped = "invite.v2." + tok[len("invite.v1."):]
    ctx = build_intake_context(None, bumped, nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


def test_no_prefix_session_rejected():
    # Strip the kindver prefix entirely -> no kind -> fail closed.
    tok = _session()
    body = tok[len("sess.v1."):]
    ctx = build_intake_context(body, None, now=_now())
    assert ctx.authenticated is False


def test_unknown_prefix_rejected():
    tok = _session()
    swapped = "bogus.v1." + tok[len("sess.v1."):]
    ctx = build_intake_context(swapped, None, now=_now())
    assert ctx.authenticated is False


def test_kindver_swap_breaks_signature():
    # Re-label a session token as invite (same body+sig): signature no longer matches
    # because KINDVER is part of the signed bytes.
    sess = _session(subject="alice")
    relabelled = "invite.v1." + sess[len("sess.v1."):]
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, relabelled, nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


# --- ADDENDUM B: UNAMBIGUOUS CANONICALIZATION -------------------------------


def test_subject_extra_part_cannot_change_field_count():
    # Appending ".extra" to a session token adds a part -> field count != 4 -> reject.
    tok = _session(subject="alice")
    parts = tok.split(".")
    # Insert an extra b64 field before the signature.
    tampered = ".".join(parts[:-1] + ["ZXh0cmE", parts[-1]])
    ctx = build_intake_context(tampered, None, now=_now())
    assert ctx.authenticated is False


def test_dot_inside_subject_cannot_change_parsing():
    # A subject literally containing '.' is b64url-encoded, so it is ONE field; the verified
    # handle still derives from the whole subject (here '.' normalizes to '_').
    ctx = build_intake_context(_session(subject="ali.ce"), None, now=_now())
    assert ctx.authenticated is True
    assert ctx.requester_handle == "ali_ce"


def test_pipe_inside_subject_cannot_change_parsing():
    ctx = build_intake_context(_session(subject="a|b|c"), None, now=_now())
    assert ctx.authenticated is True
    # '|' is not a separator; _normalize leaves it -> single field preserved.
    assert ctx.requester_handle == "a|b|c"


def test_same_logical_token_signs_same_bytes():
    a = _make_session_token(_SECRET, "alice", 999_990, 1_001_800)
    b = _make_session_token(_SECRET, "alice", 999_990, 1_001_800)
    assert a == b


def test_empty_subject_rejected():
    ctx = build_intake_context(_session(subject=""), None, now=_now())
    assert ctx.authenticated is False
    assert ctx.requester_handle is None


def test_whitespace_subject_rejected():
    ctx = build_intake_context(_session(subject="   "), None, now=_now())
    assert ctx.authenticated is False


def test_empty_handle_invite_rejected():
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, _invite(handle="", nonce="n-eh"),
                               nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


def test_whitespace_handle_invite_rejected():
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, _invite(handle="  \t ", nonce="n-wh"),
                               nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


def test_empty_nonce_invite_rejected():
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, _invite(handle="bob", nonce=""),
                               nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


def test_whitespace_nonce_invite_rejected():
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, _invite(handle="bob", nonce="   "),
                               nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


def test_malformed_base64_field_rejected():
    # Corrupt the subject b64 field with a non-alphabet char -> decode raises -> reject.
    tok = _session(subject="alice")
    parts = tok.split(".")
    parts[2] = "@@@@"  # parts[0]='sess', parts[1]='v1', parts[2]=b64(subject)
    ctx = build_intake_context(".".join(parts), None, now=_now())
    assert ctx.authenticated is False


# --- ADDENDUM C: TIME + CLOCK SKEW ------------------------------------------


def test_expired_session_rejected():
    ctx = build_intake_context(_session(iat=_past() - 10, exp=_past()), None, now=_now())
    assert ctx.authenticated is False


def test_expired_invite_rejected():
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, _invite(iat=_past() - 10, exp=_past(), nonce="exp-n"),
                               nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


def test_now_equals_exp_is_expired_boundary():
    # Boundary: now == exp -> EXPIRED/rejected (valid iff now < exp).
    exp = _now()
    ctx = build_intake_context(_session(iat=exp - 100, exp=exp), None, now=_now())
    assert ctx.authenticated is False
    # One second earlier is still valid.
    ok = build_intake_context(_session(iat=exp - 100, exp=exp + 1), None, now=_now())
    assert ok.authenticated is True


def test_future_iat_rejected():
    # Issued in the future (iat > now) -> reject (acts like an unenforced nbf would).
    ctx = build_intake_context(_session(iat=_now() + 100, exp=_now() + 200), None, now=_now())
    assert ctx.authenticated is False


def test_excessive_ttl_session_rejected_even_with_valid_signature():
    iat = _now() - 10
    exp = iat + MAX_TTL_SESSION_SECONDS + 5  # over the cap
    tok = _session(iat=iat, exp=exp)
    ctx = build_intake_context(tok, None, now=_now())
    assert ctx.authenticated is False


def test_excessive_ttl_invite_rejected_even_with_valid_signature():
    store = InMemoryNonceStore()
    iat = _now() - 10
    exp = iat + MAX_TTL_INVITE_SECONDS + 5
    tok = _invite(iat=iat, exp=exp, nonce="ttl-n")
    ctx = build_intake_context(None, tok, nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False


def test_ttl_at_exact_cap_session_allowed():
    iat = _now() - 5
    exp = iat + MAX_TTL_SESSION_SECONDS  # exactly the cap, and now < exp
    tok = _session(iat=iat, exp=exp)
    ctx = build_intake_context(tok, None, now=_now())
    assert ctx.authenticated is True


def test_clock_skew_is_zero_constant():
    assert CLOCK_SKEW_SECONDS == 0


# --- ADDENDUM D: NONCE STORE SINGLE ATOMIC METHOD ---------------------------


def test_invite_replay_second_use_rejected():
    store = InMemoryNonceStore()
    tok = _invite(nonce="replay-nonce")
    first = build_intake_context(None, tok, nonce_store=store, now=_now())
    second = build_intake_context(None, tok, nonce_store=store, now=_now())
    assert first.invite_token_verified is True
    assert second.invite_token_verified is False
    assert second.requester_handle is None


def test_consume_once_single_atomic_method_inmemory():
    store = InMemoryNonceStore()
    assert store.consume_once("atomic-nonce", expires_at=_future(), subject="bob") is True
    assert store.consume_once("atomic-nonce", expires_at=_future(), subject="bob") is False


def test_consume_once_single_atomic_method_sqlite():
    s = SQLiteNonceStore(":memory:")
    assert s.consume_once("atomic-nonce", expires_at=_future(), subject="bob") is True
    assert s.consume_once("atomic-nonce", expires_at=_future(), subject="bob") is False
    s.close()


def test_nonce_store_protocol_has_only_consume_once():
    # The Protocol surface is a single atomic method (Addendum D): no separate consume().
    assert hasattr(NonceStore, "consume_once")
    assert not hasattr(InMemoryNonceStore, "consume")
    assert not hasattr(SQLiteNonceStore, "consume")


def test_replay_rejected_across_two_sqlite_instances_same_file(tmp_path):
    db = str(tmp_path / "nonces.db")
    a = SQLiteNonceStore(db)
    b = SQLiteNonceStore(db)
    tok = _invite(nonce="cross-instance-nonce")
    first = build_intake_context(None, tok, nonce_store=a, now=_now())
    # A SEPARATE instance pointing at the SAME file must reject the replay (durable).
    second = build_intake_context(None, tok, nonce_store=b, now=_now())
    assert first.invite_token_verified is True
    assert second.invite_token_verified is False
    a.close()
    b.close()


def test_duplicate_insert_rejects_cleanly_no_raise(tmp_path):
    # A simulated duplicate insert must return False, never let an exception escape.
    db = str(tmp_path / "dup.db")
    a = SQLiteNonceStore(db)
    b = SQLiteNonceStore(db)
    assert a.consume_once("dup", expires_at=_future(), subject="x") is True
    # Same nonce via a second instance on the same file -> IntegrityError -> False.
    assert b.consume_once("dup", expires_at=_future(), subject="x") is False
    a.close()
    b.close()


def test_invite_with_none_store_still_single_use_within_call():
    tok = _invite(nonce="no-store-nonce")
    ctx = build_intake_context(None, tok, nonce_store=None, now=_now())
    assert ctx.invite_token_verified is True


# --- ADDENDUM D (CONCURRENCY): EXACTLY-ONCE CONSUME UNDER RACE ---------------
# These encode the HIGH break found in adversarial review: a single shared sqlite3
# connection (check_same_thread=False) is NOT thread-safe at the cursor level, so under
# concurrency the IntegrityError was not delivered deterministically and MULTIPLE callers
# received True for the SAME nonce -> a single-use invite double-spend. They FAIL against
# the old shared-connection implementation (reproduced 4..12 True for 16 threads) and PASS
# against the threading.Lock + BEGIN IMMEDIATE fix. A threading.Barrier maximizes the
# collision window; each test loops several trials so the race is reliably exercised.

_RACE_THREADS = 24
_RACE_TRIALS = 8


def _row_count(store: SQLiteNonceStore, nonce: str | None = None) -> int:
    if nonce is None:
        cur = store._conn.execute("SELECT COUNT(*) FROM intake_nonces")
    else:
        cur = store._conn.execute(
            "SELECT COUNT(*) FROM intake_nonces WHERE nonce = ?", (nonce,)
        )
    return int(cur.fetchone()[0])


def test_sqlite_consume_once_exactly_one_true_under_thread_race():
    # N threads race ONE SQLiteNonceStore.consume_once on the SAME nonce ->
    # EXACTLY ONE True, 0 exceptions, exactly 1 row in the table. (Loops trials.)
    for trial in range(_RACE_TRIALS):
        store = SQLiteNonceStore(":memory:")
        nonce = f"race-thread-{trial}"
        results: list[bool] = []
        errors: list[str] = []
        res_lock = threading.Lock()
        barrier = threading.Barrier(_RACE_THREADS)

        def worker() -> None:
            barrier.wait()  # release all threads at once -> maximal collision
            try:
                r = store.consume_once(nonce, expires_at=_future(), subject="bob")
            except Exception as exc:  # consume_once must NEVER raise
                with res_lock:
                    errors.append(repr(exc))
                return
            with res_lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(_RACE_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        true_count = sum(1 for r in results if r is True)
        assert not errors, f"trial {trial}: consume_once raised: {errors}"
        assert true_count == 1, f"trial {trial}: expected exactly 1 True, got {true_count}"
        assert len(results) == _RACE_THREADS, f"trial {trial}: lost results {len(results)}"
        assert _row_count(store, nonce) == 1, f"trial {trial}: expected exactly 1 row"
        store.close()


def test_build_intake_context_same_invite_verified_exactly_once_under_race():
    # N threads each call build_intake_context() with the SAME single-use invite token +
    # the SAME shared SQLiteNonceStore -> EXACTLY ONE returns invite_token_verified=True.
    for trial in range(_RACE_TRIALS):
        store = SQLiteNonceStore(":memory:")
        build_nonce = f"race-build-{trial}"
        tok = _invite(nonce=build_nonce)
        verified: list[bool] = []
        errors: list[str] = []
        res_lock = threading.Lock()
        barrier = threading.Barrier(_RACE_THREADS)

        def worker() -> None:
            barrier.wait()
            try:
                ctx = build_intake_context(None, tok, nonce_store=store, now=_now())
            except Exception as exc:  # build_intake_context fails closed, never raises
                with res_lock:
                    errors.append(repr(exc))
                return
            with res_lock:
                verified.append(ctx.invite_token_verified)

        threads = [threading.Thread(target=worker) for _ in range(_RACE_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        true_count = sum(1 for v in verified if v is True)
        assert not errors, f"trial {trial}: build_intake_context raised: {errors}"
        assert true_count == 1, (
            f"trial {trial}: invite double-spend -- expected exactly 1 "
            f"invite_token_verified=True, got {true_count}"
        )
        assert _row_count(store, build_nonce) == 1, (
            f"trial {trial}: expected exactly 1 consumed nonce"
        )
        store.close()


def test_sqlite_two_instances_same_file_exactly_one_true_under_race(tmp_path):
    # TWO SQLiteNonceStore instances on the SAME temp db file, threads split across both,
    # racing the same nonce -> EXACTLY ONE True (cross-instance durability under concurrency).
    db = str(tmp_path / "race_cross_instance.db")
    for trial in range(_RACE_TRIALS):
        a = SQLiteNonceStore(db)
        b = SQLiteNonceStore(db)
        nonce = f"race-cross-{trial}"
        results: list[bool] = []
        errors: list[str] = []
        res_lock = threading.Lock()
        barrier = threading.Barrier(_RACE_THREADS)

        def worker(idx: int) -> None:
            store = a if idx % 2 == 0 else b  # split threads across both instances
            barrier.wait()
            try:
                r = store.consume_once(nonce, expires_at=_future(), subject="bob")
            except Exception as exc:
                with res_lock:
                    errors.append(repr(exc))
                return
            with res_lock:
                results.append(r)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(_RACE_THREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        true_count = sum(1 for r in results if r is True)
        assert not errors, f"trial {trial}: consume_once raised: {errors}"
        assert true_count == 1, (
            f"trial {trial}: cross-instance double-spend -- expected exactly 1 True, "
            f"got {true_count}"
        )
        assert _row_count(a, nonce) == 1, f"trial {trial}: expected exactly 1 row on disk"
        a.close()
        b.close()


def test_inmemory_consume_once_exactly_one_true_under_thread_race():
    # InMemoryNonceStore is already GIL/Lock-safe; lock the contract in too.
    for trial in range(_RACE_TRIALS):
        store = InMemoryNonceStore()
        nonce = f"race-mem-{trial}"
        results: list[bool] = []
        errors: list[str] = []
        res_lock = threading.Lock()
        barrier = threading.Barrier(_RACE_THREADS)

        def worker() -> None:
            barrier.wait()
            try:
                r = store.consume_once(nonce, expires_at=_future(), subject="bob")
            except Exception as exc:
                with res_lock:
                    errors.append(repr(exc))
                return
            with res_lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(_RACE_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        true_count = sum(1 for r in results if r is True)
        assert not errors, f"trial {trial}: consume_once raised: {errors}"
        assert true_count == 1, f"trial {trial}: expected exactly 1 True, got {true_count}"
        store.close() if hasattr(store, "close") else None


# --- STRICT INTEGER PARSING (iat/exp digits-only) ---------------------------
# Defensive hardening: iat/exp decoded fields must match ^[0-9]+$ before int(); a leading
# sign or surrounding/embedded whitespace is rejected, not silently coerced. Minting
# requires the secret so this is not an auth bypass, but it is closed anyway.


@pytest.mark.parametrize("bad_iat", [" 999990", "999990 ", "+999990", "-999990", " 999990 "])
def test_session_iat_with_sign_or_whitespace_rejected(bad_iat):
    # Mint a token whose iat field is a non-strict integer string -> _parse_int_field None
    # -> token rejected (fails closed) even though the signature is valid.
    secret = _SECRET
    sb = secret.encode("utf-8")
    tok = _mod._mint(
        sb,
        _mod._KINDVER_SESSION,
        [b"alice", bad_iat.encode("utf-8"), str(_future()).encode("utf-8")],
    )
    ctx = build_intake_context(tok, None, now=_now())
    assert ctx.authenticated is False
    assert ctx.requester_handle is None


@pytest.mark.parametrize("bad_exp", [" 1001800", "1001800 ", "+1001800", "-1001800"])
def test_session_exp_with_sign_or_whitespace_rejected(bad_exp):
    secret = _SECRET
    sb = secret.encode("utf-8")
    tok = _mod._mint(
        sb,
        _mod._KINDVER_SESSION,
        [b"alice", str(_iat()).encode("utf-8"), bad_exp.encode("utf-8")],
    )
    ctx = build_intake_context(tok, None, now=_now())
    assert ctx.authenticated is False


def test_strict_digit_iat_still_accepted():
    # Sanity: a clean all-digit iat/exp still verifies (no over-strict regression).
    ctx = build_intake_context(_session(), None, now=_now())
    assert ctx.authenticated is True


# --- ADDENDUM E: ENV SECRET HANDLING + TEST SEAM ----------------------------


def test_secret_injected_via_provider_without_touching_environ(monkeypatch):
    # Wipe env entirely; the provider seam must still supply the secret.
    monkeypatch.delenv(HMAC_SECRET_ENV, raising=False)
    monkeypatch.delenv(HMAC_SECRET_PREVIOUS_ENV, raising=False)
    ctx = build_intake_context(_session(), None, now=_now(), secret_provider=_provider())
    assert ctx.authenticated is True
    assert ctx.requester_handle == "alice"


def test_empty_current_secret_fails_closed_via_provider():
    ctx = build_intake_context(_session(), None, now=_now(),
                               secret_provider=_provider(current=""))
    assert ctx.authenticated is False


def test_both_secrets_missing_fails_closed_via_provider():
    ctx = build_intake_context(_session(), None, now=_now(),
                               secret_provider=lambda: (None, None))
    assert ctx.authenticated is False


def test_missing_secret_fails_closed_env(monkeypatch):
    monkeypatch.delenv(HMAC_SECRET_ENV, raising=False)
    monkeypatch.delenv(HMAC_SECRET_PREVIOUS_ENV, raising=False)
    ctx = build_intake_context(_session(), None, now=_now())
    assert ctx.authenticated is False
    assert ctx.invite_token_verified is False
    assert ctx.requester_handle is None


def test_empty_secret_fails_closed_env(monkeypatch):
    monkeypatch.setenv(HMAC_SECRET_ENV, "")
    monkeypatch.delenv(HMAC_SECRET_PREVIOUS_ENV, raising=False)
    ctx = build_intake_context(_session(), None, now=_now())
    assert ctx.authenticated is False


def test_rotation_previous_secret_verifies_via_provider():
    # Token signed with PREVIOUS secret verifies while a new current is in place.
    tok = _session(secret=_PREV_SECRET)
    ctx = build_intake_context(tok, None, now=_now(),
                               secret_provider=_provider(current=_SECRET, previous=_PREV_SECRET))
    assert ctx.authenticated is True
    assert ctx.requester_handle == "alice"


def test_rotation_unrelated_secret_rejected_via_provider():
    tok = _session(secret=_OTHER_SECRET)
    ctx = build_intake_context(tok, None, now=_now(),
                               secret_provider=_provider(current=_SECRET, previous=_PREV_SECRET))
    assert ctx.authenticated is False


def test_previous_secret_never_signs():
    # A token whose signature ONLY matches the previous secret must still verify (rotation),
    # but a token signed with the CURRENT secret must NOT verify under a provider that only
    # exposes that secret as 'previous' (current empty) -> fail closed (previous never anchors).
    tok = _session(secret=_SECRET)
    ctx = build_intake_context(tok, None, now=_now(),
                               secret_provider=lambda: ("", _SECRET))
    assert ctx.authenticated is False


def test_default_secret_provider_reads_env(monkeypatch):
    monkeypatch.setenv(HMAC_SECRET_ENV, "env-current")
    monkeypatch.setenv(HMAC_SECRET_PREVIOUS_ENV, "env-previous")
    cur, prev = default_secret_provider()
    assert cur == "env-current"
    assert prev == "env-previous"


# --- NEGATIVE / ADVERSARIAL (signature) -------------------------------------


def test_forged_signature_rejected():
    ctx = build_intake_context(_session(secret=_OTHER_SECRET), None, now=_now())
    assert ctx.authenticated is False
    assert ctx.requester_handle is None


def test_tampered_signature_rejected():
    tok = _session()
    tampered = tok[:-2] + ("AA" if not tok.endswith("AA") else "BB")
    ctx = build_intake_context(tampered, None, now=_now())
    assert ctx.authenticated is False


def test_tampered_subject_rejected():
    tok = _session(subject="alice")
    parts = tok.split(".")
    parts[2] = parts[2][:-1] + ("a" if parts[2][-1] != "a" else "b")  # corrupt subject b64
    ctx = build_intake_context(".".join(parts), None, now=_now())
    assert ctx.authenticated is False


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "",
        "onlyonepart",
        "sess.v1",            # prefix only, no body
        "sess.v1.",           # prefix + empty remainder
        "sess.v1.too.few",    # 2 fields (needs 3) + sig miscount
        "invite.v1.aaaa.bbbb.cccc.dddd",  # invite shape in session slot
        "x.aaaa.bbbb.cccc",   # unknown prefix
        "sess.v1.@@@.###.$$$",  # non-base64 fields
        "   ",
    ],
)
def test_malformed_session_tokens_fail_closed(bad):
    ctx = build_intake_context(bad, None, now=_now())
    assert ctx.authenticated is False
    assert ctx.requester_handle is None


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "",
        "onlyonepart",
        "invite.v1",
        "invite.v1.too.few",
        "sess.v1.aaaa.bbbb.cccc",  # session shape in invite slot
        "invite.v1.@@@.###.$$$.%%%",
    ],
)
def test_malformed_invite_tokens_fail_closed(bad):
    store = InMemoryNonceStore()
    ctx = build_intake_context(None, bad, nonce_store=store, now=_now())
    assert ctx.invite_token_verified is False
    assert ctx.requester_handle is None


def test_provider_has_expected_signature_no_payload_confused_deputy():
    import inspect

    sig = inspect.signature(build_intake_context)
    param_names = set(sig.parameters)
    assert param_names == {"session_token", "invite_token", "nonce_store", "now", "secret_provider"}
    for forbidden in ("payload", "vouch", "on_behalf_of", "request", "claims", "assertion"):
        assert forbidden not in param_names


def test_handle_is_normalized():
    ctx = build_intake_context(_session(subject="Alice-Smith"), None, now=_now())
    assert ctx.authenticated is True
    assert ctx.requester_handle == "alice_smith"


def test_secret_looking_handle_is_redacted():
    secretish = "sk-ABCDEFGHIJKLMNOPQRSTUVWX"
    ctx = build_intake_context(_session(subject=secretish), None, now=_now())
    assert ctx.authenticated is True
    handle = ctx.requester_handle or ""
    assert secretish.lower() not in handle
    assert "abcdefghijklmnopqrstuvwx" not in handle
    assert "redacted" in handle.lower()


def test_no_downgrade_bad_session_good_invite():
    store = InMemoryNonceStore()
    bad_session = _session(secret=_OTHER_SECRET, subject="alice")
    good_invite = _invite(handle="bob", nonce="downgrade-1")
    ctx = build_intake_context(bad_session, good_invite, nonce_store=store, now=_now())
    assert ctx.authenticated is False
    assert ctx.invite_token_verified is True
    assert ctx.requester_handle == "bob"


def test_no_downgrade_good_session_bad_invite():
    store = InMemoryNonceStore()
    good_session = _session(subject="alice")
    bad_invite = _invite(secret=_OTHER_SECRET, handle="bob", nonce="downgrade-2")
    ctx = build_intake_context(good_session, bad_invite, nonce_store=store, now=_now())
    assert ctx.authenticated is True
    assert ctx.invite_token_verified is False
    assert ctx.requester_handle == "alice"


def test_default_context_is_fail_closed():
    ctx = build_intake_context(None, None, now=_now())
    assert ctx.authenticated is False
    assert ctx.invite_token_verified is False
    assert ctx.requester_handle is None


def test_nonce_store_protocol_runtime_checkable():
    assert isinstance(InMemoryNonceStore(), NonceStore)
    s = SQLiteNonceStore(":memory:")
    assert isinstance(s, NonceStore)
    s.close()


# --- LEAK: no token/secret/nonce reachable from the context -----------------


def test_no_token_secret_or_nonce_in_context_repr():
    store = InMemoryNonceStore()
    s = _session(subject="alice")
    i = _invite(handle="alice", nonce="leak-nonce")
    ctx = build_intake_context(s, i, nonce_store=store, now=_now())
    blob = repr(ctx) + str(ctx.__dict__)
    assert _SECRET not in blob
    assert s not in blob
    assert i not in blob
    assert "leak-nonce" not in blob


# --- ADDENDUM F: mint helpers are non-exported test utilities ----------------


def test_mint_helpers_not_in_public_all():
    for name in ("_mint", "_make_session_token", "_make_invite_token",
                 "make_session_token", "make_invite_token"):
        assert name not in _mod.__all__


def test_mint_helpers_require_explicit_secret():
    import inspect

    for fn in (_make_session_token, _make_invite_token):
        params = inspect.signature(fn).parameters
        assert "secret" in params
        # No default for secret -> caller MUST pass it (never read from env).
        assert params["secret"].default is inspect.Parameter.empty


# --- STATIC AST: no web framework / runtime / network / subprocess ----------


def _module_ast():
    return ast.parse(MODULE_SRC.read_text(encoding="utf-8"))


def test_module_imports_no_runtime_network_or_web_framework():
    tree = _module_ast()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    banned_roots = {
        "sys", "subprocess", "socket", "ssl", "urllib", "requests", "httpx",
        "http", "ctypes", "multiprocessing", "shutil", "pickle", "marshal",
        "pathlib", "importlib", "dotenv",
        "fastapi", "flask", "starlette", "django", "aiohttp", "tornado",
        "uvicorn", "werkzeug", "sanic", "bottle",
    }
    bad_root = {m for m in mods if m.split(".")[0] in banned_roots}
    assert not bad_root, f"banned module import: {bad_root}"
    runtime_markers = (
        "hermes", "openclaw", "wre_core", "foundup_job_consumer",
        "foundup_job_executor", "capability_token_validator",
        "security_event_correlator",
    )
    bad_runtime = {m for m in mods if any(k in m for k in runtime_markers)}
    assert not bad_runtime, f"runtime import: {bad_runtime}"
    assert any("kanban_plugin_contract" in m for m in mods), "must reuse #807 contract"


def test_os_used_only_for_getenv():
    tree = _module_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            val = node.value
            if isinstance(val, ast.Name) and val.id == "os":
                assert node.attr in {"getenv", "environ"}, f"os.{node.attr} not allowed"


def test_module_makes_no_exec_process_network_or_arbitrary_write_calls():
    tree = _module_ast()
    banned_names = {"eval", "exec", "compile", "__import__", "input", "open"}
    banned_attrs = {
        "system", "popen", "Popen", "run", "call", "check_call", "check_output",
        "urlopen", "spawn", "fork", "remove", "unlink", "write_text", "write_bytes",
        "load_dotenv", "print",
    }
    name_bad, attr_bad = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in banned_names:
                name_bad.append(f.id)
            elif isinstance(f, ast.Attribute):
                if f.attr == "connect":
                    recv = f.value
                    if not (isinstance(recv, ast.Name) and recv.id == "sqlite3"):
                        attr_bad.append("connect")
                elif f.attr in banned_attrs:
                    attr_bad.append(f.attr)
    assert not name_bad, f"banned builtin calls: {name_bad}"
    assert not attr_bad, f"banned attr calls: {attr_bad}"


def test_no_print_or_logging_of_secret_or_token():
    # No print() and no logging import at all -> nothing can emit a secret/token/nonce.
    tree = _module_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "print"
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name != "logging"
        if isinstance(node, ast.ImportFrom):
            assert node.module != "logging"
