"""Tests for the shared resident RedDog model-binding loader."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings import (
    ARCHITECT_SURFACE,
    AUDIT_SURFACE,
    load_resident_model_runtime_bindings,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]


class _Receipt:
    def __init__(
        self,
        surface: str,
        receipt_id: str,
        **overrides: object,
    ) -> None:
        from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
            ModelRuntimeBindingDecision,
        )

        self.decision = ModelRuntimeBindingDecision.BOUND
        self.principal_model = "provider/model"
        self.panel_models = ()
        self.role_bindings = (
            SimpleNamespace(
                role="principal",
                model_id=self.principal_model,
                provider="provider",
            ),
        )
        self.runtime_surface = surface
        self.task_family = "repository_audit"
        self.rejection_reasons = ()
        self.receipt_id = receipt_id
        self.benchmark_evidence_receipt_ids = ("benchmark:receipt",)
        self.promotion_evidence_receipt_ids = ("promotion:receipt",)
        self.signed_promotion_receipt_ids = ("signed:receipt",)
        self.policy = SimpleNamespace(
            task_family=self.task_family,
            runtime_surface=surface,
            min_verifier_pass_rate=0.9,
            authority_receipt_id="authority:receipt",
            required_task_set_digest="sha256:" + "1" * 64,
            required_held_out_split_digest="sha256:" + "2" * 64,
            required_verifier_digest="sha256:" + "3" * 64,
        )
        for name, value in overrides.items():
            setattr(self, name, value)

    def to_dict(self) -> dict[str, str]:
        return {
            "receipt_id": self.receipt_id,
            "runtime_surface": self.runtime_surface,
        }


def _env(runtime_root: Path, audit_path: Path, architect_path: Path) -> dict[str, str]:
    return {
        "REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": str(runtime_root),
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(audit_path),
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(
            architect_path
        ),
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": "audit:receipt",
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": "architect:receipt",
    }


def _real_receipt(surface: str) -> dict[str, object]:
    receipt = model_runtime_binding_receipt(runtime_surface=surface)
    receipt["policy"]["required_task_set_digest"] = "sha256:" + "1" * 64
    receipt["policy"]["required_held_out_split_digest"] = "sha256:" + "2" * 64
    receipt["policy"]["required_verifier_digest"] = "sha256:" + "3" * 64
    return _resign(receipt)


def _resign(receipt: dict[str, object]) -> dict[str, object]:
    body = {key: value for key, value in receipt.items() if key != "receipt_id"}
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    receipt["receipt_id"] = (
        "reddog_model_runtime_binding:" + hashlib.sha256(encoded).hexdigest()
    )
    return receipt


def test_loads_distinct_bound_receipts_outside_repo(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.json"
    architect_path = tmp_path / "architect.json"
    audit_path.write_text("{}", encoding="utf-8")
    architect_path.write_text("{}", encoding="utf-8")
    raws = [{"runtime_surface": AUDIT_SURFACE}, {"runtime_surface": ARCHITECT_SURFACE}]
    receipts = [
        _Receipt(AUDIT_SURFACE, "audit:receipt"),
        _Receipt(ARCHITECT_SURFACE, "architect:receipt"),
    ]
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "read_reddog_runtime_json_mapping",
            side_effect=raws,
        ),
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "rehydrate_model_runtime_binding_receipt",
            side_effect=receipts,
        ),
    ):
        audit, architect, reason = load_resident_model_runtime_bindings(
            REPO_ROOT,
            environ=_env(tmp_path, audit_path, architect_path),
        )

    assert reason == ""
    assert audit == receipts[0].to_dict()
    assert architect == receipts[1].to_dict()


@pytest.mark.parametrize(
    ("updates", "reason"),
    (
        ({"REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": ""}, "missing_model_runtime_binding_root"),
        (
            {"REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": ""},
            "missing_audit_model_runtime_binding_path",
        ),
        (
            {"REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": ""},
            "missing_architect_model_runtime_binding_path",
        ),
        (
            {
                "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": ""
            },
            "missing_audit_model_runtime_binding_expected_receipt_id",
        ),
        (
            {
                "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID": ""
            },
            "missing_architect_model_runtime_binding_expected_receipt_id",
        ),
    ),
)
def test_missing_configuration_fails_closed(
    tmp_path: Path, updates: dict[str, str], reason: str
) -> None:
    audit = tmp_path / "audit.json"
    architect = tmp_path / "architect.json"
    env = _env(tmp_path, audit, architect)
    env.update(updates)
    assert load_resident_model_runtime_bindings(
        REPO_ROOT, environ=env
    ) == (None, None, reason)


def test_same_artifact_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "binding.json"
    artifact.write_text("{}", encoding="utf-8")
    assert load_resident_model_runtime_bindings(
        REPO_ROOT, environ=_env(tmp_path, artifact, artifact)
    ) == (None, None, "model_runtime_binding_artifacts_not_distinct")


def test_wrong_surface_is_rejected(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.json"
    architect_path = tmp_path / "architect.json"
    audit_path.write_text("{}", encoding="utf-8")
    architect_path.write_text("{}", encoding="utf-8")
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "read_reddog_runtime_json_mapping",
            side_effect=({}, {}),
        ),
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "rehydrate_model_runtime_binding_receipt",
            side_effect=(
                _Receipt(ARCHITECT_SURFACE, "audit:receipt"),
                _Receipt(ARCHITECT_SURFACE, "architect:receipt"),
            ),
        ),
    ):
        result = load_resident_model_runtime_bindings(
            REPO_ROOT, environ=_env(tmp_path, audit_path, architect_path)
        )
    assert result == (None, None, "audit_model_runtime_binding_surface_invalid")


def test_artifact_inside_repo_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "architect.json"
    outside.write_text("{}", encoding="utf-8")
    result = load_resident_model_runtime_bindings(
        REPO_ROOT,
        environ=_env(
            tmp_path,
            REPO_ROOT / "main.py",
            outside,
        ),
    )
    assert result == (None, None, "model_runtime_binding_artifact_inside_repo")


def test_recomputed_untrusted_binding_rejects_against_host_pin(
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "audit.json"
    architect_path = tmp_path / "architect.json"
    audit_path.write_text("{}", encoding="utf-8")
    architect_path.write_text("{}", encoding="utf-8")
    forged = _Receipt(AUDIT_SURFACE, "sha256:attacker-recomputed")
    architect = _Receipt(ARCHITECT_SURFACE, "architect:receipt")
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "read_reddog_runtime_json_mapping",
            side_effect=({}, {}),
        ),
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "rehydrate_model_runtime_binding_receipt",
            side_effect=(forged, architect),
        ),
    ):
        result = load_resident_model_runtime_bindings(
            REPO_ROOT,
            environ=_env(tmp_path, audit_path, architect_path),
        )
    assert result == (None, None, "audit_model_runtime_binding_receipt_id_mismatch")


@pytest.mark.parametrize(
    "overrides",
    (
        {"benchmark_evidence_receipt_ids": ()},
        {"promotion_evidence_receipt_ids": ()},
        {"signed_promotion_receipt_ids": ()},
        {"role_bindings": ()},
        {"policy": SimpleNamespace(
            task_family="repository_audit",
            runtime_surface=AUDIT_SURFACE,
            min_verifier_pass_rate=0.0,
            authority_receipt_id="",
            required_task_set_digest="",
            required_held_out_split_digest="",
            required_verifier_digest="",
        )},
    ),
)
def test_unsigned_or_incomplete_audit_binding_fails_closed(
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    audit_path = tmp_path / "audit.json"
    architect_path = tmp_path / "architect.json"
    audit_path.write_text("{}", encoding="utf-8")
    architect_path.write_text("{}", encoding="utf-8")
    receipts = (
        _Receipt(AUDIT_SURFACE, "audit:receipt", **overrides),
        _Receipt(ARCHITECT_SURFACE, "architect:receipt"),
    )
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "read_reddog_runtime_json_mapping",
            side_effect=({}, {}),
        ),
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings."
            "rehydrate_model_runtime_binding_receipt",
            side_effect=receipts,
        ),
    ):
        result = load_resident_model_runtime_bindings(
            REPO_ROOT,
            environ=_env(tmp_path, audit_path, architect_path),
        )
    assert result == (None, None, "audit_model_runtime_binding_evidence_invalid")


def test_recomputed_empty_signed_lineage_rejects_even_when_host_pinned(
    tmp_path: Path,
) -> None:
    audit = _real_receipt(AUDIT_SURFACE)
    architect = _real_receipt(ARCHITECT_SURFACE)
    audit["signed_promotion_receipt_ids"] = []
    _resign(audit)
    audit_path = tmp_path / "audit.json"
    architect_path = tmp_path / "architect.json"
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    architect_path.write_text(json.dumps(architect), encoding="utf-8")
    env = _env(tmp_path, audit_path, architect_path)
    env["REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID"] = str(
        audit["receipt_id"]
    )
    env["REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_EXPECTED_RECEIPT_ID"] = str(
        architect["receipt_id"]
    )

    result = load_resident_model_runtime_bindings(REPO_ROOT, environ=env)

    assert result == (None, None, "audit_model_runtime_binding_evidence_invalid")
