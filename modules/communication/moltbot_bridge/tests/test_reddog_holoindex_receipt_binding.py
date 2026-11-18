"""Canonical receipt identity regressions for direct HoloIndex diagnostics."""

from __future__ import annotations

from pathlib import Path

import holo_index.query_admission as query_admission
import modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter as adapter
from holo_index.query_admission import evaluate_readonly_query_admission
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    HoloIndexReadOnlyQueryAdapter,
)
from modules.communication.moltbot_bridge.tests.test_reddog_holoindex_query_boundary import (
    _set_repo_head,
    _write_holo_receipt,
)


def _conflicting_receipts(tmp_path: Path):
    repo_root = tmp_path / "repo"
    foreign_root = tmp_path / "foreign"
    repo_root.mkdir()
    foreign_root.mkdir()
    head_sha = "9" * 40
    _set_repo_head(repo_root, head_sha)
    ssd_path = tmp_path / "ssd"
    canonical = ssd_path / "indexes" / "holoindex_freshness_receipt.json"
    external = tmp_path / "external" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(canonical, repo_root=foreign_root, head_sha=head_sha)
    _write_holo_receipt(external, repo_root=repo_root, head_sha=head_sha)
    return repo_root, ssd_path, external


def test_external_valid_receipt_rejects_before_any_read_or_backend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root, ssd_path, external = _conflicting_receipts(tmp_path)
    reads: list[Path] = []
    real_loader = query_admission.load_freshness_receipt
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        adapter,
        "evaluate_readonly_query_admission",
        evaluate_readonly_query_admission,
    )
    monkeypatch.setattr(
        query_admission,
        "load_freshness_receipt",
        lambda path: (reads.append(Path(path)), real_loader(path))[1],
    )
    monkeypatch.setattr(
        adapter,
        "_direct_backend_query",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("receipt mismatch must reject before backend")
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        ssd_path=ssd_path,
        freshness_receipt_path=external,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["error"] == "HOLOINDEX_FRESHNESS_RECEIPT_PATH_MISMATCH"
    assert result["stale_reasons"] == ["freshness_receipt_path_not_canonical"]
    assert result["hits"] == []
    assert reads == []
