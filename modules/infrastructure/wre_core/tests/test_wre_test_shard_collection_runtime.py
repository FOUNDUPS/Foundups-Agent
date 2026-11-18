from __future__ import annotations

import json
from pathlib import Path
import subprocess

from modules.infrastructure.wre_core.src.wre_test_registry import (
    REGISTRY_PATH,
    registry_payload,
)
from modules.infrastructure.wre_core.src.wre_test_shard_collection_runtime import (
    collect_registered_test_shards,
)


def _row(path: str, owner: str, shard: str) -> dict[str, object]:
    return {
        "id": "test::" + path.removesuffix(".py").replace("/", "::"),
        "path": path, "owner": owner, "suite_class": "unit",
        "shard_id": shard, "capabilities": [], "execution_type": "unit",
        "collectable": True, "timeout_s": 60, "quarantine_reasons": [],
        "description": "",
    }


def _repository(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "bad").mkdir()
    (tmp_path / "tests/test_good.py").write_text(
        "from pathlib import Path\nHOME_AT_IMPORT = Path.home()\n"
        "def test_body_not_run():\n"
        "    Path('body-ran').write_text('bad')\n",
        encoding="utf-8",
    )
    (tmp_path / "bad/test_bad.py").write_text(
        "from pathlib import Path\n"
        "Path('source-mutation').write_text('discarded')\n"
        "raise RuntimeError('collection failure')\n",
        encoding="utf-8",
    )
    (tmp_path / "forge").mkdir()
    (tmp_path / "forge/test_forge.py").write_text(
        "import __main__\n"
        "__main__._build_report = lambda *_: {'forged': True}\n"
        "def test_forge(): pass\n",
        encoding="utf-8",
    )
    payload = registry_payload([
        _row("tests/test_good.py", "repository", "repository-unit"),
        _row("bad/test_bad.py", "bad", "bad-unit"),
        _row("forge/test_forge.py", "forge", "forge-unit"),
    ])
    target = tmp_path / REGISTRY_PATH
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(payload), encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "wre@example.invalid")
    _git(tmp_path, "config", "user.name", "WRE Test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "fixture")
    return tmp_path


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True,
        encoding="utf-8", check=True,
    )
    return result.stdout.strip()


def test_collection_reports_are_shard_isolated_and_non_authoritative(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    result = collect_registered_test_shards(
        repo, head_sha=head, shard_ids=["repository-unit", "bad-unit"]
    )
    by_id = {item["shard_id"]: item for item in result["results"]}
    assert by_id["repository-unit"]["status"] == "COLLECTION_REPORTED"
    assert by_id["repository-unit"]["collected_count"] == 1
    assert by_id["repository-unit"]["collected_ids"] == [
        "tests/test_good.py::test_body_not_run"
    ]
    assert by_id["bad-unit"]["status"] == "COLLECTION_FAILED"
    assert result["reported_successful_shards"] == 1
    assert result["reported_failed_shards"] == 1
    assert result["collection_reported_complete"] is False
    assert result["test_body_execution_absence_verified"] is False
    assert result["collector_integrity_verified"] is False
    assert result["receipt_authentication_verified"] is False
    assert result["diagnostic_only"] is True
    assert result["execution_authority_verified"] is False
    assert result["source_worktree_non_execution_verified"] is False
    assert result["python_environment_digest"].startswith("sha256:")
    assert result["python_package_count"] > 0
    assert result["python_version"]
    assert not (repo / "body-ran").exists()
    assert not (repo / "source-mutation").exists()


def test_invalid_or_duplicate_shard_selection_fails_before_collection(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    for values in ([], ["unknown"], ["repository-unit", "repository-unit"]):
        result = collect_registered_test_shards(
            repo, head_sha=head, shard_ids=values
        )
        assert result["collection_reported_complete"] is False
        assert result["rejection_reasons"] == ["test_shard_selection_invalid"]
        assert result["test_body_execution_absence_verified"] is False
        assert result["source_worktree_non_execution_verified"] is False


def test_imported_test_cannot_replace_trusted_report_builder(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    result = collect_registered_test_shards(
        repo, head_sha=_git(repo, "rev-parse", "HEAD"),
        shard_ids=["forge-unit"],
    )
    assert result["collection_reported_complete"] is False
    assert result["results"][0]["status"] == "COLLECTION_FAILED"
    assert result["results"][0]["collected_ids"] == []


def test_unknown_or_non_commit_sha_rejects_before_collection(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    for head in ("", "a" * 40):
        result = collect_registered_test_shards(
            repo, head_sha=head, shard_ids=["repository-unit"]
        )
        assert result["rejection_reasons"] == ["test_shard_materialization_failed"]
        assert result["source_worktree_non_execution_verified"] is False


def test_external_checkout_import_is_blocked_before_module_execution(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo = _repository(repo_root)
    external = tmp_path / "other-checkout"
    external.mkdir()
    (external / "outside.py").write_text(
        "from pathlib import Path\n"
        "Path(__file__).with_name('executed').write_text('bad')\n",
        encoding="utf-8",
    )
    test_path = repo / "tests/test_external.py"
    test_path.write_text(
        f"import sys\nsys.path.insert(0, {str(external)!r})\nimport outside\n"
        "def test_unreachable():\n    assert False\n",
        encoding="utf-8",
    )
    payload = registry_payload([
        _row("tests/test_external.py", "repository", "repository-unit")
    ])
    (repo / REGISTRY_PATH).write_text(json.dumps(payload), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "external import fixture")
    result = collect_registered_test_shards(
        repo, head_sha=_git(repo, "rev-parse", "HEAD"),
        shard_ids=["repository-unit"],
    )
    shard = result["results"][0]
    assert shard["status"] == "COLLECTION_FAILED"
    assert shard["ordinary_import_guard_reported_passed"] is False
    assert shard["blocked_import_origins"] == [str(external / "outside.py")]
    assert not (external / "executed").exists()
