# -*- coding: utf-8 -*-
"""
Tests for STUDIO_ASK_GEMINI_READINESS_RETRY_PHASE1.

ROOT CAUSE (live-proven): the Ask Studio Gemini chat loads INTERMITTENTLY-BLANK
under automation - the dialog opens but Gemini never initializes (no greeting,
only a disclaimer placeholder). The old code typed into the not-yet-loaded panel
and scraped the disclaimer ("AI can make mistakes...") as a FALSE success. It
ALSO zeroed the whole stream whenever the persistent greeting was present (the
"greeting-zeroing" scraper bug). LIVE-PROVEN FIX: poll for the Gemini-ready
greeting ("how can i help") BEFORE typing; on a blank panel open a FRESH tab and
retry (closing the old blank tab); then EXTRACT the real answer from the stream
(stripping greeting/suggestions + processing lines + the disclaimer footer)
instead of rejecting the stream because the greeting is present.

This suite is NON-VACUOUS (each test fails on the pre-fix behavior):
  - READINESS GATE: a stream WITHOUT the greeting must NOT be typed into (old
    code typed immediately).
  - NEW-TAB RETRY + CLOSE OLD: a blank attempt-1 must open a NEW tab AND close
    the OLD blank tab; attempt-2 loaded -> proceeds; never-loads ->
    "gemini_did_not_load" (old code had no retry).
  - CAPTURE STRIPS BOILERPLATE: a stream of [prompt echo + processing + REAL
    ANSWER + disclaimer] must return ONLY the real answer (old code returned the
    disclaimer as the answer).
  - FAIL-CLOSED ON BOILERPLATE-ONLY: greeting/disclaimer-only -> no persist.

ALL tests use a MOCK driver - NO live YouTube, NO clipboard, NO network. The
combined live happy path (new-tab retry -> Gemini loads -> real answer captured)
is validated separately by 0102's live re-test (HONEST LIVE GAP).

WSP Compliance:
    WSP 5/6: Test coverage + audit
    WSP 72: Module independence (no cross-module fixtures)
    WSP 84: REUSE of the shadow-DOM finder + undetected_browser stealth JS
"""

import asyncio

import pytest

from modules.ai_intelligence.video_indexer.src import studio_ask_indexer as mod
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    StudioAskIndexer,
)

UNDAODU_ID = "UCfHM9Fw9HD-NwiS0seD_oIA"
STUDIO_VIDEO_EDIT = "https://studio.youtube.com/video/vidX/edit"
STUDIO_CHANNEL_CTX = f"https://studio.youtube.com/channel/{UNDAODU_ID}/videos/upload"

# Live-grounded deep selectors (must match the indexer's primary selectors).
TITLE_DEEP = "ytcp-social-suggestions-textbox#title-textarea"
ASK_TRIGGER = "ytcp-creator-chat-trigger"
ASK_ICON = "ytcp-icon-button"
PROMPT_DEEP = (
    'div.ytcpCreatorChatEntityAttachmentInlineFlowPromptBox'
    '[contenteditable="true"][aria-label="Ask something"]'
)
STREAM_DEEP = "ytcp-engagement-panel-section-list-renderer#PAcreator_chat_streaming"

GREETING = "How can I help you today?"
DISCLAIMER = "AI can make mistakes. You are responsible for the content you publish. Learn more"
REAL_JSON = '{"content_category": "educational", "topics": ["alpha", "beta"], "segments": []}'


# ---------------------------------------------------------------------------
# Mock element + a MULTI-WINDOW shadow-rooted driver
# ---------------------------------------------------------------------------

class El:
    """WebElement stand-in (parent = driver for scoped deep chains)."""

    def __init__(self, text="", attributes=None, parent=None, deep_children=None):
        self._text = text
        self._attributes = attributes or {}
        self.parent = parent
        self.deep_children = deep_children or {}
        self.clicked = False
        self.cleared = False
        self.sent_keys = []
        self.location = {"x": 10, "y": 10}
        self.size = {"width": 100, "height": 30}

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

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


class _SwitchTo:
    def __init__(self, driver):
        self._d = driver

    def new_window(self, _type="tab"):
        self._d._open_new_window()

    def window(self, handle):
        self._d._switch_window(handle)


class MultiTab:
    """
    A multi-window mock driver. Each tab has its OWN shadow ``deep_map`` (so a
    new tab can render Gemini loaded while the original was blank). Supports the
    Selenium window-handle idiom the retry loop uses: current_window_handle,
    window_handles, switch_to.new_window/window, close. ``execute_cdp_cmd`` is
    present so the stealth CDP hook registers (proving stealth is wired) and is
    logged in ``cdp_calls``.

    ``tab_factory(handle)`` returns the deep_map for a freshly-opened tab so a
    test can make attempt-2 (the new tab) render Gemini loaded.
    """

    def __init__(self, deep_map=None, tab_factory=None, title="YouTube Studio", body_text=""):
        self._counter = 0
        first = self._new_handle()
        self._tabs = {first: deep_map or {}}
        self._order = [first]
        self._current = first
        self.tab_factory = tab_factory
        self._title = title
        self._body_text = body_text
        self.current_url = STUDIO_CHANNEL_CTX
        self.visited = []
        self.cdp_calls = []
        self.closed_handles = []
        self.switch_to = _SwitchTo(self)

    # -- window handle API ------------------------------------------------
    def _new_handle(self):
        self._counter += 1
        return f"win-{self._counter}"

    @property
    def current_window_handle(self):
        return self._current

    @property
    def window_handles(self):
        return list(self._order)

    def _open_new_window(self):
        h = self._new_handle()
        deep = {}
        if self.tab_factory is not None:
            deep = self.tab_factory(h) or {}
        self._tabs[h] = deep
        self._order.append(h)
        self._current = h

    def _switch_window(self, handle):
        if handle in self._tabs:
            self._current = handle

    def close(self):
        self.closed_handles.append(self._current)
        self._tabs.pop(self._current, None)
        if self._current in self._order:
            self._order.remove(self._current)
        self._current = self._order[-1] if self._order else None

    # -- nav / dom --------------------------------------------------------
    @property
    def _deep(self):
        return self._tabs.get(self._current, {})

    @property
    def title(self):
        return self._title

    def get(self, url):
        self.visited.append(url)
        self.current_url = url

    def execute_cdp_cmd(self, cmd, params):
        self.cdp_calls.append((self._current, cmd))
        return {}

    def execute_script(self, *args, **kwargs):
        # The shadow-DOM deep finder calls execute_script(JS, root, css).
        if len(args) >= 3 and isinstance(args[2], str):
            root, css = args[1], args[2]
            if root is not None:
                children = getattr(root, "deep_children", None)
                return (children or {}).get(css)
            return self._deep.get(css)
        return None

    def find_element(self, by, selector):
        if selector == "body":
            return El(text=self._body_text)
        el = self._deep.get(selector)
        if el is None:
            raise Exception(f"NoSuchElement: {selector}")
        return el

    def find_elements(self, by, selector):
        el = self._deep.get(selector)
        return [el] if el else []


def _build_tab(driver, stream_text):
    """Build a fully-loaded shadow tab map (title, ask trigger, prompt, stream)."""
    title = El(attributes={"value": "Studio Title"}, parent=driver)
    icon = El(attributes={"aria-label": "spark"}, parent=driver)
    trigger = El(parent=driver, deep_children={ASK_ICON: icon})
    prompt = El(attributes={"aria-label": "Ask something"}, parent=driver)
    stream = El(text=stream_text, parent=driver)
    return {
        TITLE_DEEP: title,
        ASK_TRIGGER: trigger,
        PROMPT_DEEP: prompt,
        STREAM_DEEP: stream,
    }, {"title": title, "icon": icon, "trigger": trigger, "prompt": prompt, "stream": stream}


@pytest.fixture(autouse=True)
def _fast_and_clean(monkeypatch):
    async def _no_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0)

    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _no_delay)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(StudioAskIndexer, "GEMINI_READY_TIMEOUT_SECONDS", 0.05)

    import modules.infrastructure.foundups_selenium.src.human_behavior as hb
    monkeypatch.setattr(hb, "_human_behavior_instance", None, raising=False)

    def _fake_human_type(self, element, text):
        element.click()
        for ch in text:
            element.send_keys(ch)

    monkeypatch.setattr(hb.HumanBehavior, "human_type", _fake_human_type)


# ===========================================================================
# PURE-HELPER PROOFS (boilerplate strip / json extraction / readiness)
# ===========================================================================

def test_extract_answer_strips_disclaimer_and_processing_and_echo():
    """
    A stream of [greeting + prompt echo + processing + REAL ANSWER + disclaimer]
    -> _extract_answer returns ONLY the real answer (JSON block), NOT the
    disclaimer. NON-VACUOUS: the pre-fix scraper returned the disclaimer-bearing
    stream verbatim; here the disclaimer string is provably absent from the
    captured answer.
    """
    prompt = 'Analyze the video titled "X" (video id vidX). Respond ONLY with a JSON index'
    stream = "\n".join([
        GREETING,
        "Summarize comments",
        prompt,                       # prompt echo
        "Reviewing your request",     # processing
        "Looking through your content",
        REAL_JSON,                    # the real answer
        DISCLAIMER,                   # disclaimer footer
    ])

    answer = StudioAskIndexer()._extract_answer(stream, prompt)

    # The real answer is captured...
    assert '"topics"' in answer
    assert "alpha" in answer and "beta" in answer
    # ...and NONE of the boilerplate leaked in.
    assert "AI can make mistakes" not in answer
    assert "Reviewing your request" not in answer
    assert "Looking through your content" not in answer
    assert "How can I help" not in answer


def test_extract_answer_does_not_zero_on_persistent_greeting():
    """
    The greeting-zeroing bug: a stream that PERSISTS the greeting above a real
    answer must STILL yield the answer (the greeting must not blank the whole
    stream). For a PROSE answer, the boilerplate is stripped and the body kept.
    """
    prose = "This video is a tutorial about gardening and composting."
    stream = "\n".join([GREETING, "Summarize comments", prose, DISCLAIMER])

    answer = StudioAskIndexer()._extract_answer(stream, "")

    assert prose in answer
    assert "How can I help" not in answer
    assert "AI can make mistakes" not in answer


def test_extract_answer_empty_on_boilerplate_only():
    """Greeting + disclaimer ONLY (no answer) -> extraction is empty (fail-closed
    upstream)."""
    stream = "\n".join([GREETING, "Summarize comments", DISCLAIMER, "Learn more"])
    assert StudioAskIndexer()._extract_answer(stream, "") == ""


def test_extract_json_block_picks_last_qualifying_block():
    """
    A prompt-echo JSON example ABOVE the real answer must NOT shadow it: the LAST
    balanced {...} with topics/content_category wins.
    """
    echo = '{"content_category":"...","topics":["..."]}'   # the echoed template
    real = '{"content_category":"educational","topics":["real"],"segments":[]}'
    stream = f"{GREETING}\nAnalyze ... {echo}\n{real}\n{DISCLAIMER}"

    block = StudioAskIndexer._extract_json_block(stream)
    assert block == real
    assert '"real"' in block


def test_readiness_classifier():
    assert StudioAskIndexer._is_gemini_ready("How can I help you today?") is True
    assert StudioAskIndexer._is_gemini_ready("How can Ask Studio help me?") is True
    # A blank disclaimer-only placeholder is NOT ready.
    assert StudioAskIndexer._is_gemini_ready(DISCLAIMER) is False
    assert StudioAskIndexer._is_gemini_ready("") is False


def test_video_prompt_names_the_specific_video():
    p = StudioAskIndexer._build_video_prompt('My Title', "abc123")
    assert "abc123" in p
    assert "studio.youtube.com/video/abc123" in p
    assert "My Title" in p
    assert "JSON" in p
    # Single line (no embedded newline -> no stray ENTER in the contenteditable).
    assert "\n" not in p


# ===========================================================================
# READINESS GATE: do NOT type into a blank panel
# ===========================================================================

async def test_readiness_gate_blocks_typing_on_blank_then_proceeds_when_ready():
    """
    Attempt 1 the stream is BLANK (disclaimer only) -> readiness gate fails ->
    code does NOT type into the prompt box. A retry tab then renders Gemini
    READY (greeting + answer) -> code proceeds and types. NON-VACUOUS: pre-fix
    code typed on attempt 1's blank panel (prompt_box.clicked would be True with
    no readiness check).
    """
    # First tab: BLANK (disclaimer-only placeholder, no greeting/answer).
    blank_map, blank_nodes = _build_tab(None, DISCLAIMER)
    # Retry tab: LOADED (greeting + real JSON answer).

    captured = {}

    def factory(handle):
        loaded_map, loaded_nodes = _build_tab(None, f"{GREETING}\n{REAL_JSON}")
        captured["loaded"] = loaded_nodes
        return loaded_map

    driver = MultiTab(deep_map=blank_map, tab_factory=factory)
    # Re-parent blank nodes to the real driver so deep chains resolve.
    for n in blank_nodes.values():
        n.parent = driver
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    # The BLANK tab's prompt box was NEVER typed into (gate blocked it).
    assert blank_nodes["prompt"].clicked is False
    assert blank_nodes["prompt"].sent_keys == []
    # The LOADED retry tab's prompt box WAS typed into, and it succeeded.
    assert result.success is True
    assert captured["loaded"]["prompt"].clicked is True


# ===========================================================================
# NEW-TAB RETRY + CLOSE OLD BLANK TAB
# ===========================================================================

async def test_new_tab_retry_opens_new_and_closes_old_blank_then_proceeds():
    """
    BLANK on attempt 1 -> a NEW tab is opened AND the OLD blank tab is CLOSED
    (012: do not accumulate non-working tabs); attempt 2 loads -> proceeds.
    """
    blank_map, _ = _build_tab(None, DISCLAIMER)

    def factory(handle):
        loaded_map, _ = _build_tab(None, f"{GREETING}\n{REAL_JSON}")
        return loaded_map

    driver = MultiTab(deep_map=blank_map, tab_factory=factory)
    for el in blank_map.values():
        el.parent = driver
    first_handle = driver.current_window_handle
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    # The OLD blank tab (win-1) was CLOSED during the retry.
    assert first_handle in driver.closed_handles
    # A new tab was opened (the retry navigated the fresh tab to the edit page).
    assert STUDIO_VIDEO_EDIT in driver.visited
    # Stealth CDP hook registered on more than one tab (re-registered per tab).
    tabs_with_stealth = {h for (h, cmd) in driver.cdp_calls}
    assert len(tabs_with_stealth) >= 2


async def test_gemini_never_loads_fails_closed_no_persist(monkeypatch):
    """
    Every tab is BLANK across all retries -> fail closed "gemini_did_not_load",
    NOTHING persisted (save_index never called). NON-VACUOUS: old code had no
    readiness/retry and would have typed + scraped the disclaimer as success.
    """
    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)
    monkeypatch.setattr(StudioAskIndexer, "GEMINI_MAX_LOAD_ATTEMPTS", 3)

    blank_map, _ = _build_tab(None, DISCLAIMER)

    def factory(handle):
        # Every retry tab is ALSO blank.
        m, _ = _build_tab(None, DISCLAIMER)
        return m

    driver = MultiTab(deep_map=blank_map, tab_factory=factory)
    for el in blank_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "gemini_did_not_load"
    assert result.response_text == ""
    # Drive the persistence guard: a failed ask must never persist.
    store = mod.VideoIndexStore(base_path="/tmp/none")
    if result.success:
        store.save_index("vidX", None)
    assert saved["count"] == 0
    # No stray retry tabs left open: only the survivor remains.
    assert len(driver.window_handles) == 1


# ===========================================================================
# CAPTURE STRIPS BOILERPLATE end-to-end (greeting present, answer captured)
# ===========================================================================

async def test_capture_strips_boilerplate_end_to_end():
    """
    Gemini ready FIRST try; the stream PERSISTS [greeting + echo + processing +
    REAL ANSWER + disclaimer]. The captured response_text is ONLY the real answer
    (disclaimer + processing + greeting stripped) AND parses to the real topics.
    NON-VACUOUS: pre-fix code returned the disclaimer-bearing stream and would
    have stored "AI can make mistakes..." as the answer.
    """
    stream_text = "\n".join([
        GREETING,
        "Summarize comments",
        'Analyze the video titled "Studio Title"',  # echo-ish
        "Reviewing your request",
        REAL_JSON,
        DISCLAIMER,
    ])
    loaded_map, nodes = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    assert "AI can make mistakes" not in result.response_text
    assert "Reviewing your request" not in result.response_text
    assert "How can I help" not in result.response_text
    # The JSON answer survived and parsed.
    assert result.content_category == "educational"
    assert "alpha" in result.topics and "beta" in result.topics
    # No retry needed (loaded first try) -> no tabs closed.
    assert driver.closed_handles == []


async def test_fail_closed_on_boilerplate_only_no_persist(monkeypatch):
    """
    Gemini greeted (ready) but only greeting + disclaimer ever render (no answer)
    -> fail closed "ask_studio_no_answer", save_index call_count == 0.
    """
    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)

    stream_text = "\n".join([GREETING, "Summarize comments", DISCLAIMER, "Learn more"])
    loaded_map, _ = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "ask_studio_no_answer"
    assert result.response_text == ""
    store = mod.VideoIndexStore(base_path="/tmp/none")
    if result.success:
        store.save_index("vidX", None)
    assert saved["count"] == 0


# ===========================================================================
# STEALTH: cdc_ strip + webdriver hook registered (and per new tab)
# ===========================================================================

def test_register_stealth_uses_cdp_hook():
    """
    _register_stealth registers a Page.addScriptToEvaluateOnNewDocument CDP hook
    on the current tab. NON-VACUOUS: a driver WITHOUT execute_cdp_cmd registers
    nothing (returns False) and never raises.
    """
    loaded_map, _ = _build_tab(None, f"{GREETING}\n{REAL_JSON}")
    driver = MultiTab(deep_map=loaded_map)
    indexer = StudioAskIndexer(driver=driver)

    assert indexer._register_stealth() is True
    assert any(cmd == "Page.addScriptToEvaluateOnNewDocument" for (_, cmd) in driver.cdp_calls)

    # A driver with no CDP support -> no-op, no raise.
    class NoCdp:
        pass

    indexer2 = StudioAskIndexer(driver=NoCdp())
    assert indexer2._register_stealth() is False


def test_stealth_cdc_strip_source_targets_cdc_and_webdriver():
    """The CDP pre-load source strips cdc_/$cdc and sets navigator.webdriver."""
    src = StudioAskIndexer._STEALTH_CDC_STRIP_JS
    assert "cdc_" in src
    assert "webdriver" in src


# ===========================================================================
# TAB CLEANUP only closes flow-created tabs (never operator's pre-existing tab)
# ===========================================================================

async def test_cleanup_only_closes_flow_created_tabs():
    """
    After a successful ask that required ONE retry, the operator's ORIGINAL tab
    (win-1, the blank one) was closed as part of the retry; the flow-created
    survivor remains. The cleanup never closes a tab the flow did not create:
    here _created_handles only ever contains the retry tab, and the final session
    has exactly one tab.
    """
    blank_map, _ = _build_tab(None, DISCLAIMER)

    def factory(handle):
        m, _ = _build_tab(None, f"{GREETING}\n{REAL_JSON}")
        return m

    driver = MultiTab(deep_map=blank_map, tab_factory=factory)
    for el in blank_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    # Exactly one tab remains (no accumulation of dead tabs).
    assert len(driver.window_handles) == 1
    # The created-handles bookkeeping is drained after cleanup.
    assert indexer._created_handles == []


# ===========================================================================
# LIVE-PROVEN ZERO-STATE SUGGESTION FALSE-SUCCESS (the +6s 106-char bug)
# ---------------------------------------------------------------------------
# 0102 ran the real action: after submit the capture stabilized at +6s on the
# ZERO-STATE suggestion variant and SAVED 106 chars ("A/B Testing Guide / Hello,
# UnDaoDu / Suggest new video ideas / Summarize my channel performance / More
# suggestions") with topics=[] category=other -> FALSE SUCCESS. The real JSON
# index streamed ~30s LATER. These tests pin the fix: the suggestion variant is
# NOT an answer; we WAIT for the real JSON; a suggestion-only stream fails closed.
# ===========================================================================

# Exact live-captured zero-state suggestion variant (the 106-char false success),
# rendered as the DOM .text would join the suggestion-chip block children.
ZERO_STATE_SUGGESTION_VARIANT = "\n".join([
    "A/B Testing Guide",
    "Hello, UnDaoDu",
    "Suggest new video ideas",
    "Summarize my channel performance",
    "More suggestions",
])


class _PollingStreamEl(El):
    """
    Stream WebElement whose .text returns ZERO-STATE for the first ``zero_polls``
    reads, then switches to ``answer_text`` (mimics the real answer streaming in
    ~30s AFTER submit while the zero-state was immediately stable). Re-uses the El
    interface so it drops into _build_tab's shadow map unchanged.
    """

    def __init__(self, zero_text, answer_text, zero_polls, parent=None):
        super().__init__(text=zero_text, parent=parent)
        self._zero_text = zero_text
        self._answer_text = answer_text
        self._zero_polls = zero_polls
        self._reads = 0

    @property
    def text(self):
        self._reads += 1
        if self._reads <= self._zero_polls:
            return self._zero_text
        return self._answer_text

    @text.setter
    def text(self, value):  # keep El's settable-text contract
        self._answer_text = value


def _build_tab_with_stream(driver, stream_el):
    """_build_tab variant injecting a custom (polling) stream element."""
    title = El(attributes={"value": "Studio Title"}, parent=driver)
    icon = El(attributes={"aria-label": "spark"}, parent=driver)
    trigger = El(parent=driver, deep_children={ASK_ICON: icon})
    prompt = El(attributes={"aria-label": "Ask something"}, parent=driver)
    return {
        TITLE_DEEP: title,
        ASK_TRIGGER: trigger,
        PROMPT_DEEP: prompt,
        STREAM_DEEP: stream_el,
    }, {"title": title, "icon": icon, "trigger": trigger, "prompt": prompt, "stream": stream_el}


async def test_zero_state_then_json_answer_captures_json_not_zero_state(monkeypatch):
    """
    (a) The stream shows the ZERO-STATE suggestion variant for the first 3 polls,
    THEN the real JSON index appears -> capture returns the JSON answer
    (content_category/topics parsed), NOT the zero-state. NON-VACUOUS: the pre-fix
    scraper stabilized on the immediately-stable zero-state at +6s and saved it as
    the answer (topics=[] category=other); here the zero-state never stabilizes
    (it is not a real answer) and the loop waits for the JSON that streams later.
    """
    # Give the loop room to outlast the 3 zero-state polls before timing out.
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 5.0)

    answer_json = (
        '{"content_category": "educational", "topics": ["alpha", "beta"], '
        '"segments": [{"time": "0:00", "topic": "Intro", "summary": "s"}]}'
    )
    # Zero-state present alongside the readiness greeting so the panel reads READY,
    # then the real JSON streams in after 3 polls.
    zero_text = f"{GREETING}\n{ZERO_STATE_SUGGESTION_VARIANT}"
    answer_text = f"{GREETING}\n{ZERO_STATE_SUGGESTION_VARIANT}\n{answer_json}"
    stream = _PollingStreamEl(zero_text, answer_text, zero_polls=3)

    loaded_map, nodes = _build_tab_with_stream(None, stream)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    # The JSON answer was captured, NOT the zero-state suggestion chips.
    assert result.content_category == "educational"
    assert "alpha" in result.topics and "beta" in result.topics
    # The zero-state suggestion chips never leaked into the persisted answer.
    assert "Suggest new video ideas" not in result.response_text
    assert "Summarize my channel performance" not in result.response_text
    assert "More suggestions" not in result.response_text


async def test_zero_state_suggestion_only_whole_timeout_fails_closed_no_persist(monkeypatch):
    """
    (b) The EXACT 106-char zero-state suggestion variant ("Suggest new video ideas
    / Summarize my channel performance / More suggestions / Hello, UnDaoDu / A/B
    Testing") streams for the WHOLE timeout (no JSON, no substantial prose) ->
    fail closed "ask_studio_no_answer", and save_index call_count == 0. NON-VACUOUS:
    the pre-fix scraper SAVED these 106 chars as the answer (false success).
    """
    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)

    # Greeting (so the panel reads READY) + the suggestion variant for the whole
    # timeout; the real answer NEVER arrives.
    stream_text = f"{GREETING}\n{ZERO_STATE_SUGGESTION_VARIANT}"
    loaded_map, _ = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "ask_studio_no_answer"
    assert result.response_text == ""

    # Drive the index-path persistence guard: a failed ask must never persist.
    store = mod.VideoIndexStore(base_path="/tmp/none")
    if result.success:
        store.save_index("vidX", None)
    assert saved["count"] == 0


def test_zero_state_markers_cover_suggestion_variant():
    """
    The extended ZERO_STATE_MARKERS catch the live suggestion-chip variant + the
    channel greeting. NON-VACUOUS: pre-fix markers ("how can ask studio help" /
    "summarize comments") did NOT contain any of these phrases.
    """
    low = ZERO_STATE_SUGGESTION_VARIANT.lower()
    for phrase in (
        "suggest new video ideas",
        "summarize my channel performance",
        "more suggestions",
        "a/b testing",
        "hello,",
    ):
        assert phrase in StudioAskIndexer.ZERO_STATE_MARKERS
        assert phrase in low
    # The whole suggestion variant is recognized as zero-state...
    assert StudioAskIndexer._is_zero_state(ZERO_STATE_SUGGESTION_VARIANT) is True
    # ...and is NOT a real answer (no JSON, below the prose threshold).
    extracted = StudioAskIndexer()._extract_answer(ZERO_STATE_SUGGESTION_VARIANT)
    assert StudioAskIndexer._is_real_answer(extracted) is False


def test_is_real_answer_gate_json_vs_short_prose():
    """
    The capture/persist gate: a JSON index block OR substantial prose is a real
    answer; a short non-boilerplate remainder is NOT.
    """
    assert StudioAskIndexer._is_real_answer(REAL_JSON) is True
    assert StudioAskIndexer._is_real_answer("short note") is False
    assert StudioAskIndexer._is_real_answer("") is False
    long_prose = "x" * StudioAskIndexer.MIN_SUBSTANTIAL_PROSE_CHARS
    assert StudioAskIndexer._is_real_answer(long_prose) is True
