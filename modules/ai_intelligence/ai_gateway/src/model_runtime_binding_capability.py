"""Closure-confined one-shot capabilities for verified runtime bindings."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .model_runtime_binding_verification_receipt import (
    ModelRuntimeBindingVerificationReceipt,
    canonical_digest,
    verification_receipt_digest,
)


class VerifiedRuntimeBindingCapability:
    """Opaque handle recognized only by the verifier instance that issued it."""

    __slots__ = ("__token",)

    def __init__(self, token: str) -> None:
        object.__setattr__(self, "_VerifiedRuntimeBindingCapability__token", token)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("verified_runtime_binding_capability_is_immutable")

    def __copy__(self) -> "VerifiedRuntimeBindingCapability":
        raise TypeError("verified_runtime_binding_capability_copy_forbidden")

    def __deepcopy__(self, _memo: dict[int, Any]) -> "VerifiedRuntimeBindingCapability":
        raise TypeError("verified_runtime_binding_capability_copy_forbidden")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("verified_runtime_binding_capability_pickle_forbidden")


@dataclass(frozen=True)
class _CapabilityAdmission:
    binding_digest: str
    selection_digest: str
    verification_digest: str
    receipt: ModelRuntimeBindingVerificationReceipt


def build_verified_runtime_binding_capability_api(
    verified_inputs: Callable[..., tuple[
        Mapping[str, Any],
        Mapping[str, Any],
        ModelRuntimeBindingVerificationReceipt,
    ]],
) -> tuple[Callable[..., tuple[Any, ...]], Callable[..., Any], Callable[[Any], None]]:
    """Bind one capability registry to one canonical evidence verifier."""

    lock = threading.Lock()
    admissions: dict[str, _CapabilityAdmission] = {}
    return (
        _issue_closure(verified_inputs, lock, admissions),
        _consume_closure(lock, admissions),
        _discard_closure(lock, admissions),
    )


def _issue_closure(verified_inputs: Any, lock: Any, admissions: Any) -> Any:
    def verify_and_issue(**inputs: Any) -> tuple[Any, ...]:
        binding, selection, receipt = verified_inputs(**inputs)
        token = secrets.token_urlsafe(32)
        admission = _CapabilityAdmission(
            canonical_digest(binding),
            canonical_digest(selection),
            verification_receipt_digest(receipt),
            receipt,
        )
        with lock:
            admissions[token] = admission
        capability = VerifiedRuntimeBindingCapability(token)
        return binding, selection, receipt, capability

    return verify_and_issue


def _consume_closure(lock: Any, admissions: Any) -> Any:
    def consume(
        capability: Any,
        *,
        binding: Mapping[str, Any],
        selection: Mapping[str, Any],
        receipt: ModelRuntimeBindingVerificationReceipt,
    ) -> ModelRuntimeBindingVerificationReceipt | None:
        if type(capability) is not VerifiedRuntimeBindingCapability:
            return None
        token = object.__getattribute__(
            capability, "_VerifiedRuntimeBindingCapability__token"
        )
        with lock:
            admission = admissions.pop(token, None)
        if admission is None:
            return None
        actual = (
            canonical_digest(binding),
            canonical_digest(selection),
            verification_receipt_digest(receipt),
        )
        expected = (
            admission.binding_digest,
            admission.selection_digest,
            admission.verification_digest,
        )
        return admission.receipt if actual == expected else None

    return consume


def _discard_closure(lock: Any, admissions: Any) -> Any:
    def discard(capability: Any) -> None:
        if type(capability) is not VerifiedRuntimeBindingCapability:
            return
        token = object.__getattribute__(
            capability, "_VerifiedRuntimeBindingCapability__token"
        )
        with lock:
            admissions.pop(token, None)

    return discard


__all__ = [
    "VerifiedRuntimeBindingCapability",
    "build_verified_runtime_binding_capability_api",
]
