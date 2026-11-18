"""Root-authorized client supply for the independent secret-grant signer."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
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
    validate_runtime_root_path,
)
from .reddog_signer_system_service_owner_inputs import (
    _require_grant_disjoint_root as _require_disjoint_root,
    _grant_socket_root,
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
    _grant_socket_root(value, repo=repo, owner_root=owner_root, grant_root=root)
    _require_disjoint_root(value, owner_root=owner_root, grant_root=root)


def load_system_service_independent_grant_authority_client(
    *,
    owner_config_path: Path | str,
    repo_root: Path,
    owner_policy: Mapping[str, Any],
    timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
) -> IndependentGrantAuthorityClientSupply:
    """Load one peer-authenticated grant signer client from root-owned state."""

    if (type(timeout_s) not in (int, float)
            or not 0 < timeout_s <= 30 or not math.isfinite(timeout_s)):
        raise RuntimeArtifactManifestError("grant_authority_socket_timeout_invalid")

    from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
        SCHEMA_VERSION_V3,
        SCHEMA_VERSION_V4,
        SCHEMA_VERSION_V5,
        SCHEMA_VERSION_V6, SCHEMA_VERSION_V7, SCHEMA_VERSION_V8, SCHEMA_VERSION_V9, SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13,
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
            timeout_s=timeout_s,
            repo=repo, required_schemas={SCHEMA_VERSION_V3, SCHEMA_VERSION_V4, SCHEMA_VERSION_V5, SCHEMA_VERSION_V6, SCHEMA_VERSION_V7, SCHEMA_VERSION_V8, SCHEMA_VERSION_V9, SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13},
        )


def _build_authenticated_supply(
    *, owner: Mapping[str, Any], policy: Mapping[str, Any],
    owner_config_path: Path | str, repo: Path, required_schemas: set[str],
    timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
) -> IndependentGrantAuthorityClientSupply:
    if owner.get("schema_version") not in required_schemas:
        raise RuntimeArtifactManifestError("signer_owner_config_grant_authority_required")
    if policy["owner_config_id"] != owner["config_id"]:
        raise RuntimeArtifactManifestError("grant_authority_owner_binding_mismatch")
    _require_policy_key(policy)
    raw = owner["independent_grant_authority"]
    grant_root = Path(raw["authority_root"]).resolve()
    _require_disjoint_root(
        owner, owner_root=Path(owner_config_path).resolve().parent,
        grant_root=grant_root, policy=policy,
    )
    socket_root = _grant_socket_root(
        owner, repo=repo, owner_root=Path(owner_config_path).resolve().parent,
        grant_root=grant_root, policy=policy,
    )
    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo, socket_path=raw["authority_socket_path"],
        trusted_socket_root=socket_root,
        expected_server_uid=int(raw["authority_service_uid"]),
        expected_server_gid=int(raw["authority_service_gid"]),
        timeout_s=timeout_s,
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
