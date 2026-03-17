---
name: external_stream_chat
description: Process and respond to external stream chat messages
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: GENERATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  event: chat_message
---
# External Stream Chat Skill

## Overview
DOM-based engagement with external YouTube Live streams. Enables OpenClaw/AI Overseer to interact in ANY public stream's chat, not just owned channels.

**Key Insight**: For streams we DON'T own, we can't use YouTube API - we use Selenium DOM automation.

## Functionality

### URL-Based Engagement
- Navigate to any YouTube Live URL (e.g., `https://www.youtube.com/watch?v=BXMH9yBck3w`)
- Auto-detect chat input box ("Chat as a subscriber...")
- Send messages via DOM automation
- React with hearts/emojis (`!party` command)

### DOM Selectors (YouTube Live Chat)
```python
SELECTORS = {
    # Chat input field
    'chat_input': "#input.yt-live-chat-text-input-field-renderer",
    'chat_input_alt': "div#input[contenteditable='true']",
    'chat_input_placeholder': "[placeholder*='Chat']",

    # Send button
    'send_button': "#send-button button, yt-button-renderer#send-button",

    # Reactions (hearts, emojis)
    'reaction_panel': "yt-live-chat-action-panel-renderer",
    'heart_button': "[aria-label*='heart'], [aria-label*='Heart']",
    'emoji_picker': "yt-emoji-picker-renderer",

    # Chat messages
    'chat_messages': "yt-live-chat-text-message-renderer",
    'author_name': "#author-name",
    'message_text': "#message",
}
```

### Pixel Offset Strategy
The heart/reaction button is typically 10-50 pixels LEFT of the chat input:
```python
# Get chat input position, offset to find reaction buttons
chat_box = driver.find_element("css selector", SELECTORS['chat_input'])
chat_rect = chat_box.rect

# Reaction panel is left of chat input
reaction_x = chat_rect['x'] - 40  # ~40px left offset
reaction_y = chat_rect['y']
```

### M2M Coordinate Reference Map (Viewport: 1842x1004)

**CRITICAL**: YouTube chat is inside an `iframe` (`id="chatframe"`). DOM tools may not access it directly - coordinate-based clicking is the fallback.

| Element | Coordinates | Notes |
|---------|-------------|-------|
| Chat input field | (1260, 657) | "Chat as a subscriber..." |
| Send button | (1430, 657) | Arrow icon, right of input |
| Heart button | (1432, 657) | Same row as send |

```python
# Absolute coordinate fallback (M2M reference)
ABSOLUTE_COORDS = {
    'chat_input': (1260, 657),
    'send_button': (1430, 657),
    'heart_button': (1432, 657),
    'viewport': (1842, 1004),
}
```

### Iframe Handling

```python
# Strategy 1: Switch to iframe context
chat_frame = driver.find_element("css selector", "iframe#chatframe")
driver.switch_to.frame(chat_frame)
# Now DOM selectors work inside iframe

# Strategy 2: Coordinate fallback (when iframe switch fails)
driver.switch_to.default_content()  # Exit iframe
# Use absolute coordinates from M2M reference
```

### Click Strategy Priority
1. **DOM selectors** (best - reliable, adapts to layout)
2. **Pixel offset** from chat input (good - relative positioning)
3. **Absolute coordinates** (fallback - M2M reference map)

## Invocation

### CLI Usage
```bash
# Watch a stream and engage
python -m ai_overseer.skillz.external_stream_chat.executor --url "https://www.youtube.com/watch?v=BXMH9yBck3w"

# Send a message
python -m ai_overseer.skillz.external_stream_chat.executor --url URL --message "Hello from OpenClaw!"

# Party mode (click hearts continuously)
python -m ai_overseer.skillz.external_stream_chat.executor --url URL --party

# Interactive CLI
python -m ai_overseer.skillz.external_stream_chat.executor --interactive
```

### Python Usage
```python
from ai_overseer.skillz.external_stream_chat import ExternalStreamChat

chat = ExternalStreamChat(url="https://www.youtube.com/watch?v=BXMH9yBck3w")
await chat.connect()
await chat.send_message("Hello from OpenClaw!")
await chat.party()  # Click hearts
await chat.disconnect()
```

## Commands

| Command | Description |
|---------|-------------|
| `!party` | Click heart reaction (uses pixel offset from chat box) |
| `!send <msg>` | Send message to chat |
| `!watch <url>` | Switch to different stream |
| `!status` | Show current stream info |

## Architecture

```
URL Input → Selenium → Find Chat Input → DOM Actions
    ↓                       ↓
   Edge Browser           Chat Input rect.x
    ↓                       ↓
   Navigate              Calculate heart position
    ↓                       ↓
   Wait for chat         Click at (rect.x - 40, rect.y)
```

## Configuration

```yaml
# Environment variables
EXTERNAL_CHAT_BROWSER: edge    # Browser: edge, chrome
EXTERNAL_CHAT_PORT: 9223       # Debug port
EXTERNAL_CHAT_SEND_DELAY: 2.0  # Delay between messages (anti-spam)
EXTERNAL_CHAT_PARTY_INTERVAL: 5.0  # Delay between party clicks
```

## WSP Compliance
- WSP 27: DAE Architecture (sensor: chat messages, actuator: DOM clicks)
- WSP 77: Agent Coordination (OpenClaw integration)
- WSP 91: Observability (engagement telemetry)

## Integration with AI Overseer

This skill is wired into OpenClaw's chat menu:
```
OpenClaw → Chat → External Streams → [URL input]
                                    → Send Message
                                    → Party Mode
                                    → View Chat
```

## Anti-Detection
- Uses human behavior simulation (bezier curves, random delays)
- Imports from `foundups_selenium.src.human_behavior`
- Probabilistic action execution (don't click every time)
- **Coordinate randomization**: +-3px on all coordinate clicks
- **Typing variation**: 50-150ms per character (human-like)
- **Action delays**: Randomized pauses between operations

## Use Cases

1. **Community Engagement**: Engage in ally streams (MIDDLE EAST MULTI-LIVE, etc.)
2. **Cross-Promotion**: Mention foundups.com in relevant chats
3. **Network Building**: Connect with other creators via their live chats
4. **Monitoring**: Watch chat activity on competitor/ally streams
