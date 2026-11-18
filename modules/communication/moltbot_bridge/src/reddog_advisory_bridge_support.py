"""Pure bounded input and formatting helpers for the RedDog advisory bridge."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def clean_history(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in value[-20:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant", "system"} and isinstance(content, str):
            cleaned.append({"role": role, "content": content[:12000]})
    return cleaned


def bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or value < minimum or value > maximum:
        return default
    return value


def bounded_temperature(value: object, default: float = 0.2) -> float:
    if not isinstance(value, (int, float)) or value < 0 or value > 2:
        return default
    return float(value)


def model_slug(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip() and len(value.strip()) <= 120:
        return value.strip()
    return default


def panel_models_with_meta(
    value: object,
    *,
    defaults: Sequence[str],
    maximum: int,
) -> tuple[list[str], bool]:
    if not isinstance(value, list):
        return list(defaults), False
    models = [
        item.strip()
        for item in value[:maximum]
        if isinstance(item, str) and item.strip() and len(item.strip()) <= 120
    ]
    return models, len(value) > maximum


def safe_review_packet_bridge_meta(
    value: object,
    *,
    protected_fields: frozenset[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items() if key not in protected_fields}


def required_target_paths(
    payload: Mapping[str, Any],
    *,
    audit_context_requested: bool,
) -> tuple[str, ...] | None:
    values = payload.get("required_target_paths")
    if isinstance(values, list) and values:
        return tuple(
            str(value)
            for value in values
            if isinstance(value, str) and value.strip()
        )
    return () if audit_context_requested else None


def redaction_telemetry(report: Any) -> dict[str, Any]:
    return {
        "required_targets_redaction_checked": report.required_targets_redaction_checked,
        "required_targets_redaction_passed": report.required_targets_redaction_passed,
        "required_targets_redaction_blocked": report.required_targets_redaction_blocked,
        "required_targets_redaction_blocked_paths": list(
            report.required_targets_redaction_blocked_paths
        ),
        "required_targets_redaction_blocked_reasons": list(
            report.required_targets_redaction_blocked_reasons
        ),
    }


def system_prompt(
    payload: Mapping[str, Any],
    *,
    default_prompt: str,
    terminal_evidence_rule: str,
) -> str:
    value = payload.get("system")
    if not isinstance(value, str) or not value.strip():
        return default_prompt
    normalized = value.strip().replace(terminal_evidence_rule, "").strip()
    limit = 6000 - len(terminal_evidence_rule) - 1
    prefix = normalized[:limit].rstrip()
    return (prefix + "\n" if prefix else "") + terminal_evidence_rule


def format_panel(
    lead_model: str,
    lead_text: str,
    panel_results: Mapping[str, str],
    synthesis: str,
) -> str:
    parts = ["## Lead (" + lead_model + ")\n\n" + lead_text.strip()]
    for model, text in panel_results.items():
        parts.append("## Critic (" + model + ")\n\n" + text.strip())
    parts.append("## Synthesis (" + lead_model + ")\n\n" + synthesis.strip())
    return "\n\n".join(parts)


def synthesis_user_prompt(
    redacted_prompt: str,
    lead_text: str,
    panel_results: Mapping[str, str],
    *,
    critic_char_limit: int,
) -> str:
    panel_text = "\n\n".join(
        (model.split("/")[-1] if "/" in model else model)
        + " critique:\n"
        + text[:critic_char_limit]
        for model, text in panel_results.items()
    )
    return (
        "Original task:\n"
        + redacted_prompt
        + "\n\nLead answer:\n"
        + lead_text[:12000]
        + "\n\nPanel critiques:\n"
        + panel_text
    )


def fusion_lead_messages(
    base_system: str,
    strict_json_contract: bool,
    history: Sequence[dict[str, str]],
    redacted_prompt: str,
) -> list[dict[str, str]]:
    lead_system = base_system + (
        "\n\nLead pass: produce the initial RedDog Architect answer. Include findings, "
        "evidence, proposed fixes, uncertainties, WSP_15 priority, and next safest step."
    )
    if strict_json_contract:
        lead_system += (
            "\nReturn only a JSON object matching the requested schema. "
            "Do not wrap it in markdown."
        )
    return [
        {"role": "system", "content": lead_system},
        *history,
        {"role": "user", "content": redacted_prompt},
    ]


def fusion_critic_messages(
    base_system: str,
    redacted_prompt: str,
    lead_text: str,
) -> list[dict[str, str]]:
    critic_system = base_system + (
        "\n\nPanel critic pass: critically review the lead answer for missing WSP_97 truth "
        "labels, missing WSP_15 scoring, unsupported evidence, weak HoloIndex retrieval, "
        "and fixes that are not actionable. For cybersecurity work, focus on identifying, "
        "preventing, or remediating issues and omit exploit details unnecessary to that "
        "defensive outcome. Start with `Challenge:` when any evidence, claim, framing, "
        "scope, or WSP_15 priority issue exists, and explicitly mention the WSP_15 priority. "
        "Start with `No material challenge:` only when the lead framing, evidence, and "
        "priority are all sound. Do not claim authority."
    )
    critic_user = (
        "Original task:\n" + redacted_prompt + "\n\nLead answer:\n" + lead_text[:16000]
    )
    return [
        {"role": "system", "content": critic_system},
        {"role": "user", "content": critic_user},
    ]


def fusion_synthesis_system(base_system: str, strict_json_contract: bool) -> str:
    if strict_json_contract:
        return base_system + (
            "\n\nSynthesis pass: resolve panel disagreement, preserve useful dissent, and return "
            "only the final strict JSON object requested by the user. Do not include markdown "
            "fences or prose outside the JSON object."
        )
    return base_system + (
        "\n\nSynthesis pass: resolve panel disagreement, preserve useful dissent, and return "
        "the best actionable WSP-compliant recommendation. The final section must be WSP_15 "
        "Priority followed by Next safest step."
    )


def fusion_success_result(**values: Any) -> dict[str, Any]:
    budget = values["budget_receipt"]
    quorum = {
        "applied": True,
        "passed": True,
        "reason": "fusion_quorum_passed",
        "missing_required_evidence": [],
        "challenging_critics": values["challenging_critics"],
        "abstaining_critics": values["abstaining_critics"],
        "lead_required": True,
        "lead_semantic_retry_count": values["lead_semantic_retry_count"],
        "critic_challenge_retry_models": values["critic_challenge_retry_models"],
        "synthesis_requires_quorum": True,
    }
    review = {
        "mode": "foundups_fusion",
        "lead_model": values["lead_model"],
        "panel_models": values["panel_models"],
        "panel_models_truncated": values["panel_models_truncated"],
        "requested_max_tokens": budget["requested_max_tokens"],
        "role_max_tokens": budget["role_max_tokens"],
        "panel_max_tokens": budget["panel_max_tokens"],
        "redacted_prompt": values["redacted_prompt"],
        "lead_excerpt": values["lead_text"][:4000],
        "panel_excerpts": {
            model: text[:3000] for model, text in values["panel_results"].items()
        },
        "synthesis_excerpt": values["synthesis"][:4000],
        "fusion_panel_quorum": quorum,
        "retry_count": values["lead_retry"].get("retry_count", 0),
        "final_retry_reason": values["lead_retry"].get("final_retry_reason"),
    }
    return {
        "ok": True,
        "reason": "ok",
        "mode": "foundups_fusion",
        "lead_model": values["lead_model"],
        "panel_models": values["panel_models"],
        "content": values["content"],
        "history": values["history"][-20:],
        "review_packet": review,
    }


__all__ = [
    "bounded_int",
    "bounded_temperature",
    "clean_history",
    "format_panel",
    "fusion_critic_messages",
    "fusion_lead_messages",
    "fusion_success_result",
    "fusion_synthesis_system",
    "model_slug",
    "panel_models_with_meta",
    "redaction_telemetry",
    "required_target_paths",
    "safe_review_packet_bridge_meta",
    "synthesis_user_prompt",
    "system_prompt",
]
