import asyncio
import json
from types import SimpleNamespace

from modules.communication.livechat.src.operator_command_queue import OperatorCommandQueue


class FakeLiveChat:
    def __init__(self):
        self.messages = []

    async def send_chat_message(self, message_text, skip_delay=False, response_type="general"):
        self.messages.append((message_text, response_type))
        return True


def _write_commands(path, commands):
    path.write_text(json.dumps({"version": 1, "commands": commands}), encoding="utf-8")


def test_announce_is_dispatched_once_and_acknowledged(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_AUTOMATION_ENABLED", "true")
    monkeypatch.setenv("YT_LIVECHAT_SEND_ENABLED", "true")
    command_path, acknowledgement_path = tmp_path / "commands.json", tmp_path / "acks.json"
    _write_commands(command_path, [{"id": "voice-1", "action": "announce", "payload": {"message": "Hello live chat"}}])
    chat = FakeLiveChat()
    queue = OperatorCommandQueue(SimpleNamespace(livechat=chat), command_path, acknowledgement_path, poll_interval_seconds=0)
    assert asyncio.run(queue.poll_once())["processed"] == 1
    assert asyncio.run(queue.poll_once())["processed"] == 0
    assert chat.messages == [("Hello live chat", "operator")]
    assert json.loads(acknowledgement_path.read_text())["acknowledgements"][0]["status"] == "accepted"


def test_unknown_action_is_rejected_without_touching_livechat(tmp_path):
    command_path, acknowledgement_path = tmp_path / "commands.json", tmp_path / "acks.json"
    _write_commands(command_path, [{"id": "voice-2", "action": "run_shell", "payload": {}}])
    chat = FakeLiveChat()
    result = asyncio.run(OperatorCommandQueue(SimpleNamespace(livechat=chat), command_path, acknowledgement_path).poll_once())
    assert result["results"][0]["status"] == "rejected"
    assert chat.messages == []
