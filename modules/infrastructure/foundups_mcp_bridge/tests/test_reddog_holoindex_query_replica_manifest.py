"""Focused policy tests for the narrow RedDog query-replica closure."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
    QueryReplicaError,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_reddog_holoindex_query_replica import (
    _fixture,
    _materialize,
    _tree_manifest,
)


def _assert_replica_root_pristine(fixture) -> None:
    assert list(fixture[2].iterdir()) == []


def test_manifest_policy_import_does_not_require_site_packages() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    module = (
        "modules.infrastructure.foundups_mcp_bridge.src."
        "reddog_holoindex_query_replica_manifest"
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            f"import sys; import {module}; assert 'numpy' not in sys.modules",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_materializer_rejects_legacy_complete_vectors_closure(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    vectors = fixture[0] / "vectors"
    (vectors / "chroma.sqlite3").write_bytes(b"legacy-sqlite")
    legacy = _tree_manifest("vectors", vectors, "vectors")

    with pytest.raises(QueryReplicaError, match="ARTIFACT_SET_INVALID"):
        _materialize((*fixture[:5], (fixture[5][0], legacy)))


def test_materializer_rejects_second_model_marker_before_publication(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    model = fixture[5][0].source_root
    nested = model / "second_model"
    nested.mkdir()
    (nested / "modules.json").write_text("{}", encoding="utf-8")
    ambiguous = _tree_manifest(
        "model", model, fixture[5][0].replica_relative_root
    )

    with pytest.raises(QueryReplicaError, match="MODEL_ROOT_AMBIGUOUS"):
        _materialize((*fixture[:5], (ambiguous, fixture[5][1])))
    assert not (fixture[2] / "holoindex_query_replica.active.json").exists()
    assert not (fixture[2] / "generations").exists()


@pytest.mark.parametrize("alias_kind", ["dot", "double", "backslash"])
def test_artifact_root_aliases_fail_before_replica_root_mutation(
    tmp_path: Path, alias_kind: str,
) -> None:
    fixture = _fixture(tmp_path)
    original = fixture[5][0].replica_relative_root
    aliases = {
        "dot": original + "/.",
        "double": original.replace("/", "//", 1),
        "backslash": original.replace("/", "\\", 1),
    }
    hostile = replace(
        fixture[5][0], replica_relative_root=aliases[alias_kind]
    )

    with pytest.raises(QueryReplicaError, match="ARTIFACT_ROOT_INVALID"):
        _materialize((*fixture[:5], (hostile, fixture[5][1])))
    _assert_replica_root_pristine(fixture)


def test_receipt_path_alias_fails_before_replica_root_mutation(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    receipt = fixture[4].receipt_path
    alias = str(receipt.parent) + "\\.\\" + receipt.name
    hostile = replace(fixture[4], receipt_path=alias)

    with pytest.raises(QueryReplicaError, match="RECEIPT_PATH_NONCANONICAL"):
        _materialize((*fixture[:4], hostile, fixture[5]))
    _assert_replica_root_pristine(fixture)


def test_non_nfc_artifact_path_fails_before_replica_root_mutation(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    model = fixture[5][0].source_root
    (model / "cafe\u0301.bin").write_bytes(b"decomposed-unicode")
    hostile = _tree_manifest(
        "model", model, fixture[5][0].replica_relative_root
    )

    with pytest.raises(QueryReplicaError, match="ARTIFACT_PATH_INVALID"):
        _materialize((*fixture[:5], (hostile, fixture[5][1])))
    _assert_replica_root_pristine(fixture)


@pytest.mark.parametrize("marker", ["MODULES.JSON", "Modules.Json"])
def test_case_variant_nested_model_marker_fails_before_replica_root_mutation(
    tmp_path: Path, marker: str,
) -> None:
    fixture = _fixture(tmp_path)
    model = fixture[5][0].source_root
    nested = model / "second_model"
    nested.mkdir()
    (nested / marker).write_bytes(b"[]")
    hostile = _tree_manifest(
        "model", model, fixture[5][0].replica_relative_root
    )

    with pytest.raises(QueryReplicaError, match="MODEL_ROOT_AMBIGUOUS"):
        _materialize((*fixture[:5], (hostile, fixture[5][1])))
    _assert_replica_root_pristine(fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("size", True),
        ("size", 1.0),
        ("sha256", "sha256:" + "g" * 64),
    ],
)
def test_malformed_outer_manifest_scalar_fails_before_root_mutation(
    tmp_path: Path, field: str, value: object,
) -> None:
    fixture = _fixture(tmp_path)
    model = fixture[5][0]
    hostile_item = replace(model.files[0], **{field: value})
    hostile = replace(model, files=(hostile_item, *model.files[1:]))

    with pytest.raises(QueryReplicaError, match="ARTIFACT_MANIFEST_INVALID"):
        _materialize((*fixture[:5], (hostile, fixture[5][1])))
    _assert_replica_root_pristine(fixture)


def test_outer_manifest_container_and_order_fail_before_root_mutation(
    tmp_path: Path,
) -> None:
    cases = []
    for index in range(2):
        case = tmp_path / str(index)
        case.mkdir()
        fixture = _fixture(case)
        model = fixture[5][0]
        hostile = replace(
            model,
            files=(list(model.files) if index == 0 else tuple(reversed(model.files))),
        )
        cases.append((fixture, hostile))

    for fixture, hostile in cases:
        with pytest.raises(QueryReplicaError, match="ARTIFACT_MANIFEST"):
            _materialize((*fixture[:5], (hostile, fixture[5][1])))
        _assert_replica_root_pristine(fixture)


def test_full_descriptor_path_bound_is_preflighted_before_root_mutation(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        QueryReplicaLimits,
    )

    fixture = _fixture(tmp_path)
    item_path_bytes = len(fixture[5][0].files[0].relative_path.encode("utf-8"))
    limits = replace(QueryReplicaLimits(), max_path_bytes=item_path_bytes + 1)

    with pytest.raises(QueryReplicaError, match="PATH_BOUND"):
        _materialize(fixture, limits=limits)
    _assert_replica_root_pristine(fixture)


def test_snapshot_manifest_generation_is_bound_before_copy(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    snapshots = fixture[5][1].source_root
    manifest_path = snapshots / "snapshot_set.json"
    payload = json.loads(manifest_path.read_text(encoding="ascii"))
    payload["generation_id"] = "sha256:" + "c" * 64
    manifest_path.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        + b"\n"
    )
    changed = _tree_manifest("snapshots", snapshots, "vectors/query_snapshots")

    with pytest.raises(QueryReplicaError, match="SNAPSHOT_GENERATION_MISMATCH"):
        _materialize((*fixture[:5], (fixture[5][0], changed)))


def test_snapshot_manifest_requires_exact_twenty_two_file_set(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    snapshots = fixture[5][1].source_root
    (snapshots / "navigation_code.rows.jsonl").unlink()
    incomplete = _tree_manifest("snapshots", snapshots, "vectors/query_snapshots")

    with pytest.raises(QueryReplicaError, match="SNAPSHOT_SET_INCOMPLETE"):
        _materialize((*fixture[:5], (fixture[5][0], incomplete)))


def test_snapshot_inner_digest_mismatch_fails_before_replica_root_mutation(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    snapshots = fixture[5][1].source_root
    manifest_path = snapshots / "snapshot_set.json"
    payload = json.loads(manifest_path.read_text(encoding="ascii"))
    collection = sorted(payload["collections"])[0]
    payload["collections"][collection]["rows"]["sha256"] = (
        "sha256:" + "f" * 64
    )
    manifest_path.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        + b"\n"
    )
    hostile = _tree_manifest(
        "snapshots", snapshots, "vectors/query_snapshots"
    )

    with pytest.raises(QueryReplicaError, match="SNAPSHOT_SET_INVALID"):
        _materialize((*fixture[:5], (fixture[5][0], hostile)))
    _assert_replica_root_pristine(fixture)


@pytest.mark.parametrize("field", ["repo_head_sha", "generation_id", "receipt_digest"])
def test_generation_binding_rejects_nonexact_scalar_types(
    tmp_path: Path, field: str,
) -> None:
    from dataclasses import replace

    fixture = _fixture(tmp_path)
    hostile = replace(fixture[4], **{field: b"a" * 40})

    with pytest.raises(QueryReplicaError, match="INVALID"):
        _materialize((*fixture[:4], hostile, fixture[5]))
