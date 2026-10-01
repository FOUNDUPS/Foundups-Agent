"""Bounded CI-only Linux fixture runner; never install production authority."""

from pathlib import Path
from contextvars import ContextVar
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import types
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit

_OPEN_TARGET = ContextVar("reviewer_fixture_open_target", default=None)


def main():
    if not __debug__ or not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("isolated_assertion_enabled_no_bytecode_required")
    if not sys.platform.startswith("linux") or os.geteuid() != 0:
        raise RuntimeError("disposable_root_linux_fixture_required")
    repo = Path(__file__).resolve().parents[4]
    output = Path(sys.argv[1]).resolve()
    if not output.is_absolute() or output.is_relative_to(repo) or repo.is_relative_to(output):
        raise RuntimeError("external_evidence_directory_required")
    output.mkdir(exist_ok=False)
    paths = subprocess.check_output(["git", "-c", "safe.directory=" + str(repo), "-C", str(repo), "ls-files", "-z", "--", "*.py"])
    paths = paths.decode("utf-8").rstrip("\0").split("\0")
    before = {p: _sha(repo / p) for p in paths}
    with tempfile.TemporaryDirectory(prefix="rsi-reviewer-", dir="/root") as raw:
        base = Path(raw).resolve()
        _environment(repo, base)
        blocked, databases, restore = _install_guard(repo, base, output, set(paths))
        try:
            result = _run(repo, base, output)
        finally:
            restore()
        after = {p: _sha(repo / p) for p in paths}
        result.update(hashes_stable=before == after, source_bindings=before,
                      blocked=blocked, database_opens=databases, uid=os.geteuid())
        result["limits"] = "Disposable Linux ownership/lease fixture; supplied reviewer runtime, no production admission or retained gain. Python guard is not OS containment."
        (output / "receipt.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        assert before == after and not blocked and result["passed"]
    return 0


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _environment(repo, base):
    path = os.environ.get("PATH", "/usr/bin:/bin")
    os.environ.clear()
    os.environ.update(PATH=path, HOME=str(base), TMPDIR=str(base), TMP=str(base), TEMP=str(base),
                      RSI_REVIEWER_TEST_ROOT=str(base), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                      PYTHONDONTWRITEBYTECODE="1", FOUNDUPS_DB_ENGINE="sqlite", DATABASE_URL="")
    tempfile.tempdir = str(base)
    platform._node = lambda default="": "rsi-disposable-test-host"
    platform.machine = lambda: "x86_64"
    sys.path.insert(0, str(repo))
    for name in ("modules", "modules.communication", "modules.communication.moltbot_bridge",
                 "modules.communication.moltbot_bridge.src", "modules.communication.moltbot_bridge.tests",
                 "modules.infrastructure", "modules.infrastructure.secrets_mcp"):
        module = types.ModuleType(name)
        module.__path__ = [str(repo / Path(*name.split(".")))]
        sys.modules[name] = module
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(sys.modules[parent], child, module)


def _resolved(value, descriptor=None):
    path = Path(os.fsdecode(value))
    if not path.is_absolute() and isinstance(descriptor, int) and descriptor >= 0:
        path = Path(os.readlink("/proc/self/fd/" + str(descriptor))) / path
    return path.resolve()


def _install_guard(repo, base, output, sources):
    blocked, databases = [], []
    def owned(path):
        return path.is_relative_to(base) or path.is_relative_to(output)
    def deny(event):
        blocked.append(event)
        raise RuntimeError("reviewer_fixture_guard:" + event)
    def guard(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.exec", "os.kill"}:
            deny(event)
        if event == "import" and str(args[0]).split(".")[0] in {"openai", "anthropic", "requests", "httpx", "llama_cpp", "torch", "transformers", "dotenv", "psycopg", "psycopg2"}:
            deny("provider_import")
        if event == "sqlite3.connect":
            try:
                path = _database_path(args[0], base)
            except (TypeError, ValueError):
                deny("unqualified_database")
            if len(databases) >= 256:
                deny("unqualified_database")
            databases.append(str(path))
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = _OPEN_TARGET.get() or Path(os.fsdecode(args[0])).resolve()
            mode, flags = args[1:3]
            write = (isinstance(mode, str) and any(c in mode for c in "wax+")) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if write and not owned(path) and path != Path(os.devnull):
                deny("external_write")
            if not write and not owned(path) and (path.name.startswith(".env") or path.suffix in {".pem", ".key", ".gguf"} or any(p in {".ssh", ".aws", ".azure", ".config"} for p in path.parts)):
                deny("sensitive_read")
            if path.is_relative_to(repo) and path.suffix == ".py" and path.relative_to(repo).as_posix() not in sources:
                deny("unlisted_source")
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.utime", "os.truncate"} and not isinstance(args[0], int):
            index = {"os.remove": 1, "os.rmdir": 1, "os.mkdir": 2, "os.chmod": 2, "os.chown": 3}.get(event)
            descriptor = args[index] if index is not None and len(args) > index else None
            if not owned(_resolved(args[0], descriptor)):
                deny("external_mutation")
        if event in {"os.rename", "os.replace", "os.link", "os.symlink"}:
            descriptors = (None, args[2]) if event == "os.symlink" else (args[2], args[3])
            if not all(owned(_resolved(p, fd)) for p, fd in zip(args[:2], descriptors)):
                deny("external_link_or_move")
        if event == "os.chdir" and _resolved(args[0]) != repo and not owned(_resolved(args[0])):
            deny("external_chdir")
    sys.addaudithook(guard)
    return blocked, databases, _observe_open_targets()


def _database_path(value, base):
    if type(value) is not str or value == ":memory:":
        raise ValueError("invalid_database_target")
    raw = value
    if raw.startswith("file:"):
        uri = urlsplit(raw)
        if uri.netloc or uri.query != "mode=ro" or uri.fragment:
            raise ValueError("noncanonical_database_uri")
        path = Path(unquote(uri.path)).resolve()
        if raw != path.as_uri() + "?mode=ro":
            raise ValueError("noncanonical_database_uri")
    else:
        path = Path(raw).resolve()
    if not path.is_relative_to(base):
        raise ValueError("external_database")
    return path


def _observe_open_targets():
    """Expose dir_fd to the audit hook without changing actual descriptor calls."""
    original = os.open
    def observed(path, flags, mode=0o777, *, dir_fd=None):
        token = _OPEN_TARGET.set(_resolved(path, dir_fd))
        try:
            return original(path, flags, mode, dir_fd=dir_fd)
        finally:
            _OPEN_TARGET.reset(token)
    os.open = observed
    def restore():
        os.open = original
    return restore


def _run(repo, base, output):
    import pytest
    stem = "modules/communication/moltbot_bridge/tests/test_reddog_reviewer_authority_composition_linux.py::test_real_linux_reviewer_authority"
    nodes = [stem + "[" + case + "]" for case in ("positive", "wrong_uid", "writable_owner", "symlink_owner", "stale_generation")]
    transport = "modules/communication/moltbot_bridge/tests/test_reddog_signer_independent_grant_authority_client_supply.py::test_supply_binds_root_transport_to_signed_policy"
    nodes += [transport + "[reddog_signer_system_service_owner_config." + version + "]" for version in ("v3", "v4", "v5")]
    config = output / "pytest.ini"
    config.write_text("[pytest]\n", encoding="utf-8")
    args = nodes + ["-c", str(config), "--rootdir=" + str(repo), "--noconftest", "--import-mode=importlib",
                    "-p", "no:cacheprovider", "-v", "--tb=short", "--basetemp=" + str(base / "pytest"),
                    "--junitxml=" + str(output / "results.xml")]
    code = int(pytest.main(args))
    xml = ET.parse(output / "results.xml").getroot()
    counts = {k: sum(int(s.get(k, 0)) for s in xml) for k in ("tests", "failures", "errors", "skipped")}
    cases = [t.get("name") for t in xml.iter("testcase")]
    return dict(command=args, returncode=code, counts=counts, cases=cases,
                passed=code == 0 and counts == dict(tests=len(nodes), failures=0, errors=0, skipped=0)
                and set(cases) == {n.split("::", 1)[1] for n in nodes})


if __name__ == "__main__":
    raise SystemExit(main())
