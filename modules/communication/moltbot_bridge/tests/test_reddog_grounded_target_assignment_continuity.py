from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

import modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity as continuity
import modules.communication.moltbot_bridge.src.reddog_grounding_evidence_rehydration as evidence_rehydration
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    BOUNDED_SCHEMA_VERSION,
    SCHEMA_VERSION,
    canonical_digest,
    rehydrate_grounded_semantic_evidence,
    validate_grounded_target_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_iterative_retrieval import (
    MAX_TOTAL_GROUNDING_SECONDS,
    MAX_TOTAL_OWNER_QUERIES,
    TOTAL_READ_BUDGET_BYTES,
    run_bounded_iterative_retrieval,
    semantic_query_tokens,
)


FOCUS = "Audit pfmall architecture and tests."


def test_continuity_module_remains_wsp62_compliant() -> None:
    source = Path(continuity.__file__).read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 675
    tree = ast.parse(source)
    functions = (
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    assert all((node.end_lineno or node.lineno) - node.lineno + 1 <= 50 for node in functions)


def _receipt() -> dict:
    typed = {
        "repo_file_targets": [],
        "semantic_targets": [FOCUS],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": canonical_digest([]),
    }
    head = "c" * 40
    evidence = [
        {
            "path": "modules/foundups/pfmall/api.py",
            "digest": "sha256:" + "1" * 64,
            "bytes": 64,
            "category": "implementation",
            "truncated": False,
            "repo_head_sha": head,
            "git_mode": "100644",
            "blob_oid": "3" * 40,
        },
        {
            "path": "modules/foundups/pfmall/tests/test_api.py",
            "digest": "sha256:" + "2" * 64,
            "bytes": 64,
            "category": "verification",
            "truncated": False,
            "repo_head_sha": head,
            "git_mode": "100644",
            "blob_oid": "4" * 40,
        },
    ]
    coverage = [{
        "target": FOCUS,
        "verdict": "SUFFICIENT",
        "evidence_refs": [item["path"] for item in evidence],
        "evidence_records": evidence,
        "evidence_records_digest": canonical_digest({"evidence_records": evidence}),
        "read_rejections": [],
        "evidence_quality": {
            "required": True,
            "passed": True,
            "categories": ["implementation", "verification"],
            "target_tokens": semantic_query_tokens(FOCUS),
            "repository_state_bound": True,
        },
        "rejection_reasons": [],
    }]
    owner = {
        "ok": True,
        "freshness": "CURRENT",
        "index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
        "freshness_generation_id": "sha256:" + "a" * 64,
        "freshness_receipt_digest": "sha256:" + "b" * 64,
        "repo_head_sha": head,
        "repo_root_digest": "sha256:" + "e" * 64,
    }
    retrieval = run_bounded_iterative_retrieval(
        FOCUS,
        owner_query=lambda _query: owner,
        coverage_evaluator=lambda _target, _result: coverage[0],
    )
    traces = [dict(retrieval.receipt)]
    value = {
        "schema_version": BOUNDED_SCHEMA_VERSION,
        "source_surface": "editor_thin_client",
        "work_focus_digest": canonical_digest({"work_focus": FOCUS}),
        "typed_targets": typed,
        "typed_targets_digest": canonical_digest(typed),
        "grounding_preflight_applied": True,
        "grounding_preflight_passed": True,
        "grounding_preflight_rejection_reasons": [],
        "grounding_target_universe_required": True,
        "repo_file_targets_count": 0,
        "semantic_targets_count": 1,
        "external_research_targets_count": 0,
        "quoted_reference_blocks_count": 0,
        "semantic_target_coverage": coverage,
        "semantic_target_coverage_digest": canonical_digest({"semantic_target_coverage": coverage}),
        "semantic_retrieval_traces": traces,
        "semantic_retrieval_traces_digest": canonical_digest(
            {"semantic_retrieval_traces": traces}
        ),
        "semantic_owner_query_attempts_total": 1,
        "semantic_owner_query_budget": MAX_TOTAL_OWNER_QUERIES,
        "semantic_grounding_deadline_seconds": MAX_TOTAL_GROUNDING_SECONDS,
        "semantic_direct_read_attempts": [
            {"target": FOCUS, "path": item["path"], "bytes": item["bytes"], "reason": ""}
            for item in evidence
        ],
        "semantic_direct_read_attempts_digest": canonical_digest({
            "semantic_direct_read_attempts": [
                {"target": FOCUS, "path": item["path"], "bytes": item["bytes"], "reason": ""}
                for item in evidence
            ]
        }),
        "semantic_direct_read_bytes_total": sum(item["bytes"] for item in evidence),
        "semantic_direct_read_budget_bytes": TOTAL_READ_BUDGET_BYTES,
        "target_recall_ok": None,
        "required_targets_missing": [],
        "direct_read_paths": [],
        "semantic_direct_read_paths": [item["path"] for item in evidence],
        "repo_audit_fallback_used": False,
        "repo_audit_fallback": {},
        "repo_audit_fallback_digest": "",
        "repo_state_head_sha": head,
        "repo_state_root_digest": "sha256:" + "e" * 64,
        "holoindex_owner_query_ok": True,
        "holoindex_freshness": "CURRENT",
        "holoindex_generation_id": "sha256:" + "a" * 64,
        "holoindex_freshness_receipt_digest": "sha256:" + "b" * 64,
        "holoindex_repo_head_sha": head,
        "holoindex_repo_root_digest": "sha256:" + "e" * 64,
        "holoindex_query_receipt_id": "sha256:" + "d" * 64,
        "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
    }
    value["receipt_id"] = canonical_digest(value)
    return value


def _legacy_receipt() -> dict:
    value = deepcopy(_receipt())
    value["schema_version"] = SCHEMA_VERSION
    coverage = [{"target": FOCUS, "verdict": "SUFFICIENT"}]
    value["semantic_target_coverage"] = coverage
    value["semantic_target_coverage_digest"] = canonical_digest(
        {"semantic_target_coverage": coverage}
    )
    for key in (
        "semantic_retrieval_traces",
        "semantic_retrieval_traces_digest",
        "semantic_owner_query_attempts_total",
        "semantic_owner_query_budget",
        "semantic_grounding_deadline_seconds",
        "semantic_direct_read_paths",
        "holoindex_repo_root_digest",
        "repo_state_head_sha",
        "repo_state_root_digest",
    ):
        value.pop(key, None)
    _rehash_receipt(value)
    return value


def test_v2_receipt_requires_repository_state_root_binding() -> None:
    receipt = _receipt()
    receipt.pop("repo_state_root_digest")
    _rehash_receipt(receipt)

    result = validate_grounded_target_receipt(receipt, work_focus=FOCUS)

    assert result.accepted is False
    assert continuity.GroundingReason.REPO_STATE in result.rejection_reasons


def _rehash_receipt(value: dict) -> None:
    value["receipt_id"] = canonical_digest(
        {key: item for key, item in value.items() if key != "receipt_id"}
    )


def _rehash_v2(value: dict) -> None:
    coverage = value["semantic_target_coverage"]
    for item in coverage:
        records = item["evidence_records"]
        item["evidence_records_digest"] = canonical_digest({"evidence_records": records})
    value["semantic_target_coverage_digest"] = canonical_digest(
        {"semantic_target_coverage": coverage}
    )
    trace = value["semantic_retrieval_traces"][0]
    selected = trace["selected_round"]
    attempt = next(item for item in trace["attempts"] if item["round"] == selected)
    attempt["coverage_digest"] = canonical_digest(coverage[0])
    trace["receipt_id"] = canonical_digest(
        {key: item for key, item in trace.items() if key != "receipt_id"}
    )
    value["semantic_retrieval_traces_digest"] = canonical_digest(
        {"semantic_retrieval_traces": value["semantic_retrieval_traces"]}
    )
    _rehash_receipt(value)


def _semantic_records(value: dict) -> list[dict]:
    return [
        record
        for coverage in value["semantic_target_coverage"]
        for record in coverage["evidence_records"]
    ]


def _reader(records: list[dict]):
    by_path = {record["path"]: deepcopy(record) for record in records}

    def read(_root: Path, path: str, **_limits: int) -> dict:
        record = deepcopy(by_path[path])
        record["ok"] = True
        record["content"] = "pfmall architecture tests implementation verification"
        return record

    return read


def _bind_rehydration(monkeypatch: pytest.MonkeyPatch, value: dict) -> None:
    monkeypatch.setattr(evidence_rehydration, "repository_root_digest", lambda _root: "sha256:" + "e" * 64)
    monkeypatch.setattr(evidence_rehydration, "read_git_head_sha", lambda _root: "c" * 40)
    monkeypatch.setattr(evidence_rehydration, "secure_read_repo_head_file", _reader(_semantic_records(value)))


def test_valid_round_trip_is_accepted() -> None:
    result = validate_grounded_target_receipt(
        _receipt(), work_focus=FOCUS, expected_source_surface="editor_thin_client"
    )
    assert result.accepted is True
    assert result.verified is not None
    assert result.verified.semantic_targets == (FOCUS,)


def test_legacy_v1_metadata_fixture_remains_accepted() -> None:
    result = validate_grounded_target_receipt(
        _legacy_receipt(), work_focus=FOCUS, expected_source_surface="editor_thin_client"
    )
    assert result.accepted is True
    assert result.verified is not None
    assert result.verified.receipt["schema_version"] == SCHEMA_VERSION


@pytest.mark.parametrize("field", ["git_mode", "blob_oid"])
def test_v2_requires_git_object_binding(field: str) -> None:
    receipt = _receipt()
    receipt["semantic_target_coverage"][0]["evidence_records"][0].pop(field)
    _rehash_v2(receipt)
    result = validate_grounded_target_receipt(receipt, work_focus=FOCUS)
    assert result.accepted is False
    assert "grounding_semantic_coverage_invalid" in result.rejection_reasons


def test_valid_v2_evidence_rehydrates_from_exact_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _receipt()
    _bind_rehydration(monkeypatch, receipt)
    result = rehydrate_grounded_semantic_evidence(
        receipt, work_focus=FOCUS, repo_root=tmp_path
    )
    assert result.repo_head_sha == "c" * 40
    assert tuple(record.path for record in result.records) == (
        "modules/foundups/pfmall/api.py",
        "modules/foundups/pfmall/tests/test_api.py",
    )


def test_attacker_rehashed_duplicate_evidence_path_fails_rehydration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _receipt()
    duplicate = deepcopy(receipt["semantic_target_coverage"][0]["evidence_records"][0])
    receipt["semantic_target_coverage"][0]["evidence_records"].append(duplicate)
    receipt["semantic_target_coverage"][0]["evidence_refs"].append(duplicate["path"])
    duplicate_attempt = deepcopy(receipt["semantic_direct_read_attempts"][0])
    receipt["semantic_direct_read_attempts"].append(duplicate_attempt)
    receipt["semantic_direct_read_attempts_digest"] = canonical_digest(
        {"semantic_direct_read_attempts": receipt["semantic_direct_read_attempts"]}
    )
    receipt["semantic_direct_read_bytes_total"] += duplicate_attempt["bytes"]
    _rehash_v2(receipt)
    _bind_rehydration(monkeypatch, _receipt())

    with pytest.raises(ValueError, match="grounding_semantic_rehydration_evidence_mismatch"):
        rehydrate_grounded_semantic_evidence(receipt, work_focus=FOCUS, repo_root=tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("semantic_direct_read_budget_bytes", TOTAL_READ_BUDGET_BYTES * 2),
        ("target_tokens", ["attacker", "fabricated"]),
    ],
)
def test_attacker_rehashed_semantic_ledger_claim_fails_rehydration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str, value: object
) -> None:
    receipt = _receipt()
    if field == "target_tokens":
        receipt["semantic_target_coverage"][0]["evidence_quality"][field] = value
        _rehash_v2(receipt)
    else:
        receipt[field] = value
        _rehash_receipt(receipt)
    _bind_rehydration(monkeypatch, _receipt())

    with pytest.raises(ValueError, match="grounding_semantic_rehydration_evidence_mismatch"):
        rehydrate_grounded_semantic_evidence(receipt, work_focus=FOCUS, repo_root=tmp_path)


def test_v1_cannot_be_represented_as_immutable_v2_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="grounding_semantic_rehydration_schema_invalid"):
        rehydrate_grounded_semantic_evidence(
            _legacy_receipt(), work_focus=FOCUS, repo_root=tmp_path
        )


def test_attacker_rehash_of_v2_record_fails_rehydration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    legitimate = _receipt()
    attacker = deepcopy(legitimate)
    attacker["semantic_target_coverage"][0]["evidence_records"][0]["digest"] = (
        "sha256:" + "9" * 64
    )
    _rehash_v2(attacker)
    _bind_rehydration(monkeypatch, legitimate)
    with pytest.raises(ValueError, match="grounding_semantic_rehydration_evidence_mismatch"):
        rehydrate_grounded_semantic_evidence(
            attacker, work_focus=FOCUS, repo_root=tmp_path
        )


def test_repository_root_change_fails_rehydration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _receipt()
    _bind_rehydration(monkeypatch, receipt)
    monkeypatch.setattr(evidence_rehydration, "repository_root_digest", lambda _root: "sha256:" + "f" * 64)
    with pytest.raises(ValueError, match="grounding_semantic_rehydration_root_mismatch"):
        rehydrate_grounded_semantic_evidence(
            receipt, work_focus=FOCUS, repo_root=tmp_path
        )


def test_repository_head_change_fails_rehydration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _receipt()
    _bind_rehydration(monkeypatch, receipt)
    monkeypatch.setattr(evidence_rehydration, "read_git_head_sha", lambda _root: "d" * 40)
    with pytest.raises(ValueError, match="grounding_semantic_rehydration_head_mismatch"):
        rehydrate_grounded_semantic_evidence(
            receipt, work_focus=FOCUS, repo_root=tmp_path
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("git_mode", "100755"), ("blob_oid", "5" * 40)],
)
def test_git_object_binding_mismatch_fails_rehydration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str, value: str
) -> None:
    receipt = _receipt()
    actual_records = deepcopy(_semantic_records(receipt))
    actual_records[0][field] = value
    _bind_rehydration(monkeypatch, receipt)
    monkeypatch.setattr(
        evidence_rehydration, "secure_read_repo_head_file", _reader(actual_records)
    )
    with pytest.raises(ValueError, match="grounding_semantic_rehydration_evidence_mismatch"):
        rehydrate_grounded_semantic_evidence(
            receipt, work_focus=FOCUS, repo_root=tmp_path
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("path", "modules/foundups/pfmall/other.py"),
        ("digest", "sha256:" + "8" * 64),
        ("bytes", 63),
        ("truncated", True),
        ("repo_head_sha", "d" * 40),
    ],
)
def test_each_exact_head_record_field_mismatch_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    receipt = _receipt()
    actual = deepcopy(_semantic_records(receipt)[0])
    actual[field] = value
    expected_path = _semantic_records(receipt)[0]["path"]
    fallback_reader = _reader(_semantic_records(receipt)[1:])

    def read(root: Path, path: str, **limits: int) -> dict:
        if path == expected_path:
            return {"ok": True, **actual}
        return fallback_reader(root, path, **limits)

    _bind_rehydration(monkeypatch, receipt)
    monkeypatch.setattr(evidence_rehydration, "secure_read_repo_head_file", read)
    with pytest.raises(ValueError, match="grounding_semantic_rehydration_evidence_mismatch"):
        rehydrate_grounded_semantic_evidence(
            receipt, work_focus=FOCUS, repo_root=tmp_path
        )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), "wrong"),
        (("work_focus_digest",), "sha256:" + "0" * 64),
        (("typed_targets", "semantic_targets"), ["different"]),
        (("semantic_target_coverage", 0, "verdict"), "UNSAFE_TO_ACT"),
        (("holoindex_freshness",), "STALE"),
        (("holoindex_index_gap_detected",), True),
        (("holoindex_query_receipt_id",), ""),
        (("no_holoindex_reindex_performed",), False),
    ],
)
def test_tampering_fails_closed(path: tuple, value: object) -> None:
    receipt = deepcopy(_receipt())
    target = receipt
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    assert validate_grounded_target_receipt(receipt, work_focus=FOCUS).accepted is False


def test_rehashed_work_focus_substitution_still_fails() -> None:
    receipt = _receipt()
    receipt["work_focus_digest"] = canonical_digest({"work_focus": "different"})
    receipt["receipt_id"] = canonical_digest({key: value for key, value in receipt.items() if key != "receipt_id"})
    result = validate_grounded_target_receipt(receipt, work_focus=FOCUS)
    assert result.accepted is False
    assert "grounding_work_focus_mismatch" in result.rejection_reasons


def test_repo_target_requires_honest_recall() -> None:
    receipt = _receipt()
    typed = dict(receipt["typed_targets"])
    typed["repo_file_targets"] = ["modules/foundups/pfmall/api.py"]
    receipt["typed_targets"] = typed
    receipt["typed_targets_digest"] = canonical_digest(typed)
    receipt["repo_file_targets_count"] = 1
    receipt["target_recall_ok"] = False
    receipt["receipt_id"] = canonical_digest({key: value for key, value in receipt.items() if key != "receipt_id"})
    assert validate_grounded_target_receipt(receipt, work_focus=FOCUS).accepted is False
