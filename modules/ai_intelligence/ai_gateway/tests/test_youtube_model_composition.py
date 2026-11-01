"""Offline YouTube consumer composition through complete production definitions.

The sibling routing module owns the synthetic credential-free fixture. This
selection adds no model/network/browser effects and requires the guarded child.
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from modules.ai_intelligence.ai_gateway.tests.test_youtube_model_routing import (
    routing, _ready, _response,
)


def _consumer_definitions():
    import importlib.util
    path = Path(__file__).resolve().parents[4] / "modules/communication/video_comments/tests/test_chat_manifest_inspection.py"
    spec = importlib.util.spec_from_file_location("_youtube_route_composition", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


@pytest.mark.parametrize("cancel_review", [False, True])
def test_actual_processor_await_then_review_has_its_own_cancellation(routing, monkeypatch, cancel_review):
    import asyncio
    import threading
    from modules.ai_intelligence.ai_gateway.src import ai_gateway
    helper = _consumer_definitions()
    _ready(routing, monkeypatch)
    answers = iter(["The film details are at HornetHunter.com.", json.dumps(helper.GOOD)])
    calls = []
    monkeypatch.setattr(ai_gateway.requests, "post", lambda *a, **kw:
        calls.append(kw) or _response(text=next(answers)))
    generator = object.__new__(helper.GEN.IntelligentReplyGenerator)
    generator._generation_lock = threading.RLock()
    generator._model_gateway = routing.gateway
    generator._load_reply_theme_for_surface = lambda surface: None
    processor = object.__new__(helper.PROCESSOR.CommentProcessor)
    async def heartbeat(*args): return None
    processor._thinking_heartbeat = heartbeat
    def write(data, *, with_source, cancel_event):
        generator._current_cancel_event = cancel_event
        result = generator._call_language_model("Answer using supplied facts.", data["text"], "write")
        return helper.GEN.ReplyGenerationResult(result.response, result.provider, None,
            {"reply_surface": "comments", "assessment": {"theme_relevant": False}})
    processor._generate_intelligent_reply = write
    helper.PROCESSOR.get_reply_generator = lambda: generator
    data = {"text": "Where can I watch the film?", "author_name": "Aki", "channel_id": "viewer-A",
            "video_id": "film-A", "_target_channel_id": "receiving-A"}
    async def exercise():
        text, _ = await processor._await_reply_generation(data)
        assert generator._current_cancel_event.is_set() is True
        if cancel_review:
            explicit = Event()
            explicit.set()
            return generator.inspect_reply(data, text, cancel_event=explicit)
        return await processor._inspect_reply(data, text)
    review = asyncio.run(exercise())
    assert review.get("approved") is (not cancel_review)
    assert len(calls) == (1 if cancel_review else 2)


@pytest.mark.parametrize("prior_channel", [None, "receiving-A"])
def test_persona_refresh_rebinds_consciousness_adapter_to_current_channel(routing, monkeypatch, prior_channel):
    from modules.communication.livechat.src.llm_integration import ModelIntegration, ModelReplyRequest
    helper = _consumer_definitions()
    module = helper.definitions("_youtube_persona_refresh", "modules/communication/livechat/src/message_processor.py")
    calls = []
    def bound(channel):
        return SimpleNamespace(channel_id=channel, stream_title="Stream " + str(channel), generate_reply=lambda *a, **kw:
                               calls.append(channel) or "Reviewed answer for " + str(channel))
    old, current = bound(prior_channel), bound("receiving-B")
    processor = object.__new__(module.MessageProcessor)
    processor.intelligent_reply = old
    processor.grok = ModelIntegration(old)
    module.get_persona_config = lambda **kw: {}
    module.get_livechat_reply_generator = lambda **kw: current
    processor.update_persona_context(channel_id="receiving-B", stream_title="Stream B")
    processor.grok.all_user_messages = {"Aki": [{"username": "Aki", "user_id": "viewer-B", "message": "Where is the film?"}]}
    result = processor.grok.fact_check("Aki", "USER", "")
    assert processor.grok.reply_generator is current
    assert isinstance(result, ModelReplyRequest) and result.receiving_channel_id == "receiving-B"
    assert result.stream_title == "Stream receiving-B" and result.user_id == "viewer-B"
    assert calls == []


def test_target_author_does_not_inherit_requester_moderator_role(routing):
    from modules.communication.livechat.src.llm_integration import ModelIntegration, ModelReplyRequest
    calls = []
    generator = SimpleNamespace(channel_id="receiving-A", stream_title="Stream A",
                                generate_reply=lambda *a, **kw: calls.append(True))
    adapter = ModelIntegration(generator, {"Aki": [{"username": "Aki", "channel_id": "regular-viewer", "message": "Film question"}]})
    request = adapter.fact_check("Aki", "MOD", "")
    assert isinstance(request, ModelReplyRequest)
    assert (request.username, request.user_id, request.role) == ("Aki", "regular-viewer", "USER")
    assert request.receiving_channel_id == "receiving-A" and calls == []


@pytest.mark.parametrize("fault", ["missing", "mixed", "numeric", "container"])
def test_consciousness_target_requires_explicit_unambiguous_typed_identity(routing, fault):
    from modules.communication.livechat.src.llm_integration import ModelIntegration
    calls = []
    rows = [{"username": "Aki", "message": "Film question"}]
    if fault == "mixed":
        rows = [{"username": "Aki", "user_id": "viewer-A"}, {"username": "Aki", "user_id": "viewer-B"}]
    if fault == "numeric": rows[0]["user_id"] = 123456789
    if fault == "container": rows[0]["user_id"] = ["viewer-A"]
    generator = SimpleNamespace(channel_id="receiving-A", stream_title="Stream A",
                                generate_reply=lambda *a, **kw: calls.append(True))
    adapter = ModelIntegration(generator, {"Aki-is-only-a-display-name": rows})
    assert adapter.fact_check("Aki", "MOD", "") is None
    assert calls == []


def _command_owner(routing, monkeypatch, generate):
    from modules.communication.livechat.src.llm_integration import model_reply_request
    from modules.communication.livechat.src.intelligent_livechat_reply import ReviewedLivechatReply
    from modules.communication.livechat.src import operator_command_queue
    helper = _consumer_definitions()
    module = helper.definitions("_youtube_bounded_command", "modules/communication/livechat/src/message_processor.py")
    processor = object.__new__(module.MessageProcessor)
    processor.channel_id, processor.stream_title = "receiving-A", "Stream A"
    processor.intelligent_reply = SimpleNamespace(channel_id="receiving-A", stream_title="Stream A", generate_reply=generate)
    monkeypatch.setattr(operator_command_queue, "load_active_theme", lambda surface: None)
    request = model_reply_request(processor.intelligent_reply, "Film question", "Aki", "viewer-A", "USER")
    return processor, request, ReviewedLivechatReply


@pytest.mark.parametrize("timeout", [False, True])
def test_actual_command_async_owner_keeps_heartbeat_and_cancels_late_result(routing, monkeypatch, timeout):
    import asyncio
    calls, events, beats = [], [], []
    def generate(**kwargs):
        calls.append(kwargs)
        events.append(kwargs["cancel_event"])
        kwargs["cancel_event"].wait(0.5 if timeout else 0.04)
        return reviewed("@Aki The film details are at HornetHunter.com.", None)
    processor, request, reviewed = _command_owner(routing, monkeypatch, generate)
    original = asyncio.wait_for
    deadlines = []
    def bounded(awaitable, *, timeout):
        deadlines.append(timeout)
        return original(awaitable, timeout=min(timeout, 0.1))
    monkeypatch.setattr(asyncio, "wait_for", bounded)
    async def exercise():
        done = asyncio.Event()
        async def heartbeat():
            while not done.is_set():
                beats.append(True)
                await asyncio.sleep(0.002)
        pulse = asyncio.create_task(heartbeat())
        try:
            return await processor._resolve_model_command(request)
        finally:
            done.set()
            await pulse
    result = asyncio.run(exercise())
    assert len(calls) == 1 and len(beats) >= 2 and deadlines == [10.0]
    assert events[0].is_set() is True
    assert (result is None) is timeout
    if not timeout:
        assert isinstance(result, reviewed) and str(result) == "@Aki The film details are at HornetHunter.com."


@pytest.mark.parametrize("when,field", [("before", "channel_id"), ("before", "stream_title"),
                                      ("during", "channel_id"), ("during", "stream_title")])
def test_command_descriptor_cannot_cross_receiving_channel_or_stream(routing, monkeypatch, when, field):
    import asyncio
    calls = []
    def generate(**kwargs):
        calls.append(True)
        if when == "during": setattr(processor, field, "receiving-B" if field == "channel_id" else "Stream B")
        return reviewed("@Aki Specific reviewed answer.", None)
    processor, request, reviewed = _command_owner(routing, monkeypatch, generate)
    if when == "before": setattr(processor, field, "receiving-B" if field == "channel_id" else "Stream B")
    assert asyncio.run(processor._resolve_model_command(request)) is None
    assert calls == ([] if when == "before" else [True])


def test_command_builder_only_returns_private_scoped_descriptor(routing):
    from modules.communication.livechat.src.llm_integration import ModelReplyRequest
    helper = _consumer_definitions()
    module = helper.definitions("_youtube_command_descriptor", "modules/communication/livechat/src/command_handler.py")
    calls = []
    generator = SimpleNamespace(channel_id="receiving-A", stream_title="Stream A",
                                generate_reply=lambda *a, **kw: calls.append(True))
    handler = object.__new__(module.CommandHandler)
    handler.message_processor = SimpleNamespace(intelligent_reply=generator)
    marker = "SYNTHETIC_PRIVATE_REQUEST"
    result = handler._generate_model_command(marker, "Aki", "viewer-A", "MOD")
    assert isinstance(result, ModelReplyRequest) and calls == []
    assert (result.username, result.user_id, result.role) == ("Aki", "viewer-A", "MOD")
    assert (result.receiving_channel_id, result.stream_title) == ("receiving-A", "Stream A")
    assert result.message == marker and marker not in repr(result)


def _sdk_fixture(monkeypatch):
    import sys
    from types import ModuleType
    from modules.infrastructure.shared_utilities import local_llm_backends as backends
    constructors, calls = [], []
    def complete(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Specific useful answer."))])
    class Client:
        def __init__(self, **kwargs):
            constructors.append(kwargs)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=complete))
    sdk = ModuleType("openai")
    sdk.OpenAI = Client
    monkeypatch.setitem(sys.modules, "openai", sdk)
    monkeypatch.setattr(backends, "inspect_lm_studio_model", lambda *a, **kw: SimpleNamespace(
        state=backends.LMStudioResidencyState.RESIDENT,
        loaded_instances=(SimpleNamespace(instance_id="synthetic-instance"),)))
    monkeypatch.setattr(backends.LMStudioBackend, "_require_exact_instance_unchanged", lambda self: None)
    return backends, constructors, calls, Client


@pytest.mark.parametrize("consumer", ["generic", "youtube"])
def test_exact_sdk_retry_policy_preserves_generic_default_and_disables_youtube_retries(routing, monkeypatch, consumer):
    backends, constructors, calls, _ = _sdk_fixture(monkeypatch)
    if consumer == "generic":
        backend = backends.LMStudioBackend("qwen3.5-4b")
        assert backend.initialize() is True
        assert len(constructors) == 1 and "max_retries" not in constructors[0]
        assert calls == []
    else:
        _ready(routing, monkeypatch, role_bindings=({
            "role": "principal", "provider": "lm_studio_local", "model_id": "qwen3.5-4b"},))
        result = routing.gateway.call_youtube_task(system_prompt="Answer the film question.",
            prompt="Where are details?", stage="write", max_tokens=150)
        assert result.success is True and result.response == "Specific useful answer."
        assert len(constructors) == 1 and constructors[0]["max_retries"] == 0
        assert len(calls) == 1 and calls[0]["reasoning_effort"] == "none"
        assert calls[0]["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False


@pytest.mark.parametrize("cancel_during_probe", [False, True])
def test_backend_checks_cancellation_after_native_probe_before_sdk(routing, monkeypatch, cancel_during_probe):
    backends, _, calls, client = _sdk_fixture(monkeypatch)
    event = Event()
    backend = backends.LMStudioBackend("qwen3.5-4b", max_retries=0,
        pre_dispatch_check=lambda: routing.module._require_current(None, event))
    backend._initialized, backend._client = True, client()
    def probe():
        if cancel_during_probe: event.set()
    backend._require_exact_instance_unchanged = probe
    result = backend.create_chat_completion([{"role": "user", "content": "Film question"}])
    assert len(calls) == (0 if cancel_during_probe else 1)
    assert result["choices"][0]["message"]["content"] == ("" if cancel_during_probe else "Specific useful answer.")
