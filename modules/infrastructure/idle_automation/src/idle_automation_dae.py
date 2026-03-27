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

Idle Automation DAE - Autonomous Background Tasks
WSP-Compliant: WSP 27 (DAE Architecture), WSP 35 (Module Execution Automation)
Integrates with YouTube DAE idle loops for automatic Git + Social Media operations
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IdleAutomationDAE:
    """
    WSP 27 DAE: Idle Automation for autonomous background operations.

    Phases per WSP 27:
    -1: Signal - Idle state detection from YouTube DAE
     0: Knowledge - Git status, network connectivity, system state
     1: Protocol - Task execution with safety checks
     2: Agentic - Autonomous decision making and optimization
    """

    def __init__(self):
        """Initialize Idle Automation DAE with WSP 60 memory architecture."""
        logger.info("[ROCKET] Initializing Idle Automation DAE (WSP 27/35 compliant)")

        self.module_path = Path(__file__).parent.parent
        self.memory_path = self.module_path / "memory"
        self.memory_path.mkdir(exist_ok=True)

        # WSP 60: Load persistent state
        self.idle_state = self._load_idle_state()
        self.execution_history = self._load_execution_history()

        # Configuration from environment (WSP 70) with validation
        self.config = self._load_and_validate_config()

        # WSP 48: WRE integration for recursive improvement
        self._setup_wre_integration()

        logger.info("[OK] Idle Automation DAE initialized")
        logger.info(f"   Auto Git Push: {self.config['auto_git_push']}")
        logger.info(f"   Auto LinkedIn: {self.config['auto_linkedin_post']}")
        logger.info(f"   Auto Self Research: {self.config['auto_self_research']}")
        logger.info(f"   Health Score: {self.idle_state.get('health_score', 'N/A')}")

    def _load_idle_state(self) -> Dict[str, Any]:
        """Load persistent idle state (WSP 60) with backup recovery."""
        state_file = self.memory_path / "idle_state.json"
        backup_file = self.memory_path / "idle_state.backup.json"

        # Try primary file first
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    logger.debug("[OK] Loaded idle state from primary file")
                    # Create backup on successful load
                    self._create_backup(state)
                    return state
            except Exception as e:
                logger.warning(f"[FAIL] Failed to load primary idle state: {e}")
                # Try backup file
                if backup_file.exists():
                    try:
                        with open(backup_file, 'r') as f:
                            state = json.load(f)
                            logger.info("[OK] Recovered idle state from backup file")
                            return state
                    except Exception as backup_e:
                        logger.error(f"[FAIL] Backup file also corrupted: {backup_e}")

        # Default state with validation
        default_state = {
            "last_idle_execution": None,
            "last_git_push": None,
            "last_linkedin_post": None,
            "execution_count_today": 0,
            "last_reset_date": datetime.now().date().isoformat(),
            "idle_session_count": 0,
            "circuit_breaker_reset": datetime.now().isoformat(),
            "health_score": 100,  # 0-100 health metric
        }

        logger.info("[U+1F3D7]️ Initialized default idle state")
        return default_state

    def _create_backup(self, state: Dict[str, Any]):
        """Create backup of idle state (WSP 60)."""
        backup_file = self.memory_path / "idle_state.backup.json"
        try:
            with open(backup_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.debug(f"Failed to create backup: {e}")

    def _save_idle_state(self):
        """Save idle state persistently (WSP 60) with atomic writes."""
        state_file = self.memory_path / "idle_state.json"
        temp_file = self.memory_path / "idle_state.tmp.json"

        try:
            # Write to temporary file first (atomic operation)
            with open(temp_file, 'w') as f:
                json.dump(self.idle_state, f, indent=2, default=str)

            # Atomic move to final location
            import shutil
            shutil.move(str(temp_file), str(state_file))

            # Create backup after successful save
            self._create_backup(self.idle_state)

            logger.debug("[OK] Idle state saved successfully")

        except Exception as e:
            logger.error(f"[FAIL] Failed to save idle state: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    def _load_execution_history(self) -> list:
        """Load execution history for telemetry (WSP 60)."""
        history_file = self.memory_path / "execution_history.jsonl"

        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    return [json.loads(line) for line in f if line.strip()]
            except Exception as e:
                logger.warning(f"Failed to load execution history: {e}")

        return []

    def _log_execution(self, task_type: str, success: bool, details: Dict[str, Any]):
        """Log execution for telemetry and WRE learning (WSP 48)."""
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "success": success,
            "details": details,
            "idle_session": self.idle_state.get("idle_session_count", 0),
        }

        # Add to memory
        self.execution_history.append(execution_record)

        # Keep only last 1000 records
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]

        # Save to disk
        history_file = self.memory_path / "execution_history.jsonl"
        try:
            with open(history_file, 'a') as f:
                f.write(json.dumps(execution_record) + "\n")
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")

        # WSP 48: Report to WRE for learning
        if hasattr(self, 'wre_integration') and self.wre_integration:
            try:
                if success:
                    self.wre_integration.record_success(task_type, details)
                else:
                    self.wre_integration.record_error(task_type, details)
            except Exception as e:
                logger.debug(f"WRE integration failed: {e}")

    def _setup_wre_integration(self):
        """Setup WSP 48 WRE integration for recursive improvement."""
        try:
            from modules.infrastructure.wre_core.recursive_improvement.src.wre_integration import (
                record_error, record_success, get_optimized_approach
            )
            self.wre_integration = type('WREIntegration', (), {
                'record_error': record_error,
                'record_success': record_success,
                'get_optimized': get_optimized_approach,
            })()
            logger.info("[0102] WRE recursive improvement connected")
        except Exception as e:
            logger.debug(f"WRE integration not available: {e}")
            self.wre_integration = None

    def _create_continuity_context(self, parent_context=None):
        """Create continuity context for idle automation cycle (Gateway Continuity Layer).

        Args:
            parent_context: Optional parent continuity context for cross-surface lineage.
                           If provided, the idle context will be forked as a child.
        """
        try:
            from modules.communication.moltbot_bridge.src.continuity_context import (
                ContinuityManager,
            )
            return ContinuityManager.from_idle(
                task_type="idle_automation_cycle",
                parent_context=parent_context,
            )
        except Exception as e:
            logger.debug(f"[IDLE] Failed to create continuity context: {e}")
            return None

    def _record_continuity_breadcrumb(
        self,
        action: str,
        success: bool,
        details: Dict[str, Any],
    ) -> None:
        """Record a breadcrumb with continuity metadata for cross-surface tracking."""
        try:
            continuity_ctx = getattr(self, "_continuity_context", None)
            if continuity_ctx is None:
                return

            from modules.infrastructure.database.src.agent_db import AgentDB

            db = AgentDB()
            db.add_breadcrumb(
                session_id=continuity_ctx.session_id or "idle_automation",
                action=action,
                agent_id="idle_automation_dae",
                query=None,
                data={
                    "success": success,
                    "health_score": self.idle_state.get("health_score", 100),
                    **details,
                },
                continuity_id=continuity_ctx.continuity_id,
                runtime_surface=continuity_ctx.surface.value,
                sender_normalized=continuity_ctx.sender_normalized,
                parent_continuity_id=continuity_ctx.parent_continuity_id,
            )
            logger.debug(
                "[IDLE] Breadcrumb recorded | continuity_id=%s surface=%s",
                continuity_ctx.continuity_id,
                continuity_ctx.surface.value,
            )
        except Exception as e:
            logger.debug(f"[IDLE] Failed to record continuity breadcrumb: {e}")

    def _try_recover_origin_continuity(self):
        """Try to recover origin continuity from explicit triggering session.

        When idle automation runs without explicit parent_context, this attempts
        to recover continuity ONLY from an explicitly stored triggering session.

        No generic fallback is used to avoid false lineage between unrelated
        background cycles. If no triggering session was set, returns None and
        the idle cycle creates its own independent continuity root.

        Returns:
            ContinuityContext if recovery succeeds, None otherwise.
        """
        try:
            from modules.communication.moltbot_bridge.src.continuity_context import (
                ContinuityManager,
            )

            # Only recover from explicit triggering session - no fallback
            triggering_session = self.idle_state.get("last_triggering_session_id")
            if not triggering_session:
                logger.debug("[IDLE] No triggering session stored, skipping origin recovery")
                return None

            origin = ContinuityManager.resolve_origin_continuity_from_session(
                triggering_session
            )
            if origin:
                logger.debug(
                    "[IDLE] Recovered origin continuity from triggering session: %s",
                    origin.continuity_id,
                )
                # Clear triggering session after successful recovery to prevent
                # false reuse on subsequent unrelated cycles
                self.idle_state["last_triggering_session_id"] = None
                self._save_idle_state()
                return origin

            logger.debug(
                "[IDLE] Triggering session %s not found in breadcrumbs",
                triggering_session,
            )

        except Exception as e:
            logger.debug(f"[IDLE] Origin continuity recovery failed: {e}")

        return None

    def set_triggering_session(self, session_id: str) -> None:
        """Store the triggering session ID for origin recovery.

        Call this when another DAE triggers idle automation to enable
        continuity correlation on subsequent autonomous runs.
        """
        self.idle_state["last_triggering_session_id"] = session_id
        self._save_idle_state()
        logger.debug("[IDLE] Stored triggering session: %s", session_id)

    def _load_and_validate_config(self) -> Dict[str, Any]:
        """Load and validate configuration with defaults and bounds checking."""
        config = {}

        # Boolean configurations with validation
        config["auto_git_push"] = self._parse_bool_env("AUTO_GIT_PUSH", False)
        config["auto_linkedin_post"] = self._parse_bool_env("AUTO_LINKEDIN_POST", False)
        config["auto_self_research"] = self._parse_bool_env("AUTO_SELF_RESEARCH", True)

        # Numeric configurations with bounds
        config["idle_task_timeout"] = self._parse_int_env("IDLE_TASK_TIMEOUT", 300, 30, 3600)
        config["max_daily_executions"] = self._parse_int_env("MAX_DAILY_EXECUTIONS", 3, 1, 10)
        config["self_research_timeout"] = self._parse_int_env("AUTO_SELF_RESEARCH_TIMEOUT", 900, 60, 3600)

        # Health monitoring thresholds
        config["health_critical_threshold"] = 20  # Below this = critical
        config["health_warning_threshold"] = 50   # Below this = warning

        return config

    def _parse_bool_env(self, key: str, default: bool) -> bool:
        """Parse boolean environment variable with validation."""
        value = os.getenv(key, str(default).lower())
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        elif value.lower() in ('false', '0', 'no', 'off'):
            return False
        else:
            logger.warning(f"Invalid boolean value for {key}: '{value}', using default {default}")
            return default

    def _parse_int_env(self, key: str, default: int, min_val: int, max_val: int) -> int:
        """Parse integer environment variable with bounds checking."""
        try:
            value = int(os.getenv(key, str(default)))
            if value < min_val:
                logger.warning(f"Value for {key} ({value}) below minimum ({min_val}), using {min_val}")
                return min_val
            elif value > max_val:
                logger.warning(f"Value for {key} ({value}) above maximum ({max_val}), using {max_val}")
                return max_val
            return value
        except ValueError:
            logger.warning(f"Invalid integer value for {key}: '{os.getenv(key)}', using default {default}")
            return default

    def _check_daily_limits(self) -> bool:
        """Check if we've exceeded daily execution limits."""
        today = datetime.now().date().isoformat()

        # Reset counter if it's a new day
        if self.idle_state.get("last_reset_date") != today:
            self.idle_state["execution_count_today"] = 0
            self.idle_state["last_reset_date"] = today

        return self.idle_state["execution_count_today"] < self.config["max_daily_executions"]

    def _check_network_connectivity(self) -> bool:
        """Check network connectivity for Git and social media operations."""
        try:
            # Quick connectivity test
            result = subprocess.run(
                ['ping', '-n', '1', '-w', '1000', 'github.com'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_git_status(self) -> Dict[str, Any]:
        """Check Git working tree status."""
        try:
            # Check for uncommitted changes
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, check=True,
                cwd=self.module_path.parent.parent.parent  # Project root
            )

            changes = status.stdout.strip().split('\n') if status.stdout.strip() else []

            return {
                "has_changes": len(changes) > 0,
                "change_count": len(changes),
                "changes": changes[:10],  # First 10 changes
            }
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git status check failed: {e}")
            return {"has_changes": False, "error": str(e)}

    async def _execute_git_push(self) -> Dict[str, Any]:
        """Execute Git commit and push operations."""
        result = {
            "task": "git_push",
            "success": False,
            "commit_hash": None,
            "files_committed": 0,
            "duration": 0,
        }

        start_time = datetime.now()

        try:
            # Pre-conditions check
            if not self.config["auto_git_push"]:
                result["error"] = "Auto Git push disabled"
                return result

            if not self._check_network_connectivity():
                result["error"] = "No network connectivity"
                return result

            git_status = self._check_git_status()
            if not git_status.get("has_changes"):
                result["error"] = "No changes to commit"
                return result

            # Generate commit message
            commit_message = self._generate_commit_message(git_status)

            # Add all changes
            subprocess.run(['git', 'add', '.'], check=True,
                         cwd=self.module_path.parent.parent.parent)

            # Commit
            subprocess.run(['git', 'commit', '-m', commit_message], check=True,
                         cwd=self.module_path.parent.parent.parent)

            # Push
            subprocess.run(['git', 'push'], check=True,
                         cwd=self.module_path.parent.parent.parent)

            # Get commit hash
            commit_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, check=True,
                cwd=self.module_path.parent.parent.parent
            )

            result["success"] = True
            result["commit_hash"] = commit_result.stdout.strip()
            result["files_committed"] = git_status["change_count"]
            result["commit_message"] = commit_message

            # Update state
            self.idle_state["last_git_push"] = datetime.now().isoformat()

        except subprocess.CalledProcessError as e:
            result["error"] = f"Git operation failed: {e}"
        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
        finally:
            result["duration"] = (datetime.now() - start_time).total_seconds()

        return result

    async def _execute_linkedin_post(self, git_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LinkedIn posting using GitLinkedInBridge - IMPROVED VERSION."""
        result = {
            "task": "linkedin_post",
            "success": False,
            "post_content": None,
            "duration": 0,
            "circuit_breaker_tripped": False,
        }

        start_time = datetime.now()

        try:
            # Pre-conditions check with circuit breaker
            if not self.config["auto_linkedin_post"]:
                result["error"] = "Auto LinkedIn posting disabled"
                return result

            # Check circuit breaker for LinkedIn failures
            recent_failures = [e for e in self.execution_history[-10:]
                             if e.get("details", {}).get("linkedin_success") == False]
            if len(recent_failures) >= 3:
                result["circuit_breaker_tripped"] = True
                result["error"] = f"Circuit breaker: {len(recent_failures)} recent failures"
                return result

            # Git success is now optional - can post independently
            if not git_result.get("success"):
                logger.info("[U+26A0]️ Git push failed but proceeding with LinkedIn post")

            # Import and use GitLinkedInBridge with error handling
            from modules.platform_integration.linkedin_agent.src.git_linkedin_bridge import GitLinkedInBridge

            bridge = GitLinkedInBridge(company_id="foundups")

            # Get recent commits (with fallback to last known commit)
            commits = bridge.get_recent_commits(1)
            if not commits:
                # Fallback: use the commit from git_result if available
                if git_result.get("commit_hash"):
                    commits = [{
                        "hash": git_result["commit_hash"],
                        "subject": git_result.get("commit_message", "Recent changes"),
                        "body": "",
                        "timestamp": int(datetime.now().timestamp())
                    }]
                else:
                    result["error"] = "No commits available for posting"
                    return result

            # Generate LinkedIn content
            content = bridge.generate_linkedin_content(commits)

            # POSTING DISABLED FOR SAFETY - Only prepare content
            # TODO: Re-enable when safety mechanisms are fully tested
            logger.info("[NOTE] LinkedIn content prepared (posting disabled for safety)")
            logger.debug(f"Content preview: {content[:100]}...")

            result["success"] = True
            result["post_content"] = content
            result["commit_info"] = commits[0] if commits else None

            # Update state
            self.idle_state["last_linkedin_post"] = datetime.now().isoformat()

        except Exception as e:
            result["error"] = f"LinkedIn posting failed: {e}"
            logger.warning(f"LinkedIn operation failed: {e}")
        finally:
            result["duration"] = (datetime.now() - start_time).total_seconds()

        return result

    def _update_health_score(self, git_result: Dict[str, Any], linkedin_result: Dict[str, Any]):
        """Update system health score based on execution results."""
        current_health = self.idle_state.get("health_score", 100)

        # Calculate health impact
        health_change = 0

        # Git operations are critical (+/- 10 points)
        if git_result["success"]:
            health_change += 2  # Small positive for success
        else:
            health_change -= 10  # Large penalty for git failure

        # LinkedIn operations are secondary (+/- 5 points)
        if linkedin_result["success"]:
            health_change += 1
        elif linkedin_result.get("circuit_breaker_tripped"):
            health_change -= 2  # Moderate penalty for circuit breaker
        else:
            health_change -= 5  # Penalty for failure

        # Duration penalties (slow operations = unhealthy)
        total_duration = git_result.get("duration", 0) + linkedin_result.get("duration", 0)
        if total_duration > 60:  # Over 1 minute is slow
            health_change -= 5
        elif total_duration > 30:  # Over 30 seconds is concerning
            health_change -= 2

        # Apply health change with bounds (0-100)
        new_health = max(0, min(100, current_health + health_change))

        # Log significant health changes
        if abs(health_change) >= 5:
            level = "INFO" if health_change > 0 else "WARNING"
            logger.log(getattr(logging, level),
                      f"[U+1F3E5] Health score: {current_health} -> {new_health} ({health_change:+d})")

        self.idle_state["health_score"] = new_health

        # Trigger recovery actions for critical health
        if new_health < self.config["health_critical_threshold"]:
            logger.error("[ALERT] CRITICAL: Health score critically low, triggering recovery")
            self._trigger_critical_recovery()
        elif new_health < self.config["health_warning_threshold"]:
            logger.warning("[U+26A0]️ WARNING: Health score low, monitoring closely")

    def _trigger_critical_recovery(self):
        """Trigger critical recovery actions when health is critically low."""
        logger.info("[TOOL] Initiating critical recovery sequence")

        # Reset circuit breakers
        self.idle_state["circuit_breaker_reset"] = datetime.now().isoformat()

        # Clear execution history to remove bad patterns
        self.execution_history = self.execution_history[-10:]  # Keep only last 10

        # Reset daily counter to allow recovery attempts
        self.reset_daily_counter()

        # Force state save
        self._save_idle_state()

        logger.info("[OK] Critical recovery completed")

    def _generate_commit_message(self, git_status: Dict[str, Any]) -> str:
        """Generate contextual commit message."""
        change_count = git_status["change_count"]

        if change_count == 1:
            return "Auto-commit: 1 file updated during idle automation"
        elif change_count < 5:
            return f"Auto-commit: {change_count} files updated during idle automation"
        else:
            return f"Auto-commit: {change_count} files updated - batch changes during idle automation"

    async def _execute_pattern_training(self) -> Dict[str, Any]:
        """
        Phase 3: Execute Qwen/Gemma pattern training from 012.txt.
        Implements WRE pattern (WSP 46): Learn from 0102's operational decisions.
        """
        result = {
            "task": "pattern_training",
            "success": False,
            "patterns_stored": 0,
            "lines_processed": 0,
            "duration": 0,
        }

        start_time = datetime.now()

        try:
            # Check if training is enabled via environment variable
            training_enabled = self._parse_bool_env("AUTO_PATTERN_TRAINING", True)
            if not training_enabled:
                result["error"] = "Pattern training disabled"
                return result

            # Import pattern memory
            from holo_index.qwen_advisor.pattern_memory import PatternMemory

            # Initialize pattern memory
            pattern_memory = PatternMemory()

            # Get checkpoint - where did we stop last time?
            last_processed = pattern_memory.get_checkpoint()

            # 012.txt location
            txt_file = Path("O:/Foundups-Agent/012.txt")
            if not txt_file.exists():
                result["error"] = "012.txt not found"
                return result

            # Count total lines
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines = sum(1 for _ in f)

            # Check if there's new data to process
            if last_processed >= total_lines:
                result["error"] = f"Already processed (checkpoint: {last_processed}, total: {total_lines})"
                return result

            # Process 1000 lines per idle cycle (chunked for performance)
            chunk_size = 1000
            end_line = min(last_processed + chunk_size, total_lines)

            logger.info(f"[BOT] [TRAINING] Processing lines {last_processed}-{end_line} of 012.txt")

            # Read chunk
            lines = []
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if i > last_processed and i <= end_line:
                        lines.append((i, line.strip()))

            # Extract patterns from chunk
            patterns_found = self._extract_patterns_from_lines(lines)

            # Store patterns in ChromaDB
            for pattern in patterns_found:
                if pattern_memory.store_pattern(pattern):
                    result["patterns_stored"] += 1

            # Update checkpoint
            pattern_memory.save_checkpoint(end_line)

            result["success"] = True
            result["lines_processed"] = len(lines)
            result["progress"] = f"{end_line}/{total_lines} ({end_line/total_lines*100:.1f}%)"

            # Update idle state with training progress
            self.idle_state["last_pattern_training"] = datetime.now().isoformat()
            self.idle_state["patterns_trained_total"] = self.idle_state.get("patterns_trained_total", 0) + result["patterns_stored"]

        except Exception as e:
            result["error"] = f"Training failed: {e}"
            logger.warning(f"Pattern training error: {e}")
        finally:
            result["duration"] = (datetime.now() - start_time).total_seconds()

        return result

    async def _execute_self_research_refresh(self) -> Dict[str, Any]:
        """
        Refresh internal/external research and publish a ranked autonomous task queue.
        """
        result = {
            "task": "self_research_refresh",
            "success": False,
            "update_candidates": 0,
            "autonomous_tasks": 0,
            "duration": 0,
        }

        start_time = datetime.now()

        try:
            if not self.config["auto_self_research"]:
                result["error"] = "Self research disabled"
                return result

            from modules.infrastructure.idle_automation.src.self_research_refresh import (
                SelfResearchRefresher,
            )

            # Gateway Continuity Layer: Pass current continuity for task origin tracking
            continuity_ctx = getattr(self, "_continuity_context", None)
            origin_id = continuity_ctx.continuity_id if continuity_ctx else None

            refresher = SelfResearchRefresher(origin_continuity_id=origin_id)
            report = await asyncio.wait_for(
                asyncio.to_thread(refresher.run),
                timeout=self.config["self_research_timeout"],
            )

            result["success"] = True
            result["update_candidates"] = len(report.get("update_candidates", []))
            result["autonomous_tasks"] = len(report.get("autonomous_tasks", []))
            result["next_actions"] = report.get("next_actions", [])
            result["report_path"] = str(refresher.report_path)
            self.idle_state["last_self_research"] = datetime.now().isoformat()

        except asyncio.TimeoutError:
            result["error"] = "Self research refresh timed out"
        except Exception as e:
            result["error"] = f"Self research refresh failed: {e}"
            logger.warning(f"Self research refresh error: {e}")
        finally:
            result["duration"] = (datetime.now() - start_time).total_seconds()

        return result

    async def _execute_scheduled_routines(self) -> Dict[str, Any]:
        """
        Execute scheduled OpenClaw routines based on natural-language schedules.

        Evaluates due schedules and dispatches to existing native paths.
        Prevents duplicate immediate reruns by tracking last execution.
        """
        result = {
            "task": "scheduled_routines",
            "success": False,
            "due_count": 0,
            "executed_count": 0,
            "skipped_count": 0,
            "executed_routines": [],
            "duration": 0,
        }

        start_time = datetime.now()

        try:
            # Check if scheduled routines are enabled
            scheduled_enabled = self._parse_bool_env("AUTO_SCHEDULED_ROUTINES", True)
            if not scheduled_enabled:
                result["error"] = "Scheduled routines disabled"
                return result

            from modules.infrastructure.idle_automation.src.schedule_evaluator import (
                ScheduleEvaluator,
            )

            evaluator = ScheduleEvaluator()
            due_schedules = evaluator.get_due_schedules()
            result["due_count"] = len(due_schedules)

            if not due_schedules:
                result["success"] = True
                result["error"] = "No schedules due"
                return result

            failed_count = 0
            for spec in due_schedules:
                routine_result = await self._dispatch_scheduled_routine(spec.routine)
                success = routine_result.get("success", False)
                summary = routine_result.get("summary", "completed" if success else "failed")

                evaluator.record_execution(spec.id, success, summary)

                if success:
                    result["executed_count"] += 1
                    result["executed_routines"].append({
                        "id": spec.id,
                        "routine": spec.routine,
                        "cadence": spec.cadence,
                        "success": True,
                    })
                else:
                    failed_count += 1
                    result["skipped_count"] += 1
                    result["executed_routines"].append({
                        "id": spec.id,
                        "routine": spec.routine,
                        "cadence": spec.cadence,
                        "success": False,
                        "error": routine_result.get("error"),
                    })

            # Only report success if all due routines succeeded
            result["success"] = failed_count == 0
            result["failed_count"] = failed_count
            self.idle_state["last_scheduled_routines"] = datetime.now().isoformat()

        except ImportError:
            result["error"] = "Schedule evaluator not available"
        except Exception as e:
            result["error"] = f"Scheduled routines failed: {e}"
            logger.warning(f"Scheduled routines error: {e}")
        finally:
            result["duration"] = (datetime.now() - start_time).total_seconds()

        return result

    async def _dispatch_scheduled_routine(self, routine: str) -> Dict[str, Any]:
        """
        Dispatch a scheduled routine to its native execution path.

        Only dispatches to existing safe routines - no arbitrary command execution.
        """
        if routine == "self_research":
            # Reuse existing self-research refresh
            sr_result = await self._execute_self_research_refresh()
            return {
                "success": sr_result.get("success", False),
                "summary": f"{sr_result.get('update_candidates', 0)} candidates, {sr_result.get('autonomous_tasks', 0)} tasks",
                "error": sr_result.get("error"),
            }

        if routine == "queue_audit":
            # Run the native execution queue builder
            return await self._run_queue_audit()

        if routine == "grant_watchlist":
            # Grant watchlist is part of self-research, run targeted refresh
            return await self._run_grant_watchlist_refresh()

        return {
            "success": False,
            "error": f"Unknown routine: {routine}",
        }

    async def _run_queue_audit(self) -> Dict[str, Any]:
        """Run the OpenClaw native execution queue builder."""
        try:
            queue_script = self.module_path.parent.parent.parent / "scripts" / "build_openclaw_native_execution_queue.py"
            if not queue_script.exists():
                return {"success": False, "error": "Queue builder script not found"}

            completed = subprocess.run(
                ["python", str(queue_script)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.module_path.parent.parent.parent,
            )

            if completed.returncode == 0:
                return {
                    "success": True,
                    "summary": "Queue refreshed",
                }
            return {
                "success": False,
                "error": completed.stderr[:200] if completed.stderr else "Queue build failed",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Queue audit timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_grant_watchlist_refresh(self) -> Dict[str, Any]:
        """Run targeted grant watchlist refresh via self-research refresher."""
        try:
            from modules.infrastructure.idle_automation.src.self_research_refresh import (
                SelfResearchRefresher,
            )

            refresher = SelfResearchRefresher()
            # Run the public grant watchlist refresh method
            report = await asyncio.wait_for(
                asyncio.to_thread(refresher.refresh_grant_watchlist),
                timeout=self.config.get("self_research_timeout", 300),
            )

            # Extract counts from status snapshot
            status = report.get("status", {})
            watch_count = status.get("watch_count", 0)
            changed_count = status.get("changed_count", 0)
            error_count = status.get("error_count", 0)
            return {
                "success": report.get("refresh_success", False),
                "summary": f"Grant watchlist: {watch_count} watched, {changed_count} changed, {error_count} errors",
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Grant watchlist refresh timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_patterns_from_lines(self, lines: list) -> list:
        """
        Extract training patterns from 012.txt lines.
        Identifies Qwen decisions, priority scoring, module references.
        """
        patterns = []

        i = 0
        while i < len(lines):
            line_num, line = lines[i]

            # Pattern 1: Qwen priority scoring decisions
            if "[BOT][AI] [QWEN-SCORE]" in line:
                # Extract context (10 lines before and after)
                context_start = max(0, i - 10)
                context_end = min(len(lines), i + 20)
                context_lines = [lines[j][1] for j in range(context_start, context_end)]
                context = "\n".join(context_lines)

                # Parse score from line (format: "[BOT][AI] [QWEN-SCORE] ChannelName: 1.23")
                import re
                score_match = re.search(r'\[QWEN-SCORE\] (.+): ([\d.]+)', line)
                if score_match:
                    channel = score_match.group(1)
                    score = float(score_match.group(2))

                    pattern = {
                        "id": f"012_{line_num}_qwen_score",
                        "context": context,
                        "decision": {
                            "action": "priority_scoring",
                            "channel": channel,
                            "score": score,
                            "reasoning": "Lower score = better embedding match"
                        },
                        "outcome": {},  # Will be filled if we find result in next lines
                        "module": "modules/communication/livechat/src/qwen_youtube_integration.py",
                        "timestamp": datetime.now().isoformat(),
                        "verified": True,
                        "source": "012.txt"
                    }
                    patterns.append(pattern)

            # Pattern 2: Module paths (import statements, file references)
            elif "modules/" in line and ".py" in line:
                # Extract module reference
                import re
                module_match = re.search(r'(modules/[\w/]+/[\w]+\.py)', line)
                if module_match:
                    module_path = module_match.group(1)

                    # Get context
                    context_start = max(0, i - 5)
                    context_end = min(len(lines), i + 5)
                    context_lines = [lines[j][1] for j in range(context_start, context_end)]
                    context = "\n".join(context_lines)

                    pattern = {
                        "id": f"012_{line_num}_module_ref",
                        "context": context,
                        "decision": {
                            "action": "module_reference",
                            "module": module_path
                        },
                        "outcome": {},
                        "module": module_path,
                        "timestamp": datetime.now().isoformat(),
                        "verified": True,
                        "source": "012.txt"
                    }
                    patterns.append(pattern)

            # Pattern 3: Error patterns (ERROR, WARNING logs)
            elif "[ERROR]" in line or "[WARNING]" in line:
                # Get context
                context_start = max(0, i - 5)
                context_end = min(len(lines), i + 10)
                context_lines = [lines[j][1] for j in range(context_start, context_end)]
                context = "\n".join(context_lines)

                level = "ERROR" if "[ERROR]" in line else "WARNING"

                pattern = {
                    "id": f"012_{line_num}_error",
                    "context": context,
                    "decision": {
                        "action": "error_detected",
                        "level": level,
                        "message": line
                    },
                    "outcome": {},
                    "module": "unknown",
                    "timestamp": datetime.now().isoformat(),
                    "verified": True,
                    "source": "012.txt"
                }
                patterns.append(pattern)

            i += 1

        return patterns

    async def run_idle_tasks(self, parent_context=None) -> Dict[str, Any]:
        """
        Main entry point - execute idle automation tasks.
        Called by YouTube DAE when entering idle state.

        Args:
            parent_context: Optional parent continuity context for cross-surface lineage.
                           Pass the caller's continuity context to enable cross-surface tracking.
        """
        logger.info("[BOT] Idle Automation DAE: Executing background tasks")

        # Update idle session tracking
        self.idle_state["idle_session_count"] += 1
        self.idle_state["last_idle_execution"] = datetime.now().isoformat()

        # Gateway Continuity Layer: Create continuity context for this idle cycle
        # If no parent_context provided, try to recover from last triggering session
        effective_parent = parent_context
        if effective_parent is None:
            effective_parent = self._try_recover_origin_continuity()

        self._continuity_context = self._create_continuity_context(effective_parent)

        execution_result = {
            "session_id": self.idle_state["idle_session_count"],
            "timestamp": datetime.now().isoformat(),
            "tasks_executed": [],
            "overall_success": True,
            "duration": 0,
        }

        start_time = datetime.now()

        try:
            # Phase 0: Knowledge gathering (network, git status, limits)
            if not self._check_daily_limits():
                logger.info("⏰ Daily execution limit reached - skipping idle tasks")
                execution_result["skipped_reason"] = "daily_limit_reached"
                return execution_result

            if not self._check_network_connectivity():
                logger.info("[U+1F310] No network connectivity - skipping idle tasks")
                execution_result["skipped_reason"] = "no_network"
                return execution_result

            # Phase 1: Protocol execution (git push)
            git_result = await self._execute_git_push()
            execution_result["tasks_executed"].append(git_result)

            if git_result["success"]:
                logger.info(f"[OK] Git push successful: {git_result['commit_hash'][:8]}")
            else:
                logger.warning(f"[U+26A0]️ Git push failed: {git_result.get('error', 'Unknown error')}")
                execution_result["overall_success"] = False

            # Phase 2: Social media posting (independent of git success)
            linkedin_result = await self._execute_linkedin_post(git_result)
            execution_result["tasks_executed"].append(linkedin_result)

            if linkedin_result["success"]:
                logger.info("[OK] LinkedIn post prepared (posting disabled for safety)")
            elif linkedin_result.get("circuit_breaker_tripped"):
                logger.warning(f"[U+1F50C] Circuit breaker tripped: {linkedin_result.get('error', 'N/A')}")
            else:
                logger.info(f"ℹ️ LinkedIn posting skipped: {linkedin_result.get('error', 'N/A')}")

            # Phase 3: Qwen/Gemma Training (NEW - WRE pattern learning)
            training_result = await self._execute_pattern_training()
            execution_result["tasks_executed"].append(training_result)

            if training_result["success"]:
                logger.info(f"[BOT] Pattern training: {training_result['patterns_stored']} patterns stored")
            else:
                logger.info(f"ℹ️ Pattern training skipped: {training_result.get('error', 'N/A')}")

            # Phase 4: Self-research refresh (internal health + external opportunities)
            self_research_result = await self._execute_self_research_refresh()
            execution_result["tasks_executed"].append(self_research_result)

            if self_research_result["success"]:
                logger.info(
                    "[BOT] Self research refresh: %s candidate(s), %s task(s)",
                    self_research_result["update_candidates"],
                    self_research_result["autonomous_tasks"],
                )
            else:
                logger.info(
                    "ℹ️ Self research refresh skipped: %s",
                    self_research_result.get("error", "N/A"),
                )

            # Phase 5: Scheduled routines (natural-language schedules)
            scheduled_result = await self._execute_scheduled_routines()
            execution_result["tasks_executed"].append(scheduled_result)

            if scheduled_result["success"]:
                logger.info(
                    "[BOT] Scheduled routines: %s executed, %s skipped",
                    scheduled_result.get("executed_count", 0),
                    scheduled_result.get("skipped_count", 0),
                )
            else:
                logger.info(
                    "ℹ️ Scheduled routines skipped: %s",
                    scheduled_result.get("error", "N/A"),
                )

            # Update execution counter
            self.idle_state["execution_count_today"] += 1

            # Update health score based on execution results
            self._update_health_score(git_result, linkedin_result)

            # Log execution with enhanced telemetry
            self._log_execution(
                task_type="idle_automation_cycle",
                success=execution_result["overall_success"],
                details={
                    "git_success": git_result["success"],
                    "linkedin_success": linkedin_result["success"],
                    "circuit_breaker_tripped": linkedin_result.get("circuit_breaker_tripped", False),
                    "session_id": execution_result["session_id"],
                    "health_score": self.idle_state.get("health_score", 100),
                    "git_duration": git_result.get("duration", 0),
                    "linkedin_duration": linkedin_result.get("duration", 0),
                    "self_research_success": self_research_result.get("success", False),
                    "self_research_candidates": self_research_result.get("update_candidates", 0),
                    "scheduled_routines_success": scheduled_result.get("success", False),
                    "scheduled_routines_executed": scheduled_result.get("executed_count", 0),
                }
            )

        except Exception as e:
            logger.error(f"[FAIL] Idle automation failed: {e}")
            execution_result["overall_success"] = False
            execution_result["error"] = str(e)

            self._log_execution(
                task_type="idle_automation_cycle",
                success=False,
                details={"error": str(e)}
            )
        finally:
            execution_result["duration"] = (datetime.now() - start_time).total_seconds()
            self._save_idle_state()

            # Gateway Continuity Layer: Record breadcrumb with continuity metadata
            self._record_continuity_breadcrumb(
                action="idle_automation_cycle",
                success=execution_result["overall_success"],
                details={
                    "session_id": execution_result["session_id"],
                    "tasks_executed": len(execution_result.get("tasks_executed", [])),
                    "duration": execution_result["duration"],
                    "skipped_reason": execution_result.get("skipped_reason"),
                },
            )

        logger.info(f"[U+1F3C1] Idle automation cycle completed in {execution_result['duration']:.1f}s")
        return execution_result

    def _get_scheduled_routines_status(self) -> Dict[str, Any]:
        """Get summary of scheduled routines."""
        try:
            from modules.infrastructure.idle_automation.src.schedule_evaluator import (
                ScheduleEvaluator,
            )

            evaluator = ScheduleEvaluator()
            schedules = evaluator.list_schedules()
            due = evaluator.get_due_schedules()

            return {
                "total_count": len(schedules),
                "enabled_count": sum(1 for s in schedules if s.enabled),
                "due_count": len(due),
                "schedules": [
                    {
                        "id": s.id,
                        "phrase": s.phrase,
                        "routine": s.routine,
                        "cadence": s.cadence,
                        "enabled": s.enabled,
                        "last_run": s.last_run,
                    }
                    for s in schedules
                ],
            }
        except ImportError:
            return {"error": "Schedule evaluator not available"}
        except Exception as e:
            return {"error": str(e)}

    def get_idle_status(self) -> Dict[str, Any]:
        """Get current idle automation status (WSP 70) with health metrics."""
        health_score = self.idle_state.get("health_score", 100)
        health_status = "healthy"
        if health_score < self.config["health_critical_threshold"]:
            health_status = "critical"
        elif health_score < self.config["health_warning_threshold"]:
            health_status = "warning"

        # Get scheduled routines summary
        scheduled_info = self._get_scheduled_routines_status()

        return {
            "last_idle_execution": self.idle_state.get("last_idle_execution"),
            "last_git_push": self.idle_state.get("last_git_push"),
            "last_linkedin_post": self.idle_state.get("last_linkedin_post"),
            "last_self_research": self.idle_state.get("last_self_research"),
            "last_scheduled_routines": self.idle_state.get("last_scheduled_routines"),
            "execution_count_today": self.idle_state.get("execution_count_today", 0),
            "idle_session_count": self.idle_state.get("idle_session_count", 0),
            "auto_git_enabled": self.config["auto_git_push"],
            "auto_linkedin_enabled": self.config["auto_linkedin_post"],
            "auto_self_research_enabled": self.config["auto_self_research"],
            "auto_scheduled_routines_enabled": self._parse_bool_env("AUTO_SCHEDULED_ROUTINES", True),
            "health_score": health_score,
            "health_status": health_status,
            "circuit_breaker_reset": self.idle_state.get("circuit_breaker_reset"),
            "recent_executions": self.execution_history[-5:] if self.execution_history else [],
            "scheduled_routines": scheduled_info,
            "config": {
                "idle_task_timeout": self.config["idle_task_timeout"],
                "max_daily_executions": self.config["max_daily_executions"],
                "self_research_timeout": self.config["self_research_timeout"],
                "health_critical_threshold": self.config["health_critical_threshold"],
                "health_warning_threshold": self.config["health_warning_threshold"],
            }
        }

    def reset_daily_counter(self):
        """Reset daily execution counter (for testing)."""
        self.idle_state["execution_count_today"] = 0
        self.idle_state["last_reset_date"] = datetime.now().date().isoformat()
        self._save_idle_state()


# Convenience function for YouTube DAE integration
async def run_idle_automation(
    parent_context=None,
    triggering_session: str | None = None,
) -> Dict[str, Any]:
    """
    Convenience function for YouTube DAE integration.
    Call this from AutoModeratorDAE when entering idle state.

    Args:
        parent_context: Optional parent continuity context for cross-surface lineage.
                       Pass the caller's continuity context to enable cross-surface tracking.
                       Example: run_idle_automation(parent_context=self._continuity_context)
        triggering_session: Optional session identifier (e.g. video_id) for
                           origin recovery when no parent_context is available.
                           Stored via set_triggering_session() so the idle DAE
                           can correlate background work to the originating surface.
    """
    dae = IdleAutomationDAE()
    if triggering_session and not parent_context:
        dae.set_triggering_session(triggering_session)
    return await dae.run_idle_tasks(parent_context=parent_context)
