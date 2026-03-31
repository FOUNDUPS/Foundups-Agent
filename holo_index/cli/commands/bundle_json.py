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
        allowed_ext = {".py", ".md", ".txt", ".json", ".yaml", ".yml"}
        for path in module_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in allowed_ext:
                continue
            rel_path = str(path.relative_to(repo_root)).replace("\\", "/")
            score = _score_text(tokens, rel_path, path.name)
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

    bundle = {
        "schema_version": "wsp_memory_bundle_v1",
        "generated_at": _dt.utcnow().isoformat() + "Z",
        "ok": True,
        "task": task,
        "module_hint": module_hint,
        "module_path": module_path,
        "structured_memory": structured_memory,
        "task_retrieval": search_payload,
    }

    sys.stdout.write(_json.dumps(bundle, ensure_ascii=True) + "\n")
    return True
