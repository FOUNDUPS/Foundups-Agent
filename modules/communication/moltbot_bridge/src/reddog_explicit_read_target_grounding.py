"""Ground an already-authorized explicit repository target set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
    TransportGroundingResult,
    ground_transport_work_focus,
)


@dataclass(frozen=True)
class ExplicitReadTargetGrounding:
    """Exact-HEAD grounding result plus the canonical generated work focus."""

    work_focus: str
    result: TransportGroundingResult

    @property
    def accepted(self) -> bool:
        return self.result.accepted

    @property
    def receipt(self) -> Mapping[str, Any]:
        return self.result.grounding_receipt


def ground_explicit_read_targets(
    *,
    repo_root: Path | str,
    targets: Sequence[str],
    foundup_id: str,
    principal_id: str,
    source_surface: str,
    request_id: str,
    action: str = "Audit the authorized repository targets.",
) -> ExplicitReadTargetGrounding:
    """Use the canonical grounding service without semantic owner queries."""

    normalized = tuple(
        dict.fromkeys(str(target).replace("\\", "/").strip() for target in targets)
    )
    normalized = tuple(target for target in normalized if target)
    focus = str(action or "").strip() + "\nRead first:\n" + "\n".join(
        f"- {target}" for target in normalized
    )

    def reject_semantic_query(_query: str) -> Mapping[str, Any]:
        raise RuntimeError("explicit target grounding must not query HoloIndex")

    result = ground_transport_work_focus(
        repo_root=repo_root,
        work_focus=focus,
        foundup_id=foundup_id,
        authenticated_principal_id=principal_id,
        source_surface=source_surface,
        client_request_id=request_id,
        owner_query=reject_semantic_query,
    )
    return ExplicitReadTargetGrounding(work_focus=focus, result=result)


__all__ = ["ExplicitReadTargetGrounding", "ground_explicit_read_targets"]
