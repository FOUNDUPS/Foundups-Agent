"""CLI Module - Command Line Interface for FoundUps Agent.

Extracted from main.py per WSP 62 (file size enforcement).
"""

__all__ = ["run_main_menu"]


def __getattr__(name):
    """Speech adapters can load without importing every interactive menu dependency."""
    if name == "run_main_menu":
        from modules.infrastructure.cli.src.main_menu import run_main_menu
        return run_main_menu
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
