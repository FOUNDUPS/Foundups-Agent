"""Compatibility surface for governed HoloIndex maintenance children."""

from __future__ import annotations

from .reddog_bounded_child_process import (
    BoundedChildResult,
    CHILD_CAPTURE_CLEANUP_SECONDS,
    CHILD_STDOUT_MAX_BYTES,
    bounded_child_runner,
)


REFRESH_STDOUT_MAX_BYTES = CHILD_STDOUT_MAX_BYTES
REFRESH_CAPTURE_CLEANUP_SECONDS = CHILD_CAPTURE_CLEANUP_SECONDS
BoundedRefreshResult = BoundedChildResult


def bounded_refresh_runner(command, **kwargs) -> BoundedRefreshResult:
    """Preserve the maintenance API while using the shared child runner."""

    kwargs["_reader_name"] = "reddog-holo-refresh-output"
    return bounded_child_runner(command, **kwargs)


__all__ = ["BoundedRefreshResult", "bounded_refresh_runner"]
