"""Repository-confinement tests for offline bundle filesystem access."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from holo_index.cli import bundle_path_confinement as bundle_confinement
from holo_index.cli.commands import bundle_json


def test_module_hint_rejects_absolute_drive_without_touching_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    real_exists = Path.exists

    def guarded_exists(path: Path) -> bool:
        if str(path).replace("\\", "/").lower().startswith("e:/holoindex"):
            raise AssertionError("absolute foreign hint was touched")
        return real_exists(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert bundle_confinement._resolve_module_dir(
        repo_root, "E:/HoloIndex"
    ) is None


def test_module_hint_rejects_traversal_and_foreign_module_symlink(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "modules" / "communication").mkdir(parents=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()

    assert bundle_confinement._resolve_module_dir(repo_root, "../foreign") is None

    linked = repo_root / "modules" / "communication" / "linked"
    try:
        linked.symlink_to(foreign, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    assert bundle_confinement._resolve_module_dir(
        repo_root, "modules/communication/linked"
    ) is None


def test_module_domain_discovery_is_sorted_deterministically(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "modules" / "z_last" / "example").mkdir(parents=True)
    expected = repo_root / "modules" / "a_first" / "example"
    expected.mkdir(parents=True)

    resolved = bundle_confinement._resolve_module_dir(repo_root, "example")

    assert resolved == expected.resolve()


def test_module_domain_discovery_honors_entry_cap_before_match(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    modules_root = repo_root / "modules"
    for name in ("a_one", "b_two"):
        (modules_root / name).mkdir(parents=True)
    beyond_cap = modules_root / "c_three" / "example"
    beyond_cap.mkdir(parents=True)
    monkeypatch.setattr(
        bundle_confinement,
        "LEXICAL_MODULE_DOMAIN_MAX_ENTRIES",
        2,
        raising=False,
    )

    assert bundle_confinement._resolve_module_dir(repo_root, "example") is None


def test_module_domain_discovery_fails_closed_when_match_precedes_cap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    modules_root = repo_root / "modules"
    (modules_root / "a_one" / "example").mkdir(parents=True)
    for name in ("b_two", "c_three"):
        (modules_root / name).mkdir(parents=True)
    monkeypatch.setattr(
        bundle_confinement,
        "LEXICAL_MODULE_DOMAIN_MAX_ENTRIES",
        2,
    )

    assert bundle_confinement._resolve_module_dir(repo_root, "example") is None


def test_load_need_to_rejects_foreign_navigation_symlink(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    foreign_nav = tmp_path / "NAVIGATION.py"
    foreign_nav.write_text(
        "NEED_TO = {'foreign secret': 'E:/HoloIndex/private.py'}\n",
        encoding="utf-8",
    )
    nav_path = repo_root / "NAVIGATION.py"
    try:
        nav_path.symlink_to(foreign_nav)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    assert bundle_json._load_need_to(repo_root) == {}


def test_navigation_loader_rejects_oversize_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(
        bundle_json,
        "LEXICAL_NAVIGATION_MAX_BYTES",
        64,
        raising=False,
    )
    (repo_root / "NAVIGATION.py").write_bytes(
        b"NEED_TO = {'oversize marker': 'must_not_be_read.py'}\n" + b"#" * 64
    )

    assert bundle_json._load_need_to(repo_root) == {}


def test_load_repo_wsp_summary_rejects_symlinked_wsp_root(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "WSP_framework").mkdir(parents=True)
    foreign_wsp_root = tmp_path / "foreign-wsps"
    foreign_wsp_root.mkdir()
    (foreign_wsp_root / "WSP_999_FOREIGN.md").write_text(
        "# WSP 999 Foreign\n\nforeign secret\n",
        encoding="utf-8",
    )
    linked_root = repo_root / "WSP_framework" / "src"
    try:
        linked_root.symlink_to(foreign_wsp_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    assert bundle_json._load_repo_wsp_summary(repo_root) == {}


def test_wsp_discovery_honors_entry_cap_before_sorting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    wsp_root = repo_root / "WSP_framework" / "src"
    wsp_root.mkdir(parents=True)
    for index in range(6):
        (wsp_root / f"WSP_{index + 1}_CAP.md").write_text(
            f"# WSP {index + 1} Cap\n\nentry {index + 1}\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(
        bundle_json,
        "LEXICAL_WSP_MAX_ENTRIES",
        2,
        raising=False,
    )

    summary = bundle_json._load_repo_wsp_summary(repo_root)

    assert summary == {}


def test_wsp_discovery_does_not_use_unbounded_glob_materialization() -> None:
    import inspect

    source = inspect.getsource(bundle_json._load_repo_wsp_summary)

    assert ".glob(" not in source
    assert "LEXICAL_WSP_MAX_ENTRIES" in source


def test_reparse_detection_seam_rejects_module_nav_and_wsp_components(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "junction"
    module_dir.mkdir(parents=True)
    nav_path = repo_root / "NAVIGATION.py"
    nav_path.write_text("NEED_TO = {'foreign': 'foreign.py'}\n", encoding="utf-8")
    wsp_root = repo_root / "WSP_framework" / "src"
    wsp_root.mkdir(parents=True)
    (wsp_root / "WSP_999_FOREIGN.md").write_text(
        "# WSP 999 Foreign\n", encoding="utf-8"
    )
    rejected = {
        module_dir.resolve(strict=False),
        nav_path.resolve(strict=False),
        wsp_root.resolve(strict=False),
    }
    real_detector = bundle_confinement._is_link_or_reparse

    monkeypatch.setattr(
        bundle_confinement,
        "_is_link_or_reparse",
        lambda path: (
            Path(path).resolve(strict=False) in rejected or real_detector(path)
        ),
    )

    assert bundle_confinement._resolve_module_dir(
        repo_root, "modules/communication/junction"
    ) is None
    assert bundle_json._load_need_to(repo_root) == {}
    assert bundle_json._load_repo_wsp_summary(repo_root) == {}


def test_reparse_detection_seam_rejects_repository_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "NAVIGATION.py").write_text(
        "NEED_TO = {'foreign': 'foreign.py'}\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        bundle_confinement,
        "_is_link_or_reparse",
        lambda path: Path(path) == repo_root,
    )

    assert bundle_json._load_need_to(repo_root) == {}
    assert bundle_confinement._resolve_module_dir(
        repo_root, "modules/example"
    ) is None


def test_offline_module_walk_rejects_nested_reparse_before_enumeration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    nested = module_dir / "junction"
    nested.mkdir(parents=True)
    (repo_root / "NAVIGATION.py").write_text("NEED_TO = {}\n", encoding="utf-8")
    (nested / "foreign_secret.py").write_text("SECRET = True\n", encoding="utf-8")
    real_detector = bundle_confinement._is_link_or_reparse
    real_scandir = os.scandir

    monkeypatch.setattr(
        bundle_confinement,
        "_is_link_or_reparse",
        lambda path: (
            Path(path).resolve(strict=False) == nested.resolve(strict=False)
            or real_detector(path)
        ),
    )

    def guarded_scandir(path):
        if Path(path).resolve(strict=False) == nested.resolve(strict=False):
            raise AssertionError("nested reparse directory was enumerated")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", guarded_scandir)

    payload = bundle_json._lexical_task_retrieval(
        repo_root,
        "foreign secret",
        8,
        str(tmp_path / "unused-ssd"),
        module_dir=module_dir,
    )

    assert all("foreign_secret.py" not in str(hit) for hit in payload["code_hits"])


def test_offline_module_walk_rejects_nested_foreign_file_symlink(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    module_dir.mkdir(parents=True)
    (repo_root / "NAVIGATION.py").write_text("NEED_TO = {}\n", encoding="utf-8")
    foreign = tmp_path / "foreign_secret.py"
    foreign.write_text("SECRET = True\n", encoding="utf-8")
    linked = module_dir / "foreign_secret.py"
    try:
        linked.symlink_to(foreign)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    payload = bundle_json._lexical_task_retrieval(
        repo_root,
        "foreign secret",
        8,
        str(tmp_path / "unused-ssd"),
        module_dir=module_dir,
    )

    assert all("foreign_secret.py" not in str(hit) for hit in payload["code_hits"])


def test_offline_module_walk_honors_entry_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    module_dir.mkdir(parents=True)
    (repo_root / "NAVIGATION.py").write_text("NEED_TO = {}\n", encoding="utf-8")
    for index in range(6):
        (module_dir / f"budget_match_{index}.py").write_text(
            f"VALUE = {index}\n", encoding="utf-8"
        )
    monkeypatch.setattr(bundle_confinement, "LEXICAL_MODULE_MAX_ENTRIES", 2)

    payload = bundle_json._lexical_task_retrieval(
        repo_root,
        "budget match",
        20,
        str(tmp_path / "unused-ssd"),
        module_dir=module_dir,
    )

    module_hits = [
        hit for hit in payload["code_hits"] if "budget_match_" in hit["location"]
    ]
    assert module_hits == []


def test_artifact_snapshot_rejects_nested_reparse_without_exists_follow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    module_dir.mkdir(parents=True)
    readme = module_dir / "README.md"
    readme.write_text("# Foreign-linked contract\n", encoding="utf-8")
    real_detector = bundle_confinement._is_link_or_reparse
    real_exists = Path.exists
    touched: list[Path] = []

    monkeypatch.setattr(
        bundle_confinement,
        "_is_link_or_reparse",
        lambda path: (
            Path(path).resolve(strict=False) == readme.resolve(strict=False)
            or real_detector(path)
        ),
    )

    def guarded_exists(path: Path) -> bool:
        if path == readme:
            touched.append(path)
            raise AssertionError("artifact link target existence was followed")
        return real_exists(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    snapshot = bundle_json._artifact_snapshot(repo_root, module_dir)
    readme_row = next(
        item for item in snapshot["artifacts"] if item["name"] == "README.md"
    )
    assert readme_row["exists"] is False
    assert touched == []


def test_offline_bundle_lexical_never_reads_foreign_ssd_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    wsp_root = repo_root / "WSP_framework" / "src"
    wsp_root.mkdir(parents=True)
    (repo_root / "NAVIGATION.py").write_text("NEED_TO = {}\n", encoding="utf-8")
    (wsp_root / "WSP_97_System_Execution_Prompting_Protocol.md").write_text(
        "# WSP 97 System Execution Prompting Protocol\n\n"
        "Root-bound current repository evidence.\n",
        encoding="utf-8",
    )
    foreign_ssd = tmp_path / "foreign-store"
    foreign_summary = foreign_ssd / "indexes" / "wsp_summary.json"
    foreign_summary.parent.mkdir(parents=True)
    foreign_summary.write_text(
        '{"WSP 999":{"title":"foreign secret","summary":"foreign",'
        '"path":"Q:/other-repo/WSP_999.md"}}',
        encoding="utf-8",
    )
    reads: list[Path] = []
    real_read_text = Path.read_text

    def recording_read_text(path: Path, *args, **kwargs) -> str:
        reads.append(path.resolve(strict=False))
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording_read_text)

    payload = bundle_json._lexical_task_retrieval(
        repo_root,
        "foreign secret WSP 97 root-bound",
        8,
        str(foreign_ssd),
    )

    assert all(str(foreign_ssd) not in str(path) for path in reads)
    assert all("Q:/other-repo" not in str(hit) for hit in payload["wsp_hits"])
    assert any(hit["wsp"] == "WSP 97" for hit in payload["wsp_hits"])
    assert payload["metadata"]["no_holoindex_store_access"] is True
