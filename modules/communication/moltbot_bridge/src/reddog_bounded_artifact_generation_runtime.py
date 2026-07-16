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
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    REDACTION_GATE_PASSED,
    evaluate_redaction_gate,
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
        binding: Mapping[str, Any],
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult: ...


@dataclass(frozen=True)
class FoundupsFusionArtifactGenerationRunner:
    """Explicit-mode FoundUps Fusion runner for bounded artifact generation."""

    runtime_mode: str = ""
    lead_model: str = "z-ai/glm-5.2"
    panel_models: tuple[str, ...] = ("deepseek/deepseek-v4-pro", "moonshotai/kimi-k2.7-code")
    max_tokens: int = 1800
    temperature: float = 0.0

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: Mapping[str, Any],
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
        user_payload = gate.redacted_prompt
        if gate.redacted_context:
            user_payload = gate.redacted_prompt + "\n\n" + gate.redacted_context
        payload = {
            "mode": "foundups_fusion",
            "lead_model": self.lead_model,
            "panel_models": list(self.panel_models),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": timeout_seconds,
            "response_contract": "strict_json_bounded_artifact_contents.v1",
            "_redacted_evidence_context": gate.redacted_context or "",
            "bridge_meta": {"artifact_generation_binding": dict(binding)},
        }
        try:
            from scripts.advisory_model_once import _run_foundups_fusion

            result = _run_foundups_fusion(api_key, user_payload, [], payload)
        except TimeoutError:
            return _model_reject(FAIL_MODEL_TIMEOUT, started=started)
        except Exception:
            return _model_reject("fusion_bridge_call_failed", started=started)
        if not isinstance(result, Mapping) or result.get("ok") is not True:
            return _model_reject("fusion_result_not_ok", started=started, made_network_call=True)
        content = str(result.get("content") or result.get("text") or "")
        parsed = _extract_json_mapping(content)
        if not parsed:
            return _model_reject(FAIL_MODEL_OUTPUT, started=started, made_network_call=True)
        artifacts = _mapping(parsed.get("artifact_contents"))
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


def generate_bounded_artifact_contents(
    request: Mapping[str, Any],
    *,
    runner: Optional[BoundedArtifactGenerationRunner],
) -> BoundedArtifactGenerationResult:
    req = request if isinstance(request, Mapping) else {}
    reasons: List[str] = []
    if req.get("explicit_artifact_generation_requested") is not True:
        reasons.append(FAIL_EXPLICIT_REQUEST)
    if runner is None:
        reasons.append(FAIL_RUNNER_MISSING)

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

    model_result: ArtifactGenerationModelResult | None = None
    artifacts: Dict[str, str] = {}
    if not reasons and runner is not None:
        prompt = _artifact_prompt(req, planned)
        context = str(req.get("evidence_context") or "")
        if len(prompt) + len(context) > MAX_PROMPT_CHARS:
            reasons.append(FAIL_MODEL_OUTPUT)
        else:
            model_result = runner.generate_artifacts(
                prompt=prompt,
                context=context,
                binding=_binding(req, planned),
                timeout_seconds=_timeout(req.get("timeout_seconds")),
            )
            if model_result.ok is not True:
                reasons.extend([FAIL_RUNNER_REJECTED, *model_result.rejection_reasons])
            else:
                artifacts = {str(k): str(v) for k, v in model_result.artifact_contents.items()}
                reasons.extend(_artifact_reasons(artifacts, planned))

    deduped = _dedupe(reasons)
    accepted = not deduped
    manifest = _digest({"artifact_contents": artifacts})
    receipt = BoundedArtifactGenerationReceipt(
        receipt_id="bounded_artifacts_" + _digest(
            {
                "work_order_id": work_order_id,
                "slice_name": slice_name,
                "planned_artifacts": planned,
                "artifact_manifest_digest": manifest,
                "model_result_digest": model_result.model_result_digest if model_result else "",
                "rejection_reasons": deduped,
            }
        ).removeprefix("sha256:")[:16],
        work_order_id=work_order_id,
        slice_name=slice_name,
        planned_artifacts=planned,
        artifact_manifest_digest=manifest,
        model_result_digest=model_result.model_result_digest if model_result else "",
        model_receipt_id=model_result.model_receipt_id if model_result else None,
        rejection_reasons=deduped,
        accepted=accepted,
    )
    return BoundedArtifactGenerationResult(
        decision=ARTIFACT_GENERATION_ACCEPT if accepted else ARTIFACT_GENERATION_REJECT,
        accepted=accepted,
        artifact_contents=artifacts if accepted else {},
        rejection_reasons=deduped,
        receipt=receipt,
        model_result=model_result,
    )


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


def _binding(req: Mapping[str, Any], planned: Sequence[str]) -> Dict[str, Any]:
    return {
        "work_order_id": str(req.get("work_order_id") or ""),
        "slice_name": str(req.get("slice_name") or ""),
        "planned_artifacts_digest": _digest(list(planned)),
        "holoindex_evidence_digest": _digest(_mapping(req.get("holoindex_evidence"))),
        "signed_authority_digest": _digest(_mapping(req.get("signed_authority"))),
        "signed_receipt_chain_digest": _digest(_mapping(req.get("signed_receipt_chain"))),
    }


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
