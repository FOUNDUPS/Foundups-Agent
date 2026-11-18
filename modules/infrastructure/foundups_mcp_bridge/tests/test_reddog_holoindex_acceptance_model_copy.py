"""Live-bound and Windows parent-identity attacks for acceptance model copy."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _model_copy_module():
    # Load the public guard facade first because it owns the intentionally lazy
    # model-copy re-export boundary.
    importlib.import_module(
        "modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards"
    )
    return importlib.import_module(
        "modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_model_copy"
    )


@pytest.mark.parametrize(
    "first",
    (
        "reddog_holoindex_acceptance_guards",
        "reddog_holoindex_artifact_manifest",
        "reddog_holoindex_acceptance_model_copy",
    ),
)
def test_acceptance_modules_import_in_any_order(first: str) -> None:
    package = "modules.infrastructure.foundups_mcp_bridge.src"
    script = (
        "import importlib;"
        f"importlib.import_module({package!r} + '.' + {first!r});"
        f"g=importlib.import_module({package!r} + '.reddog_holoindex_acceptance_guards');"
        f"a=importlib.import_module({package!r} + '.reddog_holoindex_artifact_manifest');"
        f"c=importlib.import_module({package!r} + '.reddog_holoindex_acceptance_model_copy');"
        "assert g.ModelCopyLimits is a.ModelCopyLimits;"
        "assert g.ExpectedArtifactFile is a.ExpectedArtifactFile;"
        "assert g.copy_model_snapshot is c.copy_model_snapshot"
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[4],
        env=environment, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr


def _model(root: Path) -> Path:
    root.mkdir()
    for name, payload in {
        "config.json": b"{}",
        "model.safetensors": b"model",
        "modules.json": b"[]",
        "tokenizer.json": b"{}",
    }.items():
        (root / name).write_bytes(payload)
    return root


def _copy_args(tmp_path: Path, *, max_file_bytes: int, max_total_bytes: int):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        ModelCopyLimits,
        create_isolated_store,
    )

    canonical = tmp_path / "canonical"
    canonical.mkdir()
    source = _model(tmp_path / "source")
    store = tmp_path / "isolated"
    proof = create_isolated_store(store, canonical_store=canonical, repo_roots=())
    destination = store / "models" / "all-MiniLM-L6-v2"
    return source, destination, {
        "store_proof": proof,
        "canonical_store": canonical,
        "repo_roots": (),
        "limits": ModelCopyLimits(
            max_files=8,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        ),
    }


def _written_sizes(destination: Path) -> list[int]:
    if not destination.exists():
        return []
    return [path.stat().st_size for path in destination.rglob("*") if path.is_file()]


def test_live_source_growth_preserves_bounded_partial_copy_after_handles_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_copy = _model_copy_module()

    source, destination, kwargs = _copy_args(
        tmp_path, max_file_bytes=8, max_total_bytes=64
    )
    original_read = model_copy.os.read
    injected = False

    def growing_read(descriptor: int, size: int) -> bytes:
        nonlocal injected
        block = original_read(descriptor, size)
        if block and not injected:
            injected = True
            return block + b"growth-over-bound"
        return block

    monkeypatch.setattr(model_copy.os, "read", growing_read)
    with pytest.raises(model_copy.AcceptanceGuardError):
        model_copy.copy_model_snapshot(source, destination, **kwargs)
    assert injected is True
    assert all(size <= 8 for size in _written_sizes(destination))
    assert destination.is_dir()
    partials = [path for path in destination.rglob("*") if path.is_file()]
    assert partials
    moved = partials[0].with_suffix(".preserved")
    partials[0].rename(moved)
    moved.rename(partials[0])


def test_live_source_growth_preserves_partial_tree_within_total_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_copy = _model_copy_module()

    source, destination, kwargs = _copy_args(
        tmp_path, max_file_bytes=64, max_total_bytes=12
    )
    original_read = model_copy.os.read
    injected = False

    def growing_read(descriptor: int, size: int) -> bytes:
        nonlocal injected
        block = original_read(descriptor, size)
        if block and not injected:
            injected = True
            return block + b"grow"
        return block

    monkeypatch.setattr(model_copy.os, "read", growing_read)
    with pytest.raises(model_copy.AcceptanceGuardError):
        model_copy.copy_model_snapshot(source, destination, **kwargs)
    assert injected is True
    assert sum(_written_sizes(destination)) <= 12
    assert destination.is_dir()


def test_multi_link_source_file_is_rejected_before_copy(tmp_path: Path) -> None:
    model_copy = _model_copy_module()

    source, destination, kwargs = _copy_args(
        tmp_path, max_file_bytes=64, max_total_bytes=64
    )
    os.link(source / "config.json", source / "config-hardlink.json")

    with pytest.raises(
        model_copy.AcceptanceGuardError, match="MODEL_SPECIAL_FILE_REJECTED"
    ):
        model_copy.copy_model_snapshot(source, destination, **kwargs)
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-pinning contract")
def test_windows_source_parent_swap_with_same_file_identities_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_copy = _model_copy_module()

    source, destination, kwargs = _copy_args(
        tmp_path, max_file_bytes=64, max_total_bytes=64
    )
    moved = tmp_path / "source-moved"
    swapped = False

    def swap_before_open(path: Path) -> None:
        nonlocal swapped
        if not swapped and path == source:
            swapped = True
            source.rename(moved)
            source.mkdir()
            for prior in moved.iterdir():
                os.link(prior, source / prior.name)

    monkeypatch.setattr(
        model_copy, "_before_windows_source_component_open", swap_before_open
    )
    with pytest.raises(model_copy.AcceptanceGuardError):
        model_copy.copy_model_snapshot(source, destination, **kwargs)
    assert swapped is True


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-pinning contract")
def test_windows_destination_parent_swap_before_create_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_copy = _model_copy_module()

    source, destination, kwargs = _copy_args(
        tmp_path, max_file_bytes=64, max_total_bytes=64
    )
    moved = destination.parent / "destination-moved"
    swapped = False

    def swap_before_open(path: Path) -> None:
        nonlocal swapped
        if not swapped and path == destination:
            swapped = True
            destination.rename(moved)
            destination.mkdir()

    monkeypatch.setattr(
        model_copy, "_before_windows_destination_component_open", swap_before_open
    )
    with pytest.raises(model_copy.AcceptanceGuardError):
        model_copy.copy_model_snapshot(source, destination, **kwargs)
    assert swapped is True
    assert destination.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="Windows native fail-closed contract")
def test_windows_native_directory_open_failure_is_guarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_copy = _model_copy_module()

    source, destination, kwargs = _copy_args(
        tmp_path, max_file_bytes=64, max_total_bytes=64
    )

    def unavailable(*_args, **_kwargs):
        raise OSError("native API unavailable")

    monkeypatch.setattr(model_copy, "open_windows_directory_lease", unavailable)
    with pytest.raises(model_copy.AcceptanceGuardError):
        model_copy.copy_model_snapshot(source, destination, **kwargs)
    assert not destination.exists()


def test_windows_copy_surface_exports_no_delete_api() -> None:
    model_copy = _model_copy_module()
    windows = importlib.import_module(
        "modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_windows"
    )

    forbidden = {
        "delete_windows_file_descriptor", "delete_windows_directory_lease",
        "_mark_delete", "_FileDispositionInfo", "_FILE_DISPOSITION_INFO_CLASS",
    }
    assert forbidden.isdisjoint(vars(model_copy))
    assert forbidden.isdisjoint(vars(windows))
    assert forbidden.isdisjoint(set(windows.__all__))
    combined = Path(model_copy.__file__).read_text(encoding="utf-8") + Path(
        windows.__file__
    ).read_text(encoding="utf-8")
    assert all(token not in combined for token in forbidden)
