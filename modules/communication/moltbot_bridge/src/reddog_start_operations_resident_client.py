"""Use-time Skillz gate for the canonical resident RedDog client."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_operations_skill import (
    operations_skill_receipt_matches,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
    RedDogResidentArchitectClient,
)


OPERATIONS_SKILL_RUNTIME_KEY = "operations_skill_receipt"
OPERATIONS_SKILL_MISMATCH = "REJECT_REDDOG_OPERATIONS_SKILL_MISMATCH"


class StartOperationsResidentArchitectClient(RedDogResidentArchitectClient):
    """Reject submit/resume when sealed Skillz differ from persisted intent."""

    def __init__(
        self,
        *,
        runtime_defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        defaults = dict(runtime_defaults or {})
        receipt = defaults.pop(OPERATIONS_SKILL_RUNTIME_KEY, None)
        if receipt is not None and not isinstance(receipt, Mapping):
            raise ValueError(OPERATIONS_SKILL_MISMATCH)
        self._operations_skill_receipt = (
            dict(receipt) if isinstance(receipt, Mapping) else None
        )
        super().__init__(runtime_defaults=defaults, **kwargs)

    def _validate_submitted_intent(
        self,
        intent: Mapping[str, Any] | None,
    ) -> tuple[str, ...]:
        reasons = list(super()._validate_submitted_intent(intent))
        expected = self._operations_skill_receipt
        if expected is not None and (
            not isinstance(intent, Mapping)
            or not operations_skill_receipt_matches(intent, expected)
        ):
            reasons.append(OPERATIONS_SKILL_MISMATCH)
        return tuple(dict.fromkeys(reasons))


__all__ = [
    "OPERATIONS_SKILL_MISMATCH",
    "OPERATIONS_SKILL_RUNTIME_KEY",
    "StartOperationsResidentArchitectClient",
]
