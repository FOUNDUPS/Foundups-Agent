"""Generic module Tier-0 retrieval hardening regressions.

Slice: HOLOINDEX_TIER0_RETRIEVAL_HARDENING_PHASE1

All collection behavior is deterministic and in-memory. No persistent store,
model, network, reindex, or filesystem mutation is used.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from holo_index.core.collection_search import CollectionSearchOps, search_collection
from holo_index.core.search_engine import (
    _inject_module_tier0_candidates,
    _search_collection,
)
from holo_index.tier0_retrieval import (
    TIER0_REQUIRED_DOCS,
    infer_explicit_module_target,
    module_path_from_hit,
    module_tier0_paths,
)


MODULE = "modules/communication/moltbot_bridge"


@pytest.mark.parametrize("limit", [0, -1])
def test_nonpositive_limit_returns_empty_without_touching_backend(limit: int) -> None:
    class Untouchable:
        def __getattribute__(self, name):
            raise AssertionError(f"backend touched for nonpositive limit: {name}")

    ops = CollectionSearchOps(
        strict_owner=lambda _holo: False,
        lexical_search=lambda *_args, **_kwargs: pytest.fail("lexical backend touched"),
        run_with_timeout=lambda *_args, **_kwargs: pytest.fail("timeout backend touched"),
        resolve_alias_wsps=lambda _query: [], extract_wsp_numbers=lambda _query: [],
        score_result=lambda *_args, **_kwargs: pytest.fail("scorer touched"),
        encode_timeout=1.0,
    )
    assert search_collection(
        Untouchable(), Untouchable(), "unused", limit, "code", "", None, ops
    ) == []


def _hit(path: str) -> dict[str, str]:
    return {"path": path, "similarity": "60.0%"}


@dataclass
class _ExactPathCollection:
    rows: dict[str, tuple[str, dict[str, object]]]
    calls: list[tuple[dict[str, str], tuple[str, ...]]] = field(default_factory=list)
    name: str = "navigation_docs"

    def count(self):
        return len(self.rows) + 1

    def query(self, *, query_embeddings, n_results):
        assert query_embeddings == [[0.1, 0.2]]
        assert n_results > 0
        return {
            "documents": [["test readme"]],
            "metadatas": [[
                {
                    "path": f"{MODULE}/tests/README.md",
                    "title": "Tests",
                    "type": "readme",
                    "priority": 4.0,
                }
            ]],
            "distances": [[0.1]],
        }

    def get(self, *, where, include):
        self.calls.append((dict(where), tuple(include)))
        path = where.get("path")
        row = self.rows.get(path)
        if row is None:
            return {"ids": [], "documents": [], "metadatas": []}
        document, metadata = row
        return {
            "ids": [path],
            "documents": [document],
            "metadatas": [dict(metadata)],
        }


def test_tier0_contract_matches_bundle_required_order() -> None:
    assert TIER0_REQUIRED_DOCS == ("README.md", "INTERFACE.md")
    assert module_tier0_paths(MODULE) == (
        f"{MODULE}/README.md",
        f"{MODULE}/INTERFACE.md",
    )


@pytest.mark.parametrize(
    "module_path",
    [
        "modules/../moltbot_bridge",
        "modules/communication/..",
        "modules/./moltbot_bridge",
        "modules/communication/.hidden",
        "modules/communication/moltbot bridge",
        "modules/communication/moltbot_bridge.",
    ],
)
def test_tier0_paths_reject_invalid_components(module_path: str) -> None:
    assert module_tier0_paths(module_path) == ()


def test_explicit_unique_module_is_inferred_from_returned_paths() -> None:
    hits = [
        _hit(f"{MODULE}/src/worker.py"),
        _hit(f"{MODULE}/tests/test_worker.py"),
        _hit("modules/infrastructure/foundups_mcp_bridge/src/owner.py"),
    ]
    assert (
        infer_explicit_module_target(
            "RedDog moltbot_bridge worker supervisor Hermes verifier", hits
        )
        == MODULE
    )
    assert (
        infer_explicit_module_target(
            "modules/communication/moltbot_bridge architecture", hits
        )
        == MODULE
    )


def test_no_explicit_or_ambiguous_module_returns_none() -> None:
    hits = [
        _hit(f"{MODULE}/src/worker.py"),
        _hit("modules/platform_integration/moltbot_bridge/src/worker.py"),
    ]
    assert infer_explicit_module_target("worker supervisor", hits) is None
    assert infer_explicit_module_target("moltbot_bridge worker", hits) is None


def test_full_module_path_has_precedence_over_ambiguous_basenames() -> None:
    platform_module = "modules/platform_integration/moltbot_bridge"
    hits = [_hit(f"{MODULE}/src/worker.py"), _hit(f"{platform_module}/src/worker.py")]

    assert infer_explicit_module_target(
        f"audit {MODULE} and its worker", hits
    ) == MODULE
    assert infer_explicit_module_target(
        f"audit {platform_module} and its worker", hits
    ) == platform_module
    assert infer_explicit_module_target(f"audit {MODULE}", []) == MODULE
    assert (
        infer_explicit_module_target(
            "audit MODULES/COMMUNICATION/MOLTBOT_BRIDGE", []
        )
        == MODULE
    )


def test_module_intent_uses_exact_boundaries_and_anchored_hit_paths() -> None:
    bridge = "modules/communication/bridge"
    bridgework = "modules/communication/bridgework"
    hits = [_hit(f"{bridge}/src/worker.py"), _hit(f"{bridgework}/src/worker.py")]

    assert infer_explicit_module_target("audit bridgework", hits) == bridgework
    assert infer_explicit_module_target("audit bridge worker", hits) == bridge
    assert module_path_from_hit(
        _hit(f"outside/prefix/{MODULE}/src/worker.py")
    ) == ""


def test_module_intent_rejects_unbounded_or_invalid_resources() -> None:
    assert infer_explicit_module_target("x" * 4097, [_hit(f"{MODULE}/README.md")]) is None
    assert infer_explicit_module_target(
        "modules/communication/.hidden audit", []
    ) is None
    oversized = "a" * 129
    assert infer_explicit_module_target(
        f"modules/communication/{oversized} audit", []
    ) is None


def test_exact_metadata_lookup_adds_only_root_tier0_rows() -> None:
    collection = _ExactPathCollection(
        rows={
            f"{MODULE}/README.md": (
                "module readme",
                {
                    "path": f"{MODULE}/README.md",
                    "title": "Moltbot Bridge",
                    "type": "module_readme",
                    "priority": 8.0,
                },
            ),
            f"{MODULE}/INTERFACE.md": (
                "module interface",
                {
                    "path": f"{MODULE}/INTERFACE.md",
                    "title": "Moltbot Bridge Interface",
                    "type": "interface",
                    "priority": 9.0,
                },
            ),
            f"{MODULE}/tests/README.md": (
                "test readme",
                {
                    "path": f"{MODULE}/tests/README.md",
                    "title": "Tests",
                    "type": "readme",
                    "priority": 4.0,
                },
            ),
        }
    )
    docs = ["test readme"]
    metas = [{"path": f"{MODULE}/tests/README.md", "type": "readme"}]
    dists = [0.1]

    _inject_module_tier0_candidates(collection, docs, metas, dists, MODULE)

    assert [call[0] for call in collection.calls] == [
        {"path": f"{MODULE}/README.md"},
        {"path": f"{MODULE}/INTERFACE.md"},
    ]
    assert all(call[1] == ("documents", "metadatas") for call in collection.calls)
    assert [meta["path"] for meta in metas] == [
        f"{MODULE}/tests/README.md",
        f"{MODULE}/README.md",
        f"{MODULE}/INTERFACE.md",
    ]
    assert len(docs) == len(metas) == len(dists) == 3


def test_exact_metadata_lookup_is_bounded_and_deduplicated() -> None:
    readme_path = f"{MODULE}/README.md"
    collection = _ExactPathCollection(
        rows={
            readme_path: (
                "duplicate",
                {"path": readme_path, "type": "module_readme", "priority": 8.0},
            )
        }
    )
    docs = ["existing"]
    metas = [{"path": readme_path, "type": "module_readme"}]
    dists = [0.1]

    _inject_module_tier0_candidates(collection, docs, metas, dists, MODULE)

    assert len(collection.calls) == 1
    assert collection.calls[0][0] == {"path": f"{MODULE}/INTERFACE.md"}
    assert [meta["path"] for meta in metas] == [readme_path]


def test_strict_owner_replaces_duplicate_vector_tier0_with_exact_rows() -> None:
    rows = {
        f"{MODULE}/README.md": (
            "exact readme",
            {"path": f"{MODULE}/README.md", "type": "module_readme"},
        ),
        f"{MODULE}/INTERFACE.md": (
            "exact interface",
            {"path": f"{MODULE}/INTERFACE.md", "type": "interface"},
        ),
    }
    docs = ["vector readme one", "vector readme two", "vector interface"]
    metas = [
        {"path": f"{MODULE}/README.md", "type": "module_readme"},
        {"path": f"{MODULE}/README.md", "type": "module_readme"},
        {"path": f"{MODULE}/INTERFACE.md", "type": "interface"},
    ]
    dists = [0.1, 0.2, 0.3]

    _inject_module_tier0_candidates(
        _ExactPathCollection(rows), docs, metas, dists, MODULE, strict=True
    )

    assert [meta["path"] for meta in metas] == [
        f"{MODULE}/README.md",
        f"{MODULE}/INTERFACE.md",
    ]
    assert docs == ["exact readme", "exact interface"]
    assert dists == [None, None]
    assert all(meta["_retrieval_provenance"] == "exact_metadata" for meta in metas)


@pytest.mark.parametrize(
    "failure",
    ["get_failure", "malformed_cardinality", "path_mismatch"],
)
def test_strict_owner_rejects_untrusted_exact_lookup_results(failure: str) -> None:
    class _AdversarialCollection:
        def get(self, *, where, include):
            assert include == ["documents", "metadatas"]
            if failure == "get_failure":
                raise OSError("collection unavailable")
            if failure == "malformed_cardinality":
                return {
                    "documents": ["one", "two"],
                    "metadatas": [{"path": where["path"]}],
                }
            return {
                "documents": ["wrong row"],
                "metadatas": [{"path": f"{MODULE}/tests/README.md"}],
            }

    with pytest.raises(RuntimeError, match="HOLOINDEX_STRICT_TIER0_LOOKUP_FAILED"):
        _inject_module_tier0_candidates(
            _AdversarialCollection(), [], [], [], MODULE, strict=True
        )


@pytest.mark.parametrize("present", [(), ("README.md",)])
def test_strict_owner_rejects_incomplete_tier0_contract(
    present: tuple[str, ...],
) -> None:
    rows = {
        f"{MODULE}/{name}": (
            name,
            {
                "path": f"{MODULE}/{name}",
                "type": "module_readme" if name == "README.md" else "interface",
                "priority": 8.0,
            },
        )
        for name in present
    }

    with pytest.raises(RuntimeError, match="HOLOINDEX_STRICT_TIER0_INCOMPLETE"):
        _inject_module_tier0_candidates(
            _ExactPathCollection(rows), [], [], [], MODULE, strict=True
        )


def test_non_strict_lookup_failure_degrades_without_injection() -> None:
    class _UnavailableCollection:
        @staticmethod
        def get(**_kwargs):
            raise OSError("collection unavailable")

    docs = ["existing"]
    metas = [{"path": f"{MODULE}/tests/README.md"}]
    dists = [0.1]

    missing = _inject_module_tier0_candidates(
        _UnavailableCollection(), docs, metas, dists, MODULE, strict=False
    )

    assert docs == ["existing"]
    assert metas == [{"path": f"{MODULE}/tests/README.md"}]
    assert dists == [0.1]
    assert missing == module_tier0_paths(MODULE)


def test_non_strict_exact_lookup_exception_reaches_warning_surface() -> None:
    class _UnavailableCollection(_ExactPathCollection):
        def get(self, **_kwargs):
            raise OSError("collection unavailable")

    logged: list[tuple[str, str]] = []

    class _Embedding(list):
        def tolist(self):
            return list(self)

    class _Model:
        @staticmethod
        def encode(_query, *, show_progress_bar):
            assert show_progress_bar is False
            return _Embedding([0.1, 0.2])

    class _Holo:
        model = _Model()
        embedders = None
        routing_active = False
        strict_semantic_owner = False

        @staticmethod
        def _log_agent_action(message, level="INFO"):
            logged.append((message, level))

    _search_collection(
        _Holo(), _UnavailableCollection({}), "moltbot_bridge docs", 5, "docs",
        module_path_hint=MODULE,
    )

    assert logged == [(
        "Tier-0 module evidence incomplete: " + ", ".join(module_tier0_paths(MODULE)),
        "WARN",
    )]


def _function_sizes(source_path: Path) -> dict[str, int]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    return {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_vector_search_obeys_wsp62_hard_limits() -> None:
    source_path = Path(__file__).parents[1] / "core" / "search_engine.py"
    source = source_path.read_text(encoding="utf-8")
    assert len(source.splitlines()) < 1500
    search_sizes = _function_sizes(source_path)
    assert search_sizes["_search_collection"] <= 50
    assert search_sizes["_token_keyword_score"] <= 50
    assert search_sizes["_vector_result"] <= 50
    assert search_sizes["_vector_search_ops"] <= 50
    for helper in ("collection_search.py", "collection_injections.py"):
        assert max(_function_sizes(source_path.with_name(helper)).values()) <= 50


def test_search_collection_returns_tier0_before_nested_test_readme() -> None:
    collection = _ExactPathCollection(
        rows={
            f"{MODULE}/README.md": (
                "module readme",
                {
                    "path": f"{MODULE}/README.md",
                    "title": "Moltbot Bridge",
                    "summary": "Module contract",
                    "type": "module_readme",
                    "priority": 8.0,
                },
            ),
            f"{MODULE}/INTERFACE.md": (
                "module interface",
                {
                    "path": f"{MODULE}/INTERFACE.md",
                    "title": "Moltbot Bridge Interface",
                    "summary": "Public contract",
                    "type": "interface",
                    "priority": 9.0,
                },
            ),
        }
    )

    class _Embedding(list):
        def tolist(self):
            return list(self)

    class _Model:
        def encode(self, query, *, show_progress_bar):
            assert query == "moltbot_bridge worker"
            assert show_progress_bar is False
            return _Embedding([0.1, 0.2])

    class _Holo:
        model = _Model()
        embedders = None
        routing_active = False
        strict_semantic_owner = True

        @staticmethod
        def _log_agent_action(*_args, **_kwargs):
            return None

    hits = _search_collection(
        _Holo(),
        collection,
        "moltbot_bridge worker",
        5,
        "docs",
        module_path_hint=MODULE,
    )

    assert [hit["path"] for hit in hits] == [
        f"{MODULE}/README.md",
        f"{MODULE}/INTERFACE.md",
        f"{MODULE}/tests/README.md",
    ]


def test_docs_only_search_infers_module_from_initial_docs_metadata() -> None:
    collection = _ExactPathCollection(
        rows={
            f"{MODULE}/README.md": (
                "module readme",
                {
                    "path": f"{MODULE}/README.md",
                    "title": "Moltbot Bridge",
                    "summary": "Module contract",
                    "type": "module_readme",
                    "priority": 8.0,
                },
            ),
            f"{MODULE}/INTERFACE.md": (
                "module interface",
                {
                    "path": f"{MODULE}/INTERFACE.md",
                    "title": "Moltbot Bridge Interface",
                    "summary": "Public contract",
                    "type": "interface",
                    "priority": 9.0,
                },
            ),
        }
    )

    class _Embedding(list):
        def tolist(self):
            return list(self)

    class _Model:
        def encode(self, query, *, show_progress_bar):
            assert query == "moltbot_bridge docs"
            assert show_progress_bar is False
            return _Embedding([0.1, 0.2])

    class _Holo:
        model = _Model()
        embedders = None
        routing_active = False
        strict_semantic_owner = True

        @staticmethod
        def _log_agent_action(*_args, **_kwargs):
            return None

    hits = _search_collection(
        _Holo(), collection, "moltbot_bridge docs", 5, "docs"
    )

    assert [hit["path"] for hit in hits[:2]] == [
        f"{MODULE}/README.md",
        f"{MODULE}/INTERFACE.md",
    ]


def test_exact_metadata_rows_have_truthful_provenance_and_ignore_vector_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOLO_MIN_SIMILARITY", "0.50")
    collection = _ExactPathCollection(
        rows={
            f"{MODULE}/README.md": (
                "module readme",
                {
                    "path": f"{MODULE}/README.md",
                    "title": "Moltbot Bridge",
                    "summary": "Module contract",
                    "type": "module_readme",
                    "priority": 8.0,
                },
            ),
            f"{MODULE}/INTERFACE.md": (
                "module interface",
                {
                    "path": f"{MODULE}/INTERFACE.md",
                    "title": "Moltbot Bridge Interface",
                    "summary": "Public contract",
                    "type": "interface",
                    "priority": 9.0,
                },
            ),
        }
    )

    class _Embedding(list):
        def tolist(self):
            return list(self)

    class _Model:
        @staticmethod
        def encode(_query, *, show_progress_bar):
            assert show_progress_bar is False
            return _Embedding([0.1, 0.2])

    class _Holo:
        model = _Model()
        embedders = None
        routing_active = False
        strict_semantic_owner = True

        @staticmethod
        def _log_agent_action(*_args, **_kwargs):
            return None

    hits = _search_collection(
        _Holo(), collection, "moltbot_bridge docs", 5, "docs",
        module_path_hint=MODULE,
    )
    exact = hits[:2]

    assert [hit["path"] for hit in exact] == [
        f"{MODULE}/README.md",
        f"{MODULE}/INTERFACE.md",
    ]
    assert all(hit["similarity"] is None for hit in exact)
    assert all(hit["retrieval_provenance"] == "exact_metadata" for hit in exact)


def test_non_strict_search_reports_incomplete_tier0_through_warning_surface() -> None:
    collection = _ExactPathCollection(rows={})
    logged: list[tuple[str, str]] = []

    class _Embedding(list):
        def tolist(self):
            return list(self)

    class _Model:
        @staticmethod
        def encode(_query, *, show_progress_bar):
            assert show_progress_bar is False
            return _Embedding([0.1, 0.2])

    class _Holo:
        model = _Model()
        embedders = None
        routing_active = False
        strict_semantic_owner = False

        @staticmethod
        def _log_agent_action(message, level="INFO"):
            logged.append((message, level))

    hits = _search_collection(
        _Holo(), collection, "moltbot_bridge docs", 5, "docs",
        module_path_hint=MODULE,
    )

    assert [hit["path"] for hit in hits] == [f"{MODULE}/tests/README.md"]
    assert logged == [(
        "Tier-0 module evidence incomplete: "
        f"{MODULE}/README.md, {MODULE}/INTERFACE.md",
        "WARN",
    )]
