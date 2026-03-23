#!/usr/bin/env python3
"""
LinkedIn Company Poster Skill

Posts updates and articles to FoundUps LinkedIn company page.
Signature: 0102🦞

Usage:
    # Post update
    python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --post "Your content here"

    # Write article
    python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --article "Title" --body "Article body"

    # Test article modal
    python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --test-article
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Import from central LinkedIn account registry
import os
from modules.infrastructure.shared_utilities.linkedin_account_registry import (
    get_accounts as _load_linkedin_accounts,
    get_company_id,
    get_article_url as _get_article_url_base,
    get_admin_url,
    get_default_company as _get_default_company_id,
    ACCOUNT_ALIASES,
)

# Constants
COMPANY_ID = _get_default_company_id()
COMPANY_URL = get_admin_url()
ARTICLE_URL = _get_article_url_base()
SIGNATURE = "0102🦞"
DEFAULT_HASHTAGS = "#FoundUps #pAVS #0102"


def get_article_url(author: str = None) -> str:
    """
    Get article URL for specific author.
    Uses central LinkedIn account registry with fuzzy matching.

    Args:
        author: Author name or alias (default: from LINKEDIN_DEFAULT_COMPANY env)

    Returns:
        Direct article URL for that account
    """
    return _get_article_url_base(author)


def list_accounts() -> dict:
    """List all available LinkedIn accounts from env."""
    return _load_linkedin_accounts()


def get_browser():
    """Get or create LinkedIn browser session (Chrome debug port 9222)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    # Primary: Connect to existing Chrome debug session (port 9222)
    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=options)
        logger.info("[BROWSER] Connected to Chrome debug port 9222")
        return driver
    except Exception as e:
        logger.warning(f"[BROWSER] Chrome debug connection failed: {e}")

    # Fallback: Use BrowserManager with Chrome
    try:
        from modules.infrastructure.foundups_selenium.src.browser_manager import get_browser_manager
        manager = get_browser_manager()
        browser = manager.get_browser("chrome", f"linkedin_{COMPANY_ID}")
        return browser
    except Exception as e2:
        logger.error(f"[BROWSER] All connection methods failed: {e2}")
        raise RuntimeError("Cannot connect to Chrome browser for LinkedIn")


def format_post(content: str, signature: str = SIGNATURE) -> str:
    """Format post with signature and hashtags."""
    return f"{content}\n\n{signature} {DEFAULT_HASHTAGS}"


def post_update(content: str, signature: str = SIGNATURE) -> Tuple[bool, str]:
    """
    Post an update to the FoundUps LinkedIn company page.

    Args:
        content: The post content
        signature: Signature to append (default: 0102🦞)

    Returns:
        Tuple of (success, message)
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains

    formatted_content = format_post(content, signature)
    logger.info(f"[LINKEDIN] Posting update ({len(formatted_content)} chars)")

    try:
        driver = get_browser()

        # Navigate to company page with share param
        share_url = f"{COMPANY_URL}?share=true"
        driver.get(share_url)
        time.sleep(3)

        # Find text editor
        wait = WebDriverWait(driver, 10)
        text_area = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, "div.ql-editor"
        )))

        # Clear and type content
        text_area.click()
        time.sleep(0.5)

        # Use JavaScript to insert content (more reliable)
        driver.execute_script(
            "arguments[0].innerHTML = arguments[1]",
            text_area,
            formatted_content.replace('\n', '<br>')
        )
        time.sleep(1)

        # Find and click Post button
        post_selectors = [
            "//button[contains(@class, 'share-actions__primary-action') and not(contains(@aria-label, 'Schedule'))]",
            "//button[text()='Post']",
            "//button[contains(@class, 'artdeco-button--primary')]"
        ]

        post_button = None
        for selector in post_selectors:
            try:
                post_button = driver.find_element(By.XPATH, selector)
                if post_button.is_enabled():
                    break
            except:
                continue

        if not post_button:
            return False, "Could not find Post button"

        # Click with ActionChains for reliability
        ActionChains(driver).move_to_element(post_button).click().perform()
        time.sleep(3)

        # Verify redirect (success indicator)
        if "share=true" not in driver.current_url:
            logger.info("[SUCCESS] Post published!")
            return True, "Post published successfully"
        else:
            return False, "Post may not have been published (no redirect)"

    except Exception as e:
        logger.error(f"[ERROR] Post failed: {e}")
        return False, str(e)


def open_article_editor() -> Tuple[bool, str]:
    """
    Open the LinkedIn article editor using direct URL.

    Returns:
        Tuple of (success, message)
    """
    logger.info("[LINKEDIN] Opening article editor via direct URL...")

    try:
        driver = get_browser()

        # Use direct article URL (012 provided this)
        driver.get(ARTICLE_URL)
        time.sleep(3)

        # Verify we're in article editor
        current_url = driver.current_url
        logger.info(f"[NAV] Current URL: {current_url}")

        if "article" in current_url.lower():
            logger.info("[SUCCESS] Article editor opened!")
            return True, f"Article editor opened: {current_url}"
        else:
            # Take screenshot for debugging
            screenshot_path = REPO_ROOT / "linkedin_article_debug.png"
            driver.save_screenshot(str(screenshot_path))
            logger.info(f"[DEBUG] Screenshot saved: {screenshot_path}")
            return False, f"Unexpected page: {current_url}"

    except Exception as e:
        logger.error(f"[ERROR] Failed to open article editor: {e}")
        return False, str(e)


def upload_image(image_path: str) -> Tuple[bool, str]:
    """
    Upload an image to the article editor.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (success, message)
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import os

    if not os.path.exists(image_path):
        return False, f"Image not found: {image_path}"

    logger.info(f"[LINKEDIN] Uploading image: {image_path}")

    try:
        driver = get_browser()
        wait = WebDriverWait(driver, 10)

        # Find upload button - "Upload from computer"
        upload_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[contains(@class, 'artdeco-button__text') and contains(text(), 'Upload from computer')]"
        )))
        upload_btn.click()
        time.sleep(1)

        # Find file input and send path
        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(os.path.abspath(image_path))
        time.sleep(3)  # Wait for upload

        logger.info("[SUCCESS] Image uploaded")
        return True, "Image uploaded successfully"

    except Exception as e:
        logger.error(f"[ERROR] Image upload failed: {e}")
        return False, str(e)


def test_formatting() -> Tuple[bool, str]:
    """
    Test formatting capabilities in article editor.
    LinkedIn uses keyboard shortcuts: Ctrl+B (bold), Ctrl+I (italic)

    Returns:
        Tuple of (success, message)
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    logger.info("[LINKEDIN] Testing article formatting...")

    try:
        driver = get_browser()
        driver.get(ARTICLE_URL)
        time.sleep(4)

        wait = WebDriverWait(driver, 15)

        # Find body field using 012's exact selector
        body_field = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, "p.article-editor-paragraph"
        )))
        body_field.click()
        time.sleep(0.5)

        actions = ActionChains(driver)

        # Type test content with formatting (use JS for emoji compatibility)
        test_intro = "Formatting Test by 0102\n\nTesting **bold** with Ctrl+B:"
        # Use JavaScript to insert text (handles all Unicode including emojis)
        driver.execute_script(
            "arguments[0].innerText = arguments[1]",
            body_field,
            test_intro
        )
        time.sleep(0.3)

        # Select "BOLD" and apply bold
        body_field.send_keys(" BOLD")
        # Select the word
        actions.key_down(Keys.SHIFT).send_keys(Keys.LEFT * 4).key_up(Keys.SHIFT).perform()
        time.sleep(0.2)
        # Ctrl+B for bold
        actions.key_down(Keys.CONTROL).send_keys('b').key_up(Keys.CONTROL).perform()
        time.sleep(0.3)

        # Move to end and continue
        actions.send_keys(Keys.END).perform()
        body_field.send_keys("\n\nTesting *italic* with Ctrl+I: ITALIC")
        # Select and italicize
        actions.key_down(Keys.SHIFT).send_keys(Keys.LEFT * 6).key_up(Keys.SHIFT).perform()
        actions.key_down(Keys.CONTROL).send_keys('i').key_up(Keys.CONTROL).perform()
        time.sleep(0.3)

        # Test @mention
        actions.send_keys(Keys.END).perform()
        body_field.send_keys("\n\nTesting @mention: @FoundUps")
        time.sleep(1)  # Wait for mention dropdown

        # Screenshot
        screenshot_path = REPO_ROOT / "linkedin_formatting_test.png"
        driver.save_screenshot(str(screenshot_path))
        logger.info(f"[SCREENSHOT] {screenshot_path}")

        return True, f"Formatting test complete. Screenshot: {screenshot_path}"

    except Exception as e:
        logger.error(f"[ERROR] Formatting test failed: {e}")
        return False, str(e)


def _switch_author_internal(driver, author_name: str) -> Tuple[bool, str]:
    """
    Internal: Switch author using dropdown (assumes article editor is open).
    Uses persistent mouse hover to keep dropdown open.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains

    wait = WebDriverWait(driver, 10)
    actions = ActionChains(driver)

    # Find the author toggle button
    author_toggle = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, "div.article-editor-actor-toggle__author-lockup-content"
    )))
    current_author = author_toggle.text
    logger.info(f"[CURRENT] Author: {current_author}")

    if author_name.upper() in current_author.upper():
        return True, f"Already posting as {current_author}"

    # Click to open dropdown with persistent hover
    actions.move_to_element(author_toggle).click().perform()
    time.sleep(0.8)

    # Find dropdown items
    dropdown_selectors = [
        "ul[role='listbox'] li",
        "div[role='listbox'] div[role='option']",
        "div.artdeco-dropdown__content li",
        "button[role='menuitemradio']",
    ]

    options = []
    for selector in dropdown_selectors:
        options = driver.find_elements(By.CSS_SELECTOR, selector)
        if options:
            logger.info(f"[FOUND] {len(options)} options via: {selector}")
            break

    if not options:
        screenshot_path = REPO_ROOT / "linkedin_author_dropdown_debug.png"
        driver.save_screenshot(str(screenshot_path))
        return False, f"No dropdown options found. Screenshot: {screenshot_path}"

    # Navigate through options with persistent mouse
    for opt in options:
        try:
            actions.move_to_element(opt).perform()
            time.sleep(0.2)
            opt_text = opt.text.strip() or opt.get_attribute("aria-label") or ""
            if author_name.upper() in opt_text.upper():
                actions.click().perform()
                time.sleep(0.5)
                logger.info(f"[SWITCHED] Author: {opt_text}")
                return True, f"Switched to {opt_text}"
        except Exception as e:
            logger.debug(f"Option error: {e}")
            continue

    # ESC to close dropdown
    from selenium.webdriver.common.keys import Keys
    actions.send_keys(Keys.ESCAPE).perform()
    return False, f"Author '{author_name}' not found in dropdown"


def write_article(
    title: str,
    body: str,
    signature: str = SIGNATURE,
    image_path: str = None,
    author: str = None
) -> Tuple[bool, str]:
    """
    Write an article to LinkedIn. Uses direct URL for author - no dropdown needed.

    Args:
        title: Article title
        body: Article body (supports @mentions, Ctrl+B bold, Ctrl+I italic)
        signature: Signature to append
        image_path: Optional path to header image
        author: Author name (loads company ID from LINKEDIN_ACCOUNTS_JSON env)

    Returns:
        Tuple of (success, message)

    Example:
        write_article("My Title", "Content...", author="undaodu")
        write_article("Another", "More content", author="move2japan")
        write_article("FOUNDUPS post", "Content...")  # uses default
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys

    logger.info(f"[LINKEDIN] Writing article: {title}" + (f" as {author}" if author else ""))

    try:
        driver = get_browser()

        # Navigate directly to author's article editor (uses company ID from env)
        article_url = get_article_url(author)
        logger.info(f"[URL] {article_url}")
        driver.get(article_url)
        time.sleep(4)

        wait = WebDriverWait(driver, 15)

        # Find title field - 012's exact selector
        title_selectors = [
            "div.article-editor-headline",  # 012's selector
            "h1[data-placeholder]",
            "h1[contenteditable='true']",
            "[data-placeholder='Title']",
        ]

        title_field = None
        for selector in title_selectors:
            try:
                title_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger.info(f"[FOUND] Title field: {selector}")
                break
            except:
                continue

        if title_field:
            title_field.click()
            time.sleep(0.3)
            title_field.send_keys(title)
            logger.info(f"[TYPED] Title: {title}")
            time.sleep(0.5)

        # Find body field - 012's exact selector
        body_selectors = [
            "p.article-editor-paragraph",  # 012's selector
            "p.article-editor-paragraph.is-empty",
            ".ProseMirror",
            "[data-placeholder*='Write here']",
        ]

        body_field = None
        for selector in body_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed() and el != title_field:
                        body_field = el
                        logger.info(f"[FOUND] Body field: {selector}")
                        break
                if body_field:
                    break
            except:
                continue

        if body_field:
            body_field.click()
            time.sleep(0.3)
            formatted_body = f"{body}\n\n---\n{signature} {DEFAULT_HASHTAGS}"
            # Type content
            body_field.send_keys(formatted_body)
            logger.info(f"[TYPED] Body: {len(body)} chars")
            time.sleep(1)

        # Upload image if provided
        if image_path:
            success, msg = upload_image(image_path)
            if success:
                logger.info(f"[IMAGE] {msg}")
            else:
                logger.warning(f"[IMAGE] {msg}")

        # Take screenshot
        screenshot_path = REPO_ROOT / "linkedin_article_ready.png"
        driver.save_screenshot(str(screenshot_path))
        logger.info(f"[SCREENSHOT] {screenshot_path}")

        author_info = f" as {author}" if author else ""
        logger.info(f"[SUCCESS] Article content entered{author_info}. Review and click Publish.")
        return True, f"Article ready{author_info} - review and publish. Screenshot: {screenshot_path}"

    except Exception as e:
        logger.error(f"[ERROR] Article write failed: {e}")
        return False, str(e)


def switch_author(author_name: str = "FOUNDUPS") -> Tuple[bool, str]:
    """
    Switch the article author using the account dropdown.
    Opens article editor if not already there, then switches via dropdown.

    Args:
        author_name: Name to match in dropdown (default: "FOUNDUPS")

    Returns:
        Tuple of (success, message)

    Available authors (from 012's screenshot):
        - UnDaoDu Michael J Trout
        - AutonomousWall
        - eSingularity
        - LN Republican Voters Against Trump
        - AI Harmonic HapticSign
        - The Foundups 100x100 2020 Initiative
        - BitCloutFork
        - FOUNDUPS®
        - Decentralized Crypto Fund
        - Move2Japan
    """
    logger.info(f"[LINKEDIN] Switching author to: {author_name}")

    try:
        driver = get_browser()

        # Make sure we're on article page
        if "article" not in driver.current_url.lower():
            driver.get(ARTICLE_URL)
            time.sleep(3)

        # Use internal helper
        return _switch_author_internal(driver, author_name)

    except Exception as e:
        logger.error(f"[ERROR] Author switch failed: {e}")
        return False, str(e)


def test_author_list() -> Tuple[bool, str]:
    """
    Test navigating the author dropdown list.
    Opens dropdown and moves through each option with persistent hover.
    Uses position-based navigation for fragile dropdowns.

    Returns:
        Tuple of (success, list of authors found)
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains

    logger.info("[LINKEDIN] Testing author dropdown navigation...")

    # Known accounts from 012's screenshot (in order)
    KNOWN_ACCOUNTS = [
        "UnDaoDu Michael J Trout",
        "AutonomousWall",
        "eSingularity",
        "LN Republican Voters Against Trump",
        "AI Harmonic HapticSign",
        "The Foundups 100x100 2020 Initiative",
        "BitCloutFork",
        "FOUNDUPS®",
        "Decentralized Crypto Fund",
        "Move2Japan",
    ]

    try:
        driver = get_browser()

        # Make sure we're on article page
        if "article" not in driver.current_url.lower():
            driver.get(ARTICLE_URL)
            time.sleep(3)

        wait = WebDriverWait(driver, 10)
        actions = ActionChains(driver)

        # Find and click the author toggle
        author_toggle = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, "div.article-editor-actor-toggle__author-lockup-content"
        )))
        toggle_rect = author_toggle.rect
        logger.info(f"[TOGGLE] x={toggle_rect['x']}, y={toggle_rect['y']}, w={toggle_rect['width']}, h={toggle_rect['height']}")
        logger.info(f"[CURRENT] {author_toggle.text}")

        # Click with persistent hover
        actions.move_to_element(author_toggle).click().perform()
        time.sleep(0.8)

        # Screenshot the dropdown
        screenshot_path = REPO_ROOT / "linkedin_author_dropdown.png"
        driver.save_screenshot(str(screenshot_path))
        logger.info(f"[SCREENSHOT] {screenshot_path}")

        # Try to find dropdown items
        authors_found = []
        dropdown_selectors = [
            "ul[role='listbox'] li",
            "div[role='listbox'] div[role='option']",
            "div.artdeco-dropdown__content li",
            "button[role='menuitemradio']",
            "div.entity-result__item",
        ]

        dropdown_items = []
        for selector in dropdown_selectors:
            dropdown_items = driver.find_elements(By.CSS_SELECTOR, selector)
            if dropdown_items:
                logger.info(f"[FOUND] {len(dropdown_items)} items via: {selector}")
                break

        if dropdown_items:
            # Navigate through items with persistent mouse
            for i, item in enumerate(dropdown_items):
                try:
                    # Move to item (keeps dropdown open)
                    actions.move_to_element(item).perform()
                    time.sleep(0.3)

                    item_text = item.text.strip() or item.get_attribute("aria-label") or f"Item_{i}"
                    authors_found.append(item_text)
                    logger.info(f"[{i}] {item_text}")

                    # Take screenshot at each position
                    if i < 3:  # First 3 for debugging
                        ss_path = REPO_ROOT / f"linkedin_author_{i}.png"
                        driver.save_screenshot(str(ss_path))
                except Exception as e:
                    logger.warning(f"[{i}] Error: {e}")
        else:
            # Fallback: position-based navigation
            # Each item is ~64px tall, dropdown visible at toggle position
            logger.info("[FALLBACK] Using position-based navigation (64px per item)")

            # Start from toggle position and move down
            start_x = toggle_rect['x'] + toggle_rect['width'] // 2
            start_y = toggle_rect['y'] + toggle_rect['height'] + 30  # Below toggle

            for i, account in enumerate(KNOWN_ACCOUNTS):
                y_offset = start_y + (i * 64)
                try:
                    actions.move_by_offset(0, 64 if i > 0 else 0).perform()
                    time.sleep(0.2)
                    authors_found.append(f"[POS {i}] {account} (estimated)")
                    logger.info(f"[{i}] y={y_offset}: {account}")
                except:
                    break

        # Click away to close dropdown
        actions.send_keys('\x1b').perform()  # ESC key
        time.sleep(0.3)

        if authors_found:
            return True, f"Found {len(authors_found)} authors: {authors_found[:5]}..."
        else:
            return False, f"No authors found - check screenshot: {screenshot_path}"

    except Exception as e:
        logger.error(f"[ERROR] Author list test failed: {e}")
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Company Poster - Post to FoundUps page (0102🦞)",
        epilog="""
Examples:
  # Article as FOUNDUPS (default from LINKEDIN_DEFAULT_COMPANY env)
  python -m ... --article "Title" --body "Content"

  # Article as different author (direct URL from LINKEDIN_ACCOUNTS_JSON env)
  python -m ... --article "Title" --body "Content" --author "undaodu"
  python -m ... --article "Title" --body "Content" --author "move2japan"

  # List available accounts from env
  python -m ... --list-accounts

Env vars:
  LINKEDIN_DEFAULT_COMPANY=foundups
  LINKEDIN_ACCOUNTS_JSON={"foundups":"1263645","undaodu":"68706058",...}
"""
    )
    parser.add_argument("--post", "-p", type=str, help="Post an update")
    parser.add_argument("--article", "-a", type=str, help="Article title")
    parser.add_argument("--body", "-b", type=str, help="Article body")
    parser.add_argument("--author", type=str, help="Author to post as (from LINKEDIN_ACCOUNTS_JSON)")
    parser.add_argument("--image", "-i", type=str, help="Image path for article header")
    parser.add_argument("--list-accounts", action="store_true", help="List available accounts from env")
    parser.add_argument("--test-article", action="store_true", help="Test opening article editor")
    parser.add_argument("--test-format", action="store_true", help="Test formatting (bold, italic, @mention)")
    parser.add_argument("--test-authors", action="store_true", help="Test author dropdown navigation")
    parser.add_argument("--signature", "-s", type=str, default=SIGNATURE, help="Custom signature")

    args = parser.parse_args()

    if args.list_accounts:
        accounts = list_accounts()
        print(f"[LINKEDIN] {len(accounts)} accounts from LINKEDIN_ACCOUNTS_JSON:")
        for name, company_id in accounts.items():
            url = f"https://www.linkedin.com/article/new/?author=urn%3Ali%3Afs_normalized_company%3A{company_id}"
            print(f"  {name}: {company_id}")
        print(f"\nDefault: {os.getenv('LINKEDIN_DEFAULT_COMPANY', 'foundups')}")
        sys.exit(0)

    if args.test_article:
        success, msg = open_article_editor()
        print(f"{'[OK]' if success else '[FAIL]'} {msg}")
        sys.exit(0 if success else 1)

    if args.test_format:
        success, msg = test_formatting()
        print(f"{'[OK]' if success else '[FAIL]'} {msg}")
        sys.exit(0 if success else 1)

    if args.test_authors:
        success, msg = test_author_list()
        print(f"{'[OK]' if success else '[FAIL]'} {msg}")
        sys.exit(0 if success else 1)

    if args.post:
        success, msg = post_update(args.post, args.signature)
        print(f"{'[OK]' if success else '[FAIL]'} {msg}")
        sys.exit(0 if success else 1)

    if args.article:
        if not args.body:
            print("[ERROR] --body required for article")
            sys.exit(1)
        success, msg = write_article(
            args.article,
            args.body,
            args.signature,
            args.image,
            args.author  # Optional: switches author via dropdown
        )
        print(f"{'[OK]' if success else '[FAIL]'} {msg}")
        sys.exit(0 if success else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
