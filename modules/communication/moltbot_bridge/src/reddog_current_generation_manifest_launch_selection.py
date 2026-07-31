"""One-shot signer launch selection from the authenticated current generation."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    MAX_ARTIFACT_BYTES,
    DEFAULT_MAX_TTL_SECONDS,
    REQUIRED_RUNTIME_ARTIFACTS,
    RuntimeArtifactManifestError,
    canonical_signing_input,
    is_sha256,
    raw_digest,
    validate_freshness,
    validate_signed_payload,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_io import (
    MANIFEST_DIRECTORY_NAME,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_launch_selection import (
    CONFIG_FILENAME,
    RUN_PACKET_FILENAME,
    RuntimeArtifactManifestLaunchSelectionBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationActivation,
    _build_process_local_registry,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
    SignerRuntimeGenerationReader,
    SignerRuntimeGenerationReaderAuthorityBoundary,
    require_signer_runtime_generation_reader_authority,
)
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

SELECTION_TTL_SECONDS = 30


@dataclass(frozen=True)
class _OwnerAuthorityValues:
    repo: Path
    runtime: Path
    trust: tuple[str, str, str, str]
    owner_config_id: str


class CurrentGenerationLaunchOwnerAuthorityBoundary(Protocol):
    """Process-local boundary for descriptor-verified owner configuration."""

    def require(self, value: object) -> _OwnerAuthorityValues: ...


_issue_owner_authority, _lookup_owner_authority = (
    _build_process_local_registry("launch_owner_authority_unverified")
)
del _build_process_local_registry


def _owner_boundary_require(lookup: Any):
    def require(self: object, value: object) -> _OwnerAuthorityValues:
        authority, owner = lookup(self)
        if value is not authority:
            raise RuntimeArtifactManifestError(
                "launch_owner_authority_unverified"
            )
        return owner

    return require


class _OwnerAuthorityBoundary:
    __slots__ = ("__weakref__",)

    require = _owner_boundary_require(_lookup_owner_authority)


def _issue_current_generation_launch_owner_authority(
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    anchor_id: str,
    authenticator_id: str,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
    owner_config_id: str,
) -> tuple[object, CurrentGenerationLaunchOwnerAuthorityBoundary]:
    """Mint owner authority after the external loader verifies durable policy."""

    repo = Path(repo_root).resolve()
    values = _OwnerAuthorityValues(
        repo=repo,
        runtime=validate_runtime_root_path(runtime_root, repo_root=repo),
        trust=_expected_generation_trust(
            anchor_id,
            authenticator_id,
            high_water_store_id,
            high_water_durability_receipt_id,
        ),
        owner_config_id=_sha256(owner_config_id, "owner_config_id"),
    )
    authority = object()
    boundary = _OwnerAuthorityBoundary()
    _issue_owner_authority(boundary, (authority, values))
    return authority, boundary


def create_current_generation_manifest_launch_selection_boundary(
    *,
    owner_authority: object,
    owner_authority_boundary: (
        CurrentGenerationLaunchOwnerAuthorityBoundary
    ),
    generation_reader_authority: object,
    generation_reader_authority_boundary: (
        SignerRuntimeGenerationReaderAuthorityBoundary
    ),
) -> RuntimeArtifactManifestLaunchSelectionBoundary:
    """Verify the active generation before issuing a one-shot launch capability."""

    owner = _require_owner_authority(
        owner_authority, owner_authority_boundary
    )
    state = _SelectionState(
        repo=owner.repo,
        runtime=owner.runtime,
        reader=require_signer_runtime_generation_reader_authority(
            generation_reader_authority,
            generation_reader_authority_boundary,
        ),
        trust=owner.trust,
        owner_config_id=owner.owner_config_id,
    )
    return _Boundary(state.select, state.consume)


def _require_owner_authority(
    authority: object,
    boundary: CurrentGenerationLaunchOwnerAuthorityBoundary,
) -> _OwnerAuthorityValues:
    if type(boundary) is not _OwnerAuthorityBoundary:
        raise RuntimeArtifactManifestError(
            "launch_owner_boundary_invalid"
        )
    return boundary.require(authority)


class _SelectionState:
    __slots__ = (
        "repo", "runtime", "reader", "trust", "owner_config_id", "seal",
        "issued", "issue_lock", "capability_type",
    )

    def __init__(
        self,
        *,
        repo: Path,
        runtime: Path,
        reader: SignerRuntimeGenerationReader,
        trust: tuple[str, str, str, str],
        owner_config_id: str,
    ) -> None:
        self.repo = repo
        self.runtime = runtime
        self.reader = reader
        self.trust = trust
        self.owner_config_id = owner_config_id
        self.seal = object()
        self.issued: WeakKeyDictionary[object, Mapping[str, Any]] = (
            WeakKeyDictionary()
        )
        self.issue_lock = threading.Lock()
        self.capability_type = _capability_type(self.seal)

    def select(
        self, _manifest: Mapping[str, Any], *, now_epoch: int
    ) -> object:
        del _manifest, now_epoch
        values = self._current_values(selected_at=_now_epoch())
        capability = self.capability_type(values)
        with self.issue_lock:
            self.issued[capability] = values
        return capability

    def consume(self, value: object) -> Mapping[str, Any]:
        expected = _claim_capability(
            value,
            self.capability_type,
            self.seal,
            self.issued,
            self.issue_lock,
        )
        _require_selection_fresh(expected)
        current = self._current_values(
            selected_at=int(expected["selection_issued_at"])
        )
        if dict(current) != dict(expected):
            raise RuntimeArtifactManifestError(
                "manifest_launch_selection_stale"
            )
        return MappingProxyType(dict(current))

    def _current_values(self, *, selected_at: int) -> Mapping[str, Any]:
        with reddog_runtime_artifact_generation_lock(
            self.runtime, repo_root=self.repo, allow_sealed=True
        ):
            activation = self.reader.load()
            if activation is None:
                raise RuntimeArtifactManifestError(
                    "current_generation_not_activated"
                )
            _require_activation_trust(activation, self.trust)
            manifest = _read_manifest(self.repo, self.runtime, activation)
            validate_freshness(
                manifest,
                now_epoch=_now_epoch(),
                max_ttl_seconds=DEFAULT_MAX_TTL_SECONDS,
            )
            _verify_manifest(
                manifest,
                activation,
                self.repo,
                self.runtime,
                Ed25519SignatureVerifier(),
            )
            return _launch_values(
                manifest,
                activation,
                self.repo,
                self.runtime,
                selected_at=selected_at,
                owner_config_id=self.owner_config_id,
            )


class _Boundary:
    __slots__ = ("_select", "_consume")

    def __init__(self, select: Any, consume: Any) -> None:
        self._select = select
        self._consume = consume

    def select(
        self, manifest: Mapping[str, Any], *, now_epoch: int
    ) -> object:
        return self._select(manifest, now_epoch=now_epoch)

    def consume(self, value: object) -> Mapping[str, Any]:
        return self._consume(value)


def _read_manifest(
    repo: Path,
    runtime: Path,
    activation: SignerRuntimeGenerationActivation,
) -> dict[str, Any]:
    target = validate_runtime_artifact_path(
        runtime
        / MANIFEST_DIRECTORY_NAME
        / f"{activation.manifest_id[7:]}.json",
        repo_root=repo,
        allowed_root=runtime,
    )
    if target.is_symlink() or not target.is_file():
        raise RuntimeArtifactManifestError("current_generation_manifest_missing")
    raw, _ = secure_read_confined_bytes(
        target, allowed_root=runtime, max_bytes=MAX_ARTIFACT_BYTES
    )
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeArtifactManifestError(
            "current_generation_manifest_malformed"
        ) from exc
    return validate_signed_payload(value)


def _verify_manifest(
    manifest: Mapping[str, Any],
    activation: SignerRuntimeGenerationActivation,
    repo: Path,
    runtime: Path,
    verifier: Ed25519SignatureVerifier,
) -> None:
    expected = {
        "manifest_id": activation.manifest_id,
        "artifact_generation_digest": activation.artifact_generation_digest,
        "signer_service_config_digest": activation.config_digest,
        "repo_root_digest": raw_digest(str(repo).encode("utf-8")),
        "runtime_root_digest": raw_digest(str(runtime).encode("utf-8")),
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise RuntimeArtifactManifestError(
            "current_generation_manifest_binding_mismatch"
        )
    _verify_signatures(manifest, verifier)
    _verify_artifacts(manifest, repo, runtime, activation)


def _expected_generation_trust(
    anchor_id: str,
    authenticator_id: str,
    high_water_store_id: str,
    high_water_receipt_id: str,
) -> tuple[str, str, str, str]:
    values = (
        _ascii(anchor_id, "anchor_id"),
        _ascii(authenticator_id, "authenticator_id"),
        _ascii(high_water_store_id, "high_water_store_id"),
        str(high_water_receipt_id),
    )
    if not is_sha256(values[3]):
        raise RuntimeArtifactManifestError(
            "current_generation_high_water_receipt_invalid"
        )
    return values


def _require_activation_trust(
    activation: SignerRuntimeGenerationActivation,
    expected: tuple[str, str, str, str],
) -> None:
    actual = (
        activation.anchor_id,
        activation.authenticator_id,
        activation.high_water_store_id,
        activation.high_water_durability_receipt_id,
    )
    if actual != expected:
        raise RuntimeArtifactManifestError(
            "current_generation_trust_anchor_mismatch"
        )


def _verify_signatures(
    manifest: Mapping[str, Any], verifier: Ed25519SignatureVerifier
) -> None:
    public_key = str(manifest["signer_public_key"])
    if manifest["signer_key_fingerprint"] != public_key_fingerprint(public_key):
        raise RuntimeArtifactManifestError("manifest_signer_fingerprint_invalid")
    signing_input = canonical_signing_input(manifest)
    signature = str(manifest["signature"])
    if not verifier.verify(public_key, signing_input, signature):
        raise RuntimeArtifactManifestError("manifest_signature_invalid")
    attestation = canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=signature,
        audit_mac=str(manifest["signer_audit_mac"]),
        signer_public_key=public_key,
        key_epoch=str(manifest["key_epoch"]),
        requester_principal_id=str(manifest["issuer_principal_id"]),
        domain_prefix=RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    )
    if not verifier.verify(
        public_key,
        attestation,
        str(manifest["signer_audit_attestation_signature"]),
    ):
        raise RuntimeArtifactManifestError(
            "manifest_audit_attestation_invalid"
        )


def _verify_artifacts(
    manifest: Mapping[str, Any],
    repo: Path,
    runtime: Path,
    activation: SignerRuntimeGenerationActivation,
) -> None:
    descriptors = tuple(manifest["artifacts"])
    for descriptor in descriptors:
        filename = str(descriptor["filename"])
        target = validate_runtime_artifact_path(
            runtime / filename, repo_root=repo, allowed_root=runtime
        )
        if filename not in REQUIRED_RUNTIME_ARTIFACTS or target.is_symlink():
            raise RuntimeArtifactManifestError("manifest_artifact_invalid")
        raw, _ = secure_read_confined_bytes(
            target, allowed_root=runtime, max_bytes=MAX_ARTIFACT_BYTES
        )
        if (
            len(raw) != descriptor["byte_count"]
            or raw_digest(raw) != descriptor["content_digest"]
        ):
            raise RuntimeArtifactManifestError("manifest_artifacts_changed")
    by_name = {item["filename"]: item for item in descriptors}
    if (
        by_name[CONFIG_FILENAME]["content_digest"] != activation.config_raw_digest
        or by_name[RUN_PACKET_FILENAME]["content_digest"]
        != activation.run_packet_digest
    ):
        raise RuntimeArtifactManifestError(
            "current_generation_artifact_binding_mismatch"
        )


def _launch_values(
    manifest: Mapping[str, Any],
    activation: SignerRuntimeGenerationActivation,
    repo: Path,
    runtime: Path,
    *,
    selected_at: int,
    owner_config_id: str,
) -> Mapping[str, Any]:
    return MappingProxyType(
        {
            "manifest_id": activation.manifest_id,
            "artifact_generation_digest": activation.artifact_generation_digest,
            "config_digest": activation.config_digest,
            "config_raw_digest": activation.config_raw_digest,
            "run_packet_digest": activation.run_packet_digest,
            "generation": activation.generation,
            "generation_revision": activation.revision,
            "selection_issued_at": selected_at,
            "selection_expires_at": selected_at + SELECTION_TTL_SECONDS,
            "owner_config_id": owner_config_id,
            "repo_root": str(repo),
            "runtime_root": str(runtime),
            "config_path": str(runtime / CONFIG_FILENAME),
            "run_packet_path": str(runtime / RUN_PACKET_FILENAME),
        }
    )


def _capability_type(seal: object) -> type:
    class Capability:
        __slots__ = ("_values", "_seal", "__weakref__")

        def __init__(self, values: Mapping[str, Any]) -> None:
            object.__setattr__(self, "_values", values)
            object.__setattr__(self, "_seal", seal)

        def __setattr__(self, name: str, value: Any) -> None:
            del name, value
            raise AttributeError("manifest_launch_selection_immutable")

        def __reduce__(self):
            raise TypeError("manifest_launch_selection_not_serializable")

        def __copy__(self):
            raise TypeError("manifest_launch_selection_not_copyable")

        def __deepcopy__(self, memo: Any):
            del memo
            raise TypeError("manifest_launch_selection_not_copyable")

    return Capability


def _claim_capability(
    value: object,
    capability_type: type,
    seal: object,
    issued: WeakKeyDictionary[object, Mapping[str, Any]],
    issue_lock: threading.Lock,
) -> Mapping[str, Any]:
    if not isinstance(value, capability_type):
        raise RuntimeArtifactManifestError("manifest_launch_selection_unverified")
    with issue_lock:
        expected = issued.pop(value, None)
    actual = object.__getattribute__(value, "_values")
    if (
        object.__getattribute__(value, "_seal") is not seal
        or expected is None
        or dict(actual) != dict(expected)
    ):
        raise RuntimeArtifactManifestError("manifest_launch_selection_unverified")
    return MappingProxyType(dict(actual))


def _require_selection_fresh(value: Mapping[str, Any]) -> None:
    issued_at = value.get("selection_issued_at")
    expires_at = value.get("selection_expires_at")
    now = _now_epoch()
    if (
        type(issued_at) is not int
        or type(expires_at) is not int
        or expires_at - issued_at != SELECTION_TTL_SECONDS
        or issued_at > now
        or expires_at <= now
    ):
        raise RuntimeArtifactManifestError("manifest_launch_selection_expired")


def _ascii(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isascii()
        or len(value) > 1024
    ):
        raise RuntimeArtifactManifestError(
            f"current_generation_{name}_invalid"
        )
    return value.strip()


def _sha256(value: object, name: str) -> str:
    if not is_sha256(value):
        raise RuntimeArtifactManifestError(
            f"current_generation_{name}_invalid"
        )
    return str(value)


def _now_epoch() -> int:
    return int(time.time())


__all__ = [
    "CurrentGenerationLaunchOwnerAuthorityBoundary",
    "create_current_generation_manifest_launch_selection_boundary",
]


del _lookup_owner_authority
del _owner_boundary_require
