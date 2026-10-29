"""
Replay Wardrobe skill using UI-TARS vision-based automation

This replays skills using vision AI instead of DOM selectors - perfect for
YouTube Studio's custom Material Design components.
"""
import sys
import asyncio
import json
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo_root))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from modules.infrastructure.foundups_vision.src.ui_tars_bridge import UITarsBridge

print("[VISION REPLAY] Wardrobe Vision Replay Test")
print("=" * 80)

# Connect to existing Chrome on port 9222
print("[VISION REPLAY] Connecting to Chrome on port 9222...")
chrome_options = ChromeOptions()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

try:
    driver = webdriver.Chrome(options=chrome_options)
    print(f"[VISION REPLAY] Connected! Current URL: {driver.current_url}")
except Exception as e:
    print(f"[ERROR] Could not connect to Chrome: {e}")
    print("[ERROR] Make sure Chrome is running with --remote-debugging-port=9222")
    sys.exit(1)

# Load skill file
skill_path = input("\n[VISION REPLAY] Enter path to skill JSON file:\n> ").strip().strip('"')
skill_path = Path(skill_path)

if not skill_path.exists():
    print(f"[ERROR] Skill file not found: {skill_path}")
    driver.quit()
    sys.exit(1)

with open(skill_path) as f:
    skill = json.load(f)

print(f"\n[VISION REPLAY] Loaded skill: {skill['name']}")
print(f"[VISION REPLAY] Steps: {len(skill['steps'])}")
print(f"[VISION REPLAY] Target URL: {skill['meta']['target_url']}")

# Navigate to target URL if needed
current_url = driver.current_url
target_url = skill['meta']['target_url']

# Remove query parameters for comparison
current_base = current_url.split('?')[0]
target_base = target_url.split('?')[0]

if current_base != target_base:
    print(f"\n[VISION REPLAY] Navigating to target URL...")
    driver.get(target_url)
    import time
    time.sleep(3)  # Wait for page load
    print(f"[VISION REPLAY] Navigated! URL: {driver.current_url}")


async def replay_with_vision():
    """Replay skills using UI-TARS vision automation."""

    # Initialize UI-TARS bridge
    print(f"\n[VISION REPLAY] Initializing UI-TARS bridge...")
    bridge = UITarsBridge(browser_port=9222)
    await bridge.connect()

    print(f"\n[VISION REPLAY] Starting vision-based replay...")
    print(f"[VISION REPLAY] Using ui-tars-1.5-7b model via LM Studio")

    for i, step in enumerate(skill['steps'], 1):
        action = step['action']

        print(f"\n[VISION REPLAY] Step {i}/{len(skill['steps'])}: {action}")

        try:
            if action == 'click':
                # Get description from notes or construct from selector
                target_aria_label = step.get('target_aria_label', '')
                selector = step.get('selector', '')

                # Build natural language description
                if target_aria_label:
                    description = target_aria_label
                elif 'Like' in selector:
                    description = "Like button (thumbs up icon)"
                elif 'Love' in selector or 'Heart' in selector:
                    description = "Heart button (love icon)"
                elif 'Reply' in selector:
                    description = "Reply button"
                else:
                    description = "clickable button"

                print(f"[VISION REPLAY]   Looking for: {description}")

                # Use vision AI to find and click element
                result = await bridge.execute_action(
                    action='click',
                    description=description,
                    driver=driver,
                    timeout=90  # 7B model needs time for CPU inference
                )

                if result.success:
                    print(f"[VISION REPLAY]    OK Clicked: {description}")
                    print(f"[VISION REPLAY]   Confidence: {result.confidence:.2f}")
                    print(f"[VISION REPLAY]   Duration: {result.duration_ms}ms")
                    if result.metadata.get('thought'):
                        print(f"[VISION REPLAY]   Thought: {result.metadata['thought'][:80]}...")
                else:
                    print(f"[VISION REPLAY]    FAILED: {result.error}")
                    continue

            elif action == 'type':
                text = step['text']
                description = "text input field"

                print(f"[VISION REPLAY]   Typing: {text[:50]}...")

                result = await bridge.type_text(
                    description=description,
                    text=text,
                    driver=driver,
                    timeout=90
                )

                if result.success:
                    print(f"[VISION REPLAY]    OK Typed")
                else:
                    print(f"[VISION REPLAY]    FAILED: {result.error}")
                    continue

            # Small delay between steps
            import time
            time.sleep(1)

        except Exception as e:
            print(f"[VISION REPLAY]    ERROR: {str(e)[:150]}")
            continue

    bridge.close()
    print(f"\n[VISION REPLAY] Replay complete!")


# Run async replay
asyncio.run(replay_with_vision())

print("\n[VISION REPLAY] Disconnecting from Chrome (browser stays open)")
driver.quit()
