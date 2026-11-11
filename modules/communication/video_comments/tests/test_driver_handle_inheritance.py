"""Exercise both actual connect branches without starting a browser or model."""
import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("browser,port", [("Chrome", 9222), ("Edge", 9223)])
def test_comment_driver_does_not_inherit_worker_pipe_handles(monkeypatch, browser, port):
    from selenium import webdriver
    from selenium.webdriver.common import utils
    # Load the real driver classes before replacing Selenium's constructor.
    # Otherwise the package initializer subclasses this function-shaped double.
    from modules.infrastructure.foundups_selenium.src import youtube_verification
    monkeypatch.setattr(utils, "free_port", lambda: 9515)
    calls = []

    def attach(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(current_url="about:blank", execute=lambda *args:
                               pytest.fail("attach must not issue a browser effect"))

    monkeypatch.setattr(webdriver, browser, attach)
    path = Path(__file__).resolve().parents[1] / "skillz/tars_like_heart_reply/comment_engagement_dae.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and any(
        isinstance(m, ast.AsyncFunctionDef) and m.name == "connect" for m in n.body))
    connect = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "connect")
    ns = {"logger": logging.getLogger(__name__), "CHROME_PORT": port,
          "HUMAN_BEHAVIOR_AVAILABLE": False, "BrowserReplyExecutor": lambda **kw: object(),
          "create_comment_processor": lambda *a: SimpleNamespace(), "CommentProcessor": object}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[connect], type_ignores=[])), str(path), "exec"), ns)
    dae = SimpleNamespace(use_vision=False, use_dom=True, human=None, SELECTORS={})
    assert asyncio.run(ns["connect"](dae)) is True
    assert dae.driver._youtube_verification_guard.port == port
    assert len(calls) == 1
    service = calls[0].get("service")
    assert service is not None, "Windows default Service inherits unrelated worker handles"
    assert service.popen_kw.get("close_fds") is True
    assert calls[0]["options"].experimental_options["debuggerAddress"] == f"127.0.0.1:{port}"
    # Check Selenium's actual propagation, without launching any process.
    import selenium.webdriver.common.service as common_service
    launched = []
    def popen(*args, **kwargs):
        launched.append(kwargs)
        return SimpleNamespace(pid=123, poll=lambda: 0, stdin=None, stdout=None, stderr=None)
    monkeypatch.setattr(common_service.subprocess, "Popen", popen)
    service._start_process("offline-driver")
    assert launched[0]["close_fds"] is True
    service.process = None
