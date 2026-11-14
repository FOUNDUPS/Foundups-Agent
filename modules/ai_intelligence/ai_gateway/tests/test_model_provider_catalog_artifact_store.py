"""Atomicity regressions for provider catalog runtime artifacts."""

from __future__ import annotations

import asyncio
import json
import os
import stat
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src import model_provider_catalog_atomic_io
from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (
    HTTPResponse,
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_artifact_store import (
    AtomicArtifactOps,
    ProviderCatalogArtifactStore,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_atomic_io import (
    _open_windows_publication_descriptor,
    _rename_windows_descriptor,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    build_discovery_invocation,
)

FIXTURE = Path(__file__).parent / "fixtures/openrouter_models_success.json"


class _SuccessTransport:
    async def fetch(self, _request):
        return HTTPResponse(
            200,
            {"Content-Type": "application/json"},
            FIXTURE.read_bytes(),
        )


class _Clock:
    def __init__(self) -> None:
        self.value = 1_000

    def __call__(self) -> int:
        self.value += 1
        return self.value


def _discover(tmp_path: Path, ops: AtomicArtifactOps):
    return asyncio.run(
        discover_openrouter_model_catalog(
            build_discovery_invocation(mode="manual"),
            repo_root=Path.cwd(),
            runtime_root=tmp_path,
            attempt_path="attempt.json",
            candidate_path="candidate.json",
            transport=_SuccessTransport(),
            clock_ms=_Clock(),
            artifact_ops=ops,
        )
    )


def _temps(root: Path) -> list[Path]:
    return list(root.glob(".*.tmp"))


def test_partial_candidate_temp_write_preserves_lkg_and_never_completes(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate.json"
    old = b"last-known-good-byte-for-byte"
    candidate.write_bytes(old)
    writes = []

    def partial_candidate(stream, payload: bytes) -> None:
        if b"model_provider_catalog_candidate_snapshot.v1" in payload:
            stream.write(payload[:16])
            raise OSError("partial temp write")
        writes.append(json.loads(payload))
        stream.write(payload)

    result = _discover(tmp_path, AtomicArtifactOps(writer=partial_candidate))

    assert (result.receipt.outcome, result.receipt.reason) == (
        "FAILED", "candidate_write_failed"
    )
    assert candidate.read_bytes() == old
    assert _temps(tmp_path) == []
    persisted = json.loads((tmp_path / "attempt.json").read_text(encoding="utf-8"))
    assert persisted["outcome"] == "FAILED"
    assert all(item["outcome"] != "COMPLETED" for item in writes)


def test_attempt_midwrite_leaves_prior_intent_exact_and_removes_temp(
    tmp_path: Path,
) -> None:
    durable = []

    def partial_arming(stream, payload: bytes) -> None:
        item = json.loads(payload)
        if item.get("outcome") == "INDETERMINATE":
            stream.write(payload[:16])
            raise OSError("partial attempt temp write")
        durable.append(payload)
        stream.write(payload)

    result = _discover(tmp_path, AtomicArtifactOps(writer=partial_arming))

    assert result.receipt.outcome == "BLOCKED_PRECALL"
    assert result.receipt.reason == "precall_intent"
    assert (tmp_path / "attempt.json").read_bytes() == durable[0]
    assert _temps(tmp_path) == []


@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_temp_fsync_or_replace_failure_preserves_old_target(
    tmp_path: Path, failure: str
) -> None:
    target = tmp_path / "candidate.json"
    old = b"old-candidate"
    target.write_bytes(old)

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("temp fsync failed")

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("replace failed")

    ops = AtomicArtifactOps(
        fsync=fail_fsync if failure == "fsync" else os.fsync,
        replacer=fail_replace if failure == "replace" else os.replace,
    )
    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(), runtime_root=tmp_path, ops=ops
    )
    with pytest.raises(OSError):
        store.replace_text(target, "new-candidate")

    assert target.read_bytes() == old
    assert _temps(tmp_path) == []


def test_successful_atomic_replace_is_exact_and_preserves_mode(tmp_path: Path) -> None:
    target = tmp_path / "attempt.json"
    target.write_bytes(b"old")
    target.chmod(0o640)
    before_mode = stat.S_IMODE(os.lstat(target).st_mode)
    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(), runtime_root=tmp_path
    )

    replaced = store.replace_text(target, "exact-\u03c9\n")

    assert replaced == target
    assert target.read_bytes() == "exact-\u03c9\n".encode("utf-8")
    assert stat.S_IMODE(os.lstat(target).st_mode) == before_mode
    assert _temps(tmp_path) == []


@pytest.mark.parametrize("attack", ["pathname_replacement", "hard_link", "symlink"])
def test_precommit_path_attack_never_publishes_substituted_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    target = tmp_path / "candidate.json"
    old = b"last-known-good"
    target.write_bytes(old)
    original = ProviderCatalogArtifactStore._validated_temp
    attacked = False

    def attack_then_validate(self, *args):
        nonlocal attacked
        temporary = next(
            value
            for value in args
            if isinstance(value, Path) and value.suffix == ".tmp"
        )
        if not attacked:
            attacked = True
            substitute = tmp_path / f"{attack}.substitute"
            if attack == "hard_link":
                os.link(temporary, substitute)
            else:
                substitute.write_bytes(b"attacker-controlled")
                if attack == "pathname_replacement":
                    os.replace(substitute, temporary)
                else:
                    temporary.unlink()
                    try:
                        temporary.symlink_to(substitute)
                    except OSError as error:
                        pytest.skip(f"file symlink unavailable: {error}")
        return original(self, *args)

    monkeypatch.setattr(
        ProviderCatalogArtifactStore,
        "_validated_temp",
        attack_then_validate,
    )
    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(), runtime_root=tmp_path
    )

    with pytest.raises((OSError, ValueError)):
        store.replace_text(target, "trusted-new-value")

    assert attacked is True
    assert target.read_bytes() == old
    assert b"attacker-controlled" not in target.read_bytes()
    assert _temps(tmp_path) != []


def test_postvalidation_substitution_preserves_lkg_before_default_replace(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate.json"
    old = b"last-known-good"
    target.write_bytes(old)
    attempted = False
    substituted = False

    def substitute_after_validation(temporary: Path) -> None:
        nonlocal attempted, substituted
        attempted = True
        replacement = tmp_path / "postvalidation.substitute"
        replacement.write_bytes(b"attacker-controlled")
        os.replace(replacement, temporary)
        substituted = True

    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(),
        runtime_root=tmp_path,
        ops=AtomicArtifactOps(before_commit=substitute_after_validation),
    )

    with pytest.raises((OSError, ValueError)):
        store.replace_text(target, "trusted-new-value")

    assert attempted is True
    assert target.read_bytes() == old
    assert b"attacker-controlled" not in target.read_bytes()
    remaining_payloads = sorted(path.read_bytes() for path in _temps(tmp_path))
    expected_payloads = [b"attacker-controlled"] if substituted else []
    assert remaining_payloads == expected_payloads


@pytest.mark.parametrize("prior_exists", [True, False])
def test_wrong_publication_restores_exact_prior_target(
    tmp_path: Path, prior_exists: bool
) -> None:
    target = tmp_path / "candidate.json"
    old = b"last-known-good-byte-for-byte"
    if prior_exists:
        target.write_bytes(old)
        target.chmod(0o640)
        old_mode = stat.S_IMODE(os.lstat(target).st_mode)
    else:
        old_mode = None

    def publish_wrong_bytes(_source: Path, destination: Path) -> None:
        replacement = tmp_path / "wrong-publication"
        replacement.write_bytes(b"attacker-controlled")
        os.replace(replacement, destination)

    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(),
        runtime_root=tmp_path,
        ops=AtomicArtifactOps(replacer=publish_wrong_bytes),
    )

    with pytest.raises(ValueError, match="publication_identity_mismatch"):
        store.replace_text(target, "trusted-new-value")

    assert target.exists() is prior_exists
    if prior_exists:
        assert target.read_bytes() == old
        assert stat.S_IMODE(os.lstat(target).st_mode) == old_mode
    assert _temps(tmp_path) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-handle backend")
def test_windows_publish_uses_verified_object_after_final_path_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "candidate.json"
    target.write_bytes(b"last-known-good")
    real_rename = _rename_windows_descriptor
    swapped = False

    def swap_after_final_check(descriptor: int, destination: Path) -> None:
        nonlocal swapped
        source = next(iter(_temps(tmp_path)))
        second = _open_windows_publication_descriptor(source)
        displaced = tmp_path / "verified-object-displaced"
        try:
            real_rename(second, displaced)
        finally:
            os.close(second)
        source.write_bytes(b"attacker-controlled")
        swapped = True
        real_rename(descriptor, destination)

    monkeypatch.setattr(
        model_provider_catalog_atomic_io,
        "_rename_windows_descriptor",
        swap_after_final_check,
    )
    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(), runtime_root=tmp_path
    )

    store.replace_text(target, "trusted-new-value")

    assert swapped is True
    assert target.read_bytes() == b"trusted-new-value"
    assert b"attacker-controlled" not in target.read_bytes()
    assert any(
        path.read_bytes() == b"attacker-controlled" for path in _temps(tmp_path)
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-handle backend")
def test_windows_native_rename_failure_preserves_exact_lkg(tmp_path: Path) -> None:
    target = tmp_path / "candidate.json"
    old = b"last-known-good-byte-for-byte"
    target.write_bytes(old)
    blockers = []

    def block_target_delete(_temporary: Path) -> None:
        blockers.append(os.open(target, os.O_RDONLY))

    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(),
        runtime_root=tmp_path,
        ops=AtomicArtifactOps(before_commit=block_target_delete),
    )
    try:
        with pytest.raises(OSError):
            store.replace_text(target, "trusted-new-value")
    finally:
        for descriptor in blockers:
            os.close(descriptor)

    assert target.read_bytes() == old
    assert _temps(tmp_path) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-handle backend")
@pytest.mark.parametrize("prior_exists", [True, False])
def test_windows_detected_postpublication_mismatch_restores_prior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prior_exists: bool,
) -> None:
    target = tmp_path / "candidate.json"
    old = b"last-known-good-byte-for-byte"
    if prior_exists:
        target.write_bytes(old)

    def force_mismatch(_target, _verified, _payload) -> None:
        raise ValueError("forced_publication_mismatch")

    monkeypatch.setattr(
        ProviderCatalogArtifactStore,
        "_verify_published_target",
        staticmethod(force_mismatch),
    )
    store = ProviderCatalogArtifactStore.create(
        repo_root=Path.cwd(), runtime_root=tmp_path
    )

    with pytest.raises(ValueError, match="forced_publication_mismatch"):
        store.replace_text(target, "trusted-new-value")

    assert target.exists() is prior_exists
    if prior_exists:
        assert target.read_bytes() == old
    assert _temps(tmp_path) == []
