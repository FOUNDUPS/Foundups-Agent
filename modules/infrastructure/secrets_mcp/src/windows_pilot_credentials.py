"""Explicit Windows vault custody for the bounded FOUNDUPS telemetry pilot.

This principal-operated adapter is not a WRE secret permission grant. Secrets
remain in Credential Manager and are delivered only to fixed telemetry receivers.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import getpass
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Mapping


TARGETS = {
    "langfuse-viewer": "FOUNDUPS/telemetry-pilot/langfuse-jp-viewer/v1",
    "openrouter-pilot": "FOUNDUPS/telemetry-pilot/openrouter/v1",
    "sentry-errors": "FOUNDUPS/telemetry-pilot/sentry-errors/v1",
}
JP_BASE_URL = "https://jp.cloud.langfuse.com"
MAX_BLOB_BYTES = 2560
_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_REPO = Path(__file__).resolve().parents[4]
_SENTRY_RUNTIME = Path.home() / ".codex/telemetry-runtimes/sentry-pilot/Scripts/python.exe"
_READ_FLAGS = {"--from-time", "--to-time", "--trace-id", "--max-pages", "--timeout"}
_ENV_KEEP = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP",
             "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL"}


class PilotCredentialError(RuntimeError):
    """A static, credential-free failure code."""


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)), ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
    ]


def _api():
    if os.name != "nt":
        raise PilotCredentialError("windows_required")
    try:
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        api.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
        api.CredWriteW.restype = wintypes.BOOL
        api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.POINTER(ctypes.POINTER(_Credential))]
        api.CredReadW.restype = wintypes.BOOL
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredFree.restype = None
        return api
    except Exception:
        raise PilotCredentialError("credential_vault_unavailable") from None


def _target(kind: str) -> str:
    if not isinstance(kind, str) or kind not in TARGETS:
        raise PilotCredentialError("unsupported_credential_type")
    return TARGETS[kind]


def _validated(kind: str, values: Mapping[str, str]) -> dict[str, str]:
    _target(kind)
    expected = {"langfuse-viewer": {"public_key", "secret_key"},
                "openrouter-pilot": {"api_key"}, "sentry-errors": {"dsn"}}[kind]
    if not isinstance(values, Mapping) or set(values) != expected:
        raise PilotCredentialError("invalid_credential_shape")
    if kind == "sentry-errors":
        source = _REPO / "modules/infrastructure/monitoring/src/sentry_error_telemetry.py"
        spec = importlib.util.spec_from_file_location("bounded_sentry_dsn_validator", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not module._dsn_valid(values["dsn"]):
            raise PilotCredentialError("invalid_credential_shape")
        return dict(values)
    patterns = {"public_key": r"pk-lf-[A-Za-z0-9_-]{8,256}",
                "secret_key": r"sk-lf-[A-Za-z0-9_-]{8,256}",
                "api_key": r"sk-or-[A-Za-z0-9_-]{20,256}"}
    if any(not isinstance(value, str) or not re.fullmatch(patterns[key], value)
           for key, value in values.items()):
        raise PilotCredentialError("invalid_credential_shape")
    return dict(values)


def store_credentials(kind: str, values: Mapping[str, str]) -> None:
    """Write only an allowlisted dedicated target; never emit secret values."""
    target = _target(kind)
    encoded = json.dumps(_validated(kind, values), separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_BLOB_BYTES:
        raise PilotCredentialError("credential_too_large")
    api = _api()
    blob = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
    credential = _Credential()
    credential.Type = _CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.Comment = "FOUNDUPS bounded telemetry pilot; current Windows account only"
    credential.CredentialBlobSize = len(encoded)
    credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = "FOUNDUPS-telemetry-pilot"
    try:
        if not api.CredWriteW(ctypes.byref(credential), 0):
            raise PilotCredentialError("credential_store_failed")
    except PilotCredentialError:
        raise
    except Exception:
        raise PilotCredentialError("credential_store_failed") from None
    finally:
        ctypes.memset(blob, 0, len(blob))


def _read_credentials(kind: str) -> dict[str, str]:
    target = _target(kind)
    api = _api()
    pointer = ctypes.POINTER(_Credential)()
    try:
        if not api.CredReadW(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
            raise PilotCredentialError("credential_unavailable")
        try:
            record = pointer.contents
            if (record.Type != _CRED_TYPE_GENERIC or record.TargetName != target
                    or not 0 < record.CredentialBlobSize <= MAX_BLOB_BYTES
                    or not record.CredentialBlob):
                raise PilotCredentialError("invalid_credential_record")
            raw = ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize)
            return _validated(kind, json.loads(raw.decode("utf-8")))
        finally:
            api.CredFree(pointer)
    except PilotCredentialError:
        raise
    except Exception:
        raise PilotCredentialError("credential_read_failed") from None


def _receiver_argv(kind: str, args: list[str], *, with_sentry_errors: bool = False) -> list[str]:
    _target(kind)
    if with_sentry_errors and kind != "langfuse-viewer":
        raise PilotCredentialError("sentry_flag_requires_viewer")
    if kind in {"openrouter-pilot", "sentry-errors"}:
        if args:
            raise PilotCredentialError("probe_takes_no_arguments")
        filename = "reddog_sentry_probe.py" if kind == "sentry-errors" else "reddog_openrouter_telemetry_probe.py"
        receiver = _REPO / "scripts" / filename
        forwarded = []
    else:
        if len(args) % 2 or any(args[i] not in _READ_FLAGS for i in range(0, len(args), 2)):
            raise PilotCredentialError("invalid_review_arguments")
        if len({args[i] for i in range(0, len(args), 2)}) != len(args) // 2:
            raise PilotCredentialError("duplicate_review_arguments")
        receiver = _REPO / "scripts/reddog_langfuse_review.py"
        forwarded = ["--base-url", JP_BASE_URL, *args]
    if not receiver.is_file():
        raise PilotCredentialError("pilot_receiver_unavailable")
    runtime = _SENTRY_RUNTIME if kind == "sentry-errors" or with_sentry_errors else Path(sys.executable)
    if not runtime.is_file():
        raise PilotCredentialError("pilot_runtime_unavailable")
    return [str(runtime), "-B", str(receiver), *forwarded]


def run_receiver(kind: str, args: list[str], *, with_sentry_errors: bool = False) -> int:
    """Inject into one fixed receiver, not the parent or persistent environment."""
    argv = _receiver_argv(kind, args, with_sentry_errors=with_sentry_errors)
    values, sentry_values, env = {}, {}, {}
    try:
        values = _read_credentials(kind)
        if with_sentry_errors:
            sentry_values = _read_credentials("sentry-errors")
        for credential_type in ([kind, "sentry-errors"] if with_sentry_errors else [kind]):
            print(json.dumps({"event": "pilot_credential_read", "credential_type": credential_type,
                              "status": "prepared_for_fixed_receiver"}), file=sys.stderr)
        env = {key: value for key, value in os.environ.items() if key.upper() in _ENV_KEEP}
        env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
        if kind == "langfuse-viewer":
            env.update({"LANGFUSE_PUBLIC_KEY": values["public_key"], "LANGFUSE_SECRET_KEY": values["secret_key"]})
        elif kind == "openrouter-pilot":
            env["OPENROUTER_API_KEY"] = values["api_key"]
        if kind == "sentry-errors" or with_sentry_errors:
            env.update({"SENTRY_DSN": (values if kind == "sentry-errors" else sentry_values)["dsn"],
                        "FOUNDUPS_SENTRY_ENABLED": "1"})
        return int(subprocess.run(argv, env=env, cwd=_REPO, shell=False,
                                  check=False, timeout=120).returncode)
    except PilotCredentialError:
        raise
    except Exception:
        raise PilotCredentialError("pilot_receiver_failed") from None
    finally:
        values.clear()
        sentry_values.clear()
        env.clear()


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise PilotCredentialError("invalid_arguments")


def main(argv: list[str] | None = None) -> int:
    parser = _SafeParser(description=__doc__)
    parser.add_argument("action", choices=("store", "run"))
    parser.add_argument("--type", required=True, choices=tuple(TARGETS))
    parser.add_argument("--with-sentry-errors", action="store_true")
    try:
        source = sys.argv[1:] if argv is None else argv
        split = source.index("--") if "--" in source else len(source)
        options = parser.parse_args(source[:split])
        remainder = source[split + 1:] if split < len(source) else []
        if options.action == "store":
            if options.with_sentry_errors or remainder or os.name != "nt" or not sys.stdin.isatty():
                raise PilotCredentialError("interactive_windows_terminal_required")
            if options.type == "langfuse-viewer":
                values = {"public_key": getpass.getpass("Langfuse Viewer public key (hidden): "),
                          "secret_key": getpass.getpass("Langfuse Viewer secret key (hidden): ")}
            elif options.type == "openrouter-pilot":
                values = {"api_key": getpass.getpass("OpenRouter pilot key (hidden): ")}
            else:
                values = {"dsn": getpass.getpass("Sentry error DSN (hidden): ")}
            try:
                store_credentials(options.type, values)
            finally:
                values.clear()
            print(json.dumps({"ok": True, "status": "stored_in_windows_vault",
                              "credential_type": options.type}))
            return 0
        return run_receiver(options.type, remainder, with_sentry_errors=options.with_sentry_errors)
    except (EOFError, KeyboardInterrupt):
        print('{"ok":false,"status":"credential_entry_cancelled"}')
        return 2
    except PilotCredentialError as exc:
        print(json.dumps({"ok": False, "status": str(exc)}))
        return 2
    except Exception:
        print('{"ok":false,"status":"credential_operation_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
