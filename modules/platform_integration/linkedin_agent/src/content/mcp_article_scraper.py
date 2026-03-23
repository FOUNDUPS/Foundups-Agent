#!/usr/bin/env python3
"""
LinkedIn Article Scraper via MCP Chrome DevTools

Batch scrapes all 012's articles using MCP browser control.
Run this when MCP Chrome DevTools is connected and logged into LinkedIn.

Usage:
    python mcp_article_scraper.py --list          # Show articles to scrape
    python mcp_article_scraper.py --scrape        # Scrape all articles
    python mcp_article_scraper.py --scrape --limit 5  # Scrape first 5

WSP 91: Observability - All extractions logged
WSP 97: Reuse existing infrastructure (MCP Chrome DevTools)
"""

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Paths
SCRIPT_DIR = Path(__file__).parent
ARTICLES_DIR = SCRIPT_DIR / "articles"
PUBLISHING_MAP_PATH = SCRIPT_DIR.parent.parent / "data" / "linkedin_publishing_map.json"

ARTICLES_DIR.mkdir(parents=True, exist_ok=True)


def load_article_urls() -> List[Dict[str, Any]]:
    """Load all article URLs from publishing map."""
    if not PUBLISHING_MAP_PATH.exists():
        print(f"[ERROR] Publishing map not found: {PUBLISHING_MAP_PATH}")
        return []

    data = json.loads(PUBLISHING_MAP_PATH.read_text(encoding="utf-8"))

    articles = []
    seen_titles = set()

    for entity in data.get("entities", []):
        entity_key = entity.get("key", "unknown")
        for article in entity.get("published_articles", []):
            title = article.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                articles.append({
                    "title": title,
                    "date": article.get("date", ""),
                    "url": article.get("url", ""),
                    "entity": entity_key
                })

    return articles


def sanitize_filename(title: str) -> str:
    """Convert article title to safe filename."""
    safe = re.sub(r'[^\w\s-]', '', title)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:80]


def article_exists(title: str) -> bool:
    """Check if article already scraped."""
    filename = sanitize_filename(title) + ".md"
    return (ARTICLES_DIR / filename).exists()


def save_article(title: str, body: str, url: str, entity: str, date: str) -> Path:
    """Save article to markdown file."""
    filename = sanitize_filename(title) + ".md"
    filepath = ARTICLES_DIR / filename

    content = f"""# {title}

**Author:** UnDaoDu Michael J Trout (012)
**Date:** {date}
**Entity:** {entity}
**URL:** {url}
**Scraped:** {datetime.now().isoformat()}

---

{body}
"""

    filepath.write_text(content, encoding="utf-8")
    print(f"[SAVED] {filename}")
    return filepath


def list_articles():
    """List all articles and their scrape status."""
    articles = load_article_urls()

    print(f"\n=== 012's LinkedIn Articles ({len(articles)} total) ===\n")
    print(f"{'#':<4} {'Status':<8} {'Entity':<20} Title")
    print("-" * 80)

    scraped = 0
    for i, article in enumerate(articles, 1):
        exists = article_exists(article["title"])
        status = "[OK]" if exists else "[    ]"
        if exists:
            scraped += 1
        print(f"{i:<4} {status:<8} {article['entity']:<20} {article['title'][:40]}")

    print(f"\n{scraped}/{len(articles)} articles scraped")
    print(f"Location: {ARTICLES_DIR}")


# ============================================================================
# MCP Integration - Called by AI Overseer / OpenClaw
# ============================================================================

SCRAPE_JS = """
() => {
  const title = document.querySelector('h1')?.innerText || 'Untitled';
  let body = '';
  const selectors = ['article', '.article-content', 'main'];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.length > 200) {
      body = el.innerText;
      break;
    }
  }
  return {
    title,
    body: body.slice(0, 25000),
    url: window.location.href
  };
}
"""

def generate_mcp_batch_commands(limit: int = 0) -> List[Dict[str, Any]]:
    """
    Generate MCP commands for batch scraping.

    Returns list of {url, title, entity, date} for articles not yet scraped.
    AI Overseer/OpenClaw can iterate through these using MCP tools.
    """
    articles = load_article_urls()
    commands = []

    for article in articles:
        if not article_exists(article["title"]):
            # Need to construct URL if not provided
            url = article.get("url", "")
            if not url:
                # Articles without direct URLs need profile navigation
                continue

            commands.append({
                "action": "scrape_article",
                "url": url,
                "title": article["title"],
                "entity": article["entity"],
                "date": article["date"],
                "save_path": str(ARTICLES_DIR / (sanitize_filename(article["title"]) + ".md"))
            })

            if limit and len(commands) >= limit:
                break

    return commands


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LinkedIn Article Scraper via MCP")
    parser.add_argument("--list", action="store_true", help="List articles and status")
    parser.add_argument("--generate-batch", action="store_true", help="Generate MCP batch commands (JSON)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of articles")

    args = parser.parse_args()

    if args.list:
        list_articles()
    elif args.generate_batch:
        commands = generate_mcp_batch_commands(args.limit)
        print(json.dumps(commands, indent=2))
    else:
        parser.print_help()
        print("\n[INFO] For automated scraping, use AI Overseer with MCP Chrome DevTools")
        print("[INFO] Or run: python article_scraper.py --all-priority (requires Chrome debug port)")


if __name__ == "__main__":
    main()
