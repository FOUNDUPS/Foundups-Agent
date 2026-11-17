"""Initial control bootstrap; synthetic installation, real signatures and stores."""
import copy
import time
from dataclasses import replace

import pytest
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import descriptor_id_for
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import validated_root_authority_snapshot
from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_authority_client as root_client_module
from modules.communication.moltbot_bridge.tests import root_revocation_service_fixtures as fixture_owner
from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import runtime
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _sign
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import _peer
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_revocation_service import _handle, _request


def initial_control_runtime(tmp_path, monkeypatch):
    """Synthetic installed selection; real disposable signed E0, stores and RPC codec.

    No work grant reaches initialization. OS custody/transport remain fixture seams.
    """
    from modules.communication.moltbot_bridge.tests.test_reddog_signer_installed_policy import _installed
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _private_key, _public_text
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import descriptor_id_for
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_router import handle_root_authority_wire_request

    original_policy, original_selection, original_descriptor = e0._policy, e0._fixture_selection, fixture_owner._descriptor
    control = _private_key()

    def policy(**kwargs):
        value = original_policy(**kwargs)
        template = _installed()
        value.update({key: item for key, item in template.items() if key not in value})
        value.update(schema_version=template["schema_version"], generation=1,
            allowed_operations=["signer_socket_peer_handshake"],
            allowed_authority_tiers=["LOW"], consensus_required_tiers=[])
        return value

    def selection(*args):
        return dict(original_selection(*args), generation=1)

    def descriptor(*args, **kwargs):
        body, grant, store = original_descriptor(*args, **kwargs)
        body.update(schema_version="foundup_verified_outcome_root_authority.v2", grants=[],
            authority_tier="LOW", consensus_receipt_digest=None,
            root_control_authentication={"purpose": "protected-use-acquire-finish.v1",
                "public_key": _public_text(control), "key_epoch": "control-initial"})
        body["descriptor_id"] = descriptor_id_for(body)
        return body, grant, store

    monkeypatch.setattr(e0, "_policy", policy)
    monkeypatch.setattr(e0, "_fixture_selection", selection)
    monkeypatch.setattr(fixture_owner, "_descriptor", descriptor)
    values = runtime(tmp_path, monkeypatch)
    values["control_private"] = control

    def route(_path, raw, _uid, _timeout):
        return handle_root_authority_wire_request(raw, peer=_peer(), state=values["state"],
            snapshot_supplier=lambda: values["snapshot"],
            revocation_authority=values["server_authority"], now_epoch=int(time.time()))

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", route)
    return values


# Initial control uses disposable signed E0 and real stores. Selection, filesystem
# custody and socket peer are synthetic boundaries, never native enrollment proof.
@pytest.fixture
def initial_control(tmp_path, monkeypatch):
    return initial_control_runtime(tmp_path, monkeypatch)


def _initial_client(values, kind, descriptor=None, policy=None, **changes):
    import time
    from modules.communication.moltbot_bridge.src import (
        foundup_verified_outcome_root_revocation_client as revocation,
        foundup_verified_outcome_root_protected_use_client as protected,
    )
    factory = (revocation._create_root_revocation_anchor_authority if kind == "load"
               else protected._create_root_protected_use_authority)
    private = values["target_private"] if kind == "load" else values["control_private"]
    kwargs = dict(owner_config_id=values["policy"]["owner_config_id"],
        policy=policy or values["policy"], binding=values["binding"],
        exchange=revocation._lookup_client(values["client"]).exchange,
        request_signer=lambda text: _sign(private, text), now_epoch=int(time.time()))
    kwargs.update(changes)
    return factory(descriptor or values["snapshot"].descriptor, **kwargs)


def _protected_action(client, values, action):
    import time
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _sha
    return client.authorize_use(grant_id=_sha("synthetic-low-grant"),
        key_epoch=values["policy"]["target_signer_key_epoch"],
        signing_request_digest=_sha("synthetic-handshake-request"),
        grant_expires_at=int(time.time()) + 30, action=action)


def test_empty_v2_initializes_loads_advances_and_protects_use(initial_control):
    from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import signed_snapshot, stage
    values = initial_control
    assert values["snapshot"].descriptor["grants"] == []
    client = _initial_client(values, "load")
    assert client.load() is None
    candidate = signed_snapshot(values)
    stage(values, candidate)
    high = client.advance_snapshot(candidate["snapshot_id"])
    assert high.sequence == 1
    assert client.advance_snapshot(candidate["snapshot_id"]) == high
    values["store"]._finalize_under_lock(candidate["snapshot_id"])
    assert client.load() == high
    assert _protected_action(_initial_client(values, "protected"), values, lambda: "used") == "used"
    with pytest.raises(ValueError, match="verified_outcome_root_consensus_invalid"):
        validated_root_authority_snapshot(values["state"],
            snapshot_supplier=lambda: values["snapshot"], now_epoch=candidate["issued_at"] + 2)


@pytest.mark.parametrize("kind", ["load", "protected", "initialize"])
@pytest.mark.parametrize("mutation", ["legacy", "tuple", "none", "malformed-grant", "bad-id", "bad-control"])
def test_initial_control_does_not_relax_descriptor_validation(initial_control, kind, mutation):
    import time
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import initialize_root_authority_state
    values = initial_control
    descriptor = copy.deepcopy(values["snapshot"].descriptor)
    if mutation == "legacy":
        descriptor["schema_version"] = "foundup_verified_outcome_root_authority.v1"
        descriptor.pop("root_control_authentication")
    elif mutation in {"tuple", "none", "malformed-grant"}:
        descriptor["grants"] = {"tuple": (), "none": None, "malformed-grant": [{}]}[mutation]
    elif mutation == "bad-control":
        descriptor["root_control_authentication"]["public_key"] = descriptor["signer_public_key"]
    descriptor["descriptor_id"] = descriptor_id_for(descriptor)
    if mutation == "bad-id":
        descriptor["descriptor_id"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError):
        if kind == "initialize":
            initialize_root_authority_state(values["state"],
                replace(values["snapshot"], descriptor=descriptor), now_epoch=int(time.time()))
        else:
            _initial_client(values, kind, descriptor)


@pytest.mark.parametrize("kind", ["load", "protected"])
@pytest.mark.parametrize("mutation", ["older-policy", "expired", "scope", "generation", "owner", "key"])
def test_initial_clients_retain_policy_and_identity_checks(initial_control, kind, mutation):
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    values = initial_control
    policy = copy.deepcopy(values["policy"])
    changes = {}
    if mutation == "older-policy":
        policy["schema_version"] = pc.POLICY_SCHEMA_V9
        policy["grant_authority_archive_source_descriptor_digest"] = policy.pop("grant_authority_installed_runtime_descriptor_digest")
    elif mutation == "expired":
        policy["issued_at"] -= 1000
        policy["expires_at"] -= 1000
    elif mutation == "scope":
        policy["allowed_operations"] = ["issue_work_authority"]
    elif mutation == "generation":
        policy["generation"] = 2
    elif mutation == "key":
        policy["target_signer_public_key"] = policy["grant_authority_public_key"]
    else:
        changes["owner_config_id"] = "sha256:" + "f" * 64
    policy["policy_id"] = pc.signer_owner_e0_policy_id(policy)
    policy["signature"] = _sign(values["grant_private"], pc.canonical_signer_owner_e0_policy_input(policy))
    with pytest.raises(ValueError):
        _initial_client(values, kind, policy=policy, **changes)


@pytest.mark.parametrize("mutation", ["missing-pending", "missing-witness", "bad-snapshot", "bad-proof", "bad-policy", "stale", "peer"])
def test_initial_advance_requires_authentic_snapshot_and_current_context(initial_control, mutation):
    from dataclasses import asdict
    from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import signed_snapshot, stage
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_revocation_protocol as wire
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import _peer
    values = initial_control
    candidate = signed_snapshot(values)
    if mutation == "bad-snapshot":
        candidate["signature"] = _sign(values["target_private"], "unrelated")
    if mutation == "missing-witness":
        values["store"]._prepare_under_lock(candidate)
    elif mutation != "missing-pending":
        stage(values, candidate)
    request = _request(values, operation=wire.OP_ADVANCE, snapshot_id=candidate["snapshot_id"])
    peer = _peer()
    if mutation == "bad-proof":
        request = replace(request, signer_instance_signature=_sign(values["control_private"], wire.canonical_signer_input(request)))
    elif mutation == "bad-policy":
        request = replace(request, policy=dict(request.policy, rate_limit_max_requests=99))
    elif mutation == "stale":
        request = replace(request, issued_at=request.issued_at - 100)
    elif mutation == "peer":
        peer = replace(peer, uid=peer.uid + 1)
    if mutation in {"bad-policy", "stale"}:
        request = replace(request, signer_instance_signature=_sign(values["target_private"], wire.canonical_signer_input(request)))
    request = replace(request, request_id=wire.request_id_for(asdict(request)))
    assert not _handle(values, request, peer=peer).accepted
    assert values["state"].load(values["binding"].anchor_binding_digest()) is None


def test_empty_control_cannot_mint_outcome_client(initial_control):
    import time
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_revocation_client as revocation
    values = initial_control
    with pytest.raises(ValueError, match="verified_outcome_root_consensus_invalid"):
        root_client_module._create_service_backed_outcome_authority(values["snapshot"].descriptor,
            owner_config_id=values["policy"]["owner_config_id"],
            exchange=revocation._lookup_client(values["client"]).exchange, now_epoch=int(time.time()))


@pytest.mark.parametrize("mutation", ["generation", "store", "receipt", "state", "uid", "gid"])
def test_empty_initialization_retains_store_and_snapshot_identity(initial_control, mutation):
    import time
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import initialize_root_authority_state
    values = initial_control
    snapshot = values["snapshot"]
    descriptor = copy.deepcopy(snapshot.descriptor)
    if mutation in {"store", "receipt"}:
        field = "replay_store_id" if mutation == "store" else "replay_store_durability_receipt_id"
        descriptor[field] = "wrong-store" if mutation == "store" else "sha256:" + "f" * 64
        descriptor["descriptor_id"] = descriptor_id_for(descriptor)
        snapshot = replace(snapshot, descriptor=descriptor)
    else:
        fields = {"generation": ("authority_generation_sequence", 2),
            "state": ("state_binding_digest", "sha256:" + "f" * 64),
            "uid": ("signer_uid", 0), "gid": ("signer_gid", True)}
        field, value = fields[mutation]
        snapshot = replace(snapshot, **{field: value})
    with pytest.raises(ValueError, match="root_authority_(snapshot|state_store)_binding_invalid"):
        initialize_root_authority_state(values["state"], snapshot, now_epoch=int(time.time()))


@pytest.mark.parametrize("mutation", ["work-key-proof", "revoked", "generation-drift", "policy-signature"])
def test_initial_protected_use_rejects_before_action(initial_control, mutation):
    from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import signed_snapshot, stage
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
    from modules.communication.moltbot_bridge.src import reddog_signer_secret_grant_revocation_contract as rev
    values = initial_control
    candidate = signed_snapshot(values)
    if mutation == "revoked":
        candidate["revoked_key_epochs"] = [values["policy"]["target_signer_key_epoch"]]
        candidate["snapshot_id"] = rev.signer_grant_revocation_snapshot_id(candidate)
        candidate["signature"] = _sign(values["revocation_private"], rev.canonical_signer_grant_revocation_snapshot_input(candidate))
    stage(values, candidate)
    values["client"].advance_snapshot(candidate["snapshot_id"])
    values["store"]._finalize_under_lock(candidate["snapshot_id"])
    changes = {}
    if mutation == "work-key-proof":
        changes["request_signer"] = lambda text: _sign(values["target_private"], text)
    elif mutation == "policy-signature":
        values["policy"]["signature"] = _sign(values["target_private"], "wrong-policy")
    client = _initial_client(values, "protected", **changes)
    if mutation == "generation-drift":
        e0._CURRENT_SELECTION["generation_revision"] += "-changed"
    calls = []
    with pytest.raises(ValueError, match="root_protected_use_request_rejected"):
        _protected_action(client, values, lambda: calls.append("must-not-run"))
    assert calls == []


def test_initial_issuer_still_cannot_advance_before_sign_or_rpc(initial_control):
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_revocation_client as client
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import GRANT_ROLE
    values = initial_control
    calls = []
    authority = _initial_client(values, "load", requester_role=GRANT_ROLE,
        request_signer=lambda _: calls.append("signed"))
    with pytest.raises(ValueError, match="root_revocation_grant_load_only"):
        authority.advance_snapshot("sha256:" + "f" * 64)
    assert calls == []
    assert client._lookup_client(authority).requester_role == GRANT_ROLE


@pytest.mark.parametrize("kind", ["load", "protected", "initialize"])
@pytest.mark.parametrize("descriptor", [None, [], "not-a-mapping", True])
def test_initial_consumers_preserve_malformed_descriptor_failure(initial_control, kind, descriptor):
    import time
    from modules.communication.moltbot_bridge.src import (
        foundup_verified_outcome_root_authority_service as service,
        foundup_verified_outcome_root_revocation_client as load,
        foundup_verified_outcome_root_protected_use_client as protected,
    )
    values = initial_control
    with pytest.raises(ValueError, match="verified_outcome_root_descriptor_shape_invalid"):
        if kind == "initialize":
            service.initialize_root_authority_state(values["state"],
                replace(values["snapshot"], descriptor=descriptor), now_epoch=int(time.time()))
        else:
            factory = load._create_root_revocation_anchor_authority if kind == "load" else protected._create_root_protected_use_authority
            factory(descriptor, owner_config_id=values["policy"]["owner_config_id"],
                policy=values["policy"], binding=values["binding"],
                exchange=load._lookup_client(values["client"]).exchange,
                request_signer=lambda _: None, now_epoch=int(time.time()))


@pytest.mark.parametrize("mutation", ["legacy", "nonempty", "HIGH", "generation", "bool-generation", "missing", "empty-text", "wrong-id", "control-key"])
def test_absent_consensus_is_only_exact_first_low_empty_v2_identity(initial_control, mutation):
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_authority as contract
    body = copy.deepcopy(initial_control["snapshot"].descriptor)
    if mutation == "legacy":
        body["schema_version"] = contract.DESCRIPTOR_SCHEMA
        body.pop("root_control_authentication")
    elif mutation == "nonempty":
        body["grants"] = [{}]
    elif mutation == "HIGH":
        body["authority_tier"] = "HIGH"
    elif mutation in {"generation", "bool-generation"}:
        body["authority_generation_sequence"] = 2 if mutation == "generation" else True
    elif mutation == "missing":
        body.pop("consensus_receipt_digest")
    elif mutation == "empty-text":
        body["consensus_receipt_digest"] = ""
    elif mutation == "control-key":
        body["root_control_authentication"]["public_key"] = body["signer_public_key"]
    body["descriptor_id"] = descriptor_id_for(body)
    if mutation == "wrong-id":
        body["descriptor_id"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError):
        contract.validate_root_verified_outcome_descriptor_identity_public(body, now_epoch=int(time.time()))


def test_full_outcome_validator_still_explicitly_requires_consensus(initial_control):
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_authority as contract
    body = initial_control["snapshot"].descriptor
    assert contract.validate_root_verified_outcome_descriptor_identity_public(body, now_epoch=int(time.time())) == body
    with pytest.raises(ValueError, match="^verified_outcome_root_consensus_invalid$"):
        contract.validate_root_verified_outcome_descriptor_public(body, now_epoch=int(time.time()))


def test_preexisting_hashed_empty_control_identity_remains_compatible(initial_control):
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_authority as contract
    body = dict(initial_control["snapshot"].descriptor, consensus_receipt_digest="sha256:" + "a" * 64)
    body["descriptor_id"] = descriptor_id_for(body)
    assert contract.validate_root_verified_outcome_descriptor_identity_public(body, now_epoch=int(time.time())) == body
    for kind in ("load", "protected"):
        assert _initial_client(initial_control, kind, descriptor=body) is not None
    with pytest.raises(ValueError, match="^verified_outcome_root_grants_invalid$"):
        contract.validate_root_verified_outcome_descriptor_public(body, now_epoch=int(time.time()))
