# -*- coding: utf-8 -*-
"""
Tests for the shadow-DOM deep finder (find_deep / shadow_query / first_deep).

These are MOCK tests (NO live browser): a fake driver models a shadow tree where
the element lives UNDER a shadow root, so flat ``find_element`` raises but the
deep walk (modeled by ``execute_script``) returns it. They prove:
  - find_deep returns a REAL element (the mock WebElement) via the shadow path
    when flat find_element fails (flat-fails / shadow-finds);
  - find_deep falls back to flat find_element when the shadow walk yields nothing
    (so light-DOM pages + existing mock drivers keep resolving);
  - shadow_query resolves a CHAIN across shadow boundaries;
  - first_deep returns the first resolving entry.

WSP 5/6 coverage; WSP 72 module independence (no cross-module fixtures).
"""

from modules.infrastructure.foundups_selenium.src.shadow_dom_finder import (
    find_deep,
    shadow_query,
    first_deep,
)


class FakeElement:
    """Minimal WebElement stand-in that records click/keystrokes (so we can
    prove the returned object behaves like a real element for human_type/click).
    """

    def __init__(self, name="", parent=None):
        self.name = name
        self.parent = parent
        self.clicked = False
        self.sent_keys = []

    def click(self):
        self.clicked = True

    def send_keys(self, value):
        self.sent_keys.append(value)


class ShadowDriver:
    """
    Fake driver that models a SHADOW tree as ``deep_map`` (selector -> element
    reachable only via the shadow walk) and a separate FLAT map for
    ``find_element`` (light-DOM only). ``execute_script`` running the deep-walk JS
    consults ``deep_map``; the flat ``find_element`` consults ``flat_map`` and
    raises for anything absent (mimicking NoSuchElement / a non-piercing find).
    """

    def __init__(self, deep_map=None, flat_map=None):
        self.deep_map = deep_map or {}
        self.flat_map = flat_map or {}

    def execute_script(self, script, root, css):
        # Only the shadow-walk script resolves deep elements. A chain step passes
        # the prior element as ``root``; honor a sub-scope by checking the
        # element-scoped map when root is an element, else the driver-level map.
        if root is not None:
            children = getattr(root, "deep_children", None)
            return (children or {}).get(css)
        return self.deep_map.get(css)

    def find_element(self, by, selector):
        el = self.flat_map.get(selector)
        if el is None:
            raise Exception(f"NoSuchElement: {selector}")
        return el


def test_find_deep_returns_element_when_flat_fails():
    """Element exists only under a shadow root -> flat find_element raises, but
    find_deep returns the real element via the shadow walk."""
    title = FakeElement("title")
    driver = ShadowDriver(
        deep_map={"ytcp-social-suggestions-textbox#title-textarea": title},
        flat_map={},  # flat finds NOTHING
    )

    # Sanity: the flat path genuinely fails.
    flat_failed = False
    try:
        driver.find_element("css selector", "ytcp-social-suggestions-textbox#title-textarea")
    except Exception:
        flat_failed = True
    assert flat_failed is True

    found = find_deep(driver, "ytcp-social-suggestions-textbox#title-textarea")
    assert found is title
    # The returned object behaves like a real element (click/send_keys work).
    found.click()
    found.send_keys("x")
    assert found.clicked is True
    assert found.sent_keys == ["x"]


def test_find_deep_falls_back_to_flat_when_no_shadow_match():
    """If the shadow walk yields nothing, find_deep falls back to flat
    find_element (so light-DOM pages and existing mocks still resolve)."""
    flat_el = FakeElement("flat")
    driver = ShadowDriver(deep_map={}, flat_map={"div#light": flat_el})

    found = find_deep(driver, "div#light")
    assert found is flat_el


def test_find_deep_none_when_absent_everywhere():
    driver = ShadowDriver(deep_map={}, flat_map={})
    assert find_deep(driver, "div#missing") is None


def test_shadow_query_resolves_chain_across_shadow_boundaries():
    """A chain like creator-chat-trigger -> icon-button resolves the trigger
    deep, then the icon-button deep WITHIN the trigger's subtree."""
    icon_button = FakeElement("icon-button")
    driver = ShadowDriver()
    # Real Selenium WebElement.parent IS the driver; the finder uses that to run
    # the scoped shadow walk within the prior match's subtree.
    trigger = FakeElement("trigger", parent=driver)
    # The icon button is reachable only WITHIN the trigger's subtree.
    trigger.deep_children = {"ytcp-icon-button": icon_button}
    driver.deep_map = {"ytcp-creator-chat-trigger": trigger}

    found = shadow_query(driver, ["ytcp-creator-chat-trigger", "ytcp-icon-button"])
    assert found is icon_button


def test_shadow_query_chain_fails_when_step_missing():
    driver = ShadowDriver()
    trigger = FakeElement("trigger", parent=driver)
    trigger.deep_children = {}  # icon-button NOT under the trigger
    driver.deep_map = {"ytcp-creator-chat-trigger": trigger}

    found = shadow_query(driver, ["ytcp-creator-chat-trigger", "ytcp-icon-button"])
    assert found is None


def test_first_deep_returns_first_resolving_entry():
    second = FakeElement("second")
    driver = ShadowDriver(deep_map={"b": second})
    # 'a' (string) misses, ['b'] (chain) hits.
    found = first_deep(driver, ["a", ["b"]])
    assert found is second


def test_first_deep_none_when_all_miss():
    driver = ShadowDriver(deep_map={}, flat_map={})
    assert first_deep(driver, ["a", ["b", "c"]]) is None
