#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io

"""
# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

HoloIndex - Dual Semantic Navigation for Code + WSP
Leverages the E: SSD for ultra-fast, persistent search

WSP 87 Compliant - Prevents vibecoding by pairing code discovery with protocol guidance
"""

import argparse
import json
import os
import re
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import asdict
from holo_index.utils.helpers import safe_print
# WSP 97: Lazy import codeindex_reporter (4s+ startup cost) - only needed for --code-index-report
CodeIndexReporter = None  # Lazy loaded
resolve_module_paths = None  # Lazy loaded

# WSP 97: Lazy load qwen_advisor (4s+ startup cost) - only import when --llm-advisor used
# Check early if we need advisor to decide on lazy loading
_need_advisor = "--llm-advisor" in sys.argv or os.getenv("HOLOINDEX_ADVISOR") == "always"
if _need_advisor:
    try:
        from holo_index.qwen_advisor.advisor import AdvisorContext, QwenAdvisor
        from holo_index.qwen_advisor.config import QwenAdvisorConfig
        from holo_index.qwen_advisor.telemetry import record_advisor_event
        from holo_index.qwen_advisor.rules_engine import ComplianceRulesEngine
        from holo_index.qwen_advisor.agent_detection import AgentEnvironmentDetector
        ADVISOR_AVAILABLE = True
    except Exception:
        ADVISOR_AVAILABLE = False
        AdvisorContext = None  # type: ignore
        QwenAdvisor = None  # type: ignore
        QwenAdvisorConfig = None  # type: ignore
        AgentEnvironmentDetector = None  # type: ignore
        record_advisor_event = None  # type: ignore
else:
    ADVISOR_AVAILABLE = False
    AdvisorContext = None  # type: ignore
    QwenAdvisor = None  # type: ignore
    QwenAdvisorConfig = None  # type: ignore
    AgentEnvironmentDetector = None  # type: ignore
    record_advisor_event = None  # type: ignore

# Phase 3: Adaptive Learning Integration
try:
    from holo_index.adaptive_learning.adaptive_learning_orchestrator import AdaptiveLearningOrchestrator
    ADAPTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ADAPTIVE_LEARNING_AVAILABLE = False
    record_advisor_event = None  # type: ignore

# Import extracted modules with proper path handling
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Temporarily use regular print - safe_print causing scoping issues
# TODO: Fix safe_print scoping issue

if "--offline" in sys.argv:
    os.environ.setdefault('HOLO_OFFLINE', '1')
    os.environ.setdefault('HOLO_DISABLE_PIP_INSTALL', '1')
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
    # WSP 97: --offline MUST skip model to prevent import hangs
    os.environ.setdefault('HOLO_SKIP_MODEL', '1')

# WSP 97: --fast-search also skips heavy model imports
if "--fast-search" in sys.argv:
    os.environ.setdefault('HOLO_SKIP_MODEL', '1')

def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")

# 0102 speed knob: allow bundle-json/offline/fast-search fastpath without importing Chroma/model stack.
_skip_heavy_imports = (
    ("--bundle-json" in sys.argv and _env_truthy("HOLO_SKIP_MODEL", "false")) or
    ("--offline" in sys.argv) or
    ("--fast-search" in sys.argv) or
    _env_truthy("HOLO_SKIP_MODEL", "false")
)
if not _skip_heavy_imports:
    try:
        from holo_index.core import IntelligentSubroutineEngine, HoloIndex
        from holo_index.output import AgenticOutputThrottler
        from holo_index.utils import print_onboarding
    except ImportError:
        # Fallback for when run as script
        sys.path.insert(0, str(Path(__file__).parent))
        from core import IntelligentSubroutineEngine, HoloIndex
        from output import AgenticOutputThrottler
        from utils import print_onboarding
else:
    IntelligentSubroutineEngine = None  # type: ignore
    HoloIndex = None  # type: ignore
    AgenticOutputThrottler = None  # type: ignore
    print_onboarding = None  # type: ignore

# SSD locations (Phase 1 requirement)
os.environ.setdefault('CHROMADB_DATA_PATH', 'E:/HoloIndex/vectors')
os.environ.setdefault('SENTENCE_TRANSFORMERS_HOME', 'E:/HoloIndex/models')
os.environ.setdefault('HOLO_CACHE_PATH', 'E:/HoloIndex/cache')

# Dependency bootstrap
# try:
#     import chromadb
#     from sentence_transformers import SentenceTransformer
# except ImportError:
#     print("Installing required dependencies...")
#     import subprocess
#     subprocess.check_call([sys.executable, "-m", "pip", "install", "chromadb", "sentence-transformers"])
#     import chromadb
#     from sentence_transformers import SentenceTransformer

# Utility functions now imported from utils module

# -------------------- Heuristic Configuration -------------------- #

VIOLATION_RULES: List[Dict[str, str]] = [
    {
        "pattern": r"\benhanced\b|\benhanced_",
        "wsp": "WSP 84",
        "message": "WSP 84: evolve existing modules; never create enhanced_* duplicates."
    },
    {
        "pattern": r"create\s+new",
        "wsp": "WSP 50",
        "message": "WSP 50: run pre-action verification before starting new code."
    },
    {
        "pattern": r"rename|naming",
        "wsp": "WSP 57",
        "message": "WSP 57: verify naming coherence before renaming components."
    },
]

CONTEXT_WSP_MAP: Dict[str, List[str]] = {
    "document": ["WSP 22", "WSP 83"],
    "modlog": ["WSP 22"],
    "test": ["WSP 5", "WSP 6"],
    "structure": ["WSP 49"],
    "naming": ["WSP 57"],
    "token": ["WSP 75"],
    "create": ["WSP 50", "WSP 84"],
}

WSP_HINTS: Dict[str, str] = {
    "WSP 22": "Keep module documentation and ModLogs synchronized.",
    "WSP 49": "Follow module directory scaffolding (src/tests/memory/docs).",
    "WSP 50": "Log intent in pre-action journal before coding.",
    "WSP 57": "Maintain naming coherence across files and identifiers.",
    "WSP 75": "Track effort in tokens, not wall-clock minutes.",
    "WSP 84": "Evolve existing modules instead of cloning new versions.",
    "WSP 87": "Consult navigation assets before writing new code.",
}

CODEINDEX_REPORT_ALIASES: Dict[str, List[str]] = {
    "youtube_dae": [
        "modules/communication/livechat",
        "modules/communication/youtube_dae",
        "modules/platform_integration/stream_resolver",
        "modules/platform_integration/youtube_auth",
    ],
}

# Import dynamic WSP paths from helpers
try:
    from .utils.helpers import get_wsp_paths
    DEFAULT_WSP_PATHS = get_wsp_paths()
except ImportError:
    # Fallback if import fails
    DEFAULT_WSP_PATHS = [
        Path("../WSP_framework/src"),
        Path("../WSP_framework/docs"),
        Path("../WSP_knowledge/docs"),
        Path("../WSP_framework/docs/testing"),
        Path("docs"),
        Path("../modules"),
    ]

# Onboarding function now imported from utils module
# -------------------- HoloIndex Implementation -------------------- #

# HoloIndex class extracted to core/holo_index.py

# -------------------- CLI Entry Point -------------------- #

def render_response(throttler, outputs, args):
    """
    Central throttler flow - render all outputs through the throttler.

    Args:
        throttler: AgenticOutputThrottler instance
        outputs: Dict with 'sections' list and 'metadata'
        args: Parsed CLI arguments
    """
    # Set query context if available
    if 'query' in outputs.get('metadata', {}):
        throttler.set_query_context(outputs['metadata']['query'], outputs.get('search_results'))

    # Add all sections
    for section in outputs.get('sections', []):
        throttler.add_section(**section)

    # Render and print
    output = throttler.render_prioritized_output(verbose=getattr(args, 'verbose', False))
    safe_print(output)


def _is_fast_search_enabled(args) -> bool:
    """
    Decide whether to run fast retrieval-only search path.

    Fast mode intentionally skips heavy advisory/orchestration layers to keep
    CLI latency low for direct lookup workflows.
    """
    explicit = bool(getattr(args, "fast_search", False))
    env_enabled = _env_truthy("HOLO_FAST_SEARCH", "false")
    return explicit or env_enabled


def _render_fast_search_summary(results: Dict[str, Any], limit: int = 5) -> None:
    """Compact fast-mode output compatible with existing CLI usage."""
    code_hits = results.get("code", []) or []
    wsp_hits = results.get("wsps", []) or []
    total_hits = len(code_hits) + len(wsp_hits)

    safe_print(f"[OK] Analysis complete: {total_hits} hits (code={len(code_hits)}, wsp={len(wsp_hits)}), no critical issues found")
    safe_print("[RESULTS] Top matches")

    shown = 0
    for hit in code_hits:
        loc = hit.get("location") or hit.get("path") or "unknown"
        safe_print(f"  [CODE] {loc}")
        shown += 1
        if shown >= limit:
            return

    for hit in wsp_hits:
        title = hit.get("title") or "unknown"
        path = hit.get("path") or "unknown"
        safe_print(f"  [WSP] {path if path != 'unknown' else title}")
        shown += 1
        if shown >= limit:
            return

# Temporary stub - to be extracted later
def _get_search_history_for_patterns():
    """Retrieve search history for pattern analysis (Phase 2)."""
    return []  # Stub implementation


# _record_thought_to_memory function moved to utils module
def _record_thought_to_memory(results, query, advisor, add_reward_event):
    """Record thoughts to memory - stub implementation."""
    pass  # TODO: Complete implementation


# Health checking now handled by intelligent subroutines
# Function body removed during refactoring - see IntelligentSubroutineEngine


def _perform_health_checks_and_rewards(results, last_query, add_reward_event):
    """Stub function for health checks and rewards - TODO: implement properly"""
    return None

def _run_codeindex_report(target: str) -> None:
    # WSP 97: Lazy import to avoid 4s+ startup penalty when not using --code-index-report
    from holo_index.reports.codeindex_reporter import CodeIndexReporter, resolve_module_paths
    reporter = CodeIndexReporter()
    repo_root = project_root
    alias = target.strip()
    modules = CODEINDEX_REPORT_ALIASES.get(alias, [alias])
    module_paths = resolve_module_paths(repo_root, modules)
    if not module_paths:
        safe_print(f"[CODEINDEX] No modules resolved for target '{alias}'.")
        safe_print("           Provide a known alias (e.g., youtube_dae) or a module path.")
        return

    title = f"CodeIndex Report: {alias}"
    report = reporter.generate(module_paths, title)
    timestamp = report.generated_at.strftime('%Y%m%d-%H%M%S')
    sanitized_alias = re.sub(r'[^A-Za-z0-9_-]', '_', alias)
    # WSP 3: Reports belong in holo_index/reports/, not root docs/
    output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"CodeIndex_Report_{sanitized_alias}_{timestamp}.md"
    output_path.write_text(report.markdown, encoding='utf-8')

    module_list_display = ", ".join(path.name for path in module_paths)
    safe_print(f"[CODEINDEX] Report saved -> {output_path}")
    safe_print(f"[CODEINDEX] Modules analyzed: {module_list_display}")
    for summary in report.module_reports:
        safe_print(
            f"  - {summary.module_name}: {summary.critical_fix_count()} critical fixes "
            f"({len(summary.surgical_fixes)} total surgical recommendations)"
        )

    log_path = output_dir / "CodeIndex_Report_Log.md"
    # Make path relative to holo_index for cleaner display
    try:
        relative_report = output_path.relative_to(Path(__file__).parent.parent)
    except ValueError:
        relative_report = output_path  # Fallback to absolute if relative fails
    critical_summary = ", ".join(
        f"{summary.module_name}:{summary.critical_fix_count()}"
        for summary in report.module_reports
    ) or "n/a"
    log_entry = [
        f"## {report.generated_at.isoformat()} UTC — {alias}",
        f"- Report: `{relative_report}`",
        f"- Modules: {module_list_display if module_list_display else 'n/a'}",
        f"- Critical Fixes: {critical_summary}",
        ""
    ]
    if log_path.exists():
        existing = log_path.read_text(encoding='utf-8')
    else:
        existing = "# CodeIndex Report Log\n\nTracks CodeIndex surgical reports generated via CLI.\n\n"
    # Write log entry
    new_log = existing + "\n".join(log_entry) + "\n"
    log_path.write_text(new_log, encoding='utf-8')


def _generate_cli_catalog(scan_result, catalog_path: Path) -> None:
    """Generate AGENT_CLI_CATALOG.md from orphan capability scan results."""
    from datetime import datetime

    lines = [
        "# Agent CLI Catalog (OpenClaw/IronClaw)",
        "",
        "0102 reference for all CLIs that support `--json` output for agent orchestration.",
        "",
        f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M')} (auto-generated by `--index-cli`)",
        "**Indexed By**: HoloIndex semantic search",
        f"**Total CLIs**: {scan_result.total_cli_entrypoints} | **WRE-Connected**: {scan_result.registered_skills} | **Orphans**: {len(scan_result.orphans)}",
        "",
        "---",
        "",
        "## WRE-Connected CLIs (have SKILLz.md)",
        "",
        "| CLI | Path | SKILLz.md | JSON Support |",
        "|-----|------|-----------|--------------|",
    ]

    for cap in scan_result.wre_connected:
        json_flag = "✓" if cap.has_json_flag else "○"
        lines.append(f"| `{cap.module_name}` | `{cap.path}` | ✓ | {json_flag} |")

    lines.extend([
        "",
        "---",
        "",
        "## Orphan CLIs (need SKILLz.md)",
        "",
        "| CLI | Path | Lines | JSON Support | Suggested Trigger |",
        "|-----|------|-------|--------------|-------------------|",
    ])

    # Show top 50 orphans by line count (most substantial)
    sorted_orphans = sorted(scan_result.orphans, key=lambda x: x.line_count, reverse=True)[:50]
    for cap in sorted_orphans:
        json_flag = "✓" if cap.has_json_flag else "○"
        lines.append(f"| `{cap.module_name}` | `{cap.path}` | {cap.line_count} | {json_flag} | {cap.suggested_trigger} |")

    if len(scan_result.orphans) > 50:
        lines.append(f"| ... | *{len(scan_result.orphans) - 50} more orphans* | | | |")

    lines.extend([
        "",
        "---",
        "",
        "## Adding New Agent CLIs",
        "",
        "1. **Add `--json` flag** for machine-readable output",
        "2. **Create SKILLz.md** in adjacent `skillz/` directory",
        "3. **Run** `python holo_index.py --index-cli` to refresh catalog",
        "",
        "---",
        "",
        "_WSP 77 / WSP 95 / WSP 103: Agent Coordination, Skills Wardrobe, CLI Interface Standard_",
    ])

    catalog_path.write_text("\n".join(lines), encoding="utf-8")


def _generate_cli_rolodex_json(scan_result, rolodex_path: Path) -> None:
    """Generate machine-readable command_rolodex.json for agent consumption."""
    import json
    from datetime import datetime

    rolodex = {
        "generated_at": datetime.now().isoformat(),
        "total_cli_entrypoints": scan_result.total_cli_entrypoints,
        "wre_connected_count": scan_result.registered_skills,
        "orphan_count": len(scan_result.orphans),
        "commands": []
    }

    # Add WRE-connected commands
    for cap in scan_result.wre_connected:
        rolodex["commands"].append({
            "path": cap.path,
            "module_name": cap.module_name,
            "has_json_flag": cap.has_json_flag,
            "wre_connected": True,
            "skillz_md_path": cap.skillz_md_path,
            "line_count": cap.line_count,
            "category": cap.category,
        })

    # Add orphan commands
    for cap in scan_result.orphans:
        rolodex["commands"].append({
            "path": cap.path,
            "module_name": cap.module_name,
            "has_json_flag": cap.has_json_flag,
            "wre_connected": False,
            "skillz_md_path": None,
            "line_count": cap.line_count,
            "category": cap.category,
            "suggested_trigger": cap.suggested_trigger,
        })

    rolodex_path.write_text(json.dumps(rolodex, indent=2), encoding="utf-8")


def _generate_cli_rolodex_sqlite(scan_result, db_path: Path) -> None:
    """
    Generate SQLite command_rolodex.db for indexed queries (dual-write pattern).

    Enables:
    - Fast queries by WRESkillsDiscovery
    - Gemma pattern-matching for SKILLz.md suggestions
    - Analytics on orphan reduction progress
    """
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cli_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            module_name TEXT NOT NULL,
            has_json_flag BOOLEAN DEFAULT FALSE,
            wre_connected BOOLEAN DEFAULT FALSE,
            skillz_md_path TEXT,
            line_count INTEGER DEFAULT 0,
            category TEXT DEFAULT 'unknown',
            suggested_trigger TEXT DEFAULT 'manual',
            indexed_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rolodex_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Create indexes for fast queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wre_connected ON cli_commands(wre_connected)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_json ON cli_commands(has_json_flag)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON cli_commands(category)")

    # Clear existing data (full refresh)
    cursor.execute("DELETE FROM cli_commands")
    cursor.execute("DELETE FROM rolodex_metadata")

    indexed_at = datetime.now().isoformat()

    # Insert WRE-connected commands
    for cap in scan_result.wre_connected:
        cursor.execute("""
            INSERT OR REPLACE INTO cli_commands
            (path, module_name, has_json_flag, wre_connected, skillz_md_path, line_count, category, suggested_trigger, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cap.path, cap.module_name, cap.has_json_flag, True, cap.skillz_md_path, cap.line_count, cap.category, "wre_skill", indexed_at))

    # Insert orphan commands
    for cap in scan_result.orphans:
        cursor.execute("""
            INSERT OR REPLACE INTO cli_commands
            (path, module_name, has_json_flag, wre_connected, skillz_md_path, line_count, category, suggested_trigger, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cap.path, cap.module_name, cap.has_json_flag, False, None, cap.line_count, cap.category, cap.suggested_trigger, indexed_at))

    # Store metadata
    cursor.execute("INSERT INTO rolodex_metadata VALUES (?, ?)", ("indexed_at", indexed_at))
    cursor.execute("INSERT INTO rolodex_metadata VALUES (?, ?)", ("total_commands", str(scan_result.total_cli_entrypoints)))
    cursor.execute("INSERT INTO rolodex_metadata VALUES (?, ?)", ("wre_connected_count", str(scan_result.registered_skills)))
    cursor.execute("INSERT INTO rolodex_metadata VALUES (?, ?)", ("orphan_count", str(len(scan_result.orphans))))

    conn.commit()
    conn.close()


def main():
    """Main CLI entry point for HoloIndex."""
    parser = argparse.ArgumentParser(
        description='HoloIndex - Dual Semantic Navigation for Code + WSP',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--search', '-s', type=str, help='Search query')
    parser.add_argument('--limit', type=int, default=5, help='Number of results (default: 5)')
    parser.add_argument(
        '--bundle-json',
        action='store_true',
        help='Emit machine-readable WSP memory bundle JSON (stdout only, no extra text)'
    )
    parser.add_argument(
        '--bundle-module-hint',
        type=str,
        help='Module hint or module path for bundle generation (e.g., modules/communication/livechat or livechat)'
    )
    parser.add_argument(
        '--bundle-task',
        type=str,
        help='Override task string used for bundle generation (defaults to --search)'
    )
    parser.add_argument('--index', action='store_true', help='Index both code and WSP (alias for --index-all)')
    parser.add_argument('--index-all', action='store_true', help='Index both code and WSP')
    parser.add_argument('--index-code', action='store_true', help='Index code (NAVIGATION.py)')
    parser.add_argument('--index-wsp', action='store_true', help='Index WSP documents')
    parser.add_argument('--index-symbols', action='store_true', help='Index code symbols (functions/classes)')
    parser.add_argument('--symbol-roots', nargs='*', help='Limit symbol indexing to specific roots (relative to repo)')
    parser.add_argument('--index-skillz', dest='index_skills', action='store_true', help='Index SKILLz.md files for agent discovery (preferred)')
    parser.add_argument('--index-skills', dest='index_skills', action='store_true', help='Legacy alias for --index-skillz')
    parser.add_argument('--reindex-skills', dest='index_skills', action='store_true', help='Alias for --index-skillz (WRE automation)')
    parser.add_argument('--reindex-skillz', dest='index_skills', action='store_true', help='Alias for --index-skillz')
    parser.add_argument('--index-cli', dest='index_cli', action='store_true', help='Index CLI entrypoints → AGENT_CLI_CATALOG.md (command rolodex)')
    parser.add_argument('--wsp-path', type=str, nargs='*', help='Custom WSP paths to index')
    parser.add_argument('--code-index', action='store_true', help='Enable full code index mode: function indexing + inefficiency analysis + detailed mermaid diagrams')
    parser.add_argument('--dae-cubes', action='store_true', help='Enable DAE cube mapping')
    parser.add_argument('--function-index', action='store_true', help='Enable function-level indexing')
    parser.add_argument('--code-index-report', type=str, help='Generate CodeIndex report for an alias or module path (e.g., youtube_dae)')
    parser.add_argument('--doc-type', choices=['wsp_protocol', 'module_readme', 'interface', 'documentation', 'roadmap', 'modlog', 'all'], default='all', help='Filter by document type (default: all)')
    parser.add_argument('--benchmark', action='store_true', help='Benchmark SSD performance')
    parser.add_argument('--ssd', type=str, default='E:/HoloIndex', help='SSD base path (default: E:/HoloIndex)')
    parser.add_argument('--offline', action='store_true', help='Disable model downloads and pip installs; use offline lexical search if needed')
    parser.add_argument('--fast-search', action='store_true', help='Fast retrieval-only mode (skips heavy advisory/orchestration steps)')

    parser.add_argument('--llm-advisor', action='store_true', help='Force enable Qwen advisor guidance')
    parser.add_argument('--init-dae', type=str, nargs='?', const='auto', help='Initialize DAE context (auto-detect or specify DAE focus)')
    parser.add_argument('--wsp88', action='store_true', help='Run WSP 88 orphan analysis')
    parser.add_argument('--audit-docs', action='store_true', help='Audit documentation completeness for HoloIndex files')
    parser.add_argument('--check-module', type=str, help='Check if a module exists (WSP compliance - use before code generation)')
    parser.add_argument('--docs-file', type=str, help='Get documentation paths for a Python file (implements 012 insight: direct doc provision)')
    parser.add_argument('--check-wsp-docs', action='store_true', help='Run WSP Documentation Guardian compliance check (read-only)')
    parser.add_argument('--fix-ascii', action='store_true', help='Enable ASCII auto-remediation when used with --check-wsp-docs')
    parser.add_argument('--rollback-ascii', type=str, help='Rollback ASCII changes for a specific file (provide filename)')
    parser.add_argument('--fix-violations', action='store_true', help='Auto-correct correctable root directory violations (WSP compliance)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output including low-priority information')
    parser.add_argument('--no-advisor', action='store_true', help='Disable advisor (opt-out for 0102 agents)')
    parser.add_argument('--advisor-rating', choices=['useful', 'needs_more'], help='Provide feedback on advisor output')
    parser.add_argument('--memory-feedback', type=str, help='Record memory card feedback (mem:id=good|noisy|missing, comma-separated)')
    parser.add_argument('--memory-query', type=str, help='Query associated with memory feedback (optional)')
    parser.add_argument('--memory-notes', type=str, help='Optional notes for memory feedback')
    parser.add_argument('--ack-reminders', action='store_true', help='Confirm advisor reminders were acted on')
    parser.add_argument('--adaptive', action='store_true', help='Enable adaptive learning processing (default: off for performance)')
    parser.add_argument('--quiet-root-alerts', action='store_true', help='Suppress root violation alerts')

    parser.add_argument('--support', type=str, nargs='?', const='auto', help='Run support workflow (use values like auto, docs, ascii)')
    parser.add_argument('--diagnose', type=str, help='Run targeted diagnosis (e.g., holodae, compliance, modules)')
    parser.add_argument('--troubleshoot', type=str, help='Run troubleshooting workflow for common issues (e.g., large_files)')

    # Autonomous HoloDAE commands
    parser.add_argument('--start-holodae', action='store_true', help='Start autonomous HoloDAE monitoring (like YouTube DAE)')
    parser.add_argument('--stop-holodae', action='store_true', help='Stop autonomous HoloDAE monitoring')
    parser.add_argument('--holodae-status', action='store_true', help='Show HoloDAE status and activity')

    # Qwen Module Documentation Linker commands
    parser.add_argument('--link-modules', action='store_true', help='Link module documentation using Qwen advisor')
    parser.add_argument('--module', type=str, help='Specific module to link (e.g., "liberty_alert" or "communication/liberty_alert")')
    parser.add_argument('--interactive', action='store_true', help='Interactive verification mode for module linking')
    parser.add_argument('--force', action='store_true', help='Force relink even if already linked')

    # Module documentation query commands
    parser.add_argument('--query-modules', action='store_true', help='Query module documentation from database')
    parser.add_argument('--wsp', type=str, help='Find modules implementing a WSP protocol (e.g., "WSP 90")')
    parser.add_argument('--list-modules', action='store_true', help='List all registered modules')

    # HoloDAE menu feature commands (missing CLI entry points)
    parser.add_argument('--pattern-coach', action='store_true', help='Run pattern coach to prevent behavioral vibecoding')
    parser.add_argument('--module-analysis', action='store_true', help='Analyze modules for duplicates and health issues')
    parser.add_argument('--health-check', action='store_true', help='Run health analysis on system architecture')
    parser.add_argument('--performance-metrics', action='store_true', help='View HoloDAE effectiveness and performance scores')
    parser.add_argument('--system-check', action='store_true', help='Run Holo system check and generate a report')
    parser.add_argument('--slow-mode', action='store_true', help='Enable recursive feedback with 2-3s delays')
    parser.add_argument('--pattern-memory', action='store_true', help='View learned intervention patterns from memory')
    parser.add_argument('--mcp-hooks', action='store_true', help='Inspect MCP connector health and registrations')
    parser.add_argument('--mcp-log', action='store_true', help='Review recent MCP tool activity log')
    parser.add_argument('--thought-log', action='store_true', help='View chain-of-thought breadcrumb trail')
    parser.add_argument('--monitor-work', action='store_true', help='Monitor work completion for auto-publish (ai_intelligence/work_completion_publisher)')
    parser.add_argument('--organize-docs', action='store_true', help='Allow DocDAE to reorganize docs during auto-refresh')

    args = parser.parse_args()

    # --- Bundle JSON (extracted to holo_index/cli/commands/bundle_json.py) ---
    from holo_index.cli.commands.bundle_json import handle_bundle_json
    if handle_bundle_json(args):
        return

    verbose = bool(getattr(args, 'verbose', False))
    search_active = bool(getattr(args, 'search', None))

    def vprint(message: str) -> None:
        if verbose:
            if search_active:
                logging.getLogger(__name__).debug(message)
            else:
                safe_print(message)

    detector = None
    agent_is_0102 = False
    if ADVISOR_AVAILABLE and AgentEnvironmentDetector:
        try:
            detector = AgentEnvironmentDetector()
            agent_is_0102 = detector.is_0102_agent()
        except Exception:
            detector = None
    else:
        agent_is_0102 = os.getenv("AGENT_MODE") == "0102" or os.getenv("HOLOINDEX_ADVISOR") == "always"

    os.environ['HOLO_VERBOSE'] = '1' if (verbose and not agent_is_0102) else '0'
    if agent_is_0102:
        os.environ.setdefault("HOLO_SILENT", "1")

    # Quiet loggers (0102 memory-first: suppress console noise)
    quiet_level = None
    if agent_is_0102:
        quiet_level = logging.ERROR
    elif not verbose:
        quiet_level = logging.WARNING

    if quiet_level is not None:
        logging.getLogger().setLevel(quiet_level)
        noisy_loggers = [
            'chromadb',
            'chromadb.telemetry',
            'chromadb.telemetry.product.posthog',
            'sentence_transformers',
            'transformers',
            'torch',
            'httpx',
            'httpcore',
            'urllib3',
            'posthog',
            'holo_index',
            'modules',
            'holodae_activity',
            # Suppress agent breadcrumb chatter in CLI output/TTS
            'agent_0102',
            'agent_0102::BREADCRUMB',
            'agent_0102::ARBITRATION',
        ]
        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(quiet_level)
    
    if args.offline:
        os.environ['HOLO_OFFLINE'] = '1'
        os.environ['HOLO_DISABLE_PIP_INSTALL'] = '1'
        os.environ.setdefault('HF_HUB_OFFLINE', '1')
        os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
        # WSP 97: --offline mode should ALWAYS use lexical search to prevent hangs
        os.environ.setdefault('HOLO_SKIP_MODEL', '1')

    fast_search_mode = _is_fast_search_enabled(args)
    if fast_search_mode:
        # Fast mode is retrieval-focused; skip heavyweight embedding model load.
        os.environ.setdefault('HOLO_SKIP_MODEL', '1')

    if args.code_index_report:
        _run_codeindex_report(args.code_index_report)
        return

    run_number = os.getenv('HOLOINDEX_RUN', '1')

    reward_variant = os.getenv('HOLO_REWARD_VARIANT', 'A').upper()
    reward_events: List[Tuple[str, int, str]] = []
    session_points = 0
    telemetry_path: Optional[Path] = None

    def add_reward_event(event: str, points: int, note: str, extra: Optional[Dict[str, Any]] = None) -> None:
        nonlocal session_points, reward_events, telemetry_path
        session_points += points
        reward_events.append((event, points, note))
        if ADVISOR_AVAILABLE and record_advisor_event and telemetry_path and extra:
            payload = {'event': event, 'points': points, 'reward_variant': reward_variant}
            payload.update(extra)
            try:
                record_advisor_event(telemetry_path, payload)
            except Exception:
                pass

    # Pattern Coach is intentionally opt-in (can be verbose and slow)
    pattern_coach = None
    if args.pattern_coach and ADVISOR_AVAILABLE:
        try:
            from holo_index.qwen_advisor.pattern_coach import PatternCoach

            pattern_coach = PatternCoach()
        except Exception as e:
            if verbose:
                safe_print(f"[WARN] Pattern coach unavailable: {e}")

    # Initialize throttler early for all output
    # WSP 97: Handle case when AgenticOutputThrottler unavailable (offline mode)
    if AgenticOutputThrottler is None:
        # Minimal fallback class for offline/fast mode
        class MinimalThrottler:
            def __init__(self):
                self._search_results = None
                self.detected_module = None
                self.detected_dae = None
            def add_section(self, *args, **kwargs):
                pass
            def set_system_state(self, *args, **kwargs):
                pass
            def set_query_context(self, *args, **kwargs):
                pass
            def render_prioritized_output(self, *args, **kwargs):
                return ""
            def __getattr__(self, name):
                # Fallback for any other attributes
                return None
        throttler = MinimalThrottler()
    else:
        throttler = AgenticOutputThrottler()

    # Add onboarding to throttler
    onboarding_text = f"\n[0102] HoloIndex Quickstart (Run {run_number})"
    onboarding_text += "\n  - Refresh indexes with `python holo_index.py --index-all` at the start of a session."
    onboarding_text += "\n  - Running search for: " + (args.search if args.search else "benchmark")
    onboarding_text += "\n  - Add --llm-advisor to receive compliance reminders and TODO checklists."
    onboarding_text += "\n  - Log outcomes in ModLogs/TESTModLogs (WSP 22) and consult FMAS before coding."
    onboarding_text += "\n  - Example queries:"
    onboarding_text += "\n      python holo_index.py --check-module 'youtube_auth'  # Check before coding"
    onboarding_text += "\n      python holo_index.py --search 'pqn cube' --llm-advisor --limit 5"
    onboarding_text += "\n      python holo_index.py --search 'unit test plan' --llm-advisor"
    onboarding_text += "\n      python holo_index.py --search 'navigation schema' --limit 3"
    onboarding_text += "\n      python holo_index.py --init-dae 'YouTube Live'  # Initialize DAE context"
    onboarding_text += "\n  - Documentation: WSP_35_HoloIndex_Qwen_Advisor_Plan.md | docs/QWEN_ADVISOR_IMPLEMENTATION_COMPLETE.md | tests/holo_index/TESTModLog.md"
    onboarding_text += "\n  - Session points summary appears after each run (WSP reward telemetry)."
    if args.pattern_coach and pattern_coach:
        onboarding_text += "\n[INFO] Pattern Coach enabled - watching for vibecoding patterns"
    throttler.add_section('onboarding', onboarding_text, priority=1, tags=['onboarding', 'guidance'])

    # CRITICAL: Unicode compliance reminder for 0102 agents
# Removed noisy Unicode warnings - 0102 doesn't need internal system messages

    # Determine if advisor should run based on environment and args
    advisor = None
    should_run_advisor = False

    if ADVISOR_AVAILABLE and AgentEnvironmentDetector and detector:
        should_run_advisor = detector.should_run_advisor(args)

        # Log detection info if in debug mode
        if os.getenv('HOLOINDEX_DEBUG'):
            env_info = detector.get_environment_info()
            vprint(f"[DEBUG] Environment: {'0102 AGENT' if env_info['is_0102'] else '012 HUMAN'}")
            vprint(f"[DEBUG] Advisor mode: {env_info['advisor_mode']}")
    else:
        # Fallback to old behavior if detection not available
        should_run_advisor = args.llm_advisor

    if should_run_advisor:
        if not ADVISOR_AVAILABLE:
            safe_print('[WARN] Qwen advisor package unavailable; continuing without advisor output.')
        else:
            advisor = QwenAdvisor()
            # Notify user that advisor is active
            if not args.llm_advisor and verbose:
                safe_print('[INFO] Advisor enabled (0102 agent mode detected)')

    if advisor is not None:
        telemetry_path = advisor.config.telemetry_path
    elif ADVISOR_AVAILABLE and QwenAdvisorConfig is not None:
        try:
            telemetry_path = QwenAdvisorConfig.from_env().telemetry_path
        except Exception:
            telemetry_path = None

    # WSP 97: Handle case when HoloIndex is unavailable (--offline, --fast-search, HOLO_SKIP_MODEL=1)
    if HoloIndex is None:
        safe_print("[INFO] HoloIndex unavailable (offline/fast mode) - using lexical search only")
        holo = None
    else:
        holo = HoloIndex(ssd_path=args.ssd, quiet=not verbose)

    def _safe_count(collection) -> int:
        try:
            return collection.count()
        except Exception:
            return 0

    def _write_index_state(source: str) -> None:
        try:
            state_path = Path(args.ssd) / "indexes" / "index_state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "last_indexed_at": datetime.now(timezone.utc).isoformat(),
                "ssd_path": str(Path(args.ssd)),
                "source": source,
                "code_count": holo.get_code_entry_count(),
                "wsp_count": holo.get_wsp_entry_count(),
                "test_count": _safe_count(getattr(holo, "test_collection", None)),
                "skillz_count": _safe_count(getattr(holo, "skill_collection", None)),
            }
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            if verbose:
                safe_print(f"[WARN] Failed to write index state: {e}")

    index_code = args.index_code or args.index or args.index_all
    index_wsp = args.index_wsp or args.index or args.index_all
    index_symbols = args.index_symbols

    indexing_awarded = False
    if index_code:
        start_time = time.time()
        holo.index_code_entries()
        duration = time.time() - start_time

        # Record index refresh in database
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            db.record_index_refresh("code", duration, holo.get_code_entry_count())
        except Exception as e:
            print(f"[WARN] Failed to record index refresh: {e}")

        indexing_awarded = True
        # Auto symbol indexing to keep memory self-maintaining (can disable with HOLO_SYMBOL_AUTO=0)
        auto_symbols = os.getenv("HOLO_SYMBOL_AUTO", "1").lower() in {"1", "true", "yes", "on"}
        if index_symbols or auto_symbols:
            symbol_roots = None
            if args.symbol_roots:
                symbol_roots = [Path(r) for r in args.symbol_roots]
            elif args.module:
                candidate = Path(args.module)
                if not candidate.exists():
                    candidate = Path("modules") / args.module
                symbol_roots = [candidate]
            else:
                env_roots = os.getenv("HOLO_SYMBOL_ROOTS")
                if env_roots:
                    symbol_roots = [Path(r.strip()) for r in env_roots.split(";") if r.strip()]
                else:
                    symbol_roots = [Path("modules")]
            start_time = time.time()
            holo.index_symbol_entries(roots=symbol_roots)
            duration = time.time() - start_time
            safe_print(f"[SYMBOLS] Indexed symbols in {duration:.2f}s")
            indexing_awarded = True
    if index_symbols and not index_code:
        start_time = time.time()
        roots = [Path(r) for r in args.symbol_roots] if args.symbol_roots else None
        holo.index_symbol_entries(roots=roots)
        duration = time.time() - start_time
        safe_print(f"[SYMBOLS] Indexed symbols in {duration:.2f}s")
        indexing_awarded = True
    if index_wsp:
        start_time = time.time()
        wsp_dirs = [Path(p) for p in args.wsp_path] if args.wsp_path else None
        holo.index_wsp_entries(paths=wsp_dirs)
        duration = time.time() - start_time

        # Record WSP index refresh in database
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            db.record_index_refresh("wsp", duration, holo.get_wsp_entry_count())
        except Exception as e:
            print(f"[WARN] Failed to record WSP index refresh: {e}")

        indexing_awarded = True
    
    # Index SKILLz for agent discovery (Qwen/Gemma/UITars)
    index_skills = args.index_skills or args.index_all
    if index_skills:
        start_time = time.time()
        holo.index_skillz_entries()
        duration = time.time() - start_time
        safe_print(f"[SKILLS] Indexed SKILLz in {duration:.2f}s")
        indexing_awarded = True

    # Index CLI entrypoints → AGENT_CLI_CATALOG.md (command rolodex)
    index_cli = getattr(args, 'index_cli', False) or args.index_all
    if index_cli:
        start_time = time.time()
        try:
            from holo_index.skillz.orphan_capability_scanner.executor import OrphanCapabilityScanner
            scanner = OrphanCapabilityScanner(repo_root=project_root)
            result = scanner.scan()

            # Generate AGENT_CLI_CATALOG.md from scan results
            catalog_path = project_root / "holo_index" / "docs" / "AGENT_CLI_CATALOG.md"
            _generate_cli_catalog(result, catalog_path)

            # Generate machine-readable rolodex (dual-write: JSON + SQLite)
            rolodex_path = project_root / "holo_index" / "docs" / "command_rolodex.json"
            _generate_cli_rolodex_json(result, rolodex_path)

            # SQLite for indexed queries (WRESkillsDiscovery integration)
            db_path = project_root / "holo_index" / "docs" / "command_rolodex.db"
            _generate_cli_rolodex_sqlite(result, db_path)

            duration = time.time() - start_time
            safe_print(f"[CLI] Indexed {result.total_cli_entrypoints} CLI entrypoints in {duration:.2f}s")
            safe_print(f"[CLI] WRE-connected: {result.registered_skills}, Orphans: {len(result.orphans)}")
            indexing_awarded = True
        except ImportError as e:
            safe_print(f"[CLI] Skipped - orphan_capability_scanner not available: {e}")
        except Exception as e:
            safe_print(f"[CLI] Error indexing CLI entrypoints: {e}")

    if indexing_awarded:
        _write_index_state("manual_index")
        add_reward_event('index_refresh', 5, 'Refreshed indexes', {'query': args.search or ''})

    last_query = args.search or ''
    search_results = None

    # Check if indexes need automatic refresh (only if not explicitly indexing)
    auto_refreshed = False
    # WSP 97: Skip auto-refresh when holo is None (offline/fast mode)
    if holo is not None and not (index_code or index_wsp or indexing_awarded):
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()

            needs_code_refresh = db.should_refresh_index("code", max_age_hours=1)
            needs_wsp_refresh = db.should_refresh_index("wsp", max_age_hours=1)

            if needs_code_refresh or needs_wsp_refresh:
                vprint("[AUTOMATIC] Index refresh needed (last refresh > 1 hour)")
                vprint(f"[AUTOMATIC] Code index: {'STALE' if needs_code_refresh else 'FRESH'}")
                vprint(f"[AUTOMATIC] WSP index: {'STALE' if needs_wsp_refresh else 'FRESH'}")

                if args.organize_docs:
                    vprint("[DOCDAE] Checking documentation organization...")
                    try:
                        from modules.infrastructure.doc_dae.src.doc_dae import DocDAE
                        dae = DocDAE()

                        analysis = dae.analyze_docs_folder()
                        misplaced_count = analysis['markdown_docs'] + analysis['json_data']

                        if misplaced_count > 0:
                            vprint(f"[DOCDAE] Found {misplaced_count} misplaced files - organizing...")
                            result = dae.run_autonomous_organization(dry_run=False)
                            vprint(f"[DOCDAE] Organized: {result['execution']['moves_completed']} moved, "
                                   f"{result['execution']['archives_completed']} archived")
                        else:
                            vprint("[DOCDAE] Documentation already organized")
                    except Exception as e:
                        safe_print(f"[WARN] DocDAE failed: {e} - continuing with indexing")
                else:
                    vprint("[DOCDAE] Skipping automatic organization (use --organize-docs to enable)")

                # Automatically refresh stale indexes
                if needs_code_refresh:
                    vprint("[AUTO-REFRESH] Refreshing code index...")
                    start_time = time.time()
                    holo.index_code_entries()
                    duration = time.time() - start_time
                    db.record_index_refresh("code", duration, holo.get_code_entry_count())
                    vprint(f"[AUTO-REFRESH] Code index refreshed in {duration:.1f}s")
                    auto_refreshed = True
                if needs_wsp_refresh:
                    vprint("[AUTO-REFRESH] Refreshing WSP index...")
                    start_time = time.time()
                    holo.index_wsp_entries()
                    duration = time.time() - start_time
                    db.record_index_refresh("wsp", duration, holo.get_wsp_entry_count())
                    vprint(f"[AUTO-REFRESH] WSP index refreshed in {duration:.1f}s")
                    auto_refreshed = True
                vprint("[SUCCESS] Automatic index refresh completed")
            else:
                vprint("[FRESH] All indexes are up to date (< 1 hour old)")

        except Exception as e:
            safe_print(f"[WARN] Could not check index freshness: {e}")
            safe_print("[FALLBACK] Manual refresh: python holo_index.py --index-all")
    if auto_refreshed:
        _write_index_state("auto_refresh")

    # Phase 3: Initialize adaptive learning if available
    adaptive_orchestrator = None
    # TEMPORARILY DISABLED: Adaptive learning causing hangs
    # if ADAPTIVE_LEARNING_AVAILABLE:
    #     try:
    #         adaptive_orchestrator = AdaptiveLearningOrchestrator()
    # # Removed: Adaptive Learning init message - internal system info
    #     except Exception as e:
    #         print(f'[WARN] Phase 3: Adaptive Learning initialization failed: {e}')

    # Handle DAE initialization requests
    if args.init_dae:
        print("[DAE] INITIALIZING DAE CONTEXT - HoloIndex DAE Rampup Server")
        print("=" * 70)

        try:
            from holo_index.dae_cube_organizer.dae_cube_organizer import DAECubeOrganizer
            organizer = DAECubeOrganizer()

            # Determine DAE focus
            dae_focus = None if args.init_dae == 'auto' else args.init_dae

            # Get DAE context
            context = organizer.initialize_dae_context(dae_focus)

            # Display DAE identity
            identity = context['dae_identity']
            print(f"[{identity['name']}]")
            print(f"   {identity['description']}")
            print(f"   Orchestrator: {identity['orchestrator']}")
            print(f"   Main.py Reference: {identity['main_py_reference']}")
            print()

            # Display module map
            module_map = context['module_map']
            print("[MODULES] DAE MODULE ARCHITECTURE")
            print("-" * 40)
            print(module_map['ascii_map'])
            print()

            # Display orchestration flow
            flow = context['orchestration_flow']
            print("[FLOW] ORCHESTRATION FLOW")
            print("-" * 40)
            for phase in flow.get('phases', []):
                print(f"   {phase}")
            print(f"   Loop Type: {flow.get('loop_type', 'N/A')}")
            print()

            # Display quick reference
            ref = context['quick_reference']
            print("[REF] QUICK REFERENCE")
            print("-" * 40)
            print(f"   Menu Option: {ref['menu_option']}")
            print(f"   Key Modules: {', '.join(ref['key_modules'])}")
            print(f"   Primary Responsibility: {ref['primary_responsibility']}")
            print()

            # Display rampup guidance
            guidance = context['rampup_guidance']
            print("[GUIDE] 0102 RAMPUP GUIDANCE")
            print("-" * 40)
            print(f"   Focus: {guidance['immediate_focus']}")
            print("   Key Resources:")
            for resource in guidance['key_resources']:
                print(f"     - {resource}")
            print("   Avoid:")
            for pitfall in guidance['avoid_common_pitfalls']:
                print(f"     - {pitfall}")
            print()

            if 'special_notes' in guidance:
                print("[NOTE] DAE-SPECIFIC NOTES")
                print("-" * 40)
                for note in guidance['special_notes']:
                    print(f"   - {note}")
                print()

            print("[COMPLETE] DAE INITIALIZATION COMPLETE")
            print("   You are now aligned with the DAE structure and ready for autonomous operation.")
            print("=" * 70)

        except Exception as e:
            print(f"[U+2741]EDAE initialization failed: {e}")
            import traceback
            traceback.print_exc()

        return  # Exit after DAE initialization

    # --- Compliance/Audit commands (extracted to holo_index/cli/commands/compliance.py) ---
    from holo_index.cli.commands.compliance import (
        handle_wsp88, handle_audit_docs, handle_check_module,
        handle_check_wsp_docs, handle_rollback_ascii, handle_fix_violations,
        handle_docs_file,
    )
    if handle_wsp88(args, safe_print):
        return
    if handle_audit_docs(args, safe_print):
        return
    if handle_check_module(args, holo, safe_print):
        return
    if handle_check_wsp_docs(args, safe_print):
        return
    if handle_rollback_ascii(args, safe_print):
        return
    if handle_fix_violations(args, safe_print):
        return
    if handle_docs_file(args, safe_print, throttler):
        return

    if args.search:
        # Use modular components for search processing
        try:
            if holo is None:
                # WSP 97: Fallback to lexical search when HoloIndex unavailable
                safe_print(f"[OFFLINE] Running lexical search for: {args.search}")
                import re as _re
                from datetime import datetime as _dt
                from pathlib import Path as _Path

                repo_root = _Path(__file__).resolve().parents[1]

                # Reuse the lexical search logic from bundle-json path
                def _tokenize(query: str):
                    return [t for t in _re.findall(r"[a-z0-9_]+", (query or "").lower()) if t]

                def _score_text(tokens, *fields):
                    score = 0.0
                    for tok in tokens:
                        for idx, field in enumerate(fields):
                            if tok in (field or "").lower():
                                score += (2.0 if idx == 0 else 1.0)
                    return score

                # Load NAVIGATION.py NEED_TO
                import ast
                nav_path = repo_root / "NAVIGATION.py"
                need_to = {}
                if nav_path.exists():
                    try:
                        tree = ast.parse(nav_path.read_text(encoding="utf-8-sig", errors="ignore"))
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Assign):
                                for target in node.targets:
                                    if isinstance(target, ast.Name) and target.id == "NEED_TO":
                                        need_to = ast.literal_eval(node.value)
                    except Exception:
                        pass

                tokens = _tokenize(args.search)
                code_hits = []
                for need, location in need_to.items():
                    score = _score_text(tokens, need, location)
                    if score > 0:
                        similarity = min(1.0, score / max(1.0, len(tokens) * 3.0))
                        code_hits.append({
                            "need": need,
                            "location": location,
                            "similarity": f"{similarity*100:.1f}%",
                            "type": "code",
                            "priority": 1,
                        })
                code_hits.sort(key=lambda x: float(x["similarity"].rstrip("%")), reverse=True)
                code_hits = code_hits[:args.limit]

                search_payload = {
                    "code_hits": code_hits,
                    "wsp_hits": [],
                    "code": code_hits,
                    "wsps": [],
                    "metadata": {
                        "query": args.search,
                        "mode": "lexical_offline",
                        "code_count": len(code_hits),
                        "wsp_count": 0,
                    }
                }
                # WSP 97: Offline mode returns results immediately without heavy post-processing
                _render_fast_search_summary(search_payload, limit=args.limit)
                return
            else:
                search_payload = holo.search(args.search, limit=args.limit, doc_type_filter=args.doc_type)
        except Exception as exc:
            safe_print(f"[ERROR] Search failed: {exc}")
            return

        # Process search results for throttler
        results = search_payload
        throttler._search_results = results
        search_results = results

        # Set system state
        total_results = len(results.get('code', [])) + len(results.get('wsps', []))
        if total_results > 0:
            throttler.set_system_state("found")
        else:
            throttler.set_system_state("missing")

        # Set query context
        throttler.set_query_context(args.search, results)

        # Fast mode: retrieval-focused path for low-latency lookups.
        if fast_search_mode:
            _render_fast_search_summary(results, limit=args.limit)
            search_results = results
            if args.llm_advisor and results.get('advisor'):
                add_reward_event('advisor_usage', 3, 'Consulted Qwen advisor guidance', {'query': last_query})
            # Skip heavy post-processing pipeline.
            return

        # P0 FIX: Integrate Gemma root violation monitor alerts
        # Shows real-time root directory violations in HoloIndex output
        if not args.quiet_root_alerts:
            try:
                import asyncio
                from holo_index.monitoring.root_violation_monitor.src.root_violation_monitor import GemmaRootViolationMonitor

                # Run Gemma monitor asynchronously
                async def get_root_violations():
                    monitor = GemmaRootViolationMonitor()
                    return await monitor.scan_root_violations()

                # Execute async monitor (Python 3.10+ compatible)
                try:
                    violations_data = asyncio.run(get_root_violations())
                except RuntimeError:
                    # Event loop already running (rare), skip for this session
                    violations_data = None

                # Add violations to results if found
                if violations_data and violations_data.get('violations_found', 0) > 0:
                    gemma_alert = f"[GEMMA-ALERT] {violations_data['violations_found']} root directory violations detected"
                    if violations_data.get('auto_correctable', 0) > 0:
                        gemma_alert += f" ({violations_data['auto_correctable']} auto-correctable)"

                    # Add to warnings section
                    if 'warnings' not in results:
                        results['warnings'] = []
                    results['warnings'].insert(0, gemma_alert)

                    # Add detailed breakdown to results
                    results['gemma_violations'] = {
                        'total': violations_data['violations_found'],
                        'auto_correctable': violations_data.get('auto_correctable', 0),
                        'categories': violations_data.get('breakdown_by_category', {}),
                        'timestamp': violations_data.get('timestamp', '')
                    }

            except Exception as e:
                # Graceful degradation - don't break search if Gemma monitor fails
                logger.debug(f"[GEMMA-MONITOR] Failed to check root violations: {e}")

        # Run subroutine analysis
        target_module = throttler.detected_module
        subroutine_results = throttler.subroutine_engine.run_intelligent_analysis(args.search, target_module)
        results['intelligent_analysis'] = subroutine_results

        # Advisor processing
        if advisor:
            try:
                context = AdvisorContext(query=args.search, code_hits=results.get('code', []), wsp_hits=results.get('wsps', []))
                advisor_output = advisor.generate_guidance(
                    context,
                    enable_dae_cube_mapping=args.dae_cubes or args.code_index,
                    enable_function_indexing=args.function_index or args.code_index
                )
                results['advisor'] = asdict(advisor_output)

                # Health notices
                advisor_meta = advisor_output.metadata
                health_notices = _perform_health_checks_and_rewards(results, args.search, add_reward_event)

                if advisor_meta and 'violations' in advisor_meta:
                    for violation in advisor_meta.get('violations', []):
                        if 'WSP 87' in violation or 'WSP 49' in violation:
                            health_notices.append(violation)

                if health_notices:
                    results['health_notices'] = health_notices

            except Exception as exc:
                results['advisor_error'] = f'Advisor failed: {exc}'
        else:
            health_notices = _perform_health_checks_and_rewards(results, args.search, add_reward_event)
            if health_notices:
                results['health_notices'] = health_notices

            # [NEW] Pattern Coach Integration (WSP 84)
            if args.pattern_coach and pattern_coach and results:
                try:
                    coach_msg = pattern_coach.analyze_and_coach(
                        query=args.search,
                        search_results=results.get('code', []) + results.get('wsps', []),
                        health_warnings=results.get('health_notices', [])
                    )
                    if coach_msg:
                        safe_print(f"\n[WSP-COACH] {coach_msg}")
                except Exception as e:
                    logger.debug(f"Pattern coach analysis failed: {e}")

        # Pattern analysis
        if advisor:
            try:
                search_history = _get_search_history_for_patterns()
                if search_history:
                    pattern_analysis = advisor.analyze_search_patterns(search_history)
                    if pattern_analysis.get('recommendations'):
                        if 'advisor' not in results:
                            results['advisor'] = {}
                        results['advisor']['pattern_insights'] = pattern_analysis['recommendations'][:3]
            except Exception as e:
                logger.debug(f"Pattern analysis failed: {e}")

        # Memory recording
        _record_thought_to_memory(results, args.search, advisor, add_reward_event)

        # Route through Qwen orchestrator for intent-aware output (OutputComposer)
        orchestrated_output = None
        try:
            from holo_index.qwen_advisor.orchestration.qwen_orchestrator import QwenOrchestrator
            qwen_orch = QwenOrchestrator()
            orchestrated_output = qwen_orch.orchestrate_holoindex_request(args.search, results)
        except Exception as orch_exc:
            logger.debug(f"[ORCHESTRATOR] Fallback to throttler: {orch_exc}")

        if orchestrated_output:
            safe_print(orchestrated_output)
        else:
            # Fallback: delegate rendering to throttler
            throttler.display_results(results)
            final_output = throttler.render_prioritized_output(verbose=args.verbose if hasattr(args, 'verbose') else False)
            safe_print(final_output)

        if args.llm_advisor and results.get('advisor'):
            add_reward_event('advisor_usage', 3, 'Consulted Qwen advisor guidance', {'query': last_query})

    rating = getattr(args, 'advisor_rating', None)
    if rating:
        if not args.llm_advisor:
            print('[WARN] --advisor-rating ignored without --llm-advisor')
        elif advisor is None or not (search_results and search_results.get('advisor')):
            print('[WARN] --advisor-rating ignored because advisor guidance was unavailable')
        else:
            rating_points = 5 if rating == 'useful' else 2
            add_reward_event('advisor_rating', rating_points, f'Advisor rating: {rating}', {
                'query': last_query,
                'rating': rating
            })

    if args.ack_reminders:
        if not (search_results and (search_results.get('advisor') or search_results.get('advisor_error'))):
            print('[WARN] --ack-reminders ignored because advisor guidance was unavailable')
        else:
            add_reward_event('ack_reminders', 1, 'Advisor reminders acknowledged', {
                'query': last_query
            })

    memory_feedback = getattr(args, 'memory_feedback', None)
    if memory_feedback:
        def _parse_memory_feedback(raw: str) -> List[Tuple[str, str]]:
            entries: List[Tuple[str, str]] = []
            for chunk in raw.split(','):
                token = chunk.strip()
                if not token:
                    continue
                if '=' in token:
                    mem_id, rating = token.split('=', 1)
                elif ':' in token:
                    mem_id, rating = token.rsplit(':', 1)
                else:
                    continue
                mem_id = mem_id.strip()
                rating = rating.strip().lower()
                if rating not in {'good', 'noisy', 'missing'}:
                    continue
                entries.append((mem_id, rating))
            return entries

        feedback_query = args.memory_query or args.search or last_query or "unknown"
        notes = args.memory_notes
        entries = _parse_memory_feedback(memory_feedback)
        if not entries:
            safe_print("[WARN] No valid memory feedback entries parsed")
        else:
            try:
                from modules.ai_intelligence.ai_overseer.src.holo_memory_sentinel import HoloMemorySentinel
                sentinel = HoloMemorySentinel(project_root)
                for mem_id, rating in entries:
                    feedback_id = sentinel.record_memory_feedback(feedback_query, mem_id, rating, notes)
                    if feedback_id:
                        safe_print(f"[FEEDBACK] memory {mem_id} -> {rating} ({feedback_id})")
                    else:
                        safe_print(f"[FEEDBACK] memory {mem_id} -> {rating}")
            except Exception as exc:
                safe_print(f"[WARN] Memory feedback failed: {exc}")

    if reward_events:
        print("\n[POINTS] Session Summary:")
        for event, points, note in reward_events:
            sign = '+' if points >= 0 else ''
            print(f'  {sign}{points} {note}')
        print(f'  Total: {session_points} pts (variant {reward_variant})')

    # --- HoloDAE lifecycle (extracted to holo_index/cli/commands/holodae.py) ---
    from holo_index.cli.commands.holodae import handle_holodae_lifecycle
    if handle_holodae_lifecycle(args, safe_print):
        return

    # HoloDAE Commands (inline original — kept per 012 directive, shadowed by dispatch above)
    if args.start_holodae:
        safe_print("[HOLODAE] Starting Autonomous HoloDAE monitoring...")
        try:
            from holo_index.qwen_advisor import start_holodae
            start_holodae()
            safe_print("[HOLODAE] Monitoring started successfully")
        except ImportError as e:
            safe_print(f"[HOLODAE-ERROR] Failed to start: {e}")

    elif args.stop_holodae:
        safe_print("[HOLODAE] Stopping Autonomous HoloDAE monitoring...")
        try:
            from holo_index.qwen_advisor import stop_holodae
            stop_holodae()
            safe_print("[HOLODAE] Monitoring stopped")
        except ImportError as e:
            safe_print(f"[HOLODAE-ERROR] Failed to stop: {e}")

    elif args.holodae_status:
        print("[HOLODAE] Status Report:")
        try:
            from holo_index.qwen_advisor import get_holodae_status
            status = get_holodae_status()
            print(f"  Active: {'Yes' if status['active'] else 'No'}")
            print(f"  Uptime: {status['uptime_minutes']} minutes")
            print(f"  Files Watched: {status['files_watched']}")
            print(f"  Current Module: {status.get('current_module', 'None')}")
            print(f"  Task Pattern: {status['task_pattern']}")
            print(f"  Session Actions: {status['session_actions']}")
            print(f"  Last Activity: {status['last_activity']}")
        except ImportError as e:
            safe_print(f"[HOLODAE-ERROR] Failed to get status: {e}")

    # --- Module linking/queries (extracted to holo_index/cli/commands/modules_cmd.py) ---
    from holo_index.cli.commands.modules_cmd import handle_link_modules, handle_module_queries
    if handle_link_modules(args, safe_print):
        return
    if handle_module_queries(args, safe_print):
        return

    # Handle module linking requests (inline original — kept per 012 directive, shadowed by dispatch above)
    if args.link_modules:
        safe_print("[QWEN] Module Documentation Linker - Autonomous Intelligence")
        safe_print("=" * 65)
        safe_print("Using Qwen advisor to discover and link module documentation...")
        print()  # Empty line for spacing

        coordinator = None
        try:
            from holo_index.qwen_advisor.module_doc_linker import QwenModuleDocLinker
            from holo_index.qwen_advisor.holodae_coordinator import HoloDAECoordinator

            # Initialize Qwen coordinator
            if not args.verbose:
                os.environ.setdefault("HOLO_SILENT", "1")
            coordinator = HoloDAECoordinator()

            # Initialize module doc linker
            from pathlib import Path as PathLib
            repo_root = PathLib(__file__).parent.parent
            linker = QwenModuleDocLinker(repo_root, coordinator)

            if args.module:
                # Link specific module
                safe_print(f"[LINK] Linking module: {args.module}")
                success = linker.link_single_module(
                    args.module,
                    interactive=args.interactive,
                    force=args.force
                )

                if success:
                    safe_print("\n[SUCCESS] Module documentation linked successfully")
                else:
                    safe_print("\n[FAIL] Module linking failed - see errors above")

            else:
                # Link all modules
                safe_print("[LINK] Linking all modules...")
                results = linker.link_all_modules(
                    interactive=args.interactive,
                    force=args.force
                )

                # Display summary
                success_count = sum(1 for v in results.values() if v)
                fail_count = len(results) - success_count

                safe_print(f"\n[SUMMARY] Linking complete:")
                safe_print(f"  - Success: {success_count}/{len(results)} modules")
                if fail_count > 0:
                    safe_print(f"  - Failed: {fail_count} modules")
                    safe_print("\n[FAILED] Failed modules:")
                    for module_name, success in results.items():
                        if not success:
                            safe_print(f"    - {module_name}")

            safe_print("\n" + "=" * 65)
            safe_print("[TIP] Each module now has MODULE_DOC_REGISTRY.json with intelligent document relationships")

        except Exception as e:
            safe_print(f"[ERROR] Module linking failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if coordinator:
                coordinator.stop_monitoring()

        return  # Exit after module linking

    # Handle module documentation queries (database-powered)
    if args.query_modules or args.wsp or args.list_modules:
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()

            if args.wsp:
                # Query modules implementing a specific WSP
                safe_print(f"[QUERY] Modules implementing {args.wsp}")
                safe_print("=" * 65)

                modules = db.get_modules_implementing_wsp(args.wsp)

                if modules:
                    safe_print(f"\n[FOUND] {len(modules)} module(s) implementing {args.wsp}:")
                    for module in modules:
                        safe_print(f"  - {module['module_domain']}/{module['module_name']}")
                        safe_print(f"    Path: {module['module_path']}")
                        safe_print(f"    Last linked: {module['linked_timestamp']}")
                        safe_print("")
                else:
                    safe_print(f"\n[NOT FOUND] No modules found implementing {args.wsp}")

            elif args.list_modules:
                # List all registered modules
                safe_print("[QUERY] All registered modules")
                safe_print("=" * 65)

                modules = db.get_all_modules()

                if modules:
                    safe_print(f"\n[FOUND] {len(modules)} registered module(s):")

                    # Group by domain
                    by_domain = {}
                    for module in modules:
                        domain = module['module_domain']
                        if domain not in by_domain:
                            by_domain[domain] = []
                        by_domain[domain].append(module)

                    for domain in sorted(by_domain.keys()):
                        safe_print(f"\n[{domain.upper()}]")
                        for module in by_domain[domain]:
                            safe_print(f"  - {module['module_name']}")

                            # Get document count
                            docs = db.get_module_documents(module['module_id'])
                            wsps = db.get_module_wsp_implementations(module['module_id'])

                            safe_print(f"    Documents: {len(docs)}, WSP implementations: {len(wsps)}")
                            safe_print(f"    Last linked: {module['linked_timestamp']}")
                else:
                    safe_print("\n[EMPTY] No modules registered yet")
                    safe_print("[TIP] Run: python holo_index.py --link-modules")

            elif args.module:
                # Query specific module documentation
                safe_print(f"[QUERY] Module documentation: {args.module}")
                safe_print("=" * 65)

                module = db.get_module(module_name=args.module)

                if module:
                    safe_print(f"\n[MODULE] {module['module_domain']}/{module['module_name']}")
                    safe_print(f"Path: {module['module_path']}")
                    safe_print(f"Last linked: {module['linked_timestamp']}")

                    # Get documents
                    docs = db.get_module_documents(module['module_id'])
                    safe_print(f"\n[DOCUMENTS] {len(docs)} document(s):")
                    for doc in docs:
                        safe_print(f"  - [{doc['doc_type']}] {doc['title']}")
                        safe_print(f"    {doc['file_path']}")

                    # Get WSP implementations
                    wsps = db.get_module_wsp_implementations(module['module_id'])
                    if wsps:
                        safe_print(f"\n[WSP IMPLEMENTATIONS] {len(wsps)} protocol(s):")
                        safe_print(f"  {', '.join(wsps)}")
                else:
                    safe_print(f"\n[NOT FOUND] Module '{args.module}' not registered")
                    safe_print("[TIP] Run: python holo_index.py --link-modules --module {args.module}")

            safe_print("\n" + "=" * 65)

        except Exception as e:
            safe_print(f"[ERROR] Query failed: {e}")
            import traceback
            traceback.print_exc()

        return  # Exit after query

    if args.benchmark:
        holo.benchmark_ssd()

    # --- HoloDAE features (extracted to holo_index/cli/commands/holodae.py) ---
    from holo_index.cli.commands.holodae import handle_holodae_features
    if handle_holodae_features(args, safe_print, project_root):
        return

    # Handle HoloDAE menu feature requests (inline original — kept per 012 directive, shadowed by dispatch above)
    if args.pattern_coach:
        safe_print("[PATTERN-COACH] Running behavioral vibecoding pattern analysis...")
        try:
            from holo_index.qwen_advisor.pattern_coach import PatternCoach
            coach = PatternCoach()
            # Show recent pattern detections
            safe_print("[PATTERN-COACH] Analysis complete - see coaching messages above")
        except Exception as e:
            safe_print(f"[ERROR] Pattern coach failed: {e}")
        return

    if args.module_analysis:
        safe_print("[MODULE-ANALYSIS] Analyzing modules for duplicates and health issues...")
        try:
            from holo_index.module_health.size_audit import SizeAuditor
            # from holo_index.module_health.structure_audit import StructureAuditor # TODO: Implement StructureAuditor
            
            auditor = SizeAuditor()
            repo_root = Path(__file__).parent.parent
            
            # Audit key directories
            targets = [repo_root / "holo_index", repo_root / "modules"]
            issues_found = 0
            
            for target in targets:
                if target.exists():
                    safe_print(f"\n[AUDIT] Scanning {target.name}...")
                    results = auditor.audit_module(target)
                    for res in results:
                        safe_print(f"  [{res.risk_tier.value.upper()}] {res.path.name}: {res.line_count} lines")
                        safe_print(f"     Guidance: {res.guidance}")
                        issues_found += 1
            
            if issues_found == 0:
                safe_print("\n[SUCCESS] No size violations found.")
            else:
                safe_print(f"\n[SUMMARY] Found {issues_found} files needing attention.")
                
            safe_print("[MODULE-ANALYSIS] Complete")
        except Exception as e:
            safe_print(f"[ERROR] Module analysis failed: {e}")
        return

    if args.health_check:
        safe_print("[HEALTH-CHECK] Running system architecture health analysis...")
        try:
            # Use intelligent subroutine engine
            from holo_index.core import IntelligentSubroutineEngine
            from holo_index.reports.holo_system_check import run_system_check
            engine = IntelligentSubroutineEngine()
            results = engine.run_intelligent_analysis("health check", None)
            safe_print(results.get('summary', '[HEALTH-CHECK] Complete'))
            system_report = run_system_check(project_root)
            wsp_health = system_report.get("wsp_framework_health") or {}
            safe_print(
                "[HEALTH-CHECK][WSP] severity={severity} drift={drift} framework={framework} knowledge={knowledge}".format(
                    severity=wsp_health.get("severity", "unknown"),
                    drift=wsp_health.get("drift_count", 0),
                    framework=wsp_health.get("framework_count", 0),
                    knowledge=wsp_health.get("knowledge_count", 0),
                )
            )
        except Exception as e:
            safe_print(f"[ERROR] Health check failed: {e}")
        return

    if args.performance_metrics:
        safe_print("[PERFORMANCE] HoloDAE Effectiveness & Performance Metrics")
        safe_print("=" * 65)
        try:
            from holo_index.qwen_advisor.telemetry import get_performance_summary
            summary = get_performance_summary()
            safe_print(summary)
        except Exception as e:
            safe_print(f"[ERROR] Performance metrics failed: {e}")
        return

    if args.system_check:
        safe_print("[SYSTEM-CHECK] Verifying Holo CLI wiring...")
        try:
            from holo_index.reports.holo_system_check import run_system_check, write_system_check_report
            report = run_system_check(project_root)
            output_dir = Path(__file__).parent / "reports"
            output_path = write_system_check_report(report, output_dir)
            summary = report.get("summary") or {}
            wsp_health = report.get("wsp_framework_health") or {}
            safe_print(
                "[SYSTEM-CHECK] Summary: ok {ok}, in_dev {in_dev}, missing {missing}, unwired {unwired}".format(
                    ok=summary.get("ok", 0),
                    in_dev=summary.get("in_dev", 0),
                    missing=summary.get("missing", 0),
                    unwired=summary.get("unwired", 0),
                )
            )
            safe_print(
                "[SYSTEM-CHECK][WSP] severity={severity} drift={drift} framework={framework} knowledge={knowledge}".format(
                    severity=wsp_health.get("severity", "unknown"),
                    drift=wsp_health.get("drift_count", 0),
                    framework=wsp_health.get("framework_count", 0),
                    knowledge=wsp_health.get("knowledge_count", 0),
                )
            )
            safe_print(f"[SYSTEM-CHECK] Report saved -> {output_path}")
        except Exception as e:
            safe_print(f"[ERROR] System check failed: {e}")
        return

    if args.slow_mode:
        safe_print("[SLOW-MODE] Enabling recursive feedback with 2-3s delays...")
        safe_print("[SLOW-MODE] This mode is for training/observation - not production")
        # Set environment variable for slow mode
        os.environ['HOLODAE_SLOW_MODE'] = '1'
        safe_print("[SLOW-MODE] Enabled - all HoloDAE operations will use delays")
        return

    if args.pattern_memory:
        safe_print("[PATTERN-MEMORY] Learned Intervention Patterns")
        safe_print("=" * 65)
        try:
            from modules.infrastructure.wre_core.wre_master_orchestrator import PatternMemory
            memory = PatternMemory.get()
            safe_print(str(memory))
        except Exception as e:
            safe_print(f"[ERROR] Pattern memory access failed: {e}")
        return

    if args.mcp_hooks:
        safe_print("[MCP-HOOKS] Connector Health & Registration Status")
        safe_print("=" * 65)
        try:
            from modules.communication.livechat.src.mcp_youtube_integration import MCPYouTubeIntegration
            integration = MCPYouTubeIntegration()
            status = integration.connect_all()
            safe_print(f"MCP Status: {status}")
        except Exception as e:
            safe_print(f"[ERROR] MCP hooks inspection failed: {e}")
        return

    if args.mcp_log:
        safe_print("[MCP-LOG] Recent MCP Tool Activity")
        safe_print("=" * 65)
        try:
            # Show recent MCP action log
            safe_print("[MCP-LOG] Feature in development - see Qwen Daemon logs")
        except Exception as e:
            safe_print(f"[ERROR] MCP log access failed: {e}")
        return

    if args.thought_log:
        safe_print("[THOUGHT-LOG] Chain-of-Thought Breadcrumb Trail")
        safe_print("=" * 65)
        try:
            from holo_index.adaptive_learning.breadcrumb_tracer import BreadcrumbTracer
            tracer = BreadcrumbTracer()
            summary = tracer.summarize_session()
            
            safe_print(f"Session ID: {summary['session_id']}")
            safe_print(f"Timestamp: {summary['timestamp']}")
            safe_print(f"Total Actions: {summary['total_actions']}")
            
            if summary['searches']:
                safe_print("\n[SEARCHES]")
                for s in summary['searches']:
                    safe_print(f"  - {s['query']} ({s['results']} results)")
            
            if summary['actions']:
                safe_print("\n[ACTIONS]")
                for a in summary['actions']:
                    safe_print(f"  - {a['what']} -> {a['target']} ({a['result']})")
                    
            if summary['learnings']:
                safe_print("\n[LEARNINGS]")
                for l in summary['learnings']:
                    safe_print(f"  - {l}")
                    
            safe_print("\n[THOUGHT-LOG] Complete")
        except Exception as e:
            safe_print(f"[ERROR] Thought log access failed: {e}")
        return

    if args.monitor_work:
        safe_print("[WORK-MONITOR] Starting work completion monitoring...")
        try:
            from modules.ai_intelligence.work_completion_publisher.src.monitoring_service import MonitoringService
            service = MonitoringService()
            import asyncio
            asyncio.run(service.start())
        except Exception as e:
            safe_print(f"[ERROR] Work monitoring failed: {e}")
        return

    if not any([index_code, index_wsp, args.search, args.benchmark, args.start_holodae, args.stop_holodae, args.holodae_status, args.link_modules,
                args.pattern_coach, args.module_analysis, args.health_check, args.performance_metrics, args.system_check, args.slow_mode,
                args.pattern_memory, args.mcp_hooks, args.mcp_log, args.thought_log, args.monitor_work, args.memory_feedback]):
        safe_print("\n[USAGE] Usage:")
        safe_print("  python holo_index.py --index-all             # Index NAVIGATION + WSP")
        safe_print("  python holo_index.py --index-code            # Index NAVIGATION only")
        safe_print("  python holo_index.py --index-wsp             # Index WSP docs")
        safe_print("  python holo_index.py --index-skillz          # Index SKILLz wardrobe")
        safe_print("  python holo_index.py --check-module 'youtube_auth'  # WSP compliance check")
        safe_print("  python holo_index.py --search 'query'        # Search code + WSP guidance")
        safe_print("  python holo_index.py --search 'query' --limit 3")
        safe_print("  python holo_index.py --search 'query' --llm-advisor  # Add Qwen advisor guidance")
        safe_print("  python holo_index.py --index-symbols --symbol-roots modules/ai_intelligence/pqn_alignment")
        safe_print("  python holo_index.py --link-modules          # Link all module documentation (Qwen)")
        safe_print("  python holo_index.py --link-modules --module liberty_alert  # Link one module")
        safe_print("  python holo_index.py --link-modules --interactive  # Interactive mode")
        safe_print("  python holo_index.py --list-modules          # List all registered modules (DB)")
        safe_print("  python holo_index.py --wsp 'WSP 90'          # Find modules implementing WSP 90 (DB)")
        safe_print("  python holo_index.py --query-modules --module liberty_alert  # Query module docs (DB)")
        safe_print("  python holo_index.py --start-holodae         # Start autonomous HoloDAE monitoring")
        safe_print("  python holo_index.py --holodae-status        # Check HoloDAE status")
        safe_print("  python holo_index.py --system-check          # Verify CLI wiring and emit report")
        safe_print("  python holo_index.py --benchmark             # Test SSD performance")
        safe_print("  python holo_index.py --organize-docs --index-all   # Refresh indexes and allow DocDAE auto-organization")

if __name__ == "__main__":
    main()
