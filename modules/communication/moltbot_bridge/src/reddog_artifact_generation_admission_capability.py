"""Process-local, one-shot admission for bounded artifact model calls."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    ModelRuntimeBindingVerificationReceipt,
    VerifiedRuntimeBindingCapability,
    consume_verified_runtime_binding_capability,
    discard_verified_runtime_binding_capability,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_model_binding import (
    artifact_generation_digest,
    verified_artifact_generation_binding,
)

_digest = artifact_generation_digest


@dataclass(frozen=True, slots=True)
class ArtifactGenerationAuthorityCapability:
    work_order_id: str
    request_digest: str
    _seal: object


@dataclass(frozen=True, slots=True)
class ArtifactGenerationModelCapability:
    binding_json: str
    binding_digest: str
    _seal: object

    def to_dict(self) -> dict[str, Any]:
        value = json.loads(self.binding_json)
        return value if isinstance(value, dict) else {}


class InMemoryArtifactGenerationCapabilityRegistry:
    def __init__(self) -> None:
        self._seal = object()
        self._lock = threading.Lock()
        self._authority: dict[int, ArtifactGenerationAuthorityCapability] = {}
        self._models: dict[int, tuple[Any, ...]] = {}

    def issue_authority(
        self,
        request: Mapping[str, Any],
    ) -> Optional[ArtifactGenerationAuthorityCapability]:
        work_order_id = str(request.get("work_order_id") or "").strip()
        if not work_order_id:
            return None
        capability = ArtifactGenerationAuthorityCapability(
            work_order_id=work_order_id,
            request_digest=_digest(request),
            _seal=self._seal,
        )
        with self._lock:
            self._authority[id(capability)] = capability
        return capability

    def consume_authority(
        self,
        capability: Any,
        request: Mapping[str, Any],
    ) -> bool:
        with self._lock:
            expected = self._authority.pop(id(capability), None)
        return bool(
            expected is not None
            and expected is capability
            and expected._seal is self._seal
            and expected.work_order_id == str(request.get("work_order_id") or "")
            and expected.request_digest == _digest(request)
        )

    def issue_model(
        self,
        *,
        invocation_binding: Mapping[str, Any],
        runtime_binding: Mapping[str, Any],
        selection: Mapping[str, Any],
        verification: ModelRuntimeBindingVerificationReceipt,
        verified_capability: VerifiedRuntimeBindingCapability,
    ) -> Optional[ArtifactGenerationModelCapability]:
        if type(verified_capability) is not VerifiedRuntimeBindingCapability:
            return None
        trusted_binding = verified_artifact_generation_binding(
            invocation_binding=invocation_binding,
            runtime_binding=runtime_binding,
            selection=selection,
            verification=verification,
        )
        if trusted_binding is None:
            return None
        binding_json = json.dumps(
            trusted_binding,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
        capability = ArtifactGenerationModelCapability(
            binding_json=binding_json,
            binding_digest=_digest(trusted_binding),
            _seal=self._seal,
        )
        with self._lock:
            self._models[id(capability)] = (
                capability,
                dict(runtime_binding),
                dict(selection),
                verification,
                verified_capability,
            )
        return capability

    def consume_model(
        self,
        capability: Any,
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            admission = self._models.pop(id(capability), None)
        if admission is None:
            return None
        expected, runtime_binding, selection, verification, verified_capability = (
            admission
        )
        if (
            expected is not capability
            or expected._seal is not self._seal
        ):
            discard_verified_runtime_binding_capability(verified_capability)
            return None
        binding = expected.to_dict()
        if expected.binding_digest != _digest(binding):
            discard_verified_runtime_binding_capability(verified_capability)
            return None
        verified = consume_verified_runtime_binding_capability(
            verified_capability,
            binding=runtime_binding,
            selection=selection,
            receipt=verification,
        )
        return binding if verified is not None else None

    def discard_model(self, capability: Any) -> None:
        with self._lock:
            admission = self._models.pop(id(capability), None)
        if admission is not None:
            discard_verified_runtime_binding_capability(admission[-1])


_REGISTRY = InMemoryArtifactGenerationCapabilityRegistry()


def _issue_artifact_generation_authority(
    request: Mapping[str, Any],
) -> Optional[ArtifactGenerationAuthorityCapability]:
    return _REGISTRY.issue_authority(request)


def consume_artifact_generation_authority(
    capability: Any,
    request: Mapping[str, Any],
) -> bool:
    return _REGISTRY.consume_authority(capability, request)


def _issue_artifact_generation_model(
    *,
    invocation_binding: Mapping[str, Any],
    runtime_binding: Mapping[str, Any],
    selection: Mapping[str, Any],
    verification: ModelRuntimeBindingVerificationReceipt,
    verified_capability: VerifiedRuntimeBindingCapability,
) -> Optional[ArtifactGenerationModelCapability]:
    return _REGISTRY.issue_model(
        invocation_binding=invocation_binding,
        runtime_binding=runtime_binding,
        selection=selection,
        verification=verification,
        verified_capability=verified_capability,
    )


def consume_artifact_generation_model(
    capability: Any,
) -> Optional[dict[str, Any]]:
    return _REGISTRY.consume_model(capability)


def discard_artifact_generation_model(capability: Any) -> None:
    _REGISTRY.discard_model(capability)


__all__ = ["ArtifactGenerationAuthorityCapability", "ArtifactGenerationModelCapability", "consume_artifact_generation_authority", "consume_artifact_generation_model", "discard_artifact_generation_model"]
