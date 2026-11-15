"""OpenClaw Bridge Module - Digital Twin gateway via OpenClaw + WRE routing."""

__all__ = ["OpenClawDAE", "OpenClawPlugin", "HoneypotDefense", "app", "MoltbotMessage", "OpenClawMessage", "FoundupsResponse"]


def __getattr__(name):
    """Keep pure routing/security imports free of webhook startup effects."""
    if name in {"OpenClawDAE", "OpenClawPlugin", "HoneypotDefense"}:
        from importlib import import_module
        return getattr(import_module('.openclaw_dae', __name__), name)
    if name in {"app", "MoltbotMessage", "OpenClawMessage", "FoundupsResponse", "_FASTAPI_AVAILABLE"}:
        from importlib import import_module
        try:
            webhook = import_module('.webhook_receiver', __name__)
        except ImportError:
            return False if name == '_FASTAPI_AVAILABLE' else None
        return True if name == '_FASTAPI_AVAILABLE' else getattr(webhook, name)
    raise AttributeError(name)
