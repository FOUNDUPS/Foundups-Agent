"""Strict text-decoding contracts for repository search."""

from pathlib import Path
from types import SimpleNamespace

from modules.infrastructure.foundups_mcp_bridge.src import repo_tools


def test_search_repo_requests_strict_utf8_from_ripgrep(monkeypatch, tmp_path: Path):
    """Ripgrep JSON is decoded deterministically, independent of host locale."""

    observed = {}

    def fake_run(command, **kwargs):
        observed.update(kwargs)
        stdout = (
            '{"type":"match","data":{"path":{"text":"café.py"},'
            '"lines":{"text":"naïve\\n"},"line_number":7}}\n'
        )
        return SimpleNamespace(stdout=stdout, stderr="", returncode=0)

    monkeypatch.setattr(repo_tools.subprocess, "run", fake_run)

    result = repo_tools.search_repo(tmp_path, "naïve", top_k=1)

    assert result["status"] == "ok"
    assert observed["text"] is True
    assert observed["encoding"] == "utf-8"
    assert observed["errors"] == "strict"
    assert result["data"]["matches"][0]["path"] == "café.py"


def test_search_repo_fails_closed_on_invalid_utf8(monkeypatch, tmp_path: Path):
    """A decoding failure is returned as an error instead of hiding evidence."""

    def fail_decode(_command, **_kwargs):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(repo_tools.subprocess, "run", fail_decode)

    result = repo_tools.search_repo(tmp_path, "WSP")

    assert result["status"] == "error"
    assert "utf-8" in result["error"].lower()
    assert "invalid start byte" in result["error"].lower()
