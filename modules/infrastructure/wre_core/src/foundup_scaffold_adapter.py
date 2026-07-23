# -*- coding: utf-8 -*-
"""Dry-run-only consumer adapter for the distinct ``create_foundup`` route.

The adapter invokes the existing scaffold planner and verifies its lineage and
no-side-effect claims before returning a plan. It does not import or invoke the
generic Hermes job executor, a writer, FAM, or a worktree API.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


@dataclass(frozen=True)
class ScaffoldAdapterResult:
    """Fail-closed result returned to the FoundUpJob consumer."""

    ok: bool
    reason_code: str
    reason_human: str
    plan: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the adapter result for ConsumerResult evidence."""
        return {
            "ok": self.ok,
            "reason_code": self.reason_code,
            "reason_human": self.reason_human,
            "plan": self.plan,
        }


class ScaffoldAdapter(Protocol):
    """Injected adapter boundary used by ``FoundUpJobConsumer``."""

    def plan(self, job: Any) -> ScaffoldAdapterResult:
        """Produce or reject a dry-run scaffold plan."""


def digest_scaffold_contract(contract: Dict[str, Any]) -> str:
    """Return the planner-compatible canonical scaffold-contract digest."""
    raw = json.dumps(contract, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class CreateFoundUpDryRunScaffoldAdapter:
    """Default adapter backed by ``plan_create_foundup_dry_run``."""

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self._registry_path = registry_path

    @staticmethod
    def _reject(code: str, reason: str) -> ScaffoldAdapterResult:
        return ScaffoldAdapterResult(
            ok=False,
            reason_code=code,
            reason_human=reason,
        )

    def plan(self, job: Any) -> ScaffoldAdapterResult:
        """Run the existing planner and verify dry-run lineage fail closed."""
        try:
            from modules.foundups.agent.src.create_foundup_dryrun import (
                plan_create_foundup_dry_run,
            )

            if getattr(job, "requested_action", None) != "create_foundup":
                return self._reject(
                    "FAIL_WRONG_SCAFFOLD_ACTION",
                    "scaffold adapter accepts create_foundup only",
                )

            payload = getattr(job, "payload", None)
            genesis_envelope = (
                payload.get("genesis_envelope")
                if isinstance(payload, dict)
                else None
            )
            if not isinstance(genesis_envelope, dict):
                return self._reject(
                    "FAIL_MISSING_GENESIS_ENVELOPE",
                    "payload.genesis_envelope is required",
                )

            planner_result = plan_create_foundup_dry_run(
                genesis_envelope,
                actor_id=str(getattr(job, "tenant_id", "") or "0102"),
                registry_path=self._registry_path,
            )
            if not planner_result.ok:
                return self._reject(
                    planner_result.rejection_code or "FAIL_SCAFFOLD_PLAN_REJECTED",
                    planner_result.rejection_reason or "scaffold planner rejected job",
                )

            if (
                planner_result.dry_run is not True
                or planner_result.files_written
                or planner_result.fam_called
                or planner_result.hermes_called
                or planner_result.registry_mutated
                or planner_result.worktree_created
            ):
                return self._reject(
                    "FAIL_SCAFFOLD_PLAN_SIDE_EFFECT",
                    "scaffold planner result violated the dry-run-only boundary",
                )

            contract = planner_result.scaffold_contract
            if not isinstance(contract, dict):
                return self._reject(
                    "FAIL_MISSING_SCAFFOLD_CONTRACT",
                    "scaffold planner returned no contract",
                )
            if contract.get("foundup_id") != getattr(job, "foundup_id", None):
                return self._reject(
                    "FAIL_SCAFFOLD_FOUNDUP_MISMATCH",
                    "scaffold contract foundup_id does not match job",
                )
            if contract.get("genesis_envelope_digest") != getattr(
                job, "genesis_envelope_digest", None
            ):
                return self._reject(
                    "FAIL_GENESIS_LINEAGE_MISMATCH",
                    "scaffold contract genesis digest does not match job binding",
                )
            if digest_scaffold_contract(contract) != getattr(
                job, "scaffold_contract_digest", None
            ):
                return self._reject(
                    "FAIL_SCAFFOLD_LINEAGE_MISMATCH",
                    "scaffold contract digest does not match job binding",
                )

            return ScaffoldAdapterResult(
                ok=True,
                reason_code="OK_SCAFFOLD_PLAN",
                reason_human="create_foundup dry-run scaffold plan verified",
                plan=planner_result.to_dict(),
            )
        except Exception as exc:
            return self._reject(
                "FAIL_SCAFFOLD_ADAPTER_INTERNAL",
                f"scaffold adapter failed closed: {exc}",
            )
