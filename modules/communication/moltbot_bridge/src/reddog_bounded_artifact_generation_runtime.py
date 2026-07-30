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
import hmac
import importlib.util
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    REDACTION_GATE_PASSED,
    evaluate_redaction_gate,
)
from modules.communication.moltbot_bridge.src.reddog_artifact_generation_admission_capability import (
    ArtifactGenerationAuthorityCapability,
    ArtifactGenerationModelCapability,
    _issue_artifact_generation_model,
    consume_artifact_generation_authority,
    consume_artifact_generation_model,
    discard_artifact_generation_model,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_binding_query import (
    runtime_binding_rejections,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    SelectionDecision,
    SelectionPurpose,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
    rehydrate_model_selection_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    VerifiedRuntimeBindingCapability,
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)

ARTIFACT_GENERATION_ACCEPT = "BOUNDED_ARTIFACT_GENERATION_ACCEPT"
ARTIFACT_GENERATION_REJECT = "BOUNDED_ARTIFACT_GENERATION_REJECT"

ENV_ARTIFACT_GENERATOR_RUNTIME_MODE = "REDDOG_ARTIFACT_GENERATOR_RUNTIME_MODE"
RUNTIME_MODE_FOUNDUPS_FUSION = "foundups_fusion"

FAIL_EXPLICIT_REQUEST = "FAIL_EXPLICIT_ARTIFACT_GENERATION_REQUEST_MISSING"
FAIL_RUNNER_MISSING = "FAIL_ARTIFACT_GENERATION_RUNNER_MISSING"
FAIL_RUNNER_REJECTED = "FAIL_ARTIFACT_GENERATION_RUNNER_REJECTED"
FAIL_MODEL_TIMEOUT = "FAIL_ARTIFACT_GENERATION_MODEL_TIMEOUT"
FAIL_MODEL_OUTPUT = "FAIL_ARTIFACT_GENERATION_MODEL_OUTPUT"
FAIL_REQUEST_BINDING = "FAIL_ARTIFACT_GENERATION_REQUEST_BINDING"
FAIL_PLANNED_ARTIFACTS = "FAIL_ARTIFACT_GENERATION_PLANNED_ARTIFACTS"
FAIL_ARTIFACTS_MISMATCH = "FAIL_ARTIFACT_GENERATION_ARTIFACTS_MISMATCH"
FAIL_CONTENT_INVALID = "FAIL_ARTIFACT_GENERATION_CONTENT_INVALID"
FAIL_SECRET_IN_CONTENT = "FAIL_ARTIFACT_GENERATION_SECRET_IN_CONTENT"
FAIL_HOLOINDEX_EVIDENCE = "FAIL_ARTIFACT_GENERATION_HOLOINDEX_EVIDENCE"
FAIL_AUTHORITY = "FAIL_ARTIFACT_GENERATION_AUTHORITY"
FAIL_RECEIPT_CHAIN = "FAIL_ARTIFACT_GENERATION_RECEIPT_CHAIN"
FAIL_REDACTION_BLOCKED = "FAIL_ARTIFACT_GENERATION_REDACTION_BLOCKED"
FAIL_RUNTIME_MODE = "FAIL_ARTIFACT_GENERATION_RUNTIME_MODE"
FAIL_MODEL_RUNTIME_BINDING_RECEIPT = "FAIL_ARTIFACT_GENERATION_MODEL_RUNTIME_BINDING_RECEIPT"
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
class ArtifactGenerationModelResult:
    ok: bool
    status: str
    artifact_contents: Mapping[str, str] = field(default_factory=dict)
    model_receipt_id: Optional[str] = None
    model_result_digest: str = ""
    made_network_call: bool = False
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BoundedArtifactGenerationRunner(Protocol):
    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult: ...


@dataclass(frozen=True)
class FoundupsFusionArtifactGenerationRunner:
    """Explicit-mode FoundUps Fusion runner for bounded artifact generation."""

    runtime_mode: str = ""
    max_tokens: int = 1800
    temperature: float = 0.0

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        started = time.monotonic()
        configured_mode = (self.runtime_mode or os.getenv(ENV_ARTIFACT_GENERATOR_RUNTIME_MODE, "")).strip()
        if configured_mode != RUNTIME_MODE_FOUNDUPS_FUSION:
            return _model_reject(FAIL_RUNTIME_MODE, started=started)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return _model_reject("missing_openrouter_api_key", started=started)
        gate = evaluate_redaction_gate(prompt, context, audit_mode=True)
        if gate.status != REDACTION_GATE_PASSED or not gate.redacted_prompt:
            return _model_reject(FAIL_REDACTION_BLOCKED, started=started)
        verified_binding = consume_artifact_generation_model(binding)
        model_topology = _runtime_model_topology(verified_binding or {})
        if not model_topology:
            return _model_reject(FAIL_MODEL_RUNTIME_BINDING_RECEIPT, started=started)
        return _invoke_foundups_fusion(
            runner=self,
            api_key=api_key,
            redacted_prompt=gate.redacted_prompt,
            redacted_context=gate.redacted_context or "",
            verified_binding=verified_binding or {},
            model_topology=model_topology,
            timeout_seconds=timeout_seconds,
            started=started,
        )


def _invoke_foundups_fusion(
    *,
    runner: FoundupsFusionArtifactGenerationRunner,
    api_key: str,
    redacted_prompt: str,
    redacted_context: str,
    verified_binding: Mapping[str, Any],
    model_topology: Mapping[str, Any],
    timeout_seconds: int,
    started: float,
) -> ArtifactGenerationModelResult:
    user_payload = redacted_prompt
    if redacted_context:
        user_payload += "\n\n" + redacted_context
    payload = {
            "mode": "foundups_fusion",
            "lead_model": model_topology["lead_model"],
            "panel_models": list(model_topology["panel_models"]),
            "max_tokens": runner.max_tokens,
            "temperature": runner.temperature,
            "timeout": timeout_seconds,
            "response_contract": "strict_json_bounded_artifact_contents.v1",
            "_redacted_evidence_context": redacted_context,
            "bridge_meta": {
                "artifact_generation_binding": verified_binding,
                "model_selection_receipt_id": model_topology["model_selection_receipt_id"],
                "model_runtime_binding_receipt_id": model_topology["model_runtime_binding_receipt_id"],
                "model_runtime_binding_verification_receipt_id": model_topology[
                    "model_runtime_binding_verification_receipt_id"
                ],
                "model_runtime_binding_verification_digest": model_topology[
                    "model_runtime_binding_verification_digest"
                ],
            },
        }
    try:
        result = _load_foundups_fusion_runner()(api_key, user_payload, [], payload)
    except TimeoutError:
        return _model_reject(FAIL_MODEL_TIMEOUT, started=started)
    except Exception:
        return _model_reject("fusion_bridge_call_failed", started=started)
    return _parse_foundups_fusion_result(result, started=started)


def _parse_foundups_fusion_result(
    result: Any,
    *,
    started: float,
) -> ArtifactGenerationModelResult:
    if not isinstance(result, Mapping) or result.get("ok") is not True:
        return _model_reject("fusion_result_not_ok", started=started, made_network_call=True)
    content = str(result.get("content") or result.get("text") or "")
    parsed = _extract_json_mapping(content)
    artifacts = _mapping(parsed.get("artifact_contents")) if parsed else {}
    if not artifacts:
        return _model_reject(FAIL_MODEL_OUTPUT, started=started, made_network_call=True)
    review_packet = result.get("review_packet") if isinstance(result.get("review_packet"), Mapping) else {}
    return ArtifactGenerationModelResult(
        ok=True,
        status="MODEL_OK",
        artifact_contents={str(k): str(v) for k, v in artifacts.items()},
        model_receipt_id=str(review_packet.get("receipt_id") or "") or None,
        model_result_digest=_digest({"artifact_contents": artifacts, "review_packet": review_packet}),
        made_network_call=True,
        rejection_reasons=(),
    )


@dataclass(frozen=True)
class BoundedArtifactGenerationReceipt:
    receipt_id: str
    work_order_id: str
    slice_name: str
    planned_artifacts: List[str]
    artifact_manifest_digest: str
    model_result_digest: str
    model_receipt_id: Optional[str]
    rejection_reasons: List[str]
    accepted: bool
    model_selection_receipt_id: Optional[str] = None
    model_selection_digest: str = ""
    model_runtime_binding_receipt_id: Optional[str] = None
    model_runtime_binding_digest: str = ""
    model_runtime_binding_verification_receipt_id: Optional[str] = None
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
    model_result: Optional[ArtifactGenerationModelResult] = None
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
    )
    return _build_generation_result(
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
    model_runtime_binding_capability: Optional[
        VerifiedRuntimeBindingCapability
    ],
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
        else:
            model_capability = _issue_artifact_generation_model(
                invocation_binding=_binding(req, planned, model_selection),
                runtime_binding=admission.runtime_binding,
                selection=admission.selection,
                verification=admission.verification,
                verified_capability=admission.capability,
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


def _build_generation_result(
    req: Mapping[str, Any],
    *,
    planned: Sequence[str],
    model_selection: Mapping[str, Any],
    model_result: ArtifactGenerationModelResult | None,
    artifacts: Mapping[str, str],
    reasons: Sequence[str],
) -> BoundedArtifactGenerationResult:
    work_order_id = str(req.get("work_order_id") or "")
    slice_name = str(req.get("slice_name") or "")
    deduped = _dedupe(reasons)
    accepted = not deduped
    manifest = _digest({"artifact_contents": artifacts})
    receipt = BoundedArtifactGenerationReceipt(
        receipt_id=_generation_receipt_id(
            work_order_id=work_order_id,
            slice_name=slice_name,
            planned=planned,
            manifest=manifest,
            model_result=model_result,
            model_selection=model_selection,
            reasons=deduped,
        ),
        work_order_id=work_order_id,
        slice_name=slice_name,
        planned_artifacts=planned,
        artifact_manifest_digest=manifest,
        model_result_digest=model_result.model_result_digest if model_result else "",
        model_receipt_id=model_result.model_receipt_id if model_result else None,
        rejection_reasons=deduped,
        accepted=accepted,
        model_selection_receipt_id=model_selection.get("receipt_id"),
        model_selection_digest=model_selection.get("digest", ""),
        model_runtime_binding_receipt_id=model_selection.get("model_runtime_binding_receipt_id"),
        model_runtime_binding_digest=model_selection.get("model_runtime_binding_digest", ""),
        model_runtime_binding_verification_receipt_id=model_selection.get(
            "model_runtime_binding_verification_receipt_id"
        ),
        model_runtime_binding_verification_digest=model_selection.get(
            "model_runtime_binding_verification_digest", ""
        ),
    )
    return BoundedArtifactGenerationResult(
        decision=ARTIFACT_GENERATION_ACCEPT if accepted else ARTIFACT_GENERATION_REJECT,
        accepted=accepted,
        artifact_contents=dict(artifacts) if accepted else {},
        rejection_reasons=deduped,
        receipt=receipt,
        model_result=model_result,
    )


def _generation_receipt_id(
    *,
    work_order_id: str,
    slice_name: str,
    planned: Sequence[str],
    manifest: str,
    model_result: ArtifactGenerationModelResult | None,
    model_selection: Mapping[str, Any],
    reasons: Sequence[str],
) -> str:
    payload = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "planned_artifacts": planned,
        "artifact_manifest_digest": manifest,
        "model_result_digest": model_result.model_result_digest if model_result else "",
        "model_selection_receipt_id": model_selection.get("receipt_id"),
        "model_selection_digest": model_selection.get("digest", ""),
        "model_runtime_binding_receipt_id": model_selection.get(
            "model_runtime_binding_receipt_id"
        ),
        "model_runtime_binding_digest": model_selection.get(
            "model_runtime_binding_digest", ""
        ),
        "model_runtime_binding_verification_receipt_id": model_selection.get(
            "model_runtime_binding_verification_receipt_id"
        ),
        "model_runtime_binding_verification_digest": model_selection.get(
            "model_runtime_binding_verification_digest", ""
        ),
        "rejection_reasons": reasons,
    }
    return "bounded_artifacts_" + _digest(payload).removeprefix("sha256:")[:16]


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
    lineage = _validated_model_authority_lineage(
        receipt=receipt,
        binding=binding,
        signed_authority=signed_authority,
        selection_payload=selection_payload,
        capability=capability,
    )
    if lineage is None:
        reasons.append(FAIL_MODEL_RUNTIME_BINDING_RECEIPT)
        return {}, None
    selection_receipt, selection, verification = lineage
    payload = receipt.to_reddog_bridge_payload()
    model_selection = {
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
        "model_runtime_binding_verification_digest": verification_receipt_digest(
            verification
        ),
        "runtime_surface": receipt.runtime_surface,
    }
    return model_selection, _ModelRuntimeAdmission(
        runtime_binding=binding,
        selection=selection,
        verification=verification,
        capability=capability,
    )


def _validated_model_authority_lineage(
    *,
    receipt: Any,
    binding: Mapping[str, Any],
    signed_authority: Mapping[str, Any],
    selection_payload: Any,
    capability: Optional[VerifiedRuntimeBindingCapability],
) -> Optional[tuple[Any, Dict[str, Any], Any]]:
    verification = verified_runtime_binding_receipt(binding)
    if verification is None:
        return None
    selection = _json_compatible_mapping(_mapping(selection_payload))
    if not selection:
        return None
    try:
        selection_receipt = rehydrate_model_selection_receipt(selection)
    except Exception:
        return None
    if not _selection_matches_runtime(selection_receipt, receipt):
        return None
    expected = _model_authority_expected_values(
        receipt, selection_receipt, selection, verification, signed_authority
    )
    if not all(_trusted_value_matches(actual, trusted) for actual, trusted in expected):
        return None
    if type(capability) is not VerifiedRuntimeBindingCapability:
        return None
    return selection_receipt, selection, verification


def _selection_matches_runtime(selection_receipt: Any, receipt: Any) -> bool:
    return (
        selection_receipt.decision == SelectionDecision.SELECTED
        and selection_receipt.requirements.purpose == SelectionPurpose.PRODUCTION
        and selection_receipt.receipt_id == receipt.selection_receipt_id
        and tuple(selection_receipt.selected_model_ids)
        == (str(receipt.principal_model or ""), *tuple(receipt.panel_models))
        and _selection_roles(selection_receipt) == _runtime_roles(receipt)
    )


def _model_authority_expected_values(
    receipt: Any,
    selection_receipt: Any,
    selection: Mapping[str, Any],
    verification: Any,
    signed_authority: Mapping[str, Any],
) -> tuple[tuple[Any, Any], ...]:
    return (
        (receipt.receipt_id, signed_authority.get("model_runtime_binding_receipt_id")),
        (
            canonical_model_runtime_binding_digest(receipt),
            signed_authority.get("model_runtime_binding_digest"),
        ),
        (selection_receipt.receipt_id, signed_authority.get("model_selection_receipt_id")),
        (_digest(selection), signed_authority.get("model_selection_digest")),
        (
            verification.receipt_id,
            signed_authority.get(
                "model_runtime_binding_verification_receipt_id"
            ),
        ),
        (
            verification_receipt_digest(verification),
            signed_authority.get(
                "model_runtime_binding_verification_digest"
            ),
        ),
    )


def _trusted_value_matches(actual: Any, trusted: Any) -> bool:
    return (
        isinstance(actual, str)
        and bool(actual)
        and isinstance(trusted, str)
        and hmac.compare_digest(actual, trusted)
    )


def _selection_roles(receipt: Any) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (item.role, item.canonical_model_id, item.provider)
        for item in receipt.role_assignments
    )


def _runtime_roles(receipt: Any) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (item.role, item.model_id, item.provider)
        for item in receipt.role_bindings
    )


def _json_compatible_mapping(value: Mapping[str, Any]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        normalized = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    except (TypeError, ValueError):
        return {}
    return normalized if isinstance(normalized, dict) else {}


def _runtime_model_topology(
    binding: Mapping[str, Any],
) -> Dict[str, Any]:
    selection = _mapping(binding.get("model_selection"))
    lead = str(selection.get("lead_model") or "")
    raw_panel = selection.get("panel_models")
    if not lead or not isinstance(raw_panel, list):
        return {}
    panel = [str(item) for item in raw_panel]
    result = {
        "lead_model": lead,
        "panel_models": tuple(item for item in panel if item),
        "model_selection_receipt_id": str(selection.get("receipt_id") or ""),
        "model_runtime_binding_receipt_id": str(selection.get("model_runtime_binding_receipt_id") or ""),
        "model_runtime_binding_verification_receipt_id": str(
            selection.get("model_runtime_binding_verification_receipt_id") or ""
        ),
        "model_runtime_binding_verification_digest": str(
            selection.get("model_runtime_binding_verification_digest") or ""
        ),
    }
    required = (
        "model_selection_receipt_id",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_verification_receipt_id",
        "model_runtime_binding_verification_digest",
    )
    return result if all(result[name] for name in required) else {}


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


def _extract_json_mapping(text: str) -> Mapping[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, Mapping) else {}


def _load_foundups_fusion_runner():
    try:
        from scripts.advisory_model_once import _run_foundups_fusion

        return _run_foundups_fusion
    except Exception:
        script_path = Path(__file__).resolve().parents[4] / "scripts" / "advisory_model_once.py"
        spec = importlib.util.spec_from_file_location(
            "reddog_artifact_generation_advisory_model_once",
            script_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError("advisory_model_once bridge unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "_run_foundups_fusion")


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


def _model_reject(
    reason: str,
    *,
    started: float,
    made_network_call: bool = False,
) -> ArtifactGenerationModelResult:
    return ArtifactGenerationModelResult(
        ok=False,
        status=reason,
        artifact_contents={},
        model_receipt_id=None,
        model_result_digest=_digest({"reason": reason, "elapsed_ms": int((time.monotonic() - started) * 1000)}),
        made_network_call=made_network_call,
        rejection_reasons=(reason,),
    )


__all__ = [
    "ARTIFACT_GENERATION_ACCEPT",
    "ARTIFACT_GENERATION_REJECT",
    "ArtifactGenerationModelResult",
    "BoundedArtifactGenerationResult",
    "BoundedArtifactGenerationRunner",
    "FoundupsFusionArtifactGenerationRunner",
    "generate_bounded_artifact_contents",
]
