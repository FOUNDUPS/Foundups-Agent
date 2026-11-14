# -*- coding: utf-8 -*-
"""Dry-run-only adapter from a frozen create request to the existing planner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from .foundup_scaffold_route_contract import (
    CreateScaffoldRequest,
    canonical_json_copy,
    validate_scaffold_plan,
)


_REASON_HUMAN = {
    "OK_SCAFFOLD_PLAN": "create_foundup dry-run scaffold plan verified",
    "FAIL_ENVELOPE_NOT_GATE_PASSED": "genesis envelope validation failed",
    "FAIL_FOUNDUP_ID_EXISTS": "foundup_id already exists",
    "FAIL_REGISTRY_UNAVAILABLE": "FoundUp registry unavailable or invalid",
    "FAIL_SCAFFOLD_PLAN_REJECTED": "scaffold planner rejected request",
    "FAIL_SCAFFOLD_PLAN_NOT_CANONICAL": "scaffold plan is not canonical JSON",
    "FAIL_SCAFFOLD_PLAN_INVALID": "scaffold plan is invalid",
    "FAIL_SCAFFOLD_PLAN_BOUNDARY": "scaffold plan violated dry-run boundary",
    "FAIL_MISSING_SCAFFOLD_CONTRACT": "scaffold plan omitted its contract",
    "FAIL_SCAFFOLD_FOUNDUP_MISMATCH": "scaffold plan identity mismatch",
    "FAIL_GENESIS_LINEAGE_MISMATCH": "scaffold plan genesis lineage mismatch",
    "FAIL_SCAFFOLD_LINEAGE_MISMATCH": "scaffold plan digest mismatch",
    "FAIL_SCAFFOLD_ADAPTER_INTERNAL": "scaffold adapter failed closed",
}


def stable_reason_human(code: str) -> str:
    """Map internal result codes to stable redacted operator text."""
    return _REASON_HUMAN.get(code, "scaffold request rejected")


@dataclass(frozen=True)
class ScaffoldAdapterResult:
    """Detached fail-closed result returned to the scaffold dispatcher."""

    ok: bool
    reason_code: str
    reason_human: str
    plan: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.plan is not None:
            object.__setattr__(self, "plan", canonical_json_copy(self.plan))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize detached canonical evidence."""
        return canonical_json_copy({
            "ok": self.ok,
            "reason_code": self.reason_code,
            "reason_human": self.reason_human,
            "plan": self.plan,
        })


class ScaffoldAdapter(Protocol):
    """Injected adapter boundary used by ``FoundUpJobConsumer``."""

    def plan(self, request: CreateScaffoldRequest) -> ScaffoldAdapterResult:
        """Produce or reject a dry-run scaffold plan."""


class CreateFoundUpDryRunScaffoldAdapter:
    """Default adapter backed by ``plan_create_foundup_dry_run``."""

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self._registry_path = registry_path

    @staticmethod
    def _reject(code: str) -> ScaffoldAdapterResult:
        return ScaffoldAdapterResult(
            ok=False,
            reason_code=code,
            reason_human=stable_reason_human(code),
        )

    def plan(self, request: CreateScaffoldRequest) -> ScaffoldAdapterResult:
        """Plan from the frozen snapshot and verify returned lineage."""
        try:
            from modules.foundups.agent.src.create_foundup_dryrun import (
                plan_create_foundup_dry_run,
            )

            planner_result = plan_create_foundup_dry_run(
                request.genesis_envelope,
                actor_id=request.tenant_id,
                registry_path=self._registry_path,
            )
            if not planner_result.ok:
                code = (
                    planner_result.rejection_code
                    if planner_result.rejection_code in _REASON_HUMAN
                    else "FAIL_SCAFFOLD_PLAN_REJECTED"
                )
                return self._reject(code)

            plan_validation = validate_scaffold_plan(
                planner_result.to_dict(),
                request,
            )
            if not plan_validation.ok:
                return self._reject(plan_validation.reason_code)
            return ScaffoldAdapterResult(
                ok=True,
                reason_code="OK_SCAFFOLD_PLAN",
                reason_human=stable_reason_human("OK_SCAFFOLD_PLAN"),
                plan=plan_validation.plan,
            )
        except Exception:
            return self._reject("FAIL_SCAFFOLD_ADAPTER_INTERNAL")
