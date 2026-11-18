#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the lazy package __init__ (FOUNDUP_AGENT_PACKAGE_INIT_LAZY_IMPORT_PHASE1).

Decision B: the #805/#806 "no Hermes / no vendor" boundary must hold at the IMPORT
boundary, not just in the file AST. The Kanban adapter MODULE and the #807 contract
MODULE are AST-clean, but BEFORE this slice ``modules/foundups/agent/src/__init__.py``
EAGERLY imported from ``.hermes_adapter`` and ``.hermes_model_router`` to expose 8
package-level names. That eager import meant ANY leaf-module import through the package
(e.g. ``import modules.foundups.agent.src.kanban_plugin_contract``) transitively loaded
the entire Hermes/vendor runtime (subprocess, sqlite3, urllib).

The fix converts those eager blocks into a PEP 562 lazy ``__getattr__`` so the 8 public
names still resolve on ACCESS while leaf-module imports no longer eager-load Hermes.

Test method note: pytest itself may already have imported subprocess/sqlite3/urllib, so
the "no vendor pull-in" assertions run in a FRESH child interpreter (via
``subprocess.run([sys.executable, "-c", SNIPPET])``) whose ``sys.modules`` is clean. The
``subprocess`` used HERE is the TEST HARNESS that spawns the child -- the boundary
assertion is about the CHILD's ``sys.modules``, never this process's.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Repo root (worktree) so the spawned child can import modules.foundups.agent.src.
_REPO_ROOT = Path(__file__).resolve().parents[4]

_PACKAGE = "modules.foundups.agent.src"
_HERMES_ADAPTER = _PACKAGE + ".hermes_adapter"
_HERMES_ROUTER = _PACKAGE + ".hermes_model_router"

# Modules that the eager __init__ used to leak on a leaf-module import.
_VENDOR_MODULES = (
    _HERMES_ADAPTER,
    _HERMES_ROUTER,
    "subprocess",
    "sqlite3",
    "urllib",
)

# The exact public surface that must keep resolving lazily.
_PUBLIC_NAMES = (
    "HermesFoundUpBuilder",
    "DEFAULT_QWEN_CONFIG",
    "MCP_BRIDGE_AVAILABLE",
    "FAM_DAEMON_AVAILABLE",
    "HermesModelRouter",
    "TaskCapability",
    "get_model_router",
    "route_to_model",
)


def _run_child(snippet: str) -> subprocess.CompletedProcess:
    """Run ``snippet`` in a FRESH interpreter with the worktree on PYTHONPATH.

    A clean child guarantees the no-vendor-pull-in assertions are about the leaf
    import alone, not modules pytest happened to load in this process.
    """
    return subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=str(_REPO_ROOT),
        env={
            "PYTHONPATH": str(_REPO_ROOT),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
    )


def _no_pullin_snippet(leaf_module: str) -> str:
    """Snippet asserting ``leaf_module`` pulls in none of the vendor modules."""
    vendor = repr(list(_VENDOR_MODULES))
    return (
        "import sys\n"
        f"import {leaf_module} as _\n"
        f"bad = [m for m in {vendor} if m in sys.modules]\n"
        "assert not bad, bad\n"
        "print('NO_PULLIN_OK')\n"
    )


def test_leaf_adapter_import_no_vendor_pullin():
    """Importing the kanban contract leaf must not eager-load Hermes/vendor.

    The parked publish-adapter (KANBAN_EXTERNAL_ADAPTER_PUBLISH_PILOT_PHASE1) lives in
    a DIFFERENT worktree and is intentionally absent here; the contract leaf
    (kanban_plugin_contract, #807) is the AST-clean leaf present in this worktree and
    is the canonical "adapter-side" leaf for the import-boundary proof.
    """
    result = _run_child(_no_pullin_snippet(_PACKAGE + ".kanban_plugin_contract"))
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "NO_PULLIN_OK" in result.stdout


def test_leaf_contract_import_no_vendor_pullin():
    """A second independent AST-clean leaf must also not eager-load Hermes/vendor."""
    result = _run_child(_no_pullin_snippet(_PACKAGE + ".source_authority"))
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "NO_PULLIN_OK" in result.stdout


def test_all_public_exports_still_resolve():
    """Every name in __all__ resolves lazily and is identity-stable on re-access."""
    import modules.foundups.agent.src as pkg

    assert sorted(pkg.__all__) == sorted(_PUBLIC_NAMES)
    for name in _PUBLIC_NAMES:
        first = getattr(pkg, name)
        assert first is not None, name
        second = getattr(pkg, name)
        assert first is second, ("identity-unstable", name)

    # Types/values match the source-module definitions (no behavior change).
    assert isinstance(pkg.DEFAULT_QWEN_CONFIG, dict)
    assert isinstance(pkg.MCP_BRIDGE_AVAILABLE, bool)
    assert isinstance(pkg.FAM_DAEMON_AVAILABLE, bool)
    assert isinstance(pkg.HermesFoundUpBuilder, type)
    assert isinstance(pkg.HermesModelRouter, type)
    assert isinstance(pkg.TaskCapability, type)
    assert callable(pkg.get_model_router)
    assert callable(pkg.route_to_model)


def test_lazy_access_loads_hermes_only_on_demand():
    """In a fresh child, hermes_adapter is absent until a public name is accessed."""
    snippet = (
        "import sys\n"
        f"import {_PACKAGE} as pkg\n"
        f"assert '{_HERMES_ADAPTER}' not in sys.modules, 'hermes pre-loaded'\n"
        "from modules.foundups.agent.src import HermesFoundUpBuilder as _b\n"
        f"assert '{_HERMES_ADAPTER}' in sys.modules, 'hermes not loaded on demand'\n"
        "print('LAZY_OK')\n"
    )
    result = _run_child(snippet)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "LAZY_OK" in result.stdout


def test_lazy_access_resolves_value_identical_to_source():
    """Accessing a public name yields the SAME object as the source module exports.

    Proves the lazy seam introduces no behavior change: the value resolved through the
    package is identical to the value defined in hermes_adapter / hermes_model_router.
    """
    import modules.foundups.agent.src as pkg
    from modules.foundups.agent.src import hermes_adapter, hermes_model_router

    assert pkg.HermesFoundUpBuilder is hermes_adapter.HermesFoundUpBuilder
    assert pkg.DEFAULT_QWEN_CONFIG is hermes_adapter.DEFAULT_QWEN_CONFIG
    assert pkg.MCP_BRIDGE_AVAILABLE == hermes_adapter.MCP_BRIDGE_AVAILABLE
    assert pkg.FAM_DAEMON_AVAILABLE == hermes_adapter.FAM_DAEMON_AVAILABLE
    assert pkg.HermesModelRouter is hermes_model_router.HermesModelRouter
    assert pkg.TaskCapability is hermes_model_router.TaskCapability
    assert pkg.get_model_router is hermes_model_router.get_model_router
    assert pkg.route_to_model is hermes_model_router.route_to_model


def test_no_circular_import():
    """The package, both leaves, and both hermes modules import in any order."""
    modules_to_chain = [
        _PACKAGE,
        _PACKAGE + ".kanban_plugin_contract",
        _PACKAGE + ".source_authority",
        _HERMES_ADAPTER,
        _HERMES_ROUTER,
    ]
    orders = [
        modules_to_chain,
        list(reversed(modules_to_chain)),
        [
            _HERMES_ROUTER,
            _PACKAGE + ".kanban_plugin_contract",
            _HERMES_ADAPTER,
            _PACKAGE,
            _PACKAGE + ".source_authority",
        ],
    ]
    for idx, order in enumerate(orders):
        snippet = (
            "\n".join("import " + m for m in order)
            + f"\nprint('CIRCULAR_OK_{idx}')\n"
        )
        result = _run_child(snippet)
        assert result.returncode == 0, (idx, result.stdout, result.stderr)
        assert f"CIRCULAR_OK_{idx}" in result.stdout


def test_unknown_attribute_raises_AttributeError():
    """A bogus package attribute raises AttributeError (not ImportError/other)."""
    import modules.foundups.agent.src as pkg

    import pytest

    with pytest.raises(AttributeError):
        getattr(pkg, "ThisNameDoesNotExist")


def test_dir_includes_public_names():
    """__dir__ surfaces the lazy public names (autocomplete / introspection)."""
    import modules.foundups.agent.src as pkg

    listing = dir(pkg)
    for name in _PUBLIC_NAMES:
        assert name in listing, name
