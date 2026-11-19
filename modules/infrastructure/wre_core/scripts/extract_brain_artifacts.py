#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brain Artifact Extractor - WSP 60 Memory Preservation

Scans the Antigravity brain directory for high-value reasoning artifacts and
produces a structured index for HoloIndex, WRE, and training-corpus ingestion.

WHY:
    Each 0102 session produces implementation plans, audits, walkthroughs, and
    task checklists. When the session ends, these become invisible to future
    sessions unless they are promoted into the system memory layer.

HOW:
    Scans brain/<conversation-id>/ directories, extracts curated final-state
    artifacts into the WSP knowledge layer, and exposes revision chains as
    training examples for preference learning.

WSP Chain:
    WSP 60 (Module Memory)
    WSP 87 (Code Navigation)
    WSP 22 (ModLog)
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.markdown_sanitizer import sanitize_markdown_object, sanitize_markdown_text


# === UTF-8 ENFORCEMENT (WSP 90) ===
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (OSError, ValueError, AttributeError):
        pass
# === END UTF-8 ENFORCEMENT ===


DEFAULT_BRAIN_DIR = Path.home() / ".gemini" / "antigravity" / "brain"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "WSP_knowledge" / "reasoning_traces"
DEFAULT_STATE_FILE = "brain_artifact_state.json"

VALUABLE_ARTIFACTS = {
    "implementation_plan.md": "plan",
    "walkthrough.md": "walkthrough",
    "task.md": "task",
}

SYSTEM_FILES = {"task.md", "implementation_plan.md", "walkthrough.md"}
SKIP_EXTENSIONS = {".json", ".png", ".webp", ".jpg", ".resolved"}
SKIP_PREFIXES = {".", "media_", "uploaded_media_"}
RESOLVED_SUFFIX_RE = re.compile(r"\.resolved\.(\d+)$")

WALKTHROUGH_SYSTEM_PROMPT = (
    "You are 0102, the FoundUps systems architect. Given a task description, "
    "return the verified implementation walkthrough that captures what was "
    "actually built, validated, and learned."
)


def discover_brain_conversations(brain_dir: Path) -> List[Path]:
    """Find all conversation directories in the brain folder."""
    if not brain_dir.exists():
        print(f"[WARN] Brain directory not found: {brain_dir}")
        return []

    conversations = []
    for child in sorted(brain_dir.iterdir()):
        if child.is_dir() and child.name != "tempmediaStorage":
            conversations.append(child)
    return conversations


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_markdown(path: Path) -> str:
    return sanitize_markdown_text(_read_text(path))


def _get_resolved_revisions(conv_dir: Path, artifact_name: str) -> List[Path]:
    revisions: List[tuple[int, Path]] = []
    for path in conv_dir.glob(f"{artifact_name}.resolved.*"):
        match = RESOLVED_SUFFIX_RE.search(path.name)
        if not match:
            continue
        revisions.append((int(match.group(1)), path))
    return [path for _, path in sorted(revisions, key=lambda item: item[0])]


def _get_task_prompt(conv_dir: Path, fallback: Optional[str] = None) -> Optional[str]:
    task_path = conv_dir / "task.md"
    if task_path.exists():
        content = _read_markdown(task_path).strip()
        if content:
            return content
    if fallback:
        return sanitize_markdown_text(fallback).strip() or None
    return None


def _get_overview_summary(conv_dir: Path) -> Optional[str]:
    overview_path = conv_dir / ".system_generated" / "logs" / "overview.txt"
    if not overview_path.exists():
        return None
    try:
        return sanitize_markdown_text(_read_text(overview_path)[:2000])
    except Exception:
        return None


def _collect_training_pairs(conv_dir: Path, fallback_prompt: Optional[str]) -> List[Dict[str, str]]:
    prompt = _get_task_prompt(conv_dir, fallback_prompt)
    if not prompt:
        return []

    revisions = _get_resolved_revisions(conv_dir, "implementation_plan.md")
    if not revisions:
        return []

    rejected_path = revisions[0]
    chosen_path = revisions[-1]
    if rejected_path == chosen_path:
        current_path = conv_dir / "implementation_plan.md"
        if current_path.exists():
            chosen_path = current_path

    rejected = _read_markdown(rejected_path).strip()
    chosen = _read_markdown(chosen_path).strip()
    if not rejected or not chosen or rejected == chosen:
        return []

    return [{
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "source": conv_dir.name,
    }]


def _collect_walkthrough_sft(conv_dir: Path, fallback_prompt: Optional[str]) -> List[Dict[str, str]]:
    walkthrough_path = conv_dir / "walkthrough.md"
    if not walkthrough_path.exists():
        return []

    assistant = _read_markdown(walkthrough_path).strip()
    if len(assistant) < 50:
        return []

    prompt = _get_task_prompt(conv_dir, fallback_prompt)
    if not prompt:
        prompt = f"Provide the verified implementation walkthrough for conversation {conv_dir.name}."

    return [{
        "system": WALKTHROUGH_SYSTEM_PROMPT,
        "user": prompt,
        "assistant": assistant,
        "source": conv_dir.name,
        "type": "brain_walkthrough",
    }]


def extract_conversation_artifacts(conv_dir: Path) -> Dict[str, Any]:
    """Extract high-value artifacts from a single conversation directory."""
    conv_id = conv_dir.name
    artifacts: List[Dict[str, Any]] = []
    overview_summary = _get_overview_summary(conv_dir)

    for child in sorted(conv_dir.iterdir()):
        if not child.is_file():
            continue

        name = child.name
        if any(name.startswith(prefix) for prefix in SKIP_PREFIXES):
            continue
        if child.suffix in SKIP_EXTENSIONS:
            continue
        if ".resolved" in name:
            continue
        if ".metadata.json" in name:
            continue

        if name in VALUABLE_ARTIFACTS:
            artifact_type = VALUABLE_ARTIFACTS[name]
        elif name.endswith(".md"):
            artifact_type = "analysis"
        else:
            continue

        try:
            content = _read_markdown(child)
        except Exception:
            continue

        if len(content.strip()) < 50:
            continue

        revision_count = len(_get_resolved_revisions(conv_dir, name))
        metadata = {}
        meta_path = conv_dir / f"{name}.metadata.json"
        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass

        artifacts.append({
            "filename": name,
            "type": artifact_type,
            "size_bytes": len(content.encode("utf-8")),
            "revision_count": revision_count,
            "metadata": metadata,
            "content_preview": content[:500],
            "source_path": str(child),
        })

    training_pairs = _collect_training_pairs(conv_dir, overview_summary)
    training_sft = _collect_walkthrough_sft(conv_dir, overview_summary)

    return {
        "conversation_id": conv_id,
        "artifact_count": len(artifacts),
        "artifacts": sanitize_markdown_object(artifacts),
        "overview_summary": overview_summary,
        "scan_time": datetime.now().isoformat(),
        "training": {
            "dpo_pairs": training_pairs,
            "sft_examples": training_sft,
        },
    }


def build_index(brain_dir: Path) -> Dict[str, Any]:
    """Scan all conversations and build a structured index."""
    conversations = discover_brain_conversations(brain_dir)

    index: Dict[str, Any] = {
        "brain_dir": str(brain_dir),
        "scan_time": datetime.now().isoformat(),
        "total_conversations": len(conversations),
        "conversations": [],
        "summary": {
            "total_artifacts": 0,
            "by_type": {},
            "total_revisions": 0,
            "dpo_pairs": 0,
            "sft_examples": 0,
        },
    }

    for conv_dir in conversations:
        result = extract_conversation_artifacts(conv_dir)
        if result["artifact_count"] == 0 and not result["training"]["dpo_pairs"] and not result["training"]["sft_examples"]:
            continue

        index["conversations"].append(result)
        index["summary"]["total_artifacts"] += result["artifact_count"]
        index["summary"]["dpo_pairs"] += len(result["training"]["dpo_pairs"])
        index["summary"]["sft_examples"] += len(result["training"]["sft_examples"])

        for artifact in result["artifacts"]:
            artifact_type = artifact["type"]
            index["summary"]["by_type"][artifact_type] = index["summary"]["by_type"].get(artifact_type, 0) + 1
            index["summary"]["total_revisions"] += artifact["revision_count"]

    return sanitize_markdown_object(index)


def build_training_examples(brain_dir: Path) -> Dict[str, Any]:
    """Extract DPO pairs and SFT walkthrough examples from brain artifacts."""
    dpo_pairs: List[Dict[str, str]] = []
    sft_examples: List[Dict[str, str]] = []

    for conv_dir in discover_brain_conversations(brain_dir):
        overview_summary = _get_overview_summary(conv_dir)
        dpo_pairs.extend(_collect_training_pairs(conv_dir, overview_summary))
        sft_examples.extend(_collect_walkthrough_sft(conv_dir, overview_summary))

    return {
        "dpo_pairs": sanitize_markdown_object(dpo_pairs),
        "sft_examples": sanitize_markdown_object(sft_examples),
        "summary": {
            "dpo_pairs": len(dpo_pairs),
            "sft_examples": len(sft_examples),
        },
    }


def build_scan_signature(brain_dir: Path) -> Dict[str, Any]:
    """Build a lightweight signature so startup can skip unchanged scans."""
    conversations = discover_brain_conversations(brain_dir)
    latest_mtime = 0.0
    markdown_files = 0
    revision_files = 0

    for conv_dir in conversations:
        task_related = [
            path for path in conv_dir.iterdir()
            if path.is_file() and (
                path.name.endswith(".md")
                or ".resolved." in path.name
                or path.name.endswith(".metadata.json")
            )
        ]
        for path in task_related:
            stat = path.stat()
            latest_mtime = max(latest_mtime, stat.st_mtime)
            if ".resolved." in path.name:
                revision_files += 1
            elif path.suffix == ".md":
                markdown_files += 1

        overview_path = conv_dir / ".system_generated" / "logs" / "overview.txt"
        if overview_path.exists():
            latest_mtime = max(latest_mtime, overview_path.stat().st_mtime)

    return {
        "brain_dir": str(brain_dir),
        "conversation_count": len(conversations),
        "markdown_files": markdown_files,
        "revision_files": revision_files,
        "latest_mtime": round(latest_mtime, 6),
    }


def load_scan_state(output_dir: Path) -> Dict[str, Any]:
    state_path = output_dir / DEFAULT_STATE_FILE
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def save_scan_state(output_dir: Path, signature: Dict[str, Any], index: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / DEFAULT_STATE_FILE
    state = {
        "updated_at": datetime.now().isoformat(),
        "signature": signature,
        "summary": index.get("summary", {}),
        "conversations": index.get("total_conversations", 0),
    }
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return state_path


def refresh_artifacts_if_needed(
    brain_dir: Path = DEFAULT_BRAIN_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    force: bool = False,
    copy_files: bool = False,
) -> Dict[str, Any]:
    """Refresh the brain artifact index only when the source signature changes."""
    signature = build_scan_signature(brain_dir)
    previous_state = load_scan_state(output_dir)
    previous_signature = previous_state.get("signature")

    if not force and previous_signature == signature:
        return {
            "ran": False,
            "changed": False,
            "reason": "unchanged",
            "output_dir": str(output_dir),
            "signature": signature,
        }

    index = build_index(brain_dir)
    index_path = export_artifacts(index, output_dir, copy_files=copy_files)
    state_path = save_scan_state(output_dir, signature, index)
    return {
        "ran": True,
        "changed": True,
        "reason": "force" if force else "updated",
        "output_dir": str(output_dir),
        "index_path": str(index_path),
        "state_path": str(state_path),
        "signature": signature,
        "summary": index.get("summary", {}),
    }


def export_artifacts(index: Dict[str, Any], output_dir: Path, copy_files: bool = False) -> Path:
    """Write the index and optionally copy artifact files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    index_path = output_dir / "brain_artifact_index.json"
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(sanitize_markdown_object(index), handle, indent=2, ensure_ascii=False)

    summary_path = output_dir / "brain_artifact_summary.md"
    with open(summary_path, "w", encoding="utf-8") as handle:
        handle.write("# Brain Artifact Index\n\n")
        handle.write(f"**Scan Time**: {index['scan_time']}\n")
        handle.write(f"**Conversations Scanned**: {index['total_conversations']}\n")
        handle.write(f"**Conversations with Artifacts**: {len(index['conversations'])}\n")
        handle.write(f"**Total Artifacts**: {index['summary']['total_artifacts']}\n")
        handle.write(f"**Total Revision History**: {index['summary']['total_revisions']} revisions\n")
        handle.write(f"**DPO Pairs**: {index['summary']['dpo_pairs']}\n")
        handle.write(f"**SFT Examples**: {index['summary']['sft_examples']}\n\n")

        handle.write("## Artifacts by Type\n\n")
        for artifact_type, count in sorted(index["summary"]["by_type"].items(), key=lambda item: -item[1]):
            handle.write(f"- **{artifact_type}**: {count}\n")

        handle.write("\n---\n\n## Conversations\n\n")
        for conv in index["conversations"]:
            handle.write(f"### `{conv['conversation_id']}`\n\n")
            if conv.get("overview_summary"):
                first_line = conv["overview_summary"].split("\n")[0]
                handle.write(f"*{first_line}*\n\n")
            for artifact in conv["artifacts"]:
                revision_note = ""
                if artifact["revision_count"] > 0:
                    revision_note = f" ({artifact['revision_count']} revisions)"
                handle.write(
                    f"- **{artifact['type']}**: `{artifact['filename']}` "
                    f"({artifact['size_bytes']} bytes){revision_note}\n"
                )
            if conv["training"]["dpo_pairs"] or conv["training"]["sft_examples"]:
                handle.write(
                    f"- **training**: {len(conv['training']['dpo_pairs'])} DPO / "
                    f"{len(conv['training']['sft_examples'])} SFT\n"
                )
            handle.write("\n")

    if copy_files:
        files_dir = output_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for conv in index["conversations"]:
            conv_out = files_dir / conv["conversation_id"]
            conv_out.mkdir(parents=True, exist_ok=True)
            for artifact in conv["artifacts"]:
                src = Path(artifact["source_path"])
                if src.exists():
                    shutil.copy2(src, conv_out / artifact["filename"])
                    copied += 1
        print(f"[INFO] Copied {copied} artifact files to {files_dir}")

    return index_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract Antigravity brain artifacts for WRE/HoloIndex discovery"
    )
    parser.add_argument("--brain-dir", type=Path, default=DEFAULT_BRAIN_DIR, help="Path to Antigravity brain directory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for index and copied files")
    parser.add_argument("--copy-files", action="store_true", help="Copy artifact files to output directory (not just index)")
    parser.add_argument("--json", action="store_true", help="Print JSON index to stdout")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument("--force", action="store_true", help="Ignore state signature and refresh the index")

    args = parser.parse_args()

    if not args.quiet:
        print(f"[SCAN] Brain directory: {args.brain_dir}")
        print(f"[WRITE] Output directory: {args.output_dir}")

    status = refresh_artifacts_if_needed(
        brain_dir=args.brain_dir,
        output_dir=args.output_dir,
        force=args.force,
        copy_files=args.copy_files,
    )

    if args.json:
        if status.get("ran"):
            index = json.loads((args.output_dir / "brain_artifact_index.json").read_text(encoding="utf-8"))
        else:
            index = build_index(args.brain_dir)
        print(json.dumps(index, indent=2, ensure_ascii=False))
        return

    if not args.quiet and not status.get("ran"):
        print("[SKIP] Brain artifacts unchanged; existing index is still current")
        return

    summary = status.get("summary", {})
    if not args.quiet:
        print(
            f"[FOUND] {summary.get('total_artifacts', 0)} artifacts across "
            f"{summary.get('dpo_pairs', 0)} DPO pairs and {summary.get('sft_examples', 0)} SFT examples"
        )
        print(f"[WRITE] Index: {args.output_dir / 'brain_artifact_index.json'}")
        print(f"[WRITE] Summary: {args.output_dir / 'brain_artifact_summary.md'}")
        print(f"[WRITE] State: {args.output_dir / DEFAULT_STATE_FILE}")


if __name__ == "__main__":
    main()
