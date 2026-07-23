"""Atomicity regressions for provider catalog runtime artifacts."""

from __future__ import annotations

import asyncio
import json
import os
import stat
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (
    HTTPResponse,
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_artifact_store import (
    AtomicArtifactOps,
    ProviderCatalogArtifactStore,
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
