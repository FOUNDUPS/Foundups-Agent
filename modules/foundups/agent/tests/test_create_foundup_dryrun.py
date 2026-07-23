#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the create_foundup dry-run scaffold planner.

Slice: FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1
WSP:   49, 50, 97, 109

Proves:
    - Valid envelope -> dry-run plan with the full WSP-49 artifact set
    - The planned manifest passes the REAL foundup_manifest_validator
    - Registry seed carries genesis fields (specified, not written)
    - Existing foundup_id -> FAIL_FOUNDUP_ID_EXISTS
    - Invalid envelope -> FAIL_ENVELOPE_NOT_GATE_PASSED
    - create_foundup is canonical AND distinct from build/extract (no alias)
    - Dry-run only: no writes, no Hermes/FAM/registry/worktree
    - The planner imports no FAM/Hermes writer (AST guard)
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.foundups.agent.src import create_foundup_dryrun
from modules.foundups.agent.src.create_foundup_dryrun import (
    CREATE_ACTION,
    create_action_is_not_aliased,
    plan_create_foundup_dry_run,
)


def _valid_envelope(foundup_id: str = "widget_demo") -> dict:
    return {
        "foundup_id": foundup_id,
        "name": "Widget Demo",
        "tagline": "A tiny demo widget",
        "description": "A demonstration FoundUp for the create_foundup dry-run planner.",
        "category": "tools",
        "lifecycle_stage": "idea",
        "binding_state": "unbound",
        "external_repo_requested": False,
        "acceptance_criteria": [
            {"observable": "widget renders", "method": "pytest",
             "oracle": "returns HTML 200", "pass_condition": "status == 200"},
        ],
        "truth_state_map": [{"feature": foundup_id, "marker": "IDEA_ONLY", "evidence": ""}],
    }


def _registry(tmp_path: Path, ids) -> Path:
    p = tmp_path / "reg.json"
    entities = [
        {
            "foundup_id": foundup_id,
            "display_name": foundup_id,
            "entity_type": "foundup",
            "module_path": f"modules/foundups/{foundup_id}",
            "stage": "incubating",
            "tier": "F0_DAE",
            "implementation_status": "SPECIFIED",
            "token_status": "TOKEN_DEFERRED",
        }
        for foundup_id in ids
    ]
    p.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "last_updated": "2026-07-23T00:00:00Z",
                "entities": entities,
            }
        ),
        encoding="utf-8",
    )
    return p


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #

def test_valid_envelope_produces_plan(tmp_path: Path) -> None:
    res = plan_create_foundup_dry_run(_valid_envelope(), registry_path=_registry(tmp_path, []))
    assert res.ok is True, res.rejection_reason
    assert res.action == CREATE_ACTION
    assert res.rejection_code is None
    assert res.dry_run is True
    # Full WSP-49 artifact set (14 entries incl. memory/README.md).
    arts = res.planned_artifacts
    for suffix in (
        "/README.md", "/INTERFACE.md", "/ROADMAP.md", "/ModLog.md", "/requirements.txt",
        "/src/__init__.py", "/tests/TestModLog.md", "/memory/README.md", "/foundup_manifest.json",
    ):
        assert any(a.endswith(suffix) for a in arts), f"missing artifact: {suffix}"
    assert all(a.startswith("modules/foundups/widget_demo/") for a in arts)
    assert res.scaffold_contract["module_path"] == "modules/foundups/widget_demo"


def test_planned_manifest_passes_real_validator(tmp_path: Path) -> None:
    """The dry-run plan's manifest must satisfy the REAL manifest validator."""
    from modules.foundups.agent.src.foundup_manifest_validator import validate_manifest

    res = plan_create_foundup_dry_run(_valid_envelope(), registry_path=_registry(tmp_path, []))
    assert res.ok is True
    mv = validate_manifest(res.planned_manifest)  # no manifest_path -> skips on-disk equality
    assert mv.ok, mv.errors


def test_registry_seed_has_genesis_fields(tmp_path: Path) -> None:
    res = plan_create_foundup_dry_run(_valid_envelope(), registry_path=_registry(tmp_path, []))
    seed = res.planned_registry_seed
    assert seed["entity_type"] == "foundup"
    assert seed["stage"] == "incubating"
    assert seed["implementation_status"] == "SPECIFIED"
    assert seed["token_status"] == "TOKEN_DEFERRED"
    assert seed["module_path"] == "modules/foundups/widget_demo"


# --------------------------------------------------------------------------- #
# Fail-closed rejections
# --------------------------------------------------------------------------- #

def test_existing_foundup_id_rejected(tmp_path: Path) -> None:
    res = plan_create_foundup_dry_run(
        _valid_envelope("widget_demo"),
        registry_path=_registry(tmp_path, ["widget_demo"]),  # already exists
    )
    assert res.ok is False
    assert res.rejection_code == "FAIL_FOUNDUP_ID_EXISTS"
    assert res.scaffold_contract is None
    assert res.planned_artifacts == []


def test_invalid_envelope_rejected(tmp_path: Path) -> None:
    bad = _valid_envelope()
    bad["acceptance_criteria"] = []  # strict validator -> empty AC is an error
    res = plan_create_foundup_dry_run(bad, registry_path=_registry(tmp_path, []))
    assert res.ok is False
    assert res.rejection_code == "FAIL_ENVELOPE_NOT_GATE_PASSED"


def test_reserved_foundup_id_rejected_as_invalid(tmp_path: Path) -> None:
    # A reserved id (e.g. an infra name) fails genesis re-validation, not the
    # exists-check -> proves the planner is fail-closed before any planning.
    res = plan_create_foundup_dry_run(
        _valid_envelope("hermes"), registry_path=_registry(tmp_path, [])
    )
    assert res.ok is False
    assert res.rejection_code == "FAIL_ENVELOPE_NOT_GATE_PASSED"


@pytest.mark.parametrize(
    "registry_case",
    ["missing", "corrupt", "schema", "schema_enum", "directory"],
)
def test_registry_unavailable_fails_closed_with_stable_redacted_reason(
    tmp_path: Path,
    registry_case: str,
) -> None:
    registry_path = tmp_path / "sensitive-registry.json"
    if registry_case == "corrupt":
        registry_path.write_text("{not-json", encoding="utf-8")
    elif registry_case == "schema":
        registry_path.write_text(
            json.dumps({"entities": [{"foundup_id": 7}]}),
            encoding="utf-8",
        )
    elif registry_case == "schema_enum":
        registry_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "last_updated": "2026-07-23T00:00:00Z",
                    "entities": [
                        {
                            "foundup_id": "existing_demo",
                            "display_name": "Existing Demo",
                            "entity_type": "not_in_canonical_schema",
                            "module_path": "modules/foundups/existing_demo",
                            "implementation_status": "SPECIFIED",
                            "token_status": "TOKEN_DEFERRED",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    elif registry_case == "directory":
        registry_path.mkdir()

    result = plan_create_foundup_dry_run(
        _valid_envelope(),
        registry_path=registry_path,
    )

    assert result.ok is False
    assert result.rejection_code == "FAIL_REGISTRY_UNAVAILABLE"
    assert result.rejection_reason == "FoundUp registry unavailable or invalid"
    assert str(registry_path) not in result.rejection_reason
    assert result.planned_artifacts == []


def test_planning_is_deterministic_when_created_at_is_omitted(tmp_path: Path) -> None:
    envelope = _valid_envelope()
    registry_path = _registry(tmp_path, [])

    first = plan_create_foundup_dry_run(
        envelope,
        actor_id="tenant-a",
        registry_path=registry_path,
    )
    second = plan_create_foundup_dry_run(
        envelope,
        actor_id="tenant-a",
        registry_path=registry_path,
    )

    assert first.to_dict() == second.to_dict()


def test_happy_registry_fixture_validates_against_canonical_schema(
    tmp_path: Path,
) -> None:
    from jsonschema import Draft202012Validator

    registry = json.loads(_registry(tmp_path, ["existing_demo"]).read_text())
    schema_path = (
        Path(create_foundup_dryrun.__file__).resolve().parents[2]
        / "foundup_registry.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert list(Draft202012Validator(schema).iter_errors(registry)) == []


def test_planner_entrypoint_stays_below_wsp62_function_limit() -> None:
    source = Path(create_foundup_dryrun.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "plan_create_foundup_dry_run"
    )

    assert function.end_lineno - function.lineno + 1 <= 75


# --------------------------------------------------------------------------- #
# No-alias + dry-run boundary
# --------------------------------------------------------------------------- #

def test_create_action_canonical_and_distinct() -> None:
    from modules.communication.moltbot_bridge.src.foundup_job_contract import (
        CANONICAL_ACTIONS,
        EXISTING_MODULE_ACTIONS,
    )

    assert CREATE_ACTION in CANONICAL_ACTIONS
    assert CREATE_ACTION not in EXISTING_MODULE_ACTIONS
    assert "build_foundup" in EXISTING_MODULE_ACTIONS
    assert "extract_foundup" in EXISTING_MODULE_ACTIONS
    assert create_action_is_not_aliased() is True


def test_dry_run_only_no_writes(tmp_path: Path) -> None:
    res = plan_create_foundup_dry_run(_valid_envelope(), registry_path=_registry(tmp_path, []))
    assert res.dry_run is True
    assert res.files_written == []
    assert res.fam_called is False
    assert res.hermes_called is False
    assert res.registry_mutated is False
    assert res.worktree_created is False
    assert res.valve_state_required == "VALVE_OPEN_WORKTREE_CREATE"
    # The plan wrote no scaffold to disk.
    assert not (tmp_path / "modules").exists()


def test_contract_path_scope(tmp_path: Path) -> None:
    res = plan_create_foundup_dry_run(_valid_envelope(), registry_path=_registry(tmp_path, []))
    c = res.scaffold_contract
    assert c["allowed_paths"] == ["modules/foundups/widget_demo/**"]
    for marker in (".env", "main.py", "vendor"):
        assert marker in c["denied_paths"]
    assert any("_dae.py" in p for p in c["denied_paths"])
    assert c["write_owner"] == "hermes"


_FORBIDDEN_IMPORT_TOKENS = (
    "hermes_adapter", "HermesFoundUpBuilder", "fam_adapter",
    "launch_foundup", "FoundUpJobConsumer",
)


def test_no_fam_hermes_imports() -> None:
    source = Path(create_foundup_dryrun.__file__).read_text(encoding="utf-8")
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
    assert offenders == [], f"planner imports forbidden writer(s): {offenders}"
