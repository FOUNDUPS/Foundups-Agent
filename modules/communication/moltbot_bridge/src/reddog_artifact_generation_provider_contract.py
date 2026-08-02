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
    provider_runtime: str = "none"
    provider_invocation_performed: bool = False
    worker_process_started: bool = False
    worker_process_spawn_count: int = 0
    hermes_dispatch_performed: bool = False
    file_write_performed: bool = False
    external_side_effects_possible: bool = False
    effect_observation_complete: bool = True
    run_abort_confirmed: bool = True

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
