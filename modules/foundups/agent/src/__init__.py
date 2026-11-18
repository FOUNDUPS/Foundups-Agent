"""
FoundUps Agent Module

Agent lifecycle management and FoundUp building capabilities.
Hermes + dynamic model routing for autonomous FoundUp extraction.
MCP Bridge v1.4 perception layer for intelligent decisions.

Models:
- UI-TARS 1.5 7B: Vision (eyes)
- Qwen Coder 7B: Code generation
- Gemma4: Base reasoning
- Gemma 270M: Fast triage
- Qwen3-TTS: Voice/TTS

Perception (MCP Bridge v1.4):
- Layer 0: Sense (repo, docs, overseer)
- Layer 1: Dependency + Diff
- Layer 2: Impact Prediction
- Layer 3: HoloIndex Recall
- Layer 4: Signal Normalization
"""

__version__ = "0.5.0"
__all__ = [
    "HermesFoundUpBuilder",
    "DEFAULT_QWEN_CONFIG",
    "HermesModelRouter",
    "TaskCapability",
    "get_model_router",
    "route_to_model",
    "MCP_BRIDGE_AVAILABLE",
    "FAM_DAEMON_AVAILABLE",
]

# PEP 562 lazy module-level __getattr__.
#
# The 8 public names below are EAGERLY defined in .hermes_adapter and
# .hermes_model_router, both of which transitively pull in Hermes, subprocess,
# sqlite3 and urllib. Eagerly importing them here meant that ANY leaf-module
# import through this package (e.g. ``import
# modules.foundups.agent.src.kanban_plugin_contract``) silently loaded the entire
# Hermes/vendor runtime -- violating the #805/#806 "no Hermes / no vendor" import
# boundary at the IMPORT boundary, not just in the file AST.
#
# Resolving these names lazily on ACCESS keeps the public surface identical
# (``from modules.foundups.agent.src import HermesFoundUpBuilder`` still works and
# is identity-stable) while ensuring a leaf-module import no longer eager-loads
# Hermes or any vendor/runtime-heavy dependency.
_LAZY = {
    "HermesFoundUpBuilder": ".hermes_adapter",
    "DEFAULT_QWEN_CONFIG": ".hermes_adapter",
    "MCP_BRIDGE_AVAILABLE": ".hermes_adapter",
    "FAM_DAEMON_AVAILABLE": ".hermes_adapter",
    "HermesModelRouter": ".hermes_model_router",
    "TaskCapability": ".hermes_model_router",
    "get_model_router": ".hermes_model_router",
    "route_to_model": ".hermes_model_router",
}


def __getattr__(name):
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    mod = importlib.import_module(target, __name__)
    value = getattr(mod, name)
    # Cache on the package so repeated access is cheap and identity-stable, and
    # so __getattr__ is not re-invoked for an already-resolved name.
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals().keys()) | set(__all__))
