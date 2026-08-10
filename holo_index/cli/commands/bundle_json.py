# -*- coding: utf-8 -*-
"""
Bundle JSON command handler - WSP_CORE Memory System JSON output mode.

Extracted from holo_index/cli.py (lines 634-960).
Self-contained lexical search + artifact snapshot + JSON bundle output.
"""

import json as _json
import os
import re
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from holo_index.cli.bundle_path_confinement import (
    LEXICAL_NAVIGATION_MAX_BYTES,
    _artifact_exists,
    _bounded_directory_names,
    _bounded_module_files,
    _confined_repo_path,
    _read_confined_text,
    _resolve_module_dir,
)
from holo_index.cli.direct_read_path_policy import (
    direct_read_deny_reason as _direct_read_deny_reason,
    normalize_direct_read_path as _normalize_direct_read_path,
)
from holo_index.query_admission import evaluate_readonly_query_admission


def _env_truthy(key: str, default: str = "false") -> bool:
    """Check if environment variable is truthy."""
    return os.getenv(key, default).lower() in {"1", "true", "yes", "on"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _persistent_query_denial(repo_root, ssd_path):
    """Return a content-free denial before bundle backend construction."""
    admission = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
    )
    if admission.allowed:
        return None
    return admission.to_dict()


# ---------------------------------------------------------------------------
# REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3): governed direct-read.
#
# When slice-1's detector reports an index gap on an explicit required-target
# list, the extension asks the Python bundle layer (this module) to fetch those
# exact repo files' content so RedDog reasons on real source instead of HOLDing
# blind. This is a READ-ONLY capability with a HARD security allowlist. It adds
# no execution authority, no write path, and no shell-out. Fetched content still
# passes through the EXISTING extension.js redaction gate unchanged (slice 3
# owns redaction-category behavior).
# ---------------------------------------------------------------------------

# Per-file byte cap: many targets each get a bounded snippet rather than one
# file consuming the whole budget (the failing run truncated a single 24K/104K
# file and dropped the rest).
DIRECT_READ_PER_FILE_BYTES = 12000
# Total fetch budget across ALL targets. Spread so many targets each land.
DIRECT_READ_TOTAL_BUDGET_BYTES = 96000
# Hard cap on how many targets we will even attempt (defensive; ranked by order).
DIRECT_READ_MAX_TARGETS = 40

# REDDOG_SYMBOL_AWARE_EXCERPT_DEPTH_PHASE1: when a target is `path#symbol`, return a bounded LINE
# WINDOW around the symbol's DEFINITION instead of the head-clip, so a symbol defined deep in a large
# file (e.g. build_foundup / extract_foundup past the 12KB head) actually reaches the model. The
# window is still clamped to DIRECT_READ_PER_FILE_BYTES + the total budget. To LOCATE the symbol we
# may scan past the head, but only up to a hard cap (transient; never inlined) so a pathological file
# cannot force an unbounded read. Symbol is an OPAQUE search key -- never a path segment.
DIRECT_READ_SYMBOL_SCAN_BYTES = 262144   # max bytes scanned to LOCATE a symbol (not inlined)
DIRECT_READ_SYMBOL_LEAD_LINES = 6        # context lines kept BEFORE the def line (decorators/docstring)
# Cap symbol targets per file so a caller naming MANY (plausible-but-absent) symbols of ONE file
# cannot consume all target slots (DIRECT_READ_MAX_TARGETS) and starve other required targets.
DIRECT_READ_MAX_SYMBOLS_PER_PATH = 8
LEXICAL_WSP_MAX_ENTRIES = 512
LEXICAL_WSP_MAX_FILES = 256
LEXICAL_WSP_READ_BYTES = 16384
# A valid symbol is a bounded identifier. Rejecting anything else keeps the symbol an opaque, safe
# search key (no regex-injection, no path traversal via the '#' suffix).
_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")

def _resolve_within_repo(repo_root, rel_norm: str):
    """Resolve rel_norm against repo_root and verify realpath containment.

    Returns (real_path, None) on success or (None, reason) when the resolved
    real path escapes the repo root (covers symlink-escape). Never raises.
    """
    from pathlib import Path as _Path
    try:
        root_real = _Path(os.path.realpath(str(repo_root)))
        candidate = (root_real / rel_norm)
        real = _Path(os.path.realpath(str(candidate)))
    except Exception:
        return None, "path_missing"
    try:
        real.relative_to(root_real)
    except ValueError:
        return None, "outside_root"
    try:
        if real.is_file() and os.stat(real, follow_symlinks=False).st_nlink > 1:
            return None, "hardlink_denied"
    except OSError:
        return None, "path_missing"
    return real, None


def _read_bounded_direct_read(real_path, per_file_cap: int, remaining_budget: int):
    """Read a bounded UTF-8 snippet honoring per-file cap and remaining budget.

    Returns dict: {content, bytes, truncated, omitted_reason}. Binary files and
    read errors are omitted (never abort the bundle).
    """
    from pathlib import Path as _Path
    p = _Path(real_path)
    try:
        if not p.is_file():
            return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "not_a_file"}
    except Exception:
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "path_missing"}

    cap = max(0, min(per_file_cap, remaining_budget))
    if cap <= 0:
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "budget_exhausted"}
    try:
        with open(p, "rb") as fh:
            raw = fh.read(cap + 1)
    except Exception:
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "read_error"}
    # Binary sniff: a NUL byte in the head means "not source we should inline".
    if b"\x00" in raw:
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "binary"}
    truncated = len(raw) > cap
    clipped = raw[:cap]
    text = clipped.decode("utf-8", errors="replace")
    return {
        "content": text,
        "bytes": len(clipped),
        "truncated": truncated,
        "omitted_reason": "none",
    }


def _split_path_symbol(normalized: str) -> Tuple[str, Optional[str]]:
    """Split a normalized `path#symbol` target into (path, symbol).

    The symbol is an OPAQUE search key -- it is returned separately and NEVER used as a path
    segment (the deny/containment gates run on the path only). A target with no '#', or whose
    suffix is not a valid identifier, is returned as (target, None) so the whole string is
    treated as a path (backward-compatible; a real filename containing '#' is not a symbol).
    """
    s = str(normalized or "")
    if "#" not in s:
        return s, None
    path_part, _, sym = s.partition("#")
    sym = sym.strip()
    if _SYMBOL_RE.match(sym):
        return path_part, sym
    return s, None


def _locate_symbol_line(lines: List[str], symbol: str) -> Optional[int]:
    """0-based index of the best line for `symbol`: PREFER a definition line (a def/class/function/
    const/... keyword immediately followed by the symbol, or the symbol at line start followed by
    '=' / ':' / '('), else the FIRST whole-word occurrence. Matching is WORD-boundary (not
    substring) so 'build_foundup' does not match 'build_foundup_v2' or 'extract_build_foundup'.

    Prior art: holo_index/core/introspection_engine.py:_find_symbol_line (first-substring, reads the
    WHOLE file). Not reused here: this module requires a BOUNDED scan (the direct-read security model)
    and a DEFINITION preference (head-clip already had the first mention).
    """
    esc = re.escape(symbol)
    word = re.compile(r"(?<![A-Za-z0-9_])" + esc + r"(?![A-Za-z0-9_])")
    kw_def = re.compile(
        r"\b(?:async\s+def|def|class|function|func|fn|const|let|var|type|interface|struct|enum)\s+"
        + esc + r"(?![A-Za-z0-9_])")
    assign_def = re.compile(
        r"^\s*(?:export\s+|default\s+|public\s+|private\s+|protected\s+|static\s+|final\s+)*"
        + esc + r"\s*[=:(]")
    first_occ: Optional[int] = None
    for i, line in enumerate(lines):
        if not word.search(line):
            continue
        if first_occ is None:
            first_occ = i
        if kw_def.search(line) or assign_def.search(line):
            return i
    return first_occ


def _read_symbol_window(real_path, symbol, per_file_cap: int, remaining_budget: int):
    """Read a bounded LINE WINDOW around `symbol`'s definition (same return contract as
    _read_bounded_direct_read). Fail-closed omitted_reason values ('symbol_invalid',
    'symbol_not_found', 'symbol_window_empty', 'binary', 'read_error', 'budget_exhausted') tell the
    caller to fall back to the head-clip. The scan to LOCATE the symbol is bounded by
    DIRECT_READ_SYMBOL_SCAN_BYTES; the returned window is clamped to the per-file/remaining cap and
    ALWAYS includes the definition line (forward from the def line first, then lead context)."""
    from pathlib import Path as _Path
    if not (isinstance(symbol, str) and _SYMBOL_RE.match(symbol)):
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "symbol_invalid"}
    cap = max(0, min(per_file_cap, remaining_budget))
    if cap <= 0:
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "budget_exhausted"}
    try:
        with open(_Path(real_path), "rb") as fh:
            raw = fh.read(DIRECT_READ_SYMBOL_SCAN_BYTES + 1)
    except Exception:
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "read_error"}
    if b"\x00" in raw:  # binary sniff on the bytes we actually read
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "binary"}
    text = raw[:DIRECT_READ_SYMBOL_SCAN_BYTES].decode("utf-8", errors="replace")
    lines = text.split("\n")
    idx = _locate_symbol_line(lines, symbol)
    if idx is None:
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "symbol_not_found"}

    last = len(lines) - 1

    def _enc(j: int) -> Tuple[str, int]:
        piece = lines[j] + ("\n" if j < last else "")
        return piece, len(piece.encode("utf-8"))

    chosen = {}
    used = 0
    for j in range(idx, len(lines)):            # def line FIRST (guaranteed), then body forward
        piece, pb = _enc(j)
        if used + pb > cap:
            break
        chosen[j] = piece
        used += pb
    for j in range(idx - 1, max(-1, idx - 1 - DIRECT_READ_SYMBOL_LEAD_LINES), -1):  # lead context
        piece, pb = _enc(j)
        if used + pb > cap:
            break
        chosen[j] = piece
        used += pb
    if idx not in chosen:
        # The DEFINITION line itself did not fit the cap (e.g. a >12KB one-line def, a big inline
        # literal, or a minified single-line file). The lead loop may have added shorter preceding
        # lines, but shipping lead-ONLY context labeled as a successful symbol window would hide the
        # very symbol RedDog asked for (and falsely satisfy recall). Fail-closed -> head-clip fallback.
        return {"content": "", "bytes": 0, "truncated": False, "omitted_reason": "symbol_window_empty"}
    lo, hi = min(chosen), max(chosen)           # contiguous by construction (grown from idx both ways)
    content = "".join(chosen[j] for j in range(lo, hi + 1))
    truncated = (lo > 0) or (hi < last)
    return {"content": content, "bytes": used, "truncated": truncated, "omitted_reason": "none"}


def _direct_read_fetch(repo_root, requested_paths, seen_locations=None):
    """Governed direct-read-by-path fetch (slice 2/3).

    Given repo-relative target paths (ranked by caller / prompt order), read a
    bounded snippet of each into the bundle. All security rejections are recorded
    (never abort). Returns a telemetry dict plus the fetched hit records so the
    caller can splice content-bearing locations into code_hits.
    """
    from pathlib import Path as _Path

    seen = set(seen_locations or [])
    telemetry = {
        "direct_read_fallback_used": False,
        "direct_read_paths": [],
        "direct_read_rejected": [],
        "direct_read_bytes": 0,
        "direct_read_truncated": [],
        "direct_read_symbol_windows": [],  # {path, symbol} per symbol-windowed fetch (proof it fired)
        "per_file_cap": DIRECT_READ_PER_FILE_BYTES,
        "total_budget": DIRECT_READ_TOTAL_BUDGET_BYTES,
    }
    hits: List[Dict[str, Any]] = []

    # De-duplicate while preserving prompt order; cap total attempted targets. A `path#symbol` target
    # is split into (path, symbol) HERE: the symbol is an opaque key, keyed alongside the path so two
    # symbols of the same file each get their own window (and are not collapsed with a plain-path hit).
    ordered: List[Tuple[str, Optional[str]]] = []
    ordered_seen = set()
    per_path_symbols: Dict[str, int] = {}
    for raw in (requested_paths or []):
        norm = _normalize_direct_read_path(raw)
        rel, symbol = _split_path_symbol(norm)
        if not rel:
            telemetry["direct_read_rejected"].append({"path": str(raw), "reason": "path_missing"})
            continue
        # Path is case-folded (Windows), but the symbol is CASE-SENSITIVE (the locator matches
        # case-sensitively) -- 'Config' (class) and 'config' (var) are distinct symbols and must
        # each get their own window; lowercasing the symbol would silently collapse them.
        key = (rel.lower(), symbol or "")
        if key in ordered_seen:
            continue
        # Bound how many symbol targets one file may contribute, so many (plausible-but-absent)
        # symbols of one file cannot fill all target slots and starve other required targets.
        if symbol:
            if per_path_symbols.get(rel.lower(), 0) >= DIRECT_READ_MAX_SYMBOLS_PER_PATH:
                telemetry["direct_read_rejected"].append(
                    {"path": rel + "#" + symbol, "reason": "too_many_symbols_for_path"})
                continue
            per_path_symbols[rel.lower()] = per_path_symbols.get(rel.lower(), 0) + 1
        ordered_seen.add(key)
        ordered.append((rel, symbol))
    if len(ordered) > DIRECT_READ_MAX_TARGETS:
        for extra_rel, _extra_sym in ordered[DIRECT_READ_MAX_TARGETS:]:
            telemetry["direct_read_rejected"].append({"path": extra_rel, "reason": "too_many_targets"})
        ordered = ordered[:DIRECT_READ_MAX_TARGETS]

    remaining = DIRECT_READ_TOTAL_BUDGET_BYTES
    for rel, symbol in ordered:
        # 1) lexical hard-deny + traversal/absolute check.
        deny = _direct_read_deny_reason(rel)
        if deny:
            telemetry["direct_read_rejected"].append({"path": rel, "reason": deny})
            continue
        # 2) realpath containment (covers symlink escape).
        real, reason = _resolve_within_repo(repo_root, rel)
        if real is None:
            telemetry["direct_read_rejected"].append({"path": rel, "reason": reason})
            continue
        # 3) re-check deny rules against the resolved real basename (defense in
        #    depth: a symlink named foo.txt could target bar.key inside repo).
        try:
            real_rel = str(_Path(os.path.realpath(str(repo_root))))
            resolved_rel = os.path.relpath(str(real), real_rel).replace("\\", "/")
        except Exception:
            resolved_rel = rel
        deny2 = _direct_read_deny_reason(resolved_rel)
        if deny2:
            telemetry["direct_read_rejected"].append({"path": rel, "reason": deny2})
            continue
        if remaining <= 0:
            telemetry["direct_read_rejected"].append({"path": rel, "reason": "budget_exhausted"})
            continue
        # 4) bounded read. A `path#symbol` target reads a bounded LINE WINDOW around the symbol's
        #    definition; if the symbol is not locatable (or the window is unusable) it falls back to
        #    the head-clip so nothing regresses. A plain path always head-clips (unchanged).
        symbol_windowed = False
        if symbol:
            snippet = _read_symbol_window(real, symbol, DIRECT_READ_PER_FILE_BYTES, remaining)
            if snippet["content"]:
                symbol_windowed = True
            else:
                snippet = _read_bounded_direct_read(real, DIRECT_READ_PER_FILE_BYTES, remaining)
        else:
            snippet = _read_bounded_direct_read(real, DIRECT_READ_PER_FILE_BYTES, remaining)
        if not snippet["content"]:
            if snippet["omitted_reason"] not in ("none",):
                telemetry["direct_read_rejected"].append({"path": rel, "reason": snippet["omitted_reason"]})
            continue
        # Content dedup keys on the ACTUAL read MODE, not on whether a symbol was requested. A GENUINE
        # symbol window keys on (path, symbol) [case-sensitive symbol] so two distinct real symbols of
        # one file both land and neither collapses against a plain-path code_hit. A symbol target that
        # FELL BACK to the head-clip produces path-based content identical to the plain path's, so it
        # keys on the bare path -- colliding with the plain-path hit and with seen_locations (code_hits)
        # -- so N absent symbols of one file cannot each redraw a per-file cap and blow the total budget.
        seen_key = (rel.lower() + "#" + symbol) if symbol_windowed else rel.lower()
        if seen_key in seen:
            continue
        seen.add(seen_key)
        remaining -= snippet["bytes"]
        telemetry["direct_read_bytes"] += snippet["bytes"]
        telemetry["direct_read_paths"].append(rel)
        if snippet["truncated"]:
            telemetry["direct_read_truncated"].append({"path": rel, "bytes": snippet["bytes"]})
        if symbol_windowed:
            telemetry["direct_read_symbol_windows"].append({"path": rel, "symbol": symbol})
        hits.append({
            "need": "direct-read target: " + rel + ("#" + symbol if symbol else ""),
            "location": rel,
            "similarity": "100.0%",
            "cube": None,
            "type": "code",
            "priority": 1,
            "direct_read": True,
            "symbol": symbol if symbol_windowed else None,
            "content": snippet["content"],
            "content_bytes": snippet["bytes"],
            "content_truncated": snippet["truncated"],
        })
    telemetry["direct_read_fallback_used"] = len(telemetry["direct_read_paths"]) > 0
    return {"telemetry": telemetry, "hits": hits}


def _artifact_snapshot(repo_root, module_dir) -> Dict[str, Any]:
    """Generate artifact snapshot for a module directory."""
    # Tier definitions mirror WSP_CORE "Tiered Holo Retrieval Targets" (minimal v1)
    tiers: Dict[str, Dict[str, Any]] = {
        "0": {
            "name": "Contract/Guardrails",
            "required": ["README.md", "INTERFACE.md"],
            "optional": ["SPEC.md", "PRD.md", "PROMPTS.md", "prompts/", "RUNBOOK.md"],
        },
        "1": {
            "name": "Evolution/Verification",
            "required": [],
            "optional": ["ROADMAP.md", "ModLog.md", "tests/TestModLog.md", "tests/README.md"],
        },
        "2": {
            "name": "Retrieval/Decisions/Failures",
            "required": [],
            "optional": ["memory/README.md", "HOLOINDEX.md", "ADR.md", "adr/", "INCIDENTS.md", "SEV.md"],
        },
    }

    artifacts: List[Dict[str, Any]] = []
    missing_required: List[str] = []
    missing_optional: List[str] = []

    for tier_key, tier_def in tiers.items():
        tier_num = int(tier_key)
        for name in tier_def["required"]:
            is_dir = name.endswith("/")
            p = module_dir / name.rstrip("/")
            exists = _artifact_exists(
                repo_root, module_dir, name, directory=is_dir
            )
            rel = str(p.relative_to(module_dir)).replace("\\", "/")
            artifacts.append({
                "tier": tier_num,
                "required": True,
                "name": name,
                "relative_path": rel + ("/" if is_dir else ""),
                "path": str(p),
                "exists": exists,
            })
            if not exists:
                missing_required.append(f"Tier-{tier_num}: {rel}{'/' if is_dir else ''}")

        for name in tier_def["optional"]:
            is_dir = name.endswith("/")
            p = module_dir / name.rstrip("/")
            exists = _artifact_exists(
                repo_root, module_dir, name, directory=is_dir
            )
            rel = str(p.relative_to(module_dir)).replace("\\", "/")
            artifacts.append({
                "tier": tier_num,
                "required": False,
                "name": name,
                "relative_path": rel + ("/" if is_dir else ""),
                "path": str(p),
                "exists": exists,
            })
            if not exists:
                missing_optional.append(f"Tier-{tier_num}: {rel}{'/' if is_dir else ''}")

    return {
        "tiers": tiers,
        "artifacts": artifacts,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "tier0_complete": len(missing_required) == 0,
    }


def _tokenize(query: str) -> List[str]:
    import re as _re
    return [t for t in _re.findall(r"[a-z0-9_]+", (query or "").lower()) if t]


def _score_text(tokens: List[str], *fields: str) -> float:
    score = 0.0
    lowered = [(f or "").lower() for f in fields]
    normalized = [f.replace("_", "").replace("-", "") for f in lowered]
    for tok in tokens:
        if not tok:
            continue
        for idx, field in enumerate(lowered):
            if tok in field or tok in normalized[idx]:
                # Weight earlier fields slightly higher (title/need > summary/path)
                score += (2.0 if idx == 0 else 1.0 if idx == 1 else 0.5)
    return score


def _load_need_to(repo_root) -> Dict[str, str]:
    import ast as _ast
    text = _read_confined_text(
        repo_root,
        "NAVIGATION.py",
        max_bytes=LEXICAL_NAVIGATION_MAX_BYTES,
        reject_oversize=True,
    )
    if text is None:
        return {}
    try:
        tree = _ast.parse(text)
    except Exception:
        return {}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name) and target.id == "NEED_TO":
                    try:
                        return _ast.literal_eval(node.value)
                    except Exception:
                        return {}
    return {}


def _load_repo_wsp_summary(repo_root) -> Dict[str, Dict[str, str]]:
    """Build bounded lexical WSP metadata from the invoking repository only."""
    summary: Dict[str, Dict[str, str]] = {}
    repo_root = Path(repo_root)
    wsp_root = _confined_repo_path(
        repo_root, "WSP_framework/src", directory=True
    )
    if wsp_root is None:
        return summary
    repo_root = wsp_root.parents[1]
    candidates = _bounded_directory_names(
        repo_root,
        "WSP_framework/src",
        entry_cap=LEXICAL_WSP_MAX_ENTRIES,
        prefix="WSP_",
        suffix=".md",
        directories=False,
    )[:LEXICAL_WSP_MAX_FILES]
    for name in candidates:
        relative = f"WSP_framework/src/{name}"
        text = _read_confined_text(
            repo_root,
            relative,
            max_bytes=LEXICAL_WSP_READ_BYTES,
            reject_oversize=False,
        )
        if text is None:
            continue
        match = re.match(r"^WSP_(\d+)", name, flags=re.IGNORECASE)
        if not match:
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0].lstrip("# ").strip() if lines else Path(name).stem
        detail = next((line for line in lines[1:] if not line.startswith("#")), "")
        summary[f"WSP {int(match.group(1))}"] = {
            "title": title,
            "summary": detail[:500],
            "path": relative,
        }
    return summary


def _lexical_task_retrieval(repo_root, task: str, limit: int, _ssd_path: str, module_dir=None) -> Dict[str, Any]:
    """Lexical search fallback when embeddings are unavailable."""

    tokens = _tokenize(task)
    need_to = _load_need_to(repo_root)
    wsp_summary = _load_repo_wsp_summary(repo_root)

    code_hits: List[Dict[str, Any]] = []
    for need, location in list(need_to.items()):
        score = _score_text(tokens, need, location)
        need_lower = need.lower()
        query_lower = (task or "").lower()
        if need_lower == query_lower:
            score += 12.0
        elif need_lower in query_lower or query_lower in need_lower:
            score += 8.0
        if score <= 0:
            continue
        similarity = min(1.0, score / max(1.0, len(tokens) * 3.0))
        code_hits.append({
            "need": need,
            "location": location,
            "similarity": f"{similarity*100:.1f}%",
            "cube": None,
            "type": "code",
            "priority": 1,
        })

    # Path-based fallback when module hint is provided (fast lexical, no embeddings)
    if module_dir is not None:
        allowed_ext = {".py", ".js", ".md", ".txt", ".json", ".yaml", ".yml"}
        for path in _bounded_module_files(repo_root, module_dir):
            if path.suffix.lower() not in allowed_ext:
                continue
            rel_path = str(path.relative_to(repo_root)).replace("\\", "/")
            name_lower = path.name.lower()
            stem_lower = path.stem.lower()
            score = _score_text(tokens, rel_path, path.name)
            for tok in tokens:
                if tok == stem_lower or tok == name_lower:
                    score += 6.0
            if score <= 0:
                continue
            similarity = min(1.0, score / max(1.0, len(tokens) * 3.0))
            code_hits.append({
                "need": f"path match: {path.name}",
                "location": rel_path,
                "similarity": f"{similarity*100:.1f}%",
                "cube": None,
                "type": "code",
                "priority": 1,
            })

    # Deduplicate by location while preserving score order
    seen_locations = set()
    deduped_hits = []
    for hit in code_hits:
        loc = hit.get("location")
        if not loc or loc in seen_locations:
            continue
        seen_locations.add(loc)
        deduped_hits.append(hit)
    code_hits = deduped_hits
    code_hits.sort(key=lambda x: float((x.get("similarity") or "0%").rstrip("%")), reverse=True)
    code_hits = code_hits[:limit]

    wsp_hits: List[Dict[str, Any]] = []
    for wsp_id, meta in wsp_summary.items():
        title = meta.get("title", "")
        path = meta.get("path", "")
        summary = meta.get("summary", "")
        score = _score_text(tokens, title, summary, path)
        if score <= 0:
            continue
        similarity = min(1.0, score / max(1.0, len(tokens) * 3.0))
        wsp_hits.append({
            "wsp": wsp_id,
            "title": title,
            "summary": summary,
            "path": path,
            "similarity": f"{similarity*100:.1f}%",
            "cube": None,
            "type": "wsp_protocol" if str(wsp_id).startswith("WSP ") else "documentation",
            "priority": 5,
        })
    wsp_hits.sort(key=lambda x: float((x.get("similarity") or "0%").rstrip("%")), reverse=True)
    wsp_hits = wsp_hits[:limit]

    return {
        "code_hits": code_hits,
        "wsp_hits": wsp_hits,
        "test_hits": [],
        "skill_hits": [],
        "code": code_hits,
        "wsps": wsp_hits,
        "tests": [],
        "skills": [],
        "metadata": {
            "query": task,
            "mode": "lexical",
            "retrieval_mode": "lexical",
            "freshness": "UNKNOWN",
            "index_gap_detected": True,
            "no_holoindex_store_access": True,
            "wsp_source": "current_repository",
            "skip_model": True,
            "code_count": len(code_hits),
            "wsp_count": len(wsp_hits),
            "test_count": 0,
            "skill_count": 0,
            "timestamp": _utc_now_iso(),
        }
    }


def _merge_direct_read_telemetry(primary, secondary):
    """Merge independently governed read receipts without losing rejections."""
    if not primary:
        return secondary
    if not secondary:
        return primary
    merged = dict(primary)
    for key in ("direct_read_paths", "direct_read_rejected", "direct_read_truncated"):
        merged[key] = list(primary.get(key) or []) + list(secondary.get(key) or [])
    merged["direct_read_bytes"] = int(primary.get("direct_read_bytes") or 0) + int(secondary.get("direct_read_bytes") or 0)
    merged["direct_read_fallback_used"] = bool(
        primary.get("direct_read_fallback_used") or secondary.get("direct_read_fallback_used")
    )
    return merged


def _apply_repo_audit_grounding(repo_root, task, search_payload):
    """Attach governed audit evidence after normal HoloIndex retrieval."""
    from holo_index.cli.repo_audit_discovery import build_repo_audit_grounding

    audit = build_repo_audit_grounding(repo_root, task, search_payload)
    if audit["hits"]:
        search_payload["code_hits"] = audit["hits"] + list(search_payload.get("code_hits") or [])
        search_payload["code"] = search_payload["code_hits"]
        meta = search_payload.get("metadata")
        if isinstance(meta, dict):
            meta["code_count"] = len(search_payload["code_hits"])
            meta["repo_audit_grounding_applied"] = True
    return audit["receipt"], audit["telemetry"]


def _write_bundle_payload(payload: Dict[str, Any], *, sort_keys=False) -> None:
    sys.stdout.write(
        _json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=sort_keys,
        )
        + "\n"
    )


def _activate_bundle_silence() -> None:
    os.environ.setdefault("HOLO_SILENT", "1")
    try:
        logging.disable(logging.CRITICAL)
    except Exception:
        pass


def _bundle_module_context(repo_root: Path, module_hint: str):
    module_dir = (
        _resolve_module_dir(repo_root, module_hint) if module_hint else None
    )
    module_path = None
    if module_dir is not None:
        try:
            module_path = module_dir.relative_to(repo_root).as_posix()
        except ValueError:
            module_dir = None
    return module_dir, module_path


def _bundle_search(
    args,
    repo_root: Path,
    task: str,
    module_hint: str,
    module_dir,
    module_path,
    *,
    skip_model: bool,
):
    if skip_model:
        return _lexical_task_retrieval(
            repo_root,
            task,
            int(args.limit),
            str(args.ssd),
            module_dir=module_dir,
        ), None
    try:
        from holo_index.core import HoloIndex as _HoloIndex

        holo = _HoloIndex(ssd_path=args.ssd, quiet=True)
        return holo.search(
            task,
            limit=args.limit,
            doc_type_filter=getattr(args, "doc_type", "all"),
        ), None
    except Exception as exc:
        return None, {
            "schema_version": "wsp_memory_bundle_v1",
            "generated_at": _utc_now_iso(),
            "ok": False,
            "task": task,
            "module_hint": module_hint,
            "module_path": module_path,
            "error": f"holo_search_failed: {exc}",
        }


def _bundle_must_include(raw) -> List[str]:
    if not raw:
        return []
    items = raw if isinstance(raw, (list, tuple)) else (raw,)
    return [
        path
        for item in items
        for path in str(item).split(",")
        if path.strip()
    ]


def _apply_bundle_direct_read(
    repo_root: Path,
    search_payload: Dict[str, Any],
    direct_read,
    must_include_raw,
):
    must_include = _bundle_must_include(must_include_raw)
    if not must_include:
        return direct_read
    try:
        existing_locations = {
            str(hit.get("location") or "").replace("\\", "/").lower()
            for hit in (search_payload.get("code_hits") or [])
            if str(hit.get("location") or "")
        }
    except Exception:
        existing_locations = set()
    fetched = _direct_read_fetch(
        repo_root,
        must_include,
        seen_locations=existing_locations,
    )
    direct_read = _merge_direct_read_telemetry(
        direct_read,
        fetched["telemetry"],
    )
    if fetched["hits"]:
        try:
            hits = fetched["hits"] + list(search_payload.get("code_hits") or [])
            search_payload["code_hits"] = hits
            search_payload["code"] = hits
            metadata = search_payload.get("metadata")
            if isinstance(metadata, dict):
                metadata["code_count"] = len(hits)
                metadata["direct_read_fallback_used"] = direct_read[
                    "direct_read_fallback_used"
                ]
        except Exception:
            pass
    return direct_read


def _bundle_persistent_denial(args, repo_root: Path, skip_model: bool):
    if skip_model:
        return None
    denial = _persistent_query_denial(repo_root, Path(args.ssd))
    if denial is None:
        return None
    return {
        "schema_version": "wsp_memory_bundle_v1",
        "generated_at": _utc_now_iso(),
        **denial,
    }


def _bundle_success_payload(
    task: str,
    module_hint: str,
    module_path,
    structured_memory,
    search_payload,
    direct_read,
    repo_audit_grounding,
) -> Dict[str, Any]:
    return {
        "schema_version": "wsp_memory_bundle_v1",
        "generated_at": _utc_now_iso(),
        "ok": True,
        "task": task,
        "module_hint": module_hint,
        "module_path": module_path,
        "structured_memory": structured_memory,
        "task_retrieval": search_payload,
        "direct_read": direct_read,
        "repo_audit_grounding": repo_audit_grounding,
    }


def handle_bundle_json(args):
    """Handle --bundle-json command. Returns True if handled, False otherwise."""
    if not getattr(args, "bundle_json", False):
        return False

    _activate_bundle_silence()
    repo_root = Path(__file__).resolve().parents[3]
    task = (getattr(args, "bundle_task", None) or getattr(args, "search", None) or "").strip()
    module_hint = (getattr(args, "bundle_module_hint", None) or "").strip()

    if not task:
        _write_bundle_payload({
            "schema_version": "wsp_memory_bundle_v1",
            "generated_at": _utc_now_iso(),
            "ok": False,
            "error": "bundle-json requires --search or --bundle-task",
        })
        return True

    # Persistent admission must precede every caller-controlled filesystem hint.
    skip_model = _env_truthy("HOLO_SKIP_MODEL", "false")
    denial = _bundle_persistent_denial(args, repo_root, skip_model)
    if denial is not None:
        _write_bundle_payload(denial, sort_keys=True)
        return True

    module_dir, module_path = _bundle_module_context(repo_root, module_hint)
    search_payload, search_error = _bundle_search(
        args, repo_root, task, module_hint, module_dir, module_path,
        skip_model=skip_model,
    )
    if search_error is not None:
        _write_bundle_payload(search_error)
        return True
    structured_memory = (
        _artifact_snapshot(repo_root, module_dir) if module_dir else None
    )
    repo_audit_grounding, direct_read = _apply_repo_audit_grounding(repo_root, task, search_payload)
    direct_read = _apply_bundle_direct_read(
        repo_root,
        search_payload,
        direct_read,
        getattr(args, "bundle_must_include", None),
    )
    _write_bundle_payload(_bundle_success_payload(
        task, module_hint, module_path, structured_memory,
        search_payload, direct_read, repo_audit_grounding,
    ))
    return True
