"""Independent offline controls for the exact YouTube Gateway consumer.

Imports and all collaborators are constructed inside fixtures. Execute only in
the owner's credential-free, network/effect-guarded child. No installed service,
production credential, model load, or public action is part of this contract.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest


@pytest.fixture
def routing(monkeypatch, tmp_path):
    for name in tuple(os.environ):
        monkeypatch.delenv(name)
    for name, value in {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
                        "TEMP": str(tmp_path), "TMP": str(tmp_path),
                        "PYTHON_DOTENV_DISABLED": "1", "SYSTEMROOT": r"C:\Windows"}.items():
        monkeypatch.setenv(name, value)
    from modules.ai_intelligence.ai_gateway.src import youtube_model_routing as module
    from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway, ProviderConfig
    gateway = object.__new__(AIGateway)
    gateway.providers = {"openrouter": ProviderConfig(
        name="openrouter", api_key="SYNTHETIC_HEADER_ONLY",
        base_url="https://openrouter.ai/api/v1", models={},
        cost_per_token=0, rate_limit=1)}
    clock = [1_800_000_000]
    monkeypatch.setattr(module.time, "time", lambda: clock[0])
    return SimpleNamespace(module=module, gateway=gateway, clock=clock, tmp=tmp_path)


def _response(model="qwen/qwen3:free", text="The film details are at HornetHunter.com."):
    return SimpleNamespace(status_code=200, raise_for_status=lambda: None,
        json=lambda: {"model": model, "choices": [{"message": {"content": text}}]})


def _transport(monkeypatch, response=None):
    from modules.ai_intelligence.ai_gateway.src import ai_gateway
    calls = []
    monkeypatch.setattr(ai_gateway.requests, "post", lambda url, **kw:
                        calls.append({"url": url, **kw}) or (response or _response()))
    return calls


def _ready(routing, monkeypatch, **changes):
    from modules.communication.moltbot_bridge.src import reddog_model_runtime_binding_query as query
    values = dict(accepted=True, task_family="youtube_reply", panel_models=(),
        role_bindings=({"role": "principal", "provider": "openrouter", "model_id": "qwen/qwen3:free"},),
        binding_receipt_id="binding:synthetic", topology_valid_until=routing.clock[0] + 60)
    values.update(changes)
    seen = []
    def resolve(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(**values)
    monkeypatch.setattr(query, "query_model_runtime_binding", resolve)
    monkeypatch.setenv("YT_MODEL_ROUTING_ROOT", str(routing.tmp / "runtime"))
    monkeypatch.setenv("YT_MODEL_RUNTIME_BINDING_RECEIPT_PATH", str(routing.tmp / "binding.json"))
    return seen


def _call(routing, **changes):
    values = dict(system_prompt="Answer the actual question using supplied facts.",
                  prompt="Where can I watch the film?", stage="write", surface="comments", max_tokens=150)
    values.update(changes)
    return routing.gateway.call_youtube_task(**values)


def _forbid(attempts):
    def forbidden(*_args, **_kwargs):
        attempts.append(True)
        raise AssertionError("Unavailable route entered a forbidden collaborator")
    return forbidden


@pytest.mark.parametrize("filename,alias", [
    ("Gemma-4-E2B-it-Q4_K_M.gguf", "local/gemma-4-e2b-it"),
    ("Qwen3.5-4B-Q4_K_M.gguf", "qwen3.5-4b"),
])
def test_default_route_uses_exact_selected_general_role(routing, monkeypatch, filename, alias):
    from modules.infrastructure.shared_utilities import local_model_selection as selection
    roles = []
    monkeypatch.setattr(selection, "resolve_model_selection", lambda role:
        roles.append(role) or SimpleNamespace(exists=True, path=Path(filename)))
    monkeypatch.setenv("LM_STUDIO_MODEL", alias)
    calls = []
    monkeypatch.setattr(routing.module, "_local_call", lambda model, payload, *a, **kw:
        calls.append((model, payload)) or "The film details are at HornetHunter.com.")
    result = _call(routing)
    assert result.success is True and result.provider == "lm_studio_local"
    assert result.model == alias and result.response == "The film details are at HornetHunter.com."
    assert roles == ["general"] and calls[0][0] == alias


@pytest.mark.parametrize("filename", ["UI-TARS-1.5-7B-Q4.gguf", "qwen-coder-7b-Q4.gguf", "gemma-3-270m-it-Q4.gguf"])
def test_default_role_rejects_visual_coder_and_tiny_triage(routing, monkeypatch, filename):
    from modules.infrastructure.shared_utilities import local_model_selection as selection
    monkeypatch.setattr(selection, "resolve_model_selection", lambda role:
                        SimpleNamespace(exists=True, path=Path(filename)))
    calls = []
    monkeypatch.setattr(routing.module, "_local_call", lambda *a, **kw: calls.append(True))
    assert _call(routing).success is False
    assert calls == []


def test_wrong_loaded_alias_cannot_replace_selected_general_role(routing, monkeypatch):
    from modules.infrastructure.shared_utilities import local_model_selection as selection
    monkeypatch.setattr(selection, "resolve_model_selection", lambda role:
                        SimpleNamespace(exists=True, path=Path("gemma-4-e2b-it-Q4.gguf")))
    monkeypatch.setenv("LM_STUDIO_MODEL", "qwen3.5-4b")
    with pytest.raises(ValueError):
        routing.module._incumbent_model()


def test_missing_general_role_has_no_arbitrary_loaded_model_fallback(routing, monkeypatch):
    from modules.infrastructure.shared_utilities import local_model_selection as selection
    monkeypatch.setattr(selection, "resolve_model_selection", lambda role:
                        SimpleNamespace(exists=False, path=Path("gemma-4-e2b-it-Q4.gguf")))
    attempts = []
    monkeypatch.setattr(routing.module, "_local_call", _forbid(attempts))
    assert _call(routing).success is False and attempts == []


@pytest.mark.parametrize("name", ["YT_MODEL_ROUTING_ROOT", "YT_MODEL_SELECTION_RECEIPT_PATH",
    "YT_MODEL_EVIDENCE_TRUSTED_KEYS_PATH", "YT_MODEL_COMMENTS_WRITE_BINDING_PATH"])
def test_any_partial_binding_configuration_fails_without_incumbent_fallback(routing, monkeypatch, name):
    monkeypatch.setenv(name, str(routing.tmp / "missing.json"))
    fallbacks = []
    monkeypatch.setattr(routing.module, "_incumbent_model", _forbid(fallbacks))
    calls = []
    monkeypatch.setattr(routing.module, "_local_call", lambda *a, **kw: calls.append(True))
    monkeypatch.setattr(routing.module, "_openrouter_call", lambda *a, **kw: calls.append(True))
    assert _call(routing).success is False and calls == fallbacks == []


@pytest.mark.parametrize("fault", ["not_accepted", "wrong_family", "panel", "grok_provider", "xai_model", "expired"])
def test_invalid_configured_binding_never_falls_back(routing, monkeypatch, fault):
    changes = {}
    if fault == "not_accepted": changes["accepted"] = False
    if fault == "wrong_family": changes["task_family"] = "general_reasoning"
    if fault == "panel": changes["panel_models"] = ("gemma/other",)
    if fault == "grok_provider": changes["role_bindings"] = ({"role": "principal", "provider": "grok", "model_id": "grok-4"},)
    if fault == "xai_model": changes["role_bindings"] = ({"role": "principal", "provider": "openrouter", "model_id": "x-ai/grok-4"},)
    if fault == "expired": changes["topology_valid_until"] = routing.clock[0] - 1
    _ready(routing, monkeypatch, **changes)
    fallbacks = []
    monkeypatch.setattr(routing.module, "_incumbent_model", _forbid(fallbacks))
    calls = _transport(monkeypatch)
    assert _call(routing).success is False and calls == fallbacks == []


def test_stage_override_and_surface_are_passed_to_existing_verifier(routing, monkeypatch):
    seen = _ready(routing, monkeypatch)
    binding = str(routing.tmp / "live-review.json")
    selected = str(routing.tmp / "live-selection.json")
    monkeypatch.setenv("YT_MODEL_LIVECHAT_REVIEW_BINDING_PATH", binding)
    monkeypatch.setenv("YT_MODEL_LIVECHAT_REVIEW_SELECTION_PATH", selected)
    _transport(monkeypatch)
    assert _call(routing, surface="livechat", stage="review").success is True
    assert seen and all(item["expected_surface"] == "youtube_livechat" for item in seen)
    assert all(item["environ"]["REDDOG_BACKEND_ARCHITECT_MODEL_RUNTIME_BINDING_RECEIPT_PATH"] == binding for item in seen)
    assert all(item["environ"]["REDDOG_MODEL_SELECTION_RECEIPT_PATH"] == selected for item in seen)
    assert all(item["environ"]["REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS"] == "lm_studio_local,openrouter" for item in seen)


def _real_binding(routing, monkeypatch, *, surface="youtube_comments", family="youtube_reply"):
    from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
        model_runtime_binding_test_verifier, model_selection_and_runtime_binding_receipts)
    from modules.communication.moltbot_bridge.src import reddog_model_runtime_binding_query as query
    selection, binding = model_selection_and_runtime_binding_receipts(
        runtime_surface=surface, task_family=family, provider="openrouter", model_id="qwen/qwen3:free")
    runtime = routing.tmp / "runtime"
    runtime.mkdir()
    binding_path, selection_path = runtime / "binding.json", runtime / "selection.json"
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    delegate = model_runtime_binding_test_verifier(binding)
    verified = []
    def verify(**kwargs):
        verified.append(True)
        return delegate.verify(**kwargs)
    monkeypatch.setattr(query, "_runtime_verifier", lambda **kw: (SimpleNamespace(verify=verify), ()))
    monkeypatch.setenv("YT_MODEL_ROUTING_ROOT", str(runtime))
    monkeypatch.setenv("YT_MODEL_RUNTIME_BINDING_RECEIPT_PATH", str(binding_path))
    monkeypatch.setenv("YT_MODEL_SELECTION_RECEIPT_PATH", str(selection_path))
    return verified


@pytest.mark.parametrize("surface", ["comments", "livechat"])
def test_existing_signed_test_verifier_composes_with_real_query_before_cloud(routing, monkeypatch, surface):
    verified = _real_binding(routing, monkeypatch, surface="youtube_" + surface)
    calls = _transport(monkeypatch)
    result = _call(routing, surface=surface)
    assert result.success is True and result.provider == "openrouter"
    assert verified and len(calls) == 1
    assert result.response == "The film details are at HornetHunter.com."
    wire = calls[0]["json"]
    assert wire["model"] == result.model == "qwen/qwen3:free"
    assert wire["provider"] == {"data_collection": "deny", "allow_fallbacks": False,
                                "max_price": {"prompt": 0, "completion": 0}}
    assert calls[0]["allow_redirects"] is False and calls[0]["timeout"] <= 3
    assert "SYNTHETIC_HEADER_ONLY" not in json.dumps(wire)
    assert calls[0]["headers"]["Authorization"] == "Bearer SYNTHETIC_HEADER_ONLY"


@pytest.mark.parametrize("surface,family", [("reddog_backend_architect", "youtube_reply"), ("youtube_comments", "coding")])
def test_real_query_wrong_surface_or_task_family_has_zero_egress(routing, monkeypatch, surface, family):
    _real_binding(routing, monkeypatch, surface=surface, family=family)
    fallbacks = []
    monkeypatch.setattr(routing.module, "_incumbent_model", _forbid(fallbacks))
    calls = _transport(monkeypatch)
    assert _call(routing).success is False and calls == fallbacks == []


@pytest.mark.parametrize("field", ["system_prompt", "prompt", "response_format"])
def test_complete_payload_secret_guard_blocks_before_cloud(routing, monkeypatch, field, caplog):
    _ready(routing, monkeypatch)
    marker = "sk-" + "A" * 30
    change = {field: {"type": "json_schema", "description": marker} if field == "response_format" else marker}
    calls = _transport(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        assert _call(routing, **change).success is False
    assert calls == [] and marker not in caplog.text


@pytest.mark.parametrize("model", ["openrouter/free", "openrouter/auto", "x-ai/grok-4"])
def test_router_alias_and_xai_models_cannot_enter_transport(routing, monkeypatch, model):
    _ready(routing, monkeypatch, role_bindings=({"role": "principal", "provider": "openrouter", "model_id": model},))
    calls = _transport(monkeypatch)
    assert _call(routing).success is False and calls == []


def test_k3_incompatible_completion_contract_is_rejected_before_http(routing, monkeypatch):
    _ready(routing, monkeypatch, role_bindings=({"role": "principal", "provider": "openrouter", "model_id": "moonshotai/kimi-k3"},))
    calls = _transport(monkeypatch)
    assert _call(routing, max_tokens=150).success is False and calls == []


def test_cloud_response_from_different_model_is_not_attributed_as_selected(routing, monkeypatch):
    _ready(routing, monkeypatch)
    calls = _transport(monkeypatch, _response(model="x-ai/grok-4"))
    result = _call(routing)
    assert result.success is False and len(calls) == 1


@pytest.mark.parametrize("change", [{"stage": "execute"}, {"surface": "browser"}, {"max_tokens": True}, {"max_tokens": 4096}])
def test_invalid_task_does_not_resolve_or_call_provider(routing, monkeypatch, change):
    resolutions = []
    monkeypatch.setattr(routing.module, "_binding_environment", _forbid(resolutions))
    calls = _transport(monkeypatch)
    assert _call(routing, **change).success is False and calls == resolutions == []


def test_expiry_during_prompt_guard_blocks_actual_egress(routing, monkeypatch):
    _ready(routing, monkeypatch, topology_valid_until=routing.clock[0] + 1)
    original = routing.module._guard_payload
    def guard(payload):
        original(payload)
        routing.clock[0] += 2
    monkeypatch.setattr(routing.module, "_guard_payload", guard)
    calls = _transport(monkeypatch)
    assert _call(routing).success is False and calls == []


def test_expiry_during_local_initialization_blocks_inference(routing, monkeypatch):
    from modules.infrastructure.shared_utilities import local_llm_backends as backends
    _ready(routing, monkeypatch, topology_valid_until=routing.clock[0] + 1,
        role_bindings=({"role": "principal", "provider": "lm_studio_local", "model_id": "qwen3.5-4b"},))
    calls = []
    def initialize():
        routing.clock[0] += 2
        return True
    monkeypatch.setattr(backends, "LMStudioBackend", lambda **kw: SimpleNamespace(
        initialize=initialize, create_chat_completion=lambda **kw: calls.append(True)))
    assert _call(routing).success is False and calls == []


def test_cancellation_during_preparation_blocks_actual_cloud_call(routing, monkeypatch):
    _ready(routing, monkeypatch)
    event = Event()
    original = routing.module._guard_payload
    def guard(payload):
        original(payload)
        event.set()
    monkeypatch.setattr(routing.module, "_guard_payload", guard)
    calls = _transport(monkeypatch)
    assert _call(routing, cancel_event=event).success is False and calls == []


def test_late_provider_result_after_expiry_is_not_usable(routing, monkeypatch):
    _ready(routing, monkeypatch, topology_valid_until=routing.clock[0] + 1)
    from modules.ai_intelligence.ai_gateway.src import ai_gateway
    def post(*args, **kwargs):
        routing.clock[0] += 2
        return _response()
    monkeypatch.setattr(ai_gateway.requests, "post", post)
    assert _call(routing).success is False


def test_already_cancelled_call_does_not_resolve_any_route(routing, monkeypatch):
    event = Event()
    event.set()
    resolutions = []
    monkeypatch.setattr(routing.module, "_binding_environment", _forbid(resolutions))
    assert _call(routing, cancel_event=event).success is False and resolutions == []


@pytest.mark.parametrize("phase", ["initialize", "chat"])
def test_inner_local_backend_errors_do_not_echo_raw_provider_message(routing, monkeypatch, caplog, phase):
    from modules.infrastructure.shared_utilities import local_llm_backends as backends
    marker = "SYNTHETIC_PRIVATE_SDK_DIAGNOSTIC"
    def fail(*args, **kwargs):
        raise RuntimeError(marker)
    backend = backends.LMStudioBackend("qwen3.5-4b")
    if phase == "initialize":
        monkeypatch.setattr(backends, "inspect_lm_studio_model", fail)
        operation = backend.initialize
    else:
        backend._initialized = True
        backend._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
        backend._require_exact_instance_unchanged = lambda: None
        operation = lambda: backend.create_chat_completion([{"role": "user", "content": "Film question"}])
    with caplog.at_level(logging.DEBUG):
        operation()
    assert marker not in caplog.text


def test_useful_three_stage_calls_keep_each_author_and_receiving_context(routing, monkeypatch):
    _ready(routing, monkeypatch)
    calls = _transport(monkeypatch)
    for receiving in ("receiving-A", "receiving-B"):
        for stage in ("assess", "write", "review"):
            prompt = json.dumps({"author_channel_id": "viewer-" + receiving,
                "receiving_channel_id": receiving, "video_id": "film-" + receiving,
                "comment": "Where can I watch the film?", "facts": "HornetHunter.com"})
            result = _call(routing, stage=stage, prompt=prompt)
            assert result.success is True
            assert calls[-1]["json"]["messages"][1]["content"] == prompt
            assert result.response == "The film details are at HornetHunter.com."
    assert len(calls) == 6


def test_nonempty_rejected_writer_output_keeps_quality_fault_receipt(routing, monkeypatch, caplog):
    _ready(routing, monkeypatch)
    marker = "<think>SYNTHETIC_PRIVATE_OUTPUT</think>"
    calls = _transport(monkeypatch, _response(text=marker))
    with caplog.at_level(logging.DEBUG):
        result = _call(routing, stage="write")
    assert len(calls) == 1
    assert result.success is False and result.reason == "invalid_reply_text"
    assert result.response == "" and marker not in caplog.text and marker not in repr(result)
