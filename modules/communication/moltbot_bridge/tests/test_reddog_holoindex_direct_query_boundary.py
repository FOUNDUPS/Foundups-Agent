"""Direct diagnostic HoloIndex adapter truth-boundary tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.core.holo_index import HoloIndex
from holo_index.maintenance_lock import (
    acquire_maintenance_lease,
    maintenance_lock_path,
)
from holo_index.storage_contract import (
    HoloIndexStorageError,
    STORAGE_NOT_WRITABLE_CODE,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    HoloIndexReadOnlyQueryAdapter,
)
import modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter as holo_query_adapter
from holo_index.query_admission import ReadonlyQueryAdmission
from modules.communication.moltbot_bridge.tests.test_reddog_holoindex_query_boundary import (
    _patch_holo_search,
    _set_repo_head,
    _write_holo_receipt,
)


@pytest.fixture(autouse=True)
def _admit_existing_direct_diagnostic_fixtures(monkeypatch) -> None:
    monkeypatch.setattr(
        holo_query_adapter,
        "evaluate_readonly_query_admission",
        lambda **_kwargs: ReadonlyQueryAdmission(
            allowed=True,
            error="",
            reasons=(),
            freshness="CURRENT",
            binding={},
        ),
    )


def test_holoindex_adapter_preserves_typed_storage_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _set_repo_head(repo_root, "5" * 40)
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        HoloIndex,
        "__init__",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            HoloIndexStorageError(
                STORAGE_NOT_WRITABLE_CODE,
                path=tmp_path / "ssd",
                operation="open_chromadb",
                detail="sqlite code 8",
            )
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        ssd_path=tmp_path / "ssd",
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == STORAGE_NOT_WRITABLE_CODE
    assert result["storage_error"]["operation"] == "open_chromadb"


def test_holoindex_hit_normalization_preserves_wsp_and_knowledge_buckets() -> None:
    hits = holo_query_adapter.holoindex_hits(
        {
            "wsp_hits": [
                {
                    "path": "WSP_framework/src/WSP_97_Truth_Boundary_Protocol.md",
                    "title": "WSP 97",
                }
            ],
            "wsps": [
                {
                    "path": "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
                    "title": "WSP 00",
                }
            ],
            "knowledge_hits": [
                {
                    "path": "WSP_knowledge/docs/Papers/PQN_Deep_Dive.md",
                    "title": "PQN",
                }
            ],
            "knowledge": [
                {
                    "path": "WSP_knowledge/docs/Papers/FoundUps_Paper.md",
                    "title": "FoundUps",
                }
            ],
        }
    )

    assert [hit["path"] for hit in hits] == [
        "WSP_framework/src/WSP_97_Truth_Boundary_Protocol.md",
        "WSP_knowledge/docs/Papers/PQN_Deep_Dive.md",
        "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
        "WSP_knowledge/docs/Papers/FoundUps_Paper.md",
    ]


def test_holoindex_query_receipt_paths_are_normalized_and_deduplicated() -> None:
    assert holo_query_adapter.paths_from_query_receipt(
        {
            "hits": [
                {"path": "modules" + chr(92) + "example/src/module.py"},
                {"path": " modules/example/src/module.py "},
                "invalid",
                {"path": ""},
                {"path": "WSP_framework/src/WSP_97.md"},
            ]
        }
    ) == (
        "modules/example/src/module.py",
        "WSP_framework/src/WSP_97.md",
    )


def test_holoindex_direct_adapter_never_claims_current_from_valid_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "b" * 40
    _set_repo_head(repo_root, head_sha)
    receipt_path = tmp_path / "ssd" / "indexes" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(receipt_path, repo_root=repo_root, head_sha=head_sha)
    _patch_holo_search(monkeypatch)

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        ssd_path=tmp_path / "ssd",
        freshness_receipt_path=receipt_path,
    ).query(
        query="WSP 97 evidence",
        allowed_paths=("WSP_framework/src/**",),
        limit=8,
    )

    assert result["ok"] is False
    assert result["freshness"] == "UNKNOWN"
    assert result["error"] == "HOLOINDEX_DIRECT_QUERY_DIAGNOSTIC_ONLY"
    assert result["stale_reasons"] == [
        "direct_query_has_no_freshness_authority"
    ]
    assert result["index_gap_detected"] is True
    assert result["hits"][0]["path"].endswith(
        "WSP_97_Truth_Boundary_Protocol.md"
    )
    assert "freshness_generation_id" not in result


def test_holoindex_direct_adapter_blocks_active_maintenance_before_backend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "8" * 40
    _set_repo_head(repo_root, head_sha)
    ssd_path = tmp_path / "ssd"
    receipt_path = ssd_path / "indexes" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(receipt_path, repo_root=repo_root, head_sha=head_sha)
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        HoloIndex,
        "__init__",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("maintenance gate must prevent backend initialization")
        ),
    )

    with acquire_maintenance_lease(maintenance_lock_path(ssd_path)):
        result = HoloIndexReadOnlyQueryAdapter(
            repo_root=repo_root,
            ssd_path=ssd_path,
            freshness_receipt_path=receipt_path,
        ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_MAINTENANCE_ACTIVE"
    assert result["stale_reasons"] == ["holoindex_maintenance_active"]
    assert result["hits"] == []


def test_holoindex_direct_adapter_blocks_foreign_root_before_backend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "lane-a"
    foreign_root = tmp_path / "lane-b"
    repo_root.mkdir()
    foreign_root.mkdir()
    head_sha = "8" * 40
    _set_repo_head(repo_root, head_sha)
    ssd_path = tmp_path / "ssd"
    receipt_path = ssd_path / "indexes" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(
        receipt_path,
        repo_root=foreign_root,
        head_sha=head_sha,
    )
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        holo_query_adapter,
        "_direct_backend_query",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("foreign-root admission must prevent backend access")
        ),
    )
    monkeypatch.setattr(
        holo_query_adapter,
        "evaluate_readonly_query_admission",
        lambda **_kwargs: ReadonlyQueryAdmission(
            allowed=False,
            error="STALE_INDEX",
            reasons=("freshness_repo_root_mismatch",),
            freshness="STALE",
            binding={},
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        ssd_path=ssd_path,
        freshness_receipt_path=receipt_path,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "STALE_INDEX"
    assert result["stale_reasons"] == ["freshness_repo_root_mismatch"]
    assert result["hits"] == []


def test_holoindex_direct_adapter_blocks_unproven_maintenance_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        holo_query_adapter,
        "probe_maintenance_lock",
        lambda _path: SimpleNamespace(clear=False, held=False, status="error"),
    )
    monkeypatch.setattr(
        HoloIndex,
        "__init__",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("unproven maintenance state must prevent backend work")
        ),
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=tmp_path,
        ssd_path=tmp_path / "ssd",
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_MAINTENANCE_LOCK_UNPROVEN"
    assert result["stale_reasons"] == ["holoindex_maintenance_lock_unproven"]


def test_holoindex_direct_adapter_rejects_result_if_maintenance_starts_during_query(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "0" * 40
    _set_repo_head(repo_root, head_sha)
    receipt_path = tmp_path / "ssd" / "indexes" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(receipt_path, repo_root=repo_root, head_sha=head_sha)
    clear = SimpleNamespace(clear=True, held=False, status="idle")
    held = SimpleNamespace(clear=False, held=True, status="held")
    probes = iter([clear, held])
    monkeypatch.delenv("HOLOINDEX_QUERY_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        holo_query_adapter, "probe_maintenance_lock", lambda _path: next(probes)
    )
    _patch_holo_search(monkeypatch)

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        ssd_path=tmp_path / "ssd",
        freshness_receipt_path=receipt_path,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_MAINTENANCE_ACTIVE"
    assert result["stale_reasons"] == ["holoindex_maintenance_active"]
    assert result["hits"] == []


def test_holoindex_direct_adapter_old_receipt_has_no_authority(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    current_head = "c" * 40
    old_head = "d" * 40
    _set_repo_head(repo_root, current_head)
    receipt_path = tmp_path / "ssd" / "indexes" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(receipt_path, repo_root=repo_root, head_sha=old_head)
    _patch_holo_search(monkeypatch)

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        freshness_receipt_path=receipt_path,
    ).query(
        query="WSP 97 evidence",
        allowed_paths=("WSP_framework/src/**",),
        limit=8,
    )

    assert result["ok"] is False
    assert result["freshness"] == "UNKNOWN"
    assert result["index_gap_detected"] is True
    assert result["error"] == "HOLOINDEX_DIRECT_QUERY_DIAGNOSTIC_ONLY"
    assert result["stale_reasons"] == [
        "direct_query_has_no_freshness_authority"
    ]
    assert result["hits"][0]["path"].endswith("WSP_97_Truth_Boundary_Protocol.md")


def test_holoindex_direct_adapter_rejects_lexical_retrieval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "7" * 40
    _set_repo_head(repo_root, head_sha)
    receipt_path = tmp_path / "ssd" / "indexes" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(receipt_path, repo_root=repo_root, head_sha=head_sha)
    _patch_holo_search(
        monkeypatch,
        {"wsp_hits": [], "metadata": {"retrieval_mode": "lexical"}},
    )

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        ssd_path=tmp_path / "ssd",
        freshness_receipt_path=receipt_path,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["error"] == "HOLOINDEX_DIRECT_QUERY_DIAGNOSTIC_ONLY"
    assert result["freshness"] == "UNKNOWN"
    assert result["retrieval_mode"] == "lexical"
    assert "direct_query_has_no_freshness_authority" in result["stale_reasons"]
    assert "nonsemantic_retrieval" in result["stale_reasons"]


def test_holoindex_direct_adapter_unverified_receipt_has_no_authority(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    head_sha = "e" * 40
    _set_repo_head(repo_root, head_sha)
    receipt_path = tmp_path / "ssd" / "indexes" / "holoindex_freshness_receipt.json"
    _write_holo_receipt(
        receipt_path,
        repo_root=repo_root,
        head_sha=head_sha,
        unverified=("navigation_wsp", "navigation_knowledge"),
    )
    _patch_holo_search(monkeypatch)

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        freshness_receipt_path=receipt_path,
    ).query(query="protocol and research evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["freshness"] == "UNKNOWN"
    assert result["error"] == "HOLOINDEX_DIRECT_QUERY_DIAGNOSTIC_ONLY"
    assert result["stale_reasons"] == [
        "direct_query_has_no_freshness_authority"
    ]


def test_holoindex_direct_adapter_missing_receipt_is_diagnostic(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _set_repo_head(repo_root, "f" * 40)
    receipt_path = tmp_path / "missing" / "holoindex_freshness_receipt.json"
    _patch_holo_search(monkeypatch)

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        freshness_receipt_path=receipt_path,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["freshness"] == "UNKNOWN"
    assert result["error"] == "HOLOINDEX_DIRECT_QUERY_DIAGNOSTIC_ONLY"
    assert result["stale_reasons"] == [
        "direct_query_has_no_freshness_authority"
    ]
    assert result["index_gap_detected"] is True


def test_holoindex_direct_adapter_malformed_receipt_is_diagnostic(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _set_repo_head(repo_root, "1" * 40)
    receipt_path = tmp_path / "ssd" / "indexes" / "holoindex_freshness_receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text("{not-json", encoding="utf-8")
    _patch_holo_search(monkeypatch)

    result = HoloIndexReadOnlyQueryAdapter(
        repo_root=repo_root,
        freshness_receipt_path=receipt_path,
    ).query(query="evidence", allowed_paths=(), limit=8)

    assert result["ok"] is False
    assert result["freshness"] == "UNKNOWN"
    assert result["error"] == "HOLOINDEX_DIRECT_QUERY_DIAGNOSTIC_ONLY"
    assert result["stale_reasons"] == [
        "direct_query_has_no_freshness_authority"
    ]
    assert result["index_gap_detected"] is True
