"""Production model-selection receipt artifact supplier for RedDog runtime.

Slice: REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_PHASE1

This module materializes a production ``ModelSelectionReceipt`` from an
already-built catalog snapshot and signed benchmark/promotion evidence. It is a
bounded bridge for downstream RedDog work-order promotion. It does not call
models, benchmark models, mutate catalogs, persist telemetry, execute commands,
spawn workers, re-index HoloIndex, or bind the selection into live runtime.
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
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionDecision,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    ModelEvidenceKeyResolver,
    VerifiedModelEvidenceEntry,
    VerifiedModelProductionEvidence,
    build_verified_model_production_evidence,
    rehydrate_model_catalog_snapshot,
)


MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT = "MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT"
MODEL_SELECTION_ARTIFACT_SUPPLY_REJECT = "MODEL_SELECTION_ARTIFACT_SUPPLY_REJECT"
EVIDENCE_BUNDLE_SCHEMA_VERSION = "reddog_model_verified_production_evidence_bundle.v1"


class ModelSelectionArtifactSupplyReason:
    CATALOG_MISSING = "model_catalog_snapshot_missing"
    CATALOG_INVALID = "model_catalog_snapshot_invalid"
    EVIDENCE_MISSING = "verified_production_evidence_missing"
    EVIDENCE_INVALID = "verified_production_evidence_invalid"
    KEY_RESOLVER_MISSING = "model_evidence_key_resolver_missing"
    SIGNATURE_VERIFIER_MISSING = "model_evidence_signature_verifier_missing"
    REQUIREMENTS_INVALID = "model_selection_requirements_invalid"
    NON_PRODUCTION_REQUIREMENTS = "model_selection_requirements_not_production"
    SELECTION_REJECTED = "model_selection_rejected"
    OUTPUT_PATH_INVALID = "model_selection_output_path_invalid"
    OUTPUT_WRITE_FAILED = "model_selection_output_write_failed"


@dataclass(frozen=True)
class ModelSelectionArtifactSupplyResult:
    accepted: bool
    status: str
    selection_receipt_id: str | None
    catalog_snapshot_id: str | None
    selected_model_ids: tuple[str, ...]
    output_path: str | None
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_benchmark_run_performed: bool = True
    no_command_execution_performed: bool = True
    no_runtime_binding_performed: bool = True
    no_telemetry_persistence_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_selection_artifact_supply(
    *,
    repo_root: Path | str,
    catalog_snapshot: Mapping[str, Any] | None,
    verified_evidence_bundle: Mapping[str, Any] | VerifiedModelProductionEvidence | None,
    requirements: Mapping[str, Any] | ModelTaskRequirements,
    output_path: Path | str | None,
    key_resolver: ModelEvidenceKeyResolver | None = None,
    signature_verifier: SignatureVerifier | None = None,
    now: int | None = None,
    consume_nonces: bool = False,
) -> ModelSelectionArtifactSupplyResult:
    """Verify evidence, select a production model, and write one receipt."""

    root = Path(repo_root).resolve()
    reasons: list[str] = []
    snapshot = None
    if not isinstance(catalog_snapshot, Mapping) or not catalog_snapshot:
        reasons.append(ModelSelectionArtifactSupplyReason.CATALOG_MISSING)
    else:
        try:
            snapshot = rehydrate_model_catalog_snapshot(catalog_snapshot)
        except Exception:
            reasons.append(ModelSelectionArtifactSupplyReason.CATALOG_INVALID)

    normalized_requirements = None
    try:
        normalized_requirements = _requirements(requirements)
    except Exception:
        reasons.append(ModelSelectionArtifactSupplyReason.REQUIREMENTS_INVALID)
    if normalized_requirements is not None and normalized_requirements.purpose != SelectionPurpose.PRODUCTION:
        reasons.append(ModelSelectionArtifactSupplyReason.NON_PRODUCTION_REQUIREMENTS)

    evidence = None
    if verified_evidence_bundle is None:
        reasons.append(ModelSelectionArtifactSupplyReason.EVIDENCE_MISSING)
    elif isinstance(verified_evidence_bundle, VerifiedModelProductionEvidence):
        evidence = verified_evidence_bundle
    else:
        if key_resolver is None:
            reasons.append(ModelSelectionArtifactSupplyReason.KEY_RESOLVER_MISSING)
        if signature_verifier is None:
            reasons.append(ModelSelectionArtifactSupplyReason.SIGNATURE_VERIFIER_MISSING)
        if key_resolver is not None and signature_verifier is not None:
            try:
                evidence = _rehydrate_verified_evidence_bundle(
                    verified_evidence_bundle,
                    key_resolver=key_resolver,
                    signature_verifier=signature_verifier,
                    now=now,
                    consume_nonces=consume_nonces,
                )
            except Exception:
                reasons.append(ModelSelectionArtifactSupplyReason.EVIDENCE_INVALID)

    resolved_output, output_reasons = _runtime_output_path(
        output_path,
        root,
        ModelSelectionArtifactSupplyReason.OUTPUT_PATH_INVALID,
    )
    reasons.extend(output_reasons)
    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert snapshot is not None
    assert normalized_requirements is not None
    assert evidence is not None
    assert resolved_output is not None
    receipt = select_models_for_task(
        snapshot,
        normalized_requirements,
        production_evidence=evidence,
    )
    if receipt.decision != SelectionDecision.SELECTED or not receipt.selected_model_ids:
        return _reject((ModelSelectionArtifactSupplyReason.SELECTION_REJECTED, *receipt.rejection_reasons))
    try:
        _write_json_atomic(resolved_output, receipt.to_dict())
    except Exception:
        return _reject((ModelSelectionArtifactSupplyReason.OUTPUT_WRITE_FAILED,))
    return ModelSelectionArtifactSupplyResult(
        accepted=True,
        status=MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT,
        selection_receipt_id=receipt.receipt_id,
        catalog_snapshot_id=receipt.catalog_snapshot_id,
        selected_model_ids=receipt.selected_model_ids,
        output_path=str(resolved_output),
        rejection_reasons=(),
    )


def _rehydrate_verified_evidence_bundle(
    bundle: Mapping[str, Any],
    *,
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    now: int | None,
    consume_nonces: bool,
) -> VerifiedModelProductionEvidence:
    if bundle.get("schema_version") != EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise ValueError("invalid_evidence_bundle_schema")
    catalog_snapshot_id = _required(bundle.get("catalog_snapshot_id"), "catalog_snapshot_id")
    selection_receipt_id = _required(bundle.get("selection_receipt_id"), "selection_receipt_id")
    benchmark_run_receipt_id = _required(bundle.get("benchmark_run_receipt_id"), "benchmark_run_receipt_id")
    entries = bundle.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("missing_evidence_entries")
    verified_entries: list[VerifiedModelEvidenceEntry] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("invalid_evidence_entry")
        evidence = build_verified_model_production_evidence(
            catalog_snapshot_id=catalog_snapshot_id,
            selection_receipt_id=selection_receipt_id,
            benchmark_run_receipt_id=benchmark_run_receipt_id,
            benchmark_receipt=_mapping(entry.get("benchmark_receipt"), "benchmark_receipt"),
            promotion_receipt=_mapping(entry.get("promotion_receipt"), "promotion_receipt"),
            benchmark_signature_receipt=_mapping(
                entry.get("benchmark_signature_receipt"),
                "benchmark_signature_receipt",
            ),
            promotion_signature_receipt=_mapping(
                entry.get("promotion_signature_receipt"),
                "promotion_signature_receipt",
            ),
            key_resolver=key_resolver,
            signature_verifier=signature_verifier,
            now=int(now if now is not None else bundle.get("now", 0)),
            consume_nonces=consume_nonces,
        )
        verified_entries.extend(evidence.entries)
    return VerifiedModelProductionEvidence(entries=tuple(verified_entries))


def _requirements(value: Mapping[str, Any] | ModelTaskRequirements) -> ModelTaskRequirements:
    if isinstance(value, ModelTaskRequirements):
        return value.normalized()
    if not isinstance(value, Mapping):
        raise ValueError("requirements_not_mapping")
    return ModelTaskRequirements(
        task_family=_required(value.get("task_family"), "task_family"),
        selection_mode=SelectionMode(str(value.get("selection_mode") or SelectionMode.SINGLE.value)),
        purpose=SelectionPurpose(str(value.get("purpose") or SelectionPurpose.PRODUCTION.value)),
        required_modalities=tuple(str(item) for item in _list(value.get("required_modalities")) or ("text",)),
        min_context_window=_int_or_none(value.get("min_context_window")),
        require_tools=bool(value.get("require_tools", False)),
        require_structured_output=bool(value.get("require_structured_output", False)),
        require_reasoning=bool(value.get("require_reasoning", False)),
        max_input_cost_per_million=_float_or_none(value.get("max_input_cost_per_million")),
        max_output_cost_per_million=_float_or_none(value.get("max_output_cost_per_million")),
        allowed_providers=tuple(str(item) for item in _list(value.get("allowed_providers"))),
        denied_providers=tuple(str(item) for item in _list(value.get("denied_providers"))),
        max_candidates=int(value.get("max_candidates") or 1),
        min_verifier_pass_rate=_float_or_none(value.get("min_verifier_pass_rate")),
        panel_roles=tuple(str(item) for item in _list(value.get("panel_roles"))),
        panel_topology_digest=str(value.get("panel_topology_digest") or "") or None,
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


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name}_missing")
    return value


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(name + "_missing")
    return text


def _list(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _reject(reasons: Sequence[str]) -> ModelSelectionArtifactSupplyResult:
    return ModelSelectionArtifactSupplyResult(
        accepted=False,
        status=MODEL_SELECTION_ARTIFACT_SUPPLY_REJECT,
        selection_receipt_id=None,
        catalog_snapshot_id=None,
        selected_model_ids=(),
        output_path=None,
        rejection_reasons=_dedupe(reasons),
    )


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


__all__ = [
    "EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT",
    "MODEL_SELECTION_ARTIFACT_SUPPLY_REJECT",
    "ModelSelectionArtifactSupplyReason",
    "ModelSelectionArtifactSupplyResult",
    "run_reddog_model_selection_artifact_supply",
]
