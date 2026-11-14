# -*- coding: utf-8 -*-
"""
Shadow-DOM deep finder (returns REAL Selenium WebElements).

Flat Selenium ``find_element("css selector", ...)`` does NOT pierce shadow
roots. YouTube Studio's DOM is shadow-rooted, so flat selectors silently fail
on the live page even when the element exists (e.g. the flat ``input#title-field``
returns nothing while a shadow walk finds ``ytcp-social-suggestions-textbox#title-textarea``).

WSP 84 REUSE: the recursive ``findInShadow`` traversal here is the SAME proven
algorithm already used by the YT comment-reply path
(modules/communication/video_comments/skillz/tars_like_heart_reply/src/reply_executor.py
findInShadow). The difference is purely the return contract: reply_executor
self-clicks inside the JS and returns text/booleans, whereas this helper has
``execute_script`` *return the matched DOM node*, so Selenium hands Python back a
REAL WebElement. That keeps ``HumanBehavior.human_type`` + ``element.click()``
working (the #825 input behavior + #827 fail-closed paths rely on real elements).

Public surface:
    find_deep(driver_or_root, css)        -> WebElement | None
    shadow_query(driver, selector_chain)  -> WebElement | None
    first_deep(driver, selectors)         -> WebElement | None

``selector_chain`` is a list of CSS steps resolved across shadow boundaries
(each step is find_deep'd within the prior match's subtree), e.g.
``["ytcp-creator-chat-trigger", "ytcp-icon-button"]``.

WSP References: WSP 3 (infrastructure), WSP 11 (public API), WSP 84 (reuse).
"""

import logging
from typing import List, Optional, Sequence, Union

logger = logging.getLogger(__name__)

# Recursive shadow-DOM walk. Returns the FIRST element matching ``selector``
# anywhere across nested shadow roots, starting from ``root`` (a DOM node or a
# ShadowRoot). Mirrors reply_executor.findInShadow but RETURNS THE NODE so the
# caller (Selenium execute_script) receives a real WebElement.
#
# arguments[0] = root node (or null -> document)
# arguments[1] = css selector
_FIND_DEEP_JS = r"""
const selector = arguments[1];
function findInShadow(root, sel) {
    if (!root) return null;
    // Direct (light-DOM) match within this root.
    try {
        const direct = root.querySelector(sel);
        if (direct) return direct;
    } catch (e) { /* invalid selector for this root -> keep walking */ }
    // Descend into every shadow root reachable from this root.
    let descendants;
    try {
        descendants = root.querySelectorAll('*');
    } catch (e) {
        return null;
    }
    for (const child of descendants) {
        if (child.shadowRoot) {
            const found = findInShadow(child.shadowRoot, sel);
            if (found) return found;
        }
    }
    return null;
}
const start = arguments[0] || document;
return findInShadow(start, selector);
"""


def _resolve_driver(driver_or_root):
    """
    Return the object exposing ``execute_script`` (the WebDriver). ``find_deep``
    accepts either a driver or a previously-found WebElement (whose subtree we
    walk). A WebElement exposes ``parent`` (its driver) in real Selenium; we use
    that to run the script, passing the element as the JS root.
    """
    if hasattr(driver_or_root, "execute_script"):
        return driver_or_root, None
    parent = getattr(driver_or_root, "parent", None)
    if parent is not None and hasattr(parent, "execute_script"):
        return parent, driver_or_root
    return None, None


def find_deep(driver_or_root, css: str):
    """
    Find the FIRST element matching ``css`` anywhere across shadow roots and
    return a REAL WebElement (or None).

    PRIMARY path: a single ``execute_script`` that recursively walks
    element.shadowRoot + children and RETURNS the matched node (Selenium wraps
    it as a WebElement). FALLBACK (cheap, documented): if the shadow walk yields
    nothing or errors, try a flat ``find_element`` on the driver so light-DOM
    pages (and existing mock drivers) still resolve. The flat path is a fallback
    ONLY; the primary mechanism is shadow traversal.

    Args:
        driver_or_root: a Selenium WebDriver, OR a WebElement whose subtree
            (including its shadow roots) should be searched.
        css: a CSS selector string.

    Returns:
        WebElement | None
    """
    if not css:
        return None
    driver, root_el = _resolve_driver(driver_or_root)
    if driver is None:
        return None

    # PRIMARY: shadow-piercing walk returning the real node.
    try:
        el = driver.execute_script(_FIND_DEEP_JS, root_el, css)
        if el:
            return el
    except Exception as e:  # pragma: no cover - defensive (driver/JS hiccup)
        logger.debug(f"[SHADOW-FIND] deep walk failed for {css!r}: {e}")

    # FALLBACK: flat light-DOM find (only meaningful when searching from the
    # driver root; a flat find from an element root is not generally available).
    if root_el is None:
        try:
            flat = driver.find_element("css selector", css)
            if flat:
                return flat
        except Exception:
            pass
    return None


def shadow_query(driver, selector_chain: Union[str, Sequence[str]]):
    """
    Resolve a CHAIN of CSS selectors across shadow boundaries.

    Each step is find_deep'd within the prior match's subtree, so e.g.
    ``["ytcp-creator-chat-trigger", "ytcp-icon-button"]`` finds the chat trigger
    deep, then the icon-button deep WITHIN that trigger's shadow subtree.

    A plain string is treated as a single-step chain.

    Returns the final WebElement (or None if any step fails).
    """
    if isinstance(selector_chain, str):
        steps: List[str] = [selector_chain]
    else:
        steps = [s for s in selector_chain if s]
    if not steps:
        return None

    current = driver
    for step in steps:
        match = find_deep(current, step)
        if match is None:
            return None
        current = match
    # ``current`` is the WebElement from the last step (driver only when there
    # were zero steps, already guarded above).
    return current


def first_deep(driver, selectors: Sequence[Union[str, Sequence[str]]]):
    """
    Try a list of selectors/chains in order; return the first that resolves to a
    real WebElement, else None. Each entry is either a CSS string (single step)
    or a list/tuple (a cross-shadow chain for ``shadow_query``).
    """
    for entry in selectors or []:
        try:
            el = shadow_query(driver, entry)
            if el is not None:
                return el
        except Exception:
            continue
    return None
