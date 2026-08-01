"""Security regressions for backend registered-FoundUp target verification."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_registered_foundup_target_verifier import (
    verify_registered_foundup_target,
)

ROOT = Path(__file__).resolve().parents[4]
REGISTRY = ROOT / "modules/foundups/foundup_registry.json"
SCHEMA = ROOT / "modules/foundups/foundup_registry.schema.json"


def _digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _receipt() -> dict:
    registry_bytes, schema_bytes = REGISTRY.read_bytes(), SCHEMA.read_bytes()
    registry = json.loads(registry_bytes)
    entity = next(item for item in registry["entities"] if item["foundup_id"] == "trade")
    manifest = ROOT / entity["manifest_path"]
    manifest_data = json.loads(manifest.read_bytes())
    evidence = [
        {"path": "modules/foundups/foundup_registry.json", "content_digest": _digest(registry_bytes)},
        {"path": "modules/foundups/foundup_registry.schema.json", "content_digest": _digest(schema_bytes)},
        {"path": entity["manifest_path"], "content_digest": _digest(manifest.read_bytes())},
    ]
    payload = {
        "schema_version": "registered_foundup_target_receipt.v1",
        "applied": True,
        "passed": True,
        "rejection_reasons": [],
        "foundup_id": "trade",
        "registry_digest": _digest(registry_bytes),
        "registry_schema_digest": _digest(schema_bytes),
        "registry_entity_digest": _digest(entity),
        "manifest_path": entity["manifest_path"],
        "evidence_digests": evidence,
        "safe_mutation_surfaces": manifest_data["build_contract"]["safe_mutation_surface"],
        "repo_root_digest": _digest(str(ROOT.resolve())),
        "repo_head_sha": __import__("subprocess").check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "grants_authority": False,
    }
    return {**payload, "receipt_id": _digest(payload)}


def _selection(receipt: dict) -> dict:
    return {
        "foundup_id": receipt["foundup_id"],
        "registered_foundup_target_receipt_id": receipt["receipt_id"],
    }


def _work_order(receipt: dict) -> dict:
    safe = receipt["safe_mutation_surfaces"]
    return {
        "foundup_id": receipt["foundup_id"],
        "registered_foundup_target_receipt_id": receipt["receipt_id"],
        "registered_foundup_target_receipt": receipt,
        "safe_mutation_surface_digest": _digest({"safe_mutation_surfaces": safe}),
        "allowed_paths": safe,
    }


def _rehash(receipt: dict) -> dict:
    value = deepcopy(receipt)
    value.pop("receipt_id", None)
    value["receipt_id"] = _digest(value)
    return value


def test_valid_current_checkout_binding_passes() -> None:
    receipt = _receipt()
    assert verify_registered_foundup_target(
        ROOT, receipt, selection_receipt=_selection(receipt), work_order=_work_order(receipt)
    ) == ()


def test_recomputed_scope_forgery_fails_against_manifest() -> None:
    receipt = _receipt()
    receipt["safe_mutation_surfaces"] = ["modules/foundups/**"]
    forged = _rehash(receipt)
    reasons = verify_registered_foundup_target(ROOT, forged, selection_receipt=_selection(forged))
    assert "registered_foundup_target_manifest_changed" in reasons


def test_recomputed_entity_forgery_fails_against_registry() -> None:
    receipt = _receipt()
    receipt["registry_entity_digest"] = "sha256:" + "0" * 64
    forged = _rehash(receipt)
    assert "registered_foundup_target_entity_changed" in verify_registered_foundup_target(ROOT, forged)


def test_recomputed_head_forgery_fails_against_checkout() -> None:
    receipt = _receipt()
    receipt["repo_head_sha"] = "0" * 40
    forged = _rehash(receipt)
    assert "registered_foundup_target_repo_head_mismatch" in verify_registered_foundup_target(ROOT, forged)


def test_selection_and_work_order_mismatch_fail() -> None:
    receipt = _receipt()
    assert "registered_foundup_target_selection_mismatch" in verify_registered_foundup_target(
        ROOT, receipt, selection_receipt={"foundup_id": "other", "registered_foundup_target_receipt_id": receipt["receipt_id"]}
    )
    order = _work_order(receipt)
    order["foundup_id"] = "other"
    assert "registered_foundup_target_work_order_mismatch" in verify_registered_foundup_target(
        ROOT, receipt, work_order=order
    )


def test_claim_without_receipt_fails() -> None:
    assert verify_registered_foundup_target(
        ROOT, None, selection_receipt={"foundup_id": "trade"}
    ) == ("registered_foundup_target_receipt_missing",)
