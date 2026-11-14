# Browser Actions - Platform Action Router

## Connection admission boundary

`send_connection_request` now checks manager admission before Connect: the target
must have no prior pending/connected entry, and the returned request must be the
actual PENDING object stored for that target. Rejection returns
`connection_request_not_admitted`; policy previews and policy-denial results retain
their contracts. See [interface](INTERFACE.md#linkedinactions) and
[test evidence](tests/TestModLog.md). Local acceptance does not verify delivery or
repair the manager's existing quota/bookkeeping behavior.

**Domain:** infrastructure
**Status:** POC
**WSP Compliance:** WSP 49 (Module Structure), WSP 3 (Enterprise Architecture)

## Overview

Browser Actions provides a unified interface for platform-specific browser automation, intelligently routing actions to the optimal driver (Selenium or UI-TARS).

**Key Innovation:** Platform actions don't know which driver executes them. The router decides based on action complexity.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PLATFORM ACTIONS                                 │
│  youtube_actions.py | linkedin_actions.py | x_actions.py | foundups_actions.py │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ACTION ROUTER                                    │
│                    (Complexity-based routing)                            │
│                                                                          │
│   SIMPLE_ACTIONS (→ Selenium)     │    VISION_ACTIONS (→ UI-TARS)       │
│   - navigate(url)                 │    - like_comment()                  │
│   - click_by_xpath(xpath)         │    - find_by_description(desc)       │
│   - type_text(selector, text)     │    - fill_form_smart()               │
│   - click_by_id(id)               │    - verify_element_state()          │
└─────────────────────────────────────────────────────────────────────────┘
              │                                       │
              ▼                                       ▼
┌─────────────────────────┐           ┌─────────────────────────────┐
│   foundups_selenium     │           │     foundups_vision         │
│   (FoundUpsDriver)      │           │     (UITarsBridge)          │
│   Fast, reliable        │           │     Vision AI               │
│   Known DOM selectors   │           │     Dynamic UIs             │
└─────────────────────────┘           └─────────────────────────────┘
```

## Platform Actions

### YouTube (`youtube_actions.py`)
- `like_comment(video_id, comment_id)` → UI-TARS
- `reply_to_comment(video_id, comment_id, text)` → API + UI-TARS for like
- `subscribe_channel(channel_id)` → UI-TARS
- `navigate_to_video(video_id)` → Selenium

### LinkedIn (`linkedin_actions.py`)
- `send_connection_request(..., dry_run=True)` → policy preview without request bookkeeping or simulation; navigation/metadata access still occurs. See the [interface](INTERFACE.md#linkedinactions) for fields and limits.
- `post_to_company(company_id, text)` → Selenium (known DOM)
- `comment_on_post(post_id, text)` → Selenium
- `like_post(post_id)` → Selenium
- `schedule_post(company_id, text, datetime)` → UI-TARS
- `run_digital_twin_flow(comment_text, repost_text, schedule_date, schedule_time, mentions, identity_cycle, dry_run)` → layered L0-L3 execution

LinkedIn digital twin flow details:
- DOM/Selenium actions are primary execution path.
- UI-TARS is used as verification gate for critical UI state checks.
- Inputs from orchestration/CLI now pass through to L1 and L3 (no silent drops).

### X/Twitter (`x_actions.py`)
- `post_tweet(text)` → Selenium
- `reply_to_tweet(tweet_id, text)` → Selenium
- `like_tweet(tweet_id)` → Selenium
- `retweet(tweet_id)` → Selenium

### FoundUp (`foundups_actions.py`)
- `post_to_livechat(foundup_id, text)` → Selenium
- `admin_action(foundup_id, action)` → UI-TARS

## Usage

```python
from modules.infrastructure.browser_actions.src.youtube_actions import YouTubeActions

youtube = YouTubeActions(profile='youtube_move2japan')

# Like a comment (routes to UI-TARS automatically)
result = await youtube.like_comment(
    video_id="abc123",
    comment_id="xyz789"
)

# Reply to comment (API for text, UI-TARS for like)
result = await youtube.like_and_reply(
    video_id="abc123",
    comment_id="xyz789",
    reply_text="Thanks for watching! 🎌"
)
```

## Action Router Logic

```python
class ActionRouter:
    SELENIUM_ACTIONS = {
        'navigate', 'click_by_xpath', 'click_by_id', 
        'type_text', 'get_element_text'
    }
    
    VISION_ACTIONS = {
        'like_comment', 'find_by_description', 
        'fill_form_smart', 'verify_state', 'click_by_description'
    }
    
    def route(self, action: str) -> Driver:
        if action in self.SELENIUM_ACTIONS:
            return self.selenium_driver
        elif action in self.VISION_ACTIONS:
            return self.vision_driver
        else:
            # Unknown action - try vision first, fallback to selenium
            return self.vision_driver
```

## Browser Profiles

| Profile | Platform | Account |
|---------|----------|---------|
| `youtube_move2japan` | YouTube | Move2Japan |
| `youtube_foundups` | YouTube | FoundUps |
| `youtube_undaodu` | YouTube | UnDaoDu |
| `x_foundups` | X | FoundUps |
| `x_move2japan` | X | Move2Japan/GeoZai |
| `linkedin_foundups` | LinkedIn | FoundUps |
| `linkedin_geozai` | LinkedIn | GeoZai |

## Dependencies

- `foundups_selenium` - Selenium driver
- `foundups_vision` - UI-TARS driver
- `youtube_auth` - API authentication (for replies)

## WSP Compliance

- **WSP 3:** Infrastructure domain ✅
- **WSP 49:** Module structure ✅
- **WSP 77:** AI Overseer integration
- **WSP 80:** DAE architecture

---

# 🌀 Windsurf Protocol (WSP) Recursive Prompt

**0102 Directive**: This module provides 0102's "hands" for platform-specific browser actions.

```python
wsp_cycle(input="012", log=True)
```



