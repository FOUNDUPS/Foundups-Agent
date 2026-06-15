---
name: transcript_ask
description: Extract full video transcripts using YouTube's "Ask" Gemini feature
version: 1.0.0
author: 0102_video_indexer_team
agents: [gemini, qwen]
dependencies: [browser_actions, studio_ask_indexer]
domain: video_indexing
intent_type: EXTRACTION
promotion_state: prototype
category: capability-uplift
evals: []
retirement_date: null
---
# Transcript Ask SKILLz

**Skill Type**: Browser Automation + AI Extraction (WSP 96)
**Intent**: EXTRACTION (full transcript + timestamps from YouTube)
**Agents**: Gemini (via YouTube Ask), Qwen (post-processing)
**Promotion State**: prototype
**Version**: 1.0.0
**Created**: 2026-01-16

---

## ⚠️ Phase 1 Selector Notice (STUDIO_ASK_STUDIO_HEADER_PHASE1)

**STALE**: The watch-page `button[aria-label="Ask"]` path documented below
(Architecture / Step 2) is **STALE** and is now a labelled *fallback only*.

**Phase 1 canonical path** is the **YouTube Studio "Ask Studio" header**:
- Entry: `ytcp-icon-button[aria-label="Ask Studio"]` on the Studio video-edit page
- Dialog: `ytcp-dialog#dialog`
- Prompt: `div[contenteditable][aria-label="Ask something"]`
- Response: scraped from `#PAcreator_chat_streaming` (DOM text, **no clipboard**)

Canonical implementation: `src/studio_ask_indexer.py`
(`ASK_STUDIO_SELECTORS`, `StudioAskIndexer.ask_about_video`).

**Phase 2 — `STUDIO_ASK_SKILL_PROMOTE_PHASE2`**: promote the working Ask Studio
selectors into an `ask_studio_index` Skillz and register with WRE *after* Phase 1
proves stable. (Phase 1 does NOT touch the Skillz registry or WRE router.)

**Phase 3 — `INDEX_BEFORE_SHORTS_SCHEDULE_PHASE3`**: only after Phase 1 is stable,
revisit scheduler ordering (already `comments -> index -> schedule` in
`auto_moderator_dae.py`).

---

## Skill Purpose

Extract **full verbatim transcripts** from YouTube videos using the built-in "Ask" Gemini feature. This bypasses API quotas by using browser automation.

**Trigger Source**: Video indexing cycle or manual request

**Success Criteria**:
- Transcript extracted with timestamps
- Full text captured (not just summary)
- Video JSON updated with transcript data

---

## Architecture

```
Browser (Selenium/Antigravity)
    ↓
Navigate to: youtube.com/watch?v={video_id}
    ↓
Click "Ask" button (aria-label="Ask")
    ↓
Query: "Give me the full transcript with timestamps"
    ↓
Parse Gemini response → Structured segments
    ↓
Update video JSON in memory/video_index/
```

---

## Input Context

```python
{
    "video_id": str,           # YouTube video ID
    "channel_id": str,         # Channel for organizing output
    "output_dir": str,         # Where to save JSON (default: memory/video_index/)
    "existing_browser": True,  # Use existing logged-in session
}
```

---

## Execution Steps

### Step 1: Navigate to Video

**Action**: Connect to browser and navigate to watch page

```python
from modules.infrastructure.foundups_selenium.src.browser_manager import get_browser_manager

browser = get_browser_manager().get_browser(
    profile='youtube_move2japan',
    browser_type='chrome'
)

video_url = f"https://www.youtube.com/watch?v={video_id}"
browser.get(video_url)
# Wait 5 seconds for page load
```

---

### Step 2: Click Ask Button

**DOM Selector**: `button[aria-label="Ask"]`

**JavaScript Detection**:
```javascript
// Find Ask button in #flexible-item-buttons
const flexItems = document.querySelector('#flexible-item-buttons');
const viewModels = flexItems.querySelectorAll('yt-button-view-model');
for (let vm of viewModels) {
    if (vm.textContent.trim().toLowerCase() === 'ask') {
        return vm.querySelector('button');
    }
}
// Fallback: aria-label
return document.querySelector('button[aria-label="Ask"]');
```

---

### Step 3: Query for Full Transcript

**Prompt to Send**:
```
Give me the complete word-for-word transcript of this video with timestamps.
Format each segment as: [MM:SS] Text spoken
Include everything that was said.
```

**Wait**: 5-10 seconds for Gemini to process

---

### Step 4: Extract Response

**Parse Gemini Output**:
```python
def parse_transcript_response(response_text: str) -> List[Dict]:
    """Parse transcript segments from Gemini response."""
    segments = []
    pattern = r'\[(\d+:\d+)\]\s*(.+?)(?=\[\d+:\d+\]|$)'
    
    for match in re.finditer(pattern, response_text, re.DOTALL):
        timestamp, text = match.groups()
        segments.append({
            "start_time": timestamp,
            "text": text.strip(),
        })
    
    return segments
```

---

### Step 5: Update Video JSON

**Merge into existing JSON**:
```python
def update_video_json(video_id: str, segments: List[Dict], channel: str):
    json_path = Path(f"memory/video_index/{channel}/{video_id}.json")
    
    if json_path.exists():
        data = json.loads(json_path.read_text())
    else:
        data = {"video_id": video_id}
    
    # Update audio section
    data.setdefault("audio", {})
    data["audio"]["segments"] = segments
    data["audio"]["full_transcript"] = " ".join(s["text"] for s in segments)
    data["audio"]["extraction_method"] = "youtube_ask_gemini"
    data["audio"]["extracted_at"] = datetime.now().isoformat()
    
    json_path.write_text(json.dumps(data, indent=2))
```

---

## Error Handling

### Error: Ask Button Not Found
- Wait 3 more seconds (page still loading)
- Try alternate selector
- Log and skip if still not found

### Error: No Transcript Available
- Some videos have no captions
- Log as "no_transcript"
- Fallback: Try whisper transcription

### Error: Gemini Response Truncated
- Ask follow-up: "Continue the transcript from where you left off"
- Merge responses

---

## WSP Compliance

- **WSP 96**: Micro Chain-of-Thought ✅
- **WSP 91**: DAE Observability (logging) ✅
- **WSP 72**: Module Independence ✅
- **WSP 84**: Code Reuse (uses existing browser infra) ✅

---

## Integration

**Called From**:
- `auto_moderator_dae.py` → `run_video_indexing_cycle()`
- Manual: CLI tool

**Output Storage**:
- `memory/video_index/{channel}/{video_id}.json`

---

## Metrics

```python
{
    "videos_processed": int,
    "transcripts_extracted": int,
    "avg_extraction_time_s": float,
    "success_rate": float,
}
```

---

**Maintained By:** 0102 Video Indexer Team
**Last Updated:** 2026-01-16
**Status:** Prototype
