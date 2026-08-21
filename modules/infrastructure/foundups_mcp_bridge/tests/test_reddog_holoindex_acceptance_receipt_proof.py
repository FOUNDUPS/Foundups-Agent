"""Filesystem-adversary contracts for post-activation receipt proof."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from holo_index.freshness_receipt import freshness_receipt_path
from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    _receipt,
)


SHA = "a" * 40


def _write_receipt(store: Path, repo: Path) -> tuple[Path, str, str]:
    path = freshness_receipt_path(store)
    path.parent.mkdir(parents=True)
    payload = json.dumps(
        _receipt(repo_root=repo, ssd_path=store, sha=SHA),
        sort_keys=True,
    ).encode("utf-8")
    path.write_bytes(payload)
    return path, "sha256:" + hashlib.sha256(payload).hexdigest(), json.loads(payload)["generation_id"]


def _open(path: Path, store: Path, repo: Path, digest: str, generation: str, **overrides):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_receipt_proof import (
        open_freshness_receipt_proof,
    )

    values = {
        "path": path,
        "allowed_root": store,
        "expected_ssd_path": store,
        "expected_repo_root": repo,
        "expected_repo_head_sha": SHA,
        "expected_generation_id": generation,
        "expected_receipt_digest": digest,
        "max_bytes": 256 * 1024,
    }
    values.update(overrides)
    return open_freshness_receipt_proof(**values)


def test_exact_receipt_is_descriptor_bound_and_revalidates(tmp_path: Path) -> None:
    store, repo = tmp_path / "store", tmp_path / "repo"
    repo.mkdir()
    path, digest, generation = _write_receipt(store, repo)
    with _open(path, store, repo, digest, generation) as proof:
        assert proof.receipt.generation_id == generation
        assert proof.digest == digest
        proof.revalidate()


@pytest.mark.parametrize("field", ["repo_root", "ssd_path", "repo_head_sha", "generation_id"])
def test_receipt_binding_substitution_is_rejected(tmp_path: Path, field: str) -> None:
    store, repo = tmp_path / "store", tmp_path / "repo"
    repo.mkdir()
    path, digest, generation = _write_receipt(store, repo)
    overrides = {
        "repo_root": {"expected_repo_root": tmp_path / "other-repo"},
        "ssd_path": {"expected_ssd_path": tmp_path / "other-store"},
        "repo_head_sha": {"expected_repo_head_sha": "9" * 40},
        "generation_id": {"expected_generation_id": "sha256:" + "9" * 64},
    }[field]
    with pytest.raises(ValueError):
        _open(path, store, repo, digest, generation, **overrides)


def test_wrong_digest_oversize_malformed_and_duplicate_keys_reject(tmp_path: Path) -> None:
    store, repo = tmp_path / "store", tmp_path / "repo"
    repo.mkdir()
    path, digest, generation = _write_receipt(store, repo)
    with pytest.raises(ValueError):
        _open(path, store, repo, "sha256:" + "0" * 64, generation)
    with pytest.raises(ValueError):
        _open(path, store, repo, digest, generation, max_bytes=8)
    path.write_bytes(b"\xff")
    with pytest.raises(ValueError):
        _open(path, store, repo, digest, generation)
    path.write_text('{"schema_version":"a","schema_version":"b"}', encoding="utf-8")
    with pytest.raises(ValueError):
        _open(path, store, repo, digest, generation)


def test_final_link_is_rejected(tmp_path: Path) -> None:
    store, repo = tmp_path / "store", tmp_path / "repo"
    repo.mkdir()
    path, digest, generation = _write_receipt(store, repo)
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError):
        _open(path, store, repo, digest, generation)


def test_hardlink_is_rejected(tmp_path: Path) -> None:
    store, repo = tmp_path / "store", tmp_path / "repo"
    repo.mkdir()
    path, digest, generation = _write_receipt(store, repo)
    outside = tmp_path / "outside.json"
    path.unlink()
    outside.write_bytes(json.dumps(_receipt(repo_root=repo, ssd_path=store, sha=SHA), sort_keys=True).encode())
    os.link(outside, path)
    with pytest.raises(ValueError):
        _open(path, store, repo, digest, generation)


def test_revalidate_detects_replacement_when_platform_allows_it(tmp_path: Path) -> None:
    store, repo = tmp_path / "store", tmp_path / "repo"
    repo.mkdir()
    path, digest, generation = _write_receipt(store, repo)
    with _open(path, store, repo, digest, generation) as proof:
        replacement = path.with_suffix(".replacement")
        replacement.write_bytes(path.read_bytes())
        try:
            os.replace(replacement, path)
        except PermissionError:
            return  # Windows lease correctly prevents replacement.
        with pytest.raises(ValueError):
            proof.revalidate()


def test_noncanonical_receipt_path_and_case_safe_exact_path_reject(tmp_path: Path) -> None:
    store, repo = tmp_path / "store", tmp_path / "repo"
    repo.mkdir()
    path, digest, generation = _write_receipt(store, repo)
    copied = store / "indexes" / "other.json"
    copied.write_bytes(path.read_bytes())
    with pytest.raises(ValueError):
        _open(copied, store, repo, digest, generation)
