# -*- coding: utf-8 -*-
"""RTK evaluation dry-run for token-efficiency measurement.

Slice: RTK_EVALUATION_DRY_RUN_PHASE1

This module evaluates a caller-supplied compression candidate. It never invokes
RTK, never executes commands, and never performs runtime compression. Acceptance
means "the supplied candidate is safe enough to measure", not "wire RTK".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from .bypass_classifier import BypassClassifier, get_bypass_classifier
from .compute_governor import RedDogComputeDecision, Routing
from .telemetry_service import (
    ContentType,
    Operation,
    SourceLayer,
    TokenCompressionEvent,
    build_token_compression_event,
    get_telemetry_store,
)


class RtkDryRunDecision(Enum):
    """RTK dry-run evaluation result."""

    ACCEPT = "RTK_DRY_RUN_ACCEPT"
    REJECT = "RTK_DRY_RUN_REJECT"


class RtkDryRunRejection(Enum):
    """Fail-closed rejection reasons."""

    COMPUTE_DECISION_NOT_ALLOW_EVALUATION = "COMPUTE_DECISION_NOT_ALLOW_EVALUATION"
    RAW_OUTPUT_REQUIRES_BYPASS = "RAW_OUTPUT_REQUIRES_BYPASS"
    CANDIDATE_OUTPUT_REQUIRES_BYPASS = "CANDIDATE_OUTPUT_REQUIRES_BYPASS"
    RAW_REF_REQUIRED = "RAW_REF_REQUIRED"
    CANDIDATE_OUTPUT_REQUIRED = "CANDIDATE_OUTPUT_REQUIRED"
    NO_POSITIVE_SAVINGS = "NO_POSITIVE_SAVINGS"
    RUNTIME_REINDEX_FORBIDDEN = "RUNTIME_REINDEX_FORBIDDEN"


@dataclass(frozen=True)
class RtkEvaluationDryRunResult:
    """Dry-run result for one caller-supplied RTK candidate."""

    evaluation_id: str
    decision: RtkDryRunDecision
    command_digest: str
    raw_output_digest: str
    candidate_output_digest: str
    raw_ref_digest: str
    telemetry_event_id: str | None
    input_bytes: int
    candidate_bytes: int
    bytes_saved: int
    tokens_saved: int
    savings_ratio: float
    bypass_class: str | None
    rejection_reasons: list[str]
    dry_run_only: bool = True
    rtk_invoked: bool = False
    command_executed: bool = False
    compression_performed: bool = False
    raw_content_persisted: bool = False
    runtime_reindex_allowed: bool = False

    @property
    def accepted(self) -> bool:
        return self.decision == RtkDryRunDecision.ACCEPT

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload

    def to_m2m_compact(self) -> str:
        status = "ACCEPT" if self.accepted else "REJECT"
        return (
            f"RTK_EVAL:{self.evaluation_id[:8]} "
            f"STATUS:{status} "
            f"SAVED:{self.tokens_saved} "
            f"RATIO:{self.savings_ratio:.3f} "
            f"BYPASS:{self.bypass_class or 'none'}"
        )

    def to_m2m_yaml(self) -> str:
        lines = [
            "RTK_EVALUATION_DRY_RUN:",
            f"  evaluation_id: {self.evaluation_id}",
            f"  decision: {self.decision.value}",
            f"  command_digest: {self.command_digest}",
            f"  raw_output_digest: {self.raw_output_digest}",
            f"  candidate_output_digest: {self.candidate_output_digest}",
            f"  raw_ref_digest: {self.raw_ref_digest}",
            f"  telemetry_event_id: {self.telemetry_event_id}",
            "  metrics:",
            f"    input_bytes: {self.input_bytes}",
            f"    candidate_bytes: {self.candidate_bytes}",
            f"    bytes_saved: {self.bytes_saved}",
            f"    tokens_saved: {self.tokens_saved}",
            f"    savings_ratio: {self.savings_ratio:.4f}",
            "  invariants:",
            f"    dry_run_only: {self.dry_run_only}",
            f"    rtk_invoked: {self.rtk_invoked}",
            f"    command_executed: {self.command_executed}",
            f"    compression_performed: {self.compression_performed}",
            f"    raw_content_persisted: {self.raw_content_persisted}",
            f"    runtime_reindex_allowed: {self.runtime_reindex_allowed}",
            f"  rejection_reasons: {self.rejection_reasons}",
        ]
        return "\n".join(lines)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _decision_to_mapping(decision: RedDogComputeDecision | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(decision, RedDogComputeDecision):
        return decision.to_dict()
    return dict(decision)


def _routing_value(decision: Mapping[str, Any]) -> str:
    routing = decision.get("routing")
    if isinstance(routing, Routing):
        return routing.value
    return str(routing or "")


def _command_digest(decision: Mapping[str, Any], command: str) -> str:
    value = str(decision.get("command_digest") or "")
    return value or _sha256(command)


def _event_for(
    *,
    raw_output: str,
    candidate_output: str,
    bypass_decision: str | None,
    ctx_holo_present: bool,
    index_gap_detected: bool,
) -> TokenCompressionEvent:
    output_bytes = len(candidate_output.encode("utf-8"))
    if bypass_decision:
        output_bytes = len(raw_output.encode("utf-8"))
    return build_token_compression_event(
        source_layer=SourceLayer.RTK_EVALUATION,
        operation=Operation.EVALUATE,
        content_type=ContentType.TOOL_OUTPUT,
        input_bytes=len(raw_output.encode("utf-8")),
        output_bytes=output_bytes,
        bypass_decision=bypass_decision,
        raw_ref_present=True,
        ctx_holo_present=ctx_holo_present,
        index_gap_detected=index_gap_detected,
    )


def evaluate_rtk_candidate_dry_run(
    *,
    command: str,
    raw_output: str,
    candidate_output: str,
    raw_ref: str,
    compute_decision: RedDogComputeDecision | Mapping[str, Any],
    bypass_classifier: BypassClassifier | None = None,
    record_telemetry: bool = True,
) -> RtkEvaluationDryRunResult:
    """Evaluate a caller-supplied RTK candidate without invoking RTK."""

    decision = _decision_to_mapping(compute_decision)
    classifier = bypass_classifier or get_bypass_classifier()
    reasons: list[str] = []
    bypass_class: str | None = None

    if _routing_value(decision) != Routing.ALLOW_EVALUATION_DRY_RUN.value:
        reasons.append(RtkDryRunRejection.COMPUTE_DECISION_NOT_ALLOW_EVALUATION.value)
    if decision.get("runtime_reindex_allowed") is True:
        reasons.append(RtkDryRunRejection.RUNTIME_REINDEX_FORBIDDEN.value)
    if not raw_ref:
        reasons.append(RtkDryRunRejection.RAW_REF_REQUIRED.value)
    if not candidate_output:
        reasons.append(RtkDryRunRejection.CANDIDATE_OUTPUT_REQUIRED.value)

    raw_bypass = classifier.classify(command=command, output=raw_output)
    if raw_bypass.bypassed:
        bypass_class = raw_bypass.classification.value
        reasons.append(RtkDryRunRejection.RAW_OUTPUT_REQUIRES_BYPASS.value)

    if candidate_output:
        candidate_bypass = classifier.classify(command=command, output=candidate_output)
        if candidate_bypass.bypassed:
            bypass_class = bypass_class or candidate_bypass.classification.value
            reasons.append(RtkDryRunRejection.CANDIDATE_OUTPUT_REQUIRES_BYPASS.value)

    input_bytes = len(raw_output.encode("utf-8"))
    candidate_bytes = len(candidate_output.encode("utf-8"))
    bytes_saved = input_bytes - candidate_bytes

    event = _event_for(
        raw_output=raw_output,
        candidate_output=candidate_output,
        bypass_decision=bypass_class,
        ctx_holo_present=bool(decision.get("ctx_holo_present")),
        index_gap_detected=bool(decision.get("index_gap_detected")),
    )
    if not bypass_class and bytes_saved <= 0:
        reasons.append(RtkDryRunRejection.NO_POSITIVE_SAVINGS.value)

    if record_telemetry:
        get_telemetry_store().record(event)

    accepted = not reasons
    if not accepted:
        bytes_saved = max(0, bytes_saved) if not bypass_class else 0
    savings_ratio = (bytes_saved / input_bytes) if input_bytes > 0 else 0.0
    evaluation_seed = {
        "command_digest": _command_digest(decision, command),
        "raw_output_digest": _sha256(raw_output),
        "candidate_output_digest": _sha256(candidate_output),
        "raw_ref_digest": _sha256(raw_ref),
        "reasons": reasons,
    }
    evaluation_id = hashlib.sha256(
        json.dumps(evaluation_seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:32]
    return RtkEvaluationDryRunResult(
        evaluation_id=evaluation_id,
        decision=RtkDryRunDecision.ACCEPT if accepted else RtkDryRunDecision.REJECT,
        command_digest=_command_digest(decision, command),
        raw_output_digest=_sha256(raw_output),
        candidate_output_digest=_sha256(candidate_output),
        raw_ref_digest=_sha256(raw_ref),
        telemetry_event_id=event.event_id,
        input_bytes=input_bytes,
        candidate_bytes=candidate_bytes,
        bytes_saved=bytes_saved,
        tokens_saved=max(0, event.tokens_saved) if accepted else 0,
        savings_ratio=savings_ratio,
        bypass_class=bypass_class,
        rejection_reasons=reasons,
    )


__all__ = [
    "RtkDryRunDecision",
    "RtkDryRunRejection",
    "RtkEvaluationDryRunResult",
    "evaluate_rtk_candidate_dry_run",
]
