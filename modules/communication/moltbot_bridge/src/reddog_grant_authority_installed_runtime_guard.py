"""Sample the current Linux issuer runtime; success does not confer authority.

Call before secret materialization and again at critical use boundaries. The
caller must authenticate the descriptor independently. Host root and the kernel
remain trusted; these observations do not prove immutable future execution.
"""
from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path
from typing import Mapping

from .reddog_grant_authority_installed_source_contract import validate_installed_grant_source
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity, secure_digest_confined_file_impl,
)

_STATIC = frozenset(("usr", "lib", "lib64", "etc", "opt"))
_ENVIRONMENT = frozenset(("PATH", "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "HOME",
    "LOGNAME", "USER", "SHELL", "INVOCATION_ID", "JOURNAL_STREAM", "SYSTEMD_EXEC_PID",
    "MEMORY_PRESSURE_WATCH", "MEMORY_PRESSURE_WRITE", "CREDENTIALS_DIRECTORY"))


def verify_installed_grant_runtime(descriptor: Mapping) -> None:
    """Reject drift in the authenticated inventory and current process boundary."""
    value = validate_installed_grant_source(descriptor)
    if sys.platform != "linux":
        _reject("platform")
    _process(value)
    _mounts(value)
    wanted = {row["path"]: row for row in value["files"]}
    _membership(value, wanted)
    identities = {}
    for relative, row in wanted.items():
        path = Path("/") / relative
        metadata = path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0
                or metadata.st_gid != 0 or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != row["mode"]):
            _reject("file_metadata")
        identity = confined_file_identity(metadata)
        proof = secure_digest_confined_file_impl(path, allowed_root=Path("/"),
            expected_identity=identity, max_bytes=max(row["bytes"], 1))
        if proof.size != row["bytes"] or proof.digest != "sha256:" + row["sha256"]:
            _reject("file_bytes")
        identities["/" + relative] = identity
    _loaded(identities)
    _membership(value, wanted)
    _mounts(value)
    _process(value)


def _process(value):
    flags = sys.flags
    if (sys.version_info[:2] != (3, 12) or sys.executable != value["python_launch"][0]
            or os.readlink("/proc/self/exe") != sys.executable
            or list(sys.orig_argv[:4]) != value["python_launch"]
            or list(sys.path) != value["explicit_sys_path"]
            or any(getattr(flags, key) != 1 for key in
                   ("isolated", "no_site", "ignore_environment", "dont_write_bytecode"))
            or any(key in sys.modules for key in ("site", "sitecustomize", "usercustomize"))
            or not set(os.environ) <= _ENVIRONMENT):
        _reject("python_environment")
    fields = {}
    for line in _proc("status").splitlines():
        key, separator, val = line.partition(":")
        if separator:
            if key in fields:
                _reject("process_status")
            fields[key] = val.strip()
    try:
        if (any(int(fields[key], 16) != 0 for key in
                ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"))
                or fields["NoNewPrivs"] != "1" or fields["Seccomp"] != "2"):
            _reject("process_confinement")
    except (KeyError, ValueError) as exc:
        raise ValueError("grant_installed_runtime_process_confinement") from exc


def _mounts(value):
    roots = []
    for line in _proc("mountinfo").splitlines():
        fields = line.split()
        try:
            separator = fields.index("-")
            if separator < 6 or len(fields) != separator + 4:
                _reject("mountinfo")
            root, target = _unescape(fields[3]), _unescape(fields[4])
            if target == "/":
                roots.append((root, set(fields[5].split(","))))
            elif target.split("/")[1] in _STATIC:
                _reject("static_overmount")
        except (ValueError, IndexError) as exc:
            raise ValueError("grant_installed_runtime_mountinfo") from exc
    if (len(roots) != 1 or roots[0][0] != value["installed_root"]
            or "ro" not in roots[0][1] or "rw" in roots[0][1]):
        _reject("root_mount")


def _membership(value, wanted):
    expected_dirs = set(value["directories"])
    if any(path.split("/")[0] not in _STATIC for path in set(wanted) | expected_dirs):
        _reject("static_scope")
    files, directories = set(), set()
    _directory(Path("/"))
    for top in _STATIC:
        path = Path("/") / top
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        _directory(path)
        for current, names, leaves in os.walk(path, followlinks=False, onerror=_walk_error):
            directory = Path(current)
            _directory(directory)
            directories.add(directory.relative_to("/").as_posix())
            for name in names:
                _directory(directory / name)
            files.update((directory / name).relative_to("/").as_posix() for name in leaves)
            if len(files) > len(wanted) or len(directories) > len(expected_dirs):
                _reject("inventory")
    if files != set(wanted) or directories != expected_dirs:
        _reject("inventory")


def _directory(path):
    metadata = path.lstat()
    if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != 0
            or metadata.st_gid != 0 or metadata.st_mode & 0o022):
        _reject("directory_metadata")


def _loaded(identities):
    executable = identities.get(sys.executable)
    actual = os.stat("/proc/self/exe")
    if executable is None or (actual.st_dev, actual.st_ino) != (executable.device, executable.inode):
        _reject("executable_identity")
    for line in _proc("maps").splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) < 5:
            _reject("native_maps")
        path = _unescape(fields[5]) if len(fields) == 6 else ""
        if path.startswith("/"):
            identity = identities.get(path)
            device = fields[3].split(":")
            if (identity is None or int(fields[4]) != identity.inode
                    or tuple(int(part, 16) for part in device)
                    != (os.major(identity.device), os.minor(identity.device))):
                _reject("native_identity")
        elif "x" in fields[1] and path not in ("[vdso]", "[vsyscall]"):
            _reject("anonymous_executable")
    for module in tuple(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path is not None and path not in identities:
            _reject("loaded_source")


def _unescape(value):
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), value)


def _proc(name):
    with open("/proc/self/" + name, "r", encoding="utf-8", errors="strict") as stream:
        text = stream.read(4 * 1024 * 1024 + 1)
    if len(text) > 4 * 1024 * 1024:
        _reject("proc_bound")
    return text


def _walk_error(error):
    raise error


def _reject(reason):
    raise ValueError("grant_installed_runtime_" + reason)
