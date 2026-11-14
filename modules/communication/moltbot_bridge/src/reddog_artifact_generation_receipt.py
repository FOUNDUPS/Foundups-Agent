"""Canonical receipt and semantic verifier for artifact-generation effects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, List, Mapping

from .reddog_artifact_generation_model_binding import artifact_generation_digest

_PROVIDER_RUNTIMES = {"none", "foundups_fusion", "openclaw_gateway", "hermes_api"}
_EFFECT_BOOL_FIELDS = (
    "accepted",
    "no_file_write_performed",
    "no_shell_command_executed",
    "no_worktree_created",
    "no_github_call_performed",
    "no_pr_publish_performed",
    "no_merge_performed",
    "no_pattern_memory_write_performed",
    "no_reward_settlement_performed",
    "no_holoindex_reindex_performed",
    "provider_invocation_performed",
    "worker_process_started",
    "hermes_dispatch_performed",
    "external_side_effects_possible",
    "effect_observation_complete",
    "run_abort_confirmed",
)


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
    provider_runtime: str = "none"
    provider_invocation_performed: bool = False
    worker_process_started: bool = False
    worker_process_spawn_count: int = 0
    hermes_dispatch_performed: bool = False
    external_side_effects_possible: bool = False
    effect_observation_complete: bool = True
    run_abort_confirmed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def artifact_generation_receipt_id(payload: Mapping[str, Any]) -> str:
    digest = artifact_generation_digest(payload).removeprefix("sha256:")
    return "bounded_artifacts_" + digest[:16]


def rehydrate_bounded_artifact_generation_receipt(
    value: Mapping[str, Any],
) -> BoundedArtifactGenerationReceipt | None:
    """Accept only a complete, digest-valid, semantically consistent receipt."""
    expected = {item.name for item in fields(BoundedArtifactGenerationReceipt)}
    if not isinstance(value, Mapping) or set(value) != expected:
        return None
    payload = dict(value)
    receipt_id = str(payload.pop("receipt_id", ""))
    if receipt_id != artifact_generation_receipt_id(payload):
        return None
    if not _effect_semantics_are_valid(payload):
        return None
    try:
        return BoundedArtifactGenerationReceipt(**dict(value))
    except (TypeError, ValueError):
        return None


def _effect_semantics_are_valid(payload: Mapping[str, Any]) -> bool:
    if any(type(payload.get(name)) is not bool for name in _EFFECT_BOOL_FIELDS):
        return False
    spawn_count = payload.get("worker_process_spawn_count")
    if type(spawn_count) is not int or spawn_count < 0:
        return False
    if payload["worker_process_started"] is not (spawn_count > 0):
        return False
    runtime = payload.get("provider_runtime")
    if runtime not in _PROVIDER_RUNTIMES:
        return False
    invoked = payload["provider_invocation_performed"]
    if invoked and (runtime == "none" or not payload["external_side_effects_possible"]):
        return False
    if payload["hermes_dispatch_performed"] and (
        runtime != "hermes_api" or not invoked
    ):
        return False
    if not payload["effect_observation_complete"] and payload["run_abort_confirmed"]:
        return False
    if runtime == "none" and any(
        (
            invoked,
            payload["worker_process_started"],
            payload["hermes_dispatch_performed"],
            not payload["no_file_write_performed"],
            payload["external_side_effects_possible"],
        )
    ):
        return False
    return True


__all__ = [
    "BoundedArtifactGenerationReceipt",
    "artifact_generation_receipt_id",
    "rehydrate_bounded_artifact_generation_receipt",
]
