"""Shared bounded telemetry contract for HoloIndex owner acquisition."""

from __future__ import annotations


OWNER_ACQUISITION_CYCLE_COUNT = 32


def owner_acquisition_cycle_valid(value: object) -> bool:
    """Admit one bounded cycle; booleans are not integer telemetry."""

    return type(value) is int and 0 <= value < OWNER_ACQUISITION_CYCLE_COUNT


__all__ = ["OWNER_ACQUISITION_CYCLE_COUNT", "owner_acquisition_cycle_valid"]
