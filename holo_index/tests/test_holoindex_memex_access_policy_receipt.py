from __future__ import annotations

import ast
from pathlib import Path

from holo_index.memex_access_policy_receipt import (
    POLICY_READY,
    build_memex_access_policy_receipt,
    section_allowed_by_policy,
    validate_memex_access_policy_receipt,
)


MODULE_PATH = Path(__file__).parents[1] / "memex_access_policy_receipt.py"
ISSUED_AT = "2026-07-16T00:00:00+00:00"
EXPIRES_AT = "2026-07-17T00:00:00+00:00"


def _receipt() -> dict:
    result = build_memex_access_policy_receipt(
        principal_id="principal:012",
        work_order_id="work-order-1",
        foundup_scope=("foundups-agent",),
        source_scope="foundup:foundups-agent",
        sensitivity_classes=("internal",),
        allowed_record_sections=("identity", "current_state", "roadmap_state"),
        denied_record_sections=("verified_outcome",),
        max_records=8,
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
        policy_generation_id="policy-generation-1",
    )
    assert result.accepted is True
    assert result.receipt is not None
    return result.receipt.to_dict()


def test_access_policy_receipt_builds_deterministic_valid_receipt() -> None:
    first = _receipt()
    second = _receipt()

    assert first == second
    assert first["schema_version"] == "holoindex_memex_access_policy_receipt.v1"
    assert first["receipt_id"].startswith("sha256:")
    assert first["verification"] == "PASS"
    assert first["no_memex_write_performed"] is True
    assert first["no_holoindex_write_performed"] is True

    validation = validate_memex_access_policy_receipt(
        first,
        expected_foundup_id="foundups-agent",
        expected_source_scope="foundup:foundups-agent",
        expected_principal_id="principal:012",
        expected_work_order_id="work-order-1",
        now_iso=ISSUED_AT,
    )
    assert validation.accepted is True
    assert validation.status == POLICY_READY


def test_access_policy_receipt_rejects_tampered_receipt_id() -> None:
    receipt = _receipt()
    receipt["principal_id"] = "principal:attacker"

    validation = validate_memex_access_policy_receipt(receipt, now_iso=ISSUED_AT)

    assert validation.accepted is False
    assert "access_policy_receipt_id_mismatch" in validation.rejection_reasons


def test_access_policy_receipt_rejects_expired_replayed_and_revoked() -> None:
    receipt = _receipt()

    expired = validate_memex_access_policy_receipt(receipt, now_iso="2026-07-18T00:00:00+00:00")
    replayed = validate_memex_access_policy_receipt(
        receipt,
        now_iso=ISSUED_AT,
        seen_receipt_ids=(receipt["receipt_id"],),
    )
    revoked = validate_memex_access_policy_receipt(
        receipt,
        now_iso=ISSUED_AT,
        revoked_receipt_ids=(receipt["receipt_id"],),
    )

    assert expired.accepted is False
    assert "access_policy_expired" in expired.rejection_reasons
    assert replayed.accepted is False
    assert "access_policy_replayed" in replayed.rejection_reasons
    assert revoked.accepted is False
    assert "access_policy_revoked" in revoked.rejection_reasons


def test_access_policy_receipt_rejects_scope_mismatch_and_bad_sensitivity() -> None:
    receipt = _receipt()
    mismatch = validate_memex_access_policy_receipt(
        receipt,
        expected_foundup_id="other-foundup",
        expected_source_scope="foundup:foundups-agent",
        now_iso=ISSUED_AT,
    )
    bad_sensitivity = dict(receipt)
    bad_sensitivity["sensitivity_classes"] = ["secret"]

    bad = validate_memex_access_policy_receipt(bad_sensitivity, now_iso=ISSUED_AT)

    assert mismatch.accepted is False
    assert "expected_foundup_not_in_scope" in mismatch.rejection_reasons
    assert bad.accepted is False
    assert "unsupported_sensitivity_class" in bad.rejection_reasons


def test_section_policy_allows_and_denies_expected_sections() -> None:
    validation = validate_memex_access_policy_receipt(_receipt(), now_iso=ISSUED_AT)
    assert validation.receipt is not None

    assert section_allowed_by_policy("identity", validation.receipt) is True
    assert section_allowed_by_policy("verified_outcome:0", validation.receipt) is False


def test_access_policy_receipt_is_read_only_by_ast() -> None:
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
