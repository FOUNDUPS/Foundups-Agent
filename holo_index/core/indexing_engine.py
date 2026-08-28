# -*- coding: utf-8 -*-
"""HoloIndex Indexing Engine — extracted indexing surface.

Provides the indexing pipeline previously inlined in HoloIndex.
All public functions accept a ``holo`` (HoloIndex instance) parameter so
they can access collections, model, embeddings, and logging without
coupling to the class hierarchy.

Methods that only need ``holo`` for logging / collection management call
back via ``holo._get_embedding()``, ``holo._reset_collection()``, etc.
to preserve existing test stubs.

WSP Compliance: WSP 87 (Size Limits), WSP 72 (Block Independence)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from holo_index.core.document_indexing import (
    DocumentIndexDependencies,
    chunk_markdown_by_headings as _chunk_markdown_by_headings,
    index_docs_entries as _index_docs_entries,
)
from holo_index.source_scope import (
    CANONICAL_WEB_EXTENSIONS,
    CANONICAL_WEB_RELATIVE_ROOTS,
    CANONICAL_WSP_RELATIVE_ROOTS,
    CanonicalSourceScopeError,
    canonical_source_scope_id,
    filter_git_tracked_files,
    normalized_relative_roots,
)

if TYPE_CHECKING:
    from .holo_index import HoloIndex

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IndexResult dataclass (HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1)
# ---------------------------------------------------------------------------


@dataclass
class IndexResult:
    """Result of an indexing operation for observability.

    Attributes:
        discovered_count: Number of files discovered by glob/discovery phase
        indexed_count: Number of documents actually inserted into Chroma
        collection_name: Name of the target Chroma collection
        warning: Optional warning message (e.g., zero discovered)
        fallback_count: Sources represented by explicit non-authoritative
            fallback records instead of silently omitted from the collection.
        reused_count: Existing records whose exact document and embedding space
            matched, so their embeddings were retained during reconciliation.
    """
    discovered_count: int
    indexed_count: int
    collection_name: str
    warning: Optional[str] = None
    processed_count: Optional[int] = None
    failed_count: int = 0
    fallback_count: int = 0
    reused_count: int = 0
    source_manifest_digest: str = ""
    source_scope_id: str = ""

    @property
    def is_empty(self) -> bool:
        """True if zero documents were discovered or indexed."""
        return self.discovered_count == 0 or self.indexed_count == 0

    @property
    def success(self) -> bool:
        """True if at least one document was indexed."""
        return self.indexed_count > 0

    @property
    def complete(self) -> bool:
        """True only when every discovered source was accounted for."""
        return bool(
            self.success
            and self.processed_count == self.discovered_count
            and self.failed_count == 0
            and self.source_manifest_digest
        )


def source_manifest_digest(value: Any) -> str:
    """Return a deterministic digest for an indexer's declared source set."""

    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_file_manifest_digest(
    files: List[Path],
    *,
    project_root: Path,
) -> str:
    """Hash the complete bytes and normalized path of every declared source."""

    entries = []
    for path in files:
        resolved = path.resolve(strict=False)
        try:
            normalized = resolved.relative_to(project_root.resolve()).as_posix()
        except ValueError:
            normalized = resolved.as_posix()
        entries.append(
            {
                "path": normalized,
                "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return source_manifest_digest(entries)

# ---------------------------------------------------------------------------
# Federation metadata helpers (HIA Federation Phase 2)
# ---------------------------------------------------------------------------

# Cache manifest reads to avoid re-reading per file during bulk indexing
_FOUNDUP_MANIFEST_CACHE: Dict[str, Dict[str, Any]] = {}


def _read_foundup_id_from_manifest(manifest_path: Path, fallback_name: str) -> str:
    """Read foundup_id from a foundup_manifest.json, caching results."""
    cache_key = str(manifest_path)
    if cache_key in _FOUNDUP_MANIFEST_CACHE:
        return _FOUNDUP_MANIFEST_CACHE[cache_key].get("foundup_id", fallback_name)

    try:
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            _FOUNDUP_MANIFEST_CACHE[cache_key] = data
            return data.get("foundup_id", fallback_name)
    except Exception:
        pass

    _FOUNDUP_MANIFEST_CACHE[cache_key] = {"foundup_id": fallback_name}
    return fallback_name


def resolve_foundup_metadata(path: Path, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Resolve federation metadata for a file path.

    Determines which FoundUp a file belongs to based on its path.
    Files under ``modules/foundups/{name}/`` are tagged with the
    ``foundup_id`` from that FoundUp's ``foundup_manifest.json``.
    All other files are tagged as ``"core"``.

    Returns:
        dict with keys: foundup_id, tenant_id, source_scope, external_repo
    """
    path_str = str(path).replace("\\", "/")

    match = re.search(r"modules/foundups/([^/]+)", path_str)
    if match:
        foundup_dir_name = match.group(1)
        if project_root:
            manifest_path = (
                project_root / "modules" / "foundups" / foundup_dir_name / "foundup_manifest.json"
            )
        else:
            idx = path_str.find("modules/foundups/")
            base = path_str[:idx]
            manifest_path = Path(base) / "modules" / "foundups" / foundup_dir_name / "foundup_manifest.json"

        foundup_id = _read_foundup_id_from_manifest(manifest_path, foundup_dir_name)

        return {
            "foundup_id": foundup_id,
            "tenant_id": "core",
            "source_scope": "internal_foundup",
            "external_repo": False,
        }

    return {
        "foundup_id": "core",
        "tenant_id": "core",
        "source_scope": "core",
        "external_repo": False,
    }


# ---------------------------------------------------------------------------
# Worktree safety helpers (HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1)
# ---------------------------------------------------------------------------


def _has_dotfile_in_relative_path(file_path: Path, base: Path) -> bool:
    """Check if any component of the relative path starts with a dot.

    This replaces the absolute-path dot-prefix check to fix worktree safety:
    when project_root is under .claude/worktrees/, the absolute path contains
    .claude as a component, which would incorrectly reject ALL files.

    By checking only the path relative to the discovery base, we skip dotfiles
    INSIDE the docs tree (e.g., .draft/, .DS_Store) while accepting files
    whose absolute path happens to traverse a dot-prefixed parent directory.

    Args:
        file_path: Absolute path to the file
        base: Discovery base directory (e.g., project_root / "docs")

    Returns:
        True if any relative path component starts with '.', False otherwise.
        Also returns True if file_path is not under base (fail-closed).
    """
    try:
        relative_parts = file_path.relative_to(base).parts
        return any(part.startswith('.') for part in relative_parts)
    except ValueError:
        # file_path is not under base — reject (fail-closed)
        return True


# ---------------------------------------------------------------------------
# Stateless helpers (no holo parameter needed)
# ---------------------------------------------------------------------------

def _extract_wsp_id(filename: str, title: str) -> str:
    """Extract WSP identifier from filename or title."""
    match = re.search(r"WSP[_-]?(\d+)", filename)
    if match:
        return f"WSP {match.group(1)}"
    match = re.search(r"WSP\s*(\d+)", title, re.IGNORECASE)
    if match:
        return f"WSP {match.group(1)}"
    return title.split()[0] if title else "WSP"


# HXA Audit Fix: Extract slice IDs (HXA, FX, CFZ patterns) from filenames
_SLICE_ID_PATTERN = re.compile(r"(HXA\d+|FX\d+|CFZ\d+)", re.IGNORECASE)

# Audit Spec Slice ID Fix: Extract long-form audit/spec slice IDs
# Pattern: Uppercase words with underscores ending in _PHASE followed by digits
# Examples:
#   FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1
#   FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1
#   HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1
_AUDIT_SPEC_SLICE_ID_PATTERN = re.compile(
    r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_PHASE\d+)\b"
)


def _extract_slice_id(filename: str, title: str) -> Optional[str]:
    """Extract slice ID from filename or title.

    Supports two slice ID formats:
    1. Short form: HXA, FX, CFZ patterns (e.g., HXA22, FX1, CFZ4)
    2. Long form: Audit/spec IDs ending in _PHASE<digits>
       (e.g., FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1)

    Examples:
        HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md -> HXA22
        test_hxa30_scope_to_action_class.py -> HXA30
        CFZ4_COLLECTION_SEPARATION.md -> CFZ4
        FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md -> FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1
        HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1.md -> HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1
    """
    # Check filename for short-form slice IDs first (HXA/FX/CFZ)
    match = _SLICE_ID_PATTERN.search(filename)
    if match:
        return match.group(1).upper()

    # Check filename for long-form audit/spec slice IDs
    # Extract stem (filename without extension) for cleaner matching
    stem = Path(filename).stem if "." in filename else filename
    match = _AUDIT_SPEC_SLICE_ID_PATTERN.search(stem)
    if match:
        return match.group(1)

    # Check title for short-form slice IDs
    match = _SLICE_ID_PATTERN.search(title)
    if match:
        return match.group(1).upper()

    # Check title for long-form audit/spec slice IDs
    match = _AUDIT_SPEC_SLICE_ID_PATTERN.search(title)
    if match:
        return match.group(1)

    return None


def _classify_document_type(file_path: Path, title: str, lines: List[str]) -> str:
    """Classify document type based on filename, path, and content patterns.

    Returns one of: wsp_protocol, module_readme, roadmap, interface,
    modlog, documentation, test_documentation, readme, other.
    """
    filename = file_path.name.lower()
    path_str = str(file_path).lower()

    if filename.startswith('wsp') and filename.endswith('.md'):
        return "wsp_protocol"

    if filename == 'readme.md':
        parent_dir = file_path.parent
        if any((parent_dir / d).exists() for d in ['src', 'tests', 'docs']):
            return "module_readme"
        return "readme"

    if filename == 'roadmap.md':
        return "roadmap"
    if filename == 'interface.md':
        return "interface"
    if filename == 'modlog.md':
        return "modlog"

    if 'docs/' in path_str or 'docs\\' in path_str:
        return "documentation"

    if 'test' in filename and 'readme' in filename:
        return "test_documentation"

    return "other"


def _calculate_document_priority(doc_type: str, file_path: Path) -> int:
    """Calculate document priority for search ranking (1-10, higher = more important).

    HXA Audit Fix: Boost audit paths (docs/audits/openclaw_hermes, etc.) for
    better slice ID retrieval.
    """
    priority_map = {
        "wsp_protocol": 10,
        "interface": 9,
        "module_readme": 8,
        "documentation": 7,
        "roadmap": 6,
        "modlog": 5,
        "readme": 4,
        "test_documentation": 3,
        "other": 2,
    }

    base_priority = priority_map.get(doc_type, 2)

    path_str = str(file_path).lower().replace("\\", "/")

    # HXA Audit Fix: Boost audit paths
    if "/audits/openclaw_hermes/" in path_str:
        base_priority = max(base_priority, 9)  # HXA series high priority
    elif "/audits/holoindex/" in path_str:
        base_priority = max(base_priority, 9)
    elif "/audits/security/" in path_str:
        base_priority = max(base_priority, 8)
    elif "/audits/" in path_str:
        base_priority = max(base_priority, 7)
    elif 'wsp_framework' in path_str:
        base_priority += 1
    elif 'modules/' in path_str and 'platform_integration' in path_str:
        base_priority += 1

    return min(base_priority, 10)


# ---------------------------------------------------------------------------
# Web asset helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WebAssetDiscovery:
    """Web-source discovery plus complete raw-byte evidence."""

    entries: List[Dict[str, str]]
    discovered_count: int
    processed_count: int
    failed_count: int
    source_manifest_digest: str
    source_scope_id: str
    warning: str = ""


def _resolve_web_index_roots(holo: "HoloIndex") -> List[Path]:
    """Resolve web asset roots for semantic indexing."""
    roots_env = os.getenv("HOLO_WEB_INDEX_ROOTS", "public")
    roots: List[Path] = []
    for raw_root in roots_env.split(";"):
        candidate = raw_root.strip()
        if not candidate:
            continue
        root_path = Path(candidate)
        if not root_path.is_absolute():
            root_path = holo.project_root / root_path
        roots.append(root_path)
    return roots


def _web_index_extensions() -> frozenset[str]:
    raw = os.getenv(
        "HOLO_WEB_INDEX_EXTENSIONS",
        ";".join(sorted(CANONICAL_WEB_EXTENSIONS)),
    )
    values = frozenset(ext.strip().lower() for ext in raw.split(";") if ext.strip())
    return values or CANONICAL_WEB_EXTENSIONS


def _web_index_limit(name: str, default: int) -> tuple[int, bool]:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default, False
    return max(0, value), value >= 0


def _discover_web_asset_files(
    roots: List[Path],
    allowed_extensions: frozenset[str],
) -> List[Path]:
    skip_dirs = {
        ".git", "__pycache__", "node_modules", "dist", "build", ".next", "coverage"
    }
    files: set[Path] = set()
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for file_path in root.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix.lower() in allowed_extensions
                and not any(part in skip_dirs for part in file_path.parts)
            ):
                files.add(file_path.resolve(strict=False))
    return sorted(files, key=lambda path: path.as_posix().casefold())


def _web_asset_entry(
    *,
    file_path: Path,
    raw_bytes: bytes,
    project_root: Path,
    max_chars: int,
) -> Dict[str, str] | None:
    raw_text = raw_bytes.decode("utf-8", errors="ignore")
    if not raw_text.strip():
        return None
    normalized = re.sub(r"\s+", " ", raw_text).strip()
    snippet = normalized[:max_chars]
    try:
        location = file_path.relative_to(project_root).as_posix()
    except ValueError:
        location = file_path.as_posix()
    token_hint = re.sub(r"[_\-\.]+", " ", file_path.stem).strip()
    return {
        "need": f"web asset {file_path.name}",
        "location": location,
        "summary": f"{location} ({file_path.suffix.lower()}) {snippet[:240]}",
        "keywords": snippet[:1200],
        "payload": chr(10).join(
            (
                f"Web asset path: {location}",
                f"Filename: {file_path.name}",
                f"Token hint: {token_hint}",
                f"Content: {snippet}",
            )
        ),
    }


def _web_scope_id(
    holo: "HoloIndex",
    roots: List[Path],
    extensions: frozenset[str],
    *,
    enabled: bool,
    max_files: int,
    max_chars: int,
    valid_limits: bool,
) -> str:
    canonical_roots = tuple(sorted(CANONICAL_WEB_RELATIVE_ROOTS))
    actual_roots = normalized_relative_roots(holo.project_root, roots)
    if (
        enabled
        and actual_roots == canonical_roots
        and extensions == CANONICAL_WEB_EXTENSIONS
        and max_files == 0
        and max_chars == 5000
        and valid_limits
    ):
        return canonical_source_scope_id("navigation_code")
    return ""


def _tracked_web_files(
    holo: "HoloIndex",
    files: List[Path],
    scope_id: str,
) -> tuple[List[Path], str, bool]:
    if not scope_id:
        return files, scope_id, False
    try:
        return filter_git_tracked_files(holo.project_root, files), scope_id, False
    except CanonicalSourceScopeError:
        return files, "", True


def _scan_web_asset_files(
    holo: "HoloIndex",
    files: List[Path],
    selected: List[Path],
    *,
    max_chars: int,
) -> tuple[List[Dict[str, str]], List[Dict[str, str]], int, int]:
    entries: List[Dict[str, str]] = []
    manifest_entries: List[Dict[str, str]] = []
    read_failed = 0
    processed = 0
    selected_keys = {os.path.normcase(str(path)) for path in selected}
    for file_path in files:
        try:
            raw_bytes = file_path.read_bytes()
        except OSError:
            read_failed += 1
            continue
        try:
            location = file_path.relative_to(holo.project_root).as_posix()
        except ValueError:
            location = file_path.as_posix()
        manifest_entries.append(
            {
                "path": location,
                "content_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }
        )
        if os.path.normcase(str(file_path)) not in selected_keys:
            continue
        processed += 1
        entry = _web_asset_entry(
            file_path=file_path,
            raw_bytes=raw_bytes,
            project_root=holo.project_root,
            max_chars=max_chars,
        )
        if entry is not None:
            entries.append(entry)
    return entries, manifest_entries, read_failed, processed


def _web_discovery_warnings(
    *,
    truncated: bool,
    tracking_failed: bool,
    read_failed: int,
    scope_id: str,
) -> str:
    warnings = []
    if truncated:
        warnings.append("web source file cap truncated the declared source set")
    if tracking_failed:
        warnings.append("Git tracking for web sources could not be proven")
    if read_failed:
        warnings.append(f"failed to read {read_failed} web source files")
    if not scope_id:
        warnings.append("web source policy is not canonical")
    return "; ".join(warnings)


def _discover_web_assets(holo: "HoloIndex") -> WebAssetDiscovery:
    enabled = os.getenv("HOLO_INDEX_WEB", "1").lower() in {"1", "true", "yes", "on"}
    roots = _resolve_web_index_roots(holo)
    extensions = _web_index_extensions()
    max_files, valid_file_limit = _web_index_limit("HOLO_WEB_INDEX_MAX_FILES", 0)
    max_chars, valid_char_limit = _web_index_limit("HOLO_WEB_INDEX_MAX_CHARS", 5000)
    scope_id = _web_scope_id(
        holo,
        roots,
        extensions,
        enabled=enabled,
        max_files=max_files,
        max_chars=max_chars,
        valid_limits=valid_file_limit and valid_char_limit,
    )
    files = _discover_web_asset_files(roots, extensions) if enabled else []
    files, scope_id, tracking_failed = _tracked_web_files(holo, files, scope_id)
    selected = files[:max_files] if max_files else files
    entries, manifest_entries, read_failed, processed = _scan_web_asset_files(
        holo,
        files,
        selected,
        max_chars=max_chars,
    )
    warning = _web_discovery_warnings(
        truncated=len(selected) != len(files),
        tracking_failed=tracking_failed,
        read_failed=read_failed,
        scope_id=scope_id,
    )
    return WebAssetDiscovery(
        entries=entries,
        discovered_count=len(files),
        processed_count=processed,
        failed_count=read_failed + int(tracking_failed),
        source_manifest_digest=source_manifest_digest(manifest_entries),
        source_scope_id=scope_id,
        warning=warning,
    )


def _navigation_source_evidence(
    holo: "HoloIndex",
) -> tuple[str, int, str]:
    navigation_path = holo.project_root / "NAVIGATION.py"
    try:
        tracked = filter_git_tracked_files(
            holo.project_root,
            [navigation_path] if navigation_path.is_file() else [],
        )
    except CanonicalSourceScopeError:
        return "", 1, "Git tracking for NAVIGATION.py could not be proven"
    if tracked != [navigation_path.resolve(strict=False)]:
        return "", 1, "Canonical NAVIGATION.py is missing or not tracked"
    try:
        content_digest = hashlib.sha256(navigation_path.read_bytes()).hexdigest()
    except OSError:
        return "", 1, "Canonical NAVIGATION.py could not be read"
    return source_manifest_digest(
        {
            "path": "NAVIGATION.py",
            "content_sha256": content_digest,
        }
    ), 0, ""


def _collect_web_asset_entries(holo: "HoloIndex") -> List[Dict[str, str]]:
    """Collect HTML/JS/CSS assets so UI artifacts are semantically retrievable."""
    return _discover_web_assets(holo).entries


# ---------------------------------------------------------------------------
# Index orchestrators
# ---------------------------------------------------------------------------

def index_code_entries(holo: "HoloIndex") -> IndexResult:
    """Index NAVIGATION code entries and web assets into ChromaDB.

    HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PARITY_PHASE1: Returns IndexResult
    for CLI observability parity with index_docs_entries().
    """
    collection_name = "navigation_code"
    nav_entries = sorted(holo.need_to.items())
    web_discovery = _discover_web_assets(holo)
    nav_manifest, nav_failed, nav_warning = _navigation_source_evidence(holo)
    web_assets = web_discovery.entries
    discovered_count = len(nav_entries) + web_discovery.discovered_count

    if not nav_entries and not web_assets:
        holo._log_agent_action("No code or web entries to index", "WARN")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning="No code or web entries to index — discovery returned zero items"
        )

    holo._log_agent_action(f"Indexing {len(nav_entries)} code navigation entries...", "INDEX")
    if web_assets:
        holo._log_agent_action(f"Indexing {len(web_assets)} web assets from public roots...", "INDEX")
    holo.code_collection = holo._reset_collection("navigation_code")

    ids, embeddings, documents, metadatas = [], [], [], []
    for i, (need, location) in enumerate(nav_entries, start=1):
        ids.append(f"code_{i}")
        embeddings.append(holo._get_embedding(need))
        documents.append(location)
        cube = holo._infer_cube_tag(need, location)
        fed = resolve_foundup_metadata(holo.project_root / location, holo.project_root)
        meta: Dict[str, Any] = {
            "need": need,
            "type": "code",
            "source": "NAVIGATION.py",
            "foundup_id": fed["foundup_id"],
            "tenant_id": fed["tenant_id"],
            "source_scope": fed["source_scope"],
            "external_repo": fed["external_repo"],
        }
        if cube:
            meta["cube"] = cube
        metadatas.append(meta)

    next_idx = len(ids) + 1
    for web_asset in web_assets:
        ids.append(f"code_{next_idx}")
        next_idx += 1
        embeddings.append(holo._get_embedding(web_asset["payload"]))
        documents.append(web_asset["location"])
        cube = holo._infer_cube_tag(web_asset["need"], web_asset["location"], web_asset["summary"])
        web_fed = resolve_foundup_metadata(
            holo.project_root / web_asset["location"], holo.project_root
        )
        meta = {
            "need": web_asset["need"],
            "type": "web_asset",
            "source": "public_asset_index",
            "path": web_asset["location"],
            "summary": web_asset["summary"],
            "keywords": web_asset["keywords"],
            "priority": 4,
            "foundup_id": web_fed["foundup_id"],
            "tenant_id": web_fed["tenant_id"],
            "source_scope": web_fed["source_scope"],
            "external_repo": web_fed["external_repo"],
        }
        if cube:
            meta["cube"] = cube
        metadatas.append(meta)

    indexed_count = len(ids)
    holo.code_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    holo._log_agent_action("Code index refreshed on SSD", "OK")

    return IndexResult(
        discovered_count=discovered_count,
        indexed_count=indexed_count,
        collection_name=collection_name,
        warning="; ".join(
            value for value in (web_discovery.warning, nav_warning) if value
        ) or None,
        processed_count=len(nav_entries) + web_discovery.processed_count,
        failed_count=web_discovery.failed_count + nav_failed,
        source_manifest_digest=source_manifest_digest(
            {
                "navigation": nav_entries,
                "navigation_source_manifest": nav_manifest,
                "web_asset_source_manifest": web_discovery.source_manifest_digest,
            }
        ),
        source_scope_id=(
            web_discovery.source_scope_id
            if nav_failed == 0
            else ""
        ),
    )


def index_symbol_entries(holo: "HoloIndex", roots: Optional[List[Path]] = None) -> IndexResult:
    """Delegate complete symbol maintenance to the focused indexer."""

    from holo_index.symbol_indexer import index_symbol_entries as _index_symbols

    return _index_symbols(holo, roots)


def _wsp_source_roots(
    holo: "HoloIndex",
    paths: Optional[List[Path]],
) -> List[Path]:
    values = (
        [Path(value) for value in CANONICAL_WSP_RELATIVE_ROOTS]
        if paths is None
        else [Path(value) for value in paths]
    )
    return [
        value if value.is_absolute() else holo.project_root / value
        for value in values
    ]


def _wsp_source_set(
    holo: "HoloIndex",
    paths: Optional[List[Path]],
) -> tuple[List[Path], str, str]:
    roots = _wsp_source_roots(holo, paths)
    canonical_roots = tuple(sorted(CANONICAL_WSP_RELATIVE_ROOTS))
    scope_id = (
        canonical_source_scope_id("navigation_wsp")
        if normalized_relative_roots(holo.project_root, roots) == canonical_roots
        else ""
    )
    files: List[Path] = []
    for root in roots:
        if not root.exists():
            holo._log_agent_action(f"WSP path not found: {root}", "WARN")
            continue
        files.extend(sorted(root.glob("WSP_*.md")))
    files = [
        path
        for path in files
        if not any(
            _has_dotfile_in_relative_path(path, root)
            for root in roots
            if path.is_relative_to(root)
        )
        and "_backup" not in str(path).lower()
    ]
    if not scope_id:
        return files, "", ""
    try:
        return filter_git_tracked_files(holo.project_root, files), scope_id, ""
    except CanonicalSourceScopeError as exc:
        return files, "", str(exc)


def index_wsp_entries(holo: "HoloIndex", paths: Optional[List[Path]] = None) -> IndexResult:
    """Index WSP protocol documents into ChromaDB.

    CFZ4: ONLY indexes true WSP protocols (WSP_*.md files).
    Module docs, papers, and other content go to separate collections.

    Args:
        holo: HoloIndex instance
        paths: Optional list of paths to search for WSP_*.md files.
               If None, defaults to WSP_framework/src.
               WSP purity enforced: Only WSP_*.md files are indexed regardless of paths.

    Returns:
        IndexResult with discovered_count, indexed_count, collection_name,
        and optional warning message.
    """
    collection_name = "navigation_wsp"
    files, scope_id, source_error = _wsp_source_set(holo, paths)
    if source_error:
        return IndexResult(
            discovered_count=len(files),
            indexed_count=0,
            collection_name=collection_name,
            warning=source_error,
            processed_count=0,
            failed_count=1,
            source_scope_id="",
        )

    discovered_count = len(files)

    if not files:
        holo._log_agent_action("No WSP documents found to index", "WARN")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning="No WSP documents found to index"
        )

    try:
        manifest_digest = source_file_manifest_digest(
            files,
            project_root=holo.project_root,
        )
    except OSError as exc:
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=0,
            collection_name=collection_name,
            warning=f"WSP source manifest read failed: {exc}",
            processed_count=0,
            failed_count=1,
            source_scope_id=scope_id,
        )

    holo._log_agent_action(f"Indexing {len(files)} WSP documents...", "INDEX")
    holo.wsp_collection = holo._reset_collection("navigation_wsp")

    ids, embeddings, documents, metadatas = [], [], [], []
    summary_cache: Dict[str, Dict[str, str]] = {}

    for idx, file_path in enumerate(files, start=1):
        # Detect UTF-16 LE (BOM FF FE) and decode correctly (WSP 90)
        raw_head = file_path.read_bytes()[:2]
        if raw_head == b'\xff\xfe':
            text = file_path.read_bytes().decode('utf-16-le', errors='ignore').lstrip('\ufeff')
            holo._log_agent_action(f"UTF-16 detected: {file_path.name} (decoded)", "WARN")
        else:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        title = lines[0].lstrip('# ')
        summary = ' '.join(lines[1:6])[:400]
        wsp_id = _extract_wsp_id(file_path.name, title)
        doc_type = _classify_document_type(file_path, title, lines)
        doc_payload = f"{title}\n{summary}"

        ids.append(f"wsp_{idx}")
        embeddings.append(holo._get_embedding(doc_payload))
        documents.append(doc_payload)
        cube = holo._infer_cube_tag(title, summary, str(file_path))
        wsp_fed = resolve_foundup_metadata(file_path, holo.project_root)
        metadata: Dict[str, Any] = {
            "wsp": wsp_id,
            "title": title,
            "path": str(file_path),
            "summary": summary,
            "type": doc_type,
            "priority": _calculate_document_priority(doc_type, file_path),
            "foundup_id": wsp_fed["foundup_id"],
            "tenant_id": wsp_fed["tenant_id"],
            "source_scope": wsp_fed["source_scope"],
            "external_repo": wsp_fed["external_repo"],
        }
        if cube:
            metadata["cube"] = cube
        metadatas.append(metadata)
        summary_cache[wsp_id] = {
            "title": title,
            "path": str(file_path),
            "summary": summary,
        }

    indexed_count = len(ids)

    if embeddings:
        if os.getenv("HOLO_VERBOSE", "").lower() in {"1", "true", "yes"}:
            holo._log_agent_action(
                f"WSP Index counts: ids={len(ids)} docs={len(documents)} embeds={len(embeddings)}",
                "DEBUG",
            )
        holo.wsp_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        holo.wsp_summary = summary_cache
        holo.wsp_summary_file.write_text(json.dumps(holo.wsp_summary, indent=2), encoding='utf-8')
        holo._log_agent_action("WSP index refreshed and summary cache saved", "OK")
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=indexed_count,
            collection_name=collection_name,
            processed_count=discovered_count,
            source_manifest_digest=manifest_digest,
            source_scope_id=scope_id,
        )
    else:
        holo._log_agent_action("No WSP entries were indexed (empty content)", "WARN")
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=0,
            collection_name=collection_name,
            warning="No WSP entries were indexed — all discovered files had empty content"
        )


def index_docs_entries(holo: "HoloIndex") -> IndexResult:
    """Index governed Markdown documents through the bounded docs module."""

    return _index_docs_entries(
        holo,
        DocumentIndexDependencies(
            result_type=IndexResult,
            source_file_manifest_digest=source_file_manifest_digest,
            classify_document_type=_classify_document_type,
            calculate_document_priority=_calculate_document_priority,
            extract_slice_id=_extract_slice_id,
            resolve_foundup_metadata=resolve_foundup_metadata,
            canonical_source_scope_id=canonical_source_scope_id,
        ),
    )


def index_knowledge_entries(holo: "HoloIndex") -> IndexResult:
    """CFZ4: Index papers/research into navigation_knowledge collection.

    Content: WSP_knowledge/docs/Papers/**
    ID prefix: paper_ (summary), paper_{idx}_chunk_{m} (body chunks)

    Full-body chunking: Each paper gets a summary record plus heading-based
    chunks so deep sections (e.g., rESP §4.4) are retrievable.

    Returns:
        IndexResult with discovered_count, indexed_count, collection_name,
        and optional warning message.
    """
    collection_name = "navigation_knowledge"
    knowledge_path = holo.project_root / "WSP_knowledge" / "docs" / "Papers"
    from holo_index.canonical_source_manifest import _knowledge_source_files

    if not knowledge_path.exists():
        holo._log_agent_action(f"Knowledge path not found: {knowledge_path}", "WARN")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning=f"Knowledge path not found: {knowledge_path}"
        )

    files = _knowledge_source_files(holo)

    discovered_count = len(files)

    if not files:
        holo._log_agent_action("No knowledge files found to index", "WARN")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning="No knowledge files found to index"
        )

    manifest_digest = source_file_manifest_digest(
        files,
        project_root=holo.project_root,
    )

    holo._log_agent_action(f"Indexing {len(files)} papers into navigation_knowledge...", "INDEX")
    holo.knowledge_collection = holo._reset_collection("navigation_knowledge")

    ids, embeddings, documents, metadatas = [], [], [], []
    batch_size = 100

    for idx, file_path in enumerate(files, start=1):
        raw_head = file_path.read_bytes()[:2]
        if raw_head == b'\xff\xfe':
            text = file_path.read_bytes().decode('utf-16-le', errors='ignore').lstrip('\ufeff')
        else:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        title = lines[0].lstrip('# ')
        summary = ' '.join(lines[1:6])[:400]
        doc_payload = f"{title}\n{summary}"

        know_fed = resolve_foundup_metadata(file_path, holo.project_root)
        base_meta = {
            "title": title,
            "path": str(file_path),
            "type": "paper",
            "priority": 6,
            "foundup_id": know_fed["foundup_id"],
            "tenant_id": know_fed["tenant_id"],
            "source_scope": know_fed["source_scope"],
            "external_repo": know_fed["external_repo"],
        }

        ids.append(f"paper_{idx}")
        embeddings.append(holo._get_embedding(doc_payload))
        documents.append(doc_payload)
        metadatas.append({
            **base_meta,
            "summary": summary,
            "record_kind": "paper_summary",
            "section": "",
            "section_title": "",
        })

        chunks = _chunk_markdown_by_headings(text)
        for chunk_idx, chunk in enumerate(chunks):
            chunk_id = f"paper_{idx}_chunk_{chunk_idx}"
            chunk_payload = f"{title}\n[{chunk['section']}]\n{chunk['content']}"
            ids.append(chunk_id)
            embeddings.append(holo._get_embedding(chunk_payload))
            documents.append(chunk_payload)
            metadatas.append({
                **base_meta,
                "record_kind": "paper_chunk",
                "section": chunk["section"],
                "section_title": chunk["section"],
            })

    indexed_count = len(ids)

    if embeddings:
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_emb = embeddings[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            holo.knowledge_collection.add(
                ids=batch_ids, embeddings=batch_emb,
                documents=batch_docs, metadatas=batch_meta
            )
        holo._log_agent_action(
            f"Knowledge index refreshed: {discovered_count} papers, {indexed_count} records (summaries + chunks)",
            "OK"
        )
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=indexed_count,
            collection_name=collection_name,
            processed_count=discovered_count,
            source_manifest_digest=manifest_digest,
            source_scope_id=canonical_source_scope_id(collection_name),
        )
    else:
        holo._log_agent_action("No knowledge entries were indexed", "WARN")
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=0,
            collection_name=collection_name,
            warning="No knowledge entries were indexed — all discovered files had empty content"
        )


def index_test_registry(holo: "HoloIndex") -> IndexResult:
    """Delegate canonical registry maintenance to the focused indexer."""

    from holo_index.test_registry_indexer import index_test_registry as _index_tests

    return _index_tests(holo)


def index_skillz_entries(holo: "HoloIndex") -> IndexResult:
    """WSP 95: Index SKILLz files for agent discovery.

    Returns:
        IndexResult with discovered_count, indexed_count, collection_name,
        and optional warning message.
    """
    import yaml
    from holo_index.canonical_source_manifest import _skill_source_files

    collection_name = "navigation_skills"
    files = _skill_source_files(holo)

    discovered_count = len(files)

    if not files:
        holo._log_agent_action("No SKILLz files found to index", "WARN")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning="No SKILLz files found to index"
        )

    manifest_digest = source_file_manifest_digest(
        files,
        project_root=holo.project_root,
    )
    holo._log_agent_action(f"Indexing {len(files)} SKILLz files...", "INDEX")
    holo.skill_collection = holo._reset_collection("navigation_skills")

    ids, embeddings, documents, metadatas = [], [], [], []
    failed_count = 0

    for idx, file_path in enumerate(files, start=1):
        try:
            text = file_path.read_text(encoding='utf-8', errors='ignore')

            # Parse YAML frontmatter
            frontmatter: Dict[str, Any] = {}
            if text.startswith('---'):
                parts = text.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                    except Exception:
                        pass
                    content = parts[2]
                else:
                    content = text
            else:
                content = text

            name = str(frontmatter.get('name', file_path.parent.name) or file_path.parent.name)
            description_raw = frontmatter.get('description', '')
            description = str(description_raw) if description_raw is not None else ''
            agents = frontmatter.get('agents', [])
            primary_agent = str(frontmatter.get('primary_agent', 'unknown') or 'unknown')
            intent_type = str(frontmatter.get('intent_type', 'unknown') or 'unknown')
            promotion_state = str(frontmatter.get('promotion_state', 'prototype') or 'prototype')

            lines = content.strip().split('\n')
            summary = ' '.join(lines[:10])[:500]
            doc_payload = (
                f"Skillz: {name}\n"
                f"Agent: {primary_agent}\n"
                f"Type: {intent_type}\n"
                f"Description: {description}\n"
                f"{summary}"
            )
            skill_fed = resolve_foundup_metadata(file_path, holo.project_root)
            metadata: Dict[str, Any] = {
                "skill_name": name,
                "description": description[:500],
                "agents": (
                    ','.join(str(agent) for agent in agents)
                    if isinstance(agents, list)
                    else str(agents)
                ),
                "primary_agent": primary_agent,
                "intent_type": intent_type,
                "promotion_state": promotion_state,
                "path": str(file_path),
                "type": "skillz",
                "priority": 9,
                "foundup_id": skill_fed["foundup_id"],
                "tenant_id": skill_fed["tenant_id"],
                "source_scope": skill_fed["source_scope"],
                "external_repo": skill_fed["external_repo"],
            }

            embedding = holo._get_embedding(doc_payload)
            ids.append(f"skill_{idx}")
            embeddings.append(embedding)
            documents.append(doc_payload)
            metadatas.append(metadata)

        except Exception as e:
            failed_count += 1
            holo._log_agent_action(f"Failed to parse SKILLz {file_path}: {e}", "WARN")
            continue

    indexed_count = len(ids)

    if embeddings:
        if not (len(ids) == len(embeddings) == len(documents) == len(metadatas)):
            holo._log_agent_action(
                (
                    "SKILLz index length mismatch detected "
                    f"(ids={len(ids)}, embeddings={len(embeddings)}, "
                    f"documents={len(documents)}, metadatas={len(metadatas)}). "
                    "Aborting collection add."
                ),
                "ERROR",
            )
            return IndexResult(
                discovered_count=discovered_count,
                indexed_count=0,
                collection_name=collection_name,
                warning="SKILLz index length mismatch — aborting collection add"
            )
        holo.skill_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        holo._log_agent_action(f"SKILLz index refreshed: {len(embeddings)} skills indexed", "OK")
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=indexed_count,
            collection_name=collection_name,
            warning=(
                f"Failed to parse {failed_count} SKILLz sources"
                if failed_count
                else None
            ),
            processed_count=discovered_count,
            failed_count=failed_count,
            source_manifest_digest=manifest_digest,
            source_scope_id=canonical_source_scope_id(collection_name),
        )
    else:
        holo._log_agent_action("No SKILLz entries were indexed", "WARN")
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=0,
            collection_name=collection_name,
            warning="No SKILLz entries were indexed — all discovered files had empty or invalid content"
        )


# ---------------------------------------------------------------------------
# Work Ledger Indexing (FOUNDUPS_WORK_LEDGER_HOLOINDEX_IMPLEMENTATION_PHASE1)
# ---------------------------------------------------------------------------

def _calculate_freshness(last_verified_at: str | None) -> float:
    """Calculate freshness score from last_verified_at timestamp.

    Returns 1.0 for today, decays to 0.5 at 14 days, 0.1 at 30 days.
    """
    if not last_verified_at:
        return 0.5

    try:
        verified = datetime.fromisoformat(last_verified_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - verified).days

        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.9
        elif age_days <= 14:
            return 0.7
        elif age_days <= 30:
            return 0.5
        else:
            return max(0.1, 0.5 - (age_days - 30) * 0.01)
    except Exception:
        return 0.5


# Status ranking weights for work ledger queries
WORK_LEDGER_STATUS_RANKING = {
    "IN_PROGRESS": 1.0,
    "STAGED_FOR_W10": 0.95,
    "PR_OPEN": 0.9,
    "ASSIGNED": 0.8,
    "PROPOSED": 0.7,
    "BLOCKED": 0.5,
    "PARKED": 0.4,
    "MERGED": 0.3,
    "CLOSED": 0.3,
    "SUPERSEDED": 0.1,
    "ABANDONED": 0.05,
}


def index_work_ledger_entries(holo: "HoloIndex") -> IndexResult:
    """Index work ledger slices for semantic search.

    Spec: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1
    Source: docs/0102_session_briefings/work_ledger.example.json

    Extracts each slice entry as a searchable document with metadata fields:
    - slice_id, title, lane, priority, status, owner_worker
    - source, branch, pr_number, related_foundup_id
    - related_wsp_joined, blocked_by_joined, next_slice
    - last_verified_at, freshness_score, status_rank

    Returns:
        IndexResult with discovered_count, indexed_count, collection_name,
        and optional warning message.
    """
    collection_name = "navigation_work_ledger"
    ledger_path = holo.project_root / "docs" / "0102_session_briefings" / "work_ledger.example.json"

    if not ledger_path.exists():
        holo._log_agent_action("work_ledger.example.json not found", "WARN")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning="work_ledger.example.json not found"
        )

    try:
        ledger_data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception as e:
        holo._log_agent_action(f"Failed to load work ledger: {e}", "ERROR")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning=f"Failed to load work ledger: {e}"
        )

    slices = ledger_data.get("slices", [])
    discovered_count = len(slices)

    if not slices:
        holo._log_agent_action("Work ledger has no slices", "WARN")
        return IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning="Work ledger has no slices"
        )

    manifest_digest = source_manifest_digest(ledger_data)
    holo._log_agent_action(f"Indexing {len(slices)} work ledger slices...", "INDEX")
    holo.work_ledger_collection = holo._reset_collection("navigation_work_ledger")

    ids: List[str] = []
    embeddings: List[List[float]] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for idx, slice_entry in enumerate(slices, start=1):
        slice_id = slice_entry.get("slice_id", f"unknown_{idx}")
        title = slice_entry.get("title", "")
        lane = slice_entry.get("lane")
        priority = slice_entry.get("priority", "P3")
        status = slice_entry.get("status", "PROPOSED")
        owner_worker = slice_entry.get("owner_worker")
        source = slice_entry.get("source", "manual")
        branch = slice_entry.get("branch")
        pr_number = slice_entry.get("pr_number")
        related_foundup_id = slice_entry.get("related_foundup_id")
        related_wsp = slice_entry.get("related_wsp", [])
        blocked_by = slice_entry.get("blocked_by", [])
        next_slice = slice_entry.get("next_slice")
        last_verified_at = slice_entry.get("last_verified_at")
        evidence_docs = slice_entry.get("evidence_docs", [])
        wsp_97_labels = slice_entry.get("wsp_97_labels", [])

        related_wsp_joined = "|".join(related_wsp) if related_wsp else ""
        blocked_by_joined = "|".join(blocked_by) if blocked_by else ""
        evidence_docs_joined = "|".join(evidence_docs) if evidence_docs else ""
        wsp_labels_joined = "|".join(wsp_97_labels) if wsp_97_labels else ""

        freshness_score = _calculate_freshness(last_verified_at)
        status_rank = WORK_LEDGER_STATUS_RANKING.get(status, 0.5)

        doc_payload = (
            f"Work Slice: {slice_id}\n"
            f"Title: {title}\n"
            f"Status: {status}\n"
            f"Priority: {priority}\n"
            f"Owner: {owner_worker or 'unassigned'}\n"
            f"Lane: {lane or 'unassigned'}\n"
            f"Branch: {branch or 'none'}\n"
            f"PR: {pr_number or 'none'}\n"
            f"Related FoundUp: {related_foundup_id or 'none'}\n"
            f"Related WSPs: {related_wsp_joined or 'none'}\n"
            f"Blocked by: {blocked_by_joined or 'none'}\n"
            f"Next slice: {next_slice or 'none'}\n"
        )

        metadata: Dict[str, Any] = {
            "slice_id": slice_id,
            "title": title,
            "lane": lane or "",
            "priority": priority,
            "status": status,
            "owner_worker": owner_worker or "",
            "source": source,
            "branch": branch or "",
            "pr_number": pr_number if pr_number is not None else -1,
            "related_foundup_id": related_foundup_id or "",
            "related_wsp_joined": related_wsp_joined,
            "blocked_by_joined": blocked_by_joined,
            "next_slice": next_slice or "",
            "evidence_docs_joined": evidence_docs_joined,
            "wsp_labels_joined": wsp_labels_joined,
            "last_verified_at": last_verified_at or "",
            "freshness_score": freshness_score,
            "status_rank": status_rank,
            "type": "work_ledger_slice",
            "priority_num": 10,
            "path": str(ledger_path),
        }

        embedding = holo._get_embedding(doc_payload)
        ids.append(f"slice_{idx}")
        embeddings.append(embedding)
        documents.append(doc_payload)
        metadatas.append(metadata)

    indexed_count = len(ids)

    if embeddings:
        if not (len(ids) == len(embeddings) == len(documents) == len(metadatas)):
            holo._log_agent_action(
                f"Work ledger index length mismatch (ids={len(ids)}, embeddings={len(embeddings)}, "
                f"documents={len(documents)}, metadatas={len(metadatas)}). Aborting.",
                "ERROR",
            )
            return IndexResult(
                discovered_count=discovered_count,
                indexed_count=0,
                collection_name=collection_name,
                warning="Work ledger index length mismatch — aborting collection add"
            )
        holo.work_ledger_collection.add(
            ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )
        holo._log_agent_action(f"Work ledger index refreshed: {len(embeddings)} slices indexed", "OK")
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=indexed_count,
            collection_name=collection_name,
            processed_count=discovered_count,
            source_manifest_digest=manifest_digest,
        )
    else:
        holo._log_agent_action("No work ledger entries were indexed", "WARN")
        return IndexResult(
            discovered_count=discovered_count,
            indexed_count=0,
            collection_name=collection_name,
            warning="No work ledger entries were indexed"
        )
