"""
YouTube OAuth Credential Health Reporting (WSP 97 truth signaling)

Classifies OAuth refresh failures beyond "expired vs missing" and persists an
operator-visible artifact describing per-set status and effective daily quota
capacity. Stream resolver / quota selection paths can read the same classifier
so operator logs reflect real capacity, not just in-memory rotation state.

Status vocabulary (literals, not an Enum to keep JSON-friendly):
    - healthy
    - token_revoked                (user revoked grant in Google account UI)
    - token_expired_or_revoked     (invalid_grant, cause not distinguishable)
    - refresh_failed               (network / non-auth exception during refresh)
    - credential_set_unconfigured  (env or token/secret file missing)
    - no_refresh_token             (cred loaded but lacks refresh_token)
    - quota_exhausted              (exhausted this cycle, not an auth failure)

The artifact schema is documented in the generate_report() docstring.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

STATUS_HEALTHY = "healthy"
STATUS_TOKEN_REVOKED = "token_revoked"
STATUS_TOKEN_EXPIRED_OR_REVOKED = "token_expired_or_revoked"
STATUS_REFRESH_FAILED = "refresh_failed"
STATUS_UNCONFIGURED = "credential_set_unconfigured"
STATUS_NO_REFRESH_TOKEN = "no_refresh_token"
STATUS_QUOTA_EXHAUSTED = "quota_exhausted"

DEAD_STATUSES = frozenset({
    STATUS_TOKEN_REVOKED,
    STATUS_TOKEN_EXPIRED_OR_REVOKED,
    STATUS_REFRESH_FAILED,
    STATUS_UNCONFIGURED,
    STATUS_NO_REFRESH_TOKEN,
})

DAILY_QUOTA_PER_SET = 10000

SET_METADATA: Dict[int, Dict[str, str]] = {
    1: {
        "account_label": "UnDaoDu / Move2Japan",
        "browser_hint": "Chrome",
    },
    10: {
        "account_label": "FoundUps / antifaFM",
        "browser_hint": "Edge",
    },
}

_DEFAULT_REPORT_PATH = (
    Path(__file__).resolve().parent.parent / "reports" / "oauth_credential_health.json"
)


def reauth_command_for(set_id: int) -> str:
    """Exact command an operator must run to re-authorize a credential set."""
    return f"python modules/platform_integration/youtube_auth/scripts/authorize_set{set_id}.py"


def classify_refresh_error(error_msg: str) -> Tuple[str, str]:
    """
    Map a Google OAuth refresh exception message to a (status, reason) tuple.

    Google returns invalid_grant for both expired AND revoked refresh tokens
    and does not reliably distinguish the two in the error body. We classify
    as token_revoked only when the message explicitly contains 'revoked';
    otherwise we return token_expired_or_revoked so operators are told the
    truth ("we cannot tell which") rather than guessing.
    """
    msg = error_msg or ""
    lowered = msg.lower()
    if "invalid_grant" in msg:
        if "revoked" in lowered:
            return STATUS_TOKEN_REVOKED, "Refresh token revoked by user or Google"
        return (
            STATUS_TOKEN_EXPIRED_OR_REVOKED,
            "Refresh token expired or revoked (Google does not distinguish)",
        )
    return STATUS_REFRESH_FAILED, f"Refresh failed: {msg[:200]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_set_entry(
    set_id: int,
    status: str,
    reason: Optional[str] = None,
    last_checked: Optional[str] = None,
) -> Dict[str, object]:
    """Build one per-set entry for the health report."""
    meta = SET_METADATA.get(set_id, {})
    operator_action = (
        reauth_command_for(set_id) if status in DEAD_STATUSES else None
    )
    return {
        "set_id": set_id,
        "account_label": meta.get("account_label", f"Set {set_id}"),
        "browser_hint": meta.get("browser_hint", "default"),
        "status": status,
        "reason": reason,
        "operator_action": operator_action,
        "last_checked": last_checked or _now_iso(),
    }


def compute_effective_capacity(
    per_set: Iterable[Dict[str, object]],
) -> Dict[str, object]:
    """
    Summarize per-set entries into operational/dead counts and daily quota.

    Only sets with status == healthy count toward the effective daily quota;
    everything in DEAD_STATUSES is treated as dead. quota_exhausted is neither
    healthy nor permanently dead — it reduces "currently usable" capacity, but
    the set is expected to return after daily reset, so we count it separately.
    """
    per_set = list(per_set)
    total = len(per_set)
    operational: List[int] = []
    dead: List[int] = []
    exhausted: List[int] = []
    for entry in per_set:
        status = entry.get("status")
        set_id = entry.get("set_id")
        if status == STATUS_HEALTHY:
            operational.append(set_id)
        elif status == STATUS_QUOTA_EXHAUSTED:
            exhausted.append(set_id)
        elif status in DEAD_STATUSES:
            dead.append(set_id)
    return {
        "total_configured": total,
        "operational": operational,
        "dead": dead,
        "quota_exhausted_today": exhausted,
        "effective_daily_quota_estimate": len(operational) * DAILY_QUOTA_PER_SET,
    }


def write_health_report(
    per_set: Iterable[Dict[str, object]],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Persist the health report to JSON. Returns the path that was written.

    Report schema:
    {
      "generated_at": "<iso8601 utc>",
      "credential_sets": {
        "total_configured": int,
        "operational": [set_id, ...],
        "dead": [set_id, ...],
        "quota_exhausted_today": [set_id, ...],
        "effective_daily_quota_estimate": int
      },
      "per_set": [ <build_set_entry output>, ... ]
    }
    """
    per_set_list = list(per_set)
    report = {
        "generated_at": _now_iso(),
        "credential_sets": compute_effective_capacity(per_set_list),
        "per_set": per_set_list,
    }

    path = output_path or _DEFAULT_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=False)
    logger.info(f"[OAUTH-HEALTH] Wrote credential health report to {path}")
    return path


def format_capacity_log(capacity: Dict[str, object]) -> str:
    """
    Render a truthful one-line capacity message for operator logs.

    Example:
        "Effective credential capacity: 1/2 sets operational; dead=[1]; "
        "action_required=python modules/.../authorize_set1.py"
    """
    total = capacity.get("total_configured", 0)
    operational = capacity.get("operational", []) or []
    dead = capacity.get("dead", []) or []
    exhausted = capacity.get("quota_exhausted_today", []) or []

    parts = [
        f"Effective credential capacity: {len(operational)}/{total} sets operational"
    ]
    if dead:
        parts.append(f"dead={dead}")
    if exhausted:
        parts.append(f"quota_exhausted_today={exhausted}")
    if dead:
        actions = "; ".join(reauth_command_for(s) for s in dead)
        parts.append(f"action_required={actions}")
    return "; ".join(parts)


def emit_critical_reauth(set_id: int, status: str, reason: Optional[str]) -> None:
    """Emit a CRITICAL log telling the operator exactly how to reauthorize."""
    cmd = reauth_command_for(set_id)
    meta = SET_METADATA.get(set_id, {})
    label = meta.get("account_label", f"Set {set_id}")
    browser = meta.get("browser_hint", "default browser")
    logger.critical(
        f"[OAUTH-HEALTH] CRITICAL: credential set {set_id} ({label}) status={status} "
        f"reason={reason!r} -- operator must run: {cmd} (use {browser})"
    )
