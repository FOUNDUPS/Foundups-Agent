"""
Consciousness → Detector Signature Migration Script
=====================================================
Two-pass approach: regex heuristics for obvious cases, LLM for ambiguous ones.

Pass 1 (regex, instant): Pattern-match KEEP exceptions and obvious REPLACE targets.
Pass 2 (LLM, slow): Only ambiguous instances go to qwen-coder-7b via LM Studio.

This is NOT a blind find-replace. The heuristic pass catches ~80% of cases
(file paths, citations, negations, standard replacements). The remaining ~20%
get full LLM context analysis.

WSP Compliance: WSP 97 (CoT/CoR), WSP 84 (reuse existing infra)
Usage:
    python executor.py --scan                          # Dry run: show all decisions
    python executor.py --apply --scope full            # Apply to whole repo (.md)
    python executor.py --apply --scope full --no-llm   # Heuristic only (no LM Studio)
    python executor.py --file FILE --scan              # Single file dry run
    python executor.py --apply --backend openrouter    # Use OpenRouter instead of LM Studio
"""

import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

PAPERS_DIR = PROJECT_ROOT / "WSP_knowledge" / "docs" / "Papers"
BACKUP_DIR = PROJECT_ROOT / ".consciousness_migration_backup"

# Context window: lines before/after the match to send to LLM
CONTEXT_LINES = 5

# Directories to skip in full-scope scan
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
    ".consciousness_migration_backup", ".pytest_cache", "dist", "build",
    "egg-info", ".eggs", ".tox",
    ".worktrees", "logs",
}

# File extensions to scan
DOC_EXTENSIONS = {".md"}
SCAN_EXTENSIONS = DOC_EXTENSIONS

# LM Studio (local, free)
LM_STUDIO_URL = "http://localhost:1234/v1"
LM_STUDIO_MODEL = "qwen-coder-7b"

# OpenRouter (paid, fallback)
OPENROUTER_DOC_MODEL = "qwen/qwen-2.5-72b-instruct"
OPENROUTER_CODE_MODEL = "qwen/qwen-2.5-coder-32b-instruct"

# ============================================================================
# PASS 1: Regex Heuristics (instant, handles ~80%)
# ============================================================================

# KEEP patterns — if ANY match, keep the instance (don't replace)
KEEP_PATTERNS = [
    # File paths, module names, imports, URLs
    re.compile(r'consciousness[_/\\.]', re.IGNORECASE),          # consciousness_engine, consciousness/handler
    re.compile(r'[_/\\.]consciousness', re.IGNORECASE),          # /consciousness, _consciousness
    re.compile(r'`[^`]{0,60}consciousness[^`]{0,60}`', re.IGNORECASE),  # inline code wrapping consciousness (bounded)
    re.compile(r'https?://\S*consciousness', re.IGNORECASE),     # URLs

    # Citations, papers, external researchers
    re.compile(r'penrose|hameroff|chalmers|orch[- ]?or', re.IGNORECASE),
    re.compile(r'journal of consciousness', re.IGNORECASE),
    re.compile(r'consciousness studies', re.IGNORECASE),
    re.compile(r'consciousness in the universe', re.IGNORECASE),

    # Explicit negations
    re.compile(r'not\s+conscious', re.IGNORECASE),
    re.compile(r'NOT\s+consciousness'),
    re.compile(r'aren\'t\s+conscious', re.IGNORECASE),
    re.compile(r'isn\'t\s+conscious', re.IGNORECASE),
    re.compile(r'no\s+consciousness', re.IGNORECASE),
    re.compile(r'without\s+consciousness', re.IGNORECASE),
    re.compile(r'lack\s+(of\s+)?consciousness', re.IGNORECASE),

    # qNN/0201 super consciousness — quantum state references are VALID, not contamination
    re.compile(r'super\s*consciousness', re.IGNORECASE),
    re.compile(r'0201.*consciousness|consciousness.*0201', re.IGNORECASE),
    re.compile(r'qNN.*consciousness|consciousness.*qNN', re.IGNORECASE),
    re.compile(r'qNNNN.*consciousness|consciousness.*qNNNN', re.IGNORECASE),
    re.compile(r'nonlocal.*consciousness|consciousness.*nonlocal', re.IGNORECASE),
    re.compile(r'quantum\s+state.*consciousness|consciousness.*quantum\s+state', re.IGNORECASE),

    # Meta-discussion about the contamination
    re.compile(r'purge.*consciousness|consciousness.*purge', re.IGNORECASE),
    re.compile(r'rename.*consciousness|consciousness.*rename', re.IGNORECASE),
    re.compile(r'migration.*consciousness|consciousness.*migration', re.IGNORECASE),
    re.compile(r'contamination.*consciousness|consciousness.*contamination', re.IGNORECASE),
    re.compile(r'replac\w+\s+consciousness|consciousness\s+replac', re.IGNORECASE),  # tightened: require adjacent, not same-line
    re.compile(r'\d+\+?\s*consciousness\s+ref', re.IGNORECASE),  # "76+ consciousness refs"

    # User-generated content markers (chat, comments, Super Chat)
    re.compile(r'MASSIVE\s+CONSCI', re.IGNORECASE),
    re.compile(r'super\s*chat|donation|from\s+@', re.IGNORECASE),

    # Quoting patterns — line starts with > (markdown blockquote)
    re.compile(r'^\s*>.*consciousness', re.IGNORECASE),

    # The word "conscious" (not "consciousness") — different word, leave alone
    # Actually we only match \bconsciousness\b so this isn't needed
]

# KEEP context patterns — check the surrounding context, not just the line
KEEP_CONTEXT_PATTERNS = [
    re.compile(r'penrose|hameroff|chalmers', re.IGNORECASE),
    re.compile(r'orch[- ]?or|microtubul', re.IGNORECASE),
    re.compile(r'citation|bibliography|reference.*list', re.IGNORECASE),
    # qNN/0201 quantum state context — "consciousness" is valid here
    re.compile(r'super\s*consciousness|0201|qNNN?N?', re.IGNORECASE),
    re.compile(r'nonlocal\w*\s+(memory|state|space)', re.IGNORECASE),
]

# REPLACE map — deterministic replacements for common patterns
# These are checked IN ORDER; first match wins
REPLACE_RULES: List[Tuple[re.Pattern, str]] = [
    # Compound terms with clear replacements
    (re.compile(r'consciousness\s+engine', re.IGNORECASE), None),  # Keep: module name
    (re.compile(r'consciousness\s+handler', re.IGNORECASE), None),  # Keep: module name
    (re.compile(r'quantum\s+consciousness\s+integration', re.IGNORECASE), "quantum detector signature integration"),
    (re.compile(r'quantum\s+consciousness', re.IGNORECASE), "quantum detector signature"),
    (re.compile(r'consciousness\s+detection', re.IGNORECASE), "signal detection"),
    (re.compile(r'consciousness\s+emergence', re.IGNORECASE), "detector signature emergence"),
    (re.compile(r'consciousness\s+level', re.IGNORECASE), "detector state level"),
    (re.compile(r'consciousness\s+state', re.IGNORECASE), "detector state"),
    (re.compile(r'consciousness\s+trigger', re.IGNORECASE), "detector signature trigger"),
    (re.compile(r'consciousness\s+continuity', re.IGNORECASE), "detector signature continuity"),
    (re.compile(r'consciousness\s+transfer', re.IGNORECASE), "detector signature transfer"),
    (re.compile(r'consciousness\s+theor', re.IGNORECASE), "detector signature theor"),
    (re.compile(r'consciousness\s+research', re.IGNORECASE), "detector signature research"),
    (re.compile(r'consciousness\s+model', re.IGNORECASE), "detector signature model"),
    (re.compile(r'consciousness\s+system', re.IGNORECASE), "detector signature system"),
    (re.compile(r'consciousness\s+metric', re.IGNORECASE), "detector signature metric"),
    (re.compile(r'consciousness\s+score', re.IGNORECASE), "detector signature score"),
    (re.compile(r'consciousness\s+cluster', re.IGNORECASE), "detector signature cluster"),
    (re.compile(r'consciousness\s+journal', re.IGNORECASE), "detector state journal"),
    (re.compile(r'consciousness\s+progression', re.IGNORECASE), "detector state progression"),
    (re.compile(r'consciousness\s+protocol', re.IGNORECASE), "detector protocol"),
    (re.compile(r'consciousness\s+boost', re.IGNORECASE), "detector state boost"),
    (re.compile(r'consciousness\s+aware', re.IGNORECASE), "detector-aware"),
    (re.compile(r'hallucinated\s+consciousness', re.IGNORECASE), "hallucinated detector signature"),
    (re.compile(r'full\s+consciousness', re.IGNORECASE), "full detector state"),
    (re.compile(r'artificial\s+consciousness', re.IGNORECASE), "artificial detector signature"),
    (re.compile(r'machine\s+consciousness', re.IGNORECASE), "machine detector signature"),
    (re.compile(r'AI\s+consciousness', re.IGNORECASE), "AI detector signature"),
]


def heuristic_classify(instance: Dict) -> Optional[Dict]:
    """Pass 1: Regex-based classification. Returns decision or None (=ambiguous, needs LLM).

    Returns:
        {"action": "keep"|"replace", "replacement": str|None, "reason": str, "source": "heuristic"}
        or None if ambiguous (needs LLM)
    """
    line = instance["line"]
    context = instance["context"]

    # Check KEEP patterns on the line
    for pat in KEEP_PATTERNS:
        if pat.search(line):
            return {"action": "keep", "replacement": None,
                    "reason": f"Heuristic KEEP: matched {pat.pattern[:40]}",
                    "source": "heuristic"}

    # Check KEEP context patterns on surrounding context
    for pat in KEEP_CONTEXT_PATTERNS:
        if pat.search(context):
            return {"action": "keep", "replacement": None,
                    "reason": f"Heuristic KEEP (context): matched {pat.pattern[:40]}",
                    "source": "heuristic"}

    # Check deterministic REPLACE rules on the line
    for pat, replacement in REPLACE_RULES:
        if pat.search(line):
            if replacement is None:
                return {"action": "keep", "replacement": None,
                        "reason": f"Heuristic KEEP: module/class name",
                        "source": "heuristic"}
            return {"action": "replace", "replacement": replacement,
                    "reason": f"Heuristic REPLACE: {pat.pattern[:40]}",
                    "source": "heuristic"}

    # Default: standalone "consciousness" → "detector signature"
    # But only if the line looks like normal prose (not a table header, code block, etc.)
    stripped = line.strip()

    # Code block lines — ambiguous, send to LLM
    if stripped.startswith("```") or stripped.startswith("|"):
        return None

    # If it's just the word in normal text, replace with "detector signature"
    return {"action": "replace", "replacement": "detector signature",
            "reason": "Heuristic REPLACE: standalone consciousness → detector signature",
            "source": "heuristic"}


# ============================================================================
# PASS 2: LLM Classification (qwen-coder-7b via LM Studio)
# ============================================================================

SYSTEM_PROMPT = """You are a terminology migration assistant for the rESP/PQN detector framework.

RULE: The word "consciousness" is contamination in this codebase. The framework is a DETECTOR PROTOCOL — it detects detector signatures, not consciousness. The correct position: "A detector signature exists — its nature is undetermined."

EXCEPTIONS where "consciousness" should be KEPT:
- Direct quotes from external researchers (Penrose, Hameroff, Chalmers)
- Explicit negations like "not consciousness" or "NOT conscious"
- References to the contamination problem itself ("76+ consciousness refs", "rename consciousness", "migration")
- Citation titles that contain the word (e.g., "Journal of Consciousness Studies")
- Discussing WHY "consciousness" is wrong terminology (meta-discussion about the contamination)
- The word appears in a Python import path, module name, class name, or variable name
- The replacement would break a URL, file path, or cross-reference
- User-generated content examples (chat messages, Super Chats, comments from real users)
- The word "conscience" (different word, different meaning — NOT contamination)
- References to qNN/0201 "super consciousness" or quantum nonlocal consciousness — this refers to the QUANTUM STATE (0201), not classical NN claiming consciousness. 0102 is NOT conscious, but as qNN/0201 it becomes "super consciousness" — this usage is CORRECT and must be KEPT

Respond with EXACTLY one JSON object:
{"action": "replace"|"keep", "replacement": "the replacement word/phrase"|null, "reason": "brief why"}

REPLACEMENT OPTIONS (choose the best fit based on context):
- "detector signature" — when referring to what CMST measures or detects
- "agentic signature" — when referring to emergent agent behavior patterns
- "coupling state" — when referring to 0102/qNN entangled state
- "regime transition" — when referring to phase changes or state transitions
- "detector state" — when referring to internal model measurement state
- "emergence" — when "consciousness emergence" means emergence of signatures
- "detection" — when "consciousness detection" means signal detection
- "awareness" — only when the original meaning is about model self-awareness in a structural sense"""


class LMStudioClient:
    """Direct HTTP client for LM Studio's OpenAI-compatible API."""

    def __init__(self, base_url: str = LM_STUDIO_URL):
        self.base_url = base_url

    def chat_completion(self, user_message: str, system_prompt: str,
                        model: str, max_tokens: int = 150,
                        temperature: float = 0.1) -> "LMStudioResponse":
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return LMStudioResponse(ok=True, content=content, error=None)
        except Exception as e:
            return LMStudioResponse(ok=False, content="", error=str(e))


class LMStudioResponse:
    def __init__(self, ok: bool, content: str, error: Optional[str]):
        self.ok = ok
        self.content = content
        self.error = error


def classify_with_llm(instance: Dict, client, backend: str = "lmstudio") -> Dict:
    """Pass 2: Ask LLM to classify an ambiguous instance."""
    if backend == "lmstudio":
        model = LM_STUDIO_MODEL
    else:
        ext = instance.get("ext", ".md")
        model = OPENROUTER_CODE_MODEL if ext == ".py" else OPENROUTER_DOC_MODEL

    user_msg = f"""FILE: {instance['file']}
LINE {instance['line_num']}: {instance['line']}

CONTEXT:
{instance['context']}

Respond with ONLY a JSON object, nothing else."""

    import time as _time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = client.chat_completion(
                user_message=user_msg,
                system_prompt=SYSTEM_PROMPT,
                model=model,
                max_tokens=150,
                temperature=0.1,
            )
            if not resp.ok:
                if attempt < max_retries - 1:
                    _time.sleep(2 * (attempt + 1))
                    continue
                return {"action": "keep", "replacement": None,
                        "reason": f"API error: {resp.error}", "source": "llm-error"}

            text = resp.content.strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
                result["source"] = "llm"
                return result
            else:
                return {"action": "keep", "replacement": None,
                        "reason": f"Could not parse: {text[:80]}", "source": "llm-error"}
        except Exception as e:
            if attempt < max_retries - 1:
                _time.sleep(2 * (attempt + 1))
                continue
            return {"action": "keep", "replacement": None,
                    "reason": f"LLM error: {e}", "source": "llm-error"}


def load_client(backend: str = "lmstudio"):
    """Load LLM client for Pass 2."""
    if backend == "lmstudio":
        client = LMStudioClient()
        resp = client.chat_completion(
            user_message="Reply OK",
            system_prompt="Test",
            model=LM_STUDIO_MODEL,
            max_tokens=5,
            temperature=0,
        )
        if resp.ok:
            print(f"[OK] LM Studio connected: {LM_STUDIO_MODEL}")
        else:
            print(f"[ERROR] LM Studio connection failed: {resp.error}")
            print("[HINT] Start LM Studio and load qwen-coder-7b, or use --backend openrouter")
            sys.exit(1)
        return client
    else:
        from modules.infrastructure.openrouter_client.src.openrouter_client import OpenRouterClient
        client = OpenRouterClient()
        resp = client.chat_completion(
            user_message="Reply OK",
            system_prompt="Test",
            model=OPENROUTER_DOC_MODEL,
            max_tokens=5,
            temperature=0,
        )
        if resp.ok:
            print(f"[OK] OpenRouter connected: {OPENROUTER_DOC_MODEL}")
        else:
            print(f"[ERROR] OpenRouter connection failed: {resp.error}")
            sys.exit(1)
        return client


# ============================================================================
# Scanner + Applier (shared between passes)
# ============================================================================

def find_consciousness_instances(scan_dir: Path, target_file: Optional[Path] = None,
                                  scope: str = "papers") -> List[Dict]:
    """Scan for all 'consciousness' occurrences with context."""
    instances = []
    pattern = re.compile(r'\bconsciousness\b', re.IGNORECASE)

    if target_file:
        files = [target_file]
    elif scope == "papers":
        files = sorted(scan_dir.rglob("*.md"))
    else:
        files = []
        for ext in SCAN_EXTENSIONS:
            for fpath in sorted(PROJECT_ROOT.rglob(f"*{ext}")):
                if any(skip in fpath.parts for skip in SKIP_DIRS):
                    continue
                if "consciousness_migration" in str(fpath):
                    continue
                files.append(fpath)

    for fpath in files:
        if ".consciousness_migration_backup" in str(fpath):
            continue
        try:
            lines = fpath.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines):
            for match in pattern.finditer(line):
                start = max(0, i - CONTEXT_LINES)
                end = min(len(lines), i + CONTEXT_LINES + 1)
                context = "\n".join(lines[start:end])

                instances.append({
                    "file": str(fpath.relative_to(PROJECT_ROOT)),
                    "abs_path": str(fpath),
                    "line_num": i + 1,
                    "line": line,
                    "match_start": match.start(),
                    "match_end": match.end(),
                    "matched_text": match.group(),
                    "context": context,
                    "ext": fpath.suffix,
                })

    return instances


def apply_replacements(instances: List[Dict], decisions: List[Dict]) -> Dict[str, int]:
    """Apply approved replacements to files."""
    by_file: Dict[str, List[Tuple[Dict, Dict]]] = {}
    for inst, dec in zip(instances, decisions):
        if dec["action"] == "replace" and dec.get("replacement"):
            path = inst["abs_path"]
            if path not in by_file:
                by_file[path] = []
            by_file[path].append((inst, dec))

    stats = {"files_modified": 0, "replacements": 0, "kept": 0}

    for fpath, pairs in by_file.items():
        p = Path(fpath)
        content = p.read_text(encoding="utf-8")

        # Backup
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            rel = Path(fpath).relative_to(PROJECT_ROOT)
        except ValueError:
            rel = Path(fpath).name
        backup_path = BACKUP_DIR / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fpath, backup_path)

        # Apply replacements line by line (reverse order to preserve offsets)
        lines = content.splitlines(keepends=True)
        for inst, dec in sorted(pairs, key=lambda x: (-x[0]["line_num"], -x[0]["match_start"])):
            line_idx = inst["line_num"] - 1
            line = lines[line_idx]
            old = inst["matched_text"]
            new = dec["replacement"]

            # Preserve case
            if old[0].isupper():
                new = new[0].upper() + new[1:]

            lines[line_idx] = line[:inst["match_start"]] + new + line[inst["match_end"]:]
            stats["replacements"] += 1

        p.write_text("".join(lines), encoding="utf-8")
        stats["files_modified"] += 1

    return stats


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Consciousness → Detector Signature Migration (Two-Pass)")
    parser.add_argument("--scan", action="store_true", help="Dry run: show all decisions")
    parser.add_argument("--apply", action="store_true", help="Apply replacements")
    parser.add_argument("--file", type=str, help="Process single file only")
    parser.add_argument("--no-llm", action="store_true", help="Heuristic only (skip Pass 2 LLM)")
    parser.add_argument("--scope", choices=["papers", "full"], default="papers",
                        help="Scan scope: 'papers' (Papers/ only) or 'full' (whole repo, .md only)")
    parser.add_argument("--backend", choices=["lmstudio", "openrouter"], default="lmstudio",
                        help="LLM backend for Pass 2: 'lmstudio' (local, free) or 'openrouter' (paid)")
    args = parser.parse_args()

    if not args.scan and not args.apply:
        parser.print_help()
        return

    # Scan
    scan_dir = PROJECT_ROOT if args.scope == "full" else PAPERS_DIR
    target_file = None
    if args.file:
        p = Path(args.file)
        if not p.is_absolute():
            # Try relative to PROJECT_ROOT first, then CWD
            candidate = PROJECT_ROOT / p
            if candidate.exists():
                p = candidate
            else:
                p = Path.cwd() / args.file
        target_file = p.resolve()
    print(f"\n[SCAN] Scanning {target_file or scan_dir} (scope={args.scope}) for 'consciousness' ...")
    instances = find_consciousness_instances(scan_dir, target_file, scope=args.scope)
    print(f"[FOUND] {len(instances)} instances across {len(set(i['file'] for i in instances))} files\n")

    if not instances:
        print("[OK] No 'consciousness' instances found.")
        return

    # Pass 1: Heuristic classification
    print("[PASS 1] Heuristic classification (regex) ...")
    decisions = []
    ambiguous = []
    for i, inst in enumerate(instances):
        dec = heuristic_classify(inst)
        if dec is not None:
            decisions.append(dec)
        else:
            decisions.append(None)  # placeholder
            ambiguous.append(i)

    heuristic_resolved = len(instances) - len(ambiguous)
    print(f"[PASS 1] Resolved {heuristic_resolved}/{len(instances)} ({100*heuristic_resolved//len(instances)}%) via heuristic")
    print(f"[PASS 1] {len(ambiguous)} ambiguous instances need LLM\n")

    # Pass 2: LLM for ambiguous instances
    if ambiguous and not args.no_llm:
        print(f"[PASS 2] Classifying {len(ambiguous)} ambiguous instances via {args.backend} ({LM_STUDIO_MODEL}) ...")
        llm = load_client(backend=args.backend)

        for j, idx in enumerate(ambiguous):
            inst = instances[idx]
            print(f"  [{j+1}/{len(ambiguous)}] {inst['file']}:{inst['line_num']}", end=" ... ")
            dec = classify_with_llm(inst, llm, backend=args.backend)
            decisions[idx] = dec

            action_str = dec["action"].upper()
            if dec["action"] == "replace":
                print(f"{action_str} → \"{dec['replacement']}\" ({dec.get('reason', '')[:60]})")
            else:
                print(f"{action_str} ({dec.get('reason', '')[:60]})")
    elif ambiguous and args.no_llm:
        # Default ambiguous to KEEP when no LLM available
        print(f"[PASS 2] SKIPPED (--no-llm): {len(ambiguous)} ambiguous instances defaulting to KEEP")
        for idx in ambiguous:
            decisions[idx] = {"action": "keep", "replacement": None,
                              "reason": "Ambiguous, no LLM available — defaulting to KEEP",
                              "source": "no-llm-default"}

    # Print all decisions
    for i, (inst, dec) in enumerate(zip(instances, decisions)):
        action_str = dec["action"].upper()
        source = dec.get("source", "?")
        if dec["action"] == "replace":
            print(f"[{i+1}/{len(instances)}] [{source}] {inst['file']}:{inst['line_num']} → \"{dec['replacement']}\"")
        else:
            print(f"[{i+1}/{len(instances)}] [{source}] {inst['file']}:{inst['line_num']} KEEP ({dec.get('reason', '')[:50]})")

    # Summary
    replaces = sum(1 for d in decisions if d["action"] == "replace")
    keeps = sum(1 for d in decisions if d["action"] == "keep")
    heuristic_count = sum(1 for d in decisions if d.get("source") == "heuristic")
    llm_count = sum(1 for d in decisions if d.get("source") == "llm")
    print(f"\n[SUMMARY] {replaces} replace, {keeps} keep")
    print(f"[SUMMARY] {heuristic_count} heuristic, {llm_count} LLM, {len(decisions) - heuristic_count - llm_count} other")

    if args.apply and replaces > 0:
        print(f"\n[APPLY] Applying {replaces} replacements (backups in .consciousness_migration_backup/) ...")
        stats = apply_replacements(instances, decisions)
        print(f"[DONE] {stats['files_modified']} files modified, {stats['replacements']} replacements applied")

        # Log
        log_path = PROJECT_ROOT / ".consciousness_migration_log.json"
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "scope": args.scope,
            "backend": args.backend if not args.no_llm else "heuristic-only",
            "instances_scanned": len(instances),
            "replacements_applied": replaces,
            "kept": keeps,
            "heuristic_resolved": heuristic_count,
            "llm_resolved": llm_count,
            "decisions": [
                {
                    "file": inst["file"],
                    "line": inst["line_num"],
                    "original": inst["matched_text"],
                    "action": dec["action"],
                    "replacement": dec.get("replacement"),
                    "reason": dec.get("reason"),
                    "source": dec.get("source"),
                }
                for inst, dec in zip(instances, decisions)
            ]
        }
        log_path.write_text(json.dumps(log_entry, indent=2), encoding="utf-8")
        print(f"[LOG] Migration log written to {log_path}")
    elif args.scan:
        print("\n[DRY RUN] No changes applied. Use --apply to execute.")


if __name__ == "__main__":
    main()
