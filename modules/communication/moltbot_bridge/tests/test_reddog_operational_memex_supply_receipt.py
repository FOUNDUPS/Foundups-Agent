"""Security tests for operational Memex supply receipt rehydration."""

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_operational_memex_supply_receipt import (
    canonical_operational_memex_supply_digest,
    operational_memex_supply_receipt_id,
    rehydrate_operational_memex_supply_receipt,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    NOW,
    _authority_profile,
    _determination,
    _holo_receipt,
    _memex_supply,
)


MODULE_PATHS = tuple(
    Path(__file__).resolve().parents[1] / "src" / name
    for name in (
        "reddog_operational_memex_supply_freshness.py",
        "reddog_operational_memex_supply_proposal_binding.py",
        "reddog_operational_memex_supply_receipt.py",
    )
)


def _rehydrate(receipt=None, **overrides):
    determination = _determination()
    profile = _authority_profile()
    values = {
        "expected_foundup_id": profile["foundup_id"],
        "expected_principal_id": profile["principal_id"],
        "expected_snapshot_receipt_id": determination["snapshot_receipt_id"],
        "expected_snapshot_content_digest": determination[
            "snapshot_content_digest"
        ],
        "expected_holoindex_generation_id": _holo_receipt().generation_id,
        "expected_source_revision": determination["proposal_admission"][
            "work_state_revision"
        ],
        "now_iso": NOW,
    }
    values.update(overrides)
    return rehydrate_operational_memex_supply_receipt(
        receipt or _memex_supply(),
        **values,
    )


def test_valid_serialized_receipt_rehydrates_and_binds_full_digest() -> None:
    source = _memex_supply()
    receipt = _rehydrate(source)

    assert receipt.receipt_id == source["receipt_id"]
    assert canonical_operational_memex_supply_digest(receipt.to_dict()) == (
        canonical_operational_memex_supply_digest(source)
    )


def test_fabricated_sha256_looking_receipt_id_is_rejected() -> None:
    forged = {**_memex_supply(), "receipt_id": "sha256:" + ("a" * 64)}

    with pytest.raises(ValueError, match="receipt_id_mismatch"):
        _rehydrate(forged)


def test_changed_content_with_old_receipt_id_is_rejected() -> None:
    forged = {**_memex_supply(), "memex_view_id": "attacker-view"}

    with pytest.raises(ValueError, match="receipt_id_mismatch"):
        _rehydrate(forged)


def test_self_rehashed_content_cannot_satisfy_expected_bindings() -> None:
    forged = {**_memex_supply(), "foundup_id": "attacker_foundup"}
    forged["receipt_id"] = operational_memex_supply_receipt_id(forged)

    with pytest.raises(ValueError, match="authority_binding_mismatch"):
        _rehydrate(forged)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("snapshot_receipt_id", "sha256:attacker-snapshot"),
        ("snapshot_content_digest", "sha256:" + ("0" * 64)),
        ("holoindex_generation_id", "sha256:" + ("1" * 64)),
        ("source_revision", "sha256:attacker-revision"),
    ),
)
def test_self_rehashed_lineage_mismatch_is_rejected(field: str, value: str) -> None:
    forged = {**_memex_supply(), field: value}
    forged["receipt_id"] = operational_memex_supply_receipt_id(forged)

    with pytest.raises(ValueError, match="authority_binding_mismatch"):
        _rehydrate(forged)


def test_unknown_field_is_rejected() -> None:
    forged = {**_memex_supply(), "accepted": True}
    forged["receipt_id"] = operational_memex_supply_receipt_id(forged)

    with pytest.raises(ValueError, match="fields_invalid"):
        _rehydrate(forged)


def test_expired_or_timezone_ambiguous_policy_is_rejected() -> None:
    expired = _memex_supply(policy_expires_at=NOW)
    naive = _memex_supply(
        policy_issued_at="2026-07-15T23:00:00",
        policy_expires_at="2026-07-16T01:00:00",
    )

    with pytest.raises(ValueError, match="expired"):
        _rehydrate(expired)
    with pytest.raises(ValueError, match="time_invalid"):
        _rehydrate(naive)


def test_overage_and_overlong_policy_windows_are_rejected() -> None:
    old = _memex_supply(
        policy_issued_at="2026-07-15T23:54:59+00:00",
        policy_expires_at="2026-07-16T00:04:59+00:00",
    )
    overlong = _memex_supply(
        policy_expires_at="2026-07-16T00:10:01+00:00"
    )

    with pytest.raises(ValueError, match="too_old"):
        _rehydrate(old)
    with pytest.raises(ValueError, match="ttl_exceeded"):
        _rehydrate(overlong)


def test_freshness_policy_accepts_exact_age_and_ttl_boundaries() -> None:
    boundary = _memex_supply(
        policy_issued_at="2026-07-15T23:55:00+00:00",
        policy_expires_at="2026-07-16T00:05:00+00:00",
    )

    assert _rehydrate(boundary).receipt_id == boundary["receipt_id"]


def test_type_coercion_and_false_boundary_flags_are_rejected() -> None:
    scalar = copy.deepcopy(_memex_supply())
    scalar["assignment_ids"] = [1]
    scalar["receipt_id"] = operational_memex_supply_receipt_id(scalar)
    boundary = _memex_supply(no_repo_mutation_performed=False)

    with pytest.raises(ValueError, match="assignment_ids_invalid"):
        _rehydrate(scalar)
    with pytest.raises(ValueError, match="boundary_invalid"):
        _rehydrate(boundary)


def test_receipt_gate_is_bounded_and_has_no_effect_surface() -> None:
    banned_roots = {"os", "pathlib", "socket", "subprocess", "urllib"}

    for path in MODULE_PATHS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 200
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50
            if isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".", 1)[0] not in banned_roots
                    for alias in node.names
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".", 1)[0] not in banned_roots
