"""Identity-bound one-shot model-call capability for artifact generation."""

from __future__ import annotations

import json
import secrets
import threading
from typing import Any, Mapping

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    ModelRuntimeBindingVerificationReceipt,
    VerifiedRuntimeBindingCapability,
    consume_verified_runtime_binding_capability,
    discard_verified_runtime_binding_capability,
)

from .reddog_artifact_generation_model_binding import (
    artifact_generation_digest,
    verified_artifact_generation_binding,
)


class ArtifactGenerationModelCapability:
    """Opaque handle whose trusted provider binding remains registry-owned."""

    __slots__ = ("__token",)

    def __init__(self, token: str) -> None:
        object.__setattr__(self, "_ArtifactGenerationModelCapability__token", token)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("artifact_generation_model_capability_is_immutable")

    def __copy__(self) -> "ArtifactGenerationModelCapability":
        raise TypeError("artifact_generation_model_capability_copy_forbidden")

    def __deepcopy__(self, _memo: dict[int, Any]) -> "ArtifactGenerationModelCapability":
        raise TypeError("artifact_generation_model_capability_copy_forbidden")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("artifact_generation_model_capability_pickle_forbidden")


def _build_model_api():
    lock = threading.Lock()
    records: dict[str, tuple[Any, ...]] = {}
    issue = _issue_closure(lock, records)
    consume = _consume_closure(lock, records)
    discard = _discard_closure(lock, records)
    return issue, consume, discard


def _issue_closure(lock: Any, records: Any):
    def issue(
        *,
        invocation_binding: Mapping[str, Any],
        runtime_binding: Mapping[str, Any],
        selection: Mapping[str, Any],
        verification: ModelRuntimeBindingVerificationReceipt,
        verified_capability: VerifiedRuntimeBindingCapability,
    ) -> ArtifactGenerationModelCapability | None:
        if type(verified_capability) is not VerifiedRuntimeBindingCapability:
            return None
        trusted = verified_artifact_generation_binding(
            invocation_binding=invocation_binding,
            runtime_binding=runtime_binding,
            selection=selection,
            verification=verification,
        )
        if trusted is None:
            return None
        token = secrets.token_urlsafe(32)
        capability = ArtifactGenerationModelCapability(token)
        binding_json = _json(trusted)
        with lock:
            records[token] = (
                capability,
                binding_json,
                artifact_generation_digest(trusted),
                dict(runtime_binding),
                dict(selection),
                verification,
                verified_capability,
            )
        return capability

    return issue


def _consume_closure(lock: Any, records: Any):
    def consume(capability: Any) -> dict[str, Any] | None:
        record = _take_record(lock, records, capability)
        if record is None:
            return None
        _, binding_json, binding_digest, runtime, selection, receipt, verified = record
        binding = json.loads(binding_json)
        if binding_digest != artifact_generation_digest(binding):
            discard_verified_runtime_binding_capability(verified)
            return None
        accepted = consume_verified_runtime_binding_capability(
            verified,
            binding=runtime,
            selection=selection,
            receipt=receipt,
        )
        return binding if accepted is not None else None

    return consume


def _discard_closure(lock: Any, records: Any):
    def discard(capability: Any) -> None:
        record = _take_record(lock, records, capability)
        if record is not None:
            discard_verified_runtime_binding_capability(record[-1])

    return discard


def _take_record(lock: Any, records: Any, capability: Any) -> tuple[Any, ...] | None:
    if type(capability) is not ArtifactGenerationModelCapability:
        return None
    token = _token(capability)
    with lock:
        record = records.get(token)
        if record is None or record[0] is not capability:
            return None
        return records.pop(token)


def _token(capability: ArtifactGenerationModelCapability) -> str:
    return object.__getattribute__(
        capability, "_ArtifactGenerationModelCapability__token"
    )


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


(
    _issue_artifact_generation_model,
    consume_artifact_generation_model,
    discard_artifact_generation_model,
) = _build_model_api()
del _build_model_api


__all__ = [
    "ArtifactGenerationModelCapability",
    "consume_artifact_generation_model",
    "discard_artifact_generation_model",
]
