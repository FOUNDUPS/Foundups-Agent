# -*- coding: utf-8 -*-
"""Contained consumer dispatch for the frozen create_foundup scaffold request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .foundup_scaffold_adapter import (
    ScaffoldAdapter,
    ScaffoldAdapterResult,
    stable_reason_human,
)
from .foundup_scaffold_route_contract import (
    CreateScaffoldRequest,
    canonical_json_copy,
    validate_scaffold_plan,
)


_KNOWN_REJECTIONS = frozenset({
    "FAIL_ENVELOPE_NOT_GATE_PASSED",
    "FAIL_FOUNDUP_ID_EXISTS",
    "FAIL_REGISTRY_UNAVAILABLE",
    "FAIL_SCAFFOLD_PLAN_REJECTED",
    "FAIL_SCAFFOLD_PLAN_NOT_CANONICAL",
    "FAIL_SCAFFOLD_PLAN_INVALID",
    "FAIL_SCAFFOLD_PLAN_BOUNDARY",
    "FAIL_MISSING_SCAFFOLD_CONTRACT",
    "FAIL_SCAFFOLD_FOUNDUP_MISMATCH",
    "FAIL_GENESIS_LINEAGE_MISMATCH",
    "FAIL_SCAFFOLD_LINEAGE_MISMATCH",
    "FAIL_SCAFFOLD_ADAPTER_INTERNAL",
})


@dataclass(frozen=True)
class ScaffoldDispatchOutcome:
    """Stable dispatch projection consumed by the legacy consumer container."""

    dispatched: bool
    reason_code: str
    reason_human: str
    scaffold_result: Optional[Dict[str, Any]]
    checkpoint_state: str
    checkpoint_result: Optional[str] = None
    checkpoint_blocker: Optional[str] = None

    def __post_init__(self) -> None:
        if self.scaffold_result is not None:
            object.__setattr__(
                self,
                "scaffold_result",
                canonical_json_copy(self.scaffold_result),
            )


def _blocked(code: str, human: str) -> ScaffoldDispatchOutcome:
    return ScaffoldDispatchOutcome(
        dispatched=False,
        reason_code=code,
        reason_human=human,
        scaffold_result=None,
        checkpoint_state="BLOCKED",
        checkpoint_blocker=code,
    )


def _invalid_adapter_result() -> ScaffoldDispatchOutcome:
    return _blocked(
        "FAIL_SCAFFOLD_ADAPTER_RESULT",
        "scaffold adapter returned an invalid result",
    )


def _serialized_result_is_typed(result: Dict[str, Any]) -> bool:
    """Require scalar control fields before comparisons or set membership."""
    return (
        type(result.get("ok")) is bool
        and type(result.get("reason_code")) is str
        and type(result.get("reason_human")) is str
    )


def _consume_serialized_result(
    serialized: Dict[str, Any],
    request: CreateScaffoldRequest,
) -> ScaffoldDispatchOutcome:
    code = serialized["reason_code"]
    if serialized["ok"] is not True:
        if code not in _KNOWN_REJECTIONS:
            return _invalid_adapter_result()
        safe_result = ScaffoldAdapterResult(
            ok=False,
            reason_code=code,
            reason_human=stable_reason_human(code),
        ).to_dict()
        return ScaffoldDispatchOutcome(
            dispatched=False,
            reason_code=code,
            reason_human=stable_reason_human(code),
            scaffold_result=safe_result,
            checkpoint_state="BLOCKED",
            checkpoint_blocker=code,
        )
    if code != "OK_SCAFFOLD_PLAN":
        return _invalid_adapter_result()
    plan_validation = validate_scaffold_plan(serialized.get("plan"), request)
    if not plan_validation.ok:
        return _blocked(
            plan_validation.reason_code,
            stable_reason_human(plan_validation.reason_code),
        )
    safe_result = ScaffoldAdapterResult(
        ok=True,
        reason_code=code,
        reason_human=stable_reason_human(code),
        plan=plan_validation.plan,
    ).to_dict()
    return ScaffoldDispatchOutcome(
        dispatched=True,
        reason_code=code,
        reason_human=stable_reason_human(code),
        scaffold_result=safe_result,
        checkpoint_state="SIMULATED",
        checkpoint_result="create_foundup dry-run scaffold plan produced",
    )


def dispatch_create_scaffold(
    adapter: ScaffoldAdapter,
    request: CreateScaffoldRequest,
    *,
    dry_run: bool,
) -> ScaffoldDispatchOutcome:
    """Dispatch without mutable jobs and contain every malformed result."""
    if dry_run is not True:
        return _blocked(
            "BLOCKED_SCAFFOLD_CONSUMER_LIVE",
            "create_foundup scaffold consumer is dry-run only",
        )

    try:
        raw_result = adapter.plan(request)
    except Exception:
        return _blocked(
            "FAIL_SCAFFOLD_ADAPTER_EXCEPTION",
            "scaffold adapter failed closed",
        )
    if type(raw_result) is not ScaffoldAdapterResult:
        return _invalid_adapter_result()

    try:
        serialized = canonical_json_copy(raw_result.to_dict())
    except Exception:
        return _invalid_adapter_result()
    if not isinstance(serialized, dict) or not _serialized_result_is_typed(serialized):
        return _invalid_adapter_result()
    return _consume_serialized_result(serialized, request)
