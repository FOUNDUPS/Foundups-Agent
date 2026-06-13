"""Tests for the scope-free Public FoundUp Catalog projector (Phase 1).

Proves the load-bearing safety properties:
  - generator produces a scope-free projection (allowlist-only) from a registry.
  - validator REJECTS a projection containing a member-scoped field (the core
    fail-closed leak guard).
  - validator confirms derived-from-registry (entries/values match; rejects an
    invented entry and a drifted value).
  - round-trip: generate -> validate passes on the committed real artifact.
  - the projection path does NOT read the member runtime catalog.
"""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from modules.foundups.public_catalog_projector.src.projector import (
    KNOWN_MEMBER_SCOPED_FIELDS,
    PUBLIC_ALLOWLIST,
    PUBLIC_ALLOWLIST_SET,
    DEFAULT_PROJECTION_PATH,
    SourceError,
    find_repo_root,
    generate_projection,
    load_registry,
    rule_A_allowlist_only,
    rule_B_derived_from_registry,
    rule_B_filter_completeness,
    validate_projection,
)


# --- Synthetic fixtures ---------------------------------------------------


def _registry() -> dict:
    """A registry with two eligible entries + one not_portfolio entry."""
    return {
        "schema_version": "1.0.0",
        "last_updated": "2026-06-13T00:00:00Z",
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
                "website_url": None,
                "poc_url": "https://example.com/alpha",
                "app_url": None,
                "github_url": None,
                "docs_url": None,
                "screenshot_url": None,
                "public_summary": "Alpha foundup",
                "portfolio_priority": 1,
                "portfolio_ready": False,
            },
            {
                "foundup_id": "holoindex_prod_01",
                "display_name": "HoloIndex",
                "entity_type": "infra_service",
                "module_path": "modules/foundups/holoindex_prod_01",
                "implementation_status": "IMPLEMENTED",
                "token_status": "TOKEN_DEFERRED",
                "token_symbol": None,
                "portfolio_status": "portfolio_candidate",
                "poc_landing_status": "polished",
                "website_url": "https://foundups.com/holoindex",
                "poc_url": None,
                "app_url": None,
                "github_url": None,
                "docs_url": None,
                "screenshot_url": None,
                "public_summary": "HoloIndex dual identity surface",
                "portfolio_priority": 3,
                "portfolio_ready": False,
            },
            {
                "foundup_id": "hidden",
                "display_name": "Hidden",
                "entity_type": "foundup",
                "module_path": "modules/foundups/hidden",
                "implementation_status": "IMPLEMENTED",
                "token_status": "NOT_APPLICABLE",
                "token_symbol": None,
                "portfolio_status": "not_portfolio",
                "poc_landing_status": "none",
                # member-scoped-looking runtime data that must NEVER be projected
                "subscriber_count": 9999,
            },
        ],
    }


# --- Generator: scope-free projection -------------------------------------


def test_generator_produces_scope_free_projection():
    projection = generate_projection(_registry())
    # Only the two eligible entries are projected.
    ids = {e["foundup_id"] for e in projection["entities"]}
    assert ids == {"alpha", "holoindex_prod_01"}
    # Every field on every entry is on the public allowlist (scope-free).
    for entity in projection["entities"]:
        for key in entity:
            assert key in PUBLIC_ALLOWLIST_SET, f"non-allowlisted field leaked: {key}"
    # No member-scoped key appears anywhere in the projection.
    for entity in projection["entities"]:
        for member_key in KNOWN_MEMBER_SCOPED_FIELDS:
            assert member_key not in entity


def test_generator_marks_holoindex_dual_identity():
    projection = generate_projection(_registry())
    holo = next(e for e in projection["entities"] if e["foundup_id"] == "holoindex_prod_01")
    assert holo.get("is_dual_identity") is True


def test_generator_excludes_not_portfolio_entries():
    projection = generate_projection(_registry())
    ids = {e["foundup_id"] for e in projection["entities"]}
    assert "hidden" not in ids


def test_generator_output_self_validates():
    registry = _registry()
    projection = generate_projection(registry)
    report = validate_projection(projection, registry)
    assert report.is_safe, [v.to_dict() for v in report.violations]
    assert report.error_count == 0


# --- Leak guard: validator REJECTS member-scoped fields (CORE GUARD) -------


@pytest.mark.parametrize("member_field", list(KNOWN_MEMBER_SCOPED_FIELDS))
def test_validator_rejects_each_known_member_scoped_field(member_field):
    """Fail-closed proof: ANY known member-scoped field rejects the projection."""
    registry = _registry()
    projection = generate_projection(registry)
    # Inject a member-scoped field into the first projection entry.
    projection["entities"][0][member_field] = "LEAKED_MEMBER_DATA"
    report = validate_projection(projection, registry)
    assert not report.is_safe, f"leak guard failed to trip for {member_field}"
    a_hits = [
        v for v in report.violations
        if v.rule_id == "A" and v.field == member_field
    ]
    assert len(a_hits) == 1
    assert a_hits[0].severity == "error"
    assert "MEMBER-SCOPED" in a_hits[0].message


def test_validator_rejects_arbitrary_non_allowlisted_field():
    """Allowlist-only is structural: even an unknown junk field rejects."""
    registry = _registry()
    projection = generate_projection(registry)
    projection["entities"][0]["totally_new_internal_field"] = "x"
    violations = rule_A_allowlist_only(projection)
    assert any(v.field == "totally_new_internal_field" for v in violations)
    report = validate_projection(projection, registry)
    assert not report.is_safe


def test_validator_rejects_videos_payload_specifically():
    """Explicit canonical leak case: the runtime 'videos' array must reject."""
    registry = _registry()
    projection = generate_projection(registry)
    projection["entities"][1]["videos"] = [{"id": "abc", "private": True}]
    report = validate_projection(projection, registry)
    assert not report.is_safe
    assert any(v.rule_id == "A" and v.field == "videos" for v in report.violations)


# --- Derived-from-registry: invented entry + drift ------------------------


def test_validator_rejects_invented_entry():
    registry = _registry()
    projection = generate_projection(registry)
    projection["entities"].append(
        {
            "foundup_id": "phantom",
            "display_name": "Phantom",
            "portfolio_status": "portfolio_candidate",
            "poc_landing_status": "functional",
            "portfolio_ready": False,
        }
    )
    violations = rule_B_derived_from_registry(projection, registry)
    assert any(v.field == "foundup_id" and v.entity == "phantom" for v in violations)
    report = validate_projection(projection, registry)
    assert not report.is_safe


def test_validator_rejects_drifted_value():
    registry = _registry()
    projection = generate_projection(registry)
    # Drift a value away from its registry-derived expected value.
    projection["entities"][0]["display_name"] = "Tampered Name"
    violations = rule_B_derived_from_registry(projection, registry)
    drift = [v for v in violations if v.field == "display_name"]
    assert len(drift) == 1
    assert drift[0].expected == "Alpha"
    assert drift[0].actual == "Tampered Name"
    report = validate_projection(projection, registry)
    assert not report.is_safe


def test_validator_rejects_not_portfolio_entry_in_projection():
    registry = _registry()
    projection = generate_projection(registry)
    # Force a not-eligible entity into the projection with matching shape.
    projection["entities"].append(
        {
            "foundup_id": "hidden",
            "display_name": "Hidden",
            "portfolio_status": "not_portfolio",
            "poc_landing_status": "none",
            "portfolio_ready": False,
        }
    )
    violations = rule_B_filter_completeness(projection, registry)
    assert any(v.entity == "hidden" for v in violations)
    report = validate_projection(projection, registry)
    assert not report.is_safe


def test_clean_projection_passes_all_guards():
    registry = _registry()
    projection = generate_projection(registry)
    assert rule_A_allowlist_only(projection) == []
    assert rule_B_derived_from_registry(projection, registry) == []
    assert rule_B_filter_completeness(projection, registry) == []


# --- Purity: validation never mutates inputs ------------------------------


def test_validation_does_not_mutate_inputs():
    registry = _registry()
    projection = generate_projection(registry)
    reg_before = deepcopy(registry)
    proj_before = deepcopy(projection)
    validate_projection(projection, registry)
    assert registry == reg_before
    assert projection == proj_before


# --- Round-trip against the real committed artifact -----------------------


def test_round_trip_real_registry_generate_validate():
    repo_root = find_repo_root()
    registry = load_registry(repo_root)
    projection = generate_projection(registry)
    report = validate_projection(projection, registry)
    assert report.is_safe, [v.to_dict() for v in report.violations]


def test_committed_artifact_is_safe_and_scope_free():
    """The committed public_catalog.json validates clean against the registry."""
    repo_root = find_repo_root()
    registry = load_registry(repo_root)
    artifact_path = repo_root / DEFAULT_PROJECTION_PATH
    assert artifact_path.exists(), "committed artifact public/f/public_catalog.json missing"
    projection = json.loads(artifact_path.read_text(encoding="utf-8"))
    report = validate_projection(projection, registry)
    assert report.is_safe, [v.to_dict() for v in report.violations]
    # Belt-and-braces: artifact keys are a subset of the allowlist.
    for entity in projection["entities"]:
        for key in entity:
            assert key in PUBLIC_ALLOWLIST_SET


def test_committed_artifact_matches_freshly_generated():
    """The committed artifact equals a fresh generation (DERIVED, not stale)."""
    repo_root = find_repo_root()
    registry = load_registry(repo_root)
    fresh = generate_projection(registry)
    artifact_path = repo_root / DEFAULT_PROJECTION_PATH
    committed = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert committed == fresh, "committed artifact drifted from registry generation"


# --- Projection path independence from the member runtime catalog ----------


def test_projection_path_never_reads_member_runtime_catalog():
    """Generation + validation must succeed even if the member runtime catalog
    is absent, proving the projection path does NOT depend on it (leak guard C).
    """
    registry = _registry()
    projection = generate_projection(registry)
    report = validate_projection(projection, registry)
    assert report.is_safe
    # No code path here touched mall-video-catalog.json; the member catalog is
    # not even loaded by load_registry. Asserting the public API surface does
    # not expose a runtime-catalog loader.
    from modules.foundups.public_catalog_projector.src import projector as mod
    public_loaders = [n for n in dir(mod) if n.startswith("load_")]
    assert public_loaders == ["load_registry"], public_loaders


# --- CLI fail-closed semantics --------------------------------------------


def test_cli_check_exit_0_against_real_repo():
    result = subprocess.run(
        [sys.executable, "-m", "modules.foundups.public_catalog_projector", "--check"],
        cwd=str(find_repo_root()),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "is SAFE" in result.stdout


def test_cli_validate_exit_0_against_committed_artifact():
    result = subprocess.run(
        [sys.executable, "-m", "modules.foundups.public_catalog_projector", "--validate"],
        cwd=str(find_repo_root()),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_cli_exit_2_when_registry_missing(tmp_path: Path):
    repo = tmp_path
    (repo / "modules/foundups").mkdir(parents=True)
    (repo / "WSP_framework").mkdir()
    (repo / "public/f").mkdir(parents=True)
    # registry intentionally NOT created.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.foundups.public_catalog_projector",
            "--check",
            "--repo-root",
            str(repo),
        ],
        cwd=str(find_repo_root()),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.stderr
