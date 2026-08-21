"""Bounded lifecycle for upstream Hermes native leaf-delegated generation."""

from __future__ import annotations

import re
import secrets
from typing import Any, Mapping

from .reddog_artifact_generation_model_binding import artifact_generation_digest
from .reddog_artifact_generation_model_binding import signed_principal_model_route
from .reddog_artifact_generation_provider_contract import (
    ArtifactGenerationModelResult,
    validate_provider_artifact_contents,
)
from .reddog_hermes_api_confinement import strict_json_mapping
from .reddog_hermes_api_event_log import (
    verify_hermes_postflight,
    verify_hermes_run_event_log,
)

_TERMINAL = {"completed", "failed", "cancelled"}
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")


def signed_hermes_route(binding: object) -> tuple[str, str] | None:
    return signed_principal_model_route(binding)


def execute_hermes_artifact_run(
    runner: Any,
    *,
    api_key: str,
    route: tuple[str, str],
    prompt: str,
    context: str,
    timeout_seconds: int,
) -> ArtifactGenerationModelResult:
    model, provider_id = route
    run_nonce = secrets.token_hex(16)
    session_id = f"reddog-artifact-{run_nonce}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Hermes-Session-Key": f"agent:reddog-artifact:{session_id}",
    }
    payload = _request_payload(prompt, context, session_id, model, provider_id)
    try:
        started = runner.transport.request(
            "POST", "/v1/runs", headers=headers, payload=payload,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        return reject_hermes(
            "FAIL_HERMES_RUN_SUBMISSION", invoked=True, observed=False, abort=False
        )
    body = strict_json_mapping(started.body)
    run_id = str(body.get("run_id") or "") if body else ""
    if (
        started.status != 202
        or _RUN_ID.fullmatch(run_id) is None
        or body.get("status") != "started"
    ):
        return reject_hermes(
            "FAIL_HERMES_RUN_SUBMISSION", invoked=True, observed=False, abort=False
        )
    deadline = runner.monotonic() + timeout_seconds
    while runner.monotonic() < deadline:
        status = _status(runner.transport, headers, run_id, timeout_seconds)
        if status is None:
            return _stop(runner, headers, run_id, timeout_seconds, "FAIL_HERMES_RUN_STATUS")
        state = str(status.get("status") or "")
        if state == "waiting_for_approval" or _shows_forbidden_activity(status):
            return _stop(runner, headers, run_id, timeout_seconds, "FAIL_HERMES_TOOL_ACTIVITY")
        if state in _TERMINAL:
            return _finish_terminal(
                runner, headers, run_id, timeout_seconds, status, model, provider_id
            )
        runner.sleeper(0.05)
    return _stop(runner, headers, run_id, timeout_seconds, "FAIL_HERMES_RUN_TIMEOUT")


def _request_payload(prompt, context, session_id, model, provider_id):
    return {
        "input": f"TASK:\n{prompt}\n\nGOVERNED CONTEXT:\n{context}",
        "instructions": (
            "You are the RedDog parent worker. Before answering, make exactly one spawning "
            "invocation of delegate_task using the single-goal form: goal=<complete task>, "
            "context=<all needed governed context>, role='leaf', background=false. Never use "
            "the tasks array, action=list, action=steer, action=stop, background delegation, "
            "or a second delegate_task call. Wait for that leaf to finish. If it does not "
            "finish successfully, return no artifact. Do not request approval or call another "
            "tool. After the completed child result returns, independently format its useful "
            "result as only strict JSON with exactly one non-empty artifact_contents object "
            "mapping safe relative paths to text."
        ),
        "session_id": session_id,
        "model": model,
        "provider": provider_id,
    }


def reject_hermes(
    reason: str,
    *,
    network: bool = False,
    invoked: bool = False,
    observed: bool = True,
    abort: bool = False,
) -> ArtifactGenerationModelResult:
    return ArtifactGenerationModelResult(
        False,
        "MODEL_REJECT",
        model_result_digest=artifact_generation_digest({"reason": reason}),
        made_network_call=network or invoked,
        rejection_reasons=(reason,),
        provider_runtime="hermes_api",
        provider_invocation_performed=invoked,
        hermes_dispatch_performed=invoked,
        external_side_effects_possible=invoked,
        effect_observation_complete=observed,
        run_abort_confirmed=abort,
    )


def _status(transport, headers, run_id, timeout):
    response = transport.request(
        "GET", f"/v1/runs/{run_id}", headers=headers, payload=None,
        timeout_seconds=timeout,
    )
    if response.status != 200 or response.output_limit_exceeded:
        return None
    return strict_json_mapping(response.body)


def _finish_terminal(runner, headers, run_id, timeout, status, model, provider_id):
    if not verify_hermes_run_event_log(
        runner.transport, headers, run_id, timeout, status
    ):
        return reject_hermes("FAIL_HERMES_EVENT_CONFINEMENT", invoked=True, observed=False)
    if not verify_hermes_postflight(runner.transport, headers, timeout):
        return reject_hermes("FAIL_HERMES_POSTFLIGHT_CONFINEMENT", invoked=True)
    return _terminal(status, run_id, model, provider_id, native_delegation=True)


def _stop(runner, headers, run_id, timeout, reason):
    try:
        stopped = runner.transport.request(
            "POST", f"/v1/runs/{run_id}/stop", headers=headers, payload={},
            timeout_seconds=timeout,
        )
        status = _status(runner.transport, headers, run_id, timeout)
    except Exception:
        status, stopped = None, None
    confirmed = bool(stopped and stopped.status in {200, 202} and status)
    confirmed = confirmed and status.get("status") == "cancelled"
    return reject_hermes(reason, invoked=True, observed=confirmed, abort=confirmed)


def _terminal(status, run_id, model, provider_id, *, native_delegation):
    if status.get("status") != "completed" or _shows_forbidden_activity(status):
        return reject_hermes("FAIL_HERMES_RUN_REJECTED", invoked=True)
    artifacts = _artifacts(str(status.get("output") or ""))
    if artifacts is None:
        return reject_hermes("FAIL_HERMES_ARTIFACT_OUTPUT", invoked=True)
    digest = artifact_generation_digest(
        {
            "artifacts": artifacts,
            "model": model,
            "native_delegation": native_delegation,
            "provider": provider_id,
            "run_id": run_id,
        }
    )
    return ArtifactGenerationModelResult(
        True, "MODEL_OK", artifacts, run_id, digest, True,
        provider_runtime="hermes_api", provider_invocation_performed=True,
        hermes_dispatch_performed=True, external_side_effects_possible=True,
    )


def _artifacts(raw: str):
    value = strict_json_mapping(raw)
    artifacts = value.get("artifact_contents") if value and set(value) == {"artifact_contents"} else None
    return validate_provider_artifact_contents(artifacts)


def _shows_forbidden_activity(value: Mapping[str, Any]) -> bool:
    event = str(value.get("last_event") or "").lower()
    return event.startswith("approval") or bool(value.get("approval"))


__all__ = ["execute_hermes_artifact_run", "reject_hermes", "signed_hermes_route"]
