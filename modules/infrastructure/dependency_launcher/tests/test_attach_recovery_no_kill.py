"""Non-destructive browser-attach recovery tests (NO_KILL contract, Phase 1).

Slice: BROWSER_ATTACH_RECOVERY_NO_KILL_PHASE1

Confirmed problem (012 live-observed): when the operator-prepared Chrome/Edge on
the debug port is UP (DevTools /json/version works) but has NO discoverable page
target (/json page-list empty -> Selenium raises "unable to discover open pages"),
the old code ran `taskkill /F /IM chrome.exe` and relaunched, DESTROYING the
operator's prepared session.

These tests are MOCK ONLY - no live browser is started. They verify that the
discover-pages (no-page) path NEVER taskkills, recovers by opening a tab, and
fails clearly (no kill) when a tab cannot be opened. The success path is guarded
as a regression check.

Whether PUT/GET /json/new actually opens a discoverable tab on real Chrome 149 is
MOCK-validated only here; 012 live-validates (see ModLog "HONEST LIVE GAP").
"""

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

# Ensure repo root on path (pytest.ini sets pythonpath=. but be explicit/robust).
# file -> tests -> dependency_launcher -> infrastructure -> modules -> <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from modules.infrastructure.dependency_launcher.src import dae_dependencies as deps


class _DiscoverPagesError(Exception):
    """Stand-in for the Selenium error Chrome/Edge raise with no page target."""

    def __init__(self):
        super().__init__(
            "Message: session not created: unable to discover open pages"
        )


class _FakeDriver:
    """Minimal driver: .current_url read must succeed for the attach to 'pass'."""

    @property
    def current_url(self):
        return "https://studio.youtube.com/"


def _spy_subprocess_run():
    """Return (spy, taskkill_calls_list). taskkill_calls captures any taskkill."""
    taskkill_calls = []

    def _run(cmd, *args, **kwargs):
        # Record any taskkill invocation against a browser image.
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "taskkill":
            taskkill_calls.append(list(cmd))
        return mock.Mock(returncode=0, stdout=b"", stderr=b"")

    spy = mock.Mock(side_effect=_run)
    return spy, taskkill_calls


# ---------------------------------------------------------------------------
# CHROME
# ---------------------------------------------------------------------------

def test_chrome_no_kill_on_discover_pages():
    """CORE non-vacuous test: discover-pages -> open-tab recovery, NO taskkill.

    On OLD code the discover-pages branch ran subprocess.run(["taskkill", ...,
    "chrome.exe"]) at dae_dependencies.py:766, so taskkill_calls would be
    non-empty and this assertion (call_count == 0) would FAIL. On the new code
    open_devtools_page is called instead and taskkill is never invoked.
    """
    spy_run, taskkill_calls = _spy_subprocess_run()

    # DevTools is UP (version works) - is_devtools_responding True; the no-page
    # condition is surfaced only by the Selenium attach raising the error.
    chrome_ctor = mock.Mock(side_effect=_DiscoverPagesError())

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=True) as open_tab, \
         mock.patch.object(deps, "launch_chrome") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Chrome", chrome_ctor):
        sp.run = spy_run
        # max_retries=1 so the no-page branch runs on the final attempt and we
        # exercise the "no tab opened in time / attach again" tail deterministically.
        result = deps.connect_chrome_with_retry(max_retries=1, retry_delay=0)

    # The recovery helper MUST have been called on the no-page path.
    assert open_tab.called, "open_devtools_page was not called on discover-pages path"
    # NO taskkill anywhere - this is the NO_KILL contract and the proof that
    # differentiates new code from old (old code's call_count would be >= 1).
    assert all("taskkill" not in str(c) for c in spy_run.call_args_list), spy_run.call_args_list
    assert len(taskkill_calls) == 0, f"taskkill was invoked: {taskkill_calls}"
    # launch_chrome (relaunch) must NOT happen on the no-page path either.
    assert not launch.called, "launch_chrome (relaunch) must not run on no-page path"


def test_chrome_recover_then_attach():
    """After open-tab succeeds and page becomes discoverable, attach is retried."""
    spy_run, taskkill_calls = _spy_subprocess_run()

    # First attach raises discover-pages; second attach (after open-tab) succeeds.
    chrome_ctor = mock.Mock(side_effect=[_DiscoverPagesError(), _FakeDriver()])

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=True) as open_tab, \
         mock.patch.object(deps, "launch_chrome") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Chrome", chrome_ctor):
        sp.run = spy_run
        result = deps.connect_chrome_with_retry(max_retries=3, retry_delay=0)

    assert isinstance(result, _FakeDriver), "expected a driver after recover-then-attach"
    assert open_tab.called, "open_devtools_page must be called before retry"
    assert chrome_ctor.call_count == 2, "attach must be retried after opening a tab"
    assert len(taskkill_calls) == 0, f"no taskkill allowed: {taskkill_calls}"
    assert not launch.called, "no relaunch on the no-page recovery path"


def test_chrome_fail_clear_no_kill_when_open_fails():
    """If open-tab fails, return None with a clear error AND no taskkill."""
    spy_run, taskkill_calls = _spy_subprocess_run()

    chrome_ctor = mock.Mock(side_effect=_DiscoverPagesError())

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=False) as open_tab, \
         mock.patch.object(deps, "launch_chrome") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Chrome", chrome_ctor):
        sp.run = spy_run
        result = deps.connect_chrome_with_retry(max_retries=3, retry_delay=0)

    assert result is None, "open-tab failure must return None (clear failure)"
    assert open_tab.called, "open_devtools_page must be attempted"
    assert len(taskkill_calls) == 0, f"no taskkill on open-tab failure: {taskkill_calls}"
    assert not launch.called, "no relaunch when open-tab fails on no-page path"


def test_chrome_success_attach_preserved():
    """Regression guard: a normal discoverable attach returns a driver, no recovery."""
    spy_run, taskkill_calls = _spy_subprocess_run()

    chrome_ctor = mock.Mock(return_value=_FakeDriver())

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=True) as open_tab, \
         mock.patch.object(deps, "launch_chrome") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Chrome", chrome_ctor):
        sp.run = spy_run
        result = deps.connect_chrome_with_retry(max_retries=3, retry_delay=0)

    assert isinstance(result, _FakeDriver), "success path must return a driver"
    assert not open_tab.called, "no recovery should be attempted on success"
    assert chrome_ctor.call_count == 1, "success should attach on first try"
    assert len(taskkill_calls) == 0, f"success path must not taskkill: {taskkill_calls}"
    assert not launch.called, "success path must not relaunch"


# ---------------------------------------------------------------------------
# EDGE PARITY
# ---------------------------------------------------------------------------

def test_edge_no_kill_on_discover_pages():
    """EDGE PARITY: discover-pages -> open-tab recovery, NO msedge.exe taskkill."""
    spy_run, taskkill_calls = _spy_subprocess_run()

    edge_ctor = mock.Mock(side_effect=_DiscoverPagesError())

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=True) as open_tab, \
         mock.patch.object(deps, "launch_edge") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Edge", edge_ctor):
        sp.run = spy_run
        result = deps.connect_edge_with_retry(max_retries=1, retry_delay=0)

    assert open_tab.called, "open_devtools_page must be called on Edge no-page path"
    assert all("taskkill" not in str(c) for c in spy_run.call_args_list), spy_run.call_args_list
    assert len(taskkill_calls) == 0, f"taskkill was invoked for Edge: {taskkill_calls}"
    assert not launch.called, "launch_edge (relaunch) must not run on no-page path"


def test_edge_recover_then_attach():
    """EDGE PARITY: open-tab then successful retry returns a driver."""
    spy_run, taskkill_calls = _spy_subprocess_run()

    edge_ctor = mock.Mock(side_effect=[_DiscoverPagesError(), _FakeDriver()])

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=True) as open_tab, \
         mock.patch.object(deps, "launch_edge") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Edge", edge_ctor):
        sp.run = spy_run
        result = deps.connect_edge_with_retry(max_retries=3, retry_delay=0)

    assert isinstance(result, _FakeDriver), "expected a driver after Edge recover-then-attach"
    assert open_tab.called
    assert edge_ctor.call_count == 2
    assert len(taskkill_calls) == 0, f"no taskkill allowed for Edge: {taskkill_calls}"
    assert not launch.called


def test_edge_fail_clear_no_kill_when_open_fails():
    """EDGE PARITY: open-tab failure returns None, no taskkill."""
    spy_run, taskkill_calls = _spy_subprocess_run()

    edge_ctor = mock.Mock(side_effect=_DiscoverPagesError())

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=False) as open_tab, \
         mock.patch.object(deps, "launch_edge") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Edge", edge_ctor):
        sp.run = spy_run
        result = deps.connect_edge_with_retry(max_retries=3, retry_delay=0)

    assert result is None
    assert open_tab.called
    assert len(taskkill_calls) == 0, f"no taskkill on Edge open-tab failure: {taskkill_calls}"
    assert not launch.called


def test_edge_success_attach_preserved():
    """EDGE PARITY regression guard: normal attach returns driver, no recovery."""
    spy_run, taskkill_calls = _spy_subprocess_run()

    edge_ctor = mock.Mock(return_value=_FakeDriver())

    with mock.patch.object(deps, "subprocess") as sp, \
         mock.patch.object(deps, "is_devtools_responding", return_value=True), \
         mock.patch.object(deps, "open_devtools_page", return_value=True) as open_tab, \
         mock.patch.object(deps, "launch_edge") as launch, \
         mock.patch.object(deps, "time"), \
         mock.patch("selenium.webdriver.Edge", edge_ctor):
        sp.run = spy_run
        result = deps.connect_edge_with_retry(max_retries=3, retry_delay=0)

    assert isinstance(result, _FakeDriver)
    assert not open_tab.called
    assert edge_ctor.call_count == 1
    assert len(taskkill_calls) == 0, f"Edge success path must not taskkill: {taskkill_calls}"
    assert not launch.called


# ---------------------------------------------------------------------------
# open_devtools_page helper (HTTP layer) - mocked urllib, no real network
# ---------------------------------------------------------------------------

def test_open_devtools_page_put_success():
    """PUT /json/new returning a target id -> True (no GET fallback needed)."""
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"id": "ABCD", "webSocketDebuggerUrl": "ws://x"}'

    with mock.patch("urllib.request.urlopen", return_value=_Resp()) as urlopen:
        ok = deps.open_devtools_page(9222)

    assert ok is True
    # First call is PUT.
    first_req = urlopen.call_args_list[0].args[0]
    assert first_req.get_method() == "PUT"


def test_open_devtools_page_get_fallback():
    """If PUT raises, GET fallback that returns a target id -> True."""
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"id": "EFGH"}'

    def _urlopen(req, *a, **k):
        if req.get_method() == "PUT":
            raise OSError("PUT not allowed")
        return _Resp()

    with mock.patch("urllib.request.urlopen", side_effect=_urlopen):
        ok = deps.open_devtools_page(9222)

    assert ok is True


def test_open_devtools_page_failure_returns_false_never_raises():
    """All HTTP attempts fail -> False, and the helper never raises or kills."""
    with mock.patch("urllib.request.urlopen", side_effect=OSError("blocked")):
        ok = deps.open_devtools_page(9222)
    assert ok is False
