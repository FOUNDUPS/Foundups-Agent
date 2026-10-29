"""Explicit protected consensus-store metadata, separate from rate/replay custody."""
from pathlib import Path

from .reddog_grant_authority_startup_custody import (
    RATE_FIELDS, grant_rate_store_config, target_replay_store_config,
)
from .reddog_signer_secret_grant_durable_nonce_store import (
    SignerGrantReplayStoreConfig, _validate_config, _paths_overlap,
)
from .reddog_signer_system_service_wsp71_resolver_supply import _startup_credential_binding, _startup_permission
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import parse_systemd_credential_reference
from modules.infrastructure.shared_utilities.runtime_artifact_safety import validate_runtime_root_path, validate_runtime_artifact_path

PURPOSE = "elevated-consensus-nonce.v1"
INTEGRITY_PURPOSE = "elevated-consensus-integrity.v1"
FIELDS = frozenset({"store", "credential_binding", "integrity_permission"})


def consensus_nonce_config(owner, repo):
    raw = owner["consensus_nonce_authority"]["store"]
    if type(raw) is not dict or set(raw) != RATE_FIELDS or raw["purpose"] != PURPOSE:
        raise ValueError("consensus_nonce_store_shape_invalid")
    paths = ("nonce_path", "nonce_root", "high_water_path", "high_water_root")
    if any(type(raw[name]) is not str for name in paths):
        raise ValueError("consensus_nonce_store_path_invalid")
    result = SignerGrantReplayStoreConfig(**{name: Path(raw[name]) for name in paths},
        repo_root=Path(repo), **{name: raw[name] for name in
            ("replay_store_binding_digest", "replay_store_id", "durability_receipt_id")})
    _validate_config(result)
    return result


def consensus_credential_binding(owner):
    value = owner["consensus_nonce_authority"]
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError("consensus_nonce_authority_shape_invalid")
    identity = owner["independent_grant_authority"]
    requester = owner["grant_startup_custody"]["loader_credential_binding"]["expected_requester"]
    binding = _startup_credential_binding(value["credential_binding"], dict(
        signer_uid=identity["authority_service_uid"], signer_gid=identity["authority_service_gid"],
        signer_principal_id=requester))
    permission = value["integrity_permission"]
    _startup_permission(permission, binding, INTEGRITY_PURPOSE)
    reference = permission["reference"]
    if binding.credential_ids != frozenset({parse_systemd_credential_reference(reference)}):
        raise ValueError("consensus_nonce_credential_scope_invalid")
    prior = owner["grant_startup_custody"]
    if binding.credential_directory != prior["loader_credential_binding"]["credential_directory"]:
        raise ValueError("consensus_nonce_credential_directory_invalid")
    forbidden = set()
    def collect(value):
        if type(value) is dict:
            for item in value.values(): collect(item)
        elif type(value) is list:
            for item in value: collect(item)
        elif type(value) is str and parse_systemd_credential_reference(value) is not None:
            forbidden.add(value)
    collect({key: item for key, item in owner.items() if key != "consensus_nonce_authority"})
    if reference in forbidden:
        raise ValueError("consensus_nonce_credential_domain_overlap")
    return binding


def validate_consensus_nonce_custody(owner, *, repo_root, owner_root):
    consensus_credential_binding(owner)
    config = consensus_nonce_config(owner, repo_root)
    forbidden = [Path(repo_root), Path(owner_root), Path(owner["anchor_path"]).parent]
    def collect(value):
        if type(value) is dict:
            for name, item in value.items():
                if name.endswith("_root") and type(item) is str:
                    forbidden.append(Path(item))
                else: collect(item)
    collect({key: item for key, item in owner.items() if key != "consensus_nonce_authority"})
    for path, root in ((config.nonce_path, config.nonce_root), (config.high_water_path, config.high_water_root)):
        validate_runtime_root_path(root, repo_root=repo_root)
        validate_runtime_artifact_path(path, allowed_root=root, repo_root=repo_root)
        if any(_paths_overlap(root.resolve(), item.resolve()) for item in forbidden):
            raise ValueError("consensus_nonce_store_domain_overlap")
    _separate(config, grant_rate_store_config(owner, repo_root))


def _separate(config, other):
    names = ("replay_store_id", "replay_store_binding_digest", "durability_receipt_id")
    if (any(getattr(config, name) == getattr(other, name) for name in names)
            or any(_paths_overlap(left.resolve(), right.resolve())
                   for left in (config.nonce_root, config.high_water_root)
                   for right in (other.nonce_root, other.high_water_root))):
        raise ValueError("consensus_nonce_store_domain_overlap")


def current_consensus_nonce_custody(owner, policy, repo, now):
    """Signed policy binds the root-owned descriptor through its owner config ID."""
    operations = tuple(policy["allowed_operations"])
    if (policy["owner_config_id"] != owner["config_id"]
            or operations not in (("worktree_create",), ("delegate_reddog_identity", "worktree_create"))
            or tuple(policy["allowed_authority_tiers"]) != ("HIGH",)
            or tuple(policy["consensus_required_tiers"]) != ("HIGH",)):
        raise ValueError("consensus_nonce_policy_scope_invalid")
    binding = consensus_credential_binding(owner)
    permission = owner["consensus_nonce_authority"]["integrity_permission"]
    if binding.expected_requester != policy["grant_authority_principal_id"]:
        raise ValueError("consensus_nonce_principal_mismatch")
    expiry = min(binding.expires_at, permission["expires_at"], policy["expires_at"])
    if not max(binding.issued_at, permission["issued_at"], policy["issued_at"]) <= now < expiry:
        raise ValueError("consensus_nonce_permission_expired")
    config = consensus_nonce_config(owner, repo)
    _separate(config, target_replay_store_config(owner, policy, repo))
    return binding, config, expiry
