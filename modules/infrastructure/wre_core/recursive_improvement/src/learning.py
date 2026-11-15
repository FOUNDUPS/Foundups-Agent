# -*- coding: utf-8 -*-
import io


import asyncio
import json
import math
import multiprocessing
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
import datetime
import traceback
import re
import hashlib
import threading
from .core import ErrorPattern, Solution, Improvement, PatternType
from .persistence import QuantumStatePersistence, QuantumState
from .utils import load_memory, save_pattern, save_solution, save_improvement

logger = logging.getLogger(__name__)

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

class RecursiveLearningEngine:
    """
    WSP 48 Level 1: Protocol Self-Improvement Engine
    
    Learns from errors, extracts patterns, and generates improvement proposals.
    Artifact application remains fail closed until an authenticated executor is
    implemented.
    
    Enhanced with:
    - MCP server integration for tool connections
    - Chain-of-thought reasoning for better pattern extraction
    - Parallel processing support via pytest-xdist patterns
    - UV/Ruff integration hooks for faster operations
    """
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent.parent
        self.memory_root = Path(__file__).parent.parent / "memory"
        self.memory_root.mkdir(parents=True, exist_ok=True)
        
        # Memory banks
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.solutions: Dict[str, Solution] = {}
        self.improvements: Dict[str, Improvement] = {}
        
        # Enhanced: Chain-of-thought reasoning traces
        self.cot_traces: Dict[str, List[str]] = {}
        
        # Enhanced: MCP server connections for tools
        self.mcp_servers = {
            "github": None,  # For PR integration
            "database": None,  # For pattern storage
            "testing": None,  # For pytest-xdist coordination
            "linting": None   # For Ruff integration
        }
        
        # Enhanced: Parallel processing capabilities
        self.parallel_enabled = self._check_parallel_support()
        
        # Learning metrics
        self.metrics = {
            "errors_processed": 0,
            "patterns_extracted": 0,
            "solutions_generated": 0,
            "improvements_applied": 0,
            "tokens_saved": None, "token_reduction_measured": False,
            "total_tokens_saved": 0,
            "learning_velocity": 0.1,
            # Enhanced metrics
            "cot_reasoning_steps": 0,
            "parallel_processes": 1,
            "mcp_connections": 0,
            "test_time_compute": 0  # Test-time computation tracking
        }
        
        # Load existing memory
        self.error_patterns, self.solutions, self.improvements = load_memory(self.memory_root)
        
        # Initialize MCP connections if available
        self._init_mcp_connections()
        
        self.quantum_persistence = QuantumStatePersistence(self.memory_root)
        
        # Restore quantum state if available
        self.quantum_state = self._restore_quantum_state("default_session")
        self._rollback_handlers: Dict[str, Tuple[Callable[[], str], str, str]] = {}
        self._configure_auto_save()

    def _configure_auto_save(self) -> None:
        """Configure explicit opt-in persistence without growing initialization."""
        # Background persistence is explicit opt-in. Read/query construction
        # must not create an immortal thread or write repository-local memory.
        self._auto_save_stop = threading.Event()
        self._auto_save_thread: Optional[threading.Thread] = None
        if os.getenv("WRE_RECURSIVE_AUTO_SAVE", "0").strip() == "1":
            self._start_auto_save_loop(interval=300)
    
    def _restore_quantum_state(self, session: str) -> QuantumState:
        return self.quantum_persistence.restore_state(session) or QuantumState(
            coherence=0.618,  # Golden ratio default
            entanglement_matrix=[[1.0, 0.0], [0.0, 1.0]],  # Identity matrix
            operator_values={"default": 1.0},
            session_id=session
        )
    
    async def _auto_save(self):
        """Periodic state save"""
        if self.quantum_state:
            self.quantum_persistence.save_state(self.quantum_state)
            logger.debug(f"Auto-saved quantum state at {datetime.datetime.now().isoformat()}")
    
    def _start_auto_save_loop(self, interval: int):
        """Start one stoppable background loop for explicit auto-saving."""
        if interval <= 0:
            raise ValueError("auto-save interval must be positive")
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            return
        self._auto_save_stop.clear()

        def save_loop():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                while not self._auto_save_stop.is_set():
                    loop.run_until_complete(self._auto_save())
                    if self._auto_save_stop.wait(interval):
                        break
            finally:
                loop.close()

        self._auto_save_thread = threading.Thread(target=save_loop, daemon=True)
        self._auto_save_thread.start()

    def shutdown(self) -> bool:
        """Stop auto-save and persist the final state; fail closed on error."""
        self._auto_save_stop.set()
        thread = self._auto_save_thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=5.0)
        if thread and thread.is_alive():
            logger.error("Recursive learning auto-save did not stop")
            return False
        self._auto_save_thread = None
        try:
            if self.quantum_state:
                self.quantum_persistence.save_state(self.quantum_state)
            return True
        except Exception as exc:
            logger.error(
                "Recursive learning final state save failed; error_type=%s",
                type(exc).__name__,
            )
            return False

    def _check_parallel_support(self) -> bool:
        """Check if parallel processing is available (pytest-xdist pattern)"""
        try:
            import multiprocessing
            return multiprocessing.cpu_count() > 1
        except:
            return False
    
    def _init_mcp_connections(self):
        """Initialize MCP server connections if configured"""
        # Check for .claude/config.json or .cursor/rules for MCP config
        config_paths = [
            Path(".claude/config.json"),
            Path(".cursor/rules/mcp_config.json")
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if "mcp_servers" in config:
                            self._connect_mcp_servers(config["mcp_servers"])
                            break
                except Exception:
                    pass  # MCP not configured, continue without it
    
    def _connect_mcp_servers(self, servers_config: Dict):
        """Connect to configured MCP servers"""
        for server_name, server_config in servers_config.items():
            if server_name in self.mcp_servers:
                # Placeholder for actual MCP connection
                # Would connect to actual MCP server here
                self.mcp_servers[server_name] = server_config
                self.metrics["mcp_connections"] += 1
    
    async def process_error(self, error: Exception, context: Dict[str, Any] = None) -> Improvement:
        """
        Main entry point: Transform error into improvement
        
        This is where the magic happens - every error makes the system better.
        """
        self.metrics["errors_processed"] += 1
        
        # Extract pattern from error
        pattern = await self.extract_pattern(error, context)
        
        # Check if we've seen this pattern before
        existing_pattern = self._find_similar_pattern(pattern)
        if existing_pattern:
            existing_pattern.frequency += 1
            existing_pattern.last_seen = datetime.datetime.now().isoformat()
            pattern = existing_pattern
        else:
            self.error_patterns[pattern.pattern_id] = pattern
            save_pattern(self.memory_root, pattern)
            self.metrics["patterns_extracted"] += 1
        
        # Generate or retrieve solution
        solution = await self.remember_solution(pattern)
        if solution.solution_id not in self.solutions:
            self.solutions[solution.solution_id] = solution
            save_solution(self.memory_root, solution)
            self.metrics["solutions_generated"] += 1
        
        # Generate improvement
        improvement = await self.generate_improvement(pattern, solution)
        if improvement.improvement_id not in self.improvements:
            self.improvements[improvement.improvement_id] = improvement
            save_improvement(self.memory_root, improvement)
        
        # Update learning velocity (meta-improvement)
        self.metrics["learning_velocity"] *= 1.01  # Exponential growth
        
        return improvement
    
    async def extract_pattern(self, error: Exception, context: Dict[str, Any] = None) -> ErrorPattern:
        """
        Extract reusable pattern from error
        
        This is the key to learning - converting specific errors into
        general patterns that can be recognized and prevented.
        
        Enhanced with Chain-of-Thought reasoning for better pattern extraction.
        """
        # Generate pattern ID from error signature
        error_sig = f"{type(error).__name__}:{str(error)}"
        pattern_id = hashlib.md5(error_sig.encode()).hexdigest()[:8]
        
        # Enhanced: Chain-of-thought reasoning trace
        cot_trace = []
        
        # Step 1: Analyze error type
        cot_trace.append(f"Step 1: Error type is {type(error).__name__}")
        
        # Step 2: Extract root cause
        root_cause = self._extract_root_cause_cot(error, cot_trace)
        
        # Step 3: Identify similar patterns
        cot_trace.append("Step 3: Searching for similar patterns in memory...")
        similar_patterns = self._find_similar_patterns_cot(error_sig)
        
        # Step 4: Generate abstraction
        cot_trace.append("Step 4: Abstracting pattern for reusability...")
        
        # Store CoT trace for learning
        self.cot_traces[pattern_id] = cot_trace
        self.metrics["cot_reasoning_steps"] += len(cot_trace)
        
        # Extract stack trace
        stack_trace = traceback.format_exception(type(error), error, error.__traceback__)
        
        # Determine pattern type with enhanced reasoning
        pattern_type = self._classify_pattern_cot(error, cot_trace)
        
        # Create pattern with enhanced context
        pattern = ErrorPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=stack_trace,
            context={
                **(context or {}),
                "root_cause": root_cause,
                "similar_patterns": similar_patterns,
                "cot_steps": len(cot_trace)
            }
        )
        
        return pattern
    
    def _extract_root_cause_cot(self, error: Exception, trace: List[str]) -> str:
        """Extract root cause using chain-of-thought reasoning"""
        error_msg = str(error).lower()
        
        # Reasoning steps for root cause
        if "module" in error_msg and "not found" in error_msg:
            trace.append("Step 2a: Missing module detected")
            return "missing_dependency"
        elif "wsp" in error_msg:
            trace.append("Step 2b: WSP violation detected")
            return "wsp_violation"
        elif "timeout" in error_msg:
            trace.append("Step 2c: Performance issue detected")
            return "performance_bottleneck"
        else:
            trace.append("Step 2d: Generic error pattern")
            return "generic_error"
    
    def _find_similar_patterns_cot(self, error_sig: str) -> List[str]:
        """Find similar patterns using enhanced search"""
        similar = []
        for pid, pattern in self.error_patterns.items():
            # Calculate similarity score
            if pattern.error_type in error_sig:
                similar.append(pid)
        return similar[:3]  # Top 3 similar patterns
    
    def _classify_pattern_cot(self, error: Exception, trace: List[str]) -> PatternType:
        """Classify pattern with chain-of-thought reasoning"""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Enhanced classification with reasoning
        if 'wsp' in error_msg or 'violation' in error_msg:
            trace.append("Classification: WSP violation pattern")
            return PatternType.VIOLATION
        elif 'performance' in error_msg or 'timeout' in error_msg:
            trace.append("Classification: Performance pattern")
            return PatternType.PERFORMANCE
        elif 'attribute' in error_type or 'key' in error_type:
            trace.append("Classification: Structural pattern")
            return PatternType.STRUCTURAL
        elif 'behavior' in error_msg:
            trace.append("Classification: Behavioral pattern")
            return PatternType.BEHAVIORAL
        else:
            trace.append("Classification: General error pattern")
            return PatternType.ERROR
    
    def _classify_pattern(self, error: Exception) -> PatternType:
        """Classify the type of pattern"""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        if 'wsp' in error_msg or 'violation' in error_msg:
            return PatternType.VIOLATION
        elif 'performance' in error_msg or 'timeout' in error_msg:
            return PatternType.PERFORMANCE
        elif 'attribute' in error_type or 'key' in error_type:
            return PatternType.STRUCTURAL
        elif 'behavior' in error_msg:
            return PatternType.BEHAVIORAL
        else:
            return PatternType.ERROR
    
    def _find_similar_pattern(self, pattern: ErrorPattern) -> Optional[ErrorPattern]:
        """Find if we've seen a similar pattern before
        
        Enhanced with parallel search if available
        """
        if self.parallel_enabled and len(self.error_patterns) > 100:
            # Use parallel search for large pattern banks
            return self._parallel_pattern_search(pattern)
        else:
            # Standard sequential search
            for existing_id, existing_pattern in self.error_patterns.items():
                if (existing_pattern.error_type == pattern.error_type and
                    existing_pattern.error_message == pattern.error_message):
                    return existing_pattern
        return None
    
    def _parallel_pattern_search(self, pattern: ErrorPattern) -> Optional[ErrorPattern]:
        """Parallel pattern search using multiprocessing (pytest-xdist pattern)"""
        from concurrent.futures import ProcessPoolExecutor
        
        # Split patterns into chunks for parallel processing
        patterns_list = list(self.error_patterns.items())
        chunk_size = len(patterns_list) // multiprocessing.cpu_count()
        
        with ProcessPoolExecutor() as executor:
            futures = []
            for i in range(0, len(patterns_list), chunk_size):
                chunk = patterns_list[i:i+chunk_size]
                future = executor.submit(self._search_chunk, pattern, chunk)
                futures.append(future)
            
            # Collect results
            for future in futures:
                result = future.result()
                if result:
                    return result
        return None
    
    def _search_chunk(self, pattern: ErrorPattern, chunk: List[Tuple[str, ErrorPattern]]) -> Optional[ErrorPattern]:
        """Search a chunk of patterns"""
        for _, existing_pattern in chunk:
            if (existing_pattern.error_type == pattern.error_type and
                existing_pattern.error_message == pattern.error_message):
                return existing_pattern
        return None
    
    async def remember_solution(self, pattern: ErrorPattern) -> Solution:
        """
        Remember solution from 0201 quantum state
        
        This is zen coding - the solution already exists in the future state,
        we just need to remember it, not create it.
        
        Enhanced with test-time compute optimization:
        - Spends more compute at test time for better solutions
        - Multiple solution paths evaluated in parallel
        - Best solution selected based on confidence
        """
        # Track test-time compute
        start_compute = self.metrics.get("test_time_compute", 0)
        
        # Try multiple solution paths in parallel (test-time scaling)
        solution_paths = []
        
        # Path 1: Access quantum memory (fastest)
        solution_paths.append(self._access_quantum_memory(pattern))
        
        # Path 2: Search MCP tools if connected
        if self.mcp_servers.get("database"):
            solution_paths.append(self._search_mcp_solutions(pattern))
        
        # Path 3: Generate from learned patterns
        solution_paths.append(self._generate_learned_solution(pattern))
        
        # Path 4: Chain-of-thought reasoning for novel solution
        solution_paths.append(self._generate_cot_solution(pattern))
        
        # Evaluate all paths (test-time compute investment)
        solutions = []
        for path in solution_paths:
            try:
                sol = await path
                if sol:
                    solutions.append(sol)
            except:
                pass  # Some paths may fail
        
        # Select best solution based on confidence
        best_solution = max(solutions, key=lambda s: s.confidence) if solutions else None
        
        if not best_solution:
            # Ultimate fallback
            best_solution = await self._generate_learned_solution(pattern)
        
        # Update test-time compute metric
        self.metrics["test_time_compute"] = start_compute + len(solution_paths)
        
        return best_solution
    
    async def _search_mcp_solutions(self, pattern: ErrorPattern) -> Optional[Solution]:
        """Search for solutions via MCP database connection"""
        # Would query MCP server for existing solutions
        # Placeholder for actual MCP integration
        return None
    
    async def _generate_cot_solution(self, pattern: ErrorPattern) -> Optional[Solution]:
        """Generate solution using chain-of-thought reasoning"""
        solution_id = hashlib.md5(f"{pattern.pattern_id}:cot".encode()).hexdigest()[:8]
        
        # Chain-of-thought steps for solution generation
        cot_steps = []
        cot_steps.append(f"Analyzing error: {pattern.error_type}")
        cot_steps.append(f"Root cause: {pattern.context.get('root_cause', 'unknown')}")
        cot_steps.append("Considering prevention strategies...")
        cot_steps.append("Evaluating token efficiency...")
        
        # Generate solution based on CoT reasoning
        if "missing" in pattern.error_message.lower():
            cot_steps.append("Solution: Add existence checks and creation logic")
            implementation = "ensure_exists(resource) or create_default(resource)"
            confidence = 0.88
        elif "timeout" in pattern.error_message.lower():
            cot_steps.append("Solution: Implement async with timeout control")
            implementation = "async_with_timeout(operation, timeout=30)"
            confidence = 0.85
        else:
            cot_steps.append("Solution: Add comprehensive error handling")
            implementation = "handle_with_retry(operation, max_retries=3)"
            confidence = 0.75
        
        # Store CoT trace
        self.cot_traces[solution_id] = cot_steps
        
        return Solution(
            solution_id=solution_id,
            pattern_id=pattern.pattern_id,
            solution_type="prevention",
            description=cot_steps[-1].replace("Solution: ", ""),
            implementation=implementation,
            confidence=confidence,
            source="chain_of_thought",
            token_savings=0
        )
    
    async def _access_quantum_memory(self, pattern: ErrorPattern) -> Optional[Solution]:
        """
        Access 0201 quantum state for pre-existing solution
        
        In true implementation, this would use CMST Protocol to access
        the nonlocal future state where the solution already exists.
        """
        # Simulate quantum access (in reality, this would use CMST Protocol)
        quantum_solutions = {
            "FileNotFoundError": {
                "solution_type": "prevention",
                "description": "Add existence check before file access",
                "implementation": "if not path.exists(): create_with_template(path)",
                "confidence": 0.95
            },
            "AttributeError": {
                "solution_type": "fix",
                "description": "Add missing attribute with default value",
                "implementation": "setattr(obj, attr, default_value)",
                "confidence": 0.90
            },
            "WSPViolation": {
                "solution_type": "prevention",
                "description": "Add WSP compliance check before action",
                "implementation": "validate_wsp_compliance(action)",
                "confidence": 0.98
            }
        }
        
        if pattern.error_type in quantum_solutions:
            sol_data = quantum_solutions[pattern.error_type]
            solution_id = hashlib.md5(f"{pattern.pattern_id}:quantum".encode()).hexdigest()[:8]
            
            return Solution(
                solution_id=solution_id,
                pattern_id=pattern.pattern_id,
                source="quantum",
                token_savings=0,
                **sol_data
            )
        
        return None
    
    async def _generate_learned_solution(self, pattern: ErrorPattern) -> Solution:
        """Generate solution from learned patterns"""
        solution_id = hashlib.md5(f"{pattern.pattern_id}:learned".encode()).hexdigest()[:8]
        
        # Basic learned solutions based on pattern type
        if pattern.pattern_type == PatternType.VIOLATION:
            return Solution(
                solution_id=solution_id,
                pattern_id=pattern.pattern_id,
                solution_type="prevention",
                description="Add WSP validation before operation",
                implementation="await validate_wsp_compliance(operation)",
                confidence=0.85,
                source="learned",
                token_savings=0
            )
        elif pattern.pattern_type == PatternType.PERFORMANCE:
            return Solution(
                solution_id=solution_id,
                pattern_id=pattern.pattern_id,
                solution_type="optimization",
                description="Use pattern memory instead of computation",
                implementation="result = pattern_memory.get(key) or compute(key)",
                confidence=0.80,
                source="learned",
                token_savings=0
            )
        else:
            return Solution(
                solution_id=solution_id,
                pattern_id=pattern.pattern_id,
                solution_type="fix",
                description="Add error handling and retry logic",
                implementation="try_with_exponential_backoff(operation)",
                confidence=0.70,
                source="learned",
                token_savings=0
            )
    
    async def generate_improvement(self, pattern: ErrorPattern, solution: Solution) -> Improvement:
        """Generate system improvement from pattern and solution"""
        improvement_id = hashlib.md5(
            f"{pattern.pattern_id}:{solution.solution_id}".encode()
        ).hexdigest()[:8]
        
        # Determine target for improvement
        target = self._determine_improvement_target(pattern)
        
        # Generate before/after states
        before_state = self._get_current_state(target)
        after_state = self._apply_solution_to_state(before_state, solution)
        
        improvement = Improvement(
            improvement_id=improvement_id,
            pattern_id=pattern.pattern_id,
            solution_id=solution.solution_id,
            target=target,
            change_type=self._determine_change_type(solution),
            before_state=before_state,
            after_state=after_state,
            metrics={
                "expected_token_savings": None,
                "token_reduction_measured": False,
                "confidence": solution.confidence,
                "pattern_frequency": pattern.frequency
            }
        )
        
        return improvement
    
    def _determine_improvement_target(self, pattern: ErrorPattern) -> str:
        """Determine what needs to be improved"""
        # Extract file path from stack trace if available
        for line in pattern.stack_trace:
            if "File" in line and ".py" in line:
                match = re.search(r'File "([^"]+)"', line)
                if match:
                    return match.group(1)
        
        # Default to WSP framework if WSP-related
        if pattern.pattern_type == PatternType.VIOLATION:
            return "WSP_framework"
        
        return "system"
    
    def _determine_change_type(self, solution: Solution) -> str:
        """Determine type of change from solution"""
        if solution.solution_type == "prevention":
            return "add"
        elif solution.solution_type == "fix":
            return "update"
        elif solution.solution_type == "optimization":
            return "refactor"
        else:
            return "update"
    
    def _get_current_state(self, target: str) -> str:
        """Get current state of target (simplified)"""
        return f"Current state of {target}"
    
    def _apply_solution_to_state(self, state: str, solution: Solution) -> str:
        """Apply solution to state (simplified)"""
        return f"{state} + {solution.implementation}"
    
    def _get_rollback_handlers(self) -> Dict[str, Tuple[Callable[[], str], str, str]]:
        """Lazily initialize per-instance rollback handlers (safe with __new__)."""
        handlers = getattr(self, "_rollback_handlers", None)
        if handlers is None:
            handlers = {}
            setattr(self, "_rollback_handlers", handlers)
        return handlers

    @staticmethod
    def _evidence_field(obj: Any, name: str, default: Any = None) -> Any:
        if isinstance(obj, Mapping):
            return obj.get(name, default)
        return getattr(obj, name, default)

    @staticmethod
    def _is_nonempty_str(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _is_nonneg_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @staticmethod
    def _is_nonneg_number(value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        )

    @staticmethod
    def _parse_sha256_hex(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if cleaned.lower().startswith("sha256:"):
            cleaned = cleaned[7:]
        if not re.fullmatch(r"[0-9a-fA-F]{64}", cleaned):
            return None
        return cleaned.lower()

    @classmethod
    def _validate_measurement_evidence(
        cls,
        measurement_evidence: Any,
        *,
        worker_id: str,
        work_order_id: str,
        before_digest: str,
        desired_after_state: Any,
    ) -> Optional[Dict[str, Any]]:
        """Validate receipt-backed non-self-authored measurement evidence fail-closed."""
        if not isinstance(measurement_evidence, Mapping):
            return None

        m_receipt_id = measurement_evidence.get("measurement_receipt_id")
        evaluator_id = measurement_evidence.get("evaluator_id")
        m_work_order_id = measurement_evidence.get("work_order_id")
        baseline_tokens = measurement_evidence.get("baseline_tokens")
        candidate_tokens = measurement_evidence.get("candidate_tokens")

        if not (
            cls._is_nonempty_str(m_receipt_id)
            and cls._is_nonempty_str(evaluator_id)
            and evaluator_id.strip() != worker_id.strip()
            and cls._is_nonempty_str(m_work_order_id)
            and m_work_order_id == work_order_id
            and cls._is_nonneg_int(baseline_tokens)
            and cls._is_nonneg_int(candidate_tokens)
            and int(candidate_tokens) <= int(baseline_tokens)
        ):
            return None

        raw_before_digest = measurement_evidence.get("before_state_digest")
        if raw_before_digest is not None:
            expected_before_digest = cls._parse_sha256_hex(raw_before_digest)
            if expected_before_digest is None or expected_before_digest != before_digest:
                return None

        expected_after_digest: Optional[str] = None
        raw_after_digest = measurement_evidence.get("after_state_digest")
        if raw_after_digest is not None:
            expected_after_digest = cls._parse_sha256_hex(raw_after_digest)
            if expected_after_digest is None:
                return None
            if isinstance(desired_after_state, str):
                desired_after_digest = hashlib.sha256(
                    desired_after_state.encode("utf-8")
                ).hexdigest()
                if expected_after_digest != desired_after_digest:
                    return None

        validated: Dict[str, Any] = {
            "measurement_receipt_id": m_receipt_id.strip(),
            "evaluator_id": evaluator_id.strip(),
            "work_order_id": m_work_order_id,
            "baseline_tokens": int(baseline_tokens),
            "candidate_tokens": int(candidate_tokens),
            "expected_after_digest": expected_after_digest,
        }

        b_lat = measurement_evidence.get("baseline_latency_ms")
        c_lat = measurement_evidence.get("candidate_latency_ms")
        s_lat = measurement_evidence.get("latency_ms_saved")
        if cls._is_nonneg_number(b_lat):
            validated["baseline_latency_ms"] = b_lat
        if cls._is_nonneg_number(c_lat):
            validated["candidate_latency_ms"] = c_lat
        if cls._is_nonneg_number(s_lat):
            validated["latency_ms_saved"] = s_lat
        elif cls._is_nonneg_number(b_lat) and cls._is_nonneg_number(c_lat) and b_lat >= c_lat:
            validated["latency_ms_saved"] = b_lat - c_lat

        return validated

    @classmethod
    def _validate_verification_evidence(
        cls, verification_evidence: Optional[Mapping[str, Any]]
    ) -> Optional[Tuple[str, str, str]]:
        """Validate verifier, ratchet, and held-out gate receipts fail-closed."""
        if not isinstance(verification_evidence, Mapping):
            return None

        verification_result = verification_evidence.get("verification_result")
        ratchet_result = verification_evidence.get("ratchet_result")
        held_out_gate_result = verification_evidence.get("held_out_gate_result")
        if verification_result is None or ratchet_result is None or held_out_gate_result is None:
            return None

        if cls._evidence_field(verification_result, "accepted") is not True:
            return None
        if cls._evidence_field(verification_result, "decision") != "AUTONOMOUS_SLICE_VERIFIER_ACCEPT":
            return None
        v_receipt = cls._evidence_field(verification_result, "receipt")
        if v_receipt is None:
            return None
        v_receipt_id = cls._evidence_field(v_receipt, "receipt_id")
        v_work_order_id = cls._evidence_field(v_receipt, "work_order_id")
        v_worker_id = cls._evidence_field(v_receipt, "worker_id")
        v_verifier_id = cls._evidence_field(v_receipt, "verifier_id")
        v_head_sha = cls._evidence_field(v_receipt, "head_sha")
        if not (
            cls._is_nonempty_str(v_receipt_id)
            and cls._is_nonempty_str(v_work_order_id)
            and cls._is_nonempty_str(v_worker_id)
            and cls._is_nonempty_str(v_verifier_id)
            and v_verifier_id.strip() != v_worker_id.strip()
            and isinstance(v_head_sha, str)
            and bool(re.fullmatch(r"[0-9a-fA-F]{40}", v_head_sha))
        ):
            return None

        if cls._evidence_field(ratchet_result, "accepted") is not True:
            return None
        if cls._evidence_field(ratchet_result, "decision") != "OUTCOME_RATCHET_RECORDED":
            return None
        r_receipt = cls._evidence_field(ratchet_result, "receipt")
        if r_receipt is None:
            return None
        r_ratchet_id = cls._evidence_field(r_receipt, "ratchet_id")
        r_verifier_receipt_id = cls._evidence_field(r_receipt, "verifier_receipt_id")
        r_work_order_id = cls._evidence_field(r_receipt, "work_order_id")
        if not (
            cls._is_nonempty_str(r_ratchet_id)
            and r_verifier_receipt_id == v_receipt_id
            and r_work_order_id == v_work_order_id
        ):
            return None

        if cls._evidence_field(held_out_gate_result, "accepted") is not True:
            return None
        if (
            cls._evidence_field(held_out_gate_result, "decision")
            != "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT"
        ):
            return None
        g_receipt = cls._evidence_field(held_out_gate_result, "receipt")
        if g_receipt is None:
            return None
        g_gate_id = cls._evidence_field(g_receipt, "gate_id")
        g_ratchet_id = cls._evidence_field(g_receipt, "ratchet_id")
        g_verifier_receipt_id = cls._evidence_field(g_receipt, "verifier_receipt_id")
        g_admission_allowed = cls._evidence_field(g_receipt, "pattern_memory_admission_allowed")
        if not (
            cls._is_nonempty_str(g_gate_id)
            and g_ratchet_id == r_ratchet_id
            and g_verifier_receipt_id == v_receipt_id
            and g_admission_allowed is True
        ):
            return None

        return v_receipt_id, r_ratchet_id, g_gate_id

    async def apply_improvement(
        self,
        improvement: Improvement,
        *,
        verification_evidence: Optional[Mapping[str, Any]] = None,
        target_applicator: Optional[Callable[[str, str], Tuple[str, Callable[[], str]]]] = None,
        measurement_evidence: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        """
        Apply an improvement only when backed by verified non-self-authored
        ratchet + held-out gate evidence and a reversible target applicator.

        Legacy zero-evidence calls remain fail closed (`blocked_unimplemented`).
        Optional `measurement_evidence` validates fail closed before mutation.
        """
        try:
            if (
                verification_evidence is None
                and target_applicator is None
                and measurement_evidence is None
            ):
                improvement.applied = False
                improvement.applied_at = None
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False
                improvement.metrics["application_status"] = "blocked_unimplemented"
                save_improvement(self.memory_root, improvement)
                return False

            evidence_ids = self._validate_verification_evidence(verification_evidence)
            if (
                evidence_ids is None
                or not callable(target_applicator)
                or not isinstance(improvement.before_state, str)
            ):
                improvement.applied = False
                improvement.applied_at = None
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False
                improvement.metrics["application_status"] = "blocked_verification_rejected"
                save_improvement(self.memory_root, improvement)
                return False

            before_digest = hashlib.sha256(improvement.before_state.encode("utf-8")).hexdigest()

            validated_measurement: Optional[Dict[str, Any]] = None
            if measurement_evidence is not None:
                assert isinstance(verification_evidence, Mapping)
                v_result = verification_evidence.get("verification_result")
                v_receipt = self._evidence_field(v_result, "receipt")
                v_worker_id = str(self._evidence_field(v_receipt, "worker_id"))
                v_work_order_id = str(self._evidence_field(v_receipt, "work_order_id"))
                validated_measurement = self._validate_measurement_evidence(
                    measurement_evidence,
                    worker_id=v_worker_id,
                    work_order_id=v_work_order_id,
                    before_digest=before_digest,
                    desired_after_state=improvement.after_state,
                )
                if validated_measurement is None:
                    improvement.applied = False
                    improvement.applied_at = None
                    improvement.tokens_saved = None
                    improvement.metrics["token_reduction_measured"] = False
                    improvement.metrics["application_status"] = "blocked_measurement_rejected"
                    save_improvement(self.memory_root, improvement)
                    return False

            applied_result = target_applicator(improvement.before_state, improvement.after_state)
            if not isinstance(applied_result, tuple) or len(applied_result) != 2:
                improvement.applied = False
                improvement.applied_at = None
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False
                improvement.metrics["application_status"] = "blocked_verification_rejected"
                save_improvement(self.memory_root, improvement)
                return False

            applied_state, rollback_fn = applied_result
            if not isinstance(applied_state, str) or not callable(rollback_fn):
                improvement.applied = False
                improvement.applied_at = None
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False
                improvement.metrics["application_status"] = "blocked_verification_rejected"
                save_improvement(self.memory_root, improvement)
                return False

            after_digest = hashlib.sha256(applied_state.encode("utf-8")).hexdigest()
            if after_digest == before_digest:
                improvement.applied = False
                improvement.applied_at = None
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False
                improvement.metrics["application_status"] = "blocked_verification_rejected"
                save_improvement(self.memory_root, improvement)
                return False

            if (
                validated_measurement is not None
                and validated_measurement["expected_after_digest"] is not None
                and after_digest != validated_measurement["expected_after_digest"]
            ):
                rollback_fn()
                improvement.applied = False
                improvement.applied_at = None
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False
                improvement.metrics["application_status"] = "blocked_measurement_rejected"
                save_improvement(self.memory_root, improvement)
                return False

            verifier_receipt_id, ratchet_id, gate_id = evidence_ids
            self._get_rollback_handlers()[improvement.improvement_id] = (
                rollback_fn,
                before_digest,
                improvement.before_state,
            )
            improvement.applied = True
            improvement.applied_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            improvement.after_state = applied_state
            improvement.rollback_available = True
            improvement.metrics["application_status"] = "applied_verified"
            improvement.metrics["verifier_receipt_id"] = verifier_receipt_id
            improvement.metrics["ratchet_id"] = ratchet_id
            improvement.metrics["gate_id"] = gate_id
            improvement.metrics["before_state_digest"] = f"sha256:{before_digest}"
            improvement.metrics["after_state_digest"] = f"sha256:{after_digest}"
            improvement.metrics["rollback_available"] = True

            if validated_measurement is None:
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False
            else:
                tokens_saved = (
                    validated_measurement["baseline_tokens"]
                    - validated_measurement["candidate_tokens"]
                )
                improvement.tokens_saved = tokens_saved
                improvement.metrics["token_reduction_measured"] = True
                improvement.metrics["measurement_receipt_id"] = validated_measurement[
                    "measurement_receipt_id"
                ]
                improvement.metrics["evaluator_id"] = validated_measurement["evaluator_id"]
                improvement.metrics["baseline_tokens"] = validated_measurement["baseline_tokens"]
                improvement.metrics["candidate_tokens"] = validated_measurement["candidate_tokens"]
                if "baseline_latency_ms" in validated_measurement:
                    improvement.metrics["baseline_latency_ms"] = validated_measurement[
                        "baseline_latency_ms"
                    ]
                if "candidate_latency_ms" in validated_measurement:
                    improvement.metrics["candidate_latency_ms"] = validated_measurement[
                        "candidate_latency_ms"
                    ]
                if "latency_ms_saved" in validated_measurement:
                    improvement.metrics["latency_ms_saved"] = validated_measurement[
                        "latency_ms_saved"
                    ]
                self.metrics["total_tokens_saved"] = (
                    int(self.metrics.get("total_tokens_saved") or 0) + tokens_saved
                )

            self.metrics["improvements_applied"] = int(self.metrics.get("improvements_applied", 0)) + 1

            save_improvement(self.memory_root, improvement)
            return True

        except Exception as e:
            # Even failures are learning opportunities!
            await self.process_error(e, {"improvement_id": improvement.improvement_id})
            return False

    async def rollback_improvement(self, improvement: Improvement) -> bool:
        """Roll back an applied improvement and verify restored state digest."""
        handlers = self._get_rollback_handlers()
        entry = handlers.get(improvement.improvement_id)
        if entry is None:
            return False

        rollback_fn, before_digest, _ = entry
        try:
            restored_state = rollback_fn()
            if not isinstance(restored_state, str):
                return False
            restored_digest = hashlib.sha256(restored_state.encode("utf-8")).hexdigest()
            if restored_digest != before_digest:
                return False

            improvement.applied = False
            improvement.after_state = restored_state
            improvement.rollback_available = False
            improvement.metrics["application_status"] = "rolled_back"
            improvement.metrics["rolled_back_at"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            improvement.metrics["rollback_verified"] = True
            improvement.metrics["rollback_available"] = False

            if (
                improvement.metrics.get("token_reduction_measured") is True
                and isinstance(improvement.tokens_saved, int)
                and not isinstance(improvement.tokens_saved, bool)
            ):
                current_total = int(self.metrics.get("total_tokens_saved") or 0)
                self.metrics["total_tokens_saved"] = max(
                    0, current_total - improvement.tokens_saved
                )
                improvement.metrics["rolled_back_tokens_saved"] = improvement.tokens_saved
                improvement.tokens_saved = None
                improvement.metrics["token_reduction_measured"] = False

            self.metrics["improvements_applied"] = max(
                0, int(self.metrics.get("improvements_applied", 0)) - 1
            )
            handlers.pop(improvement.improvement_id, None)
            save_improvement(self.memory_root, improvement)
            return True
        except Exception as e:
            await self.process_error(e, {"improvement_id": improvement.improvement_id})
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current learning metrics"""
        metrics = self.metrics.copy()
        
        # Calculate derived metrics
        if metrics["errors_processed"] > 0:
            metrics["learning_rate"] = metrics["patterns_extracted"] / metrics["errors_processed"]
            metrics["solution_rate"] = metrics["solutions_generated"] / metrics["errors_processed"]
            metrics["improvement_rate"] = metrics["improvements_applied"] / metrics["errors_processed"]
        else:
            metrics["learning_rate"] = 0
            metrics["solution_rate"] = 0
            metrics["improvement_rate"] = 0
        
        # Calculate prevention rate
        total_patterns = len(self.error_patterns)
        recurring_patterns = sum(1 for p in self.error_patterns.values() if p.frequency > 1)
        if total_patterns > 0:
            metrics["prevention_rate"] = 1 - (recurring_patterns / total_patterns)
        else:
            metrics["prevention_rate"] = 0
        
        return metrics

# Global instance for easy access
_engine = None

def get_engine() -> RecursiveLearningEngine:
    """Get or create global engine instance"""
    global _engine
    if _engine is None:
        _engine = RecursiveLearningEngine()
    return _engine

async def process_error(error: Exception, context: Dict[str, Any] = None) -> Improvement:
    """Convenience function to process errors"""
    engine = get_engine()
    return await engine.process_error(error, context)

def install_global_handler():
    """Install global exception handler for automatic learning"""
    import sys
    
    def exception_handler(exc_type, exc_value, exc_traceback):
        """Global exception handler that triggers learning"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Process error asynchronously
        engine = get_engine()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        improvement = loop.run_until_complete(
            engine.process_error(exc_value, {"global_handler": True})
        )
        
        print(f"\n[AI] Learned from error: {improvement.improvement_id}")
        print(f"   Pattern: {improvement.pattern_id}")
        print(f"   Solution: {improvement.solution_id}")
        print(f"   Target: {improvement.target}")
        
        # Still show the original error
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_handler

if __name__ == "__main__":
    # Test the recursive learning engine
    async def test():
        engine = RecursiveLearningEngine()
        
        # Simulate some errors
        errors = [
            FileNotFoundError("config.yaml not found"),
            AttributeError("'NoneType' object has no attribute 'process'"),
            ValueError("WSP 49 violation: test file in wrong location"),
            TimeoutError("Operation exceeded 30 second limit"),
        ]
        
        print("Testing Recursive Learning Engine")
        print("=" * 50)
        
        for error in errors:
            print(f"\nProcessing: {error}")
            improvement = await engine.process_error(error)
            print(f"  Generated improvement: {improvement.improvement_id}")
            print(f"  Target: {improvement.target}")
            print(f"  Type: {improvement.change_type}")
            
            # Apply improvement
            success = await engine.apply_improvement(improvement)
            print(f"  Applied: {success}")
        
        # Show metrics
        print("\nLearning Metrics:")
        print("-" * 30)
        metrics = engine.get_metrics()
        for key, value in metrics.items():
            print(f"  {key}: {value}")
    
    asyncio.run(test())
