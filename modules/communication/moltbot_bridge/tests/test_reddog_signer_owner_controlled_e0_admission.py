from __future__ import annotations

import hashlib
import inspect
import json
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_controlled_e0_admission import (
    OwnerControlledE0AdmissionBoundary,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_owner_e0_current_selection as current_selection_module,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    POLICY_SCHEMA,
    canonical_signer_owner_e0_policy_input,
    signer_key_reference_digest,
    signer_owner_e0_authority_binding_digest,
    signer_owner_e0_policy_id,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_principal_authority import (
    load_current_generation_principal_authority_resolver,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)


pytest.importorskip("cryptography")

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64
DIGEST_E = "sha256:" + "e" * 64
_CURRENT_SELECTION: dict[str, object] = {}
SLICE_MODULES = (
    "reddog_signer_owner_e0_policy_contract.py",
    "reddog_signer_owner_e0_admission_contract.py",
    "reddog_signer_owner_e0_admission_validation.py",
    "reddog_signer_owner_e0_capability_state.py",
    "reddog_signer_owner_e0_current_selection.py",
    "reddog_signer_owner_e0_principal_authority.py",
    "reddog_signer_owner_e0_principal_records.py",
    "reddog_signer_owner_controlled_e0_admission.py",
)


class _SelectionBoundary:
    def __init__(self, capability: object, selection: dict[str, object]) -> None:
        self.capability = capability
        self.selection = selection
        self.used = False

    def consume(self, value: object) -> dict[str, object]:
        if value is not self.capability or self.used:
            raise ValueError("selection_unverified")
        self.used = True
        return dict(self.selection)

    @contextmanager
    def _lease_current(self, value: object):
        selected = self.consume(value)
        try:
            yield selected
        finally:
            if selected != dict(self.selection):
                raise ValueError("selection_changed_during_consumer")


@pytest.fixture(autouse=True)
def _root_owned_selection_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    def load(**_kwargs: object) -> tuple[object, _SelectionBoundary]:
        capability = object()
        return capability, _SelectionBoundary(capability, _CURRENT_SELECTION)

    monkeypatch.setattr(
        current_selection_module,
        "load_system_service_manifest_selection",
        load,
    )


def _keypair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private, encode_ed25519_public_key(public)


def _canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def _fixture_roots(tmp_path: Path) -> dict[str, Path]:
    roots = {
        name: tmp_path / name
        for name in ("repo", "runtime", "signer", "replay", "revocation")
    }
    for path in roots.values():
        path.mkdir()
    return roots


def _write_fixture_config(
    roots: dict[str, Path],
    policy: dict[str, object],
    target_public: str,
    signing_ref: str,
    audit_ref: str,
) -> tuple[dict[str, object], Path, str]:
    config = _config(
        repo=roots["repo"],
        runtime=roots["runtime"],
        signer=roots["signer"],
        target_public=target_public,
        signing_ref=signing_ref,
        audit_ref=audit_ref,
        authority_binding_digest=signer_owner_e0_authority_binding_digest(policy),
    )
    config_path = roots["runtime"] / "reddog-signer-service.json"
    config_path.write_text(json.dumps(config, sort_keys=True), encoding="ascii")
    return config, config_path, _canonical_digest(config)


def _write_fixture_principals(
    runtime_root: Path, grant_public: str, revocation_public: str
) -> tuple[dict[str, object], Path]:
    payload = _principals(grant_public, revocation_public)
    path = runtime_root / "principal_authority_records.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="ascii")
    return payload, path


def _fixture_selection(
    roots: dict[str, Path], config_path: Path, config_digest: str, principal_path: Path
) -> dict[str, object]:
    return {
        "owner_config_id": DIGEST_A,
        "manifest_id": DIGEST_B,
        "artifact_generation_digest": DIGEST_C,
        "config_digest": config_digest,
        "generation": 4,
        "generation_revision": "revision-4",
        "repo_root": str(roots["repo"].resolve()),
        "runtime_root": str(roots["runtime"].resolve()),
        "config_path": str(config_path.resolve()),
        "principal_authority_records_path": str(principal_path.resolve()),
        "principal_authority_records_digest": _raw_file_digest(principal_path),
    }


def _fixture(tmp_path: Path) -> dict[str, object]:
    roots = _fixture_roots(tmp_path)
    target_private, target_public = _keypair()
    grant_private, grant_public = _keypair()
    _, revocation_public = _keypair()
    signing_ref = "op://Foundups/reddog-signing/private"
    audit_ref = "op://Foundups/reddog-signing/audit"
    policy = _policy(
        selection={
            "owner_config_id": DIGEST_A,
            "manifest_id": DIGEST_B,
            "artifact_generation_digest": DIGEST_C,
            "config_digest": DIGEST_E,
            "generation": 4,
            "generation_revision": "revision-4",
        },
        signer=roots["signer"],
        replay=roots["replay"],
        revocation=roots["revocation"],
        target_public=target_public,
        grant_public=grant_public,
        revocation_public=revocation_public,
        signing_ref=signing_ref,
        audit_ref=audit_ref,
    )
    config, config_path, config_digest = _write_fixture_config(
        roots, policy, target_public, signing_ref, audit_ref
    )
    principal_payload, principal_path = _write_fixture_principals(
        roots["runtime"], grant_public, revocation_public
    )
    selection = _fixture_selection(roots, config_path, config_digest, principal_path)
    policy["config_digest"] = config_digest
    policy["policy_id"] = signer_owner_e0_policy_id(policy)
    policy["signature"] = encode_ed25519_signature(
        grant_private.sign(
            canonical_signer_owner_e0_policy_input(policy).encode("ascii")
        )
    )
    _CURRENT_SELECTION.clear()
    _CURRENT_SELECTION.update(selection)
    return {
        "boundary": OwnerControlledE0AdmissionBoundary(repo_root=roots["repo"]),
        "owner_config_path": tmp_path / "owner-config.json",
        "policy": policy,
        "selection": selection,
        "config": config,
        "config_path": config_path,
        "principal_payload": principal_payload,
        "principal_path": principal_path,
        "grant_private": grant_private,
        "grant_public": grant_public,
        "target_private": target_private,
        "target_public": target_public,
    }


def _principals(grant_public: str, revocation_public: str) -> dict[str, object]:
    records = {}
    for principal_id, public_key in (
        ("principal:grant-admin", grant_public),
        ("principal:revocation-admin", revocation_public),
    ):
        records[f"github|{principal_id}"] = {
            "principal_id": principal_id,
            "principal_provider": "github",
            "principal_public_key": public_key,
            "repo_scope": ["FOUNDUPS/Foundups-Agent"],
            "foundup_scope": ["*"],
            "verified_subject_digest": DIGEST_A,
            "reward_account": None,
            "owner_dae": None,
            "principal_wallet": None,
        }
    return {
        "schema_version": "reddog_authority_runtime_resolver_supply.v1",
        "principal_count": len(records),
        "principals": records,
        "resolver_supply_receipt_id": DIGEST_B,
        "no_holoindex_reindex_performed": True,
    }


def _raw_file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _config(
    *,
    repo: Path,
    runtime: Path,
    signer: Path,
    target_public: str,
    signing_ref: str,
    audit_ref: str,
    authority_binding_digest: str,
) -> dict[str, object]:
    del repo
    return {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "runtime_root": str(runtime.resolve()),
        "signer_runtime_root": str(signer.resolve()),
        "socket_path": str((runtime / "signer.sock").resolve()),
        "control_loop_anchor_path": str((signer / "anchor.json").resolve()),
        "control_loop_authority_policy": {
            "issuer_principal_id": "principal:grant-admin",
            "signer_public_key": target_public,
            "key_epoch": "target-epoch-1",
            "consensus_receipt_digest": DIGEST_D,
            "authority_profile_digest": DIGEST_E,
            "authority_profile_source_receipt_id": DIGEST_A,
        },
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "owner_e0_authority_binding_digest": authority_binding_digest,
        "max_requests": 3,
        "timeout_s": 2.5,
        "max_request_bytes": 4096,
        "max_response_bytes": 8192,
        "key_provider_profiles": [
            {
                "signer_profile_id": "reddog-work-authority",
                "signer_agent_id": "signer:reddog",
                "signing_key_ref": signing_ref,
                "audit_mac_key_ref": audit_ref,
                "expected_public_key": target_public,
                "expected_key_fingerprint": public_key_fingerprint(target_public),
                "expected_key_epoch": "target-epoch-1",
                "permission_snapshot_digest": DIGEST_D,
                "ttl_seconds": 60,
            }
        ],
        "peer_policy": {
            "uid_to_principal": {"1001": "principal:grant-admin"},
            "allowed_gids": [1002],
            "transport": "unix_socket",
            "credential_source_prefix": "kernel_peer_credential",
        },
    }


def _policy(
    *,
    selection: dict[str, object],
    signer: Path,
    replay: Path,
    revocation: Path,
    target_public: str,
    grant_public: str,
    revocation_public: str,
    signing_ref: str,
    audit_ref: str,
) -> dict[str, object]:
    return {
        "schema_version": POLICY_SCHEMA,
        "policy_id": DIGEST_A,
        **{
            name: selection[name]
            for name in (
                "owner_config_id",
                "manifest_id",
                "artifact_generation_digest",
                "config_digest",
                "generation",
                "generation_revision",
            )
        },
        "grant_authority_principal_id": "principal:grant-admin",
        "grant_authority_principal_provider": "github",
        "grant_authority_public_key": grant_public,
        "revocation_authority_principal_id": "principal:revocation-admin",
        "revocation_authority_principal_provider": "github",
        "revocation_authority_public_key": revocation_public,
        "target_signer_agent_id": "signer:reddog",
        "target_signer_profile_id": "reddog-work-authority",
        "target_signer_public_key": target_public,
        "target_signer_key_fingerprint": public_key_fingerprint(target_public),
        "target_signer_key_epoch": "target-epoch-1",
        "target_signer_generation_id": selection["artifact_generation_digest"],
        "signing_key_ref_hash": signer_key_reference_digest(signing_ref),
        "audit_mac_key_ref_hash": signer_key_reference_digest(audit_ref),
        "permission_snapshot_digest": DIGEST_D,
        "permission_snapshot_receipt_id": DIGEST_E,
        "replay_root": str(replay.resolve()),
        "replay_path": str((replay / "grant-nonces.db").resolve()),
        "replay_store_id": "signer-grant-replay",
        "replay_store_durability_receipt_id": DIGEST_A,
        "revocation_root": str(revocation.resolve()),
        "revocation_path": str((revocation / "revocations.db").resolve()),
        "revocation_store_id": "signer-grant-revocations",
        "revocation_store_durability_receipt_id": DIGEST_B,
        "allowed_operations": ["issue_work_authority"],
        "allowed_authority_tiers": ["HIGH", "SOVEREIGN"],
        "consensus_required_tiers": ["HIGH", "SOVEREIGN"],
        "rate_limit_window_seconds": 60,
        "rate_limit_max_requests": 10,
        "issued_at": int(time.time()) - 10,
        "expires_at": int(time.time()) + 200,
        "signature": "pending",
    }


def _resign(fixture: dict[str, object]) -> None:
    policy = fixture["policy"]
    assert isinstance(policy, dict)
    policy["policy_id"] = signer_owner_e0_policy_id(policy)
    private = fixture["grant_private"]
    policy["signature"] = encode_ed25519_signature(
        private.sign(canonical_signer_owner_e0_policy_input(policy).encode("ascii"))
    )


def _write_principal_artifact(fixture: dict[str, object]) -> None:
    path = fixture["principal_path"]
    path.write_text(
        json.dumps(fixture["principal_payload"], sort_keys=True),
        encoding="ascii",
    )
    digest = _raw_file_digest(path)
    fixture["selection"]["principal_authority_records_digest"] = digest
    _CURRENT_SELECTION["principal_authority_records_digest"] = digest


def _rebind_config_and_sign(fixture: dict[str, object], private: object) -> None:
    policy = fixture["policy"]
    config = fixture["config"]
    config["owner_e0_authority_binding_digest"] = (
        signer_owner_e0_authority_binding_digest(policy)
    )
    fixture["config_path"].write_text(
        json.dumps(config, sort_keys=True), encoding="ascii"
    )
    config_digest = _canonical_digest(config)
    fixture["selection"]["config_digest"] = config_digest
    _CURRENT_SELECTION["config_digest"] = config_digest
    policy["config_digest"] = config_digest
    policy["policy_id"] = signer_owner_e0_policy_id(policy)
    policy["signature"] = encode_ed25519_signature(
        private.sign(canonical_signer_owner_e0_policy_input(policy).encode("ascii"))
    )


def test_current_signed_generation_and_policy_issue_one_opaque_capability(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(fixture["owner_config_path"], fixture["policy"])
    assert result.accepted is True
    assert result.no_secret_resolution_performed is True
    receipt = fixture["boundary"].consume(result.capability)
    assert receipt.target_signer_agent_id == "signer:reddog"
    assert receipt.policy_id == result.policy_id
    assert receipt.no_composition_authority_released is True
    with pytest.raises(ValueError):
        fixture["boundary"].consume(result.capability)


def test_current_generation_full_principal_resolver_reuses_manifest_binding(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    selection = fixture["selection"]
    assert isinstance(selection, dict)

    resolver = load_current_generation_principal_authority_resolver(
        repo_root=Path(str(selection["repo_root"])), selection=selection
    )

    record = resolver.resolve_unique("principal:grant-admin")
    assert record is not None
    assert record.principal_provider == "github"
    assert resolver.resolve("principal:grant-admin", "github") == record
    assert resolver.resolve_unique("missing") is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("manifest_id", DIGEST_E),
        ("config_digest", DIGEST_E),
        ("owner_config_id", DIGEST_E),
        ("generation_revision", "revision-3"),
        ("permission_snapshot_digest", DIGEST_E),
        ("signing_key_ref_hash", DIGEST_E),
        ("target_signer_generation_id", DIGEST_E),
        ("allowed_operations", ["issue_principal_identity"]),
        ("rate_limit_max_requests", 11),
    ],
)
def test_attacker_recomputed_policy_still_rejects_bound_drift(
    tmp_path: Path, field: str, value: object
) -> None:
    fixture = _fixture(tmp_path)
    fixture["policy"][field] = value
    _resign(fixture)
    result = fixture["boundary"].admit(fixture["owner_config_path"], fixture["policy"])
    assert result.accepted is False


def test_self_authority_rejects_even_with_valid_signature(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    policy = fixture["policy"]
    policy["grant_authority_public_key"] = fixture["target_public"]
    record = fixture["principal_payload"]["principals"]["github|principal:grant-admin"]
    record["principal_public_key"] = fixture["target_public"]
    _write_principal_artifact(fixture)
    _rebind_config_and_sign(fixture, fixture["target_private"])
    assert (
        fixture["boundary"].admit(fixture["owner_config_path"], policy).accepted
        is False
    )


def test_untrusted_revocation_authority_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["principal_payload"]["principals"].pop("github|principal:revocation-admin")
    fixture["principal_payload"]["principal_count"] = 1
    _write_principal_artifact(fixture)
    assert (
        fixture["boundary"]
        .admit(fixture["owner_config_path"], fixture["policy"])
        .accepted
        is False
    )


@pytest.mark.parametrize(
    "mutation", ["wrong_key", "wrong_provider", "extra", "duplicate"]
)
def test_manifest_bound_principal_records_fail_closed(
    tmp_path: Path, mutation: str
) -> None:
    fixture = _fixture(tmp_path)
    records = fixture["principal_payload"]["principals"]
    grant = records["github|principal:grant-admin"]
    if mutation == "wrong_key":
        grant["principal_public_key"] = fixture["target_public"]
    elif mutation == "wrong_provider":
        grant["principal_provider"] = "gitlab"
    elif mutation == "extra":
        grant["authority"] = "self-asserted"
    else:
        records["principal:grant-admin"] = dict(grant)
        fixture["principal_payload"]["principal_count"] = 3
    _write_principal_artifact(fixture)

    assert (
        fixture["boundary"]
        .admit(fixture["owner_config_path"], fixture["policy"])
        .accepted
        is False
    )


@pytest.mark.parametrize(
    "mutation", ["top_level", "principal_only_index", "float_count", "bool_count"]
)
def test_principal_artifact_requires_exact_canonical_shape(
    tmp_path: Path, mutation: str
) -> None:
    fixture = _fixture(tmp_path)
    payload = fixture["principal_payload"]
    if mutation == "top_level":
        payload["unexpected"] = "self-asserted"
    elif mutation == "principal_only_index":
        records = payload["principals"]
        records["principal:grant-admin"] = records.pop("github|principal:grant-admin")
    elif mutation == "float_count":
        payload["principal_count"] = 2.0
    else:
        payload["principal_count"] = True
    _write_principal_artifact(fixture)

    assert (
        fixture["boundary"]
        .admit(fixture["owner_config_path"], fixture["policy"])
        .accepted
        is False
    )


def test_principal_artifact_duplicate_json_key_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    serialized = json.dumps(fixture["principal_payload"], sort_keys=True)
    duplicate = (
        '{"schema_version":"reddog_authority_runtime_resolver_supply.v1",'
        + serialized[1:]
    )
    fixture["principal_path"].write_text(duplicate, encoding="ascii")
    digest = _raw_file_digest(fixture["principal_path"])
    fixture["selection"]["principal_authority_records_digest"] = digest
    _CURRENT_SELECTION["principal_authority_records_digest"] = digest

    assert (
        fixture["boundary"]
        .admit(fixture["owner_config_path"], fixture["policy"])
        .accepted
        is False
    )


def test_production_boundary_has_no_injected_verifier_or_clock() -> None:
    parameters = inspect.signature(OwnerControlledE0AdmissionBoundary).parameters
    assert "selection_boundary" not in parameters
    assert "principal_key_resolver" not in parameters
    assert "signature_verifier" not in parameters
    assert "now_epoch" not in parameters
    assert (
        "consumer"
        not in inspect.signature(OwnerControlledE0AdmissionBoundary.consume).parameters
    )


def test_expired_policy_rejects_using_system_time(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["policy"]["issued_at"] = int(time.time()) - 200
    fixture["policy"]["expires_at"] = int(time.time()) - 1
    _resign(fixture)
    assert (
        fixture["boundary"]
        .admit(fixture["owner_config_path"], fixture["policy"])
        .accepted
        is False
    )


def test_consume_rechecks_policy_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(fixture["owner_config_path"], fixture["policy"])
    assert result.accepted is True
    monkeypatch.setattr(
        current_selection_module.time,
        "time",
        lambda: int(fixture["policy"]["expires_at"]) + 1,
    )
    with pytest.raises(ValueError):
        fixture["boundary"].consume(result.capability)


def test_consume_rechecks_current_generation(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(fixture["owner_config_path"], fixture["policy"])
    assert result.accepted is True
    _CURRENT_SELECTION["generation_revision"] = "revision-5"
    with pytest.raises(ValueError):
        fixture["boundary"].consume(result.capability)


def test_consume_rechecks_config_bytes(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(fixture["owner_config_path"], fixture["policy"])
    assert result.accepted is True
    fixture["config"]["permission_snapshot_fresh"] = False
    fixture["config_path"].write_text(
        json.dumps(fixture["config"], sort_keys=True), encoding="ascii"
    )
    with pytest.raises(ValueError):
        fixture["boundary"].consume(result.capability)
