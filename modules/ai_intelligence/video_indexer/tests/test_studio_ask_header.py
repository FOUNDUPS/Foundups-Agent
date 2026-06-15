"""
Tests for the Phase 1 "Ask Studio" header indexing path.

Covers:
  - Ask Studio header selectors are present in the selector set.
  - PRIMARY path: header button -> dialog -> contenteditable prompt -> Enter
    -> DOM-scraped response (no clipboard).
  - Old watch-page Ask missing but Ask Studio path still succeeds.
  - Response timeout fails closed (no DOM text -> success=False).
  - Channel prompt selection (undaodu != foundups; ffcpln/music is lighter;
    unknown channel falls back to the generic ASK_PROMPT).

All tests use a mock DOM driver - NO live YouTube, NO clipboard, NO network.

WSP Compliance:
    WSP 5/6: Test coverage + audit
    WSP 72: Module independence (no cross-module fixtures)
"""

import asyncio

import pytest

from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    StudioAskIndexer,
)


# ---------------------------------------------------------------------------
# Mock DOM / Selenium driver
# ---------------------------------------------------------------------------

class FakeElement:
    """Minimal stand-in for a Selenium WebElement."""

    def __init__(self, text="", attributes=None):
        self._text = text
        self._attributes = attributes or {}
        self.clicked = False
        self.sent_keys = []
        self.cleared = False

    @property
    def text(self):
        return self._text

    def get_attribute(self, name):
        return self._attributes.get(name, "")

    def click(self):
        self.clicked = True

    def clear(self):
        self.cleared = True

    def send_keys(self, value):
        self.sent_keys.append(value)


class FakeDriver:
    """
    Mock Selenium driver backed by a simple selector->element map.

    `css_map` maps a CSS selector string to a FakeElement (or None).
    `present_selectors` is the set of selectors considered "present"; a
    selector not in the map raises (mimicking NoSuchElement).
    """

    def __init__(self, css_map=None, script_result=None):
        self.css_map = css_map or {}
        self.script_result = script_result
        self.current_url = "https://studio.youtube.com/video/vidX/edit"
        self.visited = []

    def get(self, url):
        self.visited.append(url)
        self.current_url = url

    def find_element(self, by, selector):
        if selector in self.css_map and self.css_map[selector] is not None:
            return self.css_map[selector]
        raise Exception(f"NoSuchElement: {selector}")

    def find_elements(self, by, selector):
        el = self.css_map.get(selector)
        return [el] if el else []

    def execute_script(self, *args, **kwargs):
        # Legacy fallback JS calls return None by default (so the watch-page
        # Ask button is treated as MISSING unless a result is provided).
        return self.script_result


# Patch the indexer's human delay to be instant so timeout tests are fast.
@pytest.fixture(autouse=True)
def _fast_delays(monkeypatch):
    async def _no_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0)
    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _no_delay)
    # Shrink the response timeout so the fail-closed test is quick.
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 0.05)


def _ask_studio_dom(response_text):
    """Build a css_map where the Ask Studio PRIMARY path fully succeeds."""
    header = FakeElement(attributes={"aria-label": "Ask Studio"})
    dialog = FakeElement()
    prompt_box = FakeElement(attributes={"aria-label": "Ask something"})
    response = FakeElement(text=response_text)
    return {
        'ytcp-icon-button[aria-label="Ask Studio"]': header,
        "ytcp-dialog#dialog": dialog,
        'div[contenteditable][aria-label="Ask something"]': prompt_box,
        "#PAcreator_chat_streaming": response,
        "input#title-field, h1.title": FakeElement(attributes={"value": "Studio Title"}),
    }, prompt_box


# ---------------------------------------------------------------------------
# Selector presence tests
# ---------------------------------------------------------------------------

def test_ask_studio_header_selector_present():
    """ASK_STUDIO_SELECTORS must contain the canonical header target."""
    selectors = StudioAskIndexer.ASK_STUDIO_SELECTORS
    assert "header_button" in selectors
    assert any(
        'ytcp-icon-button[aria-label="Ask Studio"]' == s
        for s in selectors["header_button"]
    )


def test_ask_studio_dialog_and_prompt_selectors_present():
    selectors = StudioAskIndexer.ASK_STUDIO_SELECTORS
    assert "ytcp-dialog#dialog" in selectors["dialog"]
    assert 'div[contenteditable][aria-label="Ask something"]' in selectors["prompt_box"]
    assert (
        'div.ytcpCreatorChatEntityAttachmentInlineFlowPromptBox[contenteditable="true"]'
        in selectors["prompt_box"]
    )


def test_response_stream_selector_present():
    selectors = StudioAskIndexer.ASK_STUDIO_SELECTORS
    assert "#PAcreator_chat_streaming" in selectors["response_stream"]


def test_watch_page_is_not_primary():
    """Phase 1: watch-page Ask must be demoted (USE_WATCH_PAGE False)."""
    assert StudioAskIndexer.USE_WATCH_PAGE is False


# ---------------------------------------------------------------------------
# PRIMARY path behavior tests
# ---------------------------------------------------------------------------

async def test_ask_studio_primary_path_succeeds():
    """Header found, prompt typed, response scraped from DOM (no clipboard)."""
    css_map, prompt_box = _ask_studio_dom(
        '{"content_category": "educational", "topics": ["a", "b"], "segments": []}'
    )
    driver = FakeDriver(css_map=css_map, script_result=None)
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX")

    assert result.success is True
    assert "topics" in result.response_text  # came from the response DOM node
    # The prompt box (contenteditable) actually received keystrokes.
    assert prompt_box.clicked is True
    assert any("content_category" in str(k) or "Analyze" in str(k) or "Focus" in str(k)
               for k in prompt_box.sent_keys)
    # We navigated to the Studio edit page (PRIMARY), not the watch page first.
    assert driver.visited[0] == "https://studio.youtube.com/video/vidX/edit"


async def test_ask_studio_succeeds_when_watch_ask_missing():
    """
    Old watch-page Ask button is missing (execute_script returns None) but the
    Ask Studio header path still drives a successful index.
    """
    css_map, _ = _ask_studio_dom('{"topics": ["x"], "segments": []}')
    # script_result=None => legacy watch-page Ask button NOT found.
    driver = FakeDriver(css_map=css_map, script_result=None)
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX")

    assert result.success is True
    # Never had to fall back to the watch page.
    assert all("youtube.com/watch" not in url for url in driver.visited)


async def test_response_timeout_fails_closed():
    """No response DOM text -> success False, no garbage stored."""
    css_map, _ = _ask_studio_dom(response_text="")  # response node has empty text
    # Remove the response node entirely to simulate a stream that never fills.
    css_map["#PAcreator_chat_streaming"] = FakeElement(text="")
    driver = FakeDriver(css_map=css_map, script_result=None)
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX")

    assert result.success is False
    assert result.response_text == ""
    assert "timeout" in (result.error or "").lower()


async def test_no_clipboard_used(monkeypatch):
    """
    Guard: the indexing path must not call pyperclip / clipboard APIs.
    """
    import sys
    import types

    sentinel = {"used": False}
    fake_clip = types.ModuleType("pyperclip")

    def _paste():
        sentinel["used"] = True
        return ""

    def _copy(_):
        sentinel["used"] = True

    fake_clip.paste = _paste
    fake_clip.copy = _copy
    monkeypatch.setitem(sys.modules, "pyperclip", fake_clip)

    css_map, _ = _ask_studio_dom('{"topics": ["x"], "segments": []}')
    driver = FakeDriver(css_map=css_map, script_result=None)
    indexer = StudioAskIndexer(driver=driver)
    await indexer.ask_about_video("vidX")

    assert sentinel["used"] is False


# ---------------------------------------------------------------------------
# Channel prompt selection tests
# ---------------------------------------------------------------------------

def _entry(template):
    return {"key": "k", "name": "n", "shorts": {"description_template": template}}


def test_undaodu_prompt_differs_from_foundups():
    undaodu = StudioAskIndexer._prompt_for_channel(_entry("undaodu"))
    foundups = StudioAskIndexer._prompt_for_channel(_entry("foundups"))
    assert undaodu != foundups
    assert "UnDaoDu" in undaodu
    assert "FoundUps" in foundups


def test_ffcpln_music_prompt_is_lighter():
    """FFCPLN/music prompt must NOT demand a full transcript."""
    ffcpln = StudioAskIndexer._prompt_for_channel(_entry("ffcpln"))
    undaodu = StudioAskIndexer._prompt_for_channel(_entry("undaodu"))
    assert "Do NOT produce a full transcript" in ffcpln
    # Lighter == shorter than the speech-heavy channel prompt.
    assert len(ffcpln) < len(undaodu)


def test_unknown_channel_falls_back_to_generic():
    generic = StudioAskIndexer._prompt_for_channel(_entry("totally_unknown"))
    assert generic == StudioAskIndexer.ASK_PROMPT
    # None entry also falls back safely.
    assert StudioAskIndexer._prompt_for_channel(None) == StudioAskIndexer.ASK_PROMPT


async def test_channel_prompt_threaded_into_ask(monkeypatch):
    """index path passes channel_entry through so the ffcpln prompt is used."""
    css_map, prompt_box = _ask_studio_dom('{"topics": ["m"], "segments": []}')
    driver = FakeDriver(css_map=css_map, script_result=None)
    indexer = StudioAskIndexer(driver=driver)

    await indexer.ask_about_video("vidX", channel_entry=_entry("ffcpln"))

    typed = " ".join(str(k) for k in prompt_box.sent_keys)
    assert "Do NOT produce a full transcript" in typed
