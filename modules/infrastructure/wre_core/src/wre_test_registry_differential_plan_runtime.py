"""Exact-SHA registry scope projection without test execution."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from .wre_git_commit_archive import materialize_git_commit
from .wre_recognized_dependency_binding import (
    matching_recognized_dependency_digest,
)
from .wre_test_registry_impact_binding import (
    FAIL_POLICY,
    bound_test_impact_plan,
    effective_projection_impact,
    projected_selection_args_digest,
    validated_projection_input,
)
from .wre_test_registry_git_binding import (
    canonical_changed_paths,
    verified_git_plan_inputs,
)
from .wre_test_registry_scope_plan import plan_registry_differential
SCHEMA = "wre_test_registry_scope_projection.v1"
FAIL_LINEAGE = "FAIL_TEST_REGISTRY_PLAN_LINEAGE"
FAIL_CHANGED_PATHS = "FAIL_TEST_REGISTRY_PLAN_CHANGED_PATHS"
FAIL_MATERIALIZATION = "FAIL_TEST_REGISTRY_PLAN_MATERIALIZATION"
FAIL_DEPENDENCIES = "FAIL_TEST_REGISTRY_PLAN_DEPENDENCIES"
FAIL_REPOSITORY = "FAIL_TEST_REGISTRY_PLAN_REPOSITORY"
FAIL_REQUEST = "FAIL_TEST_REGISTRY_PLAN_REQUEST"
_REQUEST_FIELDS = {
    "base_sha", "head_sha", "expected_changed_paths", "projection_input",
}
@dataclass(frozen=True)
class RegistryScopeProjectionResult:
    projected: bool
    rejection_reasons: tuple[str, ...]
    evidence: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "projected": self.projected,
            "rejection_reasons": self.rejection_reasons,
            "evidence": _thaw(self.evidence),
        }
def produce_registry_scope_projection(
    request: Mapping[str, Any], *, worktree_path: Path, repo_root: Path,
) -> RegistryScopeProjectionResult:
    """Materialize exact commits and project bounded shards into the WRE plan."""
    req = _snapshot_request(request)
    if not req:
        return _reject(FAIL_REQUEST)
    inputs = validated_projection_input(req.get("projection_input"))
    if inputs is None:
        return _reject(FAIL_POLICY)
    base_sha, head_sha = str(req.get("base_sha") or ""), str(req.get("head_sha") or "")
    changed = canonical_changed_paths(req.get("expected_changed_paths"))
    try:
        actual, raw_binding = verified_git_plan_inputs(
            worktree_path, repo_root, base_sha, head_sha,
        )
    except ValueError as exc:
        if str(exc) == "git_repository_mismatch":
            return _reject(FAIL_REPOSITORY)
        return _reject(FAIL_LINEAGE)
    except (OSError, RuntimeError, UnicodeError, subprocess.SubprocessError):
        return _reject(FAIL_LINEAGE)
    repository_binding = {
        "worktree_path_digest": _digest(raw_binding["worktree_path"]),
        "repository_common_dir_digest": _digest(raw_binding["repository_common_dir"]),
    }
    if changed is None or changed != actual:
        return _reject(FAIL_CHANGED_PATHS)
    try:
        with tempfile.TemporaryDirectory(prefix="foundups-wre-registry-plan-") as raw:
            runtime_root = Path(raw).resolve()
            if _inside(runtime_root, worktree_path) or _inside(runtime_root, repo_root):
                raise ValueError("runtime_root_inside_repository")
            base_root, candidate_root = runtime_root / "base", runtime_root / "candidate"
            materialize_git_commit(worktree_path, base_sha, base_root, runtime_root)
            materialize_git_commit(worktree_path, head_sha, candidate_root, runtime_root)
            return _plan(
                req, inputs, changed, base_root, candidate_root, repository_binding,
            )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        return _reject(FAIL_MATERIALIZATION)
def _plan(
    req: Mapping[str, Any], inputs: Mapping[str, Any], changed: tuple[str, ...],
    base_root: Path, candidate_root: Path, repository_binding: Mapping[str, str],
) -> RegistryScopeProjectionResult:
    dependency_digest = matching_recognized_dependency_digest(base_root, candidate_root)
    if not dependency_digest:
        return _reject(FAIL_DEPENDENCIES)
    plan = plan_registry_differential(
        base_root, candidate_root, changed_paths=changed,
        requested_impact=effective_projection_impact(inputs),
        max_shards_per_batch=int(inputs["max_shards_per_batch"]),
        max_total_shards=int(inputs["max_total_shards"]),
        max_files=int(inputs["max_files"]),
    )
    if not plan.accepted:
        return RegistryScopeProjectionResult(
            False, plan.rejection_reasons, _freeze({}),
        )
    impact_plan = bound_test_impact_plan(
        inputs, base_sha=str(req["base_sha"]), head_sha=str(req["head_sha"]),
        changed_paths=changed, suite_scope_digest=plan.logical_scope_digest,
        dependency_lock_digest=dependency_digest,
        selection_args_digest=projected_selection_args_digest(plan),
    )
    if impact_plan is None or (
        impact_plan["impact_class"] != plan.impact_class
        or impact_plan["required_suite_kind"] != plan.required_suite_kind
    ):
        return _reject(FAIL_POLICY)
    evidence = _evidence(
        req, changed, plan, impact_plan, dependency_digest, repository_binding,
    )
    evidence["projection_id"] = "wre_registry_scope_" + _digest(evidence)[7:]
    return RegistryScopeProjectionResult(True, (), _freeze(evidence))
def _evidence(
    req: Mapping[str, Any], changed: Sequence[str], plan: Any,
    impact_plan: Mapping[str, Any], dependency_digest: str,
    repository_binding: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA, "base_sha": req["base_sha"],
        "head_sha": req["head_sha"], "changed_paths": list(changed),
        "changed_paths_digest": _digest(changed),
        "lineage_digest": _digest({"base": req["base_sha"], "head": req["head_sha"]}),
        **repository_binding,
        "repository_authority_verified": False,
        "recognized_dependency_digest": dependency_digest,
        "recognized_dependency_parity_verified": True,
        "impact_class": impact_plan["impact_class"],
        "required_suite_kind": impact_plan["required_suite_kind"],
        "logical_scope_digest": plan.logical_scope_digest,
        "test_impact_plan": dict(impact_plan), "base": plan.base.to_dict(),
        "candidate": plan.candidate.to_dict(),
        "systemic_batched": plan.impact_class == "SYSTEMIC",
        "planning_only": True, "test_execution_performed": False,
        "pytest_invoked": False, "candidate_code_executed": False,
        "signed_authority_verified": False, "execution_authority_verified": False,
        "collector_integrity_verified": False, "os_isolation_verified": False,
        "verification_capability_issued": False,
        "execution_status": "BLOCKED_BY_OS_ISOLATED_RUNNER",
    }
def _snapshot_request(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _REQUEST_FIELDS:
        return {}
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        )
        detached = json.loads(raw)
    except (TypeError, ValueError, OverflowError, RuntimeError):
        return {}
    return detached if type(detached) is dict else {}


def _inside(child: Path, parent: Path) -> bool:
    child_r, parent_r = child.resolve(), parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _reject(reason: str) -> RegistryScopeProjectionResult:
    return RegistryScopeProjectionResult(False, (reason,), _freeze({}))


__all__ = [
    "FAIL_CHANGED_PATHS", "FAIL_DEPENDENCIES", "FAIL_LINEAGE",
    "FAIL_MATERIALIZATION", "FAIL_REPOSITORY", "FAIL_REQUEST",
    "RegistryScopeProjectionResult", "produce_registry_scope_projection",
]
