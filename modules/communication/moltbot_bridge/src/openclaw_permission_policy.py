"""OpenClaw permission, containment, and skill-safety policy helpers."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw_dae")


SOURCE_KEYWORDS = frozenset(
    {
        "edit",
        "modify",
        "patch",
        "refactor",
        "rewrite",
        "fix",
        "change",
        "update",
        "delete",
        "remove",
        "rename",
        "move",
    }
)


def extract_file_paths(message: str) -> List[str]:
    """Extract workspace file paths from free-form command text."""
    paths: List[str] = []
    path_pattern = re.compile(
        r"""(?:["'])?"""
        r"""((?:[\w.@-]+[/\\]){1,}[\w.@-]+\.(?:py|md|json|yaml|yml|txt|toml|cfg|ini|sh|ps1))"""
        r"""(?:["'])?""",
        re.IGNORECASE,
    )
    for match in path_pattern.finditer(message):
        raw = match.group(1).replace("\\", "/")
        paths.append(raw)
    return paths


def is_source_modification(dae: Any, intent: Any) -> bool:
    """Return True when a command targets source-code modification."""
    msg_lower = intent.raw_message.lower()
    has_source_verb = any(re.search(rf"\b{kw}\b", msg_lower) for kw in SOURCE_KEYWORDS)
    file_paths = extract_file_paths(intent.raw_message)

    if has_source_verb and file_paths:
        return True

    if has_source_verb and any(
        re.search(rf"\b{kw}\b", msg_lower)
        for kw in ("module", "source", "src", "code", "implementation", "class", "function")
    ):
        return True

    return False


def resolve_autonomy_tier(dae: Any, intent: Any) -> Any:
    """Determine autonomy tier from sender authority and mutation intent."""
    if not intent.is_authorized_commander:
        return dae.AutonomyTier.ADVISORY

    if intent.category in (
        dae.IntentCategory.QUERY,
        dae.IntentCategory.MONITOR,
        dae.IntentCategory.CONVERSATION,
    ):
        return dae.AutonomyTier.METRICS

    if intent.category == dae.IntentCategory.SOCIAL:
        return dae.AutonomyTier.METRICS

    if intent.category in (dae.IntentCategory.COMMAND, dae.IntentCategory.SYSTEM):
        if dae.permissions is None:
            return dae.AutonomyTier.ADVISORY
        if is_source_modification(dae, intent):
            return dae.AutonomyTier.SOURCE
        return dae.AutonomyTier.DOCS_TESTS

    if intent.category == dae.IntentCategory.SCHEDULE:
        return dae.AutonomyTier.METRICS

    return dae.AutonomyTier.ADVISORY


def check_source_permission(dae: Any, intent: Any) -> tuple[bool, str]:
    """Check SOURCE-tier write permission via AgentPermissionManager."""
    if dae.permissions is None:
        logger.warning(
            "[OPENCLAW-DAE] [PERMISSION] SOURCE tier blocked: permission manager not loaded (fail-closed)"
        )
        return False, "permission manager unavailable"

    try:
        file_paths = extract_file_paths(intent.raw_message)

        if file_paths:
            for fpath in file_paths:
                result = dae.permissions.check_permission(
                    agent_id="openclaw",
                    operation="write",
                    file_path=fpath,
                )
                if not result.allowed:
                    logger.warning(
                        "[OPENCLAW-DAE] [PERMISSION] SOURCE denied for file %s: %s",
                        fpath,
                        result.reason,
                    )
                    return False, f"file '{fpath}': {result.reason}"

            logger.info(
                "[OPENCLAW-DAE] [PERMISSION] SOURCE granted for files: %s",
                file_paths,
            )
            return True, f"granted for {len(file_paths)} file(s)"

        result = dae.permissions.check_permission(
            agent_id="openclaw",
            operation="write",
            file_path=None,
        )
        if not result.allowed:
            logger.warning(
                "[OPENCLAW-DAE] [PERMISSION] SOURCE tier denied: %s",
                result.reason,
            )
            return False, result.reason
        return True, "granted (general write access)"
    except Exception as exc:
        logger.error(
            "[OPENCLAW-DAE] [PERMISSION] SOURCE check failed (fail-closed): %s",
            exc,
        )
        return False, f"permission check error: {exc}"


def emit_to_overseer(
    dae: Any,
    event_type: str,
    sender: str,
    channel: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit security event to AI Overseer correlator."""
    try:
        from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
            AIIntelligenceOverseer,
        )

        if not hasattr(dae, "_overseer") or dae._overseer is None:
            dae._overseer = AIIntelligenceOverseer(dae.repo_root)
        dae._overseer.ingest_security_event(
            event_type=event_type,
            sender=sender,
            channel=channel,
            details=details,
        )
    except Exception as exc:
        logger.debug("[OPENCLAW-DAE] Failed to emit to overseer: %s", exc)


def emit_permission_denied_event(dae: Any, intent: Any, tier: Any, reason: str) -> None:
    """Emit deduped permission-denied alert."""
    now = time.time()
    dedupe_key = f"perm_denied|{intent.sender}|{tier.value}|{reason}"

    if not hasattr(dae, "_permission_denied_history"):
        dae._permission_denied_history = {}

    last_seen = dae._permission_denied_history.get(dedupe_key)
    if last_seen and (now - last_seen) < 60:
        return

    dae._permission_denied_history[dedupe_key] = now
    expired = [
        key
        for key, ts in dae._permission_denied_history.items()
        if (now - ts) > 60
    ]
    for key in expired:
        dae._permission_denied_history.pop(key, None)

    logger.warning(
        "[DAEMON][OPENCLAW-PERMISSION] event=permission_denied tier=%s sender=%s reason=%s",
        tier.value,
        intent.sender,
        reason,
    )
    emit_to_overseer(
        dae,
        event_type="permission_denied",
        sender=intent.sender,
        channel=intent.channel,
        details={"tier": tier.value, "reason": reason},
    )


def check_permission_gate(dae: Any, intent: Any, tier: Any) -> bool:
    """Verify resolved autonomy tier against permission policy."""
    if tier == dae.AutonomyTier.ADVISORY:
        return True

    if not intent.is_authorized_commander and tier != dae.AutonomyTier.ADVISORY:
        logger.warning(
            "[OPENCLAW-DAE] [PERMISSION] Non-commander attempted %s tier",
            tier.value,
        )
        return False

    if tier == dae.AutonomyTier.SOURCE:
        granted, reason = check_source_permission(dae, intent)
        if not granted:
            emit_permission_denied_event(dae, intent, tier, reason)
            return False

    logger.info(
        "[OPENCLAW-DAE] [PERMISSION] Granted tier=%s for sender=%s",
        tier.value,
        intent.sender,
    )
    return True


def check_containment(dae: Any, sender: str, channel: str) -> Optional[Dict[str, Any]]:
    """Check if sender or channel is under containment."""
    try:
        from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
            AIIntelligenceOverseer,
        )

        if not hasattr(dae, "_overseer") or dae._overseer is None:
            dae._overseer = AIIntelligenceOverseer(dae.repo_root)
        return dae._overseer.check_containment(sender, channel)
    except Exception as exc:
        logger.debug("[OPENCLAW-DAE] Containment check failed: %s", exc)
        return None


def ensure_skill_safety(dae: Any, force: bool = False) -> bool:
    """Run cached Cisco skill scan for OpenClaw workspace skills."""
    now = time.time()
    if (
        not force
        and not dae._skill_scan_always
        and dae._skill_scan_checked_at > 0
        and (now - dae._skill_scan_checked_at) < dae._skill_scan_ttl_sec
    ):
        return dae._skill_scan_ok

    try:
        from .skill_safety_guard import run_skill_scan
    except Exception as exc:
        dae._skill_scan_checked_at = now
        dae._skill_scan_ok = not dae._skill_scan_required
        dae._skill_scan_message = f"skill safety guard unavailable: {exc}"
        return dae._skill_scan_ok

    skills_dir = dae.repo_root / "modules/communication/moltbot_bridge/workspace/skills"
    report_dir = dae.repo_root / "modules/communication/moltbot_bridge/reports"
    result = run_skill_scan(
        skills_dir=skills_dir,
        max_severity=dae._skill_scan_max_severity,
        report_dir=report_dir,
    )
    dae._skill_scan_checked_at = now

    if not result.available:
        dae._skill_scan_ok = not dae._skill_scan_required
        dae._skill_scan_message = result.message
        return dae._skill_scan_ok

    dae._skill_scan_ok = result.passed or (not dae._skill_scan_enforced)
    dae._skill_scan_message = result.message
    return dae._skill_scan_ok
