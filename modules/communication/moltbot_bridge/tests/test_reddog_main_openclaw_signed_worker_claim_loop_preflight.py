"""Tests for REDDOG_MAIN_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_PREFLIGHT_PHASE1."""

from __future__ import annotations

import base64
import json
import os
import socket
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW as BOOTSTRAP_NOW,
    PILOT_ARTIFACT,
    PILOT_OPERATION,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    _draft_pr_publish_request,
    _ed25519_signing_material,
    _ed25519_signing_material_with_socket_backend,
    _FakeExactShaEvidenceRunner,
    _FakeWorktreeRunner,
    _pilot_bounded_worker_plan,
    _pilot_allowed_paths,
    _pilot_path_overrides,
    _pilot_payloads,
    _pilot_worktree_path,
    _principals,
    _profile as _bootstrap_profile,
    _repo,
    _snapshot as _bootstrap_snapshot,
    _snapshots,
    _slice_verifier_request,
    _StaticSocketPeerAttestor,
    _valve_environment,
    _work_order,
    _write_runtime_json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    serve_reddog_isolated_signer_socket_bounded,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SIGNING_KEY_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_cli import (
    run_reddog_signer_socket_service_runtime_cli,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_openclaw_queue_loop_runtime_binding import (
    build_reddog_signed_worker_queue_loop_runner_from_env,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    _FakeEnvDraftPrRunner,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
    PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
    resident_queue_materializer_mode,
    resident_queue_runtime_file_path,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


REPO_ROOT = Path(__file__).resolve().parents[4]
CLAIM_LOOP = (
    "modules.communication.moltbot_bridge.src.openclaw_supervisor."
    "claim_reddog_signed_worker_dispatch_tasks_until_idle"
)


class _FakeProfileWorktreeRunner:
    instances: list["_FakeProfileWorktreeRunner"] = []

    def __init__(self, *, repo_root: Path, timeout_s: int) -> None:
        self.repo_root = Path(repo_root)
        self.timeout_s = timeout_s
        self.calls: list[tuple[str, str, str | None, str | None]] = []
        self.__class__.instances.append(self)

    def create_worktree(self, *, worktree_path: Path, branch_name: str, base_ref: str):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_ref))
        Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def cleanup_worktree(self, *, worktree_path: Path):
        self.calls.append(("cleanup_worktree", str(worktree_path), None, None))
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def push_branch(self, *, worktree_path: Path, branch_name: str):
        self.calls.append(("push_branch", str(worktree_path), branch_name, None))
        return {"ok": True, "branch_name": branch_name}

    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str):
        self.calls.append(("create_draft_pr", branch_name, base_branch, title))
        _ = body
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/4242"


class _FakeEnvCommitDraftPrRunner(_FakeEnvDraftPrRunner):
    evidence_runner: _FakeExactShaEvidenceRunner | None = None

    def commit_all(self, *, worktree_path: Path, add_paths, message: str):
        self.calls.append(
            ("commit_all", str(worktree_path), tuple(add_paths), message)
        )
        if self.evidence_runner is None:
            return {"ok": False, "returncode": 1, "stdout": "", "stderr": ""}
        self.evidence_runner.head = "a" * 40
        self.evidence_runner.parent = "b" * 40
        self.evidence_runner.dirty = False
        self.evidence_runner.commit_message = message
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}


def test_profile_materializer_default_does_not_conflict_with_explicit_work_orders() -> None:
    env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree_draft_pr",
        "REDDOG_WORK_ORDERS_PATH": "O:/runtime/work_orders.json",
    }

    assert resident_queue_materializer_mode(env) == ""


def test_explicit_blank_materializer_mode_preserves_profile_default() -> None:
    env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree_draft_pr",
        "REDDOG_WORK_ORDERS_PATH": "O:/runtime/work_orders.json",
        "REDDOG_WORK_ORDER_MATERIALIZER_MODE": "",
    }

    assert resident_queue_materializer_mode(env) == "authority_profile"


def test_profile_signed_worker_queue_loop_runner_materializes_without_work_orders(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    runtime_root.mkdir(parents=True)
    env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
        "REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER": "1",
        "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS": "1",
    }

    result = build_reddog_signed_worker_queue_loop_runner_from_env(repo_root=repo, env=env)

    assert result.accepted is True
    assert result.runner is not None
    assert result.runner.config.bootstrap_kwargs["work_order_materializer_mode"] == "authority_profile"
    assert "work_orders_path" not in result.runner.config.bootstrap_kwargs
    assert result.work_state_path.endswith("authoritative_work_state.json")
    assert result.authority_profile_path.endswith("authority_profile.json")


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    monkeypatch.setenv("OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "1")
    DatabaseManager.reset_for_tests()
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )

    monkeypatch.setattr(
        binding_module,
        "_build_assurance_reservation_store",
        lambda env: _assurance_store(),
    )
    yield
    DatabaseManager.reset_for_tests()


def _assurance_store() -> AgentDB:
    trusted_now = datetime.fromisoformat(BOOTSTRAP_NOW)
    return AgentDB(assurance_now_provider=lambda: trusted_now)


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _cli_private_key_material() -> tuple[object, str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = encode_ed25519_public_key(public_bytes)
    secret = SIGNING_KEY_PREFIX + base64.b64encode(private_bytes).decode("ascii")
    return private_key, public_key, secret


def _cli_audit_secret(raw: bytes) -> str:
    return AUDIT_KEY_PREFIX + base64.b64encode(raw).decode("ascii")


class _FakeCliResolver:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values
        self.calls: list[tuple[str, str | None]] = []

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        self.calls.append((reference, requester_id))
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=60,
            session_id="cli-test-session",
            _secret_value=self.values[reference],
        )


class _FakeCliResolverFactory:
    def __init__(self, values: dict[str, str]) -> None:
        self.resolver = _FakeCliResolver(values)
        self.calls: list[dict[str, object]] = []

    def __call__(
        self,
        *,
        op_executable: str,
        timeout_s: float,
        ttl_seconds: int,
        session_id: str,
    ) -> _FakeCliResolver:
        self.calls.append(
            {
                "op_executable": op_executable,
                "timeout_s": timeout_s,
                "ttl_seconds": ttl_seconds,
                "session_id": session_id,
            }
        )
        return self.resolver


def _cli_key_profile(
    *,
    public_key: str,
    signer_profile_id: str,
    signer_agent_id: str,
    signing_key_ref: str,
    audit_mac_key_ref: str,
) -> dict[str, object]:
    return {
        "signer_profile_id": signer_profile_id,
        "signer_agent_id": signer_agent_id,
        "signing_key_ref": signing_key_ref,
        "audit_mac_key_ref": audit_mac_key_ref,
        "expected_public_key": public_key,
        "expected_key_fingerprint": public_key_fingerprint(public_key),
        "expected_key_epoch": "epoch-1",
        "permission_snapshot_digest": "sha256:permission",
        "ttl_seconds": 60,
    }


def _wait_for_socket(path: Path, *, timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.025)
    return path.exists()


def _patch_fusion_artifact_generator(monkeypatch) -> list[dict[str, object]]:
    from modules.communication.moltbot_bridge.src import (
        reddog_bounded_artifact_generation_runtime as artifact_runtime,
    )

    calls: list[dict[str, object]] = []

    def _fake_fusion(api_key, user_payload, messages, payload):
        calls.append(
            {
                "api_key": api_key,
                "user_payload": user_payload,
                "messages": messages,
                "payload": payload,
            }
        )
        return {
            "ok": True,
            "content": json.dumps(
                {
                    "artifact_contents": {
                        PILOT_ARTIFACT: (
                            "# Generated By Fusion\n\n"
                            "This text came from the bounded artifact generator.\n"
                        )
                    }
                },
                sort_keys=True,
            ),
            "review_packet": {"receipt_id": "fusion-artifact-receipt-1"},
        }

    monkeypatch.setattr(
        artifact_runtime,
        "_load_foundups_fusion_runner",
        lambda: _fake_fusion,
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    return calls


def test_main_openclaw_signed_worker_claim_loop_disabled_by_default() -> None:
    import main

    with patch(CLAIM_LOOP, side_effect=AssertionError("claim loop must not run")):
        with patch.dict("os.environ", {}, clear=True):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True


def test_main_resident_control_loop_enforced_fails_closed_when_profile_signer_socket_missing(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    runtime_root.mkdir(parents=True)
    principal_public, reddog_public, _connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    state_payload = _bootstrap_snapshot()
    state_payload["worker_claims"][0]["expires_at"] = "2099-01-01T00:00:00+00:00"
    state = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_AUTHORITATIVE_WORK_STATE_PATH")),
        state_payload,
    )
    profile = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
            )
        ),
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
            bounded_worker_plan=_pilot_bounded_worker_plan(),
        ),
    )
    snapshots = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_PERMISSION_SNAPSHOTS_PATH")),
        _snapshots(),
    )
    principals = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
            )
        ),
        _principals(principal_public),
    )
    authority_state = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_AUTHORITY_RUNTIME_STATE_PATH")
    )
    valve_env = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_EXECUTION_VALVE_ENV_PATH")),
        _valve_environment(),
    )
    socket_path = Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SOCKET_PATH"))
    chain = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
        )
    )
    assert not socket_path.exists()

    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
    )
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_ENFORCED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "1000")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_PERMISSION_SNAPSHOTS_PATH", str(snapshots))
    monkeypatch.setenv("REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH", str(principals))
    monkeypatch.setenv("REDDOG_EXECUTION_VALVE_ENV_PATH", str(valve_env))
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_STATE_PATH", str(authority_state))
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY", "0")
    monkeypatch.delenv("REDDOG_WORK_ORDERS_PATH", raising=False)

    with patch(CLAIM_LOOP, side_effect=AssertionError("claim loop must not run after signer reject")):
        assert main.run_reddog_resident_queue_control_loop_preflight(repo) is False

    captured = capsys.readouterr().out
    assert "governed_execution_valve_environment_required" in captured
    assert "[REDDOG-QUEUE-CONTROL] preflight=FAIL" in captured
    assert main.run_reddog_resident_queue_serial_loop_preflight.last_result["accepted"] is False
    assert authority_state.exists() is False
    assert chain.exists() is False


def test_main_openclaw_signed_worker_claim_loop_passes_when_idle(capsys) -> None:
    import main

    with patch(
        CLAIM_LOOP,
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE",
            "claimed_count": 0,
            "completed_task_ids": (),
            "requeued_task_ids": (),
            "failed_task_ids": (),
            "rejection_reasons": ("NO_PENDING_TASK",),
        },
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1",
                "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "3",
            },
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["repo_root"] == REPO_ROOT
    assert mocked.call_args.kwargs["max_claims"] == 3
    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "claimed_count=0" in captured
    assert "max_claims=3" in captured


def test_main_openclaw_signed_worker_claim_loop_profile_enables_control_plane() -> None:
    import main

    with patch(
        CLAIM_LOOP,
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE",
            "claimed_count": 0,
            "completed_task_ids": (),
            "requeued_task_ids": (),
            "failed_task_ids": (),
            "rejection_reasons": ("NO_PENDING_TASK",),
        },
    ) as mocked:
        with patch.dict(
            "os.environ",
            {"REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code"},
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True

    assert mocked.call_count == 1


def test_main_openclaw_signed_worker_claim_loop_explicit_zero_overrides_profile() -> None:
    import main

    with patch(CLAIM_LOOP, side_effect=AssertionError("claim loop must not run")):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True


def test_main_openclaw_signed_worker_claim_loop_blocks_when_enforced() -> None:
    import main

    with patch(
        CLAIM_LOOP,
        return_value={
            "accepted": False,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT",
            "claimed_count": 0,
            "completed_task_ids": (),
            "requeued_task_ids": (),
            "failed_task_ids": ("task-1",),
            "rejection_reasons": ("CLAIM_REJECTED",),
        },
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1",
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED": "1",
            },
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is False


def test_main_openclaw_signed_worker_claim_loop_rejects_invalid_max_claims_when_enforced() -> None:
    import main

    with patch(CLAIM_LOOP, side_effect=AssertionError("claim loop must not run")):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1",
                "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED": "1",
                "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "0",
            },
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is False


def test_main_openclaw_signed_worker_claim_loop_exception_is_nonblocking_by_default() -> None:
    import main

    with patch(CLAIM_LOOP, side_effect=RuntimeError("agentdb unavailable")):
        with patch.dict(
            "os.environ",
            {"REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP": "1"},
            clear=True,
        ):
            assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(REPO_ROOT) is True


def test_main_openclaw_signed_worker_claim_loop_runs_real_agentdb_queue_stage(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main

    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
    )
    work_order["holoindex_evidence"] = {
        **dict(work_order["holoindex_evidence"]),
        "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
    }
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        runtime_allowed_root=tmp_path / "runtime",
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
        assurance_reservation_store=_assurance_store(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission"
    assert worktree.exists()
    assert not (worktree / PILOT_ARTIFACT).exists()

    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )

    task_id = next(
        task["task_id"]
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and task["context"].get("capability") == "queue_stage_progress"
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH", str(generic_writer))
    monkeypatch.setenv("REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH", str(governed_shell))
    monkeypatch.setenv("REDDOG_ARTIFACT_CONTENTS_PATH", str(artifacts))
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    with patch(
        "modules.infrastructure.database.src.agent_db.AgentDB",
        _assurance_store,
    ):
        assert (
            main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo)
            is True
        )

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE" in captured
    assert "claimed_count=0" in captured
    assert "requeued=(none)" in captured
    assert "receipts=(none)" in captured
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["assurance_capacity_admission"]
    assert stage["decision"] == "ASSURANCE_CAPACITY_ADMISSION_ACCEPT"
    assert stage["reservation"]["status"] == "RESERVED"
    assert stage["no_bounded_worker_pilot_performed"] is True
    assert stage["no_repo_mutation_performed"] is True
    assert not (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()


def test_main_openclaw_signed_0102_bounded_code_uses_fusion_artifact_generation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.communication.moltbot_bridge.src import (
        reddog_main_resident_queue_serial_loop_bootstrap as bootstrap_module,
    )
    from modules.foundups.agent.src import worktree_pr_runner

    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
    )
    work_order["holoindex_evidence"] = {
        **dict(work_order["holoindex_evidence"]),
        "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
    }
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        runtime_allowed_root=tmp_path / "runtime",
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
        assurance_reservation_store=_assurance_store(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission"
    assert worktree.exists()
    assert not (worktree / PILOT_ARTIFACT).exists()

    evidence_runner = _FakeExactShaEvidenceRunner(
        branch_name=str(work_order["branch_name"])
    )
    _FakeEnvCommitDraftPrRunner.evidence_runner = evidence_runner
    monkeypatch.setattr(
        worktree_pr_runner,
        "RealWorktreeRunner",
        _FakeEnvCommitDraftPrRunner,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "_build_evidence_command_runner",
        lambda *args, **kwargs: (evidence_runner, ()),
    )
    calls = _patch_fusion_artifact_generator(monkeypatch)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    task_id = next(
        task["task_id"]
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and task["context"].get("capability") == "bounded_code_change"
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_PILOT_DRYRUN_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "1")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv(
        "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH",
        str(generic_writer),
    )
    monkeypatch.setenv(
        "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH",
        str(governed_shell),
    )
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")

    assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT" in captured
    assert "claimed_count=1" in captured
    assert f"completed={task_id}" in captured
    assert "requeued=(none)" in captured
    assert "receipts=signed_worker_task_execution_" in captured
    assert str(
        main.run_reddog_openclaw_signed_worker_claim_loop_preflight.last_result[
            "receipt_ids"
        ][0]
    ).startswith("signed_worker_task_execution_")
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"
    assert calls
    assert calls[0]["api_key"] == "test-openrouter-key"
    payload = calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["mode"] == "foundups_fusion"
    assert payload["response_contract"] == "strict_json_bounded_artifact_contents.v1"
    assert "artifact_generation_binding" in payload["bridge_meta"]

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["bounded_worker_pilot"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    generation = stage["artifact_generation_result"]
    assert generation["accepted"] is True
    assert generation["receipt"]["model_receipt_id"] == "fusion-artifact-receipt-1"
    assert generation["model_result"]["made_network_call"] is True
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8").startswith(
        "# Generated By Fusion"
    )
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "REDDOG_ARTIFACT_CONTENTS_PATH" not in os.environ


def test_main_openclaw_signed_worker_claim_loop_completes_env_bound_chain(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.communication.moltbot_bridge.src import (
        reddog_main_resident_queue_serial_loop_bootstrap as bootstrap_module,
    )
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeEnvDraftPrRunner.instances.clear()
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
    )
    work_order["holoindex_evidence"] = {
        **dict(work_order["holoindex_evidence"]),
        "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
    }
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        runtime_allowed_root=tmp_path / "runtime",
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
        assurance_reservation_store=_assurance_store(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "assurance_capacity_admission"

    evidence_runner = _FakeExactShaEvidenceRunner(
        branch_name=str(work_order["branch_name"])
    )
    _FakeEnvCommitDraftPrRunner.evidence_runner = evidence_runner
    monkeypatch.setattr(
        worktree_pr_runner,
        "RealWorktreeRunner",
        _FakeEnvCommitDraftPrRunner,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "_build_evidence_command_runner",
        lambda *args, **kwargs: (evidence_runner, ()),
    )
    calls = _patch_fusion_artifact_generator(monkeypatch)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier_request = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    outcome_store = tmp_path / "runtime" / "outcomes" / "signed-worker-ratchet.jsonl"
    pattern_memory_db = tmp_path / "runtime" / "pattern_memory.db"

    pending = AgentDB().get_autonomous_tasks(status="pending", limit=10)
    signed_tasks = [
        task
        for task in pending
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert len(signed_tasks) == 2
    assigned_verifiers = [
        task
        for task in AgentDB().get_autonomous_tasks(status="assigned", limit=10)
        if task.get("discovered_by")
        == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and task["context"].get("capability")
        == "independent_slice_verification"
    ]
    assert len(assigned_verifiers) == 1
    coding_task_id = next(
        task["task_id"]
        for task in signed_tasks
        if task["context"]["worker_runtime"] == "0102"
        and task["context"]["capability"] == "bounded_code_change"
    )
    queue_stage_task_id = next(
        task["task_id"]
        for task in signed_tasks
        if task["context"]["worker_runtime"] == "openclaw"
        and task["context"]["capability"] == "queue_stage_progress"
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "8")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv(
        "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH",
        str(generic_writer),
    )
    monkeypatch.setenv(
        "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH",
        str(governed_shell),
    )
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_PILOT_DRYRUN_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv("REDDOG_HELD_OUT_GATE_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    with patch(
        "modules.infrastructure.database.src.agent_db.AgentDB",
        _assurance_store,
    ):
        assert (
            main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo)
            is True
        )

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT" in captured
    assert "claimed_count=7" in captured
    assert coding_task_id in captured
    assert queue_stage_task_id in captured
    assert AgentDB().get_autonomous_task_by_id(coding_task_id)["status"] == "completed"
    assert AgentDB().get_autonomous_task_by_id(queue_stage_task_id)["status"] == "completed"
    remaining_signed = [
        task
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert remaining_signed == []
    assert calls
    assert calls[0]["api_key"] == "test-openrouter-key"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    for stage_name in (
        "bounded_worker_pilot",
        "slice_verifier",
        "verified_draft_pr_publish",
        "verified_outcome_ratchet",
        "model_feedback_admission",
        "held_out_regression_gate",
        "pattern_memory_admission",
    ):
        assert stage_name in stored["stage_results"]
    generation = stored["stage_results"]["bounded_worker_pilot"]["artifact_generation_result"]
    assert generation["accepted"] is True
    assert generation["receipt"]["model_receipt_id"] == "fusion-artifact-receipt-1"
    assert stored["receipts"][-1]["next_action"] == "STOP_QUEUE_CHAIN_COMPLETE"
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8").startswith(
        "# Generated By Fusion"
    )
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "REDDOG_ARTIFACT_CONTENTS_PATH" not in os.environ
    draft_pr_calls = [
        call[0]
        for instance in _FakeEnvDraftPrRunner.instances
        for call in instance.calls
    ]
    assert draft_pr_calls == ["commit_all", "push_branch", "create_draft_pr"]
    assert outcome_store.exists()
    with sqlite3.connect(pattern_memory_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM skill_outcomes").fetchone()[0]
    assert count == 1
    assert not (repo / "runtime" / "pattern_memory.db").exists()


def test_private_openclaw_claim_primitives_reject_without_control_lock(
    tmp_path: Path,
) -> None:
    from modules.communication.moltbot_bridge.src import openclaw_supervisor as supervisor

    def forbidden_factory():
        raise AssertionError("AgentDB must not be opened without the control lock")

    once = supervisor._claim_reddog_signed_worker_dispatch_task_once_under_control_lock(
        repo_root=tmp_path, agent_db_factory=forbidden_factory
    )
    loop = supervisor._claim_reddog_signed_worker_dispatch_tasks_until_idle_under_control_lock(
        repo_root=tmp_path, agent_db_factory=forbidden_factory, max_claims=1
    )
    assert once["accepted"] is False
    assert loop["accepted"] is False
    assert "resident_queue_control_lock_required" in once["rejection_reasons"]
    assert "resident_queue_control_lock_required" in loop["rejection_reasons"]


def test_control_lock_reentry_is_bound_to_exact_repository_identity(
    tmp_path: Path,
) -> None:
    from modules.communication.moltbot_bridge.src import openclaw_supervisor as supervisor
    from modules.communication.moltbot_bridge.src.reddog_resident_queue_control_lock import (
        acquire_resident_queue_control_lock,
        resident_queue_control_lock_held,
    )

    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    repo_a.mkdir()
    repo_b.mkdir()

    def forbidden_factory():
        raise AssertionError("lock A must not authorize AgentDB access for repo B")

    with acquire_resident_queue_control_lock(repo_a) as lock:
        assert lock.acquired is True
        assert resident_queue_control_lock_held(repo_a) is True
        assert resident_queue_control_lock_held(repo_b) is False
        result = supervisor._claim_reddog_signed_worker_dispatch_task_once_under_control_lock(
            repo_root=repo_b,
            agent_db_factory=forbidden_factory,
        )

    assert result["accepted"] is False
    assert "resident_queue_control_lock_required" in result["rejection_reasons"]


def test_failed_claim_has_digest_bound_exact_child_outcome() -> None:
    from modules.communication.moltbot_bridge.src import openclaw_supervisor as supervisor

    claim = supervisor._signed_worker_claim_result(
        accepted=False,
        status=supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
        task_id="task-failed-1",
        rejection_reasons=("test_failure",),
    )
    result = supervisor._signed_worker_claim_loop_result(
        accepted=False,
        status=supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT,
        max_claims=1,
        claim_results=(claim,),
        failed_task_ids=("task-failed-1",),
    )
    assert claim["execution_result_digest"].startswith("sha256:")
    assert result["child_execution_evidence_digests"] == (
        claim["execution_result_digest"],
    )
    assert result["child_execution_outcomes"] == (
        {
            "task_id": "task-failed-1",
            "status": "failed",
                "receipt_id": "",
                "evidence_digest": claim["execution_result_digest"],
                "worker_execution_performed": False,
                "effect_evidence_complete": True,
                "worker_process_spawn_count": 0,
                "shell_command_count": 0,
            },
    )


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="AF_UNIX required")
def test_main_resident_control_loop_profile_runtime_completes_socket_signed_queue_chain_without_work_orders(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeProfileWorktreeRunner.instances.clear()
    monkeypatch.setattr(worktree_pr_runner, "RealWorktreeRunner", _FakeProfileWorktreeRunner)
    repo = _repo(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    runtime_root.mkdir(parents=True)
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": (
            PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY
        ),
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    principal_public, reddog_public, signer_backend = _ed25519_signing_material_with_socket_backend()
    pilot_overrides = _pilot_path_overrides()
    state = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_AUTHORITATIVE_WORK_STATE_PATH")),
        _bootstrap_snapshot(),
    )
    profile = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
            )
        ),
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
            bounded_worker_plan=_pilot_bounded_worker_plan(),
        ),
    )
    snapshots = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_PERMISSION_SNAPSHOTS_PATH")),
        _snapshots(),
    )
    principals = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
            )
        ),
        _principals(principal_public),
    )
    valve_env = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_EXECUTION_VALVE_ENV_PATH")),
        _valve_environment(),
    )
    chain = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
        )
    )
    authority_state = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_AUTHORITY_RUNTIME_STATE_PATH")
    )
    socket_path = Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SOCKET_PATH"))
    materialized_work_order = _work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
        nonce="work-order:workauth-nonce-0001",
    )
    worktree = _pilot_worktree_path(repo, materialized_work_order)
    verifier_request = _write_json(
        runtime_root / "slice_verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_json(
        runtime_root / "draft_pr_publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    outcome_store = runtime_root / "outcomes" / "signed-worker-ratchet.jsonl"
    pattern_memory_db = runtime_root / "pattern_memory.db"
    assert not socket_path.exists()

    ready = threading.Event()
    service_result: dict[str, object] = {}

    def _serve_signer() -> None:
        service_result["result"] = serve_reddog_isolated_signer_socket_bounded(
            repo_root=repo,
            socket_path=socket_path,
            backend=signer_backend,
            peer_attestor=_StaticSocketPeerAttestor(),
            max_requests=3,
            timeout_s=5,
            ready_callback=ready.set,
        )

    signer_thread = threading.Thread(target=_serve_signer, daemon=True)
    signer_thread.start()
    assert ready.wait(5)

    calls = _patch_fusion_artifact_generator(monkeypatch)
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
    )
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS", "9")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "7")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "1000")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S", "77")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY", "0")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_PERMISSION_SNAPSHOTS_PATH", str(snapshots))
    monkeypatch.setenv("REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH", str(principals))
    monkeypatch.setenv("REDDOG_EXECUTION_VALVE_ENV_PATH", str(valve_env))
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_STATE_PATH", str(authority_state))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db))
    monkeypatch.delenv("REDDOG_WORK_ORDERS_PATH", raising=False)
    assert "REDDOG_WORK_ORDERS_PATH" not in os.environ

    try:
        assert main.run_reddog_resident_queue_control_loop_preflight(repo) is True
    finally:
        signer_thread.join(5)

    result = service_result["result"]
    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RESIDENT_SERVICE_SERVED
    assert result.requests_handled == 3
    assert not socket_path.exists()

    captured = capsys.readouterr().out
    assert "[REDDOG-QUEUE-CONTROL] preflight=PASS" in captured
    assert "[REDDOG-QUEUE-LOOP] preflight=PASS" in captured
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "claimed_count=7" in captured
    assert "receipts=signed_worker_task_execution_" in captured
    assert str(
        main.run_reddog_resident_queue_control_loop_preflight.last_result[
            "receipt_ids"
        ][0]
    ).startswith("signed_worker_task_execution_")
    assert "control_receipt=reddog_resident_control_loop_" in captured
    control_receipt_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH",
        )
    )
    control_receipt = json.loads(control_receipt_path.read_text(encoding="utf-8").splitlines()[-1])
    assert (
        control_receipt["receipt_id"]
        == main.run_reddog_resident_queue_control_loop_preflight.last_result["receipt_id"]
    )
    assert control_receipt["receipt_ids"][0].startswith("signed_worker_task_execution_")
    assert control_receipt["child_execution_receipt_ids"] == control_receipt["receipt_ids"]
    assert control_receipt["child_execution_evidence_count"] == (
        control_receipt["worker_completion_count"]
        + control_receipt["worker_requeue_count"]
        + control_receipt["worker_failure_count"]
    )
    assert control_receipt["control_lock_acquired"] is True
    assert "authority_runtime" in control_receipt["dispatched_stages"]
    assert "bounded_worker_pilot" in control_receipt["dispatched_stages"]
    assert control_receipt["authority_issued"] is True
    assert control_receipt["worker_claim_performed"] is True
    assert control_receipt["worker_execution_performed"] is True
    assert control_receipt["worktree_creation_observed"] is True
    assert control_receipt["bounded_file_edit_observed"] is True
    assert control_receipt["slice_verification_observed"] is True
    assert control_receipt["draft_pr_publish_observed"] is True
    assert control_receipt["pattern_memory_admission_observed"] is True
    assert control_receipt["shell_command_execution_observed"] is False
    assert control_receipt["shell_command_count"] == 0
    assert control_receipt["worker_process_spawn_observed"] is False
    assert control_receipt["worker_process_spawn_count"] == 0
    assert control_receipt["authentication_status"] == "AUTHENTICATED"
    assert control_receipt["signature"].startswith("ed25519-sig-v1:")
    assert control_receipt["signer_audit_attestation_signature"].startswith(
        "ed25519-sig-v1:"
    )
    assert main.run_reddog_resident_queue_control_loop_preflight.last_result["control_lock_acquired"] is True
    assert "REDDOG_WORK_ORDERS_PATH" not in os.environ

    pending = [
        task
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert pending == []
    completed = [
        task
        for task in AgentDB().get_autonomous_tasks(status="completed", limit=10)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]
    assert {task["context"]["worker_runtime"] for task in completed} == {"0102", "openclaw"}
    assert calls

    stored = json.loads(chain.read_text(encoding="utf-8"))
    for stage_name in (
        "worker_dispatch_runtime",
        "worktree_create",
        "bounded_worker_pilot",
        "slice_verifier",
        "verified_draft_pr_publish",
        "verified_outcome_ratchet",
        "model_feedback_admission",
        "held_out_regression_gate",
        "pattern_memory_admission",
    ):
        assert stage_name in stored["stage_results"]
    generation = stored["stage_results"]["bounded_worker_pilot"]["artifact_generation_result"]
    assert generation["accepted"] is True
    assert generation["receipt"]["model_receipt_id"] == "fusion-artifact-receipt-1"
    assert stored["receipts"][-1]["next_action"] == "STOP_QUEUE_CHAIN_COMPLETE"
    worktree_calls = [
        call
        for instance in _FakeProfileWorktreeRunner.instances
        for call in instance.calls
        if call[0] == "create_worktree"
    ]
    assert len(worktree_calls) == 1
    worktree = Path(worktree_calls[0][1])
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8").startswith(
        "# Generated By Fusion"
    )
    assert not (repo / PILOT_ARTIFACT).exists()
    draft_pr_calls = [
        call[0]
        for instance in _FakeProfileWorktreeRunner.instances
        for call in instance.calls
        if call[0] in {"push_branch", "create_draft_pr"}
    ]
    assert draft_pr_calls == ["push_branch", "create_draft_pr"]
    assert outcome_store.exists()
    with sqlite3.connect(pattern_memory_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM skill_outcomes").fetchone()[0]
    assert count == 1
    assert not (repo / "runtime" / "pattern_memory.db").exists()


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX")
    or not hasattr(socket, "SO_PEERCRED")
    or not hasattr(os, "getuid")
    or not hasattr(os, "getgid"),
    reason="AF_UNIX SO_PEERCRED signer CLI proof requires kernel peer credentials",
)
def test_main_resident_control_loop_consumes_signer_socket_started_by_runtime_cli(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import main
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeProfileWorktreeRunner.instances.clear()
    monkeypatch.setattr(worktree_pr_runner, "RealWorktreeRunner", _FakeProfileWorktreeRunner)
    repo = _repo(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    runtime_root.mkdir(parents=True)
    profile_env = {
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": (
            PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY
        ),
        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
    }
    _principal_key, principal_public, principal_secret = _cli_private_key_material()
    _reddog_key, reddog_public, reddog_secret = _cli_private_key_material()
    resolver_factory = _FakeCliResolverFactory(
        {
            "op://prod-vault/principal/private": principal_secret,
            "op://prod-vault/principal/audit": _cli_audit_secret(
                b"principal-audit-key-000000000"
            ),
            "op://prod-vault/reddog/private": reddog_secret,
            "op://prod-vault/reddog/audit": _cli_audit_secret(
                b"reddog-audit-key-000000000000"
            ),
        }
    )
    pilot_overrides = _pilot_path_overrides()
    state = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_AUTHORITATIVE_WORK_STATE_PATH")),
        _bootstrap_snapshot(),
    )
    profile = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
            )
        ),
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
            bounded_worker_plan=_pilot_bounded_worker_plan(),
        ),
    )
    snapshots = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_PERMISSION_SNAPSHOTS_PATH")),
        _snapshots(),
    )
    principals = _write_json(
        Path(
            resident_queue_runtime_file_path(
                profile_env,
                repo,
                "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
            )
        ),
        _principals(principal_public),
    )
    valve_env = _write_json(
        Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_EXECUTION_VALVE_ENV_PATH")),
        _valve_environment(),
    )
    chain = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH",
        )
    )
    authority_state = Path(
        resident_queue_runtime_file_path(profile_env, repo, "REDDOG_AUTHORITY_RUNTIME_STATE_PATH")
    )
    socket_path = Path(resident_queue_runtime_file_path(profile_env, repo, "REDDOG_SIGNER_SOCKET_PATH"))
    materialized_work_order = _work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
        nonce="work-order:workauth-nonce-0001",
    )
    worktree = _pilot_worktree_path(repo, materialized_work_order)
    verifier_request = _write_json(
        runtime_root / "slice_verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_json(
        runtime_root / "draft_pr_publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    outcome_store = runtime_root / "outcomes" / "signed-worker-ratchet.jsonl"
    pattern_memory_db = runtime_root / "pattern_memory.db"
    signer_config = _write_json(
        runtime_root / "signer-service.json",
        {
            "socket_path": str(socket_path),
            "control_loop_anchor_path": str(
                tmp_path / "signer-state" / "control-loop-anchor.json"
            ),
            "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
            "allow_test_only_key_material": False,
            "permission_snapshot_fresh": True,
            "max_requests": 3,
            "timeout_s": 5,
            "max_request_bytes": 16384,
            "max_response_bytes": 16384,
            "key_provider_profiles": [
                _cli_key_profile(
                    public_key=principal_public,
                    signer_profile_id="principal-profile",
                    signer_agent_id="signer:principal",
                    signing_key_ref="op://prod-vault/principal/private",
                    audit_mac_key_ref="op://prod-vault/principal/audit",
                ),
                _cli_key_profile(
                    public_key=reddog_public,
                    signer_profile_id="reddog-profile",
                    signer_agent_id="signer:reddog",
                    signing_key_ref="op://prod-vault/reddog/private",
                    audit_mac_key_ref="op://prod-vault/reddog/audit",
                ),
            ],
            "peer_policy": {
                "uid_to_principal": {str(os.getuid()): "github:mjtrout"},
                "allowed_gids": [os.getgid()],
                "transport": "unix_socket",
                "credential_source_prefix": "kernel_peer_credential",
            },
        },
    )
    assert not socket_path.exists()

    signer_exit: dict[str, int] = {}
    emitted: list[str] = []

    def _serve_signer_cli() -> None:
        signer_exit["code"] = run_reddog_signer_socket_service_runtime_cli(
            [
                "--repo-root",
                str(repo),
                "--config",
                str(signer_config),
                "--op-executable",
                "op",
                "--op-timeout-s",
                "2",
                "--ttl-seconds",
                "60",
                "--session-id",
                "cli-main-loop-proof",
            ],
            resolver_factory=resolver_factory,
            emit=emitted.append,
        )

    signer_thread = threading.Thread(target=_serve_signer_cli, daemon=True)
    signer_thread.start()
    assert _wait_for_socket(socket_path)

    calls = _patch_fusion_artifact_generator(monkeypatch)
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
    )
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS", "9")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "7")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "1000")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S", "77")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY", "0")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_PERMISSION_SNAPSHOTS_PATH", str(snapshots))
    monkeypatch.setenv("REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH", str(principals))
    monkeypatch.setenv("REDDOG_EXECUTION_VALVE_ENV_PATH", str(valve_env))
    monkeypatch.setenv("REDDOG_AUTHORITY_RUNTIME_STATE_PATH", str(authority_state))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db))
    monkeypatch.delenv("REDDOG_WORK_ORDERS_PATH", raising=False)

    try:
        assert main.run_reddog_resident_queue_control_loop_preflight(repo) is True
    finally:
        signer_thread.join(5)

    assert signer_exit["code"] == 0
    assert emitted
    signer_receipt = json.loads(emitted[0])
    assert signer_receipt["status"] == "SIGNER_SOCKET_SERVICE_RUNTIME_CLI_ACCEPT"
    assert signer_receipt["result"]["accepted"] is True
    assert signer_receipt["result"]["runtime_result"]["key_provider_receipt"]["profile_count"] == 2
    assert resolver_factory.calls == [
        {
            "op_executable": "op",
            "timeout_s": 2.0,
            "ttl_seconds": 60,
            "session_id": "cli-main-loop-proof",
        }
    ]
    assert resolver_factory.resolver.calls == [
        ("op://prod-vault/principal/private", "signer:principal"),
        ("op://prod-vault/principal/audit", "signer:principal"),
        ("op://prod-vault/reddog/private", "signer:reddog"),
        ("op://prod-vault/reddog/audit", "signer:reddog"),
    ]
    assert not socket_path.exists()

    captured = capsys.readouterr().out
    assert "[REDDOG-QUEUE-CONTROL] preflight=PASS" in captured
    assert "[REDDOG-QUEUE-LOOP] preflight=PASS" in captured
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "receipts=signed_worker_task_execution_" in captured
    assert str(
        main.run_reddog_resident_queue_control_loop_preflight.last_result[
            "receipt_ids"
        ][0]
    ).startswith("signed_worker_task_execution_")
    assert "control_receipt=reddog_resident_control_loop_" in captured
    control_receipt_path = Path(
        resident_queue_runtime_file_path(
            profile_env,
            repo,
            "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH",
        )
    )
    control_receipt = json.loads(control_receipt_path.read_text(encoding="utf-8").splitlines()[-1])
    assert (
        control_receipt["receipt_id"]
        == main.run_reddog_resident_queue_control_loop_preflight.last_result["receipt_id"]
    )
    assert control_receipt["receipt_ids"][0].startswith("signed_worker_task_execution_")
    assert control_receipt["control_lock_acquired"] is True
    assert control_receipt["authentication_status"] == "AUTHENTICATED"
    assert control_receipt["signature"].startswith("ed25519-sig-v1:")
    assert main.run_reddog_resident_queue_control_loop_preflight.last_result["control_lock_acquired"] is True
    assert calls
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["worker_dispatch_runtime"]["accepted"] is True
    assert stored["stage_results"]["bounded_worker_pilot"]["artifact_generation_result"]["accepted"] is True
    assert stored["receipts"][-1]["next_action"] == "STOP_QUEUE_CHAIN_COMPLETE"
