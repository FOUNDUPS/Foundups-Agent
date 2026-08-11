"""Isolated collection diagnostics for canonical WRE test-registry shards."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

from .wre_git_commit_archive import materialize_git_commit
from .wre_python_environment_fingerprint import python_environment_fingerprint
from .wre_test_registry import TestShard, load_canonical_test_registry

SCHEMA_VERSION = "wre_test_shard_collection_receipt.v1"
MAX_SELECTED_SHARDS = 256
MAX_COLLECTION_TIMEOUT_S = 120
def collect_registered_test_shards(
    repo_root: Path | str, *, head_sha: str, shard_ids: Sequence[str]
) -> dict[str, Any]:
    """Report collection for selected shards without granting test authority."""
    root = Path(repo_root).resolve(strict=True)
    collector = Path(__file__).with_name("wre_pytest_collection_collector.py")
    collector_digest = _file_digest(collector)
    environment = python_environment_fingerprint()
    try:
        with tempfile.TemporaryDirectory(prefix="foundups-wre-collect-") as raw:
            output_root = Path(raw).resolve()
            materialized = output_root / "source"
            materialize_git_commit(root, head_sha, materialized, output_root)
            registry = load_canonical_test_registry(materialized)
            requested = _requested_ids(shard_ids)
            available = {
                shard.shard_id: shard for shard in registry.automated_shards()
            }
            if not requested or any(value not in available for value in requested):
                return _rejected(registry.registry_digest, "test_shard_selection_invalid")
            results = []
            for index, shard_id in enumerate(requested):
                results.append(_collect_one(
                    root=materialized, collector=collector,
                    output=output_root / f"{index}.json",
                    shard=available[shard_id], collector_digest=collector_digest,
                ))
    except (OSError, ValueError, subprocess.SubprocessError):
        return _rejected("", "test_shard_materialization_failed")
    return _receipt(
        registry=registry, head_sha=head_sha, collector_digest=collector_digest,
        environment=environment, requested=requested, results=results,
    )
def _receipt(
    *, registry: Any, head_sha: str, collector_digest: str,
    environment: Mapping[str, Any], requested: Sequence[str],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    complete = all(item["status"] == "COLLECTION_REPORTED" for item in results)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "registry_digest": registry.registry_digest,
        "head_sha": head_sha,
        "collector_digest": collector_digest,
        "python_environment_digest": environment["digest"],
        "python_package_count": environment["package_count"],
        "python_version": environment["python_version"],
        "selected_shard_ids": list(requested),
        "results": results,
        "reported_successful_shards": sum(
            item["status"] == "COLLECTION_REPORTED" for item in results
        ),
        "reported_failed_shards": sum(
            item["status"] != "COLLECTION_REPORTED" for item in results
        ),
        "collection_reported_complete": complete,
        "quarantined_test_files": registry.quarantined_count,
        "test_body_execution_absence_verified": False,
        "collector_integrity_verified": False,
        "receipt_authentication_verified": False,
        "diagnostic_only": True,
        "execution_authority_verified": False,
        "source_worktree_non_execution_verified": False,
    }
    payload["receipt_id"] = _digest(payload)
    return payload
def _collect_one(
    *, root: Path, collector: Path, output: Path, shard: TestShard,
    collector_digest: str,
) -> dict[str, Any]:
    sandbox_home = output.parent / "home"
    sandbox_home.mkdir(exist_ok=True)
    env = {
        name: os.environ[name] for name in (
            "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "VIRTUAL_ENV",
            "PYTHONUTF8", "PYTHONIOENCODING",
        ) if os.environ.get(name)
    }
    env["PYTHONNOUSERSITE"] = "1"
    env["HOME"] = str(sandbox_home)
    env["USERPROFILE"] = str(sandbox_home)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(collector), "--output", str(output), "--",
             *shard.paths],
            cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=min(shard.timeout_s, MAX_COLLECTION_TIMEOUT_S),
            shell=False, check=False,
        )
        report = _report(output) if output.is_file() else {}
    except (OSError, subprocess.SubprocessError):
        completed, report = None, {}
    valid = _valid_report(report) and completed is not None and completed.returncode == 0
    return {
        "shard_id": shard.shard_id,
        "owner": shard.owner,
        "suite_class": shard.suite_class,
        "plan_digest": shard.plan_digest,
        "collector_digest": collector_digest,
        "status": "COLLECTION_REPORTED" if valid else "COLLECTION_FAILED",
        "collected_count": len(report.get("collected_ids", ())) if valid else 0,
        "collected_ids": report.get("collected_ids", []) if valid else [],
        "ordinary_import_guard_reported_passed": report.get(
            "ordinary_import_guard_reported_passed", False
        ),
        "blocked_import_origins": report.get("blocked_import_origins", []),
        "report_digest": _digest(report) if report else "",
        "collection_errors": report.get("collection_errors", []) if report else [{
            "nodeid": shard.shard_id, "detail": "collector_process_failed",
        }],
    }
def _valid_report(report: Mapping[str, Any]) -> bool:
    return bool(
        set(report) == {
            "schema_version", "collection_reported_complete", "pytest_exit_code",
            "collection_errors", "collected_ids",
            "test_body_execution_absence_verified",
            "ordinary_import_guard_reported_passed", "blocked_import_origins",
            "collector_integrity_verified",
        }
        and report.get("schema_version") == "wre_pytest_collection_report.v3"
        and report.get("collection_reported_complete") is True
        and report.get("pytest_exit_code") == 0
        and report.get("collection_errors") == []
        and report.get("test_body_execution_absence_verified") is False
        and report.get("ordinary_import_guard_reported_passed") is True
        and report.get("blocked_import_origins") == []
        and report.get("collector_integrity_verified") is False
        and _canonical_strings(report.get("collected_ids"))
    )
def _requested_ids(values: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        return ()
    if len(values) > MAX_SELECTED_SHARDS:
        return ()
    if not all(isinstance(value, str) and value for value in values):
        return ()
    return tuple(values) if len(values) == len(set(values)) else ()
def _canonical_strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and value == sorted(set(value))


def _report(path: Path) -> Mapping[str, Any]:
    if path.stat().st_size > 64 * 1024 * 1024:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, Mapping) else {}


def _rejected(registry_digest: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "registry_digest": registry_digest,
        "collection_reported_complete": False, "rejection_reasons": [reason],
        "test_body_execution_absence_verified": False,
        "collector_integrity_verified": False,
        "receipt_authentication_verified": False, "diagnostic_only": True,
        "execution_authority_verified": False,
        "source_worktree_non_execution_verified": False,
    }


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = ["SCHEMA_VERSION", "collect_registered_test_shards"]
