"""Provider contract for bounded RedDog artifact generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Protocol

from .reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
)

MAX_PROVIDER_ARTIFACT_BYTES = 64 * 1024
MAX_PROVIDER_ARTIFACT_TOTAL_BYTES = 256 * 1024
_WINDOWS_DEVICE_NAMES = {
    "aux", "clock$", "con", "conin$", "conout$", "nul", "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def validate_provider_artifact_contents(value: object) -> Dict[str, str] | None:
    """Return a canonical, bounded relative-path artifact map or fail closed."""
    if not isinstance(value, Mapping) or not value:
        return None
    result: Dict[str, str] = {}
    total = 0
    for path, content in value.items():
        if not _safe_provider_artifact_path(path) or not isinstance(content, str):
            return None
        if not content.strip() or "\x00" in content:
            return None
        try:
            size = len(content.encode("utf-8"))
        except UnicodeEncodeError:
            return None
        total += size
        if size > MAX_PROVIDER_ARTIFACT_BYTES or total > MAX_PROVIDER_ARTIFACT_TOTAL_BYTES:
            return None
        result[path] = content
    return result


def _safe_provider_artifact_path(value: object) -> bool:
    if not isinstance(value, str) or value != value.strip() or len(value) > 512:
        return False
    if not value or value.startswith("/") or "\\" in value or ":" in value or "\x00" in value:
        return False
    if any(character in '<>"|?*' for character in value):
        return False
    parts = value.split("/")
    if any(not part or part in {".", ".."} or part != part.rstrip(" .") for part in parts):
        return False
    if any(any(ord(character) < 32 for character in part) for part in parts):
        return False
    return all(part.split(".", 1)[0].casefold() not in _WINDOWS_DEVICE_NAMES for part in parts)


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
    "validate_provider_artifact_contents",
]
