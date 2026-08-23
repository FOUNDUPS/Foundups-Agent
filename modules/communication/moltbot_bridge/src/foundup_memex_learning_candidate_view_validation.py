"""Bounded plain-data checks for FoundUp Memex learning view sources."""

from __future__ import annotations

import math
from typing import Any


MAX_NESTED_ITEMS = 4096
MAX_NESTED_DEPTH = 16
MAX_NESTED_NODES = 65_536
MAX_NESTED_STRING_CHARS = 1_048_576


def view_is_plain_data(view: Any) -> bool:
    """Reject callback-bearing view containers before traversal or hashing."""

    try:
        budget = [MAX_NESTED_NODES]
        return all(
            _plain_value(value, 0, budget)
            for value in (
                view.identity, view.current_state, view.source_receipts,
                view.roadmap_state, view.verified_outcomes,
                view.learning_candidates, view.roadmap_signals,
                view.assembly_receipt, view.invariants,
            )
        )
    except Exception:
        return False


def _plain_mapping(value: dict[Any, Any], depth: int, budget: list[int]) -> bool:
    return (
        len(value) <= MAX_NESTED_ITEMS
        and all(type(key) is str for key in value)
        and all(_plain_value(item, depth + 1, budget) for item in value.values())
    )


def _plain_value(value: Any, depth: int, budget: list[int]) -> bool:
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_NESTED_DEPTH:
        return False
    if value is None or type(value) in (bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is str:
        return len(value) <= MAX_NESTED_STRING_CHARS
    if type(value) in (list, tuple):
        return len(value) <= MAX_NESTED_ITEMS and all(
            _plain_value(item, depth + 1, budget) for item in value
        )
    if type(value) is dict:
        return _plain_mapping(value, depth, budget)
    return False


__all__ = ["view_is_plain_data"]
