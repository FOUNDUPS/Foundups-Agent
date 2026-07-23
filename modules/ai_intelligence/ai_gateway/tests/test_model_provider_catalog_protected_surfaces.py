"""Authority and size guards for direct provider catalog discovery."""

from __future__ import annotations

import ast
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
MODULE = REPO / "modules/ai_intelligence/ai_gateway"
NEW_MODULE_NAMES = {
    "model_openrouter_direct_discovery",
    "model_provider_catalog_snapshot",
    "openrouter_model_catalog_snapshot_once",
}
FUNCTION_LIMIT_MODULES = (
    "model_intelligence_catalog.py",
    "model_openrouter_direct_discovery.py",
    "model_provider_catalog_artifact_store.py",
    "model_provider_catalog_snapshot.py",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_protected_authority_surfaces_do_not_import_discovery() -> None:
    protected = [
        REPO / "main.py",
        MODULE / "main.py",
        MODULE / "src/ai_gateway.py",
        MODULE / "src/model_registry.py",
        MODULE / "src/model_intelligence_selection.py",
        MODULE / "src/model_promotion_gate.py",
        MODULE / "src/model_runtime_binding.py",
        MODULE / "src/model_signed_evidence.py",
        REPO / "modules/communication/moltbot_bridge/src/reddog_provider_call_evidence.py",
        REPO / "modules/infrastructure/shared_utilities/runtime_artifact_safety.py",
    ]
    for path in protected:
        imports = " ".join(_imports(path))
        assert not any(name in imports for name in NEW_MODULE_NAMES), path


def test_snapshot_is_pure_and_discovery_is_the_only_network_boundary() -> None:
    snapshot_imports = " ".join(
        _imports(MODULE / "src/model_provider_catalog_snapshot.py")
    )
    assert all(
        name not in snapshot_imports
        for name in ("aiohttp", "requests", "urllib", "socket", "subprocess")
    )
    discovery_source = (
        MODULE / "src/model_openrouter_direct_discovery.py"
    ).read_text(encoding="utf-8")
    assert "Authorization" not in discovery_source
    assert "subprocess" not in discovery_source
    assert "os.environ" not in discovery_source


def test_new_surfaces_stay_below_phase_one_size_limits() -> None:
    assert len(
        (MODULE / "src/model_provider_catalog_snapshot.py").read_text(
            encoding="utf-8"
        ).splitlines()
    ) < 450
    assert len(
        (MODULE / "src/model_openrouter_direct_discovery.py").read_text(
            encoding="utf-8"
        ).splitlines()
    ) < 400
    assert len(
        (MODULE / "src/model_provider_catalog_artifact_store.py").read_text(
            encoding="utf-8"
        ).splitlines()
    ) < 250
    assert len(
        (REPO / "scripts/openrouter_model_catalog_snapshot_once.py").read_text(
            encoding="utf-8"
        ).splitlines()
    ) < 120


def test_touched_production_functions_stay_within_wsp62_limit() -> None:
    violations = []
    for name in FUNCTION_LIMIT_MODULES:
        path = MODULE / "src" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                lines = node.end_lineno - node.lineno + 1
                if lines > 50:
                    violations.append(f"{name}:{node.name}:{lines}")
    assert violations == []


def test_no_implicit_scheduler_or_runtime_hook_was_added() -> None:
    script = (
        REPO / "scripts/openrouter_model_catalog_snapshot_once.py"
    ).read_text(encoding="utf-8")
    assert "--mode" in script
    assert "--runtime-root" in script
    assert "--attempt-path" in script
    assert "--candidate-path" in script
    assert "schedule.every" not in script
    assert "APScheduler" not in script
