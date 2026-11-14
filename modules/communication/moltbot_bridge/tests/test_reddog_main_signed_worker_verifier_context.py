"""Focused startup tests for explicit signed-worker verifier context."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    WorkerDispatchAuthorityVerificationConfig,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
)


CLAIM_LOOP = (
    "modules.communication.moltbot_bridge.src.openclaw_supervisor."
    "claim_reddog_signed_worker_dispatch_tasks_until_idle"
)


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _verification_fixture(tmp_path: Path) -> tuple[
    Path,
    WorkerDispatchAuthorityVerificationConfig,
    str,
    str,
    str,
]:
    repo = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    repo.mkdir()
    runtime_root.mkdir()
    private_key = Ed25519PrivateKey.generate()
    public_key = encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )
    signing_input = 'reddog-workauth.v1.{"task_id":"task-1"}'
    signature = encode_ed25519_signature(
        private_key.sign(signing_input.encode("utf-8"))
    )
    snapshots = _write_json(runtime_root / "snapshots.json", {"snapshots": {}})
    principals = _write_json(
        runtime_root / "principals.json",
        {"principals": {"github:mjtrout": {
            "principal_id": "github:mjtrout",
            "principal_provider": "github",
            "principal_public_key": public_key,
            "repo_scope": ["FOUNDUPS/Foundups-Agent"],
            "foundup_scope": ["paccess_001"],
            "verified_subject_digest": "sha256:verified-subject",
        }}},
    )
    config = WorkerDispatchAuthorityVerificationConfig(
        repo_root=str(repo),
        runtime_allowed_root=str(runtime_root),
        authority_state_path=str(runtime_root / "authority_state.json"),
        permission_snapshots_path=str(snapshots),
        principal_authority_records_path=str(principals),
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    )
    return repo, config, public_key, signing_input, signature


def test_claim_uses_explicit_context_when_backend_env_is_clear(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import main

    repo, config, public_key, signing_input, signature = _verification_fixture(
        tmp_path
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.delenv("REDDOG_SIGNATURE_VERIFIER_BACKEND", raising=False)

    def _claim(**kwargs):
        context = kwargs["authority_verification_context"]
        assert context.principal_key_resolver.resolve(
            "github:mjtrout", "github"
        ) == public_key
        assert context.signature_verifier.verify(
            public_key, signing_input, signature
        )
        return {
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE",
            "claimed_count": 0,
            "completed_task_ids": (),
            "requeued_task_ids": (),
            "failed_task_ids": (),
            "rejection_reasons": ("NO_PENDING_TASK",),
        }

    with patch(CLAIM_LOOP, side_effect=_claim) as mocked:
        assert main.run_reddog_openclaw_signed_worker_claim_loop_preflight(
            repo, authority_verification_config=config
        )
    assert mocked.call_count == 1
    assert "REDDOG_SIGNATURE_VERIFIER_BACKEND" not in os.environ


def test_claim_rejects_invalid_explicit_context_before_openclaw(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import main

    repo, config, _, _, _ = _verification_fixture(tmp_path)
    invalid = replace(
        config,
        principal_authority_records_path=str(
            tmp_path / "runtime" / "missing-principals.json"
        ),
    )
    monkeypatch.setenv("REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP", "1")
    monkeypatch.setenv(
        "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED", "1"
    )

    with patch(CLAIM_LOOP) as mocked:
        assert not main.run_reddog_openclaw_signed_worker_claim_loop_preflight(
            repo, authority_verification_config=invalid
        )
    mocked.assert_not_called()
