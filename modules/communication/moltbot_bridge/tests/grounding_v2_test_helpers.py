"""Shared exact-HEAD v2 grounding fixtures for RedDog runtime tests."""

from __future__ import annotations

from pathlib import Path

from holo_index.freshness_receipt import read_git_head_sha
from holo_index.repository_state import repository_root_digest
from modules.communication.moltbot_bridge.src.reddog_bounded_iterative_retrieval import (
    MAX_TOTAL_GROUNDING_SECONDS,
    MAX_TOTAL_OWNER_QUERIES,
    TOTAL_READ_BUDGET_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    BOUNDED_SCHEMA_VERSION,
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import ground_transport_work_focus


def exact_head_repo_target_grounding_receipt(
    *, repo_root: Path, work_focus: str, repo_target: str
) -> dict[str, object]:
    typed = {
        "repo_file_targets": [repo_target], "semantic_targets": [],
        "external_research_targets": [], "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": canonical_digest([]),
    }
    empty_coverage = {"semantic_target_coverage": []}
    empty_traces = {"semantic_retrieval_traces": []}
    empty_reads = {"semantic_direct_read_attempts": []}
    value = {
        "schema_version": BOUNDED_SCHEMA_VERSION, "source_surface": "editor_thin_client",
        "work_focus_digest": canonical_digest({"work_focus": work_focus}),
        "typed_targets": typed, "typed_targets_digest": canonical_digest(typed),
        "grounding_preflight_applied": True, "grounding_preflight_passed": True,
        "grounding_preflight_rejection_reasons": [], "grounding_target_universe_required": True,
        "repo_file_targets_count": 1, "semantic_targets_count": 0,
        "external_research_targets_count": 0, "quoted_reference_blocks_count": 0,
        "semantic_target_coverage": [],
        "semantic_target_coverage_digest": canonical_digest(empty_coverage),
        "semantic_retrieval_traces": [],
        "semantic_retrieval_traces_digest": canonical_digest(empty_traces),
        "semantic_owner_query_attempts_total": 0,
        "semantic_owner_query_budget": MAX_TOTAL_OWNER_QUERIES,
        "semantic_grounding_deadline_seconds": MAX_TOTAL_GROUNDING_SECONDS,
        "semantic_direct_read_attempts": [],
        "semantic_direct_read_attempts_digest": canonical_digest(empty_reads),
        "semantic_direct_read_bytes_total": 0,
        "semantic_direct_read_budget_bytes": TOTAL_READ_BUDGET_BYTES,
        "target_recall_ok": True, "required_targets_missing": [],
        "direct_read_paths": [repo_target], "semantic_direct_read_paths": [],
        "repo_audit_fallback_used": False, "repo_audit_fallback": {},
        "repo_audit_fallback_digest": "", "repo_state_head_sha": read_git_head_sha(repo_root),
        "repo_state_root_digest": repository_root_digest(repo_root),
        "holoindex_owner_query_ok": False, "holoindex_freshness": "UNKNOWN",
        "holoindex_generation_id": "", "holoindex_freshness_receipt_digest": "",
        "holoindex_repo_head_sha": "", "holoindex_repo_root_digest": repository_root_digest(repo_root),
        "holoindex_query_receipt_id": "", "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
    }
    value["receipt_id"] = canonical_digest(value)
    return value


def attach_exact_head_fixture_grounding(context: dict, repo_root: Path) -> None:
    targets = tuple(context["assignment"]["allowed_read_targets"])
    focus = "Read first:\n" + "\n".join(f"- {path}" for path in targets)
    grounding = ground_transport_work_focus(
        repo_root=repo_root, work_focus=focus, foundup_id="foundups_agent",
        authenticated_principal_id="principal-012", source_surface="hermes_thin_client",
        client_request_id="executor-model-fixture",
        owner_query=lambda _query: (_ for _ in ()).throw(
            AssertionError("explicit targets must not query HoloIndex")
        ),
    )
    if not grounding.accepted:
        raise AssertionError(grounding.rejection_reasons)
    receipt = dict(grounding.grounding_receipt)
    digest = canonical_digest(receipt)
    context.update({
        "grounding_receipt": receipt, "grounding_receipt_id": receipt["receipt_id"],
        "grounding_receipt_digest": digest, "work_focus": focus,
        "typed_targets": dict(grounding.typed_targets),
    })
    context["assignment"].update({
        "grounding_receipt_id": receipt["receipt_id"],
        "grounding_receipt_digest": digest,
    })


__all__ = ["attach_exact_head_fixture_grounding", "exact_head_repo_target_grounding_receipt"]
