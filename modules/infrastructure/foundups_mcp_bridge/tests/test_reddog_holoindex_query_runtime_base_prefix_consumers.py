"""Real-topology falsifiers for query-runtime base-prefix consumers."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_process import (
    _validated_roots,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_candidate_binding import (
    CandidateBindingError,
    _composition_truth,
)
from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_runtime_composition_test_support import (
    materialize_composition,
    materialized_runtime_components,
)


@pytest.fixture
def o_root() -> Path:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-base-prefix-", dir=parent) as raw:
        yield Path(raw).resolve()


def _materialized_composition(root: Path):
    fixture = materialized_runtime_components(root)
    return fixture, materialize_composition(fixture).binding


def test_candidate_accepts_materialized_base_prefix_topology(o_root: Path) -> None:
    _fixture, composition = _materialized_composition(o_root)
    _composition_truth(composition)


def test_candidate_rejects_generation_root_as_base_prefix(o_root: Path) -> None:
    _fixture, composition = _materialized_composition(o_root)
    obsolete = replace(
        composition,
        base_runtime=replace(
            composition.base_runtime,
            base_prefix_root=composition.base_runtime.generation_root,
        ),
        interpreter_path=composition.base_runtime.generation_root / "python.exe",
    )
    with pytest.raises(CandidateBindingError, match="COMPOSITION_INVALID"):
        _composition_truth(obsolete)


def test_process_accepts_materialized_base_prefix_topology(o_root: Path) -> None:
    fixture, composition = _materialized_composition(o_root)
    roots = _validated_roots(composition, fixture.repo)
    assert roots["base_runtime"] == composition.base_runtime.base_prefix_root
