# -*- coding: utf-8 -*-
"""
Skill Executor - WRE Integration for HoloDAE

Implements WSP 96 (Work Request Execution) logic for autonomous skill triggering.
This service analyzes monitoring results and executes appropriate skills based on
detected patterns and triggers.

WSP Compliance:
- WSP 96: Autonomous Skill Execution
- WSP 62: Modularity
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# Import Libido Monitor (WSP 96)
try:
    from modules.infrastructure.wre_core.src.libido_monitor import GemmaLibidoMonitor, LibidoSignal
except ImportError:
    # Fallback if path is different or module missing (during refactor)
    GemmaLibidoMonitor = None
    LibidoSignal = None

# Define WRE Trigger types
TRIGGER_PATTERN_MATCH = "pattern_match"
TRIGGER_CRITICAL_FIX = "critical_fix"
TRIGGER_ESCALATION = "escalation"

class SkillExecutor:
    """
    Executes skills based on WRE triggers from the monitoring loop.
    """

    def __init__(self, repo_root: Any, logger: Optional[logging.Logger] = None):
        self.repo_root = repo_root
        self.logger = logger or logging.getLogger(__name__)
        self.skills_registry = self._register_skills()
        
        # Initialize Libido Monitor if available
        if GemmaLibidoMonitor:
            self.libido_monitor = GemmaLibidoMonitor()
            self.logger.info("[WRE] Gemma Libido Monitor initialized")
        else:
            self.libido_monitor = None
            self.logger.warning("[WRE] Gemma Libido Monitor NOT found - running in bypass mode")

    def _register_skills(self) -> Dict[str, Any]:
        """Register available skills."""
        return {
            "qwen_gitpush": self._skill_git_push,
            "auto_fix": self._skill_auto_fix,
            "notify_coach": self._skill_notify_coach,
            "github_management": self._skill_github_management,
        }

    def check_wre_triggers(self, monitoring_result: Any) -> List[Dict[str, Any]]:
        """
        Analyze monitoring result for WRE triggers.
        
        Args:
            monitoring_result: MonitoringResult object from monitoring loop
            
        Returns:
            List of trigger dictionaries
        """
        triggers = []

        # 1. Check for High Confidence Pattern Alerts
        if hasattr(monitoring_result, 'pattern_alerts'):
            for alert in monitoring_result.pattern_alerts:
                if getattr(alert, 'confidence', 0.0) >= 0.9:
                    triggers.append({
                        "type": TRIGGER_PATTERN_MATCH,
                        "skill": "notify_coach",
                        "payload": {"alert": alert}
                    })

        # 2. Check for Critical CodeIndex Fixes
        if hasattr(monitoring_result, 'codeindex_reports'):
            for report in monitoring_result.codeindex_reports:
                if report.get('critical_fixes', 0) > 0:
                    triggers.append({
                        "type": TRIGGER_CRITICAL_FIX,
                        "skill": "auto_fix", # Placeholder: In real scenario, might be safer to notify first
                        "payload": {"report": report}
                    })

        return triggers

    def execute_wre_skills(self, triggers: List[Dict[str, Any]]) -> None:
        """
        Execute skills for the given triggers, gated by Libido Monitor.
        
        Args:
            triggers: List of trigger dictionaries
        """
        for trigger in triggers:
            skill_name = trigger.get("skill")
            payload = trigger.get("payload")
            execution_id = str(uuid.uuid4())
            
            if skill_name in self.skills_registry:
                # Check Libido Signal
                if self.libido_monitor:
                    signal = self.libido_monitor.should_execute(skill_name, execution_id)
                    
                    if signal == LibidoSignal.THROTTLE:
                        self.logger.info(f"[WRE] THROTTLED skill: {skill_name} (LibidoSignal.THROTTLE)")
                        continue
                    elif signal == LibidoSignal.ESCALATE:
                        self.logger.info(f"[WRE] ESCALATING skill: {skill_name} (LibidoSignal.ESCALATE)")
                        # Proceed with execution
                    else:
                        # LibidoSignal.CONTINUE
                        pass
                
                try:
                    self.logger.info(f"[WRE] Executing skill: {skill_name} [ID:{execution_id}]")
                    self.skills_registry[skill_name](payload)
                    
                    # Record execution success
                    if self.libido_monitor:
                        self.libido_monitor.record_execution(skill_name, "wre_executor", execution_id, fidelity_score=1.0)
                        
                except Exception as e:
                    self.logger.error(f"[WRE] Skill execution failed for {skill_name}: {e}")
            else:
                self.logger.warning(f"[WRE] Unknown skill: {skill_name}")

    # --- Skill Implementations ---

    def _skill_git_push(self, payload: Dict[str, Any]) -> None:
        """Execute git push skill (Real implementation - safe status check first)."""
        import subprocess
        try:
            # For safety, we first check status
            result = subprocess.run(
                ['git', 'status'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=self.repo_root,
            )
            self.logger.info(f"[WRE] SKILL: qwen_gitpush - Git Status:\n{result.stdout}")
            
            # In a real autonomous mode, we would push here:
            # subprocess.run(['git', 'push'], check=True, cwd=self.repo_root)
            self.logger.info(f"[WRE] SKILL: qwen_gitpush - Push simulated (safety mode)")
        except Exception as e:
            self.logger.error(f"[WRE] SKILL: qwen_gitpush failed: {e}")

    def _skill_auto_fix(self, payload: Dict[str, Any]) -> None:
        """Execute auto-fix skill (Placeholder)."""
        # This would call the Architect Engine to apply fixes
        self.logger.info(f"[WRE] SKILL: auto_fix triggered with {payload}")

    def _skill_notify_coach(self, payload: Dict[str, Any]) -> None:
        """Notify Pattern Coach (Placeholder)."""
        # This would send a message to the Pattern Coach
        self.logger.info(f"[WRE] SKILL: notify_coach triggered with {payload}")

    def _skill_github_management(self, payload: Dict[str, Any]) -> None:
        """Execute GitHub management skill (WSP 103)."""
        import asyncio
        try:
            from modules.infrastructure.github_orchestrator.skillz.github_management.executor import execute

            args = payload.get("args", "")
            self.logger.info(f"[WRE] SKILL: github_management triggered with args: {args}")

            # Run async executor
            result = asyncio.run(execute(args, payload))
            self.logger.info(f"[WRE] SKILL: github_management result: {result}")
        except ImportError as e:
            self.logger.warning(f"[WRE] SKILL: github_management unavailable: {e}")
        except Exception as e:
            self.logger.error(f"[WRE] SKILL: github_management error: {e}")
