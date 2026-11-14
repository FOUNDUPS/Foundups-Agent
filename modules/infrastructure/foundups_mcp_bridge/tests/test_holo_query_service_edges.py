"""Fail-closed edge coverage for the HoloIndex owner core."""

from __future__ import annotations

import ast
from concurrent.futures import TimeoutError as FutureTimeoutError
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service as core,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_response import (
    normalize_result_paths,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_path_projection import (
    project_repository_location,
    project_repository_path,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    QUERY,
    SHA,
    TOKEN,
    _Backend,
    _query,
    _raw_result,
    _receipt,
    _service,
)


_ALIASES = {
    "code_hits": "code", "wsp_hits": "wsps", "test_hits": "tests",
    "skill_hits": "skills", "docs_hits": "docs",
    "knowledge_hits": "knowledge", "work_ledger_hits": "work_ledger",
}


def _canonical_with(bucket: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    raw = deepcopy(dict(_raw_result()))
    raw[bucket] = hits
    if alias := _ALIASES.get(bucket):
        raw[alias] = hits
    metadata = dict(raw["metadata"])
    metadata[bucket.removesuffix("_hits") + "_count"] = len(hits)
    raw["metadata"] = metadata
    return raw


def _normalize(raw: dict[str, Any], root: str = r"E:\Agents\root") -> dict[str, Any]:
    return normalize_result_paths(raw, root, expected_query=QUERY)


def _changed_hit(bucket: str, **changes: Any) -> dict[str, Any]:
    raw = deepcopy(dict(_raw_result()))
    hit = dict(raw[bucket][0])
    hit.update(changes)
    return _canonical_with(bucket, [hit])


@pytest.mark.parametrize(
    "overrides",
    [
        {"query_timeout_seconds": 0},
        {"query_timeout_seconds": float("nan")},
        {"query_timeout_seconds": float("inf")},
        {"startup_warmup_timeout_seconds": 301},
        {"startup_warmup_timeout_seconds": float("nan")},
        {"startup_warmup_timeout_seconds": float("inf")},
        {"max_query_chars": 0},
        {"max_limit": 51},
    ],
)
def test_constructor_rejects_unsafe_bounds(
    tmp_path: Path,
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        core.HoloIndexQueryOwnerService(
            repo_root=tmp_path,
            ssd_path=tmp_path / "store",
            **overrides,
        )


def test_malformed_receipt_and_evaluator_failure_are_truthful(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def malformed(_path: Path) -> Any:
        raise ValueError("bad receipt")

    owner = _service(tmp_path, monkeypatch, receipt_loader=malformed)
    try:
        result = _query(owner)
        assert result["stale_reasons"] == ["malformed_freshness_receipt"]
    finally:
        owner.close()

    def evaluator_failure(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("evaluation unavailable")

    owner = _service(
        tmp_path,
        monkeypatch,
        freshness_evaluator=evaluator_failure,
    )
    try:
        reasons = _query(owner)["stale_reasons"]
        assert reasons == [
            "freshness_evaluation_failed",
            "baseline_collection_proof_incomplete",
        ]
    finally:
        owner.close()


def test_backend_exception_and_post_query_staleness_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RaisingBackend(_Backend):
        def search(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("backend failed")

    owner = _service(tmp_path, monkeypatch, backend=RaisingBackend())
    try:
        assert _query(owner)["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    finally:
        owner.close()

    receipts = iter(
        [_receipt(), _receipt(omit="navigation_knowledge")]
    )
    owner = _service(
        tmp_path,
        monkeypatch,
        receipt_loader=lambda _path: next(receipts),
    )
    try:
        result = _query(owner)
        assert result["error"] == "STALE_INDEX"
        assert (
            "missing_collection_receipt:navigation_knowledge"
            in result["stale_reasons"]
        )
        assert result["raw_result"] == {}
        assert result["hits"] == []
    finally:
        owner.close()


def _assert_unknown_timeout_and_poisoned_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(
        tmp_path,
        monkeypatch,
        repository_state_reader=lambda _root: SimpleNamespace(
            proven_clean=False,
            head_sha="",
            error="HEALTH_UNAVAILABLE",
        ),
    )
    try:
        unknown = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert unknown["error"] == "HEALTH_UNAVAILABLE"
        owner._repository_state_reader = lambda _root: SimpleNamespace(
            proven_clean=True,
            head_sha=SHA,
            error="",
        )

        def timeout(*_args, **_kwargs):
            owner._poisoned.set()
            raise FutureTimeoutError()

        monkeypatch.setattr(owner, "_run", timeout)
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "QUERY_TIMEOUT"
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "QUERY_OWNER_POISONED"
    finally:
        owner.close()


def _assert_backend_failure_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(tmp_path, monkeypatch)
    try:
        monkeypatch.setattr(
            owner,
            "_search",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("backend")),
        )
        assert owner.handle_health(
            authorization=f"Bearer {TOKEN}"
        )["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    finally:
        owner.close()


def _assert_stale_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _service(
        tmp_path,
        monkeypatch,
        receipt_loader=lambda _path: _receipt(omit="navigation_docs"),
    )
    try:
        stale = owner.handle_health(authorization=f"Bearer {TOKEN}")
        assert stale["error"] == "STALE_INDEX"
    finally:
        owner.close()


def test_health_reports_unknown_stale_timeout_and_backend_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_unknown_timeout_and_poisoned_health(tmp_path, monkeypatch)
    _assert_backend_failure_health(tmp_path, monkeypatch)
    _assert_stale_health(tmp_path, monkeypatch)


def test_internal_normalizers_reject_bad_payloads_and_dedupe_hits() -> None:
    request_args = {
        "request_size": None,
        "max_request_bytes": 100,
        "max_query_chars": 20,
        "max_limit": 8,
    }
    assert core._validate_payload([], **request_args)[1] == "INVALID_REQUEST"
    unserializable = {"query": object()}
    assert core._validate_payload(
        unserializable,
        **request_args,
    )[1] == "INVALID_REQUEST"
    assert core._validate_payload(
        {"query": "x"},
        request_size=None,
        max_request_bytes=1,
        max_query_chars=20,
        max_limit=8,
    )[1] == "REQUEST_TOO_LARGE"
    hits = core._flatten_hits(
        {
            "code_hits": [
                "bad",
                {"path": "same.py"},
                {"path": "same.py"},
                {"path": "SAME.py"},
                {"name": "pathless"},
            ]
        },
        10,
    )
    assert len(hits) == 2
    assert core._flatten_hits({"code_hits": [{"path": "one.py"}]}, 1)
    assert core._flatten_hits({"code_hits": [{"path": "one.py"}]}, 0) == []


def test_flatten_hits_uses_global_score_across_typed_buckets() -> None:
    hits = core._flatten_hits(
        {
            "code_hits": [
                {"path": "low.py", "similarity": "10.0%"},
                {"path": "same.py", "similarity": "20.0%"},
            ],
            "wsp_hits": [
                {"path": "WSP_framework/src/high.md", "similarity": "95.0%"},
                {"path": "same.py", "similarity": "90.0%"},
            ],
        },
        3,
    )
    assert [item["path"] for item in hits] == [
        "WSP_framework/src/high.md",
        "same.py",
        "low.py",
    ]
    assert hits[1]["type"] == "wsp"


def test_flatten_hits_preserves_producer_rank_within_typed_stream() -> None:
    hits = core._flatten_hits(
        {
            "code_hits": [
                {"path": "exact-symbol.py", "similarity": "50.6%"},
                {"path": "semantic-neighbor.py", "similarity": "51.0%"},
            ],
            "skill_hits": [
                {"path": "skill.md", "similarity": "49.0%"},
            ],
        },
        3,
    )

    assert [item["path"] for item in hits] == [
        "exact-symbol.py",
        "semantic-neighbor.py",
        "skill.md",
    ]


def test_flatten_hits_current_status_prefers_current_contract_over_history() -> None:
    hits = core._flatten_hits(
        {
            "docs_hits": [
                {
                    "path": "docs/audits/holoindex_search_quality/OLD_REPORT.md",
                    "similarity": "99.0%",
                    "type": "documentation",
                },
                {
                    "path": "holo_index/README.md",
                    "similarity": "41.0%",
                    "type": "module_readme",
                },
            ],
            "symbol_hits": [
                {
                    "path": "holo_index/retrieval_autoresearch.py",
                    "similarity": "90.0%",
                    "type": "symbol",
                },
            ],
        },
        3,
        query="Is HoloIndex RSI working and what is currently missing?",
    )

    assert [item["path"] for item in hits] == [
        "holo_index/README.md",
        "holo_index/retrieval_autoresearch.py",
        "docs/audits/holoindex_search_quality/OLD_REPORT.md",
    ]


def test_flatten_hits_historical_baseline_preserves_similarity_order() -> None:
    hits = core._flatten_hits(
        {
            "docs_hits": [
                {
                    "path": "docs/audits/holoindex_search_quality/BASELINE.md",
                    "similarity": "99.0%",
                    "type": "documentation",
                },
                {
                    "path": "holo_index/README.md",
                    "similarity": "41.0%",
                    "type": "module_readme",
                },
            ],
        },
        2,
        query="historical HoloIndex retrieval baseline",
    )

    assert hits[0]["path"].endswith("BASELINE.md")


def test_flatten_hits_reserves_exact_module_root_tier0_for_explicit_module() -> None:
    module = "modules/communication/moltbot_bridge"
    hits = core._flatten_hits(
        {
            "metadata": {"tier0_module_target": module},
            "symbol_hits": [
                {"path": f"{module}/src/worker.py", "similarity": "95.0%"},
            ],
            "test_hits": [
                {"path": f"{module}/tests/test_worker.py", "similarity": "90.0%"},
            ],
            "docs_hits": [
                {"path": f"{module}/tests/README.md", "similarity": "99.0%"},
                {
                    "path": f"{module}/INTERFACE.md", "similarity": None,
                    "retrieval_provenance": "exact_metadata",
                },
                {
                    "path": f"{module}/README.md", "similarity": None,
                    "retrieval_provenance": "exact_metadata",
                },
            ],
        },
        4,
        query="RedDog moltbot_bridge worker architecture",
    )
    assert [item["path"] for item in hits] == [
        f"{module}/README.md",
        f"{module}/INTERFACE.md",
        f"{module}/tests/README.md",
        f"{module}/src/worker.py",
    ]


@pytest.mark.parametrize(
    ("limit", "expected"),
    [
        (1, ["README.md"]),
        (2, ["README.md", "INTERFACE.md"]),
        (3, ["README.md", "INTERFACE.md", "worker.py"]),
    ],
)
def test_flatten_hits_tier0_reservation_is_bounded_at_low_k(
    limit: int, expected: list[str]
) -> None:
    module = "modules/communication/example_bridge"
    hits = core._flatten_hits(
        {
            "metadata": {"tier0_module_target": module},
            "code_hits": [
                {"path": f"{module}/src/worker.py", "similarity": "95.0%"},
            ],
            "docs_hits": [
                {
                    "path": f"{module}/INTERFACE.md", "similarity": None,
                    "retrieval_provenance": "exact_metadata",
                },
                {
                    "path": f"{module}/README.md", "similarity": None,
                    "retrieval_provenance": "exact_metadata",
                },
            ],
        },
        limit,
        query="example_bridge worker",
    )
    assert [item["path"].rsplit("/", 1)[-1] for item in hits] == expected


def test_flatten_hits_does_not_promote_hit_conditioned_unproven_tier0() -> None:
    hits = core._flatten_hits(
        {
            "code_hits": [
                {
                    "path": "modules/communication/example/src/high.py",
                    "similarity": "95.0%",
                },
            ],
            "docs_hits": [
                {
                    "path": "modules/communication/example/README.md",
                    "similarity": "41.0%",
                },
            ],
        },
        2,
        query=(
            "HoloDAE PQN training system UTF8 hygiene MCP testing unicode "
            "tools example Tier0 contracts"
        ),
    )
    assert [item["path"].rsplit("/", 1)[-1] for item in hits] == [
        "high.py",
        "README.md",
    ]


@pytest.mark.parametrize(
    ("metadata", "query", "extra"),
    [
        ({}, "example_bridge worker", []),
        (
            {"tier0_module_target": "modules/communication/example_bridge"},
            "unrelated worker query",
            [],
        ),
        (
            {"tier0_module_target": "modules/communication/forged_bridge"},
            "example_bridge worker",
            [],
        ),
        (
            {"tier0_module_target": "modules/communication/example_bridge"},
            "example_bridge and other_bridge workers",
            [{
                "path": "modules/communication/other_bridge/src/worker.py",
                "similarity": "94.0%",
            }],
        ),
    ],
)
def test_flatten_hits_requires_matching_attestation_and_query_intent(
    metadata: dict[str, object], query: str, extra: list[dict[str, object]],
) -> None:
    module = "modules/communication/example_bridge"
    result = {
        "metadata": metadata,
        "code_hits": [
            {"path": "high.py", "similarity": "99.0%"},
            *extra,
        ],
        "docs_hits": [
            {
                "path": f"{module}/README.md", "similarity": None,
                "retrieval_provenance": "exact_metadata",
            },
            {
                "path": f"{module}/INTERFACE.md", "similarity": None,
                "retrieval_provenance": "exact_metadata",
            },
        ],
    }

    hits = core._flatten_hits(result, 5, query=query)

    assert hits[0]["path"] == "high.py"


@pytest.mark.parametrize(
    "docs",
    [
        [
            {"path": "modules/a/one/README.md", "similarity": "41.0%",
             "retrieval_provenance": "exact_metadata"},
        ],
        [
            {"path": "modules/a/one/README.md", "similarity": "41.0%",
             "retrieval_provenance": "exact_metadata"},
            {"path": "modules/b/two/INTERFACE.md", "similarity": "42.0%",
             "retrieval_provenance": "exact_metadata"},
        ],
        [
            {"path": "modules/a/one/README.md", "similarity": "41.0%",
             "retrieval_provenance": "exact_metadata"},
            {"path": "modules/a/one/README.md", "similarity": "40.0%",
             "retrieval_provenance": "exact_metadata"},
            {"path": "modules/a/one/INTERFACE.md", "similarity": "42.0%",
             "retrieval_provenance": "exact_metadata"},
        ],
    ],
)
def test_flatten_hits_rejects_partial_mixed_or_duplicate_attested_pairs(
    docs: list[dict[str, object]],
) -> None:
    hits = core._flatten_hits(
        {
            "code_hits": [{"path": "high.py", "similarity": "95.0%"}],
            "docs_hits": docs,
        },
        5,
        query="audit one two",
    )

    assert hits[0]["path"] == "high.py"


def test_success_projects_physical_result_paths_before_receipt_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = deepcopy(dict(_raw_result()))
    docs = dict(raw["docs_hits"][0])
    docs["path"] = str(tmp_path / "docs" / "README.md")
    code = dict(raw["code_hits"][0])
    code.update(path=str(tmp_path / "module.py"), location="module.py:example()")
    raw["docs_hits"] = raw["docs"] = [docs]
    raw["code_hits"] = raw["code"] = [code]
    owner = _service(tmp_path, monkeypatch, backend=_Backend(raw))
    try:
        result = _query(owner)
    finally:
        owner.close()
    assert result["ok"] is True
    assert result["raw_result"]["docs_hits"][0]["path"] == "docs/README.md"
    assert result["raw_result"]["docs"][0]["path"] == "docs/README.md"
    assert result["raw_result"]["code_hits"][0]["path"] == "module.py"
    projected_hits = {
        hit.get("path") or hit.get("file") for hit in result["hits"]
    }
    assert {"docs/README.md", "module.py"} <= projected_hits
    assert not any(Path(str(path)).is_absolute() for path in projected_hits)


def test_absolute_result_path_outside_repository_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = deepcopy(dict(_raw_result()))
    docs = dict(raw["docs_hits"][0])
    docs["path"] = str(tmp_path.parent / "outside.md")
    raw["docs_hits"] = raw["docs"] = [docs]
    owner = _service(tmp_path, monkeypatch, backend=_Backend(raw))
    try:
        result = _query(owner)
    finally:
        owner.close()
    assert result["ok"] is False
    assert result["error"] == "QUERY_EVIDENCE_PATH_OUTSIDE_REPOSITORY"
    assert result["hits"] == []
    assert result["raw_result"] == {}


def test_relative_result_path_traversal_fails_closed() -> None:
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        _normalize(_changed_hit("docs_hits", path="../outside.md"), str(Path("repo").resolve()))


def test_windows_authority_path_projects_cross_platform() -> None:
    result = _normalize(
        _changed_hit(
            "code_hits", path=r"E:\Agents\root\module.py", location="module.py:example()"
        )
    )
    assert result["code_hits"][0]["path"] == "module.py"


@pytest.mark.parametrize(
    "candidate",
    ["/etc/passwd", r"\rooted\escape.txt", r"C:drive-relative\escape.txt"],
)
def test_foreign_or_qualified_path_forms_fail_closed(candidate: str) -> None:
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_path(candidate, r"E:\Agents\root")


def test_posix_authority_path_projects_without_host_path_semantics() -> None:
    assert project_repository_path("/srv/repo/docs/a.md", "/srv/repo") == "docs/a.md"
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_path("/srv/other/a.md", "/srv/repo")


@pytest.mark.parametrize("root", ["repo", r"\rooted"])
def test_repository_root_must_be_fully_qualified(root: str) -> None:
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_path("docs/a.md", root)


def test_backend_aliases_and_location_are_projected() -> None:
    test_hit = {
        "test_id": "test_a", "path": r"E:\Agents\root\tests\test_a.py",
        "description": "test", "capabilities": "unit", "similarity": "80.0%",
        "type": "test", "priority": 3,
    }
    skill_hit = {
        "skill_name": "a", "description": "skill", "primary_agent": "0102",
        "intent_type": "implementation", "promotion_state": "promoted",
        "path": r"E:\Agents\root\skillz\a\SKILLz.md", "similarity": "80.0%",
        "type": "skillz", "priority": 3,
    }
    raw = deepcopy(dict(_raw_result()))
    code_hit = dict(raw["code_hits"][0])
    code_hit.update(path=r"E:\Agents\root\modules\a.py", location="modules/a.py:Agent.run()")
    for bucket, alias, hits in (
        ("test_hits", "tests", [test_hit]),
        ("skill_hits", "skills", [skill_hit]),
        ("code_hits", "code", [code_hit]),
    ):
        raw[bucket] = raw[alias] = hits
    metadata = dict(raw["metadata"])
    metadata.update(test_count=1, skill_count=1, code_count=1)
    raw["metadata"] = metadata
    result = _normalize(raw)
    assert result["tests"][0]["path"] == "tests/test_a.py"
    assert result["skills"][0]["path"] == "skillz/a/SKILLz.md"
    assert result["code_hits"][0]["location"] == "modules/a.py:Agent.run()"


@pytest.mark.parametrize("invalid", [None, "", 7])
def test_malformed_path_values_fail_closed(invalid: object) -> None:
    with pytest.raises(ValueError, match="query_evidence_(?:schema|path)_invalid"):
        _normalize(_changed_hit("docs_hits", path=invalid))


@pytest.mark.parametrize(
    "candidate",
    [
        "docs/evil\x00.py",
        "docs/evil\n.py",
        "docs/evil\r.py",
        "docs/evil\x7f.py",
        "docs/file.txt:stream",
        "docs/NUL.txt",
        "docs/NUL .txt",
        "docs/trailing. ",
        "docs/wild*.py",
        "docs/trailing.py ",
        "docs/trailing.py\t",
        "docs/trailing.py\n",
        "docs/next-line.py\u0085",
        "docs/nonbreaking.py\u00a0",
        "docs/bidi-\u202eevil.py",
    ],
)
def test_malformed_or_ambiguous_windows_paths_fail_closed(candidate: str) -> None:
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_path(candidate, r"E:\Agents\root")


def test_posix_path_case_and_windows_case_rules_are_explicit() -> None:
    assert (
        project_repository_path(
            r"e:\agents\ROOT\Dir\b.py", r"E:\Agents\root"
        )
        == "Dir/b.py"
    )
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_path("/SRV/repo/a.py", "/srv/repo")
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_path(r"\srv\repo\a.py", "/srv/repo")


def test_location_descriptor_is_bound_to_projected_code_path() -> None:
    assert project_repository_location(
        "modules/a.py:Agent.run()",
        r"E:\Agents\root",
        expected_path="modules/a.py",
    ) == "modules/a.py:Agent.run()"
    assert project_repository_location(
        r"E:\Agents\root\modules\a.py:17", r"E:\Agents\root"
    ) == "modules/a.py:17"
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_location(
            "docs/a.txt:stream", r"E:\Agents\root", expected_path="docs/a.txt"
        )
    for candidate in ("docs/a.py:stream", "docs/a.md:stream"):
        with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
            project_repository_location(candidate, r"E:\Agents\root")
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_location(
            "modules/b.py:Agent.run()",
            r"E:\Agents\root",
            expected_path="modules/a.py",
        )


def test_navigation_annotations_are_removed_from_location_identity() -> None:
    assert project_repository_location(
        "modules/foundups/gotjunk/frontend/App.tsx:handleClassify() - "
        "isProcessingClassification guard",
        r"E:\Agents\root",
    ) == "modules/foundups/gotjunk/frontend/App.tsx:handleClassify()"
    assert project_repository_location(
        ".claude/skills/m2m/SKILL.md - /m2m skill commands",
        r"E:\Agents\root",
    ) == ".claude/skills/m2m/SKILL.md"
    assert project_repository_location(
        "modules/foundups/gotjunk/frontend/App.tsx:onClassify prop",
        r"E:\Agents\root",
    ) == "modules/foundups/gotjunk/frontend/App.tsx:onClassify()"
    assert project_repository_location(
        "modules/voice/index_channel.py:index_channel(channel_key, max_videos)",
        r"E:\Agents\root",
    ) == "modules/voice/index_channel.py:index_channel()"
    assert project_repository_location(
        "modules/foundups/agent_market/INTERFACE.md:FoundupRegistryService",
        r"E:\Agents\root",
    ) == "modules/foundups/agent_market/INTERFACE.md:FoundupRegistryService"


def test_canonical_navigation_location_corpus_remains_projectable() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    tree = ast.parse((repo_root / "NAVIGATION.py").read_text(encoding="utf-8"))
    candidates: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for value in node.values:
            try:
                candidate = ast.literal_eval(value)
            except (ValueError, TypeError):
                continue
            if isinstance(candidate, str) and "/" in candidate:
                candidates.append(candidate)
    assert len(candidates) >= 250 and all(project_repository_location(value, str(repo_root)) for value in candidates)


@pytest.mark.parametrize(
    "candidate",
    [
        "modules/a.py:run() - ",
        "modules/a.py:run() - annotation\ncommand",
        "modules/a.py:run()evil",
        "modules/a.py:run(arg)evil",
    ],
)
def test_malformed_navigation_annotations_fail_closed(candidate: str) -> None:
    with pytest.raises(ValueError, match="query_evidence_path_outside_repository"):
        project_repository_location(candidate, r"E:\Agents\root")


def test_unknown_backend_bucket_returns_no_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = dict(_raw_result())
    raw["unknown_hits"] = [{"path": str(tmp_path / "leak.py")}]
    owner = _service(tmp_path, monkeypatch, backend=_Backend(raw))
    try:
        result = _query(owner)
    finally:
        owner.close()
    assert result["ok"] is False
    assert result["error"] == "QUERY_EVIDENCE_INVALID"
    assert result["hits"] == []
    assert result["raw_result"] == {}


def test_normalized_result_does_not_alias_backend_evidence() -> None:
    raw = deepcopy(dict(_raw_result()))
    hit = raw["docs_hits"][0]
    backend_map = raw["metadata"]["collection_backend_map"]
    result = _normalize(raw)
    hit["path"] = "docs/changed.md"
    backend_map["navigation_code"] = "changed"
    assert result["docs_hits"][0]["path"] == "modules/example/README.md"
    assert result["docs_hits"][0]["summary"] == "module"
    assert result["docs"][0]["summary"] == "module"
    assert result["metadata"]["collection_backend_map"]["navigation_code"] == (
        "sentence_transformers"
    )


def test_uncopyable_backend_evidence_fails_with_truthful_reason() -> None:
    class _UncopyableMap(dict[str, str]):
        def __deepcopy__(self, _memo: object) -> object:
            raise TypeError("denied")

    raw = deepcopy(dict(_raw_result()))
    metadata = dict(raw["metadata"])
    metadata["collection_backend_map"] = _UncopyableMap(
        metadata["collection_backend_map"]
    )
    raw["metadata"] = metadata
    with pytest.raises(ValueError, match="query_evidence_copy_failed"):
        _normalize(raw)


def test_default_factory_and_transport_wrapper_delegate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from holo_index.core import holo_index as holo_module

    sentinel = object()
    monkeypatch.setattr(
        holo_module,
        "HoloIndex",
        lambda **_kwargs: sentinel,
    )
    assert core._default_backend_factory(tmp_path) is sentinel

    from modules.infrastructure.foundups_mcp_bridge.src import (
        holo_query_service_http,
    )

    monkeypatch.setattr(
        holo_query_service_http,
        "create_stdlib_server",
        lambda service, **kwargs: (service, kwargs),
    )
    service = object()
    assert core.create_stdlib_server(
        service,
        host="127.0.0.1",
        port=8127,
    ) == (service, {"host": "127.0.0.1", "port": 8127})
