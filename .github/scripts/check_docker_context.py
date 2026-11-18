#!/usr/bin/env python3
"""Exercise the root ignore policy with Docker itself and synthetic files only.

No credentials, application dependencies, images or registries are contacted.
This proves the selected context exclusions, not a full application-image build.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
ALLOWED = (
    "main.py", "requirements.txt", "memory/__init__.py",
    "memory/memory_manager.py", "holo_index/core.py",
    "modules/example/src/credentials_manager.py",
    "modules/example/requirements.txt", "modules/example/memory/README.md",
    "public/index.html",
    "foundups-mcp-p1/README.md", "foundups-mcp-p1/requirements.txt",
    "foundups-mcp-p1/setup_mcp_servers.py",
    "foundups-mcp-p1/servers/holo_index/server.py",
    "foundups-mcp-p1/servers/wsp_governance/server.py",
)
DENIED = (
    ".env", ".env.local", "nested/.env", "nested/.env.production",
    "credentials/probe.json", "nested/credentials/probe.json",
    "client_secret_probe.json", "nested/client_secret_probe.json",
    "nested/oauth_token_probe.json", "nested/token_probe.json",
    "nested/service_account_probe.json", "nested/probe-service-account.json",
    "nested/probe-firebase-adminsdk.json", "nested/probe.pem", "nested/probe.key",
    "nested/probe.p12", "nested/probe.pfx", ".git/config", "nested/.git",
    ".ssh/id_rsa", ".aws/credentials", ".config/gcloud/probe.json",
    "nested/.config/gcloud/probe.json", ".docker/config.json",
    "nested/.npmrc", "nested/.netrc", "nested/.pypirc",
    "nested/browser_profiles/probe.json", "nested/chrome_profile_test/Cookies",
    "nested/edge_profile_test/Cookies", ".runtime/probe.json",
    "nested/.runtime/probe.json", ".reddog/probe.json", ".worktrees/probe.py",
    ".claude/worktrees/probe.py", ".m2m/probe.json", "012.txt",
    "012.longlines.txt", "012.txt.bak_probe", "memory/private.json",
    "nested/probe.db", "nested/probe.db-wal", "nested/probe.sqlite",
    "nested/probe.sqlite3", "nested/probe.sqlite3-shm", "nested/probe.log",
    "logs/probe.txt", "02_logs/probe.txt", "nested/.venv/probe.py",
    "nested/venv/probe.py", "nested/node_modules/probe.js",
    "foundups-mcp-p1/foundups-mcp-env/Scripts/python.exe",
    "foundups-mcp-p1/foundups-mcp-env/Scripts/pip.exe",
    "foundups-mcp-p1/foundups-mcp-env/Scripts/uv.exe",
    "foundups-mcp-p1/foundups-mcp-env/bin/python",
    "foundups-mcp-p1/foundups-mcp-env/pyvenv.cfg",
    "foundups-mcp-p1/foundups-mcp-env/Lib/site-packages/probe.py",
    "nested/__pycache__/probe.pyc", "nested/probe.pyc",
    "nested/.pytest_cache/probe", "nested/.mypy_cache/probe",
    "nested/.ruff_cache/probe", "nested/.cache/probe", "nested/probe.gguf",
    "nested/probe.safetensors", "holo_index/models/probe.bin",
    "holo_index_data/probe.bin", "E\uf03a/HoloIndex/vectors/probe.bin",
)


def project(docker: str, root: Path, policy: str | None, label: str) -> set[str]:
    """Export a scratch COPY using the native Docker ignore implementation."""
    context, output = root / label / "context", root / label / "output"
    context.mkdir(parents=True)
    for name in ALLOWED + DENIED:
        path = context / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic-context-probe\n", encoding="utf-8")
    if policy is not None:
        (context / ".dockerignore").write_text(policy, encoding="utf-8")
    result = subprocess.run(
        [docker, "buildx", "build", "--no-cache", "--network=none",
         "--progress=plain", "--file", "-", "--output",
         f"type=local,dest={output}", str(context)],
        input="FROM scratch\nCOPY . /context/\n", text=True,
        capture_output=True, timeout=120, check=False,
    )
    if result.returncode:
        # Input is synthetic, but keep even diagnostic output bounded.
        raise RuntimeError(f"Docker {label} failed: {result.stderr[-4000:]}")
    exported = output / "context"
    if not output.is_dir():
        raise RuntimeError(f"Docker {label} did not produce an export")
    return {path.relative_to(exported).as_posix()
            for path in exported.rglob("*") if path.is_file()}


def main() -> int:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker with buildx is required; no simulated pass")
    policy_path = ROOT / ".dockerignore"
    if policy_path.is_symlink() or not policy_path.is_file():
        raise RuntimeError("Root .dockerignore must be a regular file")
    override = ROOT / "Dockerfile.dockerignore"
    if override.exists() or override.is_symlink():
        raise RuntimeError("Dockerfile-specific override requires explicit qualification")
    policy_bytes = policy_path.read_bytes()
    if not policy_bytes or len(policy_bytes) > 65536:
        raise RuntimeError("Empty or oversized Docker ignore policy")
    with tempfile.TemporaryDirectory(prefix="foundups-context-") as directory:
        work = Path(directory)
        actual = project(docker, work, policy_bytes.decode("utf-8"), "policy")
        leaked, missing = set(DENIED) & actual, set(ALLOWED) - actual
        if leaked or missing:
            raise RuntimeError(f"Context contract failed: leaked={sorted(leaked)}; "
                               f"missing_source={sorted(missing)}")
        # Controls prove this harness detects both no protection and blanket hiding.
        unfiltered = project(docker, work, None, "no-ignore-control")
        if not set(DENIED + ALLOWED) <= unfiltered:
            raise RuntimeError("Unfiltered control did not expose all synthetic files")
        hidden = project(docker, work, "**\n", "hide-all-control")
        if set(ALLOWED) & hidden:
            raise RuntimeError("Hide-all control did not remove required source")
    print(json.dumps({
        "status": "passed", "excluded_fixtures": len(DENIED),
        "retained_source_fixtures": len(ALLOWED), "negative_controls": 2,
        "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
        "engine": "docker-buildx", "inputs": "synthetic-only",
        "full_application_build": "not_tested",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
