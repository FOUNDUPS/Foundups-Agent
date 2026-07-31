"""Tests for the repository-bound WSP 97 execution receipt validator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import tools.wsp97_execution_validator as execution_validator
import tools.wsp97_repository_evidence as repository_evidence
from tools.wsp97_execution_validator import (
    DEFAULT_CONTRACT_PATH,
    TRUTH_BOUNDARY,
    load_contract,
    validate_execution_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "be855d74bab9e78105d0ba0fed4ddc935e053284"
SCHEMA_VERSION = "wsp97_execution_receipt.v1.1"
WSP50 = "WSP_framework/src/WSP_50_Pre_Action_Verification_Protocol.md"
WSP97 = "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md"
MIGRATED_RECEIPTS = (
    ROOT
    / "docs"
    / "audits"
    / "ai_intelligence"
    / "CONFIGURED_AUTORESEARCH_GATEWAY_WSP97_EXECUTION_RECEIPT_PHASE1.json",
    ROOT
    / "docs"
    / "audits"
    / "ai_intelligence"
    / "OPENROUTER_MODEL_EXECUTION_CONTROL_EVIDENCE_PHASE_B1_WSP97_EXECUTION_RECEIPT.json",
    ROOT
    / "docs"
    / "audits"
    / "infrastructure"
    / "HOLOINDEX_REDDOG_WSP97_EXECUTION_RECEIPT_PHASE1.json",
    ROOT
    / "docs"
    / "audits"
    / "infrastructure"
    / "HOLOINDEX_QUERY_ROOT_ADMISSION_WSP97_EXECUTION_RECEIPT_PHASE1.json",
)


def _valid_receipt(
    *,
    base_commit: str = BASE_COMMIT,
    retrieve_wsps: list[str] | None = None,
    wsps_applied: list[str] | None = None,
) -> dict:
    contract = load_contract()
    actions = contract["wsp_97"]["operator_actions"]
    evidence = {
        action.lower().replace(" ", "_"): [f"opaque evidence statement {index}"]
        for index, action in enumerate(actions, start=1)
    }
    evidence["retrieve_wsps"] = retrieve_wsps or [WSP50, WSP97]
    return {
        "schema_version": SCHEMA_VERSION,
        "repository_context": {"base_commit": base_commit},
        "execution_id": "slice-001",
        "execution_plane": "local_tools",
        "outcome": "completed",
        "action_evidence": evidence,
        "wsps_applied": wsps_applied or ["WSP_50", "WSP_97"],
        "compliance_evidence": ["https://example.invalid/opaque-never-fetched"],
    }


def _validate(receipt: dict, **kwargs):
    return validate_execution_receipt(
        receipt,
        repo_root=ROOT,
        expected_base=BASE_COMMIT,
        **kwargs,
    )


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
    (wsp_dir / "WSP_50_Pre_Action_Verification_Protocol.md").write_text(
        "# WSP 50\n", encoding="utf-8"
    )
    (wsp_dir / "WSP_97_System_Execution_Prompting_Protocol.md").write_text(
        "# WSP 97\n", encoding="utf-8"
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "test fixture")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_complete_receipt_derives_all_mantra_stages() -> None:
    result = _validate(_valid_receipt())

    assert result.is_compliant is True
    assert result.structurally_complete is True
    assert result.validation_mode == "repository_evidence_v1.1"
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


def test_default_rejects_missing_schema_version() -> None:
    receipt = _valid_receipt()
    del receipt["schema_version"]

    result = _validate(receipt)

    assert result.is_compliant is False
    assert "missing_schema_version" in result.violations


def test_default_rejects_v1_0_schema_version() -> None:
    receipt = _valid_receipt()
    receipt["schema_version"] = "wsp97_execution_receipt.v1.0"

    result = _validate(receipt)

    assert result.is_compliant is False
    assert any(item.startswith("unsupported_schema_version:") for item in result.violations)


def _assert_limit_violation_without_repository(
    receipt: dict,
    expected_violation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_calls: list[object] = []
    process_calls: list[object] = []

    def forbidden_repository(*_args, **_kwargs):
        repository_calls.append(object())
        raise AssertionError("over-limit evidence must stop before repository queries")

    monkeypatch.setattr(
        execution_validator,
        "validate_repository_evidence",
        forbidden_repository,
    )

    def forbidden_process(*_args, **_kwargs):
        process_calls.append(object())
        raise AssertionError("over-limit evidence must not spawn Git")

    monkeypatch.setattr(repository_evidence.subprocess, "run", forbidden_process)
    result = _validate(receipt)

    assert result.is_compliant is False
    assert expected_violation in result.violations
    assert repository_calls == []
    assert process_calls == []


def _assert_repository_preflight_rejects_without_git(
    receipt: dict,
    expected_violation: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    expected_base: str | None = BASE_COMMIT,
) -> None:
    process_calls: list[object] = []

    def forbidden_process(*_args, **_kwargs):
        process_calls.append(object())
        raise AssertionError("repository syntax failure must precede Git")

    monkeypatch.setattr(repository_evidence.subprocess, "run", forbidden_process)
    result = validate_execution_receipt(
        receipt,
        repo_root=ROOT,
        expected_base=expected_base,
    )

    assert result.is_compliant is False
    assert result.structurally_complete is False
    assert expected_violation in result.violations
    assert process_calls == []


def test_receipt_byte_cap_precedes_json_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    byte_limit = getattr(execution_validator, "MAX_RECEIPT_BYTES", 262_144)
    path = tmp_path / "oversized.json"
    path.write_bytes(b"{" + (b" " * byte_limit))
    parse_calls: list[object] = []

    def forbidden_parse(_payload):
        parse_calls.append(object())
        raise AssertionError("oversized receipt must not reach JSON parsing")

    monkeypatch.setattr(execution_validator.json, "loads", forbidden_parse)

    with pytest.raises(ValueError, match="byte limit"):
        execution_validator.load_receipt(path)

    assert parse_calls == []


def test_receipt_mapping_limit_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    limit = getattr(execution_validator, "MAX_RECEIPT_MAPPING_ITEMS", 32)
    receipt.update({f"extra_{index}": index for index in range(limit + 1)})
    _assert_limit_violation_without_repository(
        receipt,
        "receipt_mapping_limit_exceeded",
        monkeypatch,
    )


def test_action_mapping_limit_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    limit = getattr(execution_validator, "MAX_ACTION_EVIDENCE_MAPPING_ITEMS", 32)
    receipt["action_evidence"].update(
        {f"extra_{index}": ["opaque"] for index in range(limit + 1)}
    )
    _assert_limit_violation_without_repository(
        receipt,
        "action_evidence_mapping_limit_exceeded",
        monkeypatch,
    )


def test_evidence_list_limit_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    limit = getattr(execution_validator, "MAX_EVIDENCE_LIST_ITEMS", 128)
    receipt["action_evidence"]["research"] = ["x"] * (limit + 1)
    _assert_limit_violation_without_repository(
        receipt,
        "evidence_list_limit_exceeded:research",
        monkeypatch,
    )


def test_evidence_item_string_limit_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    limit = getattr(execution_validator, "MAX_EVIDENCE_ITEM_BYTES", 4096)
    receipt["action_evidence"]["research"] = ["x" * (limit + 1)]
    _assert_limit_violation_without_repository(
        receipt,
        "evidence_item_string_limit_exceeded:research:0",
        monkeypatch,
    )


def test_retrieve_wsp_path_limit_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    limit = getattr(execution_validator, "MAX_RETRIEVE_WSP_PATH_BYTES", 512)
    receipt["action_evidence"]["retrieve_wsps"] = ["x" * (limit + 1)]
    _assert_limit_violation_without_repository(
        receipt,
        "retrieve_wsp_path_limit_exceeded:0",
        monkeypatch,
    )


def test_retrieve_wsps_count_limit_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    limit = getattr(execution_validator, "MAX_RETRIEVE_WSPS", 64)
    receipt["action_evidence"]["retrieve_wsps"] = [WSP97] * (limit + 1)
    _assert_limit_violation_without_repository(
        receipt,
        "retrieve_wsps_count_limit_exceeded",
        monkeypatch,
    )


def test_aggregate_evidence_limit_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    aggregate_limit = getattr(execution_validator, "MAX_AGGREGATE_EVIDENCE_BYTES", 131_072)
    item_limit = getattr(execution_validator, "MAX_EVIDENCE_ITEM_BYTES", 4096)
    item_count = (aggregate_limit // item_limit) + 1
    receipt["action_evidence"]["research"] = ["x" * item_limit] * item_count
    _assert_limit_violation_without_repository(
        receipt,
        "aggregate_evidence_limit_exceeded",
        monkeypatch,
    )


def test_malformed_evidence_stops_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    receipt["action_evidence"]["research"] = {"not": "a list"}
    _assert_limit_violation_without_repository(
        receipt,
        "invalid_evidence_list:research",
        monkeypatch,
    )


def test_missing_repository_context_is_structurally_incomplete_without_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    receipt.pop("repository_context")
    _assert_repository_preflight_rejects_without_git(
        receipt,
        "invalid_repository_context",
        monkeypatch,
        expected_base=None,
    )


@pytest.mark.parametrize(
    "context",
    [
        {},
        {"base_commit": "f" * 39},
        {"base_commit": "F" * 40},
        {"base_commit": BASE_COMMIT, "unexpected": "field"},
    ],
)
def test_invalid_repository_context_stops_before_git(
    context: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt()
    receipt["repository_context"] = context
    _assert_repository_preflight_rejects_without_git(
        receipt,
        "invalid_repository_context",
        monkeypatch,
        expected_base=None,
    )


def test_invalid_expected_base_syntax_is_operational_before_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_calls: list[object] = []

    def forbidden_process(*_args, **_kwargs):
        process_calls.append(object())
        raise AssertionError("invalid caller base must precede Git")

    monkeypatch.setattr(repository_evidence.subprocess, "run", forbidden_process)

    with pytest.raises(ValueError, match="expected_base"):
        validate_execution_receipt(
            _valid_receipt(),
            repo_root=ROOT,
            expected_base="not-a-commit",
        )

    assert process_calls == []


def test_syntactically_valid_expected_base_mismatch_stops_before_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_repository_preflight_rejects_without_git(
        _valid_receipt(),
        "expected_base_mismatch",
        monkeypatch,
        expected_base="0" * 40,
    )


@pytest.mark.parametrize(
    "invalid_path",
    [
        "/WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        "C:/repo/WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        "WSP_framework/src/../src/WSP_97_System_Execution_Prompting_Protocol.md",
        "WSP_framework/src/wsp_97_System_Execution_Prompting_Protocol.md",
    ],
)
def test_lexically_invalid_retrieve_wsp_stops_before_git(
    invalid_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt(retrieve_wsps=[WSP50, invalid_path])
    _assert_repository_preflight_rejects_without_git(
        receipt,
        "invalid_retrieve_wsp_syntax:1",
        monkeypatch,
    )


@pytest.mark.parametrize("invalid_wsp_id", ["wsp_97", "WSP_97_extra", "WSP_"])
def test_invalid_wsp_identifier_stops_before_git(
    invalid_wsp_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _valid_receipt(wsps_applied=["WSP_50", invalid_wsp_id])
    _assert_repository_preflight_rejects_without_git(
        receipt,
        f"invalid_wsp_identifier:{invalid_wsp_id}",
        monkeypatch,
    )


def test_legacy_structural_mode_is_distinct_and_non_admitting() -> None:
    receipt = _valid_receipt()
    receipt.pop("schema_version")
    receipt.pop("repository_context")

    result = validate_execution_receipt(receipt, legacy_structural=True)

    assert result.structurally_complete is True
    assert result.is_compliant is False
    assert result.validation_mode == "legacy_structural_non_admitting"
    assert "legacy_structural_non_admitting" in result.violations


def test_missing_action_blocks_stage_derivation() -> None:
    receipt = _valid_receipt()
    del receipt["action_evidence"]["dialectic_sweep"]

    result = _validate(receipt)

    assert result.is_compliant is False
    assert result.missing_actions == ("dialectic_sweep",)
    assert "underived_mantra_stage:dialectic_sweep" in result.violations


def test_string_is_not_accepted_as_evidence_list() -> None:
    receipt = _valid_receipt()
    receipt["action_evidence"]["execute"] = "evidence/not-a-list.json"

    result = _validate(receipt)

    assert result.is_compliant is False
    assert result.invalid_evidence_actions == ("execute",)
    assert "underived_mantra_stage:build" in result.violations


def test_blocked_outcome_can_still_be_compliant() -> None:
    receipt = _valid_receipt()
    receipt["outcome"] = "blocked"
    receipt["action_evidence"]["execute"] = ["opaque blocker evidence"]

    assert _validate(receipt).is_compliant is True


def test_follow_wsp_requires_wsp97_and_compliance_evidence() -> None:
    receipt = _valid_receipt(wsps_applied=["WSP_50"])
    receipt["compliance_evidence"] = []

    result = _validate(receipt)

    assert result.is_compliant is False
    assert "wsp_97_not_declared" in result.violations
    assert "missing_compliance_evidence" in result.violations
    assert "underived_mantra_stage:follow_wsp" in result.violations


@pytest.mark.parametrize(
    "invalid_path",
    [
        "HoloIndex was queried before direct file reads.",
        "/WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        "C:/repo/WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        "//server/share/WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        "WSP_framework/src/../src/WSP_97_System_Execution_Prompting_Protocol.md",
        r"WSP_framework\src\WSP_97_System_Execution_Prompting_Protocol.md",
        "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md#section",
        "https://example.invalid/WSP_97_System_Execution_Prompting_Protocol.md",
    ],
)
def test_retrieve_wsps_rejects_noncanonical_or_escaping_paths(invalid_path: str) -> None:
    receipt = _valid_receipt(retrieve_wsps=[WSP50, invalid_path])

    result = _validate(receipt)

    assert result.is_compliant is False
    assert any(
        item.startswith("invalid_retrieve_wsp_syntax:")
        for item in result.violations
    )


def test_retrieve_wsps_rejects_untracked_or_missing_file() -> None:
    receipt = _valid_receipt(
        retrieve_wsps=[
            WSP50,
            "WSP_framework/src/WSP_999_Not_A_Tracked_Protocol.md",
            WSP97,
        ]
    )

    result = _validate(receipt)

    assert result.is_compliant is False
    assert any("not_tracked" in item for item in result.violations)


def test_retrieve_wsps_rejects_wrong_syntactic_case_before_git() -> None:
    receipt = _valid_receipt(
        retrieve_wsps=[
            WSP50,
            "WSP_framework/src/wsp_97_System_Execution_Prompting_Protocol.md",
        ]
    )

    result = _validate(receipt)

    assert result.is_compliant is False
    assert "invalid_retrieve_wsp_syntax:1" in result.violations


def test_every_declared_wsp_must_have_a_retrieved_canonical_path() -> None:
    receipt = _valid_receipt(wsps_applied=["WSP_22", "WSP_50", "WSP_97"])

    result = _validate(receipt)

    assert result.is_compliant is False
    assert "wsp_not_retrieved:WSP_22" in result.violations


def test_retrieved_precedent_wsps_may_exceed_wsps_applied() -> None:
    receipt = _valid_receipt(
        retrieve_wsps=[
            "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
            WSP50,
            WSP97,
        ]
    )

    assert _validate(receipt).is_compliant is True


def test_non_wsp_evidence_remains_opaque_and_urls_are_never_fetched() -> None:
    receipt = _valid_receipt()
    receipt["action_evidence"]["research"] = [
        "https://127.0.0.1:1/must-not-be-fetched",
        "missing/local/evidence.txt",
    ]

    assert _validate(receipt).is_compliant is True


def test_expected_base_mismatch_is_noncompliant() -> None:
    result = validate_execution_receipt(
        _valid_receipt(),
        repo_root=ROOT,
        expected_base="0" * 40,
    )

    assert result.is_compliant is False
    assert "expected_base_mismatch" in result.violations


def test_unknown_base_commit_is_noncompliant() -> None:
    receipt = _valid_receipt(base_commit="f" * 40)

    result = validate_execution_receipt(receipt, repo_root=ROOT)

    assert result.is_compliant is False
    assert "base_commit_not_found" in result.violations


def test_existing_nonancestor_base_commit_is_noncompliant(tmp_path: Path) -> None:
    repo, common_base = _temporary_repository(tmp_path)
    initial_branch = _git(repo, "branch", "--show-current")
    _git(repo, "checkout", "-b", "unmerged-side")
    (repo / "side.txt").write_text("side\n", encoding="utf-8")
    _git(repo, "add", "side.txt")
    _git(repo, "commit", "-m", "side")
    side_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", initial_branch)
    (repo / "main.txt").write_text("main\n", encoding="utf-8")
    _git(repo, "add", "main.txt")
    _git(repo, "commit", "-m", "main")
    receipt = _valid_receipt(base_commit=side_commit)

    result = validate_execution_receipt(receipt, repo_root=repo)

    assert side_commit != common_base
    assert result.is_compliant is False
    assert "base_commit_not_ancestor" in result.violations


def test_repo_root_must_be_exact_git_toplevel() -> None:
    with pytest.raises(ValueError, match="Git top-level"):
        validate_execution_receipt(
            _valid_receipt(),
            repo_root=ROOT / "tools",
            expected_base=BASE_COMMIT,
        )


def test_reparse_or_symlink_wsp_path_is_rejected(tmp_path: Path) -> None:
    repo, base = _temporary_repository(tmp_path)
    real_path = repo / "WSP_framework" / "src" / "WSP_97_real.md"
    real_path.write_text("# real\n", encoding="utf-8")
    link_path = repo / "WSP_framework" / "src" / "WSP_97_Linked_Protocol.md"
    try:
        os.symlink(real_path.name, link_path)
    except (NotImplementedError, OSError):
        pytest.skip("symlink creation is unavailable on this platform")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "tracked symlink")
    head = _git(repo, "rev-parse", "HEAD")
    receipt = _valid_receipt(
        base_commit=base,
        retrieve_wsps=[
            "WSP_framework/src/WSP_50_Pre_Action_Verification_Protocol.md",
            "WSP_framework/src/WSP_97_Linked_Protocol.md",
        ],
    )

    result = validate_execution_receipt(receipt, repo_root=repo, expected_base=base)

    assert head != base
    assert result.is_compliant is False
    assert any("reparse_or_symlink" in item for item in result.violations)


def test_contract_loader_rejects_declared_count_drift(tmp_path: Path) -> None:
    contract = load_contract()
    contract["wsp_97"]["operator_action_count"] = 8
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")

    with pytest.raises(ValueError, match="operator_action_count"):
        load_contract(path)


def test_contract_loader_rejects_receipt_schema_drift(tmp_path: Path) -> None:
    contract = load_contract()
    contract["wsp_97"]["validator"]["receipt_schema_version"] = "1.0"
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")

    with pytest.raises(ValueError, match="receipt_schema_version"):
        load_contract(path)


def test_canonical_contract_declares_repository_evidence_validator() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    validator = contract["wsp_97"]["validator"]

    assert contract["wsp_97"]["version"] == "1.8"
    assert validator["status"] == "active_repository_evidence_validation"
    assert validator["entrypoint"] == "tools/wsp97_execution_validator.py"
    assert validator["receipt_schema_version"] == SCHEMA_VERSION
    assert validator["resource_limits"] == execution_validator.EXPECTED_RESOURCE_LIMITS


def test_wsp97_framework_and_knowledge_mirrors_are_exact() -> None:
    for suffix in (".md", ".json"):
        name = f"WSP_97_System_Execution_Prompting_Protocol{suffix}"
        framework = (ROOT / "WSP_framework" / "src" / name).read_bytes()
        knowledge = (ROOT / "WSP_knowledge" / "src" / name).read_bytes()
        assert framework == knowledge


def test_wsp81_approval_record_is_complete_and_truthful() -> None:
    notification = (
        ROOT
        / "docs"
        / "audits"
        / "governance"
        / "WSP_97_REPOSITORY_EVIDENCE_V11_WSP81_NOTIFICATION_20260724.md"
    ).read_text(encoding="utf-8")
    framework_modlog = (ROOT / "WSP_framework" / "ModLog.md").read_text(
        encoding="utf-8"
    )
    knowledge_modlog = (ROOT / "WSP_knowledge" / "src" / "ModLog.md").read_text(
        encoding="utf-8"
    )

    for evidence in (
        "**Approval Class**: APPROVAL_REQUIRED",
        "**Approval Required**: YES",
        "**Approval Satisfied**: YES",
        "**Approval Source**: Explicit 012/user direction",
        f"**Base Commit**: `{BASE_COMMIT}`",
        "post-run accepted-output cap, not a write-time tempfile bound",
    ):
        assert evidence in notification
    assert "Approval class: APPROVAL_REQUIRED" in framework_modlog
    assert "approval satisfied: YES" in framework_modlog
    assert "Approval class: APPROVAL_REQUIRED" in knowledge_modlog


@pytest.mark.parametrize("receipt_path", MIGRATED_RECEIPTS)
def test_current_base_receipts_are_v1_1_compliant(receipt_path: Path) -> None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    result = _validate(receipt)

    assert result.is_compliant is True, result.violations


def test_cli_returns_one_for_noncompliant_receipt(tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps({"execution_id": "incomplete"}), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "wsp97_execution_validator.py"),
            str(receipt_path),
            "--repo-root",
            str(ROOT),
            "--expected-base",
            BASE_COMMIT,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["is_compliant"] is False
    assert payload["truth_boundary"] == TRUTH_BOUNDARY


def test_cli_returns_two_when_repository_root_is_unreadable(tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(_valid_receipt()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "wsp97_execution_validator.py"),
            str(receipt_path),
            "--repo-root",
            str(tmp_path / "missing"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert json.loads(completed.stderr)["error"]


def test_cli_oversized_receipt_returns_two_before_parse(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "oversized.json"
    path.write_bytes(b"{" + (b" " * execution_validator.MAX_RECEIPT_BYTES))

    assert execution_validator.main([str(path)]) == 2
    assert "byte limit" in json.loads(capsys.readouterr().err)["error"]


def test_cli_over_limit_evidence_returns_one_without_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    receipt = _valid_receipt()
    limit = getattr(execution_validator, "MAX_EVIDENCE_LIST_ITEMS", 128)
    receipt["action_evidence"]["research"] = ["x"] * (limit + 1)
    path = tmp_path / "over-limit.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")

    def forbidden_repository(*_args, **_kwargs):
        raise AssertionError("Git/repository validation must not run")

    monkeypatch.setattr(
        execution_validator,
        "validate_repository_evidence",
        forbidden_repository,
    )

    assert execution_validator.main([str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["is_compliant"] is False


def test_cli_missing_repository_context_returns_one_without_root_or_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    receipt = _valid_receipt()
    receipt.pop("repository_context")
    path = tmp_path / "missing-context.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")

    def forbidden_process(*_args, **_kwargs):
        raise AssertionError("malformed receipt must not spawn Git")

    monkeypatch.setattr(repository_evidence.subprocess, "run", forbidden_process)

    assert execution_validator.main([str(path)]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["structurally_complete"] is False
    assert "invalid_repository_context" in payload["violations"]


def test_cli_invalid_expected_base_syntax_returns_two_without_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(_valid_receipt()), encoding="utf-8")

    def forbidden_process(*_args, **_kwargs):
        raise AssertionError("invalid caller base must not spawn Git")

    monkeypatch.setattr(repository_evidence.subprocess, "run", forbidden_process)

    assert execution_validator.main(
        [
            str(path),
            "--repo-root",
            str(ROOT),
            "--expected-base",
            "not-a-commit",
        ]
    ) == 2
    assert "expected_base" in json.loads(capsys.readouterr().err)["error"]


def test_cli_git_timeout_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(_valid_receipt()), encoding="utf-8")

    def timeout_process(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(repository_evidence.subprocess, "run", timeout_process)

    assert execution_validator.main([str(path), "--repo-root", str(ROOT)]) == 2
    assert "timed out" in json.loads(capsys.readouterr().err)["error"]


def test_cli_git_process_failure_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(_valid_receipt()), encoding="utf-8")

    def failed_process(*_args, **_kwargs):
        raise OSError("process unavailable")

    monkeypatch.setattr(repository_evidence.subprocess, "run", failed_process)

    assert execution_validator.main([str(path), "--repo-root", str(ROOT)]) == 2
    assert "could not be started" in json.loads(capsys.readouterr().err)["error"]


def test_cli_legacy_mode_is_labeled_and_never_admits(tmp_path: Path) -> None:
    receipt = _valid_receipt()
    receipt.pop("schema_version")
    receipt.pop("repository_context")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "wsp97_execution_validator.py"),
            str(receipt_path),
            "--legacy-structural",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["validation_mode"] == "legacy_structural_non_admitting"
    assert payload["structurally_complete"] is True
    assert payload["is_compliant"] is False
