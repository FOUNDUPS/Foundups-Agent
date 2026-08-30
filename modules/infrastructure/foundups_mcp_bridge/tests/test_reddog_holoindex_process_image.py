"""Process-image authority contracts for isolated HoloIndex acceptance."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


def _executable_file(path: Path, payload: bytes = b"python-image") -> Path:
    path.write_bytes(payload)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_actual_process_image_is_proven_and_revalidates() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        prove_current_process_executable,
        revalidate_process_executable,
    )

    proof = prove_current_process_executable()
    assert proof.path.is_absolute()
    assert proof.path.is_file()
    assert revalidate_process_executable(proof) == proof.path


def test_launch_capability_is_live_then_closes() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        hold_process_executable_for_launch,
        prove_current_process_executable,
    )

    proof = prove_current_process_executable()
    descriptor = -1
    with hold_process_executable_for_launch(proof) as capability:
        descriptor = capability.descriptor
        assert os.fstat(descriptor).st_ino == proof.identity[1]
        if os.name == "nt":
            assert capability.launch_path == proof.path
            assert capability.pass_fds == ()
        else:
            assert capability.launch_path == Path(f"/proc/self/fd/{descriptor}")
            assert capability.pass_fds == (descriptor,)
    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_launch_capability_closes_on_error() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        hold_process_executable_for_launch,
        prove_current_process_executable,
    )

    class MarkerError(RuntimeError):
        pass

    descriptor = -1
    with pytest.raises(MarkerError):
        with hold_process_executable_for_launch(
            prove_current_process_executable()
        ) as capability:
            descriptor = capability.descriptor
            assert os.fstat(descriptor)
            raise MarkerError
    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_launch_capability_runs_actual_child() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        hold_process_executable_for_launch,
        prove_current_process_executable,
    )

    with hold_process_executable_for_launch(
        prove_current_process_executable()
    ) as capability:
        kwargs = {"pass_fds": capability.pass_fds} if capability.pass_fds else {}
        completed = subprocess.run(  # nosec B603 - proven interpreter capability.
            [
                str(capability.launch_path), "-I", "-S", "-B", "-c",
                "print('capability-ok')",
            ],
            check=False,
            capture_output=True,
            timeout=10,
            text=True,
            **kwargs,
        )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "capability-ok"


def test_mutable_sys_executable_fields_cannot_select_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        prove_current_process_executable,
    )

    hostile = _executable_file(tmp_path / ("cmd.exe" if os.name == "nt" else "cmd"))
    expected = prove_current_process_executable()
    monkeypatch.setattr(sys, "_base_executable", str(hostile))
    monkeypatch.setattr(sys, "executable", str(hostile))
    assert prove_current_process_executable().path == expected.path


@pytest.mark.parametrize("defect", ["missing", "alias", "symlink", "hardlink"])
def test_untrusted_process_image_path_is_rejected(
    tmp_path: Path, defect: str,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        ProcessExecutableProofError,
        prove_process_executable_path,
    )

    target = _executable_file(tmp_path / ("python.exe" if os.name == "nt" else "python"))
    supplied = target
    if defect == "missing":
        supplied = tmp_path / "missing.exe"
    elif defect == "alias":
        nested = tmp_path / "nested"
        nested.mkdir()
        supplied = nested / ".." / target.name
    elif defect == "symlink":
        supplied = tmp_path / "python-link.exe"
        try:
            supplied.symlink_to(target)
        except OSError:
            pytest.skip("file symlink unavailable")
    elif defect == "hardlink":
        supplied = tmp_path / "python-hardlink.exe"
        try:
            os.link(target, supplied)
        except OSError:
            pytest.skip("hardlink unavailable")
    with pytest.raises(ProcessExecutableProofError):
        prove_process_executable_path(supplied)


def test_process_image_identity_replacement_fails_revalidation(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        ProcessExecutableProofError,
        prove_process_executable_path,
        revalidate_process_executable,
    )

    target = _executable_file(tmp_path / ("python.exe" if os.name == "nt" else "python"))
    proof = prove_process_executable_path(target)
    target.unlink()
    _executable_file(target, b"replacement-image-with-different-size")
    with pytest.raises(ProcessExecutableProofError):
        revalidate_process_executable(proof)


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-case path contract")
@pytest.mark.parametrize("alias_component", ["directory", "file"])
def test_windows_case_only_process_image_alias_is_rejected(
    tmp_path: Path, alias_component: str
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        ProcessExecutableProofError,
        prove_process_executable_path,
    )

    exact_parent = tmp_path / "RuntimeRoot"
    exact_parent.mkdir()
    exact = _executable_file(exact_parent / "PyThOn.ExE")
    if alias_component == "directory":
        case_only_alias = tmp_path / "runtimeroot" / exact.name
    else:
        case_only_alias = exact.with_name("python.exe")
    assert str(case_only_alias) != str(exact)
    assert case_only_alias.exists()
    with pytest.raises(ProcessExecutableProofError):
        prove_process_executable_path(case_only_alias)


def test_junction_or_reparse_signal_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_process_image as process_image,
    )

    target = _executable_file(tmp_path / ("python.exe" if os.name == "nt" else "python"))
    real = process_image._is_link_or_reparse
    monkeypatch.setattr(
        process_image, "_is_link_or_reparse",
        lambda path, metadata: path == target or real(path, metadata),
    )
    with pytest.raises(process_image.ProcessExecutableProofError):
        process_image.prove_process_executable_path(target)


def test_missing_or_ambiguous_process_image_proof_rejects() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
        ProcessExecutableProofError,
        revalidate_process_executable,
    )

    for value in (None, (), object()):
        with pytest.raises(ProcessExecutableProofError):
            revalidate_process_executable(value)
