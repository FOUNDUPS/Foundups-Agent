"""Identity-bound one-shot authority for bounded artifact generation."""

from __future__ import annotations

import secrets
import threading
from typing import Any, Mapping

from .reddog_artifact_generation_model_binding import artifact_generation_digest


class ArtifactGenerationAuthorityCapability:
    """Opaque handle whose trusted request state remains registry-owned."""

    __slots__ = ("__token",)

    def __init__(self, token: str) -> None:
        object.__setattr__(self, "_ArtifactGenerationAuthorityCapability__token", token)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("artifact_generation_authority_capability_is_immutable")

    def __copy__(self) -> "ArtifactGenerationAuthorityCapability":
        raise TypeError("artifact_generation_authority_capability_copy_forbidden")

    def __deepcopy__(self, _memo: dict[int, Any]) -> "ArtifactGenerationAuthorityCapability":
        raise TypeError("artifact_generation_authority_capability_copy_forbidden")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("artifact_generation_authority_capability_pickle_forbidden")


def _build_authority_api():
    lock = threading.Lock()
    records: dict[str, tuple[ArtifactGenerationAuthorityCapability, str, str]] = {}

    def issue(
        request: Mapping[str, Any],
    ) -> ArtifactGenerationAuthorityCapability | None:
        work_order_id = str(request.get("work_order_id") or "").strip()
        if not work_order_id:
            return None
        token = secrets.token_urlsafe(32)
        capability = ArtifactGenerationAuthorityCapability(token)
        with lock:
            records[token] = (
                capability,
                work_order_id,
                artifact_generation_digest(request),
            )
        return capability

    def consume(capability: Any, request: Mapping[str, Any]) -> bool:
        if type(capability) is not ArtifactGenerationAuthorityCapability:
            return False
        token = _token(capability)
        with lock:
            record = records.get(token)
            if record is None or record[0] is not capability:
                return False
            records.pop(token, None)
        return (
            record[1] == str(request.get("work_order_id") or "")
            and record[2] == artifact_generation_digest(request)
        )

    return issue, consume


def _token(capability: ArtifactGenerationAuthorityCapability) -> str:
    return object.__getattribute__(
        capability, "_ArtifactGenerationAuthorityCapability__token"
    )


_issue_artifact_generation_authority, consume_artifact_generation_authority = (
    _build_authority_api()
)
del _build_authority_api


__all__ = [
    "ArtifactGenerationAuthorityCapability",
    "consume_artifact_generation_authority",
]
