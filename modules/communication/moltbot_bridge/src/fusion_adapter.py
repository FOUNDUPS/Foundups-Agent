#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FusionAdapter Contract -- Hermes Advisory Worker-Panel (CONTRACT-ONLY, mock/dry-run).

Typed contract recommended by
docs/audits/architecture/OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1.md (Section 7,
"first implementation surface"). Slice: HERMES_FUSION_ADAPTER_CONTRACT_PHASE1.

WSP 97 TRUTH BOUNDARIES:
  DOES:
    - Define typed FusionRequest / FusionAnalysis / ModelContributionReceipt dataclasses.
    - Provide a deterministic MOCK / dry-run adapter (no network, no key, no OpenRouter).
    - Force advisory_not_canonical=True and redaction_status=BLOCKED_PENDING_REDACTION_GATE.
  DOES NOT:
    - Make any live OpenRouter or network call (no requests/httpx/aiohttp/openai/openrouter import).
    - Read any OPENROUTER_* or API key (this module never imports os; it cannot getenv).
    - Wire into Hermes / OpenClaw / HoloIndex runtime execution (no registration).
    - Grant any gate / merge / CABR / payout / source-authority.

PLACEMENT: this contract is a Hermes worker-panel adapter and lives in moltbot_bridge, NOT in
modules/infrastructure/openrouter_client (that module is dormant / contract-pending; see its README).

LIVE MODES (alias, server_tool, local_fallback) are DECLARED but UNREACHABLE in this slice: invoking
any of them raises RedactionGateBlocked. Only FusionMode.MOCK / FusionMode.DRY_RUN execute. Privacy
stays BLOCKED_PENDING_REDACTION_GATE until a separate redaction-gate slice lands.

WSP: WSP 11 (typed interface), WSP 50 (pre-action), WSP 97 (truth boundary).

NAVIGATION:
  -> Spec: docs/audits/architecture/OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1.md
  -> Receipt sibling: modules/communication/moltbot_bridge/src/proof_of_compute_receipt.py
  -> Future live client (dormant): modules/infrastructure/openrouter_client/
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Constants / truth-boundary sentinels
# ---------------------------------------------------------------------------

REDACTION_BLOCKED = "BLOCKED_PENDING_REDACTION_GATE"
NOT_EVALUATED = "NOT_EVALUATED"
MIN_PANEL_MODELS = 1
MAX_PANEL_MODELS = 8


class FusionMode(str, Enum):
    """Execution modes. Only MOCK / DRY_RUN run in this slice."""

    MOCK = "mock"
    DRY_RUN = "dry_run"
    ALIAS = "alias"                    # future live mode -- BLOCKED
    SERVER_TOOL = "server_tool"        # future live mode -- BLOCKED
    LOCAL_FALLBACK = "local_fallback"  # future local panel -- BLOCKED until built


EXECUTABLE_MODES = frozenset({FusionMode.MOCK, FusionMode.DRY_RUN})
FUTURE_BLOCKED_MODES = frozenset(
    {FusionMode.ALIAS, FusionMode.SERVER_TOOL, FusionMode.LOCAL_FALLBACK}
)


class FusionProvider(str, Enum):
    """Provider that produced a contribution. Only MOCK is reachable in this slice."""

    OPENROUTER = "openrouter"
    LOCAL = "local"
    MOCK = "mock"


class RedactionGateBlocked(RuntimeError):
    """Raised when a non-mock/dry-run Fusion mode is invoked before the redaction gate exists."""


def digest(text: str) -> str:
    """Return a short, stable, non-reversible digest. Never store raw prompt/context bodies."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Request (digests / refs only -- never raw prompt or raw context bodies)
# ---------------------------------------------------------------------------


@dataclass
class FusionRequest:
    """Advisory panel request. Carries DIGESTS and REFS only.

    There is intentionally NO context_text / raw_prompt field: raw bodies cannot enter the
    contract. Use FusionRequest.for_mock(...) to digest inputs safely.
    """

    task_id: str
    prompt_digest: str
    panel_models: List[str]
    outer_model: str = "mock-foreman"
    judge_model: str = "mock-judge"
    slice_id: Optional[str] = None
    context_refs: List[str] = field(default_factory=list)
    context_digest: Optional[str] = None
    mode: FusionMode = FusionMode.MOCK

    def __post_init__(self) -> None:
        count = len(self.panel_models)
        if count < MIN_PANEL_MODELS or count > MAX_PANEL_MODELS:
            raise ValueError(
                "panel_models must be "
                f"{MIN_PANEL_MODELS}-{MAX_PANEL_MODELS}, got {count}"
            )
        if not isinstance(self.mode, FusionMode):
            raise TypeError("mode must be a FusionMode")

    @classmethod
    def for_mock(
        cls,
        task_id: str,
        prompt: str,
        panel_models: List[str],
        *,
        raw_context: Optional[str] = None,
        context_refs: Optional[List[str]] = None,
        slice_id: Optional[str] = None,
        outer_model: str = "mock-foreman",
        judge_model: str = "mock-judge",
    ) -> "FusionRequest":
        """Build a MOCK request, digesting prompt/context so no raw body is ever stored."""
        return cls(
            task_id=task_id,
            prompt_digest=digest(prompt),
            panel_models=list(panel_models),
            outer_model=outer_model,
            judge_model=judge_model,
            slice_id=slice_id,
            context_refs=list(context_refs or []),
            context_digest=digest(raw_context) if raw_context is not None else None,
            mode=FusionMode.MOCK,
        )


# ---------------------------------------------------------------------------
# Judge analysis (the structured Fusion output shape)
# ---------------------------------------------------------------------------


@dataclass
class FusionAnalysis:
    consensus: str
    contradictions: List[str] = field(default_factory=list)
    partial_coverage: List[str] = field(default_factory=list)
    unique_insights: List[str] = field(default_factory=list)
    blind_spots: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Model Contribution Receipt (the #829 bridge object; advisory, never canonical)
# ---------------------------------------------------------------------------


@dataclass
class ModelContributionReceipt:
    receipt_id: str
    task_id: str
    provider: str
    mode: str
    outer_model: str
    panel_models: List[str]
    judge_model: str
    prompt_digest: str
    response_digest: str
    consensus: str
    slice_id: Optional[str] = None
    context_refs: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    unique_insights: List[str] = field(default_factory=list)
    blind_spots: List[str] = field(default_factory=list)
    failed_models: List[str] = field(default_factory=list)
    token_usage: Optional[Dict[str, int]] = None
    estimated_cost: Optional[float] = None
    latency_ms: Optional[float] = None
    accepted_by_judge: bool = False
    later_verified_outcome: str = NOT_EVALUATED
    wsp97_status: str = NOT_EVALUATED
    redaction_status: str = REDACTION_BLOCKED
    advisory_not_canonical: bool = True

    def __post_init__(self) -> None:
        # Hard truth boundary: a Fusion receipt is advisory-only and can never be canonical.
        if self.advisory_not_canonical is not True:
            raise ValueError(
                "ModelContributionReceipt is advisory-only; advisory_not_canonical must be True"
            )

    def to_dict(self) -> Dict[str, Any]:
        # Re-assert the truth boundary at serialization time: dataclass fields are mutable, so a
        # post-construction flip must not be able to emit a canonical-looking receipt.
        if self.advisory_not_canonical is not True:
            raise ValueError(
                "ModelContributionReceipt cannot be serialized as canonical "
                "(advisory_not_canonical must stay True)"
            )
        return {
            "receipt_id": self.receipt_id,
            "task_id": self.task_id,
            "slice_id": self.slice_id,
            "provider": self.provider,
            "mode": self.mode,
            "outer_model": self.outer_model,
            "panel_models": list(self.panel_models),
            "judge_model": self.judge_model,
            "prompt_digest": self.prompt_digest,
            "context_refs": list(self.context_refs),
            "response_digest": self.response_digest,
            "consensus": self.consensus,
            "contradictions": list(self.contradictions),
            "unique_insights": list(self.unique_insights),
            "blind_spots": list(self.blind_spots),
            "failed_models": list(self.failed_models),
            "token_usage": self.token_usage,
            "estimated_cost": self.estimated_cost,
            "latency_ms": self.latency_ms,
            "accepted_by_judge": self.accepted_by_judge,
            "later_verified_outcome": self.later_verified_outcome,
            "wsp97_status": self.wsp97_status,
            "redaction_status": self.redaction_status,
            "advisory_not_canonical": self.advisory_not_canonical,
        }


# ---------------------------------------------------------------------------
# Adapter contract (Protocol) + mock/dry-run implementation
# ---------------------------------------------------------------------------


@runtime_checkable
class FusionAdapter(Protocol):
    """Typed contract for an advisory Fusion worker-panel adapter."""

    provider: FusionProvider

    def run(self, request: FusionRequest) -> ModelContributionReceipt:
        ...


def _receipt_id(task_id: str, mode: str) -> str:
    """Deterministic receipt id (stable for the same task+mode; no time/random for test stability)."""
    suffix = hashlib.sha256(f"{task_id}:{mode}".encode("utf-8")).hexdigest()[:12]
    return f"rcpt_fusion_{suffix}"


class MockFusionAdapter:
    """Deterministic mock/dry-run FusionAdapter. No network, no key read, no OpenRouter client.

    Live modes are unreachable: ALIAS / SERVER_TOOL / LOCAL_FALLBACK raise RedactionGateBlocked.
    """

    provider = FusionProvider.MOCK

    def run(self, request: FusionRequest) -> ModelContributionReceipt:
        if request.mode in FUTURE_BLOCKED_MODES:
            raise RedactionGateBlocked(
                f"Fusion mode '{request.mode.value}' is declared but UNREACHABLE in "
                "HERMES_FUSION_ADAPTER_CONTRACT_PHASE1. Live OpenRouter / local panel stays "
                f"{REDACTION_BLOCKED}. Only mock/dry_run execute in this slice."
            )
        if request.mode not in EXECUTABLE_MODES:
            raise RedactionGateBlocked(f"Unsupported Fusion mode '{request.mode!r}'.")

        analysis = self._mock_analysis(request)
        response_digest = digest("|".join(request.panel_models) + "::" + analysis.consensus)
        return ModelContributionReceipt(
            receipt_id=_receipt_id(request.task_id, request.mode.value),
            task_id=request.task_id,
            slice_id=request.slice_id,
            provider=FusionProvider.MOCK.value,
            mode=request.mode.value,
            outer_model=request.outer_model,
            panel_models=list(request.panel_models),
            judge_model=request.judge_model,
            prompt_digest=request.prompt_digest,
            response_digest=response_digest,
            consensus=analysis.consensus,
            context_refs=list(request.context_refs),
            contradictions=list(analysis.contradictions),
            unique_insights=list(analysis.unique_insights),
            blind_spots=list(analysis.blind_spots),
            failed_models=[],
            accepted_by_judge=True,
            later_verified_outcome=NOT_EVALUATED,
            wsp97_status=NOT_EVALUATED,
            redaction_status=REDACTION_BLOCKED,
            advisory_not_canonical=True,
        )

    @staticmethod
    def _mock_analysis(request: FusionRequest) -> FusionAnalysis:
        names = ", ".join(request.panel_models)
        return FusionAnalysis(
            consensus=(
                "[MOCK advisory] synthetic consensus across "
                f"{len(request.panel_models)} panel model(s): {names}"
            ),
            contradictions=[],
            partial_coverage=[],
            unique_insights=["[MOCK] synthetic unique insight"],
            blind_spots=["[MOCK] synthetic blind spot"],
        )


__all__ = [
    "REDACTION_BLOCKED",
    "NOT_EVALUATED",
    "MIN_PANEL_MODELS",
    "MAX_PANEL_MODELS",
    "FusionMode",
    "EXECUTABLE_MODES",
    "FUTURE_BLOCKED_MODES",
    "FusionProvider",
    "RedactionGateBlocked",
    "digest",
    "FusionRequest",
    "FusionAnalysis",
    "ModelContributionReceipt",
    "FusionAdapter",
    "MockFusionAdapter",
]
