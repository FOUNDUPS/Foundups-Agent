"""Offline verification handoff acceptance: fake clocks/drivers, no browser/model."""

from contextlib import nullcontext
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.infrastructure.foundups_selenium.src import youtube_verification as v


class Clock:
    now = 100.0

    def sleep(self, seconds):
        self.now += seconds
        assert self.now < 220, "handoff did not finish in synthetic bound"

    def __call__(self):
        return self.now


@pytest.fixture
def setup_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(v, "runtime_operation_lock", lambda *a, **k: nullcontext())
    # Any accidental real HTTP use fails before touching a prepared browser.
    monkeypatch.setattr(v, "_page_targets", lambda *a: pytest.fail("real HTTP forbidden"))
    clock = Clock()
    effects = []

    def original(command, params):
        effects.append(command)
        return {"value": True}

    def make(observe, **kwargs):
        return v.VerificationGate(
            9222, state_root=tmp_path / "control", observe=observe,
            clock=clock, sleep=clock.sleep, **kwargs)
    return clock, effects, original, make


@pytest.mark.parametrize("command", [
    "get", "refresh", "goBack", "close", "quit", "switchToWindow",
    "clickElement", "sendKeysToElement", "actions", "w3cExecuteScript",
    "executeCdpCommand", "screenshot",
])
def test_every_effect_waits_thirty_seconds_and_never_replays(setup_gate, command):
    clock, effects, original, make = setup_gate
    gate = make(lambda *_: (clock() < 101, "a" * 64))
    with pytest.raises(v.VerificationHandoff, match="cleared_revalidate_action"):
        gate.execute(original, command, {})
    assert clock() == 130
    assert effects == []
    assert not gate.path.exists()
    # Only a fresh owner invocation can proceed after revalidation.
    gate.execute(original, command, {})
    assert effects == [command]


def test_prompt_still_present_after_thirty_stays_held(setup_gate):
    clock, effects, original, make = setup_gate
    gate = make(lambda *_: (clock() < 145, "a" * 64))
    with pytest.raises(v.VerificationHandoff, match="cleared"):
        gate.execute(original, "get", {})
    assert clock() == 145
    assert not effects


def test_another_driver_cannot_erase_the_handoff(setup_gate):
    clock, effects, original, make = setup_gate
    first = make(lambda *_: (True, "a" * 64))
    first._start("a" * 64)
    second = make(lambda *_: (False, "b" * 64), stopped=lambda: clock() >= 135)
    with pytest.raises(v.VerificationHandoff, match="stopped"):
        second.execute(original, "refresh")
    assert clock() == 135
    assert first.path.exists()
    assert not effects
    first.observe = lambda *_: (False, "a" * 64)
    with pytest.raises(v.VerificationHandoff, match="cleared"):
        first.execute(original, "get")


def test_observation_error_cannot_clear_an_existing_hold(setup_gate):
    clock, effects, original, make = setup_gate
    def unavailable(*_):
        raise OSError("private detail must not leak")
    gate = make(unavailable, stopped=lambda: clock() >= 140)
    gate._start("a" * 64)
    with pytest.raises(v.VerificationHandoff, match="stopped"):
        gate.execute(original, "get")
    assert gate.path.exists() and not effects


def test_unknown_observation_blocks_without_effect(setup_gate):
    clock, effects, original, make = setup_gate
    gate = make(lambda *_: (_ for _ in ()).throw(OSError("private")))
    with pytest.raises(v.VerificationHandoff, match="observation_unavailable") as error:
        gate.execute(original, "get")
    assert "private" not in str(error.value)
    assert not effects


@pytest.mark.parametrize("record", [
    "{", '{"since": 99, "target": "bad"}',
    '{"since": -1, "target": "' + "a"*64 + '"}',
    '{"since": 999, "target": "' + "a"*64 + '"}',
])
def test_corrupt_or_previous_boot_control_never_allows_an_effect(setup_gate, record):
    _, effects, original, make = setup_gate
    gate = make(lambda *_: (False, "a" * 64))
    gate.path.parent.mkdir()
    gate.path.write_text(record)
    with pytest.raises(v.VerificationHandoff):
        gate.execute(original, "clickElement")
    assert not effects and gate.path.read_text() == record


def test_stop_preserves_prompt_and_record(setup_gate):
    _, effects, original, make = setup_gate
    gate = make(lambda *_: (True, "a" * 64), stopped=lambda: True)
    gate._start("a"*64)
    before = gate.path.read_bytes()
    with pytest.raises(v.VerificationHandoff, match="stopped"):
        gate.execute(original, "get")
    assert not effects and gate.path.read_bytes() == before


def test_read_only_lookup_does_not_touch_or_dismiss_prompt(setup_gate):
    _, effects, original, make = setup_gate
    gate = make(lambda *_: pytest.fail("unneeded probe"))
    gate._start("a"*64)
    gate.execute(original, "getCurrentUrl")
    assert effects == ["getCurrentUrl"] and gate.path.exists()


def test_shared_record_contains_only_control_fields(setup_gate):
    _, _, _, make = setup_gate
    gate = make(lambda *_: (False, "a"*64))
    gate._start("a"*64)
    assert set(json.loads(gate.path.read_text())) == {"since", "target"}
    other = make(lambda *_: (False, "a"*64))
    assert other._read() == gate._read()


@pytest.mark.parametrize("url,expected", [
    ("https://accounts.google.com/v3/signin/challenge/pwd", True),
    ("https://accounts.google.com/ServiceLogin", True),
    ("https://accounts.google.com.evil.test/signin/challenge", False),
    ("https://evil.test/?continue=https://accounts.google.com/signin", False),
    ("http://accounts.google.com/signin", False),
    ("https://studio.youtube.com/video/example/edit", False),
])
def test_only_google_auth_targets_signal_a_popup(url, expected):
    assert v._auth_page(url) is expected


def test_popup_detected_without_reading_auth_page_contents(monkeypatch):
    monkeypatch.setattr(v, "_page_targets", lambda *_: [
        {"type": "page", "url": "https://accounts.google.com/v3/signin/challenge/pwd"}])
    calls = []
    def execute(command, params):
        calls.append(command)
        assert command == v.Command.W3C_GET_CURRENT_WINDOW_HANDLE
        return {"value": "private-target"}
    seen, identity = v._observe(execute, 9222)
    assert seen and len(identity) == 64 and calls == [v.Command.W3C_GET_CURRENT_WINDOW_HANDLE]


def test_guard_installed_once_without_opening_browser_or_state(tmp_path, monkeypatch):
    monkeypatch.setattr(v, "VerificationGate", lambda *a, **k: SimpleNamespace(
        execute=lambda original, command, params: {"value": "guarded"}))
    driver = SimpleNamespace(execute=lambda *a: pytest.fail("unguarded"))
    assert v.install_youtube_verification_guard(driver, 9222) is driver
    wrapper = driver.execute
    v.install_youtube_verification_guard(driver, 9222)
    assert driver.execute is wrapper
    assert driver.execute("clickElement", {}) == {"value": "guarded"}


@pytest.mark.parametrize("browser", ["chrome", "edge"])
def test_actual_attach_owner_returns_guarded_driver(setup_gate, monkeypatch, browser):
    from selenium import webdriver
    from modules.infrastructure.dependency_launcher.src import dae_dependencies as deps
    clock, effects, original, make = setup_gate
    gate = make(lambda *_: (clock() < 101, "a"*64))
    monkeypatch.setattr(v, "VerificationGate", lambda *a, **k: gate)
    driver = SimpleNamespace(execute=original, current_url="https://studio.youtube.com/")
    monkeypatch.setattr(deps, "_devtools_page_state", lambda *_: "ready")
    monkeypatch.setattr(webdriver, browser.title(), lambda **_: driver)
    attached = getattr(deps, "connect_" + browser + "_with_retry")(max_retries=1)
    assert attached is driver
    with pytest.raises(v.VerificationHandoff, match="cleared"):
        attached.execute("clickElement", {"id": "save"})
    assert clock() == 130 and not effects


def test_dispatched_transport_error_remains_uncertain(setup_gate):
    _, _, _, make = setup_gate
    gate = make(lambda *_: (False, "a" * 64))
    uncertain = OSError("synthetic post-submit connection loss")
    calls = []
    def send(command, params):
        calls.append(command)
        raise uncertain
    with pytest.raises(OSError) as error:
        gate.execute(send, "clickElement")
    assert error.value is uncertain and calls == ["clickElement"]


def test_observer_uses_registered_selenium_commands(monkeypatch):
    from selenium.webdriver.remote.remote_connection import remote_commands
    monkeypatch.setattr(v, "_page_targets", lambda *_: [
        {"type": "page", "url": "https://studio.youtube.com/"}])
    def execute(command, params):
        assert command in remote_commands
        return {"value": "synthetic-handle" if command == v.Command.W3C_GET_CURRENT_WINDOW_HANDLE else False}
    assert v._observe(execute, 9222)[0] is False


def test_other_browser_port_is_independent(setup_gate):
    _, effects, original, make = setup_gate
    first = make(lambda *_: (False, "a" * 64))
    first._start("a" * 64)
    second = make(lambda *_: (False, "b" * 64))
    second = v.VerificationGate(9223, state_root=first.root, observe=second.observe)
    second.execute(original, "get")
    assert effects == ["get"] and first.path.exists()
    assert second.lock_key != first.lock_key


def test_waiter_does_not_replay_after_another_owner_clears(setup_gate):
    clock, effects, original, make = setup_gate
    gate = make(lambda *_: (False, "b" * 64))
    gate._start("a" * 64)
    def another_owner_clears(seconds):
        clock.sleep(30)
        gate.path.unlink()
    gate.sleep = another_owner_clears
    with pytest.raises(v.VerificationHandoff, match="cleared_revalidate_action"):
        gate.execute(original, "clickElement")
    assert not effects


@pytest.mark.skipif(shutil.which("node") is None, reason="Node needed for offline DOM fixture")
def test_dialog_probe_with_synthetic_dom():
    # Execute the real JS without browser/network access. Test headings across
    # shadow roots, hidden dialogs, untrusted comment text and a trusted iframe.
    fixture = r'''
const assert = require('node:assert/strict');
const probe = new Function(PROBE);
global.location = {hostname:'studio.youtube.com', href:'https://studio.youtube.com/'};
global.getComputedStyle = e => ({visibility:e.hidden ? 'hidden' : 'visible'});
function root({dialogs=[], headings=[], nodes=[]}={}) {
 return {querySelectorAll:s => s === '*' ? nodes : s.startsWith('[role="dialog"]') ? dialogs : headings};
}
function element(props={}) {
 return Object.assign(root(), {getClientRects:()=>[1], closest:()=>null}, props);
}
const heading = element({textContent:'Verify it’s you'});
const dialog = element(root({headings:[heading]}));
global.document = root({dialogs:[dialog],nodes:[dialog]});
assert.equal(probe(), true);
dialog.hidden = true;
assert.equal(probe(), false);
global.document = root({headings:[heading],nodes:[heading]});
assert.equal(probe(), false, 'ordinary text must not pause');
dialog.hidden = false;
const host = element({shadowRoot:root({headings:[heading]}),closest:()=>dialog});
global.document = root({nodes:[host]});
assert.equal(probe(), true, 'dialog heading inside shadow root');
host.hidden = true;
assert.equal(probe(), false);
const iframe = element({tagName:'IFRAME',src:'https://accounts.google.com/v3/signin/challenge/pwd'});
global.document = root({nodes:[iframe]});
assert.equal(probe(), true);
iframe.src = 'https://evil.test/signin/challenge';
assert.equal(probe(), false);
global.location.hostname = 'evil.test';
global.document = root({dialogs:[dialog]});
assert.equal(probe(), false);
'''
    script = fixture.replace("PROBE", json.dumps(v._DIALOG_PROBE))
    result = subprocess.run([shutil.which("node"), "-e", script],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_gate_serializes_with_a_separate_process(tmp_path):
    # Use an isolated synthetic port namespace. No browser/socket is opened.
    gate = v.VerificationGate(64379, state_root=tmp_path / "control",
                              observe=lambda *_: (False, "a" * 64))
    ready = tmp_path / "ready"
    script = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from modules.infrastructure.shared_utilities.runtime_artifact_safety import runtime_operation_lock
with runtime_operation_lock(sys.argv[2], timeout_seconds=5):
    Path(sys.argv[3]).write_text('ready')
    sys.stdin.read(1)
"""
    process = subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", script, str(v._REPO), gate.lock_key, str(ready)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        cwd=tmp_path,
    )
    calls = []
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), "synthetic lock holder did not become ready"
        with pytest.raises(v.VerificationHandoff, match="control_unavailable"):
            gate.execute(lambda *args: calls.append(args), "clickElement")
        assert not calls
    finally:
        process.communicate(b"x", timeout=5)
    gate.execute(lambda *args: calls.append(args), "clickElement")
    assert len(calls) == 1
