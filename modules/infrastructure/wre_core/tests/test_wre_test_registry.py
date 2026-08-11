from __future__ import annotations

from copy import deepcopy
import ast
import json
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.scripts.generate_test_registry import (
    build_registry,
    canonical_bytes,
    tracked_test_paths,
)
from modules.infrastructure.wre_core.src.wre_test_registry import (
    MAX_FILES_PER_SHARD,
    REGISTRY_PATH,
    load_canonical_test_registry,
    registry_payload,
)
from modules.infrastructure.wre_core.src.wre_test_registry_classification import (
    classify_test_file,
)

ROOT = Path(__file__).resolve().parents[4]


def test_checked_in_registry_is_exact_deterministic_git_projection() -> None:
    expected = build_registry(ROOT)
    assert (ROOT / REGISTRY_PATH).read_bytes() == canonical_bytes(expected)
    assert expected["total_tests"] == len(tracked_test_paths(ROOT))
    assert expected["total_tests"] > 1_000


def test_registry_loads_and_partitions_every_automated_file_once() -> None:
    registry = load_canonical_test_registry(ROOT)
    shards = registry.automated_shards()
    paths = [path for shard in shards for path in shard.paths]
    expected = sorted(entry.path for entry in registry.entries if entry.collectable)
    assert sorted(paths) == expected
    assert len(paths) == len(set(paths))
    assert all(1 <= len(shard.paths) <= MAX_FILES_PER_SHARD for shard in shards)
    assert all(shard.registry_digest == registry.registry_digest for shard in shards)
    assert {entry.shard_id for entry in registry.entries if entry.collectable} == {
        shard.shard_id for shard in shards
    }
    assert any("-part-" in shard.shard_id for shard in shards)


def test_known_collection_destroyers_are_explicitly_quarantined() -> None:
    registry = load_canonical_test_registry(ROOT)
    by_path = {entry.path: entry for entry in registry.entries}
    browser = by_path[
        "modules/infrastructure/browser_actions/tests/test_autonomous_gemini_heart.py"
    ]
    stream = by_path["holo_index/qwen_advisor/test_wsp91_enhancement.py"]
    assert browser.collectable is False
    assert browser.quarantine_reasons == ("module_scope_external_effect",)
    assert stream.collectable is False
    assert stream.quarantine_reasons == (
        "module_scope_process_stream_mutation",
    )


def test_live_api_program_is_never_an_automated_test() -> None:
    registry = load_canonical_test_registry(ROOT)
    by_path = {entry.path: entry for entry in registry.entries}
    live_api = by_path[
        "modules/communication/livechat/tests/integration/test_simple_message.py"
    ]
    assert live_api.collectable is False
    assert live_api.suite_class == "operational"
    assert live_api.capabilities == ("import_path_mutation", "network")
    assert live_api.quarantine_reasons == ("module_scope_external_effect",)


def test_main_guard_effect_is_not_quarantined(tmp_path: Path) -> None:
    target = tmp_path / "tests/test_guarded.py"
    target.parent.mkdir()
    target.write_text(
        "import sys\nif __name__ == '__main__':\n    sys.exit(1)\n"
        "def test_ok(): assert True\n",
        encoding="utf-8",
    )
    result = classify_test_file(tmp_path, "tests/test_guarded.py")
    assert result.collectable is True
    assert result.quarantine_reasons == ()


@pytest.mark.parametrize(
    "source,reason",
    [
        ("import sys\nsys.exit(1)\n", "module_scope_external_effect"),
        (
            "from subprocess import run as go\ngo(['echo', 'x'])\n",
            "module_scope_external_effect",
        ),
        (
            "from googleapiclient.discovery import build\n"
            "service = build('youtube', 'v3')\n",
            "module_scope_external_effect",
        ),
        (
            "import googleapiclient.discovery as discovery\n"
            "service = discovery.build('youtube', 'v3')\n",
            "module_scope_external_effect",
        ),
        (
            "try:\n"
            "    from googleapiclient.discovery import build\n"
            "except ImportError:\n"
            "    build = None\n"
            "if build:\n"
            "    service = build('youtube', 'v3')\n",
            "module_scope_external_effect",
        ),
        (
            "if True:\n"
            "    from googleapiclient.discovery import build\n"
            "    service = build('youtube', 'v3')\n",
            "module_scope_external_effect",
        ),
        (
            "from googleapiclient.discovery import *\n",
            "module_scope_external_effect",
        ),
        ("import sys\nsys.stdout = object()\n", "module_scope_process_stream_mutation"),
        ("from pathlib import Path\nPath('x').write_text('x')\n", "module_scope_file_write"),
        ("raise RuntimeError('stop')\n", "module_scope_raise"),
        (
            "def test_called():\n    assert True\ntest_called()\n",
            "module_scope_test_function_invocation",
        ),
        (
            "from pathlib import Path\n"
            "def prepare():\n    Path('x').write_text('x')\nprepare()\n",
            "module_scope_local_function_invocation",
        ),
        (
            "from pathlib import Path\n"
            "@Path('x').write_text('x')\ndef test_decorated(): pass\n",
            "module_scope_file_write",
        ),
        (
            "from pathlib import Path\n"
            "def test_default(value=Path('x').write_text('x')): pass\n",
            "module_scope_file_write",
        ),
        (
            "from pathlib import Path\n"
            "def test_annotated(value: Path('x').write_text('x')): pass\n",
            "module_scope_file_write",
        ),
        (
            "from pathlib import Path\n"
            "class TestImport:\n    Path('x').write_text('x')\n",
            "module_scope_file_write",
        ),
    ],
)
def test_module_scope_process_effects_quarantine(
    tmp_path: Path, source: str, reason: str
) -> None:
    target = tmp_path / "tests/test_effect.py"
    target.parent.mkdir()
    target.write_text(source, encoding="utf-8")
    result = classify_test_file(tmp_path, "tests/test_effect.py")
    assert result.collectable is False
    assert reason in result.quarantine_reasons


def test_google_auth_request_constructor_is_not_an_external_effect(
    tmp_path: Path,
) -> None:
    target = tmp_path / "tests/test_request.py"
    target.parent.mkdir()
    target.write_text(
        "from google.auth.transport.requests import Request\n"
        "request = Request()\n"
        "def test_request(): assert request is not None\n",
        encoding="utf-8",
    )
    result = classify_test_file(tmp_path, "tests/test_request.py")
    assert result.collectable is True
    assert result.quarantine_reasons == ()


def test_main_guard_else_effect_is_quarantined(tmp_path: Path) -> None:
    target = tmp_path / "tests/test_guarded_else.py"
    target.parent.mkdir()
    target.write_text(
        "if __name__ == '__main__':\n"
        "    pass\n"
        "else:\n"
        "    from googleapiclient.discovery import build\n"
        "    service = build('youtube', 'v3')\n",
        encoding="utf-8",
    )
    result = classify_test_file(tmp_path, "tests/test_guarded_else.py")
    assert result.collectable is False
    assert result.quarantine_reasons == ("module_scope_external_effect",)
    assert result.capabilities == ("network",)


def test_loader_rejects_unknown_fields_missing_files_and_count_tampering(
    tmp_path: Path,
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    row = {
        "id": "test::tests::test_ok", "path": "tests/test_ok.py",
        "owner": "repository", "suite_class": "unit",
        "shard_id": "repository-unit", "capabilities": [],
        "execution_type": "unit", "collectable": True, "timeout_s": 180,
        "quarantine_reasons": [], "description": "",
    }
    original = registry_payload([row])
    cases = []
    unknown = deepcopy(original)
    unknown["unexpected"] = True
    cases.append(unknown)
    missing = deepcopy(original)
    missing["tests"][0]["path"] = "tests/test_missing.py"
    cases.append(missing)
    count = deepcopy(original)
    count["total_tests"] = 2
    cases.append(count)
    shard = deepcopy(original)
    shard["tests"][0]["shard_id"] = "invented-unit"
    cases.append(shard)
    target = tmp_path / REGISTRY_PATH
    target.parent.mkdir(parents=True)
    for payload in cases:
        target.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError):
            load_canonical_test_registry(tmp_path)


def test_registry_bytes_are_ascii_clean() -> None:
    data = (ROOT / REGISTRY_PATH).read_bytes()
    assert all(value < 128 for value in data)


def test_new_registry_runtime_respects_wsp62_limits() -> None:
    paths = [
        ROOT / "modules/infrastructure/wre_core/src/wre_test_registry.py",
        ROOT / "modules/infrastructure/wre_core/src/wre_test_registry_ast.py",
        ROOT / "modules/infrastructure/wre_core/src/wre_test_registry_classification.py",
        ROOT / "modules/infrastructure/wre_core/src/wre_git_commit_archive.py",
        ROOT / "modules/infrastructure/wre_core/src/wre_pytest_collection_collector.py",
        ROOT / "modules/infrastructure/wre_core/src/wre_python_environment_fingerprint.py",
        ROOT / "modules/infrastructure/wre_core/src/wre_test_shard_collection_runtime.py",
        ROOT / "modules/infrastructure/wre_core/scripts/generate_test_registry.py",
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 200, path
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, (
                    path, node.name, node.end_lineno - node.lineno + 1
                )
