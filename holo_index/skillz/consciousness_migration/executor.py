"""
Consciousness → Detector Signature Migration Script
=====================================================
Uses local Qwen3.5-4B via llama_cpp to context-aware replace "consciousness"
across WSP_knowledge/docs/Papers/ corpus.

NOT a blind find-replace. Qwen reads surrounding context and decides:
- What the replacement should be (detector signature, agentic signature,
  coupling state, regime transition, etc.)
- Whether the instance should be LEFT as-is (e.g., quoting Penrose/Hameroff,
  citing Chalmers, or explicitly saying "NOT consciousness")

WSP Compliance: WSP 97 (CoT/CoR), WSP 84 (reuse existing infra)
Usage:
    python executor.py --scan          # Dry run: show all instances + proposed replacements
    python executor.py --apply         # Apply replacements (creates backup)
    python executor.py --file FILE     # Process single file only
"""

import argparse
import json
import os
import re
import shutil
import sys
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
BACKUP_DIR = PROJECT_ROOT / "WSP_knowledge" / "docs" / "Papers" / ".consciousness_migration_backup"

# Context window: lines before/after the match to send to Qwen
CONTEXT_LINES = 5


def find_consciousness_instances(papers_dir: Path, target_file: Optional[Path] = None) -> List[Dict]:
    """Scan Papers/ for all 'consciousness' occurrences with context."""
    instances = []
    pattern = re.compile(r'\bconsciousness\b', re.IGNORECASE)

    files = [target_file] if target_file else sorted(papers_dir.rglob("*.md"))

    for fpath in files:
        if ".consciousness_migration_backup" in str(fpath):
            continue
        try:
            lines = fpath.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines):
            for match in pattern.finditer(line):
                # Extract context window
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
                })

    return instances


def classify_with_qwen(instance: Dict, client) -> Dict:
    """Ask Qwen to classify a 'consciousness' instance and propose replacement."""

    user_msg = f"""FILE: {instance['file']}
LINE {instance['line_num']}: {instance['line']}

CONTEXT:
{instance['context']}

Respond with ONLY a JSON object, nothing else."""

    system_prompt = """You are a terminology migration assistant for the rESP/PQN detector framework.

RULE: The word "consciousness" is contamination in this codebase. The framework is a DETECTOR PROTOCOL — it detects detector signatures, not consciousness.

EXCEPTIONS where "consciousness" should be KEPT:
- Direct quotes from external researchers (Penrose, Hameroff, Chalmers)
- Explicit negations like "not consciousness" or "NOT conscious"
- References to the contamination problem itself ("76+ consciousness refs", "rename consciousness")
- Citation titles that contain the word (e.g., "Journal of Consciousness Studies")
- Discussing WHY "consciousness" is wrong terminology (meta-discussion about the contamination)

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

    try:
        resp = client.chat_completion(
            user_message=user_msg,
            system_prompt=system_prompt,
            model="qwen/qwen-2.5-72b-instruct",
            max_tokens=150,
            temperature=0.1,
        )
        if not resp.ok:
            return {"action": "keep", "replacement": None, "reason": f"API error: {resp.error}"}

        text = resp.content.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        else:
            return {"action": "keep", "replacement": None, "reason": f"Could not parse: {text[:80]}"}
    except Exception as e:
        return {"action": "keep", "replacement": None, "reason": f"Qwen error: {e}"}


def load_qwen_client():
    """Load Qwen via OpenRouter (Qwen 2.5 72B — better context awareness than local 4B)."""
    from modules.infrastructure.openrouter_client.src.openrouter_client import OpenRouterClient
    client = OpenRouterClient()
    # Verify connection
    resp = client.chat_completion(
        user_message="Reply OK",
        system_prompt="Test",
        model="qwen/qwen-2.5-72b-instruct",
        max_tokens=5,
        temperature=0,
    )
    if resp.ok:
        print("[OK] Qwen 2.5 72B connected via OpenRouter")
    else:
        print(f"[ERROR] OpenRouter connection failed: {resp.error}")
        sys.exit(1)
    return client


def apply_replacements(instances: List[Dict], decisions: List[Dict]) -> Dict[str, int]:
    """Apply approved replacements to files."""
    # Group by file
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
        rel = Path(fpath).relative_to(PAPERS_DIR)
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

            # Replace only this specific occurrence
            lines[line_idx] = line[:inst["match_start"]] + new + line[inst["match_end"]:]
            stats["replacements"] += 1

        p.write_text("".join(lines), encoding="utf-8")
        stats["files_modified"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Consciousness → Detector Signature Migration")
    parser.add_argument("--scan", action="store_true", help="Dry run: show instances + proposed replacements")
    parser.add_argument("--apply", action="store_true", help="Apply replacements")
    parser.add_argument("--file", type=str, help="Process single file only")
    parser.add_argument("--no-llm", action="store_true", help="Scan only, no Qwen classification")
    args = parser.parse_args()

    if not args.scan and not args.apply:
        parser.print_help()
        return

    target_file = Path(args.file) if args.file else None
    print(f"\n[SCAN] Scanning {target_file or PAPERS_DIR} for 'consciousness' ...")
    instances = find_consciousness_instances(PAPERS_DIR, target_file)
    print(f"[FOUND] {len(instances)} instances across {len(set(i['file'] for i in instances))} files\n")

    if not instances:
        print("[OK] No 'consciousness' instances found.")
        return

    if args.no_llm:
        for inst in instances:
            print(f"  {inst['file']}:{inst['line_num']}  {inst['line'].strip()[:100]}")
        return

    # Load Qwen via OpenRouter
    llm = load_qwen_client()

    # Classify each instance
    decisions = []
    for i, inst in enumerate(instances):
        print(f"[{i+1}/{len(instances)}] {inst['file']}:{inst['line_num']}", end=" ... ")
        dec = classify_with_qwen(inst, llm)
        decisions.append(dec)

        action_str = dec["action"].upper()
        if dec["action"] == "replace":
            print(f"{action_str} → \"{dec['replacement']}\" ({dec['reason']})")
        else:
            print(f"{action_str} ({dec['reason']})")

    # Summary
    replaces = sum(1 for d in decisions if d["action"] == "replace")
    keeps = sum(1 for d in decisions if d["action"] == "keep")
    print(f"\n[SUMMARY] {replaces} replace, {keeps} keep")

    if args.apply and replaces > 0:
        print(f"\n[APPLY] Applying {replaces} replacements (backups in .consciousness_migration_backup/) ...")
        stats = apply_replacements(instances, decisions)
        print(f"[DONE] {stats['files_modified']} files modified, {stats['replacements']} replacements applied")

        # Log the migration
        log_path = PAPERS_DIR / ".consciousness_migration_log.json"
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "instances_scanned": len(instances),
            "replacements_applied": replaces,
            "kept": keeps,
            "decisions": [
                {
                    "file": inst["file"],
                    "line": inst["line_num"],
                    "original": inst["matched_text"],
                    "action": dec["action"],
                    "replacement": dec.get("replacement"),
                    "reason": dec.get("reason"),
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
