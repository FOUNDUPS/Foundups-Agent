# -*- coding: utf-8 -*-
"""OpenClaw/Hermes RTK seam dry-run planner.

Slice: RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1

This module models the command-output seam without wiring into OpenClaw,
Hermes, WRE, extension runtime, or an RTK binary. It evaluates whether a
caller-supplied candidate could be measured by the token-efficiency stack while
always preserving the original command output.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .compute_governor import RedDogComputeDecision, Routing, get_compute_governor
from .rtk_evaluation_dryrun import (
    RtkDryRunDecision,
    RtkEvaluationDryRunResult,
    evaluate_rtk_candidate_dry_run,
)


class RtkAdapterSurface(Enum):
    """Supported command-output seam sources."""

    OPENCLAW = "OPENCLAW"
    HERMES = "HERMES"


class RtkAdapterDryRunDecision(Enum):
    """Adapter dry-run decision."""

    ACCEPT = "RTK_ADAPTER_DRY_RUN_ACCEPT"
    REJECT = "RTK_ADAPTER_DRY_RUN_REJECT"


class RtkAdapterDryRunRejection(Enum):
    """Fail-closed adapter rejection reasons."""

    UNSUPPORTED_SURFACE = "UNSUPPORTED_SURFACE"
    COMMAND_REQUIRED = "COMMAND_REQUIRED"
    RAW_REF_REQUIRED = "RAW_REF_REQUIRED"
    CANDIDATE_OUTPUT_REQUIRED = "CANDIDATE_OUTPUT_REQUIRED"
    COMPUTE_DECISION_NOT_ALLOW_EVALUATION = "COMPUTE_DECISION_NOT_ALLOW_EVALUATION"
    RTK_EVALUATION_REJECTED = "RTK_EVALUATION_REJECTED"
    RUNTIME_REINDEX_FORBIDDEN = "RUNTIME_REINDEX_FORBIDDEN"


class RtkAdapterOutputMode(Enum):
    """Output handling mode for the dry-run seam."""

    RAW_OUTPUT_PRESERVED = "RAW_OUTPUT_PRESERVED"
    DRY_RUN_CANDIDATE_MEASURED_RAW_OUTPUT_PRESERVED = (
        "DRY_RUN_CANDIDATE_MEASURED_RAW_OUTPUT_PRESERVED"
    )


@dataclass(frozen=True)
class RtkOpenClawHermesAdapterDryRunResult:
    """Dry-run receipt for the OpenClaw/Hermes command-output seam."""

    adapter_receipt_id: str
    decision: RtkAdapterDryRunDecision
    surface: RtkAdapterSurface | None
    output_mode: RtkAdapterOutputMode
    command_digest: str
    raw_output_digest: str
    candidate_output_digest: str
    raw_ref_digest: str
    compute_decision_id: str | None
    compute_routing: str | None
    evaluation_id: str | None
    evaluation_decision: str | None
    telemetry_event_id: str | None
    bytes_saved: int
    tokens_saved: int
    savings_ratio: float
    rejection_reasons: list[str]
    dry_run_only: bool = True
    rtk_invoked: bool = False
    command_executed: bool = False
    compression_performed: bool = False
    output_rewritten: bool = False
    raw_output_preserved: bool = True
    openclaw_wired: bool = False
    hermes_wired: bool = False
    wre_wired: bool = False
    extension_wired: bool = False
    runtime_reindex_allowed: bool = False
    telemetry_in_memory_only: bool = True
    raw_content_persisted: bool = False

    @property
    def accepted(self) -> bool:
        return self.decision == RtkAdapterDryRunDecision.ACCEPT

    def to_dict(self) -> dict[str, Any]:
        """Serialize without raw command, output, candidate, or raw_ref content."""

        return {
            "adapter_receipt_id": self.adapter_receipt_id,
            "decision": self.decision.value,
            "surface": self.surface.value if self.surface else None,
            "output_mode": self.output_mode.value,
            "command_digest": self.command_digest,
            "raw_output_digest": self.raw_output_digest,
            "candidate_output_digest": self.candidate_output_digest,
            "raw_ref_digest": self.raw_ref_digest,
            "compute_decision_id": self.compute_decision_id,
            "compute_routing": self.compute_routing,
            "evaluation_id": self.evaluation_id,
            "evaluation_decision": self.evaluation_decision,
            "telemetry_event_id": self.telemetry_event_id,
            "bytes_saved": self.bytes_saved,
            "tokens_saved": self.tokens_saved,
            "savings_ratio": self.savings_ratio,
            "rejection_reasons": list(self.rejection_reasons),
            "dry_run_only": self.dry_run_only,
            "rtk_invoked": self.rtk_invoked,
            "command_executed": self.command_executed,
            "compression_performed": self.compression_performed,
            "output_rewritten": self.output_rewritten,
            "raw_output_preserved": self.raw_output_preserved,
            "openclaw_wired": self.openclaw_wired,
            "hermes_wired": self.hermes_wired,
            "wre_wired": self.wre_wired,
            "extension_wired": self.extension_wired,
            "runtime_reindex_allowed": self.runtime_reindex_allowed,
            "telemetry_in_memory_only": self.telemetry_in_memory_only,
            "raw_content_persisted": self.raw_content_persisted,
        }

    def to_m2m_compact(self) -> str:
        status = "ACCEPT" if self.accepted else "REJECT"
        surface = self.surface.value if self.surface else "unsupported"
        return (
            f"RTK_SEAM:{self.adapter_receipt_id[:8]} "
            f"SURFACE:{surface} "
            f"STATUS:{status} "
            f"MODE:{self.output_mode.value} "
            f"REWRITE:{str(self.output_rewritten).lower()}"
        )

    def to_m2m_yaml(self) -> str:
        surface = self.surface.value if self.surface else None
        return "\n".join(
            [
                "RTK_OPENCLAW_HERMES_ADAPTER_DRY_RUN:",
                f"  adapter_receipt_id: {self.adapter_receipt_id}",
                f"  decision: {self.decision.value}",
                f"  surface: {surface}",
                f"  output_mode: {self.output_mode.value}",
                f"  compute_decision_id: {self.compute_decision_id}",
                f"  compute_routing: {self.compute_routing}",
                f"  evaluation_id: {self.evaluation_id}",
                f"  evaluation_decision: {self.evaluation_decision}",
                f"  telemetry_event_id: {self.telemetry_event_id}",
                "  metrics:",
                f"    bytes_saved: {self.bytes_saved}",
                f"    tokens_saved: {self.tokens_saved}",
                f"    savings_ratio: {self.savings_ratio:.4f}",
                "  invariants:",
                f"    dry_run_only: {self.dry_run_only}",
                f"    rtk_invoked: {self.rtk_invoked}",
                f"    command_executed: {self.command_executed}",
                f"    compression_performed: {self.compression_performed}",
                f"    output_rewritten: {self.output_rewritten}",
                f"    raw_output_preserved: {self.raw_output_preserved}",
                f"    runtime_reindex_allowed: {self.runtime_reindex_allowed}",
                f"    raw_content_persisted: {self.raw_content_persisted}",
                f"  rejection_reasons: {self.rejection_reasons}",
            ]
        )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_surface(surface: RtkAdapterSurface | str) -> RtkAdapterSurface | None:
    if isinstance(surface, RtkAdapterSurface):
        return surface
    normalized = str(surface or "").strip().upper()
    for candidate in RtkAdapterSurface:
        if normalized == candidate.value:
            return candidate
    return None


def _routing_value(decision: RedDogComputeDecision | Mapping[str, Any]) -> str | None:
    routing = decision.routing if isinstance(decision, RedDogComputeDecision) else decision.get("routing")
    if isinstance(routing, Routing):
        return routing.value
    return str(routing) if routing is not None else None


def _decision_id(decision: RedDogComputeDecision | Mapping[str, Any]) -> str | None:
    if isinstance(decision, RedDogComputeDecision):
        return decision.decision_id
    value = decision.get("decision_id")
    return str(value) if value is not None else None


def _runtime_reindex_allowed(decision: RedDogComputeDecision | Mapping[str, Any]) -> bool:
    if isinstance(decision, RedDogComputeDecision):
        return decision.runtime_reindex_allowed
    return bool(decision.get("runtime_reindex_allowed"))


def _build_receipt_id(
    *,
    surface: RtkAdapterSurface | None,
    command_digest: str,
    raw_output_digest: str,
    candidate_output_digest: str,
    raw_ref_digest: str,
    compute_decision_id: str | None,
    evaluation_id: str | None,
    rejection_reasons: list[str],
) -> str:
    payload = {
        "candidate_output_digest": candidate_output_digest,
        "command_digest": command_digest,
        "compute_decision_id": compute_decision_id,
        "evaluation_id": evaluation_id,
        "raw_output_digest": raw_output_digest,
        "raw_ref_digest": raw_ref_digest,
        "rejection_reasons": rejection_reasons,
        "surface": surface.value if surface else None,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:32]


def plan_rtk_openclaw_hermes_adapter_dry_run(
    *,
    surface: RtkAdapterSurface | str,
    command: str,
    command_output: str,
    candidate_output: str,
    raw_ref: str,
    compute_decision: RedDogComputeDecision | Mapping[str, Any] | None = None,
    ctx_holo_present: bool = False,
    index_gap_detected: bool = False,
    record_telemetry: bool = True,
) -> RtkOpenClawHermesAdapterDryRunResult:
    """Plan a dry-run RTK seam result without rewriting command output."""

    normalized_surface = _normalize_surface(surface)
    command_digest = _sha256(command)
    raw_output_digest = _sha256(command_output)
    candidate_output_digest = _sha256(candidate_output)
    raw_ref_digest = _sha256(raw_ref)
    reasons: list[str] = []
    evaluation: RtkEvaluationDryRunResult | None = None

    if normalized_surface is None:
        reasons.append(RtkAdapterDryRunRejection.UNSUPPORTED_SURFACE.value)
    if not command:
        reasons.append(RtkAdapterDryRunRejection.COMMAND_REQUIRED.value)
    if not raw_ref:
        reasons.append(RtkAdapterDryRunRejection.RAW_REF_REQUIRED.value)
    if not candidate_output:
        reasons.append(RtkAdapterDryRunRejection.CANDIDATE_OUTPUT_REQUIRED.value)

    decision = compute_decision
    if decision is None and normalized_surface is not None and command:
        decision = get_compute_governor().get_routing_recommendation(
            command=command,
            output_preview=command_output,
            ctx_holo_present=ctx_holo_present,
            index_gap_detected=index_gap_detected,
        )

    compute_id = _decision_id(decision) if decision is not None else None
    compute_routing = _routing_value(decision) if decision is not None else None
    if decision is not None:
        if compute_routing != Routing.ALLOW_EVALUATION_DRY_RUN.value:
            reasons.append(
                RtkAdapterDryRunRejection.COMPUTE_DECISION_NOT_ALLOW_EVALUATION.value
            )
        if _runtime_reindex_allowed(decision):
            reasons.append(RtkAdapterDryRunRejection.RUNTIME_REINDEX_FORBIDDEN.value)

    if normalized_surface is not None and decision is not None:
        evaluation = evaluate_rtk_candidate_dry_run(
            command=command,
            raw_output=command_output,
            candidate_output=candidate_output,
            raw_ref=raw_ref,
            compute_decision=decision,
            record_telemetry=record_telemetry,
        )
        if evaluation.decision != RtkDryRunDecision.ACCEPT:
            reasons.append(RtkAdapterDryRunRejection.RTK_EVALUATION_REJECTED.value)
            reasons.extend(evaluation.rejection_reasons)

    # Preserve first-seen order while removing duplicate reasons.
    rejection_reasons = list(dict.fromkeys(reasons))
    accepted = not rejection_reasons
    output_mode = (
        RtkAdapterOutputMode.DRY_RUN_CANDIDATE_MEASURED_RAW_OUTPUT_PRESERVED
        if accepted
        else RtkAdapterOutputMode.RAW_OUTPUT_PRESERVED
    )
    adapter_receipt_id = _build_receipt_id(
        surface=normalized_surface,
        command_digest=command_digest,
        raw_output_digest=raw_output_digest,
        candidate_output_digest=candidate_output_digest,
        raw_ref_digest=raw_ref_digest,
        compute_decision_id=compute_id,
        evaluation_id=evaluation.evaluation_id if evaluation else None,
        rejection_reasons=rejection_reasons,
    )
    return RtkOpenClawHermesAdapterDryRunResult(
        adapter_receipt_id=adapter_receipt_id,
        decision=(
            RtkAdapterDryRunDecision.ACCEPT
            if accepted
            else RtkAdapterDryRunDecision.REJECT
        ),
        surface=normalized_surface,
        output_mode=output_mode,
        command_digest=command_digest,
        raw_output_digest=raw_output_digest,
        candidate_output_digest=candidate_output_digest,
        raw_ref_digest=raw_ref_digest,
        compute_decision_id=compute_id,
        compute_routing=compute_routing,
        evaluation_id=evaluation.evaluation_id if evaluation else None,
        evaluation_decision=evaluation.decision.value if evaluation else None,
        telemetry_event_id=evaluation.telemetry_event_id if evaluation else None,
        bytes_saved=evaluation.bytes_saved if evaluation and accepted else 0,
        tokens_saved=evaluation.tokens_saved if evaluation and accepted else 0,
        savings_ratio=evaluation.savings_ratio if evaluation and accepted else 0.0,
        rejection_reasons=rejection_reasons,
    )


__all__ = [
    "RtkAdapterDryRunDecision",
    "RtkAdapterDryRunRejection",
    "RtkAdapterOutputMode",
    "RtkAdapterSurface",
    "RtkOpenClawHermesAdapterDryRunResult",
    "plan_rtk_openclaw_hermes_adapter_dry_run",
]
