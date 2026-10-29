# Video Comments - Public Interface

## 2026-10-29 inspected posting contract

The posting wrapper supplies `semantic_context` to `generate_reply_with_source`.
This selects meaning assessment → grounded language draft → final language
review before browser submission; legacy tier/template shortcuts do not select
the answer. Content-neutral cooldown, repetition and recent-reply controls remain.
`ReplyGenerationResult(text, source, theme=None, context=None)` retains the
generation's supplied history, verified memory, assessment and private theme.
Inspection receives that snapshot plus the original author/channel/video.
Explicit and discovered LM Studio writers must match `resolve_general_model_path`
as well as the conservative role filter. This is source routing, not a signed
provider-admission receipt or measured model quality.

`BrowserReplyExecutor.execute_reply(..., expected_comment=..., pre_submit_guard=...)`
requires original full text, author, real `comment_id`, `video_id` and
`_target_channel_id` on the exact Studio origin. It rechecks those identities and
exact entered text in the single submit script. Settled existing reply IDs form
the baseline; verification requires a new reply ID with exact text and the actual
creator channel. Hidden/ambiguous replies and row disappearance are uncertain.
Nested submission remains disabled until equivalent qualification exists.

The existing `CommenterHistoryStore` adds `reply_target_key`, `begin_reply_attempt`,
`finish_reply_attempt`, `get_reply_attempts` and `append_reply_evidence`.
Claims are keyed by receiving channel/video/comment independently of draft text;
unknown and verified reservations block later attempts across restarts. Only a
proven pre-submit failure releases a claim. Verified delivery and its existing
interaction-history row commit together. Unique screenshots, hashes, review and
inspection results remain private evidence. `YT_COMMENT_HISTORY_DB` may select an
absolute shared database across release checkouts; default module memory remains.

**Module:** communication/video_comments
**WSP Reference:** WSP 11 (Interface Documentation)
**Status:** Production

## Overview

This module provides autonomous YouTube Studio comment engagement through the `CommentEngagementDAE` class and `execute_skill()` function. All engagement actions (Like, Heart, Reply) are performed via Selenium DOM automation with optional UI-TARS vision verification.

It also provides a lightweight **012 → Comment DAE control plane** for “broadcast” updates (e.g., promote a new channel) stored in module memory and injected into replies probabilistically to avoid spam signatures.

### Shared 012 manifest context (bounded contract)

`commenting_control_plane.load_broadcast()` first reads the LiveChat queue's
`resolve_manifest_state_path()`, respecting `YT_012_MANIFEST_STATE_FILE` relative
to the checkout (or an absolute configured path). Shared state requires integer
version 1, an active context object, a nonempty allowlisted string-surface list
containing `comments`, a nonempty message of at most 500 characters, and a finite
numeric expiry strictly in the future. Boolean/string/nonfinite expiry is invalid.
Missing, unreadable, invalid, expired or non-comment context leaves the legacy
local broadcast fallback unchanged. Loading does not rewrite either file.
Legacy `set_promo`/`clear_promo` affect only the legacy file; shared context remains
queue-owned. 53 offline reader cases validate this boundary, not live posting.

## Contextual reply contract (PR1478 offline qualification)

The Studio row supplies comment text and video context; the receiving channel
selects personality. Preserve the raw comment when adding semantic guidance,
history and verified VoiceMemory. The same full prompt reaches the local
service and embedded general-language model routes.

The proposed route tries LM Studio with a three-second request bound, then
embedded general Qwen via the existing role resolver. Grok is an explicit
`YT_ENABLE_GROK_REPLIES=true` legacy opt-in. This source configuration is not
current model availability, provider admission or a measured successful call.

`generate_reply()` remains the string-returning interface. The processor uses
`generate_reply_with_source(..., cancel_event=None)` and its immutable
`ReplyGenerationResult(text, source)` snapshot under the same per-instance lock.
The source used for the posting decision and later diagnostics belongs to that
result; `get_last_llm_source()` is a legacy diagnostic, not a cross-thread receipt.
The ten-second await invalidates queued work before provider invocation. It
cannot terminate an already-running provider thread; that thread retains the
lock until it finishes, and its timed-out result is not posted.

The exact allowlist is `CommentProcessor.CONTEXTUAL_PROVIDERS`,
`CONTEXTUAL_SKILLS` and `CONTEXTUAL_STRATEGIES`: recognized providers, supported
skill/provider combinations, and specific content-aware greeting/emoji strategies.
Unknown, malformed or substring-only labels reject. Replacing or discarding a
model draft must discard its provider attribution. This local source snapshot is
not an authenticated provider-call receipt or proof of semantic correctness.
For example, the legacy `skill_0:grok_greeting` name identifies a local
content-matched response-pool strategy; it does not establish a Grok call.
`YT_ALLOW_GENERIC_REPLY_FALLBACK` explicitly restores generic legacy behavior;
it does not prove grounded generation. Grok opt-in is checked at the actual call.

`reply_context.py` owns pure prompt/personality assembly;
`comment_row_context.py` owns row extraction and small context adapters. No new
provider, store or scheduler is introduced. Missing or ambiguous row metadata
must remain absent rather than falling back to another video's inbox context.

This module does not acquire a RedDog/OpenRouter reply grant. The original PR's
provider-neutral reply-runner proposal remains a future integration requiring
current route/owner discovery and existing authenticated admission, budget and
call-evidence contracts. It is not permission to use a private script bridge or
a promise that signed inputs are presently configured.

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
