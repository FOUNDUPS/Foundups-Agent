"""Tests for the stable signer-owned system-service entrypoint."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_current_generation_manifest_launch_selection as selection_module,
    reddog_signer_system_service_entrypoint as entrypoint_module,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_entrypoint import (
    SYSTEM_SERVICE_ENTRYPOINT_ACCEPT,
    SYSTEM_SERVICE_ENTRYPOINT_REJECT,
    _UnavailableSystemServiceResolver,
    _run_entrypoint_args,
)
from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    SignerProcessIsolationReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedPrincipalKeyResolver,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_runtime_cli import (
    CapturingBoundedService,
    CapturingResolverFactory,
    FakeResolver,
    _audit_secret,
    _private_key_secret,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_manifest_selection_loader import (
    _prepare_real_cli_owner,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
)

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "reddog_signer_system_service_entrypoint.py"
)


@pytest.fixture(autouse=True)
def _trusted_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)


def _isolation_receipt(accepted: bool) -> SignerProcessIsolationReceipt:
    return SignerProcessIsolationReceipt(
        accepted, (() if accepted else ("rejected",)), 1201, 1201,
        accepted, accepted, accepted, accepted, accepted, accepted, accepted,
    )


def _accepted_isolation(
    _policy: PeerCredentialPolicy,
    *,
    expected_signer_uid: int,
    expected_signer_gid: int,
) -> SignerProcessIsolationReceipt:
    receipt = _isolation_receipt(True)
    return SignerProcessIsolationReceipt(
        **{
            **receipt.__dict__,
            "signer_uid": expected_signer_uid,
            "signer_gid": expected_signer_gid,
        }
    )


def test_stable_entrypoint_selects_current_generation_and_serves_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    monkeypatch.setattr(
        entrypoint_module,
        "load_system_service_signer_identity",
        lambda **_kwargs: (1201, 1201),
    )
    resolver = FakeResolver(
        {
            "op://prod-vault/reddog-signing/private": _private_key_secret(
                prepared["harness"].reddog_private_key
            ),
            "op://prod-vault/reddog-audit/mac": _audit_secret(),
        }
    )
    factory = CapturingResolverFactory(resolver)
    service = CapturingBoundedService()
    emitted: list[str] = []
    isolation_calls: list[tuple[int, int]] = []

    def isolation_gate(
        policy: PeerCredentialPolicy,
        *,
        expected_signer_uid: int,
        expected_signer_gid: int,
    ) -> SignerProcessIsolationReceipt:
        isolation_calls.append((expected_signer_uid, expected_signer_gid))
        return _accepted_isolation(
            policy,
            expected_signer_uid=expected_signer_uid,
            expected_signer_gid=expected_signer_gid,
        )

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        process_isolation_gate=isolation_gate,
    )

    payload = json.loads(emitted[0])
    assert code == 0, payload
    assert payload["status"] == SYSTEM_SERVICE_ENTRYPOINT_ACCEPT
    assert len(factory.calls) == 1
    assert len(service.calls) == 1
    assert isolation_calls == [(1201, 1201)]
    assert payload["no_serialized_argv_executed"] is True
    assert payload["no_signer_process_spawned"] is True
    assert payload["no_shell_invoked"] is True


def test_system_service_isolation_rejects_before_resolver_or_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    monkeypatch.setattr(
        entrypoint_module,
        "load_system_service_signer_identity",
        lambda **_kwargs: (1201, 1201),
    )
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        process_isolation_gate=lambda _policy, **_expected: _isolation_receipt(False),
    )

    assert code == 2
    assert json.loads(emitted[0])["status"] == SYSTEM_SERVICE_ENTRYPOINT_REJECT
    assert factory.calls == []
    assert service.calls == []


def test_alternate_owner_path_rejects_before_resolver_or_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    alternate_root = tmp_path / "alternate-owner"
    alternate_root.mkdir()
    alternate = alternate_root / "owner.json"
    alternate.write_bytes(Path(prepared["owner_path"]).read_bytes())
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(alternate),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
    )

    assert code == 2
    assert json.loads(emitted[0])["status"] == (
        SYSTEM_SERVICE_ENTRYPOINT_REJECT
    )
    assert factory.calls == []
    assert service.calls == []


def test_generation_capability_failure_rejects_before_resolver_or_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    class RejectedGenerationBoundary:
        @staticmethod
        def consume(_capability: object) -> object:
            raise RuntimeError("generation changed")

    monkeypatch.setattr(
        entrypoint_module,
        "load_system_service_manifest_selection",
        lambda **_kwargs: (object(), RejectedGenerationBoundary()),
    )
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
    )

    assert code == 2
    payload = json.loads(emitted[0])
    assert payload["status"] == SYSTEM_SERVICE_ENTRYPOINT_REJECT
    assert factory.calls == []
    assert service.calls == []


def test_production_secret_resolver_fails_closed_without_e0() -> None:
    result = _UnavailableSystemServiceResolver.resolve(
        "op://prod-vault/reddog-signing/private",
        requester_id="signer:reddog",
    )

    assert result.success is False
    assert result.get_value() is None
    assert result.error_message == "system_service_secret_resolver_not_admitted"


def test_real_module_entrypoint_exposes_stable_help_command() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            (
                "modules.communication.moltbot_bridge.src."
                "reddog_signer_system_service_entrypoint"
            ),
            "--help",
        ],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--repo-root" in completed.stdout
    assert "--owner-authority-config" in completed.stdout


def test_entrypoint_has_no_process_or_dynamic_execution_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    import_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        (node.value.id, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
    }

    assert "subprocess" not in imported
    assert not any(
        name.endswith("op_cli_secret_resolver")
        for name in import_modules
    )
    assert not {"eval", "exec", "compile"} & calls
    assert not {
        ("os", "system"),
        ("os", "popen"),
        ("os", "spawn"),
    } & attributes
