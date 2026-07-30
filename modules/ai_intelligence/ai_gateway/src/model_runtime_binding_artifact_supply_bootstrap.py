"""Main-startup bootstrap for RedDog runtime-binding artifact supply.

Slice: REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads outside-repo runtime JSON inputs and materializes a
``RedDogModelRuntimeBindingReceipt``. It does not call providers, execute
commands, mutate catalogs, bind extension defaults, spawn workers, re-index
HoloIndex, or write inside the repository.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply import (
    MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT,
    run_reddog_model_runtime_binding_artifact_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap import (
    _key_resolver,
    _signature_verifier,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_APPLIED = "MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_APPLIED"
MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_NOT_READY = "MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class ModelRuntimeBindingArtifactBootstrapResult:
    accepted: bool
    status: str
    runtime_binding_receipt_id: Optional[str]
    output_path: Optional[str]
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


def run_reddog_model_runtime_binding_artifact_supply_bootstrap(
    *,
    repo_root: Path | str,
    catalog_snapshot_path: Path | str | None,
    model_selection_receipt_path: Path | str | None,
    benchmark_evidence_receipts_path: Path | str | None,
    promotion_evidence_receipts_path: Path | str | None,
    evidence_bundle_path: Path | str | None,
    runtime_policy_path: Path | str | None,
    trusted_keys_path: Path | str | None,
    output_path: Path | str | None,
    signature_verifier_backend: str = "ed25519",
    signature_verifier: SignatureVerifier | None = None,
    now_epoch: int | None = None,
) -> ModelRuntimeBindingArtifactBootstrapResult:
    """Materialize the runtime-binding artifact from configured runtime files."""

    root = Path(repo_root).resolve()
    catalog, catalog_reasons = _read_json_outside_repo(
        root,
        catalog_snapshot_path,
        missing_reason="missing_model_catalog_snapshot_path",
        inside_reason="model_catalog_snapshot_path_inside_repo",
        malformed_reason="malformed_model_catalog_snapshot",
    )
    selection, selection_reasons = _read_json_outside_repo(
        root,
        model_selection_receipt_path,
        missing_reason="missing_model_selection_receipt_path",
        inside_reason="model_selection_receipt_path_inside_repo",
        malformed_reason="malformed_model_selection_receipt",
    )
    benchmark_payload, benchmark_reasons = _read_json_outside_repo(
        root,
        benchmark_evidence_receipts_path,
        missing_reason="missing_model_benchmark_evidence_receipts_path",
        inside_reason="model_benchmark_evidence_receipts_path_inside_repo",
        malformed_reason="malformed_model_benchmark_evidence_receipts",
    )
    promotion_payload, promotion_reasons = _read_json_outside_repo(
        root,
        promotion_evidence_receipts_path,
        missing_reason="missing_model_promotion_evidence_receipts_path",
        inside_reason="model_promotion_evidence_receipts_path_inside_repo",
        malformed_reason="malformed_model_promotion_evidence_receipts",
    )
    evidence, evidence_reasons = _read_json_outside_repo(
        root,
        evidence_bundle_path,
        missing_reason="missing_model_evidence_bundle_path",
        inside_reason="model_evidence_bundle_path_inside_repo",
        malformed_reason="malformed_model_evidence_bundle",
    )
    policy, policy_reasons = _read_json_outside_repo(
        root,
        runtime_policy_path,
        missing_reason="missing_model_runtime_binding_policy_path",
        inside_reason="model_runtime_binding_policy_path_inside_repo",
        malformed_reason="malformed_model_runtime_binding_policy",
    )
    trusted_keys, key_reasons = _read_json_outside_repo(
        root,
        trusted_keys_path,
        missing_reason="missing_model_evidence_trusted_keys_path",
        inside_reason="model_evidence_trusted_keys_path_inside_repo",
        malformed_reason="malformed_model_evidence_trusted_keys",
    )
    reasons = [
        *catalog_reasons,
        *selection_reasons,
        *benchmark_reasons,
        *promotion_reasons,
        *evidence_reasons,
        *policy_reasons,
        *key_reasons,
    ]
    key_resolver = None
    if trusted_keys is not None:
        key_resolver, resolver_reasons = _key_resolver(trusted_keys)
        reasons.extend(resolver_reasons)
    verifier = signature_verifier
    if verifier is None:
        verifier, verifier_reasons = _signature_verifier(signature_verifier_backend)
        reasons.extend(verifier_reasons)
    benchmarks = _receipt_list(benchmark_payload, "benchmark_evidence_receipts")
    promotions = _receipt_list(promotion_payload, "promotion_evidence_receipts")
    if benchmark_payload is not None and benchmarks is None:
        reasons.append("malformed_model_benchmark_evidence_receipts")
    if promotion_payload is not None and promotions is None:
        reasons.append("malformed_model_promotion_evidence_receipts")
    if reasons:
        return _not_ready(reasons)

    assert catalog is not None
    assert selection is not None
    assert evidence is not None
    assert policy is not None
    assert key_resolver is not None
    assert verifier is not None
    assert benchmarks is not None
    assert promotions is not None
    supply = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=root,
        catalog_snapshot=catalog,
        model_selection_receipt=selection,
        benchmark_evidence_receipts=benchmarks,
        promotion_evidence_receipts=promotions,
        verified_evidence_bundle=evidence,
        trusted_keys_payload=trusted_keys,
        runtime_policy=policy,
        output_path=output_path,
        key_resolver=key_resolver,
        signature_verifier=verifier,
        now=int(now_epoch if now_epoch is not None else time.time()),
    )
    if not supply.accepted or supply.status != MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT:
        return _not_ready(supply.rejection_reasons or ("model_runtime_binding_artifact_supply_rejected",))
    return ModelRuntimeBindingArtifactBootstrapResult(
        accepted=True,
        status=MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_APPLIED,
        runtime_binding_receipt_id=supply.runtime_binding_receipt_id,
        output_path=supply.output_path,
        rejection_reasons=(),
    )


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    malformed_reason: str,
) -> tuple[Any | None, tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if _is_inside(resolved, repo_root):
        return None, (inside_reason,)
    if not resolved.exists() or not resolved.is_file():
        return None, (missing_reason,)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception:
        return None, (malformed_reason,)
    if not isinstance(payload, (Mapping, list)):
        return None, (malformed_reason,)
    return payload, ()


def _receipt_list(value: Any, key: str) -> tuple[Mapping[str, Any], ...] | None:
    raw = value
    if isinstance(value, Mapping):
        raw = value.get(key)
    if not isinstance(raw, list) or not raw:
        return None
    records: list[Mapping[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            return None
        records.append(item)
    return tuple(records)


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(reasons: tuple[str, ...] | list[str]) -> ModelRuntimeBindingArtifactBootstrapResult:
    return ModelRuntimeBindingArtifactBootstrapResult(
        accepted=False,
        status=MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_NOT_READY,
        runtime_binding_receipt_id=None,
        output_path=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_APPLIED",
    "MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_NOT_READY",
    "ModelRuntimeBindingArtifactBootstrapResult",
    "run_reddog_model_runtime_binding_artifact_supply_bootstrap",
]
