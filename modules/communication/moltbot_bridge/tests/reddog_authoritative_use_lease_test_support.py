"""Explicit non-production authority-lease test double."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator, Mapping
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    GovernedValveUseTimeResolution,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    GovernedExecutionValveEnvironment,
)


class StubAuthoritativeUseLease:
    def __init__(
        self,
        consumer: Callable[[], bool],
        *,
        expires_at_epoch: int,
        trusted_now_epoch: Callable[[], int],
    ) -> None:
        self._consumer = consumer
        self.expires_at_epoch = expires_at_epoch
        self._trusted_now_epoch = trusted_now_epoch
        self._used = False

    def consume(self) -> bool:
        if self._used:
            return False
        self._used = True
        return (
            self._trusted_now_epoch() < self.expires_at_epoch
            and self._consumer() is True
        )


def allow_stub_authoritative_use_lease(monkeypatch: Any, *modules: Any) -> None:
    for module in modules:
        monkeypatch.setattr(
            module,
            "is_authoritative_use_lease",
            lambda value, **_expected: isinstance(value, StubAuthoritativeUseLease),
        )
        monkeypatch.setattr(
            module,
            "consume_authoritative_use_lease",
            lambda value, **_expected: value.consume() is True,
        )


class _StaticUseTimeResolver:
    def __init__(self, resolution: GovernedValveUseTimeResolution) -> None:
        self._resolution = resolution

    def resolve(self, **_: object) -> GovernedValveUseTimeResolution:
        return self._resolution


@contextmanager
def inject_stub_governed_valve_use_time_authority(
    environment: Mapping[str, Any], expected_bindings: Mapping[str, Any]
) -> Iterator[None]:
    """Admit one test-only lease after canonical environment validation."""

    governed = GovernedExecutionValveEnvironment.from_mapping(environment)
    resolver = _StaticUseTimeResolver(
        GovernedValveUseTimeResolution(
            environment=governed,
            expected_bindings=expected_bindings,
            permission_ttl_seconds=300,
            permission_expires_at="2099-01-01T00:00:00+00:00",
            rejection_reasons=(),
            signed_authority_reverified=True,
            authoritative_use_lease=StubAuthoritativeUseLease(
                lambda: True,
                expires_at_epoch=4_000_000_000,
                trusted_now_epoch=lambda: 1_000,
            ),
        )
    )
    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_resident_queue_serial_loop_bootstrap."
        "GovernedValveUseTimeAuthorityResolver",
        return_value=resolver,
    ), patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_worktree_admission_capability.is_authoritative_use_lease",
        return_value=True,
    ), patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_worktree_admission_capability.consume_authoritative_use_lease",
        side_effect=lambda value, **_expected: value.consume(),
    ):
        yield


__all__ = [
    "StubAuthoritativeUseLease",
    "allow_stub_authoritative_use_lease",
    "inject_stub_governed_valve_use_time_authority",
]
