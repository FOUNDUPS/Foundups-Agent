"""UTC normalization shared by signed-worker lease modules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_utc(value: Any) -> datetime | None:
    """Parse one timezone-bearing ISO timestamp into UTC."""

    try:
        parsed = datetime.fromisoformat(
            str(value or "").replace("Z", "+00:00")
        )
    except ValueError:
        return None
    return aware(parsed) if parsed.tzinfo is not None else None


def aware(value: datetime) -> datetime:
    """Normalize one datetime to UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = ["aware", "parse_utc"]
