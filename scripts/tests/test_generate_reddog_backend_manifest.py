"""Independent contract tests for the RedDog backend manifest generator."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = REPO_ROOT / "scripts" / "generate_reddog_backend_manifest.py"
SPEC = importlib.util.spec_from_file_location("reddog_backend_manifest_generator", GENERATOR_PATH)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def test_package_initializers_resolve_relative_imports_from_their_package() -> None:
    initializer = REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "src" / "__init__.py"
    module = initializer.with_name("openclaw_dae.py")

    expected = ["modules", "communication", "moltbot_bridge", "src"]
    assert generator._package_parts(initializer) == expected
    assert generator._package_parts(module) == expected


def test_generated_closure_binds_executable_and_dynamic_load_sentinels() -> None:
    manifest = generator.build_manifest()
    runtime = set(manifest["required_runtime_files"])
    tracked = set(generator._tracked_files())

    assert runtime.issubset(tracked)
    assert set(generator.EXECUTABLE_FILES).issubset(runtime)
    assert "holo_index.py" in runtime
    assert "scripts/reddog_authoritative_work_state_query_once.py" in runtime
    assert "modules/communication/moltbot_bridge/src/reddog_authoritative_work_state_query.py" in runtime
    assert "modules/communication/moltbot_bridge/src/openclaw_dae.py" in runtime
    assert "modules/foundups/src/foundup_registry_loader.py" in runtime
    assert "modules/platform_integration/linkedin_agent/src/linkedin_agent.py" in runtime
    assert "modules/infrastructure/database/src/Database.py" not in runtime
    assert "modules/infrastructure/database/src/database.py" in runtime


def test_checked_in_manifest_matches_independent_generation() -> None:
    checked_in = json.loads(generator.MANIFEST_PATH.read_text(encoding="utf-8"))
    generated = generator.build_manifest()

    assert checked_in == generated
    assert generator.canonical_manifest_digest(generated) == (
        "6db7bb66e8ceea1c22a46f1c36acef23aeb17d3128a620ca08d5e421b867e7c6"
    )
