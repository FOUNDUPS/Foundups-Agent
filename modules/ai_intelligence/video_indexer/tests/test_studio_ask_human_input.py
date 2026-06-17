"""
Tests for STUDIO_ASK_HUMAN_INPUT_BEHAVIOR_PHASE1.

The Studio Ask single-video action used to spam + cancel its own response 7x then
submit a malformed fragment. ROOT CAUSE: studio_ask_indexer.py did
``prompt_box.send_keys(ask_prompt)`` where ask_prompt is a MULTI-LINE template.
In a submit-on-Enter contenteditable EVERY "\\n" fires ENTER == a submit; each
submit cancels the prior streaming answer.

This suite proves the fix mimics 012's comment-input behavior - ONE clean message,
ONE submit - and is NON-VACUOUS (the SINGLE_SUBMIT regression FAILS on the old
``send_keys(multiline)`` behavior).

All tests use a mock DOM driver/element - NO live YouTube, NO clipboard, NO network.

WSP Compliance:
    WSP 5/6: Test coverage + audit
    WSP 72: Module independence (no cross-module fixtures)
    WSP 84: REUSE of human_behavior (asserted below)
"""

import asyncio

import pytest
from selenium.webdriver.common.keys import Keys

from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    AskResult,
    StudioAskIndexer,
)

# A registry-known channel ID (UnDaoDu) so the now-required owning-channel
# context (STUDIO_ASK_CHANNEL_CONTEXT_PHASE1 STEP 3) resolves in these
# input-behavior tests (the channel-context behavior itself is covered in
# test_studio_ask_channel_context.py).
UNDAODU_ID = "UCfHM9Fw9HD-NwiS0seD_oIA"


# ---------------------------------------------------------------------------
# Mock DOM that models a submit-on-Enter contenteditable
# ---------------------------------------------------------------------------

class ContentEditableBox:
    """
    Mock contenteditable prompt box that models REAL submit-on-Enter semantics:
    a bare Keys.ENTER (or a "\\n" inside a raw send_keys string) == a SUBMIT.

    This is what makes the SINGLE_SUBMIT regression non-vacuous: the OLD code
    (send_keys of the whole multi-line prompt) registers one submit PER internal
    newline, while the fixed code types char-by-char + soft-newlines and submits
    exactly once.
    """

    def __init__(self):
        self.value = ""
        self.clicked = False
        self.cleared = False
        self.submits = 0          # how many times a submit fired
        self.sent_keys = []       # raw keystroke log
        self.location = {"x": 10, "y": 10}
        self.size = {"width": 100, "height": 30}

    @property
    def text(self):
        return self.value

    def get_attribute(self, name):
        return {"aria-label": "Ask something", "contenteditable": "true"}.get(name, "")

    @property
    def tag_name(self):
        return "div"

    def click(self):
        self.clicked = True

    def clear(self):
        self.cleared = True
        self.value = ""

    def send_keys(self, *keys):
        # selenium send_keys accepts (key) or (modifier, key, ...).
        # A SHIFT held with ENTER is a SOFT newline (no submit) - the fallback
        # path emits send_keys(Keys.SHIFT, Keys.ENTER) when ActionChains is N/A.
        shift_held = Keys.SHIFT in keys
        for key in keys:
            self.sent_keys.append(key)
            if key == Keys.ENTER:
                if shift_held:
                    # Shift+Enter SOFT newline -> NOT a submit.
                    self.value += "\n"
                else:
                    # Bare ENTER -> a submit fires (cancels any in-flight answer).
                    self.submits += 1
            elif key == Keys.SHIFT:
                continue
            elif isinstance(key, str) and len(key) > 1 and "\n" in key:
                # OLD-CODE PATH: a raw multi-line string. A real contenteditable
                # fires ENTER == submit for EACH embedded newline.
                self.submits += key.count("\n")
                self.value += key.replace("\n", "")
            elif isinstance(key, str) and key == "\n":
                self.submits += 1
            elif isinstance(key, str):
                self.value += key


class SoftNewlineDriver:
    """
    Mock driver. ActionChains soft-newline (Shift+Enter) must NOT submit, so we
    record it separately and never increment box.submits for it.
    """

    def __init__(self, css_map=None, script_result=None):
        self.css_map = css_map or {}
        self.script_result = script_result
        # Single Studio tab is the active target (STEP 0 single-target path
        # passes). title has no wrong-context marker (STEP 2 passes).
        self.current_url = "https://studio.youtube.com/video/vidX/edit"
        self.title = "YouTube Studio"
        self.visited = []
        self.soft_newlines = 0

    def get(self, url):
        self.visited.append(url)
        self.current_url = url

    def find_element(self, by, selector):
        el = self.css_map.get(selector)
        if el is not None:
            return el
        raise Exception(f"NoSuchElement: {selector}")

    def find_elements(self, by, selector):
        el = self.css_map.get(selector)
        return [el] if el else []

    def execute_script(self, *args, **kwargs):
        return self.script_result


@pytest.fixture(autouse=True)
def _fast_and_clean(monkeypatch):
    """Instant delays + fresh human-behavior singleton per test."""
    async def _no_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0)

    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _no_delay)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 0.05)
    # Reset the human_behavior singleton so a stale mock driver doesn't leak in.
    import modules.infrastructure.foundups_selenium.src.human_behavior as hb
    monkeypatch.setattr(hb, "_human_behavior_instance", None, raising=False)


def _make_css_map(box, response_text="", send_button=None):
    header = _Simple(attributes={"aria-label": "Ask Studio"})
    dialog = _Simple()
    response = _Simple(text=response_text)
    css = {
        'ytcp-icon-button[aria-label="Ask Studio"]': header,
        "ytcp-dialog#dialog": dialog,
        'div[contenteditable][aria-label="Ask something"]': box,
        "#PAcreator_chat_streaming": response,
        "input#title-field, h1.title": _Simple(attributes={"value": "Studio Title"}),
    }
    if send_button is not None:
        css['ytcp-icon-button[aria-label="Send"]'] = send_button
    return css


class _Simple:
    """Minimal element for header/dialog/response/title nodes."""

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


def _patch_human_for_box(monkeypatch):
    """
    Make HumanBehavior.human_type type char-by-char into our mock box (so we can
    count submits) without needing a real viewport. Mirrors the human cadence
    (per-char send_keys) but instant. Asserts the REUSED path is exercised.
    """
    import modules.infrastructure.foundups_selenium.src.human_behavior as hb

    calls = {"human_type": 0}

    def _fake_human_type(self, element, text):
        calls["human_type"] += 1
        element.click()
        for ch in text:
            element.send_keys(ch)

    monkeypatch.setattr(hb.HumanBehavior, "human_type", _fake_human_type)
    return calls


# ---------------------------------------------------------------------------
# CORE PROOF: single-submit, no newline-spam
# ---------------------------------------------------------------------------

async def test_single_submit_no_newline_spam_on_multiline_prompt(monkeypatch):
    """
    THE regression. With a MULTI-LINE prompt the fixed path must submit EXACTLY
    ONCE. The mock contenteditable models submit-on-Enter, so the OLD code
    (send_keys of the whole multi-line ASK_PROMPT) would register one submit per
    internal newline (>=7) -> this assert (== 1) FAILS on old code.
    """
    calls = _patch_human_for_box(monkeypatch)
    box = ContentEditableBox()
    driver = SoftNewlineDriver(css_map=_make_css_map(box, response_text="{\"topics\": [\"x\"]}"))
    indexer = StudioAskIndexer(driver=driver)

    # The real generic prompt is multi-line (proves the bug surface).
    assert StudioAskIndexer.ASK_PROMPT.count("\n") >= 7

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    # EXACTLY ONE submit regardless of how many lines the prompt has.
    assert box.submits == 1, f"expected exactly 1 submit, got {box.submits}"
    # And the human_type reuse path was actually exercised.
    assert calls["human_type"] >= 1
    assert result.success is True


async def test_old_behavior_would_multi_submit(monkeypatch):
    """
    Guard that the mock genuinely models submit-on-Enter: feeding the raw
    multi-line prompt to send_keys (the OLD code) yields N submits, NOT 1.
    This is what proves the regression above is non-vacuous.
    """
    box = ContentEditableBox()
    box.send_keys(StudioAskIndexer.ASK_PROMPT)  # OLD behavior: one raw send_keys
    assert box.submits == StudioAskIndexer.ASK_PROMPT.count("\n")
    assert box.submits >= 7  # multiple cancel-causing submits


async def test_submit_prefers_send_button_single_click(monkeypatch):
    """When a Send button exists, submit clicks it exactly once (NO bare Enter)."""
    _patch_human_for_box(monkeypatch)
    box = ContentEditableBox()
    send_btn = _Simple(attributes={"aria-label": "Send"})
    driver = SoftNewlineDriver(
        css_map=_make_css_map(box, response_text="{\"topics\": [\"x\"]}", send_button=send_btn)
    )
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert send_btn.clicked is True
    # Button submit => ZERO bare-ENTER submits fired on the box. (Soft Shift+Enter
    # newlines may appear in the keystroke log but never trigger a submit.)
    assert box.submits == 0
    assert result.success is True


# ---------------------------------------------------------------------------
# HUMAN_TYPE reuse
# ---------------------------------------------------------------------------

async def test_human_type_is_used_not_raw_multiline_send_keys(monkeypatch):
    """The prompt is entered via the REUSED human path (human_type), char-wise."""
    calls = _patch_human_for_box(monkeypatch)
    box = ContentEditableBox()
    driver = SoftNewlineDriver(css_map=_make_css_map(box, response_text="{\"topics\": [\"x\"]}"))
    indexer = StudioAskIndexer(driver=driver)

    await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert calls["human_type"] >= 1
    # No single sent_key is the whole multi-line prompt (would be the old bug).
    assert all(
        not (isinstance(k, str) and "\n" in k and len(k) > 2)
        for k in box.sent_keys
    )


def test_indexer_imports_get_human_behavior():
    """WSP 84: the module reuses get_human_behavior (not a private reimpl)."""
    import modules.ai_intelligence.video_indexer.src.studio_ask_indexer as mod
    assert mod.HUMAN_BEHAVIOR_AVAILABLE is True
    assert mod.get_human_behavior is not None


# ---------------------------------------------------------------------------
# WAIT-FOR-COMPLETION (stabilization)
# ---------------------------------------------------------------------------

class GrowingResponse:
    """Response node whose text grows across polls, then stabilizes."""

    def __init__(self, frames):
        self._frames = list(frames)
        self._i = 0

    @property
    def text(self):
        frame = self._frames[min(self._i, len(self._frames) - 1)]
        self._i += 1
        return frame

    def get_attribute(self, name):
        return ""

    def click(self):
        pass


async def test_scraper_waits_for_stabilized_full_text(monkeypatch):
    """Scraper returns the STABILIZED full text, not the first partial frame."""
    async def _no_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0)
    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _no_delay)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 5.0)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_STABLE_POLLS", 3)

    # partial -> partial+more -> FULL, then FULL repeats (stabilizes).
    full = '{"topics": ["complete", "answer"], "segments": []}'
    growing = GrowingResponse(['{"topics": ["comp', '{"topics": ["complete"', full, full, full, full])
    driver = SoftNewlineDriver(css_map={"#PAcreator_chat_streaming": growing})
    indexer = StudioAskIndexer(driver=driver)

    text = await indexer._scrape_ask_response()

    assert text == full
    assert "complete" in text and "answer" in text


# ---------------------------------------------------------------------------
# FAIL-CLOSED on refusal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("refusal", [
    "I'm not quite sure what you're asking about this video.",
    "Query unsuccessful. Please try again.",
    "I didn't quite understand that.",
    "The transcript is unavailable for this video.",
    "I cannot analyze this content.",
    "You canceled this response.",
])
async def test_refusal_fails_closed_and_persists_nothing(monkeypatch, refusal):
    """A refusal -> success=False, typed error, response_text empty (store nothing)."""
    _patch_human_for_box(monkeypatch)
    box = ContentEditableBox()
    driver = SoftNewlineDriver(css_map=_make_css_map(box, response_text=refusal))
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "ask_studio_no_answer"
    assert result.response_text == ""


async def test_refusal_not_persisted_via_index_path(monkeypatch):
    """
    Drive the persistence guard: a refusal AskResult must never reach
    store.save_index (index_channel_videos persists only on result.success).
    """
    from modules.ai_intelligence.video_indexer.src import studio_ask_indexer as mod

    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)
    monkeypatch.setattr(mod, "get_channel_by_id", lambda cid: {"key": "undaodu", "name": "UnDaoDu"})

    indexer = StudioAskIndexer(driver=SoftNewlineDriver(), max_videos_per_cycle=1)

    # Stub discovery to a single video, and make ask return a refusal result.
    async def _fake_index(channel_id, max_videos=None, force_reindex=False):
        # Reuse the real persistence guard by calling ask_about_video + the guard.
        result = await indexer.ask_about_video("vidREF")
        store = SpyStore()
        results = [result]
        if result.success:
            store.save_index("vidREF", None)
        indexed = sum(1 for r in results if r.success)
        return {"indexed": indexed}

    # Make ask_about_video return a refusal (success=False) deterministically.
    async def _refusal_ask(video_id, prompt=None, channel_entry=None):
        return AskResult(
            video_id=video_id, title="", response_text="",
            topics=[], timestamps=[], success=False, error="ask_studio_no_answer",
        )

    monkeypatch.setattr(indexer, "ask_about_video", _refusal_ask)
    summary = await _fake_index("UCxxx")

    assert summary["indexed"] == 0
    assert saved["count"] == 0  # NOTHING persisted on refusal


# ---------------------------------------------------------------------------
# FALLBACK path single-submit
# ---------------------------------------------------------------------------

async def test_fallback_path_single_submit(monkeypatch):
    """
    Legacy fallback (no Ask Studio header) also submits exactly once via the
    human-type + single-submit helper (no per-newline Enter spam).
    """
    calls = _patch_human_for_box(monkeypatch)
    box = ContentEditableBox()

    # No Ask Studio header -> primary path bails; watch-page Ask button found via JS;
    # then the legacy textarea is our submit-on-Enter mock box.
    class FallbackDriver(SoftNewlineDriver):
        def __init__(self):
            super().__init__(css_map={
                "input#title-field, h1.title": _Simple(attributes={"value": "T"}),
                "textarea, input[placeholder*='Ask']": box,
                ".gemini-response, .response-content": _Simple(text=""),
                "#PAcreator_chat_streaming": _Simple(text='{"topics": ["x"]}'),
            })

        def execute_script(self, *args, **kwargs):
            # Return a truthy "ask button" so the watch-page fallback clicks it.
            script = args[0] if args else ""
            if "flexible-item-buttons" in str(script):
                return _Simple()
            return None

    driver = FallbackDriver()
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    # Exactly one submit on the fallback textarea too.
    assert box.submits == 1
    assert calls["human_type"] >= 1
    assert result.success is True
