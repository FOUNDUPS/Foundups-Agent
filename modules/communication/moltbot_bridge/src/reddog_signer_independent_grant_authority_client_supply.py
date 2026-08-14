"""Root-authorized client supply for the independent secret-grant signer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_grant_authority_binding import (
    IndependentGrantAuthorityBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection import (
    lease_validated_owner_e0_current_admission,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
GRANT_AUTHORITY_OWNER_FIELDS = frozenset(
    {
        "authority_root",
        "authority_socket_path",
        "authority_service_uid",
        "authority_service_gid",
    }
)
GRANT_AUTHORITY_SOCKET_FILENAME = "grant-authority.sock"
@dataclass(frozen=True, slots=True)
class IndependentGrantAuthorityClientSupply:
    """Public binding and root-authorized transport for one grant authority."""

    owner_config_id: str
    authority_root: str
    authority_socket_path: str
    authority_service_uid: int
    authority_service_gid: int
    binding: IndependentGrantAuthorityBinding


def validate_independent_grant_authority_owner_config(
    value: Mapping[str, Any], *, repo: Path, owner_root: Path
) -> None:
    """Validate v3 grant transport without constructing a socket client."""

    raw = value.get("independent_grant_authority")
    outcome = value.get("verified_outcome_authority")
    authority_root = raw.get("authority_root") if isinstance(raw, Mapping) else None
    authority_socket = (
        raw.get("authority_socket_path") if isinstance(raw, Mapping) else None
    )
    outcome_socket = (
        outcome.get("authority_socket_path") if isinstance(outcome, Mapping) else None
    )
    if (
        not isinstance(raw, Mapping)
        or set(raw) != GRANT_AUTHORITY_OWNER_FIELDS
        or not isinstance(outcome, Mapping)
        or not isinstance(authority_root, str)
        or not authority_root.strip()
        or not isinstance(authority_socket, str)
        or not authority_socket.strip()
        or not isinstance(outcome_socket, str)
        or not outcome_socket.strip()
        or type(raw.get("authority_service_uid")) is not int
        or int(raw["authority_service_uid"]) <= 0
        or type(raw.get("authority_service_gid")) is not int
        or int(raw["authority_service_gid"]) <= 0
        or raw["authority_service_uid"] == outcome.get("signer_uid")
        or Path(authority_socket).resolve() == Path(outcome_socket).resolve()
    ):
        raise RuntimeArtifactManifestError("grant_authority_owner_config_invalid")
    root = validate_runtime_root_path(raw["authority_root"], repo_root=repo)
    socket_path = validate_runtime_artifact_path(
        raw["authority_socket_path"], allowed_root=root, repo_root=repo
    )
    if socket_path != root / GRANT_AUTHORITY_SOCKET_FILENAME:
        raise RuntimeArtifactManifestError("grant_authority_socket_path_invalid")
    _require_disjoint_root(value, owner_root=owner_root, grant_root=root)


def load_system_service_independent_grant_authority_client(
    *,
    owner_config_path: Path | str,
    repo_root: Path,
    owner_policy: Mapping[str, Any],
) -> IndependentGrantAuthorityClientSupply:
    """Load one peer-authenticated grant signer client from root-owned state."""

    from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
        SCHEMA_VERSION_V3,
        _load_owner_config,
    )

    repo = Path(repo_root).resolve()
    with lease_validated_owner_e0_current_admission(
        owner_config_path=owner_config_path,
        repo_root=repo,
        policy=owner_policy,
    ) as admission:
        owner = _load_owner_config(owner_config_path, repo=repo)
        return _build_authenticated_supply(
            owner=owner, policy=admission.policy, owner_config_path=owner_config_path,
            repo=repo, required_schema=SCHEMA_VERSION_V3,
        )


def _build_authenticated_supply(
    *, owner: Mapping[str, Any], policy: Mapping[str, Any],
    owner_config_path: Path | str, repo: Path, required_schema: str,
) -> IndependentGrantAuthorityClientSupply:
    if owner.get("schema_version") != required_schema:
        raise RuntimeArtifactManifestError("signer_owner_config_v3_required")
    if policy["owner_config_id"] != owner["config_id"]:
        raise RuntimeArtifactManifestError("grant_authority_owner_binding_mismatch")
    _require_policy_key(policy)
    raw = owner["independent_grant_authority"]
    grant_root = Path(raw["authority_root"]).resolve()
    _require_disjoint_root(
        owner, owner_root=Path(owner_config_path).resolve().parent,
        grant_root=grant_root, policy=policy,
    )
    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo, socket_path=raw["authority_socket_path"],
        trusted_socket_root=grant_root,
        expected_server_uid=int(raw["authority_service_uid"]),
        expected_server_gid=int(raw["authority_service_gid"]),
    )
    if built.accepted is not True or built.client is None:
        raise RuntimeArtifactManifestError("grant_authority_socket_client_invalid")
    binding = IndependentGrantAuthorityBinding(
        client=built.client, authority_root=str(grant_root),
        principal_id=str(policy["grant_authority_principal_id"]),
        principal_provider=str(policy["grant_authority_principal_provider"]),
        public_key=str(policy["grant_authority_public_key"]),
        key_epoch=str(policy["grant_authority_key_epoch"]),
        requester_principal_id=str(policy["grant_requester_principal_id"]),
    )
    return IndependentGrantAuthorityClientSupply(
        owner_config_id=str(owner["config_id"]), authority_root=str(grant_root),
        authority_socket_path=str(Path(raw["authority_socket_path"]).resolve()),
        authority_service_uid=int(raw["authority_service_uid"]),
        authority_service_gid=int(raw["authority_service_gid"]), binding=binding,
    )


def _require_disjoint_root(
    value: Mapping[str, Any],
    *,
    owner_root: Path,
    grant_root: Path,
    policy: Mapping[str, Any] | None = None,
) -> None:
    outcome = value["verified_outcome_authority"]
    existing = [
        owner_root,
        *(
            Path(value[name]).resolve()
            for name in ("runtime_root", "high_water_root", "witness_root")
        ),
        *(
            Path(outcome[name]).resolve()
            for name in ("state_root", "state_witness_root", "installation_root")
        ),
    ]
    if policy is not None:
        existing.extend(
            Path(policy[name]).resolve()
            for name in ("replay_root", "revocation_root", "revocation_witness_root")
        )
    if any(
        grant_root == root or grant_root in root.parents or root in grant_root.parents
        for root in existing
    ):
        raise RuntimeArtifactManifestError("grant_authority_owner_root_overlap")


def _require_policy_key(policy: Mapping[str, Any]) -> None:
    if decode_ed25519_public_key(str(policy["grant_authority_public_key"])) is None:
        raise RuntimeArtifactManifestError("grant_authority_public_key_invalid")


__all__ = [
    "GRANT_AUTHORITY_OWNER_FIELDS",
    "GRANT_AUTHORITY_SOCKET_FILENAME",
    "IndependentGrantAuthorityClientSupply",
    "load_system_service_independent_grant_authority_client",
    "validate_independent_grant_authority_owner_config",
]
