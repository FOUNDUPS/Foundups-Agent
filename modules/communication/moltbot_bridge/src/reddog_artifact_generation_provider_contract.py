"""Provider contract for bounded RedDog artifact generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Protocol, Sequence

from prompt.swarm.m2m_compiler import decode_m2m_envelope, encode_m2m_envelope
from .reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
)
from .reddog_artifact_generation_model_binding import artifact_generation_digest

FAIL_M2M_PROMPT_BINDING = "FAIL_ARTIFACT_GENERATION_M2M_PROMPT_BINDING"
MAX_PROVIDER_ARTIFACT_BYTES = 64 * 1024
MAX_PROVIDER_ARTIFACT_TOTAL_BYTES = 256 * 1024
_WINDOWS_DEVICE_NAMES = {
    "aux", "clock$", "con", "conin$", "conout$", "nul", "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def artifact_generation_output_contract(planned: Sequence[str]) -> dict[str, Any]:
    """Existing artifact rules, separate from the canonical worker instruction."""
    return {
        "planned_artifacts": list(planned),
        "output_schema": {"artifact_contents": {"path": "text content"}},
        "hard_rules": [
            "Return JSON only.",
            "Keys must exactly match planned_artifacts.",
            "Do not include secrets, credentials, tokens, or private keys.",
            "Do not create extra files.",
        ],
    }


def validate_provider_m2m_prompt(
    binding: Mapping[str, Any], prompt: str, redacted_prompt: str,
) -> bool:
    """Check the sealed canonical prompt before egress; legacy context is unbound.

    Both mode and digest originate in runtime preparation, never caller text.
    Missing either bound field rejects. An entirely legacy binding cannot carry
    a complete canonical packet, including one introduced by redaction.
    """
    if not isinstance(binding, Mapping):
        return False
    if "prompt_schema" not in binding and "m2m_prompt_digest" not in binding:
        for wire in (prompt, redacted_prompt):
            try:
                decode_m2m_envelope(wire)
            except ValueError:
                continue
            return False
        return True
    expected = binding.get("m2m_prompt_digest")
    if binding.get("prompt_schema") != "0102_m2m_v1" or type(expected) is not str:
        return False
    try:
        canonical = encode_m2m_envelope(decode_m2m_envelope(prompt))
    except ValueError:
        return False
    return (
        canonical == prompt
        and type(redacted_prompt) is str
        and artifact_generation_digest(canonical) == expected
        and artifact_generation_digest(redacted_prompt) == expected
    )


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
    # Exact provider routes proven available for this configured runner instance.
    # This is deliberately not a broad list of providers the upstream product
    # could theoretically support.
    available_model_providers: Sequence[str]

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
    "FAIL_M2M_PROMPT_BINDING",
    "artifact_generation_output_contract",
    "validate_provider_m2m_prompt",
    "validate_provider_artifact_contents",
]
