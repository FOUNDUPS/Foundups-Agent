"""Focused embedding-space, offline-cache, and timeout truth tests."""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from holo_index.core.holo_index import HoloIndex, _run_with_timeout
from holo_index.embedding_space import (
    SENTENCE_TRANSFORMER_CONTRACT,
    SENTENCE_TRANSFORMER_MODEL_ID,
    embedding_artifact_digest,
    embedding_space_fingerprint,
    resolve_sentence_transformer_snapshot,
)
from holo_index.freshness_receipt import build_freshness_receipt


def _complete_snapshot(root: Path, revision: str) -> Path:
    snapshot = (
        root
        / "models--sentence-transformers--all-MiniLM-L6-v2"
        / "snapshots"
        / revision
    )
    snapshot.mkdir(parents=True)
    for name in ("modules.json", "config.json", "tokenizer.json"):
        (snapshot / name).write_text(f"{name}:{revision}", encoding="utf-8")
    (snapshot / "model.safetensors").write_bytes(f"weights:{revision}".encode())
    return snapshot


def test_hf_ref_selects_complete_offline_snapshot(tmp_path: Path) -> None:
    first = _complete_snapshot(tmp_path, "revision-a")
    selected = _complete_snapshot(tmp_path, "revision-b")
    ref = (
        tmp_path
        / "models--sentence-transformers--all-MiniLM-L6-v2"
        / "refs"
        / "main"
    )
    ref.parent.mkdir(parents=True)
    ref.write_text("revision-b\n", encoding="utf-8")

    assert (
        resolve_sentence_transformer_snapshot(tmp_path, "all-MiniLM-L6-v2")
        == selected.resolve(strict=False)
    )
    holo = object.__new__(HoloIndex)
    holo.models_path = tmp_path
    assert holo._model_cache_present("all-MiniLM-L6-v2") is True
    assert first != selected


def test_incomplete_or_ambiguous_cache_fails_closed(tmp_path: Path) -> None:
    incomplete = (
        tmp_path
        / "models--sentence-transformers--all-MiniLM-L6-v2"
        / "snapshots"
        / "incomplete"
    )
    incomplete.mkdir(parents=True)
    (incomplete / "config.json").write_text("{}", encoding="utf-8")
    (incomplete / "modules.json").write_text("[]", encoding="utf-8")
    assert resolve_sentence_transformer_snapshot(
        tmp_path, "all-MiniLM-L6-v2"
    ) is None

    _complete_snapshot(tmp_path, "complete-a")
    _complete_snapshot(tmp_path, "complete-b")
    assert resolve_sentence_transformer_snapshot(
        tmp_path, "all-MiniLM-L6-v2"
    ) is None


def test_artifact_or_backend_change_changes_embedding_space(tmp_path: Path) -> None:
    snapshot = _complete_snapshot(tmp_path, "revision-a")
    first_digest = embedding_artifact_digest(snapshot)
    first = embedding_space_fingerprint(
        backend="sentence_transformers",
        model_id=SENTENCE_TRANSFORMER_MODEL_ID,
        artifact_digest=first_digest,
        encoder_contract=SENTENCE_TRANSFORMER_CONTRACT,
    )
    (snapshot / "model.safetensors").write_bytes(b"different weights")
    second = embedding_space_fingerprint(
        backend="sentence_transformers",
        model_id=SENTENCE_TRANSFORMER_MODEL_ID,
        artifact_digest=embedding_artifact_digest(snapshot),
        encoder_contract=SENTENCE_TRANSFORMER_CONTRACT,
    )
    alternate = embedding_space_fingerprint(
        backend="turboquant_onnx_int8",
        model_id=SENTENCE_TRANSFORMER_MODEL_ID,
        artifact_digest=first_digest,
        encoder_contract=SENTENCE_TRANSFORMER_CONTRACT,
    )

    assert first.startswith("sha256:")
    assert len({first, second, alternate}) == 3


def test_timeout_returns_without_waiting_for_running_worker() -> None:
    started = time.monotonic()
    result = _run_with_timeout(
        lambda: time.sleep(0.3),
        timeout_sec=0.02,
        default="timed-out",
    )
    elapsed = time.monotonic() - started

    assert result == "timed-out"
    assert elapsed < 0.15


def test_timeout_wrapper_never_logs_caller_or_exception_text(caplog) -> None:
    secret = "sentinel-secret-query-material"

    def fail_with_secret() -> None:
        raise RuntimeError(secret)

    caplog.set_level("WARNING")
    result = _run_with_timeout(
        fail_with_secret,
        timeout_sec=0.1,
        default="failed",
        error_msg=secret,
        missing_dep_hint=secret,
    )
    assert result == "failed"
    assert secret not in caplog.text
    assert "HOLOINDEX_OPERATION_FAILED (RuntimeError)" in caplog.text

    caplog.clear()
    result = _run_with_timeout(
        lambda: time.sleep(0.1),
        timeout_sec=0.01,
        default="timed-out",
        error_msg=secret,
    )
    assert result == "timed-out"
    assert secret not in caplog.text
    assert "HOLOINDEX_OPERATION_TIMEOUT" in caplog.text


class _Collection:
    name = "navigation_code"

    def __init__(self, fingerprint: str) -> None:
        self.metadata = {
            "embedding_backend": "sentence_transformers",
            "embedding_model": SENTENCE_TRANSFORMER_MODEL_ID,
            "embedding_space_fingerprint": fingerprint,
        }

    def count(self) -> int:
        return 1

    def get(self, include=None):
        return {"ids": ["one"], "metadatas": [{"path": "NAVIGATION.py"}]}


def test_receipt_blanks_collection_space_when_runtime_changed(tmp_path: Path) -> None:
    stored = "sha256:" + ("1" * 64)
    active = "sha256:" + ("2" * 64)
    holo = SimpleNamespace(
        code_collection=_Collection(stored),
        index_embedding_backend="sentence_transformers",
        index_embedding_model_id=SENTENCE_TRANSFORMER_MODEL_ID,
        index_embedding_space_fingerprint=active,
    )
    receipt = build_freshness_receipt(
        holo,
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path,
        source="test",
        repo_head_sha="a" * 40,
        refreshed_collections={"navigation_code"},
    )
    code = next(
        entry for entry in receipt.collections if entry.name == "navigation_code"
    )

    assert code.embedding_backend == "sentence_transformers"
    assert code.embedding_space_fingerprint == ""
