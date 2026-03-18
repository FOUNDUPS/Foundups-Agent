#!/usr/bin/env python3
"""
Social Media DAE launch script.

Extracted from `main.py` per WSP 62.
Purpose: launch the long-running social-domain skill trigger loop and expose
an honest stop hook for the broker-managed runtime surface.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import traceback
from typing import Any, Dict

logger = logging.getLogger(__name__)

_social_media_lock = threading.RLock()
_social_media_instance: Any = None
_social_media_status: Dict[str, Any] = {}


try:
    from modules.infrastructure.wre_core.src.dae_preflight import preflight_guard
except ImportError:
    def preflight_guard(name, quiet=True):
        def decorator(func):
            return func
        return decorator


class SocialMediaDAE:
    """
    Long-running social-domain DAE that fires WRE social skills on a cadence.
    """

    def __init__(self, cadence_minutes: int = 15):
        self.cadence_minutes = cadence_minutes
        self.active = False
        self._stop_event: asyncio.Event | None = None

        try:
            from modules.infrastructure.wre_core.src.skill_trigger import SkillTriggerMixin

            self._trigger_mixin = SkillTriggerMixin()
            self._trigger_mixin.init_skill_triggers(
                domain="social",
                cadence_minutes=cadence_minutes,
            )
            self._trigger_available = True
            logger.info("[SOCIAL-DAE] SkillTriggerMixin initialized (domain=social)")
        except Exception as exc:
            logger.warning("[SOCIAL-DAE] SkillTriggerMixin unavailable: %s", exc)
            self._trigger_available = False
            self._trigger_mixin = None

    async def run(self) -> None:
        self.active = True
        self._stop_event = asyncio.Event()
        logger.info(
            "[SOCIAL-DAE] Starting social media DAE (cadence=%dm)",
            self.cadence_minutes,
        )
        print(f"[SOCIAL-DAE] Running social skill triggers every {self.cadence_minutes}m")
        print("[SOCIAL-DAE] Press Ctrl+C to stop")

        cycle = 0
        while self.active:
            cycle += 1
            try:
                if self._trigger_available and self._trigger_mixin:
                    results = await self._trigger_mixin.fire_pending_skills(
                        extra_context={"cycle": cycle},
                    )
                    succeeded = sum(1 for r in results if r.get("success"))
                    total = len(results)
                    if total > 0:
                        print(
                            f"[SOCIAL-DAE] Cycle {cycle}: {succeeded}/{total} skills succeeded"
                        )
                    else:
                        logger.debug("[SOCIAL-DAE] Cycle %d: no skills due", cycle)
                else:
                    logger.debug("[SOCIAL-DAE] Cycle %d: trigger mixin unavailable", cycle)
            except Exception as exc:
                logger.error("[SOCIAL-DAE] Cycle %d error: %s", cycle, exc)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.cadence_minutes * 60,
                )
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self.active = False
        if self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()
        logger.info("[SOCIAL-DAE] Stop requested")

    def get_status(self) -> Dict[str, Any]:
        status = {"active": self.active, "domain": "social"}
        if self._trigger_available and self._trigger_mixin:
            status["triggers"] = self._trigger_mixin.get_trigger_status()
        return status


@preflight_guard("social_media_dae")
def run_social_media_dae() -> None:
    """Run the Social Media DAE as a broker-managed runtime."""
    global _social_media_instance
    print("[INFO] Starting Social Media DAE (012 Digital Twin)...")
    try:
        dae = SocialMediaDAE(cadence_minutes=15)
        with _social_media_lock:
            _social_media_instance = dae
            _social_media_status.clear()
            _social_media_status.update({"status": "starting"})
        with _social_media_lock:
            _social_media_status["status"] = "running"
        asyncio.run(dae.run())
    except KeyboardInterrupt:
        with _social_media_lock:
            _social_media_status["status"] = "stopped"
        print("\n[STOP] Social Media DAE stopped by user")
    except Exception as exc:
        with _social_media_lock:
            _social_media_status["status"] = "failed"
        print(f"[ERROR] Social Media DAE failed: {exc}")
        traceback.print_exc()
    finally:
        with _social_media_lock:
            _social_media_instance = None
            if "status" not in _social_media_status or _social_media_status["status"] == "running":
                _social_media_status["status"] = "stopped"


def stop_social_media_dae() -> Dict[str, Any]:
    """Request shutdown for the broker-managed Social Media DAE runtime."""
    with _social_media_lock:
        dae = _social_media_instance
        if dae is None:
            return {"status": "not_running"}

        dae.stop()
        _social_media_status["status"] = "stopping"
        return {"status": "stopping"}


if __name__ == "__main__":
    run_social_media_dae()
