"""Explicit Linux Docker test transport; no deployment or runtime admission."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[4]
PREFIX = ["docker", "--host", "unix:///var/run/docker.sock"]
FILES = (
    "modules/__init__.py",
    "modules/foundups/agent/src/__init__.py",
    "modules/foundups/agent/src/kanban_plugin_contract.py",
    "modules/foundups/pfmall/__init__.py",
    "modules/foundups/pfmall/api.py",
    "modules/foundups/pfmall/http_api.py",
    "modules/foundups/pfmall/intake_host.py",
    "modules/foundups/pfmall/listing_discovery.py",
    "modules/foundups/pfmall/shell_core.py",
    "modules/foundups/pfmall/static/detail.html",
    "modules/foundups/pfmall/static/handoff.html",
    "modules/foundups/pfmall/static/index.html",
    "modules/foundups/pfmall/static/styles.css",
    "modules/ai_intelligence/ai_overseer/src/foundup_genesis/__init__.py",
    "modules/ai_intelligence/ai_overseer/src/foundup_genesis/clerk_intake.py",
    "modules/ai_intelligence/ai_overseer/src/foundup_genesis/envelope.py",
    "modules/ai_intelligence/ai_overseer/src/foundup_genesis/intake_auth_provider.py",
    "modules/ai_intelligence/ai_overseer/src/foundup_genesis/intake_transport.py",
    "modules/ai_intelligence/ai_overseer/src/foundup_genesis/launch_request.py",
    "modules/ai_intelligence/ai_overseer/src/foundup_genesis/validator.py",
    "modules/foundups/pfmall/requirements.txt",
    "modules/foundups/pfmall/requirements-server.txt",
    "modules/foundups/pfmall/requirements-container.lock",
    "modules/foundups/pfmall/Dockerfile.intake",
)


def _env(directory):
    result = {k: os.environ[k] for k in ("PATH", "SystemRoot", "WINDIR", "COMSPEC") if k in os.environ}
    result.update(HOME=str(directory), USERPROFILE=str(directory), DOCKER_CONFIG=str(directory / "docker-config"),
                  PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
    return result


def _run(args, directory, *, check=True, timeout=20, data=None):
    return subprocess.run(args, cwd=ROOT, env=_env(directory), input=data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=check)


def _docker(directory, *args, check=True, timeout=20):
    if sys.platform != "linux":
        raise RuntimeError("container_profile_requires_linux")
    return _run(PREFIX + list(args), directory, check=check, timeout=timeout)


def _pins(text):
    return {re.sub(r"[-_.]+", "-", k).lower(): v for k, v in
            re.findall(r"(?m)^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^\s\\]+)", text)}


def build_context(directory):
    """Archive only exact regular Git blobs; never send the working tree."""
    directory.mkdir(parents=True, exist_ok=True)
    head = _run(["git", "rev-parse", "HEAD"], directory).stdout.decode().strip()
    archive = _run(["git", "archive", "--format=tar", head, "--", *FILES], directory).stdout
    listing = _run(["git", "ls-tree", "-rz", head, "--", *FILES], directory).stdout
    blobs = {}
    for row in listing.split(b"\0"):
        if row:
            metadata, name = row.split(b"\t", 1)
            mode, kind, digest = metadata.split()
            assert mode in (b"100644", b"100755") and kind == b"blob"
            blobs[name.decode()] = digest.decode()
    contents = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for member in source:
            if member.isdir():
                continue
            assert member.isfile() and member.name in FILES and member.name not in contents
            raw = source.extractfile(member).read()
            assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == blobs[member.name]
            contents[member.name] = raw
    assert set(contents) == set(blobs) == set(FILES)
    lock = _pins(contents["modules/foundups/pfmall/requirements-container.lock"].decode())
    for name in ("requirements.txt", "requirements-server.txt"):
        pins = _pins(contents["modules/foundups/pfmall/" + name].decode())
        assert all(lock.get(k) == v for k, v in pins.items())
    record = dict(head=head, files={k: hashlib.sha256(v).hexdigest() for k, v in contents.items()},
                  archive_sha256=hashlib.sha256(archive).hexdigest(), locked_packages=lock)
    (directory / "context.tar").write_bytes(archive)
    (directory / "context.json").write_text(json.dumps(record, indent=2) + "\n")
    return archive, record


def build_image(directory):
    archive, context = build_context(directory)
    image_file = directory / "image-id"
    result = _run(PREFIX + ["build", "--platform", "linux/amd64", "--progress", "plain",
        "--file", "modules/foundups/pfmall/Dockerfile.intake", "--iidfile", str(image_file), "-"],
        directory, timeout=360, data=archive, check=False)
    (directory / "build.log").write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, "container_build_failed"
    image = image_file.read_text().strip()
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", image)
    image_file.write_text(image + "\n")
    config = json.loads(_docker(directory, "image", "inspect", image).stdout)[0]
    assert config["Config"]["User"] == "10001:10001" and not config["Config"]["Entrypoint"]
    assert config["Config"]["WorkingDir"] == "/app"
    assert config["Config"]["Cmd"][:5] == ["python", "-I", "-B", "-m", "uvicorn"]
    code = ("import hashlib,importlib.metadata as m,json,os,pathlib,sys;"
        "p=pathlib.Path('/app');assert not any(x.is_symlink() for x in p.rglob('*'));"
        "print(json.dumps(dict(uid=os.getuid(),python=sys.version,files={x.relative_to(p).as_posix():"
        "hashlib.sha256(x.read_bytes()).hexdigest() for x in p.rglob('*') if x.is_file()},"
        "packages={d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()},"
        "os_release=pathlib.Path('/etc/os-release').read_text(),"
        "os_packages=pathlib.Path('/var/lib/dpkg/status').read_text())))")
    name = "foundups-intake-audit-" + uuid.uuid4().hex
    assert _inspect(directory, name) is None
    try:
        audit = json.loads(_docker(directory, "run", "--name", name, "--label",
            "foundups.intake.test=" + name, "--network", "none", image,
            "python", "-I", "-B", "-c", code).stdout)
    finally:
        _remove(directory, name)
    assert audit["uid"] == 10001 and audit["python"].startswith("3.12.15 ")
    assert audit["files"] == {k: v for k, v in context["files"].items()
                              if k.startswith("modules/") and not k.endswith((".txt", ".lock", "Dockerfile.intake"))}
    assert audit["packages"] == {**context["locked_packages"], "pip": "26.2.2"}
    audit["image"] = image
    (directory / "image-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return image


def _inspect(directory, name):
    result = _docker(directory, "container", "inspect", name, check=False)
    if result.returncode:
        if b"no such object" in result.stderr.lower() or b"no such container" in result.stderr.lower():
            return None
        raise RuntimeError("container_inspection_failed")
    return json.loads(result.stdout)[0]


def _remove(directory, name):
    state = _inspect(directory, name)
    if state is not None:
        assert state["Config"]["Labels"].get("foundups.intake.test") == name
        _docker(directory, "container", "rm", "--force", state["Id"])
    assert _inspect(directory, name) is None


def container_wire_server(directory, image):
    """Yield the original test fixture contract using actual image HTTP."""
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", image)
    clients = []

    def start(config):
        name = "foundups-intake-" + uuid.uuid4().hex
        assert _inspect(directory, name) is None
        log = directory / (name + "-server.log")
        args = PREFIX + ["run", "--name", name, "--label", "foundups.intake.test=" + name,
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--memory", "256m", "--cpus", "1", "--pids-limit", "64", "--network", "bridge",
            "--publish", "127.0.0.1::8080", "--env", "PFMALL_CLERK_POLICY_FILE=/run/policy.json"]
        if config.is_file():
            args += ["--mount", "type=bind,src=" + str(config.resolve()) + ",dst=/run/policy.json,readonly"]
        clients.append([None, name])
        with log.open("wb") as stream:
            child = subprocess.Popen(args + [image], cwd=ROOT, env=_env(directory),
                                     stdout=stream, stderr=stream)
        clients[-1][0] = child
        deadline, port = time.monotonic() + 15, None
        while time.monotonic() < deadline:
            if "Uvicorn running on http://0.0.0.0:8080" in log.read_text():
                state = _inspect(directory, name)
                assert state["State"]["Running"] and state["State"]["Pid"] > 0 and state["Image"] == image
                assert state["HostConfig"]["ReadonlyRootfs"] and state["HostConfig"]["PidsLimit"] == 64
                assert state["HostConfig"]["Memory"] == 256 * 1024 * 1024
                assert state["HostConfig"]["NanoCpus"] == 1000000000
                bindings = state["NetworkSettings"]["Ports"]["8080/tcp"]
                assert len(bindings) == 1 and bindings[0]["HostIp"] == "127.0.0.1"
                port = int(bindings[0]["HostPort"])
                probe = ("import os,pathlib;assert os.getuid()==10001;"
                    "s=dict(x.split(':',1) for x in pathlib.Path('/proc/1/status').read_text().splitlines());"
                    "assert s['NoNewPrivs'].strip()=='1' and int(s['CapEff'].strip(),16)==0;"
                    "assert int(s['Uid'].split()[0])==10001;"
                    "assert b'uvicorn' in pathlib.Path('/proc/1/cmdline').read_bytes()")
                _docker(directory, "exec", name, "python", "-I", "-B", "-c", probe)
                break
            if child.poll() is not None:
                break
            time.sleep(0.05)
        state = _inspect(directory, name)
        assert state is not None
        record = dict(name=name, image=state["Image"], state={k: state["State"][k]
            for k in ("Running", "Pid", "ExitCode")}, port=port, scope="container transport only")
        (directory / (name + "-container.json")).write_text(json.dumps(record, indent=2) + "\n")
        return child, port, log

    try:
        yield start
    finally:
        for child, name in clients:
            try:
                _remove(directory, name)
            finally:
                try:
                    if child is not None:
                        if child.poll() is None:
                            child.terminate()
                        try:
                            child.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=3)
                finally:
                    _remove(directory, name)
