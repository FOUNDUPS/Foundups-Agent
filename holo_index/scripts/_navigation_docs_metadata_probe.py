"""Bounded read-only metadata proof for the docs-pipeline diagnostic."""

from __future__ import annotations

import re
import sqlite3
import stat
import subprocess
import time
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, List, Optional, Tuple

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    _contains_link_component,
)


SQLITE_PATH_PAGE_ROWS = 128
SQLITE_MAX_PATH_ROWS = 4096
SQLITE_MAX_PATH_BYTES = 4096
SQLITE_MAX_TOTAL_PATH_BYTES = 4 * 1024 * 1024
SQLITE_CONNECTION_TIMEOUT_SECONDS = 1.0
SQLITE_MAX_QUERY_SECONDS = 5.0
SQLITE_PROGRESS_OPCODE_INTERVAL = 1000
SQLITE_MAX_PROGRESS_CALLBACKS = 100_000
GIT_MAX_TRACKED_FILES = 20_000
GIT_MAX_OUTPUT_BYTES = 2 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 30
_MODULE_COMPONENT_RE = re.compile(
    r"^(?:[A-Za-z0-9_+]|[A-Za-z0-9_+][A-Za-z0-9_.+-]*[A-Za-z0-9_+])$"
)
_TIER0_DOC_NAMES = ("README.md", "INTERFACE.md")
_EXCLUDED_MODULE_ROOTS = frozenset(
    {
        "modules/economy/src",
        "modules/foundups/docs",
        "modules/gamification/_archived_duplicates_per_wsp3",
        "modules/telemetry/feedback",
    }
)
_H7_PRIORITY = (
    "TIER0_MIXED_ABSOLUTE_RELATIVE_PATHS",
    "TIER0_PATH_TRAVERSAL",
    "TIER0_DOT_PREFIX_PATH",
    "TIER0_BACKSLASH_PATH",
    "TIER0_PATH_CASE_MISMATCH",
    "TIER0_MALFORMED_PATH",
    "TIER0_ABSOLUTE_PATH_ROWS",
    "TIER0_EXACT_ROWS_DUPLICATE",
    "TIER0_EXACT_ROWS_MISSING",
    "CANONICAL_MODULE_TARGETS_ABSENT",
)


class _MetadataProbeOverflow(Exception):
    """Stable bounded-read failure without sensitive database detail."""

    def __init__(self, classification: str) -> None:
        super().__init__(classification)
        self.classification = classification


class _MetadataProbeFailure(Exception):
    """Stable operational failure without database or checkout detail."""

    def __init__(self, classification: str) -> None:
        super().__init__(classification)
        self.classification = classification


class _SqliteProgressBudget:
    """Bound total SQLite virtual-machine work and elapsed query time."""

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.callbacks = 0
        self.classification = "SQLITE_VM_STEP_LIMIT_EXCEEDED"

    def __call__(self) -> int:
        self.callbacks += 1
        if time.monotonic() - self.started > SQLITE_MAX_QUERY_SECONDS:
            self.classification = "SQLITE_TIME_LIMIT_EXCEEDED"
            return 1
        if self.callbacks > SQLITE_MAX_PROGRESS_CALLBACKS:
            return 1
        return 0


def _is_absolute_metadata_path(value: str) -> bool:
    return PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()


def _valid_module_component(value: str) -> bool:
    return 0 < len(value) <= 128 and bool(_MODULE_COMPONENT_RE.fullmatch(value))


def _module_root_from_tracked_path(path: str) -> str:
    parts = path.split("/")
    if len(parts) < 4 or parts[0] != "modules":
        return ""
    if not all(_valid_module_component(value) for value in parts[1:3]):
        return ""
    root = "/".join(parts[:3])
    return "" if root in _EXCLUDED_MODULE_ROOTS else root


def _bounded_module_roots(paths: List[str]) -> List[str]:
    if len(paths) > GIT_MAX_TRACKED_FILES:
        raise _MetadataProbeOverflow("TRACKED_FILE_LIMIT_EXCEEDED")
    roots = {root for path in paths if (root := _module_root_from_tracked_path(path))}
    return sorted(roots)


def _git_module_roots(project_root: Path) -> List[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "ls-files", "-z", "--", "modules/*/*/**"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise _MetadataProbeFailure("CANONICAL_MODULE_SOURCE_PROBE_FAILED") from None
    if result.returncode != 0:
        raise _MetadataProbeFailure("CANONICAL_MODULE_SOURCE_PROBE_FAILED")
    if len(result.stdout) > GIT_MAX_OUTPUT_BYTES:
        raise _MetadataProbeOverflow("TRACKED_SOURCE_BYTE_LIMIT_EXCEEDED")
    paths = [bytes_path.decode("utf-8", "surrogateescape") for bytes_path in result.stdout.split(b"\0") if bytes_path]
    return _bounded_module_roots(paths)


def _fixture_module_roots(project_root: Path) -> List[str]:
    modules_root = project_root / "modules"
    if not modules_root.is_dir():
        return []
    roots: List[str] = []
    try:
        for domain in sorted(modules_root.iterdir(), key=lambda item: item.name):
            if not domain.is_dir() or not _valid_module_component(domain.name):
                continue
            for module in sorted(domain.iterdir(), key=lambda item: item.name):
                root = f"modules/{domain.name}/{module.name}"
                if module.is_dir() and _valid_module_component(module.name):
                    roots.extend([] if root in _EXCLUDED_MODULE_ROOTS else [root])
    except OSError:
        raise _MetadataProbeFailure("CANONICAL_MODULE_SOURCE_PROBE_FAILED") from None
    return roots


def _canonical_tier0_paths(project_root: Path) -> List[str]:
    roots = (
        _git_module_roots(project_root)
        if (project_root / ".git").exists()
        else _fixture_module_roots(project_root)
    )
    return [f"{root}/{name}" for root in roots for name in _TIER0_DOC_NAMES]


def _candidate_repository_path(value: str) -> Tuple[str, str]:
    """Return a comparison-only candidate and sanitized stored root."""
    candidate = value.replace("\\", "/")
    stored_root = ""
    lowered = candidate.casefold()
    if _is_absolute_metadata_path(value):
        markers = (
            "/holo_index/docs/", "/wsp_framework/docs/", "/modules/", "/docs/",
        )
        for marker in markers:
            marker_index = lowered.find(marker)
            if marker_index >= 0:
                stored_root = candidate[:marker_index]
                candidate = candidate[marker_index + 1 :]
                break
    while candidate.startswith("./") or candidate.startswith("../"):
        candidate = candidate[candidate.find("/") + 1 :]
    while "//" in candidate:
        candidate = candidate.replace("//", "/")
    parts: List[str] = []
    for part in candidate.split("/"):
        if part == ".." and parts:
            parts.pop()
        elif part not in {"", ".", ".."}:
            parts.append(part)
    return "/".join(parts), stored_root.rstrip("/").casefold()


def _row_defects(value: Any, candidate: str, expected: Optional[str]) -> List[str]:
    if not isinstance(value, str):
        return ["TIER0_MALFORMED_PATH"]
    defects: List[str] = []
    segments = re.split(r"[\\/]", value)
    if _is_absolute_metadata_path(value):
        defects.append("TIER0_ABSOLUTE_PATH_ROWS")
    if "\\" in value:
        defects.append("TIER0_BACKSLASH_PATH")
    if value.startswith("./"):
        defects.append("TIER0_DOT_PREFIX_PATH")
    if ".." in segments:
        defects.append("TIER0_PATH_TRAVERSAL")
    if any(ord(character) < 32 for character in value) or "//" in value:
        defects.append("TIER0_MALFORMED_PATH")
    if expected and candidate.casefold() == expected.casefold() and candidate != expected:
        defects.append("TIER0_PATH_CASE_MISMATCH")
    if expected and value != expected and not defects:
        defects.append("TIER0_MALFORMED_PATH")
    return defects


def _metadata_row_facts(
    paths: List[Any], required: List[str]
) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, Any]]:
    exact_counts = {path: 0 for path in required}
    defect_counts = {classification: 0 for classification in _H7_PRIORITY[:7]}
    required_by_fold = {path.casefold(): path for path in required}
    facts: Dict[str, Any] = {
        "absolute": 0, "relative": 0, "absolute_tier0": 0,
        "architecture": 0, "stored_roots": [],
    }
    for value in paths:
        if not isinstance(value, str):
            defect_counts["TIER0_MALFORMED_PATH"] += 1
            continue
        absolute = _is_absolute_metadata_path(value)
        candidate, stored_root = _candidate_repository_path(value)
        expected = required_by_fold.get(candidate.casefold())
        facts["absolute" if absolute else "relative"] += 1
        if stored_root and stored_root not in facts["stored_roots"]:
            facts["stored_roots"].append(stored_root)
        if value in exact_counts:
            exact_counts[value] += 1
        if expected and absolute:
            facts["absolute_tier0"] += 1
        facts["architecture"] += int(
            candidate.casefold().startswith("docs/audits/architecture/")
        )
        for defect in _row_defects(value, candidate, expected):
            if expected or defect in {"TIER0_PATH_TRAVERSAL", "TIER0_MALFORMED_PATH"}:
                defect_counts[defect] += 1
    return exact_counts, defect_counts, facts


def _h7_findings(
    defect_counts: Dict[str, int], missing: int, duplicate: int,
    target_count: int, absolute: int, relative: int,
) -> List[str]:
    findings: List[str] = []
    if absolute and relative:
        findings.append("TIER0_MIXED_ABSOLUTE_RELATIVE_PATHS")
    for classification in _H7_PRIORITY[1:7]:
        if defect_counts[classification]:
            findings.append(classification)
    if duplicate:
        findings.append("TIER0_EXACT_ROWS_DUPLICATE")
    if missing:
        findings.append("TIER0_EXACT_ROWS_MISSING")
    if not target_count:
        findings.append("CANONICAL_MODULE_TARGETS_ABSENT")
    return findings or ["TIER0_EXACT_CONTRACT_COMPLETE"]


def _classify_metadata_paths(paths: List[Any], project_root: Path) -> Dict[str, Any]:
    required = _canonical_tier0_paths(project_root)
    exact_counts, defect_counts, facts = _metadata_row_facts(paths, required)
    defect_counts["TIER0_MIXED_ABSOLUTE_RELATIVE_PATHS"] = int(
        bool(facts["absolute"] and facts["relative"])
    )
    missing = sum(count == 0 for count in exact_counts.values())
    duplicate = sum(max(0, count - 1) for count in exact_counts.values())
    exact_rows = sum(exact_counts.values())
    targets = len(required) // len(_TIER0_DOC_NAMES)
    findings = _h7_findings(
        defect_counts, missing, duplicate, targets,
        facts["absolute"], facts["relative"],
    )
    current_root = project_root.as_posix().rstrip("/").casefold()
    roots = sorted(facts["stored_roots"])
    return {
        "metadata_path_count": len(paths),
        "absolute_path_count": facts["absolute"],
        "repository_relative_path_count": facts["relative"],
        "all_paths_absolute": bool(paths) and facts["absolute"] == len(paths),
        "canonical_module_target_count": targets,
        "required_tier0_exact_row_count": len(required),
        "absolute_tier0_rows": facts["absolute_tier0"],
        "strict_tier0_relative_exact_rows": exact_rows,
        "missing_required_tier0_rows": missing,
        "duplicate_required_tier0_rows": duplicate,
        "strict_tier0_contract_complete": findings == ["TIER0_EXACT_CONTRACT_COMPLETE"],
        "h7_findings": findings,
        "h7_classification_counts": defect_counts,
        "stored_checkout_root_count": len(roots),
        "stored_checkout_matches_diagnostic_root": len(roots) == 1 and current_root in roots,
        "docs_audits_architecture_in_index": facts["architecture"],
        "h7_finding": findings[0],
    }


def _raw_value_bytes(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, (bytes, bytearray, memoryview)):
        return len(value)
    return len(str(value).encode("utf-8"))


def _metadata_value(row: Tuple[Any, ...]) -> Any:
    populated = [(index, value) for index, value in enumerate(row) if value is not None]
    if len(populated) != 1:
        return None
    return populated[0][1]


def _read_bounded_path_rows(cursor: sqlite3.Cursor) -> List[Tuple[Any, ...]]:
    rows: List[Tuple[Any, ...]] = []
    total_bytes = 0
    while True:
        page = cursor.fetchmany(SQLITE_PATH_PAGE_ROWS)
        if not page:
            break
        for row in page:
            if len(rows) >= SQLITE_MAX_PATH_ROWS:
                raise _MetadataProbeOverflow("PATH_ROW_LIMIT_EXCEEDED")
            row_bytes = sum(_raw_value_bytes(value) for value in row)
            if any(_raw_value_bytes(value) > SQLITE_MAX_PATH_BYTES for value in row):
                raise _MetadataProbeOverflow("PATH_BYTE_LIMIT_EXCEEDED")
            total_bytes += row_bytes
            if total_bytes > SQLITE_MAX_TOTAL_PATH_BYTES:
                raise _MetadataProbeOverflow("TOTAL_PATH_BYTES_LIMIT_EXCEEDED")
            rows.append(tuple(row))
    return rows


def _validated_database_path(database: Path) -> Path:
    try:
        if _contains_link_component(database):
            raise _MetadataProbeFailure("SQLITE_LINK_COMPONENT_REJECTED")
        metadata = database.stat(follow_symlinks=False)
    except FileNotFoundError:
        raise
    except OSError:
        raise _MetadataProbeFailure("SQLITE_PATH_INSPECTION_FAILED") from None
    if not stat.S_ISREG(metadata.st_mode):
        raise _MetadataProbeFailure("SQLITE_NOT_REGULAR_FILE")
    if int(getattr(metadata, "st_nlink", 1)) != 1:
        raise _MetadataProbeFailure("SQLITE_HARDLINK_REJECTED")
    try:
        return database.resolve(strict=True)
    except OSError:
        raise _MetadataProbeFailure("SQLITE_PATH_INSPECTION_FAILED") from None


def _classify_sqlite_error(
    error: sqlite3.Error, progress: _SqliteProgressBudget
) -> str:
    code = int(getattr(error, "sqlite_errorcode", 0) or 0) & 0xFF
    if code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
        return "SQLITE_BUSY_OR_LOCKED"
    if code in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}:
        return "SQLITE_CORRUPT_OR_INVALID"
    if code == sqlite3.SQLITE_INTERRUPT:
        return progress.classification
    return "SQLITE_SCHEMA_OR_QUERY_FAILED"


def _open_readonly_database(database: Path) -> sqlite3.Connection:
    connection: Optional[sqlite3.Connection] = None
    try:
        connection = sqlite3.connect(
            database.as_uri() + "?mode=ro",
            uri=True,
            timeout=SQLITE_CONNECTION_TIMEOUT_SECONDS,
        )
        connection.execute("PRAGMA query_only=ON")
        connection.execute(
            f"PRAGMA busy_timeout={int(SQLITE_CONNECTION_TIMEOUT_SECONDS * 1000)}"
        )
        return connection
    except sqlite3.Error as error:
        if connection is not None:
            connection.close()
        raise _MetadataProbeFailure(
            _classify_sqlite_error(error, _SqliteProgressBudget())
        ) from None


def _path_rows(connection: sqlite3.Connection, join: str) -> List[Any]:
    cursor = connection.execute(
        "SELECT m.string_value, m.int_value, m.float_value, m.bool_value" + join
        + " JOIN embedding_metadata m ON m.id=e.id"
        + " WHERE c.name=? AND m.key=? LIMIT ?",
        ("navigation_docs", "path", SQLITE_MAX_PATH_ROWS + 1),
    )
    rows = _read_bounded_path_rows(cursor)
    return [_metadata_value(row) for row in rows]


def _navigation_docs_total(connection: sqlite3.Connection, join: str) -> int:
    row = connection.execute(
        "SELECT COUNT(DISTINCT e.id)" + join + " WHERE c.name=?",
        ("navigation_docs",),
    ).fetchone()
    if not row or not isinstance(row[0], int):
        raise _MetadataProbeFailure("SQLITE_SCHEMA_OR_QUERY_FAILED")
    return int(row[0])


def _finish_read_snapshot(connection: sqlite3.Connection) -> bool:
    """Release the read snapshot and connection; report cleanup failure."""
    cleanup_failed = False
    try:
        connection.set_progress_handler(None, 0)
    except sqlite3.Error:
        cleanup_failed = True
    try:
        connection.rollback()
    except sqlite3.Error:
        cleanup_failed = True
    try:
        connection.close()
    except sqlite3.Error:
        cleanup_failed = True
    return cleanup_failed


def _read_navigation_docs_metadata(database: Path) -> Tuple[int, List[Any]]:
    connection = _open_readonly_database(_validated_database_path(database))
    progress = _SqliteProgressBudget()
    result: Optional[Tuple[int, List[Any]]] = None
    cleanup_failed = False
    try:
        connection.set_progress_handler(progress, SQLITE_PROGRESS_OPCODE_INTERVAL)
        connection.execute("BEGIN")
        join = (
            " FROM collections c JOIN segments s ON s.collection=c.id"
            " JOIN embeddings e ON e.segment_id=s.id"
        )
        paths = _path_rows(connection, join)
        result = _navigation_docs_total(connection, join), paths
    except sqlite3.Error as error:
        raise _MetadataProbeFailure(_classify_sqlite_error(error, progress)) from None
    finally:
        cleanup_failed = _finish_read_snapshot(connection)
    if cleanup_failed:
        raise _MetadataProbeFailure("SQLITE_SNAPSHOT_CLEANUP_FAILED")
    if result is None:
        raise _MetadataProbeFailure("SQLITE_SCHEMA_OR_QUERY_FAILED")
    return result


def observe_navigation_docs_collection_readonly(
    ssd_path: str = "E:/HoloIndex", project_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Inspect Chroma metadata through SQLite's enforced read-only mode."""
    report: Dict[str, Any] = {"navigation_docs_available": False}
    database = Path(ssd_path) / "vectors" / "chroma.sqlite3"
    try:
        total, paths = _read_navigation_docs_metadata(database)
    except FileNotFoundError:
        report["error"] = "chroma_database_missing"
        return report
    except _MetadataProbeOverflow as error:
        report["error"] = "chroma_metadata_probe_overflow"
        report["overflow_classification"] = error.classification
        return report
    except _MetadataProbeFailure as error:
        report["error"] = "chroma_readonly_metadata_probe_failed"
        report["failure_classification"] = error.classification
        return report
    except (OSError, sqlite3.Error, TypeError, ValueError):
        report["error"] = "chroma_readonly_metadata_probe_failed"
        return report
    report["navigation_docs_available"] = True
    report["navigation_docs_total"] = total
    try:
        path_report = _classify_metadata_paths(
            paths, project_root or Path(__file__).resolve().parents[2]
        )
    except _MetadataProbeOverflow as error:
        report["navigation_docs_available"] = False
        report["error"] = "canonical_module_source_probe_overflow"
        report["overflow_classification"] = error.classification
        return report
    except _MetadataProbeFailure as error:
        report["navigation_docs_available"] = False
        report["error"] = "canonical_module_source_probe_failed"
        report["failure_classification"] = error.classification
        return report
    return {**report, **path_report}


__all__ = ["observe_navigation_docs_collection_readonly"]
