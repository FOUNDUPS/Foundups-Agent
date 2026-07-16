from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

from holo_index.memex_projection_adapter import project_foundup_memex_to_holoindex_shadow
from holo_index.memex_projection_integrity import (
    verify_and_rehydrate_memex_projection,
)
from holo_index.query_receipt import digest_json


MODULE_PATH = Path(__file__).parents[1] / "memex_projection_integrity.py"
FIXED_NOW = "2026-07-16T00:00:00+00:00"
POLICY_DIGEST = "sha256:" + "2" * 64


def _projection(*, access_policy_digest: str = POLICY_DIGEST) -> dict:
    result = project_foundup_memex_to_holoindex_shadow(
        memex_view={
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
                "selected_slice": "HOLOINDEX_MEMEX_PROJECTION_INTEGRITY_AND_REHYDRATION_GATE_PHASE1",
                "runtime_gap": "serialized projection integrity",
            },
            "roadmap_state": {
                "next_slice": "REDDOG_MEMEX_SNAPSHOT_PROJECTION_SUPPLIER_PHASE1",
            },
            "verified_outcomes": [
                {
                    "outcome_id": "o1",
                    "accepted": True,
                    "finding": "Memex projection transport exists.",
                }
            ],
        },
        source_scope="foundup:foundups-agent",
        source_revision="abc123",
        allowed_foundup_ids=("foundups-agent",),
        access_policy_digest=access_policy_digest,
        holoindex_generation_id="generation-1",
        now_iso=FIXED_NOW,
    )
    assert result.accepted is True
    return result.to_dict()


def _assert_fail(projection: dict, reason: str, **kwargs) -> None:
    gate = verify_and_rehydrate_memex_projection(projection, **kwargs)

    assert gate.accepted is False
    assert gate.projection is None
    assert reason in gate.rejection_reasons


def test_valid_round_trip_serialization_rehydrates_projection() -> None:
    projection = _projection()

    gate = verify_and_rehydrate_memex_projection(projection, runtime_mode=True, now_iso=FIXED_NOW)

    assert gate.accepted is True
    assert gate.projection is not None
    assert gate.projection.accepted is True
    assert len(gate.projection.records) == 4
    assert gate.projection.receipt is not None
    assert gate.projection.receipt.receipt_id == projection["receipt"]["receipt_id"]
    assert gate.receipt_id.startswith("sha256:")


def test_changed_record_text_with_old_digest_fails() -> None:
    projection = _projection()
    projection["records"][0]["text"] = projection["records"][0]["text"] + " tampered"

    _assert_fail(projection, "record_content_digest_mismatch")


def test_changed_record_digest_with_old_record_id_fails() -> None:
    projection = _projection()
    projection["records"][0]["content_digest"] = "sha256:" + "3" * 64

    _assert_fail(projection, "record_id_mismatch")


def test_changed_manifest_with_old_receipt_id_fails() -> None:
    projection = _projection()
    projection["receipt"]["content_manifest_digest"] = "sha256:" + "4" * 64

    gate = verify_and_rehydrate_memex_projection(projection)

    assert gate.accepted is False
    assert "content_manifest_digest_mismatch" in gate.rejection_reasons
    assert "receipt_id_mismatch" in gate.rejection_reasons


def test_verification_fail_is_rejected_even_if_accepted_true() -> None:
    projection = _projection()
    projection["accepted"] = True
    projection["receipt"]["verification"] = "FAIL"

    _assert_fail(projection, "projection_verification_not_pass")


def test_wrong_schema_is_rejected() -> None:
    projection = _projection()
    projection["receipt"]["schema_version"] = "wrong.v1"

    _assert_fail(projection, "schema_version_mismatch")


def test_mixed_foundup_records_rejected() -> None:
    projection = _projection()
    projection["records"][0]["foundup_id"] = "other-foundup"

    _assert_fail(projection, "mixed_foundup_records")


def test_mixed_snapshot_ids_rejected() -> None:
    projection = _projection()
    projection["records"][0]["memex_snapshot_id"] = "sha256:other-snapshot"

    _assert_fail(projection, "mixed_snapshot_ids")


def test_mixed_policy_digests_rejected() -> None:
    projection = _projection()
    projection["records"][0]["metadata"] = dict(projection["records"][0]["metadata"])
    projection["records"][0]["metadata"]["access_policy_digest"] = "sha256:" + "5" * 64

    _assert_fail(projection, "mixed_policy_digests")


def test_record_count_and_rejected_count_are_validated() -> None:
    projection = _projection()
    projection["receipt"]["records_indexed"] = 99

    _assert_fail(projection, "records_indexed_count_mismatch")

    rejected_mismatch = _projection()
    rejected_mismatch["receipt"]["records_rejected"] = 1
    _assert_fail(rejected_mismatch, "records_rejected_count_mismatch")


def test_expired_snapshot_rejected_when_age_bound_supplied() -> None:
    projection = _projection()

    _assert_fail(
        projection,
        "projection_expired",
        now_iso="2026-07-18T00:00:00+00:00",
        max_age_seconds=60,
    )


def test_placeholder_policy_rejected_in_runtime_mode() -> None:
    projection = _projection(access_policy_digest="sha256:" + "1" * 64)

    _assert_fail(projection, "placeholder_access_policy_digest", runtime_mode=True, now_iso=FIXED_NOW)


def test_replay_revocation_and_expected_binding_rejected() -> None:
    projection = _projection()
    receipt_id = projection["receipt"]["receipt_id"]

    _assert_fail(projection, "projection_receipt_replayed", runtime_mode=True, seen_receipt_ids=(receipt_id,))
    _assert_fail(
        projection,
        "projection_snapshot_revoked",
        runtime_mode=True,
        revoked_snapshot_ids=("sha256:brain-view",),
    )
    _assert_fail(projection, "expected_foundup_mismatch", expected_foundup_id="other")
    _assert_fail(projection, "expected_generation_mismatch", expected_holoindex_generation_id="other")


def test_content_manifest_recomputed_from_records_and_rejections() -> None:
    projection = _projection()
    receipt = deepcopy(projection["receipt"])
    records = projection["records"]
    manifest = {
        "schema_version": "holoindex_memex_governed_projection_adapter.v1",
        "records": [
            {
                "record_id": record["record_id"],
                "content_digest": record["content_digest"],
                "source_class": record["source_class"],
            }
            for record in records
        ],
        "rejected": list(receipt["rejected_reasons"]),
    }

    assert digest_json(manifest) == receipt["content_manifest_digest"]


def test_integrity_gate_is_read_only_by_ast() -> None:
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
                assert alias.name.split(".", 1)[0] not in banned_imports
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_calls
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
