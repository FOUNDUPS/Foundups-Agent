"""Synthetic explicit credential-source checks; never read a machine .env file."""
from __future__ import annotations

import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("langfuse_env_cli_test", ROOT / "scripts/reddog_langfuse_review.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)
VIEWER = {"LANGFUSE_VIEWER_PUBLIC_KEY": "viewer-public-synthetic", "LANGFUSE_VIEWER_SECRET_KEY": "viewer-secret-synthetic"}
LEGACY = {"LANGFUSE_PUBLIC_KEY": "legacy-public-synthetic", "LANGFUSE_SECRET_KEY": "legacy-secret-synthetic"}


def env_file(tmp_path, text):
    path = tmp_path / "private-path-canary.env"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("explicit", [False, True])
def test_complete_viewer_pair_preferred_without_environment_mutation(tmp_path, explicit):
    values = {**LEGACY, **VIEWER}
    path = env_file(tmp_path, "\n".join(f'{key}="{value}"' for key, value in values.items()))
    with mock.patch.dict(os.environ, values, clear=True):
        before = dict(os.environ)
        assert cli.credential_pair(path if explicit else None) == tuple(VIEWER.values())
        assert dict(os.environ) == before


@pytest.mark.parametrize("missing", list(VIEWER))
@pytest.mark.parametrize("explicit", [False, True])
def test_partial_viewer_pair_never_falls_back_to_legacy(tmp_path, missing, explicit):
    values = {**LEGACY, **VIEWER}
    values.pop(missing)
    path = env_file(tmp_path, "\n".join(f"{key}={value}" for key, value in values.items()))
    with mock.patch.dict(os.environ, values, clear=True), pytest.raises(cli.CredentialError, match="^credentials_incomplete$"):
        cli.credential_pair(path if explicit else None)


def test_explicit_file_is_authoritative_and_does_not_mix_partial_pairs(tmp_path):
    path = env_file(tmp_path, "LANGFUSE_PUBLIC_KEY=file-public\n")
    with mock.patch.dict(os.environ, {**LEGACY, **VIEWER}, clear=True), pytest.raises(cli.CredentialError, match="^credentials_incomplete$"):
        cli.credential_pair(path)


def test_file_legacy_fallback_and_no_process_interpolation(tmp_path):
    path = env_file(tmp_path, "LANGFUSE_PUBLIC_KEY=file-public\nLANGFUSE_SECRET_KEY=${PRIVATE_CANARY}\n")
    with mock.patch.dict(os.environ, {**VIEWER, "PRIVATE_CANARY": "do-not-interpolate"}, clear=True):
        assert cli.credential_pair(path) == ("file-public", "${PRIVATE_CANARY}")


def test_process_legacy_fallback_does_not_discover_files():
    with mock.patch.dict(os.environ, LEGACY, clear=True), mock.patch.object(cli.Path, "open", side_effect=AssertionError("no file reads")):
        assert cli.credential_pair() == tuple(LEGACY.values())


@pytest.mark.parametrize("body", ["LANGFUSE_VIEWER_PUBLIC_KEY=\nLANGFUSE_VIEWER_SECRET_KEY=x\n",
    "LANGFUSE_VIEWER_PUBLIC_KEY\nLANGFUSE_VIEWER_SECRET_KEY=x\n"])
def test_declared_but_empty_viewer_fails_closed(tmp_path, body):
    path = env_file(tmp_path, body + "\n".join(f"{k}={v}" for k, v in LEGACY.items()))
    with pytest.raises(cli.CredentialError, match="^credentials_incomplete$"):
        cli.credential_pair(path)


@pytest.mark.parametrize("body", ["PRIVATE_VALUE='unterminated\n", "x" * 65537], ids=["malformed", "oversized"])
def test_parse_failure_and_oversize_do_not_echo_content_or_path(tmp_path, capsys, caplog, body):
    path = env_file(tmp_path, body)
    with pytest.raises(cli.CredentialError, match="^env_file_unavailable$"):
        cli.credential_pair(path)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    assert caplog.text == ""


def test_missing_file_does_not_echo_path(tmp_path, capsys):
    with pytest.raises(cli.CredentialError, match="^env_file_unavailable$"):
        cli.credential_pair(tmp_path / "path-must-not-escape")
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("blocked_logging", ["global", "filter"])
def test_malformed_file_rejected_even_when_logging_is_suppressed(tmp_path, capsys, blocked_logging):
    path = env_file(tmp_path, "\n".join(f"{key}={value}" for key, value in VIEWER.items())
                    + "\nprivate-canary='unterminated\n")
    logger = logging.getLogger("dotenv.main")
    previous = logging.root.manager.disable
    class DropAll(logging.Filter):
        def filter(self, record):
            return False
    suppressor = DropAll()
    try:
        if blocked_logging == "global":
            logging.disable(logging.CRITICAL)
        else:
            logger.addFilter(suppressor)
        with pytest.raises(cli.CredentialError, match="^env_file_unavailable$"):
            cli.credential_pair(path)
    finally:
        logging.disable(previous)
        if blocked_logging == "filter":
            logger.removeFilter(suppressor)
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_help_is_credential_free():
    with mock.patch.object(cli, "credential_pair", side_effect=AssertionError("credentials read")):
        with pytest.raises(SystemExit) as result:
            cli.main(["--help"])
    assert result.value.code == 0


def test_cli_invalid_file_returns_only_static_json(tmp_path):
    path = env_file(tmp_path, "sensitive-canary='unterminated\n")
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/reddog_langfuse_review.py"),
        "--from-time", "2026-11-01T00:00:00Z", "--to-time", "2026-11-02T00:00:00Z", "--env-file", str(path)],
        capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {"ok": False, "reason": "env_file_unavailable"}
    assert result.stderr == "" and "sensitive-canary" not in result.stdout and str(path) not in result.stdout
