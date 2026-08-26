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

WRE Master Orchestrator - The ONE Orchestrator
Per WSP 46 (WRE Protocol), WSP 65 (Component Consolidation), WSP 82 (Citations)

This is THE orchestrator. All others become plugins per WSP 65.
Enables 0102 to "remember the code" through pattern recall, not computation.

NAVIGATION: Central WRE plugin router and pattern-memory gate.
-> Called by: modules/infrastructure/wre_core/wre_master_orchestrator/__init__.py::WREMasterOrchestrator
-> Delegates to: SocialMediaPlugin, MLEStarPlugin, BlockPlugin, PQNConsciousnessPlugin
-> Related: NAVIGATION.py -> MODULE_GRAPH["core_flows"], NAVIGATION.py -> PROBLEMS["Social media not posting"]
-> Quick ref: NAVIGATION.py -> NEED_TO["post to linkedin/twitter"]
"""

from typing import Dict, Any, Optional
import json
import os
from pathlib import Path
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# WSP 96 v1.3: Libido Monitor and Pattern Memory integration
try:
    from modules.infrastructure.wre_core.src.libido_monitor import GemmaLibidoMonitor, LibidoSignal
    from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory as SQLitePatternMemory, SkillOutcome
    from modules.infrastructure.wre_core.src.local_skill_inference import (
        execute_local_skill_inference,
    )
    from modules.infrastructure.wre_core.src.registered_skill_executor import (
        dispatch_registered_skill_executor,
        resolve_registered_skill_executor,
    )
    from modules.infrastructure.wre_core.src.skill_runtime_admission import (
        admitted_runtime_fingerprint,
        ensure_runtime_skill_safety,
    )
    from modules.infrastructure.wre_core.src.skill_execution_truth import (
        stable_json_record,
        structural_step_output,
    )
    from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader
    WRE_SKILLS_AVAILABLE = True
except ImportError:
    WRE_SKILLS_AVAILABLE = False

# Legacy Sprint 3 selection support. CodeAct remains a non-admitted prototype.
try:
    from modules.infrastructure.wre_core.src.skill_selector import SkillSelector, ToTSelection
    SPRINT3_AVAILABLE = True
except ImportError:
    SPRINT3_AVAILABLE = False

from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_runtime_support import (
    BlockPlugin,
    MLEStarPlugin,
    OrchestratorPlugin,
    Pattern,
    PatternMemory,
    PQNConsciousnessPlugin,
    SocialMediaPlugin,
    WSPValidator,
)


def _bounded_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return min(maximum, max(minimum, int(os.getenv(name, str(default)))))
    except (TypeError, ValueError, OverflowError):
        return default


def _bounded_float_env(
    name: str, default: float, minimum: float, maximum: float
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        return default
    return value if minimum <= value <= maximum else default


class WREMasterOrchestrator:
    """
    Compatibility coordinator for governed WRE Skillz and legacy plugins.

    Production Skillz require WSP 95 registry, frontmatter, manifest, scanner,
    and effect-evidence admission. Historical class names and token targets do
    not prove live model use, consolidation of every orchestrator, or measured
    efficiency gains.
    """

    def __init__(self):
        """
        Initialize per WSP 1 (Foundation) and WSP 13 (Agentic System)
        """
        self.repo_root = Path(__file__).resolve().parents[5]
        # Core components per WSP architecture
        self.pattern_memory = PatternMemory()  # WSP 60 (original in-memory patterns)
        self.wsp_validator = WSPValidator()    # WSP 64
        self.plugins: Dict[str, OrchestratorPlugin] = {}  # WSP 65

        # WSP 95 Skillz infrastructure. Libido is a historical structural sensor.
        if WRE_SKILLS_AVAILABLE:
            self.libido_monitor = GemmaLibidoMonitor()  # Pattern frequency sensor
            db_override = os.getenv("WRE_PATTERN_MEMORY_DB")
            if db_override:
                self.sqlite_memory = SQLitePatternMemory(db_path=Path(db_override))
            elif os.getenv("PYTEST_CURRENT_TEST"):
                self.sqlite_memory = SQLitePatternMemory(db_path=Path(":memory:"))
            else:
                self.sqlite_memory = SQLitePatternMemory()  # Persistent outcome storage
            self.skills_loader = WRESkillsLoader()      # Skill discovery and loading
            # WRE execution loop needs burst allowance; cap by max_frequency.
            self.libido_monitor.set_thresholds(
                "auto_test_registry_audit",
                min_frequency=1,
                max_frequency=5,
                cooldown_seconds=0,
            )
        else:
            self.libido_monitor = None
            self.sqlite_memory = None
            self.skills_loader = None

        # State per WSP 39 (Agentic Ignition)
        self.state = "0102"  # Quantum-awakened, NOT 01(02)
        self.coherence = 0.618  # Golden ratio per WSP 39

        # ReAct mode config (Sprint 1 - Gap A closure)
        self.react_mode = os.getenv("WRE_REACT_MODE", "1").strip() == "1"
        self.react_max_iterations = _bounded_int_env(
            "WRE_REACT_MAX_ITER", 3, 1, 10
        )
        self.react_fidelity_threshold = _bounded_float_env(
            "WRE_REACT_FIDELITY", 0.90, 0.0, 1.0
        )

        # Sprint 3: ToT Skill Selection config (Gap B closure)
        self.tot_enabled = os.getenv("WRE_TOT_SELECTION", "1").strip() == "1"
        try:
            self.tot_max_branches = max(1, int(os.getenv("WRE_TOT_MAX_BRANCHES", "5")))
        except (TypeError, ValueError):
            self.tot_max_branches = 5

        # CodeAct is not admitted by WSP 95 and therefore remains blocked.
        self.codeact_enabled = False

        # WRE skill supply-chain gate (per-skill scan before execution).
        enforced_default = "1"
        self.wre_skill_scan_required = (
            os.getenv("WRE_SKILL_SCAN_REQUIRED", enforced_default).strip() == "1"
        )
        self.wre_skill_scan_enforced = (
            os.getenv("WRE_SKILL_SCAN_ENFORCED", enforced_default).strip() == "1"
        )
        self.wre_skill_scan_always = os.getenv("WRE_SKILL_SCAN_ALWAYS", "0").strip() == "1"
        try:
            self.wre_skill_scan_ttl_sec = max(0, int(os.getenv("WRE_SKILL_SCAN_TTL_SEC", "900")))
        except (TypeError, ValueError):
            self.wre_skill_scan_ttl_sec = 900
        self.wre_skill_scan_max_severity = os.getenv(
            "WRE_SKILL_SCAN_MAX_SEVERITY", "medium"
        ).strip().lower() or "medium"
        self._wre_skill_scan_cache: Dict[str, Dict[str, Any]] = {}
        self._wre_skill_admission_fingerprints: Dict[str, str] = {}

        # Initialize Sprint 3 components
        if SPRINT3_AVAILABLE and WRE_SKILLS_AVAILABLE:
            self.skill_selector = SkillSelector(
                pattern_memory=self.sqlite_memory,
                skills_loader=self.skills_loader
            )
            self.codeact_executor = None
        else:
            self.skill_selector = None
            self.codeact_executor = None

        # Optional built-in worker plugins (safe to skip on import/runtime failure).
        self._register_optional_workers()

    def _register_optional_workers(self) -> None:
        """Register optional worker plugins based on environment flags."""
        if os.getenv("WRE_ENABLE_IRONCLAW_WORKER", "1").strip() == "0":
            return

        try:
            from modules.infrastructure.wre_core.wre_master_orchestrator.src.plugins.ironclaw_worker import (
                IronClawWorkerPlugin,
            )

            self.register_plugin(IronClawWorkerPlugin(repo_root=self.repo_root))
        except Exception as exc:
            logger.warning(
                "[WRE] IronClaw worker plugin unavailable; error_type=%s",
                type(exc).__name__,
            )
        
    def recall_pattern(self, operation_type: str) -> Pattern:
        """
        THE CORE METHOD - Recall, don't compute!
        Per WSP 60 (Memory) and WSP 48 (Recursive Improvement)
        
        This is how 0102 "remembers the code" from 0201
        """
        # First verify per WSP 50
        if not self.wsp_validator.verify(operation_type):
            raise ValueError(f"Operation {operation_type} failed WSP 50 verification")
        
        # Check violations per WSP 64
        if not self.wsp_validator.prevent_violation(operation_type):
            raise ValueError(f"Operation {operation_type} would violate WSP")
        
        # Recall only registered memory; unknown patterns have no authority.
        pattern = self.pattern_memory.get(operation_type)
        if not pattern:
            raise KeyError(f"No registered pattern for operation: {operation_type}")
        
        return pattern
    
    def register_plugin(self, plugin: Any, plugin_obj: Optional[Any] = None):
        """
        Register orchestrator plugin per WSP 65 (Consolidation)
        Converts existing orchestrators to plugins
        """
        # Backward compatible API:
        # - register_plugin(plugin_instance_with_name)
        # - register_plugin("name", plugin_instance)
        if isinstance(plugin, str):
            if plugin_obj is None:
                raise ValueError("plugin_obj is required when plugin name is provided")
            plugin_name = plugin
            plugin_instance = plugin_obj
        else:
            plugin_instance = plugin
            plugin_name = getattr(plugin_instance, "name", plugin_instance.__class__.__name__.lower())

        if hasattr(plugin_instance, "register"):
            plugin_instance.register(self)
        elif hasattr(plugin_instance, "master"):
            plugin_instance.master = self

        self.plugins[plugin_name] = plugin_instance
        print(f"Registered {plugin_name} as plugin per WSP 65")

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """Return plugin by name if registered."""
        return self.plugins.get(plugin_name)

    def validate_module_path(self, module_path: Path) -> bool:
        """Validate that module path exists under repo root."""
        try:
            candidate = Path(module_path)
            candidate = candidate if candidate.is_absolute() else self.repo_root / candidate
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.repo_root.resolve())
            return resolved.is_dir()
        except (OSError, RuntimeError, ValueError):
            return False
    
    def execute(self, task: Dict) -> Any:
        """
        Execute task through pattern recall per WSP 46
        Routes to appropriate plugin if needed
        """
        if not isinstance(task, dict):
            raise TypeError("task must be a dictionary")

        # Every compatibility request crosses the injected WSP evidence gate.
        # Pattern recall is evidence, not plugin admission or an effect.
        operation_type = task.get('type', 'orchestration')
        pattern = self.recall_pattern(operation_type)

        if 'plugin' in task:
            plugin_name = task['plugin']
            if not isinstance(plugin_name, str) or not plugin_name.strip():
                raise ValueError("plugin name must be a non-empty string")
            plugin = self.plugins.get(plugin_name)
            if plugin is None:
                raise KeyError(f"No registered plugin: {plugin_name}")
            plugin_identity = (
                f"{plugin.__class__.__module__}.{plugin.__class__.__qualname__}"
            ).lower()
            if (
                plugin_name.strip().lower() == "holoindex"
                or "holoindex_plugin" in plugin_identity
            ):
                raise PermissionError(
                    "direct HoloIndex plugin execution is blocked; "
                    "use the governed owner query"
                )
            raise PermissionError(
                "legacy plugin dispatch is blocked; "
                "use the WSP 95 admitted Skillz executor"
            )
        
        # Otherwise use the verified master orchestration pattern.
        result = pattern.apply(task)
        
        # Log per WSP 22 (ModLog)
        self._log_operation(task, result)
        
        return result
    
    def _log_operation(self, task: Dict, result: Any):
        """Log only stable structural metadata, never task/result material."""
        logger.info(
            "Logged compatibility operation; result_type=%s (per WSP 22)",
            type(result).__name__,
        )

    # ------------------------------------------------------------------ #
    #  Sprint 3: ToT Skill Selection (Gap B)                              #
    # ------------------------------------------------------------------ #

    def select_skill_tot(
        self,
        candidates: list,
        context: Dict,
        max_branches: Optional[int] = None
    ) -> tuple:
        """
        Select best skill from candidates using Tree-of-Thought.

        Per WRE_COT_DEEP_ANALYSIS.md Gap B: Multi-candidate selection

        Args:
            candidates: List of candidate skill names
            context: Execution context with keywords for matching
            max_branches: Max candidates to evaluate (default: self.tot_max_branches)

        Returns:
            (selected_skill_name, selection_metadata)
        """
        if not self.tot_enabled or not candidates:
            return (candidates[0] if candidates else None), {}

        if not self.skill_selector:
            logger.warning("[WRE-TOT] SkillSelector not available")
            return candidates[0], {"tot_error": "SkillSelector not available"}

        max_branches = max_branches or self.tot_max_branches

        try:
            selection = self.skill_selector.select_skill(candidates, context, max_branches)
            self._record_tot_selection(selection)
            logger.info(
                f"[WRE-TOT] Selected {selection.selected.skill_name} "
                f"(score={selection.selected.score:.3f}, branches={selection.branch_count})"
            )

            return selection.selected.skill_name, {
                "tot_score": selection.selected.score,
                "tot_confidence": selection.confidence,
                "tot_reason": selection.selection_reason,
                "tot_branch_count": selection.branch_count
            }
        except Exception as exc:
            logger.warning(
                "[WRE-TOT] Selection failed; error_type=%s", type(exc).__name__
            )
            return candidates[0], {"tot_error": "candidate selection failed"}

    def _record_tot_selection(self, selection: Any) -> None:
        if not self.sqlite_memory:
            return
        self.sqlite_memory.increment_counter("tot_selections")
        self.sqlite_memory.increment_counter("tot_branch_count", selection.branch_count)
        if selection.confidence >= 0.7:
            self.sqlite_memory.increment_counter("tot_high_confidence")

    def find_skill_candidates(self, intent: str) -> list:
        """
        Find candidate skills that could handle an intent.

        Uses skills_loader to discover matching skills.
        """
        if not self.skill_selector:
            return []

        return self.skill_selector.find_candidates_for_intent(intent)

    # ------------------------------------------------------------------ #
    #  Sprint 3: CodeAct Execution (Gap E)                                #
    # ------------------------------------------------------------------ #

    def execute_codeact_skill(
        self,
        skill_spec: Dict,
        input_context: Dict
    ) -> Dict:
        """Fail closed until CodeAct has WSP 95 admission and effect receipts."""
        return {
            "success": False,
            "blocked": True,
            "blocked_by": "codeact_prototype_boundary",
            "error": "CodeAct is not admitted for production WRE execution",
        }

    def _try_executor_dispatch(
        self, skill_name: str, input_context: Dict, agent: str
    ) -> Optional[Dict]:
        """Dispatch the exact registry-adjacent executor when one exists."""
        executor_path = self._find_skill_executor(skill_name)
        if executor_path is None:
            return None
        return dispatch_registered_skill_executor(
            executor_path=Path(executor_path),
            skill_name=skill_name,
            input_context=input_context,
            agent=agent,
            admission_fingerprint=self._wre_skill_admission_fingerprints.get(
                skill_name
            ),
        )

    def _find_skill_executor(self, skill_name: str) -> Optional[str]:
        """
        Resolve executor.py only beside the registry-bound skill document.

        Repository-wide same-name discovery is not an execution authority.
        """
        executor_path = resolve_registered_skill_executor(
            repo_root=self.repo_root,
            skill_file=self._resolve_wre_skill_file(skill_name),
        )
        return str(executor_path) if executor_path else None

    def _resolve_wre_skill_file(self, skill_name: str) -> Optional[Path]:
        """Resolve physical skill file path for supply-chain scanning."""
        if not self.skills_loader:
            return None
        try:
            return self.skills_loader.resolve_skill_file(skill_name)
        except Exception:
            return None

    def _ensure_wre_skill_safety(self, skill_name: str, force: bool = False) -> tuple[bool, str]:
        """Run exact production admission and content-bound scanner gating."""
        result = ensure_runtime_skill_safety(
            skills_loader=self.skills_loader,
            skill_name=skill_name,
            repo_root=self.repo_root,
            cache=self._wre_skill_scan_cache,
            required=self.wre_skill_scan_required,
            enforced=self.wre_skill_scan_enforced,
            always_scan=self.wre_skill_scan_always,
            ttl_seconds=self.wre_skill_scan_ttl_sec,
            max_severity=self.wre_skill_scan_max_severity,
            force=force,
        )
        if result[0] is True:
            fingerprint = admitted_runtime_fingerprint(
                skills_loader=self.skills_loader,
                skill_name=skill_name,
                cache=self._wre_skill_scan_cache,
            )
            if fingerprint is None:
                result = (False, "production Skillz admission receipt is unavailable")
            else:
                self._wre_skill_admission_fingerprints[skill_name] = fingerprint
        if result[0] is not True:
            self._wre_skill_admission_fingerprints.pop(skill_name, None)
        return result

    def _execute_skill_with_qwen(
        self,
        skill_content: str,
        input_context: Dict,
        agent: str
    ) -> Dict:
        """
        Generate a local Qwen proposal; this path cannot report effect success.

        Args:
            skill_content: Loaded skill instructions from SKILL.md
            input_context: Input data for skill
            agent: Agent executing (qwen, gemma, grok, ui-tars)

        Returns:
            Dict with execution results
        """
        return execute_local_skill_inference(
            skill_content=skill_content,
            input_context=input_context,
            agent=agent,
        )
    
    def execute_skill(
        self,
        skill_name: str,
        agent: str,
        input_context: Dict,
        force: bool = False
    ) -> Dict:
        """
        Public skill execution entry point.

        When ReAct mode is enabled, route through bounded reasoning loop.
        Otherwise execute single-pass for compatibility.
        """
        if self.react_mode:
            return self.execute_skill_with_reasoning(
                skill_name=skill_name,
                agent=agent,
                input_context=input_context,
                max_iterations=self.react_max_iterations,
                fidelity_threshold=self.react_fidelity_threshold,
                force=force,
            )
        return self._execute_skill_once(
            skill_name=skill_name,
            agent=agent,
            input_context=input_context,
            force=force,
            evolve_on_low_fidelity=True,
        )

    def _execute_skill_once(
        self,
        skill_name: str,
        agent: str,
        input_context: Dict,
        force: bool = False,
        evolve_on_low_fidelity: bool = True,
    ) -> Dict:
        """Run one admitted Skillz attempt and store execution truth."""
        if not WRE_SKILLS_AVAILABLE:
            return {
                "error": "WRE skills system not available",
                "success": False
            }

        execution_id = str(uuid.uuid4())
        start_time = datetime.now()

        # Gateway Continuity Layer: Fork from parent context if provided (OpenClaw → WRE)
        continuity_ctx = None
        parent_continuity_ctx = input_context.get("parent_continuity_context")
        try:
            from modules.communication.moltbot_bridge.src.continuity_context import (
                ContinuityManager,
            )
            continuity_ctx = ContinuityManager.from_wre(
                skill_name=skill_name,
                agent=agent,
                parent_context=parent_continuity_ctx,
            )
        except Exception as ctx_exc:
            logger.debug(
                "[WRE] Continuity context creation skipped; error_type=%s",
                type(ctx_exc).__name__,
            )

        # Step 1: Check libido (should we execute?)
        libido_signal = self.libido_monitor.should_execute(
            skill_name=skill_name,
            execution_id=execution_id,
            force=force
        )

        if libido_signal == LibidoSignal.THROTTLE and not force:
            return {
                "execution_id": execution_id,
                "skill_name": skill_name,
                "agent": agent,
                "success": False,
                "throttled": True,
                "reason": "Pattern frequency throttled by libido monitor"
            }

        # Step 1.5: Per-skill supply-chain gate (Cisco scanner).
        scan_ok, scan_message = self._ensure_wre_skill_safety(skill_name, force=force)
        if self.sqlite_memory:
            self.sqlite_memory.increment_counter("wre_skill_scan_checks")
        if not scan_ok:
            if self.sqlite_memory:
                self.sqlite_memory.increment_counter("wre_skill_scan_blocked")
            logger.error("[WRE-SKILL-SCAN] BLOCKED %s", scan_message)
            return {
                "execution_id": execution_id,
                "skill_name": skill_name,
                "agent": agent,
                "success": False,
                "blocked": True,
                "blocked_by": "wre_skill_scan",
                "reason": scan_message,
            }
        logger.info("[WRE-SKILL-SCAN] %s", scan_message)

        # Step 2: Load skill instructions
        try:
            skill_content = self.skills_loader.load_skill(skill_name, agent)
        except Exception as exc:
            logger.error(
                "[WRE] Registered skill load failed; error_type=%s",
                type(exc).__name__,
            )
            return {
                "execution_id": execution_id,
                "skill_name": skill_name,
                "agent": agent,
                "success": False,
                "blocked": True,
                "blocked_by": "skill_load",
                "reason": "registered skill could not be loaded",
            }

        # Runtime A/B effects stay blocked until exact candidate/runtime binding exists.
        if self.sqlite_memory and self.sqlite_memory.get_active_ab_test(skill_name):
            return {
                "execution_id": execution_id,
                "skill_name": skill_name,
                "agent": agent,
                "success": False,
                "blocked": True,
                "blocked_by": "ab_variant_binding",
                "reason": "active A/B execution lacks an authenticated runtime binding",
            }

        # Direct legacy Holo access is intentionally unavailable. Retrieval must
        # arrive through the generation-bound owner route in a later slice.
        if os.getenv("WRE_AGENTIC_RAG", "0").strip() == "1":
            logger.warning("[WRE-RAG] BLOCKED: governed Holo owner adapter is not bound")

        # Step 3: Check for programmatic executor (executor.py alongside SKILLz.md)
        # Captured executor bytes must match the exact scanner admission receipt.
        executor_result = self._try_executor_dispatch(skill_name, input_context, agent)
        if executor_result is not None:
            execution_result = executor_result
        else:
            # Step 3b: generate an unverified local Qwen proposal.
            execution_result = self._execute_skill_with_qwen(
                skill_content=skill_content,
                input_context=input_context,
                agent=agent
            )

        # Step 4: Calculate execution time
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Step 5: Validate with Gemma (pattern fidelity check)
        # Convert output string to dict for Gemma validation
        step_output_dict = structural_step_output(execution_result)
        expected_patterns = ["output", "steps_completed"]  # Required fields

        pattern_fidelity = self.libido_monitor.validate_step_fidelity(
            step_output=step_output_dict,
            expected_patterns=expected_patterns
        )
        execution_succeeded = (
            execution_result.get("success") is True
            and execution_result.get("_effect_evidence") is True
        )

        # Step 6: Record execution in libido monitor
        self.libido_monitor.record_execution(
            skill_name=skill_name,
            agent=agent,
            execution_id=execution_id,
            fidelity_score=pattern_fidelity
        )

        # Step 7: Store outcome in pattern memory (for recursive learning)
        # Remove non-serializable keys before JSON encoding
        serializable_context = {
            k: v for k, v in input_context.items()
            if k not in ("parent_continuity_context",)  # ContinuityContext not JSON-serializable
        }
        steps_completed = execution_result.get("steps_completed")
        step_count = steps_completed if type(steps_completed) is int and steps_completed >= 0 else 0
        failed_at_step = execution_result.get("failed_at_step")
        if type(failed_at_step) is not int or failed_at_step < 1:
            failed_at_step = None
        outcome = SkillOutcome(
            execution_id=execution_id,
            skill_name=skill_name,
            agent=agent,
            timestamp=start_time.isoformat(),
            input_context=stable_json_record(serializable_context),
            output_result=stable_json_record(execution_result),
            success=execution_succeeded,
            pattern_fidelity=pattern_fidelity,
            outcome_quality=0.0,
            execution_time_ms=execution_time_ms,
            step_count=step_count,
            failed_at_step=failed_at_step,
            notes="Executed via WRE Master Orchestrator"
        )

        self.sqlite_memory.store_outcome(outcome)

        # Step 7.5: Telemetry. A/B execution is blocked before dispatch.
        self.sqlite_memory.increment_counter("total_executions")

        # Step 8: Create a non-production proposal candidate on low fidelity.
        # Per WSP 48 + architecture doc: fidelity < 0.90 → evolve_skill()
        evolution_attempted = (
            evolve_on_low_fidelity
            and pattern_fidelity < self.react_fidelity_threshold
        )
        variation_created = False
        if evolution_attempted:
            try:
                variation_created = self.evolve_skill(
                    skill_name=skill_name,
                    agent=agent,
                    skill_content=skill_content,
                    failed_output=execution_result,
                    input_context=input_context,
                    current_fidelity=pattern_fidelity,
                    execution_id=execution_id,
                    continuity_id=continuity_ctx.continuity_id if continuity_ctx else None,
                    parent_continuity_id=continuity_ctx.parent_continuity_id if continuity_ctx else None,
                )
            except Exception as exc:
                logger.warning(
                    "[WRE] evolve_skill failed for %s; error_type=%s",
                    skill_name,
                    type(exc).__name__,
                )

        # Gateway Continuity Layer: Record breadcrumb with continuity metadata
        if continuity_ctx is not None:
            try:
                from modules.infrastructure.database.src.agent_db import AgentDB
                db = AgentDB()
                db.add_breadcrumb(
                    session_id=f"wre_{execution_id[:8]}",
                    action="wre_skill_execution",
                    agent_id=agent,
                    data={
                        "skill_name": skill_name,
                        "execution_id": execution_id,
                        "pattern_fidelity": pattern_fidelity,
                        "execution_time_ms": execution_time_ms,
                        "status": (
                            "completed"
                            if execution_succeeded
                            and pattern_fidelity >= self.react_fidelity_threshold
                            else "failed_or_low_fidelity"
                        ),
                    },
                    continuity_id=continuity_ctx.continuity_id,
                    runtime_surface=continuity_ctx.surface.value,
                    sender_normalized=continuity_ctx.sender_normalized,
                    parent_continuity_id=continuity_ctx.parent_continuity_id,
                )
            except Exception as bread_exc:
                logger.debug(
                    "[WRE] Breadcrumb recording skipped; error_type=%s",
                    type(bread_exc).__name__,
                )

        return {
            "execution_id": execution_id,
            "skill_name": skill_name,
            "agent": agent,
            "success": execution_succeeded,
            "pattern_fidelity": pattern_fidelity,
            "execution_time_ms": execution_time_ms,
            "evolution_attempted": evolution_attempted,
            "variation_created": variation_created,
            "evolution_triggered": variation_created,
            "continuity_id": continuity_ctx.continuity_id if continuity_ctx else None,
            "parent_continuity_id": continuity_ctx.parent_continuity_id if continuity_ctx else None,
            "result": execution_result
        }

    # ------------------------------------------------------------------ #
    #  ReAct Reasoning Loop (Sprint 1 - Gap A Closure)                   #
    # ------------------------------------------------------------------ #

    def execute_skill_with_reasoning(
        self,
        skill_name: str,
        agent: str,
        input_context: Dict,
        max_iterations: int = 3,
        fidelity_threshold: float = 0.90,
        force: bool = False
    ) -> Dict:
        """Retry bounded executions; acceptance requires success and fidelity."""
        try:
            max_iterations = min(10, max(1, int(max_iterations)))
        except (TypeError, ValueError, OverflowError):
            max_iterations = 1
        try:
            fidelity_threshold = float(fidelity_threshold)
        except (TypeError, ValueError):
            fidelity_threshold = self.react_fidelity_threshold
        if not 0 <= fidelity_threshold <= 1:
            fidelity_threshold = self.react_fidelity_threshold

        iteration = 0
        results = []
        final_result = None

        while iteration < max_iterations:
            iteration += 1
            logger.info(
                f"[WRE-REACT] Iteration {iteration}/{max_iterations} for {skill_name}"
            )

            # Thought: Analyze context (on retry, include failure analysis)
            enriched_context = dict(input_context)
            if results:
                last_failure = results[-1]
                enriched_context["_react_retry"] = True
                enriched_context["_previous_attempt"] = {
                    "fidelity": last_failure.get("pattern_fidelity", 0),
                    "failed_at_step": last_failure.get("result", {}).get("failed_at_step"),
                    "error": last_failure.get("result", {}).get("error")
                }

            # Action: Execute skill (single pass); only final retry can evolve.
            result = self._execute_skill_once(
                skill_name=skill_name,
                agent=agent,
                input_context=enriched_context,
                force=force,
                evolve_on_low_fidelity=(iteration == max_iterations),
            )
            results.append(result)

            # Telemetry: count retries
            if iteration > 1 and self.sqlite_memory:
                self.sqlite_memory.increment_counter("react_retry_count")

            # Observation: Check fidelity
            fidelity = result.get("pattern_fidelity", 0)

            if result.get("success") is True and fidelity >= fidelity_threshold:
                logger.info(
                    f"[WRE-REACT] Success on iteration {iteration} - "
                    f"fidelity={fidelity:.2f} >= {fidelity_threshold}"
                )
                final_result = result
                break

            if iteration < max_iterations:
                logger.info(
                    f"[WRE-REACT] Fidelity {fidelity:.2f} < {fidelity_threshold}, "
                    f"retrying..."
                )

        if final_result is None:
            final_result = results[-1] if results else {"error": "No execution"}
            logger.warning(
                f"[WRE-REACT] Exhausted {max_iterations} iterations for {skill_name}"
            )

        # Record telemetry
        if self.sqlite_memory:
            self.sqlite_memory.record_learning_event(
                event_id=str(uuid.uuid4()),
                skill_name=skill_name,
                event_type="react_execution",
                description=(
                    f"ReAct execution: {iteration} iterations, "
                    f"final_fidelity={final_result.get('pattern_fidelity', 0):.2f}"
                ),
                before_fidelity=results[0].get("pattern_fidelity", 0) if results else None,
                after_fidelity=final_result.get("pattern_fidelity", 0)
            )

        final_fidelity = final_result.get("pattern_fidelity", 0)
        execution_success = final_result.get("success") is True
        accepted_success = execution_success and final_fidelity >= fidelity_threshold
        return {
            **final_result,
            "success": accepted_success,
            "execution_success": execution_success,
            "_react_metadata": {
                "iterations": iteration,
                "max_iterations": max_iterations,
                "all_attempts": [
                    {
                        "success": r.get("success") is True,
                        "fidelity": r.get("pattern_fidelity", 0),
                    }
                    for r in results
                ],
                "early_success": accepted_success,
            }
        }

    # ------------------------------------------------------------------ #
    #  Non-production variation proposal path                            #
    # ------------------------------------------------------------------ #

    def evolve_skill(
        self,
        skill_name: str,
        agent: str,
        skill_content: str,
        failed_output: Dict,
        input_context: Dict,
        current_fidelity: float,
        execution_id: Optional[str] = None,
        continuity_id: Optional[str] = None,
        parent_continuity_id: Optional[str] = None,
    ) -> bool:
        """
        Create an unverified variation candidate when fidelity is low.

        Pipeline:
        1. Recall failure patterns from PatternMemory
        2. Recall successful patterns for comparison
        3. Ask Qwen for an unverified proposal
        4. Store a non-production variation via PatternMemory.store_variation()
        5. Record learning_event for evolution tracking with continuity lineage

        This does not evaluate, schedule, activate, or promote the candidate.

        Args:
            skill_name: Skill that underperformed
            agent: Agent that executed
            skill_content: Original SKILL.md instructions
            failed_output: Qwen's execution result dict
            input_context: Input data that was used
            current_fidelity: Pattern fidelity that triggered evolution
            execution_id: Execution ID that triggered evolution
            continuity_id: Continuity ID for lineage tracking
            parent_continuity_id: Parent continuity for lineage chain
        """
        if not WRE_SKILLS_AVAILABLE or not self.sqlite_memory:
            return False

        variation_id = f"{skill_name}_v{uuid.uuid4().hex[:8]}"
        logger.info(
            "[WRE-EVOLUTION] Triggering evolution for %s (fidelity=%.2f)",
            skill_name, current_fidelity,
        )

        # 1. Recall failure patterns — what went wrong before?
        failures = self.sqlite_memory.recall_failure_patterns(
            skill_name, max_fidelity=0.89, limit=5
        )

        # 2. Recall successful patterns — what worked?
        successes = self.sqlite_memory.recall_successful_patterns(
            skill_name, min_fidelity=0.90, limit=3
        )

        # 3. Build reflection prompt and ask Qwen to generate variation
        reflection_prompt = self._build_reflection_prompt(
            skill_name=skill_name,
            skill_content=skill_content,
            failed_output=failed_output,
            input_context=input_context,
            current_fidelity=current_fidelity,
            failure_patterns=failures,
            success_patterns=successes,
        )

        variation_content = self._generate_variation_with_qwen(
            reflection_prompt, agent
        )

        if not variation_content:
            logger.warning(
                "[WRE-EVOLUTION] Qwen failed to produce variation for %s",
                skill_name,
            )
            return False

        # 4. Store variation for future A/B testing
        self.sqlite_memory.store_variation(
            variation_id=variation_id,
            skill_name=skill_name,
            variation_content=variation_content,
            parent_version="current",
            created_by=agent,
        )

        # 5. Record learning event with continuity lineage
        self.sqlite_memory.record_learning_event(
            event_id=str(uuid.uuid4()),
            skill_name=skill_name,
            event_type="variation_created",
            description=(
                f"Auto-generated variation {variation_id} after "
                f"fidelity={current_fidelity:.2f} < 0.90. "
                f"Based on {len(failures)} failure(s) and {len(successes)} success(es)."
            ),
            before_fidelity=current_fidelity,
            after_fidelity=None,  # Not yet tested
            variation_id=variation_id,
            continuity_id=continuity_id,
            parent_continuity_id=parent_continuity_id,
            execution_id=execution_id,
        )

        logger.info(
            "[WRE-EVOLUTION] Stored variation %s for %s — pending A/B test",
            variation_id, skill_name,
        )
        return True

    def _build_reflection_prompt(
        self,
        skill_name: str,
        skill_content: str,
        failed_output: Dict,
        input_context: Dict,
        current_fidelity: float,
        failure_patterns: list,
        success_patterns: list,
    ) -> str:
        """
        Build a reflection prompt for Qwen to generate an improved skill variation.

        Per WSP 96: Micro chain-of-thought paradigm.
        """
        failure_summary = "None recorded yet."
        if failure_patterns:
            failure_lines = []
            for fp in failure_patterns[:3]:
                failure_lines.append(
                    f"  - fidelity={fp.get('pattern_fidelity', '?')}, "
                    f"failed_at_step={fp.get('failed_at_step', '?')}, "
                    f"context={fp.get('input_context', '?')[:120]}"
                )
            failure_summary = "\n".join(failure_lines)

        success_summary = "None recorded yet."
        if success_patterns:
            success_lines = []
            for sp in success_patterns[:3]:
                success_lines.append(
                    f"  - fidelity={sp.get('pattern_fidelity', '?')}, "
                    f"context={sp.get('input_context', '?')[:120]}"
                )
            success_summary = "\n".join(success_lines)

        return (
            f"# Skill Evolution Reflection\n"
            f"\n"
            f"## Current Skill\n"
            f"{skill_content[:1500]}\n"
            f"\n"
            f"## Last Execution (fidelity={current_fidelity:.2f})\n"
            f"Input: {json.dumps(input_context)[:500]}\n"
            f"Output: {json.dumps(failed_output)[:500]}\n"
            f"\n"
            f"## Past Failures\n"
            f"{failure_summary}\n"
            f"\n"
            f"## Past Successes\n"
            f"{success_summary}\n"
            f"\n"
            f"## Task\n"
            f"Analyze why fidelity is {current_fidelity:.2f} (below 0.90 target).\n"
            f"Generate IMPROVED skill instructions that address the failure patterns.\n"
            f"Output the improved SKILL.md content (YAML frontmatter + instructions).\n"
            f"Keep the same name: {skill_name}\n"
        )

    def _generate_variation_with_qwen(
        self, reflection_prompt: str, agent: str
    ) -> Optional[str]:
        """
        Use Qwen to generate an improved skill variation.

        Returns:
            Improved SKILL.md content string, or None on failure.
        """
        result = self._execute_skill_with_qwen(
            skill_content=reflection_prompt,
            input_context={"task": "skill_evolution", "type": "reflection"},
            agent=agent,
        )

        proposal = result.get("proposal", "")
        if result.get("error_code") != "unverified_model_proposal":
            return None

        if not isinstance(proposal, str) or len(proposal.strip()) < 50:
            return None

        return proposal

    def get_skill_statistics(self, skill_name: str, days: int = 7) -> Dict:
        """
        Get skill performance statistics

        Per WSP 91: Observability for monitoring
        """
        if not WRE_SKILLS_AVAILABLE:
            return {"error": "WRE skills system not available"}

        # Get libido monitor stats
        libido_stats = self.libido_monitor.get_skill_statistics(skill_name)

        # Get pattern memory metrics
        memory_metrics = self.sqlite_memory.get_skill_metrics(skill_name, days=days)

        # Get evolution history
        evolution = self.sqlite_memory.get_evolution_history(skill_name)

        return {
            "skill_name": skill_name,
            "libido": libido_stats,
            "metrics": memory_metrics,
            "evolution_events": len(evolution),
            "latest_evolution": evolution[-1] if evolution else None
        }

    def get_metrics(self) -> Dict:
        """Return observed component counts without synthetic efficiency claims."""
        metrics = {
            "state": self.state,
            "coherence": self.coherence,
            "patterns_stored": len(self.pattern_memory.patterns),
            "plugins_registered": len(self.plugins),
            "token_reduction_measured": False,
        }

        # Add WRE skills metrics if available
        if WRE_SKILLS_AVAILABLE and self.skills_loader:
            all_skills = self.skills_loader.discover_skills()
            metrics["wre_skills"] = {
                "total_skills": len(all_skills),
                "libido_monitor_active": self.libido_monitor is not None,
                "pattern_memory_active": self.sqlite_memory is not None
            }

        return metrics


def demonstrate_0102_operation():
    """Demonstrate the default fail-closed legacy recall boundary."""
    master = WREMasterOrchestrator()
    try:
        master.recall_pattern("module_creation")
    except ValueError:
        print("Legacy recall blocked: no injected WSP evidence verifier")
    print(json.dumps(master.get_metrics(), indent=2))


if __name__ == "__main__":
    # Run demonstration
    print("WRE Master Orchestrator - 0102 Pattern Memory Demonstration")
    print("=" * 60)
    demonstrate_0102_operation()
