"""Human-only verification handoff for cooperating YouTube Selenium drivers.

This gate never completes a challenge. It serializes browser effects through the
existing host lock and shares a small control record across DAE processes. No
page text, URLs, credentials or screenshots are persisted.
"""

import hashlib
import http.client
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

from selenium.webdriver.remote.command import Command

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    validate_runtime_artifact_path,
)

logger = logging.getLogger(__name__)
MINIMUM_HOLD_SECONDS = 30.0
_REPO = Path(__file__).resolve().parents[4]
_READ_ONLY = frozenset({
    "getCurrentUrl", "getTitle", Command.W3C_GET_CURRENT_WINDOW_HANDLE,
    Command.W3C_GET_WINDOW_HANDLES,
    "findElement", "findElements", "findChildElement", "findChildElements",
    "getElementText", "getElementTagName", "getElementAttribute",
    "getElementProperty", "getElementValueOfCssProperty", "isElementDisplayed",
    "isElementEnabled", "isElementSelected", "getElementRect", "getPageSource",
    "getWindowRect", "getTimeouts",
})

# Inspect only a displayed verification dialog on an official Studio page.
# A participant's comment containing the same words is not a challenge signal.
_DIALOG_PROBE = r"""
if (location.hostname !== 'studio.youtube.com') return false;
const visible = e => !!(e.getClientRects().length) &&
    getComputedStyle(e).visibility !== 'hidden';
const phrase = /verify it[’']?s you|verify your identity|confirm it[’']?s you|本人確認/i;
const dialogs = '[role="dialog"],tp-yt-paper-dialog,ytcp-dialog';
const headings = 'h1,h2,[role="heading"],#title';
const matches = root => Array.from(root.querySelectorAll(headings)).some(
    h => visible(h) && phrase.test(h.textContent || ''));
const roots = [{root: document, dialog: false}];
for (let i = 0; i < roots.length; i++) {
    if (i >= 4096) return null; // Unknown observation cannot authorize an effect.
    const {root, dialog} = roots[i];
    if (dialog && matches(root)) return true;
    if (Array.from(root.querySelectorAll(dialogs)).some(
        d => visible(d) && matches(d))) return true;
    for (const e of root.querySelectorAll('*')) {
        const parentDialog = e.closest(dialogs);
        if (e.shadowRoot && visible(e) && (!parentDialog || visible(parentDialog))) {
            roots.push({root: e.shadowRoot, dialog: dialog || !!parentDialog});
        }
        if (e.tagName === 'IFRAME' && visible(e)) {
            const u = new URL(e.src, location.href);
            if (u.protocol === 'https:' && u.hostname === 'accounts.google.com' &&
                /\/challenge|\/signin|\/ServiceLogin/.test(u.pathname)) return true;
        }
    }
}
return false;
"""


class VerificationHandoff(RuntimeError):
    """The pending effect was cancelled; its owner must revalidate, never replay."""


def _auth_page(url):
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.hostname == "accounts.google.com"
            and ("/challenge" in parsed.path or "/signin" in parsed.path
                 or "/ServiceLogin" in parsed.path))


def _page_targets(port):
    # Loopback only, no environment proxy, bounded response and no URL logging.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", "/json/list")
        response = connection.getresponse()
        raw = response.read(131073)
        if response.status != 200 or len(raw) > 131072:
            raise VerificationHandoff("verification_observation_unavailable")
        return json.loads(raw)
    finally:
        connection.close()


def _observe(execute, port):
    """Passive observations only, including a separate authentication popup."""
    targets = _page_targets(port)
    if not isinstance(targets, list) or not targets:
        raise VerificationHandoff("verification_observation_unavailable")
    if any(not isinstance(t, dict) or not isinstance(t.get("url"), str)
           for t in targets):
        raise VerificationHandoff("verification_observation_unavailable")
    popup = any(t.get("type") in ("page", "iframe") and _auth_page(t["url"]) for t in targets)
    handle = execute(Command.W3C_GET_CURRENT_WINDOW_HANDLE, {})["value"]
    if not isinstance(handle, str) or not handle:
        raise VerificationHandoff("verification_target_unknown")
    # Do not inspect the contents of the authentication page itself.
    dialog = False if popup else execute(
        Command.W3C_EXECUTE_SCRIPT, {"script": _DIALOG_PROBE, "args": []})["value"]
    if type(dialog) is not bool:
        raise VerificationHandoff("verification_observation_unavailable")
    return popup or dialog, hashlib.sha256(handle.encode()).hexdigest()


class VerificationGate:
    def __init__(self, port, *, state_root=None, observe=_observe,
                 clock=time.monotonic, sleep=time.sleep, stopped=lambda: False):
        self.port = int(port)
        if not 1 <= self.port <= 65535:
            raise ValueError("invalid_browser_port")
        self.root = Path(state_root or Path.home() / ".foundups-agent" / "browser-verification")
        self.path = self.root / f"{self.port}.json"
        self.observe, self.clock, self.sleep, self.stopped = observe, clock, sleep, stopped
        self.lock_key = f"youtube-browser-verification:127.0.0.1:{self.port}"

    def _path(self):
        return validate_runtime_artifact_path(
            self.path, repo_root=_REPO, allowed_root=self.root)

    def _read(self):
        path = self._path()
        if not path.exists():
            return None
        if path.stat().st_size > 4096:
            raise VerificationHandoff("verification_control_invalid")
        value = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(value, dict) or set(value) != {"since", "target"}
                or type(value["since"]) not in (float, int)
                or not 0 <= value["since"] <= self.clock()
                or not isinstance(value["target"], str) or len(value["target"]) != 64):
            raise VerificationHandoff("verification_control_invalid")
        return value

    def _start(self, target):
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path().with_suffix(".tmp")
        validate_runtime_artifact_path(temporary, repo_root=_REPO, allowed_root=self.root)
        temporary.write_text(json.dumps({"since": self.clock(), "target": target}), encoding="utf-8")
        os.replace(temporary, path)
        logger.warning("[VERIFY-HANDOFF] Verify it's you: browser %s yielded to 012. "
                       "Complete verification manually; at least 30 seconds, longer while present. "
                       "No automatic refresh, navigation or submission.", self.port)

    def execute(self, original, command, params=None):
        if command in _READ_ONLY:
            return original(command, params)
        waited = False
        while True:
            if self.stopped():
                raise VerificationHandoff("verification_handoff_stopped")
            dispatched = False
            try:
                with runtime_operation_lock(self.lock_key, timeout_seconds=5):
                    held = self._read()
                    try:
                        challenge, target = self.observe(original, self.port)
                    except Exception:
                        if held is None:
                            raise VerificationHandoff("verification_observation_unavailable") from None
                        challenge, target = None, None
                    if held is None and challenge:
                        self._start(target)
                        held = self._read()
                    if held is not None:
                        waited = True
                        if (challenge is False and target == held["target"]
                                and self.clock() - held["since"] >= MINIMUM_HOLD_SECONDS):
                            self._path().unlink()
                            logger.info("[VERIFY-HANDOFF] Browser %s verification cleared; "
                                        "pending effect cancelled for owner revalidation.", self.port)
                            raise VerificationHandoff("verification_cleared_revalidate_action")
                    elif waited:
                        raise VerificationHandoff("verification_cleared_revalidate_action")
                    else:
                        dispatched = True
                        return original(command, params)
            except VerificationHandoff:
                raise
            except Exception:
                if dispatched:
                    # Preserve uncertain transport/browser outcomes verbatim for
                    # the existing effect owner. A send may already have happened.
                    raise
                # Unknown control/locking state never authorizes a browser effect.
                raise VerificationHandoff("verification_control_unavailable") from None
            self.sleep(1.0)


def install_youtube_verification_guard(driver, port):
    """Install once before exposing an attached driver to any YouTube owner."""
    if driver.__dict__.get("_youtube_verification_guard") is not None:
        return driver
    from modules.communication.livechat.src.automation_gates import stop_active
    gate = VerificationGate(port, stopped=lambda: stop_active("global"))
    original = driver.execute
    driver.execute = lambda command, params=None: gate.execute(original, command, params)
    driver._youtube_verification_guard = gate
    return driver
