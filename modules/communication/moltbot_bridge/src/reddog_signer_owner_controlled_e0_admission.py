"""Opaque admission boundary for owner-controlled signer E0 composition."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Mapping
from weakref import WeakKeyDictionary

from .reddog_signer_owner_e0_capability_state import (
    owner_e0_capability_type,
)
from .reddog_signer_owner_e0_admission_contract import (
    ADMISSION_ACCEPT,
    ADMISSION_REJECT,
    FAIL_ADMISSION_INPUT,
    FAIL_ADMISSION_POLICY,
    IssuedAdmission,
    OwnerControlledE0AdmissionResult,
    OwnerControlledE0ConsumptionReceipt,
)
from .reddog_signer_owner_e0_current_selection import (
    validate_owner_e0_current_admission,
)


class OwnerControlledE0AdmissionBoundary:
    """Consume current-generation proof and issue one process-local capability."""

    def __init__(
        self,
        *,
        repo_root: Path | str,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._seal = object()
        self._capability_type = owner_e0_capability_type(self._seal)
        self._issued: WeakKeyDictionary[object, IssuedAdmission] = (
            WeakKeyDictionary()
        )
        self._lock = threading.Lock()

    def admit(
        self, owner_config_path: Path | str, policy: Mapping[str, Any]
    ) -> OwnerControlledE0AdmissionResult:
        """Revalidate the current signed generation and owner policy."""

        try:
            path = Path(owner_config_path).resolve()
            _receipt, checked = self._validate(path, policy)
        except Exception:
            return _reject(FAIL_ADMISSION_POLICY)
        capability = self._capability_type()
        with self._lock:
            self._issued[capability] = IssuedAdmission(path, checked)
        return OwnerControlledE0AdmissionResult(
            accepted=True,
            status=ADMISSION_ACCEPT,
            rejection_reasons=(),
            policy_id=str(checked["policy_id"]),
            capability=capability,
        )

    def consume(self, capability: object) -> OwnerControlledE0ConsumptionReceipt:
        if not isinstance(capability, self._capability_type):
            raise ValueError(FAIL_ADMISSION_INPUT)
        with self._lock:
            issued = self._issued.pop(capability, None)
        if (
            issued is None
            or object.__getattribute__(capability, "_seal") is not self._seal
        ):
            raise ValueError(FAIL_ADMISSION_INPUT)
        receipt, _checked = self._validate(
            issued.owner_config_path, issued.policy
        )
        return receipt

    def _validate(
        self,
        owner_config_path: Path,
        policy: Mapping[str, Any],
    ) -> tuple[OwnerControlledE0ConsumptionReceipt, Mapping[str, Any]]:
        return validate_owner_e0_current_admission(
            owner_config_path=owner_config_path,
            repo_root=self._repo_root,
            policy=policy,
        )


def _reject(reason: str) -> OwnerControlledE0AdmissionResult:
    return OwnerControlledE0AdmissionResult(False, ADMISSION_REJECT, (reason,))


__all__ = [
    "OwnerControlledE0AdmissionBoundary",
    "OwnerControlledE0AdmissionResult",
    "OwnerControlledE0ConsumptionReceipt",
]
