"""
OpenClaw Memory Query Helpers.

Extracted from openclaw_execution_routes.py per WSP 97 ANNEX.
Handles workspace memory, breadcrumb, and continuity queries.

Public interface (underscore prefix removed for external use).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Time qualifiers that should be normalized to None (not treated as topics)
TIME_ONLY_QUALIFIERS = {
    "yesterday",
    "today",
    "last night",
    "this morning",
    "this week",
    "last week",
    "recently",
    "lately",
}


def normalize_time_qualifier(topic: Optional[str]) -> Optional[str]:
    """
    Normalize time-only qualifiers to None.

    "what was I working on yesterday" should query recent activity,
    not search for the literal topic "yesterday".
    """
    if topic is None:
        return None
    topic_lower = topic.lower().strip()
    if topic_lower in TIME_ONLY_QUALIFIERS:
        return None
    return topic


def get_workspace_path(dae: Any) -> Path:
    """Get the workspace path for memory and reports."""
    repo_root = getattr(dae, "repo_root", None)
    if repo_root:
        return Path(repo_root) / "modules/communication/moltbot_bridge/workspace"
    return Path("modules/communication/moltbot_bridge/workspace")


def extract_snippet(content: str, topic: str) -> str:
    """Extract a text snippet around the topic mention."""
    content_lower = content.lower()
    pos = content_lower.find(topic)
    if pos == -1:
        # Return first meaningful paragraph
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        return lines[0] if lines else ""

    # Extract context around match
    start = max(0, pos - 100)
    end = min(len(content), pos + len(topic) + 200)

    snippet = content[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    return snippet


def search_breadcrumbs(topic: Optional[str], limit: int = 20) -> list[Dict[str, Any]]:
    """
    Search AgentDB breadcrumbs, optionally filtered by topic.

    Returns breadcrumbs matching the topic in action, query, or data fields.
    """
    try:
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()
        all_breadcrumbs = db.get_breadcrumbs(limit=limit * 2)

        if not topic:
            # Return recent breadcrumbs without filtering
            return all_breadcrumbs[:limit]

        # Filter by topic presence in action, query, or data
        topic_lower = topic.lower()
        topic_words = set(topic_lower.split())
        matches = []

        for crumb in all_breadcrumbs:
            searchable = " ".join([
                str(crumb.get("action", "")),
                str(crumb.get("query", "")),
                str(crumb.get("data", "")),
            ]).lower()

            # Match if topic or any topic word (>3 chars) found
            if topic_lower in searchable:
                matches.append(crumb)
            elif any(word in searchable for word in topic_words if len(word) > 3):
                matches.append(crumb)

        return matches[:limit]

    except ImportError:
        logger.debug("AgentDB not available for breadcrumb search")
        return []
    except Exception as exc:
        logger.debug("Failed to search breadcrumbs: %s", exc)
        return []


def get_recent_memory_notes(dae: Any, limit: int = 5) -> list[Dict[str, Any]]:
    """
    Get recent workspace memory notes without topic filtering.

    Returns list of notes with title, date, path.
    """
    memory_dir = get_workspace_path(dae) / "memory"
    if not memory_dir.exists():
        return []

    notes = []
    try:
        for note_path in sorted(memory_dir.glob("*.md"), reverse=True)[:limit]:
            try:
                content = note_path.read_text(encoding="utf-8")
                first_line = content.split("\n")[0].strip()
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else note_path.stem

                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", note_path.stem)
                date = date_match.group(1) if date_match else "unknown"

                notes.append({
                    "title": title,
                    "date": date,
                    "path": note_path.name,
                })
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Failed to get recent memory notes: %s", exc)

    return notes


def scan_workspace_memory(dae: Any, topic: str) -> list[Dict[str, Any]]:
    """
    Scan workspace memory notes for content matching a topic.

    Returns list of matches with provenance.
    """
    memory_dir = get_workspace_path(dae) / "memory"
    if not memory_dir.exists():
        return []

    topic_lower = topic.lower()
    topic_words = set(topic_lower.split())
    matches = []
    total_scanned = 0

    try:
        for note_path in memory_dir.glob("*.md"):
            total_scanned += 1
            try:
                content = note_path.read_text(encoding="utf-8")
                content_lower = content.lower()

                # Check if topic appears in content
                if topic_lower not in content_lower:
                    # Fallback: check if any topic word appears
                    if not any(word in content_lower for word in topic_words if len(word) > 3):
                        continue

                # Extract title and date
                first_line = content.split("\n")[0].strip()
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else note_path.stem

                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", note_path.stem)
                date = date_match.group(1) if date_match else "unknown"

                # Extract snippet around topic
                snippet = extract_snippet(content, topic_lower)

                matches.append({
                    "title": title,
                    "date": date,
                    "path": str(note_path.relative_to(get_workspace_path(dae))),
                    "snippet": snippet,
                    "total_scanned": total_scanned,
                })
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Failed to scan workspace memory: %s", exc)

    # Sort by date descending
    matches.sort(key=lambda m: m.get("date", ""), reverse=True)

    # Propagate total_scanned to all matches
    for match in matches:
        match["total_scanned"] = total_scanned

    return matches


def query_decisions(dae: Any, topic: str) -> str:
    """
    Search workspace memory and breadcrumbs for decisions related to a topic.

    Sources with explicit provenance:
    - workspace_memory: Memory notes containing topic
    - breadcrumbs: AgentDB activity related to topic
    """
    memory_matches = scan_workspace_memory(dae, topic)
    breadcrumb_matches = search_breadcrumbs(topic, limit=10)

    # Filter breadcrumbs to decision-related actions
    decision_keywords = {"decide", "decision", "agreed", "chose", "approved", "rejected"}
    decision_breadcrumbs = []
    for crumb in breadcrumb_matches:
        action = str(crumb.get("action", "")).lower()
        query = str(crumb.get("query", "")).lower()
        if any(kw in action or kw in query for kw in decision_keywords):
            decision_breadcrumbs.append(crumb)

    if not memory_matches and not decision_breadcrumbs:
        return (
            f"**No decisions found for:** `{topic}`\n\n"
            "I searched workspace memory notes and AgentDB breadcrumbs but found no matching records.\n"
            "This may mean:\n"
            "- The decision was made before memory notes were captured\n"
            "- The topic uses different terminology\n"
            "- No formal decision was recorded\n\n"
            "Try rephrasing or ask 012 directly."
        )

    parts = [f"**Decisions related to:** `{topic}`\n"]
    sources = []

    # Memory matches
    if memory_matches:
        sources.append("workspace_memory")
        for match in memory_matches[:5]:
            parts.append(f"### {match['title']}")
            parts.append(f"**Source:** `workspace_memory:{match['path']}`")
            parts.append(f"**Date:** {match.get('date', 'unknown')}")
            if match.get("snippet"):
                parts.append(f"\n{match['snippet'][:500]}")
            parts.append("")

    # Breadcrumb evidence
    if decision_breadcrumbs:
        sources.append("breadcrumbs")
        parts.append("### Related Activity (breadcrumbs)")
        for crumb in decision_breadcrumbs[:3]:
            date = crumb.get("timestamp", "unknown")[:10] if crumb.get("timestamp") else "unknown"
            action = crumb.get("action", "unknown")
            query = crumb.get("query", "")[:80] if crumb.get("query") else ""
            parts.append(f"- **{date}**: {action}")
            if query:
                parts.append(f"  > {query}")
        parts.append("")

    scanned = memory_matches[0].get("total_scanned", "?") if memory_matches else "0"
    parts.append(f"_Sources: {', '.join(sources)} | Scanned {scanned} memory artifacts._")
    return "\n".join(parts)


def query_past_work(dae: Any, topic: Optional[str]) -> str:
    """
    Query past work from workspace memory and AgentDB breadcrumbs.

    Combines:
    - workspace_memory: Memory notes matching topic (or recent notes if no topic)
    - breadcrumbs: Recent AgentDB activity matching topic

    Returns results with explicit provenance.
    """
    results = []

    # Source 1: Workspace memory
    if topic:
        # Topic-filtered search
        memory_matches = scan_workspace_memory(dae, topic)
        for match in memory_matches[:5]:
            results.append({
                "source": "workspace_memory",
                "title": match.get("title", "unknown"),
                "date": match.get("date", "unknown"),
                "path": match.get("path", ""),
                "snippet": match.get("snippet", "")[:300],
            })
    else:
        # No topic: include recent workspace memory notes
        recent_notes = get_recent_memory_notes(dae, limit=5)
        for note in recent_notes:
            results.append({
                "source": "workspace_memory",
                "title": note.get("title", "unknown"),
                "date": note.get("date", "unknown"),
                "path": note.get("path", ""),
                "snippet": "",
            })

    # Source 2: AgentDB breadcrumbs
    breadcrumb_matches = search_breadcrumbs(topic, limit=20)
    for crumb in breadcrumb_matches[:10]:
        results.append({
            "source": "breadcrumbs",
            "title": crumb.get("action", "unknown"),
            "date": crumb.get("timestamp", "unknown")[:10] if crumb.get("timestamp") else "unknown",
            "agent": crumb.get("agent_id", ""),
            "query": crumb.get("query", "")[:100] if crumb.get("query") else "",
        })

    if not results:
        topic_str = f" for `{topic}`" if topic else ""
        return (
            f"**No past work found{topic_str}.**\n\n"
            "Searched: workspace memory notes, AgentDB breadcrumbs.\n"
            "Try a broader topic or check recent sessions."
        )

    # Build response with provenance
    parts = []
    if topic:
        parts.append(f"**Past work on:** `{topic}`\n")
    else:
        parts.append("**Recent work activity:**\n")

    # Group by source for clarity
    memory_items = [r for r in results if r["source"] == "workspace_memory"]
    breadcrumb_items = [r for r in results if r["source"] == "breadcrumbs"]

    if memory_items:
        parts.append("### Workspace Memory")
        for item in memory_items:
            parts.append(f"- **{item['date']}**: {item['title']} (`{item['path']}`)")
            if item.get("snippet"):
                parts.append(f"  > {item['snippet'][:150]}...")
        parts.append("")

    if breadcrumb_items:
        parts.append("### Activity Breadcrumbs")
        for item in breadcrumb_items:
            agent_str = f" [{item['agent']}]" if item.get("agent") else ""
            query_str = f": {item['query']}" if item.get("query") else ""
            parts.append(f"- **{item['date']}**: {item['title']}{agent_str}{query_str}")
        parts.append("")

    source_str = ", ".join(sorted(set(r["source"] for r in results)))
    parts.append(f"_Sources: {source_str}_")
    return "\n".join(parts)


def query_unresolved_work(dae: Any) -> str:
    """Query queue status and memory for unresolved/pending work."""
    unresolved = []
    sources = []

    # Check native execution queue
    queue_path = get_workspace_path(dae) / "reports/openclaw_native_execution_queue_status.json"
    if queue_path.exists():
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
            sources.append(str(queue_path.name))

            # Next ready items
            for item in queue_data.get("next_ready", []):
                unresolved.append({
                    "title": item.get("title", "unknown"),
                    "priority": item.get("priority", "?"),
                    "source": "native_queue (ready)",
                })

            # Audit-required items
            for item in queue_data.get("next_audit", [])[:3]:
                unresolved.append({
                    "title": item.get("title", "unknown"),
                    "priority": item.get("priority", "?"),
                    "source": "native_queue (audit_required)",
                })
        except Exception as exc:
            logger.debug("Failed to read queue status: %s", exc)

    # Check self-research status for update candidates
    research_path = get_workspace_path(dae) / "reports/openclaw_self_research_status.json"
    if research_path.exists():
        try:
            with open(research_path, "r", encoding="utf-8") as f:
                research_data = json.load(f)
            sources.append(str(research_path.name))

            for candidate in research_data.get("update_candidates", [])[:3]:
                unresolved.append({
                    "title": candidate.get("title", "unknown"),
                    "priority": candidate.get("mps", {}).get("priority", "?"),
                    "source": "self_research",
                })
        except Exception as exc:
            logger.debug("Failed to read self-research status: %s", exc)

    if not unresolved:
        return (
            "**No unresolved work found.**\n\n"
            "Checked: native execution queue, self-research status.\n"
            "Either all work is complete or no pending items were recorded."
        )

    parts = ["**Unresolved Work:**\n"]
    for item in unresolved:
        parts.append(
            f"- [{item['priority']}] {item['title']} _(from {item['source']})_"
        )

    parts.append("")
    parts.append(f"_Sources: {', '.join(sources)}_")
    return "\n".join(parts)


def query_recent_sessions(dae: Any) -> str:
    """List recent high-value session notes from workspace memory."""
    memory_dir = get_workspace_path(dae) / "memory"
    if not memory_dir.exists():
        return (
            "**No session memory found.**\n\n"
            "Workspace memory directory does not exist."
        )

    # Get recent memory notes sorted by date
    notes = []
    try:
        for note_path in sorted(memory_dir.glob("*.md"), reverse=True)[:10]:
            try:
                content = note_path.read_text(encoding="utf-8")
                first_line = content.split("\n")[0].strip()
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else note_path.stem

                # Extract date from filename (2026-03-22-topic.md)
                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", note_path.stem)
                date = date_match.group(1) if date_match else "unknown"

                notes.append({
                    "title": title,
                    "date": date,
                    "path": note_path.name,
                    "size": len(content),
                })
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Failed to scan memory directory: %s", exc)

    if not notes:
        return (
            "**No recent sessions found.**\n\n"
            "Workspace memory exists but contains no readable notes."
        )

    parts = ["**Recent Sessions:**\n"]
    for note in notes:
        parts.append(f"- **{note['date']}**: {note['title']} (`{note['path']}`)")

    parts.append("")
    parts.append(f"_Found {len(notes)} session note(s) in workspace memory._")
    return "\n".join(parts)


# ============================================================================
# GATEWAY CONTINUITY LAYER - Query Handlers
# ============================================================================


def query_continuity_status(dae: Any, continuity_id: str) -> str:
    """
    Get detailed status for a specific continuity ID.

    Shows breadcrumbs, surfaces, and lineage for the given continuity ID.
    """
    try:
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()
        summary = db.get_continuity_summary(continuity_id)

        if not summary.get("found"):
            return (
                f"**Continuity ID not found:** `{continuity_id}`\n\n"
                "No breadcrumbs exist for this continuity ID."
            )

        parts = [f"**Continuity Status: `{continuity_id}`**\n"]
        parts.append(f"- **Breadcrumbs:** {summary['breadcrumb_count']}")
        parts.append(f"- **Surfaces:** {', '.join(summary['surfaces'])}")
        parts.append(f"- **First seen:** {summary['first_seen']}")
        parts.append(f"- **Last activity:** {summary['last_seen']}")

        if summary["actions"]:
            parts.append(f"- **Actions:** {', '.join(summary['actions'][:5])}")

        # Get recent breadcrumbs for detail
        breadcrumbs = db.get_breadcrumbs_by_continuity(continuity_id, limit=5)
        if breadcrumbs:
            parts.append("\n**Recent Activity:**")
            for crumb in breadcrumbs[:5]:
                action = crumb.get("action", "unknown")
                surface = crumb.get("runtime_surface", "unknown")
                timestamp = crumb.get("timestamp", "")[:19]
                parts.append(f"- `{timestamp}` [{surface}] {action}")

        return "\n".join(parts)

    except Exception as exc:
        logger.debug("Continuity query failed: %s", exc)
        return f"**Error querying continuity:** {exc}"


def query_cross_surface_activity(dae: Any) -> str:
    """
    Show recent work that spanned multiple runtime surfaces.

    Helpful for understanding how tasks transition across CLI/OpenClaw/messaging.
    """
    try:
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()
        cross_surface = db.get_cross_surface_activity(minutes=60, limit=10)

        if not cross_surface:
            return (
                "**No cross-surface activity found.**\n\n"
                "No work items in the past 60 minutes spanned multiple surfaces."
            )

        parts = ["**Cross-Surface Activity (last 60 min):**\n"]
        for item in cross_surface:
            cid = item["continuity_id"]
            surfaces = ", ".join(item["surfaces"])
            started = item["started_at"][:19] if item["started_at"] else "?"
            parts.append(f"- `{cid}`: {surfaces} (started {started})")

        parts.append("")
        parts.append(f"_Found {len(cross_surface)} cross-surface work item(s)._")
        return "\n".join(parts)

    except Exception as exc:
        logger.debug("Cross-surface query failed: %s", exc)
        return f"**Error querying cross-surface activity:** {exc}"


def query_current_continuity(dae: Any) -> str:
    """
    Show the current continuity context for this request.

    Useful for debugging continuity propagation.
    """
    continuity_ctx = getattr(dae, "_continuity_context", None)
    if continuity_ctx is None:
        return (
            "**No continuity context available.**\n\n"
            "This request does not have an active continuity context."
        )

    parts = ["**Current Continuity Context:**\n"]
    parts.append(f"- **Continuity ID:** `{continuity_ctx.continuity_id}`")
    parts.append(f"- **Surface:** {continuity_ctx.surface.value}")
    parts.append(f"- **Session ID:** {continuity_ctx.session_id}")
    parts.append(f"- **Sender:** {continuity_ctx.sender}")
    parts.append(f"- **Sender (normalized):** {continuity_ctx.sender_normalized}")
    parts.append(f"- **Channel:** {continuity_ctx.channel}")

    if continuity_ctx.parent_continuity_id:
        parts.append(f"- **Parent Continuity:** `{continuity_ctx.parent_continuity_id}`")

    parts.append(f"- **Created:** {continuity_ctx.created_at}")

    if continuity_ctx.surface_metadata:
        parts.append("\n**Surface Metadata:**")
        for key, value in continuity_ctx.surface_metadata.items():
            parts.append(f"- {key}: {value}")

    return "\n".join(parts)
