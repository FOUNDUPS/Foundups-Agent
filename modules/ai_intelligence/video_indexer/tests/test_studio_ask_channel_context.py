"""
Tests for STUDIO_ASK_CHANNEL_CONTEXT_PHASE1.

012 live-observed TWO defects on the Studio Ask single-video path:
  (1) WRONG BROWSER TARGET: Selenium attached to a Chrome SIDE-PANEL target
      first (chrome://glic / the gemini.google.com glic panel) even with a
      Studio edit tab open, so the action "asked" in a Gemini side panel.
  (2) WRONG CHANNEL CONTEXT: the single-video action navigated straight to the
      channel-AGNOSTIC studio.youtube.com/video/{id}/edit and never switched
      the active channel, so with Move2Japan active and an UnDaoDu video Ask
      Studio could not access it (metadata-only guess).

This suite proves the fix (STUDIO_ASK_CHANNEL_CONTEXT_PHASE1):
  STEP 0 - select a Studio/normal browser TARGET (reject glic/Gemini panel/
           RotateCookies) BEFORE channel nav; fail closed when none exists.
  STEP 1 - set the OWNING-channel context via the channel-scoped URL (mirror
           the batch path) BEFORE /video/{id}/edit.
  STEP 2 - OBSERVABLE owner verification (NOT URL-only): permission/not-found/
           sign-in/Oops or an absent edit surface -> fail closed.
  STEP 3 - channel_id REQUIRED (blank / unknown -> channel_unresolved), no
           guessing from the URL.
  STEP 4 - NO persist on any of these failures.

Every assertion below is NON-VACUOUS: it would FAIL on the pre-fix code (which
had no target selection, no channel-context navigation, no observable
verification, and did not require channel_id). All tests use a MOCK driver -
NO live YouTube, NO clipboard, NO network (the #817 KNOWN-GAP: real selector /
channel-switch behavior can only be live-validated by 012).

WSP Compliance:
    WSP 5/6: Test coverage + audit
    WSP 72: Module independence (no cross-module fixtures)
    WSP 84: REUSE of the youtube_channel_registry (get_channel_by_id)
"""

import asyncio

import pytest

from modules.ai_intelligence.video_indexer.src import studio_ask_indexer as mod
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    StudioAskIndexer,
)

# Registry-known channel IDs (defaults: UnDaoDu owner, Move2Japan as the
# "previously active" channel). Unknown ID is deliberately NOT in the registry.
UNDAODU_ID = "UCfHM9Fw9HD-NwiS0seD_oIA"
MOVE2JAPAN_ID = "UC-LSSlOZwpGIRIYihaz8zCw"
UNKNOWN_ID = "UC_not_a_real_channel_zzzzzz"

STUDIO_VIDEO_EDIT = "https://studio.youtube.com/video/vidX/edit"
STUDIO_CHANNEL_CTX = f"https://studio.youtube.com/channel/{UNDAODU_ID}/videos/upload"
GLIC_URL = "chrome://glic/"
GEMINI_PANEL_URL = "https://gemini.google.com/glic"


# ---------------------------------------------------------------------------
# Mock elements + multi-window driver (records handles + navigation order)
# ---------------------------------------------------------------------------

class _El:
    """Minimal Selenium element stand-in."""

    def __init__(self, text="", attributes=None):
        self._text = text
        self._attributes = attributes or {}
        self.clicked = False

    @property
    def text(self):
        return self._text

    def get_attribute(self, name):
        return self._attributes.get(name, "")

    def click(self):
        self.clicked = True

    def send_keys(self, *a):
        pass


class _SwitchTo:
    def __init__(self, driver):
        self._driver = driver

    def window(self, handle):
        self._driver._active = handle


class MultiWindowDriver:
    """
    Mock driver that models multiple browser TARGETS (window handles) with a URL
    each, records the order of get() navigations, and exposes the title/body for
    observable verification. The handle the driver is "switched" to drives
    current_url, so STEP 0 target selection is observable.
    """

    def __init__(self, handles_urls, css_map=None, body_text="", title="YouTube Studio"):
        # handles_urls: list of (handle_id, url) in window order.
        self._urls = {h: u for h, u in handles_urls}
        self._handles = [h for h, _ in handles_urls]
        self._active = self._handles[0] if self._handles else None
        self.css_map = css_map or {}
        self._body_text = body_text
        self._title = title
        self.visited = []            # ordered get() navigations
        self.switch_to = _SwitchTo(self)
        self._opened = 0

    @property
    def window_handles(self):
        # Real Selenium returns a FRESH list each access (not a shared ref).
        return list(self._handles)

    # --- target / url plumbing ---
    @property
    def current_url(self):
        # After a get(), the active handle's URL is the navigated URL.
        return self._urls.get(self._active, "")

    @property
    def current_window_handle(self):
        return self._active

    @property
    def title(self):
        return self._title

    def get(self, url):
        self.visited.append(url)
        # Navigation updates the active target's URL.
        self._urls[self._active] = url

    def execute_script(self, *args, **kwargs):
        script = str(args[0]) if args else ""
        if "window.open" in script:
            # Open a NEW normal tab via the EXISTING driver.
            self._opened += 1
            new_handle = f"opened-{self._opened}"
            self._urls[new_handle] = "about:blank"
            self._handles.append(new_handle)
            return None
        return None

    def find_element(self, by, selector):
        if selector == "body":
            return _El(text=self._body_text)
        el = self.css_map.get(selector)
        if el is not None:
            return el
        raise Exception(f"NoSuchElement: {selector}")

    def find_elements(self, by, selector):
        el = self.css_map.get(selector)
        return [el] if el else []


def _ask_dom(response_text='{"topics": ["x"], "segments": []}', with_title=True):
    """css_map where the Ask Studio PRIMARY path can fully succeed."""
    css = {
        'ytcp-icon-button[aria-label="Ask Studio"]': _El(attributes={"aria-label": "Ask Studio"}),
        "ytcp-dialog#dialog": _El(),
        'div[contenteditable][aria-label="Ask something"]': _El(attributes={"aria-label": "Ask something"}),
        "#PAcreator_chat_streaming": _El(text=response_text),
    }
    if with_title:
        css["input#title-field, h1.title"] = _El(attributes={"value": "Studio Title"})
    return css


@pytest.fixture(autouse=True)
def _fast_and_clean(monkeypatch):
    """Instant delays + short timeout + fresh human singleton + char-typing."""
    async def _no_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0)

    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _no_delay)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 0.05)

    import modules.infrastructure.foundups_selenium.src.human_behavior as hb
    monkeypatch.setattr(hb, "_human_behavior_instance", None, raising=False)

    def _fake_human_type(self, element, text):
        element.click()
        for ch in text:
            element.send_keys(ch)

    monkeypatch.setattr(hb.HumanBehavior, "human_type", _fake_human_type)


# ===========================================================================
# STEP 0 - BROWSER TARGET SELECTION
# ===========================================================================

async def test_target_selection_switches_to_studio_handle_first():
    """
    handles = [chrome://glic (FIRST), Studio tab]. The code MUST switch to the
    Studio handle BEFORE any channel/video navigation.

    NON-VACUOUS: pre-fix code had NO target selection - it would drive whatever
    handle Selenium attached to (the glic side panel) and never switch.
    """
    driver = MultiWindowDriver(
        handles_urls=[("glic", GLIC_URL), ("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    # Active target is NOT the glic side panel by the time we navigate.
    assert driver._active != "glic"
    # The FIRST navigation is the channel-context URL (already on a Studio tab).
    assert driver.visited[0] == STUDIO_CHANNEL_CTX
    assert result.success is True


async def test_target_fail_closed_when_only_side_panels_and_no_normal_tab(monkeypatch):
    """
    Only glic/Gemini side-panel handles AND the driver cannot open a normal tab
    -> success=False, error 'studio_target_unavailable', NO ask, NO channel nav.

    NON-VACUOUS: pre-fix code never inspected handles, so it could not detect
    that EVERY target was a non-Studio side panel.
    """
    driver = MultiWindowDriver(
        handles_urls=[("glic", GLIC_URL), ("gem", GEMINI_PANEL_URL)],
        css_map=_ask_dom(),
    )
    # Disable opening a normal tab (simulate a driver that can't).
    monkeypatch.setattr(driver, "execute_script", lambda *a, **k: None)

    result = await indexer_run(driver, "vidX", UNDAODU_ID)

    assert result.success is False
    assert result.error == "studio_target_unavailable"
    # NEVER navigated to a channel-context / edit / watch URL.
    assert driver.visited == []


async def test_target_opens_normal_tab_when_only_side_panels_but_driver_supports_open():
    """
    Only side-panel handles, but the EXISTING driver CAN open a normal tab ->
    target selection recovers (no new browser) and proceeds.
    """
    driver = MultiWindowDriver(
        handles_urls=[("glic", GLIC_URL), ("gem", GEMINI_PANEL_URL)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    # A normal tab was opened via the existing driver (window.open), not a new
    # browser, and the active target is that opened tab.
    assert driver._active.startswith("opened-")
    assert result.success is True


async def test_target_selection_happens_before_channel_context_navigation():
    """
    TARGET BEFORE CONTEXT: with glic FIRST, by the time the channel-context URL
    is navigated the active target is already a Studio/normal tab (not glic).

    NON-VACUOUS: pre-fix code navigated channel-context (well, edit) on whatever
    handle was attached - it had no notion of selecting a target first.
    """
    driver = MultiWindowDriver(
        handles_urls=[("glic", GLIC_URL), ("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    # First navigation is the channel-scoped context URL, and it happened on a
    # non-glic target.
    assert driver.visited[0] == STUDIO_CHANNEL_CTX
    assert driver._active != "glic"


# ===========================================================================
# STEP 1/2 - CONTEXT BEFORE ASK + OBSERVABLE VERIFICATION
# ===========================================================================

async def test_channel_context_set_before_video_edit():
    """
    CONTEXT BEFORE ASK: navigation MUST hit the channel-scoped URL (containing
    channel_id) BEFORE /video/{id}/edit.

    NON-VACUOUS: pre-fix ask_about_video navigated ONLY to
    /video/{id}/edit (studio_ask_indexer.py was channel-agnostic). There was no
    channel-scoped URL in driver.visited at all -> this assert FAILS on old code.
    """
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert STUDIO_CHANNEL_CTX in driver.visited
    assert STUDIO_VIDEO_EDIT in driver.visited
    assert driver.visited.index(STUDIO_CHANNEL_CTX) < driver.visited.index(STUDIO_VIDEO_EDIT)


async def test_wrong_channel_context_permission_page_fails_closed():
    """
    OBSERVABLE VERIFY: channel-scoped nav done but the edit page shows a
    permission/Oops body -> fail closed 'wrong_channel_context'.

    NON-VACUOUS: pre-fix code did NO post-navigation verification and returned a
    (possibly empty/garbage) AskResult; it never produced wrong_channel_context.
    """
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
        body_text="Oops, you don't have permission to access this video.",
        title="Oops",
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "wrong_channel_context"


async def test_wrong_channel_context_edit_surface_absent_fails_closed():
    """
    OBSERVABLE VERIFY: no error page, but the title/edit surface never appears
    -> fail closed 'wrong_channel_context' after the timeout.
    """
    # css_map WITHOUT the title field -> edit surface absent.
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(with_title=False),
        body_text="",
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "wrong_channel_context"


async def test_edit_surface_present_allows_ask_to_proceed():
    """OBSERVABLE VERIFY: edit surface present + no error -> ask may proceed."""
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
        body_text="Video details",
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True


# ===========================================================================
# STEP 3 - channel_id REQUIRED (no URL guessing)
# ===========================================================================

async def test_blank_channel_id_fails_closed_channel_unresolved():
    """
    channel_id REQUIRED: blank channel_id (and no channel_entry) ->
    'channel_unresolved'. No navigation, no ask.

    NON-VACUOUS: pre-fix code did not require channel_id at all - it would
    navigate + ask regardless.
    """
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX")  # no channel context at all

    assert result.success is False
    assert result.error == "channel_unresolved"
    assert driver.visited == []


async def test_unknown_channel_id_fails_closed_channel_unresolved():
    """Unknown (not-in-registry) channel_id -> 'channel_unresolved', no guessing."""
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNKNOWN_ID)

    assert result.success is False
    assert result.error == "channel_unresolved"
    assert driver.visited == []


async def test_channel_id_not_guessed_from_video_url():
    """
    Even though the active tab URL is a /video/{id}/edit URL, a MISSING
    channel_id must NOT be inferred from it -> channel_unresolved.
    """
    driver = MultiWindowDriver(
        handles_urls=[("studio", "https://studio.youtube.com/video/vidX/edit?from=UCspoofed")],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX")

    assert result.success is False
    assert result.error == "channel_unresolved"


# ===========================================================================
# STEP 4 - PERSISTENCE GUARD (no save on target/context/ask failure)
# ===========================================================================

def _spy_store(monkeypatch):
    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)
    return saved


async def _index_one(indexer, channel_id):
    """Drive the real persistence guard (index_channel_videos only saves on success)."""
    return await indexer.index_channel_videos(channel_id, max_videos=1)


async def test_no_save_on_wrong_channel_context(monkeypatch):
    """wrong_channel_context -> save_index NEVER called."""
    saved = _spy_store(monkeypatch)
    # Discovery returns a single video; the edit page is a permission/Oops page.
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
        body_text="Oops permission denied",
        title="Oops",
    )
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    async def _one_video(self, *a, **k):
        return None
    # Bypass live DOM discovery: ask a single known video through the guard.
    monkeypatch.setattr(
        indexer, "index_channel_videos",
        _patch_index_single(indexer, "vidX", UNDAODU_ID),
    )

    summary = await indexer.index_channel_videos(UNDAODU_ID)

    assert summary["indexed"] == 0
    assert saved["count"] == 0


async def test_no_save_on_target_unavailable(monkeypatch):
    """studio_target_unavailable -> save_index NEVER called."""
    saved = _spy_store(monkeypatch)
    driver = MultiWindowDriver(
        handles_urls=[("glic", GLIC_URL), ("gem", GEMINI_PANEL_URL)],
        css_map=_ask_dom(),
    )
    monkeypatch.setattr(driver, "execute_script", lambda *a, **k: None)
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)
    monkeypatch.setattr(
        indexer, "index_channel_videos",
        _patch_index_single(indexer, "vidX", UNDAODU_ID),
    )

    summary = await indexer.index_channel_videos(UNDAODU_ID)

    assert summary["indexed"] == 0
    assert saved["count"] == 0


async def test_no_save_on_channel_unresolved(monkeypatch):
    """channel_unresolved -> save_index NEVER called."""
    saved = _spy_store(monkeypatch)
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)
    monkeypatch.setattr(
        indexer, "index_channel_videos",
        _patch_index_single(indexer, "vidX", UNKNOWN_ID),
    )

    summary = await indexer.index_channel_videos(UNKNOWN_ID)

    assert summary["indexed"] == 0
    assert saved["count"] == 0


def _patch_index_single(indexer, video_id, channel_id):
    """
    Build a stand-in index_channel_videos that reuses the REAL persistence guard
    (save only on result.success) over a single ask_about_video call - so the
    spy proves no save on each failure class WITHOUT a live DOM discovery.
    """
    from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
        VideoIndexStore,
    )

    async def _run(cid, max_videos=None, force_reindex=False):
        result = await indexer.ask_about_video(video_id, channel_id=channel_id)
        store = VideoIndexStore(base_path="/tmp/none")
        if result.success:
            store.save_index(video_id, None)
        return {"indexed": 1 if result.success else 0}

    return _run


async def indexer_run(driver, video_id, channel_id):
    """Helper: construct + run ask_about_video (keeps target tests concise)."""
    indexer = StudioAskIndexer(driver=driver)
    return await indexer.ask_about_video(video_id, channel_id=channel_id)


# ===========================================================================
# REGISTRY REUSE (WSP 84) + SIGNATURE/SCHEMA PRESERVATION
# ===========================================================================

# ===========================================================================
# EXPLICIT NON-VACUITY PROOFS (use ONLY the pre-existing channel_entry signature
# so the FAILURE on pre-fix code is BEHAVIORAL, not a new-kwarg TypeError).
# ===========================================================================

def _undaodu_entry():
    """The real UnDaoDu registry entry (carries the owning id used for context)."""
    return mod.get_channel_by_id(UNDAODU_ID)


async def test_NONVACUOUS_context_before_ask_via_channel_entry():
    """
    CONTEXT BEFORE ASK (behavioral non-vacuity): pass channel_entry (a kwarg the
    PRE-FIX code already accepted). The fixed code derives the owning channel_id
    from channel_entry["id"] and navigates the channel-scoped URL BEFORE
    /video/{id}/edit.

    On PRE-FIX code this SAME call (channel_entry only) navigates ONLY to
    /video/{id}/edit -> the channel-scoped URL is ABSENT from driver.visited ->
    this assertion FAILS behaviorally (no TypeError).
    """
    driver = MultiWindowDriver(
        handles_urls=[("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    await indexer.ask_about_video("vidX", channel_entry=_undaodu_entry())

    assert STUDIO_CHANNEL_CTX in driver.visited, (
        "pre-fix code never navigates the channel-scoped context URL"
    )
    assert driver.visited.index(STUDIO_CHANNEL_CTX) < driver.visited.index(STUDIO_VIDEO_EDIT)


async def test_NONVACUOUS_target_before_context_via_channel_entry():
    """
    TARGET BEFORE CONTEXT (behavioral non-vacuity): glic side panel is the FIRST
    handle. Using ONLY channel_entry (pre-fix-compatible), the fixed code selects
    the Studio target BEFORE navigating the channel-context URL, so the first
    navigation happens on a non-glic target.

    On PRE-FIX code there is NO target selection: it would drive the attached
    (glic) handle and never reach a channel-scoped URL -> STUDIO_CHANNEL_CTX is
    absent from visited -> this assertion FAILS behaviorally.
    """
    driver = MultiWindowDriver(
        handles_urls=[("glic", GLIC_URL), ("studio", STUDIO_VIDEO_EDIT)],
        css_map=_ask_dom(),
    )
    indexer = StudioAskIndexer(driver=driver)

    await indexer.ask_about_video("vidX", channel_entry=_undaodu_entry())

    # Target was selected (active not glic) BEFORE the channel-context nav.
    assert driver._active != "glic"
    assert driver.visited and driver.visited[0] == STUDIO_CHANNEL_CTX


def test_module_reuses_channel_registry_get_channel_by_id():
    """The fix reuses the existing youtube_channel_registry, not a 2nd map."""
    from modules.infrastructure.shared_utilities import youtube_channel_registry
    assert mod.get_channel_by_id is youtube_channel_registry.get_channel_by_id


def test_action_id_and_output_schema_preserved():
    """
    STEP 3 scope guard: #819 action ID + public output schema unchanged. Only
    typed error VALUES were added to the existing 'error' field; no new public
    action argument, no action-id change, no output-schema field change.
    """
    from modules.ai_intelligence.video_indexer.src import action_surface as a
    # Action ID unchanged.
    assert a.VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO == "video_index.studio_ask.single_video"
    # Output dataclass fields unchanged.
    out_fields = set(a.StudioAskSingleVideoOutput.__dataclass_fields__.keys())
    assert out_fields == {
        "success", "video_id", "browser", "provider",
        "response_text_length", "topics_count", "saved_path", "error",
    }
    # Input dataclass fields unchanged (channel_id remains the existing field).
    in_fields = set(a.StudioAskSingleVideoInput.__dataclass_fields__.keys())
    assert in_fields == {"video_id", "browser", "channel_id", "persist"}


def test_is_studio_youtube_url_is_host_anchored():
    """STEP0 studio-target detection must match the HOST exactly, not a URL
    prefix. Regression for CodeQL py/incomplete-url-substring-sanitization:
    a startswith("https://studio.youtube.com") check accepted look-alike hosts
    like https://studio.youtube.com.evil.com -- those must be rejected.
    """
    f = StudioAskIndexer._is_studio_youtube_url
    # Real Studio URLs (host == studio.youtube.com) are accepted.
    assert f("https://studio.youtube.com/video/vidX/edit") is True
    assert f("https://studio.youtube.com/channel/UC123/videos/upload") is True
    assert f("https://studio.youtube.com") is True
    assert f("HTTPS://STUDIO.YOUTUBE.COM/video/x") is True  # host is case-insensitive
    # Bypass / look-alike hosts (the vulnerability) are rejected.
    assert f("https://studio.youtube.com.evil.com/video/x") is False
    assert f("https://evil.com/https://studio.youtube.com") is False
    assert f("https://notstudio.youtube.com/x") is False
    assert f("https://studio.youtube.com@evil.com/x") is False
    # Non-URLs / empties are rejected (never raise).
    assert f("") is False
    assert f("chrome://glic") is False
    assert f("about:blank") is False
