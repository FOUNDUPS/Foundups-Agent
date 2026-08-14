"""Adversarial tests for grant-authority WSP 71 permission admission."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_wsp71_permission_rehydration as permission_module,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_wsp71_permission_rehydration import (
    GET_SECRET,
    PERMISSION_FILENAME,
    SCHEMA_VERSION,
    SECRETS_READ,
    authorize_current_grant_authority_wsp71_use,
    permission_receipt_id,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_wsp71_permission_contract import (
    MAX_RECEIPT_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_builder import (
    build_grant_service_archive_from_git,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_json,
    raw_digest,
)
from modules.communication.moltbot_bridge.tests import (
    test_reddog_grant_authority_service_authenticated_manifest_binding as grant_fixture,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_CONFIG,
    GRANT_AUTHORITY_SERVICE_RUN_PACKET,
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    POLICY_SCHEMA_V7,
)


def test_valid_root_bound_permission_executes_one_callback_under_both_fences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    calls: list[str] = []

    result = _authorize(setup, action=lambda: calls.append(GET_SECRET) or "resolved")

    assert result == "resolved"
    assert calls == [GET_SECRET]
    assert setup["revocation_oracle"].authorize_calls == 1
    assert setup["e0"]["policy"]["schema_version"] == POLICY_SCHEMA_V7


def test_legacy_v6_authority_cannot_reach_wsp71_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(
        tmp_path, monkeypatch, git_provenance=False
    )
    calls: list[str] = []

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="grant_permission_e0_schema_invalid",
    ):
        _authorize(setup, action=lambda: calls.append("called"))
    assert calls == []


@pytest.mark.parametrize(
    "field",
    [
        "grant_authority_source_repo_root_digest",
        "grant_authority_source_commit_sha",
        "grant_authority_source_object_format",
        "grant_authority_source_policy_digest",
        "grant_authority_archive_source_descriptor_digest",
    ],
)
def test_signed_v7_provenance_substitution_rejects_before_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    policy = setup["e0"]["policy"]
    policy[field] = _different_valid_provenance_value(field, policy[field])
    grant_fixture._rebind_config_and_sign(
        setup["e0"], setup["e0"]["grant_private"]
    )
    calls: list[str] = []

    with pytest.raises((RuntimeArtifactManifestError, ValueError)):
        _authorize(setup, action=lambda: calls.append("called"))
    assert calls == []


def test_attacker_source_mapping_rehashed_and_resigned_rejects_before_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    authority = setup["harness"].authority_boundary.require(
        setup["harness"].authority
    )
    archive = build_grant_service_archive_from_git(
        repo_root=setup["harness"].repo_root,
        source_commit_sha=str(authority["authorized_base_sha"]),
        sources={
            "reddog_grant_authority_service.py": (
                "service/attacker_selected_service.py"
            )
        },
    )
    (setup["harness"].runtime_root / "grant_authority_service.pyz").write_bytes(
        archive
    )
    _rebuild_grant_artifacts(setup)
    calls: list[str] = []

    with pytest.raises(
        RuntimeArtifactManifestError,
        match="git_authority_mismatch",
    ):
        _authorize(setup, action=lambda: calls.append("called"))
    assert calls == []


def test_no_public_mint_consume_or_lease_capability_api_exists() -> None:
    source = inspect.getsource(permission_module)
    assert "mint_verified" not in source
    assert "consume_verified" not in source
    assert "lease_current_grant_authority_wsp71_permission" not in source


def test_attacker_rehashed_receipt_without_signed_binding_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    receipt["signer_agent_id"] = "signer:attacker"
    _rewrite_receipt(setup, receipt)

    with pytest.raises(RuntimeArtifactManifestError):
        _authorize(setup)


def test_grant_authority_self_rehash_without_root_generation_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    receipt["signer_agent_id"] = "signer:attacker"
    receipt["receipt_id"] = permission_receipt_id(receipt)
    raw = canonical_json(receipt).encode("ascii")
    policy = setup["e0"]["policy"]
    policy["grant_authority_permission_snapshot_digest"] = raw_digest(raw)
    policy["grant_authority_permission_snapshot_receipt_id"] = receipt["receipt_id"]
    grant_fixture._rebind_config_and_sign(
        setup["e0"], setup["e0"]["grant_private"]
    )
    _permission_path(setup).write_bytes(raw)

    with pytest.raises((ValueError, RuntimeArtifactManifestError), match="mismatch"):
        _authorize(setup)


def test_repo_write_permission_snapshot_cannot_substitute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    snapshot = PermissionSnapshot(
        evidence_digest="sha256:" + "a" * 64,
        expires_at=NOW + 60,
        can_write=True,
        can_admin=True,
        repo_full_name="FOUNDUPS/Foundups-Agent",
    )
    _permission_path(setup).write_text(
        canonical_json(snapshot.__dict__), encoding="ascii"
    )

    with pytest.raises(RuntimeArtifactManifestError, match="malformed"):
        _authorize(setup)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("signer_agent_id", "signer:attacker"),
        ("signer_profile_id", "attacker-profile"),
        ("signing_key_ref_hash", "sha256:" + "1" * 64),
        ("audit_mac_key_ref_hash", "sha256:" + "2" * 64),
        ("permission", "REPO_WRITE"),
        ("allowed_operations", ["write_repo"]),
        ("e0_generation", 999),
        ("e0_manifest_id", "sha256:" + "3" * 64),
    ],
)
def test_root_bound_but_wrong_scope_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    receipt[field] = value
    _authorize_receipt(setup, receipt)

    with pytest.raises(RuntimeArtifactManifestError):
        _authorize(setup)


def test_revoked_receipt_rejects_even_when_digest_is_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    receipt["revoked"] = True
    _authorize_receipt(setup, receipt)

    with pytest.raises(RuntimeArtifactManifestError, match="rejected"):
        _authorize(setup)


def test_durable_issuer_key_revocation_rejects_before_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    setup["revocation_oracle"].revoked = True

    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        _authorize(setup)


def test_revocation_during_action_rejects_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    setup["revocation_oracle"].revoke_during_action = True

    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        _authorize(setup)


def test_wrong_policy_oracle_rejects_before_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    setup["revocation_oracle"].binding = object()
    calls: list[str] = []

    with pytest.raises(RuntimeArtifactManifestError, match="oracle_mismatch"):
        _authorize(setup, action=lambda: calls.append("called"))
    assert calls == []


def test_expired_receipt_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)

    with pytest.raises(RuntimeArtifactManifestError, match="rejected"):
        _authorize(setup, now_epoch=setup["e0"]["policy"]["expires_at"])


def test_expiry_is_rechecked_by_the_atomic_use_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    setup["revocation_oracle"].now_epoch = receipt["expires_at"]
    with pytest.raises(RuntimeArtifactManifestError, match="rejected"):
        _authorize(setup, now_epoch=receipt["expires_at"])


def test_replaced_receipt_rejects_without_runtime_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    _permission_path(setup).write_bytes(b'{"schema_version":"attacker"}')

    with pytest.raises(RuntimeArtifactManifestError):
        _authorize(setup)
    assert not any(path.name.endswith(".sock") for path in tmp_path.rglob("*"))


@pytest.mark.parametrize("mutation", ["unknown", "missing", "duplicate", "trailing", "non_ascii"])
def test_noncanonical_or_malformed_wire_receipt_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    if mutation == "unknown":
        receipt["attacker"] = "field"
        raw = canonical_json(receipt).encode("ascii")
    elif mutation == "missing":
        receipt.pop("permission")
        raw = canonical_json(receipt).encode("ascii")
    elif mutation == "duplicate":
        encoded = canonical_json(receipt)
        raw = ('{"schema_version":"attacker",' + encoded[1:]).encode("ascii")
    elif mutation == "trailing":
        raw = canonical_json(receipt).encode("ascii") + b"\n"
    else:
        receipt["signer_profile_id"] = "non-ascii-\N{LATIN SMALL LETTER E WITH ACUTE}"
        raw = json.dumps(receipt, ensure_ascii=False).encode("utf-8")
    _permission_path(setup).write_bytes(raw)

    with pytest.raises((RuntimeArtifactManifestError, ValueError)):
        _authorize(setup)


def test_oversized_receipt_and_untrusted_oracle_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    _permission_path(setup).write_bytes(b" " * (MAX_RECEIPT_BYTES + 1))
    with pytest.raises(ValueError):
        _authorize(setup)
    setup, _ = _permission_setup(tmp_path / "second", monkeypatch)
    setup["revocation_oracle"] = object()
    with pytest.raises(RuntimeArtifactManifestError, match="oracle_mismatch"):
        _authorize(setup)


def test_canonical_receipt_prefix_with_oversized_tail_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, receipt = _permission_setup(tmp_path, monkeypatch)
    prefix = canonical_json(receipt).encode("ascii")
    tail = b" " * (MAX_RECEIPT_BYTES + 1 - len(prefix))
    _permission_path(setup).write_bytes(prefix + tail)

    with pytest.raises(RuntimeArtifactManifestError, match="oversized"):
        _authorize(setup)


def test_symlink_receipt_rejects_when_platform_allows_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, _ = _permission_setup(tmp_path, monkeypatch)
    target = _permission_path(setup)
    attacker = tmp_path / "attacker.json"
    attacker.write_text("{}", encoding="ascii")
    target.unlink()
    try:
        target.symlink_to(attacker)
    except OSError:
        pytest.skip("symlink creation unavailable")

    with pytest.raises(ValueError, match="link"):
        _authorize(setup)


def test_module_has_no_effect_or_secret_resolution_surface() -> None:
    tree = ast.parse(inspect.getsource(permission_module))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not imports.intersection({"socket", "subprocess", "shutil"})
    assert not calls.intersection({"get_secret", "resolve_secret", "bind", "listen", "Popen"})
    source = inspect.getsource(permission_module)
    assert "openclaw" not in source.lower()
    assert "hermes" not in source.lower()
    assert "op://" not in source


def test_permission_modules_follow_wsp62_bounds() -> None:
    root = Path("modules/communication/moltbot_bridge/src")
    for name in (
        "reddog_grant_authority_wsp71_permission_contract.py",
        "reddog_grant_authority_wsp71_permission_rehydration.py",
        "reddog_signer_owner_e0_selection_binding.py",
    ):
        source = (root / name).read_text(encoding="ascii")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 200
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50


def _permission_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    git_provenance: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    setup = grant_fixture._setup(
        tmp_path,
        monkeypatch,
        runtime_profile=(
            RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE
            if git_provenance
            else grant_fixture.RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE
        ),
    )
    receipt = _receipt(setup)
    _authorize_receipt(setup, receipt)
    with permission_module.lease_validated_owner_e0_current_admission(
        owner_config_path=setup["e0"]["owner_config_path"],
        repo_root=setup["e0"]["boundary"]._repo_root,
        policy=setup["e0"]["policy"],
    ) as admission:
        binding = admission.revocation_binding
    monkeypatch.setattr(
        permission_module,
        "RootAuthorizedSignerGrantRevocationOracle",
        _RevocationOracle,
    )
    setup["revocation_oracle"] = _RevocationOracle(
        binding, now_epoch=receipt["issued_at"]
    )
    return setup, receipt


def _receipt(setup: dict[str, Any]) -> dict[str, Any]:
    policy = setup["e0"]["policy"]
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "receipt_id": "pending",
        "owner_config_id": policy["owner_config_id"],
        "e0_manifest_id": policy["manifest_id"],
        "e0_artifact_generation_digest": policy["artifact_generation_digest"],
        "e0_generation": policy["generation"],
        "e0_generation_revision": policy["generation_revision"],
        "issuer_principal_id": policy["grant_authority_principal_id"],
        "issuer_principal_provider": policy["grant_authority_principal_provider"],
        "issuer_public_key": policy["grant_authority_public_key"],
        "issuer_key_epoch": policy["grant_authority_key_epoch"],
        "signer_agent_id": policy["grant_authority_signer_agent_id"],
        "signer_profile_id": policy["grant_authority_signer_profile_id"],
        "signing_key_ref_hash": policy["grant_authority_signing_key_ref_hash"],
        "audit_mac_key_ref_hash": policy["grant_authority_audit_mac_key_ref_hash"],
        "permission": SECRETS_READ,
        "allowed_operations": [GET_SECRET],
        "issued_at": policy["issued_at"],
        "expires_at": policy["expires_at"],
        "revoked": False,
    }
    value["receipt_id"] = permission_receipt_id(value)
    return value


def _authorize_receipt(setup: dict[str, Any], receipt: dict[str, Any]) -> None:
    receipt["receipt_id"] = permission_receipt_id(receipt)
    raw = canonical_json(receipt).encode("ascii")
    policy = setup["e0"]["policy"]
    policy["grant_authority_permission_snapshot_digest"] = raw_digest(raw)
    policy["grant_authority_permission_snapshot_receipt_id"] = receipt["receipt_id"]
    _permission_path(setup).write_bytes(raw)
    _rebuild_grant_artifacts(setup)


def _rewrite_receipt(setup: dict[str, Any], receipt: dict[str, Any]) -> None:
    receipt["receipt_id"] = permission_receipt_id(receipt)
    _permission_path(setup).write_bytes(canonical_json(receipt).encode("ascii"))


def _rebuild_grant_artifacts(setup: dict[str, Any]) -> None:
    policy = setup["e0"]["policy"]
    root = setup["harness"].runtime_root
    config_path = root / GRANT_AUTHORITY_SERVICE_CONFIG
    config = json.loads(config_path.read_text(encoding="ascii"))
    archive_path = root / "grant_authority_service.pyz"
    archive_raw = archive_path.read_bytes()
    archive_digest = raw_digest(archive_raw)
    setup["archive_digest"] = archive_digest
    config["archive_digest"] = archive_digest
    config["permission_snapshot_digest"] = policy[
        "grant_authority_permission_snapshot_digest"
    ]
    config["permission_snapshot_receipt_id"] = policy[
        "grant_authority_permission_snapshot_receipt_id"
    ]
    config_raw = canonical_json(config).encode("ascii")
    config_path.write_bytes(config_raw)
    packet = grant_fixture._run_packet(raw_digest(config_raw), archive_digest)
    packet_path = root / GRANT_AUTHORITY_SERVICE_RUN_PACKET
    packet_raw = canonical_json(packet).encode("ascii")
    packet_path.write_bytes(packet_raw)
    manifest = setup["manifest"]
    bodies = {
        GRANT_AUTHORITY_SERVICE_CONFIG: config_raw,
        GRANT_AUTHORITY_SERVICE_RUN_PACKET: packet_raw,
        "grant_authority_service.pyz": archive_raw,
    }
    for descriptor in manifest["artifacts"]:
        body = bodies.get(descriptor["filename"])
        if body is not None:
            descriptor["byte_count"] = len(body)
            descriptor["content_digest"] = raw_digest(body)
    manifest["artifact_generation_digest"] = grant_fixture.digest(
        manifest["artifacts"]
    )
    grant_fixture._bind_target_signer(setup["e0"], manifest)
    grant_fixture._rebind_config_and_sign(
        setup["e0"], setup["e0"]["grant_private"]
    )
    grant_fixture._align_manifest_authority(setup["e0"], setup["harness"], manifest)
    grant_fixture._bind_policy(setup["e0"], manifest)


def _different_valid_provenance_value(field: str, current: object) -> str:
    if field == "grant_authority_source_object_format":
        return "sha256" if current == "sha1" else "sha1"
    if field == "grant_authority_source_commit_sha":
        return "f" * len(str(current))
    return "sha256:" + "f" * 64


def _permission_path(setup: dict[str, Any]) -> Path:
    return setup["harness"].runtime_root / PERMISSION_FILENAME


def _authorize(
    setup: dict[str, Any], *, now_epoch: int | None = None,
    action: Any = None,
) -> Any:
    checked_at = (
        setup["e0"]["policy"]["issued_at"]
        if now_epoch is None
        else now_epoch
    )
    callback = action if callable(action) else (lambda: None)
    return authorize_current_grant_authority_wsp71_use(
        owner_config_path=setup["e0"]["owner_config_path"],
        repo_root=setup["e0"]["boundary"]._repo_root,
        owner_policy=setup["e0"]["policy"],
        now_epoch=checked_at,
        revocation_oracle=setup["revocation_oracle"],
        action=callback,
    )


class _RevocationOracle:
    def __init__(self, binding: object, *, now_epoch: int) -> None:
        self.binding = binding
        self.now_epoch = now_epoch
        self.revoked = False
        self.revoke_during_action = False
        self.authorize_calls = 0

    def authorize_key_epoch_use(
        self, *, key_epoch: str, at_epoch: int, expires_at: int,
        action: Any,
    ) -> Any:
        assert key_epoch
        self.authorize_calls += 1
        if at_epoch != self.now_epoch or at_epoch >= expires_at or self.revoked:
            raise RuntimeError("signer_key_epoch_use_rejected")
        result = action()
        if self.revoke_during_action:
            self.revoked = True
        if self.revoked or self.now_epoch >= expires_at:
            raise RuntimeError("signer_key_epoch_use_rejected")
        return result
