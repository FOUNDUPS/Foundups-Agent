"""Exact parsing for private Holo owner four-field bindings."""

from __future__ import annotations


ExactBinding = tuple[str, str, str, str]


def parse_exact_binding(
    value: object, *, allow_empty_fields: bool = False,
) -> ExactBinding | None:
    """Return an exact safe binding without invoking duck-typed field methods."""

    if type(value) is not tuple or len(value) != 4:
        return None
    for item in value:
        if type(item) is not str:
            return None
        if not item:
            if allow_empty_fields:
                continue
            return None
        if item != item.strip() or not item.isprintable():
            return None
    return value


__all__ = ["ExactBinding", "parse_exact_binding"]
