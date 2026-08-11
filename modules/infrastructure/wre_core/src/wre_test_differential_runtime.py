"""Verifier-owned parent/candidate pytest differential execution."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from modules.infrastructure.wre_core.src.wre_test_impact_differential_gate import (
    evaluate_test_differential,
    make_test_impact_plan,
    make_test_run_snapshot,
)
from modules.infrastructure.wre_core.src.wre_test_differential_capability import (
    issue_test_differential_capability,
)
from modules.infrastructure.wre_core.src.wre_test_scope_coverage import (
    resolve_test_scope_coverage,
)
from modules.infrastructure.wre_core.src.wre_git_commit_archive import (
    materialize_git_commit,
)

SCHEMA = "wre_test_differential_runtime_receipt.v1"
POLICY_SCHEMA = "wre_test_impact_policy.v1"
SELECTION_POLICY = "trusted-pytest-exact-id-collector.v1"
FAIL_POLICY = "FAIL_TEST_IMPACT_POLICY"
FAIL_LINEAGE = "FAIL_TEST_BASE_LINEAGE"
FAIL_BASE_MATERIALIZATION = "FAIL_TEST_BASE_MATERIALIZATION"
FAIL_COLLECTION = "FAIL_TEST_COLLECTION_INCOMPLETE"
FAIL_BINDING = "FAIL_TEST_DIFFERENTIAL_RUNTIME_BINDING"
FAIL_SCOPE = "FAIL_TEST_SCOPE_COVERAGE"

_LOCK_NAMES = {
    "Cargo.lock", "package-lock.json", "pnpm-lock.yaml", "poetry.lock",
    "pyproject.toml", "requirements.txt", "uv.lock", "yarn.lock",
}
_MAX_REPORT_BYTES = 64 * 1024 * 1024
_MAX_LOCK_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class TestDifferentialRuntimeResult:
    accepted: bool
    rejection_reasons: tuple[str, ...]
    evidence: dict[str, Any]
    verification_capability: object | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "rejection_reasons": self.rejection_reasons,
            "evidence": self.evidence,
        }


def produce_test_differential_evidence(
    request: Mapping[str, Any], *, worktree_path: Path, repo_root: Path
) -> TestDifferentialRuntimeResult:
    """Run identical trusted collection against exact parent and candidate."""
    req = request if isinstance(request, Mapping) else {}
    policy = _mapping(req.get("test_impact_policy"))
    reasons = _policy_reasons(policy)
    scope = resolve_test_scope_coverage(
        req.get("expected_changed_paths", ()), str(policy.get("impact_class") or ""),
        policy.get("selection_args", ()),
    )
    if not scope.accepted:
        reasons.extend((FAIL_SCOPE, *scope.rejection_reasons))
    base_sha = str(req.get("base_sha") or "")
    head_sha = str(req.get("head_sha") or "")
    collector = Path(__file__).with_name("wre_pytest_exact_id_collector.py").resolve()
    if not collector.is_file():
        reasons.append(FAIL_COLLECTION)
    collector_digest = _file_digest(collector) if collector.is_file() else ""
    lineage_digest = _lineage_digest(worktree_path, base_sha, head_sha)
    if not lineage_digest:
        reasons.append(FAIL_LINEAGE)
    if reasons:
        return _reject(reasons)

    try:
        with tempfile.TemporaryDirectory(prefix="foundups-wre-test-diff-") as raw:
            runtime_root = Path(raw).resolve()
            if _inside(runtime_root, worktree_path) or _inside(runtime_root, repo_root):
                raise ValueError("runtime artifacts must be outside repository roots")
            base_root = runtime_root / "base"
            candidate_root = runtime_root / "candidate"
            materialize_git_commit(worktree_path, base_sha, base_root, runtime_root)
            materialize_git_commit(worktree_path, head_sha, candidate_root, runtime_root)
            result = _run_pair(
                req=req, policy=policy, base_root=base_root,
                candidate_root=candidate_root, runtime_root=runtime_root,
                collector=collector, lineage_digest=lineage_digest,
                collector_digest=collector_digest,
            )
    except (OSError, ValueError, subprocess.SubprocessError):
        return _reject([FAIL_BASE_MATERIALIZATION])
    return result


def _run_pair(
    *, req: Mapping[str, Any], policy: Mapping[str, Any], base_root: Path,
    candidate_root: Path, runtime_root: Path, collector: Path,
    lineage_digest: str, collector_digest: str,
) -> TestDifferentialRuntimeResult:
    args = tuple(str(item) for item in policy["selection_args"])
    timeout_s = int(policy["timeout_s"])
    base_manifest = _source_manifest(base_root)
    candidate_manifest = _source_manifest(candidate_root)
    base_report = _run_collector(collector, base_root, runtime_root / "base.json", args, timeout_s)
    candidate_report = _run_collector(
        collector, candidate_root, runtime_root / "candidate.json", args, timeout_s
    )
    if not _report_ok(base_report) or not _report_ok(candidate_report):
        return _reject([FAIL_COLLECTION])
    if base_manifest != _source_manifest(base_root) or candidate_manifest != _source_manifest(candidate_root):
        return _reject([FAIL_BINDING])
    if _file_digest(collector) != collector_digest:
        return _reject([FAIL_BINDING])
    bindings = _bindings(req, policy, collector, base_root, candidate_root, lineage_digest)
    if not bindings:
        return _reject([FAIL_BINDING])
    plan = make_test_impact_plan(**bindings)
    evidence_author = str(req.get("verifier_id") or "")
    base = _snapshot(
        plan, base_report, str(req["base_sha"]), "base", evidence_author
    )
    candidate = _snapshot(
        plan, candidate_report, str(req["head_sha"]), "candidate",
        evidence_author,
    )
    differential = evaluate_test_differential(plan, base, candidate).to_dict()
    reasons = list(differential["rejection_reasons"])
    evidence = {
        "schema_version": SCHEMA,
        "plan": plan,
        "base_snapshot": base,
        "candidate_snapshot": candidate,
        "differential": differential,
        "collector_digest": collector_digest,
        "base_report_digest": _digest(base_report),
        "candidate_report_digest": _digest(candidate_report),
        "execution_authority_verified": False,
    }
    evidence["receipt_id"] = "wre_test_runtime_" + _digest(evidence)[7:]
    capability = (
        issue_test_differential_capability(evidence, request=req)
        if not reasons else None
    )
    return TestDifferentialRuntimeResult(not reasons, tuple(reasons), evidence, capability)


def _bindings(
    req: Mapping[str, Any], policy: Mapping[str, Any], collector: Path,
    base_root: Path, candidate_root: Path, lineage_digest: str,
) -> dict[str, Any]:
    lock_paths = tuple(sorted(
        set(_base_lock_paths(base_root)) | set(_base_lock_paths(candidate_root))
    ))
    lock_base = _lock_digest(base_root, lock_paths)
    lock_candidate = _lock_digest(candidate_root, lock_paths)
    if not lock_base or lock_base != lock_candidate:
        return {}
    authority = _mapping(req.get("signed_authority"))
    changed = sorted(str(item) for item in req.get("expected_changed_paths", ()))
    return {
        "base_sha": req.get("base_sha"), "candidate_sha": req.get("head_sha"),
        "changed_paths_digest": _digest(changed),
        "impact_class": policy.get("impact_class"),
        "suite_scope_digest": _digest(policy.get("selection_args")),
        "runner_digest": _file_digest(collector),
        "environment_digest": _environment_digest(),
        "dependency_lock_digest": lock_base,
        "selection_policy_digest": _digest(SELECTION_POLICY),
        "selection_args_digest": _digest(policy.get("selection_args")),
        "base_lineage_receipt_digest": lineage_digest,
        "wsp15_allocation_receipt_id": authority.get("wsp15_allocation_receipt_id"),
        "wsp15_allocation_receipt_digest": authority.get("wsp15_allocation_digest"),
        "dependency_evidence_stale": policy.get("dependency_evidence_stale"),
        "protected_authority_surface": policy.get("protected_authority_surface"),
        "release_candidate": policy.get("release_candidate"),
        "periodic_health_audit": policy.get("periodic_health_audit"),
        "security_closure_required": policy.get("security_closure_required"),
        "held_out_closure_required": policy.get("held_out_closure_required"),
        "omitted_scope_rationale": policy.get("omitted_scope_rationale"),
    }


def _snapshot(
    plan: Mapping[str, Any], report: Mapping[str, Any], head_sha: str,
    label: str, evidence_author: str,
) -> dict[str, Any]:
    fields = {name: report[name] for name in (
        "passed_ids", "failed_ids", "error_ids", "skipped_ids",
        "xfailed_ids", "xpassed_ids", "deselected_ids",
    )}
    report_digest = _digest(report)
    return make_test_run_snapshot(
        head_sha=head_sha, suite_kind=plan["required_suite_kind"],
        suite_scope_digest=plan["suite_scope_digest"], runner_digest=plan["runner_digest"],
        environment_digest=plan["environment_digest"],
        dependency_lock_digest=plan["dependency_lock_digest"],
        selection_policy_digest=plan["selection_policy_digest"],
        selection_args_digest=plan["selection_args_digest"],
        base_lineage_receipt_digest=plan["base_lineage_receipt_digest"],
        evidence_receipt_id=f"pytest-exact-id:{label}:{report_digest[7:23]}",
        evidence_receipt_digest=report_digest, evidence_author_id=evidence_author,
        independent=True, security_closure_passed=report.get("security_closure_passed", False),
        held_out_closure_passed=report.get("held_out_closure_passed", False), **fields,
    )


def _run_collector(
    collector: Path, cwd: Path, output: Path, args: Sequence[str], timeout_s: int
) -> dict[str, Any]:
    env = {
        name: os.environ[name] for name in (
            "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "VIRTUAL_ENV",
            "PYTHONUTF8", "PYTHONIOENCODING",
        ) if os.environ.get(name)
    }
    env["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(collector), "--output", str(output), "--", *args],
        cwd=str(cwd), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=timeout_s, shell=False, check=False,
    )
    if completed.returncode != 0 or not output.is_file():
        return {}
    if output.stat().st_size > _MAX_REPORT_BYTES:
        return {}
    return json.loads(output.read_text(encoding="utf-8"))


def _report_ok(report: Mapping[str, Any]) -> bool:
    outcome_names = (
        "passed_ids", "failed_ids", "error_ids", "skipped_ids",
        "xfailed_ids", "xpassed_ids", "deselected_ids",
    )
    expected_keys = {
        "schema_version", "collection_complete", "pytest_exit_code",
        "collection_errors", "collected_ids", *outcome_names,
    }
    if set(report) != expected_keys:
        return False
    lists = [report.get(name) for name in ("collected_ids", *outcome_names)]
    if any(not _canonical_ids(value) for value in lists):
        return False
    groups = [set(report[name]) for name in outcome_names]
    collected = set(report.get("collected_ids", ()))
    return bool(
        report.get("schema_version") == "wre_pytest_exact_id_report.v1"
        and report.get("collection_complete") is True and collected
        and report.get("collection_errors") == []
        and sum(map(len, groups)) == len(set().union(*groups))
        and set().union(*groups) == collected
        and report.get("pytest_exit_code") in (0, 1)
    )


def _canonical_ids(value: Any) -> bool:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return False
    return bool(
        value == sorted(set(value))
        and all(item.strip() == item and item for item in value)
    )


def _policy_reasons(policy: Mapping[str, Any]) -> list[str]:
    keys = {
        "schema_version", "impact_class", "selection_args", "timeout_s",
        "dependency_evidence_stale", "protected_authority_surface",
        "release_candidate", "periodic_health_audit", "security_closure_required",
        "held_out_closure_required", "omitted_scope_rationale",
    }
    valid = (
        set(policy) == keys and policy.get("schema_version") == POLICY_SCHEMA
        and policy.get("impact_class") in {"ISOLATED", "MODULAR", "SYSTEMIC"}
        and isinstance(policy.get("selection_args"), list) and bool(policy.get("selection_args"))
        and all(isinstance(item, str) and item and "\x00" not in item for item in policy.get("selection_args", ()))
        and type(policy.get("timeout_s")) is int and 1 <= policy.get("timeout_s", 0) <= 3600
        and all(type(policy.get(name)) is bool for name in keys if name.endswith("required") or name in {
            "dependency_evidence_stale", "protected_authority_surface", "release_candidate", "periodic_health_audit"
        })
        and isinstance(policy.get("omitted_scope_rationale"), str)
    )
    return [] if valid else [FAIL_POLICY]


def _lineage_digest(repo: Path, base_sha: str, head_sha: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base_sha, head_sha],
        capture_output=True, timeout=30, shell=False, check=False,
    )
    return _digest({"base_sha": base_sha, "head_sha": head_sha, "ancestor": True}) if result.returncode == 0 else ""


def _base_lock_paths(root: Path) -> tuple[str, ...]:
    paths = (
        path.relative_to(root).as_posix() for path in root.rglob("*")
        if path.is_file() and path.name in _LOCK_NAMES
    )
    return tuple(sorted(paths))


def _source_manifest(root: Path) -> str:
    records = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if "/__pycache__/" in f"/{relative}/" or relative.endswith((".pyc", ".pyo")):
            continue
        records.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(records)


def _lock_digest(root: Path, paths: Sequence[str]) -> str:
    records = []
    for relative in paths:
        path = (root / PurePosixPath(relative)).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            return ""
        if path.stat().st_size > _MAX_LOCK_BYTES:
            return ""
        records.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(records)


def _environment_digest() -> str:
    try:
        import pytest
        pytest_version = pytest.__version__
    except ImportError:
        pytest_version = "missing"
    return _digest({"python": platform.python_version(), "implementation": platform.python_implementation(), "pytest": pytest_version})


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    child_r, parent_r = child.resolve(), parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _reject(reasons: Sequence[str]) -> TestDifferentialRuntimeResult:
    return TestDifferentialRuntimeResult(False, tuple(dict.fromkeys(reasons)), {})


__all__ = [
    "FAIL_BASE_MATERIALIZATION", "FAIL_BINDING", "FAIL_COLLECTION", "FAIL_LINEAGE",
    "FAIL_POLICY", "FAIL_SCOPE", "POLICY_SCHEMA", "SCHEMA", "TestDifferentialRuntimeResult",
    "produce_test_differential_evidence",
]
