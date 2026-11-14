"""Immutable internal policy state for owner-controlled E0 capabilities."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping


def freeze_owner_e0_policy(policy: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(
        {
            key: tuple(value) if isinstance(value, list) else value
            for key, value in policy.items()
        }
    )


def thaw_owner_e0_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in policy.items()
    }


def owner_e0_capability_type(seal: object) -> type:
    class Capability:
        __slots__ = ("_seal", "__weakref__")

        def __init__(self) -> None:
            object.__setattr__(self, "_seal", seal)

        def __setattr__(self, _name: str, _value: Any) -> None:
            raise TypeError("signer_owner_e0_capability_immutable")

        def __copy__(self) -> object:
            raise TypeError("signer_owner_e0_capability_not_copyable")

        def __deepcopy__(self, _memo: Any) -> object:
            raise TypeError("signer_owner_e0_capability_not_copyable")

        def __reduce__(self) -> object:
            raise TypeError("signer_owner_e0_capability_not_serializable")

    return Capability


__all__ = [
    "freeze_owner_e0_policy",
    "owner_e0_capability_type",
    "thaw_owner_e0_policy",
]
