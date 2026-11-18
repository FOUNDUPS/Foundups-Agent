"""Tests for REDDOG_RESEARCH_HOLOINDEX_PROMOTION_GATE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_first_external_research_grounding_adapter as grounding,
)
from modules.communication.moltbot_bridge.src import (
    reddog_research_holoindex_promotion_gate as gate,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_research_holoindex_promotion_gate.py"
)


class FakeHoloIndex:
    def search(self, query: str):
        return {
            "status": "bundle_json_ok",
            "knowledge": [{"path": "WSP_knowledge/docs/Papers/prior.md"}],
        }


class FakeRetriever:
    def __init__(self, *, status: str = "candidate", content_digest: str | None = None):
        self.status = status
        self.content_digest = content_digest or "a" * 64

    def fetch(self, target):
        return {
            "source_url": "https://github.com/karpathy/autoresearch",
            "source_type": "github",
            "fetched_at": 2000,
            "content_sha256": self.content_digest,
            "provenance_refs": ["github:karpathy/autoresearch@main"],
            "freshness_receipt_digest": "sha256:" + "b" * 64,
            "finding_status": self.status,
            "content_text": "Observed repository metadata.",
        }


def _grounding(status: str = "candidate"):
    return grounding.ground_reddog_holoindex_first_external_research(
        {"external_research_targets": ["https://github.com/karpathy/autoresearch"]},
        holoindex=FakeHoloIndex(),
        external_retriever=FakeRetriever(status=status),
        now_s=2100,
    ).to_dict()


def _verification(**overrides):
    payload = {
        "decision": "RESEARCH_VERIFICATION_ACCEPT",
        "accepted": True,
        "independent_evaluator": "verifier-panel",
        "evidence_digest": "sha256:" + "c" * 64,
    }
    payload.update(overrides)
    return payload


def _holoindex(**overrides):
    payload = {
        "holoindex_freshness_receipt_digest": "sha256:" + "d" * 64,
        "index_gap_detected": False,
        "holoindex_status": "bundle_json_ok",
    }
    payload.update(overrides)
    return payload


def test_verified_external_research_plans_holoindex_promotion_without_index_write() -> None:
    result = gate.plan_reddog_research_holoindex_promotion(
        _grounding(),
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert result.accepted is True
    assert result.decision == gate.RESEARCH_HOLOINDEX_PROMOTION_ACCEPT
    assert result.receipt.entries_total == 1
    assert result.receipt.entries_positive == 1
    assert result.receipt.promotion_to_holoindex_performed is False
    assert result.receipt.no_holoindex_reindex_performed is True
    entry = result.entries[0]
    assert entry.destination_collection == gate.DESTINATION_COLLECTION
    assert entry.index_action == "promote_verified_research_finding"
    assert entry.content_digest == "sha256:" + "a" * 64
    assert entry.untrusted_data_only is True


def test_negative_research_result_is_promotable_when_grounding_allows_it() -> None:
    result = gate.plan_reddog_research_holoindex_promotion(
        _grounding("negative"),
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert result.accepted is True
    assert result.receipt.entries_negative == 1
    assert result.entries[0].finding_status == "negative"
    assert result.entries[0].index_action == "promote_negative_research_result"


def test_rejects_unaccepted_grounding_result() -> None:
    bad = _grounding()
    bad["accepted"] = False

    result = gate.plan_reddog_research_holoindex_promotion(
        bad,
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert result.accepted is False
    assert gate.FAIL_GROUNDING_NOT_ACCEPTED in result.rejection_reasons


def test_rejects_without_independent_verification_acceptance() -> None:
    result = gate.plan_reddog_research_holoindex_promotion(
        _grounding(),
        verification_receipt={"decision": "RESEARCH_VERIFICATION_REJECT", "accepted": False},
        holoindex_evidence=_holoindex(),
    )

    assert result.accepted is False
    assert gate.FAIL_VERIFICATION_NOT_ACCEPTED in result.rejection_reasons


def test_rejects_missing_or_gap_holoindex_freshness_evidence() -> None:
    missing = gate.plan_reddog_research_holoindex_promotion(
        _grounding(),
        verification_receipt=_verification(),
        holoindex_evidence={},
    )
    gap = gate.plan_reddog_research_holoindex_promotion(
        _grounding(),
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(index_gap_detected=True),
    )

    assert gate.FAIL_HOLOINDEX_FRESHNESS_RECEIPT in missing.rejection_reasons
    assert gate.FAIL_HOLOINDEX_INDEX_GAP in gap.rejection_reasons


def test_rejects_internal_holoindex_only_target_as_no_new_promotion_target() -> None:
    internal = grounding.ground_reddog_holoindex_first_external_research(
        {"semantic_targets": ["autoresearch prior memory"]},
        holoindex=FakeHoloIndex(),
    ).to_dict()

    result = gate.plan_reddog_research_holoindex_promotion(
        internal,
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert result.accepted is False
    assert gate.FAIL_NO_PROMOTABLE_RESEARCH_TARGET in result.rejection_reasons
    assert result.receipt.entries_total == 0


def test_rejects_missing_hash_or_provenance() -> None:
    bad = _grounding()
    bad["grounded_targets"][0]["content_digest"] = ""
    bad["grounded_targets"][0]["provenance_refs"] = []

    result = gate.plan_reddog_research_holoindex_promotion(
        bad,
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert gate.FAIL_SOURCE_HASH_MISSING in result.rejection_reasons
    assert gate.FAIL_PROVENANCE_MISSING in result.rejection_reasons


def test_rejects_prompt_injection_when_untrusted_boundary_is_missing() -> None:
    bad = _grounding()
    bad["grounded_targets"][0]["prompt_injection_markers_detected"] = True
    bad["grounded_targets"][0]["untrusted_data_only"] = False

    result = gate.plan_reddog_research_holoindex_promotion(
        bad,
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert gate.FAIL_UNTRUSTED_DATA_BOUNDARY in result.rejection_reasons


def test_rejects_unsupported_status_and_negative_when_not_indexable() -> None:
    unsupported = _grounding()
    unsupported["grounded_targets"][0]["finding_status"] = "hype"
    negative = _grounding("negative")
    negative["receipt"]["rejected_negative_results_indexable"] = False

    bad_status = gate.plan_reddog_research_holoindex_promotion(
        unsupported,
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )
    not_indexable = gate.plan_reddog_research_holoindex_promotion(
        negative,
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert gate.FAIL_UNSUPPORTED_FINDING_STATUS in bad_status.rejection_reasons
    assert gate.FAIL_NEGATIVE_RESULT_NOT_INDEXABLE in not_indexable.rejection_reasons


def test_rejects_secret_bearing_evidence() -> None:
    bad = _grounding()
    bad["grounded_targets"][0]["source_url"] = "https://github.com/org/repo?api_key=abc"

    result = gate.plan_reddog_research_holoindex_promotion(
        bad,
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert gate.FAIL_SECRET_BEARING_EVIDENCE in result.rejection_reasons


def test_receipt_is_deterministic_and_json_serializable() -> None:
    first = gate.plan_reddog_research_holoindex_promotion(
        _grounding(),
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )
    second = gate.plan_reddog_research_holoindex_promotion(
        _grounding(),
        verification_receipt=_verification(),
        holoindex_evidence=_holoindex(),
    )

    assert first.receipt.receipt_id == second.receipt.receipt_id
    encoded = json.dumps(first.to_dict(), sort_keys=True)
    assert "research_holoindex_promotion_" in encoded
    assert "promoted_to_holoindex" not in encoded


def test_ast_boundary_no_index_mutation_network_commands_or_persistence() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_imports = {
        "holo_index",
        "requests",
        "httpx",
        "urllib.request",
        "subprocess",
        "os",
        "socket",
        "sqlite3",
        "pattern_memory",
        "agent_db",
    }
    forbidden_calls = {
        "run",
        "Popen",
        "system",
        "popen",
        "open",
        "index_all",
        "index_code",
        "index_docs",
        "index_knowledge",
        "write_freshness_receipt",
        "store_outcome",
        "create_autonomous_task",
    }
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
