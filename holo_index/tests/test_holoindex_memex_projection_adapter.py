from __future__ import annotations

import ast
from pathlib import Path

from holo_index.memex_projection_adapter import (
    DEFAULT_ACCESS_POLICY_DIGEST,
    PROJECTION_ACCEPTED,
    PROJECTION_REJECTED,
    RECEIPT_SCHEMA_VERSION,
    SCHEMA_VERSION,
    project_foundup_memex_to_holoindex_shadow,
)


MODULE_PATH = Path(__file__).parents[1] / "memex_projection_adapter.py"
FIXED_NOW = "2026-07-16T00:00:00+00:00"


def _memex_view() -> dict[str, object]:
    return {
        "schema_version": "foundup_brain_current_state.v1",
        "foundup_brain_view_id": "sha256:brain-view",
        "foundup_id": "foundups-agent",
        "snapshot_id": "snapshot-1",
        "snapshot_content_digest": "sha256:snapshot",
        "identity": {
            "foundup_id": "foundups-agent",
            "name": "Foundups Agent",
        },
        "current_state": {
            "repo_head_sha": "abc123",
            "selected_slice": "HOLOINDEX_MEMEX_GOVERNED_PROJECTION_ADAPTER_PHASE1",
        },
        "roadmap_state": {
            "roadmap_id": "r1",
            "version": "v1",
            "content_digest": "sha256:roadmap",
        },
        "verified_outcomes": [
            {
                "outcome_id": "o1",
                "accepted": True,
                "held_out_passed": True,
                "content_digest": "sha256:outcome",
            }
        ],
    }


def _project(**overrides: object):
    kwargs = {
        "memex_view": _memex_view(),
        "source_scope": "foundup:foundups-agent",
        "source_revision": "abc123",
        "allowed_foundup_ids": ("foundups-agent",),
        "holoindex_generation_id": "generation-1",
        "now_iso": FIXED_NOW,
    }
    kwargs.update(overrides)
    return project_foundup_memex_to_holoindex_shadow(**kwargs)


def test_memex_projection_builds_shadow_records_and_receipt() -> None:
    result = _project()

    assert result.accepted is True
    assert result.status == PROJECTION_ACCEPTED
    assert len(result.records) == 4
    assert result.receipt is not None

    receipt = result.receipt.to_dict()
    assert receipt["schema_version"] == RECEIPT_SCHEMA_VERSION
    assert receipt["memex_snapshot_id"] == "sha256:brain-view"
    assert receipt["source_scope"] == "foundup:foundups-agent"
    assert receipt["source_revision"] == "abc123"
    assert receipt["created_at"] == FIXED_NOW
    assert receipt["access_policy_digest"] == DEFAULT_ACCESS_POLICY_DIGEST
    assert receipt["records_indexed"] == 4
    assert receipt["records_rejected"] == 0
    assert receipt["holoindex_generation_id"] == "generation-1"
    assert receipt["verification"] == "PASS"
    assert receipt["receipt_id"].startswith("sha256:")
    assert receipt["no_holoindex_write_performed"] is True
    assert receipt["no_memex_write_performed"] is True
    assert receipt["no_brain_write_performed"] is True
    assert receipt["no_breadcrumb_write_performed"] is True

    for record in result.records:
        record_dict = record.to_dict()
        assert record_dict["source_class"] == "memex"
        assert record_dict["foundup_id"] == "foundups-agent"
        assert record_dict["memex_snapshot_id"] == "sha256:brain-view"
        assert record_dict["source_scope"] == "foundup:foundups-agent"
        assert record_dict["source_revision"] == "abc123"
        assert record_dict["content_digest"].startswith("sha256:")
        assert record_dict["metadata"]["source_class"] == "memex"
        assert record_dict["metadata"]["snapshot_id"] == "snapshot-1"
        assert record_dict["metadata"]["snapshot_content_digest"] == "sha256:snapshot"
        assert record_dict["metadata"]["access_policy_digest"] == DEFAULT_ACCESS_POLICY_DIGEST


def test_memex_projection_is_deterministic_for_same_snapshot() -> None:
    first = _project()
    second = _project()

    assert first.to_dict() == second.to_dict()


def test_memex_projection_rejects_cross_foundup_scope() -> None:
    result = _project(allowed_foundup_ids=("other-foundup",))

    assert result.accepted is False
    assert result.status == PROJECTION_REJECTED
    assert "foundup_scope_not_authorized" in result.rejection_reasons
    assert result.records == ()
    assert result.receipt is None


def test_memex_projection_filters_secret_record_without_dropping_siblings() -> None:
    view = _memex_view()
    view["verified_outcomes"] = [
        {"outcome_id": "safe", "content_digest": "sha256:safe"},
        {"outcome_id": "unsafe", "api_key": "sk-testsecret"},
    ]

    result = _project(memex_view=view)

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.records_indexed == 4
    assert result.receipt.records_rejected == 1
    assert result.receipt.rejected_reasons == ("secret_bearing_record:verified_outcome:1",)
    joined_records = "\n".join(record.text for record in result.records)
    assert "sk-testsecret" not in joined_records
    assert "unsafe" not in joined_records


def test_memex_projection_rejects_missing_snapshot_binding() -> None:
    view = _memex_view()
    view.pop("foundup_brain_view_id")
    view.pop("snapshot_id")

    result = _project(memex_view=view)

    assert result.accepted is False
    assert "missing_snapshot_binding" in result.rejection_reasons


def test_memex_projection_rejects_missing_source_scope_and_revision() -> None:
    result = _project(source_scope="", source_revision="")

    assert result.accepted is False
    assert "missing_source_scope" in result.rejection_reasons
    assert "missing_source_revision" in result.rejection_reasons


def test_memex_projection_rejects_invalid_access_policy_digest() -> None:
    result = _project(access_policy_digest="policy-v1")

    assert result.accepted is False
    assert "invalid_access_policy_digest" in result.rejection_reasons


def test_memex_projection_is_projection_only_by_ast() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {
        "subprocess",
        "requests",
        "httpx",
        "sqlite3",
        "chromadb",
    }
    banned_calls = {
        "add",
        "upsert",
        "delete",
        "reset",
        "_reset_collection",
        "write_text",
        "write_bytes",
        "open",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                assert root not in banned_imports
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            assert root not in banned_imports
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                assert func.attr not in banned_calls
            if isinstance(func, ast.Name):
                assert func.id not in banned_calls


def test_memex_projection_exports_schema_version() -> None:
    assert SCHEMA_VERSION == "holoindex_memex_governed_projection_adapter.v1"
