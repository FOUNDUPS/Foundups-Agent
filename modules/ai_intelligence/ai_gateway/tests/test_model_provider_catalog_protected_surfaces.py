"""Authority and size guards for direct provider catalog discovery."""

from __future__ import annotations

import ast
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
MODULE = REPO / "modules/ai_intelligence/ai_gateway"
IDLE_PROJECTION = (
    REPO
    / "modules/infrastructure/idle_automation/src/openrouter_catalog_projection.py"
)
NEW_MODULE_NAMES = {
    "model_openrouter_direct_discovery",
    "model_openrouter_schedule_adapter",
    "model_openrouter_scheduled_discovery",
    "model_provider_catalog_replay_state",
    "model_provider_catalog_snapshot",
    "model_provider_execution_control_evidence",
    "model_provider_execution_control_projection",
    "openrouter_model_catalog_snapshot_once",
}
FUNCTION_LIMIT_MODULES = (
    "model_intelligence_catalog.py",
    "model_openrouter_direct_discovery.py",
    "model_openrouter_schedule_adapter.py",
    "model_openrouter_scheduled_discovery.py",
    "model_provider_catalog_atomic_io.py",
    "model_provider_catalog_artifact_store.py",
    "model_provider_catalog_snapshot.py",
    "model_provider_catalog_replay_state.py",
    "model_provider_execution_control_evidence.py",
    "model_provider_execution_control_projection.py",
)
SOURCE_LINE_LIMITS = {
    "model_provider_catalog_snapshot.py": 450,
    "model_openrouter_direct_discovery.py": 400,
    "model_provider_catalog_atomic_io.py": 400,
    "model_provider_catalog_artifact_store.py": 250,
    "model_openrouter_scheduled_discovery.py": 500,
    "model_openrouter_schedule_adapter.py": 250,
    "model_provider_catalog_replay_state.py": 500,
    "model_provider_execution_control_projection.py": 200,
    "model_provider_execution_control_evidence.py": 400,
}


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


def test_execution_control_surfaces_have_no_network_or_runtime_authority_imports() -> None:
    forbidden = (
        "ai_gateway",
        "aiohttp",
        "http",
        "httpx",
        "requests",
        "urllib",
        "socket",
        "subprocess",
        "websocket",
        "model_openrouter_direct_discovery",
        "model_intelligence_catalog",
        "model_intelligence_selection",
        "model_promotion_gate",
        "model_registry",
        "model_runtime_binding",
        "model_signed_evidence",
        "model_autoresearch_configured_gateway_runner",
        "reddog_provider_call_evidence",
    )
    for name in (
        "model_provider_execution_control_projection.py",
        "model_provider_execution_control_evidence.py",
    ):
        imports = _imports(MODULE / "src" / name)
        assert not any(
            fragment in imported
            for imported in imports
            for fragment in forbidden
        ), name


def test_new_surfaces_stay_below_phase_one_size_limits() -> None:
    for name, limit in SOURCE_LINE_LIMITS.items():
        source = (MODULE / "src" / name).read_text(encoding="utf-8")
        assert len(source.splitlines()) < limit, name
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


def test_scheduled_guard_has_no_authority_surface_imports() -> None:
    imports = set()
    for name in (
        "model_openrouter_schedule_adapter.py",
        "model_openrouter_scheduled_discovery.py",
        "model_provider_catalog_replay_state.py",
    ):
        imports.update(_imports(MODULE / "src" / name))
    forbidden = (
        "model_registry",
        "model_intelligence_catalog",
        "model_intelligence_selection",
        "model_promotion_gate",
        "model_runtime_binding",
    )
    assert not any(
        fragment in imported
        for imported in imports
        for fragment in forbidden
    )


def test_manual_surfaces_do_not_import_or_export_scheduled_guard() -> None:
    scheduled_names = (
        "model_openrouter_schedule_adapter",
        "model_openrouter_scheduled_discovery",
        "model_provider_catalog_replay_state",
    )
    manual_paths = (
        MODULE / "src/model_openrouter_direct_discovery.py",
        REPO / "scripts/openrouter_model_catalog_snapshot_once.py",
    )
    for path in manual_paths:
        imports = _imports(path)
        source = path.read_text(encoding="utf-8")
        assert not any(
            name in imported
            for imported in imports
            for name in scheduled_names
        )
        assert not any(name in source for name in scheduled_names)


def test_schedule_adapter_has_no_direct_or_bridge_escape_hatch() -> None:
    path = MODULE / "src/model_openrouter_schedule_adapter.py"
    source = path.read_text(encoding="utf-8")
    imports = _imports(path)
    forbidden = (
        "model_openrouter_direct_discovery",
        "aiohttp",
        "requests",
        "urllib",
        "socket",
    )
    assert not any(
        fragment in imported
        for imported in imports
        for fragment in forbidden
    )
    assert "discover_openrouter_model_catalog" not in source
    assert "bridge_candidate_to_canonical_catalog" not in source


def test_idle_projection_boundary_stays_pure_and_bounded() -> None:
    source = IDLE_PROJECTION.read_text(encoding="utf-8")
    imports = " ".join(_imports(IDLE_PROJECTION))
    forbidden = (
        "ai_gateway",
        "aiohttp",
        "requests",
        "urllib",
        "socket",
        "subprocess",
    )
    assert not any(fragment in imports for fragment in forbidden)
    assert len(source.splitlines()) < 100
    tree = ast.parse(source)
    assert all(
        node.end_lineno - node.lineno + 1 <= 50
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
    )
