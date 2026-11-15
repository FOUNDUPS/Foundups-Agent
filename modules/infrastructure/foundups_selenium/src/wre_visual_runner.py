#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRE Visual Test Runner - UI-TARS Verification Gates for Selenium Tests

Per WSP 48 (Recursive Self-Improvement), WSP 60 (Pattern Memory)

Provides visual-first test execution with verification gates:
1. Execute Selenium action
2. Capture screenshot 
3. UI-TARS visual verification
4. Store qualified outcome in the existing pattern_memory
5. Proceed or retry observation only (never replay the action)

WSP Compliance:
- WSP 48: Recursive learning from test outcomes
- WSP 60: Pattern recall for optimization
- WSP 91: Observable DAEMON steps
- WSP 96: Skills evolve based on verification

Usage:
    runner = WREVisualTestRunner(driver)
    runner.step("L3.1 Click Visibility", 
                action=lambda: click_element(driver, "#btn"),
                verify_prompt="visible visibility dialog")

UI-TARS currently localizes a described visible target; this is not a general
state/publication assertion or evidence of measured learning or promotion.
"""

import time
import uuid
import json
import logging
import platform
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Default screenshot directory
SCREENSHOT_DIR = Path("modules/infrastructure/foundups_vision/memory/screenshots")


@dataclass
class StepResult:
    """Result of a single test step."""
    name: str
    success: bool
    attempts: int
    screenshot_path: Optional[str] = None
    verify_prompt: str = ""
    execution_ms: int = 0
    error: Optional[str] = None
    verification: Dict[str, Any] = field(default_factory=dict)


class WREVisualTestRunner:
    """
    Visual-first test runner with UI-TARS verification gates.
    
    Each step:
    1. Executes action (Selenium)
    2. Waits for UI to settle
    3. Captures screenshot
    4. Asks UI-TARS to verify expected state
    5. Stores outcome in pattern_memory
    6. Proceeds or retries observation without repeating the action
    
    Use an explicit DOM callback for value assertions. Memory storage is separate
    from skill promotion or demonstrated recursive improvement.
    """
    
    def __init__(
        self,
        driver,
        skill_name: str = "wre_visual_test",
        use_uitars: bool = True,
        use_pattern_memory: bool = True
    ):
        """
        Initialize WRE Visual Test Runner.
        
        Args:
            driver: Selenium WebDriver instance
            skill_name: Skill name for pattern_memory tracking
            use_uitars: Enable visual localization (False requires explicit DOM check)
            use_pattern_memory: Store outcomes for learning
        """
        self.driver = driver
        self.skill_name = skill_name
        self.use_uitars = use_uitars
        self.use_pattern_memory = use_pattern_memory
        
        self.steps: List[StepResult] = []
        self.uitars = None
        self.memory = None
        self.last_verification: Dict[str, Any] = {}
        self._uitars_error = None
        
        # Lazy-load integrations
        if use_uitars:
            self._init_uitars()
        if use_pattern_memory:
            self._init_pattern_memory()
            
        # Ensure screenshot directory exists
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[WRE-TARS] Initialized - skill={skill_name}, "
                   f"uitars={use_uitars}, memory={use_pattern_memory}")
    
    def _init_uitars(self):
        """Initialize UI-TARS bridge."""
        try:
            from modules.infrastructure.foundups_vision.src.ui_tars_bridge import (
                create_ui_tars_bridge
            )
            self.uitars = create_ui_tars_bridge()
            logger.info("[WRE-TARS] UI-TARS bridge initialized")
        except Exception as e:
            logger.warning(f"[WRE-TARS] UI-TARS not available: {e}")
            self._uitars_error = str(e)

    def _init_pattern_memory(self):
        """Initialize pattern memory for learning."""
        try:
            from modules.infrastructure.wre_core.src.pattern_memory import (
                PatternMemory, SkillOutcome
            )
            self.memory = PatternMemory()
            self.SkillOutcome = SkillOutcome
            logger.info("[WRE-TARS] Pattern memory initialized")
        except ImportError as e:
            logger.warning(f"[WRE-TARS] Pattern memory not available: {e}")
            self.use_pattern_memory = False
    
    def step(
        self,
        name: str,
        action: Callable,
        verify_prompt: str,
        wait_after_action: float = 2.0,
        max_retries: int = 2,
        dom_verify: Optional[Callable[[], bool]] = None
    ) -> bool:
        """Execute action once, then verify before continuing.

        max_retries is the maximum observation count; it never repeats action.
        dom_verify selects an explicit read-only boolean assertion instead of
        visual localization. Only literal True passes either check.
        """
        if type(max_retries) is not int or max_retries < 1:
            raise ValueError("max_retries must be a positive observation count")
        logger.info(f"[WRE-TARS] Step: {name}; verify: {verify_prompt}")
        start_time = time.monotonic()
        screenshot_path = None
        attempts = 0
        success = False
        self.last_verification = self._evidence(verify_prompt, "none", "not_run")
        try:
            # A thrown action can already have taken effect. Never replay it here.
            if action() is False:
                raise RuntimeError("Action returned False; outcome requires owner inspection")
            for attempt in range(max_retries):
                attempts = attempt + 1
                time.sleep(wait_after_action)
                screenshot_path = self._capture_screenshot(name)
                success = self._verify(verify_prompt, dom_verify=dom_verify)
                if success or self.last_verification["status"] in {"unavailable", "error"}:
                    break
        except Exception as e:
            self.last_verification = self._evidence(
                verify_prompt, "none", "error", str(e)
            )
            logger.error(f"[WRE-TARS] Step outcome unverified: {e}")

        execution_ms = int((time.monotonic() - start_time) * 1000)
        self._record_outcome(
            step_name=name,
            verify_prompt=verify_prompt,
            success=success,
            screenshot_path=screenshot_path,
            execution_ms=execution_ms
        )
        self.steps.append(StepResult(
            name=name,
            success=success,
            attempts=attempts,
            screenshot_path=screenshot_path,
            verify_prompt=verify_prompt,
            execution_ms=execution_ms,
            error=self.last_verification.get("error"),
            verification=dict(self.last_verification)
        ))
        logger.info(f"[WRE-TARS] {name}: {self.last_verification['status']}")
        return success

    def _capture_screenshot(self, step_name: str) -> str:
        """Capture and save screenshot for verification."""
        # Sanitize step name for filename
        safe_name = step_name.replace(" ", "_").replace(".", "_")
        timestamp = int(time.time() * 1000)
        filename = f"{safe_name}_{timestamp}.png"
        path = SCREENSHOT_DIR / filename
        
        if not self.driver.save_screenshot(str(path)) or not path.is_file():
            raise RuntimeError("Screenshot capture did not produce evidence")
        logger.debug(f"  Screenshot saved: {path}")
        
        return str(path)
    
    def _evidence(self, assertion: str, method: str, status: str,
                  error: Optional[str] = None) -> Dict[str, Any]:
        """Bound an observation to its environment without persisting URL secrets."""
        url = None
        environment = {"host_os": platform.system()}
        try:
            parts = urlsplit(self.driver.current_url)
            # Query/fragment and userinfo can contain authentication material.
            host = parts.hostname or ""
            if ":" in host:
                host = f"[{host}]"
            if parts.port:
                host += f":{parts.port}"
            url = urlunsplit((parts.scheme, host, parts.path, "", ""))
        except Exception:
            pass
        try:
            capabilities = self.driver.capabilities
            for key in ("browserName", "browserVersion", "platformName"):
                value = capabilities.get(key)
                if isinstance(value, str):
                    environment[key] = value
        except Exception:
            pass
        return {"method": method, "status": status, "assertion": assertion,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "url": url, "url_scope": "scheme_host_path_only",
                "environment": environment, "error": error}

    def _verify(self, verify_prompt: str,
                dom_verify: Optional[Callable[[], bool]] = None) -> bool:
        """Run an explicit DOM check or UI-TARS localization; no implicit PASS."""
        if dom_verify is not None:
            try:
                passed = dom_verify() is True
                self.last_verification = self._evidence(
                    verify_prompt, "dom", "passed" if passed else "failed"
                )
                return passed
            except AssertionError as e:
                self.last_verification = self._evidence(verify_prompt, "dom", "failed", str(e))
            except Exception as e:
                self.last_verification = self._evidence(verify_prompt, "dom", "error", str(e))
            return False
        if self.use_uitars and self.uitars:
            try:
                import asyncio
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    pass
                else:
                    raise RuntimeError("Synchronous visual runner requires no active event loop")
                result = asyncio.run(self.uitars.verify(verify_prompt, driver=self.driver))
                passed = result.success is True
                self.last_verification = self._evidence(
                    verify_prompt, "visual_localization", "passed" if passed else "failed",
                    getattr(result, "error", None)
                )
                return passed
            except Exception as e:
                logger.warning(f"  UI-TARS verification error: {e}")
                self.last_verification = self._evidence(
                    verify_prompt, "visual_localization", "error", str(e)
                )
                return False
        self.last_verification = self._evidence(
            verify_prompt, "none", "unavailable",
            self._uitars_error or "UI-TARS unavailable or disabled; no explicit DOM assertion"
        )
        return False

    def _record_outcome(
        self,
        step_name: str,
        verify_prompt: str,
        success: bool,
        screenshot_path: Optional[str],
        execution_ms: int
    ):
        """Store outcome in pattern_memory for learning."""
        if not self.use_pattern_memory or not self.memory:
            return

        method = self.last_verification.get("method", "none")
        agent = "ui-tars" if method == "visual_localization" else method
        try:
            outcome = self.SkillOutcome(
                execution_id=str(uuid.uuid4()),
                skill_name=self.skill_name,
                agent=agent,
                timestamp=datetime.now(timezone.utc).isoformat(),
                input_context=json.dumps({
                    "step": step_name,
                    "verify_prompt": verify_prompt
                }),
                output_result=json.dumps({
                    "screenshot": screenshot_path,
                    "success": success,
                    "verification": self.last_verification
                }),
                success=success,
                pattern_fidelity=1.0 if success else 0.0,
                outcome_quality=1.0 if success else 0.0,
                execution_time_ms=execution_ms,
                step_count=len(self.steps) + 1
            )
            self.memory.store_outcome(outcome)
        except Exception as e:
            logger.warning(f"  Pattern memory error: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test run summary."""
        passed = sum(1 for s in self.steps if s.success)
        failed = len(self.steps) - passed
        
        return {
            "skill_name": self.skill_name,
            "total_steps": len(self.steps),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(self.steps) if self.steps else 0,
            "steps": [
                {
                    "name": s.name,
                    "success": s.success,
                    "attempts": s.attempts,
                    "execution_ms": s.execution_ms,
                    "screenshot_path": s.screenshot_path,
                    "error": s.error,
                    "verification": s.verification
                }
                for s in self.steps
            ]
        }
    
    def print_summary(self):
        """Print test run summary to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print(f"WRE-TARS Test Summary: {summary['skill_name']}")
        print("=" * 60)
        print(f"Steps: {summary['passed']}/{summary['total_steps']} passed "
              f"({summary['success_rate']:.0%})")
        print("-" * 60)
        
        for s in self.steps:
            status = "✅" if s.success else "❌"
            print(f"  {status} {s.name} ({s.attempts} attempts, {s.execution_ms}ms)")
        
        print("=" * 60 + "\n")


# Factory function
def create_wre_runner(
    driver,
    skill_name: str = "wre_visual_test",
    use_uitars: bool = True,
    use_pattern_memory: bool = True
) -> WREVisualTestRunner:
    """
    Create WRE Visual Test Runner instance.
    
    Args:
        driver: Selenium WebDriver
        skill_name: Skill name for tracking
        use_uitars: Enable UI-TARS verification
        use_pattern_memory: Store outcomes for learning
        
    Returns:
        Configured WREVisualTestRunner
    """
    return WREVisualTestRunner(
        driver=driver,
        skill_name=skill_name,
        use_uitars=use_uitars,
        use_pattern_memory=use_pattern_memory
    )


if __name__ == "__main__":
    # Quick test
    print("[WRE-TARS] Module loaded - ready for visual verification testing")
