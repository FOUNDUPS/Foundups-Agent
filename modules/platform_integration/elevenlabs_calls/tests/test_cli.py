"""CLI and actual shared speech-adapter concatenation, with no paid API access."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from modules.platform_integration.elevenlabs_calls.src import cli, speech
from .test_calls import CONTACTS, JOB, Provider


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    job, contacts = tmp_path / "job.json", tmp_path / "contacts.json"
    job.write_text(json.dumps(JOB))
    contacts.write_text(json.dumps(CONTACTS))
    provider = Provider()
    provider.create_agent = lambda cfg: {"agent_id": "new_agent"}
    monkeypatch.setattr(cli, "_client", lambda: provider)
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_test")
    monkeypatch.setenv("ELEVENLABS_PHONE_NUMBER_ID", "phone_test")
    args = ["call", "--request", str(job), "--contacts", str(contacts),
            "--journal", str(tmp_path / "calls.sqlite3")]

    def invoke(extra=None, alternate=None):
        code = cli.main(alternate if alternate is not None else args + (extra or []))
        return code, json.loads(capsys.readouterr().out)
    return SimpleNamespace(invoke=invoke, provider=provider, args=args, tmp_path=tmp_path)


def test_preview_is_offline_and_side_effect_free(run, monkeypatch):
    monkeypatch.setattr(cli, "_client", lambda: pytest.fail("must not access API"))
    code, out = run.invoke(["--dry-run", "--listen", "--json"])
    assert code == 0 and out["status"] == "preview"
    assert out["data"]["request"]["message_ja"] == JOB["message_ja"]
    assert not (run.tmp_path / "calls.sqlite3").exists()


def test_execute_and_status(run):
    assert run.invoke(["--execute"])[1]["status"] == "submitted"
    assert run.invoke(["--execute"])[1]["data"]["duplicate_suppressed"]
    code, out = run.invoke(alternate=["status", "--request-id", JOB["request_id"],
                                      "--journal", str(run.tmp_path / "calls.sqlite3")])
    assert code == 0 and out["status"] == "ended"
    assert out["data"]["delivery"] == "unconfirmed"


@pytest.mark.parametrize("utterance,expected", [("make this call", "submitted"),
                                              ("この電話をかけて。", "submitted"),
                                              ("don't make this call", "cancelled")])
def test_spoken_request_uses_shared_whisper_and_capture(run, monkeypatch, utterance, expected):
    from modules.infrastructure.cli.src import openclaw_voice as voice
    from modules.communication.voice_command_ingestion.src.voice_command_ingestion import FasterWhisperSTT, STTEvent
    monkeypatch.setattr(voice, "record_until_silence", lambda **kw: np.zeros(16000, dtype=np.float32))
    monkeypatch.setattr(FasterWhisperSTT, "transcribe", lambda self, audio, sr:
                        STTEvent(utterance, True, 0, 1000))
    code, out = run.invoke(["--execute", "--listen"])
    assert code == 0 and out["status"] == expected
    assert len(run.provider.calls) == (1 if expected == "submitted" else 0)


def test_provision_and_doctor(run, monkeypatch):
    assert run.invoke(alternate=["provision", "--voice-id", "test"])[1]["status"] == "preview"
    assert run.invoke(alternate=["provision", "--voice-id", "test", "--execute"])[1]["status"] == "agent_created"
    run.provider.create_agent = lambda cfg: {}
    assert run.invoke(alternate=["provision", "--voice-id", "test", "--execute"])[0] == 1
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    code, out = run.invoke(alternate=["doctor", "--json"])
    assert code == 0 and not out["data"]["configuration_present"]
    assert "live_connection" in out["data"]


def test_errors_are_json_and_do_not_dial(run, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_AGENT_ID")
    assert run.invoke(["--execute"])[0] == 1
    assert run.provider.calls == []
    monkeypatch.setattr(cli, "_run", lambda args: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert run.invoke()[1]["status"] == "interrupted"


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="missing"):
        cli._client()


@pytest.mark.parametrize("text,allowed", [("Make this call!", True), ("０１０２ make this call", True),
                                         ("please make this call later", False), ("cancel", False)])
def test_trigger_requires_whole_command(text, allowed):
    assert speech.is_call_trigger(text) == allowed


@pytest.mark.parametrize("available,audio,text,match", [(False, None, None, "unavailable"),
    (True, None, None, "captured"), (True, [0], "", "recognized"), (True, [0], "make this call", None)])
def test_cohere_capture_failures_and_success(monkeypatch, available, audio, text, match):
    from modules.infrastructure.cli.src import openclaw_voice as voice
    backend = SimpleNamespace(available=lambda: available, transcribe=lambda a: text)
    monkeypatch.setattr(voice, "CohereTranscribeBackend", lambda language: backend)
    monkeypatch.setattr(voice, "record_until_silence", lambda **kw: audio)
    if match:
        with pytest.raises(ValueError, match=match):
            speech.listen_once("ja", "cohere")
    else:
        assert speech.listen_once("en", "cohere") == text
