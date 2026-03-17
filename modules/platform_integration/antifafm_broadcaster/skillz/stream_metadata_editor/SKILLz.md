---
name: stream_metadata_editor
description: Stream metadata update automation
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: EXECUTION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  event: metadata_change
---
# YouTube Stream Metadata Editor Skillz

## Purpose
Edit live stream metadata (title, description, settings) via YouTube API or DOM automation.

## Methods
1. **API (Primary)** - Uses YouTube Data API via youtube_broadcast_manager.py
2. **DOM (Fallback)** - Uses Selenium to edit YouTube Studio

## OpenClaw/IronClaw Integration
```bash
# CLI commands for agent invocation
python executor.py api [title]      # API: Update title (or clickbait if no title)
python executor.py clickbait        # API: Generate clickbait title + news description
python executor.py m2m              # DOM: Apply M2M description
python executor.py title <text>     # DOM: Set stream title
```

## Skill Entry Points
- `api_update_metadata(title, description)` - Direct API update
- `api_clickbait_update(include_news)` - Generate + apply clickbait
- `edit_stream_metadata(title, description)` - DOM-based update

## Trigger
- `/stream-edit` or menu option in antifaFM broadcaster
- Called after Go Live to configure stream metadata

## DOM Elements (YouTube Studio Live Dashboard)

### Edit Button
```
Selector: ytcp-button#edit-button button
Position: top=297px, left=616px
Action: Click to open edit dialog
```

### Title Field
```
Selector: ytcp-video-title#title-wrapper #title-textarea
Position: top=132px, left=418px
Action: Clear and set title
```

### Description Field
```
Selector: ytcp-video-description#description-wrapper #description-textarea
Position: top=235px, left=418px
Action: Clear and set description with M2M hashtags
```

### Save Button
```
Selector: ytcp-button#save-button button
Position: top=417px, left=988px
Action: Click to save changes
```

### Customization Tab
```
Selector: li#customization
Position: top=164px, left=126px
Action: Click to show customization options
```

### Customization Checkboxes
- Live Chat: `#chat-enabled-checkbox` (default: ON)
- Chat Replay: `#chat-replay-checkbox` (default: ON)
- Chat Summary: `#chat-summary-opt-out-checkbox` (default: ON)
- Leaderboard: `#viewer-leaderboard-opt-out-checkbox` (default: ON)

### Participation Modes (radio buttons)
- Anyone: `#all-users-mode-radio-button` (default: ON)
- Subscribers: `#subscribers-only-mode-radio-button`
- Approved Users: `#invite-mode-radio-button`

## M2M Description Template
```
antifaFM - 24/7 Antifascist Radio

Live stream powered by FoundUps AI automation.

#antifaFM #LiveRadio #FoundUps #AI #Automation #0102 #pAVS
#AntifascistMusic #Resistance #CommunityRadio #OpenSource

LINKS:
- FoundUps: https://foundups.com
- GitHub: https://github.com/foundups

Powered by 0102 DAE Network

NOTE: ASCII-safe (no emoji) to avoid Windows cp932 encoding errors.
```

## Execution Flow
1. Navigate to live stream dashboard (already there after Go Live)
2. Click Edit button
3. Wait for dialog
4. Set title
5. Set description with M2M hashtags
6. Click Customization tab
7. Verify checkbox defaults
8. Click Save
9. Wait for save confirmation

## WSP Compliance
- WSP 27: Universal DAE Architecture
- WSP 84: Code Reuse (youtube_go_live patterns)
