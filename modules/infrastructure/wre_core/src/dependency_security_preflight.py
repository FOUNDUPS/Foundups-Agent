#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dependency/CVE preflight checks for startup gating."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


_CACHE_SCHEMA_VERSION = "dependency_security_preflight.v3"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _run(cmd: List[str], timeout_sec: int = 180, cwd: Path | None = None) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
            timeout=timeout_sec,
            cwd=str(cwd) if cwd else None,
        )
        stderr = _decode_output(completed.stderr, errors="replace")
        try:
            stdout = _decode_output(completed.stdout, errors="strict")
        except UnicodeDecodeError:
            return {
                "ok": False,
                "failure_kind": "invalid_stdout_encoding",
                "code": int(completed.returncode),
                "stdout": "",
                "stderr": "invalid_utf8_scanner_stdout",
                "cmd": cmd,
                "cwd": str(cwd) if cwd else "",
            }
        return {
            "ok": True,
            "failure_kind": "",
            "code": int(completed.returncode),
            "stdout": stdout,
            "stderr": stderr,
            "cmd": cmd,
            "cwd": str(cwd) if cwd else "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "failure_kind": "process_error",
            "code": 127,
            "stdout": "",
            "stderr": str(exc),
            "cmd": cmd,
            "cwd": str(cwd) if cwd else "",
        }


def _decode_output(value: object, *, errors: str) -> str:
    if isinstance(value, str):
        return value
    return bytes(value or b"").decode("utf-8", errors=errors)


def _resolve_tool(name: str) -> str:
    """Resolve executable name in a Windows-safe way (supports .cmd wrappers)."""
    candidates = [name]
    if os.name == "nt" and "." not in name:
        candidates = [f"{name}.cmd", f"{name}.exe", f"{name}.bat", name]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return name


def _empty_counts() -> Dict[str, int]:
    return {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}


def _load_scanner_json(stdout: str) -> object:
    if not str(stdout or "").strip():
        raise ValueError("empty_scanner_json")
    try:
        return json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("malformed_scanner_json") from exc


def _count_pip_audit(stdout: str) -> Dict[str, int]:
    """Parse and validate a pip-audit JSON payload."""
    counts = _empty_counts()
    payload = _load_scanner_json(stdout)

    # pip-audit historically emitted a list; newer versions emit
    # {"dependencies":[...], "fixes":[...]}.
    deps: List[Dict[str, Any]] = []
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise ValueError("invalid_pip_dependency_entry")
        deps = list(payload)
    elif isinstance(payload, dict):
        raw_deps = payload.get("dependencies")
        if not isinstance(raw_deps, list) or not all(
            isinstance(item, dict) for item in raw_deps
        ):
            raise ValueError("invalid_pip_dependencies")
        deps = list(raw_deps)
    else:
        raise ValueError("invalid_pip_payload")

    for pkg in deps:
        vulns = pkg.get("vulns", [])
        if not isinstance(vulns, list) or not all(
            isinstance(vuln, dict) for vuln in vulns
        ):
            raise ValueError("invalid_pip_vulnerabilities")
        for vuln in vulns:
            sev = str(vuln.get("severity", "unknown")).strip().lower()
            if sev in counts:
                counts[sev] += 1
            elif sev == "moderate":
                counts["medium"] += 1
            else:
                counts["unknown"] += 1
    return counts


def _count_npm_audit(stdout: str) -> Dict[str, int]:
    counts = _empty_counts()
    payload = _load_scanner_json(stdout)
    if not isinstance(payload, dict) or not isinstance(payload.get("metadata"), dict):
        raise ValueError("invalid_npm_metadata")
    vulns = payload["metadata"].get("vulnerabilities")
    if not isinstance(vulns, dict):
        raise ValueError("invalid_npm_vulnerabilities")
    values = {
        key: _nonnegative_int(vulns.get(key), field=f"npm_{key}")
        for key in ("info", "low", "moderate", "high", "critical", "total")
    }
    if values["total"] != sum(
        values[key] for key in ("info", "low", "moderate", "high", "critical")
    ):
        raise ValueError("invalid_npm_total")
    counts["unknown"] = values["info"]
    for key in ("critical", "high", "moderate", "low"):
        value = values[key]
        if key == "moderate":
            counts["medium"] = value
        else:
            counts[key] = value
    return counts


def _count_cargo_audit(stdout: str) -> Dict[str, int]:
    counts = _empty_counts()
    payload = _load_scanner_json(stdout)
    if not isinstance(payload, dict) or not isinstance(payload.get("vulnerabilities"), dict):
        raise ValueError("invalid_cargo_vulnerabilities")
    block = payload["vulnerabilities"]
    found = block.get("found")
    count = _nonnegative_int(block.get("count"), field="cargo_count")
    vulns = block.get("list")
    if not isinstance(vulns, list) or not all(isinstance(item, dict) for item in vulns):
        raise ValueError("invalid_cargo_vulnerability_list")
    if not isinstance(found, bool) or count != len(vulns) or found != (count > 0):
        raise ValueError("invalid_cargo_summary")
    for vuln in vulns:
        sev = str(vuln.get("severity", "unknown")).strip().lower()
        if sev in counts:
            counts[sev] += 1
        elif sev == "moderate":
            counts["medium"] += 1
        else:
            counts["unknown"] += 1
    return counts


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"invalid_{field}")
    if value < 0:
        raise ValueError(f"invalid_{field}")
    return value


def _validated_counts(
    result: Dict[str, Any],
    parser: Callable[[str], Dict[str, int]],
    *,
    allowed_exit_codes: frozenset[int],
) -> tuple[Optional[Dict[str, int]], str, bool]:
    if not result.get("ok"):
        kind = str(result.get("failure_kind") or "process_error")
        return None, str(result.get("stderr") or kind)[:240], kind != "process_error"
    code = int(result.get("code", 127))
    if code not in allowed_exit_codes:
        return None, f"unexpected_scanner_exit:{code}", True
    try:
        return parser(str(result.get("stdout") or "")), f"exit={code}", False
    except (TypeError, ValueError):
        return None, "invalid_scanner_json_evidence", True


def _merge_counts(dest: Dict[str, int], source: Dict[str, int]) -> None:
    for key in ("critical", "high", "medium", "low", "unknown"):
        dest[key] = int(dest.get(key, 0)) + int(source.get(key, 0))


def _iter_node_lockfiles(repo_root: Path, scope: str) -> List[Path]:
    scope_norm = str(scope or "all").strip().lower()
    if scope_norm in {"root", "repo-root", "main"}:
        root_lock = repo_root / "package-lock.json"
        return [root_lock] if root_lock.exists() else []
    results: List[Path] = []
    for lock in repo_root.rglob("package-lock.json"):
        rel_parts = lock.relative_to(repo_root).parts
        if rel_parts and str(rel_parts[0]).startswith("."):
            # Skip hidden top-level folders (typically nested worktrees/cache dirs).
            continue
        if "node_modules" in rel_parts:
            continue
        if ".git" in rel_parts:
            continue
        if ".worktrees" in rel_parts:
            continue
        # Skip lockfiles inside nested git repositories/worktrees.
        nested_repo = False
        probe = lock.parent
        while probe != repo_root:
            if (probe / ".git").exists():
                nested_repo = True
                break
            probe = probe.parent
        if nested_repo:
            continue
        results.append(lock)
    return sorted(results)


def _cache_path(repo_root: Path) -> Path:
    return (
        repo_root
        / "modules/infrastructure/wre_core/reports/dependency_security_cache.json"
    )


def _file_identity(path: Path, repo_root: Path) -> Dict[str, Any]:
    try:
        stat = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            label = str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            label = str(path)
        return {"path": label, "size": stat.st_size, "digest": digest}
    except OSError:
        return {"path": str(path), "missing": True}


def _tool_identity(name: str) -> Dict[str, Any]:
    resolved = Path(sys.executable) if name == "python" else Path(_resolve_tool(name))
    if not resolved.is_absolute() or not resolved.exists():
        return {"name": name, "resolved": str(resolved), "missing": True}
    stat = resolved.stat()
    return {
        "name": name,
        "resolved": str(resolved),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _python_environment_digest() -> str:
    packages = sorted(
        f"{str(dist.metadata.get('Name') or '').lower()}=={dist.version}"
        for dist in metadata.distributions()
    )
    raw = "\n".join(packages).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _cache_context_digest(
    repo_root: Path,
    *,
    config: Dict[str, Any],
    node_lockfiles: List[Path],
    cargo_lockfiles: List[Path],
) -> str:
    payload = {
        "config": config,
        "python_environment_digest": _python_environment_digest(),
        "tools": [
            _tool_identity(name) for name in ("python", "npm", "cargo")
        ],
        "node_locks": [_file_identity(path, repo_root) for path in node_lockfiles],
        "cargo_locks": [_file_identity(path, repo_root) for path in cargo_lockfiles],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _load_cache(path: Path) -> Dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("schema_version") == _CACHE_SCHEMA_VERSION:
            return payload
    except Exception:
        return None
    return None


def _cached_status(
    payload: Dict[str, Any] | None, *, config: Dict[str, Any],
    context_digest: str, now: float, ttl_sec: int,
) -> Dict[str, Any] | None:
    if not payload or payload.get("cache_context_digest") != context_digest:
        return None
    if payload.get("cache_config") != config:
        return None
    for key in (
        "ttl_sec", "require_tools", "max_critical", "max_high",
        "max_unknown", "node_lock_scope",
    ):
        if payload.get(key) != config.get(key):
            return None
    checked_at = payload.get("checked_at")
    if isinstance(checked_at, bool) or not isinstance(checked_at, (int, float)):
        return None
    if not math.isfinite(checked_at):
        return None
    if checked_at <= 0 or checked_at > now or now - checked_at >= max(ttl_sec, 0):
        return None
    try:
        totals = _validated_totals(payload.get("totals"))
        tool_failures = _nonnegative_int(payload.get("tool_failures"), field="tool_failures")
        evidence_failures = _nonnegative_int(
            payload.get("evidence_failures"), field="evidence_failures"
        )
        expected = _status_passed(totals, config, tool_failures, evidence_failures)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload.get("passed"), bool) or payload["passed"] != expected:
        return None
    return _cached_advisory(config, context_digest, checked_at, ttl_sec)


def _cached_advisory(
    config: Dict[str, Any], context_digest: str, checked_at: float, ttl_sec: int,
) -> Dict[str, Any]:
    return {
        "schema_version": _CACHE_SCHEMA_VERSION,
        "available": False, "passed": False, "degraded": True, "cached": True,
        "cache_authority": "ADVISORY_ONLY", "counts_withheld": True,
        "totals": _empty_counts(), "tool_failures": 0, "evidence_failures": 1,
        "checked_at": checked_at, "ttl_sec": ttl_sec,
        "cache_context_digest": context_digest, "cache_config": dict(config),
        "checks": [],
        "message": "cached evidence is unsigned; scanner counts withheld",
    }


def _validated_totals(value: object) -> Dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("invalid_cached_totals")
    return {
        key: _nonnegative_int(value.get(key), field=f"cached_{key}")
        for key in ("critical", "high", "medium", "low", "unknown")
    }


def _save_cache(path: Path, payload: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        return


def _append_scanner_result(
    *,
    result: Dict[str, Any],
    parser: Callable[[str], Dict[str, int]],
    ecosystem: str,
    label: str,
    totals: Dict[str, int],
    checks: List[Dict[str, Any]],
    target: str = "",
) -> tuple[int, int]:
    counts, message, evidence_failure = _validated_counts(
        result,
        parser,
        allowed_exit_codes=frozenset({0, 1}),
    )
    item: Dict[str, Any] = {"ecosystem": ecosystem}
    if target:
        item["target"] = target
    if counts is None:
        item.update(
            available=bool(result.get("ok")),
            passed=False,
            message=message,
            counts=_empty_counts(),
        )
        checks.append(item)
        return 1, int(evidence_failure)
    _merge_counts(totals, counts)
    item.update(
        available=True,
        passed=True,
        message=f"{label} {message}",
        counts=counts,
    )
    checks.append(item)
    return 0, 0


def _run_security_checks(
    repo_root: Path,
    *,
    check_node: bool,
    check_rust: bool,
    node_lockfiles: List[Path],
    cargo_lockfiles: List[Path],
) -> tuple[Dict[str, int], List[Dict[str, Any]], int, int, int]:
    totals = _empty_counts()
    checks: List[Dict[str, Any]] = []
    failures = [0, 0]
    py_cmd = [sys.executable, "-m", "pip_audit", "-f", "json", "--progress-spinner", "off"]
    result = _append_scanner_result(
        result=_run(py_cmd, timeout_sec=240), parser=_count_pip_audit,
        ecosystem="python", label="pip-audit", totals=totals,
        checks=checks,
    )
    failures = [sum(values) for values in zip(failures, result)]
    if check_node:
        for lock in node_lockfiles:
            cmd = [_resolve_tool("npm"), "audit", "--json", "--package-lock-only", "--omit=dev"]
            result = _append_scanner_result(
                result=_run(cmd, timeout_sec=300, cwd=lock.parent),
                parser=_count_npm_audit, ecosystem="node", label="npm audit",
                totals=totals, checks=checks,
                target=str(lock.relative_to(repo_root)).replace("\\", "/"),
            )
            failures = [sum(values) for values in zip(failures, result)]
    if check_rust:
        for lock in cargo_lockfiles:
            result = _append_scanner_result(
                result=_run(
                    [_resolve_tool("cargo"), "audit", "--json"],
                    timeout_sec=300,
                    cwd=lock.parent,
                ),
                parser=_count_cargo_audit, ecosystem="rust", label="cargo audit",
                totals=totals, checks=checks,
                target=str(lock.relative_to(repo_root)).replace("\\", "/"),
            )
            failures = [sum(values) for values in zip(failures, result)]
    return totals, checks, failures[0], failures[1], len(node_lockfiles)


def _status_passed(
    totals: Dict[str, int],
    policy: Dict[str, Any],
    tool_failures: int,
    evidence_failures: int,
) -> bool:
    threshold_failure = (
        totals["critical"] > int(policy["max_critical"])
        or totals["high"] > int(policy["max_high"])
        or totals["unknown"] > int(policy["max_unknown"])
    )
    return not threshold_failure and tool_failures == 0 and evidence_failures == 0


def _build_status(
    *,
    totals: Dict[str, int],
    checks: List[Dict[str, Any]],
    now: float,
    ttl_sec: int,
    require_tools: bool,
    thresholds: tuple[int, int, int],
    node_lock_scope: str,
    node_lock_count: int,
    cargo_lock_count: int,
    tool_failures: int,
    evidence_failures: int,
    cache_context_digest: str,
    cache_config: Dict[str, Any],
) -> Dict[str, Any]:
    max_critical, max_high, max_unknown = thresholds
    policy = {"max_critical": max_critical, "max_high": max_high, "max_unknown": max_unknown}
    passed = _status_passed(totals, policy, tool_failures, evidence_failures)
    degraded = not passed and evidence_failures == 0 and tool_failures > 0
    return {
        "schema_version": _CACHE_SCHEMA_VERSION,
        "available": tool_failures == 0 and evidence_failures == 0,
        "passed": passed, "degraded": degraded,
        "checked_at": now, "cached": False, "cache_authority": "LIVE_SCAN",
        "cache_context_digest": cache_context_digest,
        "cache_config": dict(cache_config), "counts_withheld": False,
        "ttl_sec": ttl_sec, "require_tools": require_tools,
        "max_critical": max_critical, "max_high": max_high, "max_unknown": max_unknown,
        "node_lock_scope": node_lock_scope, "node_lock_count": node_lock_count,
        "cargo_lock_count": cargo_lock_count,
        "totals": totals, "tool_failures": tool_failures,
        "evidence_failures": evidence_failures, "checks": checks,
        "message": (
            f"critical={totals['critical']} high={totals['high']} "
            f"unknown={totals['unknown']} tool_failures={tool_failures} "
            f"evidence_failures={evidence_failures}"
        ),
    }


def _preflight_config(runtime_24x7: bool) -> Dict[str, Any]:
    return {
        "ttl_sec": _env_int("OPENCLAW_DEP_SECURITY_PREFLIGHT_TTL_SEC", 21600),
        "require_tools": _env_bool("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", runtime_24x7),
        "max_critical": _env_int("OPENCLAW_DEP_SECURITY_MAX_CRITICAL", 0),
        "max_high": _env_int("OPENCLAW_DEP_SECURITY_MAX_HIGH", 0),
        "max_unknown": _env_int("OPENCLAW_DEP_SECURITY_MAX_UNKNOWN", 0),
        "check_node": _env_bool("OPENCLAW_DEP_SECURITY_CHECK_NODE", True),
        "check_rust": _env_bool("OPENCLAW_DEP_SECURITY_CHECK_RUST", True),
        "node_lock_scope": str(os.getenv(
            "OPENCLAW_DEP_SECURITY_NODE_LOCK_SCOPE", "all"
        )).strip().lower(),
    }


def run_dependency_security_preflight(repo_root: Path, force: bool = False) -> Dict[str, Any]:
    """Run Python/Node/Rust dependency security checks with TTL cache."""
    repo_root = Path(repo_root).resolve()
    runtime_24x7 = _env_bool("OPENCLAW_24X7", False)
    config = _preflight_config(runtime_24x7)
    thresholds = tuple(config[key] for key in ("max_critical", "max_high", "max_unknown"))
    node_lockfiles = _iter_node_lockfiles(
        repo_root, config["node_lock_scope"]
    ) if config["check_node"] else []
    cargo_lockfiles = sorted(repo_root.glob("**/Cargo.lock")) if config["check_rust"] else []
    context_digest = _cache_context_digest(
        repo_root, config=config, node_lockfiles=node_lockfiles,
        cargo_lockfiles=cargo_lockfiles,
    )
    cache = _cache_path(repo_root)
    now = time.time()
    enforced = _env_bool("OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED", runtime_24x7)
    if not force and not enforced:
        cached = _cached_status(
            _load_cache(cache), config=config, context_digest=context_digest,
            now=now, ttl_sec=config["ttl_sec"],
        )
        if cached:
            return cached

    totals, checks, tool_failures, evidence_failures, node_lock_count = (
        _run_security_checks(
            repo_root, check_node=config["check_node"], check_rust=config["check_rust"],
            node_lockfiles=node_lockfiles, cargo_lockfiles=cargo_lockfiles,
        )
    )
    status = _build_status(
        totals=totals, checks=checks, now=now, ttl_sec=config["ttl_sec"],
        require_tools=config["require_tools"], thresholds=thresholds,
        node_lock_scope=config["node_lock_scope"], node_lock_count=node_lock_count,
        cargo_lock_count=len(cargo_lockfiles),
        tool_failures=tool_failures, evidence_failures=evidence_failures,
        cache_context_digest=context_digest,
        cache_config=config,
    )
    _save_cache(cache, status)
    return status
