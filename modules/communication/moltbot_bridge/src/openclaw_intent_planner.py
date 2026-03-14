"""OpenClaw intent classification and plan construction helpers."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw_dae")


def classify_intent(
    dae: Any,
    message: str,
    sender: str,
    channel: str,
    session_key: str,
    metadata: Optional[Dict] = None,
) -> Any:
    """Classify inbound message into an OpenClaw intent."""
    msg_lower = message.lower().strip()
    metadata = metadata or {}

    def _has_keyword(text: str, keyword: str) -> bool:
        pattern = rf"\b{re.escape(keyword.lower())}\b"
        return re.search(pattern, text) is not None

    sender_lower = sender.lower()
    is_commander = any(cmd_id in sender_lower for cmd_id in dae.AUTHORIZED_COMMANDERS)
    is_direct_channel = channel in ("voice_repl", "local_repl")

    if re.match(r"^\s*(hi|hey|hello)\b", msg_lower):
        category = dae.IntentCategory.CONVERSATION
        confidence = 0.85
        extracted_task = message
        intent = dae.OpenClawIntent(
            raw_message=message,
            category=category,
            confidence=confidence,
            sender=sender,
            channel=channel,
            session_key=session_key,
            is_authorized_commander=is_commander,
            extracted_task=extracted_task,
            target_domain=dae.DOMAIN_ROUTES.get(category),
            metadata=metadata,
        )
        logger.info(
            "[OPENCLAW-DAE] Intent classified (greeting): category=%s confidence=%.2f "
            "commander=%s domain=%s",
            category.value,
            confidence,
            is_commander,
            intent.target_domain,
        )
        return intent

    if dae._is_connect_wre_request(message):
        category = dae.IntentCategory.CONVERSATION
        confidence = 0.95
        extracted_task = message
        intent = dae.OpenClawIntent(
            raw_message=message,
            category=category,
            confidence=confidence,
            sender=sender,
            channel=channel,
            session_key=session_key,
            is_authorized_commander=is_commander,
            extracted_task=extracted_task,
            target_domain=dae.DOMAIN_ROUTES.get(category),
            metadata={**metadata, "classification_method": "deterministic_connect_wre"},
        )
        logger.info(
            "[OPENCLAW-DAE] Intent classified (connect_wre): category=%s confidence=%.2f "
            "commander=%s domain=%s",
            category.value,
            confidence,
            is_commander,
            intent.target_domain,
        )
        return intent

    if is_direct_channel and (
        dae._is_model_switch_request(message)
        or dae._is_connect_wre_request(message)
        or dae._is_identity_query(message)
    ):
        category = dae.IntentCategory.CONVERSATION
        confidence = 0.9
        extracted_task = message
        intent = dae.OpenClawIntent(
            raw_message=message,
            category=category,
            confidence=confidence,
            sender=sender,
            channel=channel,
            session_key=session_key,
            is_authorized_commander=is_commander,
            extracted_task=extracted_task,
            target_domain=dae.DOMAIN_ROUTES.get(category),
            metadata={**metadata, "classification_method": "deterministic_direct_conversation"},
        )
        logger.info(
            "[OPENCLAW-DAE] Intent classified (deterministic direct): category=%s confidence=%.2f "
            "commander=%s domain=%s",
            category.value,
            confidence,
            is_commander,
            intent.target_domain,
        )
        return intent

    keyword_scores: Dict[Any, float] = {}
    for cat, keywords in dae.INTENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if _has_keyword(msg_lower, kw))
        if hits > 0:
            keyword_scores[cat] = hits / len(keywords)

    gemma_enabled = os.getenv("OPENCLAW_GEMMA_INTENT", "1") != "0"
    gemma_result = None

    if gemma_enabled and keyword_scores:
        classifier = dae._get_gemma_classifier()
        if classifier is not None:
            kw_scores_str = {cat.value: score for cat, score in keyword_scores.items()}
            gemma_result = classifier.classify(
                message=message,
                keyword_scores=kw_scores_str,
                default_category=dae.IntentCategory.CONVERSATION.value,
            )

    if gemma_result is not None and gemma_result["method"] == "gemma_hybrid":
        category_value = gemma_result["category"]
        confidence = gemma_result["confidence"]
        category = dae.IntentCategory(category_value)
        metadata["classification_method"] = "gemma_hybrid"
        metadata["gemma_scores"] = gemma_result.get("gemma_scores", {})
        metadata["classification_latency_ms"] = gemma_result.get("latency_ms", 0)

        if is_direct_channel:
            cat_kw_score = keyword_scores.get(category, 0)
            should_override = False

            if category == dae.IntentCategory.QUERY:
                should_override = cat_kw_score < 0.15 or confidence < 0.75
            elif category == dae.IntentCategory.COMMAND:
                word_count = len(msg_lower.split())
                should_override = cat_kw_score < 0.15 and confidence < 0.75 and word_count > 5
            elif category == dae.IntentCategory.SOCIAL:
                should_override = confidence < 0.75

            if should_override:
                old_cat = category.value
                category = dae.IntentCategory.CONVERSATION
                confidence = 0.6
                metadata["classification_method"] = "conversation_override"
                logger.info(
                    "[OPENCLAW-DAE] Conversation override: %s kw=%.2f conf=%.2f -> CONVERSATION",
                    old_cat,
                    cat_kw_score,
                    gemma_result["confidence"],
                )

    elif not keyword_scores:
        category = dae.IntentCategory.CONVERSATION
        confidence = 0.5
        metadata["classification_method"] = "default"
    else:
        category = max(keyword_scores, key=keyword_scores.get)
        confidence = min(keyword_scores[category] * 2.0, 1.0)
        metadata["classification_method"] = "keyword_only"

        if is_direct_channel and category == dae.IntentCategory.QUERY:
            query_kw_score = keyword_scores.get(dae.IntentCategory.QUERY, 0)
            if query_kw_score < 0.15:
                category = dae.IntentCategory.CONVERSATION
                confidence = 0.6
                metadata["classification_method"] = "conversation_override"

    extracted_task = msg_lower
    for kw in dae.INTENT_KEYWORDS.get(category, []):
        extracted_task = re.sub(
            rf"\b{re.escape(kw.lower())}\b",
            " ",
            extracted_task,
        ).strip()
    extracted_task = " ".join(extracted_task.split())

    intent = dae.OpenClawIntent(
        raw_message=message,
        category=category,
        confidence=confidence,
        sender=sender,
        channel=channel,
        session_key=session_key,
        is_authorized_commander=is_commander,
        extracted_task=extracted_task or message,
        target_domain=dae.DOMAIN_ROUTES.get(category),
        metadata=metadata,
    )

    logger.info(
        "[OPENCLAW-DAE] Intent classified: category=%s confidence=%.2f "
        "method=%s commander=%s domain=%s",
        category.value,
        confidence,
        metadata.get("classification_method", "unknown"),
        is_commander,
        intent.target_domain,
    )
    return intent


def wsp_preflight(dae: Any, intent: Any) -> bool:
    """Run WSP 50 pre-action verification."""
    if intent.category in (dae.IntentCategory.COMMAND, dae.IntentCategory.SYSTEM):
        if not intent.is_authorized_commander:
            logger.warning(
                "[OPENCLAW-DAE] [WSP-50] BLOCKED: %s intent from unauthorized sender %s",
                intent.category.value,
                intent.sender,
            )
            return False

    if intent.category in (dae.IntentCategory.SCHEDULE, dae.IntentCategory.SYSTEM):
        if dae.wre is None:
            logger.warning(
                "[OPENCLAW-DAE] [WSP-50] BLOCKED: WRE unavailable for %s",
                intent.category.value,
            )
            return False

    if intent.category == dae.IntentCategory.COMMAND and dae.wre is None:
        logger.info(
            "[OPENCLAW-DAE] [WSP-50] WRE unavailable for COMMAND - will use advisory fallback"
        )

    if intent.confidence < 0.3:
        logger.info(
            "[OPENCLAW-DAE] [WSP-50] Low confidence (%.2f) - downgrading to advisory",
            intent.confidence,
        )

    return True


def plan_execution(dae: Any, intent: Any, tier: Any) -> Any:
    """Build execution plan: route, steps, estimated cost."""
    route = intent.target_domain or "digital_twin"
    steps: List[Dict[str, Any]] = []

    if intent.category == dae.IntentCategory.QUERY:
        steps = [
            {"action": "holo_search", "input": intent.extracted_task},
            {"action": "format_response", "style": "informative"},
        ]
        est_tokens = 100
    elif intent.category == dae.IntentCategory.COMMAND:
        steps = [
            {"action": "wre_preflight", "task": intent.extracted_task},
            {"action": "wre_execute", "task": intent.extracted_task},
            {"action": "validate_output"},
            {"action": "log_outcome"},
        ]
        est_tokens = 200
    elif intent.category == dae.IntentCategory.MONITOR:
        steps = [
            {"action": "overseer_status"},
            {"action": "format_response", "style": "status_report"},
        ]
        est_tokens = 80
    elif intent.category == dae.IntentCategory.SCHEDULE:
        steps = [
            {"action": "parse_schedule", "input": intent.extracted_task},
            {"action": "check_calendar_conflicts"},
            {"action": "schedule_or_queue"},
            {"action": "confirm_response"},
        ]
        est_tokens = 150
    elif intent.category == dae.IntentCategory.SOCIAL:
        steps = [
            {"action": "route_to_communication_dae", "channel": intent.channel},
            {"action": "generate_engagement"},
        ]
        est_tokens = 120
    elif intent.category == dae.IntentCategory.SYSTEM:
        steps = [
            {"action": "verify_commander_authority"},
            {"action": "execute_system_command", "task": intent.extracted_task},
            {"action": "report_outcome"},
        ]
        est_tokens = 180
    elif intent.category == dae.IntentCategory.RESEARCH:
        steps = [
            {"action": "classify_research_sub_intent", "input": intent.extracted_task},
            {"action": "route_to_pqn_research_adapter"},
            {"action": "anti_contamination_gate"},
        ]
        est_tokens = 150
    else:
        steps = [{"action": "digital_twin_response", "context": intent.raw_message}]
        est_tokens = 60

    plan = dae.ExecutionPlan(
        intent=intent,
        route=route,
        permission_level=tier,
        wsp_preflight_passed=True,
        steps=steps,
        estimated_tokens=est_tokens,
    )

    logger.info(
        "[OPENCLAW-DAE] Plan: route=%s steps=%d tokens~%d tier=%s",
        route,
        len(steps),
        est_tokens,
        tier.value,
    )
    return plan
