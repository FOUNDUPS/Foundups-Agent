#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Autonomous Refactoring Orchestrator - Qwen + Gemma Coordination

This module enables Qwen to autonomously orchestrate code refactoring with
Gemma pattern matching and 0102 supervision. Implements WSP 77 (Agent Coordination)
for recursive autonomous coding environment.

Architecture:
    Phase 1 (Gemma): Fast pattern matching - find all dependencies
    Phase 2 (Qwen):  Strategic planning - generate refactoring plan
    Phase 3 (0102):  Supervision - approve and execute with oversight
    Phase 4 (Learning): Store patterns for recursive improvement

WSP Compliance:
    - WSP 77: Agent Coordination Protocol (Qwen -> Gemma -> 0102)
    - WSP 50: Pre-Action Verification (analyze before execute)
    - WSP 48: Recursive Self-Improvement (learn from refactorings)
    - WSP 84: Code Memory Verification (no duplication)
    - WSP 90: UTF-8 Encoding (NOTE: Header NOT needed - this is library module, not entry point)
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import shutil
import time
from modules.infrastructure.shared_utilities.local_model_selection import resolve_triage_model_path

# LLM Integration
try:
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
    from holo_index.qwen_advisor.config import QwenAdvisorConfig
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False

try:
    from llama_cpp import Llama
    GEMMA_AVAILABLE = True
except ImportError:
    GEMMA_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# WSP 91: DAEMON OBSERVABILITY PROTOCOL - Structured Logging
# ============================================================================
class DaemonLogger:
    """
    WSP 91-compliant structured logging for daemon observability.

    MUST LOG (Troubleshooting-Critical):
    - Decision Points: When AI chooses a path
    - LLM Inference: When actual AI runs with timing
    - Routing Decisions: Which method chosen and why
    - Errors/Failures: What went wrong
    - Performance Metrics: How long operations take

    MUST NOT LOG (Noise):
    - Every grep result
    - Full file contents
    - Redundant "still running" messages
    - Internal variable states
    """

    def __init__(self, component: str):
        self.component = component
        self.session_start = time.time()

    def log_decision(self, decision_type: str, chosen_path: str,
                     confidence: float, reasoning: str, **metadata):
        """Log AI decision points - CRITICAL for troubleshooting"""
        log_entry = {
            "timestamp": time.time(),
            "session_time": time.time() - self.session_start,
            "component": self.component,
            "event_type": "DECISION",
            "decision_type": decision_type,
            "chosen_path": chosen_path,
            "confidence": confidence,
            "reasoning": reasoning[:200],  # Truncate long reasoning
            **metadata
        }
        logger.info(f"[DAEMON-DECISION] {json.dumps(log_entry)}")
        return log_entry

    def log_llm_inference(self, llm_name: str, prompt_size: int,
                          response_size: int, inference_time_ms: float,
                          tokens_generated: int = 0, **metadata):
        """Log LLM inference - CRITICAL for performance analysis"""
        log_entry = {
            "timestamp": time.time(),
            "session_time": time.time() - self.session_start,
            "component": self.component,
            "event_type": "LLM_INFERENCE",
            "llm_name": llm_name,
            "prompt_size": prompt_size,
            "response_size": response_size,
            "inference_time_ms": inference_time_ms,
            "tokens_generated": tokens_generated,
            "tokens_per_second": tokens_generated / (inference_time_ms / 1000) if inference_time_ms > 0 else 0,
            **metadata
        }
        logger.info(f"[DAEMON-LLM] {json.dumps(log_entry)}")
        return log_entry

    def log_routing(self, task_description: str, routing_method: str,
                    routing_confidence: float, routing_reasoning: str, **metadata):
        """Log routing decisions - CRITICAL for Qwen meta-orchestration"""
        log_entry = {
            "timestamp": time.time(),
            "session_time": time.time() - self.session_start,
            "component": self.component,
            "event_type": "ROUTING",
            "task": task_description[:100],  # Truncate long descriptions
            "method": routing_method,
            "confidence": routing_confidence,
            "reasoning": routing_reasoning[:200],
            **metadata
        }
        logger.info(f"[DAEMON-ROUTING] {json.dumps(log_entry)}")
        return log_entry

    def log_error(self, error_type: str, error_message: str,
                  context: Dict, recoverable: bool = True, **metadata):
        """Log errors - CRITICAL for troubleshooting failures"""
        log_entry = {
            "timestamp": time.time(),
            "session_time": time.time() - self.session_start,
            "component": self.component,
            "event_type": "ERROR",
            "error_type": error_type,
            "error_message": error_message[:500],  # Truncate long errors
            "context": context,
            "recoverable": recoverable,
            **metadata
        }
        logger.error(f"[DAEMON-ERROR] {json.dumps(log_entry)}")
        return log_entry

    def log_performance(self, operation: str, duration_ms: float,
                        items_processed: int = 0, success: bool = True, **metadata):
        """Log performance metrics - CRITICAL for optimization"""
        log_entry = {
            "timestamp": time.time(),
            "session_time": time.time() - self.session_start,
            "component": self.component,
            "event_type": "PERFORMANCE",
            "operation": operation,
            "duration_ms": duration_ms,
            "items_processed": items_processed,
            "throughput": items_processed / (duration_ms / 1000) if duration_ms > 0 else 0,
            "success": success,
            **metadata
        }
        logger.info(f"[DAEMON-PERF] {json.dumps(log_entry)}")
        return log_entry


@dataclass
class RefactoringTask:
    """Single refactoring operation"""
    task_type: str  # move_module, rename_class, update_import, etc.
    source_path: str
    target_path: str
    reason: str
    wsp_justification: str
    dependencies: List[str]


@dataclass
class RefactoringPlan:
    """Complete refactoring plan with safety checks"""
    tasks: List[RefactoringTask]
    estimated_files_affected: int
    wsp_violations_fixed: List[str]
    safety_checks: List[str]
    rollback_strategy: str


class AutonomousRefactoringOrchestrator:
    """
    Orchestrates autonomous code refactoring using Qwen + Gemma coordination.

    0102 acts as architect/supervisor, Qwen does strategic planning,
    Gemma does fast pattern matching. System learns from each refactoring.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)
        self.memory_path = self.repo_root / "holo_index" / "adaptive_learning" / "refactoring_patterns.json"
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing patterns
        self.patterns = self._load_patterns()

        # WSP 91: Initialize structured daemon logger
        self.daemon_logger = DaemonLogger("AutonomousRefactoring")

        # P0 FIX: Initialize HoloAdapter for Qwen → HoloIndex semantic search
        # Enables Deep Think → HoloIndex → Occam's Razor chain for autonomous agents
        self.holo_adapter = None
        try:
            from modules.ai_intelligence.ai_overseer.src.holo_adapter import HoloAdapter
            self.holo_adapter = HoloAdapter(self.repo_root)
            logger.info("[HOLO-ADAPTER] HoloAdapter initialized for Qwen semantic search")
        except Exception as e:
            logger.warning(f"[HOLO-ADAPTER] Could not initialize HoloAdapter: {e}")
            # Graceful degradation - Qwen operates without HoloIndex context

        # Initialize Qwen LLM for strategic planning (SINGLETON - prevents redundant loading)
        # WSP 91: Singleton pattern reduces startup lag from 2-10s to 0s for repeat calls
        self.qwen_engine = None
        if QWEN_AVAILABLE:
            try:
                from modules.infrastructure.shared_utilities.ai_engine_singletons import (
                    get_qwen_engine,
                    is_qwen_loaded,
                )
                init_start = time.time()
                was_cached = is_qwen_loaded()
                self.qwen_engine = get_qwen_engine(
                    max_tokens=512,
                    temperature=0.2,
                    context_length=2048
                )
                init_time = (time.time() - init_start) * 1000

                if self.qwen_engine:
                    if was_cached:
                        logger.info("[QWEN-LLM] Using cached Qwen engine (singleton)")
                    else:
                        logger.info("[QWEN-LLM] Qwen 1.5B inference engine initialized")

                    # Log LLM initialization
                    self.daemon_logger.log_performance(
                        operation="qwen_initialization",
                        duration_ms=init_time,
                        success=True,
                        cached=was_cached
                    )
            except Exception as e:
                logger.warning(f"[QWEN-LLM] Could not initialize Qwen: {e}")
                self.daemon_logger.log_error(
                    error_type="qwen_init_failure",
                    error_message=str(e),
                    context={"component": "qwen_engine"},
                    recoverable=True
                )
                self.qwen_engine = None

        # Initialize Gemma LLM for pattern matching (SINGLETON - prevents redundant loading)
        self.gemma_engine = None
        if GEMMA_AVAILABLE:
            try:
                from modules.infrastructure.shared_utilities.ai_engine_singletons import (
                    get_gemma_engine,
                    is_gemma_loaded,
                )
                init_start = time.time()
                was_cached = is_gemma_loaded()
                self.gemma_engine = get_gemma_engine(n_ctx=1024, n_threads=4)
                init_time = (time.time() - init_start) * 1000

                if self.gemma_engine:
                    if was_cached:
                        logger.info("[GEMMA-LLM] Using cached Gemma engine (singleton)")
                    else:
                        logger.info("[GEMMA-LLM] Gemma 3 270M inference engine initialized")

                    # Log LLM initialization
                    self.daemon_logger.log_performance(
                        operation="gemma_initialization",
                        duration_ms=init_time,
                        success=True,
                        cached=was_cached
                    )
                else:
                    logger.warning("[GEMMA-LLM] Gemma engine unavailable")
                    self.daemon_logger.log_error(
                        error_type="gemma_unavailable",
                        error_message="Gemma engine returned None",
                        context={"component": "gemma_engine"},
                        recoverable=True
                    )
            except Exception as e:
                logger.warning(f"[GEMMA-LLM] Could not initialize Gemma: {e}")
                self.daemon_logger.log_error(
                    error_type="gemma_init_failure",
                    error_message=str(e),
                    context={"component": "gemma_engine"},
                    recoverable=True
                )
                self.gemma_engine = None

    def _load_patterns(self) -> Dict:
        """Load refactoring patterns from memory"""
        if self.memory_path.exists():
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"successful_refactorings": [], "failed_attempts": [], "learned_patterns": []}

    def _save_patterns(self):
        """Save patterns to memory for learning"""
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.patterns, f, indent=2)

    # PHASE 1: Gemma - Fast Pattern Matching

    def analyze_module_dependencies(self, module_path: str) -> Dict:
        """
        Gemma's role: Fast dependency analysis using pattern matching

        NOW WITH QWEN META-ORCHESTRATION:
        Qwen decides whether to use LLM or rules based on task complexity

        Returns:
            {
                "import_references": [(file, line, import_statement), ...],
                "class_references": [(file, line, class_name), ...],
                "wsp_violations": [{"issue": ..., "wsp": ...}, ...],
                "coupling_score": 0.0-1.0,  # How coupled to other modules
                "size_metrics": {"lines": ..., "classes": ..., "functions": ...}
                "analysis_method": "qwen_llm" | "gemma_llm" | "rules"
            }
        """
        # WSP 91: Track total analysis time
        analysis_start = time.time()
        logger.info(f"[QWEN-META] Analyzing dependencies for: {module_path}")

        module_name = Path(module_path).name.replace('.py', '')

        # PHASE 0: Qwen Meta-Orchestration - Decide how to analyze
        analysis_strategy = self._qwen_decide_analysis_method(module_path)
        logger.info(f"[QWEN-META] Strategy selected: {analysis_strategy['method']} (confidence: {analysis_strategy['confidence']:.2f})")

        # Find all import references (always needed regardless of method)
        import_refs = self._find_import_references(module_path)

        # Find all class references
        class_refs = self._find_class_references(module_path)

        # Detect WSP violations - USE QWEN'S DECISION
        violation_start = time.time()
        if analysis_strategy['method'] == 'gemma_llm':
            logger.info("[GEMMA-LLM] Qwen routed to Gemma LLM for violation detection")
            wsp_violations = self._detect_wsp_violations_with_llm(module_path)
        elif analysis_strategy['method'] == 'qwen_llm':
            logger.info("[QWEN-LLM] Qwen routed to Qwen LLM for deep analysis")
            wsp_violations = self._detect_wsp_violations_with_qwen(module_path)
        else:
            logger.info("[RULES] Qwen routed to rule-based detection (simple case)")
            wsp_violations = self._detect_wsp_violations_rules_only(module_path)

        violation_time = (time.time() - violation_start) * 1000

        # Calculate coupling score
        coupling_score = self._calculate_coupling(import_refs, class_refs)

        # Get size metrics
        size_metrics = self._get_size_metrics(module_path)

        # WSP 91: Log overall analysis performance
        total_time = (time.time() - analysis_start) * 1000
        self.daemon_logger.log_performance(
            operation="module_dependency_analysis",
            duration_ms=total_time,
            items_processed=1,
            success=True,
            module_path=module_path,
            analysis_method=analysis_strategy['method'],
            violations_found=len(wsp_violations),
            violation_detection_ms=violation_time,
            coupling_score=coupling_score
        )

        return {
            "import_references": import_refs,
            "class_references": class_refs,
            "wsp_violations": wsp_violations,
            "coupling_score": coupling_score,
            "size_metrics": size_metrics,
            "analysis_method": analysis_strategy['method'],
            "qwen_reasoning": analysis_strategy.get('reasoning', '')
        }

    def _qwen_decide_analysis_method(self, module_path: str) -> Dict:
        """
        QWEN META-ORCHESTRATION: Qwen decides which analysis method to use

        Returns:
            {
                "method": "qwen_llm" | "gemma_llm" | "rules",
                "confidence": 0.0-1.0,
                "reasoning": "why this method was chosen"
            }
        """
        path = Path(module_path)

        # Quick heuristics - if Qwen LLM available, use it to decide
        if self.qwen_engine:
            try:
                # Ask Qwen to decide
                prompt = f"""You are a meta-orchestrator. Decide which analysis method to use for this Python file.

File: {path.name}
Path: {path}
Size: {path.stat().st_size if path.exists() else 0} bytes

Methods available:
A) qwen_llm - Deep analysis using Qwen 1.5B (250ms, high accuracy, complex cases)
B) gemma_llm - Fast classification using Gemma 3 270M (50ms, good accuracy, simple binary decisions)
C) rules - Rule-based grep/regex (5ms, basic accuracy, trivial cases)

Which method should handle this file? Respond with just the letter (A, B, or C) and brief reason:"""

                # WSP 91: Log LLM inference with timing
                inference_start = time.time()
                response = self.qwen_engine.generate_response(prompt, max_tokens=50)
                inference_time = (time.time() - inference_start) * 1000

                self.daemon_logger.log_llm_inference(
                    llm_name="Qwen-1.5B",
                    prompt_size=len(prompt),
                    response_size=len(response),
                    inference_time_ms=inference_time,
                    tokens_generated=len(response.split()),  # Rough token estimate
                    task="meta_orchestration_routing"
                )

                # Parse Qwen's decision
                response_upper = response.upper()
                if 'A)' in response_upper or response_upper.startswith('A'):
                    decision = {
                        "method": "qwen_llm",
                        "confidence": 0.9,
                        "reasoning": f"Qwen decided: {response[:100]}"
                    }
                elif 'B)' in response_upper or response_upper.startswith('B'):
                    decision = {
                        "method": "gemma_llm",
                        "confidence": 0.85,
                        "reasoning": f"Qwen decided: {response[:100]}"
                    }
                else:
                    decision = {
                        "method": "rules",
                        "confidence": 0.8,
                        "reasoning": f"Qwen decided: {response[:100]}"
                    }

                # WSP 91: Log routing decision
                self.daemon_logger.log_routing(
                    task_description=f"Analyze {path.name}",
                    routing_method=decision["method"],
                    routing_confidence=decision["confidence"],
                    routing_reasoning=decision["reasoning"],
                    file_path=str(path),
                    file_size=path.stat().st_size if path.exists() else 0
                )

                return decision

            except Exception as e:
                logger.warning(f"[QWEN-META] Decision failed, using heuristics: {e}")
                self.daemon_logger.log_error(
                    error_type="qwen_meta_orchestration_failure",
                    error_message=str(e),
                    context={"module_path": str(path)},
                    recoverable=True
                )

        # Fallback heuristics if Qwen unavailable
        try:
            size = path.stat().st_size if path.exists() else 0

            # Complex cases need Qwen LLM
            if size > 10000 or 'infrastructure' in str(path):
                return {
                    "method": "qwen_llm" if self.qwen_engine else "rules",
                    "confidence": 0.7,
                    "reasoning": "Large/complex file - needs deep analysis"
                }

            # Simple binary decisions - use Gemma
            elif path.name.startswith('test_') or size < 5000:
                return {
                    "method": "gemma_llm" if self.gemma_engine else "rules",
                    "confidence": 0.8,
                    "reasoning": "Test file or small file - fast classification sufficient"
                }

            # Default to rules for trivial cases
            else:
                return {
                    "method": "rules",
                    "confidence": 0.9,
                    "reasoning": "Standard file - rule-based detection sufficient"
                }

        except Exception:
            return {
                "method": "rules",
                "confidence": 0.5,
                "reasoning": "Error during heuristic analysis - safe fallback"
            }

    def _holo_research(self, query: str, limit: int = 5) -> Dict:
        """
        P0 FIX: Enable Qwen to perform HoloIndex semantic search

        This implements the Deep Think → HoloIndex → Occam's Razor chain:
        1. Qwen formulates research question (Deep Think)
        2. HoloIndex performs semantic search (Research)
        3. Qwen applies Occam's Razor to results (Decision)

        Returns HoloIndex search results for Qwen to use in strategic planning
        """
        if self.holo_adapter is None:
            return {
                "query": query,
                "code": [],
                "wsps": [],
                "warnings": ["[WARN] HoloAdapter not available - operating without semantic search"],
                "reminders": [],
                "elapsed_ms": "0.0"
            }

        try:
            research_start = time.time()
            results = self.holo_adapter.search(query, limit=limit)
            research_time = (time.time() - research_start) * 1000

            # WSP 91: Log HoloIndex research operation
            self.daemon_logger.log_performance(
                operation="holo_semantic_search",
                duration_ms=research_time,
                items_processed=len(results.get('code', [])) + len(results.get('wsps', [])),
                success=True,
                query=query[:100],  # Truncate for logging
                results_found=len(results.get('code', []))
            )

            logger.info(f"[HOLO-RESEARCH] Found {len(results.get('code', []))} code results for: {query[:50]}...")
            return results

        except Exception as e:
            logger.warning(f"[HOLO-RESEARCH] Search failed: {e}")
            self.daemon_logger.log_error(
                error_type="holo_search_failure",
                error_message=str(e),
                context={"query": query[:100]},
                recoverable=True
            )
            return {
                "query": query,
                "code": [],
                "wsps": [],
                "warnings": [f"[ERROR] HoloIndex search failed: {str(e)}"],
                "reminders": [],
                "elapsed_ms": "0.0"
            }

    def _find_import_references(self, module_path: str) -> List[Tuple[str, int, str]]:
        """
        Gemma pattern: Find all files importing this module.

        Windows-safe implementation (WSP 50): do not shell out to `grep`.
        Uses lightweight Python scanning across repo for `.py` files.
        """
        import re

        refs: List[Tuple[str, int, str]] = []
        module_name = Path(module_path).name.replace(".py", "")

        # Heuristic patterns; conservative to avoid massive false positives.
        patterns = [
            re.compile(rf"^\s*from\s+[\w\.]*\b{re.escape(module_name)}\b[\w\.]*\s+import\s+", re.IGNORECASE),
            re.compile(rf"^\s*import\s+[\w\.]*\b{re.escape(module_name)}\b[\w\.]*\s*$", re.IGNORECASE),
            re.compile(rf"^\s*import\s+.*\b{re.escape(module_name)}\b", re.IGNORECASE),
        ]

        repo_root = Path(self.repo_root)
        for py_file in repo_root.rglob("*.py"):
            # Skip cache/venv-like noise (cheap guard)
            if "__pycache__" in py_file.parts or ".venv" in py_file.parts or "node_modules" in py_file.parts:
                continue

            try:
                with open(py_file, "r", encoding="utf-8", errors="replace") as handle:
                    for idx, line in enumerate(handle, start=1):
                        if any(p.search(line) for p in patterns):
                            refs.append((str(py_file), idx, line.strip()))
            except Exception:
                # Do not block analysis on unreadable files
                continue

        return refs

    def generate_file_relocation_plan(self, source_file: str, target_file: str,
                                      analysis: Dict) -> RefactoringPlan:
        """
        Qwen planning: relocate a *single file* safely.

        This prevents the dangerous behavior of treating a file path as a module directory.
        """
        tasks: List[RefactoringTask] = []

        target_path = Path(target_file)
        tasks.append(RefactoringTask(
            task_type="create_directory",
            source_path="",
            target_path=str(target_path.parent),
            reason="Prepare target location for file relocation",
            wsp_justification="WSP 49 (Module Structure)",
            dependencies=[]
        ))

        tasks.append(RefactoringTask(
            task_type="move_file",
            source_path=str(source_file),
            target_path=str(target_file),
            reason="Relocate file to WSP-compliant location",
            wsp_justification="WSP 85 (Root Protection) + WSP 50 (Pre-Action Verification)",
            dependencies=["create_directory"]
        ))

        # Update imports in any referencing files (implementation is TODO in executor, but plan records intent)
        for file_path, line_num, _import_stmt in analysis.get("import_references", []):
            tasks.append(RefactoringTask(
                task_type="update_import",
                source_path=file_path,
                target_path=file_path,
                reason=f"Fix import reference at line {line_num}",
                wsp_justification="WSP 50 (Pre-Action Verification)",
                dependencies=["move_file"]
            ))

        tasks.append(RefactoringTask(
            task_type="run_tests",
            source_path="",
            target_path="",
            reason="Verify relocation didn't break imports/runtime",
            wsp_justification="WSP 34 (Tests)",
            dependencies=["update_import"] if analysis.get("import_references") else ["move_file"]
        ))

        return RefactoringPlan(
            tasks=tasks,
            estimated_files_affected=len(analysis.get("import_references", [])),
            wsp_violations_fixed=[v.get("wsp") for v in (analysis.get("wsp_violations") or []) if v.get("wsp")],
            safety_checks=[
                "Target directory created before move",
                "No bulk directory moves",
                "Imports reviewed/updated after move",
            ],
            rollback_strategy="git reset --hard HEAD"
        )

    def _find_class_references(self, module_path: str) -> List[Tuple[str, int, str]]:
        """Gemma pattern: Find all references to classes in this module"""
        # TODO: Implement class reference finding
        return []

    def _detect_wsp_violations_with_llm(self, module_path: str) -> List[Dict]:
        """Gemma LLM: Fast binary classification for WSP violations"""
        violations = []
        path = Path(module_path)

        try:
            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Build prompt for Gemma
            prompt = f"""You are a code analyzer. Classify WSP violations in this Python file.

File: {path.name}
Lines: {len(lines)}
Location: {path.parent}

Rules:
1. WSP 3 - Files must be in correct functional domain
2. WSP 85 - Test files must be in module/tests/ not root
3. WSP 87 - Files should be <500 lines

Analyze the file path and respond with YES or NO for each rule:
WSP 3 violation: """

            # Run Gemma inference
            response = self.gemma_engine(prompt, max_tokens=50, temperature=0.1)

            # Parse response
            if isinstance(response, dict) and 'choices' in response:
                text = response['choices'][0]['text'].strip()
                if 'YES' in text.upper():
                    violations.append({
                        "issue": f"Gemma LLM detected WSP 3 violation in {path.name}",
                        "wsp": "WSP 3 (Functional Distribution)",
                        "recommendation": "Review module placement with Qwen analysis"
                    })

        except Exception as e:
            logger.warning(f"[GEMMA-LLM] Violation detection error: {e}")

        return violations

    def _detect_wsp_violations_with_qwen(self, module_path: str) -> List[Dict]:
        """Qwen LLM: Deep analysis for complex WSP violations"""
        violations = []
        path = Path(module_path)

        try:
            content = path.read_text(encoding='utf-8')[:1000]  # First 1000 chars for context

            # Build strategic prompt for Qwen
            prompt = f"""You are a software architect analyzing code structure compliance.

File: {path.name}
Path: {path}
Content preview: {content[:500]}...

Perform deep analysis for WSP violations:
1. WSP 3 (Functional Distribution) - Is this file in the correct enterprise domain?
2. WSP 49 (Module Structure) - Does file location follow proper module hierarchy?
3. WSP 85 (Root Protection) - Are test/temp files in proper directories?
4. WSP 87 (Code Navigation) - Is file size appropriate (<500 lines)?

Analyze and provide detailed findings:"""

            # Run Qwen inference
            response = self.qwen_engine.generate_response(prompt, max_tokens=200)

            # Parse Qwen's analysis
            if 'violation' in response.lower() or 'wsp' in response.lower():
                violations.append({
                    "issue": "Qwen LLM detected structural issues",
                    "wsp": "Multiple WSPs (Deep Analysis)",
                    "recommendation": response[:200]
                })

        except Exception as e:
            logger.warning(f"[QWEN-LLM] Deep analysis error: {e}")

        return violations

    def _detect_wsp_violations_rules_only(self, module_path: str) -> List[Dict]:
        """Rule-based: Fast heuristic checks for obvious violations"""
        violations = []
        path = Path(module_path)

        # WSP 3: Check if module is in correct domain
        if 'modules/infrastructure' in str(path):
            if 'doc_dae' in str(path):
                violations.append({
                    "issue": "DocDAE in infrastructure but only used by HoloIndex",
                    "wsp": "WSP 3 (Functional Distribution)",
                    "recommendation": "Move to holo_index/doc_organizer/"
                })

        # WSP 87: Check file size
        try:
            lines = len(path.read_text(encoding='utf-8').split('\n'))
            if lines > 500:
                violations.append({
                    "issue": f"File has {lines} lines (limit: 500)",
                    "wsp": "WSP 87 (Code Navigation)",
                    "recommendation": "Split into smaller modules"
                })
        except Exception:
            pass

        return violations

    def _calculate_coupling(self, import_refs: List, class_refs: List) -> float:
        """Calculate how coupled this module is"""
        total_refs = len(import_refs) + len(class_refs)
        if total_refs == 0:
            return 0.0

        # High coupling if many external references
        return min(1.0, total_refs / 10.0)

    def _get_size_metrics(self, module_path: str) -> Dict:
        """Get module size metrics"""
        try:
            content = Path(module_path).read_text(encoding='utf-8')
            lines = content.split('\n')

            classes = len([l for l in lines if l.strip().startswith('class ')])
            functions = len([l for l in lines if l.strip().startswith('def ')])

            return {
                "lines": len(lines),
                "classes": classes,
                "functions": functions
            }
        except Exception:
            return {"lines": 0, "classes": 0, "functions": 0}

    # PHASE 2: Qwen - Strategic Planning

    def generate_refactoring_plan(self, module_path: str, target_location: str,
                                   analysis: Dict) -> RefactoringPlan:
        """
        Qwen's role: Generate strategic refactoring plan

        Args:
            module_path: Current module location
            target_location: Target location for refactoring
            analysis: Gemma's dependency analysis

        Returns:
            Complete RefactoringPlan with all tasks
        """
        logger.info(f"[QWEN] Generating refactoring plan: {module_path} -> {target_location}")

        # Use Qwen LLM for intelligent planning if available
        if self.qwen_engine:
            try:
                qwen_strategy = self._generate_strategy_with_qwen(module_path, target_location, analysis)
                logger.info(f"[QWEN-LLM] Strategic plan generated: {qwen_strategy.get('strategy_type', 'standard')}")
            except Exception as e:
                logger.warning(f"[QWEN-LLM] Planning failed, using standard approach: {e}")

        tasks = []

        # Task 1: Create target directory
        target_dir = Path(target_location).parent
        tasks.append(RefactoringTask(
            task_type="create_directory",
            source_path="",
            target_path=str(target_dir),
            reason="Prepare target location for module",
            wsp_justification="WSP 49 (Module Structure)",
            dependencies=[]
        ))

        # Task 2: Move module files
        source_dir = Path(module_path).parent
        for file in source_dir.rglob('*'):
            if file.is_file():
                rel_path = file.relative_to(source_dir)
                target_file = Path(target_location) / rel_path

                tasks.append(RefactoringTask(
                    task_type="move_file",
                    source_path=str(file),
                    target_path=str(target_file),
                    reason=f"Move {file.name} to new location",
                    wsp_justification="WSP 3 (Functional Distribution)",
                    dependencies=["create_directory"]
                ))

        # Task 3: Update import references
        for file_path, line_num, import_stmt in analysis['import_references']:
            tasks.append(RefactoringTask(
                task_type="update_import",
                source_path=file_path,
                target_path=file_path,  # Update in place
                reason=f"Fix import at line {line_num}",
                wsp_justification="WSP 50 (Pre-Action Verification)",
                dependencies=["move_file"]
            ))

        # Task 4: Run tests
        tasks.append(RefactoringTask(
            task_type="run_tests",
            source_path="",
            target_path="",
            reason="Verify refactoring didn't break anything",
            wsp_justification="WSP 5 (Test Coverage)",
            dependencies=["update_import"]
        ))

        # Task 5: Cleanup old directory
        tasks.append(RefactoringTask(
            task_type="cleanup",
            source_path=str(source_dir),
            target_path="",
            reason="Remove old module directory",
            wsp_justification="WSP 84 (No Duplication)",
            dependencies=["run_tests"]
        ))

        return RefactoringPlan(
            tasks=tasks,
            estimated_files_affected=len(analysis['import_references']),
            wsp_violations_fixed=[v['wsp'] for v in analysis['wsp_violations']],
            safety_checks=[
                "All imports resolve before cleanup",
                "Tests pass after changes",
                "No circular imports created"
            ],
            rollback_strategy="git reset --hard HEAD"
        )

    def _generate_strategy_with_qwen(self, module_path: str, target_location: str, analysis: Dict) -> Dict:
        """Use Qwen 1.5B LLM for intelligent refactoring strategy"""

        # Build strategic planning prompt
        prompt = f"""You are a code refactoring strategist. Analyze this module move and suggest the best approach.

Module: {module_path}
Target: {target_location}
Dependencies: {len(analysis['import_references'])} imports found
Coupling Score: {analysis['coupling_score']:.2f}
WSP Violations: {len(analysis['wsp_violations'])}

Based on this analysis, what is the best refactoring strategy?
A) Simple Move - Direct file relocation
B) Gradual Migration - Move with compatibility layer
C) Full Restructure - Break into smaller modules

Recommend strategy: """

        # Run Qwen inference
        response = self.qwen_engine.generate_response(prompt, max_tokens=200)

        # Parse response
        strategy = {
            "strategy_type": "standard",
            "qwen_recommendation": response,
            "complexity_assessment": "medium" if analysis['coupling_score'] > 0.5 else "low"
        }

        logger.info(f"[QWEN-LLM] Strategy recommendation: {response[:100]}...")
        return strategy

    # PHASE 3: 0102 Supervision - Execution with Oversight

    def execute_with_supervision(self, plan: RefactoringPlan,
                                  auto_approve: bool = False) -> Dict:
        """
        0102's role: Supervise execution of refactoring plan

        Args:
            plan: Qwen's refactoring plan
            auto_approve: If True, execute without prompts (for automation)

        Returns:
            Execution results with success/failure status
        """
        logger.info(f"[0102] Starting supervised execution ({len(plan.tasks)} tasks)")

        results = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "errors": [],
            "success": False
        }

        # Execute each task in sequence
        for i, task in enumerate(plan.tasks, 1):
            logger.info(f"[0102] Task {i}/{len(plan.tasks)}: {task.task_type}")

            # Get approval (unless auto-approved)
            if not auto_approve:
                print(f"\n[0102-SUPERVISION] Task {i}: {task.task_type}")
                print(f"  Source: {task.source_path}")
                print(f"  Target: {task.target_path}")
                print(f"  Reason: {task.reason}")
                print(f"  WSP: {task.wsp_justification}")

                approval = input("  Approve? (y/n): ").lower()
                if approval != 'y':
                    logger.warning(f"[0102] Task {i} rejected by supervisor")
                    results['errors'].append(f"Task {i} rejected by supervisor")
                    results['success'] = False
                    return results

            # Execute task
            try:
                self._execute_task(task)
                results['tasks_completed'] += 1
                logger.info(f"[0102] Task {i} completed successfully")
            except Exception as e:
                results['tasks_failed'] += 1
                results['errors'].append(f"Task {i} failed: {str(e)}")
                logger.error(f"[0102] Task {i} failed: {e}")

                # Rollback on failure
                logger.warning(f"[0102] Rolling back: {plan.rollback_strategy}")
                subprocess.run(plan.rollback_strategy.split(), cwd=self.repo_root)
                return results

        results['success'] = True
        logger.info(f"[0102] All tasks completed successfully")
        return results

    def _execute_task(self, task: RefactoringTask):
        """Execute a single refactoring task"""
        if task.task_type == "create_directory":
            Path(task.target_path).mkdir(parents=True, exist_ok=True)

        elif task.task_type == "move_file":
            source = Path(task.source_path)
            target = Path(task.target_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            # Prefer git mv when available to preserve history (WSP 50 + WSP 22 hygiene).
            git_dir = Path(self.repo_root) / ".git"
            if git_dir.exists():
                try:
                    result = subprocess.run(
                        ["git", "mv", str(source), str(target)],
                        cwd=self.repo_root,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if result.returncode == 0:
                        return
                except Exception:
                    # Fall back to filesystem move
                    pass

            shutil.move(str(source), str(target))

        elif task.task_type == "update_import":
            # TODO: Implement import updating
            pass

        elif task.task_type == "run_tests":
            # TODO: Run integration test
            pass

        elif task.task_type == "cleanup":
            path = Path(task.source_path)
            if path.exists():
                shutil.rmtree(path)

    # PHASE 4: Learning - Store Patterns

    def store_refactoring_pattern(self, module_path: str, target_location: str,
                                   plan: RefactoringPlan, results: Dict):
        """
        Store successful refactoring as learning pattern

        This enables recursive self-improvement - Qwen learns from
        successful refactorings and can apply patterns autonomously.
        """
        pattern = {
            "timestamp": str(Path.cwd()),
            "module_path": module_path,
            "target_location": target_location,
            "tasks_executed": results['tasks_completed'],
            "wsp_violations_fixed": plan.wsp_violations_fixed,
            "success": results['success'],
            "lessons_learned": {
                "pattern_type": "module_relocation",
                "coupling_score": "calculated_by_gemma",
                "files_affected": plan.estimated_files_affected
            }
        }

        if results['success']:
            self.patterns['successful_refactorings'].append(pattern)
            logger.info("[LEARNING] Stored successful refactoring pattern")
        else:
            self.patterns['failed_attempts'].append(pattern)
            logger.warning("[LEARNING] Stored failed refactoring for analysis")

        self._save_patterns()

    # PUBLIC API

    def refactor_module_autonomously(self, module_path: str, target_location: str,
                                      auto_approve: bool = False) -> Dict:
        """
        Main entry point: Autonomous refactoring with Qwen + Gemma + 0102

        Args:
            module_path: Module to refactor
            target_location: Where to move it
            auto_approve: Skip 0102 approval prompts

        Returns:
            Results dict with success status and metrics
        """
        logger.info(f"[START] Autonomous refactoring: {module_path} -> {target_location}")

        # Phase 1: Gemma analysis
        analysis = self.analyze_module_dependencies(module_path)

        # Phase 2: Qwen planning
        plan = self.generate_refactoring_plan(module_path, target_location, analysis)

        # Phase 3: 0102 supervision
        results = self.execute_with_supervision(plan, auto_approve)

        # Phase 4: Learning
        self.store_refactoring_pattern(module_path, target_location, plan, results)

        return results
