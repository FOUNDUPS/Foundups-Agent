# -*- coding: utf-8 -*-
import sys
import io
import time
import logging
import os
import json
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from collections import Counter, deque
from typing import Dict, List, Optional, Any, Tuple, Set

# === UTF-8 ENFORCEMENT (WSP 90) ===
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        pass
# === END UTF-8 ENFORCEMENT ===

# Import core components
from .orchestration.qwen_orchestrator import QwenOrchestrator, WSP_DOC_CONFIG
from .arbitration.mps_arbitrator import MPSArbitrator, ArbitrationDecision
from holo_index.core.intelligent_subroutine_engine import IntelligentSubroutineEngine
from .services.file_system_watcher import FileSystemWatcher
from .services.context_analyzer import ContextAnalyzer
from .models.work_context import WorkContext
from .models.monitoring_types import MonitoringResult, FileChange, ChangeType
from .ui.menu_system import HoloDAEMenuSystem, StatusDisplay
from .output_formatter import HoloOutputFormatter, TelemetryLogger
from .qwen_health_monitor import CodeIndexCirculationEngine
from .architect_mode import ArchitectDecisionEngine

# Import WSP 62 Services
from .services.pid_detective import PIDDetective
from .services.mcp_integration import MCPIntegration
from .services.telemetry_formatter import TelemetryFormatter
from .services.module_metrics import ModuleMetrics
from .services.monitoring_loop import MonitoringLoop
from holo_index.wre_integration.skill_executor import SkillExecutor
from modules.communication.livechat.src.automation_gates import gate_snapshot

# Import breadcrumb tracer
from holo_index.adaptive_learning.breadcrumb_tracer import get_tracer
from urllib import request as _urllib_request

# PatternMemory for collective false-positive learning (WSP 48/60)
try:
    from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
    PATTERN_MEMORY_AVAILABLE = True
except ImportError:
    PATTERN_MEMORY_AVAILABLE = False

class HoloDAECoordinator:
    """
    Refactored HoloDAE Coordinator - Clean architecture implementation
    Follows WSP 80: Qwen orchestrates -> 0102 arbitrates -> 012 observes
    """

    def __init__(self):
        """Initialize the HoloDAE coordinator with all components"""
        self.repo_root = Path(__file__).resolve().parents[2]
        
        # Core orchestration components
        self.qwen_orchestrator = QwenOrchestrator(coordinator=self)
        self.mps_arbitrator = MPSArbitrator()

        # Core services
        self.file_watcher = FileSystemWatcher()
        self.context_analyzer = ContextAnalyzer()
        self.codeindex_engine = CodeIndexCirculationEngine()
        self.architect_engine = ArchitectDecisionEngine()
        
        # State management
        self.current_work_context = WorkContext()
        self.mcp_action_log = deque(maxlen=100)
        self.mcp_watchlist = [
            {
                'name': 'ricDAE Research Ingestion Cube',
                'module': 'modules/ai_intelligence/ric_dae',
                'description': 'Sovereign research ingestion MCP server',
                'priority': 'P0'
            },
            {
                'name': 'YouTube MCP Bridge',
                'module': 'modules/communication/livechat',
                'description': 'Live stream moderation MCP adapters',
                'priority': 'P1'
            },
            {
                'name': 'Whack-A-MCP Control',
                'module': 'modules/gamification/whack_a_magat',
                'description': 'Game loop MCP command surface',
                'priority': 'P2'
            }
        ]

        # Logging must exist before any discovery hooks run. Gate scanning uses
        # _detailed_log, so initialize this before _scan_for_gates().
        self.holo_console_enabled = os.getenv("HOLO_SILENT", "0").lower() not in {"1", "true", "yes"}
        self.verbose = os.getenv('HOLO_VERBOSE', '').lower() in {"1", "true", "yes"}
        self.session_id = f"holo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.logger = logging.getLogger('holodae_activity')
        self.telemetry_logger = TelemetryLogger(self.session_id)
        self.telemetry_formatter = TelemetryFormatter(
            telemetry_logger=self.telemetry_logger,
            current_work_context=self.current_work_context,
            logger=self.logger
        )
        self.holo_agent_id = self.telemetry_logger.session_id
        
        # Initialize doc tracking
        self.doc_only_modules: Set[str] = set()
        self._initialize_doc_only_modules()
        self.module_map: Dict[str, Dict[str, Any]] = {}
        self.orphan_candidates: List[str] = []

        # AI Discovery: Gate Registry
        self.detected_gates: Dict[str, Any] = {}
        self._scan_for_gates()

        # Initialize breadcrumb tracer
        self.breadcrumb_tracer = get_tracer()

        # Initialize WSP 62 Services with full wiring
        self.pid_detective = PIDDetective()
        
        self.mcp_integration = MCPIntegration(
            mcp_watchlist=self.mcp_watchlist,
            mcp_action_log=self.mcp_action_log,
            breadcrumb_tracer=self.breadcrumb_tracer,
            telemetry_logger=self.telemetry_logger
        )
        
        self.module_metrics = ModuleMetrics(
            repo_root=self.repo_root,
            doc_only_modules=self.doc_only_modules,
            module_map=self.module_map,
            orphan_candidates=self.orphan_candidates
        )
        
        self.skill_executor = SkillExecutor(repo_root=self.repo_root)

        # PatternMemory for false-positive filtering (WSP 48/60)
        self.pattern_memory: Optional[Any] = None
        if PATTERN_MEMORY_AVAILABLE:
            try:
                self.pattern_memory = PatternMemory()
                self._detailed_log("[HOLODAE] PatternMemory initialized for result filtering")
            except Exception as exc:
                self._detailed_log(f"[HOLODAE] PatternMemory unavailable: {exc}")

        self.monitoring_loop = MonitoringLoop(
            file_watcher=self.file_watcher,
            context_analyzer=self.context_analyzer,
            repo_root=self.repo_root,
            codeindex_engine=self.codeindex_engine,
            architect_engine=self.architect_engine,
            current_work_context=self.current_work_context,
            telemetry_formatter=self.telemetry_formatter,
            logger=self.logger,
            monitoring_interval=max(1.0, float(os.getenv('HOLO_MONITOR_INTERVAL', '5.0'))),
            monitoring_heartbeat=max(5.0, float(os.getenv('HOLO_MONITOR_HEARTBEAT', '60.0'))),
            module_metrics_cache=self.module_metrics._module_metrics_cache, # Share cache
            holo_log_callback=self._holo_log,
            detailed_log_callback=self._detailed_log,
            build_monitor_summary_callback=self.telemetry_formatter.build_monitor_summary_block,
            skill_executor=self.skill_executor
        )

        # UI components
        self.menu_system = HoloDAEMenuSystem()
        self.status_display = StatusDisplay()

        self._detailed_log("[HOLODAE-COORDINATOR] Initialized with modular architecture and breadcrumb tracing")

    def _initialize_doc_only_modules(self) -> None:
        """Register documentation-only bundles that skip runtime checks."""
        wsp_doc_only = WSP_DOC_CONFIG.get('doc_only_modules', set())
        doc_paths = ['holo_index/docs'] + list(wsp_doc_only)

        for doc_path in doc_paths:
            normalized = doc_path.replace('\\', '/').strip()
            if normalized:
                self.doc_only_modules.add(normalized)
            absolute = (self.repo_root / normalized).resolve()
            self.doc_only_modules.add(str(absolute).replace('\\', '/'))

    def _scan_for_gates(self) -> None:
        """
        AI GENESIS: Recursively discover 'Gate' capabilities in modules.
        This allows the Coordinator to 'awaken' to new compliance officers like AutoGate.
        """
        self._detailed_log("[HOLODAE-GENESIS] Scanning for autonomous gates...")
        modules_root = self.repo_root / "modules"
        
        # Heuristic: Look for *_gate.py files
        for gate_file in modules_root.rglob("*_gate.py"):
            try:
                # Convert path to module string
                rel_path = gate_file.relative_to(self.repo_root)
                module_str = str(rel_path).replace(os.sep, ".")[:-3]
                
                # Dynamic import
                if module_str not in sys.modules:
                    import importlib
                    module = importlib.import_module(module_str)
                else:
                    module = sys.modules[module_str]
                
                # Inspect for Gate classes
                import inspect
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and name.endswith("Gate") and name != "AutoGate": 
                        # We found a generic gate! (AutoGate is special, but let's register it too if generic)
                        pass
                    
                    # Specific check for AutoGate (our known entity)
                    if name == "AutoGate":
                        self.detected_gates["AutoGate"] = {
                            "module": module_str,
                            "path": str(rel_path),
                            "class": obj,
                            "discovered_at": time.time()
                        }
                        self._detailed_log(f"[HOLODAE-GENESIS] ✨ Discovered ACTIVE GATE: {name} in {rel_path}")
                        self.telemetry_logger.log_system_event(
                            "gate_discovery", 
                            "high", 
                            f"AI successfully identified compliance gate: {name}"
                        )

            except Exception as e:
                self._detailed_log(f"[HOLODAE-GENESIS] Failed to probe {gate_file}: {e}")

    def _holo_log(self, message: str, console: Optional[bool] = None) -> None:
        """Log HoloDAE activity visible to 012 with HOLO_AGENT_ID"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        sanitized = message.replace('\n', ' ').strip()
        holo_message = f"[{timestamp}] {self.holo_agent_id} - holo {sanitized}"
        self.logger.info(holo_message)
        should_print = self.holo_console_enabled if console is None else console
        if should_print:
            print(holo_message)

    def _detailed_log(self, message: str) -> None:
        """Log detailed information to file only"""
        self.logger.info(message)

    def _filter_false_positive_results(self, query: str, search_results: dict) -> dict:
        """
        Filter search results to remove known false positives using PatternMemory.

        WSP 48/60: Collective learning - skip results that are learned false positives
        (e.g., filter out "holo_dae module" results when searching for modules)

        Args:
            query: Original search query
            search_results: Raw search results from HoloIndex

        Returns:
            Filtered search results with false positives removed
        """
        if not self.pattern_memory:
            return search_results  # No filtering if PatternMemory unavailable

        filtered_results = {
            'code': [],
            'wsps': search_results.get('wsps', [])  # WSP docs rarely false positives
        }

        # Filter code results
        for result in search_results.get('code', []):
            file_path = result.get('file', '')
            module_name = self._extract_module_from_path(file_path)

            # Check if this module/file is a known false positive
            if module_name and self.pattern_memory.is_false_positive("module", module_name):
                details = self.pattern_memory.get_false_positive_reason("module", module_name)
                self._detailed_log(
                    f"[HOLODAE] [LEARNED] Filtered false positive: {module_name}\n"
                    f"  Reason: {details.get('reason', 'Unknown')}\n"
                    f"  Actual: {details.get('actual_location', 'Unknown')}"
                )
                continue  # Skip this result

            filtered_results['code'].append(result)

        # Log filtering stats
        original_count = len(search_results.get('code', []))
        filtered_count = len(filtered_results['code'])
        if filtered_count < original_count:
            self._detailed_log(
                f"[HOLODAE] [LEARNED] Filtered {original_count - filtered_count} "
                f"false positive results ({filtered_count} relevant results remain)"
            )

        return filtered_results

    def _extract_module_from_path(self, file_path: str) -> Optional[str]:
        """Extract module name from file path (e.g., 'modules/ai_intelligence/ai_overseer/...' -> 'ai_overseer')"""
        if not file_path:
            return None

        parts = Path(file_path).parts
        if 'modules' in parts:
            idx = parts.index('modules')
            if len(parts) > idx + 2:
                return parts[idx + 2]  # Return module name (third part after 'modules')
        elif 'holo_index' in parts:
            idx = parts.index('holo_index')
            if len(parts) > idx + 1:
                return parts[idx + 1]  # Return submodule (e.g., 'qwen_advisor')

        return None

    def _extract_search_result_paths(self, search_results: dict) -> List[str]:
        """Extract repository paths from HoloIndex result records."""
        paths: List[str] = []
        for section in ("code", "wsps", "wsp"):
            for result in search_results.get(section, []) or []:
                if isinstance(result, str):
                    candidate = result
                elif isinstance(result, dict):
                    candidate = (
                        result.get("location")
                        or result.get("file")
                        or result.get("path")
                        or result.get("source")
                        or ""
                    )
                else:
                    candidate = ""
                if candidate and candidate not in paths:
                    paths.append(candidate)
        return paths

    def handle_holoindex_request(self, query: str, search_results: dict) -> str:
        """Handle HoloIndex search request - Main orchestration entry point"""
        self._detailed_log(f"[HOLODAE-COORDINATOR] Processing query: '{query}'")

        # Phase 0: Filter false positives using PatternMemory (WSP 48/60)
        filtered_results = self._filter_false_positive_results(query, search_results)

        # Breadcrumb: Record search initiation (with filtered count)
        self.breadcrumb_tracer.add_search(query, filtered_results.get('code', [])[:3], [])

        # Step 1: Qwen orchestrates the analysis (receives filtered results)
        qwen_report = self.qwen_orchestrator.orchestrate_holoindex_request(query, filtered_results)

        # Extract analysis context and gather module metrics
        analysis_context = self.qwen_orchestrator.get_analysis_context()
        involved_files = analysis_context['files']
        involved_modules = analysis_context['modules']
        
        # Delegate to ModuleMetrics
        module_metrics = self.module_metrics.collect_module_metrics_for_request(involved_modules)
        alerts = self.module_metrics.get_system_alerts(list(module_metrics.keys()))

        # Breadcrumb: Record modules discovered
        if involved_modules:
            self.breadcrumb_tracer.add_discovery(
                "module_discovery",
                f"modules_{len(involved_modules)}",
                f"{len(involved_files)} files across {len(involved_modules)} modules",
                f"Found implementations in modules: {', '.join(involved_modules[:3])}"
            )

        # Build module map for orphan detection
        self.module_metrics.build_module_map(module_metrics)

        # Step 2: 0102 arbitrates using MPS
        arbitration_decisions = self.mps_arbitrator.arbitrate_qwen_findings(qwen_report)
        high_priority_decisions: List[ArbitrationDecision] = []

        # Breadcrumb: Record key arbitration decisions
        if arbitration_decisions:
            high_priority_decisions = [d for d in arbitration_decisions if getattr(d, 'mps_analysis', None) and d.mps_analysis.total_score >= 13]
            if high_priority_decisions:
                self.breadcrumb_tracer.add_action(
                    "arbitration_decision",
                    f"{len(high_priority_decisions)} high-priority tasks",
                    f"MPS arbitration identified {len(high_priority_decisions)} critical actions",
                    f"Key decisions: {', '.join([d.description[:30] + '...' for d in high_priority_decisions[:2]])}"
                )

        # Step 3: Execute arbitration decisions
        execution_results = self.mps_arbitrator.execute_arbitration_decisions(arbitration_decisions)

        # Update work context
        analysis_context = self.qwen_orchestrator.get_recent_analysis_context()
        session_actions = [f"{decision.recommended_action.value}:{decision.description}" for decision in arbitration_decisions]
        result_files = self._extract_search_result_paths(filtered_results)
        context_files = result_files or analysis_context['files']
        if context_files or session_actions:
            self.current_work_context = self.context_analyzer.analyze_work_context(context_files, session_actions)
            if result_files:
                first_result_module = self.context_analyzer._extract_module(result_files[0])
                if first_result_module:
                    self.current_work_context.primary_module = first_result_module
            # Update formatter's context reference
            self.telemetry_formatter.current_work_context = self.current_work_context
            self.monitoring_loop.current_work_context = self.current_work_context

        search_summary = {
            'code': search_results.get('code', []),
            'wsps': search_results.get('wsps', [])
        }
        
        # Delegate telemetry logging
        self.telemetry_formatter.log_request_telemetry(query, search_summary, module_metrics, alerts)

        # Format final report
        final_report = self.telemetry_formatter.format_final_report(
            qwen_report, arbitration_decisions, execution_results
        )
        
        module_summary = self.telemetry_formatter.format_module_metrics_summary(module_metrics, alerts)
        if module_summary:
            final_report = f"{final_report}\n{module_summary}" if final_report else module_summary

        # Delegate MCP tracking
        self.mcp_integration.track_mcp_activity(
            query=query,
            module_metrics=module_metrics,
            qwen_report=qwen_report
        )

        # Extract findings and append to summary (if enabled)
        findings = self.telemetry_formatter.extract_key_findings(alerts, module_metrics)
        actions_overview = self.telemetry_formatter.extract_high_priority_actions(high_priority_decisions)
        
        # Note: append_012_summary is disabled/manual only, but we keep the call structure if needed
        # self.telemetry_formatter.append_012_summary(...) 

        # Add breadcrumb trail from other agents
        breadcrumb_summary = self._get_collaborative_breadcrumb_summary()
        if breadcrumb_summary:
            final_report = f"{breadcrumb_summary}\n{final_report}" if final_report else breadcrumb_summary

        self._detailed_log("[HOLODAE-COORDINATOR] Request processing complete")
        return final_report

    def _get_collaborative_breadcrumb_summary(self) -> str:
        """Get summary of recent breadcrumbs from other 0102 agents for collaboration."""
        try:
            recent_discoveries = self.breadcrumb_tracer.get_recent_discoveries(5)
            if not recent_discoveries:
                return ""

            other_agent_discoveries = [
                d for d in recent_discoveries
                if d.get('session_id') != self.breadcrumb_tracer.session_id
            ]

            if not other_agent_discoveries:
                return ""

            lines = ["[0102-COLLABORATION] Recent discoveries from other agents:"]
            for discovery in other_agent_discoveries[:3]:
                discovery_type = discovery.get('type', 'unknown')
                item = discovery.get('item', 'unknown')
                location = discovery.get('location', '')
                impact = discovery.get('impact', '')

                if discovery_type == 'module_discovery':
                    lines.append(f"  [PIN] Agent found {item} at {location}")
                elif discovery_type == 'typo_handler':
                    lines.append(f"  [IDEA] Agent discovered {item} typo handler")
                else:
                    lines.append(f"  [SEARCH] Agent discovered: {item}")

                if impact:
                    lines.append(f"     Impact: {impact}")

            lines.append("  [HANDSHAKE] Other agents may benefit from your current search results")
            return "\n".join(lines)

        except Exception as e:
            self.logger.debug(f"Error getting collaborative breadcrumb summary: {e}")
            return ""

    # =========================================================================
    # DELEGATED METHODS (WSP 62)
    # =========================================================================

    def start_monitoring(self) -> bool:
        return self.monitoring_loop.start_monitoring()

    def stop_monitoring(self) -> bool:
        return self.monitoring_loop.stop_monitoring()

    def enable_monitoring(self) -> None:
        self.monitoring_loop.enable_monitoring()

    @property
    def monitoring_active(self) -> bool:
        """Compatibility access to the broker-owned monitoring state."""
        return self.monitoring_loop.monitoring_active

    @property
    def last_monitoring_result(self) -> Optional[MonitoringResult]:
        """Compatibility access for status/report tests and legacy callers."""
        return self.monitoring_loop.last_monitoring_result

    def run_monitoring_cycle(self) -> MonitoringResult:
        """Run one read-only HoloDAE monitoring cycle."""
        result = self.monitoring_loop.run_monitoring_cycle()
        self.current_work_context = self.monitoring_loop.current_work_context
        self.telemetry_formatter.current_work_context = self.current_work_context
        return result

    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status summary"""
        return {
            'monitoring_active': self.monitoring_loop.monitoring_active,
            'qwen_status': self.qwen_orchestrator.get_chain_of_thought_summary(),
            'arbitration_status': self.mps_arbitrator.get_arbitration_summary(),
            'files_watched': self.file_watcher.get_watched_files_count(),
            'current_work_context': self.current_work_context.get_summary(),
            'last_monitoring_summary': self.monitoring_loop.last_monitoring_result.get_summary() if self.monitoring_loop.last_monitoring_result else None,
            'last_monitoring_timestamp': self.monitoring_loop.last_monitoring_result.timestamp.isoformat() if self.monitoring_loop.last_monitoring_result else None,
            'last_monitoring_timestamp': self.monitoring_loop.last_monitoring_result.timestamp.isoformat() if self.monitoring_loop.last_monitoring_result else None,
            'automation_gates': gate_snapshot(),
            'discovered_gates': list(self.detected_gates.keys())
        }

    def show_menu(self) -> str:
        self.menu_system.show_main_menu()
        return self.menu_system.get_menu_choice()

    def show_sprint_status(self) -> None:
        # Placeholder for sprint status
        pass

    def show_mcp_hook_status(self) -> None:
        self.mcp_integration.show_mcp_hook_status(self.module_metrics)

    def show_mcp_action_log(self, limit: int = 10) -> None:
        self.mcp_integration.show_mcp_action_log(limit)

    def check_pid_health(self) -> List[str]:
        return self.pid_detective.check_pid_health()

    def show_pid_detective(self) -> None:
        self.pid_detective.show_pid_detective()
        
    def check_git_health(self) -> Dict[str, Any]:
        return self.skill_executor.check_git_health()

# Legacy compatibility functions (for gradual migration)
def start_holodae():
    """Legacy compatibility - start HoloDAE monitoring"""
    if not _urllib_request:
        print("[HOLODAE] Python stdlib urllib not available; aborting.")
        return False

    base_url = os.getenv("HOLO_LLM_BASE_URL") or ""
    if not base_url:
        print("[HOLODAE] Missing HOLO_LLM_BASE_URL. Start overseer (Qwen/Gemma) and set the env before launching.")
        return False

    probe_url = base_url.rstrip("/") + "/models"
    try:
        with _urllib_request.urlopen(probe_url, timeout=5) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}")
    except Exception as exc:  # pragma: no cover - best effort guard
        print(f"[HOLODAE] Overseer endpoint not reachable at {probe_url}: {exc}")
        print("          Start the overseer model server (e.g., LM Studio on port 1235) and retry.")
        return False

    coordinator = HoloDAECoordinator()
    coordinator.enable_monitoring()
    return coordinator.start_monitoring()

def stop_holodae():
    """Legacy compatibility - stop HoloDAE monitoring"""
    coordinator = HoloDAECoordinator()
    return coordinator.stop_monitoring()

def get_holodae_status():
    """Legacy compatibility - get HoloDAE status"""
    coordinator = HoloDAECoordinator()
    return coordinator.get_status_summary()

def show_holodae_menu():
    """Legacy compatibility - show HoloDAE menu"""
    coordinator = HoloDAECoordinator()
    return coordinator.show_menu()

if __name__ == "__main__":
    coordinator = HoloDAECoordinator()
    print("HoloDAE Coordinator initialized with modular architecture")
    print(f"Status: {coordinator.get_status_summary()}")
