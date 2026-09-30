# Video Comments - Public Interface

**Module:** communication/video_comments
**WSP Reference:** WSP 11 (Interface Documentation)
**Status:** Production

## Overview

This module provides autonomous YouTube Studio comment engagement through the `CommentEngagementDAE` class and `execute_skill()` function. All engagement actions (Like, Heart, Reply) are performed via Selenium DOM automation with optional UI-TARS vision verification.

It also provides a lightweight **012 → Comment DAE control plane** for “broadcast” updates (e.g., promote a new channel) stored in module memory and injected into replies probabilistically to avoid spam signatures.

## Contextual Reply Contract

For autonomous replies, the Studio row is the authority for context. The DOM extractor returns `text`, `author_name`, `channel_id`, `video_title`, `video_id`, and `video_url`. `CommentProcessor` forwards the per-row video title and the receiving channel ID to `IntelligentReplyGenerator`.

The default provider order is:

1. LM Studio local model service (normally the general Qwen model; 3-second request bound)
2. Embedded general Qwen resolved by `resolve_general_model_path()`
3. Grok only when `YT_ENABLE_GROK_REPLIES=true` and credentials are configured

RedDog/OpenRouter is not called from this module yet. RedDog's production Fusion calls are autonomous: policy, signed runtime/model bindings, and durable provider-call evidence replace any per-call 012 approval. The currently exposed production runners are typed for repository audits, backend-architect decisions, and bounded artifact generation rather than short-form YouTube replies. Integration should therefore add a provider-neutral reply runner that consumes the daemon's preconfigured policy and emits a content-free call receipt; it must not import the private script bridge.

Every generated reply carries a source receipt. Template, BanterEngine, unknown, or stale sources are not posted by default. Set `YT_ALLOW_GENERIC_REPLY_FALLBACK=true` only to restore the legacy generic-template behavior.

## Primary Interface: execute_skill()

### Function Signature

```python
async def execute_skill(
    channel_id: str,
    max_comments: int = 5,
    do_like: bool = True,
    do_heart: bool = True,
    reply_text: str = "",
    use_vision: bool = True
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `channel_id` | str | - | Yes | YouTube channel ID (e.g., "UC-LSSlOZwpGIRIYihaz8zCw") |
| `max_comments` | int | 5 | No | Maximum comments to process |
| `do_like` | bool | True | No | Enable thumbs up action |
| `do_heart` | bool | True | No | Enable creator heart action |
| `reply_text` | str | "" | No | Reply text (empty = skip reply) |
| `use_vision` | bool | True | No | Enable UI-TARS verification |

### Return Value

```python
{
    'session_id': str,        # Unique session identifier (YYYYMMDD_HHMMSS)
    'channel_id': str,        # YouTube channel ID
    'total_processed': int,   # Total comments processed
    'stats': {
        'comments_processed': int,
        'likes': int,
        'hearts': int,
        'replies': int,
        'errors': int
    },
    'results': [              # Per-comment results
        {
            'comment_idx': int,
            'like': bool,
            'heart': bool,
            'reply': bool,
            'errors': List[str]
        }
    ]
}
```

### Example Usage

```python
from modules.communication.video_comments.skillz.tars_like_heart_reply.comment_engagement_dae import execute_skill

# Full engagement
result = await execute_skill(
    channel_id="UC-LSSlOZwpGIRIYihaz8zCw",
    max_comments=5,
    reply_text="Thanks for watching! 🎌"
)

print(f"Processed: {result['stats']['comments_processed']}")
print(f"Likes: {result['stats']['likes']}")
print(f"Hearts: {result['stats']['hearts']}")
print(f"Replies: {result['stats']['replies']}")
```

## Secondary Interface: CommentEngagementDAE

### Class Signature

```python
class CommentEngagementDAE:
    def __init__(
        self,
        channel_id: str,
        use_vision: bool = True,
        use_dom: bool = True
    )
```

### Methods

#### connect() → bool
Connect to browser and vision system.
```python
await dae.connect()
```

#### navigate_to_inbox() → None
Navigate to YouTube Studio comments inbox.
```python
await dae.navigate_to_inbox()
```

#### get_comment_count() → int
Count visible comments on page.
```python
count = dae.get_comment_count()
```

#### engage_comment(comment_idx, do_like, do_heart, reply_text) → Dict
Engage with a single comment.
```python
result = await dae.engage_comment(
    comment_idx=1,         # 1-based index
    do_like=True,
    do_heart=True,
    reply_text="Thanks!"
)
```

#### engage_all_comments(max_comments, ...) → Dict
Engage with all visible comments.
```python
result = await dae.engage_all_comments(
    max_comments=10,
    do_like=True,
    do_heart=True,
    reply_text="Thanks!",
    refresh_between=True
)
```

#### close() → None
Release resources.
```python
dae.close()
```

### Full Example

```python
from modules.communication.video_comments.skillz.tars_like_heart_reply.comment_engagement_dae import CommentEngagementDAE

async def engage_channel_comments():
    dae = CommentEngagementDAE(
        channel_id="UC-LSSlOZwpGIRIYihaz8zCw",
        use_vision=True,
        use_dom=True
    )
    
    try:
        await dae.connect()
        await dae.navigate_to_inbox()
        
        result = await dae.engage_all_comments(
            max_comments=10,
            do_like=True,
            do_heart=True,
            reply_text="Arigatou! 🇯🇵",
            refresh_between=True
        )
        
        return result
    finally:
        dae.close()
```

## CLI Interface

```bash
# Basic usage
python skillz/tars_like_heart_reply/run_skill.py --max-comments 5

# With reply
python skillz/tars_like_heart_reply/run_skill.py --max-comments 5 --reply-text "0102"

# DOM-only (no vision)
python skillz/tars_like_heart_reply/run_skill.py --max-comments 10 --dom-only

# Skip actions
python skillz/tars_like_heart_reply/run_skill.py --no-like --no-heart

# Custom channel
python skillz/tars_like_heart_reply/run_skill.py --channel UC-XXXXX

# Named channel aliases (resolved via .env)
python skillz/tars_like_heart_reply/run_skill.py --channel move2japan
python skillz/tars_like_heart_reply/run_skill.py --channel undaodu
python skillz/tars_like_heart_reply/run_skill.py --channel ravingantifa

## 012 → Comment DAE Control Plane (Broadcast Updates)

```python
from modules.communication.video_comments.src.commenting_control_plane import (
    load_broadcast,
    set_promo,
    clear_promo,
)

# Enable promotion of a new channel
set_promo(enabled=True, promo_handles=["@MyNewChannel"], promo_message="New channel drop:", updated_by="012")

cfg = load_broadcast()
print(cfg.enabled, cfg.promo_handles, cfg.promo_message)

# Disable/clear
clear_promo()
```
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--channel` | str | `MOVE2JAPAN_CHANNEL_ID` | YouTube channel ID (`UC...`) **or alias**: `move2japan`, `undaodu`, `ravingantifa` |
| `--max-comments` | int | 5 | Max comments to process |
| `--reply-text` | str | "" | Reply text |
| `--no-like` | flag | False | Skip like action |
| `--no-heart` | flag | False | Skip heart action |
| `--dom-only` | flag | False | Disable vision verification |
| `--no-refresh` | flag | False | Don't refresh between batches |

## Error Handling

### Connection Errors
```python
try:
    await dae.connect()
except Exception as e:
    # Chrome not running or wrong port
    print(f"Connection failed: {e}")
```

### Action Errors
Individual action failures are captured in results:
```python
result = await dae.engage_comment(1, reply_text="Hi")
if result['errors']:
    print(f"Errors: {result['errors']}")
```

## Telemetry Output

Session results are saved to:
```
modules/communication/video_comments/memory/engagement_sessions/session_YYYYMMDD_HHMMSS.json
```

## DOM Selectors Reference

```python
SELECTORS = {
    'comment_thread': 'ytcp-comment-thread',
    'like': "ytcp-icon-button[aria-label='Like']",
    'heart': "ytcp-icon-button[aria-label='Heart']",
    'reply_btn': "#reply-button-end button",
    'reply_input': "textarea#textarea",
    'reply_submit': "#submit-button button",
}
```

---

## CommenterClassifier: 0/1/2/3 Classification System

### Overview
Classifies commenters into 4 tiers for skill routing. Used by intelligent_reply_generator.py to select appropriate response strategy.

### Enum: CommenterType
```python
class CommenterType(Enum):
    MAGA_TROLL = 0    # ✊ Previously whacked → Skill 0 (mockery)
    REGULAR = 1       # ✋ Default → Skill 1 (contextual)
    MODERATOR = 2     # 🖐️ Community leader OR anti-MAGA ally → Skill 2 (appreciation + agreement)
```

### Function: get_classifier()
```python
def get_classifier(enable_gemma: bool = False, enable_qwen: bool = False) -> CommenterClassifier
```
Returns singleton classifier instance.

### Method: classify()
```python
def classify(self, user_id: str, comment_text: str, ...) -> Dict
```

**Returns:**
```python
{
    'classification': CommenterType,   # 0/1/2 tier enum
    'confidence': float,               # 0.0-1.0
    'method': str,                     # 'whack_history', 'sentiment_ally', etc.
    'pattern_detected': str | None,    # Pattern that triggered classification
    'is_ally': bool | None,            # True if anti-Trump ally (agreement mode)
}
```

### Classification Priority
1. **MAGA_TROLL (0✊)**: User in whack history (`magadoom_scores.db`) → mockery response
2. **MODERATOR (2🖐️)**: Verified MOD badge OR anti-Trump ally → appreciation/agreement
3. **REGULAR (1✋)**: Default → contextual response

### Database Source
- **Whack History**: `modules/gamification/whack_a_magat/data/magadoom_scores.db` (`whacked_users` table)
- **Moderator Stats**: `modules/communication/chat_rules/data/chat_rules.db` (`moderators` table)

### Ally Detection (within MODERATOR tier)
Anti-Trump patterns trigger `is_ally=True` flag with MODERATOR classification:
- Direct Trump criticism: "isn't qualified", "worst president", "impeach"
- MAGA mockery: "maga cult", "magats", "brainwashed"
- Fascism awareness: "fascist", "authoritarian", "nazi", "1933"
- Scandal refs: "pedo", "epstein", "fake university", "fraud"

### Example Usage
```python
from modules.communication.video_comments.src.commenter_classifier import get_classifier, CommenterType

classifier = get_classifier()
result = classifier.classify(
    user_id="UC123",
    comment_text="Trump isn't qualified to run anything"
)

if result.get('is_ally'):
    # Use agreement mode: agree + amplify + #FFCPLN
    pass
elif result['classification'] == CommenterType.MODERATOR:
    # Standard moderator appreciation
    pass
```

---

**WSP 11 Compliance:** Complete
**Last Updated:** 2026-02-19
