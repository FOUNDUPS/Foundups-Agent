"""Security tests for signer-owned production WSP 71 resolver supply."""

from __future__ import annotations

import ast
import base64
import copy
import os
import stat
import time
from dataclasses import asdict
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_signer_system_service_wsp71_resolver_supply as target,
)
from modules.infrastructure.secrets_mcp.src.op_cli_secret_resolver import (
    OpCliCommandResult,
)
from modules.infrastructure.secrets_mcp.src import systemd_credential_secret_resolver as credential_os
from modules.communication.moltbot_bridge.tests import (
    test_reddog_signer_owner_controlled_e0_admission as e0_fixture,
)
from modules.communication.moltbot_bridge.tests.root_revocation_service_topology_fixture import (
    bind_selection_loader,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _descriptor,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    descriptor_id_for,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    revocation_authority_binding_from_policy,
)


MODULE_PATH = Path(target.__file__).resolve()
OWNER_ID = "sha256:" + "a" * 64


def _systemd_binding():
    now = time.time()
    return target.SystemdCredentialBinding(
        credential_directory="/run/credentials/reddog-signer.service",
        expected_uid=1001, expected_gid=1001, expected_requester="signer:reddog",
        issued_at=now - 1, expires_at=now + 30,
        credential_ids=frozenset({"work-signing", "work-audit"}),
    )


def test_explicit_systemd_supply_is_lazy_and_does_not_select_op(monkeypatch):
    def forbidden(*args):
        raise AssertionError("op backend must not be inspected for systemd selection")
    monkeypatch.setattr(target, "_require_root_owned_executable", forbidden)
    binding = _systemd_binding()
    factory = target.build_system_service_wsp71_resolver_factory(
        owner_config_id=OWNER_ID, credential_binding=binding,
    )
    assert isinstance(factory(), target.SystemdCredentialSecretResolver)


@pytest.mark.parametrize("owner,binding,runner", [
    ("invalid", None, None),
    (OWNER_ID, object(), None),
    (OWNER_ID, "valid", object()),
])
def test_systemd_supply_rejects_invalid_owner_binding_or_mixed_backend(owner, binding, runner):
    selected = _systemd_binding() if binding == "valid" or binding is None else binding
    with pytest.raises(ValueError):
        target.SystemServiceWsp71ResolverFactory(
            owner, runner=runner, credential_binding=selected,
        )()


class _Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv, *, timeout_s, max_stdout_chars):
        self.calls.append(tuple(argv))
        return OpCliCommandResult(returncode=0, stdout="secret-in-memory")


def _trusted_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"#!/bin/sh\n")
    os.chmod(path, 0o755)


def test_factory_resolves_only_after_root_owned_executable_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "usr" / "bin" / "op"
    _trusted_executable(executable)
    runner = _Runner()
    monkeypatch.setattr(target, "SYSTEM_SERVICE_OP_EXECUTABLE", executable)
    monkeypatch.setattr(target.sys, "platform", "linux")
    monkeypatch.setattr(target, "_require_root_owned_executable", lambda path: None)

    factory = target.SystemServiceWsp71ResolverFactory(OWNER_ID, runner=runner)
    assert runner.calls == []

    result = factory().resolve("op://Foundups/reddog/private", "signer:reddog")

    assert result.success is True
    assert result.get_value() == "secret-in-memory"
    assert runner.calls == [
        (str(executable), "read", "op://Foundups/reddog/private", "--no-newline")
    ]
    assert "secret-in-memory" not in str(result.to_audit_dict())


def test_factory_rejects_invalid_owner_before_secret_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _Runner()
    executable_checks: list[Path] = []
    monkeypatch.setattr(
        target,
        "_require_root_owned_executable",
        lambda path: executable_checks.append(path),
    )

    with pytest.raises(ValueError, match="owner_config_id_invalid"):
        target.SystemServiceWsp71ResolverFactory("sha256-looking", runner=runner)()

    assert runner.calls == []
    assert executable_checks == []


def test_executable_gate_rejects_missing_symlink_and_writable_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(target.sys, "platform", "linux")
    missing = tmp_path / "missing" / "op"
    with pytest.raises(ValueError, match="executable_unavailable"):
        target._require_root_owned_executable(missing)

    executable = tmp_path / "op"
    _trusted_executable(executable)
    link = tmp_path / "op-link"
    try:
        link.symlink_to(executable)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="executable_invalid"):
        target._require_root_owned_executable(link)

    os.chmod(executable, stat.S_IRWXU | stat.S_IWGRP | stat.S_IXGRP)
    with pytest.raises(ValueError, match="executable_untrusted"):
        target._require_root_owned_executable(executable)


@pytest.mark.skipif(not target.sys.platform.startswith("linux"), reason="Linux only")
def test_executable_gate_accepts_root_owned_linux_binary() -> None:
    target._require_root_owned_executable(Path("/usr/bin/env"))


def test_supply_module_has_no_secret_persistence_or_shell_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_calls = {"open", "eval", "exec", "compile", "write_text", "write_bytes"}
    banned_imports = {"subprocess", "socket", "requests", "httpx"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {alias.name.split(".", 1)[0] for alias in node.names} & banned_imports
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".", 1)[0] not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_calls


def _root_descriptor(tmp_path, values, control_public, now):
    policy = values["policy"]
    descriptor, _, _ = _descriptor(
        tmp_path / "descriptor", signer_key=values["target_private"],
        descriptor_overrides={
            "issued_at": now - 2, "expires_at": now + 120,
            "signer_manifest_id": policy["manifest_id"],
            "signer_artifact_generation_digest": policy["artifact_generation_digest"],
            "signer_config_digest": policy["config_digest"],
            "signer_key_epoch": policy["target_signer_key_epoch"],
        },
    )
    descriptor.update(schema_version=target.DESCRIPTOR_SCHEMA_V2,
        root_control_authentication={"purpose": target.ROOT_CONTROL_PURPOSE,
                                    "public_key": control_public, "key_epoch": "control-1"})
    descriptor["descriptor_id"] = descriptor_id_for(descriptor)
    return descriptor


def _custody_owner(values, binding, descriptor, now):
    metadata = asdict(binding)
    metadata["credential_ids"] = sorted(binding.credential_ids)
    permissions = {}
    for purpose, identifier, public, epoch in (
        (target.ROOT_LOAD_PURPOSE, "work", descriptor["signer_public_key"], descriptor["signer_key_epoch"]),
        (target.ROOT_CONTROL_PURPOSE, "control", descriptor["root_control_authentication"]["public_key"], "control-1"),
    ):
        permissions[purpose] = {"operation": "SECRETS_READ", "reference": "systemd-creds://" + identifier,
            "requester_id": binding.expected_requester, "purpose": purpose, "public_key": public,
            "key_epoch": epoch, "issued_at": now - 1, "expires_at": now + 30}
    return {"config_id": values["policy"]["owner_config_id"],
        "verified_outcome_authority": {"descriptor": descriptor, "signer_uid": 1001,
            "signer_gid": 1001, "signer_principal_id": binding.expected_requester},
        "startup_custody": {"credential_binding": metadata, "root_request_permissions": permissions}}


def _root_supply_fixture(tmp_path, monkeypatch):
    """Real E0 validators/crypto; synthetic selection, owner-file and OS custody boundaries."""
    from cryptography.hazmat.primitives import serialization
    values = e0_fixture._fixture(tmp_path)
    bind_selection_loader(monkeypatch)
    control_private, control_public = e0_fixture._keypair()
    now = int(time.time())
    descriptor = _root_descriptor(tmp_path, values, control_public, now)
    binding = target.SystemdCredentialBinding(
        credential_directory="/run/credentials/reddog-signer.service",
        expected_uid=1001, expected_gid=1001, expected_requester="signer:reddog",
        issued_at=now - 2, expires_at=now + 60, credential_ids=frozenset({"work", "control"}),
    )
    owner = _custody_owner(values, binding, descriptor, now)
    secrets = {name: "ed25519-private-raw-b64-v1:" + base64.b64encode(key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption(),
    )).decode("ascii") for name, key in (("work", values["target_private"]), ("control", control_private))}
    calls = []
    def read_credential(selected, identifier):
        assert selected == binding
        calls.append(identifier)
        return secrets[identifier]
    monkeypatch.setattr(target, "_load_owner_config", lambda *args, **kwargs: copy.deepcopy(owner))
    monkeypatch.setattr(credential_os, "_identity_matches", lambda selected: selected == binding)
    monkeypatch.setattr(credential_os, "_read_credential", read_credential)
    return {**values, "descriptor": descriptor, "custody": binding, "owner": owner,
            "calls": calls, "secrets": secrets, "now": now}


def _root_signer(values, purpose):
    return target.build_system_service_root_request_signer(
        owner_config_path=values["owner_config_path"],
        repo_root=Path(values["selection"]["repo_root"]), policy=values["policy"],
        descriptor=values["descriptor"], purpose=purpose, credential_binding=values["custody"],
    )


def _root_input(values, operation):
    policy = values["policy"]
    binding = revocation_authority_binding_from_policy(policy,
        repo_root=Path(values["selection"]["repo_root"]),
        signer_runtime_root=Path(values["config"]["signer_runtime_root"]))
    payload = {"operation": operation, "request_nonce": "a" * 64,
        "descriptor_id": values["descriptor"]["descriptor_id"], "owner_config_id": policy["owner_config_id"],
        "policy_id": policy["policy_id"], "binding_digest": binding.anchor_binding_digest(),
        "policy": policy, "issued_at": int(time.time())}
    if operation in {target.load_wire.OP_LOAD, target.load_wire.OP_ADVANCE}:
        wire = target.load_wire
        payload["snapshot_id"] = None if operation == wire.OP_LOAD else e0_fixture.DIGEST_B
    else:
        wire = target.control_wire
        payload.update(grant_id=e0_fixture.DIGEST_B, key_epoch=policy["target_signer_key_epoch"],
            signing_request_digest=e0_fixture.DIGEST_C, use_nonce="b" * 64,
            grant_expires_at=values["now"] + 20, acquired_sequence=None, acquired_revision=None)
        if operation == wire.OP_FINISH:
            payload.update(acquired_sequence=1, acquired_revision="c" * 64)
        payload["protected_use_id"] = wire.protected_use_id_for(payload)
    return wire.SIGNING_PREFIX + target.canonical_bytes(payload).decode("ascii")


@pytest.mark.parametrize("purpose,operation,credential", [
    (target.ROOT_LOAD_PURPOSE, target.load_wire.OP_LOAD, "work"),
    (target.ROOT_CONTROL_PURPOSE, target.control_wire.OP_ACQUIRE, "control"),
    (target.ROOT_CONTROL_PURPOSE, target.control_wire.OP_FINISH, "control"),
])
def test_root_request_signing_authenticates_each_use_and_resolves_only_one_key(
    tmp_path, monkeypatch, purpose, operation, credential,
):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    signer = _root_signer(values, purpose)
    assert values["calls"] == []
    message = _root_input(values, operation)
    signature = signer(message)
    public = values["owner"]["startup_custody"]["root_request_permissions"][purpose]["public_key"]
    assert target.Ed25519SignatureVerifier().verify(public, message, signature) is True
    assert values["calls"] == [credential]
    values["policy"]["signature"] = "ed25519-sig-v1:" + "A" * 86
    invalid = _root_signer(values, purpose)
    with pytest.raises(ValueError, match="signature_invalid"):
        invalid(_root_input(values, operation))
    assert values["calls"] == [credential]


@pytest.mark.parametrize("change", [
    "operation", "reference", "requester", "purpose", "public", "epoch", "expired",
    "extra", "owner", "binding", "descriptor", "generation",
])
def test_root_request_rejects_invalid_permission_or_current_authority_before_read(tmp_path, monkeypatch, change):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    signer = _root_signer(values, target.ROOT_LOAD_PURPOSE)
    message = _root_input(values, target.load_wire.OP_LOAD)
    owner = values["owner"]
    permission = owner["startup_custody"]["root_request_permissions"][target.ROOT_LOAD_PURPOSE]
    if change == "operation": permission["operation"] = "read"
    elif change == "reference": permission["reference"] = "op://foreign/key"
    elif change == "requester": permission["requester_id"] = "other"
    elif change == "purpose": permission["purpose"] = target.ROOT_CONTROL_PURPOSE
    elif change == "public": permission["public_key"] = values["grant_public"]
    elif change == "epoch": permission["key_epoch"] = "other"
    elif change == "expired": permission["expires_at"] = values["now"] - 1
    elif change == "extra": permission["allow"] = True
    elif change == "owner": owner["config_id"] = e0_fixture.DIGEST_B
    elif change == "binding": owner["startup_custody"]["credential_binding"]["expected_uid"] = 1002
    elif change == "descriptor": owner["verified_outcome_authority"]["descriptor"]["descriptor_id"] = e0_fixture.DIGEST_B
    else: e0_fixture._CURRENT_SELECTION["generation"] += 1
    with pytest.raises(ValueError):
        signer(message)
    assert values["calls"] == []


@pytest.mark.parametrize("case", ["load_by_control", "control_by_work", "advance", "whitespace", "duplicate", "extra", "policy", "binding"])
def test_root_request_rejects_cross_purpose_or_noncanonical_input_before_read(tmp_path, monkeypatch, case):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    purpose = target.ROOT_CONTROL_PURPOSE if case == "load_by_control" else target.ROOT_LOAD_PURPOSE
    signer = _root_signer(values, purpose)
    operation = target.control_wire.OP_ACQUIRE if case == "control_by_work" else target.load_wire.OP_LOAD
    if case == "advance": operation = target.load_wire.OP_ADVANCE
    message = _root_input(values, operation)
    if case == "whitespace": message += " "
    elif case == "duplicate": message = message.replace('{"binding_digest":', '{"issued_at":1,"binding_digest":', 1)
    elif case == "extra": message = message.replace('{"binding_digest":', '{"extra":true,"binding_digest":', 1)
    elif case == "policy": message = message.replace(values["policy"]["policy_id"], e0_fixture.DIGEST_B)
    elif case == "binding": message = message.replace('"binding_digest":"sha256:', '"binding_digest":"sha256:f', 1)
    with pytest.raises(ValueError):
        signer(message)
    assert values["calls"] == []


def test_root_request_rechecks_current_selection_on_later_use(tmp_path, monkeypatch):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    signer = _root_signer(values, target.ROOT_LOAD_PURPOSE)
    message = _root_input(values, target.load_wire.OP_LOAD)
    signer(message)
    e0_fixture._CURRENT_SELECTION["generation"] += 1
    with pytest.raises(ValueError): signer(message)
    assert values["calls"] == ["work"]


@pytest.mark.parametrize("phase", ["before_sign", "after_sign", "monotonic"])
def test_root_request_expiry_prevents_signature_delivery(tmp_path, monkeypatch, phase):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    signer = _root_signer(values, target.ROOT_LOAD_PURPOSE)
    message = _root_input(values, target.load_wire.OP_LOAD)
    original = target._decode_ed25519_private_key
    original_sign = target._sign_root_proof
    if phase == "before_sign":
        def decode(secret):
            key = original(secret)
            monkeypatch.setattr(target.time, "time", lambda: values["now"] + 31)
            return key
        monkeypatch.setattr(target, "_decode_ed25519_private_key", decode)
    elif phase == "after_sign":
        def sign(*args):
            result = original_sign(*args)
            monkeypatch.setattr(target.time, "time", lambda: values["now"] + 31)
            return result
        monkeypatch.setattr(target, "_sign_root_proof", sign)
    else:
        monkeypatch.setattr(target.time, "monotonic", lambda: signer.mono_start + 61)
    with pytest.raises(ValueError, match="expired"):
        signer(message)
    assert values["calls"] == ([] if phase == "monotonic" else ["work"])


def test_root_request_wrong_private_key_is_not_used_for_signing(tmp_path, monkeypatch):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    values["secrets"]["work"] = values["secrets"]["control"]
    signer = _root_signer(values, target.ROOT_LOAD_PURPOSE)
    with pytest.raises(ValueError, match="key_mismatch"):
        signer(_root_input(values, target.load_wire.OP_LOAD))
    assert values["calls"] == ["work"]


def test_root_request_rejects_equal_but_nonidentical_policy_before_read(tmp_path, monkeypatch):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    signer = _root_signer(values, target.ROOT_LOAD_PURPOSE)
    message = _root_input(values, target.load_wire.OP_LOAD)
    prefix = target.load_wire.SIGNING_PREFIX
    payload = target.decode_message(message[len(prefix):].encode("ascii"))
    payload["policy"]["generation"] = float(payload["policy"]["generation"])
    assert payload["policy"] == values["policy"]
    assert target.canonical_bytes(payload["policy"]) != target.canonical_bytes(values["policy"])
    altered = prefix + target.canonical_bytes(payload).decode("ascii")
    rejected = False
    try:
        signer(altered)
    except ValueError:
        rejected = True
    assert values["calls"] == []
    assert rejected is True


def test_root_request_final_owner_reread_cannot_outlive_permission(tmp_path, monkeypatch):
    values = _root_supply_fixture(tmp_path, monkeypatch)
    permission = values["owner"]["startup_custody"]["root_request_permissions"][target.ROOT_LOAD_PURPOSE]
    permission["expires_at"] = values["now"] + 5
    signer = _root_signer(values, target.ROOT_LOAD_PURPOSE)
    message = _root_input(values, target.load_wire.OP_LOAD)
    original = target._load_owner_config
    reads = []

    def delayed_owner_read(*args, **kwargs):
        owner = original(*args, **kwargs)
        reads.append(True)
        if len(reads) == 2:
            monkeypatch.setattr(target.time, "time", lambda: values["now"] + 6)
        return owner

    monkeypatch.setattr(target, "_load_owner_config", delayed_owner_read)
    delivered = None
    rejected = False
    try:
        delivered = signer(message)
    except ValueError:
        rejected = True
    assert reads == [True, True]
    assert values["calls"] == ["work"]
    delivery_withheld = delivered is None
    assert delivery_withheld, "signature delivered after permission expiry"
    assert rejected is True
