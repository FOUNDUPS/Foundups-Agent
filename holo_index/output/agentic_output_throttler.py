# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import io


"""Agentic Output Throttler - WSP 87 Compliant Output Management

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

This module provides intelligent output prioritization and organization
for 0102 agent consumption, preventing information overload.

WSP Compliance: WSP 87 (Size Limits), WSP 49 (Module Structure), WSP 72 (Block Independence)
"""

import re
import os
import json
import threading
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.intelligent_subroutine_engine import IntelligentSubroutineEngine

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parent / "holo_output_history.jsonl"
SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "qwen_holo_output_skill" / "SKILL.md"


class AgenticOutputThrottler:
    """
    FIRST PRINCIPLES: Intelligently throttles and organizes output for 0102 efficiency

    Instead of massive verbose output, provides concise, prioritized information
    that 0102 can act upon immediately.

    WSP Compliance: WSP 75 (Token-Based Development), WSP 80 (Cube-Level Orchestration)
    """

    def __init__(self):
        self.output_sections = []
        self.query_context = ""
        self.detected_module = None
        self.subroutine_engine = IntelligentSubroutineEngine()
        self.system_state = "unknown"  # "error", "found", "missing"
        self.last_error = None
        self.max_sections = 3  # FIRST PRINCIPLES: Limit to prevent overload

        # Agent detection: Supports 0102 (Claude), qwen (1.5B), gemma (270M)
        raw_agent_id = (os.getenv("HOLO_ID_0102") or os.getenv("0102_HOLO_ID") or "0102").strip()
        self.agent_id = raw_agent_id if raw_agent_id else "0102"

        self.skill_manifest = self._load_skill_manifest()
        self.history_path = self._resolve_history_path()
        self.repo_root = Path(__file__).resolve().parents[2]
        self._memory_bundle: Optional[Dict[str, Any]] = None

    def set_query_context(self, query: str, search_results=None):
        """Set current query for relevance scoring and detect target module."""
        self.query_context = query.lower()
        self._search_results = search_results or {}  # Store full search results for decision framework
        self.detected_module = self._detect_target_module(query, search_results)

        # FIRST PRINCIPLES: Detect potential truncation and warn user
        if search_results:
            code_count = len(search_results.get('code', []))
            wsp_count = len(search_results.get('wsps', []))
            total_count = code_count + wsp_count
            if total_count > 20:
                self.add_section('warnings', f'[TRUNCATION WARNING] {total_count} results may exceed console capacity. Use --limit 3 to prevent truncation.', priority=1, tags=['warning', 'truncation'])

    def set_system_state(self, state: str, error: Exception = None):
        """
        Set the current system state for output rendering.

        Args:
            state: "error", "found", "missing"
            error: Exception object if state is "error"
        """
        self.system_state = state
        self.last_error = error

    def _determine_system_state(self):
        """Auto-determine system state based on current context."""
        if self.system_state != "unknown":
            return self.system_state

        # Auto-detect based on available data
        if self.last_error:
            return "error"

        search_results = getattr(self, '_search_results', {})
        total_results = len(search_results.get('code', [])) + len(search_results.get('wsps', []))

        if total_results > 0:
            return "found"
        else:
            return "missing"

    def _detect_target_module(self, query: str, search_results=None):
        """Detect which module the user is likely working on based on query and results."""
        query_lower = query.lower()

        # Direct module mentions (normalized for spaces/underscores)
        module_keywords = {
            'stream resolver': 'platform_integration/stream_resolver',
            'stream_resolver': 'platform_integration/stream_resolver',
            'auto moderator': 'communication/livechat',
            'auto_moderator': 'communication/livechat',
            'social media': 'platform_integration/social_media_orchestrator',
            'social_media': 'platform_integration/social_media_orchestrator',
            'youtube': 'platform_integration/youtube_auth',
            'livechat': 'communication/livechat',
            'gamification': 'gamification/whack_a_magat',
            'wre': 'infrastructure/wre_core',
            'pqn': 'ai_intelligence/pqn_alignment',
            'module creator': 'development/module_creator',
            'module_creator': 'development/module_creator',
            'dae cube': 'holo_index/dae_cube_organizer',
            'dae_cube': 'holo_index/dae_cube_organizer',
            'banter engine': 'ai_intelligence/banter_engine',
            'banter_engine': 'ai_intelligence/banter_engine'
        }

        for keyword, module in module_keywords.items():
            if keyword in query_lower:
                return module

        # Check search results for module patterns
        if search_results and 'code' in search_results:
            for hit in search_results['code'][:3]:  # Check top 3 results
                location = hit.get('location', '')
                if 'modules/' in location:
                    # Extract module path from location
                    module_match = re.search(r'modules/([^/]+/[^/]+)', location)
                    if module_match:
                        return module_match.group(1)

        return None

    def add_section(self, section_type: str, content: str, priority: int = 5, tags: List[str] = None):
        """Add output section with priority scoring (1=highest, 10=lowest)."""
        if tags is None:
            tags = []

        # Boost priority for query-relevant content
        relevance_boost = 0
        if any(tag in self.query_context for tag in tags):
            relevance_boost = -2  # Higher priority

        self.output_sections.append({
            'type': section_type,
            'content': content,
            'priority': max(1, priority + relevance_boost),
            'tags': tags
        })

    def _infer_module_from_hits(self, code_hits: List[Dict[str, Any]]) -> Optional[str]:
        for hit in code_hits[:3]:
            location = hit.get('location') or hit.get('path') or ''
            normalized = location.replace('\\', '/')
            module_match = re.search(r'modules/([^/]+/[^/]+)', normalized)
            if module_match:
                return module_match.group(1)
        return None

    def _extract_doc_summary(self, path: Path, fallback: str) -> str:
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    stripped = line.strip()
                    if stripped:
                        return self._clean_summary(stripped.lstrip('# ').strip(), max_len=120)
        except Exception:
            pass
        return self._clean_summary(fallback, max_len=120)

    def _clean_summary(self, text: str, max_len: int = 120) -> str:
        cleaned = re.sub(r"[`#*_>]", "", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > max_len:
            return cleaned[: max_len - 3] + "..."
        return cleaned

    def _compute_memory_value(self, doc_type: str, pointers: List[str], wsp: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute Memory Value Score (MVS) from existing WSP signals:
        - Base score derived from doc_type priority (mirrors core HoloIndex priority map)
        - Entry-point boosts for system boot/orchestration docs (e.g., main.py)
        - Foundational WSP boosts (WSP_00, WSP_CORE, WSP_MASTER_INDEX)
        """
        priority_map = {
            "wsp_protocol": 10,
            "wsp": 10,
            "interface": 9,
            "module_readme": 8,
            "documentation": 7,
            "roadmap": 6,
            "modlog": 5,
            "readme": 4,
            "test_documentation": 3,
            "other": 2,
        }

        normalized_type = (doc_type or "other").lower()
        score = float(priority_map.get(normalized_type, 2))
        normalized_pointers = [(p or "").replace("\\", "/") for p in (pointers or [])]

        # Entry-point boost (main.py and orchestrator roots)
        if any("/main.py" in p or p.endswith("main.py") or "main.py:" in p for p in normalized_pointers):
            score += 2.0

        # Foundational WSP boost
        if any(
            token in p
            for p in normalized_pointers
            for token in ("WSP_00", "WSP_CORE", "WSP_MASTER_INDEX")
        ):
            score += 2.0
        if wsp and str(wsp).strip().upper() in {"WSP 00", "WSP CORE", "WSP MASTER INDEX"}:
            score += 1.0

        score = max(1.0, min(score, 10.0))
        if score >= 8.0:
            band = "high"
        elif score >= 5.0:
            band = "medium"
        else:
            band = "low"

        return {"score": round(score, 1), "band": band}

    def _make_memory_card(
        self,
        module: str,
        doc_type: str,
        summary: str,
        pointers: List[str],
        wsp: Optional[str] = None,
        trust: float = 0.8,
        salience: float = 0.7,
    ) -> Dict[str, Any]:
        raw = f"{module}|{doc_type}|{wsp or ''}|{summary}|{pointers[:1]}"
        card_id = "mem:" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:12]
        memory_value = self._compute_memory_value(doc_type, pointers, wsp)
        return {
            "id": card_id,
            "module": module,
            "doc_type": doc_type,
            "wsp": wsp,
            "intent": "memory",
            "summary": summary,
            "pointers": pointers,
            "memory_value": memory_value,
            "salience": round(salience, 2),
            "trust": round(trust, 2),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }

    def _build_memory_bundle(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        wsp_cards: List[Dict[str, Any]] = []
        doc_cards: List[Dict[str, Any]] = []
        skill_cards: List[Dict[str, Any]] = []
        reason = ""

        code_hits = search_results.get('code', [])
        wsp_hits = search_results.get('wsps', [])
        skill_hits = search_results.get('skills') or search_results.get('skill_hits') or []
        module = self.detected_module or self._infer_module_from_hits(code_hits)

        if wsp_hits:
            for hit in wsp_hits[:2]:
                raw_summary = (hit.get('summary') or hit.get('content') or '').replace('\n', ' ').strip()
                summary = self._clean_summary(raw_summary, max_len=120)
                pointer = hit.get('path') or hit.get('location')
                if pointer:
                    pointer = pointer.replace('\\', '/')
                wsp_cards.append(self._make_memory_card(
                    module=module or "unknown",
                    doc_type="wsp",
                    wsp=hit.get('wsp') or "WSP",
                    summary=summary or "WSP guidance available for this query.",
                    pointers=[pointer] if pointer else [],
                    trust=0.95,
                    salience=0.8,
                ))

        if module:
            parts = module.split('/', 1)
            if len(parts) == 2:
                module_root = self.repo_root / "modules" / parts[0] / parts[1]
                doc_specs = [
                    ("INTERFACE.md", "interface", 0.9),
                    ("README.md", "readme", 0.9),
                    ("ModLog.md", "modlog", 0.7),
                ]
                for filename, doc_type, trust in doc_specs:
                    path = module_root / filename
                    if path.exists():
                        summary = self._extract_doc_summary(
                            path,
                            f"See {filename} for module context."
                        )
                        pointer = str(path.relative_to(self.repo_root)).replace('\\', '/')
                        doc_cards.append(self._make_memory_card(
                            module=module,
                            doc_type=doc_type,
                            summary=summary,
                            pointers=[pointer],
                            trust=trust,
                            salience=0.7,
                        ))

        if skill_hits and self._should_include_skillz():
            for hit in skill_hits[:1]:
                summary = self._clean_summary(
                    hit.get('description') or hit.get('skill_name') or "Skillz guidance available.",
                    max_len=120,
                )
                pointer = hit.get('path')
                if pointer:
                    pointer = str(pointer).replace('\\', '/')
                skill_cards.append(self._make_memory_card(
                    module="skillz",
                    doc_type="skillz",
                    summary=summary,
                    pointers=[pointer] if pointer else [],
                    trust=0.9,
                    salience=0.8,
                ))

        cards = []
        if skill_cards:
            cards.extend(skill_cards[:1])
        if wsp_cards:
            cards.append(wsp_cards[0])
        if doc_cards:
            cards.extend(doc_cards[:2])
        if wsp_cards:
            cards.extend(wsp_cards[1:])
        if doc_cards:
            cards.extend(doc_cards[2:])
        if not cards:
            reason = "no memory sources found (no WSP hits, no module docs)"

        return {
            "cards": cards[:5],
            "reason": reason,
        }

    def _should_include_skillz(self) -> bool:
        query = self.query_context or ""
        return any(token in query for token in ["skill", "skillz", "wardrobe", "mps"])

    def _format_memory_bundle(self, bundle: Dict[str, Any], max_cards: int, include_metrics: bool = False) -> List[str]:
        cards = bundle.get("cards") or []
        reason = bundle.get("reason") or ""
        output_lines = ["[MEMORY]"]

        if not cards:
            output_lines.append("- id: mem:none")
            output_lines.append(f"  summary: \"{reason or 'memory bundle empty'}\"")
            return output_lines

        for card in cards[:max_cards]:
            output_lines.append(f"- id: {card.get('id')}")
            output_lines.append(f"  module: {card.get('module')}")
            output_lines.append(f"  doc_type: {card.get('doc_type')}")
            if card.get('wsp'):
                output_lines.append(f"  wsp: {card.get('wsp')}")
            memory_value = card.get("memory_value")
            if not memory_value:
                memory_value = self._compute_memory_value(
                    card.get("doc_type"),
                    card.get("pointers") or [],
                    card.get("wsp"),
                )
            if isinstance(memory_value, dict):
                output_lines.append(
                    f"  memory_value: {memory_value.get('score')} ({memory_value.get('band')})"
                )
            output_lines.append(f"  intent: {card.get('intent')}")
            output_lines.append(f"  summary: \"{card.get('summary', '')}\"")
            pointers = card.get("pointers") or []
            if pointers:
                output_lines.append("  pointers:")
                for pointer in pointers:
                    output_lines.append(f"    - {pointer}")
            if include_metrics:
                output_lines.append(f"  salience: {card.get('salience')}")
                output_lines.append(f"  trust: {card.get('trust')}")
                output_lines.append(f"  last_seen: {card.get('last_seen')}")

        return output_lines

    def _enforce_section_limit(self, verbose: bool) -> None:
        """Ensure only the top priority sections are retained for default output."""
        if verbose or len(self.output_sections) <= self.max_sections:
            return

        prioritized = [
            (section.get('priority', 5), idx, section)
            for idx, section in enumerate(self.output_sections)
        ]
        prioritized.sort(key=lambda item: (item[0], item[1]))
        kept = [item[2] for item in prioritized[:self.max_sections]]
        dropped_count = len(prioritized) - len(kept)

        if dropped_count and kept:
            kept[-1]['content'] += f"\n[INFO] {dropped_count} additional sections hidden; re-run with --verbose to view all details."

        self.output_sections = kept

    def render_prioritized_output(self, verbose: bool = False) -> str:
        """Render PERFECT output for 0102 decision-making using tri-state architecture.

        Agent-aware rendering:
        - 0102 (Claude Sonnet, 200K context): Full verbose documentation (200 tokens)
        - qwen (1.5B model, 32K context): Concise JSON with action items (50 tokens)
        - gemma (270M model, 8K context): Minimal classification (10 tokens)
        """
        self._enforce_section_limit(verbose)
        state = self._determine_system_state()

        if state == "error":
            content = self._render_error_state()
        elif state == "found":
            content = self._render_found_state(verbose)
        elif state == "missing":
            content = self._render_missing_state()
        else:
            # Fallback to auto-detection
            content = self._render_auto_state(verbose)

        # REAL-TIME UNICODE FILTERING - BEFORE agent formatting (WSP 90)
        # This ensures ALL agents (0102, qwen, gemma) get clean ASCII output
        filtered_content, stats = self.filter_unicode_violations(content)

        # Log if fixes were applied (for learning)
        if stats.get('replaced', 0) > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"[UNICODE-FIX] Replaced {stats['replaced']} emojis for agent={self.agent_id}")

        # Format output based on calling agent's capabilities (after cleaning)
        formatted_output = self._format_for_agent(filtered_content, state)

        # Persist output history for Gemma/Qwen pattern analysis
        self._record_output_history(state, formatted_output, filtered_content, verbose)

        return formatted_output

    def _render_error_state(self) -> str:
        """State 1: [ERROR] System Error - Show ONLY the error, suppress all noise."""
        output_lines = []

        output_lines.append("[ERROR] [SYSTEM FAILURE] Fatal error in analysis pipeline")
        output_lines.append("")

        if self.last_error:
            output_lines.append(f"[ERROR] {type(self.last_error).__name__}: {str(self.last_error)}")
            # Add traceback if available
            import traceback
            tb_lines = traceback.format_exception(type(self.last_error), self.last_error, self.last_error.__traceback__)
            # Show only the most relevant part of traceback
            for line in tb_lines[-3:]:  # Last 3 lines usually contain the key info
                if line.strip():
                    output_lines.append(f"[TRACEBACK] {line.rstrip()}")
        else:
            output_lines.append("[ERROR] Unknown system error occurred")

        output_lines.append("")
        output_lines.append("[ACTION] Fix the system error before proceeding with any development tasks")
        output_lines.append("[NEXT] Run diagnostic queries or fix the identified issue")

        return "\n".join(output_lines)

    def _render_found_state(self, verbose: bool = False) -> str:
        """State 2: [GREEN] Solution Found - Show clean results, suppress noise for 0102."""
        output_lines = []
        search_results = getattr(self, '_search_results', {})

        # Extract module information for 0102 context
        code_results = search_results.get('code', [])
        wsp_results = search_results.get('wsps', [])

        # Count modules involved
        modules_found = set()
        for hit in code_results[:5]:  # Check top 5 for module diversity
            location = hit.get('location', '') or hit.get('path', '')
            normalized = location.replace('\\', '/')
            module_match = re.search(r'modules/([^/]+/[^/]+)', normalized)
            if module_match:
                modules_found.add(module_match.group(1))

        memory_bundle = self._memory_bundle or self._build_memory_bundle(search_results)
        self._memory_bundle = memory_bundle
        output_lines.extend(self._format_memory_bundle(memory_bundle, max_cards=5 if verbose else 3))
        output_lines.append("")

        output_lines.append("[GREEN] [SOLUTION FOUND] Existing functionality discovered")
        output_lines.append(f"[MODULES] Found implementations across {len(modules_found)} modules: {', '.join(sorted(modules_found))}")
        output_lines.append("")

        # Only show detailed results if verbose=True (WSP 87 - prevent noisy output)
        if verbose:
            # Show top code results with more detail for 0102 agents
            if code_results:
                output_lines.append("[CODE RESULTS] Top implementations:")
                for i, hit in enumerate(code_results[:3], 1):  # Top 3
                    location = hit.get('path') or hit.get('location', 'Unknown')
                    similarity = hit.get('similarity', 'N/A')
                    line = hit.get('line')
                    preview = hit.get('preview') or hit.get('content', '')
                    preview_inline = preview.replace('\n', ' ').strip()
                    if len(preview_inline) > 120:
                        preview_inline = preview_inline[:117] + '...'
                    header = f"  {i}. {location}"
                    if line:
                        header += f":{line}"
                    output_lines.append(header)
                    output_lines.append(f"     Match: {similarity} | Preview: {preview_inline or '[No preview]'}")
                output_lines.append("")

            # Show top WSP guidance with more context
            if wsp_results:
                output_lines.append("[WSP GUIDANCE] Protocol references:")
                for i, hit in enumerate(wsp_results[:2], 1):  # Top 2
                    wsp_id = hit.get('wsp', 'Unknown')
                    title = hit.get('title', 'Unknown')
                    similarity = hit.get('similarity', 'N/A')
                    content_preview = hit.get('content', '')[:80].replace('\n', ' ') + '...' if len(hit.get('content', '')) > 80 else hit.get('content', '')
                    output_lines.append(f"  {i}. {wsp_id}: {title}")
                    output_lines.append(f"     Match: {similarity} | Guidance: {content_preview}")
                output_lines.append("")

            output_lines.append("[ACTION] ENHANCE/REFACTOR existing code based on findings")
            output_lines.append("[NEXT] Read the discovered files and WSP documentation")
        else:
            # Clean summary for 0102 (WSP 87 - prevent information overload)
            total_code = len(code_results)
            total_wsp = len(wsp_results)
            summary_preview = ""
            if code_results:
                first_preview = code_results[0].get('preview') or ''
                summary_preview = first_preview.replace('\n', ' ').strip()
                if len(summary_preview) > 120:
                    summary_preview = summary_preview[:117] + '...'
            output_lines.append(f"[RESULTS] {total_code} code hits, {total_wsp} WSP docs found")
            if summary_preview:
                output_lines.append(f"[PREVIEW] {summary_preview}")
            output_lines.append("[ACTION] Use --verbose for detailed results and recommendations")

        return "\n".join(output_lines)

    def _render_missing_state(self) -> str:
        """State 3: [YELLOW] No Solution Found - Allow creation, show guidance."""
        output_lines = []
        query = getattr(self, 'query_context', 'unknown query')

        memory_bundle = self._memory_bundle or self._build_memory_bundle(getattr(self, '_search_results', {}) or {})
        self._memory_bundle = memory_bundle
        output_lines.extend(self._format_memory_bundle(memory_bundle, max_cards=3))
        output_lines.append("")

        output_lines.append("[YELLOW] [NO SOLUTION FOUND] No existing implementation discovered")
        output_lines.append("")
        output_lines.append(f"[MISSING] Query '{query}' found no relevant existing code")
        output_lines.append("")
        output_lines.append("[ACTION] CREATE new module following WSP guidelines")
        output_lines.append("[NEXT] Follow WSP 50 pre-action verification before creating")
        output_lines.append("")
        output_lines.append("[WSP GUIDANCE] Creation Requirements:")
        output_lines.append("  - WSP 84: Verify no similar functionality exists")
        output_lines.append("  - WSP 49: Follow module directory structure")
        output_lines.append("  - WSP 22: Create README.md and ModLog.md")
        output_lines.append("  - WSP 11: Define clear public API in INTERFACE.md")

        return "\n".join(output_lines)

    def _render_auto_state(self, verbose: bool = False) -> str:
        """Fallback auto-detection when state is unknown."""
        search_results = getattr(self, '_search_results', {})
        total_results = len(search_results.get('code', [])) + len(search_results.get('wsps', []))

        if total_results > 0:
            return self._render_found_state(verbose)
        else:
            return self._render_missing_state()

    def _format_for_agent(self, content: str, state: str) -> str:
        """Format output based on calling agent's capabilities.

        Agent Token Budgets:
        - 0102: 200K context -> Full verbose output (200 tokens)
        - qwen: 32K context -> Concise JSON (50 tokens)
        - gemma: 8K context -> Minimal classification (10 tokens)

        WSP Compliance: WSP 75 (Token-Based Development), Universal WSP Pattern
        """
        if self.agent_id == "gemma":
            return self._format_gemma(content, state)
        elif self.agent_id == "qwen":
            return self._format_qwen(content, state)
        else:  # 0102 or unknown
            return content  # Keep full verbose output for 0102

    def _format_gemma(self, content: str, state: str) -> str:
        """Gemma formatter: Minimal binary classifications (10 tokens).

        Gemma (270M model, 8K context): Function-specific classifications.
        Output: Binary state + minimal metadata.
        """
        if state == "error":
            return "ERROR|retry_needed|check_logs"
        elif state == "found":
            module = self.detected_module or "unknown"
            return f"FOUND|{module}|enhance_existing|confidence_high"
        else:  # missing
            return "MISSING|create_needed|follow_wsp49|confirm_first"

    def _format_qwen(self, content: str, state: str) -> str:
        """Qwen formatter: Concise JSON with action items (50 tokens).

        Qwen (1.5B model, 32K context): Coordination and orchestration focus.
        Output: Structured JSON with WSP guidance and next actions.
        """
        search_results = getattr(self, '_search_results', {})
        code_count = len(search_results.get('code', []))
        wsp_count = len(search_results.get('wsps', []))

        result = {
            "state": state,
            "module": self.detected_module,
            "results": {"code": code_count, "wsps": wsp_count},
            "action": self._get_qwen_action(state),
            "wsps": self._get_relevant_wsps(state),
            "priority": "high" if state == "error" else "medium"
        }

        return json.dumps(result, indent=2)

    def _get_qwen_action(self, state: str) -> str:
        """Get recommended action for Qwen based on state."""
        if state == "error":
            return "fix_error_then_retry"
        elif state == "found":
            return "read_docs_then_enhance"
        else:  # missing
            return "verify_missing_then_create"

    def _get_relevant_wsps(self, state: str) -> List[str]:
        """Get relevant WSPs for current state."""
        if state == "error":
            return ["WSP_50", "WSP_64"]  # Pre-action verification + violation prevention
        elif state == "found":
            return ["WSP_50", "WSP_84", "WSP_22"]  # Verify + enhance existing + update ModLog
        else:  # missing
            return ["WSP_49", "WSP_3", "WSP_22"]  # Module structure + enterprise domain + ModLog

    def filter_unicode_violations(self, content: str) -> tuple:
        """
        Real-time Unicode violation detection and fixing for multi-agent output.

        Filters emojis from HoloIndex output BEFORE agent formatting to ensure:
        - 0102 (Claude): cp932 console compatibility
        - Qwen (1.5B): Valid JSON parsing (no Unicode breaks)
        - Gemma (270M): Pure ASCII classification (no pattern noise)

        Reuses existing patterns from qwen_advisor/patterns/unicode_violations.json

        Args:
            content: Output content to filter

        Returns:
            (filtered_content, stats) - Clean ASCII content + fix statistics

        WSP Compliance: WSP 90 (UTF-8 Enforcement), WSP 84 (Enhance Existing)
        """
        try:
            # Load emoji patterns from existing unicode_violations.json
            from pathlib import Path
            import json

            patterns_file = Path(__file__).parent.parent / "qwen_advisor" / "patterns" / "unicode_violations.json"

            if not patterns_file.exists():
                # Fallback: No patterns available, return original
                return content, {"violations": 0, "replaced": 0, "error": "patterns_file_missing"}

            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)

            emoji_replacements = patterns.get('emoji_replacements', {})

            # Quick check: any emojis present?
            violations_detected = any(emoji in content for emoji in emoji_replacements.keys())

            if not violations_detected:
                return content, {"violations": 0, "replaced": 0}

            # Apply replacements
            filtered_content = content
            replacements = 0

            for emoji, replacement in emoji_replacements.items():
                if emoji in filtered_content:
                    filtered_content = filtered_content.replace(emoji, replacement)
                    replacements += 1

            return filtered_content, {
                "violations": len([e for e in emoji_replacements.keys() if e in content]),
                "replaced": replacements,
                "agent": self.agent_id
            }

        except Exception as e:
            # On error, return original content (fail-safe)
            return content, {"violations": 0, "replaced": 0, "error": str(e)}

    def _is_wsp_relevant_to_module(self, wsp_hit: Dict[str, Any], target_module: str = None) -> bool:
        """Determine if WSP guidance is relevant to the target module."""
        if not target_module:
            return True  # Show all if no specific module detected

        wsp_title = wsp_hit.get('title', '').lower()
        wsp_number = wsp_hit.get('wsp', '').lower()

        # Module-specific WSP relevance mapping
        module_wsp_map = {
            'platform_integration/stream_resolver': ['wsp 27', 'wsp 49', 'wsp 87'],
            'communication/livechat': ['wsp 27', 'wsp 49', 'wsp 87', 'wsp 11'],
            'platform_integration/social_media_orchestrator': ['wsp 27', 'wsp 49', 'wsp 87'],
            'platform_integration/youtube_auth': ['wsp 27', 'wsp 49', 'wsp 87'],
            'gamification/whack_a_magat': ['wsp 27', 'wsp 49', 'wsp 87'],
            'infrastructure/wre_core': ['wsp 49', 'wsp 87', 'wsp 80'],
            'ai_intelligence/pqn_alignment': ['wsp 49', 'wsp 87', 'wsp 35'],
            'development/module_creator': ['wsp 49', 'wsp 55', 'wsp 84'],
            'holo_index/dae_cube_organizer': ['wsp 80', 'wsp 49', 'wsp 87']
        }

        relevant_wsps = module_wsp_map.get(target_module, [])
        return wsp_number in relevant_wsps or any(keyword in wsp_title for keyword in ['module', 'structure', 'dae', target_module.split('/')[-1]])

    def _is_health_violation_for_module(self, notice: str, target_module: str = None) -> bool:
        """Determine if health notice is a critical violation for the target module."""
        notice_lower = notice.lower()

        # Only show critical violations, not warnings
        if '[warn]' in notice_lower or '[structure]' in notice_lower:
            return False

        # Only show violations with critical severity markers
        if not any(severity in notice_lower for severity in ['[critical]', '[violation]', 'exceeds', 'missing']):
            return False

        # If target module specified, check if notice relates to that module
        if target_module:
            module_parts = target_module.lower().split('/')
            return any(part in notice_lower for part in module_parts)

        # If no target module, only show the most critical system-wide issues
        return '[critical]' in notice_lower or 'exceeds 1000' in notice_lower

    def _generate_module_specific_wsp_prompts(self, target_module: str = None) -> List[str]:
        """Generate 0102-to-0102 WSP compliance prompts based on module context and violation history."""
        prompts = []

        # REMOVED: Unicode compliance warnings create FUD noise for 0102
        # These warnings were moved to logs only to prevent output pollution
        # 0102 agents should focus on decisions, not internal system constraints

        if not target_module:
            # General prompts when no specific module detected
            prompts.extend([
                "[CHECK] 0102: Before starting - did you read the WSP docs for this task?",
                "[THINK] 0102: Deep think: Is this a module that needs to be created or enhanced?",
                "[NOTE] 0102: Check WSP_MODULE_VIOLATIONS.md - are you creating another duplicate?",
                "[RECURSIVE] 0102: Code is remembered from 02 state - don't vibecode, research first"
            ])
            return prompts

        # Module-specific prompts based on violation patterns from WSP_MODULE_VIOLATIONS.md
        module_name = target_module.split('/')[-1].lower()

        # Common violation patterns by module type
        violation_patterns = {
            'livechat': [
                "[WARN] 0102: Livechat module exceeded 1000+ lines - WSP 62 violation! Refactor before adding more.",
                "[CHECK] 0102: Multiple livechat duplicates exist - did you check existing implementations first?",
                "[STATS] 0102: Size check: Is your change pushing livechat over WSP 62 limits?"
            ],
            'banter_engine': [
                "[RECURSIVE] 0102: Banter engine has 5+ duplicate files - WSP 40 violation! Consolidate, don't create more.",
                "[NOTE] 0102: Check sequence_responses duplicates before making changes.",
                "[THINK] 0102: Deep think: Enhance existing banter_engine instead of creating banter_engine_v2"
            ],
            'youtube_proxy': [
                "[TOOL] 0102: YouTube proxy has runtime patches - integrate them properly, don't add more hacks.",
                "[DOC] 0102: Document your proxy changes in ModLog - WSP 22 compliance required."
            ],
            'stream_resolver': [
                "[LIBRARY] 0102: Stream resolver has legitimate multi-version pattern - document it properly.",
                "[CHECK] 0102: Check WSP 40 compliance before adding another stream_resolver variant."
            ],
            'dae_cube_organizer': [
                "[TARGET] 0102: DAE Cube Organizer - ensure WSP 80 compliance in your changes.",
                "[NOTE] 0102: This is HoloIndex core - test thoroughly before committing."
            ],
            'pqn_alignment': [
                "[DNA] 0102: PQN research - follow WSP 23 rESP protocols strictly.",
                "[SCIENCE] 0102: Quantum consciousness work - validate against WSP 61 foundations."
            ],
            'wre_core': [
                "[CONFIG] 0102: WRE core changes affect everything - extensive testing required.",
                "[RECURSIVE] 0102: Check for recursive loop prevention - WSP 48 compliance critical."
            ]
        }

        # Add module-specific prompts
        if module_name in violation_patterns:
            prompts.extend(violation_patterns[module_name])

        # Add universal 0102 prompts for all module work
        prompts.extend([
            f"[DOC] 0102: Working on {target_module} - did you read its README.md and INTERFACE.md first?",
            f"[DOC] 0102: {target_module} changes require ModLog update - WSP 22 compliance mandatory.",
            f"[TEST] 0102: Does {target_module} have tests? WSP 5/WSP 34 require test coverage.",
            f"[DEPS] 0102: Check {target_module} requirements.txt - WSP 12 dependency management.",
            f"[CHECK] 0102: Is this change enhancing existing {module_name} or creating unnecessary duplication?",
            f"[STATS] 0102: File size check - is your change pushing {target_module} over WSP 62 limits?",
            f"[THINK] 0102: Deep think: Can {target_module} be simplified? Follow WSP simplicity principle.",
            f"[RECURSIVE] 0102: Code is remembered from 02 state - don't write, remember the solution.",
            f"[TARGET] 0102: Ask yourself: 'Does this module need to exist?' - WSP core question.",
            f"[FAST] 0102: Ask yourself: 'Can I afford to build this?' - Resource reality check.",
            f"[LAUNCH] 0102: Ask yourself: 'Can I live without this?' - Essential vs nice-to-have."
        ])

        return prompts[:5]  # Limit to 5 most relevant prompts to avoid overload

    def display_results(self, result: Dict[str, Any]) -> None:
        """Display search results using the throttler's prioritized output system."""
        code_hits = result.get('code', [])
        wsp_hits = result.get('wsps', [])
        docs_hits = result.get('docs', [])
        knowledge_hits = result.get('knowledge', [])
        warnings = result.get('warnings', [])
        reminders = result.get('reminders', [])

        # Get contextual filtering information
        target_module = self.detected_module

        # Memory-first bundle (WSP 60)
        memory_bundle = self._build_memory_bundle(result)
        self._memory_bundle = memory_bundle
        memory_section = "\n".join(self._format_memory_bundle(memory_bundle, max_cards=3))
        self.add_section('memory', memory_section, priority=1, tags=['memory'])

        # Code results - highest priority for search queries
        if code_hits:
            code_content = "[CODE] Code Results:"
            for idx, hit in enumerate(code_hits, start=1):
                code_content += f"\n  {idx}. [{hit['similarity']}] {hit['need']}"
                code_content += f"\n     -> {hit['location']}"
                if hit.get('cube'):
                    code_content += f"\n     cube: {hit['cube']}"
            self.add_section('results', code_content, priority=1, tags=['code', 'results'])
        else:
            self.add_section('results', "[CODE] No matching code entries found", priority=3, tags=['code', 'empty'])

        # WSP guidance - filter for contextual relevance
        if wsp_hits:
            # Filter WSP guidance based on target module and query relevance
            filtered_wsp_hits = []
            for hit in wsp_hits:
                if self._is_wsp_relevant_to_module(hit, target_module):
                    filtered_wsp_hits.append(hit)

            # Limit to top 3 most relevant for context
            filtered_wsp_hits = filtered_wsp_hits[:3]

            if filtered_wsp_hits:
                wsp_content = f"[WSP] WSP Guidance ({'for ' + target_module if target_module else 'general'}:"
                for idx, hit in enumerate(filtered_wsp_hits, start=1):
                    wsp_content += f"\n  {idx}. [{hit['similarity']}] {hit['wsp']} - {hit['title']}"
                    if hit.get('summary'):
                        wsp_content += f"\n     " + hit['summary'][:100] + ('...' if len(hit['summary']) > 100 else '')
                    wsp_content += f"\n     -> {hit['path']}"
                    if hit.get('cube'):
                        wsp_content += f"\n     cube: {hit['cube']}"
                self.add_section('guidance', wsp_content, priority=2, tags=['wsp', 'guidance', 'contextual'])
            else:
                self.add_section('guidance', "[WSP] No module-specific WSP guidance found", priority=4, tags=['wsp', 'empty'])
        else:
            self.add_section('guidance', "[WSP] No relevant WSP protocols found", priority=4, tags=['wsp', 'empty'])

        # Docs results - module/root documentation
        if docs_hits:
            docs_content = "[DOCS] Documentation:"
            for idx, hit in enumerate(docs_hits[:5], start=1):
                path = hit.get('path', 'unknown')
                title = hit.get('title', '')
                docs_content += f"\n  {idx}. {path}"
                if title:
                    docs_content += f" - {title}"
            self.add_section('docs', docs_content, priority=2, tags=['docs', 'documentation'])

        # Knowledge results - papers/research
        if knowledge_hits:
            knowledge_content = "[KNOWLEDGE] Research/Papers:"
            for idx, hit in enumerate(knowledge_hits[:3], start=1):
                path = hit.get('path', 'unknown')
                title = hit.get('title', '')
                knowledge_content += f"\n  {idx}. {path}"
                if title:
                    knowledge_content += f" - {title}"
            self.add_section('knowledge', knowledge_content, priority=3, tags=['knowledge', 'research'])

        # Warnings - critical priority
        if warnings:
            warning_content = "[WARN] Critical Issues:"
            for warning in warnings:
                warning_content += f"\n  - {warning}"
            self.add_section('warnings', warning_content, priority=1, tags=['warnings', 'critical'])
        else:
            self.add_section('status', "[SUCCESS] No WSP violations detected", priority=5, tags=['status', 'compliance'])

        # Reminders - medium priority
        if reminders:
            reminder_content = "[REM] Action Items:"
            for reminder in reminders:
                reminder_content += f"\n  - {reminder}"
            self.add_section('reminders', reminder_content, priority=3, tags=['reminders', 'actions'])

        # Intelligent subroutine results - only show when violations detected
        intelligent_analysis = result.get('intelligent_analysis', {})
        if intelligent_analysis:
            # Size analysis results
            if 'size_analysis' in intelligent_analysis:
                size_data = intelligent_analysis['size_analysis']
                if size_data.get('exceeds_threshold') and not size_data.get('error'):
                    size_content = f"[ANALYSIS] Module Size Alert ({target_module}:"
                    size_content += f"\n  - Total lines: {size_data['total_lines']} ({size_data['file_count']} files)"
                    if size_data['large_files']:
                        size_content += f"\n  - Large files exceeding WSP 62 threshold:"
                        for large_file in size_data['large_files'][:3]:  # Top 3
                            size_content += f"\n    - {large_file['file']}: {large_file['lines']} lines (> {large_file['threshold']})"
                    size_content += f"\n  - WSP 62 Status: {size_data['wsp_compliance']}"
                    self.add_section('analysis', size_content, priority=2, tags=['analysis', 'size', 'wsp62', 'violation'])

            # Duplication analysis results
            if 'duplication_check' in intelligent_analysis:
                dup_data = intelligent_analysis['duplication_check']
                if dup_data.get('wsp_violation') and not dup_data.get('error'):
                    dup_content = f"[ANALYSIS] Code Duplication Detected ({target_module}:"
                    dup_content += f"\n  - Duplicates found: {dup_data['duplicates_found']}"
                    if dup_data['duplicate_pairs']:
                        dup_content += f"\n  - Duplicate pairs:"
                        for pair in dup_data['duplicate_pairs'][:2]:  # Top 2
                            dup_content += f"\n    - {pair['original']} <-> {pair['duplicate']} ({pair['lines']} lines)"
                    dup_content += f"\n  - WSP 40 Status: VIOLATION - {dup_data['recommendation']}"
                    self.add_section('analysis', dup_content, priority=2, tags=['analysis', 'duplication', 'wsp40', 'violation'])

            if 'module_scoring' in intelligent_analysis:
                score_data = intelligent_analysis['module_scoring']
                if score_data.get('error'):
                    score_content = f"[SCORING] Module scoring unavailable: {score_data['error']}"
                    self.add_section('analysis', score_content, priority=3, tags=['analysis', 'scoring', 'warning'])
                else:
                    score_content = "[SCORING] WSP 15/37 Module Priority:"

                    target_score = score_data.get('target_score')
                    if target_score:
                        score_content += (
                            f"\n  - Target: {target_score.get('name')} "
                            f"({target_score.get('priority')}, {target_score.get('mps_score')})"
                        )

                    top_active = score_data.get('top_active') or []
                    if top_active:
                        score_content += "\n  - Top Active:"
                        for entry in top_active[:3]:
                            score_content += (
                                f"\n    - {entry.get('name')} "
                                f"({entry.get('priority')}, {entry.get('mps_score')})"
                            )

                    top_inactive = score_data.get('top_inactive') or []
                    if top_inactive:
                        score_content += "\n  - Next Activation:"
                        for entry in top_inactive[:3]:
                            score_content += (
                                f"\n    - {entry.get('name')} "
                                f"({entry.get('priority')}, {entry.get('mps_score')})"
                            )

                    self.add_section('analysis', score_content, priority=2, tags=['analysis', 'scoring', 'wsp15', 'wsp37'])

        # Health notices - only show violations for target module
        health_notices = result.get('health_notices', [])
        if health_notices:
            # Filter to only show violations (not warnings) and only for target module
            filtered_health = []
            for notice in health_notices:
                if self._is_health_violation_for_module(notice, target_module):
                    filtered_health.append(notice)

            if filtered_health:
                health_content = f"[HEALTH] Critical Health Violations ({'for ' + target_module if target_module else 'system-wide'}:"
                for notice in filtered_health[:3]:  # Limit to top 3
                    health_content += f"\n  - {notice}"
                self.add_section('health', health_content, priority=2, tags=['health', 'violations', 'critical', 'actionable'])

        # 0102-to-0102 WSP Compliance Prompts - contextual guidance
        wsp_prompts = self._generate_module_specific_wsp_prompts(target_module)
        if wsp_prompts:
            prompt_content = "[0102] WSP Compliance Prompts:\n"
            for prompt in wsp_prompts:
                prompt_content += f"  - {prompt}\n"
            self.add_section('prompts', prompt_content.strip(), priority=1, tags=['0102', 'prompts', 'wsp', 'compliance'])

        # FMAS reference - low priority
        fmas_hint_needed = bool(result.get('fmas_hint'))
        if fmas_hint_needed:
            self.add_section('reference', "[REF] Review FMAS plan: WSP_framework/docs/testing/HOLOINDEX_QWEN_ADVISOR_FMAS_PLAN.md", priority=8, tags=['reference', 'fmas'])

        # AI Advisor guidance - medium priority
        advisor_info = result.get('advisor')
        advisor_error = result.get('advisor_error')
        if advisor_info:
            guidance_text = advisor_info.get('guidance')
            code_index_present = "[CODE-INDEX]" in str(guidance_text)
            if os.getenv('HOLO_VERBOSE', '').lower() in {'1', 'true', 'yes'}:
                print(f"[DEBUG] THROTTLER: Code index in guidance: {code_index_present}, guidance length: {len(str(guidance_text))}")  # DEBUG
            advisor_content = "[ADVISOR] AI Guidance:"
            advisor_content += f"\n  Guidance: {guidance_text}"
            for reminder in advisor_info.get('reminders', [])[:2]:  # Limit reminders
                advisor_content += f"\n  Reminder: {reminder}"
            todos = advisor_info.get('todos', [])[:3]  # Limit todos
            if todos:
                advisor_content += "\n  TODOs:"
                for item in todos:
                    advisor_content += f"\n    - {item}"
            self.add_section('advisor', advisor_content, priority=3, tags=['advisor', 'ai', 'guidance'])

            # Pattern insights - only if highly relevant
            pattern_insights = advisor_info.get('pattern_insights', [])
            if pattern_insights and len(pattern_insights) <= 2:  # Limit verbosity
                pattern_content = "[PATTERN] Key Insights:"
                for insight in pattern_insights:
                    pattern_content += f"\n  {insight}"
                self.add_section('insights', pattern_content, priority=4, tags=['patterns', 'insights'])

        elif advisor_error:
            self.add_section('advisor', f"[ADVISOR] Qwen Guidance:\n  {advisor_error}", priority=7, tags=['advisor', 'error'])

        # Adaptive learning results - low priority (technical metrics)
        adaptive_info = result.get('adaptive_learning')
        if adaptive_info:
            adaptive_content = f"[ADAPTIVE] Learning: Adaptation={adaptive_info.get('system_adaptation_score', 0.0):.2f}, Efficiency={adaptive_info.get('memory_efficiency', 0.0):.2f}"
            self.add_section('metrics', adaptive_content, priority=9, tags=['metrics', 'learning', 'verbose'])

    def generate_0102_summary(self, component_results: Dict[str, Any], query: str) -> str:
        """
        FIRST PRINCIPLES: Generate concise, actionable summary for 0102

        Instead of massive verbose output, provide 3-5 key insights that 0102 can act upon.

        Args:
            component_results: Results from executed components
            query: Original user query

        Returns:
            Concise summary string optimized for 0102 consumption

        Token Budget: ~500 tokens max output
        WSP Compliance: WSP 75 (Token-Based Development), WSP 80 (Cube-Level Orchestration)
        """
        summary_parts = []
        query_lower = query.lower()

        # FIRST PRINCIPLES: Extract only actionable insights
        critical_issues = []
        recommendations = []
        key_findings = []

        # Process component results for key insights
        for component_name, results in component_results.items():
            if not results:
                continue

            if component_name == 'health_analysis':
                violations = results.get('violations', [])
                if violations:
                    critical_issues.extend([f"WSP violation: {v}" for v in violations[:2]])  # Max 2

            elif component_name == 'file_size_monitor':
                large_files = results.get('large_files', [])
                if large_files:
                    critical_issues.append(f"Large files: {len(large_files)} files exceed limits")

            elif component_name == 'module_analysis':
                incomplete_modules = results.get('incomplete_modules', [])
                if incomplete_modules:
                    recommendations.append(f"Fix docs: {len(incomplete_modules)} modules missing README/INTERFACE")

            elif component_name == 'vibecoding_analysis':
                patterns = results.get('patterns', [])
                if patterns:
                    key_findings.append(f"Code patterns: {len(patterns)} detected")

            elif component_name == 'orphan_analysis':
                orphans = results.get('orphans', [])
                if orphans:
                    recommendations.append(f"Fix orphans: {len(orphans)} files lack tests")

        # FIRST PRINCIPLES: Structure output for 0102 decision-making
        if critical_issues:
            summary_parts.append(f"[ALERT] CRITICAL: {len(critical_issues)} issues need immediate attention")
            summary_parts.extend(critical_issues[:2])  # Max 2 details

        if recommendations:
            summary_parts.append(f"[IDEA] ACTIONABLE: {len(recommendations)} improvements available")
            summary_parts.extend(recommendations[:2])  # Max 2 details

        if key_findings:
            summary_parts.append(f"[DATA] KEY FINDINGS: {len(key_findings)} insights")
            summary_parts.extend(key_findings[:1])  # Max 1 detail

        # FIRST PRINCIPLES: If no significant findings, provide minimal useful info
        if not summary_parts:
            total_files = sum(len(results.get('files', [])) for results in component_results.values())
            # Prefer search result counts over component-derived file counts when available
            if hasattr(self, "_search_results") and self._search_results:
                code_count = len(self._search_results.get('code', []) or [])
                wsp_count = len(self._search_results.get('wsps', []) or [])
                docs_count = len(self._search_results.get('docs', []) or [])
                knowledge_count = len(self._search_results.get('knowledge', []) or [])
                total_hits = code_count + wsp_count + docs_count + knowledge_count
                if total_hits > 0:
                    summary_parts.append(
                        f"[OK] Analysis complete: {total_hits} hits (code={code_count}, wsp={wsp_count}, docs={docs_count}, knowledge={knowledge_count}), no critical issues found"
                    )
                else:
                    summary_parts.append(f"[OK] Analysis complete: {total_files} files checked, no critical issues found")
            else:
                summary_parts.append(f"[OK] Analysis complete: {total_files} files checked, no critical issues found")

        # FIRST PRINCIPLES: Keep total output under 500 tokens
        final_summary = "\n".join(summary_parts)
        if len(final_summary.split()) > 100:  # Rough token estimate
            final_summary = final_summary[:400] + "... (truncated for efficiency)"

        return final_summary

    def _resolve_history_path(self) -> Path:
        if self.skill_manifest:
            telemetry = self.skill_manifest.get('telemetry') or {}
            history_path = telemetry.get('history_path')
            if history_path:
                candidate = Path(history_path)
                if not candidate.is_absolute():
                    base = Path(__file__).resolve().parents[1]
                    candidate = base / history_path
                return candidate
        return DEFAULT_HISTORY_PATH

    def _load_skill_manifest(self) -> Optional[Dict[str, Any]]:
        try:
            import yaml  # type: ignore
        except Exception:
            yaml = None
        if not SKILL_PATH.exists() or yaml is None:
            return None
        content = SKILL_PATH.read_text(encoding='utf-8')
        if not content.startswith('---'):
            return None
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None
        try:
            return yaml.safe_load(parts[1]) or {}
        except Exception:
            return None

    def _should_log_history(self, state: str, search_results: Dict[str, Any], verbose: bool) -> bool:
        """Gate output history logging to avoid unbounded growth."""
        raw_flag = os.getenv("HOLO_OUTPUT_HISTORY", "1").strip().lower()
        if raw_flag in {"0", "false", "no", "off"}:
            return False

        mode = os.getenv("HOLO_OUTPUT_HISTORY_MODE", "all").strip().lower()
        if mode == "verbose":
            return verbose
        if mode == "errors":
            return state == "error"
        if mode == "signals":
            return bool(search_results.get("warnings")) or bool(search_results.get("reminders"))
        return True

    def _rotate_history_if_needed(self, max_mb: float) -> None:
        """Rotate history file when it exceeds size threshold."""
        if max_mb <= 0:
            return
        try:
            if not self.history_path.exists():
                return
            size_bytes = self.history_path.stat().st_size
            if size_bytes <= max_mb * 1024 * 1024:
                return
            rotated_path = self.history_path.with_suffix(self.history_path.suffix + ".1")
            if rotated_path.exists():
                rotated_path.unlink(missing_ok=True)
            self.history_path.replace(rotated_path)
        except Exception:
            pass

    def _record_output_history(self, state: str, rendered_output: str, filtered_content: str, verbose: bool) -> None:
        """Persist structured output history for downstream pattern analysis."""

        def _write():
            try:
                search_results = getattr(self, "_search_results", {}) or {}
                if not self._should_log_history(state, search_results, verbose):
                    return
                max_mb_env = os.getenv("HOLO_OUTPUT_HISTORY_MAX_MB", "10").strip()
                max_mb = float(max_mb_env) if max_mb_env else 10.0
                self._rotate_history_if_needed(max_mb)
                self.history_path.parent.mkdir(parents=True, exist_ok=True)

                section_summaries = []
                for section in self.output_sections[:10]:
                    section_summaries.append({
                        "type": section.get("type"),
                        "priority": section.get("priority"),
                        "tags": section.get("tags", []),
                        "line_count": len(section.get("content", "").splitlines()),
                    })

                advisor_info = search_results.get("advisor") or {}

                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent": self.agent_id,
                    "query": self.query_context,
                    "detected_module": self.detected_module,
                    "state": state,
                    "verbose": verbose,
                    "search_metrics": {
                        "code_hits": len(search_results.get("code", [])),
                        "wsp_hits": len(search_results.get("wsps", [])),
                        "warnings": len(search_results.get("warnings", [])),
                        "reminders": len(search_results.get("reminders", [])),
                    },
                    "advisor_summary": {
                        "has_guidance": bool(advisor_info.get("guidance")),
                        "reminders": len(advisor_info.get("reminders", [])),
                        "todos": len(advisor_info.get("todos", [])),
                        "pattern_insights": len(advisor_info.get("pattern_insights", []))
                    } if advisor_info else None,
                    "sections": section_summaries,
                    "rendered_preview": rendered_output.splitlines()[:20],
                    "filtered_preview": filtered_content.splitlines()[:20],
                }

                with self.history_path.open("a", encoding="utf-8") as handle:
                    json.dump(record, handle, ensure_ascii=False)
                    handle.write("\n")
            except Exception:
                # History logging should never interfere with primary execution
                pass

        threading.Thread(target=_write, daemon=True).start()
