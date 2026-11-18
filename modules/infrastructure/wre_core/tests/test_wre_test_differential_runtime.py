from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import pickle
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    verify_autonomous_slice_runtime,
)
from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
    produce_independent_slice_evidence,
)
from modules.infrastructure.wre_core.src.wre_test_differential_runtime import (
    POLICY_SCHEMA,
    produce_test_differential_evidence,
)
from modules.infrastructure.wre_core.src.wre_test_differential_verification import (
    verify_test_differential_evidence,
)
from modules.infrastructure.wre_core.src.wre_test_differential_capability import (
    ProducedTestDifferentialCapability,
)
from modules.infrastructure.wre_core.src import wre_independent_test_evidence_runtime as checks_runtime


DIGEST = "sha256:" + "a" * 64


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True,
        encoding="utf-8", check=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "candidate"
    (repo / "tests").mkdir(parents=True)
    _git(repo.parent, "init", str(repo))
    _git(repo, "config", "user.email", "wre@example.invalid")
    _git(repo, "config", "user.name", "WRE Test")
    (repo / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (repo / "demo.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (repo / "tests/test_base.py").write_text(
        "from demo import value\n\ndef test_pass(): assert value() == 1\n"
        "def test_known_failure(): assert value() == 2\n", encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "tests/test_added.py").write_text(
        "from demo import value\n\ndef test_added(): assert value() == 1\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "candidate")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _policy(**updates: object) -> dict[str, object]:
    result = {
        "schema_version": POLICY_SCHEMA,
        "impact_class": "SYSTEMIC",
        "selection_args": [".", "-q"],
        "timeout_s": 60,
        "dependency_evidence_stale": False,
        "protected_authority_surface": False,
        "release_candidate": False,
        "periodic_health_audit": False,
        "security_closure_required": False,
        "held_out_closure_required": False,
        "omitted_scope_rationale": "full repository health is separately scheduled",
    }
    result.update(updates)
    return result


def _authority() -> dict[str, object]:
    authority = {
        "authority_id": "authority-test-differential",
        "work_order_id": "wo-test-differential",
        "wsp15_allocation_receipt_id": "sha256:" + "1" * 64,
        "wsp15_allocation_digest": "sha256:" + "2" * 64,
    }
    return {
        **authority, "accepted": True,
        "signature_gate_digest": canonical_work_authority_digest(authority),
    }


def _canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def _commit_receipt(request: dict[str, object]) -> dict[str, object]:
    work_order = request["bound_work_order"]
    payload = {
        "schema_version": "reddog_resident_queue_exact_sha_commit_receipt.v1",
        "work_order_id": request["work_order_id"], "queue_item_id": "queue-1",
        "selected_slice": request["slice_name"], "base_sha": request["base_sha"],
        "head_sha": request["head_sha"], "parent_sha": request["base_sha"],
        "tree_sha": "c" * 40, "branch_name": "feat/test-differential",
        "worktree_path": request["worktree_path"],
        "changed_paths": request["expected_changed_paths"],
        "bounded_worker_receipt_id": "bounded-test", "bounded_worker_receipt_digest": DIGEST,
        "worktree_create_result_digest": DIGEST, "commit_message_digest": DIGEST,
        "work_order_digest": canonical_full_work_order_digest(work_order),
        "commit_attempt_key": DIGEST, "chain_state_digest": DIGEST,
        "effect_commit_state": "COMMITTED", "reconciliation_required": False,
        "reconciled_existing_commit": False, "main_checkout_untouched": True,
        "no_push_performed": True, "no_pr_created": True, "no_merge_performed": True,
        "no_holoindex_reindex_performed": True, "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }
    return {"receipt_id": _canonical_digest(payload), **payload}


def _request(repo: Path, base: str, head: str, **updates: object) -> dict[str, object]:
    authority_root = repo.parent / "authority-root"
    authority_root.mkdir(exist_ok=True)
    result = {
        "explicit_evidence_production_requested": True,
        "work_order_id": "wo-test-differential", "slice_name": "TEST_DIFFERENTIAL",
        "worker_id": "worker:author", "verifier_id": "worker:verifier",
        "assurance_reservation_id": "assurance-reservation-test",
        "assurance_reservation_digest": "sha256:" + "4" * 64,
        "verifier_task_id": "reddog-worker-dispatch-test",
        "base_sha": base, "head_sha": head, "repo_root": str(authority_root),
        "worktree_path": str(repo), "operation_cwd": str(repo),
        "allowed_path_patterns": ["tests/**"],
        "expected_changed_paths": ["tests/test_added.py"],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "required_checks": [{
            "name": "pytest", "argv": ["python", "-m", "pytest", ".", "-q"],
            "timeout_s": 60,
        }],
        "test_impact_policy": _policy(), "signed_authority": _authority(),
        "holoindex_evidence": {
            "index_gap_detected": False, "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": "sha256:" + "3" * 64,
        },
    }
    result.update(updates)
    result["bound_work_order"] = {
        "work_order_id": result["work_order_id"],
        "slice_verifier_plan": {"test_impact_policy": result["test_impact_policy"]},
    }
    result["exact_sha_commit_receipt"] = _commit_receipt(result)
    return result


def test_exact_parent_failures_and_added_pass_are_accepted(tmp_path: Path) -> None:
    repo, base, head = _repository(tmp_path)
    (repo / "demo.py").write_text("def value():\n    return 99\n", encoding="utf-8")
    request = _request(repo, base, head)
    produced = produce_independent_slice_evidence(request)
    assert produced.accepted is True, produced.rejection_reasons
    evidence = produced.test_evidence["differential_evidence"]
    differential = evidence["differential"]
    assert differential["unchanged_failures"] == ("tests/test_base.py::test_known_failure",)
    assert differential["added_passing_tests"] == ("tests/test_added.py::test_added",)
    assert differential["differential_clean"] is True
    request["test_differential_capability"] = produced.test_differential_capability
    assert verify_test_differential_evidence(evidence, request=request)[0] is True


def test_final_verifier_rejects_local_only_differential(tmp_path: Path) -> None:
    repo, base, head = _repository(tmp_path)
    request = _request(repo, base, head)
    produced = produce_independent_slice_evidence(request)
    verifier_request = {
        **request, "assurance_reservation_id": "assurance-reservation-test",
        "assurance_reservation_digest": "sha256:" + "4" * 64,
        "verifier_task_id": "reddog-worker-dispatch-test",
        "diff_evidence": produced.diff_evidence, "test_evidence": produced.test_evidence,
        "signed_receipt_chain": {"accepted": True, "terminal_receipt_hash": "sha256:" + "5" * 64},
        "worktree_receipt": {"accepted": True, "receipt_id": "sha256:" + "6" * 64},
        "pattern_memory_write_performed": False, "draft_pr_published": False,
        "merge_performed": False,
        "test_differential_capability": produced.test_differential_capability,
    }
    result = verify_autonomous_slice_runtime(
        verifier_request,
        trusted_work_authority_digest=request["signed_authority"]["signature_gate_digest"],
    )
    assert result.accepted is False
    assert "FAIL_TEST_EVIDENCE" in result.rejection_reasons
    attack_produced = produce_independent_slice_evidence(request)
    attack = deepcopy({
        key: value for key, value in verifier_request.items()
        if key != "test_differential_capability"
    })
    attack["test_evidence"] = attack_produced.test_evidence
    attack["test_differential_capability"] = attack_produced.test_differential_capability
    attack["test_evidence"]["differential_evidence"]["differential"]["new_failures"] = ["forged"]
    assert verify_autonomous_slice_runtime(
        attack,
        trusted_work_authority_digest=request["signed_authority"]["signature_gate_digest"],
    ).accepted is False


def test_lock_drift_and_selection_substitution_fail_closed(tmp_path: Path) -> None:
    repo, base, head = _repository(tmp_path)
    (repo / "requirements.txt").write_text("pytest==0\n", encoding="utf-8")
    _git(repo, "add", "requirements.txt")
    _git(repo, "commit", "-m", "lock drift")
    drift_head = _git(repo, "rev-parse", "HEAD")
    drift = _request(
        repo, head, drift_head, expected_changed_paths=["requirements.txt"],
        allowed_path_patterns=["requirements.txt"],
    )
    assert produce_test_differential_evidence(
        drift, worktree_path=repo, repo_root=repo.parent / "authority-root"
    ).accepted is False
    repo2, base2, head2 = _repository(tmp_path / "selection")
    mismatch = _request(repo2, base2, head2)
    mismatch["test_impact_policy"] = _policy(selection_args=["tests/test_base.py", "-q"])
    result = produce_independent_slice_evidence(mismatch)
    assert result.accepted is False


def test_malformed_differential_mapping_never_raises() -> None:
    hostile = {"schema_version": "wre_test_differential_runtime_receipt.v1", "plan": [[]]}
    assert verify_test_differential_evidence(hostile, request={}) == (False, "", "")


def test_deeply_nested_differential_never_recurses() -> None:
    hostile: object = "leaf"
    for _ in range(100):
        hostile = {"nested": hostile}
    assert verify_test_differential_evidence(hostile, request={}) == (False, "", "")


def test_raw_self_hashed_evidence_has_no_authority(tmp_path: Path) -> None:
    repo, base, head = _repository(tmp_path)
    request = _request(repo, base, head)
    produced = produce_independent_slice_evidence(request)
    assert verify_test_differential_evidence(
        produced.test_evidence["differential_evidence"], request=request,
    ) == (False, "", "")


def test_signed_policy_or_work_order_substitution_rejects(tmp_path: Path) -> None:
    repo, base, head = _repository(tmp_path)
    request = _request(repo, base, head)
    produced = produce_independent_slice_evidence(request)
    evidence = produced.test_evidence["differential_evidence"]
    hostile = deepcopy(request)
    hostile["test_impact_policy"]["selection_args"] = ["tests", "-q"]
    hostile["test_differential_capability"] = produced.test_differential_capability
    assert verify_test_differential_evidence(evidence, request=hostile) == (False, "", "")
    request["test_differential_capability"] = produced.test_differential_capability
    assert verify_test_differential_evidence(evidence, request=request)[0] is True


def test_differential_capability_is_opaque_one_use(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        ProducedTestDifferentialCapability()
    repo, base, head = _repository(tmp_path)
    request = _request(repo, base, head)
    produced = produce_independent_slice_evidence(request)
    capability = produced.test_differential_capability
    with pytest.raises(TypeError):
        pickle.dumps(capability)
    request["test_differential_capability"] = capability
    evidence = produced.test_evidence["differential_evidence"]
    assert verify_test_differential_evidence(evidence, request=request)[0] is True
    assert verify_test_differential_evidence(evidence, request=request) == (False, "", "")


def test_candidate_source_mutation_is_rejected(tmp_path: Path) -> None:
    repo, base, head = _repository(tmp_path)
    (repo / "tests/test_mutate.py").write_text(
        "from pathlib import Path\n\ndef test_mutate():\n"
        "    (Path(__file__).parents[1] / 'demo.py').write_text('changed')\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "candidate mutation")
    mutated_head = _git(repo, "rev-parse", "HEAD")
    request = _request(
        repo, head, mutated_head,
        expected_changed_paths=["tests/test_mutate.py"],
    )
    assert produce_independent_slice_evidence(request).accepted is False


def test_candidate_process_does_not_receive_unrelated_environment(
    tmp_path: Path, monkeypatch,
) -> None:
    repo, base, head = _repository(tmp_path)
    marker = "WRE_TEST_UNRELATED_MARKER"
    monkeypatch.setenv(marker, "must-not-cross")
    (repo / "tests/test_environment.py").write_text(
        f"import os\n\ndef test_scrubbed(): assert {marker!r} not in os.environ\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "environment check")
    checked_head = _git(repo, "rev-parse", "HEAD")
    request = _request(
        repo, head, checked_head,
        expected_changed_paths=["tests/test_environment.py"],
    )
    assert produce_independent_slice_evidence(request).accepted is True


class _RecordingCheckRunner:
    """Preflight observation only: no command or model is executed."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, **kwargs):
        self.calls.append(tuple(argv))
        return SimpleNamespace(
            returncode=0, timed_out=False, stdout="", stderr="", duration_ms=0,
            stdout_truncated=False, stderr_truncated=False,
        )


def _observe_check_execution(request: dict, tmp_path: Path, monkeypatch):
    runner = _RecordingCheckRunner()
    differential_calls: list[dict] = []

    def fake_differential(req, **kwargs):
        differential_calls.append(dict(req))
        return SimpleNamespace(evidence={}, verification_capability=None, rejection_reasons=())

    monkeypatch.setattr(checks_runtime, "produce_test_differential_evidence", fake_differential)
    result = checks_runtime.execute_independent_test_evidence(
        request, runner=runner, operation_cwd=tmp_path,
        worktree_path=tmp_path, repo_root=tmp_path.parent,
        head_sha=request["head_sha"],
    )
    return result, runner.calls, differential_calls


@pytest.mark.parametrize("policy_owner", ["request", "bound_work_order"])
@pytest.mark.parametrize("policy", [None, False, True, [], ["malformed"], "malformed", 7])
def test_malformed_policy_rejects_before_check_execution(
    tmp_path: Path, monkeypatch, policy_owner: str, policy: object,
) -> None:
    request = _request(tmp_path, "b" * 40, "a" * 40)
    request["test_impact_policy"] = {}
    request["bound_work_order"]["slice_verifier_plan"]["test_impact_policy"] = {}
    if policy_owner == "request":
        request["test_impact_policy"] = policy
    else:
        request["bound_work_order"]["slice_verifier_plan"]["test_impact_policy"] = policy
    result, ordinary, differential = _observe_check_execution(request, tmp_path, monkeypatch)
    assert result.rejection_reasons
    assert ordinary == differential == []


@pytest.mark.parametrize("request_policy", ["absent", "empty", "mismatch"])
def test_bound_policy_cannot_be_dropped_or_substituted_before_execution(
    tmp_path: Path, monkeypatch, request_policy: str,
) -> None:
    request = _request(tmp_path, "b" * 40, "a" * 40)
    if request_policy == "absent":
        request.pop("test_impact_policy")
    elif request_policy == "empty":
        request["test_impact_policy"] = {}
    else:
        request["test_impact_policy"] = _policy(impact_class="MODULAR")
    result, ordinary, differential = _observe_check_execution(request, tmp_path, monkeypatch)
    assert result.rejection_reasons
    assert ordinary == differential == []


@pytest.mark.parametrize("failure", ["late-invalid", "duplicate", "missing", "selection"])
def test_entire_check_plan_preflight_precedes_every_command(
    tmp_path: Path, monkeypatch, failure: str,
) -> None:
    request = _request(tmp_path, "b" * 40, "a" * 40)
    pytest_check = request["required_checks"][0]
    request["required_checks"] = [{"name": "lint", "argv": ["ruff", "check", "."]}, pytest_check]
    if failure == "late-invalid":
        request["required_checks"].append({"name": "invalid", "argv": ["shell", "anything"]})
    elif failure == "duplicate":
        request["required_checks"].append(deepcopy(pytest_check))
    elif failure == "missing":
        request["required_checks"].pop()
    else:
        pytest_check["argv"] = ["python", "-m", "pytest", "tests/other.py", "-q"]
    result, ordinary, differential = _observe_check_execution(request, tmp_path, monkeypatch)
    assert result.rejection_reasons
    assert ordinary == differential == []


@pytest.mark.parametrize("empty_policy", [False, True], ids=["absent", "adapter-empty"])
def test_preflight_preserves_ordinary_check_execution_without_differential_policy(
    tmp_path: Path, monkeypatch, empty_policy: bool,
) -> None:
    request = _request(tmp_path, "b" * 40, "a" * 40, test_impact_policy={})
    if not empty_policy:
        request.pop("test_impact_policy")
        request["bound_work_order"]["slice_verifier_plan"].pop("test_impact_policy")
    result, ordinary, differential = _observe_check_execution(request, tmp_path, monkeypatch)
    assert result.rejection_reasons == ()
    assert len(ordinary) == 1
    assert differential == []


@pytest.mark.parametrize("signal", [
    "dependency_evidence_stale", "protected_authority_surface",
    "release_candidate", "periodic_health_audit",
])
@pytest.mark.parametrize("full_scope", [False, True], ids=["narrow-reject", "full-control"])
def test_force_full_signals_are_applied_before_check_execution(
    tmp_path: Path, monkeypatch, signal: str, full_scope: bool,
) -> None:
    path = "modules/communication/moltbot_bridge/tests/test_leaf.py"
    selection = [".", "-q"] if full_scope else [path, "-q"]
    request = _request(
        tmp_path, "b" * 40, "a" * 40, expected_changed_paths=[path],
        test_impact_policy=_policy(
            impact_class="SYSTEMIC" if full_scope else "ISOLATED",
            selection_args=selection, **{signal: True},
        ),
        required_checks=[
            {"name": "lint", "argv": ["ruff", "check", "."]},
            {"name": "pytest", "argv": ["python", "-m", "pytest", *selection]},
        ],
    )
    result, ordinary, differential = _observe_check_execution(request, tmp_path, monkeypatch)
    if full_scope:
        assert result.rejection_reasons == ()
        assert len(ordinary) == len(differential) == 1
    else:
        assert result.rejection_reasons
        assert ordinary == differential == []


@pytest.mark.parametrize("updates", [
    {"schema_version": "wrong"}, {"timeout_s": True}, {"impact_class": []},
    {"selection_args": None}, {"protected_authority_surface": 0},
])
def test_malformed_policy_fields_fail_before_ordinary_checks(
    tmp_path: Path, monkeypatch, updates: dict,
) -> None:
    request = _request(tmp_path, "b" * 40, "a" * 40, test_impact_policy=_policy(**updates))
    request["required_checks"].insert(0, {"name": "lint", "argv": ["ruff", "check", "."]})
    result, ordinary, differential = _observe_check_execution(request, tmp_path, monkeypatch)
    assert result.rejection_reasons
    assert ordinary == differential == []


def test_narrowed_systemic_selection_fails_before_ordinary_checks(
    tmp_path: Path, monkeypatch,
) -> None:
    path = "modules/communication/moltbot_bridge/tests/test_leaf.py"
    request = _request(
        tmp_path, "b" * 40, "a" * 40, expected_changed_paths=[path],
        test_impact_policy=_policy(selection_args=[path, "-q"]),
        required_checks=[
            {"name": "lint", "argv": ["ruff", "check", "."]},
            {"name": "pytest", "argv": ["python", "-m", "pytest", path, "-q"]},
        ],
    )
    result, ordinary, differential = _observe_check_execution(request, tmp_path, monkeypatch)
    assert result.rejection_reasons
    assert ordinary == differential == []
