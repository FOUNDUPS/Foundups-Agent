"""OpenClaw runtime telemetry and cooperative turn-cancel helpers."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("openclaw_dae")


def mark_conversation_engine(dae: Any, engine: str, detail: str = "none") -> None:
    """Record which conversation runtime produced the latest reply."""
    dae._previous_conversation_engine = dae._last_conversation_engine
    dae._previous_conversation_detail = dae._last_conversation_detail
    dae._last_conversation_engine = engine
    dae._last_conversation_detail = detail or "none"


def mark_preferred_external_status(dae: Any, status: str, detail: str = "none") -> None:
    """Record preferred external model routing status for diagnostics."""
    dae._preferred_external_last_status = (status or "unknown").strip().lower() or "unknown"
    dae._preferred_external_last_status_detail = (detail or "none").strip() or "none"
    dae._preferred_external_last_status_at = time.time()


def safe_int(value: Any) -> Optional[int]:
    """Safely coerce telemetry fields to non-negative ints."""
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else None
    except (TypeError, ValueError):
        return None


def estimate_token_count(text: str) -> int:
    """Lightweight token estimate (~4 chars/token) for providers without usage data."""
    clean = (text or "").strip()
    if not clean:
        return 0
    return max(1, int(round(len(clean) / 4.0)))


def record_token_usage(
    dae: Any,
    *,
    prompt_text: str,
    completion_text: str,
    engine: str,
    provider: str,
    model: str,
    usage: Optional[Dict[str, Any]] = None,
    source: str = "estimated",
    cost_estimate_usd: Optional[float] = None,
) -> None:
    """Store per-turn + session token telemetry for runtime diagnostics."""
    usage = usage or {}

    prompt_tokens = safe_int(usage.get("prompt_tokens"))
    completion_tokens = safe_int(usage.get("completion_tokens"))
    total_tokens = safe_int(usage.get("total_tokens"))

    if prompt_tokens is None:
        prompt_tokens = estimate_token_count(prompt_text)
    if completion_tokens is None:
        completion_tokens = estimate_token_count(completion_text)
    if total_tokens is None:
        total_tokens = prompt_tokens + completion_tokens

    cost = 0.0
    if cost_estimate_usd is not None:
        try:
            cost = max(0.0, float(cost_estimate_usd))
        except (TypeError, ValueError):
            cost = 0.0

    resolved_source = (source or "estimated").strip().lower() or "estimated"
    dae._token_usage_last_prompt_tokens = prompt_tokens
    dae._token_usage_last_completion_tokens = completion_tokens
    dae._token_usage_last_total_tokens = total_tokens
    dae._token_usage_last_engine = (engine or "unknown").strip() or "unknown"
    dae._token_usage_last_provider = (provider or "unknown").strip() or "unknown"
    dae._token_usage_last_model = (model or "unknown").strip() or "unknown"
    dae._token_usage_last_source = resolved_source
    dae._token_usage_last_cost_estimate_usd = cost
    dae._token_usage_last_at = time.time()

    dae._token_usage_session_turns += 1
    dae._token_usage_session_prompt_tokens += prompt_tokens
    dae._token_usage_session_completion_tokens += completion_tokens
    dae._token_usage_session_total_tokens += total_tokens
    dae._token_usage_session_cost_estimate_usd += cost


def get_token_usage_snapshot(dae: Any) -> Dict[str, Any]:
    """Return token telemetry snapshot for identity/monitor/status responses."""
    if dae._token_usage_last_at > 0:
        age = f"{int(max(0.0, time.time() - dae._token_usage_last_at))}s"
    else:
        age = "never"

    return {
        "last_prompt_tokens": dae._token_usage_last_prompt_tokens,
        "last_completion_tokens": dae._token_usage_last_completion_tokens,
        "last_total_tokens": dae._token_usage_last_total_tokens,
        "last_engine": dae._token_usage_last_engine,
        "last_provider": dae._token_usage_last_provider,
        "last_model": dae._token_usage_last_model,
        "last_source": dae._token_usage_last_source,
        "last_cost_estimate_usd": dae._token_usage_last_cost_estimate_usd,
        "last_age": age,
        "session_turns": dae._token_usage_session_turns,
        "session_prompt_tokens": dae._token_usage_session_prompt_tokens,
        "session_completion_tokens": dae._token_usage_session_completion_tokens,
        "session_total_tokens": dae._token_usage_session_total_tokens,
        "session_cost_estimate_usd": dae._token_usage_session_cost_estimate_usd,
    }


def build_token_usage_report(dae: Any) -> str:
    """Deterministic token spend report for operator queries."""
    snapshot = get_token_usage_snapshot(dae)
    return "\n".join(
        [
            "0102: token usage telemetry",
            (
                "- last_turn: "
                f"engine={snapshot['last_engine']} "
                f"provider={snapshot['last_provider']} "
                f"model={snapshot['last_model']} "
                f"prompt={snapshot['last_prompt_tokens']} "
                f"completion={snapshot['last_completion_tokens']} "
                f"total={snapshot['last_total_tokens']} "
                f"source={snapshot['last_source']} "
                f"cost_estimate_usd={snapshot['last_cost_estimate_usd']:.6f} "
                f"age={snapshot['last_age']}"
            ),
            (
                "- session: "
                f"turns={snapshot['session_turns']} "
                f"prompt={snapshot['session_prompt_tokens']} "
                f"completion={snapshot['session_completion_tokens']} "
                f"total={snapshot['session_total_tokens']} "
                f"cost_estimate_usd={snapshot['session_cost_estimate_usd']:.6f}"
            ),
            "- note: token counts are estimated unless provider_usage is available.",
        ]
    )


def request_turn_cancel(dae: Any, reason: str = "external_interrupt") -> None:
    """Signal cooperative cancellation for the currently executing turn."""
    dae._turn_cancel_reason = (reason or "external_interrupt").strip()
    dae._turn_cancel_event.set()
    logger.info("[OPENCLAW-DAE] Turn cancel requested | reason=%s", dae._turn_cancel_reason)


def clear_turn_cancel(dae: Any) -> None:
    """Reset cancellation signal before starting a new turn."""
    dae._turn_cancel_reason = "none"
    dae._turn_cancel_event.clear()


def is_turn_cancelled(dae: Any, point: str = "") -> bool:
    """Check whether current turn was cancelled."""
    if not dae._turn_cancel_event.is_set():
        return False
    if point:
        logger.info(
            "[OPENCLAW-DAE] Turn cancellation observed at %s | reason=%s",
            point,
            dae._turn_cancel_reason,
        )
    return True


def turn_cancelled_response() -> str:
    """User-facing response when a turn is interrupted."""
    return "0102: Interrupted. Ready for your next prompt."
