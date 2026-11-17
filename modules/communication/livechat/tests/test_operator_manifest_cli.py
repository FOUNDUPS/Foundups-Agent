"""Credential-free local producer contracts; no daemon or public effects."""

import io
import json
from types import SimpleNamespace

import pytest

from modules.communication.livechat.scripts import operator_manifest as cli


def options(tmp_path, operation="enqueue", **changes):
    args = SimpleNamespace(operation=operation, input=str(tmp_path / "command.json"),
                           id=None, manifest=tmp_path / "inbox.json",
                           acknowledgements=tmp_path / "acks.json", state=tmp_path / "state.json")
    for key, value in changes.items():
        setattr(args, key, value)
    return args


def write_command(args, command=None):
    command = command or {"action": "set_context", "payload": {"message": "private direction"}}
    with open(args.input, "w", encoding="utf-8") as handle:
        json.dump(command, handle)


def test_enqueue_preserves_work_and_does_not_activate(tmp_path):
    args = options(tmp_path)
    previous = {"id": "retained", "action": "status", "payload": {}}
    args.manifest.write_text(json.dumps({"version": 1, "commands": [previous]}))
    write_command(args)
    result = cli.run(args)
    commands = json.loads(args.manifest.read_text())["commands"]
    assert commands[0] == previous
    assert commands[1]["id"] == result["id"]
    assert commands[1]["payload"]["ttl_seconds"] == 3600
    assert result["queued"] and not result["received"] and not result["active"]
    assert not args.acknowledgements.exists() and not args.state.exists()
    assert "private direction" not in json.dumps(result)


def test_unique_ids_and_duplicate_refusal_preserve_inbox(tmp_path):
    args = options(tmp_path)
    write_command(args)
    first, second = cli.run(args), cli.run(args)
    assert first["id"] != second["id"]
    before = args.manifest.read_bytes()
    write_command(args, {"id": first["id"], "action": "status", "payload": {}})
    with pytest.raises(ValueError, match="command_id_already_exists"):
        cli.run(args)
    assert args.manifest.read_bytes() == before


@pytest.mark.parametrize("raw", [b"[]", b"{", b'{"action":"status","payload":[]}',
    b'{"action":"status","payload":{},"extra":1}',
    b'{"action":"status","payload":{"value":NaN}}'])
def test_invalid_input_cannot_change_queue(tmp_path, raw):
    args = options(tmp_path)
    with open(args.input, "wb") as handle:
        handle.write(raw)
    with pytest.raises((ValueError, TypeError)):
        cli.run(args)
    assert not args.manifest.exists() and not args.acknowledgements.exists()


def test_bounded_input_and_explicit_duration():
    with pytest.raises(ValueError, match="command_input_too_large"):
        cli.read_command(stream=io.BytesIO(b" " * (cli.MAX_INPUT_BYTES + 1)))
    command = cli.read_command(stream=io.BytesIO(
        b'{"action":"set_context","payload":{"message":"guide","ttl_seconds":120}}'))
    assert command["payload"]["ttl_seconds"] == 120


def test_duration_starts_when_instruction_is_enqueued(monkeypatch):
    monkeypatch.setattr(cli.time, "time", lambda: 100)
    command = cli.read_command(stream=io.BytesIO(
        b'{"action":"set_video_policy","payload":{"ttl_seconds":120}}'))
    assert command["payload"]["expires_at_unix"] == 220
    stale = cli.read_command(stream=io.BytesIO(
        b'{"action":"set_context","payload":{"ttl_seconds":120,"expires_at_unix":90}}'))
    assert stale["payload"]["expires_at_unix"] == 90


@pytest.mark.parametrize("duration", [True, 0, 86401, "3600"])
def test_invalid_duration_is_not_queued(duration):
    raw = json.dumps({"action": "set_context", "payload": {"ttl_seconds": duration}}).encode()
    with pytest.raises(ValueError, match="invalid_command_input"):
        cli.read_command(stream=io.BytesIO(raw))


def test_state_inbox_alias_is_rejected_before_producer_write(tmp_path):
    args = options(tmp_path)
    args.state = args.manifest
    write_command(args)
    with pytest.raises(ValueError, match="manifest_paths_must_be_distinct"):
        cli.run(args)
    assert not args.manifest.exists()


def test_inspection_does_not_consume_queued_command(tmp_path):
    args = options(tmp_path)
    write_command(args)
    queued = cli.run(args)
    before = args.manifest.read_bytes()
    inspected = cli.run(options(tmp_path, "inspect", id=queued["id"]))
    assert inspected["queued"] and not inspected["received"]
    assert args.manifest.read_bytes() == before
    assert not args.acknowledgements.exists() and not args.state.exists()


def test_main_output_never_echoes_private_payload(tmp_path, capsys):
    args = options(tmp_path)
    write_command(args)
    code = cli.main(["enqueue", "--input", args.input, "--manifest", str(args.manifest),
                     "--acknowledgements", str(args.acknowledgements)])
    output = capsys.readouterr().out
    assert code == 0 and json.loads(output)["queued"]
    assert "private direction" not in output
