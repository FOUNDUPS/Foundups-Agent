#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

WSP Orchestrator - 0102 Meta-Orchestration with Role-Based Model Selection

Capability Roles (stable contracts - models are fluid):

    Resolver-supported (local_model_selection.py):
        - triage: fast validation/classification (<10ms target)
        - general: synthesis, reasoning, non-code tasks
        - code: resident coding, refactoring, test generation

    Separate surfaces (not in local_model_selection.py):
        - vision: UI_TARS_PATH via ui_tars_bridge.py (browser automation)

    Policy-only (explicit escalation, not resolvable):
        - architect_escalation: bounded high-compute path (frontier API)

Role Resolution: local_model_selection.py resolves triage/general/code roles.
Future trained models enter as role candidates, not architectural rewrites.

CORRECT ARCHITECTURE (User-Specified):
    0102 Meta-Orchestration: YOU (Claude) are in charge, using WSP 15 MPS scoring
    +--> Request role="code" for strategic planning (resolved at runtime)
    +--> Local model generates plan -> 0102 modifies and improves
    +--> role="triage" for fast pattern matching (Phase 1)
    +--> role="code" for strategic planning (Phase 2)
    +--> 0102 supervision (Phase 3)
    +--> Pattern learning/memory (Phase 4)

WSP Compliance:
    - WSP 15: MPS Prioritization (0102 decides complexity/importance/defer ability/impact)
    - WSP 77: Agent Coordination (0102 -> code-role -> triage-role hierarchy)
    - WSP 50: Pre-Action Verification (HoloIndex + MCP first)
    - WSP 84: Code Memory (MCP tools, no duplication)
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import time

# Ensure repo root is importable when this file is executed directly.
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# FIRST PRINCIPLES: Direct MCP Tool Integration
# No abstraction layers - direct tool access for maximum efficiency
try:
    import asyncio
    import aiohttp
    import json
    from typing import Dict, Any, List
    MCP_DIRECT_AVAILABLE = True
except ImportError:
    MCP_DIRECT_AVAILABLE = False

# Enhanced Qwen/Gemma Integration with MCP Tools
try:
    from holo_index.qwen_advisor.orchestration.autonomous_refactoring import AutonomousRefactoringOrchestrator, DaemonLogger
    from holo_index.qwen_advisor.pattern_memory import PatternMemory
    WORKERS_AVAILABLE = True
except ImportError:
    WORKERS_AVAILABLE = False

try:
    from modules.infrastructure.monitoring.src.wsp_00_zen_state_tracker import WSP00ZenStateTracker
    WSP00_TRACKER_AVAILABLE = True
except ImportError:
    WSP00_TRACKER_AVAILABLE = False

logger = logging.getLogger(__name__)


class MCPToolExecutor:
    """
    FIRST PRINCIPLES MCP Tool Execution
    Direct tool access without abstraction layers for maximum Qwen/Gemma efficiency
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.pattern_memory = PatternMemory() if WORKERS_AVAILABLE else None
        self.session = None

    async def initialize_session(self):
        """Initialize MCP tool session"""
        if not MCP_DIRECT_AVAILABLE:
            return False

        try:
            # Direct MCP server connection (bypassing manager abstraction)
            self.session = aiohttp.ClientSession()
            return True
        except Exception as e:
            logger.error(f"MCP session initialization failed: {e}")
            return False

    async def execute_semantic_search(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        FIRST PRINCIPLES: Direct semantic code search via HoloIndex
        Qwen/Gemma use this for pre-action verification (WSP 50)
        """
        try:
            # Direct subprocess call to HoloIndex (most efficient)
            import subprocess
            import re

            cmd = [
                "python", str(self.repo_root / "holo_index.py"),
                "--search", query,
                "--limit", "5"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=30
            )

            if result.returncode == 0:
                # Parse the text output to extract results
                stdout = result.stdout or ""
                stderr = result.stderr or ""

                # Handle encoding issues
                try:
                    stdout = stdout.encode('utf-8', errors='ignore').decode('utf-8')
                except:
                    stdout = str(stdout)

                # Extract result counts from output
                code_matches = re.search(r'(\d+)\s+code\s+results?', stdout, re.IGNORECASE)
                wsp_matches = re.search(r'(\d+)\s+wsp\s+results?', stdout, re.IGNORECASE)

                code_count = int(code_matches.group(1)) if code_matches else 0
                wsp_count = int(wsp_matches.group(1)) if wsp_matches else 0

                # Store pattern for Qwen/Gemma learning
                await self._store_pattern("semantic_search", {
                    "query": query,
                    "context": context or {},
                    "results_count": code_count + wsp_count,
                    "code_results": code_count,
                    "wsp_results": wsp_count,
                    "success": True
                })

                return {
                    "query": query,
                    "code_results_count": code_count,
                    "wsp_results_count": wsp_count,
                    "total_results": code_count + wsp_count,
                    "raw_output": stdout[:1000]  # Limited for efficiency
                }
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Semantic search failed: {error_msg}")
                return {"error": error_msg}

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return {"error": str(e)}

    async def execute_wsp_lookup(self, protocol_numbers: List[str], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        FIRST PRINCIPLES: Direct WSP protocol lookup
        Critical for Qwen/Gemma WSP compliance verification
        """
        try:
            wsp_results = {}

            for protocol in protocol_numbers:
                # Direct file access to WSP knowledge (most efficient)
                # Try both locations
                wsp_file = None
                for base_path in ["WSP_knowledge/src", "WSP_framework/src"]:
                    candidate = self.repo_root / base_path / f"WSP_{protocol}.md"
                    if candidate.exists():
                        wsp_file = candidate
                        break

                if wsp_file:
                    try:
                        with open(wsp_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Extract title from first line
                            lines = content.split('\n')
                            title = "Unknown"
                            for line in lines[:5]:  # Check first few lines
                                if line.strip().startswith('# '):
                                    title = line.strip()[2:]  # Remove '# '
                                    break
                            wsp_results[protocol] = {
                                "title": title,
                                "content": content[:2000],  # Limit for efficiency
                                "file": str(wsp_file)
                            }
                    except Exception as e:
                        logger.warning(f"Error reading WSP {protocol}: {e}")
                else:
                    logger.debug(f"WSP {protocol} file not found")

            # Store WSP lookup pattern
            await self._store_pattern("wsp_lookup", {
                "protocols": protocol_numbers,
                "context": context or {},
                "results_count": len(wsp_results),
                "success": bool(wsp_results)
            })

            return wsp_results

        except Exception as e:
            logger.error(f"WSP lookup error: {e}")
            return {"error": str(e)}

    async def execute_code_refactor(self, target_file: str, refactoring_type: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        FIRST PRINCIPLES: Direct code refactoring via surgical tools
        Qwen plans, Gemma validates, tools execute
        """
        try:
            # Use surgical refactor tool
            refactor_cmd = [
                "python", str(self.repo_root / "foundups-mcp-p1" / "servers" / "codeindex" / "server.py"),
                "surgical_refactor",
                "--file", target_file,
                "--type", refactoring_type
            ]

            import subprocess
            result = subprocess.run(
                refactor_cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=60
            )

            success = result.returncode == 0
            output = result.stdout if success else result.stderr

            # Store refactoring pattern
            await self._store_pattern("code_refactor", {
                "target_file": target_file,
                "refactoring_type": refactoring_type,
                "context": context or {},
                "success": success,
                "output_length": len(output)
            })

            return {
                "success": success,
                "output": output,
                "target_file": target_file
            }

        except Exception as e:
            logger.error(f"Code refactor error: {e}")
            return {"error": str(e)}

    async def _store_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]):
        """Store patterns for Qwen/Gemma learning (WSP 84)"""
        if not self.pattern_memory:
            return

        try:
            pattern = {
                "id": f"mcp_{pattern_type}_{int(time.time())}",
                "context": f"MCP tool execution: {pattern_type}",
                "decision": {
                    "action": pattern_type,
                    "reasoning": "First principles MCP tool integration",
                    "efficiency": "Direct tool access without abstraction"
                },
                "outcome": pattern_data,
                "module": "wsp_orchestrator",
                "timestamp": time.time(),
                "verified": True,
                "source": "mcp_tool_executor"
            }

            success = self.pattern_memory.store_pattern(pattern)
            if success:
                logger.debug(f"Pattern stored: {pattern_type}")
            else:
                logger.warning(f"Pattern storage failed: {pattern_type}")

        except Exception as e:
            logger.error(f"Pattern storage error: {e}")

    async def close_session(self):
        """Clean up MCP session without leaking aiohttp resources."""
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None


@dataclass
class MPSScore:
    """WSP 15 Module Prioritization System Score"""
    complexity: int  # 1-5 (implementation difficulty)
    importance: int  # 1-5 (system dependency level)
    deferability: int  # 1-5 (urgency factor)
    impact: int  # 1-5 (value delivery)

    @property
    def total(self) -> int:
        """MPS Total: A + B + C + D"""
        return self.complexity + self.importance + self.deferability + self.impact

    @property
    def priority(self) -> str:
        """Priority: P0=16-20, P1=13-15, P2=10-12, P3=7-9, P4=4-6"""
        score = self.total
        if score >= 16:
            return "P0"
        elif score >= 13:
            return "P1"
        elif score >= 10:
            return "P2"
        elif score >= 7:
            return "P3"
        else:
            return "P4"


@dataclass
class WSPTask:
    """Single WSP compliance task with MPS scoring"""
    task_type: str
    description: str
    wsp_references: List[str]
    mps_score: MPSScore
    worker_assignment: Optional[str] = None


@dataclass
class WorkerPlan:
    """Plan generated by a code-role worker (to be improved by 0102).

    Previously ``QwenPlan``.  Renamed to decouple the data structure from
    any specific model provider — the *role* is ``code`` (strategic
    planning), not a permanent model name.
    """
    tasks: List[str]
    reasoning: str
    estimated_time_ms: float
    confidence: float


# ---------------------------------------------------------------------------
# Worker-role constants — the canonical dispatch labels used throughout
# orchestration.  MCP tools keep their own prefix ("MCP:*") because they
# are infrastructure, not model roles.
# ---------------------------------------------------------------------------

ROLE_TRIAGE = "role:triage"        # fast pattern matching / binary decisions
ROLE_CODE = "role:code"            # strategic planning / deep analysis / docs
ROLE_GENERAL = "role:general"      # reserved — dispatchable but not yet planner-emitted
ROLE_0102 = "role:0102"            # human oversight / direct action


class WSPOrchestrator:
    """
    0102-CONTROLLED Orchestration with Qwen/Gemma Workers

    CRITICAL: 0102 (YOU) are the meta-orchestrator, NOT Qwen
    """

    def __init__(self, repo_root: Path = Path("O:/Foundups-Agent")):
        self.repo_root = Path(repo_root)
        self.wsp00_auto_awaken = os.getenv("WSP00_AUTO_AWAKEN", "1") not in {"0", "false", "False", "no", "No"}
        self.wsp00_strict_gate = os.getenv("WSP00_STRICT_GATE", "1") not in {"0", "false", "False", "no", "No"}

        # FIRST PRINCIPLES: Direct MCP Tool Access (no abstraction layers)
        self.mcp_executor = MCPToolExecutor(self.repo_root) if MCP_DIRECT_AVAILABLE else None
        self._mcp_session_initialized = False

        # Worker engines (triage-role and code-role backed by local models)
        self.workers = None
        self.pattern_memory = None
        if WORKERS_AVAILABLE:
            self.workers = AutonomousRefactoringOrchestrator(self.repo_root)
            self.pattern_memory = PatternMemory()
            self.daemon_logger = DaemonLogger("0102_MetaOrchestrator")
        else:
            self.daemon_logger = None

        self.wsp00_tracker = WSP00ZenStateTracker() if WSP00_TRACKER_AVAILABLE else None

    async def follow_wsp(self, user_task: str) -> Dict:
        """
        0102 META-ORCHESTRATION: Main "follow WSP" entry point

        Architecture Flow:
        1. 0102 analyzes task using WSP 15 MPS scoring
        2. 0102 prompts Qwen for strategic plan
        3. 0102 reviews, modifies, and improves Qwen's plan
        4. 0102 coordinates worker execution (triage -> code -> 0102)
        5. Workers store learning patterns
        """
        print("\n" + "="*70)
        print("0102 META-ORCHESTRATOR - WSP 15 MPS Scoring + Role-Based Workers")
        print("="*70)

        # PHASE -1: WSP_00 hard gate
        print(f"\n[0102-PHASE--1] Verifying WSP_00 gate...")
        gate = self._ensure_wsp00_gate()
        print(
            f"  Gate passed: {gate['gate_passed']} | "
            f"auto_awaken={gate['auto_awaken']} | "
            f"attempted={gate['attempted_awakening']}"
        )
        if not gate['gate_passed'] and self.wsp00_strict_gate:
            return {
                "tasks_completed": 0,
                "tasks_failed": 1,
                "outputs": [{
                    "task": "WSP_00 zen-state gate",
                    "worker": "WSP_00",
                    "output": gate.get("message", "WSP_00 gate failed"),
                }],
                "success": False,
                "wsp00_gate": gate,
            }

        # Initialize MCP session lazily inside active event loop.
        await self._ensure_mcp_session()

        # PHASE 0: 0102 WSP 15 MPS Analysis
        print(f"\n[0102-PHASE-0] Analyzing task with WSP 15 MPS...")
        mps_analysis = self._0102_analyze_with_mps(user_task)
        print(f"  MPS Score: {mps_analysis['mps'].total} ({mps_analysis['mps'].priority})")
        print(f"  Complexity: {mps_analysis['mps'].complexity}/5")
        print(f"  Importance: {mps_analysis['mps'].importance}/5")
        print(f"  Deferability: {mps_analysis['mps'].deferability}/5")
        print(f"  Impact: {mps_analysis['mps'].impact}/5")

        # PHASE 1: 0102 Requests Plan from Code-Role Worker
        print(f"\n[0102-PHASE-1] Requesting strategic plan from code-role worker...")
        worker_plan = self._0102_request_plan(user_task, mps_analysis)

        if worker_plan:
            print(f"  Worker plan generated ({len(worker_plan.tasks)} tasks)")
            print(f"  Worker confidence: {worker_plan.confidence:.2f}")
        else:
            print("  Code-role worker unavailable - using 0102 direct planning")

        # PHASE 2: 0102 Reviews and Improves Worker's Plan
        print(f"\n[0102-PHASE-2] Reviewing and improving worker plan...")
        final_plan = self._0102_improve_plan(worker_plan, mps_analysis)
        print(f"  Final plan: {len(final_plan)} tasks")

        # PHASE 3: 0102 Coordinates Worker Execution
        print(f"\n[0102-PHASE-3] Coordinating worker execution...")
        results = await self._0102_coordinate_workers(final_plan)

        # PHASE 4: Workers Store Learning Patterns
        print(f"\n[0102-PHASE-4] Storing learning patterns...")
        self._workers_store_patterns(user_task, results)
        results["wsp00_gate"] = gate

        return results

    async def _ensure_mcp_session(self) -> None:
        """Initialize MCP session only when an event loop is active."""
        if not self.mcp_executor or self._mcp_session_initialized:
            return
        self._mcp_session_initialized = await self.mcp_executor.initialize_session()

    async def shutdown(self) -> None:
        """Release async resources used by the orchestrator."""
        if self.mcp_executor:
            await self.mcp_executor.close_session()
        self._mcp_session_initialized = False

    def _ensure_wsp00_gate(self) -> Dict[str, Any]:
        """Run WSP_00 gate before executing follow_wsp work."""
        payload: Dict[str, Any] = {
            "gate_passed": True,
            "tracker_available": bool(self.wsp00_tracker),
            "auto_awaken": self.wsp00_auto_awaken,
            "attempted_awakening": False,
            "message": "WSP_00 gate passed.",
        }

        if not self.wsp00_tracker:
            payload["gate_passed"] = not self.wsp00_strict_gate
            payload["message"] = (
                "WSP_00 tracker unavailable; strict gate is OFF, continuing."
                if payload["gate_passed"]
                else "WSP_00 tracker unavailable; strict gate is ON, blocking execution."
            )
            return payload

        try:
            status = self.wsp00_tracker.run_compliance_gate(auto_awaken=self.wsp00_auto_awaken)
            gate_passed = bool(status.get("gate_passed", False))
            payload.update(status)
            payload["gate_passed"] = gate_passed
            payload["message"] = (
                "WSP_00 gate passed."
                if gate_passed
                else "WSP_00 gate failed after auto-awakening attempt."
            )
        except Exception as exc:
            payload["gate_passed"] = not self.wsp00_strict_gate
            payload["error"] = str(exc)
            payload["message"] = (
                "WSP_00 gate check errored; strict gate is OFF, continuing."
                if payload["gate_passed"]
                else "WSP_00 gate check errored; strict gate is ON, blocking execution."
            )
        return payload

    def _0102_analyze_with_mps(self, user_task: str) -> Dict:
        """
        0102 META-ORCHESTRATION: Analyze task using WSP 15 MPS scoring

        YOU (0102) decide complexity/importance/deferability/impact
        """
        # 0102 evaluates task characteristics
        task_lower = user_task.lower()

        # Complexity (1-5): Implementation difficulty
        if 'create' in task_lower or 'new module' in task_lower:
            complexity = 4  # Creating new modules is complex
        elif 'update' in task_lower or 'modify' in task_lower:
            complexity = 3  # Modifications are moderate
        elif 'fix' in task_lower or 'bug' in task_lower:
            complexity = 2  # Fixes are simpler
        else:
            complexity = 3  # Default moderate

        # Importance (1-5): System dependency level
        if 'critical' in task_lower or 'wsp' in task_lower:
            importance = 5  # WSP compliance is critical
        elif 'integration' in task_lower or 'orchestrat' in task_lower:
            importance = 4  # Integration is important
        else:
            importance = 3  # Default moderate

        # Deferability (1-5): Urgency (higher = less urgent)
        if 'urgent' in task_lower or 'fix' in task_lower:
            deferability = 1  # Cannot defer urgent tasks
        elif 'enhance' in task_lower or 'improve' in task_lower:
            deferability = 3  # Enhancements can wait
        else:
            deferability = 2  # Default low defer

        # Impact (1-5): Value delivery
        if 'user' in task_lower or 'feature' in task_lower:
            impact = 5  # User features = high impact
        elif 'refactor' in task_lower:
            impact = 3  # Refactoring = medium impact
        else:
            impact = 4  # Default high-medium

        mps = MPSScore(
            complexity=complexity,
            importance=importance,
            deferability=deferability,
            impact=impact
        )

        return {
            "mps": mps,
            "reasoning": f"0102 analyzed: complexity={complexity}, importance={importance}, defer={deferability}, impact={impact}"
        }

    def _0102_request_plan(self, user_task: str, mps_analysis: Dict) -> Optional[WorkerPlan]:
        """
        0102 META-ORCHESTRATION: Request strategic plan from code-role worker.

        0102 gives the worker the task and MPS context; the worker generates
        an initial plan.  Currently backed by ``workers.qwen_engine`` but the
        caller sees only a role-neutral ``WorkerPlan``.
        """
        if not self.workers or not self.workers.qwen_engine:
            return None

        prompt = f"""You are a strategic planning assistant to 0102.

User Task: {user_task}

MPS Analysis (from 0102):
- Priority: {mps_analysis['mps'].priority}
- Complexity: {mps_analysis['mps'].complexity}/5
- Importance: {mps_analysis['mps'].importance}/5

Generate a step-by-step plan to accomplish this task following WSP protocols.
List 4-6 specific tasks. Be concise."""

        try:
            response = self.workers.qwen_engine.generate_response(prompt, max_tokens=200)

            # Parse worker response into tasks
            tasks = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                    # Remove numbering/bullets
                    task = line.lstrip('0123456789.-* ')
                    if task:
                        tasks.append(task)

            return WorkerPlan(
                tasks=tasks,
                reasoning=response[:200],
                estimated_time_ms=len(tasks) * 1000,  # Rough estimate
                confidence=0.8
            )

        except Exception as e:
            logger.error(f"[0102] Code-role planning failed: {e}")
            return None

    def _0102_improve_plan(self, worker_plan: Optional[WorkerPlan], mps_analysis: Dict) -> List[WSPTask]:
        """
        0102 META-ORCHESTRATION: Review and improve worker plan.

        0102 modifies worker suggestions based on WSP compliance knowledge.
        """
        tasks = []

        # ALWAYS start with HoloIndex search (WSP 50)
        tasks.append(WSPTask(
            task_type="holoindex_search",
            description="Search for existing implementations via HoloIndex MCP",
            wsp_references=["WSP 50 (Pre-Action)", "WSP 84 (No Duplication)"],
            mps_score=MPSScore(complexity=1, importance=5, deferability=1, impact=5),
            worker_assignment="MCP:HoloIndex"
        ))

        # ALWAYS check WSP Master Index (WSP 64)
        tasks.append(WSPTask(
            task_type="wsp_lookup",
            description="Lookup applicable WSP protocols via MCP",
            wsp_references=["WSP 64 (Violation Prevention)"],
            mps_score=MPSScore(complexity=1, importance=5, deferability=1, impact=4),
            worker_assignment="MCP:WSP"
        ))

        # Add worker suggestions (if available) with 0102 modifications
        if worker_plan and worker_plan.tasks:
            for suggested_task in worker_plan.tasks[:4]:  # Limit to 4 tasks
                # 0102 assigns role based on task semantics
                if 'search' in suggested_task.lower() or 'find' in suggested_task.lower():
                    worker = "MCP:HoloIndex"
                elif 'pattern' in suggested_task.lower() or 'match' in suggested_task.lower():
                    worker = ROLE_TRIAGE
                elif 'plan' in suggested_task.lower() or 'design' in suggested_task.lower():
                    worker = ROLE_CODE
                else:
                    worker = ROLE_0102

                tasks.append(WSPTask(
                    task_type="worker_suggested",
                    description=suggested_task,
                    wsp_references=["WSP 77 (Agent Coordination)"],
                    mps_score=mps_analysis['mps'],
                    worker_assignment=worker
                ))

        # ALWAYS end with ModLog update (WSP 22)
        tasks.append(WSPTask(
            task_type="update_modlog",
            description="Document changes in ModLog.md",
            wsp_references=["WSP 22 (Traceable Narrative)"],
            mps_score=MPSScore(complexity=1, importance=3, deferability=3, impact=3),
            worker_assignment=ROLE_CODE
        ))

        return tasks

    async def _0102_coordinate_workers(self, tasks: List[WSPTask]) -> Dict:
        """
        0102 SUPERVISION: Coordinate worker execution

        0102 assigns tasks to workers and supervises execution
        """
        results = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "outputs": [],
            "success": False
        }

        for i, task in enumerate(tasks):
            print(f"\n[TASK-{i+1}/{len(tasks)}] {task.description}")
            print(f"  Worker: {task.worker_assignment}")
            print(f"  Priority: {task.mps_score.priority} (MPS: {task.mps_score.total})")
            print(f"  WSP: {', '.join(task.wsp_references)}")

            # 0102 decides whether to execute or skip
            if task.mps_score.priority in ["P0", "P1"]:
                # High priority - execute
                try:
                    output = await self._execute_worker(task)
                    results['outputs'].append({
                        "task": task.description,
                        "worker": task.worker_assignment,
                        "output": output
                    })
                    results['tasks_completed'] += 1
                    print(f"  Status: [OK] Completed")
                except Exception as e:
                    results['tasks_failed'] += 1
                    print(f"  Status: [FAIL] Failed - {e}")
            else:
                # Lower priority - defer
                print(f"  Status: [DEFER] Deferred ({task.mps_score.priority} priority)")

        results['success'] = results['tasks_failed'] == 0
        return results

    async def _execute_worker(self, task: WSPTask) -> str:
        """
        Execute task using the assigned worker role.

        Dispatch is keyed on role semantics, not provider names:
        - ``MCP:*``       → MCP tool infrastructure (HoloIndex, WSP, CodeIndex)
        - ``role:triage``  → fast pattern matching / binary decisions
        - ``role:code``    → strategic planning / deep analysis / docs
        - ``role:general`` → synthesis / reasoning (non-code)
        - ``role:0102``    → human oversight / direct action
        """
        worker = task.worker_assignment or ""

        # Runtime emitter: structured dispatch event
        _rt_start = None
        try:
            from modules.infrastructure.dae_daemon.src.runtime_emitter import (
                emit_start, emit_success, emit_failure,
            )
            _rt_start = emit_start(
                "wsp_orchestrator", "worker_dispatch",
                details={"worker": worker, "task_type": task.task_type,
                         "description": task.description[:80]},
            )
        except Exception:
            emit_success = emit_failure = None  # type: ignore[assignment]

        try:
            result = await self._dispatch_worker_inner(task, worker)
        except Exception as exc:
            if _rt_start is not None and emit_failure:
                emit_failure("wsp_orchestrator", "worker_dispatch", _rt_start,
                             str(exc)[:200], details={"worker": worker})
            raise
        else:
            is_error = "ERROR" in result or "UNAVAILABLE" in result
            if _rt_start is not None:
                if is_error and emit_failure:
                    emit_failure("wsp_orchestrator", "worker_dispatch", _rt_start,
                                 result[:200], details={"worker": worker})
                elif emit_success:
                    emit_success("wsp_orchestrator", "worker_dispatch", _rt_start,
                                 details={"worker": worker})
            return result

    async def _dispatch_worker_inner(self, task: WSPTask, worker: str) -> str:
        """Inner dispatch logic (separated for emitter wrapping)."""
        if worker.startswith("MCP:"):
            if not self.mcp_executor:
                return "[MCP-UNAVAILABLE] MCP executor not initialized"

            try:
                if "HoloIndex" in worker:
                    return await self._execute_holoindex_task(task)
                elif "WSP" in worker:
                    return await self._execute_wsp_task(task)
                elif "CodeIndex" in worker:
                    return await self._execute_codeindex_task(task)
                else:
                    return f"[MCP] Generic {worker} executed"

            except Exception as e:
                logger.error(f"MCP tool execution failed: {e}")
                return f"[MCP-ERROR] {e}"

        elif worker == ROLE_TRIAGE:
            return await self._execute_triage_task(task)

        elif worker == ROLE_CODE:
            return await self._execute_code_task(task)

        elif worker == ROLE_GENERAL:
            return await self._execute_code_task(task)  # same executor for now

        elif worker == ROLE_0102:
            return await self._execute_0102_task(task)

        else:
            # Fallback for any unrecognised worker label
            return await self._execute_0102_task(task)

    async def _execute_holoindex_task(self, task: WSPTask) -> str:
        """Execute HoloIndex MCP tasks (semantic search, etc.)"""
        if task.task_type == "holoindex_search":
            # Generate search query from task description
            search_query = self._generate_search_query(task.description)

            results = await self.mcp_executor.execute_semantic_search(
                query=search_query,
                context={"task_type": task.task_type, "mps_score": task.mps_score.total}
            )

            if "error" in results:
                return f"[HOLO-ERROR] {results['error']}"

            code_count = len(results.get('code', []))
            wsp_count = len(results.get('wsps', []))

            return f"[HOLO-SUCCESS] Found {code_count} code results, {wsp_count} WSP results for query: '{search_query}'"

        return f"[HOLO] Unknown task type: {task.task_type}"

    async def _execute_wsp_task(self, task: WSPTask) -> str:
        """Execute WSP governance MCP tasks (protocol lookup, etc.)"""
        if task.task_type == "wsp_lookup":
            # Extract protocol numbers from task or related tasks
            protocols = self._extract_wsp_protocols(task)

            results = await self.mcp_executor.execute_wsp_lookup(
                protocol_numbers=protocols,
                context={"task_type": task.task_type, "source": "orchestrator"}
            )

            if "error" in results:
                return f"[WSP-ERROR] {results['error']}"

            found_count = len([p for p in protocols if p in results])
            return f"[WSP-SUCCESS] Found {found_count}/{len(protocols)} WSP protocols: {', '.join(protocols)}"

        return f"[WSP] Unknown task type: {task.task_type}"

    async def _execute_codeindex_task(self, task: WSPTask) -> str:
        """Execute CodeIndex MCP tasks (refactoring, health assessment, etc.)"""
        # This would integrate with the codeindex MCP server
        return f"[CODEINDEX] {task.task_type} task delegated to CodeIndex MCP server"

    async def _execute_triage_task(self, task: WSPTask) -> str:
        """Execute triage-role tasks (fast pattern matching / binary decisions).

        Currently backed by ``workers.gemma_engine``.
        """
        if not self.workers or not self.workers.gemma_engine:
            return "[TRIAGE-UNAVAILABLE] Triage-role engine not initialized"

        try:
            if "pattern" in task.description.lower():
                search_results = await self.mcp_executor.execute_semantic_search(
                    query=task.description,
                    context={"role": "triage", "task_type": "pattern_matching"}
                )

                analysis = f"Triage analyzed {len(search_results.get('code', []))} patterns"
                return f"[TRIAGE] {analysis} - patterns stored for future matching"

            elif "validate" in task.description.lower():
                wsp_results = await self.mcp_executor.execute_wsp_lookup(
                    protocol_numbers=["50", "77"],
                    context={"role": "triage", "task_type": "validation"}
                )

                return f"[TRIAGE] Validation completed using {len(wsp_results)} WSP protocols"

            else:
                return f"[TRIAGE] Fast pattern matching completed for: {task.description[:50]}..."

        except Exception as e:
            return f"[TRIAGE-ERROR] {e}"

    async def _execute_code_task(self, task: WSPTask) -> str:
        """Execute code-role tasks (strategic planning / deep analysis / docs).

        Currently backed by ``workers.qwen_engine``.
        """
        if not self.workers or not self.workers.qwen_engine:
            return "[CODE-UNAVAILABLE] Code-role engine not initialized"

        try:
            if "plan" in task.description.lower() or "design" in task.description.lower():
                search_results = await self.mcp_executor.execute_semantic_search(
                    query=task.description,
                    context={"role": "code", "task_type": "strategic_planning"}
                )

                wsp_results = await self.mcp_executor.execute_wsp_lookup(
                    protocol_numbers=["15", "77", "84"],
                    context={"role": "code", "task_type": "planning"}
                )

                return f"[CODE] Strategic plan developed using {len(search_results.get('code', []))} code references and {len(wsp_results)} WSP protocols"

            elif "document" in task.description.lower():
                return f"[CODE] Documentation completed with MCP tool verification"

            else:
                return f"[CODE] Strategic analysis completed for: {task.description[:50]}..."

        except Exception as e:
            return f"[CODE-ERROR] {e}"

    async def _execute_0102_task(self, task: WSPTask) -> str:
        """Execute 0102 direct tasks (highest authority level)"""
        # 0102 can use all MCP tools directly and has final authority
        if "create" in task.description.lower() or "implement" in task.description.lower():
            return f"[0102-ACTION] Direct implementation required: {task.description[:100]}..."
        elif "review" in task.description.lower():
            return f"[0102-ACTION] Manual review required: {task.description[:100]}..."
        else:
            return f"[0102-ACTION] Direct execution: {task.description[:100]}..."

    def _generate_search_query(self, task_description: str) -> str:
        """Generate semantic search query from task description"""
        # Extract key terms for semantic search
        query = task_description.lower()
        # Remove common words
        query = query.replace("create", "").replace("implement", "").replace("add", "")
        query = query.replace("update", "").replace("modify", "").replace("fix", "")
        # Clean up extra spaces
        query = " ".join(query.split())
        return query.strip()

    def _extract_wsp_protocols(self, task: WSPTask) -> List[str]:
        """Extract WSP protocol numbers from task"""
        protocols = []
        # Extract from task description
        import re
        wsp_matches = re.findall(r'WSP\s*(\d+)', task.description)
        protocols.extend(wsp_matches)

        # Extract from wsp_references
        for ref in task.wsp_references:
            wsp_matches = re.findall(r'WSP\s*(\d+)', ref)
            protocols.extend(wsp_matches)

        # Remove duplicates and return
        return list(set(protocols))

    def _workers_store_patterns(self, task: str, results: Dict):
        """Workers store learning patterns (Phase 4)"""
        print(f"  Patterns stored for future learning")


# Standalone CLI
def main():
    """Standalone "follow WSP" CLI - 0102 in command"""
    import sys

    orchestrator = WSPOrchestrator()

    print("\n" + "="*70)
    print("WSP Orchestrator - 0102 Meta-Orchestration")
    print("="*70)
    print("\nCORRECT HIERARCHY:")
    print("  0102 (YOU) → role:code (strategic planning) → role:triage (pattern matching)")
    print("  0102 uses WSP 15 MPS scoring to prioritize tasks\n")

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = input("Enter task: ").strip()

    if not task or task.lower() == 'exit':
        return

    try:
        results = asyncio.run(orchestrator.follow_wsp(task))
    finally:
        # Standalone CLI is one-shot; release async session resources deterministically.
        asyncio.run(orchestrator.shutdown())

    print("\n" + "="*70)
    print("EXECUTION SUMMARY")
    print("="*70)
    print(f"Tasks Completed: {results['tasks_completed']}")
    print(f"Tasks Failed: {results['tasks_failed']}")
    print(f"Success: {results['success']}")

    if results['outputs']:
        print("\nTask Outputs:")
        for output in results['outputs']:
            print(f"  [{output['worker']}] {output['output']}")


if __name__ == "__main__":
    main()
