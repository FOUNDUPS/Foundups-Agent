"""Process-local launch selection from a verified signed runtime manifest."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    RuntimeArtifactManifestAuthority,
    RuntimeArtifactManifestAuthorityBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    verify_signed_runtime_artifact_manifest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


CONFIG_FILENAME = "signer_service_config.json"
RUN_PACKET_FILENAME = "signer_service_run_packet.json"


class RuntimeArtifactManifestLaunchSelectionBoundary(Protocol):
    """Signer-local one-shot selector and consumer."""

    def select(
        self,
        manifest: Mapping[str, Any],
        *,
        now_epoch: int,
    ) -> object:
        """Verify a signed manifest and mint one process-local capability."""

    def consume(self, value: object) -> Mapping[str, Any]:
        """Consume a capability once and return immutable launch bindings."""


class _LaunchSelectionBoundary:
    __slots__ = ("_select", "_consume")

    def __init__(self, select: Any, consume: Any) -> None:
        self._select = select
        self._consume = consume

    def select(
        self,
        manifest: Mapping[str, Any],
        *,
        now_epoch: int,
    ) -> object:
        return self._select(manifest, now_epoch=now_epoch)

    def consume(self, value: object) -> Mapping[str, Any]:
        return self._consume(value)


def create_runtime_artifact_manifest_launch_selection_boundary(
    *,
    authority: RuntimeArtifactManifestAuthority,
    authority_boundary: RuntimeArtifactManifestAuthorityBoundary,
    signature_verifier: SignatureVerifier,
) -> RuntimeArtifactManifestLaunchSelectionBoundary:
    """Create a boundary that verifies manifests before issuing capabilities."""

    seal = object()
    issued: WeakKeyDictionary[object, Mapping[str, Any]] = WeakKeyDictionary()
    capability_type = _capability_type(seal)

    def select(
        manifest: Mapping[str, Any],
        *,
        now_epoch: int,
    ) -> object:
        payload = verify_signed_runtime_artifact_manifest(
            manifest,
            authority=authority,
            authority_boundary=authority_boundary,
            now_epoch=now_epoch,
            signature_verifier=signature_verifier,
        )
        authority_values = authority_boundary.require(authority)
        values = _launch_values(payload, authority_values)
        capability = capability_type(values)
        issued[capability] = values
        return capability

    def consume(value: object) -> Mapping[str, Any]:
        if not isinstance(value, capability_type):
            raise RuntimeArtifactManifestError(
                "manifest_launch_selection_unverified"
            )
        if object.__getattribute__(value, "_seal") is not seal:
            raise RuntimeArtifactManifestError(
                "manifest_launch_selection_unverified"
            )
        expected = issued.pop(value, None)
        actual = object.__getattribute__(value, "_values")
        if expected is None or dict(actual) != dict(expected):
            raise RuntimeArtifactManifestError(
                "manifest_launch_selection_unverified"
            )
        return MappingProxyType(dict(actual))

    return _LaunchSelectionBoundary(select, consume)


def _capability_type(seal: object) -> type:
    class Capability:
        __slots__ = ("_values", "_seal", "__weakref__")

        def __init__(self, values: Mapping[str, Any]) -> None:
            object.__setattr__(
                self,
                "_values",
                MappingProxyType(dict(values)),
            )
            object.__setattr__(self, "_seal", seal)

        def __setattr__(self, name: str, value: Any) -> None:
            del name, value
            raise AttributeError("manifest_launch_selection_immutable")

        def __copy__(self):
            raise TypeError("manifest_launch_selection_not_copyable")

        def __deepcopy__(self, memo: Any):
            del memo
            raise TypeError("manifest_launch_selection_not_copyable")

        def __reduce__(self):
            raise TypeError("manifest_launch_selection_not_serializable")

    return Capability


def _launch_values(
    manifest: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> Mapping[str, Any]:
    descriptors = {
        str(item.get("filename") or ""): item
        for item in manifest.get("artifacts") or ()
        if isinstance(item, Mapping)
    }
    config = descriptors.get(CONFIG_FILENAME)
    run_packet = descriptors.get(RUN_PACKET_FILENAME)
    runtime_root = Path(authority["runtime_root"]).resolve()
    repo_root = Path(authority["repo_root"]).resolve()
    if not config or not run_packet:
        raise RuntimeArtifactManifestError(
            "manifest_launch_artifacts_missing"
        )
    values = {
        "manifest_id": manifest.get("manifest_id"),
        "artifact_generation_digest": manifest.get(
            "artifact_generation_digest"
        ),
        "config_digest": manifest.get("signer_service_config_digest"),
        "config_raw_digest": config.get("content_digest"),
        "run_packet_digest": run_packet.get("content_digest"),
        "repo_root": str(repo_root),
        "runtime_root": str(runtime_root),
        "config_path": str(runtime_root / CONFIG_FILENAME),
        "run_packet_path": str(runtime_root / RUN_PACKET_FILENAME),
    }
    if not all(
        is_sha256(values[key])
        for key in (
            "manifest_id",
            "artifact_generation_digest",
            "config_digest",
            "config_raw_digest",
            "run_packet_digest",
        )
    ):
        raise RuntimeArtifactManifestError(
            "manifest_launch_bindings_invalid"
        )
    return values


__all__ = [
    "CONFIG_FILENAME",
    "RUN_PACKET_FILENAME",
    "RuntimeArtifactManifestLaunchSelectionBoundary",
    "create_runtime_artifact_manifest_launch_selection_boundary",
]
