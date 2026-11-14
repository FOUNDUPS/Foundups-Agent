"""Disposable custody fixture: real E0/signatures/stores, synthetic OS installation."""
import base64
import copy
import json
import time
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

from cryptography.hazmat.primitives import serialization
from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_runtime_dependencies as runtime,
    reddog_grant_authority_root_request_signer as proof,
    reddog_signer_system_service_manifest_selection_loader as owner_loader,
    reddog_signer_owner_e0_current_selection as selection,
    foundup_verified_outcome_root_authority_client as transport,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_startup_custody import GRANT_LOAD_PURPOSE
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import signer_key_reference_digest
from modules.communication.moltbot_bridge.tests import test_foundup_verified_outcome_root_grant_load as root_fixture
from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
from modules.communication.moltbot_bridge.tests import test_reddog_signer_root_protected_use_composition as startup
from modules.communication.moltbot_bridge.tests import test_reddog_signer_socket_service_runtime_wiring as wiring
from modules.infrastructure.secrets_mcp.src import systemd_credential_secret_resolver as credential_os


def custody_metadata(owner, public_key, *, signer_agent="grant:fixture", principal="principal:grant-admin"):
    now = int(time.time())
    identity = owner["independent_grant_authority"]
    common = dict(credential_directory="/run/credentials/grant-test.service",
        expected_uid=identity["authority_service_uid"], expected_gid=identity["authority_service_gid"],
        issued_at=now - 1, expires_at=now + 60, max_secret_bytes=65536)
    signing = dict(common, expected_requester=signer_agent, credential_ids=["grant-audit", "grant-signing"])
    loader = dict(common, expected_requester=principal, credential_ids=["grant-signing", "replay"])
    permissions = dict(operation="SECRETS_READ", requester_id=principal, issued_at=now - 1, expires_at=now + 30)
    return dict(signing_key_ref="systemd-creds://grant-signing", audit_mac_key_ref="systemd-creds://grant-audit",
        credential_binding=signing, loader_credential_binding=loader,
        root_load_permission=dict(permissions, reference="systemd-creds://grant-signing",
            purpose=GRANT_LOAD_PURPOSE, public_key=public_key, key_epoch="grant-epoch-1"),
        replay_integrity_permission=dict(permissions, reference="systemd-creds://replay",
            purpose="signer-grant-replay-integrity.v1", encoding="utf8"))


def build_case(tmp_path, monkeypatch):
    _v2_descriptor(monkeypatch)
    policy_builder = e0._policy
    def low_policy(**kwargs):
        policy = policy_builder(**kwargs)
        policy.update(allowed_operations=["signer_socket_peer_handshake"], allowed_authority_tiers=["LOW"],
            consensus_required_tiers=[], grant_authority_signer_agent_id="grant:fixture")
        for field, ref in [("signing_key_ref", "grant-signing"), ("audit_mac_key_ref", "grant-audit")]:
            policy["grant_authority_" + field + "_hash"] = signer_key_reference_digest("systemd-creds://" + ref)
        return policy
    monkeypatch.setattr(e0, "_policy", low_policy)
    values = root_fixture._runtime(tmp_path, monkeypatch)
    grant_fixture = wiring.factory_fixture.grant_fixture
    owner, _, replay_config = startup._startup_materializer_owner(values, tmp_path, grant_fixture)
    owner.update(schema_version=owner_loader.SCHEMA_VERSION_V9,
        independent_grant_authority=values["owner"]["independent_grant_authority"])
    owner["verified_outcome_authority"].update(signer_uid=1001, signer_gid=1001,
        signer_principal_id="reddog-e0-signer")
    owner["grant_startup_custody"] = custody_metadata(owner, values["policy"]["grant_authority_public_key"])
    values["owner"] = owner
    case = SimpleNamespace(values=values, owner=owner, replay_config=replay_config,
        events=[], active=0, isolated=False, after_read=None, after_rpc=None, secret_override=None)
    _bind_boundaries(case, monkeypatch, grant_fixture)
    return case


def _v2_descriptor(monkeypatch):
    from modules.communication.moltbot_bridge.tests import root_revocation_service_fixtures as fixture
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _private_key, _public_text
    original = fixture._descriptor
    control = _private_key()
    def descriptor(*args, **kwargs):
        overrides = dict(kwargs.get("descriptor_overrides", {}))
        overrides.update(schema_version="foundup_verified_outcome_root_authority.v2",
            root_control_authentication={"purpose": "protected-use-acquire-finish.v1",
                "public_key": _public_text(control), "key_epoch": "control-epoch-1"})
        return original(*args, **{**kwargs, "descriptor_overrides": overrides})
    monkeypatch.setattr(fixture, "_descriptor", descriptor)


def _bind_boundaries(case, monkeypatch, grant_fixture):
    owner, values = case.owner, case.values
    def read_owner(*args, **kwargs):
        return copy.deepcopy(owner)
    def read_policy(*args):
        return json.dumps(values["policy"]).encode("ascii")
    for module in (owner_loader, runtime, proof):
        monkeypatch.setattr(module, "_load_owner_config", read_owner)
    monkeypatch.setattr(runtime, "_read_root_owned_bytes", read_policy)
    def isolate(*args, **kwargs):
        case.events.append("isolate")
        case.isolated = True
        return SimpleNamespace(accepted=True)
    monkeypatch.setattr(runtime, "enforce_signer_process_isolation", isolate)
    _track_leases(case, monkeypatch)
    monkeypatch.setattr(credential_os, "_identity_matches", lambda binding: case.isolated)
    def read_credential(binding, identifier):
        assert case.isolated and case.active, "secret before isolation/current E0"
        case.events.append(identifier)
        if case.after_read:
            case.after_read()
        if case.secret_override:
            return case.secret_override
        if identifier == "replay":
            return grant_fixture.INTEGRITY_KEY.decode("utf-8")
        assert identifier == "grant-signing"
        raw = values["grant_private"].private_bytes(serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw, serialization.NoEncryption())
        return "ed25519-private-raw-b64-v1:" + base64.b64encode(raw).decode("ascii")
    monkeypatch.setattr(credential_os, "_read_credential", read_credential)
    def roundtrip(_path, raw, _uid, _timeout):
        assert case.active == 0, "E0 lease held across root RPC"
        case.events.append("root-rpc")
        response = root_fixture._dispatch(values, root_fixture.wire.request_from_bytes(raw)).to_bytes()
        if case.after_rpc:
            case.after_rpc()
        return response
    monkeypatch.setattr(transport, "_root_socket_roundtrip", roundtrip)


def _track_leases(case, monkeypatch):
    original = selection.lease_validated_owner_e0_current_admission
    @contextmanager
    def lease(**kwargs):
        with original(**kwargs) as current:
            case.active += 1
            try:
                yield current
            finally:
                case.active -= 1
    monkeypatch.setattr(runtime, "lease_validated_owner_e0_current_admission", lease)
    monkeypatch.setattr(proof, "lease_validated_owner_e0_current_admission", lease)


def materialize(case):
    return runtime.materialize_grant_authority_runtime_dependencies(
        owner_config_path=case.values["owner_config_path"], repo_root=case.values["repo"],
        expected_owner_config_id=case.owner["config_id"])
