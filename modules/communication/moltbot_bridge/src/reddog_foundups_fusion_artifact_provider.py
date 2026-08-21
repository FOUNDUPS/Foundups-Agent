"""Explicit FoundUps Fusion provider for bounded artifact generation."""

from __future__ import annotations
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    REDACTION_GATE_PASSED,
    evaluate_redaction_gate,
)
from .reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
    consume_artifact_generation_model,
)
from .reddog_artifact_generation_model_binding import (
    artifact_generation_digest,
    resolved_model_topology,
)
from .reddog_artifact_generation_provider_contract import ArtifactGenerationModelResult

ENV_ARTIFACT_GENERATOR_RUNTIME_MODE = "REDDOG_ARTIFACT_GENERATOR_RUNTIME_MODE"
RUNTIME_MODE_FOUNDUPS_FUSION = "foundups_fusion"
FAIL_MODEL_TIMEOUT = "FAIL_ARTIFACT_GENERATION_MODEL_TIMEOUT"
FAIL_MODEL_OUTPUT = "FAIL_ARTIFACT_GENERATION_MODEL_OUTPUT"
FAIL_REDACTION_BLOCKED = "FAIL_ARTIFACT_GENERATION_REDACTION_BLOCKED"
FAIL_RUNTIME_MODE = "FAIL_ARTIFACT_GENERATION_RUNTIME_MODE"
FAIL_MODEL_RUNTIME_BINDING_RECEIPT = "FAIL_ARTIFACT_GENERATION_MODEL_RUNTIME_BINDING_RECEIPT"

@dataclass(frozen=True)
class FoundupsFusionArtifactGenerationRunner:
    """Explicit-mode FoundUps Fusion runner for bounded artifact generation."""

    runtime_mode: str = ""
    max_tokens: int = 1800
    temperature: float = 0.0
    # Fusion's transport is OpenRouter. Vendor ownership encoded in a model ID
    # is not the provider route used for egress.
    available_model_providers: tuple[str, ...] = ()

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        started = time.monotonic()
        mode = (self.runtime_mode or os.getenv(ENV_ARTIFACT_GENERATOR_RUNTIME_MODE, "")).strip()
        if mode != RUNTIME_MODE_FOUNDUPS_FUSION:
            return _reject(FAIL_RUNTIME_MODE, started)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return _reject("missing_openrouter_api_key", started)
        gate = evaluate_redaction_gate(prompt, context, audit_mode=True)
        if gate.status != REDACTION_GATE_PASSED or not gate.redacted_prompt:
            return _reject(FAIL_REDACTION_BLOCKED, started)
        verified = consume_artifact_generation_model(binding)
        topology = _topology(verified or {})
        if not topology:
            return _reject(FAIL_MODEL_RUNTIME_BINDING_RECEIPT, started)
        return _invoke(
            self,
            api_key,
            gate.redacted_prompt,
            gate.redacted_context or "",
            verified or {},
            topology,
            timeout_seconds,
            started,
        )
def _invoke(
    runner: FoundupsFusionArtifactGenerationRunner,
    api_key: str,
    prompt: str,
    context: str,
    verified: Mapping[str, Any],
    topology: Mapping[str, Any],
    timeout: int,
    started: float,
) -> ArtifactGenerationModelResult:
    payload = {
        "mode": RUNTIME_MODE_FOUNDUPS_FUSION,
        "lead_model": topology["lead_model"],
        "panel_models": list(topology["panel_models"]),
        "max_tokens": runner.max_tokens,
        "temperature": runner.temperature,
        "timeout": timeout,
        "response_contract": "strict_json_bounded_artifact_contents.v1",
        "_redacted_evidence_context": context,
        "bridge_meta": {"artifact_generation_binding": verified, **_lineage(topology)},
    }
    try:
        runtime = _runtime_loader()
    except Exception:
        return _reject("fusion_bridge_unavailable", started)
    try:
        result = runtime(api_key, prompt + ("\n\n" + context if context else ""), [], payload)
    except TimeoutError:
        return _reject(FAIL_MODEL_TIMEOUT, started, True)
    except Exception:
        return _reject("fusion_bridge_call_failed", started, True)
    return _parse(result, started)
def _parse(result: Any, started: float) -> ArtifactGenerationModelResult:
    if not isinstance(result, Mapping) or result.get("ok") is not True:
        return _reject("fusion_result_not_ok", started, True)
    parsed = _json_mapping(str(result.get("content") or result.get("text") or ""))
    artifacts = parsed.get("artifact_contents") if isinstance(parsed, Mapping) else None
    if not isinstance(artifacts, Mapping) or not artifacts:
        return _reject(FAIL_MODEL_OUTPUT, started, True)
    review = result.get("review_packet")
    review = review if isinstance(review, Mapping) else {}
    normalized = {str(key): str(value) for key, value in artifacts.items()}
    return ArtifactGenerationModelResult(
        ok=True,
        status="MODEL_OK",
        artifact_contents=normalized,
        model_receipt_id=str(review.get("receipt_id") or "") or None,
        model_result_digest=artifact_generation_digest(
            {"artifact_contents": normalized, "review_packet": review}
        ),
        made_network_call=True,
        provider_runtime=RUNTIME_MODE_FOUNDUPS_FUSION,
        provider_invocation_performed=True,
        external_side_effects_possible=True,
    )
def _topology(binding: Mapping[str, Any]) -> dict[str, Any]:
    endpoints = resolved_model_topology(binding)
    if endpoints is None:
        return {}
    principals = [row for row in endpoints if row[0] == "principal"]
    if len(principals) != 1:
        return {}
    lead = principals[0][2]
    panel = tuple(row[2] for row in endpoints if row[0] != "principal")
    selected = binding.get("model_selection")
    required = (
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "model_runtime_binding_verification_receipt_id",
        "model_runtime_binding_verification_digest",
    )
    lineage = {
        "model_selection_receipt_id": selected.get("receipt_id") if isinstance(selected, Mapping) else None,
        "model_selection_digest": selected.get("digest") if isinstance(selected, Mapping) else None,
        **{
            key: selected.get(key) if isinstance(selected, Mapping) else None
            for key in required
        },
        "model_runtime_topology_resolution_receipt_id": binding.get("runtime_topology_resolution_receipt_id"),
        "model_runtime_topology_verification_receipt_id": binding.get("runtime_topology_verification_receipt_id"),
    }
    return {"lead_model": lead, "panel_models": panel, **lineage} if lead else {}
def _lineage(topology: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in topology.items() if key not in {"lead_model", "panel_models"}}
def _json_mapping(content: str) -> Mapping[str, Any]:
    raw = content.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        lines = lines[1:] if lines else lines
        lines = lines[:-1] if lines and lines[-1].startswith("```") else lines
        raw = "\n".join(lines).strip()
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, Mapping) else {}
def _load_runner():
    root = Path(__file__).resolve().parents[4]
    path = root / "scripts" / "advisory_model_once.py"
    spec = importlib.util.spec_from_file_location("reddog_artifact_fusion_bridge", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("fusion_bridge_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._run_foundups_fusion
def _runtime_loader():
    module = sys.modules.get(
        "modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime"
    )
    loader = getattr(module, "_load_foundups_fusion_runner", _load_runner)
    return loader()
def _reject(reason: str, started: float, made_network_call: bool = False) -> ArtifactGenerationModelResult:
    return ArtifactGenerationModelResult(
        ok=False,
        status="MODEL_REJECT",
        model_result_digest=artifact_generation_digest(
            {"reason": reason, "duration_ms": int((time.monotonic() - started) * 1000)}
        ),
        made_network_call=made_network_call,
        rejection_reasons=(reason,),
        provider_runtime=RUNTIME_MODE_FOUNDUPS_FUSION,
        provider_invocation_performed=made_network_call,
        external_side_effects_possible=made_network_call,
    )

__all__ = [
    "ENV_ARTIFACT_GENERATOR_RUNTIME_MODE",
    "FoundupsFusionArtifactGenerationRunner",
    "RUNTIME_MODE_FOUNDUPS_FUSION",
]
