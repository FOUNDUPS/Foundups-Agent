"""Real disposable file digests; process and RootDirectory observations synthetic."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import reddog_grant_authority_installed_runtime_guard as guard
from modules.communication.moltbot_bridge.tests.test_reddog_grant_installed_source_contract import _descriptor


class _MountedPath:
    """Test-only path projection; production exposes no alternate-root parameter."""
    root = None

    def __init__(self, path):
        text = str(path)
        prefix = str(self.root)
        self.virtual = PurePosixPath("/" + text[len(prefix):].lstrip("/")
                                    if text == prefix or text.startswith(prefix + "/") else text)

    def __truediv__(self, other):
        return type(self)(self.virtual / other)

    def __fspath__(self):
        return str(self.root / str(self.virtual).lstrip("/"))

    def __str__(self):
        return self.__fspath__()

    def lstat(self):
        return os.lstat(self)

    def relative_to(self, other):
        return self.virtual.relative_to(other)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    if sys.platform != "linux" or os.getuid() != 0:
        pytest.skip("Disposable root-owned filesystem exercise requires Linux root")
    descriptor = _descriptor()
    for name in descriptor["directories"]:
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    for row in descriptor["files"]:
        path = tmp_path / row["path"]
        path.write_bytes(b"fixture" if row["bytes"] else b"")
        path.chmod(row["mode"])
    monkeypatch.setattr(_MountedPath, "root", tmp_path)
    monkeypatch.setattr(guard, "Path", _MountedPath)
    fake_sys = SimpleNamespace(platform="linux", version_info=(3, 12, 0),
        executable="/usr/bin/python3.12", orig_argv=descriptor["python_launch"] + ["-c", "fixture"],
        path=descriptor["explicit_sys_path"][:], modules={}, flags=SimpleNamespace(
            isolated=1, no_site=1, ignore_environment=1, dont_write_bytecode=1))
    monkeypatch.setattr(guard, "sys", fake_sys)
    monkeypatch.setattr(guard, "os", SimpleNamespace(environ={"CREDENTIALS_DIRECTORY": "unread"},
        readlink=lambda name: "/usr/bin/python3.12", walk=os.walk, major=os.major, minor=os.minor,
        stat=lambda name: (tmp_path / "usr/bin/python3.12").stat()))
    status = "\n".join(key + ":\t00000000" for key in
                       ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"))
    proc = {"status": status + "\nNoNewPrivs:\t1\nSeccomp:\t2\n",
        "mountinfo": "1 2 8:1 /var/lib/foundups/isolated-issuer / ro - ext4 /dev/disk rw\n",
        "maps": _map_line(tmp_path, "usr/bin/python3.12")}
    monkeypatch.setattr(guard, "_proc", lambda name: proc[name])
    return SimpleNamespace(descriptor=descriptor, root=tmp_path, proc=proc, system=fake_sys)


def _map_line(root, relative):
    metadata = (root / relative).stat()
    return (f"1000-2000 r-xp 00000000 {os.major(metadata.st_dev):x}:{os.minor(metadata.st_dev):x} "
            f"{metadata.st_ino} /{relative}\n")


def test_disposable_inventory_and_repeated_use(runtime):
    runtime.system.modules["source"] = SimpleNamespace(__file__="/opt/grant-source/modules/__init__.py")
    before = copy.deepcopy(runtime.descriptor)
    assert guard.verify_installed_grant_runtime(runtime.descriptor) is None
    assert guard.verify_installed_grant_runtime(runtime.descriptor) is None
    assert runtime.descriptor == before


@pytest.mark.parametrize("relative", ["usr/lib/python3.12/abc.py", "opt/grant-source/modules/__init__.py"])
@pytest.mark.parametrize("change", ["tamper", "remove", "mode", "symlink", "hardlink"])
def test_file_drift(runtime, relative, change):
    target = runtime.root / relative
    if change == "tamper":
        target.write_bytes(b"changed")
    elif change == "remove":
        target.unlink()
    elif change == "mode":
        target.chmod(0o644)
    elif change == "symlink":
        target.unlink()
        target.symlink_to(runtime.root / "usr/bin/python3.12")
    else:
        os.link(target, runtime.root / "outside-static-link")
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


@pytest.mark.parametrize("change", ["extra_file", "extra_directory", "directory_mode", "broken_top_link"])
def test_membership_drift(runtime, change):
    if change == "extra_file":
        (runtime.root / "usr/extra").write_text("extra")
    elif change == "extra_directory":
        (runtime.root / "usr/extra").mkdir()
    elif change == "directory_mode":
        (runtime.root / "usr").chmod(0o777)
    else:
        (runtime.root / "lib64").symlink_to("missing")
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


@pytest.mark.parametrize("mount", [
    "", "malformed", "1 2 8:1 /wrong / ro - ext4 /dev/disk rw\n",
    "1 2 8:1 /var/lib/foundups/isolated-issuer / rw - ext4 /dev/disk rw\n",
    "1 2 8:1 /var/lib/foundups/isolated-issuer / ro,rw - ext4 /dev/disk rw\n",
])
def test_bad_root_mount(runtime, mount):
    runtime.proc["mountinfo"] = mount
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


@pytest.mark.parametrize("target", ["/", "/usr", "/opt/grant-source", "/lib64/hidden"])
def test_duplicate_root_or_static_overmount(runtime, target):
    runtime.proc["mountinfo"] += f"2 1 0:1 / {target} ro - tmpfs tmpfs ro\n"
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


def test_kernel_escaped_mount_root(runtime):
    runtime.proc["mountinfo"] = runtime.proc["mountinfo"].replace("isolated-issuer", r"isolated\055issuer")
    assert guard.verify_installed_grant_runtime(runtime.descriptor) is None


@pytest.mark.parametrize("field", ["CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs", "Seccomp"])
def test_process_confinement_drift(runtime, field):
    lines = runtime.proc["status"].splitlines()
    runtime.proc["status"] = "\n".join(line if not line.startswith(field + ":")
        else field + ":\t" + ("1" if field.startswith("Cap") else "0") for line in lines)
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


@pytest.mark.parametrize("change", ["sys_path", "flags", "site", "argv", "exe", "env", "module", "platform"])
def test_launch_or_loaded_source_drift(runtime, change):
    if change == "sys_path":
        runtime.system.path.append("/tmp")
    elif change == "flags":
        runtime.system.flags.isolated = 0
    elif change == "site":
        runtime.system.modules["site"] = object()
    elif change == "argv":
        runtime.system.orig_argv[1] = "-E"
    elif change == "exe":
        guard.os.readlink = lambda name: "/tmp/foreign"
    elif change == "env":
        guard.os.environ["LD_PRELOAD"] = "not-read"
    elif change == "module":
        runtime.system.modules["bad"] = SimpleNamespace(__file__="/tmp/foreign.py")
    else:
        runtime.system.platform = "win32"
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


@pytest.mark.parametrize("change", ["inode", "device", "deleted", "foreign", "anonymous"])
def test_native_mapping_drift(runtime, change):
    fields = runtime.proc["maps"].split()
    if change == "inode":
        fields[4] = "0"
    elif change == "device":
        fields[3] = "ff:ff"
    elif change == "deleted":
        fields.append("(deleted)")
    elif change == "foreign":
        fields[5] = "/tmp/foreign.so"
    else:
        fields = fields[:5]
    runtime.proc["maps"] = " ".join(fields)
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


def test_late_environment_drift_rejected(runtime, monkeypatch):
    original = guard._loaded
    def changed(identities):
        original(identities)
        guard.os.environ["PYTHONPATH"] = "not-read"
    monkeypatch.setattr(guard, "_loaded", changed)
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


@pytest.mark.parametrize("relative", ["usr", "usr/lib/python3.12/abc.py"])
@pytest.mark.parametrize("owner", [(1, 0), (0, 1)])
def test_root_ownership_required(runtime, relative, owner):
    os.chown(runtime.root / relative, *owner)
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


@pytest.mark.parametrize("status", ["", "CapEff:\tbad\n", "NoNewPrivs:\t1\nNoNewPrivs:\t1\n"])
def test_missing_malformed_duplicate_status(runtime, status):
    runtime.proc["status"] = status
    with pytest.raises(ValueError):
        guard.verify_installed_grant_runtime(runtime.descriptor)


def test_executable_inode_is_current(runtime):
    guard.os.stat = lambda name: (runtime.root / "usr/lib/python3.12/abc.py").stat()
    with pytest.raises(ValueError, match="executable_identity"):
        guard.verify_installed_grant_runtime(runtime.descriptor)


def test_platform_rejection_before_observation(monkeypatch):
    monkeypatch.setattr(guard, "sys", SimpleNamespace(platform="win32"))
    assert guard.verify_installed_grant_runtime.__annotations__["return"] == "None"
    with pytest.raises(ValueError, match="platform"):
        guard.verify_installed_grant_runtime(_descriptor())
