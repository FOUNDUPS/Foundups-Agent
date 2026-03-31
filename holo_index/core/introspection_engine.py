# -*- coding: utf-8 -*-
"""HoloIndex Introspection Engine — module compliance and preview enrichment.

Provides module existence checks, TypeScript entity parsing, and code
preview enrichment previously inlined in HoloIndex.

All public functions accept a ``holo`` (HoloIndex instance) parameter where
instance state is needed (project_root, need_to, _ts_entity_cache).
Stateless helpers are plain module-level functions.

WSP Compliance: WSP 87 (Size Limits), WSP 72 (Block Independence)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .holo_index import HoloIndex


# ---------------------------------------------------------------------------
# TypeScript regex patterns
# ---------------------------------------------------------------------------

TS_FUNCTION_PATTERN = re.compile(r'^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(?P<name>[A-Za-z0-9_]+)\s*\(')
TS_CLASS_PATTERN = re.compile(r'^(?:export\s+)?(?:abstract\s+)?class\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_INTERFACE_PATTERN = re.compile(r'^(?:export\s+)?interface\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_TYPE_PATTERN = re.compile(r'^(?:export\s+)?type\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_ENUM_PATTERN = re.compile(r'^(?:export\s+)?enum\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_CONST_PATTERN = re.compile(r'^(?:export\s+)?const\s+(?P<name>[A-Za-z0-9_]+)\s*(?::[^=]+)?=')
TS_ARRAY_STATE_PATTERN = re.compile(r'^(?:export\s+)?const\s+\[\s*(?P<name>[A-Za-z0-9_]+)')


# ---------------------------------------------------------------------------
# Stateless helpers
# ---------------------------------------------------------------------------

def _normalize_symbol_key(symbol: str) -> str:
    """Normalize symbol names for consistent dictionary lookups."""
    if not symbol:
        return ""
    return re.sub(r'[^a-z0-9]+', '', symbol.lower())


def _build_preview_from_lines(lines: List[str], index: int, context: int = 6) -> str:
    start = max(0, index - context)
    end = min(len(lines), index + context + 1)
    preview = '\n'.join(lines[start:end]).strip()
    if len(preview) > 400:
        preview = preview[:400] + "..."
    return preview or "[No preview available]"


def parse_typescript_entities(lines: List[str], context: int = 6) -> Dict[str, Dict[str, Any]]:
    """Extract TypeScript/TSX entities (components, hooks, interfaces, etc.) from raw lines."""
    entities: Dict[str, Dict[str, Any]] = {}

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('//'):
            continue

        entry: Optional[Dict[str, Any]] = None
        match = TS_ARRAY_STATE_PATTERN.match(stripped)
        if match and ('useState' in stripped or 'useReducer' in stripped):
            name = match.group('name')
            entry = {"name": name, "kind": "state"}
        else:
            for kind, pattern in (
                ("function", TS_FUNCTION_PATTERN),
                ("const", TS_CONST_PATTERN),
                ("class", TS_CLASS_PATTERN),
                ("interface", TS_INTERFACE_PATTERN),
                ("type", TS_TYPE_PATTERN),
                ("enum", TS_ENUM_PATTERN),
            ):
                match = pattern.match(stripped)
                if match:
                    name = match.group('name')
                    entry = {"name": name, "kind": kind}
                    break

        if not entry:
            continue

        normalized_key = _normalize_symbol_key(entry["name"])
        if not normalized_key:
            continue

        preview = _build_preview_from_lines(lines, idx, context)
        entities[normalized_key] = {
            "name": entry["name"],
            "line": idx + 1,
            "preview": preview,
            "kind": entry["kind"]
        }

        # Capture both state variable and setter for destructured hooks
        if entry["kind"] == "state" and 'set' in stripped:
            setter_match = re.search(r'set([A-Za-z0-9_]+)', stripped)
            if setter_match:
                setter_name = setter_match.group(1)
                setter_key = _normalize_symbol_key(setter_name)
                if setter_key and setter_key not in entities:
                    entities[setter_key] = {
                        "name": setter_name,
                        "line": idx + 1,
                        "preview": preview,
                        "kind": "state_setter"
                    }

    return entities


# ---------------------------------------------------------------------------
# File / symbol resolution helpers
# ---------------------------------------------------------------------------

def _resolve_location_parts(holo: "HoloIndex", location: str) -> Tuple[Optional[Path], Optional[str]]:
    """Parse a NAVIGATION location string into file path + optional symbol/line descriptor."""
    if not location:
        return None, None

    normalized = location.strip()
    if not normalized:
        return None, None

    symbol = None
    split_idx = normalized.rfind(':')
    filepath = normalized

    if split_idx > 1:
        filepath = normalized[:split_idx]
        symbol = normalized[split_idx + 1:].strip() or None

    try:
        raw_filepath = filepath.strip()

        filepath_candidates = [raw_filepath]
        for sep in (" - ", " \u2014 ", " \u2013 "):
            if sep in raw_filepath:
                filepath_candidates.append(raw_filepath.split(sep, 1)[0].strip())

        resolved_first: Optional[Path] = None
        for candidate in filepath_candidates:
            if not candidate:
                continue
            file_path = Path(candidate)
            if not file_path.is_absolute():
                file_path = (holo.project_root / candidate).resolve()
            if resolved_first is None:
                resolved_first = file_path
            if file_path.exists():
                return file_path, symbol

        return resolved_first, symbol
    except Exception:
        return None, symbol


def _find_symbol_line(file_path: Path, symbol: Optional[str]) -> Optional[int]:
    """Heuristic search for a symbol name within a file to approximate its line number."""
    if not symbol or not file_path.exists():
        return None

    target = symbol.replace('()', '').strip()
    if not target:
        return None

    primary = target.split()[0]
    candidates = [target, primary]
    seen: set[str] = set()

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as handle:
            lines = handle.readlines()
    except Exception:
        return None

    for idx, line in enumerate(lines, start=1):
        lowered = line.lower()
        for candidate in candidates:
            key = candidate.lower()
            if key in seen:
                continue
            if key and key in lowered:
                seen.add(key)
                return idx

    return None


# ---------------------------------------------------------------------------
# TypeScript entity extraction (instance-dependent via cache)
# ---------------------------------------------------------------------------

def _extract_typescript_entities(holo: "HoloIndex", file_path: Path) -> Dict[str, Dict[str, Any]]:
    """Parse TypeScript/TSX file for entity metadata with simple caching."""
    suffix = file_path.suffix.lower()
    if suffix not in {'.ts', '.tsx', '.jsx'}:
        return {}

    try:
        stat = file_path.stat()
    except FileNotFoundError:
        return {}

    cache_entry = holo._ts_entity_cache.get(str(file_path))
    if cache_entry and cache_entry.get('mtime') == stat.st_mtime:
        return cache_entry.get('entities', {})

    try:
        text = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return {}

    lines = text.splitlines()
    entities = parse_typescript_entities(lines)
    holo._ts_entity_cache[str(file_path)] = {
        "mtime": stat.st_mtime,
        "entities": entities
    }
    return entities


def _match_typescript_entity(symbol: Optional[str], entities: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[int]]:
    """Match a NAVIGATION symbol description to a parsed TypeScript entity."""
    if not symbol or not entities:
        return None, None

    cleaned = symbol.strip()
    if not cleaned:
        return None, None

    cleaned = cleaned.replace('()', '')
    candidates = [cleaned]

    if '(' in symbol:
        candidates.append(symbol.split('(', 1)[0])
    if ' ' in cleaned:
        candidates.append(cleaned.split(' ', 1)[0])

    for candidate in candidates:
        key = _normalize_symbol_key(candidate)
        if key and key in entities:
            entry = entities[key]
            return entry.get('preview'), entry.get('line')

    return None, None


def _extract_ast_preview(filepath: str, match_line: int, context: int = 6) -> str:
    """Extract surrounding code block for preview."""
    try:
        file_path = Path(filepath)
        if not file_path.exists():
            return "[File not found]"

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.read().splitlines()

        if not lines or match_line <= 0 or match_line > len(lines):
            return "[Invalid line range]"

        start_line = max(0, match_line - context - 1)
        end_line = min(len(lines), match_line + context)

        preview_lines = lines[start_line:end_line]
        preview = '\n'.join(preview_lines).strip()

        if len(preview) > 400:
            preview = preview[:400] + "..."

        return preview if preview else "[No preview available]"

    except Exception as e:
        return f"[0102 preview extraction error: {str(e)}]"


# ---------------------------------------------------------------------------
# Preview enrichment (called by search_engine via holo delegate)
# ---------------------------------------------------------------------------

def enhance_code_results_with_previews(holo: "HoloIndex", code_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enhance code results with AST-based previews for empty results."""
    enhanced_hits = []

    for hit in code_hits:
        enhanced_hit = hit.copy()

        if enhanced_hit.get('preview'):
            enhanced_hits.append(enhanced_hit)
            continue

        location = (hit.get('location') or '').strip()
        if not location:
            enhanced_hit['preview'] = "[Location unavailable]"
            enhanced_hits.append(enhanced_hit)
            continue

        file_path, symbol = _resolve_location_parts(holo, location)
        if not file_path:
            enhanced_hit['preview'] = "[Location format error]"
            enhanced_hits.append(enhanced_hit)
            continue

        enhanced_hit['path'] = str(file_path)

        if not file_path.exists():
            enhanced_hit['preview'] = "[File not found]"
            enhanced_hits.append(enhanced_hit)
            continue

        preview = None
        line_num = None
        manual_preview = None

        suffix = file_path.suffix.lower()
        if symbol and suffix in {'.ts', '.tsx', '.jsx'}:
            entities = _extract_typescript_entities(holo, file_path)
            manual_preview, line_num = _match_typescript_entity(symbol, entities)

        # Numeric symbol is almost certainly a line number (e.g., "file.py:336")
        if line_num is None and symbol and symbol.isdigit():
            try:
                line_num = int(symbol)
            except ValueError:
                line_num = None

        if line_num is None:
            line_num = _find_symbol_line(file_path, symbol)

        if line_num:
            preview = _extract_ast_preview(str(file_path), line_num)
            enhanced_hit['line'] = line_num
        elif manual_preview:
            preview = manual_preview
        else:
            # Default to file header for human-friendly previews (docs/config files)
            preview = _extract_ast_preview(str(file_path), 1)
            enhanced_hit['line'] = 1

        enhanced_hit['preview'] = preview
        enhanced_hits.append(enhanced_hit)

    return enhanced_hits


# ---------------------------------------------------------------------------
# Module compliance introspection
# ---------------------------------------------------------------------------

def check_module_exists(holo: "HoloIndex", module_name: str) -> Dict[str, Any]:
    """WSP Compliance: Check if a module exists before code generation.

    Args:
        holo: HoloIndex instance (for project_root and need_to)
        module_name: Name of the module to check

    Returns:
        Dict with exists, path, compliance info, and recommendation.
    """
    project_root = Path(__file__).resolve().parents[2]
    normalized = module_name.strip().strip("/\\")
    normalized = normalized.replace("\\", "/")

    domains = [
        "modules/ai_intelligence",
        "modules/communication",
        "modules/platform_integration",
        "modules/infrastructure",
        "modules/monitoring",
        "modules/development",
        "modules/foundups",
        "modules/gamification",
        "modules/blockchain"
    ]
    domain_names = {Path(d).name for d in domains}

    candidate_paths = []
    if normalized:
        candidate_paths.append(project_root / normalized)
        if normalized.startswith("modules/"):
            parts = normalized.split("/")
            if len(parts) >= 3:
                domain_part = parts[1]
                module_part = parts[2]
                candidate_paths.append(project_root / "modules" / domain_part / module_part)
        else:
            parts = normalized.split("/")
            if len(parts) >= 2 and parts[0] in domain_names:
                domain_part = parts[0]
                module_part = parts[1]
                candidate_paths.append(project_root / "modules" / domain_part / module_part)
            if len(parts) >= 3 and parts[0] == "modules":
                domain_part = parts[1]
                module_part = parts[2]
                candidate_paths.append(project_root / "modules" / domain_part / module_part)

    module_basename = normalized.split("/")[-1] if normalized else module_name.strip()
    for domain in domains:
        domain_path = project_root / domain
        candidate_paths.append(domain_path / module_basename)

    module_path = None
    seen = set()
    for candidate in candidate_paths:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.is_dir():
            module_path = resolved
            break

    if not module_path:
        similar_modules = []
        key = normalized.lower() if normalized else module_name.lower()
        for need, location in holo.need_to.items():
            if key in need.lower() or key in location.lower():
                path_parts = location.split('/')
                if len(path_parts) >= 3 and path_parts[0] == 'modules':
                    module_path_str = '/'.join(path_parts[:4])
                    if module_path_str not in similar_modules:
                        similar_modules.append(module_path_str)

        return {
            "exists": False,
            "module_name": module_name,
            "similar_modules": similar_modules,
            "recommendation": f"[BLOCKED] MODULE '{module_name}' DOES NOT EXIST - DO NOT CREATE IT! " +
                               (f"Similar modules found: {', '.join(similar_modules)}. " if similar_modules else "") +
                               "ENHANCE EXISTING MODULES - DO NOT VIBECODE (See WSP_84_Module_Evolution). " +
                               "Use --search to find existing functionality FIRST before ANY code generation."
        }

    try:
        module_label = str(module_path.relative_to(project_root))
    except ValueError:
        module_label = str(module_path)

    readme_exists = (module_path / "README.md").exists()
    interface_exists = (module_path / "INTERFACE.md").exists()
    roadmap_exists = (module_path / "ROADMAP.md").exists()
    modlog_exists = (module_path / "ModLog.md").exists()
    requirements_exists = (module_path / "requirements.txt").exists()
    tests_exist = (module_path / "tests").exists()
    memory_exists = (module_path / "memory").exists()

    compliance_score = sum([
        readme_exists, interface_exists, roadmap_exists,
        modlog_exists, requirements_exists, tests_exist, memory_exists
    ])

    wsp_compliance = "[VIOLATION] NON-COMPLIANT" if compliance_score < 7 else "[COMPLIANT] COMPLIANT"

    health_warnings = []
    if not tests_exist:
        health_warnings.append("Missing tests directory (WSP 49)")
    if not readme_exists:
        health_warnings.append("Missing README.md (WSP 22)")
    if not interface_exists:
        health_warnings.append("Missing INTERFACE.md (WSP 11)")

    return {
        "exists": True,
        "module_name": module_label,
        "path": str(module_path),
        "readme_exists": readme_exists,
        "interface_exists": interface_exists,
        "roadmap_exists": roadmap_exists,
        "modlog_exists": modlog_exists,
        "requirements_exists": requirements_exists,
        "tests_exist": tests_exist,
        "memory_exists": memory_exists,
        "wsp_compliance": wsp_compliance,
        "compliance_score": f"{compliance_score}/7",
        "health_warnings": health_warnings,
        "recommendation": f"Module '{module_label}' exists at {module_path}. " +
                           (f"WSP Compliance: {wsp_compliance}. " if wsp_compliance == "[VIOLATION] NON-COMPLIANT" else "[COMPLIANT] WSP Compliant. ") +
                           ("MANDATORY: Read README.md and INTERFACE.md BEFORE making changes. " if readme_exists and interface_exists else "CRITICAL: Create missing documentation FIRST (WSP_22_Documentation). ")
    }
