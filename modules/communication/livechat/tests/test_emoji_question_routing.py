"""Offline actual-method controls for emoji questions and reviewed reply identity."""
import ast
import asyncio
import importlib.util
import logging
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture
def processor(monkeypatch):
    path = SRC / "message_processor.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MessageProcessor")
    cls.bases = []
    cls.body = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name in {"generate_response", "_conversation_response", "_resolve_model_command", "_check_whack_command"}]
    env = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_env_truthy")
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    ns = {"logger": logging.getLogger(__name__), "os": os, "re": re, "time": time,
          "_sanitize_username": lambda name: name}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, env, cls], type_ignores=[])), str(path), "exec"), ns)
    name = "modules.communication.livechat.src.llm_integration"
    spec = importlib.util.spec_from_file_location(name, SRC / "llm_integration.py")
    integration = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, integration)
    spec.loader.exec_module(integration)
    queue = ModuleType("modules.communication.livechat.src.operator_command_queue")
    theme = {"topic": "Offline factual site description"}
    queue.load_active_theme = Mock(return_value=theme)
    monkeypatch.setitem(sys.modules, queue.__name__, queue)
    monkeypatch.setenv("YT_LIVECHAT_ENGAGE_MODS_ONLY", "true")
    monkeypatch.setenv("YT_COMMENT_REPLY_ENABLED", "true")

    # Use the actual reviewed string carrier, without importing model owners.
    reply_tree = ast.parse((SRC / "intelligent_livechat_reply.py").read_text(encoding="utf-8"))
    reply_cls = next(n for n in reply_tree.body if isinstance(n, ast.ClassDef) and n.name == "ReviewedLivechatReply")
    reply_ns = {}
    exec(compile(ast.Module(body=[reply_cls], type_ignores=[]), str(SRC / "intelligent_livechat_reply.py"), "exec"), reply_ns)
    reply = reply_ns["ReviewedLivechatReply"]("Offline factual answer", theme)
    obj = ns["MessageProcessor"]()
    obj.channel_id = "receiving-channel"
    obj.stream_title = "Offline stream"
    obj.intelligent_reply = SimpleNamespace(channel_id=obj.channel_id, stream_title=obj.stream_title)
    obj.memory_manager = SimpleNamespace(current_session='current', get_conversation_context=Mock(return_value={
        'session_id': 'current', 'participant_id': 'captured-author', 'recent_messages': [], 'participant_messages': []}))
    obj._await_intelligent_reply = AsyncMock(return_value=reply)
    obj.self_improvement = SimpleNamespace(observe_command=Mock())
    obj.persona_config = {}
    obj._check_pqn_command = Mock(return_value=False)
    obj.consciousness_mode = "mods_only"
    obj.command_handler = SimpleNamespace(handle_whack_command=Mock(return_value="Quiz answer"))
    obj.agentic_engine = SimpleNamespace(generate_agentic_response=Mock(
        return_value="@Viewer Good question! The answer lies in consciousness evolution. Keep exploring!"))
    obj.intelligent_throttle = SimpleNamespace(
        check_message_diversity=Mock(return_value=(True, "ok")),
        check_moderator_command_allowed=Mock(return_value=(True, "ok")),
        record_moderator_command=Mock())
    obj._update_trigger_time = Mock()
    return obj, reply, theme


def message(text, role="MOD", **flags):
    return {"text": text, "author_name": "Viewer", "author_id": "captured-author",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "is_moderator": role == "MOD", "is_owner": role == "OWNER",
            "has_consciousness": True, **flags}


@pytest.mark.parametrize("role", ["MOD", "OWNER"])
@pytest.mark.parametrize("text", [
    "✊✋🖐 What is the oversight site for?",
    "✊✋🖐️ Explain the oversight site",
    "What is the oversight site for? ✊✋🖐️",
    "✊🏽✋🏽🖐🏽 このサイトについて説明して",
])
def test_emoji_question_uses_exact_question_context_and_reviewed_reply(processor, role, text):
    obj, reply, theme = processor
    data = message(text, role)
    result = asyncio.run(obj.generate_response(data))
    assert result is reply, "canned text or rewritten reviewed text is not an answer"
    obj._await_intelligent_reply.assert_awaited_once_with(
        theme_snapshot=theme, message=text, username="Viewer", user_id="captured-author", role=role,
        is_member=False,
        conversation_context={**obj.memory_manager.get_conversation_context.return_value, 'directed_request': True})
    obj.agentic_engine.generate_agentic_response.assert_not_called()
    assert len(obj._conversation_attempts) == 1
    assert data["response_type"] == "conversation"


@pytest.mark.parametrize("failure", ["unavailable", "disabled", "missing_generator", "rate_limited", "diversity", "changed_context"])
def test_emoji_question_never_falls_back_to_canned_success(processor, monkeypatch, failure):
    obj, _, _ = processor
    data = message("✊✋🖐 What is the oversight site for?")
    if failure == "unavailable":
        obj._await_intelligent_reply.return_value = None
    elif failure == "disabled":
        monkeypatch.setenv("YT_COMMENT_REPLY_ENABLED", "false")
    elif failure == "missing_generator":
        obj.intelligent_reply = None
    elif failure == "rate_limited":
        data["is_rate_limited"] = True
    elif failure == "diversity":
        obj.intelligent_throttle.check_message_diversity.return_value = (False, "repeat")
    else:
        async def change_context(**kwargs):
            obj.channel_id = "different-channel"
            return "Late response"
        obj._await_intelligent_reply.side_effect = change_context
    assert asyncio.run(obj.generate_response(data)) is None
    obj.agentic_engine.generate_agentic_response.assert_not_called()
    if failure in {"disabled", "missing_generator", "rate_limited"}:
        obj._await_intelligent_reply.assert_not_called()
    else:
        assert obj._await_intelligent_reply.await_count == 1


@pytest.mark.parametrize("text", ["✊✋🖐", "✊✋🖐️", "✊🏽✋🏽🖐🏽"])
def test_bare_emoji_is_observation_only(processor, text):
    obj, _, _ = processor
    obj.agentic_engine.generate_agentic_response.return_value = "@Viewer Emoji acknowledgment"
    assert asyncio.run(obj.generate_response(message(text))) is None
    obj.agentic_engine.generate_agentic_response.assert_not_called()
    obj._await_intelligent_reply.assert_not_called()


@pytest.mark.parametrize("text", ["✊✋🖐 2", "✊✋🖐️ 2", "✊🏽✋🏽🖐🏽 2"])
def test_quiz_answer_precedes_question_generation(processor, text):
    obj, _, _ = processor
    assert asyncio.run(obj.generate_response(message(text))) == "Quiz answer"
    obj.command_handler.handle_whack_command.assert_called_once_with("/quiz 2", "Viewer", "captured-author", "MOD")
    obj.agentic_engine.generate_agentic_response.assert_not_called()
    obj._await_intelligent_reply.assert_not_called()


def test_stakeholder_question_is_eligible_without_badge(processor):
    obj, reply, _ = processor
    assert asyncio.run(obj.generate_response(message("✊✋🖐 Explain this site", "USER"))) is reply
    obj.agentic_engine.generate_agentic_response.assert_not_called()
    assert obj._await_intelligent_reply.await_args.kwargs['role'] == 'USER'


def test_explicit_everyone_mode_preserves_actual_viewer_role(processor, monkeypatch):
    obj, reply, _ = processor
    monkeypatch.setenv("YT_LIVECHAT_ENGAGE_MODS_ONLY", "false")
    obj.consciousness_mode = "everyone"
    assert asyncio.run(obj.generate_response(message("✊✋🖐 Explain this site", "USER"))) is reply
    assert obj._await_intelligent_reply.await_args.kwargs["role"] == "USER"


def test_number_at_start_of_question_is_not_consumed_as_quiz_answer(processor):
    obj, reply, _ = processor
    data = message("✊✋🖐 2 questions: what is this site and who maintains it?")
    assert asyncio.run(obj.generate_response(data)) is reply
    obj.command_handler.handle_whack_command.assert_not_called()
    assert obj._await_intelligent_reply.await_args.kwargs["message"] == data["text"]


def test_text_before_quiz_shaped_suffix_remains_a_question(processor):
    obj, reply, _ = processor
    data = message("Please explain choice ✊✋🖐2")
    assert asyncio.run(obj.generate_response(data)) is reply
    obj.command_handler.handle_whack_command.assert_not_called()
    assert obj._await_intelligent_reply.await_args.kwargs["message"] == data["text"]


def test_quiz_with_no_response_never_falls_through_to_model(processor):
    obj, _, _ = processor
    obj.command_handler.handle_whack_command.return_value = None
    assert asyncio.run(obj.generate_response(message("✊✋🖐 2"))) is None
    obj.command_handler.handle_whack_command.assert_called_once()
    obj._await_intelligent_reply.assert_not_called()
    obj.agentic_engine.generate_agentic_response.assert_not_called()


def test_existing_slash_command_has_priority_over_emoji_question(processor):
    obj, _, _ = processor
    obj._handle_whack_command = Mock(return_value="Existing help response")
    text = "/help ✊✋🖐"
    assert obj._check_whack_command(text) is True
    assert obj._check_whack_command("✊✋🖐 /help") is False
    data = message(text, has_whack_command=obj._check_whack_command(text))
    assert asyncio.run(obj.generate_response(data)) == "Existing help response"
    obj._handle_whack_command.assert_called_once_with(data["text"], "Viewer", "captured-author", "MOD", False)
    obj._await_intelligent_reply.assert_not_called()
    obj.agentic_engine.generate_agentic_response.assert_not_called()


def test_explicit_code_command_keeps_existing_path(processor):
    obj, _, _ = processor
    obj.agentic_engine.generate_agentic_response.return_value = "@Viewer Existing code command path"
    data = message("✊✋🖐 holoindex find the chat owner")
    assert asyncio.run(obj.generate_response(data)) == "@Viewer Existing code command path"
    obj.agentic_engine.generate_agentic_response.assert_called_once_with("Viewer", data["text"], "MOD")
    obj._await_intelligent_reply.assert_not_called()
