"""Bounded artifact generation through the upstream OpenClaw Gateway CLI."""
from __future__ import annotations
import json, os, re, secrets, tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_root_path,
)
from .fusion_redaction_gate import REDACTION_GATE_PASSED, evaluate_redaction_gate
from .reddog_artifact_generation_admission_capability import (
    ArtifactGenerationModelCapability,
    consume_artifact_generation_model,
)
from .reddog_artifact_generation_model_binding import (
    artifact_generation_digest,
    resolved_principal_model_route,
)
from .reddog_artifact_generation_provider_contract import (
    ArtifactGenerationModelResult,
    validate_provider_artifact_contents,
)
from .reddog_openclaw_gateway_command_runner import (
    OpenClawCommandResult,
    SystemOpenClawCommandRunner,
)
from .reddog_openclaw_gateway_confinement import openclaw_artifact_session_is_confined

FAIL_GATEWAY = "FAIL_OPENCLAW_GATEWAY_PREFLIGHT"
_VERSION = re.compile(r"(?:OpenClaw\s+)?(\d{4}\.\d+\.\d+(?:-\d+)?)")
_AGENT_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
class OpenClawCommandRunner(Protocol):
    def run(self, argv: Sequence[str], *, timeout_seconds: int) -> OpenClawCommandResult: ...
@dataclass(frozen=True)
class _Preflight:
    version: str = ""
    spawn_count: int = 0
    observation_complete: bool = True
@dataclass(frozen=True)
class OpenClawGatewayArtifactGenerationRunner:
    repo_root: Path
    runtime_root: Path
    agent_id: str
    command_runner: OpenClawCommandRunner = SystemOpenClawCommandRunner()
    # Supplied from the governed runtime profile. Empty means unavailable and
    # causes capability issuance to fail before any OpenClaw process is started.
    available_model_providers: tuple[str, ...] = ()

    def generate_artifacts(self, *, prompt: str, context: str,
                           binding: ArtifactGenerationModelCapability,
                           timeout_seconds: int) -> ArtifactGenerationModelResult:
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
            return _reject("FAIL_OPENCLAW_TIMEOUT_BOUND")
        gate = evaluate_redaction_gate(prompt, context, audit_mode=True)
        if gate.status != REDACTION_GATE_PASSED or not gate.redacted_prompt:
            return _reject("FAIL_OPENCLAW_REDACTION_BLOCKED")
        runtime = _runtime_root(self.runtime_root, self.repo_root)
        if runtime is None:
            return _reject("FAIL_OPENCLAW_RUNTIME_ROOT")
        verified = consume_artifact_generation_model(binding)
        model, session_key = _signed_invocation(verified)
        if not model or not session_key:
            return _reject("FAIL_OPENCLAW_MODEL_BINDING")
        preflight = _preflight(self.command_runner, self.agent_id, session_key, timeout_seconds)
        if not preflight.version:
            return _reject(FAIL_GATEWAY, spawn_count=preflight.spawn_count,
                           observation_complete=preflight.observation_complete)
        return _invoke(self, runtime, gate.redacted_prompt, gate.redacted_context or "",
                       preflight, model, session_key, timeout_seconds)
def _preflight(runner, agent_id: str, session_key: str, timeout: int) -> _Preflight:
    if _AGENT_ID.fullmatch(agent_id) is None:
        return _Preflight()
    # Put the RPC probe last: on WSL cold start the preceding read-only CLI
    # calls give the user service time to bind without a retry or hidden launch.
    commands = (("openclaw", "--version"),
                ("openclaw", "agents", "list", "--json"),
                ("openclaw", "sandbox", "explain", "--session", session_key, "--json"),
                ("openclaw", "gateway", "status", "--require-rpc", "--json"))
    results = []
    try:
        for command in commands:
            results.append(runner.run(command, timeout_seconds=timeout))
    except Exception:
        return _Preflight(spawn_count=sum(item.process_started for item in results))
    count = sum(item.process_started for item in results)
    complete = all(item.termination_confirmed and not item.output_limit_exceeded for item in results)
    if any(item.returncode or item.timed_out for item in results) or not complete:
        return _Preflight(spawn_count=count, observation_complete=complete)
    version_result, agents_result, sandbox_result, status_result = results
    match = _VERSION.search(version_result.stdout.strip())
    status, agents = _json(status_result.stdout, Mapping) or {}, _json(agents_result.stdout, list)
    cli = str(_nested(status, "cli", "version") or "")
    gateway = str(_nested(status, "rpc", "server", "version") or "")
    config, gateway_state = _nested(status, "config", "cli"), status.get("gateway")
    service_audit = _nested(status, "service", "configAudit")
    plugin_drift = status.get("pluginVersionDrift")
    status_ok = (_nested(status, "rpc", "ok") is True and isinstance(gateway_state, Mapping)
                 and gateway_state.get("bindMode") == "loopback" and isinstance(config, Mapping)
                 and config.get("exists") is True and config.get("valid") is True
                 and isinstance(service_audit, Mapping) and service_audit.get("ok") is True
                 and service_audit.get("issues") == [] and isinstance(plugin_drift, Mapping)
                 and plugin_drift.get("drifts") == [])
    agent_ok = isinstance(agents, list) and any(
        isinstance(item, Mapping) and item.get("id") == agent_id for item in agents)
    sandbox_ok = openclaw_artifact_session_is_confined(
        _json(sandbox_result.stdout, Mapping) or {}, agent_id=agent_id, session_key=session_key
    )
    version = match.group(1) if match and status_ok and agent_ok and sandbox_ok else ""
    exact_versions = (
        version
        and cli == gateway == version
        and gateway_state.get("version") == version
        and plugin_drift.get("gatewayVersion") == version
    )
    return _Preflight(version if exact_versions else "", count, complete)
def _invoke(provider, runtime, prompt, context, preflight, model, session_key, timeout):
    message = ("Return only strict JSON with exactly one key: artifact_contents. "
               "artifact_contents must be a non-empty object whose keys are safe relative "
               "artifact paths and whose values are non-empty text strings.\n\nTASK:\n" + prompt +
               "\n\nGOVERNED CONTEXT:\n" + context)
    path = None
    try:
        descriptor, raw = tempfile.mkstemp(prefix="reddog-openclaw-", suffix=".md", dir=runtime)
        path = Path(raw)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(message)
        os.chmod(path, 0o600)
        argv = ("openclaw", "agent", "--message-file", str(path), "--agent", provider.agent_id,
                "--model", model, "--session-key", session_key, "--json", "--timeout", str(timeout))
        result = provider.command_runner.run(argv, timeout_seconds=timeout + 30)
    except (OSError, ValueError):
        return _reject("FAIL_OPENCLAW_RUNTIME_ROOT", spawn_count=preflight.spawn_count,
                       file_write=path is not None)
    except Exception:
        return _reject("FAIL_OPENCLAW_AGENT_REJECTED", spawn_count=preflight.spawn_count,
                       file_write=path is not None, observation_complete=False,
                       abort_confirmed=False)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
    count = preflight.spawn_count + int(result.process_started)
    incomplete = result.timed_out or result.output_limit_exceeded or not result.termination_confirmed
    if incomplete:
        return _reject("FAIL_OPENCLAW_AGENT_INDETERMINATE", invoked=True, spawn_count=count,
                       file_write=True, observation_complete=False, abort_confirmed=False)
    parsed = None if result.returncode else _agent_artifacts(result.stdout)
    if parsed is None:
        return _reject("FAIL_OPENCLAW_ARTIFACT_OUTPUT", invoked=True, spawn_count=count, file_write=True)
    run_id, artifacts = parsed
    digest = artifact_generation_digest({"agent_id": provider.agent_id, "artifacts": artifacts,
        "model": model, "openclaw_version": preflight.version, "run_id": run_id,
        "session_digest": artifact_generation_digest(session_key)})
    return ArtifactGenerationModelResult(True, "MODEL_OK", artifacts, run_id, digest, True,
        provider_runtime="openclaw_gateway", provider_invocation_performed=True,
        worker_process_started=count > 0, worker_process_spawn_count=count,
        file_write_performed=True, external_side_effects_possible=True)
def _agent_artifacts(raw: str):
    response = _json(raw, Mapping) or {}
    payloads = _nested(response, "result", "payloads")
    if response.get("status") != "ok" or not isinstance(payloads, list) or len(payloads) != 1:
        return None
    answer = _json(str(payloads[0].get("text") or ""), Mapping) if isinstance(payloads[0], Mapping) else None
    artifacts = answer.get("artifact_contents") if isinstance(answer, Mapping) else None
    run_id = str(response.get("runId") or "")
    validated = validate_provider_artifact_contents(artifacts)
    valid = isinstance(answer, Mapping) and set(answer) == {"artifact_contents"} and run_id
    return (run_id, validated) if valid and validated is not None else None


def _signed_invocation(binding):
    route = resolved_principal_model_route(binding)
    if route is None:
        return "", ""
    canonical_model, provider = route
    runtime_model = (
        canonical_model
        if canonical_model.startswith(provider + "/")
        else f"{provider}/{canonical_model}"
    )
    if _MODEL_ID.fullmatch(runtime_model) is None:
        return "", ""
    return runtime_model, f"agent:reddog-artifact:reddog-{secrets.token_hex(16)}"


def _runtime_root(runtime_root, repo_root):
    try:
        root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
        root.mkdir(parents=True, exist_ok=True)
        return validate_runtime_root_path(root, repo_root=repo_root)
    except (OSError, ValueError):
        return None


def _json(raw, expected):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("duplicate_json_key")
            result[key] = value
        return result
    try: value = json.loads(raw, object_pairs_hook=unique)
    except (TypeError, ValueError): return None
    return value if isinstance(value, expected) else None


def _nested(value, *keys):
    for key in keys:
        if not isinstance(value, Mapping): return None
        value = value.get(key)
    return value


def _reject(reason, *, invoked=False, spawn_count=0, file_write=False,
            observation_complete=True, abort_confirmed=True):
    return ArtifactGenerationModelResult(False, "MODEL_REJECT",
        model_result_digest=artifact_generation_digest({"reason": reason}), made_network_call=invoked,
        rejection_reasons=(reason,), provider_runtime="openclaw_gateway",
        provider_invocation_performed=invoked, worker_process_started=spawn_count > 0,
        worker_process_spawn_count=spawn_count, file_write_performed=file_write,
        external_side_effects_possible=invoked, effect_observation_complete=observation_complete,
        run_abort_confirmed=abort_confirmed)
