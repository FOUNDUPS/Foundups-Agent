#!/usr/bin/env python3
"""
WRE Skill Trigger Mixin — DAE-embedded skill scheduling.

Lightweight mixin that any DAE can compose to fire WRE skills on a
cadence. Production Skillz are selected from the exact WRE registry by domain
and then pass the normal admission/execution-truth pipeline.

Usage:
    class MyDAE(SkillTriggerMixin):
        def __init__(self):
            self.init_skill_triggers(domain="social", cadence_minutes=15)

        async def main_loop(self):
            while True:
                await self.do_work()
                await self.fire_pending_skills()
                await asyncio.sleep(600)

WSP Compliance: WSP 27 (DAE Architecture), WSP 46 (WRE Protocol),
                WSP 77 (Agent Coordination), WSP 95 (WRE Skillz)
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillTriggerMixin:
    """
    Mixin for DAEs that want to fire WRE skills on a cadence.

    Discovers skills by domain, respects libido gating, and executes
    through the full WRE pipeline.
    """

    def init_skill_triggers(
        self,
        domain: str,
        cadence_minutes: int = 10,
        agent: str = "qwen",
        repo_root: Optional[Path] = None,
    ) -> None:
        """
        Initialize skill trigger subsystem for this DAE.

        Args:
            domain: Domain filter for skills (e.g. "social", "youtube",
                    "code_intelligence"). Matched against `domain` field
                    in SKILLz.md frontmatter.
            cadence_minutes: Minimum minutes between skill fire cycles.
            agent: Default agent for skill execution.
            repo_root: Repository root (defaults to auto-detect).
        """
        self._trigger_domain = domain
        self._trigger_cadence_s = cadence_minutes * 60
        self._trigger_agent = agent
        self._trigger_last_fire: float = 0.0
        self._trigger_repo_root = repo_root or Path(__file__).resolve().parents[4]

        # Lazy-loaded references
        self._trigger_orchestrator = None
        self._trigger_discovered_skills: List[str] = []
        self._trigger_initialized = True

        logger.info(
            "[SKILL-TRIGGER] Initialized domain=%s cadence=%dm agent=%s",
            domain, cadence_minutes, agent,
        )

    def _ensure_trigger_orchestrator(self) -> bool:
        """Lazy-init WREMasterOrchestrator (expensive, so deferred)."""
        if self._trigger_orchestrator is not None:
            return True
        try:
            from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
                WREMasterOrchestrator,
            )
            self._trigger_orchestrator = WREMasterOrchestrator()
            return True
        except Exception as exc:
            logger.warning(
                "[SKILL-TRIGGER] Failed to init orchestrator; error_type=%s",
                type(exc).__name__,
            )
            return False

    def _discover_domain_skills(self) -> List[str]:
        """Select registered production Skillz matching this DAE domain."""
        try:
            from modules.infrastructure.wre_core.skillz.wre_skills_loader import (
                WRESkillsLoader,
            )
            loader = WRESkillsLoader(repo_root=self._trigger_repo_root)
            domain_skills = loader.list_skills(
                domain=self._trigger_domain,
                promotion_state="production",
            )
            self._trigger_discovered_skills = domain_skills
            logger.info(
                "[SKILL-TRIGGER] Discovered %d skills for domain=%s: %s",
                len(domain_skills), self._trigger_domain, domain_skills,
            )
            return domain_skills
        except Exception as exc:
            logger.warning(
                "[SKILL-TRIGGER] Discovery failed; error_type=%s",
                type(exc).__name__,
            )
            return []

    def _should_fire(self) -> bool:
        """Check if enough time has elapsed since last fire cycle."""
        if not getattr(self, '_trigger_initialized', False):
            return False
        elapsed = time.monotonic() - self._trigger_last_fire
        return elapsed >= self._trigger_cadence_s

    def _trigger_context(self, extra_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        context = dict(extra_context or {})
        context.update({
            "triggered_by": f"dae_{self._trigger_domain}",
            "trigger_timestamp": datetime.now().isoformat(),
            "domain": self._trigger_domain,
        })
        return context

    def _trigger_failure(
        self, skill_name: str, exc: Exception, *, mode: str
    ) -> Dict[str, Any]:
        logger.error(
            "[SKILL-TRIGGER] %s failed for %s; error_type=%s",
            mode,
            skill_name,
            type(exc).__name__,
        )
        return {
            "skill_name": skill_name,
            "success": False,
            "error": "registered production Skillz execution failed",
        }

    async def _fire_one_skill(
        self, skill_name: str, extra_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        try:
            context = self._trigger_context(extra_context)
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self._trigger_orchestrator.execute_skill(
                    skill_name=skill_name,
                    agent=self._trigger_agent,
                    input_context=context,
                ),
            )
            if not isinstance(result, dict):
                raise TypeError("orchestrator result must be an object")
            logger.info(
                "[SKILL-TRIGGER] %s -> success=%s fidelity=%.2f",
                skill_name,
                result.get("success") is True,
                result.get("pattern_fidelity", 0.0),
            )
            return result
        except Exception as exc:
            return self._trigger_failure(skill_name, exc, mode="async execution")

    def _fire_one_skill_sync(
        self, skill_name: str, extra_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        try:
            result = self._trigger_orchestrator.execute_skill(
                skill_name=skill_name,
                agent=self._trigger_agent,
                input_context=self._trigger_context(extra_context),
            )
            if not isinstance(result, dict):
                raise TypeError("orchestrator result must be an object")
            return result
        except Exception as exc:
            return self._trigger_failure(skill_name, exc, mode="sync execution")

    async def fire_pending_skills(
        self,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute any skills due for this DAE's domain.

        Called from the DAE's main event loop. Respects cadence gating
        and libido monitoring. Returns list of execution results.

        Args:
            extra_context: Additional context to pass to each skill.

        Returns:
            List of skill execution result dicts.
        """
        if not self._should_fire():
            return []

        if not self._ensure_trigger_orchestrator():
            return []

        # Re-discover periodically (skills may be added/removed)
        skills = self._discover_domain_skills()
        if not skills:
            self._trigger_last_fire = time.monotonic()
            return []

        results = []
        logger.info(
            "[SKILL-TRIGGER] Firing %d skills for domain=%s",
            len(skills), self._trigger_domain,
        )

        for skill_name in skills:
            results.append(await self._fire_one_skill(skill_name, extra_context))

        self._trigger_last_fire = time.monotonic()
        logger.info(
            "[SKILL-TRIGGER] Cycle complete: %d/%d succeeded",
            sum(1 for r in results if r.get("success") is True), len(results),
        )
        return results

    def fire_pending_skills_sync(
        self,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Synchronous version of fire_pending_skills for non-async DAEs.
        """
        if not self._should_fire():
            return []

        if not self._ensure_trigger_orchestrator():
            return []

        skills = self._discover_domain_skills()
        if not skills:
            self._trigger_last_fire = time.monotonic()
            return []

        results = []
        logger.info(
            "[SKILL-TRIGGER] (sync) Firing %d skills for domain=%s",
            len(skills), self._trigger_domain,
        )

        for skill_name in skills:
            results.append(self._fire_one_skill_sync(skill_name, extra_context))

        self._trigger_last_fire = time.monotonic()
        return results

    def get_trigger_status(self) -> Dict[str, Any]:
        """Return trigger subsystem status for observability."""
        elapsed = time.monotonic() - getattr(self, '_trigger_last_fire', 0)
        return {
            "domain": getattr(self, '_trigger_domain', None),
            "cadence_minutes": getattr(self, '_trigger_cadence_s', 0) / 60,
            "skills_discovered": len(getattr(self, '_trigger_discovered_skills', [])),
            "skill_names": list(getattr(self, '_trigger_discovered_skills', [])),
            "seconds_since_last_fire": round(elapsed, 1),
            "orchestrator_loaded": self._trigger_orchestrator is not None,
        }
