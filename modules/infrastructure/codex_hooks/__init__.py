"""FoundUps Codex lifecycle hook integration."""

from typing import Any, Mapping


def dispatch_hook(event: Mapping[str, Any], **kwargs: Any) -> dict[str, Any] | None:
    """Lazily dispatch without preloading the ``python -m`` entry module."""

    from .src.codex_hooks import dispatch_hook as _dispatch_hook

    return _dispatch_hook(event, **kwargs)


__all__ = ["dispatch_hook"]
