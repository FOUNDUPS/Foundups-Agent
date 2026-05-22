"""Portfolio Data Validator core (Phase 1).

Read-only drift detector for ``public/f/portfolio_data.json``.

Sources (canonical hierarchy per spec section 1):
  L1 PRIMARY  - ``modules/foundups/foundup_registry.json``
  L2 RUNTIME  - ``public/member/mall-video-catalog.json``
  L3 DETAIL   - ``modules/foundups/<id>/foundup_manifest.json``
  DERIVED     - ``public/f/portfolio_data.json``

Rules implemented (spec section 6):
  R1-R7   structural validation
  R8-R11  source-of-truth validation
  C1-C4   consistency checks

The module is intentionally side-effect-free: ``run_validation`` returns a
report object; nothing is written. Use the CLI in ``__main__`` for exit-code
semantics (0 pass / 1 violations / 2 input error).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# --- Constants -------------------------------------------------------------

REPO_ROOT_MARKERS = ("modules", "WSP_framework", "public")

DEFAULT_REGISTRY_PATH = Path("modules/foundups/foundup_registry.json")
DEFAULT_CATALOG_PATH = Path("public/member/mall-video-catalog.json")
DEFAULT_PROJECTION_PATH = Path("public/f/portfolio_data.json")
DEFAULT_MANIFEST_DIR = Path("modules/foundups")

# Enum values pulled from foundup_registry.schema.json (Phase 1).
VALID_PORTFOLIO_STATUS = {
    "not_portfolio",
    "portfolio_candidate",
    "portfolio_ready",
    "portfolio_featured",
}
VALID_POC_LANDING_STATUS = {"none", "placeholder", "functional", "polished"}

PORTFOLIO_ELIGIBLE_STATUSES = {
    "portfolio_candidate",
    "portfolio_ready",
    "portfolio_featured",
}

URL_FIELDS = (
    "website_url",
    "poc_url",
    "app_url",
    "github_url",
    "docs_url",
    "screenshot_url",
)

# Permissive URI guard - validator is read-only and the schema's full uri
# format check is not portable across jsonschema validator versions.
_URL_PATTERN = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


# --- Data classes ----------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """A single validator finding.

    ``severity`` is ``error`` or ``warning``. Errors cause CLI exit 1.
    Warnings do NOT cause failure but are still surfaced in the report.
    """

    rule_id: str
    severity: str
    entity: str
    field: str
    expected: Any
    actual: Any
    source: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    """Structured validation result.

    ``violations`` is the canonical list. ``stats`` carries supplementary
    counts (e.g. total registry inventory coverage) that are not themselves
    spec rules but help operators interpret the report.
    """

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
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violations": [v.to_dict() for v in self.violations],
            "stats": self.stats,
            "summary": {
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "total_violations": len(self.violations),
            },
        }


# --- Source loading --------------------------------------------------------


class SourceError(Exception):
    """Raised when a canonical source is missing or malformed.

    Maps to CLI exit code 2 (fail-closed input error).
    """


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


@dataclass
class Sources:
    """Loaded canonical inputs. ``manifests`` is keyed by foundup_id."""

    registry: Dict[str, Any]
    catalog: List[Dict[str, Any]]
    projection: Dict[str, Any]
    manifests: Dict[str, Dict[str, Any]]
    paths: Dict[str, Path]


def load_sources(
    repo_root: Path,
    registry_path: Optional[Path] = None,
    catalog_path: Optional[Path] = None,
    projection_path: Optional[Path] = None,
    manifest_dir: Optional[Path] = None,
) -> Sources:
    """Load all canonical inputs from ``repo_root``.

    Manifests are best-effort: a missing or malformed per-foundup manifest is
    not fatal (manifests are L3 detail; absence is a normal state). Missing
    registry/catalog/projection raise :class:`SourceError`.
    """

    registry_path = repo_root / (registry_path or DEFAULT_REGISTRY_PATH)
    catalog_path = repo_root / (catalog_path or DEFAULT_CATALOG_PATH)
    projection_path = repo_root / (projection_path or DEFAULT_PROJECTION_PATH)
    manifest_dir = repo_root / (manifest_dir or DEFAULT_MANIFEST_DIR)

    registry = _read_json(registry_path)
    catalog = _read_json(catalog_path)
    projection = _read_json(projection_path)

    if not isinstance(registry, dict) or "entities" not in registry:
        raise SourceError(f"Registry missing 'entities' array: {registry_path}")
    if not isinstance(catalog, list):
        raise SourceError(f"Catalog must be a JSON array: {catalog_path}")
    if not isinstance(projection, dict) or "entities" not in projection:
        raise SourceError(
            f"Projection missing 'entities' array: {projection_path}"
        )

    manifests: Dict[str, Dict[str, Any]] = {}
    if manifest_dir.exists():
        for manifest in manifest_dir.glob("*/foundup_manifest.json"):
            try:
                data = _read_json(manifest)
                if isinstance(data, dict) and data.get("foundup_id"):
                    manifests[data["foundup_id"]] = data
            except SourceError:
                # Malformed manifest is non-fatal for Phase 1 validator
                # (manifests are L3 detail and not used for fail-closed gates).
                continue

    return Sources(
        registry=registry,
        catalog=catalog,
        projection=projection,
        manifests=manifests,
        paths={
            "registry": registry_path,
            "catalog": catalog_path,
            "projection": projection_path,
            "manifest_dir": manifest_dir,
        },
    )


# --- Helpers --------------------------------------------------------------


def _index_registry(registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {e["foundup_id"]: e for e in registry["entities"] if "foundup_id" in e}


def _portfolio_eligible_count(registry: Dict[str, Any]) -> int:
    return sum(
        1
        for e in registry["entities"]
        if e.get("portfolio_status") in PORTFOLIO_ELIGIBLE_STATUSES
    )


# --- Rule implementations -------------------------------------------------
#
# Each rule is implemented as ``rule_<id>(sources) -> list[Violation]``.
# A rule may return zero or more violations. The rule_id in the produced
# violation MUST match the function name suffix.
# --------------------------------------------------------------------------


def rule_R1(sources: Sources) -> List[Violation]:
    """R1: All projection entities MUST exist in registry."""
    out: List[Violation] = []
    reg = _index_registry(sources.registry)
    for entity in sources.projection["entities"]:
        fid = entity.get("foundup_id")
        if fid is None or fid not in reg:
            out.append(
                Violation(
                    rule_id="R1",
                    severity="error",
                    entity=fid or "<missing>",
                    field="foundup_id",
                    expected="<present in foundup_registry.json>",
                    actual=fid,
                    source="registry",
                    message=(
                        f"Projection entity '{fid}' has no matching entry in "
                        "foundup_registry.json"
                    ),
                )
            )
    return out


def rule_R2(sources: Sources) -> List[Violation]:
    """R2: foundup_id MUST match registry exactly (case + format)."""
    out: List[Violation] = []
    reg_ids = {e.get("foundup_id") for e in sources.registry["entities"]}
    for entity in sources.projection["entities"]:
        fid = entity.get("foundup_id")
        if fid is None:
            continue
        # Exact membership check already enforced by R1; R2 additionally guards
        # against case-folded near-matches that would slip past a downstream
        # consumer's loose comparison.
        if fid not in reg_ids:
            lowered = {x.lower() for x in reg_ids if isinstance(x, str)}
            if isinstance(fid, str) and fid.lower() in lowered:
                out.append(
                    Violation(
                        rule_id="R2",
                        severity="error",
                        entity=fid,
                        field="foundup_id",
                        expected="<exact case match in registry>",
                        actual=fid,
                        source="registry",
                        message=(
                            f"Projection foundup_id '{fid}' differs only by "
                            "case from a registry entry"
                        ),
                    )
                )
    return out


def rule_R3(sources: Sources) -> List[Violation]:
    """R3: portfolio_status MUST be a valid enum value."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        status = entity.get("portfolio_status")
        if status not in VALID_PORTFOLIO_STATUS:
            out.append(
                Violation(
                    rule_id="R3",
                    severity="error",
                    entity=entity.get("foundup_id", "<missing>"),
                    field="portfolio_status",
                    expected=sorted(VALID_PORTFOLIO_STATUS),
                    actual=status,
                    source="projection",
                    message=(
                        f"portfolio_status '{status}' is not a recognised enum "
                        "value"
                    ),
                )
            )
    return out


def rule_R4(sources: Sources) -> List[Violation]:
    """R4: poc_landing_status MUST be a valid enum value."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        status = entity.get("poc_landing_status")
        if status not in VALID_POC_LANDING_STATUS:
            out.append(
                Violation(
                    rule_id="R4",
                    severity="error",
                    entity=entity.get("foundup_id", "<missing>"),
                    field="poc_landing_status",
                    expected=sorted(VALID_POC_LANDING_STATUS),
                    actual=status,
                    source="projection",
                    message=(
                        f"poc_landing_status '{status}' is not a recognised "
                        "enum value"
                    ),
                )
            )
    return out


def rule_R5(sources: Sources) -> List[Violation]:
    """R5: URL fields MUST be a valid URI or null."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        fid = entity.get("foundup_id", "<missing>")
        for field_name in URL_FIELDS:
            val = entity.get(field_name)
            if val is None:
                continue
            if not isinstance(val, str) or not _URL_PATTERN.match(val):
                out.append(
                    Violation(
                        rule_id="R5",
                        severity="warning",
                        entity=fid,
                        field=field_name,
                        expected="http(s) URL or null",
                        actual=val,
                        source="projection",
                        message=(
                            f"{field_name} is not a valid http(s) URL nor null"
                        ),
                    )
                )
    return out


def rule_R6(sources: Sources) -> List[Violation]:
    """R6: public_summary MUST be <= 280 characters."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        summary = entity.get("public_summary")
        if isinstance(summary, str) and len(summary) > 280:
            out.append(
                Violation(
                    rule_id="R6",
                    severity="warning",
                    entity=entity.get("foundup_id", "<missing>"),
                    field="public_summary",
                    expected="length <= 280",
                    actual=len(summary),
                    source="projection",
                    message=(
                        f"public_summary length {len(summary)} exceeds 280 "
                        "character limit"
                    ),
                )
            )
    return out


def rule_R7(sources: Sources) -> List[Violation]:
    """R7: portfolio_priority MUST be integer 1-100 or null."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        prio = entity.get("portfolio_priority")
        if prio is None:
            continue
        if not isinstance(prio, int) or isinstance(prio, bool) or not (
            1 <= prio <= 100
        ):
            out.append(
                Violation(
                    rule_id="R7",
                    severity="error",
                    entity=entity.get("foundup_id", "<missing>"),
                    field="portfolio_priority",
                    expected="integer in [1, 100] or null",
                    actual=prio,
                    source="projection",
                    message=(
                        f"portfolio_priority '{prio}' is not an integer in "
                        "[1, 100] nor null"
                    ),
                )
            )
    return out


def rule_R8(sources: Sources) -> List[Violation]:
    """R8: Projection portfolio_status MUST match registry."""
    out: List[Violation] = []
    reg = _index_registry(sources.registry)
    for entity in sources.projection["entities"]:
        fid = entity.get("foundup_id")
        if fid not in reg:
            # R1 already flags this. Skip to avoid double-reporting.
            continue
        actual = entity.get("portfolio_status")
        expected = reg[fid].get("portfolio_status")
        if actual != expected:
            out.append(
                Violation(
                    rule_id="R8",
                    severity="error",
                    entity=fid,
                    field="portfolio_status",
                    expected=expected,
                    actual=actual,
                    source="registry",
                    message=(
                        f"portfolio_status drift: registry says '{expected}', "
                        f"projection says '{actual}'"
                    ),
                )
            )
    return out


def rule_R9(sources: Sources) -> List[Violation]:
    """R9: Projection portfolio_ready MUST match registry."""
    out: List[Violation] = []
    reg = _index_registry(sources.registry)
    for entity in sources.projection["entities"]:
        fid = entity.get("foundup_id")
        if fid not in reg:
            continue
        actual = entity.get("portfolio_ready")
        expected = reg[fid].get("portfolio_ready", False)
        if actual != expected:
            out.append(
                Violation(
                    rule_id="R9",
                    severity="error",
                    entity=fid,
                    field="portfolio_ready",
                    expected=expected,
                    actual=actual,
                    source="registry",
                    message=(
                        f"portfolio_ready drift: registry says {expected}, "
                        f"projection says {actual}"
                    ),
                )
            )
    return out


def rule_R10(sources: Sources) -> List[Violation]:
    """R10: Projection entity count MUST match portfolio-eligible registry count.

    Portfolio-eligible = registry portfolio_status in
    ``{portfolio_candidate, portfolio_ready, portfolio_featured}``.
    """
    out: List[Violation] = []
    expected = _portfolio_eligible_count(sources.registry)
    actual = len(sources.projection["entities"])
    if actual != expected:
        out.append(
            Violation(
                rule_id="R10",
                severity="warning",
                entity="global",
                field="entities.length",
                expected=expected,
                actual=actual,
                source="registry",
                message=(
                    f"Projection lists {actual} entities, but registry has "
                    f"{expected} portfolio-eligible entries (status in "
                    f"{sorted(PORTFOLIO_ELIGIBLE_STATUSES)})"
                ),
            )
        )
    return out


def rule_R11(sources: Sources) -> List[Violation]:
    """R11: No projection entity without registry backing.

    Semantically R11 reinforces R1 with explicit "no orphan" framing. It is
    kept as a separate rule so reports can cite the spec ID directly.
    """
    out: List[Violation] = []
    reg_ids = {e.get("foundup_id") for e in sources.registry["entities"]}
    for entity in sources.projection["entities"]:
        fid = entity.get("foundup_id")
        if fid not in reg_ids:
            out.append(
                Violation(
                    rule_id="R11",
                    severity="error",
                    entity=fid or "<missing>",
                    field="foundup_id",
                    expected="<must be backed by a registry entry>",
                    actual=fid,
                    source="registry",
                    message=(
                        f"Projection entity '{fid}' has no registry backing "
                        "(orphan projection entry)"
                    ),
                )
            )
    return out


def rule_C1(sources: Sources) -> List[Violation]:
    """C1: portfolio_ready=true => poc_landing_status != 'none'."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        if entity.get("portfolio_ready") is True:
            landing = entity.get("poc_landing_status")
            if landing == "none":
                out.append(
                    Violation(
                        rule_id="C1",
                        severity="warning",
                        entity=entity.get("foundup_id", "<missing>"),
                        field="poc_landing_status",
                        expected="!= 'none' when portfolio_ready=true",
                        actual=landing,
                        source="projection",
                        message=(
                            "portfolio_ready=true but poc_landing_status is "
                            "'none' (no landing surface)"
                        ),
                    )
                )
    return out


def rule_C2(sources: Sources) -> List[Violation]:
    """C2: portfolio_status='portfolio_featured' => portfolio_ready=true."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        if entity.get("portfolio_status") == "portfolio_featured":
            ready = entity.get("portfolio_ready")
            if ready is not True:
                out.append(
                    Violation(
                        rule_id="C2",
                        severity="error",
                        entity=entity.get("foundup_id", "<missing>"),
                        field="portfolio_ready",
                        expected=True,
                        actual=ready,
                        source="projection",
                        message=(
                            "portfolio_status='portfolio_featured' requires "
                            "portfolio_ready=true"
                        ),
                    )
                )
    return out


def rule_C3(sources: Sources) -> List[Violation]:
    """C3: portfolio_status='not_portfolio' entities MUST NOT appear in projection.

    Checked from the registry side: any registry entry with
    ``portfolio_status='not_portfolio'`` that still shows up in the projection
    is a filter-rule violation.
    """
    out: List[Violation] = []
    reg = _index_registry(sources.registry)
    proj_ids = {e.get("foundup_id") for e in sources.projection["entities"]}
    for fid, entry in reg.items():
        if entry.get("portfolio_status") == "not_portfolio" and fid in proj_ids:
            out.append(
                Violation(
                    rule_id="C3",
                    severity="error",
                    entity=fid,
                    field="portfolio_status",
                    expected="entity excluded from projection",
                    actual="present in projection",
                    source="projection",
                    message=(
                        f"Registry marks '{fid}' as 'not_portfolio' but it "
                        "still appears in the projection"
                    ),
                )
            )
    return out


def rule_C4(sources: Sources) -> List[Violation]:
    """C4: HoloIndex MUST have is_dual_identity=true in projection."""
    out: List[Violation] = []
    for entity in sources.projection["entities"]:
        if entity.get("foundup_id") == "holoindex_prod_01":
            if entity.get("is_dual_identity") is not True:
                out.append(
                    Violation(
                        rule_id="C4",
                        severity="warning",
                        entity="holoindex_prod_01",
                        field="is_dual_identity",
                        expected=True,
                        actual=entity.get("is_dual_identity"),
                        source="projection",
                        message=(
                            "HoloIndex projection must set "
                            "is_dual_identity=true (spec section 5)"
                        ),
                    )
                )
    return out


# Ordered registry of rule callables. The order is preserved in the report
# for deterministic diff'ing across runs.
RULES: Tuple[Tuple[str, Callable[[Sources], List[Violation]]], ...] = (
    ("R1", rule_R1),
    ("R2", rule_R2),
    ("R3", rule_R3),
    ("R4", rule_R4),
    ("R5", rule_R5),
    ("R6", rule_R6),
    ("R7", rule_R7),
    ("R8", rule_R8),
    ("R9", rule_R9),
    ("R10", rule_R10),
    ("R11", rule_R11),
    ("C1", rule_C1),
    ("C2", rule_C2),
    ("C3", rule_C3),
    ("C4", rule_C4),
)


# --- Orchestration --------------------------------------------------------


def run_validation(sources: Sources) -> ValidationReport:
    """Run every rule in ``RULES`` against ``sources`` and return a report.

    The function is pure - it never mutates any source file. It also never
    raises on rule violations; it only raises if a rule callable itself
    crashes (which is treated as a bug, not an input issue).
    """

    report = ValidationReport()
    for rule_id, fn in RULES:
        for violation in fn(sources):
            if violation.rule_id != rule_id:
                # Defensive: keep rule_id/function_name aligned.
                violation = Violation(
                    rule_id=rule_id,
                    severity=violation.severity,
                    entity=violation.entity,
                    field=violation.field,
                    expected=violation.expected,
                    actual=violation.actual,
                    source=violation.source,
                    message=violation.message,
                )
            report.add(violation)

    # Supplementary global stats (informational - NOT spec rules).
    reg_total = len(sources.registry["entities"])
    proj_total = len(sources.projection["entities"])
    eligible = _portfolio_eligible_count(sources.registry)
    report.stats.update(
        {
            "registry_total": reg_total,
            "registry_portfolio_eligible": eligible,
            "projection_total": proj_total,
            "registry_inventory_coverage": {
                "registry_total": reg_total,
                "projection_total": proj_total,
                "delta": reg_total - proj_total,
                "note": (
                    "Informational only - not a spec rule. R10 enforces "
                    "projection==portfolio_eligible, not projection==registry."
                ),
            },
        }
    )
    return report


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk upward from ``start`` (or this file) to find the repo root.

    A directory is considered the repo root if it contains all the markers in
    :data:`REPO_ROOT_MARKERS`.
    """
    here = (start or Path(__file__)).resolve()
    if here.is_file():
        here = here.parent
    for candidate in [here, *here.parents]:
        if all((candidate / marker).exists() for marker in REPO_ROOT_MARKERS):
            return candidate
    raise SourceError(
        f"Cannot locate repo root from {here}; "
        f"expected markers {REPO_ROOT_MARKERS}"
    )
