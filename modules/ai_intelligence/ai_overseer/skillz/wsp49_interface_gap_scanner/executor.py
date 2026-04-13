#!/usr/bin/env python3
"""
WSP 49 INTERFACE gap scanner — read-only discovery + ranked queue + prompt packs.

Does NOT write INTERFACE.md. Use output with Codex/0102 for WSP 11 drafts, then ModLog (WSP 22).

Usage:
  python executor.py --scan
  python executor.py --scan --json path/to/queue.json
  python executor.py --scan --emit-prompts path/to/dir/
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Enterprise domains (WSP 3). Higher in list = earlier in ranked queue for remediation.
SCAN_DOMAIN_ORDER: Tuple[str, ...] = (
    "infrastructure",
    "platform_integration",
    "communication",
    "ai_intelligence",
    "development",
    "foundups",
    "monitoring",
    "gamification",
    "blockchain",
)

_SKIP_DIR_NAMES = frozenset({"__pycache__", ".git", ".pytest_cache", "node_modules"})


def _domain_rank(domain: str) -> int:
    try:
        return SCAN_DOMAIN_ORDER.index(domain)
    except ValueError:
        return len(SCAN_DOMAIN_ORDER)


def _module_candidates(modules_dir: Path, domain: str) -> List[Path]:
    d = modules_dir / domain
    if not d.is_dir():
        return []
    out: List[Path] = []
    for child in d.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith("_") or name in _SKIP_DIR_NAMES:
            continue
        out.append(child)
    return sorted(out, key=lambda p: p.name.lower())


def _existing_context_files(module_path: Path) -> List[str]:
    rel: List[str] = []
    for rel_name in (
        "README.md",
        "README.rst",
        "INTERFACE.md",
        "ModLog.md",
        "ROADMAP.md",
        "requirements.txt",
        "src/__init__.py",
        "src/__init__.pyi",
        "__init__.py",
    ):
        if (module_path / rel_name).is_file():
            rel.append(rel_name)
    return rel


def _extract_public_symbols(init_path: Path, max_lines: int = 400) -> Dict[str, Any]:
    """Lightweight parse: __all__ if present, else top-level def/class names."""
    if not init_path.is_file():
        return {"__all__": None, "top_level": []}
    try:
        text = init_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"__all__": None, "top_level": []}
    lines = text.splitlines()[:max_lines]
    snippet = "\n".join(lines)
    try:
        tree = ast.parse(snippet + "\n", filename=str(init_path))
    except SyntaxError:
        names: List[str] = []
        for m in re.finditer(r"^def\s+(\w+)|^async\s+def\s+(\w+)|^class\s+(\w+)", snippet, re.MULTILINE):
            names.append(next(g for g in m.groups() if g))
        return {"__all__": None, "top_level": names[:40]}

    top: List[str] = []
    all_names: Optional[List[str]] = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    try:
                        all_val = ast.literal_eval(node.value)
                        if isinstance(all_val, (list, tuple)):
                            all_names = [str(x) for x in all_val]
                    except (ValueError, SyntaxError):
                        all_names = None
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                top.append(node.name)
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                top.append(node.name)
    return {"__all__": all_names, "top_level": top[:40]}


def _build_prompt_pack(module_rel: str, context_files: Sequence[str], symbols: Dict[str, Any]) -> str:
    ctx = ", ".join(context_files) if context_files else "(none found)"
    sy = symbols.get("__all__")
    tl = symbols.get("top_level") or []
    sy_block = ""
    if sy:
        sy_block = f"__all__ (if trustworthy): {sy!r}\n"
    elif tl:
        sy_block = f"Inferred public-ish names from ast (verify): {', '.join(tl[:30])}\n"
    return f"""WSP 11 INTERFACE draft — module: `{module_rel}`

Read before writing (repo paths relative to root):
- {ctx}

Mission: create or complete `INTERFACE.md` at `{module_rel}/INTERFACE.md` per WSP 11:
- Public API (functions, classes) with parameters, returns, errors
- Integration points / env vars if any
- Examples minimal but accurate — no fiction

Constraints:
- Do not invent APIs; ground every symbol in code or existing README.
- After file write, 0102 updates `ModLog.md` (WSP 22) for this module.

Symbol hints (verify in source):
{sy_block or '(no src/__init__.py snippet parsed)'}

---
Generated by skillz/wsp49_interface_gap_scanner (scaffold only; not autonomous repair).
"""


def discover_interface_gaps(repo_root: Path) -> List[Dict[str, Any]]:
    """Return one dict per module directory missing INTERFACE.md."""
    modules_dir = repo_root / "modules"
    if not modules_dir.is_dir():
        logger.warning("No modules/ at %s", repo_root)
        return []
    rows: List[Dict[str, Any]] = []
    for domain in SCAN_DOMAIN_ORDER:
        for mod_path in _module_candidates(modules_dir, domain):
            iface = mod_path / "INTERFACE.md"
            if iface.is_file():
                continue
            rel = mod_path.relative_to(repo_root).as_posix()
            ctx = _existing_context_files(mod_path)
            init_py = mod_path / "src" / "__init__.py"
            if not init_py.is_file():
                init_py = mod_path / "__init__.py"
            symbols = _extract_public_symbols(init_py)
            rows.append(
                {
                    "domain": domain,
                    "module_name": mod_path.name,
                    "path": rel,
                    "context_files": ctx,
                    "symbol_hints": symbols,
                }
            )
    return rows


def rank_gaps(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stable sort: domain priority (WSP 3), then richer context first (CO), then name."""
    indexed = list(enumerate(rows))
    indexed.sort(
        key=lambda it: (
            _domain_rank(it[1]["domain"]),
            -len(it[1].get("context_files") or []),
            it[1]["module_name"].lower(),
            it[0],
        )
    )
    ranked: List[Dict[str, Any]] = []
    for r, (_, row) in enumerate(indexed, start=1):
        entry = dict(row)
        entry["rank"] = r
        entry["prompt_pack"] = _build_prompt_pack(
            entry["path"], entry.get("context_files") or [], entry.get("symbol_hints") or {}
        )
        ranked.append(entry)
    return ranked


def _write_prompt_files(out_dir: Path, ranked: Sequence[Dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for row in ranked:
        safe = re.sub(r"[^\w\-]+", "_", row["path"])[:120]
        f = out_dir / f"{row['rank']:03d}_{safe}.md"
        f.write_text(row["prompt_pack"], encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="WSP 49 INTERFACE.md gap scanner (read-only)")
    parser.add_argument("--scan", action="store_true", help="Run discovery (default if no other action)")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Repo root")
    parser.add_argument("--json", type=Path, metavar="FILE", help="Write full ranked queue JSON")
    parser.add_argument(
        "--emit-prompts",
        type=Path,
        metavar="DIR",
        help="Write one .md prompt file per gap",
    )
    parser.add_argument("--quiet", action="store_true", help="Less stdout")
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO)

    raw = discover_interface_gaps(args.repo_root.resolve())
    ranked = rank_gaps(raw)

    if not args.quiet:
        print(f"[WSP49] Missing INTERFACE.md: {len(ranked)} module(s)")
        for row in ranked:
            print(f"  {row['rank']:3d}. src/…/{row['path']}  (+{len(row['context_files'])} context files)")

    if args.json:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repo_root": str(args.repo_root.resolve()),
            "count": len(ranked),
            "gaps": ranked,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"[WSP49] Wrote JSON: {args.json}")

    if args.emit_prompts:
        _write_prompt_files(args.emit_prompts, ranked)
        if not args.quiet:
            print(f"[WSP49] Wrote {len(ranked)} prompt file(s) under {args.emit_prompts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
