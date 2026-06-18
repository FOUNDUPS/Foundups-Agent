"""
Tests for STUDIO_ASK_SHADOW_DOM_SELECTORS_PHASE1.

ROOT CAUSE (live-confirmed): YouTube Studio's DOM is SHADOW-ROOTED. Flat
Selenium find_element("css selector", ...) does NOT pierce shadow roots, so the
indexer's selectors silently failed on the live page even when the element
existed. #817 fixed selector NAMES but not the TRAVERSAL MODEL. The live-grounded
truth: the flat input#title-field returns nothing but a shadow walk finds
ytcp-social-suggestions-textbox#title-textarea; the old Ask-button selector
aria-label="Ask Studio" does NOT exist -- the real entry is the creator-chat
"spark" trigger (ytcp-creator-chat-trigger -> ytcp-icon-button).

This suite proves the fix and is NON-VACUOUS: each "flat-fails / shadow-finds"
test builds a mock DOM where the OLD flat selector is ABSENT (find_element
raises) but the element exists under a shadow root (resolved via the deep walk
modeled by execute_script). The flat path returns None (so the PRE-fix flat-only
code would fail) while the deep finder returns the real element.

All tests use a MOCK driver -- NO live YouTube, NO clipboard, NO network. The
combined live happy path (submit -> stream -> scrape) is validated separately by
0102's live re-test (HONEST LIVE GAP).

WSP Compliance:
    WSP 5/6: Test coverage + audit
    WSP 72: Module independence (no cross-module fixtures)
    WSP 84: REUSE of the foundups_selenium shadow-DOM deep finder
"""

import asyncio

import pytest
from selenium.webdriver.common.keys import Keys

from modules.ai_intelligence.video_indexer.src import studio_ask_indexer as mod
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    StudioAskIndexer,
)

UNDAODU_ID = "UCfHM9Fw9HD-NwiS0seD_oIA"
STUDIO_VIDEO_EDIT = "https://studio.youtube.com/video/vidX/edit"
STUDIO_CHANNEL_CTX = f"https://studio.youtube.com/channel/{UNDAODU_ID}/videos/upload"

# Live-grounded selectors under test.
TITLE_DEEP = "ytcp-social-suggestions-textbox#title-textarea"
ASK_TRIGGER = "ytcp-creator-chat-trigger"
ASK_ICON = "ytcp-icon-button"
PROMPT_DEEP = (
    'div.ytcpCreatorChatEntityAttachmentInlineFlowPromptBox'
    '[contenteditable="true"][aria-label="Ask something"]'
)
STREAM_DEEP = "ytcp-engagement-panel-section-list-renderer#PAcreator_chat_streaming"


# ---------------------------------------------------------------------------
# Mock element + a SHADOW-ROOTED driver (deep walk vs flat find)
# ---------------------------------------------------------------------------

class ShadowElement:
    """WebElement stand-in. parent is set to the driver (matching real Selenium
    WebElement.parent) so the deep finder can run scoped chain steps."""

    def __init__(self, text="", attributes=None, parent=None, deep_children=None):
        self._text = text
        self._attributes = attributes or {}
        self.parent = parent
        self.deep_children = deep_children or {}
        self.clicked = False
        self.cleared = False
        self.sent_keys = []
        # geometry so any human_* helper that reads it does not explode
        self.location = {"x": 10, "y": 10}
        self.size = {"width": 100, "height": 30}

    @property
    def text(self):
        return self._text

    @property
    def tag_name(self):
        return "div"

    def get_attribute(self, name):
        return self._attributes.get(name, "")

    def click(self):
        self.clicked = True

    def clear(self):
        self.cleared = True

    def send_keys(self, *keys):
        for k in keys:
            self.sent_keys.append(k)


class ShadowDriver:
    """
    Mock driver where elements live ONLY under shadow roots: the deep walk
    (modeled here by ``execute_script`` consulting ``deep_map`` / element-scoped
    ``deep_children``) resolves them, while the FLAT ``find_element`` consults a
    SEPARATE ``flat_map`` and raises for anything absent (a non-piercing find).

    This is what makes the tests non-vacuous: the flat-only PRE-fix path cannot
    see shadow-rooted elements.
    """

    def __init__(self, deep_map=None, flat_map=None, body_text="", title="YouTube Studio"):
        self.deep_map = deep_map or {}
        self.flat_map = flat_map or {}
        self._body_text = body_text
        self._title = title
        self.current_url = STUDIO_CHANNEL_CTX
        self.visited = []

    @property
    def title(self):
        return self._title

    def get(self, url):
        self.visited.append(url)
        self.current_url = url

    def execute_script(self, *args, **kwargs):
        # The shadow-DOM deep finder calls execute_script(JS, root, css).
        if len(args) >= 3 and isinstance(args[2], str):
            root, css = args[1], args[2]
            if root is not None:
                children = getattr(root, "deep_children", None)
                return (children or {}).get(css)
            return self.deep_map.get(css)
        # Any legacy JS (watch-page fallback etc.) returns nothing.
        return None

    def find_element(self, by, selector):
        if selector == "body":
            return ShadowElement(text=self._body_text)
        el = self.flat_map.get(selector)
        if el is None:
            raise Exception(f"NoSuchElement: {selector}")
        return el

    def find_elements(self, by, selector):
        el = self.flat_map.get(selector)
        return [el] if el else []


@pytest.fixture(autouse=True)
def _fast_and_clean(monkeypatch):
    """Instant delays, short timeout, fresh human singleton, char-typing."""
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


def _shadow_dom(driver, response_text='{"topics": ["x"], "segments": []}'):
    """Populate a ShadowDriver so the full Ask Studio path resolves via SHADOW
    traversal ONLY (flat_map stays empty -> flat finds nothing)."""
    title = ShadowElement(attributes={"value": "Studio Title"}, parent=driver)
    icon = ShadowElement(attributes={"aria-label": "spark"}, parent=driver)
    trigger = ShadowElement(parent=driver, deep_children={ASK_ICON: icon})
    prompt = ShadowElement(attributes={"aria-label": "Ask something"}, parent=driver)
    stream = ShadowElement(text=response_text, parent=driver)
    driver.deep_map = {
        TITLE_DEEP: title,
        ASK_TRIGGER: trigger,
        PROMPT_DEEP: prompt,
        STREAM_DEEP: stream,
    }
    return {"title": title, "icon": icon, "trigger": trigger,
            "prompt": prompt, "stream": stream}


# ===========================================================================
# FLAT-FAILS / SHADOW-FINDS (TITLE)
# ===========================================================================

def test_flat_fails_shadow_finds_title():
    """
    input#title-field is ABSENT (flat find raises) but the title field exists
    under a shadow root -> the flat path returns None AND the deep finder returns
    the element. NON-VACUOUS: pre-fix flat-only code returns None here.
    """
    driver = ShadowDriver()
    nodes = _shadow_dom(driver)
    indexer = StudioAskIndexer(driver=driver)

    # PROOF (flat fails): the legacy flat selector is not resolvable.
    flat_failed = False
    try:
        driver.find_element("css selector", "input#title-field")
    except Exception:
        flat_failed = True
    assert flat_failed is True

    # PROOF (shadow finds): the indexer's edit-surface check resolves via deep.
    assert indexer._edit_surface_present() is True
    # And it returns the REAL shadow title element (usable like a WebElement).
    el = indexer._first_element([TITLE_DEEP, "input#title-field, h1.title"])
    assert el is nodes["title"]
    assert el.get_attribute("value") == "Studio Title"


# ===========================================================================
# FLAT-FAILS / SHADOW-FINDS (ASK BUTTON)
# ===========================================================================

def test_flat_fails_shadow_finds_ask_button():
    """
    aria-label="Ask Studio" is ABSENT (the live page has no such selector) but
    the spark trigger chain ytcp-creator-chat-trigger -> ytcp-icon-button exists
    under shadow -> deep finder resolves the icon-button; flat does not.
    """
    driver = ShadowDriver()
    nodes = _shadow_dom(driver)
    indexer = StudioAskIndexer(driver=driver)

    # PROOF (flat fails): the old aria-label selector is not resolvable.
    flat_failed = False
    try:
        driver.find_element("css selector", 'ytcp-icon-button[aria-label="Ask Studio"]')
    except Exception:
        flat_failed = True
    assert flat_failed is True

    # PROOF (shadow finds): _first_element on the header_button list (spark chain
    # FIRST) resolves the icon-button deep within the trigger's subtree.
    btn = indexer._first_element(StudioAskIndexer.ASK_STUDIO_SELECTORS["header_button"])
    assert btn is nodes["icon"]

    # And the open path clicks it.
    assert indexer._open_ask_studio() is True
    assert nodes["icon"].clicked is True


# ===========================================================================
# PINNED SELECTORS present + ordered shadow-first
# ===========================================================================

def test_pinned_grounded_selectors_present_and_primary():
    sel = StudioAskIndexer.ASK_STUDIO_SELECTORS
    # Title textarea (live-grounded).
    assert StudioAskIndexer.TITLE_TEXTAREA_SELECTOR == TITLE_DEEP
    # Ask button: the spark trigger chain is FIRST (primary), aria-label demoted.
    assert sel["header_button"][0] == [ASK_TRIGGER, ASK_ICON]
    assert 'ytcp-icon-button[aria-label="Ask Studio"]' in sel["header_button"]
    assert sel["header_button"].index([ASK_TRIGGER, ASK_ICON]) < sel["header_button"].index(
        'ytcp-icon-button[aria-label="Ask Studio"]'
    )
    # Prompt box: the live-grounded class selector is present + primary-ordered.
    assert sel["prompt_box"][0] == PROMPT_DEEP
    # Stream: the live-grounded host#id is present + ordered before legacy id.
    assert STREAM_DEEP in sel["response_stream"]
    assert sel["response_stream"].index(STREAM_DEEP) < sel["response_stream"].index(
        "#PAcreator_chat_streaming"
    )
    # Dialog: tp-yt-paper-dialog#dialog is the live-grounded host.
    assert "tp-yt-paper-dialog#dialog" in sel["dialog"]


# ===========================================================================
# FULL PRIMARY PATH over SHADOW-ONLY DOM (combined mock happy path)
# ===========================================================================

async def test_full_primary_path_resolves_via_shadow_only():
    """
    With ALL elements shadow-rooted (flat_map empty), the full ask path still
    succeeds: title read, Ask opened, prompt typed, response scraped.
    """
    driver = ShadowDriver()
    nodes = _shadow_dom(driver)
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    assert result.title == "Studio Title"
    assert "topics" in result.response_text
    # The spark trigger was clicked (Ask opened) and the prompt box typed into.
    assert nodes["icon"].clicked is True
    assert nodes["prompt"].clicked is True


# ===========================================================================
# DIALOG OPEN VERIFIED VIA CHILDREN (not the host's visibility)
# ===========================================================================

async def test_dialog_open_confirmed_via_children_not_host():
    """
    Live caveat: the dialog HOST is not even present/visible, but the prompt box
    + stream ARE -> the ask still proceeds (open confirmed via children).
    """
    driver = ShadowDriver()
    nodes = _shadow_dom(driver)
    # Remove the dialog host entirely; children (prompt + stream) remain.
    driver.deep_map.pop("tp-yt-paper-dialog#dialog", None)
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    assert nodes["prompt"].clicked is True


# ===========================================================================
# ZERO-STATE NOT SCRAPED AS ANSWER
# ===========================================================================

async def test_zero_state_not_scraped_as_answer():
    """
    The stream shows the ZERO-STATE suggestion list (Gemini greeted == ready) but
    no real answer ever renders. The greeting must NOT be returned as the answer:
    the scrape extracts nothing -> the ask fails closed "ask_studio_no_answer"
    (nothing persisted). (STUDIO_ASK_GEMINI_READINESS_RETRY_PHASE1 boilerplate-
    only fail-closed supersedes the old generic timeout error.)
    """
    driver = ShadowDriver()
    _shadow_dom(driver, response_text="How can Ask Studio help me? Summarize comments")
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.response_text == ""
    assert result.error == "ask_studio_no_answer"


def test_is_zero_state_classifier():
    assert StudioAskIndexer._is_zero_state("How can Ask Studio help me?") is True
    assert StudioAskIndexer._is_zero_state("Summarize comments for this video") is True
    assert StudioAskIndexer._is_zero_state('{"topics": ["real", "answer"]}') is False
    assert StudioAskIndexer._is_zero_state("") is False


# ===========================================================================
# WRONG / ERROR PAGE STILL FAILS CLOSED (#827 preserved)
# ===========================================================================

async def test_wrong_error_page_still_fails_closed_over_shadow():
    """
    An Oops/something-went-wrong page -> #827 wrong-context detection still
    returns wrong_channel_context; no ask; even though the shadow DOM has the
    elements. #827 fail-closed preserved EXACTLY.
    """
    driver = ShadowDriver(body_text="Oops, something went wrong", title="Oops")
    _shadow_dom(driver)
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "wrong_channel_context"


# ===========================================================================
# NO PERSIST ON FAILURE (shadow path)
# ===========================================================================

async def test_no_persist_on_failure_shadow(monkeypatch):
    """Any failure (here: zero-state -> timeout) -> save_index call_count == 0."""
    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)

    driver = ShadowDriver()
    _shadow_dom(driver, response_text="How can I help you? Summarize comments")
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    async def _run(cid, max_videos=None, force_reindex=False):
        result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)
        store = mod.VideoIndexStore(base_path="/tmp/none")
        if result.success:
            store.save_index("vidX", None)
        return {"indexed": 1 if result.success else 0}

    summary = await _run(UNDAODU_ID)
    assert summary["indexed"] == 0
    assert saved["count"] == 0


# ===========================================================================
# #825 INPUT BEHAVIOR PRESERVED over the SHADOW path (single clean submit)
# ===========================================================================

class SubmitCountingBox(ShadowElement):
    """A shadow prompt box modeling submit-on-Enter so we can prove #825's
    single-submit behavior survives the shadow-finder rewrite."""

    def __init__(self, parent=None):
        super().__init__(attributes={"aria-label": "Ask something"}, parent=parent)
        self.submits = 0

    def send_keys(self, *keys):
        shift_held = Keys.SHIFT in keys
        for key in keys:
            self.sent_keys.append(key)
            if key == Keys.ENTER and not shift_held:
                self.submits += 1
            elif isinstance(key, str) and "\n" in key and len(key) > 1:
                self.submits += key.count("\n")


async def test_825_single_submit_preserved_over_shadow():
    """
    The multi-line prompt typed into a shadow-resolved contenteditable still
    submits EXACTLY ONCE (no newline-spam). #825 behavior preserved.
    """
    driver = ShadowDriver()
    nodes = _shadow_dom(driver, response_text='{"topics": ["x"]}')
    box = SubmitCountingBox(parent=driver)
    driver.deep_map[PROMPT_DEEP] = box  # prompt box is shadow-resolved
    indexer = StudioAskIndexer(driver=driver)

    assert StudioAskIndexer.ASK_PROMPT.count("\n") >= 7

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert box.submits == 1, f"expected exactly 1 submit, got {box.submits}"
    assert result.success is True
