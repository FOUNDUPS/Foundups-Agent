"""
Visual QA Loop for Cube Animation
Playwright screenshot capture -> Vision analysis -> Fix -> Repeat

Usage:
    python -m modules.foundups.simulator.visual_qa [--url URL] [--wait SECONDS]

Agent Pattern:
    1. capture_screenshot() -> path
    2. (Vision tool reads image)
    3. Analyze issues
    4. Fix code
    5. capture_screenshot() -> verify
    6. Repeat until fixed
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import argparse

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"


def capture_screenshot(
    url: str = "http://localhost:5000/about/",
    name: str = "cube_qa",
    wait_sec: float = 5.0,
    scroll_to: str = "buildCanvas",
) -> Path:
    """Capture screenshot of cube animation for vision analysis."""
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})

        page.goto(url)

        # Scroll to target element
        if scroll_to:
            page.evaluate(f"""
                const el = document.getElementById("{scroll_to}");
                if (el) el.scrollIntoView({{ behavior: "instant", block: "center" }});
            """)

        # Wait for animation to render
        time.sleep(wait_sec)

        timestamp = int(time.time())
        screenshot_path = SCREENSHOT_DIR / f"{name}_{timestamp}.png"
        page.screenshot(path=str(screenshot_path))
        browser.close()

        print(f"Screenshot saved: {screenshot_path}")
        return screenshot_path


def capture_sequence(
    url: str = "http://localhost:5000/about/",
    count: int = 3,
    interval: float = 10.0,
) -> list:
    """Capture multiple screenshots to catch different animation phases."""
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    paths = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})

        page.goto(url)
        page.evaluate("""
            const canvas = document.getElementById("buildCanvas");
            if (canvas) canvas.scrollIntoView({ behavior: "instant", block: "center" });
        """)

        time.sleep(3)  # Initial render

        for i in range(count):
            timestamp = int(time.time())
            path = SCREENSHOT_DIR / f"phase_{i}_{timestamp}.png"
            page.screenshot(path=str(path))
            paths.append(path)
            print(f"Screenshot {i+1}/{count}: {path}")
            if i < count - 1:
                time.sleep(interval)

        browser.close()

    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visual QA for cube animation")
    parser.add_argument("--url", default="http://localhost:5000/about/")
    parser.add_argument("--wait", type=float, default=5.0, help="Seconds to wait before capture")
    parser.add_argument("--sequence", action="store_true", help="Capture sequence of phases")
    parser.add_argument("--count", type=int, default=3, help="Number of screenshots in sequence")
    args = parser.parse_args()

    if args.sequence:
        paths = capture_sequence(args.url, args.count)
        print(f"\nCaptured {len(paths)} screenshots")
    else:
        path = capture_screenshot(args.url, wait_sec=args.wait)
        print(f"\nReady for vision analysis: {path}")
