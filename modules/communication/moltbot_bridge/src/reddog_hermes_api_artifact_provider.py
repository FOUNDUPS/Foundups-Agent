"""Text-only artifact generation through the authenticated upstream Hermes API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from .fusion_redaction_gate import REDACTION_GATE_PASSED, evaluate_redaction_gate
from .reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
    consume_artifact_generation_model,
)
from .reddog_artifact_generation_provider_contract import ArtifactGenerationModelResult
from .reddog_hermes_api_confinement import (
    strict_json_mapping,
    verify_hermes_api_preflight,
)
from .reddog_hermes_api_run_lifecycle import (
    execute_hermes_artifact_run,
    reject_hermes,
    signed_hermes_route,
)
from .reddog_hermes_api_transport import HermesApiTransport


@dataclass(frozen=True)
class HermesApiArtifactGenerationRunner:
    transport: HermesApiTransport
    api_key_provider: Any
    sleeper: Callable[[float], None] = time.sleep
    monotonic: Callable[[], float] = time.monotonic

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: ArtifactGenerationModelCapability,
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
            return reject_hermes("FAIL_HERMES_TIMEOUT_BOUND")
        gate = evaluate_redaction_gate(prompt, context, audit_mode=True)
        if gate.status != REDACTION_GATE_PASSED or not gate.redacted_prompt:
            return reject_hermes("FAIL_HERMES_REDACTION_BLOCKED")
        verified = consume_artifact_generation_model(binding)
        route = signed_hermes_route(verified)
        if route is None:
            return reject_hermes("FAIL_HERMES_MODEL_BINDING")
        try:
            api_key = self.api_key_provider.read_key()
        except Exception:
            return reject_hermes("FAIL_HERMES_SERVICE_IDENTITY")
        accepted, reason = _preflight(self.transport, api_key, timeout_seconds)
        if not accepted:
            return reject_hermes(reason, network=True)
        return execute_hermes_artifact_run(
            self,
            api_key=api_key,
            route=route,
            prompt=gate.redacted_prompt,
            context=gate.redacted_context or "",
            timeout_seconds=timeout_seconds,
        )


def _preflight(transport, api_key: str, timeout: int) -> tuple[bool, str]:
    auth = {"Authorization": f"Bearer {api_key}"}
    try:
        unauth = transport.request(
            "GET", "/v1/capabilities", headers={}, payload=None,
            timeout_seconds=timeout,
        )
        values = []
        paths = ("/v1/capabilities", "/health/detailed", "/v1/toolsets", "/v1/skills")
        for path in paths:
            response = transport.request(
                "GET", path, headers=auth, payload=None, timeout_seconds=timeout
            )
            if response.status != 200 or response.output_limit_exceeded:
                return False, "FAIL_HERMES_PREFLIGHT_TRANSPORT"
            values.append(strict_json_mapping(response.body))
    except Exception:
        return False, "FAIL_HERMES_PREFLIGHT_TRANSPORT"
    receipt = verify_hermes_api_preflight(
        unauthenticated_status=unauth.status,
        capabilities=values[0], health=values[1], toolsets=values[2], skills=values[3],
    )
    if receipt.accepted:
        return True, ""
    if receipt.rejection_reason == "FAIL_HERMES_TOOLSET_CONFINEMENT":
        toolsets_closed = values[2] is not None and values[2].get("data") is not None
        if toolsets_closed and values[3] != {"object": "list", "data": []}:
            return False, "FAIL_HERMES_SKILL_CONFINEMENT"
    return False, receipt.rejection_reason


__all__ = ["HermesApiArtifactGenerationRunner"]
