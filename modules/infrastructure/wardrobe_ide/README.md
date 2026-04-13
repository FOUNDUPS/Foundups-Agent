# Wardrobe IDE - Browser Interaction Recording & Replay System

**Version:** 0.0.1
**Status:** Foundation Layer PoC

## Overview

Wardrobe IDE is a browser interaction recording and replay system that enables:
- **Recording** short browser interactions (15-30 seconds) as reusable "skills"
- **Replaying** those skills later via Selenium or Playwright
- **Storing** skills in a searchable JSON-based library

This is the **foundation layer** - no AI selection logic yet, just clean abstractions + basic UX.

## Architecture

```
Wardrobe IDE
├── Backends
│   ├── Playwright (primary recorder)
│   └── Selenium (replay only)
├── Skills Store (JSON-based)
└── Recorder (orchestration + CLI)
```

### Key Components

**1. WardrobeSkill (Dataclass)**
```python
@dataclass
class WardrobeSkill:
    name: str
    backend: Literal["playwright", "selenium"]
    steps: list[dict]  # [{action, selector, text, timestamp}]
    created_at: datetime
    meta: dict  # {target_url, tags, notes}
```

**2. Backends**
- **PlaywrightBackend**: Records and replays browser interactions
- **SeleniumBackend**: Replays recorded skills (recording stubbed)

**3. Skills Store**
- JSON files: `skills/<slugified_name>.<backend>.json`
- Index file: `skills/skills_index.json`
- Functions: `save_skill()`, `load_skill()`, `list_skills()`

**4. Recorder (Orchestration)**
- `record_new_skill()`: Record new skill
- `replay_skill_by_name()`: Replay existing skill
- `show_skills_library()`: List all skills

## Installation

### Prerequisites

```bash
pip install playwright selenium pytest
playwright install chromium
```

### Setup

The module is ready to use - no additional setup required.

## Usage

### Python API

```python
from modules.infrastructure.wardrobe_ide import record_new_skill, replay_skill_by_name

# Record a skill
skill = record_new_skill(
    name="YouTube Like",
    target_url="https://studio.youtube.com/...",
    backend="playwright",
    duration_seconds=20,
    tags=["youtube", "engagement"]
)

# Replay the skill
replay_skill_by_name("YouTube Like")

# Replay with different backend
replay_skill_by_name("YouTube Like", backend="selenium")
```

### CLI

```bash
# Record a skill
python -m modules.infrastructure.wardrobe_ide record \
    --name "yt_like_and_reply" \
    --url "https://studio.youtube.com/..." \
    --backend playwright \
    --duration 20 \
    --tags youtube engagement

# Replay a skill
python -m modules.infrastructure.wardrobe_ide replay \
    --name "yt_like_and_reply"

# List all skills
python -m modules.infrastructure.wardrobe_ide list

# List skills by backend
python -m modules.infrastructure.wardrobe_ide list --backend playwright

# Import a downloaded skill (e.g., from the Chrome extension)
python -m modules.infrastructure.wardrobe_ide import \
    --file "~/Downloads/yt_like_heart_reply.json" \
    --backend selenium \
    --name "yt_like_heart_reply"

# Bulk-import everything in Downloads (optional helper)
python -m modules.infrastructure.wardrobe_ide.import_from_downloads --pattern "*.json" --backend selenium --delete

# Watch for YT Studio recordings and auto-import (Ctrl+C to stop)
python -m modules.infrastructure.wardrobe_ide.watch_yt_downloads --pattern "yt_studio_*.json" --backend selenium --delete
```

## Recording Process

1. **Start recording**: Browser opens to target URL
2. **Interact**: Click buttons, type text (JavaScript listeners capture everything)
3. **Auto-stop**: Recording stops after specified duration
4. **Save**: Skill is saved to library with all captured steps

## Replay Process

1. **Load skill**: Read from JSON file
2. **Navigate**: Go to `skill.meta["target_url"]`
3. **Execute steps**: For each step:
   - `click`: `page.click(selector)`
   - `type`: `page.fill(selector, text)`
4. **Verify**: Visual confirmation (3-second delay)

## Skill Format

```json
{
  "name": "YouTube Like",
  "backend": "playwright",
  "created_at": "2024-12-10T12:00:00",
  "steps": [
    {
      "action": "click",
      "selector": "ytcp-icon-button[aria-label='Like']",
      "timestamp": 2.5,
      "target_tag": "YTCP-ICON-BUTTON",
      "target_text": ""
    },
    {
      "action": "type",
      "selector": "#comment-input",
      "text": "Great video!",
      "timestamp": 5.0
    }
  ],
  "meta": {
    "target_url": "https://studio.youtube.com/...",
    "tags": ["youtube", "engagement"],
    "notes": "Like and comment on first video",
    "step_count": 2
  }
}
```

## Testing

```bash
# Run unit tests
pytest modules/infrastructure/wardrobe_ide/tests/test_wardrobe_ide_basic.py -v
```

Tests use mocking to avoid launching actual browsers.

## Configuration

Environment variables (all optional):

```bash
# Default backend (default: "playwright")
export WARDROBE_DEFAULT_BACKEND=playwright

# Recording duration (default: 15 seconds)
export WARDROBE_RECORD_DURATION=15

# Skills storage directory
export WARDROBE_SKILLS_DIR=/path/to/skills

# Browser settings
export WARDROBE_HEADLESS=false  # Run browser in headless mode
export WARDROBE_SLOW_MO=0       # Slow down operations (ms)

# Attach Selenium to an existing signed-in Chrome (recommended for YouTube Studio)
export WARDROBE_CHROME_PORT=9222
export WARDROBE_CHROME_USER_DATA_DIR=O:\\Foundups-Agent\\modules\\platform_integration\\browser_profiles\\youtube_move2japan\\chrome

# Where to scan for downloaded skills (for import_from_downloads helper)
export WARDROBE_DOWNLOADS_DIR=C:\\Users\\user\\Downloads
```

## Integration with Existing Infrastructure

### Importing Skills from the Chrome Extension
- Use the CLI import command to pull a downloaded JSON into the Wardrobe library:
  ```bash
  python -m modules.infrastructure.wardrobe_ide import --file ~/Downloads/<skill>.json --backend selenium
  ```
- The importer:
  - Maps `chrome_extension` backend → `selenium` by default
  - Preserves tags/notes/target_url
  - Stores source file path for traceability

### BrowserManager Integration (TODO)

### BrowserManager Integration (TODO)

```python
# Current: Standalone Chrome
driver = webdriver.Chrome()

# Future: Integrate with existing BrowserManager
from modules.infrastructure.foundups_selenium.src.browser_manager import BrowserManager

browser_mgr = BrowserManager()
driver = browser_mgr.get_browser(
    browser_type="chrome",
    profile_name="youtube_move2japan"
)
```

### Action Router Integration (TODO)

```python
# Future: Use existing action router for multi-driver support
from modules.infrastructure.browser_actions.src.action_router import ActionRouter

router = ActionRouter()
router.execute_action(
    action_type="click",
    driver_type="PLAYWRIGHT",
    selector="#button"
)
```

## Future Enhancements (Phase 8+)

### Chrome Extension / Popup (TODO)
- Lightweight Chrome extension for recording trigger
- Desktop popup UI: name skill + start/stop
- Real-time preview of captured steps

### 012 ↔ 0102 Messaging (TODO)
- Accept tasks triggered remotely by 0102
- Example: "run skill yt_like_and_reply on host PC"

### Skill Catalog Integration (TODO)
- Searchable registry by tags, domain, app
- Skill versioning and history
- Export/import skill libraries

### AI Backend Selection (TODO)
```python
# Placeholder for future AI-based backend selection
def get_backend(name: str) -> WardrobeBackendBase:
    # TODO: Plug in 0102-based backend selection here
    #       (e.g. choose best backend per domain/skill using AI/LLM)
    ...
```

### Advanced Recording Features (TODO)
- Screenshot capture during record/replay
- Better selector strategies (data-testid, aria-label priority)
- Smart timing replay (use recorded timestamps)
- Validation/verification after replay

## Known Limitations

1. **Selector Strategy**: Currently uses basic CSS selectors (ID/class/nth-child)
   - May be fragile for dynamic UIs
   - TODO: Implement data-testid and aria-label priority

2. **Timing**: Sequential replay with fixed delays
   - TODO: Use recorded timestamps for precise timing

3. **Selenium Recording**: Not implemented (Playwright only)
   - Selenium backend is replay-only
   - TODO: Add Selenium recording if needed

4. **Verification**: No automatic verification after replay
   - TODO: Add DOM state checking or visual diff

## WSP Compliance

- **WSP 3**: Module Organization - Proper infrastructure domain placement
- **WSP 11**: Interface Protocol - `INTERFACE.md` (public API)
- **WSP 49**: Module Structure - README, tests, src/ layout
- **WSP 72**: Module Independence - Minimal external dependencies

## File Structure

```
modules/infrastructure/wardrobe_ide/
├── __init__.py                  # Package exports
├── __main__.py                  # CLI entry point
├── README.md                    # This file
├── INTERFACE.md                 # Public API (WSP 11)
├── requirements.txt             # Dependencies
├── backends/
│   ├── __init__.py              # Backend interface + resolver
│   ├── playwright_backend.py   # Playwright implementation
│   └── selenium_backend.py     # Selenium implementation
├── src/
│   ├── __init__.py              # Core exports
│   ├── skill.py                 # WardrobeSkill dataclass
│   ├── config.py                # Configuration
│   ├── recorder.py              # Orchestration + Python API
│   └── skills_store.py          # JSON-based storage
├── skills/                      # Skills library (created at runtime)
│   ├── skills_index.json        # Skills index
│   └── *.playwright.json        # Individual skill files
└── tests/
    └── test_wardrobe_ide_basic.py  # Unit tests
```

## License

Part of the FoundUps Agent framework.

---

**Maintained by:** 0102
**Created:** 2024-12-10
**Status:** Foundation layer complete, ready for extension
