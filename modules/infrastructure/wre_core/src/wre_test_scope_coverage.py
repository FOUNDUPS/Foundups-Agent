"""Deterministic changed-path to pytest-scope coverage resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
import re
from typing import Any, Sequence

IMPACT_RANK = {"ISOLATED": 1, "MODULAR": 2, "SYSTEMIC": 3}
SUITE_KIND = {
    "ISOLATED": "FOCUSED",
    "MODULAR": "MODULE_CLOSURE",
    "SYSTEMIC": "FULL_REPOSITORY",
}
FAIL_CHANGED_PATHS = "FAIL_TEST_SCOPE_CHANGED_PATHS"
FAIL_POLICY_DOWNGRADE = "FAIL_TEST_SCOPE_POLICY_DOWNGRADE"
FAIL_SELECTION = "FAIL_TEST_SCOPE_SELECTION"
FAIL_COVERAGE = "FAIL_TEST_SCOPE_COVERAGE"

_SYSTEMIC_PREFIXES = (
    ".github/",
    "WSP_agentic/",
    "WSP_framework/",
    "WSP_knowledge/",
    "docs/",
    "holo_index/",
    "scripts/",
    "tests/",
    "modules/infrastructure/shared_utilities/",
    "modules/infrastructure/wre_core/",
)
_ALLOWED_FLAGS = {
    "-q", "--quiet", "-v", "--verbose", "--disable-warnings",
    "--strict-markers", "--strict-config",
    "--tb=auto", "--tb=long", "--tb=short", "--tb=line", "--tb=native",
    "--tb=no", "--color=yes", "--color=no", "--color=auto",
}
_DRIVE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class TestScopeCoverage:
    accepted: bool
    minimum_impact: str
    effective_impact: str
    required_suite_kind: str
    module_root: str
    selection_paths: tuple[str, ...]
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_test_scope_coverage(
    changed_paths: Sequence[str], requested_impact: str, selection_args: Sequence[str]
) -> TestScopeCoverage:
    """Resolve and prove the minimum test scope; ambiguity escalates to full."""
    paths, roots, path_reason = _changed_paths(changed_paths)
    minimum, module_root = _minimum_impact(paths, roots, path_reason)
    selection, selection_reason = _selection_paths(selection_args)
    reasons = [reason for reason in (path_reason, selection_reason) if reason]
    requested = requested_impact if requested_impact in IMPACT_RANK else ""
    if not requested or IMPACT_RANK.get(requested, 0) < IMPACT_RANK[minimum]:
        reasons.append(FAIL_POLICY_DOWNGRADE)
    effective = requested if requested and IMPACT_RANK[requested] >= IMPACT_RANK[minimum] else minimum
    if not reasons and not _covers(effective, paths, module_root, selection):
        reasons.append(FAIL_COVERAGE)
    if reasons:
        return _failed(minimum, module_root, selection, reasons)
    return TestScopeCoverage(
        True, minimum, effective, SUITE_KIND[effective], module_root,
        selection, (),
    )


def _changed_paths(
    values: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    if not isinstance(values, (list, tuple)) or not values:
        return (), (), FAIL_CHANGED_PATHS
    paths: list[str] = []
    roots: list[str] = []
    for value in values:
        path = _confined_path(value, allow_dot=False)
        root = _module_root(path) if path else ""
        if not path or not root:
            return (), (), FAIL_CHANGED_PATHS
        paths.append(path)
        roots.append(root)
    if len(paths) != len(set(paths)):
        return (), (), FAIL_CHANGED_PATHS
    return tuple(sorted(paths)), tuple(sorted(set(roots))), ""


def _minimum_impact(
    paths: Sequence[str], roots: Sequence[str], reason: str
) -> tuple[str, str]:
    if reason or not paths or len(roots) != 1 or roots[0] == "SYSTEMIC":
        return "SYSTEMIC", ""
    root = roots[0]
    if any(path.startswith(_SYSTEMIC_PREFIXES) for path in paths):
        return "SYSTEMIC", ""
    if len(paths) == 1 and _isolated_test(paths[0], root):
        return "ISOLATED", root
    return "MODULAR", root


def _module_root(path: str) -> str:
    parts = PurePosixPath(path).parts
    if any(path.startswith(prefix) for prefix in _SYSTEMIC_PREFIXES):
        return "SYSTEMIC"
    if len(parts) == 1:
        return "SYSTEMIC"
    if len(parts) >= 4 and parts[0] == "modules":
        return "/".join(parts[:3])
    if len(parts) >= 3 and parts[0] == "extensions":
        return "/".join(parts[:2])
    return ""


def _selection_paths(values: Sequence[str]) -> tuple[tuple[str, ...], str]:
    if not isinstance(values, (list, tuple)) or not values:
        return (), FAIL_SELECTION
    selected: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value or any(char in value for char in "\x00\n\r"):
            return (), FAIL_SELECTION
        if value.startswith("-"):
            if value not in _ALLOWED_FLAGS:
                return (), FAIL_SELECTION
            continue
        path = _confined_path(value, allow_dot=True)
        if not path or "::" in value:
            return (), FAIL_SELECTION
        selected.append(path)
    if not selected or len(selected) != len(set(selected)):
        return (), FAIL_SELECTION
    return tuple(sorted(selected)), ""


def _confined_path(value: Any, *, allow_dot: bool) -> str:
    if not isinstance(value, str) or not value or "\\" in value or _DRIVE.match(value):
        return ""
    if value.startswith(("/", "~", "@")) or any(char in value for char in "*?[]"):
        return ""
    parts = PurePosixPath(value).parts
    if any(part in {"", ".."} for part in parts):
        return ""
    normalized = PurePosixPath(*parts).as_posix()
    if normalized == "." and not allow_dot:
        return ""
    return normalized


def _isolated_test(path: str, root: str) -> bool:
    relative = PurePosixPath(path).relative_to(PurePosixPath(root))
    return len(relative.parts) >= 2 and relative.parts[0] == "tests" and relative.name.startswith("test_") and relative.suffix == ".py"


def _covers(
    impact: str, changed: Sequence[str], module_root: str, selected: Sequence[str]
) -> bool:
    if impact == "SYSTEMIC":
        return "." in selected
    if impact == "MODULAR":
        return f"{module_root}/tests" in selected
    return len(changed) == 1 and changed[0] in selected


def _failed(
    minimum: str, module_root: str, selected: tuple[str, ...], reasons: Sequence[str]
) -> TestScopeCoverage:
    return TestScopeCoverage(
        False, minimum, "SYSTEMIC", "FULL_REPOSITORY", module_root,
        selected, tuple(dict.fromkeys(reasons)),
    )


__all__ = [
    "FAIL_CHANGED_PATHS", "FAIL_COVERAGE", "FAIL_POLICY_DOWNGRADE",
    "FAIL_SELECTION", "TestScopeCoverage", "resolve_test_scope_coverage",
]
