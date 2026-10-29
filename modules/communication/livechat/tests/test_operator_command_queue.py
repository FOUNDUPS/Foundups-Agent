"""Offline contracts using real queue/locks, disposable files and fake senders."""
import asyncio
import ast
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from modules.communication.livechat.src import operator_command_queue as module
from modules.communication.livechat.src.operator_command_queue import OperatorCommandQueue


class FakeLiveChat:
    def __init__(self):
        self.messages = []

    async def send_chat_message(self, message_text, response_type="general"):
        self.messages.append((message_text, response_type))
        return True


@pytest.fixture(autouse=True)
def isolated_gates(tmp_path, monkeypatch):
    monkeypatch.setenv("YT_AUTOMATION_STOP_FILE", str(tmp_path / "STOP"))
    for name in ("YT_AUTOMATION_ENABLED", "YT_LIVECHAT_SEND_ENABLED", "YT_LIVECHAT_ANNOUNCEMENTS_ENABLED", "YT_COMMENT_ENGAGEMENT_ENABLED"):
        monkeypatch.setenv(name, "true")
    monkeypatch.setenv("YT_LIVECHAT_DRY_RUN", "false")


def command(action="announce", command_id="voice-1", **payload):
    return {"id": command_id, "action": action, "payload": payload or {"message": "Hello"}}


def make_queue(tmp_path, commands=None, chat=True, **kwargs):
    sender = FakeLiveChat() if chat is True else chat
    queue = OperatorCommandQueue(SimpleNamespace(livechat=sender), tmp_path / "inbox.json",
                                 tmp_path / "acks.json", tmp_path / "state.json",
                                 poll_interval_seconds=0, **kwargs)
    queue.command_path.write_text(json.dumps({"version": 1, "commands": commands if commands is not None else [command()]}))
    return queue


def poll(queue):
    return asyncio.run(queue.poll_once())


def test_announce_is_claimed_once_across_restarts_and_reports_only_sender_acceptance(tmp_path):
    queue = make_queue(tmp_path)
    assert poll(queue)["results"][0]["status"] == "accepted"
    again = make_queue(tmp_path)
    assert poll(again)["processed"] == 0
    assert queue.dae.livechat.messages == [("Hello", "operator")]
    assert again.dae.livechat.messages == []
    receipt = json.loads(queue.state_path.read_text())["last_receipt"]
    assert receipt["health"] == "amber"
    assert receipt["result"] == {"sender_accepted": True, "delivery_verified": False}


def test_missing_chat_defers_with_durable_first_observation(tmp_path, monkeypatch):
    queue = make_queue(tmp_path, chat=None)
    monkeypatch.setattr(module.time, "time", lambda: 100)
    assert poll(queue)["results"][0]["status"] == "deferred"
    assert json.loads(queue.acknowledgement_path.read_text())["acknowledgements"][0]["first_seen_unix"] == 100
    queue.dae.livechat = FakeLiveChat()
    monkeypatch.setattr(module.time, "time", lambda: 110)
    assert poll(queue)["results"][0]["status"] == "accepted"
    assert len(queue.dae.livechat.messages) == 1


@pytest.mark.parametrize("fault", ["final_ledger", "receipt"])
def test_post_effect_write_failure_never_replays(tmp_path, monkeypatch, fault):
    queue = make_queue(tmp_path)
    original = queue._atomic_write
    def write(path, value):
        if (fault == "final_ledger" and path == queue.acknowledgement_path and value["acknowledgements"][0]["status"] == "accepted") or (fault == "receipt" and path == queue.state_path):
            raise OSError("injected storage failure")
        original(path, value)
    monkeypatch.setattr(queue, "_atomic_write", write)
    with pytest.raises(OSError):
        poll(queue)
    restarted = make_queue(tmp_path)
    assert poll(restarted)["processed"] == 0
    assert len(queue.dae.livechat.messages) == 1
    assert restarted.dae.livechat.messages == []
    stored = json.loads(queue.acknowledgement_path.read_text())["acknowledgements"][0]
    assert stored["status"] == ("unknown" if fault == "final_ledger" else "accepted")


def test_failed_preclaim_prevents_effect(tmp_path, monkeypatch):
    queue = make_queue(tmp_path)
    def fail(*args):
        raise OSError("unwritable")
    monkeypatch.setattr(queue, "_atomic_write", fail)
    with pytest.raises(OSError):
        poll(queue)
    assert queue.dae.livechat.messages == []


@pytest.mark.parametrize("content", ["{broken", "[]", '{"version":1,"acknowledgements":null}',
                                     '{"version":1,"acknowledgements":[{"id":"x","status":"deferred"}]}'])
def test_corrupt_ledger_is_preserved_and_blocks_all_effects(tmp_path, content):
    queue = make_queue(tmp_path)
    queue.acknowledgement_path.write_text(content)
    with pytest.raises(ValueError):
        poll(queue)
    assert queue.acknowledgement_path.read_text() == content
    assert queue.dae.livechat.messages == []


@pytest.mark.parametrize("invalid", [None, [], {"version": True, "commands": []}, {"version": 1, "commands": None},
                                      {"version": 1, "commands": [{"id": []}]}])
def test_malformed_inbox_fails_closed(tmp_path, invalid):
    queue = make_queue(tmp_path)
    queue.command_path.write_text(json.dumps(invalid))
    with pytest.raises(ValueError):
        poll(queue)
    assert queue.dae.livechat.messages == []


def test_unknown_action_and_payload_are_rejected(tmp_path):
    queue = make_queue(tmp_path, [command("run_shell"), {"id": "bad", "action": "announce", "payload": []}])
    assert [r["status"] for r in poll(queue)["results"]] == ["rejected", "rejected"]
    assert queue.dae.livechat.messages == []
    assert json.loads(queue.state_path.read_text())["last_receipt"]["health"] == "red"


def test_conflicting_id_rejected_and_legacy_terminal_ack_remains_terminal(tmp_path):
    queue = make_queue(tmp_path, [command(), command(message="changed")])
    with pytest.raises(ValueError, match="conflicting_command_id"):
        poll(queue)
    assert queue.dae.livechat.messages == []
    queue = make_queue(tmp_path)
    queue.acknowledgement_path.write_text(json.dumps({"version": 1, "acknowledgements": [{"id": "voice-1", "status": "accepted"}]}))
    assert poll(queue)["processed"] == 0


def test_pending_id_payload_mutation_is_rejected(tmp_path):
    queue = make_queue(tmp_path, chat=None)
    poll(queue)
    before = queue.acknowledgement_path.read_bytes()
    queue = make_queue(tmp_path, [command(message="changed")])
    with pytest.raises(ValueError, match="command_id_payload_changed"):
        poll(queue)
    assert queue.acknowledgement_path.read_bytes() == before
    assert queue.dae.livechat.messages == []


def test_conflict_later_in_inbox_prevents_earlier_new_effect(tmp_path):
    queue = make_queue(tmp_path, chat=None)
    poll(queue)
    queue = make_queue(tmp_path, [command(command_id="new"), command(message="changed")])
    with pytest.raises(ValueError, match="command_id_payload_changed"):
        poll(queue)
    assert queue.dae.livechat.messages == []


def test_identical_duplicate_pending_is_processed_once_and_old_reason_is_removed(tmp_path):
    queue = make_queue(tmp_path, [command(), command()], chat=None)
    assert poll(queue)["processed"] == 1
    queue.dae.livechat = FakeLiveChat()
    result = poll(queue)
    assert result["processed"] == 1
    assert "reason" not in result["results"][0]


@pytest.mark.parametrize("advance,expected", [(10, "accepted"), (60, "expired"), (1000, "expired")])
def test_deferred_context_does_not_extend_ttl(tmp_path, monkeypatch, advance, expected):
    queue = make_queue(tmp_path, [command("set_context", ttl_seconds=60, message="Update")], chat=None)
    monkeypatch.setattr(module.time, "time", lambda: 100)
    assert poll(queue)["results"][0]["status"] == "deferred"
    assert json.loads(queue.state_path.read_text())["active_context"] is None
    monkeypatch.setattr(module.time, "time", lambda: 100 + advance)
    queue.dae.livechat = FakeLiveChat()
    assert poll(queue)["results"][0]["status"] == expected
    state = json.loads(queue.state_path.read_text())
    if expected == "accepted":
        assert state["active_context"]["expires_at_unix"] == 160
    else:
        assert state["active_context"] is None
        assert queue.dae.livechat.messages == []


@pytest.mark.parametrize("newer", [
    {"id": "new", "action": "clear_context", "payload": {}},
    {"id": "new", "action": "set_context", "payload": {"message": "New", "surfaces": ["comments"]}},
])
def test_pending_context_cannot_resurrect_cleared_or_superseded_context(tmp_path, newer):
    queue = make_queue(tmp_path, [command("set_context"), newer], chat=None)
    assert poll(queue)["results"][0]["status"] == "deferred"
    before = json.loads(queue.state_path.read_text())["active_context"]
    queue.dae.livechat = FakeLiveChat()
    assert poll(queue)["results"][0]["status"] == "superseded"
    assert json.loads(queue.state_path.read_text())["active_context"] == before
    assert queue.dae.livechat.messages == []


@pytest.mark.parametrize("payload", [{"message": "X" * 201}, {"message": "X", "surfaces": [None]},
                                     {"message": "X", "surfaces": [{}]}, {"message": "X", "ttl_seconds": True}])
def test_invalid_context_has_no_effect(tmp_path, payload):
    queue = make_queue(tmp_path, [command("set_context", **payload)])
    assert poll(queue)["results"][0]["status"] == "rejected"
    assert json.loads(queue.state_path.read_text())["active_context"] is None
    assert queue.dae.livechat.messages == []


@pytest.mark.parametrize("gate", ["YT_AUTOMATION_ENABLED", "YT_LIVECHAT_SEND_ENABLED", "YT_LIVECHAT_ANNOUNCEMENTS_ENABLED", "YT_COMMENT_ENGAGEMENT_ENABLED", "STOP"])
def test_closed_gate_prevents_context_and_send(tmp_path, monkeypatch, gate):
    queue = make_queue(tmp_path, [command("set_context")])
    if gate == "STOP":
        (tmp_path / "STOP").touch()
    else:
        monkeypatch.setenv(gate, "false")
    assert poll(queue)["results"][0]["status"] == "blocked"
    assert json.loads(queue.state_path.read_text())["active_context"] is None
    assert queue.dae.livechat.messages == []


def test_dry_run_is_simulated_without_context_or_sender_effect(tmp_path, monkeypatch):
    queue = make_queue(tmp_path, [command("set_context")])
    monkeypatch.setenv("YT_LIVECHAT_DRY_RUN", "true")
    assert poll(queue)["results"][0]["status"] == "simulated"
    assert queue.dae.livechat.messages == []
    assert json.loads(queue.state_path.read_text())["active_context"] is None


def test_comments_only_context_retains_500_character_contract(tmp_path):
    queue = make_queue(tmp_path, [command("set_context", message="X" * 500, surfaces=["comments"])])
    assert poll(queue)["results"][0]["status"] == "accepted"
    assert queue.dae.livechat.messages == []


@pytest.mark.parametrize("behavior", ["exception", "timeout", "false", "wrong_type"])
def test_ambiguous_sender_result_is_terminal_unknown(tmp_path, behavior):
    class Uncertain:
        async def send_chat_message(self, *args, **kwargs):
            if behavior == "exception":
                raise RuntimeError("unknown provider result")
            if behavior == "timeout":
                await asyncio.sleep(10)
            return False if behavior == "false" else "sent"
    queue = make_queue(tmp_path, chat=Uncertain(), dispatch_timeout_seconds=0.02)
    assert poll(queue)["results"][0]["status"] == "unknown"
    assert poll(make_queue(tmp_path))["processed"] == 0


def test_concurrent_instances_and_cancellation_do_not_replay(tmp_path):
    async def run():
        entered = asyncio.Event()
        class Waiting:
            async def send_chat_message(self, *args, **kwargs):
                entered.set()
                await asyncio.Event().wait()
        first = make_queue(tmp_path, chat=Waiting())
        second = make_queue(tmp_path)
        task = asyncio.create_task(first.poll_once())
        await entered.wait()
        assert (await second.poll_once())["status"] == "busy"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert (await second.poll_once())["processed"] == 0
        assert second.dae.livechat.messages == []
    asyncio.run(run())


def test_watcher_survives_corrupt_input_and_cancels(tmp_path):
    async def run():
        queue = make_queue(tmp_path)
        queue.command_path.write_text("broken")
        task = asyncio.create_task(queue.watch_forever())
        await asyncio.sleep(0.02)
        assert not task.done()
        assert queue.last_result["status"] == "blocked"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())


@pytest.mark.parametrize("action,expected,watcher_state", [
    ("status", "accepted", "inactive"), ("announce", "accepted", "inactive"),
    ("run_shell", "rejected", "inactive"), ("announce", "accepted", "running"),
    ("announce", "accepted", "cancelled"), ("announce", "accepted", "stopped"),
])
def test_queue_result_reaches_real_heartbeat_writer_offline(tmp_path, monkeypatch, action, expected, watcher_state):
    # Compile the unmodified writer method, avoiding optional model/auth imports.
    # Actual queue, filesystem serialization and writer body execute; no full DAE.
    queue = make_queue(tmp_path, [command(action)])
    poll(queue)
    source = Path(module.__file__).with_name("youtube_dae_heartbeat.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "YouTubeDAEHeartbeat")
    method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_write_telemetry")
    namespace = {"Path": Path, "os": os, "json": json, "gate_snapshot": module.gate_snapshot,
                 "YouTubeHeartbeatData": object, "logger": logging.getLogger(__name__)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
    monkeypatch.chdir(tmp_path)
    instance = SimpleNamespace(dae=SimpleNamespace(operator_manifest_queue=queue))
    async def emit():
        watcher = None
        if watcher_state != "inactive":
            watcher = asyncio.create_task(asyncio.sleep(0 if watcher_state == "stopped" else 100))
            if watcher_state == "stopped":
                await watcher
            elif watcher_state == "cancelled":
                watcher.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await watcher
        instance.dae.operator_manifest_task = watcher
        try:
            await namespace["_write_telemetry"](instance, SimpleNamespace(to_dict=lambda: {"status": "fixture"}))
        finally:
            if watcher is not None and not watcher.done():
                watcher.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await watcher
    asyncio.run(emit())
    output = json.loads((tmp_path / "logs/youtube_dae_heartbeat.jsonl").read_text())
    assert output["operator_commands"] == queue.last_result
    assert output["operator_watcher"] == watcher_state
    assert output["operator_commands"]["results"][0]["status"] == expected
    if action == "announce":
        assert output["operator_commands"]["results"][0]["result"]["delivery_verified"] is False


_PROCESS = '''
import asyncio, json, os, sys, time
from pathlib import Path
from types import SimpleNamespace
from modules.communication.livechat.src.operator_command_queue import OperatorCommandQueue
root, mode = Path(sys.argv[1]), sys.argv[2]
class Sender:
    async def send_chat_message(self, *args, **kwargs):
        with (root / "effects").open("a") as stream:
            stream.write("attempt\\n")
        (root / "entered").touch()
        if mode == "crash": os._exit(17)
        if mode == "wait":
            while not (root / "release").exists(): await asyncio.sleep(0.01)
        return True
q = OperatorCommandQueue(SimpleNamespace(livechat=Sender()), root / "inbox.json", root / "acks.json", root / "state.json", poll_interval_seconds=0)
print(json.dumps(asyncio.run(q.poll_once())))
'''


@pytest.mark.parametrize("mode", ["wait", "crash"])
def test_real_process_lock_and_crash_restart(tmp_path, mode):
    make_queue(tmp_path)
    script = tmp_path / "worker.py"
    script.write_text(_PROCESS)
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[4]), PYTHONDONTWRITEBYTECODE="1")
    args = [sys.executable, "-B", str(script), str(tmp_path)]
    first = subprocess.Popen([*args, mode], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 15
        while not (tmp_path / "entered").exists() and time.monotonic() < deadline:
            if first.poll() is not None:
                break
            time.sleep(0.02)
        assert (tmp_path / "entered").exists(), first.communicate(timeout=2)
        if mode == "wait":
            busy = subprocess.run([*args, "normal"], env=env, capture_output=True, text=True, timeout=15, check=True)
            assert json.loads(busy.stdout)["status"] == "busy"
            (tmp_path / "release").touch()
        output, error = first.communicate(timeout=15)
        assert first.returncode == (17 if mode == "crash" else 0), error
        later = subprocess.run([*args, "normal"], env=env, capture_output=True, text=True, timeout=15, check=True)
        assert json.loads(later.stdout)["processed"] == 0
        assert (tmp_path / "effects").read_text() == "attempt\n"
    finally:
        if first.poll() is None:
            first.kill()
            first.communicate(timeout=5)
