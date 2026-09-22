# Browser Actions - Interface Specification

**WSP 11 Compliance:** In Progress
**Version:** 0.1.0

---

## Public API

### ActionRouter

Routes actions to the optimal driver.

```python
class ActionRouter:
    """Routes browser actions to optimal driver (Selenium or UI-TARS)."""
    
    def __init__(
        self,
        selenium_driver: FoundUpsDriver = None,
        vision_driver: UITarsBridge = None,
        profile: str = None
    ) -> None:
        """Initialize router with drivers.
        
        Args:
            selenium_driver: FoundUpsDriver instance (or creates new)
            vision_driver: UITarsBridge instance (or creates new)
            profile: Browser profile to use
        """
    
    async def execute(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> ActionResult:
        """Execute an action via appropriate driver.
        
        Args:
            action: Action name (e.g., 'like_comment', 'navigate')
            params: Action parameters
            
        Returns:
            ActionResult with success status
        """
    
    def get_driver_for_action(self, action: str) -> str:
        """Determine which driver handles an action.
        
        Returns:
            'selenium' or 'vision'
        """
```

### YouTubeActions

YouTube-specific browser actions.

```python
class YouTubeActions:
    """YouTube browser automation actions."""
    
    def __init__(self, profile: str = 'youtube_move2japan') -> None:
        """Initialize with browser profile."""
    
    async def like_comment(
        self,
        video_id: str,
        comment_id: str
    ) -> ActionResult:
        """Like a YouTube comment (via UI-TARS vision).
        
        Args:
            video_id: YouTube video ID
            comment_id: Comment thread ID
            
        Returns:
            ActionResult with like status
        """
    
    async def reply_to_comment(
        self,
        video_id: str,
        comment_id: str,
        text: str
    ) -> ActionResult:
        """Reply to a YouTube comment (via API).
        
        Args:
            video_id: YouTube video ID
            comment_id: Comment thread ID
            text: Reply text
            
        Returns:
            ActionResult with reply status
        """
    
    async def like_and_reply(
        self,
        video_id: str,
        comment_id: str,
        text: str
    ) -> ActionResult:
        """Like and reply to a comment in single session.
        
        Args:
            video_id: YouTube video ID
            comment_id: Comment thread ID
            text: Reply text
            
        Returns:
            ActionResult with both actions
        """
    
    async def subscribe_channel(
        self,
        channel_id: str
    ) -> ActionResult:
        """Subscribe to a YouTube channel (via UI-TARS vision)."""
    
    async def navigate_to_video(
        self,
        video_id: str
    ) -> ActionResult:
        """Navigate to a video (via Selenium)."""
```

### LinkedInActions

`send_connection_request(..., dry_run=True)` previews the existing role policy
after navigation/metadata retrieval, before request bookkeeping or simulation.
Its `LinkedInActionResult.details` contains `dry_run`, `policy_reason`,
`matched_allow`, `matched_deny`, `profile`; it omits `request_status`. Allowed
policy returns success, denied policy returns failure. Neither certifies quota,
deduplication or authority. Constructor/browser access remains separate.
Missing-metadata/manager early errors retain their existing shapes. Explicit
live calls retain their existing request-status/results contract.
See [verified scope](../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-connection-policy-preview--2026-09-22).

```python
class LinkedInActions:
    """LinkedIn browser automation actions."""
    
    async def post_to_company(
        self,
        company_id: str,
        text: str,
        image_path: Optional[str] = None
    ) -> ActionResult:
        """Post to a LinkedIn company page."""
    
    async def comment_on_post(
        self,
        post_id: str,
        text: str
    ) -> ActionResult:
        """Comment on a LinkedIn post."""
    
    async def like_post(
        self,
        post_id: str
    ) -> ActionResult:
        """Like a LinkedIn post."""

    async def run_digital_twin_flow(
        self,
        comment_text: str,
        repost_text: str,
        schedule_date: str,
        schedule_time: str,
        mentions: Optional[List[str]] = None,
        identity_cycle: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> ActionResult:
        """Run LinkedIn layered flow (L0-L3) with explicit orchestration inputs."""
```

### XActions

```python
class XActions:
    """X/Twitter browser automation actions."""
    
    async def post_tweet(
        self,
        text: str,
        image_path: Optional[str] = None
    ) -> ActionResult:
        """Post a tweet."""
    
    async def reply_to_tweet(
        self,
        tweet_id: str,
        text: str
    ) -> ActionResult:
        """Reply to a tweet."""
    
    async def like_tweet(
        self,
        tweet_id: str
    ) -> ActionResult:
        """Like a tweet."""
    
    async def retweet(
        self,
        tweet_id: str
    ) -> ActionResult:
        """Retweet a tweet."""
```

---

## Action Classification

### Simple Actions (→ Selenium)

| Action | Description |
|--------|-------------|
| `navigate` | Navigate to URL |
| `click_by_xpath` | Click element by XPath |
| `click_by_id` | Click element by ID |
| `type_text` | Type into element |
| `get_element_text` | Read element text |

### Vision Actions (→ UI-TARS)

| Action | Description |
|--------|-------------|
| `like_comment` | Like any comment (vision-based) |
| `find_by_description` | Find element by description |
| `fill_form_smart` | Fill form intelligently |
| `verify_state` | Verify UI state |
| `click_by_description` | Click by element description |

---

## Events (Telemetry)

| Event | Payload |
|-------|---------|
| `action_routed` | `{action, driver, params}` |
| `action_complete` | `{action, driver, success, duration_ms}` |
| `action_failed` | `{action, driver, error, fallback_attempted}` |
| `driver_fallback` | `{from_driver, to_driver, reason}` |

---

## Usage Examples

### YouTube Comment Engagement

```python
from modules.infrastructure.browser_actions.src.youtube_actions import YouTubeActions

youtube = YouTubeActions(profile='youtube_move2japan')

# Engage with a comment
result = await youtube.like_and_reply(
    video_id="dQw4w9WgXcQ",
    comment_id="UgxAbC123",
    text="Thanks for watching! Check out more videos on the channel 🎌"
)

print(f"Success: {result.success}")
print(f"Like: {result.like_result.success}")
print(f"Reply: {result.reply_result.success}")
```

### Multi-Platform Posting

```python
from modules.infrastructure.browser_actions.src import (
    YouTubeActions, LinkedInActions, XActions
)

# Post announcement across platforms
message = "New video coming tomorrow! 🎥"

x = XActions(profile='x_foundups')
linkedin = LinkedInActions(profile='linkedin_foundups')

await x.post_tweet(message)
await linkedin.post_to_company('foundups-company', message)
```

---

**Interface Version:** 0.1.0
**WSP 11 Compliance:** Structure Complete, Implementation Pending



