"""One-shot RedDog GitHub permission probe bridge.

Reads a JSON packet from stdin, runs the existing read-only GitHub permission
probe, and prints a bounded JSON result. This bridge performs no repo mutation,
no signing, no worktree creation, no enqueue, and no HoloIndex mutation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
    build_probe_backend_from_callable,
    probe_repo_permission,
)


def _read_payload() -> Dict[str, Any]:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:
        return {"_bridge_error": "invalid_json", "_bridge_error_class": type(exc).__name__}
    return payload if isinstance(payload, dict) else {"_bridge_error": "payload_not_object"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _snapshot_payload(snapshot: Any) -> Dict[str, Any]:
    mapped = dict(snapshot.to_repo_permission_snapshot())
    mapped["expires_at"] = snapshot.expires_at
    mapped["repo_full_name"] = snapshot.repo_full_name
    mapped["principal_login"] = snapshot.principal_login
    mapped["principal_provider"] = snapshot.principal_provider
    mapped["can_read"] = snapshot.can_read
    mapped["can_write"] = snapshot.can_write
    mapped["can_admin"] = snapshot.can_admin
    mapped["extension_probe_performed"] = True
    mapped["branch_protection_observed"] = snapshot.branch_protection_observed
    mapped["default_branch"] = snapshot.default_branch
    return mapped


def _result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if payload.get("_bridge_error"):
        return {
            "decision": "GITHUB_PERMISSION_PROBE_REJECT",
            "repo_permission_snapshot": None,
            "probe_performed": False,
            "permission_observed": False,
            "rejection_reasons": [str(payload["_bridge_error"])],
            "no_repo_mutation_performed": True,
            "no_execution_performed": True,
            "no_enqueue_performed": True,
        }

    repo_full_name = str(payload.get("repo_full_name") or "FOUNDUPS/Foundups-Agent")
    ttl_seconds = int(payload.get("ttl_seconds") or 300)
    backend = None
    if payload.get("allow_mock_backend") is True:
        backend_payload = dict(_mapping(payload.get("mock_backend")))
        backend = build_probe_backend_from_callable(lambda _repo: backend_payload)

    snapshot = probe_repo_permission(
        repo_full_name,
        principal_login=(str(payload["principal_login"]) if payload.get("principal_login") else None),
        principal_provider=str(payload.get("principal_provider") or "github"),
        backend=backend,
        ttl_seconds=ttl_seconds,
    )
    observed = snapshot.permission not in {"unknown", "none", ""}
    return {
        "decision": "GITHUB_PERMISSION_PROBE_OBSERVED" if observed else "GITHUB_PERMISSION_PROBE_FAIL_CLOSED",
        "repo_permission_snapshot": _snapshot_payload(snapshot),
        "probe_performed": True,
        "permission_observed": observed,
        "repo_full_name": snapshot.repo_full_name,
        "principal_login": snapshot.principal_login,
        "principal_provider": snapshot.principal_provider,
        "permission": snapshot.permission,
        "can_read": snapshot.can_read,
        "can_write": snapshot.can_write,
        "can_admin": snapshot.can_admin,
        "source": snapshot.source,
        "checked_at": snapshot.checked_at,
        "expires_at": snapshot.expires_at,
        "evidence_digest": snapshot.evidence_digest,
        "raw_secret_included": False,
        "token_scopes_count": len(snapshot.token_scopes),
        "branch_protection_observed": snapshot.branch_protection_observed,
        "default_branch": snapshot.default_branch,
        "rejection_reasons": [] if observed else ["permission_unknown_or_none"],
        "no_repo_mutation_performed": True,
        "no_execution_performed": True,
        "no_enqueue_performed": True,
    }


def main() -> int:
    print(json.dumps(_result(_read_payload()), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
