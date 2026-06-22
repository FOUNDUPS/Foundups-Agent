#!/usr/bin/env python3
"""One-shot advisory model call for the FoundUps Cursor extension.

Reads JSON from stdin and writes JSON to stdout. Raw prompt and bounded
context are evaluated by the Fusion redaction gate before any external request.
The caller should store only the returned redacted history/review packet.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (  # noqa: E402
    REDACTION_GATE_PASSED,
    evaluate_redaction_gate,
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ENV_API_KEY = "OPENROUTER_API_KEY"
GLM_PRINCIPAL_MODEL = "z-ai/glm-5.2"
DEEPSEEK_CRITIC_MODEL = "deepseek/deepseek-v4-pro"
KIMI_PANEL_MODEL = "moonshotai/kimi-k2.7-code"
DEFAULT_LEAD_MODEL = GLM_PRINCIPAL_MODEL
DEFAULT_PANEL_MODELS = (DEEPSEEK_CRITIC_MODEL, KIMI_PANEL_MODEL)
MAX_PANEL_MODELS = 6
RETRYABLE_HTTP_STATUS = frozenset({429, 502, 503})
MAX_HTTP_RETRIES = 2

DEFAULT_SYSTEM_PROMPT = (
    "You are 0102 operating as an advisory RedDog Architect worker inside a Cursor extension tab. "
    "You do not edit files, run commands, merge PRs, create repos, or claim WSP/CABR authority. "
    "Operate in WSP_00, apply WSP_97 truth boundaries, and end substantive answers with WSP_15 priority. "
    "For every finding, include evidence, uncertainty, and an actionable proposed fix or explicit defer reason."
)


def _json_result(**fields: Any) -> int:
    sys.stdout.write(json.dumps(fields, ensure_ascii=True, sort_keys=True))
    sys.stdout.write("\n")
    return 0


def _progress(stage: str, text: str) -> None:
    sys.stderr.write(json.dumps({"event": "progress", "stage": stage, "text": text}, ensure_ascii=True))
    sys.stderr.write("\n")
    sys.stderr.flush()


def _post_openrouter(api_key: str, body: dict[str, Any], timeout: int) -> tuple[dict[str, Any], dict[str, Any]]:
    retry_meta: dict[str, Any] = {"retry_count": 0, "final_retry_reason": None}
    last_exc: urllib.error.HTTPError | None = None
    for attempt in range(MAX_HTTP_RETRIES + 1):
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
                "X-Title": "FoundUps Cursor Advisory Worker",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), retry_meta
        except urllib.error.HTTPError as exc:
            status = getattr(exc, "code", None)
            if status in RETRYABLE_HTTP_STATUS and attempt < MAX_HTTP_RETRIES:
                retry_meta["retry_count"] = attempt + 1
                retry_meta["final_retry_reason"] = "http_" + str(status)
                last_exc = exc
                continue
            setattr(exc, "retry_meta", dict(retry_meta))
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("retry loop exited without response")


def _http_error_detail(exc: urllib.error.HTTPError) -> dict[str, Any]:
    detail = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            message = error.get("message") or error.get("code") or error.get("type")
            if isinstance(message, str):
                detail = message
        if not detail:
            detail = body
    except Exception:
        detail = ""
    return {"status": getattr(exc, "code", None), "detail": detail[:500]}


def _http_failure_reason(exc: urllib.error.HTTPError, retry_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    status = getattr(exc, "code", None)
    detail = _http_error_detail(exc)
    meta = retry_meta if retry_meta is not None else getattr(exc, "retry_meta", None)
    if meta and meta.get("retry_count", 0) >= MAX_HTTP_RETRIES and status in RETRYABLE_HTTP_STATUS:
        return {
            "ok": False,
            "reason": "retry_exhausted",
            "http_status": status,
            "retry_count": meta.get("retry_count"),
            "final_retry_reason": meta.get("final_retry_reason"),
            **detail,
        }
    return {"ok": False, "reason": "http_error", "http_status": status, **detail}


def _chat_completion(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    data, retry_meta = _post_openrouter(api_key, body, timeout)
    content = data["choices"][0]["message"]["content"]
    return str(content), retry_meta


def _clean_history(value: object) -> list[dict[str, str]]:
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


def _bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or value < minimum or value > maximum:
        return default
    return value


def _bounded_temperature(value: object, default: float = 0.2) -> float:
    if not isinstance(value, (int, float)) or value < 0 or value > 2:
        return default
    return float(value)


def _model_slug(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip() and len(value.strip()) <= 120:
        return value.strip()
    return default


def _panel_models(value: object) -> list[str]:
    if not isinstance(value, list):
        return list(DEFAULT_PANEL_MODELS)
    models: list[str] = []
    for item in value[:MAX_PANEL_MODELS]:
        if isinstance(item, str) and item.strip() and len(item.strip()) <= 120:
            models.append(item.strip())
    return models or list(DEFAULT_PANEL_MODELS)


def _system_prompt(payload: dict[str, Any]) -> str:
    system_prompt = payload.get("system")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        return DEFAULT_SYSTEM_PROMPT
    return system_prompt[:6000]


def _model_label(model: str) -> str:
    return model.split("/")[-1] if "/" in model else model


def _format_panel(lead_model: str, lead_text: str, panel_results: dict[str, str], synthesis: str) -> str:
    parts = ["## Lead (" + lead_model + ")\n\n" + lead_text.strip()]
    for model, text in panel_results.items():
        parts.append("## Critic (" + model + ")\n\n" + text.strip())
    parts.append("## Synthesis (" + lead_model + ")\n\n" + synthesis.strip())
    return "\n\n".join(parts)


def _openrouter_fusion_alias(
    api_key: str,
    redacted_prompt: str,
    history: list[dict[str, str]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    timeout = _bounded_int(payload.get("timeout"), 120, 1, 240)
    judge_model = _model_slug(payload.get("lead_model"), DEFAULT_LEAD_MODEL)
    panel_models = _panel_models(payload.get("panel_models"))
    messages = [{"role": "system", "content": _system_prompt(payload)}]
    messages.extend(history)
    messages.append({"role": "user", "content": redacted_prompt})
    body = {
        "model": "openrouter/fusion",
        "messages": messages,
        "plugins": [
            {
                "id": "fusion",
                "analysis_models": panel_models,
                "model": judge_model,
            }
        ],
    }
    _progress("fusion_alias_start", "OpenRouter Fusion alias request started. Judge: " + judge_model)
    try:
        data, retry_meta = _post_openrouter(api_key, body, timeout)
        content = str(data["choices"][0]["message"]["content"])
    except urllib.error.HTTPError as exc:
        return _http_failure_reason(exc)
    except (urllib.error.URLError, TimeoutError):
        return {"ok": False, "reason": "timeout"}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {"ok": False, "reason": "fusion_alias_malformed_response"}
    _progress("fusion_alias_done", "OpenRouter Fusion alias response received.")
    next_history = history + [
        {"role": "user", "content": redacted_prompt},
        {"role": "assistant", "content": content},
    ]
    return {
        "ok": True,
        "reason": "ok",
        "mode": "openrouter_fusion_alias",
        "lead_model": judge_model,
        "panel_models": panel_models,
        "content": content,
        "history": next_history[-20:],
        "review_packet": {
            "mode": "openrouter_fusion_alias",
            "lead_model": judge_model,
            "panel_models": panel_models,
            "redacted_prompt": redacted_prompt,
            "synthesis_excerpt": content[:4000],
            "trace_boundary": "OpenRouter Fusion alias does not expose individual critic transcripts.",
            "retry_count": retry_meta.get("retry_count", 0),
            "final_retry_reason": retry_meta.get("final_retry_reason"),
        },
    }


def _run_foundups_fusion(
    api_key: str,
    redacted_prompt: str,
    history: list[dict[str, str]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    timeout = _bounded_int(payload.get("timeout"), 75, 1, 180)
    max_tokens = _bounded_int(payload.get("max_tokens"), 1600, 256, 4096)
    temperature = _bounded_temperature(payload.get("temperature"), 0.2)
    lead_model = _model_slug(payload.get("lead_model"), DEFAULT_LEAD_MODEL)
    panel_models = _panel_models(payload.get("panel_models"))
    base_system = _system_prompt(payload)

    lead_system = (
        base_system
        + "\n\nLead pass: produce the initial RedDog Architect answer. Include findings, evidence, proposed fixes, uncertainties, WSP_15 priority, and next safest step."
    )
    lead_messages = [{"role": "system", "content": lead_system}]
    lead_messages.extend(history)
    lead_messages.append({"role": "user", "content": redacted_prompt})

    _progress("lead_start", "Lead request started: " + lead_model)
    lead_retry: dict[str, Any] = {"retry_count": 0, "final_retry_reason": None}
    try:
        lead_text, lead_retry = _chat_completion(
            api_key,
            lead_model,
            lead_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
    except urllib.error.HTTPError as exc:
        return {**_http_failure_reason(exc), "lead_model": lead_model}
    except (urllib.error.URLError, TimeoutError):
        return {"ok": False, "reason": "timeout", "lead_model": lead_model}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {"ok": False, "reason": "lead_malformed_response", "lead_model": lead_model}

    _progress("lead_done", "Lead response received: " + lead_model)
    critic_system = (
        base_system
        + "\n\nPanel critic pass: attack the lead answer for missing WSP_97 truth labels, missing WSP_15 scoring, unsupported evidence, weak HoloIndex retrieval, and fixes that are not actionable. Do not claim authority."
    )
    critic_user = "Original task:\n" + redacted_prompt + "\n\nLead answer:\n" + lead_text[:16000]
    critic_messages = [
        {"role": "system", "content": critic_system},
        {"role": "user", "content": critic_user},
    ]
    panel_results: dict[str, str] = {}
    _progress("panel_start", "Panel requests started: " + ", ".join(panel_models))
    with ThreadPoolExecutor(max_workers=len(panel_models)) as executor:
        futures = {
            executor.submit(
                _chat_completion,
                api_key,
                model,
                critic_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            ): model
            for model in panel_models
        }
        for future in as_completed(futures):
            model = futures[future]
            try:
                panel_results[model], _panel_retry = future.result()
                _progress("panel_done", "Panel response received: " + model)
            except urllib.error.HTTPError as exc:
                panel_results[model] = "[blocked: http_error " + str(getattr(exc, "code", "")) + "]"
                _progress("panel_blocked", "Panel blocked: " + model)
            except (urllib.error.URLError, TimeoutError):
                panel_results[model] = "[blocked: timeout]"
                _progress("panel_blocked", "Panel network error: " + model)
            except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                panel_results[model] = "[blocked: malformed_response]"
                _progress("panel_blocked", "Panel malformed response: " + model)

    synthesis_system = (
        base_system
        + "\n\nSynthesis pass: resolve panel disagreement, preserve useful dissent, and return the best actionable WSP-compliant recommendation. The final section must be WSP_15 Priority followed by Next safest step."
    )
    panel_text = "\n\n".join(
        _model_label(model) + " critique:\n" + text[:8000]
        for model, text in panel_results.items()
    )
    synthesis_user = (
        "Original task:\n"
        + redacted_prompt
        + "\n\nLead answer:\n"
        + lead_text[:12000]
        + "\n\nPanel critiques:\n"
        + panel_text
    )
    _progress("synthesis_start", "Synthesis request started: " + lead_model)
    try:
        synthesis, _syn_retry = _chat_completion(
            api_key,
            lead_model,
            [
                {"role": "system", "content": synthesis_system},
                {"role": "user", "content": synthesis_user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        synthesis = "Synthesis unavailable. Use the lead answer and panel critiques above."

    _progress("synthesis_done", "Synthesis complete.")
    content = _format_panel(lead_model, lead_text, panel_results, synthesis)
    next_history = history + [
        {"role": "user", "content": redacted_prompt},
        {"role": "assistant", "content": content},
    ]
    return {
        "ok": True,
        "reason": "ok",
        "mode": "foundups_fusion",
        "lead_model": lead_model,
        "panel_models": panel_models,
        "content": content,
        "history": next_history[-20:],
        "review_packet": {
            "mode": "foundups_fusion",
            "lead_model": lead_model,
            "panel_models": panel_models,
            "redacted_prompt": redacted_prompt,
            "lead_excerpt": lead_text[:4000],
            "panel_excerpts": {model: text[:3000] for model, text in panel_results.items()},
            "synthesis_excerpt": synthesis[:4000],
            "retry_count": lead_retry.get("retry_count", 0),
            "final_retry_reason": lead_retry.get("final_retry_reason"),
        },
    }


def main() -> int:
    _progress("bridge_start", "Bridge Python started.")
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return _json_result(ok=False, reason="invalid_json")

    api_key = os.getenv(ENV_API_KEY)
    _progress("env_check", "OPENROUTER_API_KEY visible to bridge: " + ("yes" if bool(api_key) else "no"))
    if not api_key:
        return _json_result(ok=False, reason="missing_key")

    model = payload.get("model")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return _json_result(ok=False, reason="missing_prompt")
    context = payload.get("context")
    context_for_gate = context if isinstance(context, str) and context.strip() else None
    bridge_meta = payload.get("bridge_meta") if isinstance(payload.get("bridge_meta"), dict) else {}

    _progress("redaction_start", "Redaction gate started.")
    gate = evaluate_redaction_gate(prompt, context_for_gate)
    if gate.status != REDACTION_GATE_PASSED or not gate.redacted_prompt:
        _progress("redaction_blocked", "Redaction gate blocked before network.")
        return _json_result(ok=False, reason="redaction_blocked", redaction_reason=gate.reason)

    _progress("redaction_pass", "Redaction gate passed.")
    system_prompt = _system_prompt(payload)
    redacted_user_message = gate.redacted_prompt
    if gate.redacted_context:
        redacted_user_message = gate.redacted_prompt + "\n\n" + gate.redacted_context

    history = _clean_history(payload.get("history"))
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": redacted_user_message})

    if payload.get("mode") == "openrouter_fusion_alias":
        result = _openrouter_fusion_alias(api_key, redacted_user_message, history, payload)
        if bridge_meta:
            packet = result.get("review_packet")
            if isinstance(packet, dict):
                packet.update(bridge_meta)
        return _json_result(**result)

    if payload.get("mode") == "foundups_fusion":
        result = _run_foundups_fusion(api_key, redacted_user_message, history, payload)
        if bridge_meta:
            packet = result.get("review_packet")
            if isinstance(packet, dict):
                packet.update(bridge_meta)
        return _json_result(**result)

    if payload.get("mode") == "openrouter_single":
        model = payload.get("lead_model") or model

    if not isinstance(model, str) or not model:
        return _json_result(ok=False, reason="missing_model")

    max_tokens = _bounded_int(payload.get("max_tokens"), 2048, 1, 4096)
    temperature = _bounded_temperature(payload.get("temperature"), 0.2)
    timeout = _bounded_int(payload.get("timeout"), 60, 1, 120)

    _progress("single_start", "Regular OpenRouter request started: " + model)
    try:
        content, retry_meta = _chat_completion(
            api_key,
            model,
            messages,
            max_tokens=max_tokens,
            temperature=float(temperature),
            timeout=timeout,
        )
    except urllib.error.HTTPError as exc:
        return _json_result(**_http_failure_reason(exc))
    except (urllib.error.URLError, TimeoutError):
        return _json_result(ok=False, reason="timeout")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return _json_result(ok=False, reason="malformed_response")

    _progress("single_done", "Regular OpenRouter response received: " + model)
    assistant_text = str(content)
    next_history = history + [
        {"role": "user", "content": redacted_user_message},
        {"role": "assistant", "content": assistant_text},
    ]
    return _json_result(
        ok=True,
        reason="ok",
        model=model,
        redacted_prompt=redacted_user_message,
        content=assistant_text,
        history=next_history[-20:],
        retry_count=retry_meta.get("retry_count", 0),
        final_retry_reason=retry_meta.get("final_retry_reason"),
        review_packet={
            "mode": "openrouter_single",
            "lead_model": model,
            "redacted_prompt_excerpt": redacted_user_message[:4000],
            "retry_count": retry_meta.get("retry_count", 0),
            "final_retry_reason": retry_meta.get("final_retry_reason"),
            **bridge_meta,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
