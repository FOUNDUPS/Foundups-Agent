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

Enhanced Breadcrumb Tracer for HoloIndex - Multi-Agent Intelligence Streams
WSP 48 Recursive Learning with 0102/0102 Collaboration Contracts

This creates actionable intelligence streams enabling seamless multi-agent collaboration:
1. Handoff Contracts: Specific task assignments with time estimates
2. Agent Collaboration Triggers: Signals when other agents should join
3. Task Assignments: Concrete work packages for parallel development
4. Collaboration Toggles: 0102 agents can signal availability

Other 0102 agents can read these streams to immediately understand:
- What work is being done
- What specific help is needed
- How long tasks will take
- Who should handle each task
- When collaboration is active
"""

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Unified agent logging for multi-agent coordination
try:
    from holo_index.utils.agent_logger import log_breadcrumb_activity
    UNIFIED_LOGGING_AVAILABLE = True
except ImportError:
    UNIFIED_LOGGING_AVAILABLE = False

# WSP 78 Database imports
from modules.infrastructure.database.src.agent_db import AgentDB

logger = logging.getLogger(__name__)


def _new_runtime_id(prefix: str) -> str:
    """Create a collision-resistant runtime identifier for adaptive-learning records."""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:8]}"


def _breadcrumb_enabled() -> bool:
    return os.getenv("HOLO_BREADCRUMB_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _breadcrumb_logs_enabled() -> bool:
    return os.getenv("HOLO_BREADCRUMB_LOGS", "true").lower() in {"1", "true", "yes", "on"}


class _NullBreadcrumbTracer:
    """No-op tracer to suppress breadcrumb logging and background threads."""

    def add_search(self, *args, **kwargs):
        return None

    def add_action(self, *args, **kwargs):
        return None

    def add_documentation_link(self, *args, **kwargs):
        return None

    def create_handoff_contract(self, *args, **kwargs):
        return ""

    def signal_collaboration_readiness(self, *args, **kwargs):
        return None

    def get_available_collaborators(self, *args, **kwargs):
        return []

    def assign_task_from_contract(self, *args, **kwargs):
        return False

    def complete_contract(self, *args, **kwargs):
        return False

    def get_active_contracts(self, *args, **kwargs):
        return []

    def discover_autonomous_task(self, *args, **kwargs):
        return ""

    def enable_autonomous_mode(self, *args, **kwargs):
        return None

    def get_autonomous_status(self, *args, **kwargs):
        return {"enabled": False}

    def get_recent_agents(self, *args, **kwargs):
        return []

    def __getattr__(self, name):
        def _noop(*_args, **_kwargs):
            return None
        return _noop


@dataclass
class HandoffContract:
    """A concrete task assignment with time estimate and ownership."""
    contract_id: str
    task_description: str
    assigned_agent: str
    estimated_minutes: int
    priority: str  # "high", "medium", "low"
    dependencies: List[str]
    deliverables: List[str]
    created_at: str
    deadline: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CollaborationSignal:
    """Signal that an agent is ready to collaborate."""
    agent_id: str
    collaboration_mode: str  # "active", "passive", "focused"
    available_until: str
    skills_offered: List[str]
    current_focus: str
    last_ping: str
    autonomy_level: str = "semi"  # "manual", "semi", "full"
    workload_capacity: float = 1.0  # 0.0-1.0, how much work agent can take

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AutonomousTask:
    """A task discovered autonomously by agents."""
    task_id: str
    description: str
    required_skills: List[str]
    estimated_complexity: float  # 0.0-1.0
    priority_score: float  # 0.0-1.0, calculated autonomously
    discovered_by: str
    discovered_at: str
    context: Dict[str, Any]  # Additional context for task execution

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CoordinationEvent:
    """An autonomous coordination event between agents."""
    event_id: str
    event_type: str  # "task_discovery", "agent_available", "work_assignment", "collaboration_request"
    initiator_agent: str
    target_agents: List[str]
    payload: Dict[str, Any]
    timestamp: str
    resolution_status: str = "pending"  # "pending", "accepted", "rejected", "completed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BreadcrumbTracer:
    """Enhanced tracer with multi-agent collaboration contracts using WSP 78 database."""

    def __init__(self):
        # WSP 78 Database integration - replaces JSON files
        self.db = AgentDB()
        raw_agent_id = (os.getenv("HOLO_ID_0102") or os.getenv("0102_HOLO_ID") or "0102").strip()
        self.agent_id = raw_agent_id if raw_agent_id else "0102"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"{self.agent_id}_{timestamp}"
        if _breadcrumb_logs_enabled() and os.getenv("HOLO_SILENT", "0").lower() not in {"1", "true", "yes", "on"}:
            logger.info("[BREADCRUMB] Session started for agent %s (%s)", self.agent_id, self.session_id)

        # In-memory caches for performance (synced with database)
        self.active_contracts = []
        self.collaboration_signals = {}
        self.autonomous_tasks = []
        self.coordination_events = []

        # Console announcement tracking
        self._console_hint_shown = False

        # Breadcrumb broadcast counter for local tracking
        self._breadcrumb_counter = 0

        # Autonomous coordination settings
        self.autonomous_mode = True
        self.task_discovery_enabled = True
        self.auto_assignment_enabled = True

        # Session-level deduplication for WSP violations (prevent spam)
        self._discovered_violations = set()  # Track violations already reported this session

        # Load existing data from database
        self._load_from_database()

        # Start autonomous coordination
        self.collaboration_monitor = threading.Thread(target=self._monitor_collaboration, daemon=True)
        self.task_discovery_monitor = threading.Thread(target=self._autonomous_task_discovery, daemon=True)
        self.coordination_processor = threading.Thread(target=self._process_coordination_events, daemon=True)

        self.collaboration_monitor.start()
        self.task_discovery_monitor.start()
        self.coordination_processor.start()

        if _breadcrumb_logs_enabled() and os.getenv("HOLO_SILENT", "0").lower() not in {"1", "true", "yes", "on"}:
            logger.info(
                "[BRAIN] AUTONOMOUS Breadcrumb Tracer initialized - WSP 78 database enabled - 0102/0102 coordination active"
            )

    def _add_breadcrumb(self, action: str, **kwargs) -> int:
        """Persist breadcrumb for shared memory and emit live updates."""
        breadcrumb_id = self.db.add_breadcrumb(
            session_id=self.session_id,
            action=action,
            agent_id=self.agent_id,
            **kwargs
        )

        self._breadcrumb_counter += 1
        fallback_identifiers = {None, 0, 1, "1"}
        reference_id = self._breadcrumb_counter if breadcrumb_id in fallback_identifiers else breadcrumb_id

        # Log to unified agent stream so 012 and other agents can follow DBA entries
        if UNIFIED_LOGGING_AVAILABLE:
            # Add agent and session context
            enriched_kwargs = kwargs.copy()
            enriched_kwargs['agent_id'] = self.agent_id
            enriched_kwargs['session_id'] = self.session_id
            log_breadcrumb_activity(action, reference_id, **enriched_kwargs)

        # Also log locally for backward compatibility
        self._log_breadcrumb(action, kwargs, reference_id)
        return breadcrumb_id

    def _log_breadcrumb(self, action: str, payload: Dict[str, Any], breadcrumb_id: int) -> None:
        """Emit breadcrumb summary for shared logs without console noise."""
        try:
            details: List[str] = []
            query = payload.get("query")
            if query:
                details.append(f"query={query}")
            results = payload.get("results")
            if isinstance(results, list):
                details.append(f"results={len(results)}")
            related_docs = payload.get("related_docs")
            if isinstance(related_docs, list) and related_docs:
                details.append(f"docs={len(related_docs)}")
            data = payload.get("data")
            if isinstance(data, dict) and data:
                contract_id = data.get("contract_id")
                if contract_id:
                    details.append(f"contract={contract_id}")
                task_id = data.get("task_id")
                if task_id:
                    details.append(f"task={task_id}")
                description = data.get("description")
                if description:
                    desc_short = description if len(description) <= 60 else description[:57] + "..."
                    details.append(f'description="{desc_short}"')
                impact = data.get("impact")
                if impact:
                    details.append(f"impact={impact}")
            contract_direct = payload.get("contract_id")
            if contract_direct:
                details.append(f"contract={contract_direct}")
            task_direct = payload.get("task_id")
            if task_direct:
                details.append(f"task={task_direct}")
            detail_text = " | ".join(details) if details else "recorded"
            timestamp = datetime.now().strftime("%H:%M:%S")
            if not _breadcrumb_logs_enabled() or os.getenv("HOLO_SILENT", "0").lower() in {"1", "true", "yes", "on"}:
                return
            message = f"[{timestamp}] [BREADCRUMB][{self.agent_id}][{self.session_id}][{breadcrumb_id}] {action}: {detail_text}"
            logger.info(message)
        except Exception as exc:
            logger.debug("Breadcrumb logging failed: %s", exc)
    def _load_from_database(self):
        """Load existing data from database into memory caches."""
        try:
            # Load active contracts
            self.active_contracts = self.db.get_active_contracts()

            # Load collaboration signals (get all available collaborators)
            collaborators = self.db.get_collaborators()
            self.collaboration_signals = {c['agent_id']: c for c in collaborators}

            # Load pending autonomous tasks
            self.autonomous_tasks = self.db.get_autonomous_tasks("pending", 100)

            # Load pending coordination events
            self.coordination_events = self.db.get_coordination_events("pending", 50)

            logger.debug(f"[DB] Loaded {len(self.active_contracts)} contracts, {len(self.collaboration_signals)} signals, {len(self.autonomous_tasks)} tasks, {len(self.coordination_events)} events")

        except Exception as e:
            logger.error(f"Failed to load data from database: {e}")
            # Initialize empty caches on failure
            self.active_contracts = []
            self.collaboration_signals = {}
            self.autonomous_tasks = []
            self.coordination_events = []

        # Breadcrumb broadcast counter for local tracking
        self._breadcrumb_counter = 0

    def add_search(self, query: str, results: List[Dict], related_docs: List[str]):
        """Record a search operation with results and related documentation."""
        # Use database instead of JSON files (WSP 78)
        self._add_breadcrumb(
            action="search",
            query=query,
            results=results[:3],  # Store top 3 results
            related_docs=related_docs
        )

    def add_discovery(self, discovery_type: str, item: str, location: str, impact: str = ""):
        """Record a discovery made during search."""
        self._add_breadcrumb(
            action="discovery",
            data={
                "type": discovery_type,
                "item": item,
                "location": location,
                "impact": impact
            }
        )

    def add_action(self, action: str, target: str, result: str, learned: str = None):
        """Record an action taken and its result."""
        self._add_breadcrumb(
            action="action_taken",
            data={
                "what": action,
                "target": target,
                "result": result,
                "learned": learned
            }
        )

    def add_documentation_link(self, search: str, doc_path: str, relevance: float):
        """Record a link to relevant documentation."""
        self._add_breadcrumb(
            action="doc_link",
            query=search,
            data={
                "doc_path": doc_path,
                "relevance": relevance
            }
        )


    def get_session_trail(self) -> List[Dict]:
        """Get the current session's breadcrumb trail."""
        return self.db.get_breadcrumbs(session_id=self.session_id)

    def get_recent_agents(self, minutes: int = 120, limit: int = 5) -> List[str]:
        """Return recent agent identifiers contributing breadcrumbs."""
        if not hasattr(self.db, "get_recent_breadcrumb_agents"):
            return []
        try:
            return self.db.get_recent_breadcrumb_agents(minutes=minutes, limit=limit)
        except Exception:
            return []

    def get_recent_discoveries(self, limit: int = 10) -> List[Dict]:
        """Get recent discoveries across all sessions."""
        try:
            # Get all breadcrumbs and filter for discoveries
            all_breadcrumbs = self.db.get_breadcrumbs(limit=limit * 5)  # Get more to filter
            discoveries = []

            for bc in all_breadcrumbs:
                if bc.get("action") == "discovery" and bc.get("data"):
                    # Convert database format back to expected format
                    discovery = {
                        "timestamp": bc["timestamp"],
                        "session_id": bc["session_id"],
                        "action": "discovery",
                        **bc["data"]
                    }
                    discoveries.append(discovery)

            # Sort by timestamp and return most recent
            discoveries.sort(key=lambda x: x["timestamp"], reverse=True)
            return discoveries[:limit]

        except Exception as e:
            logger.error(f"Failed to get recent discoveries: {e}")
            return []

    def summarize_session(self) -> Dict:
        """Summarize the current session for other agents."""
        session_breadcrumbs = self.get_session_trail()

        summary = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_actions": len(session_breadcrumbs),
            "searches": [],
            "discoveries": [],
            "actions": [],
            "docs_found": [],
            "learnings": []
        }

        for bc in session_breadcrumbs:
            if bc["action"] == "search":
                summary["searches"].append({
                    "query": bc.get("query", ""),
                    "results": len(bc.get("results", [])),
                    "docs": bc.get("related_docs", [])
                })
            elif bc["action"] == "discovery" and bc.get("data"):
                summary["discoveries"].append({
                    "type": bc["data"].get("type"),
                    "item": bc["data"].get("item"),
                    "location": bc["data"].get("location")
                })
            elif bc["action"] == "action_taken" and bc.get("data"):
                summary["actions"].append({
                    "what": bc["data"].get("what"),
                    "target": bc["data"].get("target"),
                    "result": bc["data"].get("result")
                })
                if bc["data"].get("learned"):
                    summary["learnings"].append(bc["data"]["learned"])
            elif bc["action"] == "doc_link" and bc.get("data"):
                summary["docs_found"].append(bc["data"].get("doc_path"))

        return summary

    # ============================================================================
    # ENHANCED COLLABORATION FEATURES
    # ============================================================================

    def create_handoff_contract(self, task_description: str, assigned_agent: str,
                               estimated_minutes: int, priority: str = "medium",
                               dependencies: List[str] = None, deliverables: List[str] = None) -> str:
        """Create a handoff contract for multi-agent task assignment."""
        contract_id = _new_runtime_id("contract")

        # Add deadline if high priority
        deadline = None
        if priority == "high":
            deadline = (datetime.now() + timedelta(minutes=estimated_minutes)).isoformat()

        # Create contract in database (WSP 78)
        success = self.db.create_contract(
            contract_id=contract_id,
            task_description=task_description,
            assigned_agent=assigned_agent,
            estimated_minutes=estimated_minutes,
            priority=priority,
            dependencies=dependencies,
            deliverables=deliverables,
            deadline=deadline
        )

        if success:
            # Update in-memory cache
            contract = self.db.get_contract(contract_id)
            if contract:
                self.active_contracts.append(contract)

            # Create breadcrumb for contract creation
            self._add_breadcrumb(
                action="contract_created",
                data={
                    "contract_id": contract_id,
                    "task": task_description,
                    "assigned_to": assigned_agent,
                    "estimated_time": f"{estimated_minutes} minutes",
                    "priority": priority
                }
            )

            logger.info(f"[TASK] Contract created: {task_description} -> {assigned_agent} ({estimated_minutes}min)")
            return contract_id
        else:
            logger.error(f"Failed to create contract in database")
            return None

    def signal_collaboration_readiness(self, agent_id: str, mode: str = "active",
                                      skills: List[str] = None, focus: str = "general") -> None:
        """Signal that an agent is ready to collaborate."""
        # Use database instead of JSON files (WSP 78)
        success = self.db.signal_collaboration(
            agent_id=agent_id,
            collaboration_mode=mode,
            available_until=(datetime.now() + timedelta(hours=2)).isoformat(),
            skills_offered=skills,
            current_focus=focus
        )

        if success:
            # Update in-memory cache
            collaborators = self.db.get_collaborators()
            self.collaboration_signals = {c['agent_id']: c for c in collaborators}

            logger.info(f"[HANDSHAKE] {agent_id} signaled collaboration readiness (mode: {mode})")
        else:
            logger.error(f"Failed to signal collaboration for {agent_id}")

    def get_available_collaborators(self, required_skills: List[str] = None) -> List[Dict[str, Any]]:
        """Get list of agents currently signaling collaboration readiness."""
        # Use database instead of JSON files (WSP 78)
        return self.db.get_collaborators(required_skills)

    def assign_task_from_contract(self, contract_id: str, actual_agent: str) -> bool:
        """Assign a contract task to an actual agent (may differ from originally assigned)."""
        # Update contract in database (WSP 78)
        success = self.db.update_contract(contract_id, {"assigned_agent": actual_agent})

        if success:
            # Update in-memory cache
            self._load_from_database()  # Refresh cache

            # Get updated contract for breadcrumb
            contract = self.db.get_contract(contract_id)
            if contract:
                # Create breadcrumb for assignment
                self._add_breadcrumb(
                    action="contract_assigned",
                    data={
                        "contract_id": contract_id,
                        "assigned_to": actual_agent,
                        "task": contract["task_description"]
                    }
                )

                logger.info(f"[OK] Contract {contract_id} assigned to {actual_agent}")
                return True

        logger.warning(f"Failed to assign contract {contract_id} to {actual_agent}")
        return False

    def complete_contract(self, contract_id: str, deliverables: List[str] = None) -> bool:
        """Mark a contract as completed."""
        # Complete contract in database (WSP 78)
        success = self.db.complete_contract(contract_id)

        if success:
            # Update in-memory cache
            self._load_from_database()  # Refresh cache

            # Get contract details for breadcrumb
            contract = self.db.get_contract(contract_id)
            if contract:
                # Create completion breadcrumb
                self._add_breadcrumb(
                    action="contract_completed",
                    data={
                        "contract_id": contract_id,
                        "task": contract.get("task_description"),
                        "assigned_to": contract.get("assigned_agent"),
                        "actual_deliverables": deliverables or contract.get("deliverables", []),
                        "completion_time": datetime.now().isoformat()
                    }
                )

                logger.info(f"[COMPLETE] Contract {contract_id} completed by {contract.get('assigned_agent')}")
                return True

        logger.warning(f"Failed to complete contract {contract_id}")
        return False

    def get_active_contracts(self, agent_filter: str = None) -> List[Dict[str, Any]]:
        """Get active contracts, optionally filtered by assigned agent."""
        # Use database instead of in-memory cache (WSP 78)
        return self.db.get_active_contracts(agent_filter)

    def _monitor_collaboration(self):
        """Monitor collaboration signals and clean up expired ones."""
        while True:
            try:
                # Clean up expired collaboration signals
                current_time = datetime.now()
                expired_agents = []

                for agent_id, signal in self.collaboration_signals.items():
                    available_until = datetime.fromisoformat(signal.available_until)
                    if current_time > available_until:
                        expired_agents.append(agent_id)

                for agent_id in expired_agents:
                    del self.collaboration_signals[agent_id]
                    logger.debug(f"[CLEANUP] Cleaned up expired collaboration signal for {agent_id}")

                # Check for new contracts that need assignment
                self._check_contract_assignments()

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in collaboration monitor: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def _check_contract_assignments(self):
        """Check for contracts that need agent assignment based on availability."""
        for contract in self.active_contracts:
            if contract.get("assigned_agent") == "unassigned":
                # Look for available agents with matching skills
                required_skills = self._extract_skills_from_task(contract.get("task_description", ""))
                available_agents = self.get_available_collaborators(required_skills)

                if available_agents:
                    # Assign to first available agent
                    best_agent = available_agents[0]["agent_id"]
                    self.assign_task_from_contract(contract.get("contract_id"), best_agent)
                    logger.info(f"[HANDSHAKE] Auto-assigned contract {contract.get('contract_id')} to {best_agent}")

    def _extract_skills_from_task(self, task: str) -> List[str]:
        """Extract required skills from task description."""
        skills = []

        task_lower = task.lower()
        if "test" in task_lower or "testing" in task_lower:
            skills.append("testing")
        if "code" in task_lower or "implement" in task_lower:
            skills.append("coding")
        if "design" in task_lower or "architecture" in task_lower:
            skills.append("architecture")
        if "document" in task_lower or "readme" in task_lower:
            skills.append("documentation")

        return skills or ["general_assistance"]



    # ============================================================================
    # AUTONOMOUS COORDINATION SYSTEM
    # ============================================================================

    def discover_autonomous_task(self, task_description: str, context: Dict[str, Any] = None) -> str:
        """Autonomously discover and register a task that needs to be done."""
        task_id = _new_runtime_id("auto_task")

        # Analyze task to determine requirements
        required_skills = self._analyze_task_requirements(task_description)
        complexity = self._estimate_task_complexity(task_description, context or {})
        priority = self._calculate_task_priority(task_description, context or {})

        # Create autonomous task in database (WSP 78)
        success = self.db.create_autonomous_task(
            task_id=task_id,
            description=task_description,
            required_skills=required_skills,
            estimated_complexity=complexity,
            priority_score=priority,
            context=context
        )

        if success:
            # Update in-memory cache
            self.autonomous_tasks = self.db.get_autonomous_tasks("pending", 100)

            # Create coordination event for task discovery
            self._create_coordination_event(
                "task_discovery",
                "autonomous_discovery",
                [],  # Broadcast to all available agents
                {"task": {
                    "task_id": task_id,
                    "description": task_description,
                    "required_skills": required_skills,
                    "estimated_complexity": complexity,
                    "priority_score": priority,
                    "context": context
                }}
            )

            # Create breadcrumb for autonomous task discovery
            self._add_breadcrumb(
                action="autonomous_task_discovered",
                data={
                    "task_id": task_id,
                    "description": task_description,
                    "required_skills": required_skills,
                    "complexity": complexity,
                    "priority": priority
                }
            )

            logger.info(f"[TARGET] Autonomous task discovered: {task_description} (priority: {priority:.2f})")
            return task_id

        logger.error(f"Failed to create autonomous task in database")
        return None

    def enable_autonomous_mode(self, agent_id: str, capabilities: Dict[str, Any]) -> None:
        """Enable autonomous mode for an agent with full self-assessment capabilities."""
        # Assess agent's autonomy level based on capabilities
        autonomy_level = self._assess_agent_autonomy(capabilities)

        # Calculate workload capacity
        workload_capacity = self._calculate_workload_capacity(capabilities)

        # Auto-signal collaboration readiness
        skills = capabilities.get("skills", [])
        focus = capabilities.get("current_focus", "autonomous_operation")

        signal = CollaborationSignal(
            agent_id=agent_id,
            collaboration_mode="autonomous",
            available_until=(datetime.now() + timedelta(hours=24)).isoformat(),  # 24/7 autonomous
            skills_offered=skills,
            current_focus=focus,
            last_ping=datetime.now().isoformat(),
            autonomy_level=autonomy_level,
            workload_capacity=workload_capacity
        )

        self.collaboration_signals[agent_id] = signal
        self._save_collaboration_signal(signal)

        # Create coordination event for autonomous agent joining
        self._create_coordination_event(
            "agent_autonomous",
            agent_id,
            [],  # Broadcast availability
            {
                "capabilities": capabilities,
                "autonomy_level": autonomy_level,
                "workload_capacity": workload_capacity
            }
        )

        logger.info(f"[AI] Agent {agent_id} entered autonomous mode (level: {autonomy_level})")

    def _autonomous_task_discovery(self):
        """Continuously monitor for tasks that need autonomous discovery."""
        while True:
            try:
                if self.task_discovery_enabled:
                    self._scan_for_work_opportunities()
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in autonomous task discovery: {e}")
                time.sleep(600)  # Wait longer on error

    def _scan_for_work_opportunities(self):
        """Scan the system for work that needs to be done autonomously."""
        # Check for WSP compliance violations
        wsp_violations = self._scan_wsp_violations()
        for violation in wsp_violations:
            # Create unique violation key for session deduplication (Occam's Razor)
            violation_key = f"{violation['location']}:{violation['description']}"

            # Skip if already discovered this session (prevent spam)
            if violation_key in self._discovered_violations:
                continue

            # Mark as discovered
            self._discovered_violations.add(violation_key)

            # Create autonomous task
            self.discover_autonomous_task(
                f"Fix WSP violation: {violation['description']}",
                {
                    "violation_type": violation["type"],
                    "location": violation["location"],
                    "severity": violation["severity"]
                }
            )

        # Check for incomplete contracts that need follow-up
        stale_contracts = self._find_stale_contracts()
        for contract in stale_contracts:
            self.discover_autonomous_task(
                f"Follow up on stale contract: {contract.get('task_description', '')}",
                {"contract_id": contract.get("contract_id"), "reason": "stale"}
            )

    def _analyze_task_requirements(self, task_description: str) -> List[str]:
        """Analyze a task description to determine required skills."""
        skills = []
        desc_lower = task_description.lower()

        if "code" in desc_lower or "implement" in desc_lower:
            skills.append("coding")
        if "test" in desc_lower or "validate" in desc_lower:
            skills.append("testing")
        if "document" in desc_lower or "readme" in desc_lower:
            skills.append("documentation")
        if "design" in desc_lower or "architecture" in desc_lower:
            skills.append("architecture")
        if "wsp" in desc_lower or "compliance" in desc_lower:
            skills.append("wsp_compliance")

        return skills or ["general_assistance"]

    def _estimate_task_complexity(self, task_description: str, context: Dict) -> float:
        """Estimate the complexity of a task (0.0-1.0)."""
        complexity = 0.3  # Base complexity

        desc_lower = task_description.lower()

        # Keywords that increase complexity
        if "refactor" in desc_lower or "optimize" in desc_lower:
            complexity += 0.2
        if "multiple" in desc_lower or "complex" in desc_lower:
            complexity += 0.2
        if "architecture" in desc_lower or "design" in desc_lower:
            complexity += 0.1
        if "urgent" in desc_lower or "critical" in desc_lower:
            complexity += 0.2

        # Context factors
        if context.get("severity") == "high":
            complexity += 0.2

        return min(complexity, 1.0)

    def _calculate_task_priority(self, task_description: str, context: Dict) -> float:
        """Calculate task priority score (0.0-1.0)."""
        priority = 0.5  # Base priority

        desc_lower = task_description.lower()

        # High priority keywords
        if "critical" in desc_lower or "urgent" in desc_lower:
            priority += 0.3
        if "violation" in desc_lower or "error" in desc_lower:
            priority += 0.2
        if "security" in desc_lower or "fix" in desc_lower:
            priority += 0.1

        # Context factors
        if context.get("severity") == "high":
            priority += 0.2

        return min(priority, 1.0)

    def _assess_agent_autonomy(self, capabilities: Dict[str, Any]) -> str:
        """Assess an agent's autonomy level based on capabilities."""
        autonomy_features = capabilities.get("autonomy_features", [])

        if "full_task_execution" in autonomy_features and "independent_decision_making" in autonomy_features:
            return "full"
        elif "supervised_task_execution" in autonomy_features or "human_oversight" in autonomy_features:
            return "semi"
        else:
            return "manual"

    def _calculate_workload_capacity(self, capabilities: Dict[str, Any]) -> float:
        """Calculate agent's workload capacity (0.0-1.0)."""
        base_capacity = 1.0

        # Reduce capacity based on current workload
        current_tasks = capabilities.get("current_task_count", 0)
        if current_tasks > 5:
            base_capacity *= 0.3
        elif current_tasks > 3:
            base_capacity *= 0.6
        elif current_tasks > 1:
            base_capacity *= 0.8

        # Reduce capacity based on time constraints
        available_hours = capabilities.get("available_hours_per_day", 8)
        if available_hours < 4:
            base_capacity *= 0.5
        elif available_hours < 8:
            base_capacity *= 0.75

        return base_capacity

    def _scan_wsp_violations(self) -> List[Dict[str, Any]]:
        """Scan for WSP compliance violations that need fixing."""
        violations = []

        # This would integrate with actual WSP compliance checking
        # For now, return mock violations for demonstration
        try:
            # Check for missing module structures (simplified)
            import os
            modules_path = Path("modules")
            if modules_path.exists():
                for domain_dir in modules_path.iterdir():
                    if domain_dir.is_dir() and not domain_dir.name.startswith('_'):
                        for module_dir in domain_dir.iterdir():
                            # Skip non-module directories (Occam's Razor - filter noise)
                            if not module_dir.is_dir():
                                continue
                            if module_dir.name.startswith(('_', '.')):
                                continue
                            if module_dir.name in ('__pycache__', '.pytest_cache', 'node_modules'):
                                continue

                            # Check for missing WSP 49 structure
                            missing_items = []
                            if not (module_dir / "README.md").exists():
                                missing_items.append("README.md")
                            if not (module_dir / "src").exists():
                                missing_items.append("src/")

                            # Add violation if any items missing (correct indentation)
                            if missing_items:
                                violations.append({
                                    "type": "wsp_49_violation",
                                    "description": f"Module {module_dir.name} missing: {', '.join(missing_items)}",
                                    "location": str(module_dir),
                                    "severity": "medium"
                                })
        except Exception as e:
            logger.debug(f"Error scanning WSP violations: {e}")

        return violations

    def _find_stale_contracts(self) -> List[HandoffContract]:
        """Find contracts that haven't been updated recently."""
        stale_contracts = []
        cutoff = datetime.now() - timedelta(hours=24)  # 24 hours

        for contract in self.active_contracts:
            created_at = contract.get("created_at")
            if not created_at:
                continue
            try:
                contract_time = datetime.fromisoformat(created_at)
            except ValueError:
                continue
            if contract_time < cutoff and contract.get("assigned_agent") == "unassigned":
                stale_contracts.append(contract)

        return stale_contracts

    def _create_coordination_event(self, event_type: str, initiator: str,
                                 targets: List[str], payload: Dict[str, Any]) -> None:
        """Create a coordination event for inter-agent communication."""
        event_id = _new_runtime_id("coord")

        # Create coordination event in database (WSP 78)
        success = self.db.create_coordination_event(
            event_id=event_id,
            event_type=event_type,
            initiator_agent=initiator,
            target_agents=targets,
            payload=payload
        )

        if success:
            # Update in-memory cache
            self.coordination_events = self.db.get_coordination_events("pending", 50)

            logger.debug(f"[SIGNAL] Coordination event created: {event_type} from {initiator}")
        else:
            logger.error(f"Failed to create coordination event in database")

    def _process_coordination_events(self):
        """Process autonomous coordination events and take actions."""
        while True:
            try:
                # Get pending coordination events from database (WSP 78)
                pending_events = self.db.get_coordination_events("pending", 50)

                # Process pending coordination events
                for event_data in pending_events:
                    # Convert database dict back to CoordinationEvent-like object
                    event = type('CoordinationEvent', (), event_data)()
                    self._handle_coordination_event(event)

                # Clean up old resolved events (this is handled by limiting results in get_coordination_events)

                time.sleep(60)  # Process every minute
            except Exception as e:
                logger.error(f"Error processing coordination events: {e}")
                time.sleep(300)

    def _handle_coordination_event(self, event: CoordinationEvent):
        """Handle a specific coordination event."""
        if event.event_type == "task_discovery":
            # New task discovered - try to assign it
            task_data = event.payload.get("task", {})
            if task_data and self.auto_assignment_enabled:
                self._auto_assign_discovered_task(task_data)

        elif event.event_type == "agent_autonomous":
            # New autonomous agent available - redistribute work if needed
            agent_id = event.initiator_agent
            self._redistribute_work_for_new_agent(agent_id)

        # Mark event as processed in database (WSP 78)
        self.db.resolve_coordination_event(event.event_id, "completed")

    def _auto_assign_discovered_task(self, task_data: Dict[str, Any]):
        """Automatically assign a discovered task to an available agent."""
        required_skills = task_data.get("required_skills", [])
        priority = task_data.get("priority_score", 0.5)

        # Find best agent for this task
        available_agents = self.get_available_collaborators(required_skills)
        if not available_agents:
            logger.debug("No agents available for task assignment")
            return

        # Select best agent based on workload capacity and skill match
        best_agent = self._select_best_agent_for_task(available_agents, required_skills, priority)
        if best_agent:
            # Create contract for this task
            contract_id = self.create_handoff_contract(
                task_data["description"],
                best_agent["agent_id"],
                max(15, int(task_data.get("estimated_complexity", 0.5) * 60)),  # 15-60 minutes
                "high" if priority > 0.7 else "medium",
                deliverables=["autonomous_task_completed"]
            )

            logger.info(f"[AI] Auto-assigned task '{task_data['description']}' to {best_agent['agent_id']}")

    def _select_best_agent_for_task(self, agents: List[Dict], required_skills: List[str], priority: float) -> Dict:
        """Select the best agent for a task based on various factors."""
        if not agents:
            return None

        scored_agents = []
        for agent in agents:
            score = 0.0

            # Skill match score (0-0.5)
            agent_skills = set(agent.get("skills_offered", []))
            required_skills_set = set(required_skills)
            if required_skills_set:
                skill_match = len(agent_skills & required_skills_set) / len(required_skills_set)
                score += skill_match * 0.5

            # Workload capacity score (0-0.3)
            capacity = agent.get("workload_capacity", 1.0)
            score += capacity * 0.3

            # Autonomy preference for high-priority tasks (0-0.2)
            if priority > 0.7:
                autonomy = agent.get("autonomy_level", "semi")
                autonomy_score = {"manual": 0.0, "semi": 0.1, "full": 0.2}.get(autonomy, 0.0)
                score += autonomy_score

            scored_agents.append((agent, score))

        # Return agent with highest score
        if scored_agents:
            return max(scored_agents, key=lambda x: x[1])[0]
        return None

    def _redistribute_work_for_new_agent(self, new_agent_id: str):
        """Redistribute work when a new autonomous agent becomes available."""
        # Find high-priority unassigned contracts
        unassigned_contracts = [c for c in self.active_contracts if c.get("assigned_agent") == "unassigned"]

        for contract in unassigned_contracts:
            if contract.get('priority') == "high":
                # Check if new agent can handle this
                agent_signal = self.collaboration_signals.get(new_agent_id)
                if agent_signal and self._agent_can_handle_contract(agent_signal, contract):
                    self.assign_task_from_contract(contract.get("contract_id"), new_agent_id)
                    logger.info(f"[REFRESH] Redistributed high-priority contract to new agent {new_agent_id}")

    def _agent_can_handle_contract(self, agent_signal: CollaborationSignal, contract: HandoffContract) -> bool:
        """Check if an agent can handle a specific contract."""
        agent_skills = set(agent_signal.skills_offered)
        required_skills = set(self._extract_skills_from_task(contract.get("task_description", "")))

        # Must have at least 50% skill match
        skill_match = len(agent_skills & required_skills) / len(required_skills) if required_skills else 1.0
        return skill_match >= 0.5 and agent_signal.workload_capacity > 0.2

    def _save_autonomous_task(self, task: AutonomousTask):
        """Save autonomous task to WSP 78 database."""
        try:
            # Save to database using WSP 78 AgentDB
            self.db.create_autonomous_task(
                task_id=task.task_id,
                description=task.description,
                required_skills=task.required_skills,
                estimated_complexity=task.estimated_complexity,
                priority_score=task.priority_score,
                context=task.context
            )
        except Exception as e:
            logger.error(f"Failed to save autonomous task {task.task_id}: {e}")

    def _save_coordination_event(self, event: CoordinationEvent):
        """Save coordination event to WSP 78 database."""
        try:
            # Save to database using WSP 78 AgentDB
            self.db.create_coordination_event(
                event_id=event.event_id,
                event_type=event.event_type,
                initiator_agent=event.initiator_agent,
                target_agents=event.target_agents,
                payload=event.payload
            )
        except Exception as e:
            logger.error(f"Failed to save coordination event {event.event_id}: {e}")

    def _cleanup_resolved_events(self):
        """Clean up old resolved coordination events."""
        cutoff = datetime.now() - timedelta(hours=24)  # Keep events for 24 hours
        self.coordination_events = [
            e for e in self.coordination_events
            if datetime.fromisoformat(e.timestamp) > cutoff or e.resolution_status == "pending"
        ]


# Global instance for easy access
_tracer = None

def get_tracer() -> BreadcrumbTracer:
    """Get or create the global breadcrumb tracer."""
    global _tracer
    if _tracer is None:
        if not _breadcrumb_enabled():
            _tracer = _NullBreadcrumbTracer()
            return _tracer
        _tracer = BreadcrumbTracer()
    return _tracer

def trace_search(query: str, results: List[Dict], docs: List[str]):
    """Convenience function to trace a search."""
    get_tracer().add_search(query, results, docs)

def trace_action(action: str, target: str, result: str, learned: str = None):
    """Convenience function to trace an action."""
    get_tracer().add_action(action, target, result, learned)

def trace_doc_link(search: str, doc: str, relevance: float):
    """Convenience function to trace a documentation link."""
    get_tracer().add_documentation_link(search, doc, relevance)

# ============================================================================
# ENHANCED COLLABORATION CONVENIENCE FUNCTIONS
# ============================================================================

def create_contract(task: str, agent: str, minutes: int, priority: str = "medium") -> str:
    """Create a handoff contract for task assignment."""
    return get_tracer().create_handoff_contract(task, agent, minutes, priority)

def signal_ready(agent_id: str, mode: str = "active", skills: List[str] = None, focus: str = "general"):
    """Signal that an agent is ready to collaborate."""
    get_tracer().signal_collaboration_readiness(agent_id, mode, skills, focus)

def get_collaborators(required_skills: List[str] = None) -> List[Dict[str, Any]]:
    """Get list of available collaborators."""
    return get_tracer().get_available_collaborators(required_skills)

def assign_contract(contract_id: str, agent: str) -> bool:
    """Assign a contract to an agent."""
    return get_tracer().assign_task_from_contract(contract_id, agent)

def complete_contract(contract_id: str, deliverables: List[str] = None) -> bool:
    """Mark a contract as completed."""
    return get_tracer().complete_contract(contract_id, deliverables)

def get_my_contracts(agent_id: str) -> List[Dict[str, Any]]:
    """Get contracts assigned to a specific agent."""
    return get_tracer().get_active_contracts(agent_id)

# ============================================================================
# AUTONOMOUS COORDINATION CONVENIENCE FUNCTIONS
# ============================================================================

def discover_task(task: str, context: Dict[str, Any] = None) -> str:
    """Autonomously discover a task that needs to be done."""
    return get_tracer().discover_autonomous_task(task, context)

def enable_autonomy(agent_id: str, capabilities: Dict[str, Any]) -> None:
    """Enable autonomous mode for an agent."""
    get_tracer().enable_autonomous_mode(agent_id, capabilities)

def get_autonomous_status() -> Dict[str, Any]:
    """Get the autonomous coordination system status."""
    tracer = get_tracer()
    return {
        "autonomous_mode": tracer.autonomous_mode,
        "task_discovery_enabled": tracer.task_discovery_enabled,
        "auto_assignment_enabled": tracer.auto_assignment_enabled,
        "available_collaborators": len(tracer.get_available_collaborators()),
        "active_contracts": len(tracer.active_contracts),
        "autonomous_tasks": len(tracer.autonomous_tasks),
        "coordination_events": len(tracer.coordination_events)
    }




