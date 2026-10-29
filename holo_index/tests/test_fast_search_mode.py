#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for fast-search execution path in HoloIndex CLI."""

from types import SimpleNamespace

from holo_index.cli import _is_fast_search_enabled, _render_fast_search_summary


def _args(**overrides):
    base = {
        "fast_search": False,
        "search": "test",
        "offline": True,
        "llm_advisor": False,
        "pattern_coach": False,
        "code_index": False,
        "function_index": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_fast_search_enabled_by_flag(monkeypatch):
    monkeypatch.delenv("HOLO_FAST_SEARCH", raising=False)
    assert _is_fast_search_enabled(_args(fast_search=True)) is True


def test_fast_search_enabled_by_env(monkeypatch):
    monkeypatch.setenv("HOLO_FAST_SEARCH", "1")
    assert _is_fast_search_enabled(_args()) is True


def test_fast_search_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HOLO_FAST_SEARCH", raising=False)
    assert _is_fast_search_enabled(_args()) is False


def test_fast_search_summary_output(capsys):
    payload = {
        "code": [
            {"location": "modules/foundups/agent_market/src/orchestrator.py"},
            {"location": "modules/communication/moltbot_bridge/src/fam_adapter.py"},
        ],
        "wsps": [
            {"path": "modules/foundups/agent_market/INTERFACE.md"},
        ],
    }
    _render_fast_search_summary(payload, limit=3)
    captured = capsys.readouterr().out
    assert (
        "[OK] Analysis complete: 3 hits "
        "(code=2, wsp=1, docs=0, knowledge=0)" in captured
    )
    assert "[CODE] modules/foundups/agent_market/src/orchestrator.py" in captured
    assert "[WSP] modules/foundups/agent_market/INTERFACE.md" in captured

