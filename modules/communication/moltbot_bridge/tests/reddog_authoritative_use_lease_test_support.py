"""Explicit non-production authority-lease test double."""

from __future__ import annotations

from typing import Any, Callable


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
            lambda value: isinstance(value, StubAuthoritativeUseLease),
        )
        monkeypatch.setattr(
            module,
            "consume_authoritative_use_lease",
            lambda value: value.consume() is True,
        )


__all__ = ["StubAuthoritativeUseLease", "allow_stub_authoritative_use_lease"]
