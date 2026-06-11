"""
Unified Agent Logging System for 0102 Multi-Agent Coordination
WSP 48 Recursive Learning - Enables other agents to follow DBA entries

This creates a single log stream where all agents (HoloIndex, Qwen, 0102, etc.)
can post their activities with clear identification, allowing seamless coordination.
"""

import os
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict




if os.name == 'nt':
    try:
        import ctypes
        if ctypes.windll.kernel32.GetConsoleOutputCP() != 65001:
            os.system('chcp 65001 >nul')
    except Exception:
        pass

def _current_identity() -> str:
    """Resolve the active 0102 agent identity."""
    raw_identity = (os.getenv("HOLO_ID_0102") or os.getenv("0102_HOLO_ID") or os.getenv("HOLO_AGENT_ID") or "").strip()
    return raw_identity if raw_identity else "0102"

class AgentLogger:
    """Unified logging system for all 0102 agents with HOLO_AGENT_ID identification."""

    def __init__(self, agent_role: str = None, log_file: str = "holo_index/logs/unified_agent_activity.log"):
        self.identity = _current_identity()
        self.agent_role = (agent_role or self.identity).strip()
        self.agent_label = self.identity if self.agent_role == self.identity else f"{self.identity}::{self.agent_role}"
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Setup Python logging for structured output
        self.logger = logging.getLogger(f"agent_{self.agent_label}")
        self.logger.setLevel(logging.INFO)

        # Remove any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add our custom handler
        handler = UnifiedAgentHandler(self.agent_label, self.log_file)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')  # Handler formats message
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.propagate = False

        # Log agent initialization
        self.logger.info(
            f"[AGENT-INIT] role={self.agent_role} identity={self.identity} stream=unified"
        )

    def log_search(self, query: str, results_count: int = 0, **kwargs):
        """Log HoloIndex search activities for other agents to follow."""
        details = [f"query='{query}'", f"results={results_count}"]
        code_results = kwargs.get('code_results')
        wsp_results = kwargs.get('wsp_results')
        if isinstance(code_results, list):
            details.append(f"code_hits={len(code_results)}")
        if isinstance(wsp_results, list):
            details.append(f"wsp_hits={len(wsp_results)}")

        # Add agent context and trigger Qwen focus
        agent_context = kwargs.get('agent_context', 'unknown')
        if agent_context != 'unknown':
            details.append(f"agent_context={agent_context}")

        # Signal Qwen to focus on this area
        focus_areas = []
        if isinstance(code_results, list) and code_results:
            modules = set()
            for result in code_results[:3]:  # Top 3 results
                metadata = result.get('metadata', {})
                module = metadata.get('module', metadata.get('path', ''))
                if module:
                    modules.add(module.split('/')[0] if '/' in module else module)
            if modules:
                focus_areas.extend(modules)

        if focus_areas:
            details.append(f"qwen_focus={','.join(focus_areas[:3])}")

        # REMINDER: Always use ASCII, never emojis - prevents Unicode encoding violations
        if 'emoji' in query.lower() or any(char in query for char in ['[SEARCH]', '[AI]', '[U+26A0]️', '[FAIL]']):
            details.append("REMINDER: Use ASCII tags like [SEARCH], [THINK], [WARN], [SUCCESS], [ERROR] - NEVER emojis (causes UnicodeEncodeError on Windows)")

        detail_str = " | ".join(details)
        self.logger.info(f"[SEARCH] {detail_str}")

    def log_breadcrumb(self, action: str, breadcrumb_id: int, **kwargs):
        """Log breadcrumb activities for DBA following with agent attribution."""
        details = []

        # Add agent attribution
        agent_id = kwargs.get('agent_id', self.identity)
        if agent_id:
            details.append(f"agent={agent_id}")

        # Add session context
        session_id = kwargs.get('session_id')
        if session_id:
            details.append(f"session={session_id}")

        # Add query and results
        if 'query' in kwargs and kwargs['query']:
            details.append(f"query={kwargs['query']}")
        results = kwargs.get('results')
        if isinstance(results, list):
            details.append(f"results={len(results)}")

        # Add rich data context
        data = kwargs.get('data')
        if isinstance(data, dict):
            if data.get('contract_id'):
                details.append(f"contract={data['contract_id']}")
            if data.get('task_id'):
                details.append(f"task={data['task_id']}")
            if data.get('description'):
                desc = data['description']
                desc_short = desc if len(desc) <= 60 else desc[:57] + '...'
                details.append(f"description=\"{desc_short}\"")
            if data.get('impact'):
                details.append(f"impact={data['impact']}")
            if data.get('required_skills'):
                skills = data['required_skills']
                if isinstance(skills, list):
                    details.append(f"skills={','.join(skills[:3])}")

        # Add direct contract/task references
        if kwargs.get('contract_id'):
            details.append(f"contract={kwargs['contract_id']}")
        if kwargs.get('task_id'):
            details.append(f"task={kwargs['task_id']}")

        detail_str = " | ".join(details) if details else "recorded"
        self.logger.info(f"[BREAD] [BREADCRUMB #{breadcrumb_id}] {action} - {detail_str}")

    def log_analysis(self, analysis_type: str, target: str, **kwargs):
        """Log Qwen/HoloDAE analysis activities with agent context."""
        details = [f"target={target}"]

        # Add agent context if provided
        agent_context = kwargs.get('agent_context')
        if agent_context:
            details.append(f"agent={agent_context}")

        if kwargs.get('confidence') is not None:
            try:
                details.append(f"confidence={float(kwargs['confidence']):.1%}")
            except (ValueError, TypeError):
                details.append(f"confidence={kwargs['confidence']}")
        patterns = kwargs.get('patterns')
        if isinstance(patterns, (list, tuple, set)):
            details.append(f"patterns={len(patterns)}")
        detail_str = " | ".join(details)
        self.logger.info(f"[ANALYSIS:{analysis_type.upper()}] {detail_str}")

    def log_decision(self, decision: str, reasoning: str = "", **kwargs):
        """Log agent decisions for coordination."""
        details = []
        if reasoning:
            details.append(f"reasoning='{reasoning[:50]}...'")
        if kwargs.get('priority'):
            details.append(f"priority={kwargs['priority']}")

        detail_str = " | ".join(details) if details else ""
        message = f"[DECISION] {decision}"
        if detail_str:
            message = f"{message} | {detail_str}"
        self.logger.info(message)

    def log_action(self, action: str, target: str = "", **kwargs):
        """Log agent actions taken."""
        details = []
        if target:
            details.append(f"target={target}")
        if kwargs.get('result'):
            details.append(f"result={kwargs['result']}")

        detail_str = " | ".join(details)
        message = f"[ACTION] {action}"
        if detail_str:
            message = f"{message} | {detail_str}"
        self.logger.info(message)

    def info(self, message: str):
        """General info logging."""
        self.logger.info(f"[INFO] {message}")

    def warning(self, message: str):
        """Warning logging."""
        self.logger.warning(f"[WARN] {message}")

    def error(self, message: str):
        """Error logging."""
        self.logger.error(f"[ERROR] {message}")

class UnifiedAgentHandler(logging.Handler):
    """Custom handler that formats messages for unified agent coordination."""

    def __init__(self, agent_label: str, log_file: Path):
        super().__init__()
        self.agent_label = agent_label
        self.log_file = log_file

    def emit(self, record):
        """Emit formatted log message to both console and file."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{self.agent_label}] {record.getMessage()}"
        message = record.getMessage()
        try:
            verbose_mode = os.getenv('HOLO_VERBOSE', '').lower() in {'1', 'true', 'yes'}
            important = any(tag in message for tag in ("[WARN]", "[ERROR]", "[FAIL]"))
            silent = os.getenv('HOLO_SILENT', '').lower() in {'1', 'true', 'yes', 'on'}
            breadcrumb_logs = os.getenv('HOLO_BREADCRUMB_LOGS', '').lower() in {'1', 'true', 'yes', 'on'}
            is_breadcrumb_logger = "BREADCRUMB" in self.agent_label
            allow_console = (not silent) and (verbose_mode or important)
            if is_breadcrumb_logger and not breadcrumb_logs:
                allow_console = False
            if allow_console:
                print(formatted_message)
        except Exception:
            pass
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{formatted_message}\n")
        except Exception:
            pass

# Global agent logger cache
_logger_cache: Dict[str, AgentLogger] = {}

def get_agent_logger(agent_role: str = None) -> AgentLogger:
    """Get or create the unified agent logger instance."""
    role_key = (agent_role or "DEFAULT").strip()
    identity = _current_identity()
    logger = _logger_cache.get(role_key)
    if logger is None or getattr(logger, "identity", None) != identity:
        logger = AgentLogger(agent_role)
        _logger_cache[role_key] = logger
    return logger

def log_holo_search(query: str, results_count: int = 0, **kwargs):
    """Convenience function for HoloIndex search logging."""
    logger = get_agent_logger("HOLO-SEARCH")
    logger.log_search(query, results_count, **kwargs)

def log_qwen_analysis(analysis_type: str, target: str, **kwargs):
    """Convenience function for Qwen analysis logging."""
    logger = get_agent_logger("QWEN-ANALYSIS")
    logger.log_analysis(analysis_type, target, **kwargs)

def log_breadcrumb_activity(action: str, breadcrumb_id: int, **kwargs):
    """Convenience function for breadcrumb activity logging."""
    logger = get_agent_logger("BREADCRUMB")
    logger.log_breadcrumb(action, breadcrumb_id, **kwargs)

