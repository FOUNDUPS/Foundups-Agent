"""OpenClaw conversation execution helper.

WSP 73/97 boundary:
- OpenClaw owns dialogue, identity, and execution-plane selection.
- WRE is invoked when the resolved execution plane requires orchestration.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from .openclaw_runtime_support import _env_truthy

if TYPE_CHECKING:
    from .openclaw_dae import OpenClawIntent


logger = logging.getLogger("openclaw_dae")


def execute_conversation(dae: Any, intent: "OpenClawIntent") -> str:
    """
    Default: Digital Twin conversational response.

    Chain (local-first):
      1) Deterministic identity/model/control handling
      2) IronClaw sidecar (when backend=ironclaw)
      3) Local Qwen via AI Overseer
      4) Ollama local fallback
      5) AI Gateway cloud fallback (when enabled)
    """
    user_msg = intent.raw_message.strip()
    system_prompt = dae._build_conversation_system_prompt()
    if dae._is_turn_cancelled("conversation_start"):
        dae._mark_conversation_engine("cancelled", "conversation_start")
        return dae._turn_cancelled_response()

    if dae._is_connect_wre_request(user_msg):
        if not intent.is_authorized_commander:
            dae._mark_conversation_engine("connect_wre_blocked", "commander_required")
            return "0102: connect_wre is operator-only. 012 commander authority required."
        verbose = dae._wants_connect_wre_details(user_msg)
        dae._mark_conversation_engine("connect_wre", "deterministic_conversation_route")
        return dae._build_connect_wre_status(verbose=verbose)

    if dae._is_model_switch_request(user_msg):
        target = dae._parse_model_switch_target(user_msg)
        if not target:
            dae._mark_conversation_engine("model_switch", "target_missing")
            return dae._model_switch_target_help()
        gate_error = dae._wsp00_model_switch_gate(intent, target)
        if gate_error:
            dae._mark_conversation_engine("model_switch_blocked", "wsp00_gate")
            return gate_error
        dae._mark_conversation_engine("model_switch", f"target={target or 'unknown'}")
        return dae._apply_model_switch_target(target or "")

    if dae._is_token_usage_query(user_msg):
        dae._mark_conversation_engine("token_usage", "deterministic_conversation_route")
        return dae._build_token_usage_report()

    if dae._is_identity_query(user_msg):
        if dae._wants_full_identity_card(user_msg):
            dae._mark_conversation_engine("identity_card", "deterministic_conversation_route")
            return dae._build_identity_card()
        dae._mark_conversation_engine("identity_compact", "deterministic_conversation_route")
        if dae._is_compact_identity_query(user_msg):
            return dae._build_identity_compact_runtime()
        return dae._build_identity_compact()

    dae._maybe_apply_agentic_conversation_model(intent, user_msg)

    if dae._is_turn_cancelled("pre_ironclaw"):
        dae._mark_conversation_engine("cancelled", "pre_ironclaw")
        return dae._turn_cancelled_response()
    if dae._conversation_backend == "ironclaw":
        ironclaw_reply = dae._try_ironclaw_conversation(user_msg, system_prompt)
        if dae._is_turn_cancelled("post_ironclaw"):
            dae._mark_conversation_engine("cancelled", "post_ironclaw")
            return dae._turn_cancelled_response()
        if ironclaw_reply:
            dae._record_token_usage(
                prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                completion_text=ironclaw_reply,
                engine="ironclaw",
                provider="ironclaw",
                model=os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
                source="estimated",
            )
            dae._mark_conversation_engine("ironclaw", "gateway_chat_completion")
            return ironclaw_reply

        if dae._ironclaw_strict and not dae._ironclaw_allow_local_fallback:
            recovered, recover_detail = dae._attempt_ironclaw_autostart()
            if recovered:
                retry_reply = dae._try_ironclaw_conversation(user_msg, system_prompt)
                if retry_reply:
                    dae._record_token_usage(
                        prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                        completion_text=retry_reply,
                        engine="ironclaw",
                        provider="ironclaw",
                        model=os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
                        source="estimated",
                    )
                    dae._mark_conversation_engine("ironclaw", "autostart_recovered")
                    return retry_reply

            runtime = dae._probe_ironclaw_runtime()
            dae._mark_conversation_engine(
                "ironclaw_unavailable_strict",
                f"{runtime.get('detail', 'unavailable')}|{recover_detail}",
            )
            base = (
                "0102: IronClaw runtime is unavailable in strict mode, so local fallback is disabled. "
                "Auto-recovery was attempted. Use menu 16 -> 5 (IronClaw Runtime Status), or enable "
                "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK=1."
            )
            if _env_truthy("OPENCLAW_VERBOSE_RUNTIME_ERRORS", "0"):
                return (
                    f"{base} "
                    f"health={runtime.get('healthy', 'UNKNOWN')} "
                    f"detail={runtime.get('detail', 'not-probed')} "
                    f"base_url={runtime.get('base_url', 'unknown')} "
                    f"autostart={recover_detail}."
                )
            return base

    if dae._conversation_backend != "ironclaw":
        preferred_external_reply = dae._try_preferred_external_conversation(user_msg, system_prompt)
        if dae._is_turn_cancelled("post_preferred_external"):
            dae._mark_conversation_engine("cancelled", "post_preferred_external")
            return dae._turn_cancelled_response()
        if preferred_external_reply:
            dae._record_token_usage(
                prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                completion_text=preferred_external_reply,
                engine="ai_gateway_preferred",
                provider=dae._preferred_external_provider or "external",
                model=dae._preferred_external_model or "unknown",
                source="estimated",
            )
            dae._mark_conversation_engine(
                "ai_gateway_preferred",
                f"{dae._preferred_external_provider}/{dae._preferred_external_model}",
            )
            return preferred_external_reply
        if dae._preferred_external_provider and dae._preferred_external_model:
            logger.info(
                "[OPENCLAW-DAE] Preferred external not used | target=%s/%s status=%s detail=%s -> fallback=local",
                dae._preferred_external_provider,
                dae._preferred_external_model,
                dae._preferred_external_last_status,
                dae._preferred_external_last_status_detail,
            )

    if dae._is_turn_cancelled("pre_local_qwen"):
        dae._mark_conversation_engine("cancelled", "pre_local_qwen")
        return dae._turn_cancelled_response()
    if dae.overseer:
        try:
            conversation_context = f"Channel: {intent.channel}, Sender: {intent.sender}"
            platform_context = dae._load_platform_context_pack()
            if platform_context:
                conversation_context = (
                    f"{conversation_context}\n\n"
                    f"{platform_context[: dae._platform_context_quick_response_chars]}"
                )
            result = dae.overseer.quick_response(
                prompt=user_msg,
                context=conversation_context,
                max_tokens=80,
            )
            if dae._is_turn_cancelled("post_local_qwen"):
                dae._mark_conversation_engine("cancelled", "post_local_qwen")
                return dae._turn_cancelled_response()
            if result and result.get("response"):
                resp = dae._trim_self_dialogue(result["response"])
                if resp and len(resp) > 3 and "Error:" not in resp:
                    prompt_context = (
                        f"{system_prompt}\n\n"
                        f"{conversation_context}\n\n"
                        f"User: {user_msg}"
                    )
                    dae._record_token_usage(
                        prompt_text=prompt_context,
                        completion_text=resp,
                        engine="local_qwen",
                        provider="local_qwen",
                        model=dae._conversation_model_target_id or "local/qwen-coder-7b",
                        source="estimated",
                    )
                    logger.info(
                        "[OPENCLAW-DAE] Conversation via local Qwen: %d chars",
                        len(resp),
                    )
                    dae._mark_conversation_engine("local_qwen", "ai_overseer.quick_response")
                    return dae._ensure_conversation_identity(resp)
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] Local Qwen response failed: %s", exc)

    if dae._is_turn_cancelled("pre_ollama"):
        dae._mark_conversation_engine("cancelled", "pre_ollama")
        return dae._turn_cancelled_response()
    if dae._ollama_model:
        try:
            import requests as _req

            ollama_resp = _req.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": dae._ollama_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    "stream": False,
                    "options": {"num_predict": 80, "temperature": 0.7},
                },
                timeout=15,
            )
            if dae._is_turn_cancelled("post_ollama"):
                dae._mark_conversation_engine("cancelled", "post_ollama")
                return dae._turn_cancelled_response()
            if ollama_resp.ok:
                body = ollama_resp.json()
                content = body.get("message", {}).get("content", "")
                content = dae._trim_self_dialogue(content)
                if content and len(content) > 3:
                    prompt_eval = dae._safe_int(body.get("prompt_eval_count"))
                    eval_count = dae._safe_int(body.get("eval_count"))
                    total_tokens = (
                        (prompt_eval + eval_count)
                        if (prompt_eval is not None and eval_count is not None)
                        else None
                    )
                    usage = {
                        "prompt_tokens": prompt_eval,
                        "completion_tokens": eval_count,
                        "total_tokens": total_tokens,
                    }
                    dae._record_token_usage(
                        prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                        completion_text=content,
                        engine="ollama",
                        provider="ollama",
                        model=dae._ollama_model,
                        usage=usage,
                        source="provider_usage" if (prompt_eval is not None or eval_count is not None) else "estimated",
                    )
                    logger.info(
                        "[OPENCLAW-DAE] Conversation via Ollama (%s): %d chars",
                        dae._ollama_model,
                        len(content),
                    )
                    dae._mark_conversation_engine("ollama", dae._ollama_model)
                    return dae._ensure_conversation_identity(content)
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] Ollama unavailable: %s", exc)

    if (
        dae._conversation_backend != "ironclaw"
        and _env_truthy("OPENCLAW_ALLOW_IRONCLAW_FALLBACK", "0")
    ):
        ironclaw_reply = dae._try_ironclaw_conversation(user_msg, system_prompt)
        if dae._is_turn_cancelled("post_ironclaw_fallback"):
            dae._mark_conversation_engine("cancelled", "post_ironclaw_fallback")
            return dae._turn_cancelled_response()
        if ironclaw_reply:
            dae._record_token_usage(
                prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                completion_text=ironclaw_reply,
                engine="ironclaw_fallback",
                provider="ironclaw",
                model=os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
                source="estimated",
            )
            dae._mark_conversation_engine("ironclaw_fallback", "openclaw_allow_ironclaw_fallback")
            return ironclaw_reply

    if dae._is_turn_cancelled("pre_ai_gateway"):
        dae._mark_conversation_engine("cancelled", "pre_ai_gateway")
        return dae._turn_cancelled_response()
    if not dae._allow_external_llm:
        logger.info("[OPENCLAW-DAE] External LLM disabled by key-isolation policy")
        dae._mark_conversation_engine("none", "external_llm_disabled")
        return "0102: I'm here. Local conversation models are unavailable right now."

    try:
        from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway

        gw = AIGateway()
        prompt = f"{system_prompt}\n\nUser: {user_msg}"
        result = gw.call_with_fallback(prompt=prompt, task_type="quick")
        if dae._is_turn_cancelled("post_ai_gateway"):
            dae._mark_conversation_engine("cancelled", "post_ai_gateway")
            return dae._turn_cancelled_response()
        if result and result.success and result.response and len(result.response) > 3:
            trimmed = dae._trim_self_dialogue(result.response)
            if trimmed and len(trimmed) > 3:
                dae._record_token_usage(
                    prompt_text=prompt,
                    completion_text=trimmed,
                    engine="ai_gateway",
                    provider=str(result.provider),
                    model=str(getattr(result, "model", "")),
                    source="estimated",
                    cost_estimate_usd=getattr(result, "cost_estimate", None),
                )
                logger.info(
                    "[OPENCLAW-DAE] Conversation via AI Gateway (%s): %d chars",
                    result.provider,
                    len(trimmed),
                )
                dae._mark_conversation_engine("ai_gateway", str(result.provider))
                return dae._ensure_conversation_identity(trimmed)
    except Exception as exc:
        logger.debug("[OPENCLAW-DAE] AI Gateway unavailable: %s", exc)

    dae._mark_conversation_engine("none", "minimal_ack")
    return "0102: I'm here. My conversation models aren't fully responding right now."
