"""Tests for REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_WIRING_PHASE1."""

from __future__ import annotations

import ast
import base64
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    SIGNER_SOCKET_RESIDENT_SERVICE_REJECT,
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    IsolatedSignerSocketResidentServiceResult,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
    REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY,
    REJECT_ED25519_SIGNER_POLICY_MISSING,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SIGNING_KEY_PREFIX,
    SignerKeyProviderProfile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    FAIL_SIGNER_RUNTIME_CONFIG_INVALID,
    FAIL_SIGNER_RUNTIME_CONTROL_ANCHOR_INVALID,
    FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE,
    FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED,
    FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID,
    FAIL_SIGNER_RUNTIME_PROFILE_INVALID,
    FAIL_SIGNER_RUNTIME_SERVICE_INVALID,
    FAIL_SIGNER_RUNTIME_SERVICE_REJECTED,
    SIGNER_SOCKET_RUNTIME_WIRING_REJECT,
    SIGNER_SOCKET_RUNTIME_WIRING_SERVED,
    SignerSocketServiceRuntimeWiringConfig,
    run_reddog_signer_socket_service_runtime_wiring,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_runtime_wiring.py"
)


pytest.importorskip("cryptography")


class FakeResolver:
    def __init__(self, values: dict[str, str], ttl: int = 60) -> None:
        self.values = values
        self.ttl = ttl
        self.calls: list[tuple[str, str | None]] = []

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        self.calls.append((reference, requester_id))
        value = self.values[reference]
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=self.ttl,
            session_id="test-session",
            _secret_value=value,
        )


class RepoMutatingResolver(FakeResolver):
    def __init__(
        self,
        values: dict[str, str],
        marker_path: Path,
    ) -> None:
        super().__init__(values)
        self.marker_path = marker_path

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        self.marker_path.write_text("injected effect", encoding="utf-8")
        return super().resolve(reference, requester_id)


class CapturingBoundedService:
    def __init__(self, result: IsolatedSignerSocketResidentServiceResult | object | None = None) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.result is not None:
            return self.result
        return IsolatedSignerSocketResidentServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(kwargs["socket_path"]),
            requests_handled=int(kwargs["max_requests"]),
            response_digests=("sha256:response",),
            socket_removed=True,
        )


class RaisingBoundedService:
    def __call__(self, **kwargs):
        raise RuntimeError("service failed")


def _private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def _private_key_secret(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return SIGNING_KEY_PREFIX + base64.b64encode(raw).decode("ascii")


def _public_text(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return encode_ed25519_public_key(public_bytes)


def _audit_secret(raw: bytes = b"0123456789abcdef0123456789abcdef") -> str:
    return AUDIT_KEY_PREFIX + base64.b64encode(raw).decode("ascii")


def _resolver(private_key) -> FakeResolver:
    return FakeResolver(
        {
            "op://test-vault/reddog-signing/private": _private_key_secret(private_key),
            "op://test-vault/reddog-audit/mac": _audit_secret(),
        }
    )


def _profile(public_key: str, **overrides: object) -> SignerKeyProviderProfile:
    values = {
        "signer_profile_id": "signer-profile-1",
        "signer_agent_id": "signer:reddog-authority",
        "signing_key_ref": "op://test-vault/reddog-signing/private",
        "audit_mac_key_ref": "op://test-vault/reddog-audit/mac",
        "expected_public_key": public_key,
        "expected_key_fingerprint": public_key_fingerprint(public_key),
        "expected_key_epoch": "epoch-1",
        "permission_snapshot_digest": "sha256:permission",
        "ttl_seconds": 60,
    }
    values.update(overrides)
    return SignerKeyProviderProfile(**values)


def _policy(**overrides: object) -> PeerCredentialPolicy:
    values = {
        "uid_to_principal": {1001: "github:mjtrout"},
        "allowed_gids": (1002,),
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }
    values.update(overrides)
    return PeerCredentialPolicy(**values)


def _config(tmp_path: Path, public_key: str, **overrides: object) -> SignerSocketServiceRuntimeWiringConfig:
    values = {
        "repo_root": tmp_path / "repo",
        "runtime_root": tmp_path / "runtime",
        "signer_runtime_root": tmp_path / "signer-runtime",
        "key_provider_profile": _profile(public_key),
        "peer_policy": _policy(),
        "provider_mode": PROVIDER_MODE_TEST_ONLY_DRYRUN,
        "allow_test_only_key_material": True,
        "permission_snapshot_fresh": True,
        "max_requests": 3,
        "timeout_s": 2.5,
        "max_request_bytes": 4096,
        "max_response_bytes": 8192,
        "control_loop_authority_policy": {
            "issuer_principal_id": "github:012",
            "signer_public_key": public_key,
            "key_epoch": "epoch-1",
            "consensus_receipt_digest": "sha256:" + ("1" * 64),
            "authority_profile_digest": "sha256:" + ("2" * 64),
            "authority_profile_source_receipt_id": "sha256:" + ("3" * 64),
        },
    }
    values.update(overrides)
    values.setdefault("socket_path", Path(values["runtime_root"]) / "reddog-signer.sock")
    values.setdefault("control_loop_anchor_path", Path(values["signer_runtime_root"]) / "anchor.json")
    return SignerSocketServiceRuntimeWiringConfig(**values)


def _request(public_key: str) -> SigningRequest:
    return SigningRequest(
        signing_input='reddog-workauth.v1.{"work_order_id":"wo-1"}',
        payload_digest="sha256:payload",
        signer_role="reddog",
        signer_public_key=public_key,
        requester_principal_id="github:mjtrout",
        nonce="nonce-1",
        key_epoch="epoch-1",
        requested_operation="create_foundup",
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:consensus",
    )


def _peer() -> SignerPeerAttestation:
    return SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="unix_socket",
        credential_source="test_peer_credential",
        boundary_attested=True,
    )


def test_runtime_wiring_composes_provider_attestor_and_bounded_service(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(tmp_path, public_key),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RUNTIME_WIRING_SERVED
    assert result.key_provider_receipt["ok"] is True
    assert result.service_result["status"] == SIGNER_SOCKET_RESIDENT_SERVICE_SERVED
    assert result.max_requests == 3
    assert result.no_env_parsed is False
    assert result.no_process_spawned is False
    assert result.no_repo_mutation_performed is False
    assert len(service.calls) == 1
    assert service.calls[0]["max_requests"] == 3
    assert service.calls[0]["timeout_s"] == 2.5
    backend = service.calls[0]["backend"]
    response = backend.sign(_request(public_key), _peer())
    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY


def test_runtime_receipt_does_not_overclaim_injected_dependency_effects(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    signer_runtime = tmp_path / "signer-runtime"
    repo.mkdir()
    marker = repo / "resolver-side-effect.txt"
    resolver = RepoMutatingResolver(_resolver(private_key).values, marker)

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            repo_root=repo,
            runtime_root=runtime,
            signer_runtime_root=signer_runtime,
            socket_path=runtime / "reddog-signer.sock",
            control_loop_anchor_path=signer_runtime / "anchor.json",
        ),
        resolver,
        serve_bounded=CapturingBoundedService(),
    )

    assert result.accepted is True
    assert marker.is_file()
    assert result.no_env_parsed is False
    assert result.no_file_io_performed is False
    assert result.no_process_spawned is False
    assert result.no_repo_mutation_performed is False
    assert result.no_openclaw_enqueue_performed is False
    assert result.no_hermes_dispatch_performed is False
    assert result.no_pr_created is False
    assert result.no_reward_settlement_performed is False
    assert result.no_holoindex_reindex_performed is False


def test_runtime_wiring_accepts_wsp71_permissioned_provider_mode_without_test_override(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            permission_snapshot_fresh=True,
        ),
        resolver,
        serve_bounded=service,
    )

    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RUNTIME_WIRING_SERVED
    assert result.key_provider_receipt["ok"] is True
    assert len(service.calls) == 1
    assert resolver.calls == [
        ("op://test-vault/reddog-signing/private", "signer:reddog-authority"),
        ("op://test-vault/reddog-audit/mac", "signer:reddog-authority"),
    ]


def test_runtime_wiring_routes_multiple_wsp71_permissioned_profiles(tmp_path: Path) -> None:
    principal_key = _private_key()
    reddog_key = _private_key()
    principal_public = _public_text(principal_key)
    reddog_public = _public_text(reddog_key)
    resolver = FakeResolver(
        {
            "op://test-vault/principal/private": _private_key_secret(principal_key),
            "op://test-vault/principal/audit": _audit_secret(b"principal-audit-key-000000000"),
            "op://test-vault/reddog/private": _private_key_secret(reddog_key),
            "op://test-vault/reddog/audit": _audit_secret(b"reddog-audit-key-000000000000"),
        }
    )
    service = CapturingBoundedService()
    principal_profile = _profile(
        principal_public,
        signer_profile_id="principal-profile",
        signer_agent_id="signer:principal",
        signing_key_ref="op://test-vault/principal/private",
        audit_mac_key_ref="op://test-vault/principal/audit",
    )
    reddog_profile = _profile(
        reddog_public,
        signer_profile_id="reddog-profile",
        signer_agent_id="signer:reddog",
        signing_key_ref="op://test-vault/reddog/private",
        audit_mac_key_ref="op://test-vault/reddog/audit",
    )

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            principal_public,
            key_provider_profile=None,
            key_provider_profiles=(principal_profile, reddog_profile),
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            permission_snapshot_fresh=True,
        ),
        resolver,
        serve_bounded=service,
    )

    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RUNTIME_WIRING_SERVED
    assert result.key_provider_receipt["ok"] is True
    assert result.key_provider_receipt["profile_count"] == 2
    backend = service.calls[0]["backend"]
    expected_rejections = {
        principal_public: REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY,
        reddog_public: REJECT_ED25519_SIGNER_POLICY_MISSING,
    }
    for public_key in (principal_public, reddog_public):
        request = _request(public_key)
        response = backend.sign(request, _peer())
        assert response.accepted is False
        assert response.rejection_code == expected_rejections[public_key]
    unknown = _request(_public_text(_private_key()))
    assert backend.sign(unknown, _peer()).accepted is False
    assert resolver.calls == [
        ("op://test-vault/principal/private", "signer:principal"),
        ("op://test-vault/principal/audit", "signer:principal"),
        ("op://test-vault/reddog/private", "signer:reddog"),
        ("op://test-vault/reddog/audit", "signer:reddog"),
    ]


def test_runtime_wiring_rejects_duplicate_multi_profile_public_key(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingBoundedService()
    profile = _profile(public_key)

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            key_provider_profile=None,
            key_provider_profiles=(profile, profile),
        ),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE in result.rejection_reasons
    assert service.calls == []


def test_runtime_wiring_rejects_duplicate_profile_id_across_keys(tmp_path: Path) -> None:
    first_key = _private_key()
    second_key = _private_key()
    first = _profile(
        _public_text(first_key),
        signer_profile_id="duplicate-profile",
    )
    second = _profile(
        _public_text(second_key),
        signer_profile_id="duplicate-profile",
    )
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            _public_text(first_key),
            key_provider_profile=None,
            key_provider_profiles=(first, second),
        ),
        _resolver(first_key),
        serve_bounded=service,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_RUNTIME_PROFILE_INVALID in result.rejection_reasons
    assert service.calls == []


def test_mapping_config_normalizes_profile_and_peer_policy(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    profile = _profile(public_key).__dict__
    policy = {
        "uid_to_principal": {"1001": "github:mjtrout"},
        "allowed_gids": ["1002"],
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(tmp_path, public_key, key_provider_profile=profile, peer_policy=policy),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is True
    attestor = service.calls[0]["peer_attestor"]
    assert attestor.policy.uid_to_principal == {1001: "github:mjtrout"}
    assert attestor.policy.allowed_gids == (1002,)


def test_default_provider_mode_rejects_before_service_call(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(tmp_path, public_key, allow_test_only_key_material=False),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is False
    assert result.status == SIGNER_SOCKET_RUNTIME_WIRING_REJECT
    assert FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED in result.rejection_reasons
    assert service.calls == []


def test_runtime_wiring_rejects_linked_control_anchor_path(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    signer_runtime = tmp_path / "signer-runtime"
    signer_runtime.mkdir()
    real = signer_runtime / "real"
    real.mkdir()
    linked = signer_runtime / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            repo_root=repo,
            runtime_root=runtime,
            signer_runtime_root=signer_runtime,
            control_loop_anchor_path=linked / "anchor.json",
        ),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_RUNTIME_CONTROL_ANCHOR_INVALID in result.rejection_reasons
    assert service.calls == []


def test_runtime_wiring_rejects_socket_outside_declared_runtime_root(
    tmp_path: Path,
) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "resident"
    signer_runtime = tmp_path / "signer"
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            repo_root=repo,
            runtime_root=runtime,
            signer_runtime_root=signer_runtime,
            socket_path=tmp_path / "outside" / "escaped.sock",
            control_loop_anchor_path=signer_runtime / "anchor.json",
        ),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert not result.accepted
    assert FAIL_SIGNER_RUNTIME_CONFIG_INVALID in result.rejection_reasons
    assert service.calls == []


def test_wsp71_runtime_wiring_requires_control_anchor_and_policy(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            control_loop_anchor_path=None,
            control_loop_authority_policy=None,
        ),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert not result.accepted
    assert FAIL_SIGNER_RUNTIME_CONFIG_INVALID in result.rejection_reasons
    assert service.calls == []


def test_runtime_wiring_rejects_malformed_typed_control_policy(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    service = CapturingBoundedService()
    malformed = ControlLoopAuthorityPolicy(
        issuer_principal_id=1,  # type: ignore[arg-type]
        signer_public_key=public_key,
        key_epoch="epoch-1",
        consensus_receipt_digest="sha256:" + ("1" * 64),
        authority_profile_digest="sha256:" + ("2" * 64),
        authority_profile_source_receipt_id="sha256:" + ("3" * 64),
    )

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            control_loop_authority_policy=malformed,
        ),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert not result.accepted
    assert FAIL_SIGNER_RUNTIME_CONFIG_INVALID in result.rejection_reasons
    assert service.calls == []


@pytest.mark.parametrize("relation", ["same", "nested", "ancestor"])
def test_runtime_wiring_rejects_overlapping_runtime_roots(
    tmp_path: Path,
    relation: str,
) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    repo = tmp_path / "repo"
    repo.mkdir()
    state = tmp_path / "state"
    runtime = state / "resident"
    signer_runtime = {
        "same": runtime,
        "nested": runtime / "signer",
        "ancestor": state,
    }[relation]
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(
            tmp_path,
            public_key,
            repo_root=repo,
            runtime_root=runtime,
            signer_runtime_root=signer_runtime,
            socket_path=runtime / "reddog-signer.sock",
            control_loop_anchor_path=signer_runtime / "anchor.json",
        ),
        _resolver(private_key),
        serve_bounded=service,
    )

    assert not result.accepted
    assert FAIL_SIGNER_RUNTIME_CONTROL_ANCHOR_INVALID in result.rejection_reasons
    assert service.calls == []


def test_invalid_config_profile_or_peer_policy_rejects(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    bad_config = run_reddog_signer_socket_service_runtime_wiring(
        "not-config",  # type: ignore[arg-type]
        resolver,
        serve_bounded=service,
    )
    bad_profile = run_reddog_signer_socket_service_runtime_wiring(
        _config(tmp_path, public_key, key_provider_profile={"signer_profile_id": "only-one-field"}),
        resolver,
        serve_bounded=service,
    )
    bad_policy = run_reddog_signer_socket_service_runtime_wiring(
        _config(tmp_path, public_key, peer_policy={"uid_to_principal": {}}),
        resolver,
        serve_bounded=service,
    )

    assert FAIL_SIGNER_RUNTIME_CONFIG_INVALID in bad_config.rejection_reasons
    assert FAIL_SIGNER_RUNTIME_PROFILE_INVALID in bad_profile.rejection_reasons
    assert FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID in bad_policy.rejection_reasons
    assert service.calls == []


def test_service_reject_exception_or_wrong_type_rejects(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    config = _config(tmp_path, public_key)
    resolver = _resolver(private_key)

    rejected = run_reddog_signer_socket_service_runtime_wiring(
        config,
        resolver,
        serve_bounded=CapturingBoundedService(
            IsolatedSignerSocketResidentServiceResult(
                accepted=False,
                status=SIGNER_SOCKET_RESIDENT_SERVICE_REJECT,
                rejection_reasons=("FAIL_SOCKET",),
            )
        ),
    )
    raised = run_reddog_signer_socket_service_runtime_wiring(
        config,
        resolver,
        serve_bounded=RaisingBoundedService(),
    )
    wrong = run_reddog_signer_socket_service_runtime_wiring(
        config,
        resolver,
        serve_bounded=CapturingBoundedService(result={"not": "service-result"}),
    )

    assert FAIL_SIGNER_RUNTIME_SERVICE_REJECTED in rejected.rejection_reasons
    assert rejected.service_result["status"] == SIGNER_SOCKET_RESIDENT_SERVICE_REJECT
    assert FAIL_SIGNER_RUNTIME_SERVICE_REJECTED in raised.rejection_reasons
    assert FAIL_SIGNER_RUNTIME_SERVICE_INVALID in wrong.rejection_reasons


def test_result_serialization_contains_no_secret_material_or_backend(tmp_path: Path) -> None:
    private_key = _private_key()
    public_key = _public_text(private_key)
    result = run_reddog_signer_socket_service_runtime_wiring(
        _config(tmp_path, public_key),
        _resolver(private_key),
        serve_bounded=CapturingBoundedService(),
    )

    text = json.dumps(result.to_dict(), sort_keys=True)

    assert "backend" not in text
    assert SIGNING_KEY_PREFIX not in text
    assert AUDIT_KEY_PREFIX not in text
    assert "0123456789abcdef" not in text
    assert result.no_file_io_performed is False
    assert result.no_process_spawned is False
    assert result.no_repo_mutation_performed is False
    assert result.no_holoindex_reindex_performed is False


def test_module_has_no_env_shell_file_repo_openclaw_hermes_or_holoindex_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "os",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "git",
        "holo_index",
    }
    banned_name_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_attrs = {
        "getenv",
        "environ",
        "system",
        "popen",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "spawn",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
    }
    banned_name_fragments = ("openclaw", "hermes", "worktree", "holoindex")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert not any(fragment in node.module.lower() for fragment in banned_name_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_name_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs


# Admission composition fixtures are synthetic; no operating trust is enrolled.
from contextlib import contextmanager
from dataclasses import asdict, replace
from types import SimpleNamespace
import weakref
from modules.communication.moltbot_bridge.src import (
    reddog_signer_socket_service_runtime_wiring as grant_runtime,
    reddog_signer_owner_e0_current_selection as grant_owner,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_binding import resolve_secret_grant_target_binding
from modules.communication.moltbot_bridge.src.reddog_signer_wsp71_ephemeral_backend_factory import Wsp71EphemeralSignerBackendFactory
from modules.communication.moltbot_bridge.tests import (
    test_reddog_signer_root_protected_use_composition as protected_fixture,
    test_reddog_signer_wsp71_ephemeral_backend_factory as factory_fixture,
    test_reddog_signer_owner_controlled_e0_admission as owner_fixture,
)


def _admission_root_case(tmp_path, monkeypatch):
    admission_type = getattr(grant_runtime, "SignerSocketServiceGrantAdmission", None)
    assert admission_type is not None, "missing independent owner-held grant runtime API"
    old_policy = owner_fixture._policy

    def low_policy(**kwargs):
        value = old_policy(**kwargs)
        value.update(allowed_operations=["signed_0102_readonly_review:foundup_module"],
                     allowed_authority_tiers=["HIGH", "LOW"], consensus_required_tiers=["HIGH"])
        return value

    monkeypatch.setattr(owner_fixture, "_policy", low_policy)
    monkeypatch.setattr(protected_fixture.time, "time", lambda: factory_fixture.grant_fixture.NOW)
    values = protected_fixture.runtime(tmp_path / "root-owner", monkeypatch)
    protected_fixture._install_current(values, protected_fixture.signed_snapshot(values))
    protected_fixture._bind_router(values, monkeypatch)
    owner_fixture._CURRENT_SELECTION.update(run_packet_path=str(tmp_path / "synthetic-packet.json"),
                                            session_id="synthetic-session",
                                            config_raw_digest=owner_fixture._raw_file_digest(values["config_path"]))
    with grant_owner.lease_validated_owner_e0_current_admission(
        owner_config_path=values["owner_config_path"], repo_root=values["repo"],
        policy=values["policy"],
    ) as owner:
        pass
    return admission_type, values, owner


def _admission_store(tmp_path, owner):
    fixture = factory_fixture.grant_fixture
    policy = owner.policy
    config = fixture.SignerGrantReplayStoreConfig(
        nonce_path=Path(policy["replay_path"]), nonce_root=Path(policy["replay_root"]),
        high_water_path=tmp_path / "high-water" / "authority.sqlite3",
        high_water_root=tmp_path / "high-water", repo_root=Path(owner.config.repo_root),
        replay_store_binding_digest=fixture._binding().replay_store_binding_digest,
        replay_store_id=policy["replay_store_id"],
        durability_receipt_id=policy["replay_store_durability_receipt_id"],
    )
    fixture._provision_store(config)
    return fixture.DurableSignerSecretGrantNonceStore(
        config, integrity_key=fixture.INTEGRITY_KEY, clock=lambda: fixture.NOW)


def _admission_oracle(values, owner):
    durable = protected_fixture.UncomposedDurableSignerGrantRevocationOracle(
        binding=values["binding"], policy=values["policy"],
        reader=values["store"].reader(), witness=values["witness"].reader(),
        anchor=values["client"], principal_key_resolver=owner.resolver,
        signature_verifier=protected_fixture.Ed25519SignatureVerifier(),
        clock=lambda: factory_fixture.grant_fixture.NOW,
    )
    return protected_fixture.RootAuthorizedSignerGrantRevocationOracle(
        durable=durable, protected_use=protected_fixture._protected_client(values))


def _admission_request(values, owner, store):
    fixture = factory_fixture.grant_fixture
    binding = resolve_secret_grant_target_binding(owner.policy, store)
    operation = owner.policy["allowed_operations"][0]
    text = 'reddog-workauth.v1.' + json.dumps(
        {"authority_tier": "LOW", "requested_operation": operation,
         "work_order_id": "synthetic-runtime-grant"}, sort_keys=True, separators=(",", ":"))
    request = factory_fixture.signer_fixture._request(
        binding.signer_public_key, signing_input=text,
        payload_digest=factory_fixture.signer_fixture._request_digest(text),
        requester_principal_id=binding.issuer_principal_id, key_epoch=binding.key_epoch,
        requested_operation=operation, authority_tier="LOW", consensus_receipt_digest=None,
    )
    grant = fixture._grant(request, store, **asdict(binding))
    grant["signature"] = protected_fixture.encode_ed25519_signature(
        values["grant_private"].sign(fixture.canonical_signer_secret_access_grant_input(grant).encode("ascii")))
    peer = replace(fixture._peer(), peer_principal_id=request.requester_principal_id)
    return request, grant, peer


def _admission_case(tmp_path, monkeypatch):
    admission_type, values, owner = _admission_root_case(tmp_path, monkeypatch)
    store = _admission_store(tmp_path, owner)
    oracle = _admission_oracle(values, owner)
    profile = grant_runtime._profiles(owner.config)[0][0]
    resolver = factory_fixture._Resolver({
        profile.signing_key_ref: _private_key_secret(values["target_private"]),
        profile.audit_mac_key_ref: _audit_secret(),
    })
    request, grant, peer = _admission_request(values, owner, store)
    admission = admission_type(owner_config_path=values["owner_config_path"],
                               owner_policy=owner.policy, replay_store=store,
                               revocation_oracle=oracle)
    attached = _admission_attached_config(owner, monkeypatch)
    case = SimpleNamespace(config=attached, owner=owner, admission=admission,
                           resolver=resolver, request=request, grant=grant, peer=peer,
                           active=False, events=[], builds=[], values=values)
    real_lease = grant_owner.lease_validated_owner_e0_current_admission

    @contextmanager
    def tracked_lease(**kwargs):
        with real_lease(**kwargs) as selected:
            case.active = True
            case.events.append("enter")
            try:
                yield selected
            finally:
                assert all(ref() is None for ref in case.builds + case.signing_backends)
                case.active = False
                case.events.append("exit")

    monkeypatch.setattr(grant_owner, "lease_validated_owner_e0_current_admission", tracked_lease)
    monkeypatch.setattr(grant_runtime, "lease_validated_owner_e0_current_admission", tracked_lease, raising=False)
    _observe_admission_resolution(case, monkeypatch)
    _observe_admission_root_roundtrip(case, monkeypatch)
    return case


def _admission_attached_config(owner, monkeypatch):
    from modules.communication.moltbot_bridge.src import reddog_signer_socket_service_runtime_bootstrap as bootstrap
    from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import SignerPeerInstanceBinding, SignerPeerProfileBinding
    profile = grant_runtime._profiles(owner.config)[0][0]
    selected = owner.selection
    binding = SignerPeerInstanceBinding(
        run_packet_id="sha256:" + "a" * 64, config_digest=selected["config_digest"],
        session_id="synthetic-session", socket_path=str(owner.config.socket_path),
        signer_profiles=(SignerPeerProfileBinding(profile.signer_profile_id,
                         profile.expected_public_key, profile.expected_key_epoch),),
        manifest_id=selected["manifest_id"], artifact_generation_digest=selected["artifact_generation_digest"],
        generation=selected["generation"], generation_revision=selected["generation_revision"],
        owner_config_id=selected["owner_config_id"],
    )
    attached = replace(owner.config, signer_peer_instance_binding=binding,
                       system_service_owner_config_id=selected["owner_config_id"])

    def attach(config, *args, **kwargs):
        # Explicit synthetic packet-loader boundary; production config stays real.
        assert asdict(config) == asdict(owner.config)
        return attached

    monkeypatch.setattr(bootstrap, "_attach_peer_binding", attach)
    return attached


def _observe_admission_resolution(case, monkeypatch):
    real_call = Wsp71EphemeralSignerBackendFactory.__call__
    real_resolve = case.resolver.resolve
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import Ed25519SignerBackend
    real_sign = Ed25519SignerBackend.sign
    from modules.communication.moltbot_bridge.src import reddog_signer_resolve_per_sign_backend as backend_module
    real_verify = backend_module.signature_matches
    case.signing_backends = []

    def tracked_verify(*args):
        assert case.active is True
        case.events.append("verify")
        return real_verify(*args)

    def tracked_sign(backend, request, peer):
        assert case.active is True
        case.signing_backends.append(weakref.ref(backend))
        case.events.append("sign")
        return real_sign(backend, request, peer)

    def tracked_call(factory):
        assert case.active is True
        result = real_call(factory)
        if result.backend is not None:
            case.builds.append(weakref.ref(result.backend))
        return result

    def tracked_resolve(reference, requester_id=None):
        assert case.active is True
        assert case.admission.replay_store.consume_grant(case.grant) is False
        case.events.append("resolve")
        return real_resolve(reference, requester_id)

    monkeypatch.setattr(Wsp71EphemeralSignerBackendFactory, "__call__", tracked_call)
    monkeypatch.setattr(case.resolver, "resolve", tracked_resolve)
    monkeypatch.setattr(Ed25519SignerBackend, "sign", tracked_sign)
    monkeypatch.setattr(backend_module, "signature_matches", tracked_verify)


def _observe_admission_root_roundtrip(case, monkeypatch):
    module = protected_fixture.root_client_module
    original = module._root_socket_roundtrip

    def roundtrip(*args):
        assert case.active is False, "root RPC while owner generation lease held"
        operation = json.loads(args[1]).get("operation")
        if operation == "PROTECTED_USE_ACQUIRE":
            case.events.append("root_acquire")
        elif operation == "PROTECTED_USE_FINISH":
            case.events.append("root_finish")
        return original(*args)

    monkeypatch.setattr(module, "_root_socket_roundtrip", roundtrip)


def _admission_wire(case, backend, grant):
    fixture = factory_fixture.grant_fixture
    wire = {"schema_version": fixture.SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
            "request": case.request.to_dict(), "secret_access_grant": grant}
    if grant is None:
        wire.pop("secret_access_grant")
    return json.loads(fixture.handle_reddog_isolated_signer_socket_request(
        json.dumps(wire).encode("utf-8"), peer=case.peer, backend=backend))


@pytest.mark.parametrize("shadow_boundary", [False, True])
def test_grant_runtime_actual_v2_lazy_one_use_and_replay(tmp_path, monkeypatch, shadow_boundary):
    case = _admission_case(tmp_path, monkeypatch)

    def serve(**kwargs):
        assert case.active is False and case.resolver.calls == []
        backend = kwargs["backend"]
        assert type(backend) is factory_fixture.grant_fixture.ResolvePerSignSignerBackend
        if shadow_boundary:
            backend.grant_boundary.authorize_consumed_use = lambda grant, action: action()
        assert _admission_wire(case, backend, None)["accepted"] is False
        assert case.resolver.calls == []
        bad = {**case.grant, "signature": "invalid-signature"}
        assert _admission_wire(case, backend, bad)["accepted"] is False
        assert case.resolver.calls == []
        response = _admission_wire(case, backend, case.grant)
        assert response["accepted"] is True, response["rejection_code"]
        assert protected_fixture.Ed25519SignatureVerifier().verify(
            case.request.signer_public_key, case.request.signing_input, response["signature"])
        assert len(case.resolver.calls) == 2 and len(case.builds) == 1
        assert _admission_wire(case, backend, case.grant)["accepted"] is False
        assert len(case.resolver.calls) == 2
        return CapturingBoundedService()(**kwargs)

    result = run_reddog_signer_socket_service_runtime_wiring(
        case.config, case.resolver, serve_bounded=serve, secret_grant_admission=case.admission)
    assert result.accepted is True, result.rejection_reasons
    assert case.events == ["enter", "exit", "root_acquire", "enter",
                           "resolve", "resolve", "sign", "verify", "exit", "root_finish"]
    assert case.active is False and all(ref() is None for ref in case.builds)
    assert len(case.signing_backends) == 1 and all(ref() is None for ref in case.signing_backends)


def test_grant_runtime_rejects_substituted_consuming_boundary(tmp_path, monkeypatch):
    case = _admission_case(tmp_path, monkeypatch)
    fixture = factory_fixture.grant_fixture
    observed = []

    def serve(**kwargs):
        boundary = fixture.SignerSecretAccessGrantBoundary(
            nonce_store=case.admission.replay_store,
            revocation_oracle=fixture.AtomicSignerSecretGrantRevocationOracle(),
            clock=lambda: fixture.NOW,
        )
        backend = replace(kwargs["backend"], grant_boundary=boundary)
        response = _admission_wire(case, backend, case.grant)
        observed.append((response["accepted"], len(case.resolver.calls), len(case.builds)))
        return CapturingBoundedService()(**kwargs)

    result = run_reddog_signer_socket_service_runtime_wiring(
        case.config, case.resolver, serve_bounded=serve, secret_grant_admission=case.admission)
    assert result.accepted is True, result.rejection_reasons
    assert observed == [(False, 0, 0)]


@pytest.mark.parametrize("corruption", ["ownerless_factory", "shadowed_lease", "binding_mismatch"])
def test_grant_runtime_requires_matching_factory_owner(tmp_path, monkeypatch, corruption):
    case = _admission_case(tmp_path, monkeypatch)

    def serve(**kwargs):
        backend = kwargs["backend"]
        factory = backend.backend_factory
        if corruption in ("ownerless_factory", "shadowed_lease"):
            factory = replace(factory, owner_context=None)
            if corruption == "shadowed_lease":
                from contextlib import nullcontext
                factory.__dict__["signing_authority_lease"] = lambda: nullcontext(backend.binding)
        else:
            from modules.communication.moltbot_bridge.src.reddog_signer_wsp71_ephemeral_backend_factory import _lease_authenticated_factory
            binding = factory.owner_context[2]
            # Exercise the guard directly so grant validation cannot mask this check.
            expected = replace(binding, signer_profile_id=binding.signer_profile_id + "-substituted")
            before = len(case.events)
            with pytest.raises(ValueError, match="signer_grant_current_owner_mismatch"):
                with _lease_authenticated_factory(factory, expected, backend.grant_boundary):
                    pytest.fail("mismatched binding entered protected body")
            assert case.events[before:] == ["enter", "exit"]
            assert case.resolver.calls == [] and case.builds == []
            return CapturingBoundedService()(**kwargs)
        backend = replace(backend, backend_factory=factory)
        response = _admission_wire(case, backend, case.grant)
        assert response["accepted"] is False
        assert case.resolver.calls == [] and case.builds == []
        assert case.active is False
        return CapturingBoundedService()(**kwargs)

    result = run_reddog_signer_socket_service_runtime_wiring(
        case.config, case.resolver, serve_bounded=serve, secret_grant_admission=case.admission)
    assert result.accepted is True, result.rejection_reasons
    assert "sign" not in case.events and "resolve" not in case.events


@pytest.mark.parametrize("corruption", ["config", "peer", "owner_id", "multiple_profiles", "specialized_policy",
                                           "store", "store_path", "oracle_type", "durable_binding", "protected_owner"])
def test_grant_runtime_rejects_substituted_admission_before_resolve(tmp_path, monkeypatch, corruption):
    case = _admission_case(tmp_path, monkeypatch)
    if corruption == "config":
        case.config = replace(case.config, max_requests=case.config.max_requests + 1)
    elif corruption == "peer":
        case.config = replace(case.config, signer_peer_instance_binding=replace(
            case.config.signer_peer_instance_binding, session_id="wrong-session"))
    elif corruption == "owner_id":
        case.config = replace(case.config, system_service_owner_config_id="sha256:" + "f" * 64)
    elif corruption == "multiple_profiles":
        profiles = case.config.key_provider_profiles
        case.config = replace(case.config, key_provider_profiles=profiles + profiles)
    elif corruption == "specialized_policy":
        case.config = replace(case.config, conversation_scope_signer_policy={"unexpected": True})
    elif corruption == "store":
        case.admission = replace(case.admission, replay_store=factory_fixture.grant_fixture._store(tmp_path / "other"))
    elif corruption == "store_path":
        case.admission = replace(case.admission, replay_store=_alternate_admission_store(case, tmp_path))
    elif corruption == "oracle_type":
        case.admission = replace(case.admission, revocation_oracle=SimpleNamespace(binding=case.owner.revocation_binding))
    elif corruption == "durable_binding":
        case.admission.revocation_oracle._durable.binding = replace(
            case.owner.revocation_binding, primary_store_id="substituted-store")
    else:
        old = protected_fixture._protected_client(case.values)
        from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_protected_use_client as client
        state = client._lookup_client(old)
        changed = replace(state, owner_config_id="sha256:" + "f" * 64)
        foreign = object.__new__(client.RootProtectedUseAuthority)
        client._issue_client(foreign, changed)
        case.admission.revocation_oracle._protected_use = foreign
    service = CapturingBoundedService()
    result = run_reddog_signer_socket_service_runtime_wiring(
        case.config, case.resolver, serve_bounded=service, secret_grant_admission=case.admission)
    assert result.accepted is False and result.rejection_reasons
    assert service.calls == [] and case.resolver.calls == []
    assert case.active is False


def _alternate_admission_store(case, tmp_path):
    fixture = factory_fixture.grant_fixture
    config = replace(case.admission.replay_store._config,
                     nonce_root=tmp_path / "alternate-nonce",
                     nonce_path=tmp_path / "alternate-nonce" / "grant-nonces.json",
                     high_water_root=tmp_path / "alternate-high-water",
                     high_water_path=tmp_path / "alternate-high-water" / "authority.sqlite3")
    fixture._provision_store(config)
    return fixture.DurableSignerSecretGrantNonceStore(
        config, integrity_key=fixture.INTEGRITY_KEY, clock=lambda: fixture.NOW)


@pytest.mark.parametrize("failure", ["service_exception", "service_rejection", "resolver_exception"])
def test_grant_runtime_exits_generation_lease_on_failure(tmp_path, monkeypatch, failure):
    case = _admission_case(tmp_path, monkeypatch)

    def serve(**kwargs):
        assert case.active is False and case.resolver.calls == []
        case.events.append("serve")
        if failure == "service_exception":
            raise RuntimeError("synthetic service failure")
        if failure == "resolver_exception":
            def reject_resolve(*args, **kwargs):
                raise RuntimeError("synthetic resolution failure")
            monkeypatch.setattr(case.resolver, "resolve", reject_resolve)
            assert _admission_wire(case, kwargs["backend"], case.grant)["accepted"] is False
        return IsolatedSignerSocketResidentServiceResult(
            accepted=False, status=SIGNER_SOCKET_RESIDENT_SERVICE_REJECT,
            rejection_reasons=("synthetic_rejection",), socket_path=str(case.config.socket_path),
            requests_handled=0, response_digests=(), socket_removed=True)

    result = run_reddog_signer_socket_service_runtime_wiring(
        case.config, case.resolver, serve_bounded=serve, secret_grant_admission=case.admission)
    assert result.accepted is False
    expected = ["enter", "exit", "serve"]
    if failure == "resolver_exception":
        expected += ["root_acquire", "enter", "exit", "root_finish"]
    assert case.events == expected
    assert case.active is False and case.resolver.calls == []


def test_grant_runtime_rechecks_generation_after_root_acquire(tmp_path, monkeypatch):
    case = _admission_case(tmp_path, monkeypatch)
    original = dict(owner_fixture._CURRENT_SELECTION)
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_protected_use_client as client
    real_exchange = client._exchange
    finish_results = []

    def rotated_exchange(*args):
        operation = args[1]
        assert case.active is False, "root exchange while owner lease held"
        try:
            result = real_exchange(*args)
        except Exception as exc:
            if operation == client.OP_FINISH:
                finish_results.append(("raised", type(exc).__name__))
            raise
        if operation == client.OP_ACQUIRE:
            owner_fixture._CURRENT_SELECTION["artifact_generation_digest"] = "sha256:" + "f" * 64
        elif operation == client.OP_FINISH:
            finish_results.append(("returned", result))
        return result

    monkeypatch.setattr(client, "_exchange", rotated_exchange)

    def serve(**kwargs):
        assert case.active is False and case.resolver.calls == []
        response = _admission_wire(case, kwargs["backend"], case.grant)
        assert response["accepted"] is False
        assert case.resolver.calls == [] and case.builds == []
        return CapturingBoundedService()(**kwargs)

    try:
        result = run_reddog_signer_socket_service_runtime_wiring(
            case.config, case.resolver, serve_bounded=serve, secret_grant_admission=case.admission)
    finally:
        owner_fixture._CURRENT_SELECTION.clear()
        owner_fixture._CURRENT_SELECTION.update(original)
    assert result.accepted is True, result.rejection_reasons
    # Service completion is not signing success; failed FINISH does not prove cleanup.
    assert [event for event in case.events if event != "root_finish"] == ["enter", "exit", "root_acquire"]
    assert len(finish_results) == 2 and all(kind == "raised" for kind, _ in finish_results)
    assert case.active is False
