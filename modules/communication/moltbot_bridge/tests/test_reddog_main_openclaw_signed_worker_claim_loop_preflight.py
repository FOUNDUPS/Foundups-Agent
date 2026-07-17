"""Tests for REDDOG_MAIN_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_PREFLIGHT_PHASE1."""

from __future__ import annotations

import base64
import json
import os
import socket
import sqlite3
import threading
import time
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
    _FakeWorkerDispatchTaskWriter,
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
    _allocation,
    _FakeEnvDraftPrRunner,
    _publish_agentdb_task,
    _publish_agentdb_task_with_allocation,
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
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


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
    assert "FAIL_SIGNER_SOCKET_PATH_UNAVAILABLE" in captured
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
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=9,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "worktree_create"
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

    task_id = _publish_agentdb_task()
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
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

    assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT" in captured
    assert "claimed_count=1" in captured
    assert f"requeued={task_id}" in captured
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["bounded_worker_pilot"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    assert stage["bounded_task_execution_performed"] is True
    assert stage["bounded_file_edit_performed"] is True
    assert stage["shell_command_executed"] is False
    assert stage["openclaw_enqueue_performed"] is False
    assert stage["hermes_dispatch_performed"] is False
    assert stage["holoindex_reindex_performed"] is False
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8").startswith(
        "# Resident Queue Pilot"
    )
    assert not (repo / PILOT_ARTIFACT).exists()


def test_main_openclaw_signed_0102_bounded_code_uses_fusion_artifact_generation(
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
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=9,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "worktree_create"
    assert worktree.exists()
    assert not (worktree / PILOT_ARTIFACT).exists()

    calls = _patch_fusion_artifact_generator(monkeypatch)
    task_id = _publish_agentdb_task_with_allocation(
        _allocation(),
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_PILOT_DRYRUN_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "1")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT" in captured
    assert "claimed_count=1" in captured
    assert f"completed={task_id}" in captured
    assert "requeued=(none)" in captured
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
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeEnvDraftPrRunner.instances.clear()
    monkeypatch.setattr(worktree_pr_runner, "RealWorktreeRunner", _FakeEnvDraftPrRunner)
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
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=9,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "worktree_create"

    calls = _patch_fusion_artifact_generator(monkeypatch)
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
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS", "7")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
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
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(repo) is True

    captured = capsys.readouterr().out
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT" in captured
    assert "claimed_count=7" in captured
    assert f"completed={coding_task_id},{queue_stage_task_id}" in captured
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
    assert draft_pr_calls == ["push_branch", "create_draft_pr"]
    assert outcome_store.exists()
    with sqlite3.connect(pattern_memory_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM skill_outcomes").fetchone()[0]
    assert count == 1
    assert not (repo / "runtime" / "pattern_memory.db").exists()


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
            max_requests=2,
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
    assert result.requests_handled == 2
    assert not socket_path.exists()

    captured = capsys.readouterr().out
    assert "[REDDOG-QUEUE-CONTROL] preflight=PASS" in captured
    assert "[REDDOG-QUEUE-LOOP] preflight=PASS" in captured
    assert "[REDDOG-OPENCLAW-CLAIM-LOOP] preflight=PASS" in captured
    assert "claimed_count=7" in captured
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
            "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
            "allow_test_only_key_material": False,
            "permission_snapshot_fresh": True,
            "max_requests": 2,
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
    assert calls
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["worker_dispatch_runtime"]["accepted"] is True
    assert stored["stage_results"]["bounded_worker_pilot"]["artifact_generation_result"]["accepted"] is True
    assert stored["receipts"][-1]["next_action"] == "STOP_QUEUE_CHAIN_COMPLETE"
