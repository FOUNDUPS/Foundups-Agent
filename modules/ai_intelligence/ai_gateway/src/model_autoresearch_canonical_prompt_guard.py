"""Code-owned approval-only prompt guard for configured AutoResearch egress."""

from __future__ import annotations

import hashlib
from typing import Callable

from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    REDACTION_GATE_PASSED,
    evaluate_redaction_gate,
)

from .model_autoresearch_configured_gateway_evidence import (
    PromptGuardApprovalReceipt,
)


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST = _digest(
    "canonical-autoresearch-prompt-guard-contract-v1"
)
CANONICAL_PROMPT_GUARD_PROFILE_DIGEST = _digest(
    "canonical-local-autoresearch-prompt-guard-profile-v1"
)
CANONICAL_PROMPT_GUARD_REPORT_DIGEST = _digest(
    "canonical-local-autoresearch-prompt-approved-v1"
)
CANONICAL_PROMPT_GUARD_PROFILE = "canonical_local_v1"


def build_canonical_local_autoresearch_prompt_guard(
    *,
    redaction_gate: Callable[..., object] = evaluate_redaction_gate,
):
    """Build the approval-only adapter over Fusion's audit-mode redaction gate."""

    def _guard(
        *,
        prompt: str,
        task_id: str,
        source_prompt_digest: str,
    ) -> PromptGuardApprovalReceipt:
        del task_id, source_prompt_digest
        if not isinstance(prompt, str):
            return _blocked_receipt()
        try:
            result = redaction_gate(prompt, audit_mode=True)
        except Exception:
            return _blocked_receipt()
        status = getattr(result, "status", None)
        redacted = getattr(result, "redacted_prompt", None)
        if (
            status != REDACTION_GATE_PASSED
            or not isinstance(redacted, str)
            or redacted.encode("utf-8") != prompt.encode("utf-8")
        ):
            return _blocked_receipt()
        return PromptGuardApprovalReceipt(
            passed=True,
            prompt=prompt,
            contract_digest=CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST,
            profile_digest=CANONICAL_PROMPT_GUARD_PROFILE_DIGEST,
            report_digest=CANONICAL_PROMPT_GUARD_REPORT_DIGEST,
        ).normalized()

    return _guard


def _blocked_receipt() -> PromptGuardApprovalReceipt:
    return PromptGuardApprovalReceipt(
        passed=False,
        prompt=None,
        contract_digest=CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST,
        profile_digest=CANONICAL_PROMPT_GUARD_PROFILE_DIGEST,
        report_digest=CANONICAL_PROMPT_GUARD_REPORT_DIGEST,
    ).normalized()


__all__ = [
    "CANONICAL_PROMPT_GUARD_CONTRACT_DIGEST",
    "CANONICAL_PROMPT_GUARD_PROFILE",
    "CANONICAL_PROMPT_GUARD_PROFILE_DIGEST",
    "CANONICAL_PROMPT_GUARD_REPORT_DIGEST",
    "build_canonical_local_autoresearch_prompt_guard",
]
