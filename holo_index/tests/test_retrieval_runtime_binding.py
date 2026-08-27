"""Tests for owner-emitted HoloIndex retrieval runtime bindings."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.retrieval_runtime_binding import (
    RANKER_RUNTIME_MODULES,
    loaded_retrieval_ranker_digest,
    retrieval_ranker_digest_for_root,
)


def _runtime_tree(root: Path) -> None:
    for index, (_module, relative) in enumerate(RANKER_RUNTIME_MODULES):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"RUNTIME = {index}\n", encoding="utf-8")


def test_ranker_closure_pins_routing_projection_and_owner_config() -> None:
    paths = {relative for _module, relative in RANKER_RUNTIME_MODULES}
    assert {
        "holo_index/core/backend_routing.py",
        "modules/infrastructure/foundups_mcp_bridge/src/holo_query_service_response.py",
        "modules/infrastructure/foundups_mcp_bridge/src/holo_query_path_projection.py",
        "modules/infrastructure/foundups_mcp_bridge/src/holo_query_service_replica.py",
    }.issubset(paths)


def test_root_digest_changes_with_ranker_bytes(tmp_path: Path) -> None:
    _runtime_tree(tmp_path)
    before = retrieval_ranker_digest_for_root(tmp_path)
    (tmp_path / "holo_index/core/search_engine.py").write_text(
        "RUNTIME = 'changed'\n", encoding="utf-8"
    )
    after = retrieval_ranker_digest_for_root(tmp_path)

    assert before.startswith("sha256:")
    assert after != before


def test_loaded_digest_uses_one_exact_runtime_root(tmp_path: Path) -> None:
    _runtime_tree(tmp_path)
    origins = {
        module: SimpleNamespace(__file__=str(tmp_path / relative))
        for module, relative in RANKER_RUNTIME_MODULES
    }

    observed = loaded_retrieval_ranker_digest(origins.__getitem__)

    assert observed == retrieval_ranker_digest_for_root(tmp_path)


def test_loaded_digest_rejects_mixed_runtime_roots(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    _runtime_tree(first)
    _runtime_tree(second)
    origins = {
        module: SimpleNamespace(__file__=str(first / relative))
        for module, relative in RANKER_RUNTIME_MODULES
    }
    mixed_module, mixed_relative = RANKER_RUNTIME_MODULES[-1]
    origins[mixed_module] = SimpleNamespace(__file__=str(second / mixed_relative))

    with pytest.raises(ValueError, match="retrieval_runtime_module_origin_mismatch"):
        loaded_retrieval_ranker_digest(origins.__getitem__)


def test_root_digest_rejects_linked_ranker_file(tmp_path: Path) -> None:
    _runtime_tree(tmp_path)
    target = tmp_path / "outside.py"
    target.write_text("RUNTIME = 'outside'\n", encoding="utf-8")
    ranker = tmp_path / "holo_index/core/search_engine.py"
    ranker.unlink()
    try:
        ranker.symlink_to(target)
    except OSError:
        pytest.skip("host cannot create symlinks")

    with pytest.raises(ValueError, match="retrieval_runtime_path_invalid"):
        retrieval_ranker_digest_for_root(tmp_path)
