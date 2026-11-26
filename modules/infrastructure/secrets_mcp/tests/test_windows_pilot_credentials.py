"""Offline tests: synthetic secrets and fake Win32 APIs only."""

import ctypes
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
PATH = ROOT / "modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py"
spec = importlib.util.spec_from_file_location("pilot_credentials_test_subject", PATH)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
LF = {"public_key": "pk-" + "lf-" + "synthetic_public", "secret_key": "sk-" + "lf-" + "synthetic_secret"}
OR = {"api_key": "sk-" + "or-" + "synthetic_credential_for_offline_test"}
SENTRY = {"dsn": "https://" + "a" * 32 + "@o1.ingest.us.sentry.io/1"}


class FakeApi:
    def __init__(self, value=None):
        self.value = value
        self.freed = 0
        self.written = None
        self.blob = None
        self.record = None

    def CredWriteW(self, pointer, flags):
        record = ctypes.cast(pointer, ctypes.POINTER(subject._Credential)).contents
        self.written = (record.TargetName, record.Type, record.Persist,
                        ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize), flags)
        return True

    def CredReadW(self, target, kind, flags, output):
        assert kind == 1 and flags == 0
        if self.value is None:
            return False
        self.blob = ctypes.create_string_buffer(self.value)
        self.record = subject._Credential()
        self.record.Type = kind
        self.record.TargetName = target
        self.record.CredentialBlobSize = len(self.value)
        self.record.CredentialBlob = ctypes.cast(self.blob, ctypes.POINTER(ctypes.c_ubyte))
        ctypes.cast(output, ctypes.POINTER(ctypes.POINTER(subject._Credential)))[0] = ctypes.pointer(self.record)
        return True

    def CredFree(self, pointer):
        self.freed += 1


def test_store_uses_only_dedicated_vault_target_and_current_machine_persistence(monkeypatch, capsys):
    api = FakeApi()
    monkeypatch.setattr(subject, "_api", lambda: api)
    subject.store_credentials("langfuse-viewer", LF)
    target, kind, persistence, blob, flags = api.written
    assert target == subject.TARGETS["langfuse-viewer"]
    assert (kind, persistence, flags) == (1, 2, 0)
    assert json.loads(blob) == LF
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind,values", [("langfuse-viewer", LF), ("openrouter-pilot", OR), ("sentry-errors", SENTRY)])
def test_read_validates_and_frees_allocated_win32_record(monkeypatch, kind, values):
    api = FakeApi(json.dumps(values).encode())
    monkeypatch.setattr(subject, "_api", lambda: api)
    assert subject._read_credentials(kind) == values
    assert api.freed == 1


@pytest.mark.parametrize("raw", [b"hostile secret raw text", b"[]", b'{"secret_key":"DO_NOT_ECHO"}', b"{}"])
def test_corrupt_vault_record_fails_without_exposing_blob(monkeypatch, raw):
    api = FakeApi(raw)
    monkeypatch.setattr(subject, "_api", lambda: api)
    with pytest.raises(subject.PilotCredentialError) as caught:
        subject._read_credentials("langfuse-viewer")
    assert raw.decode() not in str(caught.value)
    assert api.freed == 1


def test_oversized_record_refused_before_blob_read(monkeypatch):
    api = FakeApi(b"x" * (subject.MAX_BLOB_BYTES + 1))
    monkeypatch.setattr(subject, "_api", lambda: api)
    with pytest.raises(subject.PilotCredentialError, match="invalid_credential_record"):
        subject._read_credentials("openrouter-pilot")
    assert api.freed == 1


@pytest.mark.parametrize("kind,values", [("other", OR), ([], OR), ("openrouter-pilot", LF),
                                       ("langfuse-viewer", {**LF, "extra": "DO_NOT_ECHO"}),
                                       ("openrouter-pilot", {"api_key": "DO_NOT_ECHO"})])
def test_bad_target_or_shape_rejects_before_api(monkeypatch, kind, values):
    monkeypatch.setattr(subject, "_api", lambda: pytest.fail("vault must not be touched"))
    with pytest.raises(subject.PilotCredentialError) as caught:
        subject.store_credentials(kind, values)
    assert "DO_NOT_ECHO" not in str(caught.value)


def test_fixed_receiver_and_environment_injection_exclude_other_credentials(monkeypatch):
    monkeypatch.setattr(subject, "_read_credentials", lambda kind: dict(LF))
    monkeypatch.setenv("UNRELATED_SECRET_KEY", "NOT_FOR_CHILD")
    monkeypatch.setenv("PYTHONINSPECT", "1")
    captured = {}
    def fake_run(argv, **kwargs):
        captured.update({"argv": argv, "env": dict(kwargs["env"]), **{k:v for k,v in kwargs.items() if k != "env"}})
        return type("Result", (), {"returncode": 0})()
    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    assert subject.run_receiver("langfuse-viewer", ["--from-time", "2026-11-01T00:00:00Z",
                                                   "--to-time", "2026-11-02T00:00:00Z"]) == 0
    assert captured["argv"][2].endswith("scripts\\reddog_langfuse_review.py") or captured["argv"][2].endswith("scripts/reddog_langfuse_review.py")
    assert captured["argv"][3:5] == ["--base-url", subject.JP_BASE_URL]
    assert captured["env"]["LANGFUSE_SECRET_KEY"] == LF["secret_key"]
    assert "UNRELATED_SECRET_KEY" not in captured["env"]
    assert "PYTHONINSPECT" not in captured["env"]
    assert captured["shell"] is False and captured["timeout"] == 120


@pytest.mark.parametrize("args", [["--base-url", "https://other.example"], ["-c", "print('bad')"],
                                 ["--timeout"], ["--timeout", "1", "--timeout", "2"]])
def test_arbitrary_child_routes_rejected_before_secret_read(monkeypatch, args):
    monkeypatch.setattr(subject, "_read_credentials", lambda kind: pytest.fail("no secret read"))
    with pytest.raises(subject.PilotCredentialError):
        subject.run_receiver("langfuse-viewer", args)


def test_unexpected_exception_is_static_cli_error(monkeypatch, capsys):
    monkeypatch.setattr(subject, "run_receiver", lambda *args: (_ for _ in ()).throw(ValueError("SECRET_MUST_NOT_ECHO")))
    assert subject.main(["run", "--type", "openrouter-pilot"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "credential_operation_failed"


def test_noninteractive_store_fails_before_prompt(monkeypatch, capsys):
    monkeypatch.setattr(subject.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(subject.getpass, "getpass", lambda prompt: pytest.fail("no fallback input"))
    assert subject.main(["store", "--type", "langfuse-viewer"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "interactive_windows_terminal_required"


def test_unknown_cli_argument_never_echoes_value(capsys):
    assert subject.main(["run", "--type", "openrouter-pilot", "SECRET_MUST_NOT_ECHO"]) == 2
    assert "SECRET_MUST_NOT_ECHO" not in capsys.readouterr().out


def test_sentry_store_uses_exact_fixed_target(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(subject, "_api", lambda: api)
    subject.store_credentials("sentry-errors", SENTRY)
    assert api.written[0] == subject.TARGETS["sentry-errors"]
    assert json.loads(api.written[3]) == SENTRY


@pytest.mark.parametrize("dsn", ["http://PRIVATE.invalid/1", "https://PRIVATE@attacker.example/1",
                                SENTRY["dsn"] + "?PRIVATE", SENTRY["dsn"] + "/../PRIVATE"])
def test_sentry_dsn_uses_shared_strict_validator_before_vault(monkeypatch, dsn):
    monkeypatch.setattr(subject, "_api", lambda: pytest.fail("no vault call"))
    with pytest.raises(subject.PilotCredentialError) as caught:
        subject.store_credentials("sentry-errors", {"dsn": dsn})
    assert str(caught.value) == "invalid_credential_shape"


def test_sentry_receiver_is_fixed_and_injects_only_own_credentials(monkeypatch):
    reads, captured = [], {}
    monkeypatch.setattr(subject, "_SENTRY_RUNTIME", Path(subject.sys.executable))
    def read(kind):
        reads.append(kind)
        return dict(SENTRY)
    def run(argv, **kwargs):
        captured.update({"argv": list(argv), "env": dict(kwargs["env"])})
        return type("Result", (), {"returncode": 0})()
    monkeypatch.setattr(subject, "_read_credentials", read)
    monkeypatch.setattr(subject.subprocess, "run", run)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "PRIVATE")
    assert subject.run_receiver("sentry-errors", []) == 0
    assert reads == ["sentry-errors"]
    assert Path(captured["argv"][2]).name == "reddog_sentry_probe.py"
    assert captured["env"]["SENTRY_DSN"] == SENTRY["dsn"]
    assert captured["env"]["FOUNDUPS_SENTRY_ENABLED"] == "1"
    assert "LANGFUSE_SECRET_KEY" not in captured["env"]


def test_viewer_sentry_optin_reads_both_and_uses_sdk_runtime(monkeypatch):
    reads, captured = [], {}
    monkeypatch.setattr(subject, "_SENTRY_RUNTIME", Path(subject.sys.executable))
    def read(kind):
        reads.append(kind)
        return dict(SENTRY if kind == "sentry-errors" else LF)
    def run(argv, **kwargs):
        captured.update({"argv": list(argv), "env": dict(kwargs["env"])})
        return type("Result", (), {"returncode": 0})()
    monkeypatch.setattr(subject, "_read_credentials", read)
    monkeypatch.setattr(subject.subprocess, "run", run)
    args = ["--from-time", "2026-11-01T00:00:00Z", "--to-time", "2026-11-02T00:00:00Z"]
    assert subject.run_receiver("langfuse-viewer", args, with_sentry_errors=True) == 0
    assert reads == ["langfuse-viewer", "sentry-errors"]
    assert captured["argv"][0] == str(subject._SENTRY_RUNTIME)
    assert Path(captured["argv"][2]).name == "reddog_langfuse_review.py"
    assert captured["env"]["LANGFUSE_SECRET_KEY"] == LF["secret_key"]
    assert captured["env"]["SENTRY_DSN"] == SENTRY["dsn"]
    assert captured["env"]["FOUNDUPS_SENTRY_ENABLED"] == "1"


def test_viewer_default_never_reads_or_enables_sentry(monkeypatch):
    reads, captured = [], {}
    def read(kind):
        reads.append(kind)
        return dict(LF)
    def run(argv, **kwargs):
        captured.update(dict(kwargs["env"]))
        return type("Result", (), {"returncode": 0})()
    monkeypatch.setattr(subject, "_read_credentials", read)
    monkeypatch.setattr(subject.subprocess, "run", run)
    monkeypatch.setenv("SENTRY_DSN", "PRIVATE")
    monkeypatch.setenv("FOUNDUPS_SENTRY_ENABLED", "1")
    assert subject.run_receiver("langfuse-viewer", []) == 0
    assert reads == ["langfuse-viewer"]
    assert "SENTRY_DSN" not in captured and "FOUNDUPS_SENTRY_ENABLED" not in captured


@pytest.mark.parametrize("kind,flag,args", [("openrouter-pilot", True, []), ("sentry-errors", True, []),
                                          ("sentry-errors", False, ["-c", "PRIVATE"])])
def test_invalid_sentry_routes_reject_before_secret_read(monkeypatch, kind, flag, args):
    monkeypatch.setattr(subject, "_read_credentials", lambda kind: pytest.fail("no credential read"))
    with pytest.raises(subject.PilotCredentialError):
        subject.run_receiver(kind, args, with_sentry_errors=flag)


def test_missing_fixed_sentry_runtime_refuses_before_read(monkeypatch, tmp_path):
    monkeypatch.setattr(subject, "_SENTRY_RUNTIME", tmp_path / "absent.exe")
    monkeypatch.setattr(subject, "_read_credentials", lambda kind: pytest.fail("no credential read"))
    with pytest.raises(subject.PilotCredentialError, match="pilot_runtime_unavailable"):
        subject.run_receiver("sentry-errors", [])
