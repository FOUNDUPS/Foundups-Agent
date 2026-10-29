"""Opt-in physical repeatability gate for the reviewed O:/E: packaging wheel."""

from __future__ import annotations

import gc
import base64
import csv
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
import time
import zipfile

import psutil
import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
    BuilderPackagingSourceContractError,
    BuilderPackagingSourceLimits,
    absolute_builder_packaging_source_store_path,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_materializer import (
    BuilderPackagingSourceMaterializationError,
    _BuilderPackagingSourceDependencies,
    _materialize_builder_packaging_source_bytes_for_test,
    materialize_pinned_builder_packaging_source,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_writer_windows import (
    write_builder_packaging_source_windows,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_wheel import (
    BuilderPackagingWheelError,
    PACKAGING_26_WHEEL_SHA256,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_packaging_source_topology_windows as source_topology,
    reddog_holoindex_query_runtime_builder_packaging_source_verifier as source_verifier,
    reddog_holoindex_query_runtime_builder_packaging_wheel as wheel_module,
)


pytestmark = pytest.mark.integration
_REPEAT_REUSES = 200


def test_opt_in_physical_source_generation_repeatability_and_resources() -> None:
    if os.environ.get("REDDOG_RUN_PACKAGING_26_SOURCE_SCALE") != "1":
        pytest.skip("set REDDOG_RUN_PACKAGING_26_SOURCE_SCALE=1 for this physical gate")
    wheel_path = _reviewed_wheel_path()
    before_digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    assert before_digest == PACKAGING_26_WHEEL_SHA256
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-scale-", dir=parent) as raw:
        root = Path(raw).resolve()
        assert root.parent == parent and root.drive.upper() == "O:"
        canonical, repo = root / "canonical", Path("O:/Foundups-Agent").resolve()
        canonical.mkdir()
        source_store = root / "source-store"
        first = _materialize(wheel_path, source_store, canonical, repo)
        process = psutil.Process()
        before_handles, before_rss = process.num_handles(), process.memory_info().rss
        started = time.perf_counter()
        reuses = tuple(
            _materialize(wheel_path, source_store, canonical, repo)
            for _index in range(_REPEAT_REUSES)
        )
        elapsed = time.perf_counter() - started
        gc.collect()
        _assert_scale_results(
            first, reuses, source_store, before_handles, before_rss,
            process, elapsed,
        )
    assert hashlib.sha256(wheel_path.read_bytes()).hexdigest() == before_digest


def _reviewed_wheel_path() -> Path:
    configured = os.environ.get("REDDOG_PACKAGING_26_WHEEL", "")
    if configured:
        path = Path(configured)
    else:
        path = Path(
            "O:/RedDog-Builder-Artifacts/packaging/26.0/"
            f"{PACKAGING_26_WHEEL_SHA256}/packaging-26.0-py3-none-any.whl"
        )
    assert path.is_absolute() and path.drive.rstrip(":").upper() in {"O", "E"}
    assert path.is_file()
    return path


def _materialize(wheel_path: Path, source_store: Path, canonical: Path, repo: Path):
    return materialize_pinned_builder_packaging_source(
        wheel_path=wheel_path, wheel_store_root=wheel_path.parent,
        source_store_root=source_store, canonical_store=canonical,
        repo_roots=(repo,),
    )


def _assert_scale_results(
    first, reuses, source_store: Path, before_handles: int, before_rss: int,
    process: psutil.Process, elapsed: float,
) -> None:
    assert first.reused_existing_generation is False
    assert all(result.reused_existing_generation is True for result in reuses)
    expected_reuse = replace(
        first.binding, source_lease_held_through_publication=False,
    )
    assert all(result.binding == expected_reuse for result in reuses)
    assert len(tuple(source_store.iterdir())) == 1
    assert first.binding.descriptor_path.name == BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME
    assert not (first.binding.generation_root / "dependency-runtime").exists()
    assert process.num_handles() - before_handles < 8
    assert process.memory_info().rss - before_rss < 24 * 1024 * 1024
    assert elapsed < 120.0


def test_synthetic_sibling_scale_retains_handles_by_depth_not_file_count() -> None:
    payload = _many_member_wheel(100)
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    observed = []

    def capture(**kwargs):
        result = write_builder_packaging_source_windows(**kwargs)
        observed.append(result)
        return result

    with tempfile.TemporaryDirectory(prefix="reddog-source-handles-", dir=parent) as raw:
        root = Path(raw).resolve()
        repo, canonical = root / "repo", root / "canonical"
        (repo / ".git").mkdir(parents=True)
        canonical.mkdir()
        result = _materialize_builder_packaging_source_bytes_for_test(
            wheel_bytes=payload, source_store_root=root / "source-store",
            canonical_store=canonical, repo_roots=(repo,),
            dependencies=_BuilderPackagingSourceDependencies(write_source=capture),
        )
    assert result.binding.member_count == 105
    assert observed[0].written_member_count == 105
    assert observed[0].peak_retained_leases <= 4


def test_source_store_volume_gate_rejects_c_before_mutation() -> None:
    with pytest.raises(BuilderPackagingSourceContractError, match="STORE_VOLUME_INVALID"):
        absolute_builder_packaging_source_store_path("C:/tmp/reddog-source-forbidden")
    with pytest.raises(source_verifier.BuilderPackagingSourceVerificationError, match="STORE_VOLUME_INVALID"):
        source_verifier.verify_builder_packaging_source_generation(
            source_store_root="C:/tmp/reddog-source-forbidden",
            generation_root="C:/tmp/reddog-source-forbidden/generation",
            canonical_store="O:/tmp", repo_roots=("O:/Foundups-Agent",),
        )


@pytest.mark.parametrize("mutation", ["wheel_ads", "wheel_hardlink", "wheel_reparse", "member_case_alias"])
def test_synthetic_generation_rejects_windows_topology_aliases(monkeypatch, mutation: str) -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-hostile-", dir=parent) as raw:
        root, repo, canonical, source_store, result = _synthetic_generation(Path(raw), _many_member_wheel(1))
        wheel_path = result.binding.wheel_path
        if mutation == "wheel_ads":
            Path(str(wheel_path) + ":hidden").write_bytes(b"hidden")
        elif mutation == "wheel_hardlink":
            os.link(wheel_path, root / "wheel-alias.whl")
        elif mutation == "wheel_reparse":
            backup = root / "wheel-target.whl"
            os.replace(wheel_path, backup)
            try:
                os.symlink(backup, wheel_path)
            except OSError:
                os.replace(backup, wheel_path)
                original = source_topology._is_link_or_reparse
                monkeypatch.setattr(
                    source_topology, "_is_link_or_reparse",
                    lambda path, metadata: path == wheel_path or original(path, metadata),
                )
        else:
            member = result.binding.site_packages_root / "packaging/module_000.py"
            temporary = member.with_name("rename.tmp")
            os.replace(member, temporary)
            os.replace(temporary, member.with_name("Module_000.py"))
        with pytest.raises(source_verifier.BuilderPackagingSourceVerificationError):
            _verify_synthetic(repo, canonical, source_store, result)


def test_unicode_member_is_rejected_before_source_store_mutation() -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-unicode-", dir=parent) as raw:
        root = Path(raw).resolve()
        payload = _many_member_wheel(1, unicode_member=True)
        repo, canonical, source_store = root / "repo", root / "canonical", root / "source-store"
        (repo / ".git").mkdir(parents=True)
        canonical.mkdir()
        with pytest.raises(BuilderPackagingWheelError, match="STRICT_WHEEL_FLAGS_INVALID"):
            _materialize_builder_packaging_source_bytes_for_test(
                wheel_bytes=payload, source_store_root=source_store,
                canonical_store=canonical, repo_roots=(repo,),
            )
        assert not source_store.exists()


def test_valid_payload_bounds_and_token_fail_before_store_mutation() -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-premutation-", dir=parent) as raw:
        root = Path(raw).resolve()
        repo, canonical, source_store = root / "repo", root / "canonical", root / "source-store"
        (repo / ".git").mkdir(parents=True)
        canonical.mkdir()
        with pytest.raises(Exception, match="BOUND_INVALID"):
            _materialize_builder_packaging_source_bytes_for_test(
                wheel_bytes=_many_member_wheel(1), source_store_root=source_store,
                canonical_store=canonical, repo_roots=(repo,),
                limits=BuilderPackagingSourceLimits(max_files=1),
            )
        assert not source_store.exists()
        with pytest.raises(Exception, match="TOKEN_INVALID"):
            _materialize_builder_packaging_source_bytes_for_test(
                wheel_bytes=_many_member_wheel(1), source_store_root=source_store,
                canonical_store=canonical, repo_roots=(repo,),
                dependencies=_BuilderPackagingSourceDependencies(token=lambda: "../escape"),
            )
        assert not source_store.exists()


def test_public_error_boundary_never_exposes_os_path() -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-error-", dir=parent) as raw:
        root = Path(raw).resolve()
        repo, canonical = root / "repo", root / "canonical"
        (repo / ".git").mkdir(parents=True)
        canonical.mkdir()

        def fail_with_path(**_kwargs):
            raise OSError("O:/private/source/path")

        with pytest.raises(BuilderPackagingSourceMaterializationError) as captured:
            _materialize_builder_packaging_source_bytes_for_test(
                wheel_bytes=_many_member_wheel(1),
                source_store_root=root / "source-store",
                canonical_store=canonical, repo_roots=(repo,),
                dependencies=_BuilderPackagingSourceDependencies(write_source=fail_with_path),
            )
        assert str(captured.value) == "BUILDER_PACKAGING_SOURCE_MATERIALIZATION_FAILED"


@pytest.mark.parametrize("mutation", ["descriptor", "inventory", "wheel", "member"])
def test_second_complete_pass_rejects_interpass_mutation(monkeypatch, mutation: str) -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-two-pass-", dir=parent) as raw:
        root, repo, canonical, source_store, result = _synthetic_generation(Path(raw), _many_member_wheel(1))
        targets = {
            "descriptor": result.binding.descriptor_path,
            "inventory": result.binding.generation_root / "reddog_builder_packaging_source_inventory.json",
            "wheel": result.binding.wheel_path,
            "member": result.binding.site_packages_root / "packaging/module_000.py",
        }
        original = source_verifier._verify_contents
        calls = 0

        def mutate_after_first(*args, **kwargs):
            nonlocal calls
            binding = original(*args, **kwargs)
            calls += 1
            if calls == 1:
                targets[mutation].write_bytes(b"corrupt")
            return binding

        monkeypatch.setattr(source_verifier, "_verify_contents", mutate_after_first)
        with pytest.raises(source_verifier.BuilderPackagingSourceVerificationError):
            _verify_synthetic(repo, canonical, source_store, result)
        assert calls == 1


@pytest.mark.parametrize("mutation", ["descriptor", "inventory", "wheel", "member"])
def test_terminal_retained_file_leases_deny_tail_mutation(monkeypatch, mutation: str) -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-tail-file-", dir=parent) as raw:
        root, repo, canonical, source_store, result = _synthetic_generation(Path(raw), _many_member_wheel(1))
        targets = {
            "descriptor": result.binding.descriptor_path,
            "inventory": result.binding.generation_root / "reddog_builder_packaging_source_inventory.json",
            "wheel": result.binding.wheel_path,
            "member": result.binding.site_packages_root / "packaging/module_000.py",
        }
        original = source_verifier._verify_contents
        calls = 0

        def attempt_after_second(*args, **kwargs):
            nonlocal calls
            binding = original(*args, **kwargs)
            calls += 1
            if calls == 2:
                with pytest.raises(PermissionError):
                    targets[mutation].write_bytes(b"corrupt")
            return binding

        monkeypatch.setattr(source_verifier, "_verify_contents", attempt_after_second)
        verified = _verify_synthetic(repo, canonical, source_store, result)
        assert verified == result.binding
        assert calls == 2


def test_terminal_topology_reproof_rejects_tail_extra_file(monkeypatch) -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-tail-extra-", dir=parent) as raw:
        root, repo, canonical, source_store, result = _synthetic_generation(Path(raw), _many_member_wheel(1))
        original = source_verifier._verify_contents
        calls = 0

        def add_after_second(*args, **kwargs):
            nonlocal calls
            binding = original(*args, **kwargs)
            calls += 1
            if calls == 2:
                (result.binding.site_packages_root / "tail-extra.py").write_bytes(b"extra")
            return binding

        monkeypatch.setattr(source_verifier, "_verify_contents", add_after_second)
        with pytest.raises(
            source_verifier.BuilderPackagingSourceVerificationError,
            match="VERIFICATION_CHANGED",
        ):
            _verify_synthetic(repo, canonical, source_store, result)
        assert calls == 2


def test_source_lease_spans_every_target_proof_and_scope_exit(monkeypatch) -> None:
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-final-proof-", dir=parent) as raw:
        root = Path(raw).resolve()
        repo, canonical, wheel_root = root / "repo", root / "canonical", root / "wheel"
        (repo / ".git").mkdir(parents=True)
        canonical.mkdir()
        wheel_root.mkdir()
        payload = _many_member_wheel(1)
        wheel_path = wheel_root / "packaging-26.0-py3-none-any.whl"
        wheel_path.write_bytes(payload)
        monkeypatch.setattr(wheel_module, "PACKAGING_26_WHEEL_SIZE", len(payload))
        monkeypatch.setattr(wheel_module, "PACKAGING_26_WHEEL_SHA256", hashlib.sha256(payload).hexdigest())
        original_verify = source_verifier.verify_builder_packaging_source_generation
        original_reproof = wheel_module._final_reproof
        target_proofs = scope_reproofs = 0

        def verify_with_denied_source_write(**kwargs):
            nonlocal target_proofs
            target_proofs += 1
            with pytest.raises(PermissionError):
                wheel_path.write_bytes(payload)
            return original_verify(**kwargs)

        def count_reproof(*args, **kwargs):
            nonlocal scope_reproofs
            scope_reproofs += 1
            return original_reproof(*args, **kwargs)

        monkeypatch.setattr(source_verifier, "verify_builder_packaging_source_generation", verify_with_denied_source_write)
        monkeypatch.setattr(wheel_module, "_final_reproof", count_reproof)
        materialize_pinned_builder_packaging_source(
            wheel_path=wheel_path, wheel_store_root=wheel_root,
            source_store_root=root / "source-store", canonical_store=canonical,
            repo_roots=(repo,),
        )
        assert target_proofs == 1
        assert scope_reproofs == 3


def _synthetic_generation(root: Path, payload: bytes):
    repo, canonical, source_store = root / "repo", root / "canonical", root / "source-store"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    result = _materialize_builder_packaging_source_bytes_for_test(
        wheel_bytes=payload, source_store_root=source_store,
        canonical_store=canonical, repo_roots=(repo,),
    )
    return root, repo, canonical, source_store, result


def _verify_synthetic(repo: Path, canonical: Path, source_store: Path, result):
    return source_verifier._verify_builder_packaging_source_generation_for_test(
        source_store_root=source_store, generation_root=result.binding.generation_root,
        expected_generation_id=result.binding.generation_id,
        canonical_store=canonical, repo_roots=(repo,),
        limits=BuilderPackagingSourceLimits(),
    )


def _many_member_wheel(count: int, *, unicode_member: bool = False) -> bytes:
    files = [(f"packaging/module_{index:03d}.py", b"VALUE = 1\n") for index in range(count)]
    if unicode_member:
        files.append(("packaging/café.py", b"CAFE = True\n"))
    files.extend((
        ("packaging/__init__.py", b'__version__ = "26.0"\n'),
        ("packaging/version.py", b"class Version: pass\n"),
        ("packaging-26.0.dist-info/METADATA", b"Name: packaging\nVersion: 26.0\n"),
        ("packaging-26.0.dist-info/WHEEL", b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"),
    ))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name, body in files:
        digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode("ascii").rstrip("=")
        writer.writerow((name, "sha256=" + digest, len(body)))
    writer.writerow(("packaging-26.0.dist-info/RECORD", "", ""))
    members = [*files, ("packaging-26.0.dist-info/RECORD", output.getvalue().encode())]
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in members:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type, info.create_system = zipfile.ZIP_DEFLATED, 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, body)
    return archive_bytes.getvalue()
