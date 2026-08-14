"""Root-owned authority for the grant-service executable source policy."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (  # noqa: E501
    SOURCE_POLICY_SCHEMA,
    canonical_grant_service_git_sources,
    grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    digest,
    is_sha256,
    raw_digest,
)


OWNER_POLICY_FIELDS = frozenset(
    {"schema_version", "repo_root_digest", "sources", "source_policy_digest"}
)


class GrantAuthoritySourcePolicyAuthority(Protocol):
    """Opaque capability issued from one authenticated owner-config read."""


class GrantAuthoritySourcePolicyBoundary(Protocol):
    def revalidate(self, value: object) -> Mapping[str, Any]: ...


def validate_grant_authority_source_policy_owner_config(
    owner: Mapping[str, Any], *, repo: Path
) -> Mapping[str, Any]:
    """Validate the exact canonical policy embedded in owner config v4."""
    raw = owner.get("grant_authority_source_policy")
    if not isinstance(raw, Mapping) or set(raw) != OWNER_POLICY_FIELDS:
        raise RuntimeArtifactManifestError("grant_source_policy_owner_shape_invalid")
    expected_root = raw_digest(str(Path(repo).resolve()).encode("utf-8"))
    if raw.get("schema_version") != SOURCE_POLICY_SCHEMA:
        raise RuntimeArtifactManifestError("grant_source_policy_owner_schema_invalid")
    if raw.get("repo_root_digest") != expected_root:
        raise RuntimeArtifactManifestError("grant_source_policy_repo_binding_mismatch")
    sources = canonical_grant_service_git_sources(raw.get("sources", {}))
    policy_digest = grant_service_git_source_policy_digest(sources)
    if not is_sha256(raw.get("source_policy_digest")) or raw.get(
        "source_policy_digest"
    ) != policy_digest:
        raise RuntimeArtifactManifestError("grant_source_policy_digest_mismatch")
    return MappingProxyType(
        {
            "schema_version": SOURCE_POLICY_SCHEMA,
            "repo_root_digest": expected_root,
            "sources": MappingProxyType(dict(sources)),
            "source_policy_digest": policy_digest,
        }
    )


def load_grant_authority_source_policy_authority(
    *, owner_config_path: Path | str, repo_root: Path | str
) -> tuple[GrantAuthoritySourcePolicyAuthority, GrantAuthoritySourcePolicyBoundary]:
    """Load root-owned v4 policy and return one revalidatable capability."""
    repo = Path(repo_root).resolve()
    owner = _load_owner(owner_config_path, repo)
    if owner.get("schema_version") != _owner_schema_v4():
        raise RuntimeArtifactManifestError("grant_source_policy_owner_v4_required")
    policy = validate_grant_authority_source_policy_owner_config(owner, repo=repo)
    return _make_boundary(owner_config_path, repo, owner, policy)


def _make_boundary(
    owner_config_path: Path | str,
    repo: Path,
    owner: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> tuple[GrantAuthoritySourcePolicyAuthority, GrantAuthoritySourcePolicyBoundary]:
    seal = object()
    issued: WeakKeyDictionary[object, str] = WeakKeyDictionary()
    capability_type = _capability_type(seal)
    values = _capability_values(owner, policy)
    capability = capability_type(values)
    issued[capability] = _fingerprint(values)

    class Boundary:
        __slots__ = ()

        def revalidate(self, value: object) -> Mapping[str, Any]:
            admitted = _require(value, capability_type, seal, issued)
            current = _load_owner(owner_config_path, repo)
            if current.get("schema_version") != _owner_schema_v4():
                raise RuntimeArtifactManifestError("grant_source_policy_owner_stale")
            current_policy = validate_grant_authority_source_policy_owner_config(
                current, repo=repo
            )
            if _capability_values(current, current_policy) != admitted:
                raise RuntimeArtifactManifestError("grant_source_policy_owner_stale")
            return admitted

    return capability, Boundary()


def _capability_type(seal: object) -> type:
    class Capability:
        __slots__ = ("_values", "_seal", "__weakref__")

        def __init__(self, values: Mapping[str, Any]) -> None:
            object.__setattr__(self, "_values", values)
            object.__setattr__(self, "_seal", seal)

        def __setattr__(self, _name: str, _value: Any) -> None:
            raise AttributeError("grant_source_policy_authority_immutable")

        def __copy__(self):
            raise TypeError("grant_source_policy_authority_not_copyable")

        def __deepcopy__(self, _memo: Any):
            raise TypeError("grant_source_policy_authority_not_copyable")

        def __reduce__(self):
            raise TypeError("grant_source_policy_authority_not_serializable")

    return Capability


def _require(
    value: object,
    capability_type: type,
    seal: object,
    issued: WeakKeyDictionary[object, str],
) -> Mapping[str, Any]:
    if not isinstance(value, capability_type):
        raise RuntimeArtifactManifestError("grant_source_policy_authority_unverified")
    values = object.__getattribute__(value, "_values")
    if (
        object.__getattribute__(value, "_seal") is not seal
        or issued.get(value) != _fingerprint(values)
    ):
        raise RuntimeArtifactManifestError("grant_source_policy_authority_unverified")
    return values


def _capability_values(
    owner: Mapping[str, Any], policy: Mapping[str, Any]
) -> Mapping[str, Any]:
    return MappingProxyType(
        {
            "owner_config_id": str(owner.get("config_id", "")),
            "repo_root_digest": str(policy["repo_root_digest"]),
            "source_policy_digest": str(policy["source_policy_digest"]),
            "sources": MappingProxyType(dict(policy["sources"])),
        }
    )


def _fingerprint(values: Mapping[str, Any]) -> str:
    return digest({**values, "sources": dict(values["sources"])})


def _load_owner(path: Path | str, repo: Path) -> Mapping[str, Any]:
    from modules.communication.moltbot_bridge.src import (
        reddog_signer_system_service_manifest_selection_loader as loader,
    )

    return loader._load_owner_config(path, repo=repo)


def _owner_schema_v4() -> str:
    from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (  # noqa: E501
        SCHEMA_VERSION_V4,
    )

    return SCHEMA_VERSION_V4


__all__ = [
    "GrantAuthoritySourcePolicyAuthority",
    "GrantAuthoritySourcePolicyBoundary",
    "OWNER_POLICY_FIELDS",
    "load_grant_authority_source_policy_authority",
    "validate_grant_authority_source_policy_owner_config",
]
