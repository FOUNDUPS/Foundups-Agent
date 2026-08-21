"""Final no-stale-time verification and APPLIED transition."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from .model_autoresearch_production_binding_freshness import (
    refresh_production_authority,
)
from .model_autoresearch_production_binding_json import read_production_json
from .model_autoresearch_production_binding_temporal import (
    pure_recheck_production_time,
)
from .model_autoresearch_production_binding_transaction import advance_publication


def verify_current_production_time(
    inputs: dict[str, Any],
    bundle: Mapping[str, Any],
    runtime_path: Path,
    verifier: Callable[[Mapping[str, Any], Mapping[str, Any]], tuple[Any, ...]],
) -> None:
    refresh_production_authority(inputs)
    values = verifier(inputs, bundle)
    runtime = read_production_json(
        runtime_path, "single_model_production_runtime_artifact_invalid"
    )
    pure_recheck_production_time(inputs, values, runtime)


def complete_production_publication(
    inputs: dict[str, Any],
    bundle: Mapping[str, Any],
    publication: tuple[str, str, tuple[tuple[str, str], ...]],
    verifier: Callable[[Mapping[str, Any], Mapping[str, Any]], tuple[Any, ...]],
) -> None:
    verify_current_production_time(
        inputs, bundle, inputs["output_transaction"].runtime_stage, verifier
    )
    nonce, binding, _evidence = publication
    advance_publication(
        inputs["authority_use"].publication_store,
        nonce=nonce,
        binding_digest=binding,
        target_status="APPLIED",
    )


__all__ = ["complete_production_publication", "verify_current_production_time"]
