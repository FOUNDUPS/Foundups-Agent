"""Bounded Git-tree authority tests for module-name intent."""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from holo_index.module_intent_snapshot import (
    MAX_GIT_TREE_BYTES,
    MAX_MODULE_PATHS,
    ModuleIntentSnapshotError,
    clear_module_intent_snapshot_cache,
    load_module_intent_paths,
)
from holo_index.core import search_engine
from holo_index.core.search_engine import _module_intent
from holo_index.tests.module_intent_test_support import (
    HEAD_A,
    HEAD_B,
    candidate_batch as _batch,
    directory_tree as _tree,
)
from holo_index.tier0_retrieval import infer_explicit_module_target


def _snapshot_failure(tmp_path: Path, tree: bytes) -> None:
    def run(argv, **kwargs):
        if "rev-parse" in argv:
            output = HEAD_A.encode()
        elif "cat-file" in argv:
            output = _batch(kwargs["input"])
        else:
            output = tree
        return SimpleNamespace(returncode=0, stdout=output)

    with pytest.raises(
        ModuleIntentSnapshotError,
        match="HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE",
    ):
        load_module_intent_paths(tmp_path, run=run)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_module_intent_snapshot_cache()


def test_snapshot_uses_closed_git_authority_and_head_pinned_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    hostile_git = {
        "GIT_DIR": "attacker", "GIT_WORK_TREE": "attacker",
        "GIT_OBJECT_DIRECTORY": "attacker",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "attacker",
        "GIT_REPLACE_REF_BASE": "refs/evil",
    }
    for key, value in hostile_git.items():
        monkeypatch.setenv(key, value)

    def run(argv, **kwargs):
        calls.append(tuple(argv))
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 5.0
        assert all(kwargs["env"].get(key) != value for key, value in hostile_git.items())
        assert kwargs["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
        assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        if "rev-parse" in argv:
            return SimpleNamespace(returncode=0, stdout=(HEAD_A + "\n").encode())
        if "cat-file" in argv:
            assert kwargs["input"]
            return SimpleNamespace(returncode=0, stdout=_batch(kwargs["input"]))
        return SimpleNamespace(returncode=0, stdout=_tree(
            "modules/zeta/worker", "modules/zeta/worker/src",
            "modules/alpha/worker", "modules/alpha/worker/tests",
            "modules/alpha/unique", "modules/alpha/unique/src",
        ))

    assert load_module_intent_paths(tmp_path, run=run) == (
        "modules/alpha/unique",
        "modules/alpha/worker",
        "modules/zeta/worker",
    )
    assert calls[1][-8:] == (
        "ls-tree", "-z", "-d", "-r", "--full-tree", HEAD_A, "--", "modules",
    )
    assert "--no-replace-objects" in calls[1]
    assert "--no-optional-locks" in calls[1]
    assert calls[2][-2:] == ("cat-file", "--batch")


@pytest.mark.parametrize(
    ("name", "paths"),
    [
        ("src", (
            "modules/ai_intelligence/src", "modules/blockchain/src",
            "modules/economy/src", "modules/foundups/src",
        )),
        ("tests", (
            "modules/ai_intelligence/tests", "modules/blockchain/tests",
            "modules/foundups/tests", "modules/gamification/tests",
            "modules/platform_integration/tests",
        )),
        ("docs", ("modules/foundups/docs", "modules/infrastructure/docs")),
    ],
)
def test_duplicate_basenames_remain_ambiguous(
    name: str, paths: tuple[str, ...],
) -> None:
    assert infer_explicit_module_target(
        f"audit {name}", ({"path": path} for path in paths)
    ) is None


def test_cache_is_keyed_by_resolved_root_and_head(tmp_path: Path) -> None:
    heads = iter((HEAD_A, HEAD_A, HEAD_B))
    tree_calls = 0

    def run(argv, **_kwargs):
        nonlocal tree_calls
        if "rev-parse" in argv:
            return SimpleNamespace(returncode=0, stdout=next(heads).encode())
        if "cat-file" in argv:
            return SimpleNamespace(
                returncode=0, stdout=_batch(_kwargs["input"])
            )
        tree_calls += 1
        suffix = "one" if HEAD_A in argv else "two"
        return SimpleNamespace(
            returncode=0, stdout=_tree(
                f"modules/domain/{suffix}", f"modules/domain/{suffix}/src"
            )
        )

    assert load_module_intent_paths(tmp_path, run=run)[0].endswith("/one")
    assert load_module_intent_paths(tmp_path, run=run)[0].endswith("/one")
    assert load_module_intent_paths(tmp_path, run=run)[0].endswith("/two")
    assert tree_calls == 2


def test_root_identity_is_platform_aware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import holo_index.module_intent_snapshot as snapshot

    monkeypatch.setattr(snapshot.os.path, "normcase", lambda value: value)
    assert snapshot._root_identity(Path("/Repo/One")) != snapshot._root_identity(
        Path("/repo/one")
    )

    monkeypatch.setattr(
        snapshot.os.path, "normcase", lambda value: value.replace("/", "\\").lower()
    )
    assert snapshot._root_identity(Path("C:/Repo/One")) == snapshot._root_identity(
        Path("c:/repo/one")
    )


def test_concurrent_cache_population_remains_bounded(tmp_path: Path) -> None:
    import holo_index.module_intent_snapshot as snapshot

    roots = [tmp_path / f"repo-{index}" for index in range(24)]
    for root in roots:
        root.mkdir()

    def load(root: Path) -> tuple[str, ...]:
        marker = root.name.replace("repo-", "module")

        def run(argv, **kwargs):
            if "rev-parse" in argv:
                output = HEAD_A.encode()
            elif "cat-file" in argv:
                output = _batch(kwargs["input"])
            else:
                output = _tree(
                    f"modules/domain/{marker}", f"modules/domain/{marker}/src"
                )
            return SimpleNamespace(returncode=0, stdout=output)

        return load_module_intent_paths(root, run=run)

    with ThreadPoolExecutor(max_workers=24) as executor:
        assert all(executor.map(load, roots))

    assert hasattr(snapshot, "_CACHE_LOCK")
    assert len(snapshot._CACHE) <= snapshot.MAX_CACHED_GENERATIONS == 8


def test_duplicate_cold_git_loads_are_allowed_but_single_entry_is_published(
    tmp_path: Path,
) -> None:
    import holo_index.module_intent_snapshot as snapshot

    barrier = threading.Barrier(2)
    tree_calls = 0

    def run(argv, **kwargs):
        nonlocal tree_calls
        if "rev-parse" in argv:
            return SimpleNamespace(returncode=0, stdout=HEAD_A.encode())
        if "cat-file" in argv:
            return SimpleNamespace(
                returncode=0, stdout=_batch(kwargs["input"])
            )
        tree_calls += 1
        barrier.wait(timeout=2)
        return SimpleNamespace(
            returncode=0, stdout=_tree(
                "modules/domain/valid", "modules/domain/valid/src"
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(
            lambda _index: load_module_intent_paths(tmp_path, run=run),
            range(2),
        ))

    assert results == (("modules/domain/valid",),) * 2
    assert tree_calls == 2
    assert len(snapshot._CACHE) == 1


@pytest.mark.parametrize(
    "hostile_path",
    [
        "modules/d/good/src/../escape",
        "modules/d/good//src",
        "modules/d/good/./src",
        "modules\\d\\good\\src",
        "outside/d/m/src",
    ],
)
def test_every_tree_path_is_validated_before_depth_filter(
    tmp_path: Path, hostile_path: str,
) -> None:
    _snapshot_failure(
        tmp_path,
        _tree("modules/domain/valid", "modules/domain/valid/src", hostile_path),
    )


@pytest.mark.parametrize(
    "hostile_character",
    [
        pytest.param("\u0085", id="c1-next-line"),
        pytest.param("\u202e", id="bidi-override"),
        pytest.param("\u2066", id="bidi-isolate"),
        pytest.param("\u200c", id="zero-width-non-joiner"),
        pytest.param("\u200d", id="zero-width-joiner"),
        pytest.param("\ufeff", id="zero-width-no-break-space"),
    ],
)
def test_every_tree_path_rejects_unicode_control_and_format_characters(
    tmp_path: Path, hostile_character: str,
) -> None:
    _snapshot_failure(
        tmp_path,
        _tree(
            "modules/domain/valid", "modules/domain/valid/src",
            f"modules/domain/valid/src{hostile_character}hidden",
        ),
    )


def test_every_tree_path_rejects_surrogate_code_points() -> None:
    import holo_index.module_intent_snapshot as snapshot

    record = (
        f"040000 tree {'1' * 40}\tmodules/domain/valid/src\ud800hidden"
    )
    with pytest.raises(
        ModuleIntentSnapshotError,
        match="HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE",
    ):
        snapshot._tree_entry(record)


def test_nfc_equivalent_deeper_paths_are_duplicates(tmp_path: Path) -> None:
    _snapshot_failure(
        tmp_path,
        _tree(
            "modules/domain/valid", "modules/domain/valid/src",
            "modules/domain/valid/caf\u00e9",
            "modules/domain/valid/cafe\u0301",
        ),
    )


def test_visible_unicode_letters_and_symbols_remain_valid(tmp_path: Path) -> None:
    tree = _tree(
        "modules/domain/valid", "modules/domain/valid/src",
        "modules/domain/valid/caf\u00e9",
        "modules/domain/valid/\u5de5\u5177",
        "modules/domain/valid/\u2605",
    )

    def run(argv, **kwargs):
        if "rev-parse" in argv:
            output = HEAD_A.encode()
        elif "cat-file" in argv:
            output = _batch(kwargs["input"])
        else:
            output = tree
        return SimpleNamespace(returncode=0, stdout=output)

    assert load_module_intent_paths(tmp_path, run=run) == (
        "modules/domain/valid",
    )


@pytest.mark.parametrize(
    "tree",
    [
        _tree("modules/domain/valid", "modules/domain/valid/src")[:-1],
        _tree("modules/domain/valid", "modules/domain/valid/src") + b"\0",
        b"040000 tree " + (b"1" * 40) + b" modules/domain/valid\0",
        b"040000 tree " + (b"1" * 40) + b"\t\0",
        _tree("modules/domain/valid", "modules/domain/valid/src") + b"\xff\0",
    ],
)
def test_nul_framing_truncation_and_utf8_fail_closed(
    tmp_path: Path, tree: bytes,
) -> None:
    _snapshot_failure(tmp_path, tree)


@pytest.mark.parametrize("case_variant", [False, True])
def test_duplicate_deeper_records_fail_before_depth_filter(
    tmp_path: Path, case_variant: bool,
) -> None:
    duplicate = (
        "modules/domain/valid/SRC"
        if case_variant else "modules/domain/valid/src"
    )
    _snapshot_failure(
        tmp_path,
        _tree(
            "modules/domain/valid", "modules/domain/valid/src",
            duplicate,
        ),
    )


def test_valid_module_evidence_and_deeper_artifacts_are_accepted(tmp_path: Path) -> None:
    tree = _tree(
        "modules", "modules/domain", "modules/domain/valid",
        "modules/domain/valid/src", "modules/domain/valid/src/deeper",
        "modules/domain/valid/docs",
    )

    def run(argv, **kwargs):
        if "rev-parse" in argv:
            output = HEAD_A.encode()
        elif "cat-file" in argv:
            output = _batch(kwargs["input"])
        else:
            output = tree
        return SimpleNamespace(returncode=0, stdout=output)

    assert load_module_intent_paths(tmp_path, run=run) == (
        "modules/domain/valid",
    )


def test_exact_module_root_cap_accepts_4096_and_rejects_4097(tmp_path: Path) -> None:
    accepted_paths = tuple(
        path
        for index in range(MAX_MODULE_PATHS)
        for path in (
            f"modules/domain/module{index:04d}",
            f"modules/domain/module{index:04d}/src",
        )
    )
    accepted = _tree(*accepted_paths)

    def run_accepted(argv, **kwargs):
        if "rev-parse" in argv:
            output = HEAD_A.encode()
        elif "cat-file" in argv:
            output = _batch(kwargs["input"])
        else:
            output = accepted
        return SimpleNamespace(returncode=0, stdout=output)

    assert len(load_module_intent_paths(tmp_path, run=run_accepted)) == 4096
    clear_module_intent_snapshot_cache()
    _snapshot_failure(
        tmp_path,
        _tree(*(path for index in range(MAX_MODULE_PATHS + 1) for path in (
            f"modules/domain/module{index:04d}",
            f"modules/domain/module{index:04d}/src",
        ))),
    )


@pytest.mark.parametrize(
    "failure",
    [
        SimpleNamespace(returncode=7, stdout=b"failed"),
        SimpleNamespace(returncode=0, stdout=b"x" * (MAX_GIT_TREE_BYTES + 1)),
        SimpleNamespace(
            returncode=0,
            stdout=_tree("modules/domain/valid", "modules/domain/valid/src")
            + b"malformed\0",
        ),
        SimpleNamespace(
            returncode=0,
            stdout=_tree("modules/domain/valid", "modules/domain/valid/src")
            + f"100644 tree {'1' * 40}\tmodules/domain/mode\0".encode(),
        ),
        SimpleNamespace(
            returncode=0,
            stdout=_tree("modules/domain/valid", "modules/domain/valid/src")
            + f"040000 blob {'1' * 40}\tmodules/domain/type\0".encode(),
        ),
        SimpleNamespace(
            returncode=0,
            stdout=_tree("modules/domain/valid", "modules/domain/valid/src")
            + f"040000 tree {'z' * 40}\tmodules/domain/hash\0".encode(),
        ),
        SimpleNamespace(
            returncode=0,
            stdout=_tree("modules/domain/valid", "modules/domain/valid/src")
            + f"040000 tree {'1' * 40}\t\0".encode(),
        ),
        SimpleNamespace(
            returncode=0,
            stdout=_tree(
                "modules/domain/valid", "modules/domain/valid/src",
                "modules/DOMAIN/VALID", "modules/DOMAIN/VALID/SRC",
            ),
        ),
        SimpleNamespace(
            returncode=0,
            stdout=_tree(
                "modules/domain/valid", "modules/domain/valid/src",
                "modules/domain/valid/src",
            ),
        ),
        SimpleNamespace(
            returncode=0,
            stdout=_tree(
                "modules/domain/bad\nname", "modules/domain/bad\nname/src"
            ),
        ),
    ],
)
def test_nonzero_oversize_and_hostile_tree_fail_closed(
    tmp_path: Path, failure: SimpleNamespace,
) -> None:
    def run(argv, **_kwargs):
        if "rev-parse" in argv:
            return SimpleNamespace(returncode=0, stdout=HEAD_A.encode())
        return failure

    with pytest.raises(
        ModuleIntentSnapshotError,
        match="HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE",
    ):
        load_module_intent_paths(tmp_path, run=run)


def test_timeout_fails_closed_without_filesystem_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        Path, "rglob", lambda *_args, **_kwargs: pytest.fail("filesystem walk")
    )

    def run(_argv, **_kwargs):
        raise subprocess.TimeoutExpired("git", 5.0)

    with pytest.raises(ModuleIntentSnapshotError):
        load_module_intent_paths(tmp_path, run=run)


def test_full_path_intent_is_independent_of_module_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = "modules/communication/moltbot_bridge"
    monkeypatch.setattr(
        "holo_index.core.search_engine.load_module_intent_paths",
        lambda _root: pytest.fail("full path consulted module catalog"),
    )
    holo = type("_Holo", (), {"project_root": Path.cwd()})()

    path, registry = _module_intent(holo, f"audit {module}")

    assert path == module
    assert registry is None


@pytest.mark.parametrize("strict", [False, True])
def test_catalog_failure_never_reintroduces_hit_conditioned_inference(
    monkeypatch: pytest.MonkeyPatch, strict: bool,
) -> None:
    logged: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "holo_index.core.search_engine.load_module_intent_paths",
        lambda _root: (_ for _ in ()).throw(
            ModuleIntentSnapshotError("untrusted-detail")
        ),
    )
    holo = type("_Holo", (), {
        "project_root": Path.cwd(),
        "strict_semantic_owner": strict,
        "_log_agent_action": staticmethod(
            lambda message, level="INFO": logged.append((message, level))
        ),
    })()

    if strict:
        with pytest.raises(ModuleIntentSnapshotError):
            _module_intent(holo, "moltbot_bridge docs")
        assert logged == []
    else:
        assert _module_intent(holo, "moltbot_bridge docs") == (None, ())
        assert logged == [(
            "Module intent catalog unavailable; Tier-0 name promotion suppressed",
            "WARN",
        )]


@pytest.mark.parametrize("strict", [False, True])
def test_execute_search_catalog_failure_is_mode_explicit(
    monkeypatch: pytest.MonkeyPatch, strict: bool,
) -> None:
    registry_values: list[object] = []
    monkeypatch.setattr(
        search_engine,
        "load_module_intent_paths",
        lambda _root: (_ for _ in ()).throw(ModuleIntentSnapshotError("detail")),
    )
    monkeypatch.setattr(
        search_engine,
        "_search_collection",
        lambda *_args, **kwargs: registry_values.append(
            kwargs.get("module_registry_hits")
        ) or [],
    )
    holo = type("_Holo", (), {
        "project_root": Path.cwd(), "strict_semantic_owner": strict,
        "search_cache": None, "model": None, "docs_collection": object(),
        "_log_agent_action": staticmethod(lambda *_args, **_kwargs: None),
    })()

    result = search_engine.execute_search(
        holo, "moltbot_bridge docs", doc_type_filter="docs"
    )

    if strict:
        assert result["metadata"]["error"] == (
            "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
        )
        assert registry_values == []
    else:
        assert "error" not in result["metadata"]
        assert registry_values == [()]
