"""Typed capabilities and values for signer runtime generation authority."""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_CONFIG,
    GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS,
    REQUIRED_RUNTIME_ARTIFACTS,
    RuntimeArtifactManifestError,
    required_runtime_artifacts_for,
)


def _build_process_local_registry(error: str):
    lock = threading.RLock()
    records: WeakKeyDictionary[object, Any] = WeakKeyDictionary()

    def issue(key: object, value: Any) -> None:
        with lock:
            if key in records:
                raise ValueError(f"{error}_already_issued")
            records[key] = value

    def lookup(key: object) -> Any:
        with lock:
            try:
                return records[key]
            except KeyError as exc:
                raise ValueError(error) from exc

    return issue, lookup


class SignerRuntimeGenerationSigner(Protocol):
    @property
    def authenticator_id(self) -> str: ...

    def authenticate(self, payload: bytes) -> str: ...


class SignerRuntimeGenerationVerifier(Protocol):
    @property
    def authenticator_id(self) -> str: ...

    def verify(self, payload: bytes, authentication_tag: str) -> bool: ...


@dataclass(frozen=True)
class SignerRuntimeGenerationHighWater:
    generation: int
    revision: str


@dataclass(frozen=True)
class SignerRuntimeGenerationPendingAdvance:
    transaction_id: str
    expected: SignerRuntimeGenerationHighWater | None
    next_value: SignerRuntimeGenerationHighWater
    previous_anchor_state_json: str = "{}"


@runtime_checkable
class SignerRuntimeGenerationHighWaterStore(Protocol):
    @property
    def store_id(self) -> str: ...

    @property
    def durability_receipt_id(self) -> str: ...

    @property
    def rollback_domain_root(self) -> Path: ...

    @property
    def witness_rollback_domain_root(self) -> Path: ...

    def witness_load(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationHighWater | None: ...

    def witness_advance(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
    ) -> None: ...

    def load(self, anchor_id: str) -> SignerRuntimeGenerationHighWater | None: ...

    def advance(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
    ) -> None: ...


@runtime_checkable
class TransactionalSignerRuntimeGenerationHighWaterStore(
    SignerRuntimeGenerationHighWaterStore,
    Protocol,
):
    def pending(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationPendingAdvance | None: ...

    def prepare(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
        previous_anchor_state_json: str = "{}",
    ) -> SignerRuntimeGenerationPendingAdvance: ...

    def commit_prepared(self, anchor_id: str, transaction_id: str) -> None: ...

    def abort_prepared(self, anchor_id: str, transaction_id: str) -> None: ...


@dataclass(frozen=True)
class VerifiedSignerRuntimeGenerationHighWater:
    store: SignerRuntimeGenerationHighWaterStore
    store_id: str
    durability_receipt_id: str


class SignerRuntimeGenerationHighWaterAuthorityBoundary(Protocol):
    def require(
        self, value: object
    ) -> VerifiedSignerRuntimeGenerationHighWater: ...


@dataclass(frozen=True)
class SignerRuntimeGenerationBinding:
    generation: int
    manifest_id: str
    artifact_generation_digest: str
    config_digest: str
    config_raw_digest: str
    run_packet_digest: str


@dataclass(frozen=True)
class SignerRuntimeGenerationActivation:
    anchor_id: str
    generation: int
    manifest_id: str
    artifact_generation_digest: str
    config_digest: str
    config_raw_digest: str
    run_packet_digest: str
    previous_revision: str | None
    authenticator_id: str
    high_water_store_id: str
    high_water_durability_receipt_id: str
    authentication_tag: str
    revision: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignerRuntimeGenerationRecoveryOutcome:
    """Typed evidence describing one authenticated recovery attempt."""

    activation: SignerRuntimeGenerationActivation | None
    pending_completed: bool
    committed_witness_recovered: bool


def signer_runtime_generation_binding_from_manifest(
    manifest: Mapping[str, Any], *, generation: int
) -> SignerRuntimeGenerationBinding:
    """Project one validated profile's launch digests into generation state."""

    required = required_runtime_artifacts_for(manifest)
    if required == REQUIRED_RUNTIME_ARTIFACTS:
        config_name, run_packet_name = required[-2:]
    elif required == REQUIRED_GRANT_AUTHORITY_RUNTIME_ARTIFACTS:
        config_name = GRANT_AUTHORITY_SERVICE_CONFIG
        run_packet_name = GRANT_AUTHORITY_SERVICE_RUN_PACKET
    else:
        raise RuntimeArtifactManifestError("manifest_launch_artifacts_missing")
    descriptors = {
        str(item.get("filename") or ""): item
        for item in manifest["artifacts"]
        if isinstance(item, Mapping)
    }
    config = descriptors.get(config_name)
    run_packet = descriptors.get(run_packet_name)
    if not config or not run_packet:
        raise RuntimeArtifactManifestError("manifest_launch_artifacts_missing")
    return SignerRuntimeGenerationBinding(
        generation=generation,
        manifest_id=str(manifest["manifest_id"]),
        artifact_generation_digest=str(manifest["artifact_generation_digest"]),
        config_digest=str(manifest["signer_service_config_digest"]),
        config_raw_digest=str(config["content_digest"]),
        run_packet_digest=str(run_packet["content_digest"]),
    )


__all__ = [
    "SignerRuntimeGenerationActivation",
    "SignerRuntimeGenerationBinding",
    "SignerRuntimeGenerationHighWater",
    "SignerRuntimeGenerationHighWaterAuthorityBoundary",
    "SignerRuntimeGenerationHighWaterStore",
    "SignerRuntimeGenerationPendingAdvance",
    "SignerRuntimeGenerationRecoveryOutcome",
    "SignerRuntimeGenerationSigner",
    "SignerRuntimeGenerationVerifier",
    "signer_runtime_generation_binding_from_manifest",
    "TransactionalSignerRuntimeGenerationHighWaterStore",
    "VerifiedSignerRuntimeGenerationHighWater",
]
