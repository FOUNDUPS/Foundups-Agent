"""Tests for REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    IsolatedSignerSocketResidentServiceResult,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SIGNING_KEY_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_bootstrap import (
    FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED,
    FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT,
    SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED,
    run_reddog_signer_socket_service_runtime_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_verified_outcome_authority_admission import (
    admit_verified_outcome_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
    run_reddog_signer_socket_service_run_packet_supply,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_runtime_bootstrap.py"
)


pytest.importorskip("cryptography")


class FakeResolver:
    def __init__(self, values: dict[str, str], ttl: int = 60) -> None:
        self.values = values
        self.ttl = ttl
        self.calls: list[tuple[str, str | None]] = []

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        self.calls.append((reference, requester_id))
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=self.ttl,
            session_id="wsp71-session",
            _secret_value=self.values[reference],
        )


class CapturingBoundedService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return IsolatedSignerSocketResidentServiceResult(
            accepted=True,
            status=SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
            rejection_reasons=(),
            socket_path=str(kwargs["socket_path"]),
            requests_handled=int(kwargs["max_requests"]),
            response_digests=("sha256:response",),
            socket_removed=True,
        )


class _ManifestSelection:
    pass


class _ManifestSelectionBoundary:
    def __init__(self, capability: object, values: dict[str, object]) -> None:
        self._capability = capability
        self._values = values

    def consume(self, value: object) -> dict[str, object]:
        if value is not self._capability:
            raise ValueError("manifest_selection_unverified")
        self._capability = None
        return dict(self._values)


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


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
            "op://prod-vault/reddog-signing/private": _private_key_secret(private_key),
            "op://prod-vault/reddog-audit/mac": _audit_secret(),
        }
    )


def _config(public_key: str, *, socket_path: Path, **overrides: object) -> dict[str, object]:
    signer_runtime = (
        socket_path.parent.parent / f"{socket_path.parent.name}-signer-state"
    )
    values: dict[str, object] = {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "runtime_root": str(socket_path.parent),
        "signer_runtime_root": str(signer_runtime),
        "socket_path": str(socket_path),
        "control_loop_anchor_path": str(signer_runtime / "anchor.json"),
        "control_loop_authority_policy": {
            "issuer_principal_id": "github:012",
            "signer_public_key": public_key,
            "key_epoch": "epoch-1",
            "consensus_receipt_digest": "sha256:" + ("1" * 64),
            "authority_profile_digest": "sha256:" + ("2" * 64),
            "authority_profile_source_receipt_id": "sha256:" + ("3" * 64),
        },
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "max_requests": 3,
        "timeout_s": 2.5,
        "max_request_bytes": 4096,
        "max_response_bytes": 8192,
        "key_provider_profile": {
            "signer_profile_id": "signer-profile-1",
            "signer_agent_id": "signer:reddog-authority",
            "signing_key_ref": "op://prod-vault/reddog-signing/private",
            "audit_mac_key_ref": "op://prod-vault/reddog-audit/mac",
            "expected_public_key": public_key,
            "expected_key_fingerprint": public_key_fingerprint(public_key),
            "expected_key_epoch": "epoch-1",
            "permission_snapshot_digest": "sha256:permission",
            "ttl_seconds": 60,
        },
        "peer_policy": {
            "uid_to_principal": {"1001": "github:mjtrout"},
            "allowed_gids": [1002],
            "transport": "unix_socket",
            "credential_source_prefix": "kernel_peer_credential",
        },
    }
    values.update(overrides)
    return values


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _launch_binding(
    repo: Path,
    config_path: Path,
    *,
    session_id: str = "bootstrap-test",
) -> dict[str, object]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    single = payload.pop("key_provider_profile", None)
    if single is not None:
        payload["key_provider_profiles"] = [single]
        _write_json(config_path, payload)
    packet_path = config_path.parent / f"{config_path.stem}-run-packet.json"
    owner_path = config_path.parent.parent / "signer-owner" / "owner.json"
    supplied = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo,
        config_path=config_path,
        output_path=packet_path,
        owner_authority_config_path=owner_path,
        session_id=session_id,
        python_executable=sys.executable,
    )
    assert supplied.accepted is True
    capability = _ManifestSelection()
    selection = {
        "manifest_id": "sha256:" + ("a" * 64),
        "artifact_generation_digest": "sha256:" + ("b" * 64),
        "config_digest": supplied.config_digest,
        "config_raw_digest": _raw_digest(config_path),
        "run_packet_digest": _raw_digest(packet_path),
        "repo_root": str(repo.resolve()),
        "runtime_root": str(config_path.parent.resolve()),
        "config_path": str(config_path.resolve()),
        "run_packet_path": str(packet_path.resolve()),
        "generation": 1,
        "generation_revision": "a" * 64,
        "selection_issued_at": 100,
        "selection_expires_at": 130,
        "owner_config_id": "sha256:" + ("c" * 64),
    }
    return {
        "expected_config_digest": supplied.config_digest,
        "run_packet_path": packet_path,
        "expected_session_id": session_id,
        "expected_owner_authority_config_path": owner_path,
        "manifest_selection": capability,
        "manifest_selection_boundary": _ManifestSelectionBoundary(
            capability, selection
        ),
    }


def _payload_digest(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _raw_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _rehash_packet(payload: dict[str, object]) -> None:
    without_id = {
        key: value for key, value in payload.items() if key != "run_packet_id"
    }
    raw = json.dumps(
        without_id,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    payload["run_packet_id"] = (
        "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
    )


def test_bootstrap_reads_outside_repo_config_and_runs_runtime_wiring(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    public_key = _public_text(private_key)
    config_path = _write_json(
        runtime / "signer-service.json",
        _config(public_key, socket_path=runtime / "signer.sock"),
    )
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=resolver,
        serve_bounded=service,
        verified_outcome_signing_authority_supplier=lambda: (_ for _ in ()).throw(
            AssertionError("dormant_outcome_policy_touched_root_socket")
        ),
        **_launch_binding(repo, config_path),
    )

    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED
    assert result.config_path == str(config_path.resolve())
    assert result.config_digest and result.config_digest.startswith("sha256:")
    assert result.runtime_result is not None
    assert result.runtime_result["status"] == "SIGNER_SOCKET_RUNTIME_WIRING_SERVED"
    assert len(service.calls) == 1
    assert service.calls[0]["max_requests"] == 3
    assert resolver.calls == [
        ("op://prod-vault/reddog-signing/private", "signer:reddog-authority"),
        ("op://prod-vault/reddog-audit/mac", "signer:reddog-authority"),
    ]
    assert result.no_env_parsed is True
    assert result.no_holoindex_reindex_performed is True


def test_outcome_authority_supplier_runs_only_for_configured_policy() -> None:
    calls: list[str] = []
    authority = object()

    def supply():
        calls.append("called")
        return authority

    dormant = admit_verified_outcome_authority(
        None,
        None,
        lambda: (_ for _ in ()).throw(AssertionError("supplier_called")),
    )
    active = admit_verified_outcome_authority(
        {"configured": True},
        None,
        supply,
    )

    assert dormant is None
    assert active is authority
    assert calls == ["called"]


def test_configured_outcome_policy_fails_closed_when_supplier_fails() -> None:
    authority = admit_verified_outcome_authority(
        {"configured": True},
        None,
        lambda: (_ for _ in ()).throw(RuntimeError("socket unavailable")),
    )

    assert authority is None


def test_bootstrap_rejects_legacy_selection_downgrade(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config_path = _write_json(
        runtime / "signer-service.json",
        _config(
            _public_text(private_key),
            socket_path=runtime / "signer.sock",
        ),
    )
    launch = _launch_binding(repo, config_path)
    boundary = launch["manifest_selection_boundary"]
    assert isinstance(boundary, _ManifestSelectionBoundary)
    for field in (
        "generation",
        "generation_revision",
        "selection_issued_at",
        "selection_expires_at",
        "owner_config_id",
    ):
        boundary._values.pop(field)
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=resolver,
        serve_bounded=service,
        **launch,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED in result.rejection_reasons
    assert resolver.calls == []
    assert service.calls == []


@pytest.mark.parametrize(
    "mutation",
    (
        "session",
        "socket",
        "config",
        "argv",
        "python_executable",
        "python_module",
        "profile_count",
        "unknown_field",
    ),
)
def test_bootstrap_rejects_attacker_rehashed_run_packet(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config_path = _write_json(
        runtime / "signer-service.json",
        _config(_public_text(private_key), socket_path=runtime / "signer.sock"),
    )
    launch = _launch_binding(repo, config_path)
    packet_path = Path(str(launch["run_packet_path"]))
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if mutation == "session":
        packet["session_id"] = "attacker-session"
        launch["expected_session_id"] = "attacker-session"
    elif mutation == "socket":
        packet["socket_path"] = str(runtime / "attacker.sock")
    elif mutation == "config":
        packet["config_digest"] = "sha256:" + "9" * 64
    elif mutation == "argv":
        packet["argv"].extend(["--attacker", "value"])
    elif mutation == "python_executable":
        packet["argv"][0] = str(tmp_path / "attacker-python.exe")
    elif mutation == "python_module":
        packet["python_module"] = "attacker.module"
        packet["argv"][2] = "attacker.module"
    elif mutation == "profile_count":
        packet["profile_count"] = 99
    else:
        packet["attacker_field"] = "value"
    _rehash_packet(packet)
    _write_json(packet_path, packet)
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=resolver,
        serve_bounded=service,
        **launch,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED in result.rejection_reasons
    assert resolver.calls == []
    assert service.calls == []


def test_bootstrap_rejects_test_provider_after_signed_launch_admission(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config_path = _write_json(
        runtime / "signer-service.json",
        _config(
            _public_text(private_key),
            socket_path=runtime / "signer.sock",
        ),
    )
    launch = _launch_binding(repo, config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["provider_mode"] = "TEST_ONLY_DRYRUN"
    config["allow_test_only_key_material"] = True
    _write_json(config_path, config)
    config_digest = _payload_digest(config)
    packet_path = Path(str(launch["run_packet_path"]))
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["provider_mode"] = "TEST_ONLY_DRYRUN"
    packet["config_digest"] = config_digest
    _rehash_packet(packet)
    _write_json(packet_path, packet)
    boundary = launch["manifest_selection_boundary"]
    assert isinstance(boundary, _ManifestSelectionBoundary)
    boundary._values.update(
        {
            "config_digest": config_digest,
            "config_raw_digest": _raw_digest(config_path),
            "run_packet_digest": _raw_digest(packet_path),
        }
    )
    launch["expected_config_digest"] = config_digest
    resolver = _resolver(private_key)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=resolver,
        serve_bounded=service,
        **launch,
    )

    assert result.accepted is False
    assert FAIL_SIGNER_BOOTSTRAP_CONFIG_MALFORMED in result.rejection_reasons
    assert resolver.calls == []
    assert service.calls == []


def test_bootstrap_accepts_multi_profile_config_without_secret_return(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    principal_key = _private_key()
    reddog_key = _private_key()
    principal_public = _public_text(principal_key)
    reddog_public = _public_text(reddog_key)
    payload = _config(principal_public, socket_path=runtime / "signer.sock")
    principal_profile = dict(payload["key_provider_profile"])
    principal_profile.update(
        {
            "signer_profile_id": "principal-profile",
            "signer_agent_id": "signer:principal",
            "signing_key_ref": "op://prod-vault/principal/private",
            "audit_mac_key_ref": "op://prod-vault/principal/audit",
            "expected_public_key": principal_public,
            "expected_key_fingerprint": public_key_fingerprint(principal_public),
        }
    )
    reddog_profile = dict(payload["key_provider_profile"])
    reddog_profile.update(
        {
            "signer_profile_id": "reddog-profile",
            "signer_agent_id": "signer:reddog",
            "signing_key_ref": "op://prod-vault/reddog/private",
            "audit_mac_key_ref": "op://prod-vault/reddog/audit",
            "expected_public_key": reddog_public,
            "expected_key_fingerprint": public_key_fingerprint(reddog_public),
        }
    )
    payload.pop("key_provider_profile")
    payload["key_provider_profiles"] = [principal_profile, reddog_profile]
    config_path = _write_json(runtime / "signer-service.json", payload)
    resolver = FakeResolver(
        {
            "op://prod-vault/principal/private": _private_key_secret(principal_key),
            "op://prod-vault/principal/audit": _audit_secret(b"principal-audit-key-000000000"),
            "op://prod-vault/reddog/private": _private_key_secret(reddog_key),
            "op://prod-vault/reddog/audit": _audit_secret(b"reddog-audit-key-000000000000"),
        }
    )
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=config_path,
        resolver=resolver,
        serve_bounded=service,
        **_launch_binding(repo, config_path),
    )

    assert result.accepted is True
    assert result.status == SIGNER_SOCKET_RUNTIME_BOOTSTRAP_SERVED
    assert result.runtime_result is not None
    receipt = result.runtime_result["key_provider_receipt"]
    assert receipt["ok"] is True
    assert receipt["profile_count"] == 2
    assert receipt["secret_values_returned"] is False
    assert sorted(receipt["public_keys"]) == sorted([principal_public, reddog_public])
    assert resolver.calls == [
        ("op://prod-vault/principal/private", "signer:principal"),
        ("op://prod-vault/principal/audit", "signer:principal"),
        ("op://prod-vault/reddog/private", "signer:reddog"),
        ("op://prod-vault/reddog/audit", "signer:reddog"),
    ]


def test_bootstrap_rejects_missing_relative_inside_and_unreadable_config(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inside = _write_json(repo / "signer-service.json", {})
    malformed = tmp_path / "runtime" / "bad.json"
    malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_text("{not-json", encoding="utf-8")

    missing = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=None,
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )
    relative = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path="signer.json",
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )
    inside_repo = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=inside,
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )
    unreadable = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=malformed,
        resolver=object(),  # type: ignore[arg-type]
        serve_bounded=CapturingBoundedService(),
    )

    assert missing.status == SIGNER_SOCKET_RUNTIME_BOOTSTRAP_REJECT
    for result in (missing, relative, inside_repo, unreadable):
        assert result.rejection_reasons == (
            FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
        )


def test_bootstrap_rejects_hard_linked_config_before_runtime_call(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    public_key = _public_text(private_key)
    source = _write_json(
        tmp_path / "outside.json",
        _config(public_key, socket_path=runtime / "signer.sock"),
    )
    linked = runtime / "signer-service.json"
    linked.parent.mkdir(parents=True)
    try:
        os.link(source, linked)
    except OSError as exc:
        pytest.skip(f"hard-link creation unavailable: {exc}")
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=linked,
        resolver=_resolver(private_key),
        serve_bounded=service,
    )

    assert result.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    )
    assert service.calls == []


def test_bootstrap_rejects_config_runtime_root_mismatch(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    public_key = _public_text(private_key)
    config = _config(public_key, socket_path=runtime / "signer.sock")
    config["runtime_root"] = str(tmp_path / "other-runtime")
    path = _write_json(runtime / "signer-service.json", config)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=path,
        resolver=_resolver(private_key),
        serve_bounded=service,
    )

    assert result.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    )
    assert service.calls == []


@pytest.mark.parametrize("escaped_field", ("socket_path", "control_loop_anchor_path"))
def test_bootstrap_rejects_runtime_artifact_outside_declared_root(
    tmp_path: Path,
    escaped_field: str,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config = _config(
        _public_text(private_key),
        socket_path=runtime / "signer.sock",
    )
    config[escaped_field] = str(tmp_path / "outside" / "escaped")
    path = _write_json(runtime / "signer-service.json", config)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=path,
        resolver=_resolver(private_key),
        serve_bounded=service,
    )

    assert result.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    )
    assert service.calls == []


def test_bootstrap_rejects_nested_control_anchor(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config = _config(
        _public_text(private_key),
        socket_path=runtime / "signer.sock",
    )
    signer_runtime = Path(str(config["signer_runtime_root"]))
    config["control_loop_anchor_path"] = str(
        signer_runtime / "nested" / "anchor.json"
    )
    path = _write_json(runtime / "signer-service.json", config)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=path,
        resolver=_resolver(private_key),
        serve_bounded=service,
    )

    assert result.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    )
    assert service.calls == []


@pytest.mark.parametrize(
    "missing_key",
    ("control_loop_anchor_path", "control_loop_authority_policy"),
)
def test_bootstrap_rejects_current_config_without_control_authority_binding(
    tmp_path: Path,
    missing_key: str,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config = _config(
        _public_text(private_key),
        socket_path=runtime / "signer.sock",
    )
    config.pop(missing_key)
    path = _write_json(runtime / "signer-service.json", config)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=path,
        resolver=_resolver(private_key),
        serve_bounded=service,
    )

    assert result.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    )
    assert service.calls == []


def test_bootstrap_rejects_explicit_v2_config_before_service_invocation(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config = _config(
        _public_text(private_key),
        socket_path=runtime / "signer.sock",
    )
    config["schema_version"] = "reddog_signer_service_config.v2"
    path = _write_json(runtime / "signer-service.json", config)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=path,
        resolver=_resolver(private_key),
        serve_bounded=service,
    )

    assert result.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    )
    assert service.calls == []


def test_bootstrap_rejects_overlapping_resident_and_signer_roots(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    config = _config(
        _public_text(private_key),
        socket_path=runtime / "signer.sock",
    )
    config["signer_runtime_root"] = str(runtime)
    config["control_loop_anchor_path"] = str(runtime / "anchor.json")
    path = _write_json(runtime / "signer-service.json", config)
    service = CapturingBoundedService()

    result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=path,
        resolver=_resolver(private_key),
        serve_bounded=service,
    )

    assert result.rejection_reasons == (
        FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
    )
    assert service.calls == []


def test_bootstrap_rejects_malformed_runtime_shape_and_preserves_runtime_reject(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    private_key = _private_key()
    public_key = _public_text(private_key)
    malformed = _write_json(runtime / "malformed.json", {"key_provider_profile": []})
    wrong_schema = _write_json(
        runtime / "wrong-schema.json",
        _config(
            public_key,
            socket_path=runtime / "wrong-schema.sock",
            schema_version="reddog_signer_service_config.v1",
        ),
    )
    rejected = _write_json(
        runtime / "rejected.json",
        _config(
            public_key,
            socket_path=runtime / "signer.sock",
            allow_test_only_key_material=True,
        ),
    )

    malformed_result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=malformed,
        resolver=_resolver(private_key),
        serve_bounded=CapturingBoundedService(),
    )
    wrong_schema_result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=wrong_schema,
        resolver=_resolver(private_key),
        serve_bounded=CapturingBoundedService(),
    )
    rejected_result = run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo,
        config_path=rejected,
        resolver=_resolver(private_key),
        serve_bounded=CapturingBoundedService(),
    )

    for result in (malformed_result, wrong_schema_result, rejected_result):
        assert result.rejection_reasons == (
            FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION,
        )


def test_bootstrap_module_has_no_env_shell_repo_openclaw_hermes_or_holoindex_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "os",
        "subprocess",
        "socket",
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


# Grant-aware bootstrap integration; synthetic selection is explicit below.
from modules.communication.moltbot_bridge.src import reddog_signer_socket_service_runtime_bootstrap as bootstrap
from modules.communication.moltbot_bridge.tests import test_reddog_signer_socket_service_runtime_wiring as fixture


def test_bootstrap_preserves_lazy_grant_validation(tmp_path, monkeypatch):
    case = fixture._admission_case(tmp_path, monkeypatch)
    # Selection/packet loading is explicitly substituted in this seam probe.
    # Runtime, owner validation, protected-use router and signatures remain real.
    monkeypatch.setattr(bootstrap, "_load_bound_runtime_config", lambda *args: (
        case.config, Path(case.values["config_path"]), case.owner.selection["config_digest"], None))

    def serve(**kwargs):
        assert case.resolver.calls == []
        backend = kwargs["backend"]
        assert fixture._admission_wire(case, backend, None)["accepted"] is False
        assert fixture._admission_wire(case, backend, {**case.grant, "signature": "invalid-signature"})["accepted"] is False
        assert case.resolver.calls == []
        response = fixture._admission_wire(case, backend, case.grant)
        assert response["accepted"] is True
        assert fixture.protected_fixture.Ed25519SignatureVerifier().verify(
            case.request.signer_public_key, case.request.signing_input, response["signature"])
        assert len(case.resolver.calls) == 2
        assert fixture._admission_wire(case, backend, case.grant)["accepted"] is False
        assert len(case.resolver.calls) == 2
        return fixture.CapturingBoundedService()(**kwargs)

    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=case.values["repo"], config_path=case.values["config_path"],
        resolver=case.resolver, serve_bounded=serve,
        secret_grant_admission=case.admission)
    assert result.accepted is True, result.rejection_reasons
    assert case.events == ["enter", "exit", "root_acquire", "enter", "resolve", "resolve",
                           "sign", "verify", "exit", "root_finish"]


def test_bootstrap_rejects_invalid_admission_before_resolution(tmp_path, monkeypatch):
    case = fixture._admission_case(tmp_path, monkeypatch)
    monkeypatch.setattr(bootstrap, "_load_bound_runtime_config", lambda *args: (
        case.config, Path(case.values["config_path"]), case.owner.selection["config_digest"], None))
    service = fixture.CapturingBoundedService()
    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=case.values["repo"], config_path=case.values["config_path"],
        resolver=case.resolver, serve_bounded=service, secret_grant_admission=object())
    assert result.accepted is False
    assert case.resolver.calls == []
    assert service.calls == []


@pytest.mark.parametrize("gate", ["selection", "isolation"])
def test_bootstrap_admission_preserves_pre_resolver_gates(tmp_path, monkeypatch, gate):
    case = fixture._admission_case(tmp_path, monkeypatch)
    if gate == "isolation":
        monkeypatch.setattr(bootstrap, "_load_bound_runtime_config", lambda *args: (
            case.config, Path(case.values["config_path"]), case.owner.selection["config_digest"], None))
    created = []
    service = fixture.CapturingBoundedService()

    def factory():
        created.append(True)
        return case.resolver

    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=case.values["repo"], config_path=None, resolver_factory=factory,
        serve_bounded=service, secret_grant_admission=case.admission,
        process_isolation_required=True, process_isolation_gate=lambda *args, **kwargs: None,
        expected_signer_uid=1234, expected_signer_gid=1234)
    assert result.accepted is False
    expected = (bootstrap.FAIL_SIGNER_BOOTSTRAP_MANIFEST_SELECTION if gate == "selection"
                else bootstrap.FAIL_SIGNER_BOOTSTRAP_PROCESS_ISOLATION)
    assert expected in result.rejection_reasons
    assert created == [] and case.resolver.calls == [] and service.calls == []


def _dependency_supply_case(tmp_path, monkeypatch, *, isolation_accepted=True):
    """Synthetic selection/isolation; actual lazy grant runtime stays in use."""
    from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import SignerProcessIsolationReceipt

    case = fixture._admission_case(tmp_path, monkeypatch)
    order = []

    def load(*args):
        order.append("config")
        return (case.config, Path(case.values["config_path"]),
                case.owner.selection["config_digest"], None)

    def isolate(*args, **kwargs):
        order.append("isolation")
        return SignerProcessIsolationReceipt(
            accepted=isolation_accepted, rejection_reasons=(),
            signer_uid=1234, signer_gid=1234, distinct_consumer_uid=True,
            ptrace_scope_enforced=True, cap_sys_ptrace_absent=True,
            tracer_absent=True, core_dumps_disabled=True,
            dumpable_disabled=True, environment_cleared=True)

    monkeypatch.setattr(bootstrap, "_load_bound_runtime_config", load)
    options = dict(repo_root=case.values["repo"],
                   config_path=case.values["config_path"],
                   process_isolation_required=True, process_isolation_gate=isolate,
                   expected_signer_uid=1234, expected_signer_gid=1234)
    return case, order, options


def _supplied_dependencies(case, **changes):
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_bootstrap_admission import SignerSocketServiceRuntimeDependencies

    values = dict(resolver=case.resolver,
                  principal_key_resolver=fixture.SimpleNamespace(resolve=lambda *args: None),
                  proposal_replay_high_water_store=None,
                  secret_grant_admission=case.admission)
    values.update(changes)
    return SignerSocketServiceRuntimeDependencies(**values)


def test_dependency_supplier_not_called_after_denied_isolation(tmp_path, monkeypatch):
    case, order, options = _dependency_supply_case(
        tmp_path, monkeypatch, isolation_accepted=False)
    calls = []
    service = CapturingBoundedService()
    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        **options, serve_bounded=service,
        runtime_dependencies_supplier=lambda: calls.append("supplier"))
    assert result.accepted is False
    assert bootstrap.FAIL_SIGNER_BOOTSTRAP_PROCESS_ISOLATION in result.rejection_reasons
    assert order == ["config", "isolation"]
    assert calls == [] and case.resolver.calls == [] and service.calls == []


def test_dependency_supplier_not_called_after_real_config_rejection(tmp_path):
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    path = _write_json(runtime / "signer-service.json", _config(
        _public_text(_private_key()), socket_path=runtime / "signer.sock"))
    launch = _launch_binding(repo, path)
    path.write_text("{malformed", encoding="utf-8")
    calls = []
    service = CapturingBoundedService()
    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        repo_root=repo, config_path=path, serve_bounded=service, **launch,
        process_isolation_required=True,
        process_isolation_gate=lambda *args, **kwargs: calls.append("isolation"),
        expected_signer_uid=1234, expected_signer_gid=1234,
        runtime_dependencies_supplier=lambda: calls.append("supplier"))
    assert result.accepted is False
    assert bootstrap.FAIL_SIGNER_BOOTSTRAP_CONFIG_UNREADABLE in result.rejection_reasons
    assert calls == [] and service.calls == []


@pytest.mark.parametrize("conflict", ["isolation_not_required", "resolver",
    "resolver_factory", "principal_key_resolver", "proposal_replay_high_water_store",
    "secret_grant_admission"])
def test_dependency_supplier_rejects_mixed_or_unisolated_supply(tmp_path, monkeypatch, conflict):
    case, order, options = _dependency_supply_case(tmp_path, monkeypatch)
    monkeypatch.setattr(bootstrap, "run_reddog_signer_socket_service_runtime_wiring",
                        lambda *args, **kwargs: pytest.fail("conflicting supply reached wiring"))
    if conflict == "isolation_not_required":
        options["process_isolation_required"] = False
    else:
        options[conflict] = lambda: pytest.fail("explicit dependency factory invoked")
    calls = []
    service = CapturingBoundedService()
    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        **options, serve_bounded=service,
        runtime_dependencies_supplier=lambda: calls.append("supplier"))
    assert result.accepted is False
    assert "FAIL_SIGNER_BOOTSTRAP_DEPENDENCY_SUPPLY" in result.rejection_reasons
    assert calls == [] and case.resolver.calls == [] and service.calls == []


@pytest.mark.parametrize("failure", ["raises", "wrong_type", "resolver_missing",
    "resolver_invalid", "principal_missing", "principal_invalid", "grant_missing", "grant_invalid"])
def test_dependency_supplier_invalid_result_never_reaches_wiring(tmp_path, monkeypatch, failure):
    case, order, options = _dependency_supply_case(tmp_path, monkeypatch)
    monkeypatch.setattr(bootstrap, "run_reddog_signer_socket_service_runtime_wiring",
                        lambda *args, **kwargs: pytest.fail("invalid supply reached wiring"))

    def supply():
        order.append("supplier")
        if failure == "raises":
            raise RuntimeError("synthetic supplier failure")
        if failure == "wrong_type":
            return fixture.SimpleNamespace(resolver=case.resolver,
                                           secret_grant_admission=case.admission)
        field, shape = failure.rsplit("_", 1)
        name = {"resolver": "resolver", "principal": "principal_key_resolver",
                "grant": "secret_grant_admission"}[field]
        return _supplied_dependencies(case, **{name: None if shape == "missing" else object()})

    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        **options, serve_bounded=CapturingBoundedService(), runtime_dependencies_supplier=supply)
    assert result.accepted is False
    assert "FAIL_SIGNER_BOOTSTRAP_DEPENDENCY_SUPPLY" in result.rejection_reasons
    assert order == ["config", "isolation", "supplier"]
    assert case.resolver.calls == [] and case.events == []


@pytest.mark.parametrize("optional_store", [False, True])
def test_dependency_supplier_forwards_once_to_real_lazy_grant_runtime(tmp_path, monkeypatch, optional_store):
    case, order, options = _dependency_supply_case(tmp_path, monkeypatch)
    # This control-only config does not require a proposal high-water store.
    dependencies = _supplied_dependencies(case,
        proposal_replay_high_water_store=object() if optional_store else None)
    real_wiring = bootstrap.run_reddog_signer_socket_service_runtime_wiring

    def supply():
        assert order == ["config", "isolation"] and case.resolver.calls == []
        order.append("supplier")
        return dependencies

    def wiring(config, resolver, **kwargs):
        order.append("wiring")
        assert config is case.config and resolver is dependencies.resolver
        assert kwargs["principal_key_resolver"] is dependencies.principal_key_resolver
        assert kwargs["proposal_replay_high_water_store"] is dependencies.proposal_replay_high_water_store
        assert kwargs["secret_grant_admission"] is dependencies.secret_grant_admission
        return real_wiring(config, resolver, **kwargs)

    def serve(**kwargs):
        assert case.resolver.calls == []
        backend = kwargs["backend"]
        assert fixture._admission_wire(case, backend, None)["accepted"] is False
        assert case.resolver.calls == []
        response = fixture._admission_wire(case, backend, case.grant)
        assert response["accepted"] is True
        assert fixture.protected_fixture.Ed25519SignatureVerifier().verify(
            case.request.signer_public_key, case.request.signing_input, response["signature"])
        assert fixture._admission_wire(case, backend, case.grant)["accepted"] is False
        assert len(case.resolver.calls) == 2
        return CapturingBoundedService()(**kwargs)

    monkeypatch.setattr(bootstrap, "run_reddog_signer_socket_service_runtime_wiring", wiring)
    result = bootstrap.run_reddog_signer_socket_service_runtime_bootstrap(
        **options, serve_bounded=serve, runtime_dependencies_supplier=supply)
    assert result.accepted is True, result.rejection_reasons
    assert order == ["config", "isolation", "supplier", "wiring"]
    assert case.events == ["enter", "exit", "root_acquire", "enter", "resolve", "resolve",
                           "sign", "verify", "exit", "root_finish"]
