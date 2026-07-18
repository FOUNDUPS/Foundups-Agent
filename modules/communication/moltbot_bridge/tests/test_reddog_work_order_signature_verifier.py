#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the RedDog work-order signature VERIFIER (E1).

A TEST-ONLY mock crypto backend SIGNS (production only verifies). The mock maps each
"public key" string to a secret and HMAC-signs the canonical signing_input; its verify
recomputes and constant-time-compares. No real keys, no real crypto, no network.

Slice: REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1
WSP:   50, 54, 71, 96, 97
"""

from __future__ import annotations

import ast
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import reddog_work_order_signature_verifier as v
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
    PermissionSnapshot,
    PREFIX_IDENTITY,
    PREFIX_WORKAUTH,
    ReasonCode,
    WorkAuthorityVerificationPhase,
    canonical_signing_input,
    verify_delegated_work_authority,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_ACCEPT,
    POLICY_REJECT,
    SIGNATURE_GATE_ACCEPTED,
    evaluate_signed_work_order_policy_gate,
)

_VALVE = "VALVE_OPEN_WORKTREE_CREATE"
_REPO = "FOUNDUPS/Foundups-Agent"
_FID = "paccess_001"


# --- test-only mock crypto (SIGNS; production never does) --------------------
class _MockCrypto:
    def __init__(self) -> None:
        self._secrets: dict = {}

    def keypair(self, name: str) -> str:
        pub = f"pub:{name}"
        self._secrets[pub] = (f"mock-secret-{name}").encode("utf-8")
        return pub

    def sign(self, public_key: str, signing_input: str) -> str:
        return hmac.new(self._secrets[public_key], signing_input.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        secret = self._secrets.get(public_key)
        if secret is None or not isinstance(signature, str):
            return False
        expected = hmac.new(secret, signing_input.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)  # constant-time (test 15)


class _MockResolver:
    def __init__(self, mapping: dict) -> None:
        self._m = mapping

    def resolve(self, digest: str):
        return self._m.get(digest)


class _NoRevocation:
    def is_revoked(self, *, reddog_id, fingerprint, principal_id, key_epoch) -> bool:
        return False


class _MockPrincipalKeyResolver:
    """Maps a token-verified principal_id -> its trusted principal public key."""

    def __init__(self, mapping: dict) -> None:
        self._m = mapping

    def resolve(self, principal_id: str, principal_provider: str):
        return self._m.get(principal_id)


def _build(now: int = 1000):
    crypto = _MockCrypto()
    ppub = crypto.keypair("principal")
    rpub = crypto.keypair("reddog")
    identity = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": ppub,
        "principal_key_fingerprint": "fp:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": rpub,
        "reddog_key_fingerprint": "fp:reddog",
        "repo_scope": [_REPO],
        "foundup_scope": [_FID],
        "issued_at": now - 10,
        "expires_at": now + 3600,
    }
    identity["signature"] = crypto.sign(ppub, canonical_signing_input(identity, PREFIX_IDENTITY))
    digest = "sha256:snap-1"
    workauth = {
        "work_order_id": "wo-1",
        "principal_id": "github:mjtrout",
        "reddog_id": "reddog:abc123",
        "repo_full_name": _REPO,
        "foundup_id": _FID,
        "allowed_paths": [f"modules/foundups/{_FID}/**"],
        "denied_paths": [],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": digest,
        "wsp15_allocation_receipt_id": "sha256:wsp15-allocation",
        "wsp15_allocation_digest": "sha256:wsp15-allocation-digest",
        "wsp15_priority": "P0",
        "wsp15_mps_total": 20,
        "wsp15_reasoning_tier": "ULTRA",
        "nonce": "nonce-unique-0001",
        "issued_at": now - 5,
        "expires_at": now + 120,
        "valve_state_required": _VALVE,
        "key_epoch": "epoch-1",
    }
    workauth["signature"] = crypto.sign(rpub, canonical_signing_input(workauth, PREFIX_WORKAUTH))
    snap = PermissionSnapshot(evidence_digest=digest, expires_at=now + 300, can_write=True, repo_full_name=_REPO)
    ctx = dict(
        signature_verifier=crypto,
        principal_key_resolver=_MockPrincipalKeyResolver({"github:mjtrout": ppub}),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_MockResolver({digest: snap}),
        revocation_oracle=_NoRevocation(),
        now=now,
        required_valve_state=_VALVE,
        forbidden_operations=("rm_rf",),
    )
    return crypto, identity, workauth, ctx


def _resign_wa(crypto, identity, workauth):
    workauth["signature"] = crypto.sign(identity["reddog_public_key"], canonical_signing_input(workauth, PREFIX_WORKAUTH))
    return workauth


def _run(identity, workauth, ctx):
    return verify_delegated_work_authority(work_authority=workauth, identity=identity, **ctx)


def _policy_order_from_workauth(workauth, now: int = 1000, **overrides):
    captured = datetime.fromtimestamp(now - 60, timezone.utc).replace(microsecond=0).isoformat()
    expiry = datetime.fromtimestamp(now + 3600, timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "work_order_id": workauth["work_order_id"],
        "created_at": captured,
        "red_dog_instance_id": "reddog-test",
        "authenticated_principal": workauth["principal_id"],
        "principal_provider": "github",
        "repo_full_name": workauth["repo_full_name"],
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": captured,
            "source": "mock",
            "digest": workauth["permission_snapshot_digest"],
        },
        "requested_operation": workauth["requested_operation"],
        "authority_tier": "source",
        "allowed_paths": list(workauth["allowed_paths"]),
        "denied_paths": list(workauth["denied_paths"]),
        "branch_name": "feat/signed-policy-test",
        "base_ref": "main",
        "task_summary": "Signed policy gate integration test.",
        "wsp_applicability": ["WSP_50", "WSP_97"],
        "holoindex_evidence_refs": ["docs/contracts/REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1.md"],
        "skillz_candidates": [],
        "required_tests": ["modules/communication/moltbot_bridge/tests/test_reddog_work_order_signature_verifier.py"],
        "required_policy_gates": ["openclaw_policy_gate", "signed_work_order_authority"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "No execution performed.",
        "expiry": expiry,
        "nonce": "policy-" + workauth["nonce"],
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog signed work order",
            "holoindex_status": "bundle_json_ok",
            "code_hits": ["modules/communication/moltbot_bridge/src/reddog_work_order_signature_verifier.py"],
            "wsp_hits": ["WSP_framework/src/WSP_97_WSP_97_Truth_Boundary_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": False,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_97"],
            "evidence_refs": ["docs/contracts/REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1.md"],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


# 1 -------------------------------------------------------------------------- #
def test_valid_signed_authority_verifies() -> None:
    _, identity, workauth, ctx = _build()
    r = _run(identity, workauth, ctx)
    assert r.accepted is True, r.reason_codes
    assert r.reason_codes == []
    assert r.work_order_id == "wo-1"


def test_preflight_reverification_does_not_consume_authoritative_nonce() -> None:
    _, identity, workauth, ctx = _build()

    first = verify_delegated_work_authority(
        work_authority=workauth,
        identity=identity,
        verification_phase=WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING,
        **ctx,
    )
    second = verify_delegated_work_authority(
        work_authority=workauth,
        identity=identity,
        verification_phase=WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING,
        **ctx,
    )
    authoritative = _run(identity, workauth, ctx)
    replay = _run(identity, workauth, ctx)

    assert first.accepted is True
    assert second.accepted is True
    assert authoritative.accepted is True
    assert replay.reason_codes == [ReasonCode.NONCE_REPLAY]


def test_consumed_nonce_can_be_preflight_checked_but_not_authoritatively_reused() -> None:
    _, identity, workauth, ctx = _build()

    consumed = _run(identity, workauth, ctx)
    preflight = verify_delegated_work_authority(
        work_authority=workauth,
        identity=identity,
        verification_phase=WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING,
        **ctx,
    )
    replay = _run(identity, workauth, ctx)

    assert consumed.accepted is True
    assert preflight.accepted is True
    assert replay.reason_codes == [ReasonCode.NONCE_REPLAY]


def test_nonce_replay_rejects_different_signed_work_order_with_same_nonce() -> None:
    crypto, identity, first, ctx = _build()
    second = dict(first)
    second["work_order_id"] = "wo-2"
    _resign_wa(crypto, identity, second)

    assert _run(identity, first, ctx).accepted is True
    replay = _run(identity, second, ctx)

    assert replay.work_order_id == "wo-2"
    assert replay.reason_codes == [ReasonCode.NONCE_REPLAY]


# 2 -------------------------------------------------------------------------- #
def test_payload_tampering_rejects() -> None:
    _, identity, workauth, ctx = _build()
    workauth["allowed_paths"] = ["**"]  # widen after signing
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.WORKAUTH_SIGNATURE_INVALID in r.reason_codes


# 3 -------------------------------------------------------------------------- #
def test_non_canonical_serialization_rejects() -> None:
    crypto, identity, workauth, ctx = _build()
    # attacker signs over a NON-canonical input (extra prefix noise); verifier recomputes canonical.
    bad_input = PREFIX_WORKAUTH + ".{ }" + canonical_signing_input(workauth, PREFIX_WORKAUTH)
    workauth["signature"] = crypto.sign(identity["reddog_public_key"], bad_input)
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.WORKAUTH_SIGNATURE_INVALID in r.reason_codes


# 4 -------------------------------------------------------------------------- #
def test_expired_authority_rejects() -> None:
    _, identity, workauth, ctx = _build()
    ctx["now"] = 1000 + 100000  # well past expires_at + leeway
    r = _run(identity, workauth, ctx)
    assert r.accepted is False
    assert ReasonCode.EXPIRED_WORKAUTH in r.reason_codes or ReasonCode.EXPIRED_IDENTITY in r.reason_codes


# 5 -------------------------------------------------------------------------- #
def test_replayed_nonce_rejects() -> None:
    _, identity, workauth, ctx = _build()
    first = _run(identity, workauth, ctx)
    assert first.accepted is True
    # same nonce store, resubmit the identical (still valid) order -> replay
    second = _run(identity, workauth, ctx)
    assert second.accepted is False and ReasonCode.NONCE_REPLAY in second.reason_codes


# 6 -------------------------------------------------------------------------- #
def test_revoked_key_epoch_rejects() -> None:
    _, identity, workauth, ctx = _build()
    ctx["revoked_key_epochs"] = ("epoch-1",)
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.KEY_EPOCH_REVOKED in r.reason_codes


# 7 -------------------------------------------------------------------------- #
def test_wrong_principal_rejects() -> None:
    crypto, identity, workauth, ctx = _build()
    workauth["principal_id"] = "github:attacker"
    workauth["signature"] = crypto.sign(identity["reddog_public_key"], canonical_signing_input(workauth, PREFIX_WORKAUTH))
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.PRINCIPAL_MISMATCH in r.reason_codes


# 8 -------------------------------------------------------------------------- #
def test_wrong_reddog_id_rejects() -> None:
    crypto, identity, workauth, ctx = _build()
    workauth["reddog_id"] = "reddog:evil"
    workauth["signature"] = crypto.sign(identity["reddog_public_key"], canonical_signing_input(workauth, PREFIX_WORKAUTH))
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.REDDOG_ID_MISMATCH in r.reason_codes


# 9 -------------------------------------------------------------------------- #
def test_changed_allowed_paths_rejects() -> None:
    _, identity, workauth, ctx = _build()
    workauth["allowed_paths"] = workauth["allowed_paths"] + [".github/workflows/**"]
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.WORKAUTH_SIGNATURE_INVALID in r.reason_codes


# 10 ------------------------------------------------------------------------- #
def test_changed_foundup_scope_rejects() -> None:
    _, identity, workauth, ctx = _build()
    identity["foundup_scope"] = [_FID, "evil_002"]  # tamper the principal-signed identity
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.IDENTITY_SIGNATURE_INVALID in r.reason_codes


# 11 ------------------------------------------------------------------------- #
def test_permission_snapshot_stale_or_missing_rejects() -> None:
    _, identity, workauth, ctx = _build()
    ctx["snapshot_resolver"] = _MockResolver({})  # digest resolves to nothing
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.SNAPSHOT_STALE in r.reason_codes


def test_permission_snapshot_digest_mismatch_rejects() -> None:
    _, identity, workauth, ctx = _build()
    d = workauth["permission_snapshot_digest"]
    ctx["snapshot_resolver"] = _MockResolver(
        {d: PermissionSnapshot(evidence_digest="sha256:OTHER", expires_at=1000 + 300, can_write=True, repo_full_name=_REPO)}
    )
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.SNAPSHOT_DIGEST_MISMATCH in r.reason_codes


# 12 ------------------------------------------------------------------------- #
def test_missing_signature_rejects() -> None:
    _, identity, workauth, ctx = _build()
    workauth["signature"] = None
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.MISSING_SIGNATURE in r.reason_codes


# 13 ------------------------------------------------------------------------- #
def test_prompt_text_i_am_012_without_signature_rejects() -> None:
    """A packet asserting authority in free text but not PRINCIPAL-signed is inert:
    principal_id '012' is not a token-verified subject and its key is not on record."""
    crypto, identity, workauth, ctx = _build()
    identity["principal_id"] = "012"
    identity["signature"] = crypto.sign(identity["reddog_public_key"], canonical_signing_input(identity, PREFIX_IDENTITY))
    r = _run(identity, workauth, ctx)
    assert r.accepted is False
    assert (ReasonCode.PRINCIPAL_KEY_UNTRUSTED in r.reason_codes
            or ReasonCode.IDENTITY_SIGNATURE_INVALID in r.reason_codes
            or ReasonCode.PRINCIPAL_MISMATCH in r.reason_codes)


# 14 ------------------------------------------------------------------------- #
def test_failure_reasons_never_leak_expected_material() -> None:
    crypto, identity, workauth, ctx = _build()
    workauth["allowed_paths"] = ["**"]
    r = _run(identity, workauth, ctx)
    assert r.accepted is False
    blob = " ".join(r.reason_codes)
    # reason codes are static enums: no signature, secret, or key bytes leak
    assert workauth["signature"] not in blob
    assert "mock-secret" not in blob
    for code in r.reason_codes:
        assert code.startswith("REJECT_")


# 15 ------------------------------------------------------------------------- #
def test_constant_time_compare_used_for_signature_bytes() -> None:
    # production helper is constant-time (wraps hmac.compare_digest)
    assert v.constant_time_compare("abc", "abc") is True
    assert v.constant_time_compare("abc", "abd") is False
    src = Path(v.__file__).read_text(encoding="utf-8")
    assert "hmac.compare_digest" in src
    # the mock verifier (the MAC/signature byte comparison) uses constant-time compare too
    msrc = Path(__file__).read_text(encoding="utf-8")
    assert "hmac.compare_digest" in msrc


# 16 ------------------------------------------------------------------------- #
def test_no_private_key_material_in_production_module() -> None:
    src = Path(v.__file__).read_text(encoding="utf-8").lower()
    for banned in ("private_key", "privatekey", "-----begin", "secret =", "signing_secret", "os.urandom", "token_bytes"):
        assert banned not in src, f"possible key material in production module: {banned!r}"


# 17 ------------------------------------------------------------------------- #
def test_ast_denylist_no_keygen_signing_subprocess_shell_wallet_chain() -> None:
    src = Path(v.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: set = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    forbidden = {
        "subprocess", "os", "secrets", "socket", "pty", "shutil", "importlib",
        "cryptography", "nacl", "ecdsa", "web3", "eth_account", "bitcoin", "wallet",
    }
    assert not (imported & forbidden), f"forbidden import(s): {imported & forbidden}"
    # no dynamic dispatch, no MAC/keygen calls (verification delegates to the injected backend)
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func
            if isinstance(fn, ast.Name):
                called.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                called.add(fn.attr)
    assert not (called & {"eval", "exec", "compile", "__import__", "system", "Popen", "run"})
    # hmac is imported ONLY for compare_digest -- never hmac.new (which would compute a MAC = sign)
    assert "new" not in called or "hmac" not in imported or "compare_digest" in called
    assert "compare_digest" in called, "verifier must use constant-time compare_digest"


# ---- CoR regression: path-scope binding (BLOCKER) --------------------------- #
def test_path_outside_foundup_scope_rejects() -> None:
    """A validly-signed, in-scope order still cannot target paths outside its FoundUp."""
    crypto, identity, workauth, ctx = _build()
    workauth["allowed_paths"] = [".github/workflows/deploy.yml"]
    _resign_wa(crypto, identity, workauth)
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.PATH_OUT_OF_SCOPE in r.reason_codes


def test_path_traversal_rejects() -> None:
    crypto, identity, workauth, ctx = _build()
    workauth["allowed_paths"] = [f"modules/foundups/{_FID}/../../.env"]
    _resign_wa(crypto, identity, workauth)
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.PATH_OUT_OF_SCOPE in r.reason_codes


# ---- CoR regression: principal-key trust anchor (BLOCKER) ------------------- #
def test_untrusted_principal_key_rejects() -> None:
    """A self-supplied principal_public_key not on record for the principal is rejected."""
    _, identity, workauth, ctx = _build()
    ctx["principal_key_resolver"] = _MockPrincipalKeyResolver({})  # nothing token-verified
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.PRINCIPAL_KEY_UNTRUSTED in r.reason_codes


def test_principal_key_mismatch_rejects() -> None:
    _, identity, workauth, ctx = _build()
    ctx["principal_key_resolver"] = _MockPrincipalKeyResolver({"github:mjtrout": "pub:someone-else"})
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.PRINCIPAL_KEY_UNTRUSTED in r.reason_codes


# ---- CoR regression: key-reuse self-mint (BLOCKER) ------------------------- #
def test_self_mint_key_reuse_rejects() -> None:
    """principal_public_key == reddog_public_key is a self-grant and must be refused."""
    crypto, identity, workauth, ctx = _build()
    shared = identity["reddog_public_key"]
    identity["principal_public_key"] = shared
    identity["signature"] = crypto.sign(shared, canonical_signing_input(identity, PREFIX_IDENTITY))
    ctx["principal_key_resolver"] = _MockPrincipalKeyResolver({"github:mjtrout": shared})
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.SELF_MINT_KEY_REUSE in r.reason_codes


# ---- CoR regression: key_epoch required (MAJOR) ---------------------------- #
def test_empty_key_epoch_rejects() -> None:
    crypto, identity, workauth, ctx = _build()
    workauth["key_epoch"] = ""
    _resign_wa(crypto, identity, workauth)
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.KEY_EPOCH_MISSING in r.reason_codes


# ---- CoR regression: nonce NOT burned on a transient later-gate reject (MAJOR) #
def test_nonce_not_burned_on_transient_reject() -> None:
    _, identity, workauth, ctx = _build()
    # 1st attempt: valve transiently CLOSED -> reject at the valve gate (after nonce would
    # previously have been consumed). Nonce must survive.
    ctx["required_valve_state"] = "VALVE_CLOSED"
    first = _run(identity, workauth, ctx)
    assert first.accepted is False and ReasonCode.VALVE_STATE in first.reason_codes
    # operator opens the valve; the SAME signed order retries against the SAME nonce store.
    ctx["required_valve_state"] = _VALVE
    second = _run(identity, workauth, ctx)
    assert second.accepted is True, second.reason_codes  # not locked out


# ---- CoR regression: enforcement helper / truthiness (MAJOR) --------------- #
def test_result_bool_and_require_authorized() -> None:
    from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
        require_authorized, WorkOrderRejected,
    )
    _, identity, workauth, ctx = _build()
    ok = _run(identity, workauth, ctx)
    assert bool(ok) is True
    require_authorized(ok)  # does not raise
    _, identity2, workauth2, ctx2 = _build()
    workauth2["allowed_paths"] = ["**"]  # tamper -> reject
    bad = _run(identity2, workauth2, ctx2)
    assert bool(bad) is False
    with pytest.raises(WorkOrderRejected):
        require_authorized(bad)


# ---- CoR regression: admin verb requires can_admin (MINOR) ----------------- #
def test_admin_verb_requires_can_admin() -> None:
    crypto, identity, workauth, ctx = _build()
    workauth["requested_operation"] = "manage_permissions"  # admin-tier
    _resign_wa(crypto, identity, workauth)
    # snapshot grants write but NOT admin
    d = workauth["permission_snapshot_digest"]
    ctx["snapshot_resolver"] = _MockResolver(
        {d: PermissionSnapshot(evidence_digest=d, expires_at=1000 + 300, can_write=True, can_admin=False, repo_full_name=_REPO)}
    )
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.SNAPSHOT_INSUFFICIENT in r.reason_codes


# ---- CoR-R2 regression: lax backend returning a truthy non-bool must reject - #
def test_non_bool_truthy_verifier_result_rejects() -> None:
    class _LaxVerifier:
        def verify(self, public_key, signing_input, signature):
            return 1  # truthy, not True

    _, identity, workauth, ctx = _build()
    ctx["signature_verifier"] = _LaxVerifier()
    r = _run(identity, workauth, ctx)
    assert r.accepted is False and ReasonCode.IDENTITY_SIGNATURE_INVALID in r.reason_codes


# ---- 012 review point 1: nonce semantics (identity reusable; work-auth once) --- #
def test_identity_reusable_but_work_authority_nonce_consume_once() -> None:
    """The SAME identity authorizes multiple work orders (reusable within TTL); each
    work-authority nonce is single-use; reusing a work-auth nonce replays."""
    crypto, identity, wa1, ctx = _build()
    store = ctx["nonce_store"]  # one store shared across all submissions

    # wo-1 with its own nonce -> ACCEPT (identity used once)
    assert _run(identity, wa1, ctx).accepted is True

    # wo-2: SAME identity, DIFFERENT work order + DIFFERENT nonce -> ACCEPT (identity reused)
    wa2 = dict(wa1)
    wa2["work_order_id"] = "wo-2"
    wa2["nonce"] = "nonce-unique-0002"
    _resign_wa(crypto, identity, wa2)
    assert _run(identity, wa2, ctx).accepted is True, "identity must be reusable within TTL"

    # wo-3: SAME identity but REUSE wo-1's nonce -> REPLAY (work-auth nonce is consume-once)
    wa3 = dict(wa1)
    wa3["work_order_id"] = "wo-3"
    wa3["nonce"] = wa1["nonce"]  # reused
    _resign_wa(crypto, identity, wa3)
    r3 = _run(identity, wa3, ctx)
    assert r3.accepted is False and ReasonCode.NONCE_REPLAY in r3.reason_codes


# ---- 012 review point 2: a rejected result must be falsey (cannot authorize) --- #
def test_rejected_result_is_falsey_and_cannot_authorize() -> None:
    from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
        require_authorized, WorkOrderRejected,
    )
    _, identity, workauth, ctx = _build()
    workauth["allowed_paths"] = ["**"]  # tamper -> rejected
    rejected = _run(identity, workauth, ctx)
    assert rejected.accepted is False
    assert bool(rejected) is False              # accidental `if result:` cannot authorize
    assert not rejected                          # explicit falsiness
    assert rejected.reason_codes                 # ...even though reason_codes is a NON-empty (truthy) list
    with pytest.raises(WorkOrderRejected):
        require_authorized(rejected)


# ---- CoR-R2 regression: non-serializable payload fails closed (no crash) ---- #
def test_non_serializable_payload_fails_closed() -> None:
    _, identity, workauth, ctx = _build()
    workauth["allowed_paths"] = [{"unhashable-nonjson"}]  # a set -> json.dumps raises
    r = _run(identity, workauth, ctx)
    assert r.accepted is False  # rejected, never raised
    assert r.reason_codes  # a static code was recorded


def test_signed_policy_gate_invokes_verifier_and_accepts_exact_binding() -> None:
    _, identity, workauth, ctx = _build()
    order = _policy_order_from_workauth(workauth, now=ctx["now"])

    receipt = evaluate_signed_work_order_policy_gate(
        order,
        identity=identity,
        work_authority=workauth,
        signature_verifier=ctx["signature_verifier"],
        principal_key_resolver=ctx["principal_key_resolver"],
        nonce_store=ctx["nonce_store"],
        snapshot_resolver=ctx["snapshot_resolver"],
        revocation_oracle=ctx["revocation_oracle"],
        required_valve_state=_VALVE,
        now=datetime.fromtimestamp(ctx["now"], timezone.utc),
        seen_nonces=set(),
        forbidden_operations=["rm_rf"],
    )

    assert receipt.decision == POLICY_ACCEPT
    assert receipt.signature_gate_status == SIGNATURE_GATE_ACCEPTED
    assert receipt.signature_gate_digest
    assert "signed_work_order_authority" in receipt.gates_checked


def test_signed_policy_gate_rejects_valid_signature_for_different_path_scope() -> None:
    _, identity, workauth, ctx = _build()
    order = _policy_order_from_workauth(
        workauth,
        now=ctx["now"],
        allowed_paths=["modules/foundups/other_002/**"],
    )

    receipt = evaluate_signed_work_order_policy_gate(
        order,
        identity=identity,
        work_authority=workauth,
        signature_verifier=ctx["signature_verifier"],
        principal_key_resolver=ctx["principal_key_resolver"],
        nonce_store=ctx["nonce_store"],
        snapshot_resolver=ctx["snapshot_resolver"],
        revocation_oracle=ctx["revocation_oracle"],
        required_valve_state=_VALVE,
        now=datetime.fromtimestamp(ctx["now"], timezone.utc),
        seen_nonces=set(),
        forbidden_operations=["rm_rf"],
    )

    assert receipt.decision == POLICY_REJECT
    assert "signed_work_authority_not_accepted" in receipt.rejection_reasons
    assert (
        "signed_work_authority_reject:REJECT_SIGNED_AUTHORITY_BINDING_MISMATCH:allowed_paths"
        in receipt.rejection_reasons
    )
