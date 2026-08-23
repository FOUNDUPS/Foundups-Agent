"""Bounded plain-data checks for FoundUp Memex learning view sources."""

from __future__ import annotations

import math
from typing import Any


MAX_NESTED_ITEMS = 4096
MAX_NESTED_DEPTH = 16
MAX_NESTED_STRING_CHARS = 1_048_576


def view_sources_are_plain_data(view: Any) -> bool:
    """Reject callback-bearing receipt/outcome containers before traversal."""

    try:
        receipts = view.source_receipts
        outcomes = view.verified_outcomes
        return (
            type(receipts) is dict
            and _plain_mapping(receipts, 0)
            and type(outcomes) is tuple
            and len(outcomes) <= MAX_NESTED_ITEMS
            and all(type(item) is dict and _plain_mapping(item, 0) for item in outcomes)
        )
    except Exception:
        return False


def _plain_mapping(value: dict[Any, Any], depth: int) -> bool:
    return (
        len(value) <= MAX_NESTED_ITEMS
        and all(type(key) is str for key in value)
        and all(_plain_value(item, depth + 1) for item in value.values())
    )


def _plain_value(value: Any, depth: int) -> bool:
    if depth > MAX_NESTED_DEPTH:
        return False
    if value is None or type(value) in (bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is str:
        return len(value) <= MAX_NESTED_STRING_CHARS
    if type(value) in (list, tuple):
        return len(value) <= MAX_NESTED_ITEMS and all(
            _plain_value(item, depth + 1) for item in value
        )
    if type(value) is dict:
        return _plain_mapping(value, depth)
    return False


__all__ = ["view_sources_are_plain_data"]
