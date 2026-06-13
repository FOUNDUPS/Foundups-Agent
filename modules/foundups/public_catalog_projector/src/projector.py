"""Scope-free Public FoundUp Catalog projector + validator core (Phase 1).

This module derives a SCOPE-FREE PUBLIC CATALOG from the canonical registry
(``modules/foundups/foundup_registry.json``) and validates that the derived
projection contains ONLY public-allowlisted fields. It mirrors the existing
``portfolio_validator`` convention (drift detection vs registry) and the
``portfolio_data.json`` derived-projection pattern.

WHY (PlayFoundups Mall public-discovery audit, smallest-step #1): the public
``/f/`` surface today reads the MEMBER RUNTIME catalog
``public/member/mall-video-catalog.json`` WHOLE, client-side, with NO field
filtering. Any member-scoped field later added to that runtime catalog would
LEAK publicly. The fix is to project a scope-free public catalog from the
registry (single source of truth), validated to contain ONLY public
allowlisted fields, so the public surface can later read the PROJECTION instead
of the runtime catalog.

Sources (canonical hierarchy):
  L1 PRIMARY  - ``modules/foundups/foundup_registry.json`` (the ONLY source)
  DERIVED     - ``public/f/public_catalog.json`` (this projection)

The member runtime catalog ``public/member/mall-video-catalog.json`` is NOT a
source for this projection. Its member-scoped field keys are enumerated here
ONLY as the validator's forbidden set (leak guard) - the projection path never
reads that file.

Safety properties enforced FAIL-CLOSED by :func:`validate_projection`:
  (a) ALLOWLIST-ONLY: every field in every projection entry is on the public
      allowlist; ANY non-allowlisted field (especially a known member-scoped
      key) REJECTS the projection. This is the leak guard.
  (b) DERIVED-FROM-REGISTRY: every projection entry corresponds to a registry
      entry and its values match the registry projection (drift check); no
      invented entries.
  (c) NO dependency on the member runtime catalog in the projection path.

The module is side-effect-free except for :func:`write_projection`, which is
the explicit artifact-emit step. Validation never writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Constants -------------------------------------------------------------

REPO_ROOT_MARKERS = ("modules", "WSP_framework", "public")

DEFAULT_REGISTRY_PATH = Path("modules/foundups/foundup_registry.json")
DEFAULT_PROJECTION_PATH = Path("public/f/public_catalog.json")

# The member RUNTIME catalog. Listed ONLY so its member-scoped keys can seed the
# forbidden set below. The projection path NEVER reads this file.
MEMBER_RUNTIME_CATALOG_PATH = Path("public/member/mall-video-catalog.json")

# --- Public allowlist ------------------------------------------------------
#
# The ONLY fields permitted in a public catalog projection entry. Every field
# is sourced from the canonical registry (RegistryEntry) and is public-safe per
# the Mall public-discovery audit Section 5 (DISCOVERY = PUBLIC). Any field not
# in this set is rejected by the validator (allowlist-only leak guard).
#
# Mapping notes (registry source field -> projection field):
#   display_name        <- display_name
#   mission/pain/...    <- NOT YET in RegistryEntry (added by a later slice
#                          FOUNDUP_REGISTRY_NARRATIVE_FIELDS_PHASE1); projected
#                          straight through IF present so the projector is
#                          forward-compatible, but never invented.
#   token_symbol        <- token_symbol
#   readiness           <- poc_landing_status (registry)
#   lightpaper_url      <- NOT YET in RegistryEntry; projected through if present
#   poc_url / app_url   <- poc_url / app_url
PUBLIC_ALLOWLIST: Tuple[str, ...] = (
    "foundup_id",
    "display_name",
    "mission",
    "pain",
    "solution",
    "outcome",
    "token_symbol",
    "portfolio_status",
    "poc_landing_status",
    "lightpaper_url",
    "website_url",
    "poc_url",
    "app_url",
    "github_url",
    "docs_url",
    "screenshot_url",
    "public_summary",
    "portfolio_priority",
    "portfolio_ready",
    "is_dual_identity",
)
PUBLIC_ALLOWLIST_SET = frozenset(PUBLIC_ALLOWLIST)

# Registry source fields copied verbatim into the projection (subset of the
# allowlist that maps 1:1 to a RegistryEntry property of the same name). These
# are the fields the generator projects from the registry. Narrative fields
# (mission/pain/solution/outcome/lightpaper_url) are projected through IF the
# registry entry already carries them (forward-compat with the narrative-field
# slice) but are otherwise omitted - never invented.
REGISTRY_PROJECTED_FIELDS: Tuple[str, ...] = (
    "foundup_id",
    "display_name",
    "portfolio_status",
    "poc_landing_status",
    "website_url",
    "poc_url",
    "app_url",
    "github_url",
    "docs_url",
    "screenshot_url",
    "public_summary",
    "portfolio_priority",
    "portfolio_ready",
)

# Narrative/extension fields projected straight through ONLY when the registry
# entry already carries them (forward-compatible, never invented).
PASSTHROUGH_OPTIONAL_FIELDS: Tuple[str, ...] = (
    "mission",
    "pain",
    "solution",
    "outcome",
    "token_symbol",
    "lightpaper_url",
)

# Filter: only registry entries with one of these portfolio_status values are
# included in the public projection (mirrors the portfolio projection filter).
PORTFOLIO_ELIGIBLE_STATUSES = frozenset(
    {"portfolio_candidate", "portfolio_ready", "portfolio_featured"}
)

# Known member-scoped / runtime keys observed in the member runtime catalog
# (public/member/mall-video-catalog.json). Enumerated at Phase-0 inspection
# time; used to give the leak guard a concrete, named forbidden set in addition
# to the structural allowlist-only check. Any of these appearing in a
# projection entry is an explicit, named leak.
KNOWN_MEMBER_SCOPED_FIELDS: Tuple[str, ...] = (
    "videos",
    "video_count",
    "true_video_count",
    "subscriber_count",
    "creator",
    "creator_id",
    "creator_display",
    "channel_avatar_url",
    "source_handle",
    "source_id",
    "source_type",
    "parent_channels",
    "related_lanes",
    "data_namespace",
    "derivation_method",
    "routing_prefix",
    "entry_url",
    "entry_copy",
    "external_url",
    "poster_url",
    "display_order",
    "geo",
    "topic_family",
    "launch_readiness",
)
KNOWN_MEMBER_SCOPED_SET = frozenset(KNOWN_MEMBER_SCOPED_FIELDS)


# --- Errors ----------------------------------------------------------------


class SourceError(Exception):
    """Raised when a canonical source is missing or malformed (fail-closed)."""


# --- Data classes ----------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """A single validator finding. ``severity`` is always ``error`` for the
    fail-closed safety guards in this module."""

    rule_id: str
    severity: str
    entity: str
    field: str
    expected: Any
    actual: Any
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    """Structured validation result. ``violations`` is the canonical list."""

    violations: List[Violation] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    @property
    def has_errors(self) -> bool:
        return any(v.severity == "error" for v in self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def is_safe(self) -> bool:
        """Fail-closed: a projection is SAFE only when zero errors are found."""
        return not self.has_errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violations": [v.to_dict() for v in self.violations],
            "stats": self.stats,
            "summary": {
                "error_count": self.error_count,
                "total_violations": len(self.violations),
                "is_safe": self.is_safe,
            },
        }


# --- IO helpers ------------------------------------------------------------


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise SourceError(f"Source file missing: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise SourceError(f"Malformed JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise SourceError(f"Cannot read {path}: {exc}") from exc


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk upward from ``start`` (or this file) to find the repo root."""
    here = (start or Path(__file__)).resolve()
    if here.is_file():
        here = here.parent
    for candidate in [here, *here.parents]:
        if all((candidate / marker).exists() for marker in REPO_ROOT_MARKERS):
            return candidate
    raise SourceError(
        f"Cannot locate repo root from {here}; expected markers {REPO_ROOT_MARKERS}"
    )


def load_registry(repo_root: Path, registry_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and structurally validate the canonical registry (the ONLY source).

    The member runtime catalog is intentionally NOT loaded here: the projection
    path must never depend on it (leak guard C).
    """
    registry_path = repo_root / (registry_path or DEFAULT_REGISTRY_PATH)
    registry = _read_json(registry_path)
    if not isinstance(registry, dict) or "entities" not in registry:
        raise SourceError(f"Registry missing 'entities' array: {registry_path}")
    if not isinstance(registry["entities"], list):
        raise SourceError(f"Registry 'entities' must be a JSON array: {registry_path}")
    return registry


# --- Generator -------------------------------------------------------------


def _project_entry(registry_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Project ONE registry entry to a scope-free public catalog entry.

    Only allowlisted fields are emitted. ``foundup_id`` is always present.
    Narrative/extension fields are included ONLY if the registry entry already
    carries them (never invented).
    """
    out: Dict[str, Any] = {}
    for key in REGISTRY_PROJECTED_FIELDS:
        # foundup_id is mandatory; other registry-projected fields default to
        # the registry value (or None if absent, mirroring the portfolio
        # projection which carries explicit nulls).
        if key == "foundup_id":
            out[key] = registry_entry.get("foundup_id")
        else:
            out[key] = registry_entry.get(key, None)

    for key in PASSTHROUGH_OPTIONAL_FIELDS:
        if key in registry_entry and registry_entry[key] is not None:
            out[key] = registry_entry[key]

    # Derived public flag (mirrors portfolio projection C4 convention).
    if out.get("foundup_id") == "holoindex_prod_01":
        out["is_dual_identity"] = True

    return out


def generate_projection(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Derive the scope-free public catalog projection from the registry.

    Filters to portfolio-eligible entries, projects ONLY allowlisted fields,
    and sorts by ``portfolio_priority`` (nulls last) then ``foundup_id`` for a
    deterministic, diff-stable artifact.
    """
    entries: List[Dict[str, Any]] = []
    for reg_entry in registry["entities"]:
        if reg_entry.get("portfolio_status") in PORTFOLIO_ELIGIBLE_STATUSES:
            entries.append(_project_entry(reg_entry))

    def _sort_key(e: Dict[str, Any]) -> Tuple[Any, Any]:
        prio = e.get("portfolio_priority")
        prio_key = prio if isinstance(prio, int) and not isinstance(prio, bool) else 10**9
        return (prio_key, e.get("foundup_id") or "")

    entries.sort(key=_sort_key)
    return {
        "schema_version": "1.0.0",
        "projection": "public_catalog",
        "source": "modules/foundups/foundup_registry.json",
        "note": (
            "DERIVED scope-free public catalog. Generated from the canonical "
            "registry; contains ONLY public-allowlisted fields. Never "
            "hand-authored. Does NOT read public/member/mall-video-catalog.json."
        ),
        "entities": entries,
    }


# --- Validator (fail-closed safety) ----------------------------------------


def _index_registry(registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {e["foundup_id"]: e for e in registry["entities"] if "foundup_id" in e}


def _expected_projection_value(reg_entry: Dict[str, Any], key: str) -> Any:
    """The value the projection SHOULD carry for ``key`` given the registry."""
    if key in REGISTRY_PROJECTED_FIELDS:
        if key == "foundup_id":
            return reg_entry.get("foundup_id")
        return reg_entry.get(key, None)
    if key in PASSTHROUGH_OPTIONAL_FIELDS:
        return reg_entry.get(key, None)
    if key == "is_dual_identity":
        return True if reg_entry.get("foundup_id") == "holoindex_prod_01" else None
    return None


def rule_A_allowlist_only(projection: Dict[str, Any]) -> List[Violation]:
    """A: every projection field MUST be on the public allowlist (leak guard).

    Any field not on the allowlist REJECTS the projection. A field that is also
    a known member-scoped key is reported with that explicit framing.
    """
    out: List[Violation] = []
    for entity in projection["entities"]:
        fid = entity.get("foundup_id", "<missing>")
        for key in entity.keys():
            if key not in PUBLIC_ALLOWLIST_SET:
                is_member = key in KNOWN_MEMBER_SCOPED_SET
                out.append(
                    Violation(
                        rule_id="A",
                        severity="error",
                        entity=fid,
                        field=key,
                        expected="<field on PUBLIC_ALLOWLIST>",
                        actual=key,
                        message=(
                            f"Non-allowlisted field '{key}' in public projection"
                            + (
                                " (KNOWN MEMBER-SCOPED key - leak guard tripped)"
                                if is_member
                                else " (leak guard tripped)"
                            )
                        ),
                    )
                )
    return out


def rule_B_derived_from_registry(
    projection: Dict[str, Any], registry: Dict[str, Any]
) -> List[Violation]:
    """B: every projection entry MUST be derived from a registry entry.

    - No invented entries (every projection foundup_id exists in the registry).
    - Values match the registry projection (drift check) for every field.
    """
    out: List[Violation] = []
    reg = _index_registry(registry)
    for entity in projection["entities"]:
        fid = entity.get("foundup_id")
        if fid is None or fid not in reg:
            out.append(
                Violation(
                    rule_id="B",
                    severity="error",
                    entity=fid or "<missing>",
                    field="foundup_id",
                    expected="<present in foundup_registry.json>",
                    actual=fid,
                    message=(
                        f"Projection entry '{fid}' has no matching registry "
                        "entry (invented/orphan projection entry)"
                    ),
                )
            )
            continue
        reg_entry = reg[fid]
        for key, actual in entity.items():
            # Allowlist membership is rule A's job; here we only drift-check the
            # allowlisted fields against their registry-derived expected value.
            if key not in PUBLIC_ALLOWLIST_SET:
                continue
            expected = _expected_projection_value(reg_entry, key)
            if actual != expected:
                out.append(
                    Violation(
                        rule_id="B",
                        severity="error",
                        entity=fid,
                        field=key,
                        expected=expected,
                        actual=actual,
                        message=(
                            f"Field '{key}' drifts from registry: registry "
                            f"projects {expected!r}, projection has {actual!r}"
                        ),
                    )
                )
    return out


def rule_B_filter_completeness(
    projection: Dict[str, Any], registry: Dict[str, Any]
) -> List[Violation]:
    """B (filter): a not_portfolio registry entry MUST NOT appear in projection.

    Reinforces the derived-from-registry contract from the filter side so a
    leaked non-eligible entity is caught even if its fields happen to match.
    """
    out: List[Violation] = []
    reg = _index_registry(registry)
    proj_ids = {e.get("foundup_id") for e in projection["entities"]}
    for fid, reg_entry in reg.items():
        status = reg_entry.get("portfolio_status")
        if status not in PORTFOLIO_ELIGIBLE_STATUSES and fid in proj_ids:
            out.append(
                Violation(
                    rule_id="B",
                    severity="error",
                    entity=fid,
                    field="portfolio_status",
                    expected="<entity excluded: not portfolio-eligible>",
                    actual="present in projection",
                    message=(
                        f"Registry marks '{fid}' portfolio_status="
                        f"'{status}' (not eligible) but it appears in the "
                        "public projection"
                    ),
                )
            )
    return out


def validate_projection(
    projection: Dict[str, Any], registry: Dict[str, Any]
) -> ValidationReport:
    """Run every fail-closed safety rule and return a report.

    Pure: never mutates either input, never writes. The projection is SAFE
    (``report.is_safe``) only when zero error violations are found.
    """
    if not isinstance(projection, dict) or "entities" not in projection:
        raise SourceError("Projection missing 'entities' array")
    if not isinstance(projection["entities"], list):
        raise SourceError("Projection 'entities' must be a JSON array")

    report = ValidationReport()
    for v in rule_A_allowlist_only(projection):
        report.add(v)
    for v in rule_B_derived_from_registry(projection, registry):
        report.add(v)
    for v in rule_B_filter_completeness(projection, registry):
        report.add(v)

    eligible = sum(
        1
        for e in registry["entities"]
        if e.get("portfolio_status") in PORTFOLIO_ELIGIBLE_STATUSES
    )
    report.stats.update(
        {
            "registry_total": len(registry["entities"]),
            "registry_portfolio_eligible": eligible,
            "projection_total": len(projection["entities"]),
            "allowlist_size": len(PUBLIC_ALLOWLIST),
        }
    )
    return report


# --- Artifact emit ---------------------------------------------------------


def write_projection(
    projection: Dict[str, Any],
    repo_root: Path,
    projection_path: Optional[Path] = None,
) -> Path:
    """Write the derived projection artifact (the ONLY side-effecting function).

    Emits stable, sorted JSON so the committed artifact is diff-friendly.
    """
    out_path = repo_root / (projection_path or DEFAULT_PROJECTION_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(projection, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return out_path
