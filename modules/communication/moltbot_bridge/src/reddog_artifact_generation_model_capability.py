"""Identity-bound one-shot model-call capability for artifact generation."""

from __future__ import annotations

import json
import secrets
import threading
from typing import Any, Callable, Mapping, Sequence

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    ModelRuntimeBindingVerificationReceipt,
    VerifiedRuntimeBindingCapability,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_evidence_verifier import (
    VerifiedRuntimeBindingArtifact,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_topology_resolver import (
    consume_resolved_runtime_topology,
    discard_resolved_runtime_topology,
    resolve_verified_runtime_topology,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
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
        available_providers: Sequence[str] | None = None,
        trusted_now_epoch: Callable[[], int] | None = None,
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
        if not available_providers or not callable(trusted_now_epoch):
            return None
        try:
            runtime = rehydrate_model_runtime_binding_receipt(runtime_binding)
            now = int(trusted_now_epoch())
            topology = resolve_verified_runtime_topology(
                verified=VerifiedRuntimeBindingArtifact(
                    runtime, verification, verified_capability
                ),
                selection=selection,
                available_providers=available_providers,
                now=now,
                expected_runtime_surface=runtime.runtime_surface,
            )
        except Exception:
            return None
        token = secrets.token_urlsafe(32)
        capability = ArtifactGenerationModelCapability(token)
        binding_json = _json(trusted)
        with lock:
            records[token] = (
                capability,
                binding_json,
                artifact_generation_digest(trusted),
                topology,
                trusted_now_epoch,
            )
        return capability

    return issue


def _consume_closure(lock: Any, records: Any):
    def consume(capability: Any) -> dict[str, Any] | None:
        record = _take_record(lock, records, capability)
        if record is None:
            return None
        _, binding_json, binding_digest, topology, trusted_now_epoch = record
        binding = json.loads(binding_json)
        if binding_digest != artifact_generation_digest(binding):
            discard_resolved_runtime_topology(topology)
            return None
        endpoints = consume_resolved_runtime_topology(
            topology, trusted_now_epoch=trusted_now_epoch
        )
        if endpoints is None or not _topology_matches(binding, endpoints):
            return None
        binding["resolved_runtime_topology"] = [item.to_dict() for item in endpoints]
        binding["runtime_topology_resolution_receipt_id"] = topology.receipt_id
        binding["runtime_topology_verification_receipt_id"] = (
            topology.verification_receipt_id
        )
        return binding

    return consume


def _discard_closure(lock: Any, records: Any):
    def discard(capability: Any) -> None:
        record = _take_record(lock, records, capability)
        if record is not None:
            discard_resolved_runtime_topology(record[-2])

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


def _topology_matches(binding: Mapping[str, Any], endpoints: Sequence[Any]) -> bool:
    selection = binding.get("model_selection")
    assignments = selection.get("role_assignments") if isinstance(selection, Mapping) else None
    if not isinstance(assignments, list) or len(assignments) != len(endpoints):
        return False
    expected = tuple(
        (
            str(item.get("role") or ""),
            str(item.get("provider") or ""),
            str(item.get("canonical_model_id") or ""),
        )
        for item in assignments
        if isinstance(item, Mapping)
    )
    actual = tuple((item.role, item.provider, item.model_id) for item in endpoints)
    return len(expected) == len(endpoints) and expected == actual


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
