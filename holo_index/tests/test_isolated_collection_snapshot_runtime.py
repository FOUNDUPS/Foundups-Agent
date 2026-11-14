"""Trusted-runtime contracts for the isolated collection snapshot child."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import holo_index.isolated_collection_snapshot_probe as probe
from holo_index.tests.test_isolated_collection_snapshot_probe import _fixture
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
    prove_current_process_executable,
    prove_process_executable_path,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_process_image as process_image,
)


def _runtime(tmp_path: Path) -> Path:
    path = tmp_path / "runtime" / ".venv" / "Lib" / "site-packages"
    path.mkdir(parents=True)
    return path


def _executable(path: Path, payload: bytes = b"verified-python-image") -> Path:
    path.write_bytes(payload)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _completed(receipt) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=0,
        stdout=json.dumps({
            "schema_version": probe.SCHEMA_VERSION,
            "ok": True,
            "generation_id": receipt.generation_id,
            "mismatched_collections": [],
            "error": "",
        }),
        stderr="",
    )


def test_launcher_uses_base_python_candidate_cwd_exact_runtime_and_scrubbed_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    runtime = _runtime(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    observed = {}
    monkeypatch.setenv("PYTHONHOME", "hostile")
    monkeypatch.setenv("PYTHONPATH", "hostile")
    monkeypatch.setenv("PYTHONSTARTUP", "hostile-startup")
    monkeypatch.setenv("PYTHONUSERBASE", "hostile-userbase")
    monkeypatch.setenv("PYTHONINSPECT", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-secret")
    executable_proof = prove_current_process_executable()
    hostile = tmp_path / "cmd.exe"
    hostile.write_bytes(b"not the process image")
    monkeypatch.setattr(sys, "_base_executable", str(hostile))
    monkeypatch.setattr(sys, "executable", str(hostile))

    def run(command, **kwargs):
        observed.update(command=command, **kwargs)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "schema_version": probe.SCHEMA_VERSION,
                "ok": True,
                "generation_id": receipt.generation_id,
                "mismatched_collections": [],
                "error": "",
            }),
            stderr="",
        )

    monkeypatch.setattr(probe.subprocess, "run", run)
    assert probe.verify_collection_snapshots_isolated(
        receipt, ssd_path=tmp_path / "ssd", repo_root=repo,
        runtime_site_packages=(str(runtime),),
        base_executable_proof=executable_proof,
    ) == []
    assert observed["command"] == [
        str(executable_proof.path),
        "-S", "-B", "-m", "holo_index.isolated_collection_snapshot_probe",
        "--ssd", str((tmp_path / "ssd").resolve()),
        "--runtime-site-packages", str(runtime.resolve()),
        "--repo-root", str(repo.resolve()),
    ]
    assert observed["cwd"] == str(repo.resolve())
    assert observed["env"]["PYTHONPATH"] == str(runtime.resolve())
    assert observed["env"]["PYTHONNOUSERSITE"] == "1"
    assert "PYTHONHOME" not in observed["env"]
    assert "PYTHONSTARTUP" not in observed["env"]
    assert "PYTHONUSERBASE" not in observed["env"]
    assert "PYTHONINSPECT" not in observed["env"]
    assert "OPENAI_API_KEY" not in observed["env"]


def test_exact_trusted_chroma_origin_and_version_open_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path)
    origin = runtime / "chromadb" / "__init__.py"
    origin.parent.mkdir()
    origin.write_text("", encoding="utf-8")
    calls: list[dict[str, object]] = []
    monkeypatch.setitem(
        sys.modules, "chromadb",
        SimpleNamespace(
            __version__="1.5.5", __file__=str(origin),
            PersistentClient=lambda **kwargs: calls.append(kwargs) or "client",
        ),
    )
    monkeypatch.setitem(
        sys.modules, "chromadb.config",
        SimpleNamespace(Settings=lambda **kwargs: kwargs),
    )
    assert probe._default_client_factory(tmp_path / "ssd", runtime) == "client"
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["missing", "ambiguous", "unrelated", "link"])
def test_invalid_runtime_dependency_fails_before_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    runtime = _runtime(tmp_path)
    values = (str(runtime),)
    if kind == "missing":
        values = (str(tmp_path / "missing"),)
    elif kind == "ambiguous":
        values = (str(runtime), str(runtime))
    elif kind == "unrelated":
        other = tmp_path / "other"
        other.mkdir()
        values = (str(other),)
    elif kind == "link":
        link = tmp_path / "runtime-link"
        try:
            link.symlink_to(runtime, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlink unavailable")
        values = (str(link),)
    monkeypatch.setattr(
        probe.subprocess, "run",
        lambda *_args, **_kwargs: pytest.fail("child must not spawn"),
    )
    executable_proof = prove_current_process_executable()
    with pytest.raises(probe.IsolatedSnapshotProbeError, match="RUNTIME_DEPENDENCY_UNAVAILABLE"):
        probe.verify_collection_snapshots_isolated(
            receipt, ssd_path=tmp_path / "ssd", repo_root=tmp_path / "repo",
            runtime_site_packages=values,
            base_executable_proof=executable_proof,
        )


def test_missing_or_changed_executable_proof_fails_before_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        probe.subprocess, "run",
        lambda *_args, **_kwargs: pytest.fail("child must not spawn"),
    )
    with pytest.raises(probe.IsolatedSnapshotProbeError):
        probe.verify_collection_snapshots_isolated(
            receipt, ssd_path=tmp_path / "ssd", repo_root=tmp_path / "repo",
            runtime_site_packages=(str(runtime),), base_executable_proof=None,
        )

    executable = _executable(tmp_path / "python-proof.exe")
    proof = prove_process_executable_path(executable)
    executable.unlink()
    _executable(executable, b"replacement-python-image")
    with pytest.raises(probe.IsolatedSnapshotProbeError):
        probe.verify_collection_snapshots_isolated(
            receipt, ssd_path=tmp_path / "ssd", repo_root=tmp_path / "repo",
            runtime_site_packages=(str(runtime),), base_executable_proof=proof,
        )


def test_runner_retains_exact_executable_capability_across_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    runtime = _runtime(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    original_payload = b"verified-python-image"
    replacement_payload = b"replacement-python-image"
    executable = _executable(tmp_path / "python-capability.exe", original_payload)
    replacement = _executable(tmp_path / "replacement.exe", replacement_payload)
    executable_proof = prove_process_executable_path(executable)
    descriptors: list[int] = []
    original_open = process_image._open_verified

    def recording_open(*args, **kwargs):
        descriptor, parent = original_open(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor, parent

    monkeypatch.setattr(process_image, "_open_verified", recording_open)

    def run(command, **kwargs):
        descriptor = descriptors[-1]
        assert os.fstat(descriptor).st_ino == executable_proof.identity[1]
        if os.name == "nt":
            assert command[0] == str(executable)
            assert "pass_fds" not in kwargs
            with pytest.raises(OSError):
                os.replace(replacement, executable)
        else:
            assert command[0] == f"/proc/self/fd/{descriptor}"
            assert kwargs["pass_fds"] == (descriptor,)
            os.replace(replacement, executable)
            assert Path(command[0]).read_bytes() == original_payload
            assert executable.read_bytes() == replacement_payload
        return _completed(receipt)

    output = probe._run_isolated_probe(
        receipt,
        tmp_path / "ssd",
        repo,
        5.0,
        (str(runtime),),
        executable_proof,
        runner=run,
    )
    assert json.loads(output)["ok"] is True
    with pytest.raises(OSError):
        os.fstat(descriptors[-1])
    if os.name == "nt":
        os.replace(replacement, executable)
        assert executable.read_bytes() == replacement_payload


def test_runner_error_closes_executable_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    runtime = _runtime(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    executable = _executable(tmp_path / "python-error.exe")
    executable_proof = prove_process_executable_path(executable)
    descriptors: list[int] = []
    original_open = process_image._open_verified

    def recording_open(*args, **kwargs):
        descriptor, parent = original_open(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor, parent

    monkeypatch.setattr(process_image, "_open_verified", recording_open)

    def failing_runner(_command, **_kwargs):
        assert os.fstat(descriptors[-1])
        raise OSError("runner failed")

    with pytest.raises(
        probe.IsolatedSnapshotProbeError, match="ISOLATED_PROBE_PROCESS_FAILED"
    ):
        probe._run_isolated_probe(
            receipt,
            tmp_path / "ssd",
            repo,
            5.0,
            (str(runtime),),
            executable_proof,
            runner=failing_runner,
        )
    with pytest.raises(OSError):
        os.fstat(descriptors[-1])


def test_child_wrong_chroma_version_is_generation_bound_and_never_opens_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    runtime = _runtime(tmp_path)
    fake_chroma = runtime / "chromadb" / "__init__.py"
    fake_chroma.parent.mkdir()
    fake_chroma.write_text("", encoding="utf-8")
    monkeypatch.setitem(
        sys.modules, "chromadb",
        SimpleNamespace(
            __version__="1.3.0", __file__=str(fake_chroma),
            PersistentClient=lambda **_kwargs: pytest.fail("store must not open"),
        ),
    )
    monkeypatch.setitem(
        sys.modules, "chromadb.config",
        SimpleNamespace(Settings=lambda **kwargs: kwargs),
    )
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=SimpleNamespace(
        read=lambda _limit: receipt.to_json().encode("utf-8")
    )))
    output: list[str] = []
    monkeypatch.setattr(sys, "stdout", SimpleNamespace(write=output.append))
    assert probe.main([
        "--ssd", str(tmp_path / "ssd"),
        "--runtime-site-packages", str(runtime),
        "--repo-root", str(Path(probe.__file__).resolve().parents[1]),
    ]) == 0
    response = json.loads("".join(output))
    assert response["error"] == "UNSUPPORTED_CHROMADB_VERSION"
    assert response["generation_id"] == receipt.generation_id
