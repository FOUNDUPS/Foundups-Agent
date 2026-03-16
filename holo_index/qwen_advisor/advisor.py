# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import io



import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cache import AdvisorCache
from .config import QwenAdvisorConfig
from .llm_engine import QwenInferenceEngine
from .pattern_coach import PatternCoach
from .wsp_master import WSPMaster
from .prompts import build_compliance_prompt
from .telemetry import record_advisor_event
from .rules_engine import ComplianceRulesEngine

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

logger = logging.getLogger(__name__)


@dataclass
class AdvisorContext:
    """Inputs collected from HoloIndex search results."""

    query: str
    code_hits: List[Dict[str, Any]]
    wsp_hits: List[Dict[str, Any]]


@dataclass
class AdvisorResult:
    """Structured advisor response consumed by the CLI."""

    guidance: str
    reminders: List[str]
    todos: List[str]
    metadata: Dict[str, Any]


class QwenAdvisor:
    """Qwen-backed advisor with LLM intelligence.

    Uses local Qwen 1.5B coder model for intelligent code analysis and guidance,
    with rules engine fallback for compliance checking.
    """

    def __init__(
        self,
        config: Optional[QwenAdvisorConfig] = None,
        cache: Optional[AdvisorCache] = None,
    ) -> None:
        self.config = config or QwenAdvisorConfig.from_env()
        self.cache = cache or AdvisorCache(enabled=self.config.cache_enabled)
        self.rules_engine = ComplianceRulesEngine()  # Initialize rules engine

        # Initialize LLM engine for intelligent analysis
        self.llm_engine = QwenInferenceEngine(
            model_path=self.config.model_path,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )

        # Initialize WSP Master for comprehensive protocol guidance
        self.wsp_master = WSPMaster()

        # Initialize Pattern Coach for intelligent behavioral coaching
        self.pattern_coach = PatternCoach()
        self.pattern_coach.set_wsp_master(self.wsp_master)

        # Troubleshooting pattern database
        self.troubleshooting_db = self._build_troubleshooting_db()

    def detect_file_movements_and_compliance(self, context: AdvisorContext) -> Dict[str, Any]:
        """
        NEW: Detect file movements and provide WSP compliance guidance.

        Analyzes context for signs of file movements and ensures 0102 discoverability.
        Returns guidance for proper WSP compliance after file operations.
        """
        guidance = {
            'file_movements_detected': [],
            'wsp_violations': [],
            'documentation_updates_needed': [],
            'navigation_updates_needed': [],
            '0102_discoverability_score': 1.0
        }

        # Detect file movement patterns in query
        movement_indicators = ['move', 'moved', 'refactor', 'relocate', 'organize', 'wsp']
        if any(indicator in context.query.lower() for indicator in movement_indicators):
            guidance['file_movements_detected'].append('Query indicates file movement operation')

        # Check code hits for moved files
        for hit in context.code_hits:
            path = hit.get('path', hit.get('file_path', ''))
            if path and ('moved' in path.lower() or 'refactor' in path.lower()):
                guidance['file_movements_detected'].append(f"File movement detected: {path}")

        # WSP compliance analysis
        if guidance['file_movements_detected']:
            guidance['wsp_violations'].append('WSP VIOLATION: Files moved without 0102 indexing verification')
            guidance['documentation_updates_needed'].extend([
                'Update module README.md to document moved files',
                'Verify files are indexed in navigation system',
                'Check WSP knowledge base for proper documentation'
            ])
            guidance['navigation_updates_needed'].extend([
                'Add moved files to modules/infrastructure/navigation/src/navigation.py NEED_TO dictionary',
                'Ensure 0102 agents can discover moved files through navigation system'
            ])
            guidance['0102_discoverability_score'] = 0.3  # Low score indicates potential issues

        return guidance

    def detect_integration_gaps(self, context: AdvisorContext) -> Dict[str, Any]:
        """
        HOLOINDEX IMPROVEMENT OPPORTUNITY #1: Integration Gap Detection

        Detect when Module A monitors state but Module B could act on it,
        but NO CONNECTION exists between A->B.

        Example: QuotaAwarePoller monitors quota but TokenManager.rotate() exists
        but no integration between them.
        """
        gaps = {
            'detected_gaps': [],
            'missing_connections': [],
            'recommended_integrations': [],
            'confidence_score': 1.0
        }

        # Step 1: Extract modules and their capabilities from search results
        monitoring_modules = {}
        action_modules = {}

        for hit in context.code_hits:
            path = hit.get('path', hit.get('file_path', ''))
            content = hit.get('content', hit.get('preview', ''))

            # Detect monitoring patterns (Module A - monitors state)
            if any(keyword in content.lower() for keyword in [
                'monitor', 'check', 'quota', 'usage', 'status', 'health', 'alert'
            ]):
                module_name = self._extract_module_name(path)
                if module_name not in monitoring_modules:
                    monitoring_modules[module_name] = {'path': path, 'capabilities': []}
                monitoring_modules[module_name]['capabilities'].append('monitoring')

            # Detect action patterns (Module B - can act on state)
            if any(keyword in content.lower() for keyword in [
                'rotate', 'switch', 'change', 'update', 'reset', 'refresh', 'cleanup'
            ]):
                module_name = self._extract_module_name(path)
                if module_name not in action_modules:
                    action_modules[module_name] = {'path': path, 'capabilities': []}
                action_modules[module_name]['capabilities'].append('action')

        # Step 2: Analyze for integration gaps
        for monitor_name, monitor_info in monitoring_modules.items():
            monitor_path = monitor_info['path']

            # Look for potential action partners
            for action_name, action_info in action_modules.items():
                if monitor_name == action_name:
                    continue  # Same module, not a gap

                action_path = action_info['path']

                # Check if there's any connection between modules
                connection_exists = self._check_module_connection(monitor_path, action_path, context)

                if not connection_exists:
                    # Detect specific integration gap patterns
                    gap_type = self._classify_integration_gap(monitor_path, action_path)

                    if gap_type:
                        gap = {
                            'type': gap_type,
                            'monitoring_module': monitor_name,
                            'action_module': action_name,
                            'monitor_path': monitor_path,
                            'action_path': action_path,
                            'severity': 'HIGH' if 'quota' in monitor_path.lower() else 'MEDIUM'
                        }

                        gaps['detected_gaps'].append(gap)
                        gaps['missing_connections'].append(
                            f"{monitor_name} -> {action_name} (no integration detected)"
                        )

                        # Generate specific recommendations
                        recommendation = self._generate_integration_recommendation(gap)
                        if recommendation:
                            gaps['recommended_integrations'].append(recommendation)

        # Adjust confidence based on gap detection quality
        if gaps['detected_gaps']:
            gaps['confidence_score'] = 0.8  # High confidence when gaps found
        else:
            gaps['confidence_score'] = 0.9  # High confidence when no gaps (good integration)

        return gaps

    def _extract_module_name(self, path: str) -> str:
        """Extract module name from file path."""
        parts = path.split('/')
        # Look for modules/ pattern
        if 'modules' in parts:
            modules_idx = parts.index('modules')
            if modules_idx + 2 < len(parts):
                return f"{parts[modules_idx+1]}.{parts[modules_idx+2]}"
        return path.split('/')[-2] if '/' in path else 'unknown'

    def _check_module_connection(self, monitor_path: str, action_path: str, context: AdvisorContext) -> bool:
        """Check if there's any connection between two modules in the codebase."""
        # Look for imports, function calls, or references between modules
        monitor_module = self._extract_module_name(monitor_path)
        action_module = self._extract_module_name(action_path)

        for hit in context.code_hits:
            content = hit.get('content', hit.get('preview', ''))
            # Check for cross-module references
            if monitor_module in content and action_module in content:
                return True

        return False

    def _classify_integration_gap(self, monitor_path: str, action_path: str) -> Optional[str]:
        """Classify the type of integration gap detected."""
        monitor_lower = monitor_path.lower()
        action_lower = action_path.lower()

        # Quota monitoring -> Token rotation gap
        if ('quota' in monitor_lower or 'poller' in monitor_lower) and ('token' in action_lower or 'oauth' in action_lower):
            return 'QUOTA_TOKEN_ROTATION_GAP'

        # Health monitoring -> Cleanup action gap
        if 'health' in monitor_lower and ('cleanup' in action_lower or 'reset' in action_lower):
            return 'HEALTH_MAINTENANCE_GAP'

        # Generic monitoring -> action gap
        if ('monitor' in monitor_lower or 'check' in monitor_lower) and ('rotate' in action_lower or 'switch' in action_lower):
            return 'MONITORING_ACTION_GAP'

        return None

    def _generate_integration_recommendation(self, gap: Dict[str, Any]) -> Optional[str]:
        """Generate specific integration recommendations."""
        gap_type = gap['type']

        if gap_type == 'QUOTA_TOKEN_ROTATION_GAP':
            return f"INTEGRATION: Add token rotation to {gap['monitoring_module']} when quota >95%. Pass token_manager to __init__ and call rotate() in calculate_optimal_interval()"

        elif gap_type == 'HEALTH_MAINTENANCE_GAP':
            return f"INTEGRATION: Connect {gap['monitoring_module']} health checks to {gap['action_module']} cleanup actions"

        elif gap_type == 'MONITORING_ACTION_GAP':
            return f"INTEGRATION: Connect {gap['monitoring_module']} state monitoring to {gap['action_module']} corrective actions"

        return None

    def _generate_work_context_map(self, context: AdvisorContext) -> Optional[Dict[str, Any]]:
        """
        Generate a real-time work context map showing what 0102 is currently working on.

        This analyzes multiple signals:
        - Query content (what the agent is asking about)
        - Recent code changes (what files are being modified)
        - Module relationships (what's connected to current work)
        - Task patterns (what type of work is being done)
        """
        try:
            work_map = {
                'current_task': 'Unknown',
                'active_module': 'Unknown',
                'exact_location': 'Unknown',
                'related_modules': [],
                'task_type': 'unknown',
                'confidence': 0.0
            }

            # Signal 1: Analyze query content for current task
            query_lower = context.query.lower()
            if any(kw in query_lower for kw in ['quota', 'token', 'oauth', 'rotation']):
                work_map['current_task'] = 'OAuth Token Rotation Integration'
                work_map['task_type'] = 'integration'
                work_map['active_module'] = 'communication.livechat'
                work_map['related_modules'] = ['platform_integration.utilities.oauth_management']
                work_map['confidence'] = 0.9
            elif any(kw in query_lower for kw in ['greeting', 'spam', 'session']):
                work_map['current_task'] = 'Bot Greeting Optimization'
                work_map['task_type'] = 'optimization'
                work_map['active_module'] = 'communication.livechat'
                work_map['confidence'] = 0.8
            elif any(kw in query_lower for kw in ['holo', 'index', 'search']):
                work_map['current_task'] = 'HoloIndex Enhancement'
                work_map['task_type'] = 'enhancement'
                work_map['active_module'] = 'holo_index'
                work_map['confidence'] = 0.7

            # Signal 2: Analyze code hits for active modules
            if context.code_hits:
                # Find most recently modified files
                active_files = []
                for hit in context.code_hits:
                    path = hit.get('path', hit.get('file_path', ''))
                    if path:
                        active_files.append(path)

                if active_files:
                    # Extract module from most active file
                    primary_file = active_files[0]
                    work_map['active_module'] = self._extract_module_name(primary_file)

                    # Set exact location if we can determine it
                    if len(active_files) == 1:
                        work_map['exact_location'] = f"{primary_file}"

            # Signal 3: Check breadcrumb tracer for recent activity
            try:
                from ..adaptive_learning.breadcrumb_tracer import BreadcrumbTracer
                tracer = BreadcrumbTracer()
                recent_tasks = tracer.get_recent_tasks(limit=1)
                if recent_tasks:
                    recent_task = recent_tasks[0]
                    work_map['current_task'] = recent_task.get('description', work_map['current_task'])
                    work_map['confidence'] = min(1.0, work_map['confidence'] + 0.2)
            except Exception:
                pass  # Breadcrumb tracer not available

            # Only return if we have reasonable confidence
            if work_map['confidence'] >= 0.5:
                return work_map
            else:
                return None

        except Exception as e:
            logger.warning(f"Failed to generate work context map: {e}")
            return None

    def generate_guidance(self, context: AdvisorContext, enable_dae_cube_mapping: bool = False, enable_function_indexing: bool = False) -> AdvisorResult:
        """Generate intelligent guidance using WSP Master, LLM, and Pattern Coach.

        WSP 97 Refactored: Extracted into 4 phases per Occam's Layer Discipline.
        """
        # PHASE 1: Check cache
        cache_key = self.cache.make_key(context.query, {"code": len(context.code_hits), "wsp": len(context.wsp_hits)})
        cube_tags = sorted({hit.get('cube') for hit in context.code_hits + context.wsp_hits if hit and hit.get('cube')})
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug("Advisor cache hit for query: %s", context.query)
            return AdvisorResult(**cached)

        # PHASE 2: Pre-analysis (file movement, integration gaps, troubleshooting)
        pre_analysis = self._run_pre_analysis(context)

        # PHASE 3: Core analysis (WSP, LLM, rules engine)
        core_analysis = self._run_core_analysis(context)
        prompt = core_analysis['prompt']

        # PHASE 4: Synthesize and build result
        return self._build_guidance_result(
            context, pre_analysis, core_analysis, cube_tags, cache_key, prompt,
            enable_dae_cube_mapping, enable_function_indexing
        )

    def _run_pre_analysis(self, context: AdvisorContext) -> Dict[str, Any]:
        """Run pre-analysis phase: file movement, integration gaps, troubleshooting."""
        result = {
            'file_movement_analysis': {},
            'integration_gaps': None,
            'troubleshooting_guidance': ""
        }

        # File Movement Detection & WSP Compliance
        result['file_movement_analysis'] = self.detect_file_movements_and_compliance(context)
        if result['file_movement_analysis']['file_movements_detected']:
            logger.info("[CYCLE] File movement detected - initiating WSP compliance verification")

        # Integration Gap Detection
        logger.info("[INTEGRATION-GAP] Starting integration gap detection analysis")
        integration_gap_analysis = self.detect_integration_gaps(context)
        logger.info(f"[INTEGRATION-GAP] Analysis complete - Found {len(integration_gap_analysis.get('detected_gaps', []))} gaps")
        if integration_gap_analysis['detected_gaps']:
            logger.info("[LINK] Integration gaps detected - Module A monitors but Module B can't act")
            for gap in integration_gap_analysis['detected_gaps']:
                logger.info(f"[GAP] {gap['type']}: {gap['monitoring_module']} -> {gap['action_module']}")
            result['integration_gaps'] = integration_gap_analysis

        # Troubleshooting Pattern Recognition
        troubleshooting_patterns = self._detect_troubleshooting_patterns(context.query)
        if troubleshooting_patterns:
            logger.info("[TOOL] Troubleshooting patterns detected: %s", list(troubleshooting_patterns.keys()))
            result['troubleshooting_guidance'] = self._generate_troubleshooting_guidance(troubleshooting_patterns)

        return result

    def _run_core_analysis(self, context: AdvisorContext) -> Dict[str, Any]:
        """Run core analysis phase: WSP, LLM, rules engine."""
        result = {
            'wsp_analysis': None,
            'llm_analysis': None,
            'rules_guidance': {},
            'unicode_check': None,
            'prompt': ""
        }

        # WSP Master Analysis
        result['wsp_analysis'] = self.wsp_master.analyze_query(context.query, context.code_hits)

        # Unicode/emojis preventive warnings (WSP 20)
        if any(kw in context.query.lower() for kw in ["code", "implement", "python"]):
            result['unicode_check'] = self.wsp_master.check_unicode_violation(context.query, "query")
            if result['unicode_check']["preventive_warning"]:
                if "WSP_20" not in result['wsp_analysis'].suggested_wsps:
                    result['wsp_analysis'].suggested_wsps.append("WSP_20")
                    result['wsp_analysis'].wsp_relevance["WSP_20"] = 0.7

        logger.debug("WSP Master analysis completed: intent=%s, risk=%s",
                    result['wsp_analysis'].intent_category, result['wsp_analysis'].risk_level)

        # LLM Analysis
        result['prompt'] = build_compliance_prompt(context.query, context.code_hits, context.wsp_hits)
        try:
            result['llm_analysis'] = self.llm_engine.analyze_code_context(
                query=context.query,
                code_snippets=[hit.get('content', '')[:500] for hit in context.code_hits[:5]],
                wsp_guidance=[hit.get('content', '')[:300] for hit in context.wsp_hits[:3]]
            )
            logger.debug("LLM analysis completed successfully")
        except Exception as e:
            logger.warning(f"LLM analysis failed, falling back to rules engine: {e}")

        # Rules Engine Fallback
        result['rules_guidance'] = self.rules_engine.generate_contextual_guidance(
            context.query,
            context.code_hits,
            {"wsp_hits": context.wsp_hits}
        )

        return result

    def _build_guidance_result(
        self, context: AdvisorContext, pre_analysis: Dict[str, Any],
        core_analysis: Dict[str, Any], cube_tags: List[str], cache_key: str, prompt: str,
        enable_dae_cube_mapping: bool, enable_function_indexing: bool
    ) -> AdvisorResult:
        """Build final guidance result from all analyses."""
        wsp_analysis = core_analysis['wsp_analysis']
        llm_analysis = core_analysis['llm_analysis']
        rules_guidance = core_analysis['rules_guidance']
        unicode_check = core_analysis['unicode_check']
        file_movement_analysis = pre_analysis['file_movement_analysis']

        # Synthesize guidance
        guidance = self._synthesize_guidance(
            llm_analysis, wsp_analysis, rules_guidance,
            pre_analysis['troubleshooting_guidance'],
            pre_analysis['integration_gaps'],
            context, enable_dae_cube_mapping, enable_function_indexing
        )
        todos = self._synthesize_todos(llm_analysis, wsp_analysis, rules_guidance)
        reminders = self._synthesize_reminders(wsp_analysis, rules_guidance)

        # Apply Unicode warnings
        guidance, todos = self._apply_unicode_warnings(guidance, todos, unicode_check)

        # Add test-specific guidance
        if 'test' in context.query.lower():
            fmas_todo = "Review FMAS plan: WSP_framework/docs/testing/HOLOINDEX_QWEN_ADVISOR_FMAS_PLAN.md"
            if fmas_todo not in todos:
                todos.append(fmas_todo)

        # Apply file movement guidance
        guidance, todos = self._apply_file_movement_guidance(guidance, todos, file_movement_analysis)

        # Build metadata
        confidence = self._calculate_confidence(llm_analysis, wsp_analysis)
        violations = [f"[{v['wsp_reference']}] {v['guidance']}" for v in rules_guidance.get("violations", [])]

        result = AdvisorResult(
            guidance=guidance,
            reminders=reminders,
            todos=todos,
            metadata={
                "prompt": prompt,
                "model_path": str(self.config.model_path),
                "cache_key": cache_key,
                "cubes": cube_tags,
                "risk_level": wsp_analysis.risk_level,
                "violations": violations,
                "intent": {"category": wsp_analysis.intent_category, "prevention_focus": wsp_analysis.prevention_focus},
                "llm_used": llm_analysis is not None,
                "llm_confidence": confidence,
                "llm_model": llm_analysis.get("model_used") if llm_analysis else None,
                "wsp_analysis": {
                    "suggested_wsps": wsp_analysis.suggested_wsps,
                    "relevance_scores": wsp_analysis.wsp_relevance
                },
                "file_movement_analysis": file_movement_analysis,
            },
        )

        # Cache and record telemetry
        self.cache.set(cache_key, result.__dict__)
        record_advisor_event(self.config.telemetry_path, {
            "query": context.query,
            "reminder_count": len(reminders),
            "todo_count": len(todos),
            "cubes": cube_tags,
            "llm_used": llm_analysis is not None,
            "intent": wsp_analysis.intent_category,
            "risk_level": wsp_analysis.risk_level,
        })

        return result

    def _apply_unicode_warnings(self, guidance: str, todos: List[str], unicode_check: Optional[Dict]) -> tuple:
        """Apply Unicode preventive warnings to guidance and todos."""
        if unicode_check and unicode_check.get("preventive_warning"):
            unicode_todo = "WSP 20 PREVENTION: Avoid Unicode/emojis in future code - use ASCII alternatives like [OK], [ERROR], [TARGET]"
            if unicode_todo not in todos:
                todos.insert(0, unicode_todo)
            preventive_warning = f"\\n\\n{unicode_check['recommendation']}"
            guidance = (guidance + preventive_warning) if guidance else unicode_check['recommendation']
        return guidance, todos

    def _apply_file_movement_guidance(self, guidance: str, todos: List[str], file_movement_analysis: Dict) -> tuple:
        """Apply file movement compliance guidance."""
        if not file_movement_analysis.get('file_movements_detected'):
            return guidance, todos

        guidance += f"\n\n[CYCLE] FILE MOVEMENT DETECTED - WSP COMPLIANCE REQUIRED:\n"
        guidance += f"0102 Discoverability Score: {file_movement_analysis['0102_discoverability_score']:.1f}/1.0\n\n"

        if file_movement_analysis.get('wsp_violations'):
            guidance += "[ERROR] WSP VIOLATIONS:\n"
            for violation in file_movement_analysis['wsp_violations']:
                guidance += f"   - {violation}\n"

        if file_movement_analysis.get('documentation_updates_needed'):
            guidance += "\n[DOCS] REQUIRED DOCUMENTATION UPDATES:\n"
            for update in file_movement_analysis['documentation_updates_needed']:
                guidance += f"   - {update}\n"
                todos.append(update)

        if file_movement_analysis.get('navigation_updates_needed'):
            guidance += "\n[NAV] REQUIRED NAVIGATION UPDATES:\n"
            for update in file_movement_analysis['navigation_updates_needed']:
                guidance += f"   - {update}\n"
                todos.append(update)

        return guidance, todos

    def _synthesize_guidance(self, llm_analysis, wsp_analysis, rules_guidance, troubleshooting_guidance="", integration_gaps=None, context=None, enable_dae_cube_mapping=False, enable_function_indexing=False) -> str:
        """Synthesize guidance from all sources. WSP 97 refactored into modular sections."""
        logger.info(f"[CODE-INDEX-DEBUG] enable_dae_cube_mapping={enable_dae_cube_mapping}, enable_function_indexing={enable_function_indexing}")

        # PHASE 1: Determine output mode
        strict_mode = self._check_strict_mode(context)
        guidance_parts = []

        # PHASE 2: Add optional sections based on flags and mode
        self._add_cube_mapping_section(guidance_parts, context, wsp_analysis, enable_dae_cube_mapping, strict_mode)
        self._add_codeindex_section(guidance_parts, context, wsp_analysis, enable_function_indexing, strict_mode)

        # PHASE 3: Add troubleshooting if detected
        if troubleshooting_guidance and not strict_mode:
            guidance_parts.append(troubleshooting_guidance)
            guidance_parts.append("")

        # PHASE 4: Add integration gaps and work context
        self._add_integration_gap_section(guidance_parts, integration_gaps, strict_mode)
        self._add_work_context_section(guidance_parts, context, strict_mode)

        # PHASE 5: Add primary guidance (LLM/WSP/rules fallback)
        self._add_primary_guidance_section(guidance_parts, llm_analysis, wsp_analysis, rules_guidance)

        return " ".join(guidance_parts)

    def _check_strict_mode(self, context: Optional[AdvisorContext]) -> bool:
        """Determine if strict output limiting is needed to prevent truncation."""
        total_findings = 0
        if context:
            total_findings = len(context.code_hits) + len(context.wsp_hits)

        strict_mode = total_findings > 20
        if strict_mode:
            logger.info(f"[FIRST-PRINCIPLES] High volume results ({total_findings}) - applying strict output limiting")

        # Check for output truncation patterns
        if hasattr(self, '_detect_output_truncation_patterns') and context:
            truncation_detected = self._detect_output_truncation_patterns(context, total_findings)
            if truncation_detected:
                logger.info("[RECURSIVE] Output truncation pattern detected - enabling emergency limiting")
                strict_mode = True

        return strict_mode

    def _add_cube_mapping_section(self, guidance_parts: List[str], context, wsp_analysis, enabled: bool, strict_mode: bool) -> None:
        """Add DAE cube mapping section to guidance."""
        if not enabled or strict_mode:
            return

        cube_mapping = self._generate_dae_cube_mapping(context, wsp_analysis)
        if not cube_mapping:
            return

        guidance_parts.append("[CUBE-MAP] DAE CUBE MAPPING (WSP 80):")
        guidance_parts.append(f"  [BOUNDARY] Active Cube: {cube_mapping.get('active_cube', 'Unknown')}")
        guidance_parts.append(f"  [MODULES] Cube contains: {len(cube_mapping.get('modules', []))} modules")

        mermaid_flow = cube_mapping.get('mermaid_flow')
        if mermaid_flow and len(mermaid_flow) < 500:
            guidance_parts.append("  [FLOW] Mermaid System Flow:")
            guidance_parts.append("    ```mermaid")
            guidance_parts.append(f"    {mermaid_flow}")
            guidance_parts.append("    ```")
        guidance_parts.append("")

    def _add_codeindex_section(self, guidance_parts: List[str], context, wsp_analysis, enabled: bool, strict_mode: bool) -> None:
        """Add CodeIndex surgical analysis section to guidance."""
        if not enabled:
            return

        verbose_mode = os.getenv('HOLO_VERBOSE', '').lower() in {'1', 'true', 'yes'}
        if verbose_mode:
            print("[DEBUG] CODEINDEX: Starting comprehensive surgical analysis...")

        if not strict_mode:
            self._add_full_codeindex_analysis(guidance_parts, context)
        else:
            self._add_basic_codeindex_analysis(guidance_parts, context, wsp_analysis)

    def _add_full_codeindex_analysis(self, guidance_parts: List[str], context) -> None:
        """Add full CodeIndex surgical analysis (non-strict mode)."""
        # 1. SURGICAL CODE INDEX
        surgical_results = self.surgical_code_index(context)
        if surgical_results['exact_fixes']:
            guidance_parts.append("[SURGERY] SURGICAL CODE INDEX - EXACT FIX LOCATIONS:")
            for fix in surgical_results['exact_fixes'][:3]:
                guidance_parts.append(f"  [TARGET] {fix['function']} ({fix['line_range']}) - {fix['estimated_effort']}min effort")
                guidance_parts.append(f"     -> Lines {fix['start_line']}-{fix['end_line']} ({fix['end_line'] - fix['start_line'] + 1} lines)")
            guidance_parts.append("")

        # 2. LEGO VISUALIZATION
        lego_viz = self.lego_visualization(context)
        if "[BLOCK-" in lego_viz:
            guidance_parts.append(lego_viz)
            guidance_parts.append("")

        # 3. CONTINUOUS CIRCULATION
        guidance_parts.append(self.continuous_circulation(context))
        guidance_parts.append("")

        # 4. PRESENT CHOICE
        guidance_parts.append(self.present_choice(context))
        guidance_parts.append("")

        # 5. CHALLENGE ASSUMPTIONS
        assumption_analysis = self.challenge_assumptions(context)
        if len(assumption_analysis.split('\n')) > 2:
            guidance_parts.append(assumption_analysis)
            guidance_parts.append("")

    def _add_basic_codeindex_analysis(self, guidance_parts: List[str], context, wsp_analysis) -> None:
        """Add basic CodeIndex analysis (strict mode fallback)."""
        function_indexing = self._generate_function_level_indexing(context, wsp_analysis)
        if not function_indexing:
            return

        guidance_parts.append("[CODE-INDEX] FUNCTION-LEVEL CODE INDEXING (WSP 92):")
        primary_module = function_indexing.get('primary_module')
        if primary_module:
            functions = primary_module.get('functions', [])
            guidance_parts.append(f"  [FUNCTIONS] {len(functions)} functions indexed")
            complex_funcs = sorted(functions, key=lambda f: f.get('complexity', 1), reverse=True)[:3]
            for func in complex_funcs:
                complexity_str = self._complexity_to_string(func.get('complexity', 1))
                guidance_parts.append(f"    [BULLET] {func.get('name', 'unknown')} - {complexity_str}")
        guidance_parts.append("")

    def _add_integration_gap_section(self, guidance_parts: List[str], integration_gaps: Optional[Dict], strict_mode: bool) -> None:
        """Add integration gap detection section to guidance."""
        if not integration_gaps or not integration_gaps.get('detected_gaps'):
            return

        guidance_parts.append("[LINK] INTEGRATION GAPS DETECTED:")
        gap_limit = 1 if strict_mode else 3
        for gap in integration_gaps['detected_gaps'][:gap_limit]:
            guidance_parts.append(f"  - {gap['type']}: {gap['monitoring_module']} -> {gap['action_module']}")

        if integration_gaps.get('recommended_integrations') and not strict_mode:
            guidance_parts.append("  [IDEA] RECOMMENDED INTEGRATIONS:")
            for rec in integration_gaps['recommended_integrations'][:1]:
                guidance_parts.append(f"     {rec}")
        guidance_parts.append("")

    def _add_work_context_section(self, guidance_parts: List[str], context, strict_mode: bool) -> None:
        """Add 0102 work context map section to guidance."""
        logger.info("[WORK-CONTEXT] Generating 0102 work context map")
        work_context_map = self._generate_work_context_map(context)
        confidence = work_context_map.get('confidence', 0.0) if work_context_map else 0.0
        logger.info(f"[WORK-CONTEXT] Map generated - Confidence: {confidence:.2f}")

        if not work_context_map or strict_mode:
            return

        logger.info(f"[WORK-CONTEXT] Current task: {work_context_map.get('current_task', 'Unknown')}")
        logger.info(f"[WORK-CONTEXT] Active module: {work_context_map.get('active_module', 'Unknown')}")

        guidance_parts.append("[MAP] 0102 WORK CONTEXT MAP:")
        guidance_parts.append(f"  [TARGET] Current Focus: {work_context_map.get('current_task', 'Unknown')}")
        guidance_parts.append(f"  [FOLDER] Active Module: {work_context_map.get('active_module', 'Unknown')}")
        guidance_parts.append(f"  [LOCATION] Exact Location: {work_context_map.get('exact_location', 'Unknown')}")

        if work_context_map.get('related_modules'):
            guidance_parts.append("  [LINK] Related Modules:")
            related_limit = 1 if strict_mode else 3
            for mod in work_context_map['related_modules'][:related_limit]:
                guidance_parts.append(f"     - {mod}")
        guidance_parts.append("")

    def _add_primary_guidance_section(self, guidance_parts: List[str], llm_analysis, wsp_analysis, rules_guidance: Dict) -> None:
        """Add primary guidance from LLM, WSP, or rules engine."""
        if llm_analysis and llm_analysis.get("guidance"):
            guidance_parts.append(llm_analysis["guidance"])
        else:
            wsp_guidance_items = self.wsp_master.generate_comprehensive_guidance(wsp_analysis)
            if wsp_guidance_items:
                top_guidance = wsp_guidance_items[0]
                guidance_parts.append(f"{top_guidance.wsp_reference}: {top_guidance.guidance}")

        if not guidance_parts:
            guidance_parts.append(rules_guidance.get("primary_guidance", "Query processed. Follow WSP protocols."))

    def _synthesize_todos(self, llm_analysis, wsp_analysis, rules_guidance) -> List[str]:
        """Synthesize TODOs from all sources."""
        todos = []

        # From rules engine
        todos.extend(rules_guidance.get("action_items", []))

        # From LLM recommendations
        if llm_analysis and llm_analysis.get("recommendations"):
            todos.extend(llm_analysis["recommendations"])

        # From WSP Master
        wsp_guidance_items = self.wsp_master.generate_comprehensive_guidance(wsp_analysis)
        for guidance in wsp_guidance_items[:2]:  # Top 2 WSP items
            todos.extend(guidance.action_items)

        return list(set(todos))  # Remove duplicates

    def _synthesize_reminders(self, wsp_analysis, rules_guidance) -> List[str]:
        """Synthesize reminders from WSP and rules sources."""
        reminders = []

        # From rules engine
        for reminder in rules_guidance.get("reminders", []):
            reminders.append(f"{reminder['wsp_reference']}: {reminder['guidance']}")

        # From WSP Master
        wsp_guidance_items = self.wsp_master.generate_comprehensive_guidance(wsp_analysis)
        for guidance in wsp_guidance_items[:3]:  # Top 3 WSP items
            if guidance.priority in ['CRITICAL', 'HIGH']:
                reminders.append(f"{guidance.wsp_reference}: {guidance.guidance}")

        return list(set(reminders))  # Remove duplicates

    def _generate_dae_cube_mapping(self, context, wsp_analysis) -> Dict[str, Any]:
        """
        REVOLUTIONARY DAE CUBE MAPPING: Map modules to DAE cubes and generate flow awareness.

        This prevents vibecoding by giving 0102 "brain surgeon" level system awareness:
        - Shows which DAE cube is active
        - Maps modules within cube boundaries
        - Generates mermaid flow diagrams
        - Prevents daemons from running "unshackled" from system flow

        Args:
            context: Search context with code_hits and wsp_hits
            wsp_analysis: WSP protocol analysis

        Returns:
            Dict with cube mapping, boundaries, and mermaid flow
        """
        try:
            # Define DAE cubes per WSP 80 (from knowledge)
            DAE_CUBES = {
                "youtube": {
                    "boundary": "communication/livechat",
                    "modules": ["auto_moderator_dae", "livechat_core", "banter_engine", "stream_resolver", "consciousness_handler"],
                    "purpose": "YouTube live stream monitoring and interaction",
                    "inputs": ["YouTube API", "Live streams"],
                    "outputs": ["Chat moderation", "Automated responses", "XP/ranks"],
                    "dependencies": ["platform_integration/youtube_auth", "ai_intelligence/banter_engine"]
                },
                "linkedin": {
                    "boundary": "platform_integration/linkedin_agent",
                    "modules": ["linkedin_agent", "linkedin_scheduler", "linkedin_proxy"],
                    "purpose": "LinkedIn professional networking automation",
                    "inputs": ["LinkedIn API", "Professional content"],
                    "outputs": ["Automated posts", "Connection management"],
                    "dependencies": ["platform_integration/linkedin_auth", "infrastructure/oauth"]
                },
                "infrastructure": {
                    "boundary": "infrastructure/",
                    "modules": ["idle_automation", "database", "session_management", "auth"],
                    "purpose": "Cross-platform infrastructure utilities",
                    "inputs": ["System events", "User sessions"],
                    "outputs": ["Automated maintenance", "Session persistence"],
                    "dependencies": ["All platform modules"]
                },
                "ai_intelligence": {
                    "boundary": "ai_intelligence/",
                    "modules": ["banter_engine", "consciousness_handler", "priority_scorer"],
                    "purpose": "AI decision making and response generation",
                    "inputs": ["User messages", "System events"],
                    "outputs": ["AI responses", "Decision recommendations"],
                    "dependencies": ["All communication modules"]
                }
            }

            # Determine active cube from context
            active_cube = self._determine_active_cube(context, DAE_CUBES)
            if not active_cube:
                return None

            cube_info = DAE_CUBES[active_cube]

            # Generate mermaid flow diagram
            mermaid_flow = self._generate_cube_mermaid_flow(active_cube, cube_info)

            # Map modules within cube
            cube_modules = self._map_modules_to_cube(context, cube_info)

            return {
                "active_cube": active_cube,
                "boundary": cube_info["boundary"],
                "purpose": cube_info["purpose"],
                "modules": cube_modules,
                "inputs": cube_info["inputs"],
                "outputs": cube_info["outputs"],
                "dependencies": cube_info["dependencies"],
                "mermaid_flow": mermaid_flow
            }

        except Exception as e:
            logger.error(f"[CUBE-MAP] Error generating DAE cube mapping: {e}")
            return None

    def _determine_active_cube(self, context, dae_cubes) -> str:
        """Determine which DAE cube is currently active based on search context."""
        if not context or not hasattr(context, 'code_hits'):
            return None

        # Count module hits per cube boundary
        cube_scores = {}
        for cube_name, cube_info in dae_cubes.items():
            boundary = cube_info["boundary"]
            score = 0

            # Count files in this cube's boundary
            for hit in context.code_hits:
                file_path = hit.get('file_path', '').lower()
                if boundary.rstrip('/') in file_path:
                    score += 1

            cube_scores[cube_name] = score

        # Return cube with highest score, or None if no clear winner
        if cube_scores:
            max_score = max(cube_scores.values())
            if max_score > 0:  # At least one module in cube
                winners = [cube for cube, score in cube_scores.items() if score == max_score]
                return winners[0]  # Take first if tie

        return None

    def _generate_cube_mermaid_flow(self, cube_name: str, cube_info: Dict) -> str:
        """Generate mermaid flow diagram for DAE cube interactions."""
        try:
            # Simple mermaid flowchart showing cube inputs -> processing -> outputs
            flow = f"graph TD\\n"

            # Inputs
            for i, input_src in enumerate(cube_info["inputs"]):
                flow += f"    I{i}([{input_src}]) --> P\\n"

            # Processing node
            flow += f"    P[{cube_name.upper()} CUBE\\n{cube_info['purpose']}]\\n"

            # Outputs
            for i, output in enumerate(cube_info["outputs"]):
                flow += f"    P --> O{i}([{output}])\\n"

            # Dependencies
            for i, dep in enumerate(cube_info["dependencies"][:2]):  # Limit to 2 to prevent truncation
                flow += f"    D{i}[{dep}] -.-> P\\n"

            return flow

        except Exception as e:
            logger.error(f"[CUBE-MAP] Error generating mermaid flow: {e}")
            return None

    def _map_modules_to_cube(self, context, cube_info) -> List[str]:
        """Map specific modules found in search to their cube locations."""
        cube_modules = []
        boundary = cube_info["boundary"]

        if context and hasattr(context, 'code_hits'):
            for hit in context.code_hits:
                file_path = hit.get('file_path', '').lower()
                if boundary.rstrip('/') in file_path:
                    # Extract module name from path
                    parts = file_path.split('/')
                    if len(parts) >= 3:  # domain/module/file
                        module_name = parts[-2] if parts[-1].endswith('.py') else parts[-1]
                        if module_name not in cube_modules:
                            cube_modules.append(module_name)

        return cube_modules

    def _generate_function_level_indexing(self, context, wsp_analysis) -> Dict[str, Any]:
        """
        BRAIN SURGEON LEVEL INDEXING: Extract function-level code structure and generate Mermaid diagrams.

        This transforms HoloIndex from module finder to code surgeon:
        - Indexes every function/method with line numbers
        - Analyzes code complexity and flow
        - Generates Mermaid diagrams showing internal module logic
        - Identifies inefficiencies, duplicate code, and logic issues

        Args:
            context: Search context with code_hits and wsp_hits
            wsp_analysis: WSP protocol analysis

        Returns:
            Dict with function indexing, complexity analysis, and Mermaid diagrams
        """
        try:
            # Find primary module from search results
            primary_module = self._identify_primary_module(context)
            if not primary_module:
                return None

            # Extract function-level information
            function_analysis = self._extract_function_structure(primary_module)

            # Generate Mermaid diagram for module flow
            module_mermaid = self._generate_module_mermaid_diagram(function_analysis)

            # Analyze for inefficiencies
            inefficiencies = self._analyze_module_inefficiencies(function_analysis)

            return {
                "primary_module": {
                    "name": primary_module.get('file_path', 'unknown').split('/')[-1],
                    "path": primary_module.get('file_path', 'unknown'),
                    "functions": function_analysis.get('functions', []),
                    "total_lines": function_analysis.get('total_lines', 0),
                    "complexity_score": function_analysis.get('complexity_score', 0)
                },
                "module_mermaid": module_mermaid,
                "inefficiencies": inefficiencies,
                "analysis_timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"[CODE-INDEX] Error generating function-level indexing: {e}")
            return None

    def _identify_primary_module(self, context) -> Dict[str, Any]:
        """Identify the primary module from search results based on relevance."""
        if not context or not hasattr(context, 'code_hits') or not context.code_hits:
            return None

        # For now, take the first result as primary (can be enhanced with scoring)
        return context.code_hits[0] if context.code_hits else None

    def _extract_function_structure(self, module_hit) -> Dict[str, Any]:
        """Extract function/method structure from module code."""
        try:
            file_path = module_hit.get('file_path')
            if not file_path:
                return {"functions": [], "total_lines": 0, "complexity_score": 0}

            # Read the module file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception as e:
                logger.warning(f"[CODE-INDEX] Could not read file {file_path}: {e}")
                return {"functions": [], "total_lines": 0, "complexity_score": 0}

            functions = []
            current_function = None
            brace_count = 0
            in_multiline_string = False
            string_char = None

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Handle multiline strings
                if in_multiline_string:
                    if string_char in line and line.count(string_char) % 2 == 1:
                        in_multiline_string = False
                        string_char = None
                    continue

                # Detect start of multiline strings
                if ('"""' in stripped or "'''" in stripped) and stripped.count('"""') % 2 == 1:
                    in_multiline_string = True
                    string_char = '"""' if '"""' in stripped else "'''"
                    continue

                # Find function/class definitions
                if stripped.startswith('def ') or stripped.startswith('    def ') or stripped.startswith('class '):
                    # Save previous function if exists
                    if current_function:
                        end_line = i - 1
                        line_count = max(1, end_line - current_function['start_line'] + 1)
                        current_function['line_range'] = f"{current_function['start_line']}-{end_line}"
                        current_function['line_count'] = line_count
                        function_lines = lines[current_function['start_line'] - 1:end_line]
                        current_function['complexity'] = self._calculate_function_complexity(
                            function_lines,
                            line_count
                        )
                        functions.append(current_function)

                    # Start new function
                    func_name = stripped.split('(')[0].replace('def ', '').replace('class ', '').strip()
                    current_function = {
                        'name': func_name,
                        'start_line': i,
                        'complexity': self._calculate_function_complexity([], 0),  # Placeholder
                        'type': 'class' if stripped.startswith('class') else 'function'
                    }
                    brace_count = 0

                # Count braces for function boundaries (Python uses indentation, but this helps)
                elif current_function and ('{' in line or '}' in line):
                    brace_count += line.count('{') - line.count('}')

            # Add final function
            if current_function:
                end_line = len(lines)
                line_count = max(1, end_line - current_function['start_line'] + 1)
                current_function['line_range'] = f"{current_function['start_line']}-{end_line}"
                current_function['line_count'] = line_count
                function_lines = lines[current_function['start_line'] - 1:end_line]
                current_function['complexity'] = self._calculate_function_complexity(
                    function_lines,
                    line_count
                )
                functions.append(current_function)

            # Calculate overall complexity
            total_complexity = sum(f.get('complexity', 1) for f in functions)

            return {
                "functions": functions,
                "total_lines": len(lines),
                "complexity_score": total_complexity,
                "function_count": len(functions)
            }

        except Exception as e:
            logger.error(f"[CODE-INDEX] Error extracting function structure: {e}")
            return {"functions": [], "total_lines": 0, "complexity_score": 0}

    def _calculate_function_complexity(self, lines: List[str], line_count: int) -> int:
        """Calculate function complexity based on size and structure. Returns numeric score."""
        if line_count > 50:
            return 3  # High Complexity
        elif line_count > 20:
            return 2  # Medium Complexity
        else:
            return 1  # Low Complexity

    def _complexity_to_string(self, complexity_score: int) -> str:
        """Convert numeric complexity score to readable string."""
        if complexity_score >= 3:
            return "High Complexity"
        elif complexity_score >= 2:
            return "Medium Complexity"
        else:
            return "Low Complexity"

    def _generate_module_mermaid_diagram(self, function_analysis) -> str:
        """Generate Mermaid flowchart for module function flow."""
        try:
            functions = function_analysis.get('functions', [])
            if not functions:
                return None

            # Create simple flowchart showing function relationships
            flow = "graph TD\\n"

            # Add nodes for each function
            for i, func in enumerate(functions[:8]):  # Limit to 8 functions for readability
                func_name = func.get('name', f'func_{i}')
                complexity_score = func.get('complexity', 1)
                complexity_str = self._complexity_to_string(complexity_score)
                flow += f"    F{i}[{func_name}\\n{complexity_str}]\\n"

            # Add basic flow connections (can be enhanced with actual call analysis)
            for i in range(len(functions[:8]) - 1):
                flow += f"    F{i} --> F{i+1}\\n"

            return flow

        except Exception as e:
            logger.error(f"[CODE-INDEX] Error generating module Mermaid: {e}")
            return None

    def _analyze_module_inefficiencies(self, function_analysis) -> List[str]:
        """Analyze module for inefficiencies, duplicate code, and logic issues."""
        inefficiencies = []
        functions = function_analysis.get('functions', [])

        # Check for overly complex functions
        for func in functions:
            if func.get('line_count', 0) > 50:
                inefficiencies.append(f"Function '{func.get('name')}' is too long ({func.get('line_count')} lines)")

        # Check for too many functions (potential over-engineering)
        if len(functions) > 15:
            inefficiencies.append(f"Module has {len(functions)} functions - consider consolidating")

        # Check for functions with similar names (potential duplication)
        func_names = [f.get('name', '').lower() for f in functions]
        duplicates = set([name for name in func_names if func_names.count(name) > 1])
        if duplicates:
            inefficiencies.append(f"Potential duplicate functions: {', '.join(duplicates)}")

        return inefficiencies

    def _detect_output_truncation_patterns(self, context, total_findings) -> bool:
        """
        RECURSIVE LEARNING: Detect patterns that lead to output truncation.

        Uses first principles to identify when output will be truncated:
        - High volume results (>50 findings)
        - Complex queries with many components
        - Previous truncation patterns in similar contexts
        """
        # FIRST PRINCIPLES: High volume results always risk truncation
        if total_findings > 50:
            return True

        # FIRST PRINCIPLES: Complex multi-part queries risk truncation
        query_indicators = [' and ', ' or ', ' vs ', ' vs. ', ' comparison ', ' versus ']
        if any(indicator in context.query.lower() for indicator in query_indicators):
            return True

        # RECURSIVE LEARNING: Check for patterns that historically caused truncation
        # (This would be enhanced with actual learning data in production)
        truncation_patterns = [
            'large file', 'size limit', 'violation', 'warning',
            'module.*missing', 'documentation.*gap'
        ]

        query_lower = context.query.lower()
        for pattern in truncation_patterns:
            if pattern in query_lower:
                return True

        return False

    def _calculate_confidence(self, llm_analysis, wsp_analysis) -> float:
        """Calculate overall confidence in the guidance."""
        confidence = 0.3  # Base confidence

        # LLM confidence
        if llm_analysis:
            confidence += llm_analysis.get("confidence", 0.5) * 0.4

        # WSP relevance confidence
        if wsp_analysis and wsp_analysis.wsp_relevance:
            max_relevance = max(wsp_analysis.wsp_relevance.values())
            confidence += max_relevance * 0.3

        # Risk level adjustment
        risk_multiplier = {'LOW': 1.0, 'MEDIUM': 0.9, 'HIGH': 0.8, 'CRITICAL': 0.7}
        confidence *= risk_multiplier.get(wsp_analysis.risk_level, 1.0)

        return min(confidence, 1.0)

    def _detect_troubleshooting_patterns(self, query: str) -> Dict[str, Dict[str, Any]]:
        """Detect common troubleshooting patterns in queries."""
        patterns = {}
        query_lower = query.lower()

        for pattern_name, pattern_data in self.troubleshooting_db.items():
            if any(keyword in query_lower for keyword in pattern_data['keywords']):
                # Check if any of the code hits match the expected modules
                patterns[pattern_name] = pattern_data

        return patterns

    def _build_troubleshooting_db(self) -> Dict[str, Dict[str, Any]]:
        """Build database of common troubleshooting patterns and solutions."""
        return {
            'youtube_daemon_stuck': {
                'keywords': ['youtube', 'daemon', 'stuck', 'hung', 'not responding', 'circuit breaker'],
                'description': 'YouTube daemon is stuck, likely due to circuit breaker or authentication issues',
                'solutions': [
                    'Check circuit breaker status - may need manual reset',
                    'Verify YouTube API authentication tokens',
                    'Check for NO-QUOTA mode fallback capability',
                    'Review rate limiting and CAPTCHA detection'
                ],
                'modules': ['communication/livechat', 'platform_integration/youtube_auth', 'platform_integration/stream_resolver'],
                'priority': 'HIGH'
            },
            'rate_limiting_captcha': {
                'keywords': ['rate limit', '429', 'captcha', 'blocked', 'google.com/sorry'],
                'description': 'YouTube is rate limiting requests or showing CAPTCHA pages',
                'solutions': [
                    'Increase anti-detection delays (10-18s recommended)',
                    'Implement CAPTCHA detection and automatic cooldown',
                    'Reduce retry attempts from 5 to 2',
                    'Use NO-QUOTA web scraping mode as fallback'
                ],
                'modules': ['platform_integration/stream_resolver'],
                'priority': 'HIGH'
            },
            'authentication_failure': {
                'keywords': ['auth', 'token', 'oauth', 'api client is none', 'credential'],
                'description': 'YouTube API authentication is failing',
                'solutions': [
                    'Verify .env file has correct credential paths',
                    'Check OAuth token files exist and are valid',
                    'Ensure credential sets are properly configured (1, 10)',
                    'Test token refresh functionality'
                ],
                'modules': ['platform_integration/youtube_auth'],
                'priority': 'CRITICAL'
            },
            'stream_detection_failure': {
                'keywords': ['stream', 'detection', 'not finding', 'live video', 'video id'],
                'description': 'Daemon cannot detect live streams',
                'solutions': [
                    'Verify NO-QUOTA mode is properly initialized',
                    'Check channel IDs are correct in environment variables',
                    'Test individual video verification',
                    'Review anti-detection delays and patterns'
                ],
                'modules': ['platform_integration/stream_resolver', 'communication/livechat'],
                'priority': 'HIGH'
            },
            'circuit_breaker_open': {
                'keywords': ['circuit breaker', 'open', 'blocked', 'api calls blocked'],
                'description': 'Circuit breaker is stuck open, blocking all API calls',
                'solutions': [
                    'Implement manual circuit breaker reset',
                    'Reduce circuit breaker threshold from 10 to 5 failures',
                    'Add automatic recovery after timeout period',
                    'Improve fallback to NO-QUOTA mode'
                ],
                'modules': ['platform_integration/stream_resolver'],
                'priority': 'MEDIUM'
            }
        }

    def _generate_troubleshooting_guidance(self, patterns: Dict[str, Dict[str, Any]]) -> str:
        """Generate troubleshooting guidance for detected patterns."""
        guidance_parts = ["[TOOL] TROUBLESHOOTING DETECTED:"]

        for pattern_name, pattern_data in patterns.items():
            guidance_parts.append(f"\n[ERROR] Issue: {pattern_data['description']}")
            guidance_parts.append(f"[TARGET] Priority: {pattern_data['priority']}")
            guidance_parts.append("[IDEA] Solutions:")

            for solution in pattern_data['solutions']:
                guidance_parts.append(f"   - {solution}")

            if pattern_data['modules']:
                guidance_parts.append(f"[FOLDER] Focus modules: {', '.join(pattern_data['modules'])}")

        return "\n".join(guidance_parts)

    # ===== CODEINDEX: SURGICAL PRECISION METHODS =====

    def surgical_code_index(self, context: AdvisorContext) -> Dict[str, Any]:
        """
        CodeIndex: Surgical precision analysis returning exact fix locations.

        Returns exact line numbers and actionable fix coordinates for code issues.
        Hybrid approach: Uses existing HoloIndex search results, adds surgical precision.
        """
        logger.info("[CODEINDEX] Starting surgical code index analysis")

        results = {
            'modules_analyzed': [],
            'exact_fixes': [],
            'complexity_map': {},
            'inefficiency_alerts': []
        }

        # Use existing HoloIndex results - no duplicate file reading
        for hit in context.code_hits[:3]:  # Limit to prevent overload
            module_path = hit.get('file_path', '')
            if not module_path:
                continue

            # Leverage existing function indexing
            function_analysis = self._generate_function_level_indexing(context, None)
            if not function_analysis:
                continue

            primary_module = function_analysis.get('primary_module', {})
            functions = primary_module.get('functions', [])

            module_fixes = []
            for func in functions:
                func_name = func.get('name', 'unknown')
                line_range = func.get('line_range', 'unknown')
                complexity = func.get('complexity', 1)

                # Calculate exact fix locations
                if complexity >= 3:  # High complexity = needs fixing
                    start_line, end_line = self._parse_line_range(line_range)
                    fix_location = {
                        'module': module_path,
                        'function': func_name,
                        'line_range': line_range,
                        'start_line': start_line,
                        'end_line': end_line,
                        'complexity': complexity,
                        'estimated_effort': self._estimate_refactor_effort(start_line, end_line)
                    }
                    module_fixes.append(fix_location)
                    results['complexity_map'][f"{module_path}:{func_name}"] = complexity

            if module_fixes:
                results['modules_analyzed'].append(module_path)
                results['exact_fixes'].extend(module_fixes)

        # Generate inefficiency alerts with exact locations
        for fix in results['exact_fixes']:
            if fix['estimated_effort'] > 60:  # High effort = alert
                alert = {
                    'type': 'HIGH_COMPLEXITY_FUNCTION',
                    'location': f"{fix['module']}:{fix['function']} ({fix['line_range']})",
                    'severity': 'CRITICAL' if fix['estimated_effort'] > 120 else 'WARNING',
                    'action_required': f"Refactor function to <200 lines (currently {fix['end_line'] - fix['start_line'] + 1} lines)"
                }
                results['inefficiency_alerts'].append(alert)

        logger.info(f"[CODEINDEX] Surgical analysis complete: {len(results['exact_fixes'])} fixes identified")
        return results

    def lego_visualization(self, context: AdvisorContext) -> str:
        """
        CodeIndex: LEGO visualization - format existing function calls as snap points.

        Shows how functions connect like LEGO blocks, identifying snap points for
        modular connections and potential refactoring opportunities.
        """
        logger.info("[CODEINDEX] Generating LEGO visualization")

        lego_blocks = []

        # Use existing function analysis
        function_analysis = self._generate_function_level_indexing(context, None)
        if not function_analysis:
            return "[LEGO] No function analysis available"

        primary_module = function_analysis.get('primary_module', {})
        functions = primary_module.get('functions', [])

        mermaid = function_analysis.get('module_mermaid', '')
        if not mermaid:
            return "[LEGO] No flow diagram available"

        # Parse mermaid to identify connection points
        lines = mermaid.split('\n')
        connections = []

        for line in lines:
            if '-->' in line:
                # Extract function connections
                parts = line.split('-->')
                if len(parts) == 2:
                    from_func = parts[0].strip()
                    to_func = parts[1].strip()
                    connections.append((from_func, to_func))

        # Format as LEGO snap points
        lego_parts = ["[LEGO] FUNCTION SNAP POINTS (LEGO-style connections):"]

        for i, (from_func, to_func) in enumerate(connections):
            lego_parts.append(f"  [BLOCK-{i+1}] {from_func} ⟷ {to_func}")
            lego_parts.append("    [U+21B3] SNAP POINT: Function call interface")
            lego_parts.append("    [U+21B3] STABILITY: Modular connection point")
        # Identify potential LEGO refactoring opportunities
        complex_functions = [f for f in functions if f.get('complexity', 1) >= 3]
        if complex_functions:
            lego_parts.append("\n[LEGO] BREAK APART CANDIDATES:")
            for func in complex_functions:
                func_name = func.get('name', 'unknown')
                lego_parts.append(f"  [BREAK] {func_name} -> Split into 2-3 smaller LEGO blocks")

        return "\n".join(lego_parts)

    def continuous_circulation(self, context: AdvisorContext) -> str:
        """
        CodeIndex: Continuous circulation - run existing checks as daemon.

        Continuously monitors code quality metrics in the background,
        providing ongoing health status like a circulatory system.
        """
        logger.info("[CODEINDEX] Running continuous circulation checks")

        circulation_report = ["[CIRCULATION] CONTINUOUS CODE HEALTH MONITORING:"]

        # Leverage existing HoloIndex infrastructure for ongoing checks
        health_checks = []

        # Check file sizes (existing WSP 62 compliance)
        for hit in context.code_hits:
            file_path = hit.get('file_path', '')
            if file_path and 'lines' in hit:
                line_count = hit.get('lines', 0)
                if line_count > 1000:
                    health_checks.append(f"[WARNING] LARGE FILE: {file_path} ({line_count} lines)")

        # Check for test coverage (existing patterns)
        test_coverage = self._assess_test_coverage(context)
        if test_coverage < 70:
            health_checks.append(f"[WARNING] LOW TEST COVERAGE: {test_coverage}% (target: 80%+)")

        # Check complexity distribution
        complexity_distribution = self._analyze_complexity_distribution(context)
        high_complexity_count = sum(1 for c in complexity_distribution.values() if c >= 3)
        if high_complexity_count > 0:
            health_checks.append(f"[WARNING] HIGH COMPLEXITY: {high_complexity_count} functions need refactoring")

        # Format as circulation status
        circulation_report.append(f"  [HEARTBEAT] Files monitored: {len(context.code_hits)}")
        circulation_report.append(f"  [BLOOD-FLOW] Functions analyzed: {len(complexity_distribution)}")
        circulation_report.append(f"  [PRESSURE] Complexity alerts: {high_complexity_count}")

        if health_checks:
            circulation_report.append("\n[CIRCULATION] HEALTH ALERTS:")
            circulation_report.extend(f"  {alert}" for alert in health_checks[:5])  # Limit alerts
        else:
            circulation_report.append("\n[CIRCULATION] [HEALTHY] ALL SYSTEMS HEALTHY")

        return "\n".join(circulation_report)

    def present_choice(self, context: AdvisorContext) -> str:
        """
        CodeIndex: Present choice - format findings as A/B/C options.

        Provides clear decision frameworks with multiple options for code improvements,
        allowing 0102 agents to make informed choices.
        """
        logger.info("[CODEINDEX] Generating choice framework")

        choices = ["[CHOICE] CODE IMPROVEMENT OPTIONS:"]

        # Analyze current state
        surgical_results = self.surgical_code_index(context)
        high_priority_fixes = [f for f in surgical_results['exact_fixes'] if f['estimated_effort'] > 60]

        if not high_priority_fixes:
            choices.append("  [MAINTAIN] A) MAINTAIN: Code is healthy, no immediate action needed")
            choices.append("  [MONITOR] B) MONITOR: Continue standard health checks")
            choices.append("  [ENHANCE] C) ENHANCE: Look for minor optimization opportunities")
            return "\n".join(choices)

        # Present real choices based on analysis
        choices.append("  [SURGICAL] A) SURGICAL: Fix highest priority issues immediately")
        choices.append(f"     -> Target: {high_priority_fixes[0]['function']} ({high_priority_fixes[0]['line_range']})")
        choices.append("     -> Impact: Reduce complexity, improve maintainability")
        if len(high_priority_fixes) > 1:
            choices.append("  [GRADUAL] B) GRADUAL: Address issues incrementally")
            choices.append(f"     -> Plan: Fix {len(high_priority_fixes)} functions over multiple sessions")
            choices.append("     -> Strategy: Break down large functions into smaller modules")

        choices.append("  [HOLISTIC] C) HOLISTIC: Comprehensive codebase refactoring")
        choices.append("     -> Approach: Full module restructuring with dependency analysis")
        choices.append("     -> Tools: Use CodeIndex for complete system mapping")

        # Add risk assessment
        risk_level = "HIGH" if len(high_priority_fixes) > 3 else "MEDIUM" if len(high_priority_fixes) > 1 else "LOW"
        choices.append(f"\n[CHOICE] RISK ASSESSMENT: {risk_level}")
        choices.append("  Recommended: Option A for immediate impact, Option C for long-term health")

        return "\n".join(choices)

    def challenge_assumptions(self, context: AdvisorContext) -> str:
        """
        CodeIndex: Challenge assumptions - parse code for hidden assumptions.

        Analyzes code to identify hardcoded values, magic numbers, and implicit
        assumptions that could break under different conditions.
        """
        logger.info("[CODEINDEX] Challenging code assumptions")

        assumptions_found = ["[ASSUMPTIONS] HIDDEN ASSUMPTIONS DETECTED:"]

        # Use existing file reading infrastructure
        for hit in context.code_hits[:3]:  # Limit analysis scope
            file_path = hit.get('file_path', '')
            if not file_path or not file_path.endswith('.py'):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                file_assumptions = []

                for i, line in enumerate(lines, 1):
                    line_str = line.strip()

                    # Find magic numbers (excluding common values)
                    import re
                    magic_numbers = re.findall(r'\b\d{2,}\b', line_str)  # Numbers >= 10
                    magic_numbers = [n for n in magic_numbers if n not in ['10', '100', '1000', '60', '24', '365']]

                    if magic_numbers:
                        file_assumptions.append({
                            'line': i,
                            'type': 'MAGIC_NUMBER',
                            'content': f"Hardcoded numbers: {', '.join(magic_numbers)}",
                            'risk': 'Configuration should be externalized'
                        })

                    # Find hardcoded strings that might be assumptions
                    hardcoded_strings = re.findall(r"'[^']{20,}'|\"[^\"]{20,}\"", line_str)
                    if hardcoded_strings:
                        file_assumptions.append({
                            'line': i,
                            'type': 'HARDCODED_STRING',
                            'content': f"Long hardcoded string: {hardcoded_strings[0][:50]}...",
                            'risk': 'May break in different environments'
                        })

                    # Find TODO/FIXME comments indicating known issues
                    if 'TODO' in line_str.upper() or 'FIXME' in line_str.upper():
                        file_assumptions.append({
                            'line': i,
                            'type': 'DEFERRED_ISSUE',
                            'content': line_str.strip(),
                            'risk': 'Known issue not addressed'
                        })

                # Format assumptions for this file
                if file_assumptions:
                    assumptions_found.append(f"\n[FILE] {file_path}:")
                    for assumption in file_assumptions[:3]:  # Limit per file
                        assumptions_found.append(f"  Line {assumption['line']}: {assumption['content']}")
                        assumptions_found.append(f"    [RISK] {assumption['risk']}")

            except Exception as e:
                logger.warning(f"Could not analyze assumptions in {file_path}: {e}")

        if len(assumptions_found) == 1:
            assumptions_found.append("  [CLEAN] No problematic assumptions detected")

        return "\n".join(assumptions_found)

    # ===== HELPER METHODS =====

    def _parse_line_range(self, line_range: str) -> tuple[int, int]:
        """Parse line range string like '138-553' into start/end integers."""
        try:
            if '-' in line_range:
                start, end = line_range.split('-')
                return int(start), int(end)
            else:
                line_num = int(line_range)
                return line_num, line_num
        except (ValueError, AttributeError):
            return 0, 0

    def _estimate_refactor_effort(self, start_line: int, end_line: int) -> int:
        """Estimate refactoring effort in minutes based on line count."""
        line_count = end_line - start_line + 1
        if line_count < 50:
            return 15  # Quick fix
        elif line_count < 200:
            return 45  # Moderate effort
        else:
            return 90  # Major refactoring

    def _assess_test_coverage(self, context: AdvisorContext) -> float:
        """Assess test coverage percentage from available files and module structure."""
        import os

        # Get total implementation files from search results
        total_files = len([h for h in context.code_hits if h.get('file_path', '').endswith('.py')])

        # Also scan module directories for test files (more comprehensive)
        test_files_found = 0
        for hit in context.code_hits:
            file_path = hit.get('file_path', '')
            if file_path:
                # Extract module path (e.g., modules/platform_integration/stream_resolver)
                parts = file_path.split('/')
                if len(parts) >= 3 and parts[0] == 'modules':
                    module_path = '/'.join(parts[:4])  # modules/domain/module
                    test_dir = f"{module_path}/tests"

                    try:
                        if os.path.exists(test_dir):
                            test_files = [f for f in os.listdir(test_dir)
                                        if f.startswith('test_') and f.endswith('.py')]
                            test_files_found = max(test_files_found, len(test_files))
                    except (OSError, IOError):
                        pass  # Directory doesn't exist or can't be read

        # Use both search results and file system scan
        test_files = len([h for h in context.code_hits if 'test' in h.get('file_path', '').lower()])
        test_files = max(test_files, test_files_found)  # Use the higher count

        if total_files == 0:
            return 0.0

        # More realistic: expect at least 1 test per module, up to 1 test per 2 files
        expected_tests = max(1, min(total_files // 2, total_files // 3 + 1))
        coverage = min(100.0, (test_files / expected_tests) * 100) if expected_tests > 0 else 0.0

        return round(coverage, 1)

    def _analyze_complexity_distribution(self, context: AdvisorContext) -> Dict[str, int]:
        """Analyze complexity distribution across functions."""
        distribution = {}

        function_analysis = self._generate_function_level_indexing(context, None)
        if function_analysis:
            primary_module = function_analysis.get('primary_module', {})
            functions = primary_module.get('functions', [])

            for func in functions:
                func_name = func.get('name', 'unknown')
                complexity = func.get('complexity', 1)
                distribution[func_name] = complexity

        return distribution

