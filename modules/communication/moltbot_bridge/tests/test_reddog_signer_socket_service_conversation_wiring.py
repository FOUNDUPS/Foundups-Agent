"""Conversation authority binding for the signer socket runtime."""

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    ConversationScopeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    FAIL_SIGNER_RUNTIME_CONVERSATION_AUTH_INVALID,
    run_reddog_signer_socket_service_runtime_wiring,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_runtime_wiring import (
    CapturingBoundedService,
    _config,
    _private_key,
    _public_text,
    _resolver,
)


class CurrentResolver:
    @staticmethod
    def resolve(_principal_id: str, _principal_provider: str):
        return None


def _conversation_config(tmp_path: Path, private_key: object):
    public_key = _public_text(private_key)
    repo = tmp_path / "repo"
    repo.mkdir()
    signer_runtime = tmp_path / "signer-runtime"
    policy = ConversationScopeSignerPolicy(
        issuer_principal_id="github:mjtrout",
        issuer_principal_provider="github",
        repo_full_name="FOUNDUPS/Foundups-Agent",
        signer_public_key=public_key,
        key_epoch="epoch-1",
    )
    config = _config(
        public_key, repo_root=repo, runtime_root=tmp_path / "runtime",
        signer_runtime_root=signer_runtime,
        socket_path=tmp_path / "runtime/reddog-signer.sock",
        control_loop_anchor_path=signer_runtime / "control-anchor.json",
        conversation_scope_anchor_path=signer_runtime / "conversation-anchor.json",
        conversation_scope_signer_policy=policy, max_request_bytes=163840,
    )
    return config, policy


def test_conversation_scope_runtime_requires_current_principal_resolver(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    config, policy = _conversation_config(tmp_path, private_key)
    missing = run_reddog_signer_socket_service_runtime_wiring(
        config, _resolver(private_key), serve_bounded=CapturingBoundedService()
    )
    service = CapturingBoundedService()
    accepted = run_reddog_signer_socket_service_runtime_wiring(
        config, _resolver(private_key), serve_bounded=service,
        conversation_scope_principal_resolver=CurrentResolver(),
    )
    assert missing.accepted is False
    assert FAIL_SIGNER_RUNTIME_CONVERSATION_AUTH_INVALID in missing.rejection_reasons
    assert accepted.accepted is True
    backend = service.calls[0]["backend"]
    assert backend.conversation_scope_signer_policy == policy
    assert backend.conversation_scope_principal_resolver is not None
    assert backend.conversation_scope_anchor_store is not None
