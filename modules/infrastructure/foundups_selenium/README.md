# FoundUps Selenium - Enhanced Browser Automation

**Extended Selenium WebDriver with anti-detection, vision, and platform helpers built-in**

This is a **wrapper** around official Selenium (not a fork), providing FoundUps-specific enhancements while maintaining compatibility with official Selenium updates.

## Features

YouTube attachment owners install a human verification handoff: a detected
“Verify it's you” prompt yields browser effects for at least 30 seconds so 012
can finish verification, and longer while the prompt remains. It never answers
the challenge or replays the interrupted effect. See the
[handoff contract](INTERFACE.md#youtube-human-verification-handoff) for shared
state, recovery and coverage limits. Source tests do not prove live activation.

笨・**Anti-Detection by Default** - Stealth mode enabled automatically
笨・**Browser Reuse** - Connect to existing browsers via port 9222 (no more multiple windows!)
笨・**Gemini Vision Integration** - AI-powered UI analysis built-in
笨・**Platform Helpers** - High-level posting for X, LinkedIn, etc.
笨・**Human-Like Behavior** - Random delays, character-by-character typing
笨・**Pattern Learning** - Remembers successful automation patterns
笨・**Session Persistence** - Profile-based session management

---

## Quick Start

### Basic Usage

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver

# Create driver with all enhancements enabled
driver = FoundUpsDriver()

# Navigate and interact
driver.get("https://x.com/home")
driver.random_delay()  # Human-like pause

# Close when done
driver.quit()
```

### Browser Reuse (No More Multiple Windows!)

```python
# Start Chrome with debugging port (run once manually)
# > start_chrome_for_selenium.bat

# Connect to existing browser
driver = FoundUpsDriver(port=9222)

# Or use connect_or_create helper
driver = FoundUpsDriver()
driver.connect_or_create(port=9222)  # Connects to existing or creates new
```

### Vision-Guided Automation

```python
# Enable Gemini Vision (enabled by default)
driver = FoundUpsDriver(vision_enabled=True)

# Analyze current page UI
driver.get("https://x.com/compose/post")
analysis = driver.analyze_ui(save_screenshot=True)

print(f"Post button enabled: {analysis.get('post_button', {}).get('enabled')}")
print(f"UI State: {analysis.get('ui_state')}")
```

### Platform-Specific Helpers

```python
# High-level X posting
driver = FoundUpsDriver()
driver.connect_or_create(port=9222)
success = driver.post_to_x("Hello from FoundUps Selenium!")

# LinkedIn posting (coming soon)
success = driver.post_to_linkedin("Professional update...")
```

### Telemetry & MCP Integration (WSP 77 / 80 Alignment)

FoundUpsDriver now exposes a lightweight observer interface so Model Context Protocol
servers (or any supervisory agent) can subscribe to browser telemetry without forking
Selenium.

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver

events = []

def observer(event: str, payload: dict) -> None:
    # Persist to MCP bus, Gateway Sentinel, etc.
    events.append({"event": event, **payload})

driver = FoundUpsDriver(observers=[observer], port=9222)
driver.post_to_x("Holo + Qwen approved copy")
```

Key events emitted:

- `init_requested`, `init_retry`, `init_retry_succeeded`
- `connect_or_create_*` lifecycle with navigation payloads
- `vision_analyze_*` detailing Gemini calls and screenshot paths
- `human_type` and `post_to_x_*` for human-in-the-loop auditing

The Social Media Orchestrator's browser manager automatically registers this observer for every Chrome session and appends JSON-lines telemetry to `logs/foundups_browser_events.log`, so the MCP gateway (plus Gemma 3 270M and Qwen 1.5B sentinels) can audit reuse vs. creation, UI analysis, and posting outcomes in real time.

These hooks map cleanly onto the MCP Browser faﾃｧade described in
`docs/mcp/MCP_Master_Services.md`, giving Gemma 3 270M and Qwen 1.5B real-time
visibility into 0102 execution trails.

### Telemetry Storage - SQLite Database

Browser telemetry sessions are automatically persisted to `data/foundups.db` for offline analysis and pattern learning. The `selenium_sessions` table stores:

**Schema**:
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment session ID |
| `timestamp` | TEXT | ISO8601 UTC timestamp (auto-generated) |
| `url` | TEXT | Page URL being browsed (required) |
| `screenshot_hash` | TEXT | SHA256 hash for deduplication |
| `screenshot_path` | TEXT | Absolute path to raw screenshot |
| `annotated_path` | TEXT | Path to Gemini-annotated screenshot |
| `analysis_json` | TEXT | Raw JSON dump of Gemini Vision analysis |

**Indexes**:
- `idx_selenium_sessions_timestamp` - Efficient time-based queries
- `idx_selenium_sessions_hash` - Screenshot deduplication

**Usage Example**:

```python
from modules.infrastructure.foundups_selenium.src.telemetry_store import record_session

# Record a telemetry session
session_id = record_session({
    "url": "https://x.com/compose/post",
    "screenshot_hash": "sha256:abc123...",
    "screenshot_path": "/tmp/screenshots/session_001.png",
    "annotated_path": "/tmp/annotated/session_001_annotated.png",
    "analysis_json": {
        "post_button": {"found": True, "enabled": True},
        "ui_state": "ready_to_post",
        "confidence": 0.95
    }
})
```

**Implementation**:
- Module: `src/telemetry_store.py`
- Tests: `tests/test_telemetry_store.py` (17/17 passing)
- Thread-safe: Uses SQLite autocommit mode for concurrent writes
- Auto-creation: Table and indexes created automatically on first use
- WSP References: WSP 72 (Module Independence), WSP 22 (Documentation)

**MCP Integration**:
The telemetry store can be queried by MCP servers and Gemma/Qwen agents for:
- Session replay and debugging
- Pattern learning from successful automations
- UI state transition analysis
- Performance profiling (screenshot timing, analysis duration)

---

## Installation

### Within FoundUps System

```bash
# No installation needed - already part of FoundUps infrastructure
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver
```

### As Standalone Package (Future)

```bash
pip install foundups-selenium
```

---

## API Reference

### FoundUpsDriver

Main driver class extending `selenium.webdriver.Chrome`

#### Constructor

```python
FoundUpsDriver(
    vision_enabled: bool = True,
    stealth_mode: bool = True,
    profile_dir: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs
)
```

**Parameters**:
- `vision_enabled` - Enable Gemini Vision integration (default: True)
- `stealth_mode` - Enable anti-detection measures (default: True)
- `profile_dir` - Browser profile directory for session persistence
- `port` - Debugging port to connect to existing browser (e.g., 9222)
- `**kwargs` - Additional args passed to selenium.webdriver.Chrome

#### Methods

**`connect_or_create(port=9222, profile_dir=None, url=None) -> bool`**

Smart browser reuse - connect to existing or create new

```python
driver = FoundUpsDriver()
connected = driver.connect_or_create(port=9222)
# Returns: True if connected to existing, False if created new
```

**`analyze_ui(save_screenshot=False, screenshot_dir='./screenshots') -> dict`**

Analyze current page UI with Gemini Vision

```python
analysis = driver.analyze_ui(save_screenshot=True)
# Returns: {
#     "post_button": {"found": bool, "enabled": bool},
#     "text_area": {"found": bool, "has_text": bool},
#     "errors": [list of errors],
#     "ui_state": "ready_to_post" | "error" | "posted"
# }
```

**`human_type(element, text, min_delay=0.03, max_delay=0.08)`**

Type like a human with random delays

```python
text_box = driver.find_element(By.ID, "post-text")
driver.human_type(text_box, "Hello world!")
```

**`random_delay(min_sec=1.0, max_sec=3.0)`**

Random human-like delay

```python
driver.random_delay(1, 3)  # Wait 1-3 seconds randomly
```

**`post_to_x(content, account='foundups') -> bool`**

Post to X/Twitter with vision guidance

```python
success = driver.post_to_x("Testing FoundUps Selenium!", account='foundups')
```

**`smart_find_element(selectors, description="", timeout=10, use_vision=False)`**

Smart element finding with fallbacks

```python
# Try multiple selectors, fall back to vision
element = driver.smart_find_element(
    selectors=["//button[@id='post']", "//button[text()='Post']"],
    description="blue Post button in top right",
    use_vision=True
)
```

### Factory Function

**`create_driver(browser='chrome', vision=True, stealth=True, profile=None, port=None)`**

Factory function to create FoundUps driver

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import create_driver

driver = create_driver(
    browser='chrome',
    vision=True,
    stealth=True,
    port=9222
)
```

---

## Configuration

### Anti-Detection Settings

Anti-detection is **enabled by default**. The following measures are applied:

**Chrome Options**:
- `--disable-blink-features=AutomationControlled`
- Exclude automation switches
- Disable automation extension
- Human-like window size (1920x1080)
- Real user agent string

**JavaScript Patches**:
- Override `navigator.webdriver` (set to undefined)
- Add fake plugins array
- Add chrome runtime object

### Browser Reuse Setup

To enable browser reuse, you need to start Chrome with debugging port enabled:

#### Windows (start_chrome_for_selenium.bat):
```batch
start chrome.exe ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%PROFILE_DIR%" ^
  --disable-blink-features=AutomationControlled ^
  https://x.com/home
```

#### Linux/Mac:
```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE_DIR" \
  --disable-blink-features=AutomationControlled \
  https://x.com/home
```

Then in your code:
```python
driver = FoundUpsDriver(port=9222)  # Connects to existing browser
```

### Gemini Vision Setup

Gemini Vision requires Google AI Studio API key (FREE):

1. Get API key: https://makersuite.google.com/app/apikey
2. Add to `.env`: `GOOGLE_API_KEY=your_key_here`
3. Vision will be enabled automatically

---

## Examples

### Example 1: Simple Posting with Browser Reuse

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver

# Connect to existing browser (or create new)
driver = FoundUpsDriver()
driver.connect_or_create(port=9222)

# Post to X
success = driver.post_to_x("Hello from FoundUps!")

# Keep browser open for next post
print("Browser staying open for reuse...")
```

### Example 2: Vision-Guided Automation

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver

driver = FoundUpsDriver(vision_enabled=True)
driver.get("https://x.com/compose/post")

# Type content
text_area = driver.smart_find_element(
    selectors=["//div[@role='textbox']"],
    description="main text input area"
)
driver.human_type(text_area, "Testing vision-guided posting")

# Check if Post button is enabled
analysis = driver.analyze_ui(save_screenshot=True)
if analysis['post_button']['enabled']:
    # Click Post button
    post_button = driver.smart_find_element(
        selectors=["//button[@data-testid='tweetButton']"]
    )
    post_button.click()
```

### Example 3: Multi-Account Posting

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver

# Post to FoundUps account
driver_foundups = FoundUpsDriver(profile_dir='./profiles/foundups')
driver_foundups.post_to_x("Update from FoundUps!", account='foundups')

# Post to Move2Japan account (different browser/profile)
driver_m2j = FoundUpsDriver(profile_dir='./profiles/move2japan')
driver_m2j.post_to_x("Update from Move2Japan!", account='move2japan')
```

---

## Architecture

### Components

```
foundups_selenium/
笏懌楳笏 src/
笏・  笏懌楳笏 foundups_driver.py       # Main FoundUpsDriver class
笏・  笏懌楳笏 anti_detection.py        # Anti-detection helpers (future)
笏・  笏懌楳笏 vision_helpers.py        # Vision integration (future)
笏・  笏披楳笏 platform_helpers.py      # Platform-specific helpers (future)
笏懌楳笏 tests/
笏・  笏披楳笏 test_foundups_driver.py  # Test suite
笏懌楳笏 docs/
笏・  笏披楳笏 Selenium_Fork_Analysis.md
笏懌楳笏 README.md
笏懌楳笏 INTERFACE.md
笏披楳笏 requirements.txt
```

### Integration Points

FoundUps Selenium integrates with:

1. **Gemini Vision Analyzer** - `social_media_orchestrator/src/gemini_vision_analyzer.py`
2. **X Anti-Detection Poster** - `x_twitter/src/x_anti_detection_poster.py`
3. **Browser Manager** - `social_media_orchestrator/src/core/browser_manager.py`
4. **Pattern Memory** - `social_media_orchestrator/memory/posting_patterns.json`

---

## Advantages Over Stock Selenium

| Feature | Stock Selenium | FoundUps Selenium |
|---------|---------------|-------------------|
| Anti-detection | Manual setup | 笨・Built-in |
| Browser reuse | Manual port 9222 | 笨・connect_or_create() |
| Vision analysis | Not available | 笨・Gemini Vision |
| Human typing | Manual delays | 笨・human_type() |
| Platform helpers | Write yourself | 笨・post_to_x(), etc. |
| Session persistence | Manual profiles | 笨・Built-in |
| Element finding | XPath only | 笨・Vision fallback |

---

## Why NOT Fork Selenium?

We chose to **extend** rather than **fork** because:

1. **Easy Maintenance** - Get official Selenium updates automatically
2. **Community Support** - Benefit from Selenium ecosystem
3. **Less Overhead** - Don't maintain entire WebDriver infrastructure
4. **Faster Development** - Focus on FoundUps features, not browser drivers
5. **Compatibility** - Works with existing Selenium tools and libraries

**Future**: We may fork Selenium for deeper improvements, but extension approach gives us 80% of benefits with 20% of effort.

---

## Roadmap

### Phase 1: Extension Package 笨・COMPLETE
- [x] FoundUpsDriver class with anti-detection
- [x] Browser reuse via port 9222
- [x] Gemini Vision integration
- [x] Human-like behavior helpers
- [x] X posting helper

### Phase 2: Advanced Features (NEXT) - 20K tokens
- [ ] Vision-based element finding (no XPath needed)
- [ ] LinkedIn posting helper
- [ ] Instagram posting helper
- [ ] Pattern learning and memory
- [ ] Multi-account orchestration

### Phase 3: Selenium Fork (FUTURE) - 50K tokens
- [ ] Fork Selenium repository
- [ ] Native stealth mode at WebDriver level
- [ ] Built-in vision integration
- [ ] Custom browser driver optimizations
- [ ] Contribute improvements back to Selenium

### Sprint Execution Plan (0102 Autonomous Loop)
- **Sprint 1 – Stabilise Selenium DAE (✅ complete)**  
  Harden driver init, fallback, and vision workflows with pytest coverage so Qwen/Gemma have a reliable browser worker.
- **Sprint 2 – Telemetry & Logging (🚧 in progress)**  
  Persist hashed screenshots plus session JSONL/SQL telemetry so Holo + Gemma can summarise runs; expose the data over MCP.
- **Sprint 3 – MCP Interface Stub (⏭ queued)**  
  Publish driver actions through a lightweight MCP server (`connect_or_create`, `analyze_ui`, `post_to_x`) for Overseer teams.
- **Sprint 4 – Credential Vault Hook (⏭ queued)**  
  Replace raw environment lookups with Secrets MCP fetches while keeping pytest doubles for offline CI.
- **Sprint 5 – Human-in-the-loop UX (⏭ queued)**  
  Add preview/approve checkpoints and ensure telemetry records the approvals for auditing.

**Qwen execution routing:**
Default to the FoundUps Selenium driver for browser-only automations; escalate to **UI‑TARS‑1.5** when missions cross into desktop or multi-application control so the autonomous loop respects WSP 3 modular boundaries.

### Sprint 6 – Draft & Schedule Loop (Planned)
- Integrate `skills.md` templates with the Social Media DAE so Claude/Grok/Gemini author LinkedIn copy.
- Use UI‑TARS to populate LinkedIn scheduler with 012-approved drafts instead of immediate posting.
- Expand Vision DAE telemetry for approval feedback so Qwen/Gemma learn from 012 edits.

---

## License

Same as Selenium: Apache License 2.0

FoundUps Selenium is a wrapper/extension of Selenium, not a fork. All Selenium functionality remains unchanged and subject to Selenium's license.

---

## Contributing

Improvements welcome! Areas of interest:

1. Vision-guided element finding
2. Additional platform helpers (TikTok, Instagram, etc.)
3. Pattern learning algorithms
4. Performance optimizations
5. Documentation improvements

---

## Support

- **Issues**: Report in FoundUps repository
- **Questions**: See `docs/Selenium_Fork_Analysis.md`
- **Examples**: See `tests/` directory

---

**Status**: 笨・Phase 1 Complete - Core functionality working
**Token Budget**: ~10K tokens used
**Next**: Vision-based element finding + LinkedIn helpers


