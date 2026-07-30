"""Result and receipt construction for bounded artifact generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence

from .reddog_artifact_generation_model_binding import artifact_generation_digest
from .reddog_artifact_generation_provider_contract import ArtifactGenerationModelResult

ARTIFACT_GENERATION_ACCEPT = "BOUNDED_ARTIFACT_GENERATION_ACCEPT"
ARTIFACT_GENERATION_REJECT = "BOUNDED_ARTIFACT_GENERATION_REJECT"


@dataclass(frozen=True)
class BoundedArtifactGenerationReceipt:
    receipt_id: str
    work_order_id: str
    slice_name: str
    planned_artifacts: List[str]
    artifact_manifest_digest: str
    model_result_digest: str
    model_receipt_id: str | None
    rejection_reasons: List[str]
    accepted: bool
    model_selection_receipt_id: str | None = None
    model_selection_digest: str = ""
    model_runtime_binding_receipt_id: str | None = None
    model_runtime_binding_digest: str = ""
    model_runtime_binding_verification_receipt_id: str | None = None
    model_runtime_binding_verification_digest: str = ""
    no_file_write_performed: bool = True
    no_shell_command_executed: bool = True
    no_worktree_created: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    receipt = BoundedArtifactGenerationReceipt(
        receipt_id=_receipt_id(
            work_order_id, slice_name, planned, manifest, model_result, model_selection, deduped
        ),
        work_order_id=work_order_id,
        slice_name=slice_name,
        planned_artifacts=list(planned),
        artifact_manifest_digest=manifest,
        model_result_digest=model_result.model_result_digest if model_result else "",
        model_receipt_id=model_result.model_receipt_id if model_result else None,
        rejection_reasons=deduped,
        accepted=not deduped,
        **_lineage(model_selection),
    )
    return BoundedArtifactGenerationResult(
        decision=ARTIFACT_GENERATION_REJECT if deduped else ARTIFACT_GENERATION_ACCEPT,
        accepted=not deduped,
        artifact_contents=dict(artifacts) if not deduped else {},
        rejection_reasons=deduped,
        receipt=receipt,
        model_result=model_result,
    )


def _receipt_id(
    work_order_id: str,
    slice_name: str,
    planned: Sequence[str],
    manifest: str,
    result: ArtifactGenerationModelResult | None,
    selection: Mapping[str, Any],
    reasons: Sequence[str],
) -> str:
    payload = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "planned_artifacts": list(planned),
        "artifact_manifest_digest": manifest,
        "model_result_digest": result.model_result_digest if result else "",
        **_lineage(selection),
        "rejection_reasons": list(reasons),
    }
    return "bounded_artifacts_" + artifact_generation_digest(payload).removeprefix("sha256:")[:16]


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
]
