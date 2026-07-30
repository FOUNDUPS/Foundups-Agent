"""Provider contract for bounded RedDog artifact generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Protocol

from .reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
)


@dataclass(frozen=True)
class ArtifactGenerationModelResult:
    ok: bool
    status: str
    artifact_contents: Mapping[str, str] = field(default_factory=dict)
    model_receipt_id: str | None = None
    model_result_digest: str = ""
    made_network_call: bool = False
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BoundedArtifactGenerationRunner(Protocol):
    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult: ...


__all__ = [
    "ArtifactGenerationModelResult",
    "BoundedArtifactGenerationRunner",
]
