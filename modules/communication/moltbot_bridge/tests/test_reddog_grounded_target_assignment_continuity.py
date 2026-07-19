from __future__ import annotations

from copy import deepcopy

import pytest

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    SCHEMA_VERSION,
    canonical_digest,
    validate_grounded_target_receipt,
)


FOCUS = "Audit pfmall architecture and tests."


def _receipt() -> dict:
    typed = {
        "repo_file_targets": [],
        "semantic_targets": [FOCUS],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": canonical_digest([]),
    }
    coverage = [{"target": FOCUS, "verdict": "SUFFICIENT", "evidence_refs": ["code:pfmall"]}]
    value = {
        "schema_version": SCHEMA_VERSION,
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
        "target_recall_ok": None,
        "required_targets_missing": [],
        "direct_read_paths": [],
        "holoindex_owner_query_ok": True,
        "holoindex_freshness": "CURRENT",
        "holoindex_generation_id": "sha256:" + "a" * 64,
        "holoindex_freshness_receipt_digest": "sha256:" + "b" * 64,
        "holoindex_repo_head_sha": "c" * 40,
        "holoindex_query_receipt_id": "sha256:" + "d" * 64,
        "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
    }
    value["receipt_id"] = canonical_digest(value)
    return value


def test_valid_round_trip_is_accepted() -> None:
    result = validate_grounded_target_receipt(
        _receipt(), work_focus=FOCUS, expected_source_surface="editor_thin_client"
    )
    assert result.accepted is True
    assert result.verified is not None
    assert result.verified.semantic_targets == (FOCUS,)


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
