"""Bounded artifact generation runtime for resident RedDog worktree slices.

Slice: REDDOG_BOUNDED_ARTIFACT_GENERATION_BINDING_PHASE1

This module validates text artifacts produced by an injected coding/model
runner before the resident queue bounded-worker pilot may materialize them in
an isolated worktree. It does not write files, create worktrees, run shell
commands, call GitHub, publish PRs, merge, settle rewards, or re-index
HoloIndex.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_artifact_generation_admission_capability import (
    ArtifactGenerationAuthorityCapability,
    _issue_artifact_generation_model,
    consume_artifact_generation_authority,
    discard_artifact_generation_model,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_authority_lineage import (
    validated_model_authority_lineage,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_provider_contract import (
    ArtifactGenerationModelResult,
    BoundedArtifactGenerationRunner,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_result import (
    ARTIFACT_GENERATION_ACCEPT,
    ARTIFACT_GENERATION_REJECT,
    BoundedArtifactGenerationResult,
    build_generation_result,
)
from modules.communication.moltbot_bridge.src.reddog_foundups_fusion_artifact_provider import (
    ENV_ARTIFACT_GENERATOR_RUNTIME_MODE,
    FAIL_MODEL_OUTPUT,
    FAIL_MODEL_RUNTIME_BINDING_RECEIPT,
    FAIL_MODEL_TIMEOUT,
    FAIL_REDACTION_BLOCKED,
    FAIL_RUNTIME_MODE,
    FoundupsFusionArtifactGenerationRunner,
    RUNTIME_MODE_FOUNDUPS_FUSION,
    _load_runner as _load_foundups_fusion_runner,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_binding_query import (
    runtime_binding_rejections,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
)

FAIL_EXPLICIT_REQUEST = "FAIL_EXPLICIT_ARTIFACT_GENERATION_REQUEST_MISSING"
FAIL_RUNNER_MISSING = "FAIL_ARTIFACT_GENERATION_RUNNER_MISSING"
FAIL_RUNNER_REJECTED = "FAIL_ARTIFACT_GENERATION_RUNNER_REJECTED"
FAIL_REQUEST_BINDING = "FAIL_ARTIFACT_GENERATION_REQUEST_BINDING"
FAIL_PLANNED_ARTIFACTS = "FAIL_ARTIFACT_GENERATION_PLANNED_ARTIFACTS"
FAIL_ARTIFACTS_MISMATCH = "FAIL_ARTIFACT_GENERATION_ARTIFACTS_MISMATCH"
FAIL_CONTENT_INVALID = "FAIL_ARTIFACT_GENERATION_CONTENT_INVALID"
FAIL_SECRET_IN_CONTENT = "FAIL_ARTIFACT_GENERATION_SECRET_IN_CONTENT"
FAIL_HOLOINDEX_EVIDENCE = "FAIL_ARTIFACT_GENERATION_HOLOINDEX_EVIDENCE"
FAIL_AUTHORITY = "FAIL_ARTIFACT_GENERATION_AUTHORITY"
FAIL_RECEIPT_CHAIN = "FAIL_ARTIFACT_GENERATION_RECEIPT_CHAIN"
RUNTIME_SURFACE_ARTIFACT_GENERATION = "reddog_artifact_generation"

MAX_ARTIFACTS = 8
MAX_FILE_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 256 * 1024
MAX_PROMPT_CHARS = 24_000

SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization:",
    "bearer ",
    "begin private key",
    "private_key",
    "password=",
    "secret=",
    "token=",
)


@dataclass(frozen=True)
class _ModelRuntimeAdmission:
    runtime_binding: Dict[str, Any]
    selection: Dict[str, Any]
    verification: Any
    capability: VerifiedRuntimeBindingCapability


def generate_bounded_artifact_contents(
    request: Mapping[str, Any],
    *,
    runner: Optional[BoundedArtifactGenerationRunner],
    authority_capability: Optional[ArtifactGenerationAuthorityCapability] = None,
    model_runtime_binding_capability: Optional[
        VerifiedRuntimeBindingCapability
    ] = None,
    trusted_now_epoch: Optional[Callable[[], int]] = None,
) -> BoundedArtifactGenerationResult:
    req = request if isinstance(request, Mapping) else {}
    reasons, planned, model_selection, admission = _validate_generation_request(
        req,
        runner=runner,
        authority_capability=authority_capability,
        model_runtime_binding_capability=model_runtime_binding_capability,
    )
    model_result, artifacts = _run_bounded_artifact_model(
        req,
        runner=runner,
        planned=planned,
        model_selection=model_selection,
        admission=admission,
        reasons=reasons,
        trusted_now_epoch=trusted_now_epoch,
    )
    return build_generation_result(
        req,
        planned=planned,
        model_selection=model_selection,
        model_result=model_result,
        artifacts=artifacts,
        reasons=reasons,
    )


def _validate_generation_request(
    req: Mapping[str, Any],
    *,
    runner: Optional[BoundedArtifactGenerationRunner],
    authority_capability: Optional[ArtifactGenerationAuthorityCapability],
    model_runtime_binding_capability: Optional[VerifiedRuntimeBindingCapability],
) -> tuple[
    List[str],
    List[str],
    Dict[str, Any],
    Optional[_ModelRuntimeAdmission],
]:
    reasons: List[str] = []
    if req.get("explicit_artifact_generation_requested") is not True:
        reasons.append(FAIL_EXPLICIT_REQUEST)
    if runner is None:
        reasons.append(FAIL_RUNNER_MISSING)
    if not consume_artifact_generation_authority(
        authority_capability,
        req,
    ):
        reasons.append(FAIL_AUTHORITY)
    work_order_id = str(req.get("work_order_id") or "")
    slice_name = str(req.get("slice_name") or "")
    task_summary = str(req.get("task_summary") or "")
    raw_planned = _list(req.get("planned_artifacts"))
    planned = _normalize_paths(raw_planned)
    if not work_order_id or not slice_name or not task_summary:
        reasons.append(FAIL_REQUEST_BINDING)
    if not planned or len(planned) > MAX_ARTIFACTS or len(planned) != len(raw_planned):
        reasons.append(FAIL_PLANNED_ARTIFACTS)

    holo = _mapping(req.get("holoindex_evidence"))
    if holo.get("index_gap_detected") is True or str(holo.get("retrieval_quality") or "").upper() == "INDEX_GAP":
        reasons.append(FAIL_HOLOINDEX_EVIDENCE)
    if _mapping(req.get("signed_authority")).get("accepted") is not True:
        reasons.append(FAIL_AUTHORITY)
    if _mapping(req.get("signed_receipt_chain")).get("accepted") is not True:
        reasons.append(FAIL_RECEIPT_CHAIN)
    model_selection, admission = _model_runtime_binding(
        req.get("model_runtime_binding_receipt"),
        reasons,
        expected_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION,
        signed_authority=_mapping(req.get("signed_authority")),
        selection_payload=req.get("model_selection_receipt"),
        capability=model_runtime_binding_capability,
    )
    if not model_selection:
        reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
    return reasons, planned, model_selection, admission


def _run_bounded_artifact_model(
    req: Mapping[str, Any],
    *,
    runner: Optional[BoundedArtifactGenerationRunner],
    planned: Sequence[str],
    model_selection: Mapping[str, Any],
    admission: Optional[_ModelRuntimeAdmission],
    reasons: List[str],
    trusted_now_epoch: Optional[Callable[[], int]],
) -> tuple[ArtifactGenerationModelResult | None, Dict[str, str]]:
    model_result: ArtifactGenerationModelResult | None = None
    artifacts: Dict[str, str] = {}
    if not reasons and runner is not None:
        prompt = _artifact_prompt(req, planned)
        context = str(req.get("evidence_context") or "")
        if len(prompt) + len(context) > MAX_PROMPT_CHARS:
            reasons.append(FAIL_MODEL_OUTPUT)
        elif admission is None:
            reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
        elif not callable(trusted_now_epoch):
            reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
        else:
            available_providers = getattr(runner, "available_model_providers", ())
            model_capability = _issue_artifact_generation_model(
                invocation_binding=_binding(req, planned, model_selection),
                runtime_binding=admission.runtime_binding,
                selection=admission.selection,
                verification=admission.verification,
                verified_capability=admission.capability,
                available_providers=available_providers,
                trusted_now_epoch=trusted_now_epoch,
            )
            if model_capability is None:
                reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
                return model_result, artifacts
            try:
                model_result = runner.generate_artifacts(
                    prompt=prompt,
                    context=context,
                    binding=model_capability,
                    timeout_seconds=_timeout(req.get("timeout_seconds")),
                )
            finally:
                discard_artifact_generation_model(model_capability)
            if model_result.ok is not True:
                reasons.extend([FAIL_RUNNER_REJECTED, *model_result.rejection_reasons])
            else:
                artifacts = {str(k): str(v) for k, v in model_result.artifact_contents.items()}
                reasons.extend(_artifact_reasons(artifacts, planned))
    return model_result, artifacts


def _artifact_prompt(req: Mapping[str, Any], planned: Sequence[str]) -> str:
    return json.dumps(
        {
            "mission": "Produce exact text contents for the planned repository artifacts only.",
            "work_order_id": str(req.get("work_order_id") or ""),
            "slice_name": str(req.get("slice_name") or ""),
            "task_summary": str(req.get("task_summary") or ""),
            "planned_artifacts": list(planned),
            "output_schema": {"artifact_contents": {"path": "text content"}},
            "hard_rules": [
                "Return JSON only.",
                "Keys must exactly match planned_artifacts.",
                "Do not include secrets, credentials, tokens, or private keys.",
                "Do not create extra files.",
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _binding(
    req: Mapping[str, Any],
    planned: Sequence[str],
    model_selection: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "work_order_id": str(req.get("work_order_id") or ""),
        "slice_name": str(req.get("slice_name") or ""),
        "planned_artifacts_digest": _digest(list(planned)),
        "holoindex_evidence_digest": _digest(_mapping(req.get("holoindex_evidence"))),
        "signed_authority_digest": _digest(_mapping(req.get("signed_authority"))),
        "signed_receipt_chain_digest": _digest(_mapping(req.get("signed_receipt_chain"))),
        "model_selection": dict(model_selection),
    }


def _model_runtime_binding(
    value: Any,
    reasons: List[str],
    *,
    expected_surface: str,
    signed_authority: Mapping[str, Any],
    selection_payload: Any,
    capability: Optional[VerifiedRuntimeBindingCapability],
) -> tuple[Dict[str, Any], Optional[_ModelRuntimeAdmission]]:
    if value is None:
        return {}, None
    binding = _json_compatible_mapping(_mapping(value))
    if not binding:
        reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
        return {}, None
    try:
        receipt = rehydrate_model_runtime_binding_receipt(binding)
    except Exception:
        reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
        return {}, None
    if runtime_binding_rejections(receipt, expected_surface=expected_surface):
        reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
        return {}, None
    selection = _json_compatible_mapping(_mapping(selection_payload))
    lineage = validated_model_authority_lineage(
        receipt=receipt,
        binding=binding,
        signed_authority=signed_authority,
        selection=selection,
        capability=capability,
    )
    if lineage is None:
        reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
        return {}, None
    selection_receipt, verification = lineage
    model_selection = _model_selection_payload(
        receipt,
        receipt.to_reddog_bridge_payload(),
        selection_receipt,
        verification,
        selection,
    )
    return model_selection, _ModelRuntimeAdmission(
        runtime_binding=binding,
        selection=selection,
        verification=verification,
        capability=capability,
    )


def _model_selection_payload(
    receipt: Any,
    payload: Mapping[str, Any],
    selection_receipt: Any,
    verification: Any,
    selection: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "receipt_id": receipt.selection_receipt_id,
        "digest": _digest(selection),
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "task_family": receipt.task_family,
        "purpose": "production",
        "selected_model_ids": [receipt.principal_model, *receipt.panel_models],
        "role_assignments": [asdict(item) for item in selection_receipt.role_assignments],
        "panel_topology_digest": selection_receipt.panel_topology_digest or "",
        "lead_model": str(payload.get("lead_model") or ""),
        "panel_models": [str(item) for item in payload.get("panel_models") or ()],
        "model_runtime_binding_receipt_id": receipt.receipt_id,
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(receipt),
        "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        "model_runtime_binding_verification_digest": verification_receipt_digest(verification),
        "runtime_surface": receipt.runtime_surface,
    }


def _json_compatible_mapping(value: Mapping[str, Any]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        normalized = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    except (TypeError, ValueError):
        return {}
    return normalized if isinstance(normalized, dict) else {}


def _artifact_reasons(artifacts: Mapping[str, str], planned: Sequence[str]) -> List[str]:
    reasons: List[str] = []
    normalized = _normalize_paths(artifacts.keys())
    if sorted(normalized) != sorted(planned):
        reasons.append(FAIL_ARTIFACTS_MISMATCH)
    total = 0
    for path, content in artifacts.items():
        if _normalize_path(path) is None:
            reasons.append(FAIL_ARTIFACTS_MISMATCH)
        if not isinstance(content, str):
            reasons.append(FAIL_CONTENT_INVALID)
            continue
        lower = content.lower()
        if any(marker in lower for marker in SECRET_MARKERS):
            reasons.append(FAIL_SECRET_IN_CONTENT)
        if "\x00" in content:
            reasons.append(FAIL_CONTENT_INVALID)
            continue
        size = len(content.encode("utf-8"))
        total += size
        if size > MAX_FILE_BYTES:
            reasons.append(FAIL_CONTENT_INVALID)
    if total > MAX_TOTAL_BYTES:
        reasons.append(FAIL_CONTENT_INVALID)
    return reasons


def _normalize_paths(values: Sequence[Any]) -> List[str]:
    paths: List[str] = []
    for value in values:
        path = _normalize_path(value)
        if path is not None:
            paths.append(path)
    return _dedupe(paths)


def _normalize_path(value: Any) -> Optional[str]:
    text = str(value or "").replace("\\", "/").strip().strip("/")
    if not text or text.startswith("/") or ":" in text or "\x00" in text:
        return None
    parts = [part.strip(" \t").rstrip(" .") for part in text.split("/")]
    if not parts or any((not part or part in {".", ".."}) for part in parts):
        return None
    lowered = "/".join(parts).lower()
    if fnmatch.fnmatch(lowered, "**/.env") or "/secrets/" in lowered:
        return None
    return "/".join(parts)


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _timeout(value: Any) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = 120
    return max(1, min(parsed, 600))


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


__all__ = [
    "ARTIFACT_GENERATION_ACCEPT",
    "ARTIFACT_GENERATION_REJECT",
    "ArtifactGenerationModelResult",
    "BoundedArtifactGenerationResult",
    "BoundedArtifactGenerationRunner",
    "ENV_ARTIFACT_GENERATOR_RUNTIME_MODE",
    "FAIL_MODEL_TIMEOUT",
    "FAIL_REDACTION_BLOCKED",
    "FAIL_RUNTIME_MODE",
    "FoundupsFusionArtifactGenerationRunner",
    "RUNTIME_MODE_FOUNDUPS_FUSION",
    "_load_foundups_fusion_runner",
    "generate_bounded_artifact_contents",
]
