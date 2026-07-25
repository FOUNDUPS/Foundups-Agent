"""Read-only RedDog model runtime binding query.

The runtime binding artifact is produced by the existing signed-evidence
artifact supply. This consumer rehydrates its deterministic receipt and checks
the runtime-facing policy/topology invariants before exposing model IDs to the
RedDog extension.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingDecision,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)


SCHEMA_VERSION = "reddog_model_runtime_binding_query.v1"
STATUS_READY = "MODEL_RUNTIME_BINDING_READY"
STATUS_UNCONFIGURED = "MODEL_RUNTIME_BINDING_UNCONFIGURED"
STATUS_NOT_READY = "MODEL_RUNTIME_BINDING_NOT_READY"
EXPECTED_SURFACE = "reddog_backend_architect"
MAX_PANEL_MODELS = 6
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,119}$")
DIGEST_RE = re.compile(r"^(?:sha256:)?[a-f0-9]{64}$")


@dataclass(frozen=True)
class ModelRuntimeBindingQueryReceipt:
    schema_version: str
    query_receipt_id: str
    configured: bool
    accepted: bool
    status: str
    binding_receipt_id: Optional[str]
    runtime_surface: Optional[str]
    catalog_snapshot_id: Optional[str]
    selection_receipt_id: Optional[str]
    task_family: Optional[str]
    principal_model: Optional[str]
    panel_models: tuple[str, ...]
    role_bindings: tuple[Mapping[str, str], ...]
    benchmark_evidence_receipt_ids: tuple[str, ...]
    promotion_evidence_receipt_ids: tuple[str, ...]
    signed_promotion_receipt_ids: tuple[str, ...]
    min_verifier_pass_rate: Optional[float]
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_holoindex_query_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_command_execution_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_runtime_artifact_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def query_model_runtime_binding(
    *,
    repo_root: Path | str,
    environ: Mapping[str, str] | None = None,
) -> ModelRuntimeBindingQueryReceipt:
    """Return one validated architect model binding or fail closed."""

    env = environ if environ is not None else os.environ
    root_value = str(env.get("REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT") or "").strip()
    path_value = str(env.get(
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH"
    ) or "").strip()
    configured = bool(root_value or path_value)
    if not configured:
        return _receipt(configured=False, status=STATUS_UNCONFIGURED)
    reasons = _path_rejections(repo_root, root_value, path_value)
    if reasons:
        return _receipt(configured=True, status=STATUS_NOT_READY, reasons=reasons)
    try:
        binding = _load_binding(root_value, path_value)
    except Exception:
        return _receipt(configured=True, status=STATUS_NOT_READY,
                        reasons=("model_runtime_binding_artifact_invalid",))
    reasons = _binding_rejections(binding)
    if reasons:
        return _receipt(configured=True, status=STATUS_NOT_READY,
                        reasons=tuple(reasons))
    return _ready_receipt(binding)


def _load_binding(root_value: str, path_value: str) -> Any:
    runtime_root = Path(root_value).resolve()
    raw = read_reddog_runtime_json_mapping(
        Path(path_value),
        allowed_root=runtime_root,
    )
    return rehydrate_model_runtime_binding_receipt(raw)


def _ready_receipt(binding: Any) -> ModelRuntimeBindingQueryReceipt:
    role_bindings = tuple(
        {
            "role": item.role,
            "model_id": item.model_id,
            "provider": item.provider,
        }
        for item in binding.role_bindings
    )
    return _receipt(
        configured=True,
        accepted=True,
        status=STATUS_READY,
        binding_receipt_id=binding.receipt_id,
        runtime_surface=binding.runtime_surface,
        catalog_snapshot_id=binding.catalog_snapshot_id,
        selection_receipt_id=binding.selection_receipt_id,
        task_family=binding.task_family,
        principal_model=binding.principal_model,
        panel_models=binding.panel_models,
        role_bindings=role_bindings,
        benchmark_ids=binding.benchmark_evidence_receipt_ids,
        promotion_ids=binding.promotion_evidence_receipt_ids,
        signed_ids=binding.signed_promotion_receipt_ids,
        min_verifier_pass_rate=binding.policy.min_verifier_pass_rate,
    )


def _path_rejections(
    repo_root: Path | str,
    root_value: str,
    path_value: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not root_value:
        reasons.append("missing_model_runtime_binding_root")
    if not path_value:
        reasons.append("missing_architect_model_runtime_binding_path")
    if reasons:
        return tuple(reasons)
    runtime_root = Path(root_value)
    artifact_path = Path(path_value)
    if not runtime_root.is_absolute() or not artifact_path.is_absolute():
        return ("model_runtime_binding_path_not_absolute",)
    repo = Path(repo_root).resolve()
    runtime = runtime_root.resolve()
    artifact = Path(os.path.abspath(artifact_path))
    if _inside(runtime, repo):
        reasons.append("model_runtime_binding_root_inside_repo")
    if _inside(artifact, repo):
        reasons.append("model_runtime_binding_artifact_inside_repo")
    if not _inside(artifact, runtime):
        reasons.append("model_runtime_binding_artifact_outside_runtime_root")
    return tuple(reasons)


def _binding_rejections(binding: Any) -> list[str]:
    reasons: list[str] = []
    if binding.decision != ModelRuntimeBindingDecision.BOUND:
        reasons.append("model_runtime_binding_not_bound")
    if binding.runtime_surface != EXPECTED_SURFACE:
        reasons.append("model_runtime_binding_surface_invalid")
    if binding.rejection_reasons:
        reasons.append("model_runtime_binding_contains_rejections")
    reasons.extend(_topology_rejections(binding))
    reasons.extend(_policy_rejections(binding))
    reasons.extend(_evidence_rejections(binding))
    return sorted(set(reasons))


def _topology_rejections(binding: Any) -> list[str]:
    reasons: list[str] = []
    models = (str(binding.principal_model or ""), *tuple(binding.panel_models))
    role_names = tuple(str(item.role) for item in binding.role_bindings)
    role_models = tuple(str(item.model_id) for item in binding.role_bindings)
    if not models[0] or any(not MODEL_RE.fullmatch(model) for model in models):
        reasons.append("model_runtime_binding_model_id_invalid")
    if len(binding.panel_models) > MAX_PANEL_MODELS:
        reasons.append("model_runtime_binding_panel_too_large")
    if len(set(models)) != len(models):
        reasons.append("model_runtime_binding_duplicate_model")
    if role_names.count("principal") != 1 or "verifier" in role_names:
        reasons.append("model_runtime_binding_role_boundary_invalid")
    if len(set(role_names)) != len(role_names):
        reasons.append("model_runtime_binding_duplicate_role")
    if role_models != models:
        reasons.append("model_runtime_binding_role_topology_mismatch")
    return reasons


def _policy_rejections(binding: Any) -> list[str]:
    reasons: list[str] = []
    policy = binding.policy
    if policy.task_family != binding.task_family:
        reasons.append("model_runtime_binding_task_family_mismatch")
    if policy.runtime_surface != binding.runtime_surface:
        reasons.append("model_runtime_binding_policy_surface_mismatch")
    if policy.min_verifier_pass_rate <= 0:
        reasons.append("model_runtime_binding_verifier_threshold_invalid")
    if not policy.authority_receipt_id:
        reasons.append("model_runtime_binding_authority_missing")
    if not all(
        DIGEST_RE.fullmatch(value)
        for value in (
            policy.required_task_set_digest,
            policy.required_held_out_split_digest,
            policy.required_verifier_digest,
        )
    ):
        reasons.append("model_runtime_binding_policy_digest_invalid")
    return reasons


def _evidence_rejections(binding: Any) -> list[str]:
    model_count = 1 + len(binding.panel_models)
    evidence_counts = (
        len(binding.benchmark_evidence_receipt_ids),
        len(binding.promotion_evidence_receipt_ids),
        len(binding.signed_promotion_receipt_ids),
    )
    return (
        ["model_runtime_binding_evidence_count_mismatch"]
        if any(count != model_count for count in evidence_counts)
        else []
    )


def _receipt(
    *,
    configured: bool,
    status: str,
    accepted: bool = False,
    reasons: tuple[str, ...] = (),
    **values: Any,
) -> ModelRuntimeBindingQueryReceipt:
    defaults: dict[str, Any] = {
        "binding_receipt_id": None, "runtime_surface": None,
        "catalog_snapshot_id": None, "selection_receipt_id": None,
        "task_family": None, "principal_model": None, "panel_models": (),
        "role_bindings": (), "benchmark_ids": (), "promotion_ids": (),
        "signed_ids": (), "min_verifier_pass_rate": None,
    }
    defaults.update(values)
    payload = _receipt_payload(configured, accepted, status, reasons, defaults)
    return ModelRuntimeBindingQueryReceipt(
        query_receipt_id=_digest(payload),
        **payload,
    )


def _receipt_payload(
    configured: bool,
    accepted: bool,
    status: str,
    reasons: tuple[str, ...],
    values: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "configured": configured,
        "accepted": accepted,
        "status": status,
        "binding_receipt_id": values["binding_receipt_id"], "runtime_surface": values["runtime_surface"],
        "catalog_snapshot_id": values["catalog_snapshot_id"], "selection_receipt_id": values["selection_receipt_id"],
        "task_family": values["task_family"],
        "principal_model": values["principal_model"],
        "panel_models": tuple(values["panel_models"]),
        "role_bindings": tuple(values["role_bindings"]),
        "benchmark_evidence_receipt_ids": tuple(values["benchmark_ids"]),
        "promotion_evidence_receipt_ids": tuple(values["promotion_ids"]), "signed_promotion_receipt_ids": tuple(values["signed_ids"]),
        "min_verifier_pass_rate": values["min_verifier_pass_rate"],
        "rejection_reasons": tuple(reasons),
        "no_model_call_performed": True, "no_holoindex_query_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_command_execution_performed": True,
        "no_repo_mutation_performed": True,
        "no_runtime_artifact_mutation_performed": True,
    }


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    return child_resolved == parent_resolved or parent_resolved in child_resolved.parents


__all__ = [
    "EXPECTED_SURFACE",
    "MAX_PANEL_MODELS",
    "ModelRuntimeBindingQueryReceipt",
    "SCHEMA_VERSION",
    "STATUS_NOT_READY",
    "STATUS_READY",
    "STATUS_UNCONFIGURED",
    "query_model_runtime_binding",
]
