"""Evidence-qualified module roots and hostile candidate-tree batches."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.module_intent_snapshot import (
    MAX_GIT_TREE_BYTES,
    ModuleIntentSnapshotError,
    clear_module_intent_snapshot_cache,
    load_module_intent_paths,
)
from holo_index.tests.module_intent_test_support import (
    HEAD_A,
    candidate_batch,
    directory_tree,
    framed_tree,
    raw_tree,
)
from holo_index.tier0_retrieval import infer_explicit_module_target


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_module_intent_snapshot_cache()


def test_data_containers_are_excluded_without_hiding_scaffolds(
    tmp_path: Path,
) -> None:
    tree = directory_tree(
        "modules/telemetry/feedback",
        "modules/telemetry/feedback/comment_engagement",
        "modules/foundups/docs",
        "modules/domain/scaffold", "modules/domain/scaffold/src",
        "modules/domain/test_scaffold", "modules/domain/test_scaffold/tests",
        "modules/domain/doc_only", "modules/domain/interface_only",
    )

    def run(argv, **kwargs):
        if "rev-parse" in argv:
            output = HEAD_A.encode()
        elif "cat-file" in argv:
            output = candidate_batch(kwargs["input"], documented={0, 1})
        else:
            output = tree
        return SimpleNamespace(returncode=0, stdout=output)

    modules = load_module_intent_paths(tmp_path, run=run)
    assert modules == (
        "modules/domain/doc_only", "modules/domain/interface_only",
        "modules/domain/scaffold", "modules/domain/test_scaffold",
    )
    assert infer_explicit_module_target(
        "WRE feedback", ({"path": path} for path in modules)
    ) is None


def test_repository_excludes_feedback_without_hiding_real_modules() -> None:
    modules = load_module_intent_paths(Path(__file__).resolve().parents[2])
    assert "modules/telemetry/feedback" not in modules
    assert "modules/ai_intelligence/holo_dae" in modules
    assert "modules/ai_intelligence/consciousness_engine" in modules
    assert infer_explicit_module_target(
        "WRE feedback", ({"path": path} for path in modules)
    ) is None


def test_regular_root_contract_qualifies_doc_only_module(tmp_path: Path) -> None:
    tree = directory_tree("modules/domain/doc_only")

    def run(argv, **kwargs):
        if "rev-parse" in argv:
            output = HEAD_A.encode()
        elif "cat-file" in argv:
            output = framed_tree(kwargs["input"], raw_tree("INTERFACE.md"))
        else:
            output = tree
        return SimpleNamespace(returncode=0, stdout=output)

    assert load_module_intent_paths(tmp_path, run=run) == (
        "modules/domain/doc_only",
    )


def test_symlinked_root_contract_is_not_module_evidence(tmp_path: Path) -> None:
    tree = directory_tree("modules/domain/data")
    symlink = b"120000 README.md\0" + (b"x" * 20)

    def run(argv, **kwargs):
        if "rev-parse" in argv:
            output = HEAD_A.encode()
        elif "cat-file" in argv:
            output = framed_tree(kwargs["input"], symlink)
        else:
            output = tree
        return SimpleNamespace(returncode=0, stdout=output)

    with pytest.raises(ModuleIntentSnapshotError):
        load_module_intent_paths(tmp_path, run=run)


def _hostile_batch(kind: str, input_data: bytes) -> SimpleNamespace:
    valid = candidate_batch(input_data)
    if kind == "nonzero":
        return SimpleNamespace(returncode=9, stdout=b"failed")
    if kind == "oversize":
        return SimpleNamespace(
            returncode=0, stdout=b"x" * (MAX_GIT_TREE_BYTES + 1)
        )
    if kind == "wrong_oid":
        output = framed_tree(input_data, raw_tree("artifact.txt"), oid="f" * 40)
    elif kind == "truncated":
        output = valid[:-1]
    elif kind == "extra":
        output = valid + b"unexpected"
    elif kind == "bad_header":
        output = b"missing\n"
    elif kind == "bad_size":
        oid = input_data.decode("ascii").strip()
        output = f"{oid} tree 999\nshort\n".encode("ascii")
    elif kind == "bad_mode":
        output = framed_tree(
            input_data, b"999999 artifact.txt\0" + (b"x" * 20)
        )
    elif kind == "invalid_utf8":
        output = framed_tree(
            input_data, b"100644 bad\xffname\0" + (b"x" * 20)
        )
    elif kind == "duplicate_casefold":
        output = framed_tree(input_data, raw_tree("Artifact.txt", "artifact.TXT"))
    elif kind == "truncated_raw_oid":
        output = framed_tree(
            input_data, b"100644 artifact.txt\0" + (b"x" * 19)
        )
    elif kind == "backslash_name":
        output = framed_tree(input_data, raw_tree("bad\\name"))
    else:
        raise AssertionError(kind)
    return SimpleNamespace(returncode=0, stdout=output)


@pytest.mark.parametrize(
    "failure_kind",
    [
        "nonzero", "oversize", "wrong_oid", "truncated", "extra",
        "bad_header", "bad_size", "bad_mode", "invalid_utf8",
        "duplicate_casefold", "truncated_raw_oid", "backslash_name",
    ],
)
def test_hostile_candidate_tree_batch_fails_closed(
    tmp_path: Path, failure_kind: str,
) -> None:
    tree = directory_tree("modules/domain/valid", "modules/domain/valid/src")

    def run(argv, **kwargs):
        if "rev-parse" in argv:
            return SimpleNamespace(returncode=0, stdout=HEAD_A.encode())
        if "cat-file" in argv:
            return _hostile_batch(failure_kind, kwargs["input"])
        return SimpleNamespace(returncode=0, stdout=tree)

    with pytest.raises(
        ModuleIntentSnapshotError,
        match="HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE",
    ):
        load_module_intent_paths(tmp_path, run=run)
