"""Security regressions for the root revocation-anchor service boundary."""

from __future__ import annotations

import copy
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_client as root_client_module,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_authority import (
    RootRevocationServiceAuthority,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
    RootRevocationAnchorAuthority,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
    OP_ADVANCE,
    OP_LOAD,
    RootRevocationRequest,
    canonical_signer_input,
    request_id_for,
    response_from_bytes,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_service import (
    handle_root_revocation_request,
)
from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import (
    runtime,
    signed_snapshot,
    stage,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _sha,
    _sign,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import (
    _peer,
)


def _request(
    values,
    *,
    operation=OP_LOAD,
    snapshot_id=None,
    issued_at=None,
    policy=None,
    binding_digest=None,
):
    client_state = __import__(
        "modules.communication.moltbot_bridge.src."
        "foundup_verified_outcome_root_revocation_client",
        fromlist=["_lookup_client"],
    )._lookup_client(values["client"])
    request = RootRevocationRequest(
        operation=operation,
        request_id="sha256:" + "0" * 64,
        request_nonce="a" * 64,
        descriptor_id=str(values["snapshot"].descriptor["descriptor_id"]),
        owner_config_id=str(values["policy"]["owner_config_id"]),
        policy_id=str(values["policy"]["policy_id"]),
        binding_digest=binding_digest or values["binding"].anchor_binding_digest(),
        policy=policy or dict(client_state.policy),
        snapshot_id=snapshot_id,
        issued_at=issued_at or int(time.time()),
        signer_instance_signature="ed25519-sig-v1:" + "A" * 86,
    )
    request = replace(
        request,
        signer_instance_signature=_sign(
            values["target_private"], canonical_signer_input(request)
        ),
    )
    return replace(request, request_id=request_id_for(asdict(request)))


def _handle(values, request, *, peer=None):
    return response_from_bytes(
        handle_root_revocation_request(
            request.to_bytes(),
            peer=peer or _peer(),
            state=values["state"],
            snapshot_supplier=lambda: values["snapshot"],
            revocation_authority=values["server_authority"],
            now_epoch=int(time.time()),
        )
    )


def test_load_advance_and_lost_response_retry_are_idempotent(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    assert values["client"].load() is None
    candidate = signed_snapshot(values)
    stage(values, candidate)
    wanted = values["client"].advance_snapshot(candidate["snapshot_id"])
    assert wanted.sequence == 1
    assert values["client"].advance_snapshot(candidate["snapshot_id"]) == wanted
    binding = values["binding"].anchor_binding_digest()
    assert values["state"].load(binding) == wanted


def test_two_concurrent_exact_requests_converge_once(tmp_path, monkeypatch) -> None:
    values = runtime(tmp_path, monkeypatch)
    candidate = signed_snapshot(values)
    stage(values, candidate)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _index: values["client"].advance_snapshot(candidate["snapshot_id"]),
            range(2),
        ))
    assert results[0] == results[1]
    assert values["state"].load(
        values["binding"].anchor_binding_digest()
    ) == results[0]


@pytest.mark.parametrize("mutation", ["binding", "policy", "snapshot"])
def test_attacker_selected_context_rejects_without_root_mutation(
    tmp_path, monkeypatch, mutation
) -> None:
    values = runtime(tmp_path, monkeypatch)
    candidate = signed_snapshot(values)
    stage(values, candidate)
    policy = dict(values["policy"])
    binding = values["binding"].anchor_binding_digest()
    snapshot_id = candidate["snapshot_id"]
    if mutation == "binding":
        binding = _sha("attacker-binding")
    elif mutation == "policy":
        policy["rate_limit_max_requests"] += 1
    else:
        snapshot_id = _sha("attacker-snapshot")
    response = _handle(values, _request(
        values, operation=OP_ADVANCE, snapshot_id=snapshot_id,
        policy=policy, binding_digest=binding,
    ))
    assert response.accepted is False
    assert values["state"].load(
        values["binding"].anchor_binding_digest()
    ) is None


def test_forged_cross_operation_stale_and_wrong_peer_reject(tmp_path, monkeypatch) -> None:
    values = runtime(tmp_path, monkeypatch)
    load = _request(values)
    forged = replace(
        load, signer_instance_signature="ed25519-sig-v1:" + "B" * 86,
        request_id="sha256:" + "0" * 64,
    )
    forged = replace(forged, request_id=request_id_for(asdict(forged)))
    cross = replace(
        load, operation=OP_ADVANCE, snapshot_id=_sha("candidate"),
        request_id="sha256:" + "0" * 64,
    )
    cross = replace(cross, request_id=request_id_for(asdict(cross)))
    stale = _request(values, issued_at=int(time.time()) - 31)
    assert _handle(values, forged).accepted is False
    assert _handle(values, cross).accepted is False
    assert _handle(values, stale).accepted is False
    assert _handle(values, load, peer=_peer(uid=1002)).accepted is False


def test_response_substitution_and_fabricated_capabilities_reject(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    valid_exchange = values["exchange"]

    def substitute(_path, raw, _uid, _timeout):
        response = response_from_bytes(valid_exchange(raw))
        return replace(response, request_id=_sha("other-request")).to_bytes()

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", substitute)
    with pytest.raises(ValueError, match="request_rejected"):
        values["client"].load()
    with pytest.raises(TypeError):
        RootRevocationAnchorAuthority()
    with pytest.raises(TypeError):
        RootRevocationServiceAuthority()
    with pytest.raises(TypeError):
        copy.copy(values["client"])
    with pytest.raises(TypeError):
        copy.deepcopy(values["client"])
    with pytest.raises(TypeError):
        pickle.dumps(values["client"])
