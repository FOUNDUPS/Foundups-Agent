"""Manual Chrome/Gemini YouTube heart probe; never automated test evidence.

Importing this module performs no browser, model, or platform action. Running
the program explicitly retains the historical live heart-click behavior; that
workflow has not been validated by the import-safety regression.
"""

WRE_TEST_MODE = "manual"

PROMPT = 'TASK: Find the CREATOR HEART button (NOT like button) on YouTube Studio.\n\nCRITICAL DISTINCTIONS:\n- LIKE button: Thumbs up icon - position 3 from left - IGNORE THIS\n- HEART button: Outlined heart icon - position 5 from left - TARGET THIS\n\nThe heart is between thumbs down and three-dot menu in comment action bar.\n\nReturn JSON:\n{\n  "found": true/false,\n  "confidence": "High/Medium/Low",\n  "element_description": "describe heart button only",\n  "selector": "CSS selector or XPath for HEART button"\n}\n'


def _analyze_heart(browser):
    import io
    import json
    from PIL import Image

    print("[4] Gemini analyzing page for heart button...")
    screenshot = browser.get_screenshot_as_png()
    img = Image.open(io.BytesIO(screenshot))
    result = browser.vision_analyzer.model.generate_content([PROMPT, img]).text
    print(f"[GEMINI RESPONSE]:\n{result}")
    if "```json" in result:
        result = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
        result = result.split("```")[1].split("```")[0].strip()
    result_data = json.loads(result)
    print(f"[5] Gemini Result: {result_data}")
    if not result_data.get('found', False):
        raise RuntimeError("Gemini did not find heart button")
    return result_data


def _find_heart(browser, selector):
    from selenium.webdriver.common.by import By

    elements = []
    try:
        if selector.startswith('//'):
            elements = browser.find_elements(By.XPATH, selector)
        elif selector:
            elements = browser.find_elements(By.CSS_SELECTOR, selector)
    except Exception as exc:
        print(f"[WARN] Gemini selector failed: {exc}")
    if not elements and 'aria-label="Give appreciation"' in selector:
        print("[INFO] Trying simpler aria-label selector...")
        try:
            elements = browser.find_elements(
                By.CSS_SELECTOR, 'button[aria-label="Give appreciation"]')
        except Exception as exc:
            print(f"[WARN] Aria-label selector failed: {exc}")
    if not elements:
        print("[INFO] Trying yt-icon-button search...")
        try:
            for button in browser.find_elements(By.TAG_NAME, 'yt-icon-button'):
                aria = (button.get_attribute('aria-label') or '').lower()
                if 'appreciation' in aria or 'heart' in aria:
                    elements = [button]
                    break
        except Exception as exc:
            print(f"[WARN] Icon button search failed: {exc}")
    if not elements:
        raise RuntimeError(f"All selector strategies failed: {selector}")
    return elements[0]


def _click_heart(browser, element):
    import time

    print(f"[OK] Element located: <{element.tag_name}>")
    browser.execute_script("""
        arguments[0].style.border = '3px solid red';
        arguments[0].style.backgroundColor = 'rgba(255,0,0,0.2)';
    """, element)
    print("[7] Element highlighted with RED border (2 seconds)")
    time.sleep(2)
    browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(1)
    element.click()
    print("[SUCCESS] Heart click executed; check browser for filled heart")
    time.sleep(5)
    print("[OK] Probe complete - browser staying open for 30 seconds...")
    time.sleep(30)


def main():
    import sys
    import time
    import traceback
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root))
    from modules.infrastructure.foundups_selenium.src.browser_manager import get_browser_manager

    print("MANUAL GEMINI VISION - YouTube Studio Heart Click")
    browser = None
    try:
        print("[1] Launching FoundUps browser with Gemini Vision...")
        browser = get_browser_manager().get_browser(
            browser_type='chrome', profile_name='youtube_move2japan')
        print("[2] Navigating to YouTube Studio...")
        browser.get('https://studio.youtube.com/channel/UC-LSSlOZwpGIRIYihaz8zCw/comments/inbox')
        time.sleep(8)
        print("[3] Verifying Gemini Vision...")
        if not getattr(browser, 'vision_analyzer', None):
            raise RuntimeError("vision_analyzer not available")
        result = _analyze_heart(browser)
        _click_heart(browser, _find_heart(browser, result.get('selector', '')))
        return 0
    except Exception as exc:
        print(f"[ERROR] Manual probe failed: {exc}")
        traceback.print_exc()
        return 1
    finally:
        if browser is not None:
            print("Closing browser...")
            browser.quit()


if __name__ == '__main__':
    raise SystemExit(main())
