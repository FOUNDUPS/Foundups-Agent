"""Tests for the Portfolio Data Validator (Phase 1).

Coverage strategy:
  - Synthetic fixtures exercising each rule's pass case and fail case in
    isolation.
  - Real-repo tests proving the two architect-identified drifts are caught
    against the current repo state.
  - Failure-mode tests for missing/malformed JSON inputs (exit code 2).
"""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from modules.foundups.portfolio_validator.src.validator import (
    RULES,
    SourceError,
    Sources,
    Violation,
    find_repo_root,
    load_sources,
    rule_C1,
    rule_C2,
    rule_C3,
    rule_C4,
    rule_R1,
    rule_R2,
    rule_R3,
    rule_R4,
    rule_R5,
    rule_R6,
    rule_R7,
    rule_R8,
    rule_R9,
    rule_R10,
    rule_R11,
    run_validation,
)


# --- Synthetic fixture helpers --------------------------------------------


def _baseline_sources() -> Sources:
    """A clean baseline with one well-formed registry entry and matching projection."""
    registry = {
        "schema_version": "1.0.0",
        "last_updated": "2026-05-22T00:00:00Z",
        "entities": [
            {
                "foundup_id": "alpha",
                "display_name": "Alpha",
                "entity_type": "foundup",
                "module_path": "modules/foundups/alpha",
                "implementation_status": "IMPLEMENTED",
                "token_status": "EXISTS",
                "token_symbol": "ALPHA",
                "portfolio_status": "portfolio_candidate",
                "poc_landing_status": "functional",
                "portfolio_priority": 1,
                "portfolio_ready": False,
                "public_summary": "Alpha foundup",
            }
        ],
    }
    projection = {
        "entities": [
            {
                "foundup_id": "alpha",
                "display_name": "Alpha",
                "portfolio_status": "portfolio_candidate",
                "poc_landing_status": "functional",
                "website_url": None,
                "poc_url": "https://example.com/alpha",
                "app_url": None,
                "github_url": None,
                "docs_url": None,
                "screenshot_url": None,
                "public_summary": "Alpha foundup",
                "portfolio_priority": 1,
                "portfolio_ready": False,
            }
        ]
    }
    return Sources(
        registry=registry,
        catalog=[],
        projection=projection,
        manifests={},
        paths={},
    )


# --- Sanity / structure tests --------------------------------------------


def test_rules_registry_covers_full_spec():
    expected = {f"R{i}" for i in range(1, 12)} | {f"C{i}" for i in range(1, 5)}
    actual = {rid for rid, _ in RULES}
    assert actual == expected, f"Rule coverage gap: missing={expected - actual}"


def test_baseline_passes_all_rules():
    report = run_validation(_baseline_sources())
    assert report.violations == [], (
        f"Baseline produced violations: {[v.to_dict() for v in report.violations]}"
    )


# --- R1: projection entity missing from registry --------------------------


def test_R1_pass():
    assert rule_R1(_baseline_sources()) == []


def test_R1_fail_when_projection_id_missing_from_registry():
    s = _baseline_sources()
    s.projection["entities"][0]["foundup_id"] = "ghost"
    violations = rule_R1(s)
    assert len(violations) == 1
    assert violations[0].rule_id == "R1"
    assert violations[0].severity == "error"
    assert violations[0].entity == "ghost"


# --- R2: foundup_id case/format mismatch ---------------------------------


def test_R2_pass_exact_match():
    assert rule_R2(_baseline_sources()) == []


def test_R2_fail_case_mismatch():
    s = _baseline_sources()
    s.projection["entities"][0]["foundup_id"] = "ALPHA"
    violations = rule_R2(s)
    assert len(violations) == 1
    assert violations[0].rule_id == "R2"


# --- R3: portfolio_status enum -------------------------------------------


def test_R3_pass_valid_enum():
    assert rule_R3(_baseline_sources()) == []


def test_R3_fail_invalid_enum():
    s = _baseline_sources()
    s.projection["entities"][0]["portfolio_status"] = "not_a_status"
    violations = rule_R3(s)
    assert len(violations) == 1
    assert violations[0].severity == "error"


# --- R4: poc_landing_status enum -----------------------------------------


def test_R4_pass_valid_enum():
    assert rule_R4(_baseline_sources()) == []


def test_R4_fail_invalid_enum():
    s = _baseline_sources()
    s.projection["entities"][0]["poc_landing_status"] = "wibble"
    violations = rule_R4(s)
    assert len(violations) == 1
    assert violations[0].severity == "error"


# --- R5: URL fields valid http(s) or null --------------------------------


def test_R5_pass_null_and_valid_url():
    assert rule_R5(_baseline_sources()) == []


def test_R5_fail_malformed_url():
    s = _baseline_sources()
    s.projection["entities"][0]["poc_url"] = "not a url"
    violations = rule_R5(s)
    assert len(violations) == 1
    assert violations[0].severity == "warning"
    assert violations[0].field == "poc_url"


# --- R6: public_summary <= 280 -------------------------------------------


def test_R6_pass_short_summary():
    assert rule_R6(_baseline_sources()) == []


def test_R6_fail_long_summary():
    s = _baseline_sources()
    s.projection["entities"][0]["public_summary"] = "x" * 281
    violations = rule_R6(s)
    assert len(violations) == 1
    assert violations[0].severity == "warning"
    assert violations[0].actual == 281


# --- R7: portfolio_priority int 1..100 or null ---------------------------


def test_R7_pass_int_and_null():
    s = _baseline_sources()
    assert rule_R7(s) == []
    s.projection["entities"][0]["portfolio_priority"] = None
    assert rule_R7(s) == []


def test_R7_fail_out_of_range():
    s = _baseline_sources()
    s.projection["entities"][0]["portfolio_priority"] = 0
    violations = rule_R7(s)
    assert len(violations) == 1
    assert violations[0].severity == "error"


def test_R7_fail_wrong_type():
    s = _baseline_sources()
    s.projection["entities"][0]["portfolio_priority"] = "one"
    violations = rule_R7(s)
    assert len(violations) == 1


# --- R8: portfolio_status match registry ---------------------------------


def test_R8_pass_match():
    assert rule_R8(_baseline_sources()) == []


def test_R8_fail_drift():
    s = _baseline_sources()
    s.projection["entities"][0]["portfolio_status"] = "portfolio_ready"
    violations = rule_R8(s)
    assert len(violations) == 1
    assert violations[0].expected == "portfolio_candidate"
    assert violations[0].actual == "portfolio_ready"


# --- R9: portfolio_ready match registry ----------------------------------


def test_R9_pass_match():
    assert rule_R9(_baseline_sources()) == []


def test_R9_fail_drift():
    s = _baseline_sources()
    s.projection["entities"][0]["portfolio_ready"] = True
    violations = rule_R9(s)
    assert len(violations) == 1
    assert violations[0].expected is False
    assert violations[0].actual is True


# --- R10: projection count == portfolio-eligible registry count ----------


def test_R10_pass_when_counts_align():
    assert rule_R10(_baseline_sources()) == []


def test_R10_fail_when_projection_overcounts():
    s = _baseline_sources()
    # Add a not_portfolio registry entry plus a matching projection entry.
    s.projection["entities"].append(
        {
            "foundup_id": "beta",
            "display_name": "Beta",
            "portfolio_status": "not_portfolio",
            "poc_landing_status": "none",
            "portfolio_priority": None,
            "portfolio_ready": False,
            "website_url": None,
            "poc_url": None,
            "app_url": None,
            "github_url": None,
            "docs_url": None,
            "screenshot_url": None,
            "public_summary": None,
        }
    )
    violations = rule_R10(s)
    assert len(violations) == 1
    assert violations[0].severity == "warning"
    assert violations[0].expected == 1
    assert violations[0].actual == 2


# --- R11: no orphan projection entries -----------------------------------


def test_R11_pass():
    assert rule_R11(_baseline_sources()) == []


def test_R11_fail_orphan():
    s = _baseline_sources()
    s.projection["entities"].append(
        {
            "foundup_id": "phantom",
            "display_name": "Phantom",
            "portfolio_status": "portfolio_candidate",
            "poc_landing_status": "functional",
            "portfolio_priority": 2,
            "portfolio_ready": False,
            "website_url": None,
            "poc_url": None,
            "app_url": None,
            "github_url": None,
            "docs_url": None,
            "screenshot_url": None,
            "public_summary": None,
        }
    )
    violations = rule_R11(s)
    assert len(violations) == 1
    assert violations[0].entity == "phantom"


# --- C1: portfolio_ready=true => poc_landing_status != none --------------


def test_C1_pass_when_ready_false():
    assert rule_C1(_baseline_sources()) == []


def test_C1_fail_ready_with_no_landing():
    s = _baseline_sources()
    s.projection["entities"][0]["portfolio_ready"] = True
    s.projection["entities"][0]["poc_landing_status"] = "none"
    violations = rule_C1(s)
    assert len(violations) == 1
    assert violations[0].severity == "warning"


# --- C2: portfolio_featured => portfolio_ready=true ----------------------


def test_C2_pass_when_not_featured():
    assert rule_C2(_baseline_sources()) == []


def test_C2_fail_featured_without_ready():
    s = _baseline_sources()
    s.projection["entities"][0]["portfolio_status"] = "portfolio_featured"
    s.projection["entities"][0]["portfolio_ready"] = False
    violations = rule_C2(s)
    assert len(violations) == 1
    assert violations[0].severity == "error"


# --- C3: not_portfolio entities MUST NOT appear in projection ------------


def test_C3_pass_when_not_portfolio_not_in_projection():
    s = _baseline_sources()
    s.registry["entities"].append(
        {
            "foundup_id": "hidden",
            "display_name": "Hidden",
            "entity_type": "foundup",
            "module_path": "modules/foundups/hidden",
            "implementation_status": "IMPLEMENTED",
            "token_status": "NOT_APPLICABLE",
            "portfolio_status": "not_portfolio",
        }
    )
    assert rule_C3(s) == []


def test_C3_fail_when_not_portfolio_appears_in_projection():
    s = _baseline_sources()
    # Change alpha's registry status to not_portfolio - it now must not appear.
    s.registry["entities"][0]["portfolio_status"] = "not_portfolio"
    violations = rule_C3(s)
    assert len(violations) == 1
    assert violations[0].severity == "error"
    assert violations[0].entity == "alpha"


# --- C4: HoloIndex is_dual_identity --------------------------------------


def test_C4_pass_when_holoindex_marked_dual_identity():
    s = _baseline_sources()
    s.registry["entities"].append(
        {
            "foundup_id": "holoindex_prod_01",
            "display_name": "HoloIndex",
            "entity_type": "infra_service",
            "module_path": "modules/foundups/holoindex_prod_01",
            "implementation_status": "IMPLEMENTED",
            "token_status": "EXISTS",
            "token_symbol": "HOLO",
            "portfolio_status": "portfolio_candidate",
            "poc_landing_status": "polished",
            "portfolio_priority": 3,
            "portfolio_ready": False,
        }
    )
    s.projection["entities"].append(
        {
            "foundup_id": "holoindex_prod_01",
            "display_name": "HoloIndex",
            "portfolio_status": "portfolio_candidate",
            "poc_landing_status": "polished",
            "is_dual_identity": True,
            "portfolio_priority": 3,
            "portfolio_ready": False,
            "website_url": None,
            "poc_url": None,
            "app_url": None,
            "github_url": None,
            "docs_url": None,
            "screenshot_url": None,
            "public_summary": "HoloIndex dual identity",
        }
    )
    assert rule_C4(s) == []


def test_C4_fail_when_holoindex_missing_dual_identity():
    s = _baseline_sources()
    s.projection["entities"].append(
        {
            "foundup_id": "holoindex_prod_01",
            "display_name": "HoloIndex",
            "portfolio_status": "portfolio_candidate",
            "poc_landing_status": "polished",
            "portfolio_priority": 3,
            "portfolio_ready": False,
            "website_url": None,
            "poc_url": None,
            "app_url": None,
            "github_url": None,
            "docs_url": None,
            "screenshot_url": None,
            "public_summary": "HoloIndex without dual identity flag",
        }
    )
    violations = rule_C4(s)
    assert len(violations) == 1
    assert violations[0].severity == "warning"


# --- Real-repo drift detection -------------------------------------------


@pytest.fixture(scope="module")
def real_sources() -> Sources:
    return load_sources(find_repo_root())


def test_real_repo_detects_holoindex_missing_from_registry(real_sources):
    """Architect-identified drift #1: holoindex_prod_01 in projection but NOT in registry."""
    report = run_validation(real_sources)
    rule_ids = [v.rule_id for v in report.violations if v.entity == "holoindex_prod_01"]
    assert "R1" in rule_ids
    assert "R11" in rule_ids


def test_real_repo_detects_count_mismatch(real_sources):
    """Architect-identified drift #2: projection count != portfolio-eligible registry count."""
    report = run_validation(real_sources)
    r10 = [v for v in report.violations if v.rule_id == "R10"]
    assert len(r10) == 1
    # Two architect-identified portfolio candidates (gotjunk_001, kosei) in registry,
    # three in projection.
    assert r10[0].expected == 2
    assert r10[0].actual == 3


def test_real_repo_does_not_claim_holoindex_is_not_portfolio(real_sources):
    """Negative test: validator must NOT fabricate a 'registry says not_portfolio' claim
    when the entity does not actually exist in the registry."""
    report = run_validation(real_sources)
    for v in report.violations:
        if v.entity == "holoindex_prod_01" and v.rule_id in {"R8", "R9", "C3"}:
            pytest.fail(
                f"Validator falsely cited registry drift for an entity that does not "
                f"exist in the registry: {v.to_dict()}"
            )


def test_real_repo_stats_capture_full_inventory(real_sources):
    """Total registry inventory coverage stat must be reported separately from R10."""
    report = run_validation(real_sources)
    assert report.stats["registry_total"] == 14
    assert report.stats["projection_total"] == 3
    assert report.stats["registry_portfolio_eligible"] == 2
    coverage = report.stats["registry_inventory_coverage"]
    assert coverage["registry_total"] == 14
    assert coverage["projection_total"] == 3
    assert coverage["delta"] == 11


# --- CLI / fail-closed input handling ------------------------------------


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_cli_exit_code_2_when_projection_missing(tmp_path: Path):
    repo = tmp_path
    (repo / "modules/foundups").mkdir(parents=True)
    (repo / "WSP_framework").mkdir()
    (repo / "public/member").mkdir(parents=True)
    (repo / "public/f").mkdir(parents=True)
    _write_json(
        repo / "modules/foundups/foundup_registry.json",
        {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-22T00:00:00Z",
            "entities": [],
        },
    )
    _write_json(repo / "public/member/mall-video-catalog.json", [])
    # projection_data.json intentionally NOT created.

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.foundups.portfolio_validator",
            "--check",
            "--repo-root",
            str(repo),
        ],
        cwd=str(find_repo_root()),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"Expected exit 2 for missing projection, got {result.returncode}. "
        f"stderr={result.stderr!r}"
    )


def test_cli_exit_code_2_when_projection_malformed(tmp_path: Path):
    repo = tmp_path
    (repo / "modules/foundups").mkdir(parents=True)
    (repo / "WSP_framework").mkdir()
    (repo / "public/member").mkdir(parents=True)
    (repo / "public/f").mkdir(parents=True)
    _write_json(
        repo / "modules/foundups/foundup_registry.json",
        {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-22T00:00:00Z",
            "entities": [],
        },
    )
    _write_json(repo / "public/member/mall-video-catalog.json", [])
    (repo / "public/f/portfolio_data.json").write_text(
        "{not: valid json,", encoding="utf-8"
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.foundups.portfolio_validator",
            "--check",
            "--repo-root",
            str(repo),
        ],
        cwd=str(find_repo_root()),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_cli_exit_code_1_against_current_repo():
    """Running against the real repo must surface drift => exit 1."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.foundups.portfolio_validator",
            "--check",
        ],
        cwd=str(find_repo_root()),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "R1" in result.stdout or "R11" in result.stdout


def test_cli_json_output_is_parseable():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.foundups.portfolio_validator",
            "--check",
            "--json",
        ],
        cwd=str(find_repo_root()),
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert "violations" in payload
    assert "stats" in payload
    assert "summary" in payload


# --- Read-only guarantee: no mutation occurs during validation -----------


def test_validation_does_not_mutate_sources():
    """Defensive: validator must not mutate the loaded source dicts."""
    s = _baseline_sources()
    registry_before = deepcopy(s.registry)
    catalog_before = deepcopy(s.catalog)
    projection_before = deepcopy(s.projection)
    run_validation(s)
    assert s.registry == registry_before
    assert s.catalog == catalog_before
    assert s.projection == projection_before


def test_load_sources_raises_on_missing_registry(tmp_path: Path):
    with pytest.raises(SourceError):
        load_sources(tmp_path)
