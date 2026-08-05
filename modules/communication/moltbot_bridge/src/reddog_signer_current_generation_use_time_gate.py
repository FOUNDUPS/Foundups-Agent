"""Audit-only use-time evidence for the current signer generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SignerCurrentGenerationRuntimeBinding,
    verify_signer_current_generation_runtime_binding,
)


@dataclass(frozen=True)
class SignerCurrentGenerationUseTimeEvidence:
    """Non-authoritative evidence collected inside the valve resolver."""

    binding: SignerCurrentGenerationRuntimeBinding | None

    @property
    def receipt_id(self) -> str | None:
        binding = self.binding
        if (
            type(binding) is not SignerCurrentGenerationRuntimeBinding
            or binding.accepted is not True
        ):
            return None
        return binding.receipt_id if is_sha256(binding.receipt_id) else None

    def remaining_reasons(
        self, all_reasons: Iterable[str], bound_reasons: Iterable[str]
    ) -> tuple[str, ...]:
        bound = frozenset(bound_reasons)
        return tuple(
            reason
            for reason in all_reasons
            if self.receipt_id is None or reason not in bound
        )


def collect_signer_current_generation_use_time_evidence(
    enabled: bool,
    repo_root: Path,
    runtime_root: Path,
    trusted_now_epoch: Callable[[], int],
) -> SignerCurrentGenerationUseTimeEvidence:
    """Collect current-generation evidence without minting a capability."""

    if enabled is not True:
        return SignerCurrentGenerationUseTimeEvidence(None)
    try:
        now_epoch = trusted_now_epoch()
        binding = verify_signer_current_generation_runtime_binding(
            repo_root=repo_root,
            runtime_root=runtime_root,
            now_epoch=now_epoch,
        )
    except Exception:
        return SignerCurrentGenerationUseTimeEvidence(None)
    return SignerCurrentGenerationUseTimeEvidence(binding)


__all__ = [
    "SignerCurrentGenerationUseTimeEvidence",
    "collect_signer_current_generation_use_time_evidence",
]
