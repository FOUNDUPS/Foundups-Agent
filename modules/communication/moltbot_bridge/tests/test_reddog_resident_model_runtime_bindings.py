"""Tests for the shared resident RedDog model-binding loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings import (
    ARCHITECT_SURFACE,
    AUDIT_SURFACE,
    load_resident_model_runtime_bindings,
)


REPO_ROOT = Path(__file__).resolve().parents[4]


class _Receipt:
    def __init__(self, surface: str) -> None:
        from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
            ModelRuntimeBindingDecision,
        )

        self.decision = ModelRuntimeBindingDecision.BOUND
        self.principal_model = "provider/model"
        self.runtime_surface = surface
        self.rejection_reasons = ()


def _env(runtime_root: Path, audit_path: Path, architect_path: Path) -> dict[str, str]:
    return {
        "REDDOG_RESIDENT_MODEL_RUNTIME_BINDING_ROOT": str(runtime_root),
        "REDDOG_READONLY_AUDIT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(audit_path),
        "REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH": str(
            architect_path
        ),
    }


def test_loads_distinct_bound_receipts_outside_repo(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.json"
    architect_path = tmp_path / "architect.json"
    audit_path.write_text("{}", encoding="utf-8")
    architect_path.write_text("{}", encoding="utf-8")
    raws = [{"runtime_surface": AUDIT_SURFACE}, {"runtime_surface": ARCHITECT_SURFACE}]
    receipts = [_Receipt(AUDIT_SURFACE), _Receipt(ARCHITECT_SURFACE)]
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
    assert audit == raws[0]
    assert architect == raws[1]


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
            side_effect=(_Receipt(ARCHITECT_SURFACE), _Receipt(ARCHITECT_SURFACE)),
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
