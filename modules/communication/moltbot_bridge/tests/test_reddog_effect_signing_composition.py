"""Connected effect approval -> one-use permit -> independent signer checks."""

from copy import deepcopy
from dataclasses import replace
import pytest

from .reddog_effect_signing_test_support import setup, reset_owner_reads
from modules.communication.moltbot_bridge.src.reddog_effect_consensus_proof import (
    VerifiedEffectSigningPermit, consume_effect_signing_permit, _receipt_id,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_client import admit_secret_grant_consensus
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import signer_secret_access_request_digest
from modules.communication.moltbot_bridge.src.reddog_elevated_consensus_signer_reservation import (
    commit_elevated_consensus_nonce,
)


def test_current_effect_seal_keeps_target_unchanged_and_is_one_use(monkeypatch, tmp_path):
    s = setup(monkeypatch, tmp_path)
    target = s.kw["target"]
    before = target.to_dict()
    permit = s.signing.prepare_permit(s.proof)
    assert type(permit) is VerifiedEffectSigningPermit
    assert not s.lease.active
    proof = admit_secret_grant_consensus(target, permit, now=s.now)
    assert proof == s.proof and target.to_dict() == before
    assert target.consensus_receipt_digest is None
    assert consume_effect_signing_permit(permit, signing_request=target, now=s.now) is None
    reset_owner_reads(s)
    reserved = s.signing.reserve(proof,
        signing_request_digest=signer_secret_access_request_digest(before), now=s.now, grant_expires_at=1020)
    assert reserved is not None
    assert commit_elevated_consensus_nonce(reserved)
    reset_owner_reads(s)
    assert s.signing.reserve(proof,
        signing_request_digest=signer_secret_access_request_digest(before), now=s.now, grant_expires_at=1020) is None


@pytest.mark.parametrize("case", ["consent", "review", "runtime", "author", "parent", "expiry", "generation", "target"])
def test_invalid_effect_approval_cannot_mint_or_reserve(monkeypatch, tmp_path, case):
    s = setup(monkeypatch, tmp_path)
    proof = deepcopy(s.proof)
    if case in {"consent", "review"}:
        item = proof["consensus_receipt"]["consent"] if case == "consent" else proof["consensus_receipt"]["decisions"][0]
        item["signature"] = "invalid"
    elif case in {"runtime", "author", "parent"}:
        name = {"runtime": "runtime_evidence_resolver", "author": "author_runtime_evidence_resolver",
                "parent": "sovereign_authorization_resolver"}[case]
        from .reddog_effect_signing_test_support import Resolver
        s.signing = replace(s.signing, **{name: Resolver(None)})
    elif case == "expiry":
        s.now = 1020
    elif case == "generation":
        s.selection["generation"] += 1
    else:
        proof["target_signing_request"]["nonce"] = "another-target"
    proof["consensus_receipt"]["receipt_id"] = _receipt_id(proof)
    assert s.signing.prepare_permit(proof) is None
    assert not s.nonces.reserved and not s.nonces.consumed


def test_constructed_permission_does_not_confer_authority(monkeypatch, tmp_path):
    s = setup(monkeypatch, tmp_path)
    assert consume_effect_signing_permit(VerifiedEffectSigningPermit(),
        signing_request=s.kw["target"], now=s.now) is None


@pytest.mark.parametrize("change", ["clock_rollback", "runtime_expiry", "owner_drift", "exit_failure"])
def test_composed_approval_fails_closed_on_lifecycle_change(monkeypatch, tmp_path, change):
    from contextlib import contextmanager
    s = setup(monkeypatch, tmp_path)
    if change == "clock_rollback":
        s.callback = lambda _: setattr(s, "now", 999)
    elif change == "runtime_expiry":
        s.runtime_records["reviewer:test"] = replace(s.runtime_records["reviewer:test"], expires_at=1001)
        s.callback = lambda _: setattr(s, "now", 1001)
    elif change == "owner_drift":
        s.callback = lambda _: s.owner.update(config_id="sha256:" + "f" * 64)
    else:
        original = s.lease._lease_current
        @contextmanager
        def failed_exit(token):
            with original(token) as selected:
                yield selected
            raise RuntimeError("synthetic cleanup failure")
        monkeypatch.setattr(s.lease, "_lease_current", failed_exit)
    assert s.signing.prepare_permit(s.proof) is None
    assert not s.lease.active and not s.nonces.consumed


def test_permission_lifetime_is_capped_by_reviewer_runtime(monkeypatch, tmp_path):
    s = setup(monkeypatch, tmp_path)
    s.runtime_records["reviewer:test"] = replace(s.runtime_records["reviewer:test"], expires_at=1001)
    permit = s.signing.prepare_permit(s.proof)
    assert permit is not None
    assert consume_effect_signing_permit(permit, signing_request=s.kw["target"], now=1001) is None


@pytest.mark.parametrize("phase", ["reserve", "commit"])
def test_expired_permission_rolls_back_nonce(monkeypatch, tmp_path, phase):
    s = setup(monkeypatch, tmp_path)
    original = s.nonces.reserve
    def reserve(*args, **kwargs):
        token = original(*args, **kwargs)
        if phase == "reserve":
            s.now = 1020
        return token
    monkeypatch.setattr(s.nonces, "reserve", reserve)
    reservation = s.signing.reserve(s.proof,
        signing_request_digest=signer_secret_access_request_digest(s.kw["target"].to_dict()), now=s.now, grant_expires_at=1020)
    if phase == "reserve":
        assert reservation is None
    else:
        assert reservation is not None
        s.now = 1020
        assert not commit_elevated_consensus_nonce(reservation)
    assert not s.nonces.reserved and not s.nonces.consumed


@pytest.mark.parametrize("expires", [None, True, 1001.0, "1001", 0, 1000, 1021])
def test_effect_signer_rejects_missing_invalid_or_excess_grant_lifetime(monkeypatch, tmp_path, expires):
    s = setup(monkeypatch, tmp_path)
    reservation = s.signing.reserve(s.proof,
        signing_request_digest=signer_secret_access_request_digest(s.kw["target"].to_dict()),
        now=s.now, grant_expires_at=expires)
    assert reservation is None
    assert not s.nonces.reserved and not s.nonces.consumed


@pytest.mark.parametrize("mode", ["expired", "current", "no_reservation"])
def test_consensus_flow_guards_actual_signing_callback(monkeypatch, mode):
    from types import SimpleNamespace
    from modules.communication.moltbot_bridge.src import reddog_ed25519_elevated_consensus_flow as flow
    monkeypatch.setattr(flow, "elevated_consensus_reservation_current", lambda _: mode == "current")
    calls = []
    def sign(*args):
        calls.append(args)
        return "signed", ""
    result = flow.sign_prepared_consensus(None if mode == "no_reservation" else object(),
        sign, "backend", SimpleNamespace(requested_operation="fixture"), "peer", ())
    assert bool(calls) is (mode != "expired")
    assert result == ((None, "REJECT_ED25519_SIGNER_REQUEST_INVALID") if mode == "expired" else ("signed", ""))
