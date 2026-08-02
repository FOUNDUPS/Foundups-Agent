"""Compose bounded artifact providers without growing the resident bootstrap."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .reddog_artifact_generation_provider_modes import (
    RUNTIME_MODE_FOUNDUPS_FUSION,
    RUNTIME_MODE_HERMES_API,
    RUNTIME_MODE_OPENCLAW_GATEWAY,
    normalize_artifact_generator_mode,
)
from .reddog_model_runtime_verifier_bootstrap import (
    ModelRuntimeVerifierConfig,
    build_model_runtime_verifier,
)
from .reddog_artifact_generation_result import (
    rehydrate_bounded_artifact_generation_receipt,
)

OPENCLAW_ARTIFACT_AGENT_ID = "reddog-artifact"


@dataclass(frozen=True)
class ArtifactProviderDependencies:
    """Process-local dependencies that cannot be reconstructed from JSON."""

    openclaw_command_runner: Any = None


def build_artifact_generator(
    *,
    injected_runner: Any,
    mode: str | None,
    repo_root: Path,
    runtime_root: Path,
    dependencies: ArtifactProviderDependencies | None = None,
) -> tuple[Any, tuple[str, ...]]:
    """Build one canonical provider or fail closed on an unknown mode."""
    if injected_runner is not None:
        return injected_runner, ()
    normalized = normalize_artifact_generator_mode(mode)
    if not normalized:
        reasons = () if not str(mode or "").strip() else ("unsupported_artifact_generator_mode",)
        return None, reasons
    supplied = dependencies or ArtifactProviderDependencies()
    if normalized == RUNTIME_MODE_OPENCLAW_GATEWAY:
        return _build_openclaw(repo_root, runtime_root, supplied)
    if normalized == RUNTIME_MODE_HERMES_API:
        return _build_hermes(supplied)
    if normalized != RUNTIME_MODE_FOUNDUPS_FUSION:
        return None, ("unsupported_artifact_generator_mode",)
    from .reddog_bounded_artifact_generation_runtime import (
        FoundupsFusionArtifactGenerationRunner,
    )

    return FoundupsFusionArtifactGenerationRunner(
        runtime_mode=RUNTIME_MODE_FOUNDUPS_FUSION
    ), ()


def build_generation_dependencies(
    root: Path,
    runtime_root: Path,
    artifact_generator: Any,
    artifact_generator_mode: str | None,
    model_verifier: Any,
    verifier_config: ModelRuntimeVerifierConfig | Mapping[str, Any] | None,
    trusted_now: Callable[[], int],
    provider_dependencies: ArtifactProviderDependencies | None = None,
    verifier_builder: Callable[..., Any] = build_model_runtime_verifier,
) -> tuple[Any, Any, tuple[str, ...]]:
    """Compose provider and signed model verifier for the resident loop."""
    generator, reasons = build_artifact_generator(
        injected_runner=artifact_generator,
        mode=artifact_generator_mode,
        repo_root=root,
        runtime_root=runtime_root,
        dependencies=provider_dependencies,
    )
    if reasons:
        return None, None, reasons
    verifier, reasons = verifier_builder(
        repo_root=root,
        runtime_root=runtime_root,
        config=verifier_config,
        trusted_now=trusted_now,
        injected=model_verifier,
        artifact_generator=generator,
    )
    return generator, verifier, reasons


def read_artifact_provider_effects(chain_results_path: Path) -> dict[str, Any]:
    """Read provider effect truth from the canonical chain-results stage."""
    try:
        state = json.loads(chain_results_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        state = {}
    stages = state.get("stage_results") if isinstance(state, Mapping) else None
    pilot = stages.get("bounded_worker_pilot") if isinstance(stages, Mapping) else None
    generation = pilot.get("artifact_generation_result") if isinstance(pilot, Mapping) else None
    value = generation if isinstance(generation, Mapping) else {}
    if not value:
        return {
            "runtime": "none", "invoked": False, "worker_process_started": False,
            "worker_process_spawn_count": 0, "hermes": False,
            "file_write_performed": False, "external_side_effects_possible": False,
            "effect_observation_complete": True, "run_abort_confirmed": True,
        }
    receipt_value = value.get("receipt") if isinstance(value, Mapping) else None
    receipt = rehydrate_bounded_artifact_generation_receipt(receipt_value or {})
    if receipt is None:
        return {
            "runtime": "none",
            "invoked": False,
            "worker_process_started": False,
            "worker_process_spawn_count": 0,
            "hermes": False,
            "file_write_performed": False,
            "external_side_effects_possible": False,
            "effect_observation_complete": False,
            "run_abort_confirmed": False,
        }
    return {
        "runtime": receipt.provider_runtime,
        "invoked": receipt.provider_invocation_performed,
        "worker_process_started": receipt.worker_process_started,
        "worker_process_spawn_count": receipt.worker_process_spawn_count,
        "hermes": receipt.hermes_dispatch_performed,
        "file_write_performed": not receipt.no_file_write_performed,
        "external_side_effects_possible": receipt.external_side_effects_possible,
        "effect_observation_complete": receipt.effect_observation_complete,
        "run_abort_confirmed": receipt.run_abort_confirmed,
    }


def _build_openclaw(
    repo_root: Path,
    runtime_root: Path,
    dependencies: ArtifactProviderDependencies,
) -> tuple[Any, tuple[str, ...]]:
    from .reddog_openclaw_gateway_artifact_provider import (
        OpenClawGatewayArtifactGenerationRunner,
    )

    runner = dependencies.openclaw_command_runner
    if runner is None:
        from .reddog_openclaw_gateway_command_runner import SystemOpenClawCommandRunner
        from modules.infrastructure.dependency_launcher.src.wsl_agent_runtime import (
            DEFAULT_DISTRO,
        )

        runner = SystemOpenClawCommandRunner(distro=DEFAULT_DISTRO)
    return OpenClawGatewayArtifactGenerationRunner(
        repo_root=repo_root,
        runtime_root=runtime_root / "openclaw-artifacts",
        agent_id=OPENCLAW_ARTIFACT_AGENT_ID,
        command_runner=runner,
    ), ()


def _build_hermes(
    dependencies: ArtifactProviderDependencies,
) -> tuple[Any, tuple[str, ...]]:
    del dependencies
    return None, ("missing_hermes_authenticated_service_identity",)


__all__ = [
    "ArtifactProviderDependencies",
    "OPENCLAW_ARTIFACT_AGENT_ID",
    "build_artifact_generator",
    "build_generation_dependencies",
    "read_artifact_provider_effects",
]
