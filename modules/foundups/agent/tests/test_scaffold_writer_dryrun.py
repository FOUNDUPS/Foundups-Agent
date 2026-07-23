#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the FoundUp scaffold dry-run materializer.

Slice: FOUNDUP_SCAFFOLD_WRITER_DRYRUN_PHASE1
WSP:   49, 50, 97, 109

Proves:
    - Materializes EXACTLY the 14 planned artifacts into a sandbox (end-to-end
      from the create_foundup dry-run planner)
    - The written manifest passes the REAL foundup_manifest_validator
    - Fail-closed: write-to-main-repo, path traversal, denied path, existing
      module, registry overwrite
    - No registry mutation, no worktree, sandbox-only
    - Imports no FAM/Hermes writer (AST guard)
    - The LIVE writer file remains ABSENT (boundary preserved)
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from modules.foundups.agent.src import scaffold_writer_dryrun
from modules.foundups.agent.src.create_foundup_dryrun import plan_create_foundup_dry_run
from modules.foundups.agent.src.scaffold_writer_dryrun import materialize_scaffold_dry_run


def _valid_envelope(foundup_id: str = "widget_demo") -> dict:
    return {
        "foundup_id": foundup_id,
        "name": "Widget Demo",
        "tagline": "A tiny demo widget",
        "description": "A demonstration FoundUp for the scaffold dry-run writer.",
        "category": "tools",
        "acceptance_criteria": [
            {"observable": "renders", "method": "pytest",
             "oracle": "200", "pass_condition": "status == 200"},
        ],
        "truth_state_map": [{"feature": foundup_id, "marker": "IDEA_ONLY", "evidence": ""}],
    }


@pytest.fixture
def contract(tmp_path_factory) -> dict:
    reg = tmp_path_factory.mktemp("reg") / "registry.json"
    reg.write_text(
        '{"schema_version":"1.0.0","last_updated":"2026-07-23T00:00:00Z",'
        '"entities":[]}',
        encoding="utf-8",
    )
    res = plan_create_foundup_dry_run(_valid_envelope(), registry_path=reg)
    assert res.ok, res.rejection_reason
    return res.scaffold_contract


# --------------------------------------------------------------------------- #
# Happy path (sandbox materialization)
# --------------------------------------------------------------------------- #

def test_materializes_exactly_planned_artifacts(contract: dict, tmp_path: Path) -> None:
    res = materialize_scaffold_dry_run(contract, output_root=tmp_path)
    assert res.ok is True, res.rejection_reason
    assert res.materialized is True
    assert res.matches_plan is True
    assert len(res.files_written) == 14
    assert len(contract["scaffold_artifacts"]) == 14

    # The set of files on disk (relative to sandbox) equals the planned set exactly.
    on_disk = sorted(
        str(p.relative_to(tmp_path)).replace("\\", "/")
        for p in tmp_path.rglob("*") if p.is_file()
    )
    planned = sorted(a.replace("\\", "/") for a in contract["scaffold_artifacts"])
    assert on_disk == planned

    # Every file was written under the sandbox, never the real repo.
    assert res.wrote_to_main_repo is False
    for f in res.files_written:
        assert str(tmp_path) in f


def test_written_manifest_passes_real_validator(contract: dict, tmp_path: Path) -> None:
    from modules.foundups.agent.src.foundup_manifest_validator import validate_manifest

    res = materialize_scaffold_dry_run(contract, output_root=tmp_path)
    assert res.ok is True
    manifest_file = tmp_path / contract["module_path"] / "foundup_manifest.json"
    assert manifest_file.exists()
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    mv = validate_manifest(data)
    assert mv.ok, mv.errors


def test_no_registry_mutation_or_worktree(contract: dict, tmp_path: Path) -> None:
    res = materialize_scaffold_dry_run(contract, output_root=tmp_path)
    assert res.registry_mutated is False
    assert res.worktree_created is False
    assert res.dry_run_sandbox is True
    # No registry file materialized in the sandbox.
    assert not any(p.name == "foundup_registry.json" for p in tmp_path.rglob("*"))


# --------------------------------------------------------------------------- #
# Fail-closed guards
# --------------------------------------------------------------------------- #

def test_write_to_main_repo_rejected(contract: dict, tmp_path: Path) -> None:
    # Fake repo; output_root INSIDE it must be refused (no real-repo touch).
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    inside = fake_repo / "modules" / "foundups" / "x"
    res = materialize_scaffold_dry_run(contract, output_root=inside, real_repo_root=fake_repo)
    assert res.ok is False
    assert res.rejection_code == "FAIL_WRITE_TO_MAIN_REPO"
    assert res.files_written == []


def test_existing_module_rejected(contract: dict, tmp_path: Path) -> None:
    fake_repo = tmp_path / "repo"
    (fake_repo / contract["module_path"]).mkdir(parents=True)  # module already exists
    sandbox = tmp_path / "sandbox"
    res = materialize_scaffold_dry_run(contract, output_root=sandbox, real_repo_root=fake_repo)
    assert res.ok is False
    assert res.rejection_code == "FAIL_MODULE_EXISTS"


def test_path_traversal_rejected(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"]) + [
        "modules/foundups/widget_demo/../../../etc/evil.txt"
    ]
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_PATH_TRAVERSAL"
    # Nothing materialized because guards run before any write.
    assert list(tmp_path.rglob("*")) == []


def test_denied_path_rejected(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"]) + [
        "modules/foundups/widget_demo/.env"
    ]
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_DENIED_PATH"
    assert list(tmp_path.rglob("*")) == []


def test_registry_overwrite_rejected(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"]) + [
        "modules/foundups/foundup_registry.json"
    ]
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_REGISTRY_OVERWRITE"
    assert res.registry_mutated is False
    assert list(tmp_path.rglob("*")) == []


def test_dae_denied_marker_rejected(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"]) + [
        "modules/foundups/widget_demo/src/widget_demo_dae.py"
    ]
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_DENIED_PATH"


# --------------------------------------------------------------------------- #
# Boundary / imports
# --------------------------------------------------------------------------- #

_FORBIDDEN_IMPORT_TOKENS = (
    "hermes_adapter", "HermesFoundUpBuilder", "fam_adapter",
    "launch_foundup", "FoundUpJobConsumer",
)


def test_no_fam_hermes_imports() -> None:
    source = Path(scaffold_writer_dryrun.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(a.name for a in node.names)
    blob = " ".join(imported)
    offenders = [t for t in _FORBIDDEN_IMPORT_TOKENS if t in blob]
    assert offenders == [], f"writer imports forbidden dependency: {offenders}"


def test_live_writer_remains_absent() -> None:
    """The LIVE writer stays forbidden until the valve-gated slice."""
    repo = Path(__file__).resolve().parents[3]
    for live in (
        repo / "modules/foundups/agent/src/foundup_scaffold_writer.py",
        repo / "modules/foundups/src/foundup_scaffold_writer.py",
        repo / "modules/foundups/agent/src/scaffold_plan_executor.py",
    ):
        assert not live.exists(), f"LIVE writer must not exist yet: {live}"


# --------------------------------------------------------------------------- #
# Adversarial-sweep regressions (CoR findings on the default repo root and
# Win32 filename normalization). Each maps to a blocker/major the sweep found.
# --------------------------------------------------------------------------- #

def test_default_repo_root_rejects_in_repo_output_outside_modules(contract: dict) -> None:
    """SANDBOX_ESCAPE blocker: with the DEFAULT (real) repo root, an output_root
    inside the repo but outside modules/ must be refused before any write."""
    from modules.foundups.agent.src.scaffold_writer_dryrun import _default_repo_root

    repo = _default_repo_root()
    target = repo / "docs" / "__pytest_sandbox_escape_must_never_exist__"
    res = materialize_scaffold_dry_run(contract, output_root=target)  # default real_repo_root
    assert res.ok is False
    assert res.rejection_code == "FAIL_WRITE_TO_MAIN_REPO"
    assert not target.exists()


def test_default_repo_root_is_actual_repo_root() -> None:
    from modules.foundups.agent.src.scaffold_writer_dryrun import _default_repo_root

    repo = _default_repo_root()
    # Sentinel: the resolved root is the actual repo (has WSP_framework or .git),
    # NOT the modules/ subdirectory (the off-by-one the sweep found).
    assert (repo / "WSP_framework").exists() or (repo / ".git").exists()
    assert repo.name != "modules"


@pytest.mark.parametrize("bad_artifact,code", [
    ("modules/foundups/foundup_registry.json ", "FAIL_REGISTRY_OVERWRITE"),   # trailing space
    ("modules/foundups/FOUNDUP_REGISTRY.JSON", "FAIL_REGISTRY_OVERWRITE"),     # uppercase
    ("modules/foundups/foundup_registry.json:evil", "FAIL_PATH_TRAVERSAL"),    # NTFS ADS colon
    ("modules/foundups/widget_demo/.ENV", "FAIL_DENIED_PATH"),                 # uppercase denied
    ("modules/foundups/widget_demo/main.PY", "FAIL_DENIED_PATH"),              # uppercase denied
    ("modules/foundups/widget_demo/foo_DAE.py", "FAIL_DENIED_PATH"),           # uppercase dae
    ("modules/foundups/widget_demo/.env ", "FAIL_DENIED_PATH"),                # trailing-space denied
    ("modules/foundups/widget_demo/.. /x.txt", "FAIL_PATH_TRAVERSAL"),         # trailing-space dotdot
    ("modules/foundups/widget_demo/sub/../../../etc/x", "FAIL_PATH_TRAVERSAL"),# classic traversal
])
def test_win32_normalization_attacks_fail_closed(
    contract: dict, tmp_path: Path, bad_artifact: str, code: str
) -> None:
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"]) + [bad_artifact]
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == code, f"{bad_artifact} -> {res.rejection_code}"
    assert list(tmp_path.rglob("*")) == []  # nothing materialized on rejection


def test_extra_benign_artifact_rejected_by_exact_set(contract: dict, tmp_path: Path) -> None:
    """MAJOR (exact-14): a benign EXTRA artifact must be rejected, not materialized."""
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"]) + [
        "modules/foundups/widget_demo/extra_unplanned.txt"
    ]
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_ARTIFACT_SET_MISMATCH"
    assert list(tmp_path.rglob("*")) == []


def test_missing_artifact_rejected_by_exact_set(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"])[:-1]  # drop one of the 14
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_ARTIFACT_SET_MISMATCH"


# --------------------------------------------------------------------------- #
# Round-2 sweep regressions: ancestor/drive-root sandbox escape, narrowed
# real_repo_root, module_path pin, leading-space registry.
# --------------------------------------------------------------------------- #

def test_drive_root_output_rejected(contract: dict, tmp_path: Path) -> None:
    """output_root == a filesystem/drive root is not an isolated sandbox."""
    drive_root = Path(tmp_path.anchor)  # e.g. C:\ -- guard rejects BEFORE any write
    res = materialize_scaffold_dry_run(contract, output_root=drive_root)
    assert res.ok is False
    assert res.rejection_code == "FAIL_WRITE_TO_MAIN_REPO"


def test_repo_inside_output_root_rejected(contract: dict, tmp_path: Path) -> None:
    """Bidirectional guard: an output_root that CONTAINS a repo is refused."""
    fake_repo = tmp_path / "fakerepo"
    fake_repo.mkdir()
    res = materialize_scaffold_dry_run(
        contract, output_root=tmp_path, real_repo_root=fake_repo
    )
    assert res.ok is False
    assert res.rejection_code == "FAIL_WRITE_TO_MAIN_REPO"


def test_narrowed_real_repo_root_still_blocks_real_repo(contract: dict) -> None:
    """A caller-narrowed real_repo_root cannot unlock writes into the true repo:
    the default (sentinel-checked) repo root is ALWAYS also enforced."""
    from modules.foundups.agent.src.scaffold_writer_dryrun import _default_repo_root

    repo = _default_repo_root()
    target = repo / "docs" / "__pytest_narrowed_escape_must_never_exist__"
    res = materialize_scaffold_dry_run(
        contract, output_root=target,
        real_repo_root=repo / "modules" / "foundups" / "agent" / "src",  # narrowed lie
    )
    assert res.ok is False
    assert res.rejection_code == "FAIL_WRITE_TO_MAIN_REPO"
    assert not target.exists()


def test_module_path_pin_rejects_mismatch(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["module_path"] = "modules/foundups/widget_demo/nested/deep"  # not canonical
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_CONTRACT_INVALID"


def test_module_path_traversal_rejected(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["module_path"] = "../../../../Windows"
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_CONTRACT_INVALID"


def test_leading_space_registry_rejected(contract: dict, tmp_path: Path) -> None:
    bad = copy.deepcopy(contract)
    bad["scaffold_artifacts"] = list(bad["scaffold_artifacts"]) + [
        "modules/foundups/ foundup_registry.json"  # leading space before filename
    ]
    res = materialize_scaffold_dry_run(bad, output_root=tmp_path)
    assert res.ok is False
    assert res.rejection_code == "FAIL_REGISTRY_OVERWRITE"
