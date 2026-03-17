---
name: manage_metadata_editor
description: Manage stream metadata editing interface
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: MANAGEMENT
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  manual
---
# YouTube Manage Metadata Editor Skillz

## Purpose
Edit past/scheduled broadcast metadata (title, description) via YouTube Studio Manage page DOM automation.

## Difference from stream_metadata_editor
- **stream_metadata_editor**: Edits LIVE stream via API or Live Dashboard
- **manage_metadata_editor**: Edits ANY broadcast via Manage page DOM (works for past streams too)

## CLI Commands
```bash
# List recent broadcasts
python executor.py list

# Edit specific broadcast by index (0 = most recent)
python executor.py edit <index> --title "New Title" --description "New desc"

# Edit most recent broadcast
python executor.py recent --title "New Title"

# Apply clickbait + M2M to most recent
python executor.py clickbait

# Get shareable link for a broadcast
python executor.py link <index>
python executor.py link 0              # Most recent
```

## DOM Navigation Flow

### Step 1: Navigate to Manage page
```
URL: https://studio.youtube.com/channel/UCVSmg5aOhP4tnQ9KFUg97qA/livestreaming/manage
Note: This URL navigates directly to the Manage tab (no need to click tab)
```

### Step 2: Find video row and click Options button (three dots)
```
Selector: ytcp-video-row div#hover-items ytcp-icon-button.open-menu-button
Position: top=243px, left=690px
Action: Hover over row first to reveal Options button (three dots)
Note: Only appears on mouse hover at the row location
```

### Step 2b: Options Menu Items (persistent menu after click)
```
Menu ID: ytcp-text-menu#video-inline-actions-menu

Option 0 - Edit title and description:
  Selector: tp-yt-paper-item#text-item-0 yt-formatted-string.item-text
  Text: "Edit title and description"

Option 1 - Get shareable link:
  Selector: tp-yt-paper-item#text-item-1 div.right-container
  Text: "Get shareable link"
  Position: top=279px, left=280px

Option 3 - Brainstorm video ideas (Gemini/Inspiration tab):
  Selector: tp-yt-paper-item#text-item-3 yt-formatted-string.item-text
  Text: "Brainstorm video ideas"
  Position: top=343px, left=280px
  Notes:
    - Opens YouTube's "Inspiration tab" (Gemini-powered)
    - Generates ideas, titles, thumbnails, outlines
    - Desktop only, English only
    - AI-generated content may be inaccurate
    - Not all creators have access
    - Could be useful for clickbait title generation

Option 4 - Delete forever:
  Selector: tp-yt-paper-item#text-item-4 div.right-container
  Text: "Delete forever"
  Position: top=375px, left=280px
  WARNING: DESTRUCTIVE - Only use if 012 explicitly instructs!
```

### Step 3: Click "Edit title and description"
```
Selector: ytcp-text-menu tp-yt-paper-item#text-item-0 yt-formatted-string.item-text
Position: top=247px, left=533px
Text: "Edit title and description"
```

### Step 4: Edit title
```
Selector: ytcp-video-list-cell-video-edit-dialog #title-input #textbox
Position: top=274px, left=478px
Action: Clear and type new title
Attributes: contenteditable="true", role="textbox"
```

### Step 5: Edit description
```
Selector: ytcp-video-list-cell-video-edit-dialog #description-textarea #textbox
Position: top=393px, left=478px
Action: Clear and type new description
Attributes: contenteditable="true", role="textbox"
```

### Step 6: Save
```
Selector: ytcp-video-list-cell-video-edit-dialog #save-button button
Position: top=459px, left=811px
```

## WSP Compliance
- WSP 27: Universal DAE Architecture
- WSP 84: Code Reuse (youtube_go_live patterns)
- WSP 103: CLI Interface Standard
