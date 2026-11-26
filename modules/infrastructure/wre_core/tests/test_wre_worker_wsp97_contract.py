"""Tests for WRE worker WSP_00 0.2A and WSP_97 pure-evaluation contract."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src.wre_worker_wsp97_contract import (
    ALLOWED_WORKER_SELF,
    FAIL_ENVELOPE_TYPE,
    FAIL_IMPLICIT_ROLE_ESCALATION,
    FAIL_INVALID_ORIGIN,
    FAIL_INVALID_ROLE,
    FAIL_INVALID_SELF,
    FAIL_MISSING_PRINCIPAL_REF,
    FAIL_RECEIPT_INVALID_TYPE,
    FAIL_RECEIPT_NON_COMPLIANT,
    FAIL_RECEIPT_VALIDATION_ERROR,
    FAIL_REPO_ROOT_REQUIRED,
    FAIL_ROLE_ESCALATION,
    FAIL_SELF_IS_012,
    FAIL_SELF_VERIFICATION_PROHIBITED,
    RECEIPT_SCHEMA_VERSION,
    WSP00_ENVELOPE_VALID,
    WSP97_RECEIPT_VALID,
    build_worker_wsp97_prompt_contract,
    validate_worker_wsp00_envelope,
    validate_worker_wsp97_receipt,
)
from tools.wsp97_execution_validator import load_contract


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "infrastructure"
    / "wre_core"
    / "src"
    / "wre_worker_wsp97_contract.py"
)
WSP_00_PATH = "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md"
WSP_97_PATH = "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md"


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        check=True,
        text=True,
    )
    return completed.stdout.strip()


def _temporary_repository(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repository"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "wsp97-tests@example.invalid")
    _git(repo, "config", "user.name", "WSP 97 Tests")
    wsp_dir = repo / "WSP_framework" / "src"
    wsp_dir.mkdir(parents=True)
    (wsp_dir / "WSP_00_Zen_State_Attainment_Protocol.md").write_text("# WSP 00\n", encoding="utf-8")
    (wsp_dir / "WSP_97_System_Execution_Prompting_Protocol.md").write_text("# WSP 97\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "test fixture")
    return repo, _git(repo, "rev-parse", "HEAD")


def _valid_receipt(base_commit: str) -> dict:
    actions = load_contract()["wsp_97"]["operator_actions"]
    evidence = {
        action.lower().replace(" ", "_"): [f"opaque evidence {index}"]
        for index, action in enumerate(actions, start=1)
    }
    evidence["retrieve_wsps"] = [WSP_00_PATH, WSP_97_PATH]
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "repository_context": {"base_commit": base_commit},
        "execution_id": "worker-slice-001",
        "execution_plane": "wre",
        "outcome": "completed",
        "action_evidence": evidence,
        "wsps_applied": ["WSP_00", "WSP_97"],
        "compliance_evidence": ["https://example.invalid/opaque"],
    }


def test_wsp00_envelope_accepts_valid_worker_identity() -> None:
    res = validate_worker_wsp00_envelope(
        {
            "self": "0102",
            "role": "worker",
            "origin": "internal_handoff",
            "principal_ref": "012",
            "worker_id": "worker-a",
            "verifier_id": "verifier-b",
        },
        expected_role="worker",
        require_verifier_separation=True,
    )
    assert res.ok is True
    assert res.code == WSP00_ENVELOPE_VALID
    assert res.locked_self == ALLOWED_WORKER_SELF
    assert res.locked_role == "worker"
    assert res.no_repo_mutation_performed is True
    assert res.no_authority_granted is True
    assert res.self_issued_receipt_not_independent_verification is True


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ("not-a-mapping", FAIL_ENVELOPE_TYPE),
        ({"self": "012", "role": "worker", "origin": "internal_handoff", "principal_ref": "012"}, FAIL_SELF_IS_012),
        ({"self": "9999", "role": "worker", "origin": "internal_handoff", "principal_ref": "012"}, FAIL_INVALID_SELF),
        ({"self": "0102", "role": "admin", "origin": "internal_handoff", "principal_ref": "012"}, FAIL_INVALID_ROLE),
        ({"self": "0102", "role": "worker", "origin": "bad_origin", "principal_ref": "012"}, FAIL_INVALID_ORIGIN),
        ({"self": "0102", "role": "worker", "origin": "internal_handoff", "principal_ref": "   "}, FAIL_MISSING_PRINCIPAL_REF),
    ],
)
def test_wsp00_envelope_rejects_invalid_identity_fields(payload, expected_code: str) -> None:
    res = validate_worker_wsp00_envelope(payload)
    assert res.ok is False
    assert res.code == expected_code
    assert res.no_authority_granted is True


def test_wsp00_envelope_rejects_role_escalation_and_self_verification() -> None:
    escalated = validate_worker_wsp00_envelope(
        {"self": "0102", "role": "architect", "origin": "internal_handoff", "principal_ref": "012"},
        expected_role="worker",
    )
    assert escalated.ok is False and escalated.code == FAIL_ROLE_ESCALATION

    implicit = validate_worker_wsp00_envelope(
        {
            "self": "0102", "role": "worker", "claimed_role": "architect",
            "origin": "internal_handoff", "principal_ref": "012",
        }
    )
    assert implicit.ok is False and implicit.code == FAIL_IMPLICIT_ROLE_ESCALATION

    same_verifier = validate_worker_wsp00_envelope(
        {
            "self": "0102", "role": "worker", "origin": "internal_handoff",
            "principal_ref": "012", "worker_id": "agent-1", "verifier_id": "agent-1",
        }
    )
    assert same_verifier.ok is False and same_verifier.code == FAIL_SELF_VERIFICATION_PROHIBITED

    missing_verifier = validate_worker_wsp00_envelope(
        {"self": "0102", "role": "worker", "origin": "internal_handoff", "principal_ref": "012", "worker_id": "a"},
        require_verifier_separation=True,
    )
    assert missing_verifier.ok is False and missing_verifier.code == FAIL_SELF_VERIFICATION_PROHIBITED


def test_build_worker_wsp97_prompt_contract_loads_canonical_protocol() -> None:
    prompt_contract = build_worker_wsp97_prompt_contract(role="worker", agent_profile="0102")
    assert prompt_contract.role == "worker"
    assert prompt_contract.receipt_schema_version == RECEIPT_SCHEMA_VERSION
    assert "self=0102" in prompt_contract.system_prompt
    assert "role=worker" in prompt_contract.system_prompt
    assert "architect intent != worker truth" in prompt_contract.system_prompt
    assert "retrieve before stating" in prompt_contract.cot_gate
    assert "dialectic sweep before committing" in prompt_contract.cor_gate
    assert len(prompt_contract.required_actions) == 9
    assert len(prompt_contract.mantra_stages) == 7

    with pytest.raises(ValueError):
        build_worker_wsp97_prompt_contract(role="unknown_role")
    with pytest.raises(ValueError):
        build_worker_wsp97_prompt_contract(role="worker", agent_profile="nonexistent")


def test_validate_worker_wsp97_receipt_accepts_valid_repo_bound_receipt(tmp_path: Path) -> None:
    repo, base_commit = _temporary_repository(tmp_path)
    res = validate_worker_wsp97_receipt(
        _valid_receipt(base_commit),
        repo_root=repo,
        expected_base=base_commit,
        worker_id="worker-1",
        verifier_id="verifier-2",
    )
    assert res.ok is True
    assert res.code == WSP97_RECEIPT_VALID
    assert res.is_compliant is True
    assert res.structurally_complete is True
    assert res.validated_base_commit == base_commit
    assert res.self_issued_receipt_not_independent_verification is True


def test_validate_worker_wsp97_receipt_fails_closed_on_invalid_inputs(tmp_path: Path) -> None:
    repo, base_commit = _temporary_repository(tmp_path)
    assert validate_worker_wsp97_receipt(["bad"], repo_root=repo).code == FAIL_RECEIPT_INVALID_TYPE
    assert validate_worker_wsp97_receipt(_valid_receipt(base_commit), repo_root=None).code == FAIL_REPO_ROOT_REQUIRED
    assert validate_worker_wsp97_receipt(
        _valid_receipt(base_commit), repo_root=repo, worker_id="a", verifier_id="a"
    ).code == FAIL_SELF_VERIFICATION_PROHIBITED

    bad_base = validate_worker_wsp97_receipt(_valid_receipt(base_commit), repo_root=repo, expected_base="not-a-sha")
    assert bad_base.ok is False and bad_base.code == FAIL_RECEIPT_VALIDATION_ERROR

    missing_wsp = _valid_receipt(base_commit)
    missing_wsp["action_evidence"]["retrieve_wsps"] = ["WSP_framework/src/WSP_999_Missing.md"]
    non_compliant = validate_worker_wsp97_receipt(missing_wsp, repo_root=repo, expected_base=base_commit)
    assert non_compliant.ok is False
    assert non_compliant.code == FAIL_RECEIPT_NON_COMPLIANT
    assert non_compliant.is_compliant is False


def test_module_has_no_shell_git_execution_or_filesystem_mutation_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {"subprocess", "os", "shutil", "socket", "requests", "urllib", "holo_index"}
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_module_attrs = {"run", "Popen", "system", "popen", "remove", "unlink", "rmdir", "replace", "rename"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id in {"subprocess", "os", "shutil", "Path"}:
                    assert node.func.attr not in banned_module_attrs
