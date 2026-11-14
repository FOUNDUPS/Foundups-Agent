"""Main-startup bootstrap for RedDog model-selection artifact supply.

Slice: REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

This adapter reads outside-repo runtime JSON inputs, constructs a trusted
model-evidence key resolver, verifies signed benchmark/promotion evidence, and
materializes the production ``ModelSelectionReceipt`` JSON expected by the
RedDog architect FIX promotion bridge.

It does not call models, run benchmarks, execute commands, mutate catalogs,
persist telemetry, bind runtime defaults, mutate the extension, spawn workers,
write PatternMemory, or re-index HoloIndex.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply import (
    MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT,
    run_reddog_model_selection_artifact_supply,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    StaticModelEvidenceKeyResolver,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


MODEL_SELECTION_ARTIFACT_BOOTSTRAP_APPLIED = "MODEL_SELECTION_ARTIFACT_BOOTSTRAP_APPLIED"
MODEL_SELECTION_ARTIFACT_BOOTSTRAP_NOT_READY = "MODEL_SELECTION_ARTIFACT_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class ModelSelectionArtifactBootstrapResult:
    accepted: bool
    status: str
    model_selection_receipt_id: Optional[str]
    output_path: Optional[str]
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_benchmark_run_performed: bool = True
    no_command_execution_performed: bool = True
    no_runtime_binding_performed: bool = True
    no_telemetry_persistence_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_extension_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_model_selection_artifact_supply_bootstrap(
    *,
    repo_root: Path | str,
    catalog_snapshot_path: Path | str | None,
    evidence_bundle_path: Path | str | None,
    requirements_path: Path | str | None,
    trusted_keys_path: Path | str | None,
    output_path: Path | str | None,
    signature_verifier_backend: str = "ed25519",
    signature_verifier: SignatureVerifier | None = None,
    now_epoch: int | None = None,
) -> ModelSelectionArtifactBootstrapResult:
    """Materialize the model-selection artifact from configured runtime files."""

    root = Path(repo_root).resolve()
    catalog, catalog_reasons = _read_json_outside_repo(
        root,
        catalog_snapshot_path,
        missing_reason="missing_model_catalog_snapshot_path",
        inside_reason="model_catalog_snapshot_path_inside_repo",
        malformed_reason="malformed_model_catalog_snapshot",
    )
    evidence, evidence_reasons = _read_json_outside_repo(
        root,
        evidence_bundle_path,
        missing_reason="missing_model_evidence_bundle_path",
        inside_reason="model_evidence_bundle_path_inside_repo",
        malformed_reason="malformed_model_evidence_bundle",
    )
    requirements, requirements_reasons = _read_json_outside_repo(
        root,
        requirements_path,
        missing_reason="missing_model_selection_requirements_path",
        inside_reason="model_selection_requirements_path_inside_repo",
        malformed_reason="malformed_model_selection_requirements",
    )
    trusted_keys, key_reasons = _read_json_outside_repo(
        root,
        trusted_keys_path,
        missing_reason="missing_model_evidence_trusted_keys_path",
        inside_reason="model_evidence_trusted_keys_path_inside_repo",
        malformed_reason="malformed_model_evidence_trusted_keys",
    )
    reasons = [*catalog_reasons, *evidence_reasons, *requirements_reasons, *key_reasons]
    key_resolver = None
    if trusted_keys is not None:
        key_resolver, resolver_reasons = _key_resolver(trusted_keys)
        reasons.extend(resolver_reasons)
    verifier = signature_verifier
    if verifier is None:
        verifier, verifier_reasons = _signature_verifier(signature_verifier_backend)
        reasons.extend(verifier_reasons)
    if reasons:
        return _not_ready(reasons)

    assert catalog is not None
    assert evidence is not None
    assert requirements is not None
    assert key_resolver is not None
    assert verifier is not None
    supply = run_reddog_model_selection_artifact_supply(
        repo_root=root,
        catalog_snapshot=catalog,
        verified_evidence_bundle=evidence,
        requirements=requirements,
        output_path=output_path,
        key_resolver=key_resolver,
        signature_verifier=verifier,
        now=int(now_epoch if now_epoch is not None else time.time()),
    )
    if not supply.accepted or supply.status != MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT:
        return _not_ready(supply.rejection_reasons or ("model_selection_artifact_supply_rejected",))
    return ModelSelectionArtifactBootstrapResult(
        accepted=True,
        status=MODEL_SELECTION_ARTIFACT_BOOTSTRAP_APPLIED,
        model_selection_receipt_id=supply.selection_receipt_id,
        output_path=supply.output_path,
        rejection_reasons=(),
    )


def _signature_verifier(backend: str | None) -> tuple[SignatureVerifier | None, tuple[str, ...]]:
    normalized = str(backend or "").strip().lower()
    if normalized != "ed25519":
        return None, ("unsupported_model_evidence_signature_verifier_backend",)
    try:
        from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
            Ed25519SignatureVerifier,
        )
    except Exception:
        return None, ("model_evidence_signature_verifier_unavailable",)
    return Ed25519SignatureVerifier(), ()


def _key_resolver(payload: Mapping[str, Any]) -> tuple[StaticModelEvidenceKeyResolver | None, tuple[str, ...]]:
    raw = payload.get("trusted_public_keys", payload)
    keys: dict[object, str] = {}
    if isinstance(raw, Mapping):
        return None, ("exact_model_evidence_trusted_key_tuples_required",)
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                return None, ("malformed_model_evidence_trusted_keys",)
            role = str(item.get("signer_role") or "")
            fingerprint = str(item.get("signer_key_fingerprint") or "")
            epoch = str(item.get("key_epoch") or "")
            public_key = str(item.get("public_key") or "")
            if not (role and fingerprint and epoch and public_key):
                return None, ("malformed_model_evidence_trusted_keys",)
            keys[(role, fingerprint, epoch)] = public_key
    else:
        return None, ("malformed_model_evidence_trusted_keys",)
    if not keys:
        return None, ("missing_model_evidence_trusted_keys",)
    return StaticModelEvidenceKeyResolver(keys), ()


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    malformed_reason: str,
) -> tuple[Mapping[str, Any] | None, tuple[str, ...]]:
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
    if not isinstance(payload, Mapping):
        return None, (malformed_reason,)
    return payload, ()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(reasons: tuple[str, ...] | list[str]) -> ModelSelectionArtifactBootstrapResult:
    return ModelSelectionArtifactBootstrapResult(
        accepted=False,
        status=MODEL_SELECTION_ARTIFACT_BOOTSTRAP_NOT_READY,
        model_selection_receipt_id=None,
        output_path=None,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
    )


__all__ = [
    "MODEL_SELECTION_ARTIFACT_BOOTSTRAP_APPLIED",
    "MODEL_SELECTION_ARTIFACT_BOOTSTRAP_NOT_READY",
    "ModelSelectionArtifactBootstrapResult",
    "run_reddog_model_selection_artifact_supply_bootstrap",
]
