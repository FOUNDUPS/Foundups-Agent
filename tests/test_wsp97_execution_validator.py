"""Tests for the structural WSP 97 execution receipt validator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.wsp97_execution_validator import (
    DEFAULT_CONTRACT_PATH,
    TRUTH_BOUNDARY,
    load_contract,
    validate_execution_receipt,
)


ROOT = Path(__file__).resolve().parents[1]


def _valid_receipt() -> dict:
    contract = load_contract()
    actions = contract["wsp_97"]["operator_actions"]
    return {
        "execution_id": "slice-001",
        "execution_plane": "local_tools",
        "outcome": "completed",
        "action_evidence": {
            action.lower().replace(" ", "_"): [f"evidence/{index}.json"]
            for index, action in enumerate(actions, start=1)
        },
        "wsps_applied": ["WSP_50", "WSP_97"],
        "compliance_evidence": ["pr://1256"],
    }


def test_complete_receipt_derives_all_mantra_stages() -> None:
    result = validate_execution_receipt(_valid_receipt())

    assert result.is_compliant is True
    assert result.violations == ()
    assert len(result.required_actions) == 9
    assert result.derived_mantra_stages == (
        "holoindex",
        "research",
        "hard_think",
        "dialectic_sweep",
        "first_principles",
        "build",
        "follow_wsp",
    )
    assert result.truth_boundary == TRUTH_BOUNDARY


def test_missing_action_blocks_stage_derivation() -> None:
    receipt = _valid_receipt()
    del receipt["action_evidence"]["dialectic_sweep"]

    result = validate_execution_receipt(receipt)

    assert result.is_compliant is False
    assert result.missing_actions == ("dialectic_sweep",)
    assert "underived_mantra_stage:dialectic_sweep" in result.violations


def test_string_is_not_accepted_as_evidence_list() -> None:
    receipt = _valid_receipt()
    receipt["action_evidence"]["execute"] = "evidence/not-a-list.json"

    result = validate_execution_receipt(receipt)

    assert result.is_compliant is False
    assert result.invalid_evidence_actions == ("execute",)
    assert "underived_mantra_stage:build" in result.violations


def test_blocked_outcome_can_still_be_structurally_compliant() -> None:
    receipt = _valid_receipt()
    receipt["outcome"] = "blocked"
    receipt["action_evidence"]["execute"] = ["evidence/blocker.json"]

    result = validate_execution_receipt(receipt)

    assert result.is_compliant is True


def test_follow_wsp_requires_wsp97_and_compliance_evidence() -> None:
    receipt = _valid_receipt()
    receipt["wsps_applied"] = ["WSP_50"]
    receipt["compliance_evidence"] = []

    result = validate_execution_receipt(receipt)

    assert result.is_compliant is False
    assert "wsp_97_not_declared" in result.violations
    assert "missing_compliance_evidence" in result.violations
    assert "underived_mantra_stage:follow_wsp" in result.violations


def test_contract_loader_rejects_declared_count_drift(tmp_path: Path) -> None:
    contract = load_contract()
    contract["wsp_97"]["operator_action_count"] = 8
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")

    with pytest.raises(ValueError, match="operator_action_count"):
        load_contract(path)


def test_canonical_contract_declares_active_structural_validator() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    validator = contract["wsp_97"]["validator"]

    assert validator["status"] == "active_structural_validation"
    assert validator["entrypoint"] == "tools/wsp97_execution_validator.py"
    assert validator["receipt_schema_version"] == "1.0"


def test_cli_returns_one_for_incomplete_receipt(tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps({"execution_id": "incomplete"}), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "wsp97_execution_validator.py"), str(receipt_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["is_compliant"] is False
    assert payload["truth_boundary"] == TRUTH_BOUNDARY
