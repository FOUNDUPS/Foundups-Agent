"""Activation-window race tests for signer runtime artifact generations."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_runtime_artifact_activation_lease as lease_module,
    reddog_signer_system_service_manifest_selection_loader as owner_loader,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_activation_lease import (
    runtime_artifact_activation_lease,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_atomic_provisioning import (
    _context,
    _provision,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
)


@pytest.fixture(autouse=True)
def _fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    monkeypatch.setattr(target, "_trusted_now", lambda: NOW)


@pytest.mark.skipif(os.name != "nt", reason="Windows lease required")
def test_direct_write_during_anchor_activation_is_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    original = anchor.activate

    def mutate_then_activate(*args, **kwargs):
        config = harness.runtime_root / "signer_service_config.json"
        config.write_text("{}", encoding="utf-8")
        return original(*args, **kwargs)

    monkeypatch.setattr(anchor, "activate", mutate_then_activate)
    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.inactive_artifacts_preserved is True


@pytest.mark.skipif(os.name != "nt", reason="Windows lease required")
def test_preopened_writer_cannot_leave_failed_generation_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    config = harness.runtime_root / "signer_service_config.json"
    descriptor = os.open(config, os.O_WRONLY)
    original = anchor.activate

    def mutate_then_activate(*args, **kwargs):
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, b"{}")
        os.ftruncate(descriptor, 2)
        os.fsync(descriptor)
        return original(*args, **kwargs)

    monkeypatch.setattr(anchor, "activate", mutate_then_activate)
    try:
        result = _provision(context)
    finally:
        os.close(descriptor)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.inactive_artifacts_preserved is True


@pytest.mark.skipif(os.name != "nt", reason="Windows lease required")
def test_path_replacement_cannot_leave_failed_generation_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness, anchor, context = _context(tmp_path)
    config = harness.runtime_root / "signer_service_config.json"
    displaced = harness.runtime_root / "signer_service_config.displaced"
    original = anchor.activate

    def replace_then_activate(*args, **kwargs):
        config.replace(displaced)
        config.write_text("{}", encoding="utf-8")
        return original(*args, **kwargs)

    monkeypatch.setattr(anchor, "activate", replace_then_activate)
    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None
    assert result.inactive_artifacts_preserved is True


@pytest.mark.skipif(os.name == "nt", reason="POSIX fail-closed contract")
def test_posix_activation_requires_external_owner(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "artifact.json"
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="external_owner_required"):
        with runtime_artifact_activation_lease(
            (target,),
            repo_root=tmp_path / "repo",
            allowed_root=runtime,
        ):
            raise AssertionError("POSIX activation lease entered")


# These Linux contract cases use explicit OS seams on every CI platform.
# They do not substitute for native filesystem/credential qualification.
@pytest.mark.parametrize("kind", [
    "qualified", "root", "nnp0", "nnp_missing", "CapInh", "CapPrm",
    "CapEff", "CapAmb", "bad_cap",
])
def test_linux_process_qualification(monkeypatch, kind):
    fields = dict(NoNewPrivs="1", CapInh="0", CapPrm="0", CapEff="0", CapAmb="0")
    uid = 0 if kind == "root" else 999
    if kind == "nnp0":
        fields["NoNewPrivs"] = "0"
    elif kind == "nnp_missing":
        del fields["NoNewPrivs"]
    elif kind == "bad_cap":
        fields["CapEff"] = "invalid"
    elif kind in fields:
        fields[kind] = "80"
    text = "\n".join(f"{name}:\t{value}" for name, value in fields.items())
    monkeypatch.setattr(lease_module, "Path", lambda _: SimpleNamespace(
        read_text=lambda **kwargs: text,
    ))
    monkeypatch.setattr(lease_module, "os", SimpleNamespace(geteuid=lambda: uid))
    if kind == "qualified":
        lease_module._linux_unprivileged_activation_process()
    else:
        with pytest.raises((RuntimeError, ValueError)):
            lease_module._linux_unprivileged_activation_process()


@pytest.mark.parametrize("kind", [
    "qualified", "uid", "group_write", "other_write", "hardlink", "directory",
    "replaced", "mutable",
])
def test_linux_inode_qualification(monkeypatch, kind):
    fields = dict(st_mode=stat.S_IFREG | 0o444, st_uid=0, st_nlink=1, st_dev=1, st_ino=2)
    current = SimpleNamespace(st_dev=1, st_ino=2)
    if kind == "uid":
        fields["st_uid"] = 999
    elif kind == "group_write":
        fields["st_mode"] |= 0o020
    elif kind == "other_write":
        fields["st_mode"] |= 0o002
    elif kind == "hardlink":
        fields["st_nlink"] = 2
    elif kind == "directory":
        fields["st_mode"] = stat.S_IFDIR | 0o555
    elif kind == "replaced":
        current.st_ino = 3
    target = SimpleNamespace(parent=Path("/root-controlled"), lstat=lambda: current)
    monkeypatch.setattr(lease_module, "os", SimpleNamespace(
        fstat=lambda _: SimpleNamespace(**fields),
    ))
    monkeypatch.setattr(owner_loader, "_require_secure_ancestry", lambda _: None)

    def ioctl(fd, request, flags, mutate):
        flags[0] = 0 if kind == "mutable" else 0x10

    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(ioctl=ioctl))
    if kind == "qualified":
        lease_module._require_linux_immutable_file(target, 12)
    else:
        with pytest.raises(RuntimeError, match="external_owner_required"):
            lease_module._require_linux_immutable_file(target, 12)


@pytest.mark.parametrize("failure", ["open_second", "verify_second", "body", "postcheck"])
def test_linux_lease_closes_acquired_descriptors_on_failure(monkeypatch, failure):
    opened, closed, checks = [], [], []

    def opening(path, flags):
        if failure == "open_second" and opened:
            raise OSError("injected-open-failure")
        descriptor = 10 + len(opened)
        opened.append(descriptor)
        return descriptor

    def checking(path, descriptor):
        checks.append(descriptor)
        if failure == "verify_second" and len(checks) == 2:
            raise RuntimeError("injected-check-failure")
        if failure == "postcheck" and len(checks) == 3:
            raise RuntimeError("injected-postcheck-failure")

    fake = SimpleNamespace(open=opening, close=closed.append, O_RDONLY=0,
                           O_NOFOLLOW=0x20000, O_CLOEXEC=0x80000, O_NONBLOCK=0x800)
    monkeypatch.setattr(lease_module, "os", fake)
    monkeypatch.setattr(lease_module, "_linux_unprivileged_activation_process", lambda: None)
    monkeypatch.setattr(lease_module, "_require_linux_immutable_file", checking)
    monkeypatch.setattr(owner_loader, "_require_secure_ancestry", lambda _: None)
    with pytest.raises((OSError, RuntimeError)):
        with lease_module._linux_immutable_activation_lease((Path("first"), Path("second"))):
            if failure == "body":
                raise RuntimeError("injected-body-failure")
    assert closed == list(reversed(opened))


def test_linux_untrusted_ancestry_rejected_before_open(monkeypatch):
    """An unqualified mutable target must not block before the owner check."""
    def ancestry(_):
        raise ValueError("untrusted-ancestry")

    monkeypatch.setattr(owner_loader, "_require_secure_ancestry", ancestry)
    monkeypatch.setattr(lease_module, "_linux_unprivileged_activation_process", lambda: None)
    monkeypatch.setattr(lease_module, "os", SimpleNamespace(
        open=lambda *args: pytest.fail("target opened before ancestry qualification"),
        O_RDONLY=0, O_NOFOLLOW=0x20000, O_CLOEXEC=0x80000, O_NONBLOCK=0x800,
    ))
    with pytest.raises(ValueError, match="untrusted-ancestry"):
        with lease_module._linux_immutable_activation_lease((Path("artifact"),)):
            pytest.fail("unqualified ancestry admitted")


def test_linux_fifo_swap_does_not_block_before_inode_rejection(monkeypatch):
    """Model a FIFO substituted after path qualification without hanging CI."""
    opened, closed = [], []

    def opening(path, flags):
        if not flags & 0x800:
            pytest.fail("FIFO open could block without O_NONBLOCK")
        opened.append(12)
        return 12

    def inode_check(path, descriptor):
        raise RuntimeError("runtime_artifact_activation_lease_external_owner_required")

    monkeypatch.setattr(owner_loader, "_require_secure_ancestry", lambda _: None)
    monkeypatch.setattr(lease_module, "_linux_unprivileged_activation_process", lambda: None)
    monkeypatch.setattr(lease_module, "_require_linux_immutable_file", inode_check)
    monkeypatch.setattr(lease_module, "os", SimpleNamespace(
        open=opening, close=closed.append, O_RDONLY=0,
        O_NOFOLLOW=0x20000, O_CLOEXEC=0x80000, O_NONBLOCK=0x800,
    ))
    with pytest.raises(RuntimeError, match="external_owner_required"):
        with lease_module._linux_immutable_activation_lease((Path("artifact"),)):
            pytest.fail("FIFO admitted")
    assert opened == closed == [12]
