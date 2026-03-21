#!/usr/bin/env python3
"""
LinkedIn Article Scraper for Digital Twin Voice Pattern Loading

Connects to existing Chrome session, navigates to LinkedIn articles,
extracts full content, and saves to markdown for HoloIndex ingestion.

Usage:
    python article_scraper.py --profile openstartup
    python article_scraper.py --company 1263645
    python article_scraper.py --list  # List known entities from publishing map

WSP 91: Observability - All extractions logged
WSP 50: Pre-Action - Verifies Chrome session before scraping
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
ARTICLES_DIR = SCRIPT_DIR / "articles"
PUBLISHING_MAP_PATH = SCRIPT_DIR.parent.parent / "data" / "linkedin_publishing_map.json"

# Ensure articles directory exists
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)


def load_publishing_map() -> Dict[str, Any]:
    """Load the LinkedIn publishing map."""
    if not PUBLISHING_MAP_PATH.exists():
        logger.error(f"Publishing map not found: {PUBLISHING_MAP_PATH}")
        return {"entities": []}
    return json.loads(PUBLISHING_MAP_PATH.read_text(encoding="utf-8"))


def get_browser(port: int = 9222):
    """
    Connect to existing Chrome debug session.

    Args:
        port: Chrome debug port (default 9222)
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    import requests

    # Check if Chrome is running on debug port
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
        if resp.status_code != 200:
            raise RuntimeError(f"Chrome not responding on port {port}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"No Chrome session on port {port}. Start Chrome with: chrome.exe --remote-debugging-port={port}")

    # Connect to existing Chrome
    chrome_options = ChromeOptions()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")

    driver = webdriver.Chrome(options=chrome_options)

    # Verify connection
    _ = driver.current_url
    logger.info(f"[BROWSER] Connected to Chrome on port {port}")

    return driver


def sanitize_filename(title: str) -> str:
    """Convert article title to safe filename."""
    # Remove special characters, replace spaces with underscores
    safe = re.sub(r'[^\w\s-]', '', title)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:80]  # Limit length


def extract_article_content(driver, url: str) -> Optional[Dict[str, Any]]:
    """
    Navigate to article URL and extract content.

    Returns dict with: title, date, author, content, url
    """
    logger.info(f"[SCRAPE] Navigating to: {url}")
    driver.get(url)
    time.sleep(3)  # Wait for page load

    try:
        # LinkedIn article structure varies, try multiple selectors
        content = {}

        # Title
        title_selectors = [
            "h1.article-title",
            "h1[data-test-id='article-title']",
            ".article-content h1",
            "h1"
        ]
        for sel in title_selectors:
            try:
                elem = driver.find_element("css selector", sel)
                if elem and elem.text.strip():
                    content["title"] = elem.text.strip()
                    break
            except:
                continue

        # Author
        author_selectors = [
            ".article-author-name",
            "[data-test-id='author-name']",
            ".author-info .name"
        ]
        for sel in author_selectors:
            try:
                elem = driver.find_element("css selector", sel)
                if elem and elem.text.strip():
                    content["author"] = elem.text.strip()
                    break
            except:
                continue

        # Date
        date_selectors = [
            ".article-date",
            "time",
            "[data-test-id='published-date']"
        ]
        for sel in date_selectors:
            try:
                elem = driver.find_element("css selector", sel)
                if elem:
                    content["date"] = elem.get_attribute("datetime") or elem.text.strip()
                    break
            except:
                continue

        # Main content - try multiple approaches
        body_selectors = [
            ".article-content",
            "[data-test-id='article-content']",
            ".article__content",
            "article",
            ".reader-article-content"
        ]
        for sel in body_selectors:
            try:
                elem = driver.find_element("css selector", sel)
                if elem and elem.text.strip():
                    content["body"] = elem.text.strip()
                    break
            except:
                continue

        # Fallback: get all text from main content area
        if "body" not in content:
            try:
                main = driver.find_element("css selector", "main")
                content["body"] = main.text.strip()
            except:
                pass

        content["url"] = url
        content["scraped_at"] = datetime.now().isoformat()

        if "title" not in content and "body" not in content:
            logger.warning(f"[SCRAPE] Could not extract content from {url}")
            return None

        return content

    except Exception as e:
        logger.error(f"[SCRAPE] Extraction failed: {e}")
        return None


def save_article(content: Dict[str, Any], entity_key: str) -> Path:
    """Save article content to markdown file."""
    title = content.get("title", "Untitled")
    filename = f"{sanitize_filename(title)}.md"
    filepath = ARTICLES_DIR / filename

    md_content = f"""# {title}

**Author:** {content.get('author', 'UnDaoDu Michael J Trout')}
**Date:** {content.get('date', 'Unknown')}
**Entity:** {entity_key}
**URL:** {content.get('url', '')}
**Scraped:** {content.get('scraped_at', '')}

---

{content.get('body', '[Content extraction failed]')}
"""

    filepath.write_text(md_content, encoding="utf-8")
    logger.info(f"[SAVE] Article saved: {filepath}")
    return filepath


def scrape_profile_articles(driver, profile_slug: str = "openstartup") -> List[Path]:
    """
    Scrape all articles from a personal profile.

    Args:
        driver: Selenium WebDriver
        profile_slug: LinkedIn profile URL slug (e.g., 'openstartup')
    """
    articles_url = f"https://www.linkedin.com/in/{profile_slug}/recent-activity/articles/"
    logger.info(f"[PROFILE] Loading articles from: {articles_url}")

    driver.get(articles_url)
    time.sleep(3)

    # Find all article links
    article_links = []
    try:
        # LinkedIn article links in activity feed
        link_elements = driver.find_elements("css selector", "a[href*='/pulse/']")
        for elem in link_elements:
            href = elem.get_attribute("href")
            if href and "/pulse/" in href and href not in article_links:
                article_links.append(href)

        logger.info(f"[PROFILE] Found {len(article_links)} article links")
    except Exception as e:
        logger.error(f"[PROFILE] Failed to find article links: {e}")

    # Scrape each article
    saved_files = []
    for i, link in enumerate(article_links):
        logger.info(f"[PROFILE] Scraping article {i+1}/{len(article_links)}")
        content = extract_article_content(driver, link)
        if content:
            filepath = save_article(content, f"personal_{profile_slug}")
            saved_files.append(filepath)
        time.sleep(2)  # Rate limiting

    return saved_files


def scrape_company_articles(driver, company_id: str) -> List[Path]:
    """
    Scrape all articles from a company page.

    Args:
        driver: Selenium WebDriver
        company_id: LinkedIn company numeric ID
    """
    # Load publishing map to get entity info
    pub_map = load_publishing_map()
    entity = None
    for e in pub_map.get("entities", []):
        if e.get("company_id") == company_id:
            entity = e
            break

    if not entity:
        logger.warning(f"[COMPANY] Company {company_id} not in publishing map")
        entity = {"key": f"company_{company_id}", "published_articles": []}

    manage_url = f"https://www.linkedin.com/article/manage/published/?author=urn:li:fs_normalized_company:{company_id}"
    logger.info(f"[COMPANY] Loading articles from: {manage_url}")

    driver.get(manage_url)
    time.sleep(3)

    # Find all article links from management page
    article_links = []
    try:
        link_elements = driver.find_elements("css selector", "a[href*='/pulse/']")
        for elem in link_elements:
            href = elem.get_attribute("href")
            if href and "/pulse/" in href and href not in article_links:
                article_links.append(href)

        logger.info(f"[COMPANY] Found {len(article_links)} article links")
    except Exception as e:
        logger.error(f"[COMPANY] Failed to find article links: {e}")

    # Scrape each article
    saved_files = []
    for i, link in enumerate(article_links):
        logger.info(f"[COMPANY] Scraping article {i+1}/{len(article_links)}")
        content = extract_article_content(driver, link)
        if content:
            filepath = save_article(content, entity.get("key", f"company_{company_id}"))
            saved_files.append(filepath)
        time.sleep(2)  # Rate limiting

    return saved_files


def list_entities():
    """List all known entities from publishing map."""
    pub_map = load_publishing_map()

    print("\n=== LinkedIn Publishing Entities ===\n")
    print(f"{'Key':<35} {'Company ID':<12} {'Articles':<8} Status")
    print("-" * 70)

    for entity in pub_map.get("entities", []):
        key = entity.get("key", "unknown")
        cid = entity.get("company_id") or "personal"
        articles = len(entity.get("published_articles", []))
        status = entity.get("status", "unknown")
        print(f"{key:<35} {cid:<12} {articles:<8} {status}")

    print("\nUsage:")
    print("  python article_scraper.py --profile openstartup")
    print("  python article_scraper.py --company 1263645")


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Article Scraper for Digital Twin Voice Pattern Loading"
    )
    parser.add_argument("--profile", type=str, help="Personal profile slug (e.g., openstartup)")
    parser.add_argument("--company", type=str, help="Company numeric ID (e.g., 1263645)")
    parser.add_argument("--list", action="store_true", help="List known entities")
    parser.add_argument("--all-priority", action="store_true", help="Scrape all priority entities")

    args = parser.parse_args()

    if args.list:
        list_entities()
        return

    if not args.profile and not args.company and not args.all_priority:
        parser.print_help()
        return

    # Connect to Chrome
    try:
        driver = get_browser()
        logger.info("[BROWSER] Connected to Chrome session")
    except Exception as e:
        logger.error(f"[BROWSER] Failed to connect: {e}")
        logger.info("[BROWSER] Ensure Chrome is running with: chrome.exe --remote-debugging-port=9222")
        return

    saved_files = []

    if args.profile:
        saved_files.extend(scrape_profile_articles(driver, args.profile))

    if args.company:
        saved_files.extend(scrape_company_articles(driver, args.company))

    if args.all_priority:
        # Scrape priority entities
        logger.info("[ALL] Scraping all priority entities...")
        saved_files.extend(scrape_profile_articles(driver, "openstartup"))

        priority_companies = ["1263645", "107481170", "2199715", "377243"]
        for cid in priority_companies:
            saved_files.extend(scrape_company_articles(driver, cid))

    print(f"\n=== Scraping Complete ===")
    print(f"Articles saved: {len(saved_files)}")
    print(f"Location: {ARTICLES_DIR}")

    if saved_files:
        print("\nSaved files:")
        for f in saved_files:
            print(f"  - {f.name}")


if __name__ == "__main__":
    main()
