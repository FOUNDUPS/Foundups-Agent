"""Tests for read-only RedDog GitHub permission probe."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    DECISION_ACCEPT,
    DECISION_ACCEPT_WITH_GAP,
    DECISION_REJECT,
    validate_work_order_dryrun,
)
from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
    GhCliPermissionProbeBackend,
    build_probe_backend_from_callable,
    is_snapshot_fresh,
    permission_to_capabilities,
    probe_repo_permission,
)


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _backend(**fields):
    payload = {
        "authenticated": True,
        "login": "operator-012",
        "permission": "write",
        "default_branch": "main",
        "scopes": ["repo"],
        "branch_protection_observed": "true",
        "source": "mock",
    }
    payload.update(fields)
    return build_probe_backend_from_callable(lambda _repo: payload)


class TestPermissionCapabilities:
    def test_read_permission(self):
        can_read, can_write, can_admin = permission_to_capabilities("read")
        assert can_read is True
        assert can_write is False
        assert can_admin is False

    def test_write_permission(self):
        can_read, can_write, can_admin = permission_to_capabilities("write")
        assert can_read is True
        assert can_write is True
        assert can_admin is False

    def test_admin_permission_reports_capabilities_without_authorizing_admin_ops(self):
        can_read, can_write, can_admin = permission_to_capabilities("admin")
        assert can_read is True
        assert can_write is True
        assert can_admin is True


class TestProbeRepoPermission:
    def test_unauthenticated_unknown_fail_closed(self):
        backend = _backend(authenticated=False, permission="write", login="unknown")
        snap = probe_repo_permission("FOUNDUPS/Foundups-Agent", backend=backend)
        assert snap.permission == "unknown"
        assert snap.can_read is False
        assert snap.can_write is False
        assert snap.can_admin is False

    def test_read_permission_snapshot(self):
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="read"),
        )
        assert snap.can_read is True
        assert snap.can_write is False
        assert snap.raw_secret_included is False

    def test_write_permission_snapshot(self):
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="write"),
        )
        assert snap.can_write is True
        assert snap.can_admin is False

    def test_admin_permission_snapshot(self):
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="admin"),
        )
        assert snap.can_write is True
        assert snap.can_admin is True

    def test_unknown_permission_fail_closed(self):
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="unexpected-role"),
        )
        assert snap.permission == "unknown"
        assert snap.can_write is False

    def test_token_scopes_not_leaked_in_digest_payload(self):
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(scopes=["repo", "read:org"]),
        )
        assert "ghp_" not in snap.evidence_digest
        assert snap.token_scopes == ["repo", "read:org"]

    def test_snapshot_digest_stable(self):
        fixed = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
        snap_a = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="write"),
            now=fixed,
        )
        snap_b = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="write"),
            now=fixed,
        )
        assert snap_a.evidence_digest == snap_b.evidence_digest
        assert snap_a.evidence_digest.startswith("sha256:")

    def test_stale_snapshot_rejected(self):
        past = datetime(2026, 6, 28, 10, 0, 0, tzinfo=timezone.utc)
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="write"),
            now=past,
            ttl_seconds=60,
        )
        assert is_snapshot_fresh(snap, now=datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)) is False

    def test_to_repo_permission_snapshot_shape(self):
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission="write"),
        )
        mapped = snap.to_repo_permission_snapshot()
        assert set(mapped.keys()) == {"permission_level", "captured_at", "source", "digest"}
        assert mapped["permission_level"] == "write"
        assert mapped["digest"].startswith("sha256:")


class TestDryRunIntegration:
    def _work_order_with_snapshot(self, permission_level: str):
        snap = probe_repo_permission(
            "FOUNDUPS/Foundups-Agent",
            backend=_backend(permission=permission_level),
        )
        return {
            "work_order_id": "wo-perm-001",
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "red_dog_instance_id": "reddog-ext-0.3.27",
            "authenticated_principal": "principal-012",
            "principal_provider": "github",
            "repo_full_name": "FOUNDUPS/Foundups-Agent",
            "repo_permission_snapshot": snap.to_repo_permission_snapshot(),
            "requested_operation": "audit_only",
            "authority_tier": "advisory",
            "allowed_paths": ["docs/**"],
            "denied_paths": [".env"],
            "branch_name": "docs/probe-test",
            "base_ref": "main",
            "task_summary": "Validate permission probe snapshot wiring",
            "wsp_applicability": ["WSP_34", "WSP_50"],
            "holoindex_evidence_refs": [
                "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"
            ],
            "skillz_candidates": [],
            "required_tests": [],
            "required_policy_gates": ["github_permission_fresh"],
            "required_reviewers": [],
            "sentinel_checks": [],
            "rollback_plan": "No mutation performed.",
            "expiry": _future_expiry(),
            "nonce": "nonce-perm-001",
            "evidence_digest": "sha256:" + ("f" * 64),
            "advisory_only_source_packet": {
                "work_focus_digest": "sha256:" + ("a" * 64),
                "wsp_prompt_digest": "sha256:" + ("b" * 64),
                "copy_md_run_trace_digest": "sha256:" + ("c" * 64),
            },
            "holoindex_evidence": {
                "holoindex_query": "RedDog governed repo work order",
                "holoindex_status": "bundle_json_ok",
                "code_hits": [],
                "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
                "skillz_hits": [],
                "direct_read_fallback_used": False,
                "index_gap_detected": True,
                "applicable_wsps": ["WSP_34"],
                "evidence_refs": [],
                "retrieval_quality": "INDEX_GAP",
                "skillz_gap_detected": True,
            },
        }

    def test_snapshot_accepted_by_dry_run_validator(self):
        receipt = validate_work_order_dryrun(
            self._work_order_with_snapshot("write"),
            seen_nonces=set(),
        )
        assert receipt.decision in {DECISION_ACCEPT, DECISION_ACCEPT_WITH_GAP}

    def test_admin_snapshot_still_blocks_admin_operation_in_dry_run(self):
        order = self._work_order_with_snapshot("admin")
        order["requested_operation"] = "grant_permission_admin"
        receipt = validate_work_order_dryrun(order, seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "forbidden_requested_operation" in receipt.rejection_reasons


class TestReadOnlyGhAllowlist:
    def test_non_allowlisted_gh_command_blocked(self):
        from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
            _run_gh_readonly,
        )

        with pytest.raises(ValueError, match="not allowlisted"):
            _run_gh_readonly(["pr", "create"])
