"""Security tests for manifest-authenticated Holo subprocesses."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service_supervisor as supervisor,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_maintenance_handshake as handshake,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_sealed_holo_runtime import (
    SEALED_BOOTSTRAP_ENV,
    SEALED_MANIFEST_DIGEST_ENV,
    SEALED_MANIFEST_ENV,
    SEALED_REQUIRED_ENV,
    SEALED_ROOT_ENV,
    SEALED_SITE_PACKAGES_ENV,
    scrub_holo_child_environment,
    sealed_holo_command,
    trusted_holo_site_packages,
)


def _sealed_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    source = tmp_path / "runtime"
    trusted = (
        source
        / "modules"
        / "infrastructure"
        / "foundups_mcp_bridge"
        / "src"
        / "trusted.py"
    )
    bootstrap = (
        source
        / "extensions"
        / "reddog"
        / "start_operations_python_bootstrap.py"
    )
    entry = source / "holo_index.py"
    owner_entry = source / "scripts" / "reddog_holoindex_owner_service_once.py"
    manifest = source / ".reddog-runtime-manifest.json"
    site = tmp_path / "site-packages"
    for path in (trusted, bootstrap, entry, owner_entry):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass\n", encoding="utf-8")
    runtime_files = {}
    for path in (trusted, bootstrap, entry, owner_entry):
        relative = path.relative_to(source).as_posix()
        runtime_files[relative] = hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
    value = {"required_runtime_sha256": runtime_files}
    manifest.write_text(json.dumps(value), encoding="utf-8")
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    site.mkdir()
    env = {
        SEALED_REQUIRED_ENV: "1",
        SEALED_ROOT_ENV: str(source),
        SEALED_MANIFEST_ENV: str(manifest),
        SEALED_MANIFEST_DIGEST_ENV: hashlib.sha256(canonical).hexdigest(),
        SEALED_BOOTSTRAP_ENV: str(bootstrap),
        SEALED_SITE_PACKAGES_ENV: str(site),
    }
    return trusted, source, env


def test_sealed_command_uses_manifest_runtime_not_live_checkout(
    tmp_path: Path,
) -> None:
    trusted, source, env = _sealed_fixture(tmp_path)
    command = sealed_holo_command(
        environ=env,
        trusted_module_path=trusted,
        target_repo_root=tmp_path / "repo",
        entry_relative_path="holo_index.py",
        script_args=("--index-all",),
        python_executable="python",
    )

    assert command is not None
    assert command[:4] == ("python", "-I", "-S", "-B")
    assert command[5] == str(source / "holo_index.py")
    assert command[-1] == "--index-all"


def test_sealed_command_rejects_live_or_substituted_paths(tmp_path: Path) -> None:
    trusted, _source, env = _sealed_fixture(tmp_path)
    env[SEALED_BOOTSTRAP_ENV] = str(tmp_path / "attacker.py")

    assert sealed_holo_command(
        environ=env,
        trusted_module_path=trusted,
        target_repo_root=tmp_path / "repo",
        entry_relative_path="holo_index.py",
        script_args=(),
        python_executable="python",
    ) == ()


def test_sealed_command_rejects_tampered_bootstrap_before_spawn(
    tmp_path: Path,
) -> None:
    trusted, _source, env = _sealed_fixture(tmp_path)
    Path(env[SEALED_BOOTSTRAP_ENV]).write_text("attacker()\n", encoding="utf-8")

    assert sealed_holo_command(
        environ=env,
        trusted_module_path=trusted,
        target_repo_root=tmp_path / "repo",
        entry_relative_path="holo_index.py",
        script_args=(),
        python_executable="python",
    ) == ()


def test_holo_child_environment_drops_provider_and_authority_secrets() -> None:
    child = scrub_holo_child_environment(
        {
            "PATH": "runtime-path",
            "OPENROUTER_API_KEY": "secret",
            "GITHUB_TOKEN": "secret",
            "GOOGLE_AISTUDIO_API_KEY": "secret",
            "REDDOG_AUTHENTICATED_PRINCIPAL_ID": "principal",
            "REDDOG_SEALED_RUNTIME_REQUIRED": "1",
            "PYTHONPATH": "attacker",
        }
    )

    assert child["PATH"] == "runtime-path"
    assert child["REDDOG_SEALED_RUNTIME_REQUIRED"] == "1"
    assert "OPENROUTER_API_KEY" not in child
    assert "GITHUB_TOKEN" not in child
    assert "GOOGLE_AISTUDIO_API_KEY" not in child
    assert "REDDOG_AUTHENTICATED_PRINCIPAL_ID" not in child
    assert "PYTHONPATH" not in child


def test_trusted_holo_site_packages_accepts_only_checkout_local_windows_venv(
    tmp_path: Path,
) -> None:
    base = tmp_path / "Python312" / "python.exe"
    base.parent.mkdir()
    base.write_bytes(b"python")
    site_packages = tmp_path / ".venv" / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    (tmp_path / ".venv" / "pyvenv.cfg").write_text(
        "\n".join(
            (
                f"home = {base.parent}",
                "include-system-site-packages = false",
                "version = 3.12.2",
                f"executable = {base}",
            )
        ),
        encoding="utf-8",
    )

    assert trusted_holo_site_packages(
        tmp_path,
        platform_name="nt",
        python_version=(3, 12),
        base_executable=base,
    ) == (str(site_packages.resolve()),)
    assert trusted_holo_site_packages(
        tmp_path,
        platform_name="nt",
        python_version=(3, 11),
        base_executable=base,
    ) == ()
    assert trusted_holo_site_packages(
        tmp_path, platform_name="posix"
    ) == ()
    assert trusted_holo_site_packages(
        tmp_path / "missing", platform_name="nt"
    ) == ()


def test_maintenance_runner_uses_sealed_holo_index_copy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trusted, source, env = _sealed_fixture(tmp_path)
    repo = tmp_path / "repo"
    ssd = tmp_path / "ssd"
    repo.mkdir()
    ssd.mkdir()
    calls: list[tuple[list[str], dict]] = []
    monkeypatch.setattr(handshake, "__file__", str(trusted))

    def runner(command, **kwargs):
        calls.append((list(command), kwargs))
        return SimpleNamespace(returncode=0)

    error = handshake._run_full_refresh(
        repo_root=repo,
        runtime_root=tmp_path,
        ssd_path=ssd,
        environ=env,
        timeout=30.0,
        runner=runner,
    )

    assert error == ""
    assert calls[0][0][5] == str(source / "holo_index.py")
    assert str(repo / "holo_index.py") not in calls[0][0]
    assert calls[0][1]["env"][SEALED_REQUIRED_ENV] == "1"
    assert "PYTHONPATH" not in calls[0][1]["env"]


def test_owner_runner_uses_sealed_wrapper_copy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trusted, source, env = _sealed_fixture(tmp_path)
    monkeypatch.setattr(supervisor, "__file__", str(trusted))

    command = supervisor._owner_command(
        "python",
        8127,
        123,
        repo_root=tmp_path / "repo",
        environ=env,
    )

    expected = source / "scripts" / "reddog_holoindex_owner_service_once.py"
    assert command[5] == str(expected)
    assert "-m" not in command
