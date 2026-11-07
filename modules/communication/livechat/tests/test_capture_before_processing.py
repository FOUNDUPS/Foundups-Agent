"""Offline receive-path regression tests; no browser, provider or model imports."""
import ast
import asyncio
import importlib.util
import logging
from pathlib import Path
import sqlite3
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"


def _core_methods():
    path = SRC / "livechat_core.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "LiveChatCore")
    cls.bases = []
    cls.body = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name in {"process_message", "_log_to_user_file"}]
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), cls], type_ignores=[])
    ns = {"__file__": str(path), "logger": logging.getLogger(__name__), "time": time}
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), ns)
    return ns["LiveChatCore"]


@pytest.fixture
def memory(tmp_path, monkeypatch):
    # Keep the secondary telemetry boundary private; exercise the real immediate DB.
    telemetry = ModuleType("modules.communication.livechat.src.chat_telemetry_store")
    telemetry.ChatTelemetryStore = lambda: SimpleNamespace(record_message=lambda **kw: None)
    monkeypatch.setitem(sys.modules, telemetry.__name__, telemetry)
    path = SRC / "chat_memory_manager.py"
    spec = importlib.util.spec_from_file_location("capture_memory_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manager = module.ChatMemoryManager(str(tmp_path / "memory"))
    manager.start_session("offline-capture")
    return manager


@pytest.mark.parametrize("role", ["USER", "MOD", "OWNER"])
@pytest.mark.parametrize("outcome", ["filtered", "skip", "processor_error", "generation_error", "normal", "router", "command_duplicate", "history"])
def test_received_text_survives_processing_decisions(memory, role, outcome):
    core = _core_methods()()
    core.memory_manager = memory
    core.processed_message_ids = set()
    core.message_timestamps = []
    core.mod_stats = SimpleNamespace(record_message=lambda: None)
    core.wre_monitor = None
    core.router_mode = outcome == "router"
    core.recent_command_cache = {}
    calls = {"processor": 0, "router": 0, "generate": 0}

    def rows():
        with sqlite3.connect(memory.db_path) as db:
            return db.execute("SELECT session_id,user_id,username,message_text,role FROM chat_messages").fetchall()

    def process(message):
        calls["processor"] += 1
        if outcome == "history":
            pytest.fail("historical capture must not invoke response processing")
        expected = 2 if message["id"] == "different-command-id" else 1
        assert len(rows()) == expected, "received message must be durable before processing"
        if outcome == "processor_error":
            raise RuntimeError("offline processing failure")
        return None if outcome == "filtered" else {"skip": outcome == "skip"}

    async def generate(_processed):
        calls["generate"] += 1
        if outcome == "generation_error":
            raise RuntimeError("offline generation failure")
        return "Offline response"

    def route(message):
        calls["router"] += 1
        assert len(rows()) == 1
        return {"response": "Offline response"}

    core.message_processor = SimpleNamespace(process_message=process, generate_response=generate)
    core.message_router = SimpleNamespace(route_message=route)
    core.send_chat_message = AsyncMock()
    text = "/help" if outcome == "command_duplicate" else "A factual question"
    message = {"id": "offline-message", "snippet": {"displayMessage": text},
               "authorDetails": {"displayName": "Fixture", "channelId": "fixture-author",
                                 "isChatModerator": role == "MOD", "isChatOwner": role == "OWNER"}}
    if outcome == "history":
        message["_capture_only"] = True
    asyncio.run(core.process_message(message))
    assert rows() == [(memory.current_session, "fixture-author", "Fixture", text, role)]
    asyncio.run(core.process_message(message))
    assert len(rows()) == 1, "duplicate polling must not duplicate capture"
    assert len(memory.session_mod_messages) == (role in {"MOD", "OWNER"})
    if outcome == "command_duplicate":
        message["id"] = "different-command-id"
        asyncio.run(core.process_message(message))
        assert len(rows()) == 2, "command throttling must not suppress capture of a distinct message"
    assert calls["processor"] == (0 if outcome in {"history", "router"} else 2 if outcome == "command_duplicate" else 1)
    assert calls["router"] == (outcome == "router")
    assert calls["generate"] == (outcome in {"normal", "router", "command_duplicate", "generation_error"})
    if outcome in {"normal", "router", "command_duplicate"}:
        response_type = "general" if outcome == "normal" else "whack"
        core.send_chat_message.assert_awaited_once_with("Offline response", response_type=response_type)
    else:
        core.send_chat_message.assert_not_called()


@pytest.mark.parametrize("role", ["MOD", "OWNER"])
@pytest.mark.parametrize("historical", [True, False])
def test_schema_commands_only_act_on_live_messages(memory, monkeypatch, role, historical):
    core = _core_methods()()
    core.memory_manager = memory
    core.processed_message_ids = set()
    core.message_timestamps = []
    core.mod_stats = SimpleNamespace(record_message=lambda: None)
    core.wre_monitor = None
    core.router_mode = False
    processor = Mock(return_value=None)
    core.message_processor = SimpleNamespace(process_message=processor)
    write = Mock()
    monkeypatch.setattr(Path, "write_text", write)
    message = {"id": "schema-command", "_capture_only": historical,
               "snippet": {"displayMessage": "/news"},
               "authorDetails": {"displayName": "Fixture", "channelId": "fixture-author",
                                 "isChatModerator": role == "MOD", "isChatOwner": role == "OWNER"}}
    asyncio.run(core.process_message(message))
    with sqlite3.connect(memory.db_path) as db:
        assert db.execute("SELECT message_text,role FROM chat_messages").fetchall() == [("/news", role)]
    if historical:
        write.assert_not_called()
        processor.assert_not_called()
    else:
        write.assert_called_once_with("NEWS")
        processor.assert_called_once_with(message)


@pytest.mark.parametrize("kind", ["ban_event", "timeout_event"])
def test_moderation_events_retain_their_separate_path(kind):
    core = _core_methods()()
    core.process_ban_event = AsyncMock()
    core._log_to_user_file = lambda message: pytest.fail("moderation event is not a text comment")
    message = {"type": kind}
    asyncio.run(core.process_message(message))
    core.process_ban_event.assert_awaited_once_with(message)


def _poll_method():
    path = SRC / "chat_poller.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatPoller")
    method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "poll_messages")
    ns = {"logger": logging.getLogger(__name__), "time": time, "asyncio": asyncio,
          "List": list, "Dict": dict, "Any": object,
          "googleapiclient": SimpleNamespace(errors=SimpleNamespace(HttpError=type("HttpError", (Exception,), {})))}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), "exec"), ns)
    return ns["poll_messages"]


@pytest.mark.parametrize("event_type", ["textMessageEvent", "superChatEvent", "newSponsorEvent"])
def test_available_initial_text_batch_is_captured_without_replaying_actions(event_type):
    poll_messages = _poll_method()
    item = {"id": "historical-text", "snippet": {"type": event_type, "displayMessage": "Available history"},
            "authorDetails": {"displayName": "Fixture", "isChatModerator": True}}
    poller = SimpleNamespace(first_poll=True, live_chat_id="offline", connection_time=None,
                             _make_api_call=AsyncMock(return_value={"items": [item]}),
                             _update_polling_interval=lambda *a: None,
                             _handle_polling_error=AsyncMock())
    messages = asyncio.run(poll_messages(poller))
    assert messages == [{**item, "_capture_only": True}]
    assert "_capture_only" not in item, "provider item must not be mutated"
    assert poller.first_poll is False
    # The next normal text poll remains eligible for existing reply decisions.
    live = {"id": "new-text", "snippet": {"type": "textMessageEvent", "displayMessage": "Current text"}}
    poller._make_api_call = AsyncMock(return_value={"items": [live]})
    assert asyncio.run(poll_messages(poller)) == [live]


@pytest.mark.parametrize("event_type,expected", [("messageDeletedEvent", "timeout_event"), ("userBannedEvent", "ban_event")])
def test_initial_moderation_events_are_not_replayed_but_live_events_are(event_type, expected):
    poll_messages = _poll_method()
    def item(identifier, timestamp):
        return {"id": identifier,
                "snippet": {"type": event_type, "displayMessage": "Moderation event",
                            "publishedAt": timestamp, "userBannedDetails": {
                                "bannedUserDetails": {"channelId": "target", "displayName": "Target"},
                                "banType": "temporary", "banDurationSeconds": 30}},
                "authorDetails": {"displayName": "Moderator", "channelId": "moderator"}}
    poller = SimpleNamespace(first_poll=True, live_chat_id="offline", connection_time=None,
                             channel_name="Channel", channel_id="channel", seen_event_ids=set(),
                             event_dedup_window={},
                             _make_api_call=AsyncMock(return_value={"items": [item("old", "old-time")]}),
                             _update_polling_interval=lambda *a: None,
                             _handle_polling_error=AsyncMock())
    assert asyncio.run(poll_messages(poller)) == []
    assert poller.first_poll is False
    poller._make_api_call = AsyncMock(return_value={"items": [item("new", "new-time")]})
    events = asyncio.run(poll_messages(poller))
    assert len(events) == 1
    assert events[0]["type"] == expected
    assert events[0]["is_live"] is True
    assert events[0]["moderator_id"] == "moderator"
    poller._handle_polling_error.assert_not_called()
