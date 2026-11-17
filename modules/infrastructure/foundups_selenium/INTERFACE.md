# FoundUps Selenium - Public Interface

**Module**: `foundups_selenium`
**Domain**: `infrastructure`
**Purpose**: Enhanced Selenium WebDriver with anti-detection, vision, and automation helpers

---

## Public API

### YouTube human verification handoff

`src.youtube_verification.install_youtube_verification_guard(driver, port)`
wraps an already attached Selenium driver once, retaining its identity. It does
not connect, launch a browser or complete authentication. Cooperating drivers on
the same loopback debug port serialize effects using the existing runtime lock.

Before an effect, a bounded passive target inventory detects official Google
sign-in/challenge pages; a read-only Studio dialog probe recognizes English or
Japanese verification headings, including open shadow roots. Ordinary comment
text is not a verification signal. A detected challenge creates a shared hold
for **at least 30 seconds**, extended while it remains present or unobservable.
Navigation, refresh, close, typing, clicks, scripts, CDP and screenshots wait.
Passive Selenium lookups remain available; global STOP exits without clearing
the hold. No authentication text, URLs, screenshots or credentials are stored.

The control record is `%USERPROFILE%/.foundups-agent/browser-verification/<port>.json`
(home-directory equivalent elsewhere), containing monotonic start time and a
hashed Selenium target handle. A clear observation on that same target after
the minimum interval removes the hold and raises `VerificationHandoff`; the
interrupted effect is **cancelled**, not replayed. An effect already dispatched
retains its original exception and uncertain outcome. Existing owners must
revalidate their page/action before another attempt and retain unknown writes.

Malformed control state, lost original target or unavailable observations do
not authorize effects. A lost target/stale record needs explicit owner recovery;
never automatically discard it or clear another STOP. Coverage is limited to
participating Selenium drivers and observable page/dialog signals. It does not
cover native OS prompts, closed shadow roots or other browser clients, and does
not implement the scheduler's separate 60-second draft/manual-takeover contract.
Offline qualification is separate from installation and live popup acceptance.

### Main Class: FoundUpsDriver

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver

class FoundUpsDriver(webdriver.Chrome):
    """Extended Selenium with FoundUps enhancements"""
```

#### Constructor

```python
def __init__(
    self,
    vision_enabled: bool = True,
    stealth_mode: bool = True,
    profile_dir: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs
) -> None
```

#### Core Methods

**Browser Management**:
- `connect_or_create(port=9222, profile_dir=None, url=None) -> bool` - Smart browser reuse
- `quit() -> None` - Close browser (inherited from Selenium)

**Vision Analysis**:
- `analyze_ui(save_screenshot=False, screenshot_dir='./screenshots') -> dict` - Gemini Vision UI analysis

**Human-Like Interaction**:
- `human_type(element, text, min_delay=0.03, max_delay=0.08) -> None` - Type with delays
- `random_delay(min_sec=1.0, max_sec=3.0) -> None` - Random pause

**Smart Element Finding**:
- `smart_find_element(selectors, description="", timeout=10, use_vision=False) -> WebElement` - Find with fallbacks

**Platform Helpers**:
- `post_to_x(content, account='foundups') -> bool` - X/Twitter posting
- `post_to_linkedin(content, account='default') -> bool` - LinkedIn posting (future)

### Factory Function

```python
def create_driver(
    browser: str = 'chrome',
    vision: bool = True,
    stealth: bool = True,
    profile: Optional[str] = None,
    port: Optional[int] = None
) -> FoundUpsDriver
```

---

## Usage Examples

### Basic Usage

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import FoundUpsDriver

# Create with all defaults (anti-detection + vision enabled)
driver = FoundUpsDriver()

# Navigate
driver.get("https://example.com")

# Close
driver.quit()
```

### Browser Reuse

```python
# Connect to existing Chrome on port 9222
driver = FoundUpsDriver(port=9222)

# Or use helper
driver = FoundUpsDriver()
driver.connect_or_create(port=9222)
```

### Vision Analysis

```python
driver = FoundUpsDriver(vision_enabled=True)
driver.get("https://x.com/compose/post")

# Analyze UI
analysis = driver.analyze_ui(save_screenshot=True)
print(f"Post button enabled: {analysis['post_button']['enabled']}")
```

### Platform Posting

```python
driver = FoundUpsDriver()
driver.connect_or_create(port=9222)

# High-level posting
success = driver.post_to_x("Hello from FoundUps!")
```

---

## Return Types

### analyze_ui() Returns

```python
{
    "post_button": {
        "found": bool,
        "enabled": bool
    },
    "text_area": {
        "found": bool,
        "has_text": bool
    },
    "errors": [str],  # List of error messages
    "ui_state": str,  # "ready_to_post" | "error" | "posted"
    "screenshot_path": str  # Optional, if save_screenshot=True
}
```

---

## Integration Points

### Imports

```python
from modules.infrastructure.foundups_selenium.src.foundups_driver import (
    FoundUpsDriver,
    create_driver
)
```

### Dependencies

**Required**:
- `selenium>=4.0.0`
- Python 3.8+

**Optional** (for vision):
- `modules.platform_integration.social_media_orchestrator.src.gemini_vision_analyzer`
- Google AI Studio API key in .env

**Optional** (for platform helpers):
- `modules.platform_integration.x_twitter.src.x_anti_detection_poster`

---

## Configuration

### Environment Variables

```bash
# Optional - for Gemini Vision
GOOGLE_API_KEY=your_google_ai_studio_key

# Optional - for X posting
X_Acc2=foundups_username
x_Acc_pass=password
```

### Browser Setup for Reuse

**Windows**:
```batch
start chrome.exe --remote-debugging-port=9222 --user-data-dir="./profile"
```

**Linux/Mac**:
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="./profile"
```

---

## Anti-Detection Features

Enabled by default when `stealth_mode=True`:

**Chrome Flags**:
- `--disable-blink-features=AutomationControlled`
- Exclude automation switches
- Disable automation extension
- Real user agent

**JavaScript Patches**:
- `navigator.webdriver = undefined`
- Fake plugins array
- Chrome runtime object

---

## Error Handling

All methods may raise standard Selenium exceptions:

- `selenium.common.exceptions.NoSuchElementException`
- `selenium.common.exceptions.TimeoutException`
- `selenium.common.exceptions.WebDriverException`

Additional FoundUps-specific behaviors:

- **Vision disabled**: `analyze_ui()` returns `{"error": "Vision not enabled"}`
- **Port connection failed**: Falls back to creating new browser
- **Platform helper unavailable**: Returns `False` and logs warning

---

## Performance Considerations

**Token Usage** (when using vision):
- `analyze_ui()`: ~100-200 tokens per call
- Gemini API: FREE tier sufficient for moderate usage

**Memory**:
- Each driver instance: ~100-200MB (Chrome process)
- Browser reuse recommended to avoid multiple instances

**Network**:
- Vision analysis: ~10-50KB per screenshot upload to Gemini
- Real-time analysis: ~1-2 seconds per call

---

## Module Status

**Version**: 1.0.0 (Initial Release)
**Status**: [OK] Production Ready - Core functionality complete
**Maintenance**: Active - Part of FoundUps infrastructure

### Feature Status

- [OK] Anti-detection (complete)
- [OK] Browser reuse (complete)
- [OK] Gemini Vision (complete)
- [OK] X posting helper (complete)
- [REFRESH] LinkedIn helper (in progress)
- [CLIPBOARD] Vision-based element finding (planned)
- [CLIPBOARD] Pattern learning (planned)

---

## Testing

```python
# Run example
python modules/infrastructure/foundups_selenium/src/foundups_driver.py

# Run tests (future)
pytest modules/infrastructure/foundups_selenium/tests/
```

---

## Related Modules

**Uses**:
- `social_media_orchestrator` - Gemini Vision analyzer
- `x_twitter` - X posting implementation

**Used By**:
- `x_twitter` - Browser automation
- `linkedin_agent` - Browser automation (future)
- Any module needing web automation

---

## Support & Documentation

**Full Documentation**: See `README.md`
**Examples**: See `README.md` Examples section
**Architecture**: See `docs/Selenium_Fork_Analysis.md`
**Issues**: Report in FoundUps repository

---

**Last Updated**: 2025-10-16
**Token Budget**: ~10K tokens used for initial implementation
## WRE visual verification evidence

`WREVisualTestRunner.step(name, action, verify_prompt, wait_after_action=2.0,
max_retries=2, dom_verify=None) -> bool` executes the action **once**. The existing
`max_retries` argument now limits read-only observations, never action replay.
An action exception or explicit `False` result stops the step with uncertain
outcome; inspect it before any separately authorized action. Callers must stop
dependent steps when the returned value is false.

With `dom_verify`, only that explicit read-only callback's literal `True` passes,
and the evidence method is `dom`. Without it, UI-TARS receives the actual driver
and performs **visual target localization** (`visual_localization`). Its current
bridge locates a described element; coordinate detection does not prove arbitrary
field values, publication, media playback or task completion. Use target
descriptions for localization and explicit assertions for values. `use_uitars=False`
does not supply a DOM assertion. Missing/disabled vision returns `unavailable`;
exceptions return `error`, never an assumed pass. The synchronous vision path
refuses an already running event loop without constructing an unused coroutine.

Step summaries and existing PatternMemory output retain method, status
(`passed`, `failed`, `unavailable`, `error`), requested assertion, UTC observation/
attempt time, URL scheme/host/path (query, fragment and userinfo omitted), available
browser/OS environment and error. Missing provenance is null/absent, not invented.
The compatibility `failed` count includes every unsuccessful step; inspect status
to distinguish a negative assertion from missing evidence. Screenshot capture must
produce a file. The runner's saved screenshot supports the step record; the bridge
captures its own model input, so these are not guaranteed to be the same frame.
Memory storage does not admit a skill, prove learning or authorize production.

Before reporting visibility unavailable, inspect the current host's available
browser/vision tools and authorized delegation under existing routing/admission.
Return URL, time, environment, observed assertions, blocked attempts and remaining
unknowns. DOM checks, rendered observations and worker reports are distinct evidence.
Retain authentication, permission, human-verification and anti-bot gates.

Static audit at base `e62e9eb`: the tracked runner consumer is the manual Shorts
`test_layer3_schedule.py --wre-tars` harness. No direct runner/vision import was
found in the scoped `moltbot_bridge/src` or `extensions/reddog` search. The existing
`browser_actions/src/action_router.py` owns DOM/vision routing; the managed
`foundups-wsp` workspace skill supplies guidance, not an execution router.
This correction does not establish installed Red Dog wiring or live vision use.
