"""Result and receipt construction for bounded artifact generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence

from .reddog_artifact_generation_model_binding import artifact_generation_digest
from .reddog_artifact_generation_provider_contract import ArtifactGenerationModelResult
from .reddog_artifact_generation_receipt import (
    BoundedArtifactGenerationReceipt,
    artifact_generation_receipt_id as _receipt_id,
    rehydrate_bounded_artifact_generation_receipt,
)

ARTIFACT_GENERATION_ACCEPT = "BOUNDED_ARTIFACT_GENERATION_ACCEPT"
ARTIFACT_GENERATION_REJECT = "BOUNDED_ARTIFACT_GENERATION_REJECT"
@dataclass(frozen=True)
class BoundedArtifactGenerationResult:
    decision: str
    accepted: bool
    artifact_contents: Dict[str, str]
    rejection_reasons: List[str]
    receipt: BoundedArtifactGenerationReceipt
    model_result: ArtifactGenerationModelResult | None = None
    no_file_write_performed: bool = True
    no_shell_command_executed: bool = True
    no_worktree_created: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    provider_runtime: str = "none"
    provider_invocation_performed: bool = False
    worker_process_started: bool = False
    worker_process_spawn_count: int = 0
    hermes_dispatch_performed: bool = False
    external_side_effects_possible: bool = False
    effect_observation_complete: bool = True
    run_abort_confirmed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
        payload["model_result"] = self.model_result.to_dict() if self.model_result else None
        return payload


def build_generation_result(
    request: Mapping[str, Any],
    *,
    planned: Sequence[str],
    model_selection: Mapping[str, Any],
    model_result: ArtifactGenerationModelResult | None,
    artifacts: Mapping[str, str],
    reasons: Sequence[str],
) -> BoundedArtifactGenerationResult:
    deduped = list(dict.fromkeys(str(item) for item in reasons if str(item)))
    work_order_id = str(request.get("work_order_id") or "")
    slice_name = str(request.get("slice_name") or "")
    manifest = artifact_generation_digest({"artifact_contents": artifacts})
    receipt_values = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "planned_artifacts": list(planned),
        "artifact_manifest_digest": manifest,
        "model_result_digest": model_result.model_result_digest if model_result else "",
        "model_receipt_id": model_result.model_receipt_id if model_result else None,
        "rejection_reasons": deduped,
        "accepted": not deduped,
        **_provider_effects(model_result),
        **_lineage(model_selection),
    }
    provisional = BoundedArtifactGenerationReceipt(receipt_id="", **receipt_values)
    canonical_values = provisional.to_dict()
    canonical_values.pop("receipt_id")
    receipt = BoundedArtifactGenerationReceipt(
        receipt_id=_receipt_id(canonical_values), **receipt_values
    )
    return BoundedArtifactGenerationResult(
        decision=ARTIFACT_GENERATION_REJECT if deduped else ARTIFACT_GENERATION_ACCEPT,
        accepted=not deduped,
        artifact_contents=dict(artifacts) if not deduped else {},
        rejection_reasons=deduped,
        receipt=receipt,
        model_result=model_result,
        **_provider_effects(model_result),
    )


def _provider_effects(
    result: ArtifactGenerationModelResult | None,
) -> dict[str, Any]:
    return {
        "provider_runtime": result.provider_runtime if result else "none",
        "provider_invocation_performed": bool(
            result and result.provider_invocation_performed
        ),
        "worker_process_started": bool(result and result.worker_process_started),
        "worker_process_spawn_count": int(
            result.worker_process_spawn_count if result else 0
        ),
        "hermes_dispatch_performed": bool(
            result and result.hermes_dispatch_performed
        ),
        "no_file_write_performed": not bool(result and result.file_write_performed),
        "external_side_effects_possible": bool(
            result and result.external_side_effects_possible
        ),
        "effect_observation_complete": bool(
            result is None or result.effect_observation_complete
        ),
        "run_abort_confirmed": bool(result is None or result.run_abort_confirmed),
    }


def _lineage(selection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model_selection_receipt_id": selection.get("receipt_id"),
        "model_selection_digest": selection.get("digest", ""),
        "model_runtime_binding_receipt_id": selection.get("model_runtime_binding_receipt_id"),
        "model_runtime_binding_digest": selection.get("model_runtime_binding_digest", ""),
        "model_runtime_binding_verification_receipt_id": selection.get(
            "model_runtime_binding_verification_receipt_id"
        ),
        "model_runtime_binding_verification_digest": selection.get(
            "model_runtime_binding_verification_digest", ""
        ),
    }


__all__ = [
    "ARTIFACT_GENERATION_ACCEPT",
    "ARTIFACT_GENERATION_REJECT",
    "BoundedArtifactGenerationReceipt",
    "BoundedArtifactGenerationResult",
    "build_generation_result",
    "rehydrate_bounded_artifact_generation_receipt",
]
