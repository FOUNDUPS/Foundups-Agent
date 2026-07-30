"""Production runtime-binding receipt artifact supplier for RedDog.

Slice: REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_PHASE1

This module materializes a ``RedDogModelRuntimeBindingReceipt`` from an
existing production model-selection receipt and its signed benchmark/promotion
evidence. It is a bounded bridge for resident RedDog runtime inputs. It does
not call providers, benchmark models, execute commands, mutate catalogs, bind
extension runtime defaults, spawn workers, write PatternMemory, or re-index
HoloIndex.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)

from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelPromotionEvidenceReceipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingPolicy,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_evidence_verifier import (
    verify_model_runtime_binding_artifact,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    ModelEvidenceKeyResolver,
    VerifiedModelProductionEvidence,
    rehydrate_model_benchmark_evidence_receipt,
    rehydrate_model_catalog_snapshot,
    rehydrate_model_promotion_evidence_receipt,
    rehydrate_model_selection_receipt,
)


MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT = "MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT"
MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_REJECT = "MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_REJECT"


class ModelRuntimeBindingArtifactSupplyReason:
    CATALOG_MISSING = "model_catalog_snapshot_missing"
    CATALOG_INVALID = "model_catalog_snapshot_invalid"
    SELECTION_MISSING = "model_selection_receipt_missing"
    SELECTION_INVALID = "model_selection_receipt_invalid"
    BENCHMARKS_MISSING = "model_benchmark_evidence_receipts_missing"
    BENCHMARKS_INVALID = "model_benchmark_evidence_receipts_invalid"
    PROMOTIONS_MISSING = "model_promotion_evidence_receipts_missing"
    PROMOTIONS_INVALID = "model_promotion_evidence_receipts_invalid"
    EVIDENCE_MISSING = "verified_production_evidence_missing"
    EVIDENCE_INVALID = "verified_production_evidence_invalid"
    KEY_RESOLVER_MISSING = "model_evidence_key_resolver_missing"
    SIGNATURE_VERIFIER_MISSING = "model_evidence_signature_verifier_missing"
    POLICY_MISSING = "model_runtime_binding_policy_missing"
    POLICY_INVALID = "model_runtime_binding_policy_invalid"
    RUNTIME_BINDING_REJECTED = "model_runtime_binding_rejected"
    OUTPUT_PATH_INVALID = "model_runtime_binding_output_path_invalid"
    OUTPUT_WRITE_FAILED = "model_runtime_binding_output_write_failed"


@dataclass(frozen=True)
class ModelRuntimeBindingArtifactSupplyResult:
    accepted: bool
    status: str
    runtime_binding_receipt_id: str | None
    catalog_snapshot_id: str | None
    selection_receipt_id: str | None
    runtime_surface: str | None
    principal_model: str | None
    panel_models: tuple[str, ...]
    output_path: str | None
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_benchmark_run_performed: bool = True
    no_command_execution_performed: bool = True
    no_extension_runtime_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_telemetry_persistence_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_runtime_binding_artifact_supply(
    *,
    repo_root: Path | str,
    catalog_snapshot: Mapping[str, Any] | None,
    model_selection_receipt: Mapping[str, Any] | None,
    benchmark_evidence_receipts: Sequence[Mapping[str, Any] | ModelBenchmarkEvidenceReceipt] | None,
    promotion_evidence_receipts: Sequence[Mapping[str, Any] | ModelPromotionEvidenceReceipt] | None,
    verified_evidence_bundle: Mapping[str, Any] | VerifiedModelProductionEvidence | None,
    trusted_keys_payload: Mapping[str, Any] | None,
    runtime_policy: Mapping[str, Any] | ModelRuntimeBindingPolicy | None,
    output_path: Path | str | None,
    key_resolver: ModelEvidenceKeyResolver | None = None,
    signature_verifier: SignatureVerifier | None = None,
    now: int | None = None,
    consume_nonces: bool = False,
) -> ModelRuntimeBindingArtifactSupplyResult:
    """Verify model evidence, bind runtime models, and write one receipt."""

    root = Path(repo_root).resolve()
    reasons: list[str] = []

    snapshot = None
    if not isinstance(catalog_snapshot, Mapping) or not catalog_snapshot:
        reasons.append(ModelRuntimeBindingArtifactSupplyReason.CATALOG_MISSING)
    else:
        try:
            snapshot = rehydrate_model_catalog_snapshot(catalog_snapshot)
        except Exception:
            reasons.append(ModelRuntimeBindingArtifactSupplyReason.CATALOG_INVALID)

    selection = None
    if not isinstance(model_selection_receipt, Mapping) or not model_selection_receipt:
        reasons.append(ModelRuntimeBindingArtifactSupplyReason.SELECTION_MISSING)
    else:
        try:
            selection = rehydrate_model_selection_receipt(model_selection_receipt)
        except Exception:
            reasons.append(ModelRuntimeBindingArtifactSupplyReason.SELECTION_INVALID)

    benchmarks: tuple[ModelBenchmarkEvidenceReceipt, ...] = ()
    benchmark_reasons: list[str] = []
    if not benchmark_evidence_receipts:
        benchmark_reasons.append(ModelRuntimeBindingArtifactSupplyReason.BENCHMARKS_MISSING)
    else:
        try:
            benchmarks = tuple(_benchmark_receipts(benchmark_evidence_receipts))
        except Exception:
            benchmark_reasons.append(ModelRuntimeBindingArtifactSupplyReason.BENCHMARKS_INVALID)
    reasons.extend(benchmark_reasons)

    promotion_reasons: list[str] = []
    if not promotion_evidence_receipts:
        promotion_reasons.append(ModelRuntimeBindingArtifactSupplyReason.PROMOTIONS_MISSING)
    else:
        try:
            tuple(_promotion_receipts(promotion_evidence_receipts, benchmarks))
        except Exception:
            promotion_reasons.append(ModelRuntimeBindingArtifactSupplyReason.PROMOTIONS_INVALID)
    reasons.extend(promotion_reasons)

    serialized_evidence: Mapping[str, Any] | None = None
    if verified_evidence_bundle is None:
        reasons.append(ModelRuntimeBindingArtifactSupplyReason.EVIDENCE_MISSING)
    elif isinstance(verified_evidence_bundle, VerifiedModelProductionEvidence):
        reasons.append(ModelRuntimeBindingArtifactSupplyReason.EVIDENCE_INVALID)
    else:
        serialized_evidence = verified_evidence_bundle
        if key_resolver is None:
            reasons.append(ModelRuntimeBindingArtifactSupplyReason.KEY_RESOLVER_MISSING)
        if signature_verifier is None:
            reasons.append(ModelRuntimeBindingArtifactSupplyReason.SIGNATURE_VERIFIER_MISSING)

    if not isinstance(trusted_keys_payload, Mapping) or not trusted_keys_payload:
        reasons.append(ModelRuntimeBindingArtifactSupplyReason.KEY_RESOLVER_MISSING)

    policy = None
    if runtime_policy is None:
        reasons.append(ModelRuntimeBindingArtifactSupplyReason.POLICY_MISSING)
    else:
        try:
            policy = _policy(runtime_policy)
        except Exception:
            reasons.append(ModelRuntimeBindingArtifactSupplyReason.POLICY_INVALID)

    resolved_output, output_reasons = _runtime_output_path(
        output_path,
        root,
        ModelRuntimeBindingArtifactSupplyReason.OUTPUT_PATH_INVALID,
    )
    reasons.extend(output_reasons)
    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert snapshot is not None
    assert selection is not None
    assert policy is not None
    assert resolved_output is not None
    assert serialized_evidence is not None
    assert trusted_keys_payload is not None
    try:
        verified = verify_model_runtime_binding_artifact(
            catalog_snapshot=dict(catalog_snapshot or {}),
            model_selection_receipt=dict(model_selection_receipt or {}),
            benchmark_evidence_receipts=tuple(
                item.to_dict() if hasattr(item, "to_dict") else dict(item)
                for item in benchmark_evidence_receipts or ()
            ),
            promotion_evidence_receipts=tuple(
                item.to_dict() if hasattr(item, "to_dict") else dict(item)
                for item in promotion_evidence_receipts or ()
            ),
            verified_evidence_bundle=serialized_evidence,
            runtime_policy=dict(runtime_policy or {}),
            trusted_keys_payload=trusted_keys_payload,
            key_resolver=key_resolver,
            signature_verifier=signature_verifier,
            now=int(now or 0),
        )
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("model_runtime_binding_rejected:"):
            return _reject(
                (
                    ModelRuntimeBindingArtifactSupplyReason.RUNTIME_BINDING_REJECTED,
                    *detail.partition(":")[2].split(","),
                )
            )
        return _reject((ModelRuntimeBindingArtifactSupplyReason.EVIDENCE_INVALID,))

    try:
        _write_json_atomic(resolved_output, verified.to_artifact())
    except Exception:
        return _reject((ModelRuntimeBindingArtifactSupplyReason.OUTPUT_WRITE_FAILED,))

    return ModelRuntimeBindingArtifactSupplyResult(
        accepted=True,
        status=MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT,
        runtime_binding_receipt_id=verified.binding.receipt_id,
        catalog_snapshot_id=verified.binding.catalog_snapshot_id,
        selection_receipt_id=verified.binding.selection_receipt_id,
        runtime_surface=verified.binding.runtime_surface,
        principal_model=verified.binding.principal_model,
        panel_models=verified.binding.panel_models,
        output_path=str(resolved_output),
        rejection_reasons=(),
    )


def _benchmark_receipts(
    values: Sequence[Mapping[str, Any] | ModelBenchmarkEvidenceReceipt],
) -> tuple[ModelBenchmarkEvidenceReceipt, ...]:
    receipts: list[ModelBenchmarkEvidenceReceipt] = []
    for value in values:
        if isinstance(value, ModelBenchmarkEvidenceReceipt):
            receipts.append(value)
        elif isinstance(value, Mapping):
            receipts.append(rehydrate_model_benchmark_evidence_receipt(value))
        else:
            raise ValueError("invalid_benchmark_receipt")
    return tuple(receipts)


def _promotion_receipts(
    values: Sequence[Mapping[str, Any] | ModelPromotionEvidenceReceipt],
    benchmarks: Sequence[ModelBenchmarkEvidenceReceipt],
) -> tuple[ModelPromotionEvidenceReceipt, ...]:
    by_id = {receipt.receipt_id: receipt for receipt in benchmarks}
    receipts: list[ModelPromotionEvidenceReceipt] = []
    for value in values:
        if isinstance(value, ModelPromotionEvidenceReceipt):
            receipts.append(value)
            continue
        if not isinstance(value, Mapping):
            raise ValueError("invalid_promotion_receipt")
        benchmark = by_id.get(str(value.get("benchmark_evidence_receipt_id") or ""))
        if benchmark is None:
            raise ValueError("promotion_benchmark_receipt_missing")
        receipts.append(rehydrate_model_promotion_evidence_receipt(value, benchmark_receipt=benchmark))
    return tuple(receipts)


def _policy(value: Mapping[str, Any] | ModelRuntimeBindingPolicy) -> ModelRuntimeBindingPolicy:
    if isinstance(value, ModelRuntimeBindingPolicy):
        return value.normalized()
    if not isinstance(value, Mapping):
        raise ValueError("policy_not_mapping")
    return ModelRuntimeBindingPolicy(
        task_family=_required(value.get("task_family"), "task_family"),
        runtime_surface=_required(value.get("runtime_surface"), "runtime_surface"),
        min_verifier_pass_rate=float(value.get("min_verifier_pass_rate")),
        required_task_set_digest=_required(value.get("required_task_set_digest"), "required_task_set_digest"),
        required_held_out_split_digest=_required(
            value.get("required_held_out_split_digest"),
            "required_held_out_split_digest",
        ),
        required_verifier_digest=_required(value.get("required_verifier_digest"), "required_verifier_digest"),
        max_panel_models=int(value.get("max_panel_models", 4)),
        required_panel_topology_digest=_optional(value.get("required_panel_topology_digest")),
        authority_receipt_id=_optional(value.get("authority_receipt_id")),
    ).normalized()


def _runtime_output_path(
    value: Path | str | None,
    repo_root: Path,
    reason: str,
) -> tuple[Path | None, list[str]]:
    if not value:
        return None, [reason]
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
        return None, [reason]
    except ValueError:
        pass
    return resolved, []


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(name + "_missing")
    return text


def _optional(value: Any) -> str | None:
    text = str(value or "").strip() if value is not None else ""
    return text or None


def _reject(reasons: Sequence[str]) -> ModelRuntimeBindingArtifactSupplyResult:
    return ModelRuntimeBindingArtifactSupplyResult(
        accepted=False,
        status=MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_REJECT,
        runtime_binding_receipt_id=None,
        catalog_snapshot_id=None,
        selection_receipt_id=None,
        runtime_surface=None,
        principal_model=None,
        panel_models=(),
        output_path=None,
        rejection_reasons=_dedupe(reasons),
    )


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


__all__ = [
    "MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT",
    "MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_REJECT",
    "ModelRuntimeBindingArtifactSupplyReason",
    "ModelRuntimeBindingArtifactSupplyResult",
    "run_reddog_model_runtime_binding_artifact_supply",
]
