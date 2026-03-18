---
name: unified_metadata_updater
description: Unified metadata updater for all stream platforms
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: ORCHESTRATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  event: schema_change
---
# Unified Metadata Updater Skillz

## Purpose
Unified skill that lets agents choose the best method to update YouTube metadata.

## Methods Available

| Method | When to Use | Speed | Reliability |
|--------|-------------|-------|-------------|
| **API** | Stream is LIVE | Fast | High (requires OAuth) |
| **DOM-Live** | Stream is LIVE, API fails | Medium | Medium |
| **DOM-Manage** | Past broadcasts, any time | Medium | High |

## Agent Decision Flow
```
Is stream live?
  YES → Try API first → Falls back to DOM-Live
  NO  → Use DOM-Manage

Is title update needed?
  Check urgency >= 8 (BREAKING, LIVE) → MAJOR EVENT → Update title

Is description update needed?
  Top news changed? → Update description for SEO
```

## CLI Commands
```bash
# Auto-select best method
python executor.py auto --title "..." --description "..."

# Force specific method
python executor.py api --title "..."           # YouTube API
python executor.py dom-live --title "..."      # Live Dashboard DOM
python executor.py dom-manage --title "..."    # Manage page DOM

# Clickbait + SEO (auto method)
python executor.py clickbait

# Major event only (title change)
python executor.py major-event

# SEO refresh (description only)
python executor.py seo-refresh
```

## Integration Points

### 1. YouTube API (Primary for LIVE)
- Module: `youtube_broadcast_manager.py`
- Function: `update_current_broadcast(title, description)`
- Requires: OAuth token for antifaFM channel

### 2. DOM Live Dashboard (Fallback for LIVE)
- Module: `stream_metadata_editor/executor.py`
- Function: `edit_stream_metadata(title, description)`
- Requires: Chrome on port 9222

### 3. DOM Manage Page (Past broadcasts)
- Module: `manage_metadata_editor/executor.py`
- Function: `edit_broadcast_metadata(index, title, description)`
- Requires: Chrome on port 9222

## OBS Note
OBS WebSocket cannot update YouTube metadata directly.
OBS only controls:
- Streaming start/stop
- Scene switching
- Source visibility
- Recording

For metadata, use this unified skill instead.

## WSP Compliance
- WSP 27: Universal DAE Architecture
- WSP 77: Agent Coordination (method selection)
- WSP 103: CLI Interface Standard
