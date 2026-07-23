"""Read-only persistent-query admission regressions."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import holo_index.query_admission as query_admission
from holo_index.freshness_receipt import freshness_receipt_path
from holo_index.query_admission import evaluate_readonly_query_admission
from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    _receipt,
)


SHA = "a" * 40


def _clear_maintenance(_path: Path) -> SimpleNamespace:
    return SimpleNamespace(clear=True, held=False, status="idle")


def _clean_repository(head_sha: str = SHA):
    return lambda _root: SimpleNamespace(
        proven_clean=True,
        head_sha=head_sha,
        error="",
    )


def _write_receipt(
    ssd_path: Path,
    *,
    repo_root: Path,
    head_sha: str = SHA,
    omit: str = "",
    receipt_ssd_path: Path | None = None,
    generation: str = "generation-1",
) -> Path:
    path = freshness_receipt_path(ssd_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            _receipt(
                sha=head_sha,
                generation=generation,
                repo_root=repo_root,
                ssd_path=receipt_ssd_path or ssd_path,
                omit=omit,
            )
        ),
        encoding="utf-8",
    )
    return path


def test_foreign_worktree_receipt_is_rejected_before_backend_use(
    tmp_path: Path,
) -> None:
    invoking_root = tmp_path / "lane-a"
    foreign_root = tmp_path / "lane-b"
    invoking_root.mkdir()
    foreign_root.mkdir()
    ssd_path = tmp_path / "ssd"
    _write_receipt(ssd_path, repo_root=foreign_root)

    result = evaluate_readonly_query_admission(
        repo_root=invoking_root,
        ssd_path=ssd_path,
        repository_state_reader=_clean_repository(),
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is False
    assert result.error == "STALE_INDEX"
    assert result.reasons == ("freshness_repo_root_mismatch",)


def test_active_maintenance_is_rejected_before_receipt_or_backend(
    tmp_path: Path,
) -> None:
    receipt_loaded = False

    def unexpected_loader(_path: Path):
        nonlocal receipt_loaded
        receipt_loaded = True
        raise AssertionError("maintenance must reject before receipt loading")

    result = evaluate_readonly_query_admission(
        repo_root=tmp_path / "repo",
        ssd_path=tmp_path / "ssd",
        repository_state_reader=_clean_repository(),
        receipt_loader=unexpected_loader,
        maintenance_probe=lambda _path: SimpleNamespace(
            clear=False,
            held=True,
            status="held",
        ),
    )

    assert result.allowed is False
    assert result.error == "HOLOINDEX_MAINTENANCE_ACTIVE"
    assert result.reasons == ("holoindex_maintenance_active",)
    assert receipt_loaded is False


def test_same_root_wrong_head_is_rejected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ssd_path = tmp_path / "ssd"
    _write_receipt(ssd_path, repo_root=repo_root, head_sha="b" * 40)

    result = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        repository_state_reader=_clean_repository(SHA),
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is False
    assert result.error == "REPO_HEAD_MISMATCH"
    assert "stale_repo_head_sha" in result.reasons


def test_same_root_wrong_ssd_is_rejected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ssd_path = tmp_path / "ssd"
    _write_receipt(
        ssd_path,
        repo_root=repo_root,
        receipt_ssd_path=tmp_path / "other-ssd",
    )

    result = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        repository_state_reader=_clean_repository(),
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is False
    assert result.error == "STALE_INDEX"
    assert "freshness_ssd_path_mismatch" in result.reasons


def test_missing_generation_binding_is_rejected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ssd_path = tmp_path / "ssd"
    _write_receipt(
        ssd_path,
        repo_root=repo_root,
        generation="",
    )

    result = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        repository_state_reader=_clean_repository(),
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is False
    assert result.error == "MISSING_GENERATION_BINDING"
    assert "missing_holoindex_generation_id" in result.reasons


def test_incomplete_baseline_generation_is_rejected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ssd_path = tmp_path / "ssd"
    _write_receipt(
        ssd_path,
        repo_root=repo_root,
        omit="navigation_knowledge",
    )

    result = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        repository_state_reader=_clean_repository(),
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is False
    assert result.error == "STALE_INDEX"
    assert "missing_collection_receipt:navigation_knowledge" in result.reasons


def test_exact_clean_generation_is_admitted(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ssd_path = tmp_path / "ssd"
    _write_receipt(ssd_path, repo_root=repo_root)

    result = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        repository_state_reader=_clean_repository(),
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is True
    assert result.error == ""
    assert result.reasons == ()
    assert result.freshness == "CURRENT"


def test_explicit_noncanonical_receipt_is_rejected_before_any_read(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    foreign_root = tmp_path / "foreign"
    repo_root.mkdir()
    foreign_root.mkdir()
    ssd_path = tmp_path / "ssd"
    _write_receipt(ssd_path, repo_root=foreign_root)
    external = tmp_path / "external" / "holoindex_freshness_receipt.json"
    external.parent.mkdir()
    external.write_text(
        json.dumps(
            _receipt(
                sha=SHA,
                generation="generation-external",
                repo_root=repo_root,
                ssd_path=ssd_path,
            )
        ),
        encoding="utf-8",
    )
    reads: list[Path] = []

    def recording_loader(path: Path):
        reads.append(Path(path))
        return json.loads(Path(path).read_text(encoding="utf-8"))

    result = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        receipt_path=external,
        repository_state_reader=_clean_repository(),
        receipt_loader=recording_loader,
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is False
    assert result.error == "HOLOINDEX_FRESHNESS_RECEIPT_PATH_MISMATCH"
    assert result.reasons == ("freshness_receipt_path_not_canonical",)
    assert reads == []


def test_canonical_receipt_final_link_or_reparse_fails_before_read(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ssd_path = tmp_path / "ssd"
    canonical = _write_receipt(ssd_path, repo_root=repo_root)
    monkeypatch.setattr(
        query_admission,
        "_final_receipt_link_or_reparse",
        lambda path: Path(path) == canonical,
        raising=False,
    )
    reads: list[Path] = []

    result = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        repository_state_reader=_clean_repository(),
        receipt_loader=lambda path: reads.append(Path(path)),
        maintenance_probe=_clear_maintenance,
    )

    assert result.allowed is False
    assert result.error == "HOLOINDEX_FRESHNESS_RECEIPT_PATH_MISMATCH"
    assert result.reasons == ("freshness_receipt_path_not_canonical",)
    assert reads == []
