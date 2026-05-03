#!/usr/bin/env python3
"""
QwenOrchestrator - Primary orchestrator for HoloDAE intelligence system

This is the Qwen LLM orchestration layer that coordinates all HoloIndex components.
Qwen acts as the "circulatory system" - continuously analyzing and orchestrating operations,
then presenting findings to 0102 for arbitration.

ENHANCEMENT (2025-10-07): Intent-driven component routing with breadcrumb event tracking
Design Doc: docs/agentic_journals/HOLODAE_INTENT_ORCHESTRATION_DESIGN.md

WSP Compliance: WSP 80 (Cube-Level DAE Orchestration), WSP 48 (Recursive Learning)
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Intent Classification Integration
from holo_index.intent_classifier import get_classifier, IntentType

# Breadcrumb Tracer for event tracking
from holo_index.adaptive_learning.breadcrumb_tracer import get_tracer

# PHASE 3: Output Composition Integration
from holo_index.output_composer import get_composer

# PHASE 4: Feedback Learning Integration
from holo_index.feedback_learner import get_learner

from ..qwen_health_monitor import CodeIndexCirculationEngine
from ..architect_mode import ArchitectDecisionEngine

# WSP 62 Refactoring: Extracted modules
from .src.wsp_documentation_guardian import WSPDocumentationGuardian
from .src.intent_response_processor import IntentResponseProcessor

# MCP Integration imports
try:
    from modules.ai_intelligence.ric_dae.src.mcp_tools import ResearchIngestionMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ResearchIngestionMCP = None

# Local MCP Handler
from .services.mcp_handler import MCPHandler
from .services.mission_coordinator import MissionCoordinator
from .services.component_router import ComponentRouter

# Import for agent type detection
from holo_index.intent_classifier import get_classifier


COMPONENT_META = {
    'health_analysis': ('[PILL][OK]', 'Health & WSP Compliance'),
    'vibecoding_analysis': ('[AI]', 'Vibecoding Analysis'),
    'file_size_monitor': ('[RULER]', 'File Size Monitor'),
    'module_analysis': ('[BOX]', 'Module Analysis'),
    'pattern_coach': ('[AI]', 'Pattern Coach'),
    'orphan_analysis': ('[GHOST]', 'Orphan Analysis'),
    'wsp_documentation_guardian': ('[BOOKS]', 'WSP Documentation Guardian'),
}

# Intent-to-Component Routing Map (ENHANCEMENT 2025-10-07)
# Maps IntentType to relevant components for smart routing
INTENT_COMPONENT_MAP = {
    IntentType.DOC_LOOKUP: [
        'wsp_documentation_guardian',  # Primary - WSP/README/INTERFACE docs
        'module_analysis'              # Secondary - module context
    ],
    IntentType.CODE_LOCATION: [
        'module_analysis',             # Primary - find files/modules
        'orphan_analysis',             # Secondary - check if orphaned
        'file_size_monitor'            # Secondary - large file warnings
    ],
    IntentType.MODULE_HEALTH: [
        'health_analysis',             # Primary - WSP compliance
        'vibecoding_analysis',         # Secondary - pattern violations
        'orphan_analysis',             # Secondary - orphaned files
        'file_size_monitor'            # Secondary - size issues
    ],
    IntentType.RESEARCH: [
        'pattern_coach',               # Primary - explain patterns
        'wsp_documentation_guardian',  # Secondary - WSP context
        # MCP tools called separately for RESEARCH intent
    ],
    IntentType.GENERAL: [
        # FIRST PRINCIPLES: Smart component selection based on query content
        # Instead of running ALL components, select 2-3 most relevant based on keywords
        # This is handled by _select_general_components() method below
    ]
}

# WSP Documentation Guardian Configuration
WSP_DOC_CONFIG = {
    'doc_only_modules': {
        'holo_index/docs',
        'WSP_framework/docs',
        'WSP_framework/historic_assets',
        'WSP_framework/reports/legacy',
    },
    'expected_update_intervals_days': {
        'README.md': 90,  # Quarterly updates
        'ModLog.md': 30,  # Monthly updates (tracking changes)
        'requirements.txt': 30,  # Monthly dependency updates
        'INTERFACE.md': 60,  # Bi-monthly API changes
        'ROADMAP.md': 30,  # Monthly planning updates
    },
    'auto_remediate_ascii': False,  # Default to read-only mode - remediation opt-in
    'remediation_log_path': 'WSP_framework/docs/WSP_ASCII_REMEDIATION_LOG.md',
    'backup_temp_dir': 'temp/wsp_backups',  # Store backups in temp directory
}

class QwenOrchestrator:
    """Primary orchestrator for HoloDAE - Qwen's decision-making and coordination layer"""

    def __init__(self, coordinator=None) -> None:
        """Initialize the Qwen orchestrator"""
        self._ensure_utf8_console()
        self.logger = logging.getLogger('holodae_activity')
        self.chain_of_thought_log: List[Dict[str, Any]] = []
        self.performance_history: List[float] = []
        self._last_files: List[str] = []
        self._last_modules: List[str] = []
        self._last_executed_components: List[str] = []
        self.repo_root = Path(__file__).resolve().parents[3]
        self.coordinator = coordinator  # Reference to HoloDAECoordinator for MCP logging

        # Initialize QWEN filtering attributes
        self._intent_filters = {}
        self._intent_keywords = {}
        self._max_suggestions = 10
        self._deduplicate_alerts = False

        # ENHANCEMENT (2025-10-07): Intent classifier for smart routing
        self.intent_classifier = get_classifier()
        self._log_chain_of_thought("INTENT-INIT", "[TARGET] Intent classifier initialized")

        # ENHANCEMENT (2025-10-07): Breadcrumb tracer for event tracking
        self.breadcrumb_tracer = get_tracer()
        # Initialize Services
        self.mission_coordinator = MissionCoordinator(agent_type="qwen" if self._is_qwen_agent() else "0102")
        self.component_router = ComponentRouter()
        self.mcp_handler = MCPHandler(mcp_client=None, logger=self._log_chain_of_thought)

        # WSP 93: CodeIndex circulation + architect decision helpers
        self.codeindex_engine = CodeIndexCirculationEngine()
        self.architect_engine = ArchitectDecisionEngine()
        self._last_module_snapshots: Dict[str, Dict[str, Any]] = {}
        self._last_codeindex_reports: List[Dict[str, Any]] = []

        # Initialize MCP client if available (toggleable)
        mcp_enabled = os.getenv("HOLO_MCP_ENABLED", "true").lower() in {"1", "true", "yes"}
        if MCP_AVAILABLE and ResearchIngestionMCP and mcp_enabled:
            try:
                self.mcp_client = ResearchIngestionMCP()
                self.mcp_handler.mcp_client = self.mcp_client
            except Exception as e:
                self.mcp_client = None
                logging.debug(f"[QWEN] MCP client unavailable (non-fatal): {e}")
        else:
            self.mcp_client = None

        # Initialize core components
        self.feedback_learner = get_learner()
        self.output_composer = get_composer()

        # WSP 62 Refactoring: Initialize WSP Documentation Guardian
        self.wsp_guardian = WSPDocumentationGuardian(
            repo_root=self.repo_root,
            logger=self.logger,
            relative_path_func=self._relative_path,
            count_lines_func=self._count_file_lines
        )

        # WSP 62 Refactoring: Initialize Intent Response Processor
        self.intent_processor = IntentResponseProcessor(
            logger=self.logger,
            breadcrumb_tracer=self.breadcrumb_tracer,
            output_composer=self.output_composer
        )

    def _ensure_utf8_console(self):
        """Ensure console supports UTF-8 encoding (Windows compatibility)."""
        try:
            if sys.platform == 'win32':
                import codecs
                # Wrap stdout/stderr with UTF-8 codec writer
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        except Exception as e:
            # Non-fatal - keep quiet by default
            logging.debug(f"[QWEN] Failed to set UTF-8 console: {e}")

    def _select_general_components(self, query: str, files: List[str], modules: List[str]) -> List[str]:
        """Select appropriate components for GENERAL intent queries based on content analysis."""
        from collections import defaultdict
        component_scores = defaultdict(int)

        query_lower = query.lower()

        # Score based on query content (FIRST PRINCIPLES: Intent analysis)
        if any(word in query_lower for word in ['orphan', 'missing', 'test', 'connection']):
            component_scores['orphan_analysis'] += 3

        if any(word in query_lower for word in ['doc', 'readme', 'interface', 'modlog', 'documentation']):
            component_scores['wsp_documentation_guardian'] += 3

        # Score based on file/module context (FIRST PRINCIPLES: Context awareness)
        if len(files) > 10:
            component_scores['file_size_monitor'] += 2  # Large result sets suggest size monitoring
        if len(modules) > 3:
            component_scores['module_analysis'] += 2    # Multiple modules suggest module analysis

        # FIRST PRINCIPLES: Select top 2-3 components with highest relevance
        # Never select more than 3 to prevent output overload
        sorted_components = sorted(component_scores.items(), key=lambda x: x[1], reverse=True)
        selected = [comp for comp, score in sorted_components if score > 0][:3]

        # FIRST PRINCIPLES: Ensure at least basic analysis if no strong matches
        if not selected:
            selected = ['module_analysis', 'health_analysis']  # Minimal useful analysis

        self._log_chain_of_thought(
            "SMART-SELECTION",
            f"[TARGET] GENERAL query '{query[:30]}...' -> Selected {len(selected)} components: {', '.join(selected)}"
        )

        return selected

    def _is_qwen_agent(self) -> bool:
        """Check if this orchestrator is running as a Qwen agent vs 0102 agent."""
        try:
            # Check if we have Qwen models available
            qwen_available = hasattr(self, 'qwen_engine') and self.qwen_engine is not None
            return qwen_available
        except:
            return False

    def orchestrate_monitoring(self, work_context):
        """Handle monitoring orchestration for autonomous HoloDAE"""
        # Create a monitoring result object with expected attributes for self-improvement
        class MonitoringResult:
            def __init__(self, active_files=0, task_pattern='monitoring'):
                self.violations_found = []
                self.optimization_suggestions = []
                self.pattern_alerts = []
                self.active_files_count = active_files
                self.task_pattern = task_pattern
                self.timestamp = datetime.now().isoformat()
                self.status = 'monitoring_complete'

        active_files = len(work_context.active_files) if hasattr(work_context, 'active_files') else 0
        task_pattern = getattr(work_context, 'task_pattern', 'monitoring')

        return MonitoringResult(active_files, task_pattern)

    def orchestrate_holoindex_request(self, query: str, search_results: Dict[str, Any]) -> str:
        """
        Handle incoming HoloIndex request with intent-driven orchestration
        """
        involved_files = self._extract_files_from_results(search_results)
        involved_modules = self._extract_modules_from_files(involved_files)

        # Persist context for coordinator integration
        self._last_files = involved_files.copy()
        self._last_modules = involved_modules.copy()

        # Log the orchestration initiation
        self._log_chain_of_thought("INIT", f"Processing HoloIndex query: '{query}'")
        self._log_chain_of_thought(
            "CONTEXT",
            f"Found {len(involved_files)} files across {len(involved_modules)} modules",
        )

        if not involved_files:
            self._log_chain_of_thought("DECISION", "No files to analyze - returning early")
            return "[HOLODAE-ANALYZE] No files found to analyze"

        # FIRST PRINCIPLES: Check for mission coordination FIRST (MCP adoption, then orphans)
        
        # Check MCP adoption status first (higher priority)
        mcp_coordination = self.mission_coordinator.coordinate_mcp_adoption_mission(query)
        if mcp_coordination is not None:
            self._log_chain_of_thought(
                "COORDINATION",
                f"[U+1F3D7]️ MCP adoption mission detected - HoloIndex providing Rubik status"
            )
            return mcp_coordination

        # Check orphan archaeology coordination
        orphan_coordination = self.mission_coordinator.coordinate_orphan_archaeology_mission(query)
        if orphan_coordination is not None:
            self._log_chain_of_thought(
                "COORDINATION",
                f"[U+1F3DB]️ Orphan archaeology mission detected - HoloIndex coordinating Qwen/Gemma analysis"
            )
            return orphan_coordination

        # ENHANCEMENT: Classify intent using new intent classifier
        intent_classification = self.intent_classifier.classify(query)
        intent = intent_classification.intent

        # BREADCRUMB EVENT: Intent classification
        self.breadcrumb_tracer.add_action(
            'intent_classification',
            intent.value,
            f"Query classified as {intent.value} (confidence: {intent_classification.confidence:.2f})",
            query
        )

        self._log_chain_of_thought(
            "INTENT",
            f"[TARGET] Classified as {intent.value.upper()} (confidence: {intent_classification.confidence:.2f}, patterns: {len(intent_classification.patterns_matched)})"
        )

        context = self._build_orchestration_context(query, involved_files, involved_modules, intent)

        # Legacy intent mapping for backward compatibility with output filters
        legacy_intent = self._map_intent_to_legacy(intent)
        output_filter = self.intent_processor._get_output_filter_for_intent(legacy_intent)

        # PHASE 5: MCP Integration Separation (Intent-Gated)
        mcp_insights = []
        if intent == IntentType.RESEARCH:
            self._log_chain_of_thought("MCP-GATE", "[U+1F52C] RESEARCH intent detected - calling MCP tools")
            mcp_insights = self.mcp_handler.call_research_mcp_tools(query, context)
            if mcp_insights:
                self._log_chain_of_thought("MCP-RESEARCH", f"[SEARCH] Retrieved {len(mcp_insights)} research insights")
                self.mcp_handler.learn_from_mcp_usage(query, mcp_insights, context)
        else:
            self._log_chain_of_thought("MCP-SKIP", f"⏭️ Intent {intent.value} - skipping MCP research tools")

        # Log detected intent
        if intent == "fix_error":
            self._log_chain_of_thought("INTENT", "[TOOL] Error fixing mode - minimizing health checks")
        elif intent == "locate_code":
            self._log_chain_of_thought("INTENT", "[PIN] Code location mode - focused output")
        elif intent == "explore":
            self._log_chain_of_thought("INTENT", "[SEARCH] Exploration mode - full analysis")

        # ENHANCEMENT: Get intent-based component routing
        base_components = self.component_router.select_components(intent.value, query, involved_files, involved_modules)

        # PHASE 4: Apply feedback learning to filter components
        components_to_execute = self.feedback_learner.get_filtered_components(
            intent=intent,
            available_components=base_components,
            threshold=0.3  # Filter components with weight < 0.3
        )

        # BREADCRUMB EVENT: Component routing decision
        all_components = list(COMPONENT_META.keys())
        components_filtered = [c for c in all_components if c not in components_to_execute]

        self.breadcrumb_tracer.add_discovery(
            'component_routing',
            f"routed_{intent.value}",
            f"Selected {len(components_to_execute)} relevant, filtered {len(components_filtered)} noisy"
        )

        self._log_chain_of_thought(
            "ROUTING",
            f"[PIN] Intent {intent.value} -> {len(components_to_execute)} components selected (filtered {len(components_filtered)})"
        )

        # Get orchestration decisions for selected components only
        raw_decisions = self._get_orchestration_decisions_for_components(
            context, components_to_execute
        )
        orchestration_decisions = self._filter_orchestration_decisions(raw_decisions, output_filter)

        # Execute analysis with filtered output
        import time
        start_time = time.time()

        analysis_report = self._execute_orchestrated_analysis_filtered(
            query, involved_files, involved_modules, orchestration_decisions, output_filter
        )

        should_codeindex, trigger_reason = self._should_trigger_codeindex(
            query=query,
            intent_classification=intent_classification,
            module_snapshots=self._last_module_snapshots,
        )
        if should_codeindex:
            codeindex_section = self._generate_codeindex_section(self._last_module_snapshots)
            if codeindex_section:
                analysis_report = f"{analysis_report}\n{codeindex_section}"
                self._log_chain_of_thought("CODEINDEX", f"🩺 CodeIndex triggered: {trigger_reason}")
                self.breadcrumb_tracer.add_action(
                    'codeindex_activation',
                    'codeindex_surgical',
                    trigger_reason,
                    query
                )

        duration_ms = int((time.time() - start_time) * 1000)

        # BREADCRUMB EVENT: Orchestration execution
        self.breadcrumb_tracer.add_action(
            'orchestration_execution',
            f"executed_{len(orchestration_decisions)}_components",
            f"Executed {len(orchestration_decisions)} components in {duration_ms}ms",
            query
        )

        # Calculate effectiveness (filtered logging)
        effectiveness = self._calculate_analysis_effectiveness(analysis_report)
        self.performance_history.append(effectiveness)
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

        if output_filter["show_performance_logs"]:
            self._log_chain_of_thought("EFFECTIVENESS", f"Analysis effectiveness: {effectiveness:.2f}")

        # PHASE 3: Output Composition - Structure and deduplicate output
        # Collect alerts from analysis_report
        collected_alerts = []
        for line in analysis_report.split('\n'):
            if any(keyword in line.upper() for keyword in ['WARNING', 'VIOLATION', 'STALE', 'ALERT', 'ERROR']):
                collected_alerts.append(line.strip())

        # Format MCP insights if available
        mcp_section = None
        if mcp_insights:
            mcp_lines = []
            for insight in mcp_insights[:3]:  # Limit to top 3 insights
                tool_name = insight.get('tool_name', 'Unknown')
                result = insight.get('result', 'No result')
                mcp_lines.append(f"  - [{tool_name}] {result[:200]}...")  # Truncate long results
            mcp_section = '\n'.join(mcp_lines)

        # Compose structured output with context-aware formatting
        composed = self.output_composer.compose(
            intent_classification=intent_classification,
            findings=analysis_report,
            mcp_results=mcp_section,
            alerts=collected_alerts if collected_alerts else None,
            query=query,
            search_results=search_results  # Pass search results for CODE_LOCATION
        )

        # BREADCRUMB EVENT: Output composition
        self.breadcrumb_tracer.add_action(
            'output_composition',
            f"composed_{intent.value}",
            f"Composed {len(composed.full_output)} chars with {len(collected_alerts)} alerts",
            query
        )

        # FIRST PRINCIPLES: For GENERAL queries, use intelligent 0102 summary instead of massive output
        if intent == IntentType.GENERAL:
            # Import throttler here to avoid circular imports
            from holo_index.output.agentic_output_throttler import AgenticOutputThrottler

            throttler = AgenticOutputThrottler()
            throttler.set_query_context(query, search_results)

            # Extract component results from analysis_report for summary generation
            component_results = self.intent_processor._extract_component_results_from_report(analysis_report)

            concise_summary = throttler.generate_0102_summary(component_results, query)

            # Log the efficiency gain
            original_length = len(composed.full_output.split())
            summary_length = len(concise_summary.split())
            compression_ratio = original_length / max(summary_length, 1)

            self._log_chain_of_thought(
                "0102-OPTIMIZATION",
                f"[TARGET] GENERAL query optimized: {compression_ratio:.1f}x compression ({original_length} -> {summary_length} tokens)"
            )

            # Ensure GENERAL queries still surface top search hits (avoid "0 files checked" dead-end)
            if search_results:
                code_hits = search_results.get('code', []) or []
                wsp_hits = search_results.get('wsps', []) or []
                docs_hits = search_results.get('docs', []) or []
                knowledge_hits = search_results.get('knowledge', []) or []
                if code_hits or wsp_hits or docs_hits or knowledge_hits:
                    result_lines = ["[RESULTS] Top matches"]
                    for item in code_hits[:3]:
                        path = item.get('path') or item.get('id') or item.get('title') or 'unknown'
                        result_lines.append(f"  [CODE] {path}")
                    for item in wsp_hits[:3]:
                        path = item.get('path') or item.get('id') or item.get('title') or 'unknown'
                        result_lines.append(f"  [WSP] {path}")
                    for item in docs_hits[:3]:
                        path = item.get('path') or item.get('id') or item.get('title') or 'unknown'
                        result_lines.append(f"  [DOCS] {path}")
                    for item in knowledge_hits[:2]:
                        path = item.get('path') or item.get('id') or item.get('title') or 'unknown'
                        result_lines.append(f"  [KNOWLEDGE] {path}")
                    concise_summary = concise_summary.rstrip() + "\n" + "\n".join(result_lines)

            return concise_summary

        # Return composed output for other intents (replaces legacy format_intent_aware_response)
        return composed.full_output

    # WSP 62 Refactoring: Intent processing methods extracted to src/intent_response_processor.py
    # Extracted: _extract_component_results_from_report, _get_output_filter_for_intent, _format_intent_aware_response

    def _filter_orchestration_decisions(self, decisions: List[Dict[str, Any]], output_filter: Dict[str, bool]) -> List[Dict[str, Any]]:
        """
        NEW: Filter orchestration decisions based on QWEN output filter
        """
        if not output_filter:
            return decisions

        # Filter out components based on intent
        filtered_decisions = []
        for decision in decisions:
            component = decision.get('component', '')

            # Skip health checks for error/locator intents
            if not output_filter.get("show_health_checks", True):
                if 'health' in component.lower():
                    continue

            # Skip module analysis for simple queries
            if not output_filter.get("show_module_metrics", True):
                if 'module' in component.lower():
                    continue

            filtered_decisions.append(decision)

        return filtered_decisions

    def _execute_orchestrated_analysis_filtered(self, query: str, files: List[str], modules: List[str],
                                               orchestration_decisions: List[Dict[str, Any]],
                                               output_filter: Dict[str, bool] = None) -> str:
        """
        Enhanced with QWEN output filtering during execution
        """
        # Use existing method
        report = self._execute_orchestrated_analysis(query, files, modules, orchestration_decisions)

        if output_filter and output_filter.get("compact_format", False):
            # Apply compact formatting
            lines = report.split('\n')
            compact_lines = []

            # Keep headers and essential info, skip noise
            for line in lines:
                # Skip noisy technical details
                if any(noise in line.lower() for noise in [
                    'holodae-', 'orchestration', 'processing', 'telemetry',
                    'effectiveness', 'chain-of-thought'
                ]):
                    continue

                # Keep important information
                if line.strip() and len(line.strip()) > 10:  # Meaningful content
                    compact_lines.append(line)

            return '\n'.join(compact_lines[:10]) if compact_lines else report  # Limit output

        return report

    def _should_trigger_codeindex(
        self,
        query: str,
        intent_classification,
        module_snapshots: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, str]:
        """Decide if CodeIndex surgical analysis should augment the response."""
        if not module_snapshots:
            return False, ""

        query_lower = query.lower()
        reasons: List[str] = []

        keyword_map = {
            "keyword 'codeindex'": ["codeindex", "surgical"],
            "refactor keyword": ["refactor", "split function", "break apart", "too long"],
            "optimization keyword": ["optimize", "performance", "efficiency"],
        }
        for label, keywords in keyword_map.items():
            if any(keyword in query_lower for keyword in keywords):
                reasons.append(label)
                break

        large_modules = [
            module for module, snapshot in module_snapshots.items()
            if snapshot.get("large_python_files")
        ]
        if large_modules:
            reasons.append(f"large modules detected ({len(large_modules)})")

        coverage_gaps = [
            module for module, snapshot in module_snapshots.items()
            if snapshot.get("py_file_count", 0) >= 3 and snapshot.get("test_count", 0) == 0
        ]
        if coverage_gaps and intent_classification.intent in {
            IntentType.CODE_LOCATION,
            IntentType.MODULE_HEALTH,
            IntentType.GENERAL,
        }:
            reasons.append("module coverage gap identified")

        if intent_classification.intent == IntentType.MODULE_HEALTH:
            reasons.append("module health review")

        # Encourage pattern-based triggers only when module set is manageable
        if len(module_snapshots) > 6 and not reasons:
            return False, ""

        if not reasons:
            return False, ""

        return True, "; ".join(reasons[:3])

    def _generate_codeindex_section(self, module_snapshots: Dict[str, Dict[str, Any]]) -> str:
        """Produce textual summary of CodeIndex reports for selected modules."""
        if not module_snapshots:
            return ""

        module_candidates: List[Tuple[int, str, Path]] = []
        for module, snapshot in module_snapshots.items():
            path = snapshot.get("path")
            if not path or not snapshot.get("exists"):
                continue
            score = 0
            large_files = snapshot.get("large_python_files", [])
            if large_files:
                score += min(6, len(large_files) * 2)
                max_lines = max((info[1] for info in large_files), default=0)
                score += min(6, max_lines // 200)
            if snapshot.get("py_file_count", 0) and snapshot.get("test_count", 0) == 0:
                score += 2
            module_candidates.append((score, module, path))

        module_candidates.sort(key=lambda item: item[0], reverse=True)
        selected_paths = [
            path for score, module, path in module_candidates if score > 0
        ][:2]
        if not selected_paths and module_candidates:
            selected_paths = [module_candidates[0][2]]
        if not selected_paths:
            return ""

        reports = self.codeindex_engine.evaluate_modules(selected_paths)
        if not reports:
            return ""

        self._last_codeindex_reports = [report.to_summary() for report in reports]

        lines: List[str] = ["[CODEINDEX][WSP 93] Surgical intelligence summary:"]
        for report in reports:
            lines.append(f"  - Module {report.module_name}: {report.critical_fix_count()} critical fixes")
            for fix in report.surgical_fixes[:2]:
                lines.append(
                    f"    - {fix.function} ({fix.line_range}) -> {fix.estimated_effort}min (complexity {fix.complexity})"
                )
            architect_lines = self.architect_engine.summarize(report).splitlines()
            for architect_line in architect_lines[:4]:
                lines.append(f"    {architect_line}")
            if report.assumption_alerts:
                assumption_lines = [
                    line.strip() for line in report.assumption_alerts.splitlines()
                    if line.strip() and not line.startswith("[ASSUMPTIONS]")
                ][:2]
                for assumption_line in assumption_lines:
                    lines.append(f"    [ASSUMPTION] {assumption_line}")
        return "\n".join(lines)

    def get_recent_analysis_context(self) -> Dict[str, List[str]]:
        """Return the most recent file/module context analyzed by Qwen"""
        return {'files': self._last_files.copy(), 'modules': self._last_modules.copy()}

    def get_recent_execution_summary(self) -> Dict[str, Any]:
        """Return latest executed component list for downstream consumers"""
        return {'executed_components': self._last_executed_components.copy()}

    def record_feedback(self, query: str, intent: IntentType, components: List[str], rating: str, notes: str = "") -> Optional[str]:
        """
        PHASE 4: Record user feedback for recursive learning

        Args:
            query: The original query
            intent: Classified intent type
            components: Components that were executed
            rating: "good", "noisy", or "missing"
            notes: Optional notes about the feedback

        Returns:
            Feedback ID if recorded, None if error
        """
        from holo_index.feedback_learner import FeedbackRating, FeedbackDimensions

        # Map string rating to enum
        rating_map = {
            "good": FeedbackRating.GOOD,
            "noisy": FeedbackRating.NOISY,
            "missing": FeedbackRating.MISSING
        }

        feedback_rating = rating_map.get(rating.lower())
        if not feedback_rating:
            self._log_chain_of_thought("FEEDBACK-ERROR", f"Invalid rating: {rating}")
            return None

        # For advanced ratings, parse dimensions from notes
        dimensions = None
        if "relevance:" in notes.lower():
            # Parse dimension scores from notes (format: "relevance:0.8 noise:0.2 ...")
            dimensions = self._parse_feedback_dimensions(notes)

        # Record feedback
        feedback_id = self.feedback_learner.record_feedback(
            query=query,
            intent=intent,
            components_executed=components,
            rating=feedback_rating,
            dimensions=dimensions,
            notes=notes
        )

        if feedback_id:
            self._log_chain_of_thought("FEEDBACK-RECORDED", f"[OK] Feedback recorded: {feedback_id}")

            # BREADCRUMB EVENT: Feedback learning
            self.breadcrumb_tracer.add_action(
                'feedback_learning',
                f"feedback_{rating}",
                f"Recorded {rating} feedback for {len(components)} components",
                query
            )

        return feedback_id

    def _parse_feedback_dimensions(self, notes: str) -> Optional[object]:
        """Parse FeedbackDimensions from notes string"""
        from holo_index.feedback_learner import FeedbackDimensions
        import re

        try:
            # Extract dimension scores (format: "relevance:0.8 noise:0.2 completeness:0.9 efficiency:0.7")
            relevance = float(re.search(r'relevance:(\d+\.?\d*)', notes, re.I).group(1)) if re.search(r'relevance:', notes, re.I) else 0.5
            noise_level = float(re.search(r'noise:(\d+\.?\d*)', notes, re.I).group(1)) if re.search(r'noise:', notes, re.I) else 0.5
            completeness = float(re.search(r'completeness:(\d+\.?\d*)', notes, re.I).group(1)) if re.search(r'completeness:', notes, re.I) else 0.5
            token_efficiency = float(re.search(r'efficiency:(\d+\.?\d*)', notes, re.I).group(1)) if re.search(r'efficiency:', notes, re.I) else 0.5

            return FeedbackDimensions(
                relevance=relevance,
                noise_level=noise_level,
                completeness=completeness,
                token_efficiency=token_efficiency
            )
        except Exception as e:
            self._log_chain_of_thought("FEEDBACK-PARSE-ERROR", f"Failed to parse dimensions: {e}")
            return None

    def _extract_files_from_results(self, search_results: Dict[str, Any]) -> List[str]:
        """Extract file paths from HoloIndex search results"""
        files: List[str] = []
        for category in ('code', 'wsps'):
            hits = search_results.get(category) or []
            for hit in hits:
                file_path: Optional[str] = None
                if category == 'code':
                    file_path = hit.get('location')
                else:
                    file_path = hit.get('path')
                if file_path and file_path not in files:
                    files.append(file_path)
        return files

    def _extract_modules_from_files(self, files: List[str]) -> List[str]:
        """Extract module names from file paths"""
        modules: set[str] = set()
        for file_path in files:
            module = self._extract_module_from_path(file_path)
            if module:
                modules.add(module)
        return list(modules)

    def _extract_module_from_path(self, file_path: str) -> Optional[str]:
        """Extract module name from file path"""
        path_parts = Path(file_path).parts
        if 'modules' in path_parts:
            try:
                idx = path_parts.index('modules')
                if idx + 2 < len(path_parts):
                    return f"modules/{path_parts[idx + 1]}/{path_parts[idx + 2]}"
            except ValueError:
                pass
        if 'holo_index' in path_parts:
            try:
                idx = path_parts.index('holo_index')
                if idx + 1 < len(path_parts):
                    return f"holo_index/{path_parts[idx + 1]}"
            except ValueError:
                pass
        return None

    def _detect_query_intent(self, query: str) -> str:
        """Detect the primary intent of the query for smarter output"""
        lower_query = query.lower()

        # Error fixing takes priority - no health checks needed
        error_keywords = ['error', 'exception', 'traceback', 'fix', 'bug', 'crash',
                         'nonetype', 'attribute', 'failed', 'broken']
        if any(kw in lower_query for kw in error_keywords):
            return "fix_error"

        # WSP documentation management takes precedence - surgical WSP compliance checking
        wsp_keywords = ['wsp', 'windsurf', 'protocol', 'compliance', 'documentation', 'readme', 'modlog']
        if any(kw in lower_query for kw in wsp_keywords):
            return "wsp_manage"

        # Code location request - minimal output
        locate_keywords = ['where', 'find', 'location', 'which file', 'line']
        if any(kw in lower_query for kw in locate_keywords):
            return "locate_code"

        # Regex patterns indicate code search - treat as locate_code for surgical output
        if '.*' in query or '|' in query or '\\' in query or '[' in query:
            return "locate_code"

        # Module exploration - show health
        explore_keywords = ['module', 'structure', 'architecture', 'health', 'status']
        if any(kw in lower_query for kw in explore_keywords):
            return "explore"

        # Default to standard
        return "standard"

    def _build_orchestration_context(
        self,
        query: str,
        files: List[str],
        modules: List[str],
        intent: IntentType = None
    ) -> Dict[str, Any]:
        """
        Build context dictionary for orchestration decisions

        ENHANCEMENT (2025-10-07): Added intent parameter for new classification system
        """
        lower_query = query.lower()

        # Use new intent if provided, otherwise fall back to legacy detection
        if intent is None:
            legacy_intent = self._detect_query_intent(query)
        else:
            legacy_intent = self._map_intent_to_legacy(intent)

        # Only check health if intent is MODULE_HEALTH or GENERAL
        should_check_health = (
            intent in [IntentType.MODULE_HEALTH, IntentType.GENERAL] if intent
            else (legacy_intent == "explore" or 'health' in lower_query)
        )

        return {
            "query": query,
            "query_intent": legacy_intent,  # Legacy field for backward compat
            "intent_type": intent,  # New field for intent-based routing
            "files_count": len(files),
            "modules_count": len(modules),
            "query_keywords": lower_query.split(),
            "is_search_request": True,
            "has_files": bool(files),
            "has_modules": bool(modules),
            "query_contains_health": should_check_health,
            "query_contains_vibecoding": any(kw in lower_query for kw in ['vibe', 'pattern', 'behavior', 'coach']),
            "query_contains_module": any(kw in lower_query for kw in ['module', 'create', 'refactor']),
            "query_contains_error": any(kw in lower_query for kw in ['error', 'fix', 'debug', 'issue']),
            "query_contains_wsp": any(kw in lower_query for kw in ['wsp', 'windsurf', 'protocol', 'compliance', 'documentation']),
        }

    # WSP 62 Refactoring: Orchestration decision logic extracted to src/intent_response_processor.py
    # Extracted: _get_orchestration_decisions

    def _get_orchestration_decisions_for_components(
        self,
        context: Dict[str, Any],
        allowed_components: List[str]
    ) -> List[Dict[str, Any]]:
        """
        ENHANCEMENT (2025-10-07): Get orchestration decisions for specific components only

        This method filters component execution based on intent-driven routing.
        Only components in allowed_components list are considered.

        Args:
            context: Orchestration context dictionary
            allowed_components: List of component names to consider

        Returns:
            List of orchestration decisions for allowed components only
        """
        # Get all decisions
        all_decisions = self.intent_processor._get_orchestration_decisions(context)

        # Filter to only allowed components
        filtered_decisions = [
            decision for decision in all_decisions
            if decision['component_name'] in allowed_components
        ]

        return filtered_decisions

    def _map_intent_to_legacy(self, intent: IntentType) -> str:
        """
        ENHANCEMENT (2025-10-07): Map new IntentType to legacy intent strings

        For backward compatibility with existing output filter system.

        Args:
            intent: New IntentType enum

        Returns:
            Legacy intent string
        """
        intent_mapping = {
            IntentType.DOC_LOOKUP: "wsp_manage",
            IntentType.CODE_LOCATION: "locate_code",
            IntentType.MODULE_HEALTH: "explore",
            IntentType.RESEARCH: "explore",
            IntentType.GENERAL: "standard"
        }

        return intent_mapping.get(intent, "standard")

    def _execute_orchestrated_analysis(
        self,
        query: str,
        files: List[str],
        modules: List[str],
        decisions: List[Dict[str, Any]],
    ) -> str:
        """Execute the orchestrated analysis components."""
        report_lines: List[str] = [f"[HOLODAE-INTELLIGENCE] Data-driven analysis for query: '{query}'"]
        unique_modules = sorted({module for module in modules if module})
        module_snapshots = {module: self.wsp_guardian._build_module_snapshot(module) for module in unique_modules}
        self._last_module_snapshots = module_snapshots
        report_lines.append(
            f"[SEMANTIC] {len(files)} files across {len(unique_modules)} modules"
        )

        if not unique_modules:
            report_lines.append("[HOLODAE-CONTEXT] No module directories resolved from search results")

        executed_components: List[str] = []
        for decision in decisions:
            component_name = decision["component_name"]
            display_name = self._format_component_display(component_name)
            results = self._execute_component_stub(
                component_name, query, files, unique_modules, module_snapshots
            )
            if results:
                executed_components.append(display_name)
                report_lines.extend(results)
                self._log_chain_of_thought("PERFORMANCE", f"{display_name} executed with results")

        self._last_executed_components = executed_components
        if executed_components:
            report_lines.append(
                f"[HOLODAE-ORCHESTRATION] Executed components: {', '.join(executed_components)}"
            )
        else:
            report_lines.append(
                "[HOLODAE-ORCHESTRATION] No components produced actionable output"
            )
        return '\n'.join(report_lines)

    @staticmethod
    def _format_component_display(component_name: str) -> str:
        """Format component name for display (snake_case -> Title Case)."""
        return component_name.replace("_", " ").title()

    def _execute_component_stub(
        self,
        component_name: str,
        query: str,
        files: List[str],
        modules: List[str],
        module_snapshots: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Execute a named analysis component using lightweight heuristics."""
        if component_name == "health_analysis":
            return self._run_health_analysis(module_snapshots)
        if component_name == "vibecoding_analysis":
            return self._run_vibecoding_analysis(module_snapshots)
        if component_name == "file_size_monitor":
            return self._run_file_size_monitor(files, module_snapshots)
        if component_name == "module_analysis":
            return self._run_module_analysis(module_snapshots)
        if component_name == "pattern_coach":
            return self._run_pattern_coach(module_snapshots)
        if component_name == "orphan_analysis":
            return self._run_orphan_analysis(module_snapshots)
        if component_name == "wsp_documentation_guardian":
            return self.wsp_guardian._run_wsp_documentation_guardian(query, files, modules, module_snapshots)
        return []

    def _run_health_analysis(self, module_snapshots: Dict[str, Dict[str, Any]]) -> List[str]:
        if not module_snapshots:
            return []  # WSP 87 noise reduction: Empty output when nothing to report
        lines: List[str] = []
        violation_count = 0
        ok_count = 0
        for module, snapshot in module_snapshots.items():
            if not snapshot['exists']:
                lines.append(f"[HEALTH][WARNING] FOUND missing module on disk: {module}")
                violation_count += 1
                continue
            missing_docs = snapshot['missing_docs']
            if missing_docs:
                lines.append(
                    f"[HEALTH][VIOLATION] {module} missing {', '.join(missing_docs)} (WSP 22)"
                )
                violation_count += 1
            else:
                ok_count += 1
        # WSP 87 noise reduction: Suppress individual OK messages.
        # Only show a compact summary when all modules are healthy.
        if ok_count > 0 and violation_count == 0:
            lines.append(f"[HEALTH][OK] All {ok_count} modules compliant")
        elif ok_count > 0:
            lines.append(f"[HEALTH] {ok_count}/{ok_count + violation_count} modules compliant")
        return lines

    def _run_vibecoding_analysis(self, module_snapshots: Dict[str, Dict[str, Any]]) -> List[str]:
        lines: List[str] = []
        for module, snapshot in module_snapshots.items():
            if not snapshot['exists']:
                continue
            py_count = snapshot['py_file_count']
            tests = snapshot['test_count']
            if py_count == 0:
                continue
            coverage = tests / py_count
            if tests == 0 and py_count >= 3:
                lines.append(
                    f"[PATTERN] Found {py_count} implementation files with 0 tests in {module} (coverage 0%)"
                )
            elif coverage < 0.2 and py_count >= 5:
                lines.append(
                    f"[PATTERN] Low coverage {coverage:.0%} in {module} ({tests} tests across {py_count} files)"
                )
        if not lines:
            lines.append("[VIBECODING-PATTERN] No high-risk vibecoding patterns detected")
        return lines

    def _run_file_size_monitor(
        self,
        files: List[str],
        module_snapshots: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        lines: List[str] = []
        flagged: set[str] = set()
        for snapshot in module_snapshots.values():
            if not snapshot['exists']:
                continue
            for py_file, line_count, size_kb in snapshot['large_python_files']:
                rel = self._relative_path(py_file)
                if rel in flagged:
                    continue
                lines.append(
                    f"[SIZE][WARNING] FOUND large file {rel} ({line_count} lines, {size_kb} KB)"
                )
                flagged.add(rel)
        for file_path in files:
            resolved = self._resolve_file_path(file_path)
            if not resolved or not resolved.exists():
                continue
            rel = self._relative_path(resolved)
            if rel in flagged:
                continue
            size_kb = max(1, resolved.stat().st_size // 1024)
            if resolved.suffix == '.py':
                line_count = self._count_file_lines(resolved)
                if line_count > 400 or size_kb > 120:
                    lines.append(
                        f"[SIZE][WARNING] FOUND large file {rel} ({line_count} lines, {size_kb} KB)"
                    )
                    flagged.add(rel)
            elif size_kb > 256:
                lines.append(
                    f"[SIZE][NOTICE] FOUND large artifact {rel} ({size_kb} KB)"
                )
                flagged.add(rel)
        if not lines:
            lines.append("[HOLODAE-SIZE][OK] No file size anomalies detected")
        return lines

    def _run_module_analysis(self, module_snapshots: Dict[str, Dict[str, Any]]) -> List[str]:
        lines: List[str] = []
        for module, snapshot in module_snapshots.items():
            if not snapshot['exists']:
                continue
            py_count = snapshot['py_file_count']
            tests = snapshot['test_count']
            lines.append(
                f"[MODULE][FOUND] {module} contains {py_count} python files with {tests} tests"
            )
            if snapshot['missing_docs']:
                lines.append(
                    f"[MODULE][WARNING] {module} missing {', '.join(snapshot['missing_docs'])}"
                )
            if snapshot['large_python_files']:
                rel = self._relative_path(snapshot['large_python_files'][0][0])
                lines.append(
                    f"[MODULE][WARNING] Large implementation file detected: {rel}"
                )
        if not lines:
            lines.append("[HOLODAE-MODULE][OK] Modules within healthy structural bounds")
        return lines

    def _run_pattern_coach(self, module_snapshots: Dict[str, Dict[str, Any]]) -> List[str]:
        lines: List[str] = []
        for module, snapshot in module_snapshots.items():
            if not snapshot['exists']:
                continue
            if snapshot['missing_docs']:
                lines.append(
                    f"[PATTERN] Found documentation gap in {module}: {', '.join(snapshot['missing_docs'])}"
                )
            if snapshot['script_orphans']:
                samples = ', '.join(
                    self._relative_path(path) for path in snapshot['script_orphans'][:2]
                )
                lines.append(
                    f"[PATTERN] Found {len(snapshot['script_orphans'])} scripts lacking tests in {module}: {samples}"
                )
        if not lines:
            lines.append("[PATTERN-COACH] Patterns stable - no interventions required")
        return lines

    def _run_orphan_analysis(self, module_snapshots: Dict[str, Dict[str, Any]]) -> List[str]:
        lines: List[str] = []
        for module, snapshot in module_snapshots.items():
            if not snapshot['exists']:
                continue
            orphans = snapshot['script_orphans']
            for orphan in orphans[:3]:
                rel = self._relative_path(orphan)
                lines.append(f"[ORPHAN-FOUND] {rel} lacks matching tests - investigate connection")
            if len(orphans) > 3:
                lines.append(
                    f"[ORPHAN-SUMMARY] {len(orphans)} potential orphan scripts detected in {module}"
                )
        if not lines:
            lines.append("[ORPHAN-ANALYSIS][OK] No orphaned scripts identified")
        return lines

    # WSP 62 Refactoring: WSP Documentation Guardian methods extracted to src/wsp_documentation_guardian.py
    # Extracted methods: _run_wsp_documentation_guardian, _is_doc_only_path, _sanitize_ascii_content,
    # _execute_wsp_remediation_pipeline, rollback_ascii_changes, _log_rollback_to_remediation_log, _build_module_snapshot

    def _resolve_module_path(self, module: str) -> Optional[Path]:
        if not module:
            return None
        candidate = (self.repo_root / module).resolve()
        if candidate.exists():
            return candidate
        return None

    def _resolve_file_path(self, file_path: str) -> Optional[Path]:
        if not file_path:
            return None
        candidate = Path(file_path)
        if candidate.is_absolute() and candidate.exists():
            return candidate
        candidate = (self.repo_root / file_path).resolve()
        return candidate if candidate.exists() else None

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.repo_root))
        except Exception:
            return str(path)

    def _count_file_lines(self, path: Path) -> int:
        try:
            with path.open('r', encoding='utf-8', errors='ignore') as handle:
                return sum(1 for _ in handle)
        except OSError:
            return 0

    def _calculate_analysis_effectiveness(self, report: str) -> float:
        lines = report.split('\n')
        result_lines = [
            line
            for line in lines
            if any(keyword in line.upper() for keyword in ['FOUND', 'DETECTED', 'VIOLATION', 'PATTERN', 'OK', 'HEALTH'])
        ]
        return min(1.0, len(result_lines) / max(1, len(lines) * 0.3))

    def _log_chain_of_thought(self, step_type: str, message: str) -> None:
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [BOT][AI] [QWEN-{step_type}] {message}"
        self.chain_of_thought_log.append({
            'timestamp': datetime.now(),
            'type': step_type,
            'message': message,
        })
        self.logger.info(log_entry)
        # WSP 87 noise reduction: Only print chain-of-thought to stdout in verbose mode.
        # Default: log to file/logger only. Reduces ~20-30 lines of console noise per query.
        verbose = os.getenv('HOLO_VERBOSE', '').lower() in {'1', 'true', 'yes'}
        if verbose:
            try:
                print(log_entry)
            except UnicodeEncodeError:
                sys.stdout.buffer.write((log_entry + '\n').encode('utf-8', errors='replace'))

    def get_analysis_context(self) -> Dict[str, Any]:
        return {
            'files': self._last_files.copy(),
            'modules': self._last_modules.copy(),
            'executed_components': self._last_executed_components.copy(),
        }

    def get_chain_of_thought_summary(self) -> Dict[str, Any]:
        return {
            'total_steps': len(self.chain_of_thought_log),
            'step_types': list({entry['type'] for entry in self.chain_of_thought_log[-20:]}),
            'recent_activity': [entry['message'] for entry in self.chain_of_thought_log[-5:]],
            'avg_effectiveness': sum(self.performance_history[-10:]) / max(1, len(self.performance_history[-10:])),
        }
