"""Additional rollback and lifecycle tests for root revocation RPC."""

from __future__ import annotations

import ast
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_client as root_client_module,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_router import (
    handle_root_authority_wire_request,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
    MAX_MESSAGE_BYTES,
    OP_ADVANCE,
    RootRevocationResponse,
    request_from_bytes,
    request_id_for,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.tests import (
    test_reddog_signer_owner_controlled_e0_admission as e0,
)
from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import (
    runtime,
    signed_snapshot,
    stage,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import (
    _peer,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_revocation_service import (
    _handle,
    _request,
)


def test_owner_generation_rotation_rejects_current_request(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    request = _request(values)
    e0._CURRENT_SELECTION["generation_revision"] = "attacker-rotation"
    assert _handle(values, request).accepted is False


def test_missing_witness_and_tampered_snapshot_reject_without_anchor(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    candidate = signed_snapshot(values)
    values["store"]._prepare_under_lock(candidate)
    with pytest.raises(ValueError, match="request_rejected"):
        values["client"].advance_snapshot(candidate["snapshot_id"])
    assert values["state"].load(
        values["binding"].anchor_binding_digest()
    ) is None

    values = runtime(tmp_path / "tampered", monkeypatch)
    candidate = signed_snapshot(values)
    candidate["revoked_key_epochs"] = ["attacker-epoch"]
    values["store"]._prepare_under_lock(candidate)
    high = ProposalReplayHighWater(1, str(candidate["snapshot_id"])[7:])
    values["witness"].advance(
        values["binding"].witness_binding_digest(),
        expected=None,
        next_value=high,
    )
    with pytest.raises(ValueError, match="request_rejected"):
        values["client"].advance_snapshot(candidate["snapshot_id"])
    assert values["state"].load(
        values["binding"].anchor_binding_digest()
    ) is None


def test_root_state_must_be_disjoint_from_local_revocation_domains(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch, overlap_root=True)
    assert _handle(values, _request(values)).accepted is False


def test_response_snapshot_must_equal_high_water_revision() -> None:
    response = RootRevocationResponse(
        status="ACCEPT", request_id=e0.DIGEST_A,
        descriptor_id=e0.DIGEST_B, owner_config_id=e0.DIGEST_C,
        policy_id=e0.DIGEST_D, binding_digest=e0.DIGEST_E,
        snapshot_id=e0.DIGEST_A, state="LOADED", sequence=1,
        revision="b" * 64,
    )
    with pytest.raises(ValueError, match="response_invalid"):
        response.to_bytes()

def test_old_snapshot_replay_rejects_after_later_advance(tmp_path, monkeypatch) -> None:
    values = runtime(tmp_path, monkeypatch)
    first = signed_snapshot(values)
    stage(values, first)
    values["client"].advance_snapshot(first["snapshot_id"])
    values["store"]._finalize_under_lock(first["snapshot_id"])
    second = signed_snapshot(values, sequence=2)
    stage(values, second)
    current = values["client"].advance_snapshot(second["snapshot_id"])
    values["store"]._finalize_under_lock(second["snapshot_id"])
    with pytest.raises(ValueError, match="request_rejected"):
        values["client"].advance_snapshot(first["snapshot_id"])
    assert values["state"].load(
        values["binding"].anchor_binding_digest()
    ) == current


def test_request_nonce_is_signed_unique_and_strict(tmp_path, monkeypatch) -> None:
    values = runtime(tmp_path, monkeypatch)
    raw_requests = []
    valid_exchange = values["exchange"]

    def capture(_path, raw, _uid, _timeout):
        raw_requests.append(request_from_bytes(raw))
        return valid_exchange(raw)

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", capture)
    assert values["client"].load() is None
    assert values["client"].load() is None
    assert raw_requests[0].request_nonce != raw_requests[1].request_nonce
    malformed = replace(
        raw_requests[0], request_nonce="z" * 64,
        request_id="sha256:" + "0" * 64,
    )
    malformed = replace(malformed, request_id=request_id_for(asdict(malformed)))
    with pytest.raises(ValueError, match="request_invalid"):
        malformed.to_bytes()
    with pytest.raises(ValueError, match="message_invalid"):
        request_from_bytes(b"x" * (MAX_MESSAGE_BYTES + 1))
    raw = raw_requests[0].to_bytes().decode("ascii")
    duplicate = raw.replace(
        '"operation":', '"operation":"REVOCATION_ANCHOR_LOAD","operation":', 1
    ).encode("ascii")
    with pytest.raises(ValueError, match="duplicate_key"):
        request_from_bytes(duplicate)


def test_router_rejects_revocation_when_authority_not_composed(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    response = handle_root_authority_wire_request(
        _request(values).to_bytes(),
        peer=_peer(),
        state=values["state"],
        snapshot_supplier=lambda: values["snapshot"],
        revocation_authority=None,
        now_epoch=1,
    )
    assert response == b'{"status":"REJECT"}\n'


def test_root_revocation_slice_obeys_wsp62_boundaries() -> None:
    root = Path(__file__).resolve().parents[1]
    files = [
        *(root / "src").glob("foundup_verified_outcome_root_revocation_*.py"),
        root / "src" / "foundup_verified_outcome_root_authority_router.py",
        root / "src" / "foundup_verified_outcome_root_authority_wire_codec.py",
        root / "src" / "foundup_verified_outcome_root_runtime_materializer.py",
        root / "src" / "reddog_signer_owner_e0_current_selection.py",
        root / "tests" / "root_revocation_service_fixtures.py",
        root / "tests" / "root_revocation_service_topology_fixture.py",
        root / "tests" / "root_revocation_snapshot_fixture.py",
        root / "tests" / "root_revocation_linux_socket_fixture.py",
        root / "tests" / "durable_revocation_anchor_client_fixture.py",
        Path(__file__),
        root / "tests" / "test_foundup_verified_outcome_root_revocation_linux.py",
        root / "tests" / "test_foundup_verified_outcome_root_revocation_service.py",
        root / "tests" / "test_foundup_verified_outcome_root_revocation_identity.py",
    ]
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 200, path
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 50, (
                    path,
                    node.name,
                )
    assert len((root / "src" / "reddog_signer_system_service_manifest_selection_loader.py").read_text(encoding="utf-8").splitlines()) <= 675
    assert len((root / "tests" / "test_reddog_signer_secret_grant_revocation_durable_authority.py").read_text(encoding="utf-8").splitlines()) <= 801
    assert len((root / "INTERFACE.md").read_text(encoding="utf-8").splitlines()) <= 1511
