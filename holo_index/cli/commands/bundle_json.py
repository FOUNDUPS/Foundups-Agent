# -*- coding: utf-8 -*-
"""
Bundle JSON command handler - WSP_CORE Memory System JSON output mode.

Extracted from holo_index/cli.py (lines 634-960).
Self-contained lexical search + artifact snapshot + JSON bundle output.
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional


def _env_truthy(key: str, default: str = "false") -> bool:
    """Check if environment variable is truthy."""
    return os.getenv(key, default).lower() in {"1", "true", "yes", "on"}


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

# HARD-DENY basenames (exact match, case-insensitive).
DIRECT_READ_DENY_BASENAMES = frozenset({
    ".env",
    "id_rsa",
    "id_ed25519",
})

# HARD-DENY path segments: any path traversing one of these dirs is rejected.
DIRECT_READ_DENY_SEGMENTS = frozenset({
    ".git",
    ".ssh",
    ".gnupg",
    ".aws",
    ".azure",
    ".gcloud",
    "node_modules",
    "__pycache__",
    ".venv",
})

# HARD-DENY glob-ish suffix / substring rules applied to the lowercased basename
# (and, for the *secret*/*credential*/*token* rules, any path segment).
DIRECT_READ_DENY_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".keystore",
    ".pfx",
    ".vsix",
)
# basename prefixes that hard-deny (covers .env.local, id_rsa.pub, etc.).
DIRECT_READ_DENY_PREFIXES = (
    ".env",
    "id_rsa",
    "id_ed25519",
)
# substring markers that hard-deny anywhere in a path segment.
DIRECT_READ_DENY_SUBSTRINGS = (
    "secret",
    "credential",
    "token",
)


def _direct_read_deny_reason(rel_norm: str) -> Optional[str]:
    """Return a deny reason string for a normalized repo-relative path, else None.

    Pure lexical gate (no filesystem access). Absolute paths, drive-letters and
    `..` traversal are rejected here; realpath containment is checked separately.
    """
    if not rel_norm:
        return "path_missing"
    # Absolute POSIX path or Windows drive-letter path -> reject.
    if rel_norm.startswith("/") or (len(rel_norm) >= 2 and rel_norm[1] == ":"):
        return "absolute_path"
    parts = rel_norm.lower().split("/")
    if any(p == ".." for p in parts):
        return "traversal"
    # Deny by path segment (credential dirs, .git, caches).
    for seg in parts:
        if seg in DIRECT_READ_DENY_SEGMENTS:
            return "denied_segment"
        for marker in DIRECT_READ_DENY_SUBSTRINGS:
            if marker in seg:
                return "denied_secret_like"
    base = parts[-1]
    if base in DIRECT_READ_DENY_BASENAMES:
        return "denied_basename"
    for pref in DIRECT_READ_DENY_PREFIXES:
        if base == pref or base.startswith(pref + "."):
            return "denied_basename"
    for suf in DIRECT_READ_DENY_SUFFIXES:
        if base.endswith(suf):
            return "denied_extension"
    return None


def _normalize_direct_read_path(raw: str) -> str:
    """Normalize a requested target into a candidate path string.

    IMPORTANT: this MUST preserve a leading '/' or a drive-letter prefix so the
    deny gate can reject absolute paths. It only trims quotes/whitespace and
    collapses a leading './'. It never strips a leading slash (doing so would
    silently turn '/etc/passwd' into a relative 'etc/passwd' and defeat the
    absolute-path rejection).
    """
    norm = str(raw or "").strip().replace("\\", "/")
    # Strip surrounding quotes/backticks a prompt might carry through.
    norm = norm.strip("`'\"")
    if norm in ("", "."):
        return ""
    # Collapse a leading ./ but keep the rest verbatim (do NOT resolve here).
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


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
        "per_file_cap": DIRECT_READ_PER_FILE_BYTES,
        "total_budget": DIRECT_READ_TOTAL_BUDGET_BYTES,
    }
    hits: List[Dict[str, Any]] = []

    # De-duplicate while preserving prompt order; cap total attempted targets.
    ordered: List[str] = []
    ordered_seen = set()
    for raw in (requested_paths or []):
        rel = _normalize_direct_read_path(raw)
        if not rel:
            telemetry["direct_read_rejected"].append({"path": str(raw), "reason": "path_missing"})
            continue
        key = rel.lower()
        if key in ordered_seen:
            continue
        ordered_seen.add(key)
        ordered.append(rel)
    if len(ordered) > DIRECT_READ_MAX_TARGETS:
        for extra in ordered[DIRECT_READ_MAX_TARGETS:]:
            telemetry["direct_read_rejected"].append({"path": extra, "reason": "too_many_targets"})
        ordered = ordered[:DIRECT_READ_MAX_TARGETS]

    remaining = DIRECT_READ_TOTAL_BUDGET_BYTES
    for rel in ordered:
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
        # 4) bounded read.
        snippet = _read_bounded_direct_read(real, DIRECT_READ_PER_FILE_BYTES, remaining)
        if not snippet["content"]:
            if snippet["omitted_reason"] not in ("none",):
                telemetry["direct_read_rejected"].append({"path": rel, "reason": snippet["omitted_reason"]})
            continue
        remaining -= snippet["bytes"]
        telemetry["direct_read_bytes"] += snippet["bytes"]
        telemetry["direct_read_paths"].append(rel)
        if snippet["truncated"]:
            telemetry["direct_read_truncated"].append({"path": rel, "bytes": snippet["bytes"]})
        if rel.lower() not in seen:
            seen.add(rel.lower())
            hits.append({
                "need": "direct-read target: " + rel,
                "location": rel,
                "similarity": "100.0%",
                "cube": None,
                "type": "code",
                "priority": 1,
                "direct_read": True,
                "content": snippet["content"],
                "content_bytes": snippet["bytes"],
                "content_truncated": snippet["truncated"],
            })
    telemetry["direct_read_fallback_used"] = len(telemetry["direct_read_paths"]) > 0
    return {"telemetry": telemetry, "hits": hits}


def _resolve_module_dir(repo_root, hint: str):
    """Resolve a module hint to an actual directory path."""
    from pathlib import Path as _Path

    raw = (hint or "").strip()
    if not raw:
        return None

    norm = raw.replace("\\", "/").strip("/")

    # Allow direct relative paths (modules/... or holo_index/...)
    direct = repo_root / norm
    if direct.exists() and direct.is_dir():
        return direct

    # Allow shorthand "communication/livechat" by prefixing "modules/"
    if "/" in norm and not norm.startswith("modules/"):
        prefixed = repo_root / "modules" / norm
        if prefixed.exists() and prefixed.is_dir():
            return prefixed

    # Allow module name-only resolution under modules/<domain>/<module>
    modules_root = repo_root / "modules"
    if modules_root.exists():
        try:
            for domain_dir in modules_root.iterdir():
                if not domain_dir.is_dir():
                    continue
                candidate = domain_dir / norm
                if candidate.exists() and candidate.is_dir():
                    return candidate
        except Exception:
            return None

    return None


def _artifact_snapshot(module_dir) -> Dict[str, Any]:
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

    def _exists(p, is_dir: bool) -> bool:
        try:
            return p.is_dir() if is_dir else p.exists()
        except Exception:
            return False

    for tier_key, tier_def in tiers.items():
        tier_num = int(tier_key)
        for name in tier_def["required"]:
            is_dir = name.endswith("/")
            p = module_dir / name.rstrip("/")
            exists = _exists(p, is_dir=is_dir)
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
            exists = _exists(p, is_dir=is_dir)
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
    nav_path = repo_root / "NAVIGATION.py"
    if not nav_path.exists():
        return {}
    try:
        tree = _ast.parse(nav_path.read_text(encoding="utf-8-sig", errors="ignore"))
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


def _load_wsp_summary(ssd_path: str) -> Dict[str, Dict[str, str]]:
    import json as _json
    from pathlib import Path as _Path
    try:
        summary_path = _Path(ssd_path) / "indexes" / "wsp_summary.json"
        if not summary_path.exists():
            return {}
        return _json.loads(summary_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def _lexical_task_retrieval(repo_root, task: str, limit: int, ssd_path: str, module_dir=None) -> Dict[str, Any]:
    """Lexical search fallback when embeddings are unavailable."""
    from datetime import datetime as _dt

    tokens = _tokenize(task)
    need_to = _load_need_to(repo_root)
    wsp_summary = _load_wsp_summary(ssd_path)

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
    if module_dir is not None and module_dir.exists():
        allowed_ext = {".py", ".js", ".md", ".txt", ".json", ".yaml", ".yml"}
        for path in module_dir.rglob("*"):
            if not path.is_file():
                continue
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
            "skip_model": True,
            "code_count": len(code_hits),
            "wsp_count": len(wsp_hits),
            "test_count": 0,
            "skill_count": 0,
            "timestamp": _dt.utcnow().isoformat() + "Z",
        }
    }


def handle_bundle_json(args):
    """Handle --bundle-json command. Returns True if handled, False otherwise."""
    if not getattr(args, "bundle_json", False):
        return False

    import json as _json
    from datetime import datetime as _dt
    from pathlib import Path as _Path

    # Hard silence: bundle-json requires stdout = JSON only
    os.environ.setdefault("HOLO_SILENT", "1")
    try:
        logging.disable(logging.CRITICAL)
    except Exception:
        pass

    repo_root = _Path(__file__).resolve().parents[3]
    task = (getattr(args, "bundle_task", None) or getattr(args, "search", None) or "").strip()
    module_hint = (getattr(args, "bundle_module_hint", None) or "").strip()

    if not task:
        sys.stdout.write(_json.dumps({
            "schema_version": "wsp_memory_bundle_v1",
            "generated_at": _dt.utcnow().isoformat() + "Z",
            "ok": False,
            "error": "bundle-json requires --search or --bundle-task",
        }, ensure_ascii=True) + "\n")
        return True

    module_dir = _resolve_module_dir(repo_root, module_hint) if module_hint else None
    module_path = None
    if module_dir is not None:
        try:
            module_path = str(module_dir.relative_to(repo_root)).replace("\\", "/")
        except Exception:
            module_path = str(module_dir).replace("\\", "/")

    # Task retrieval: fast lexical path when HOLO_SKIP_MODEL=1, otherwise full HoloIndex search.
    skip_model = _env_truthy("HOLO_SKIP_MODEL", "false")
    if skip_model:
        search_payload = _lexical_task_retrieval(repo_root, task, int(args.limit), str(args.ssd), module_dir=module_dir)
    else:
        try:
            from holo_index.core import HoloIndex as _HoloIndex  # local import to avoid heavy imports in fastpath
            holo = _HoloIndex(ssd_path=args.ssd, quiet=True)
            search_payload = holo.search(task, limit=args.limit, doc_type_filter=getattr(args, "doc_type", "all"))
        except Exception as exc:
            sys.stdout.write(_json.dumps({
                "schema_version": "wsp_memory_bundle_v1",
                "generated_at": _dt.utcnow().isoformat() + "Z",
                "ok": False,
                "task": task,
                "module_hint": module_hint,
                "module_path": module_path,
                "error": f"holo_search_failed: {exc}",
            }, ensure_ascii=True) + "\n")
            return True

    structured_memory = None
    if module_dir is not None:
        structured_memory = _artifact_snapshot(module_dir)

    # REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3): governed direct-read.
    # When the extension names must-include target paths (from an explicit
    # "Required direct-read targets" prompt list) that the semantic bundle did
    # not surface, fetch those exact files here under the hard security allowlist
    # and splice them into code_hits so slice-1's recall check sees real content.
    must_include_raw = getattr(args, "bundle_must_include", None)
    must_include: List[str] = []
    if must_include_raw:
        if isinstance(must_include_raw, (list, tuple)):
            for item in must_include_raw:
                must_include.extend([p for p in str(item).split(",") if p.strip()])
        else:
            must_include.extend([p for p in str(must_include_raw).split(",") if p.strip()])

    direct_read = None
    if must_include:
        existing_locations = set()
        try:
            for hit in (search_payload.get("code_hits") or []):
                loc = str(hit.get("location") or "").replace("\\", "/").lower()
                if loc:
                    existing_locations.add(loc)
        except Exception:
            existing_locations = set()
        fetched = _direct_read_fetch(repo_root, must_include, seen_locations=existing_locations)
        direct_read = fetched["telemetry"]
        if fetched["hits"]:
            try:
                # Prepend direct-read hits (highest priority) so recall + display
                # both see the fetched content-bearing locations first.
                search_payload["code_hits"] = fetched["hits"] + list(search_payload.get("code_hits") or [])
                search_payload["code"] = search_payload["code_hits"]
                meta = search_payload.get("metadata")
                if isinstance(meta, dict):
                    meta["code_count"] = len(search_payload["code_hits"])
                    meta["direct_read_fallback_used"] = direct_read["direct_read_fallback_used"]
            except Exception:
                pass

    bundle = {
        "schema_version": "wsp_memory_bundle_v1",
        "generated_at": _dt.utcnow().isoformat() + "Z",
        "ok": True,
        "task": task,
        "module_hint": module_hint,
        "module_path": module_path,
        "structured_memory": structured_memory,
        "task_retrieval": search_payload,
        "direct_read": direct_read,
    }

    sys.stdout.write(_json.dumps(bundle, ensure_ascii=True) + "\n")
    return True
