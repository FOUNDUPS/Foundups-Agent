# p.fMALL Fullscreen Player Contract

**Version**: 2.1.0
**Date**: 2026-04-05
**Status**: Phase 2 landed (save/share/history/resume)
**Owner**: Worker F (0102)

---

## 1. Purpose

Define the fullscreen video player and queue rail contract for the admitted p.fMALL.

The fullscreen player is a dedicated video viewing layer that:
- Displays one video at a time from a FoundUp-constrained queue
- Provides gesture-driven navigation (swipe, pinch, tap)
- Shows a bottom queue rail for browsing adjacent videos
- Enforces topic stability (no cross-FoundUp drift)

This is NOT a global feed or discovery surface. It is a focused playback layer for content within a single FoundUp's video queue.

---

## 2. Scope

### Owned by this contract

- Fullscreen entry/exit mechanics
- Top action bar (back, share, save, info, more)
- Bottom queue rail with auto-hide
- Queue-constrained autoplay
- Swipe/pinch/tap gesture semantics
- Safe-area handling (notched devices)
- Chrome visibility toggle

### NOT owned by this contract

- Mall tile field behavior (`PFMALL_MALL_NAVIGATION_CONTRACT.md`)
- Red Dog controls (`public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`)
- Video catalog content (`mall-video-catalog.json`)
- Media delivery paths (`test_video_mall_media_delivery.py`)
- FoundUp interior behavior (`PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`)

---

## 3. Runtime Files

| File | Purpose |
|------|---------|
| `public/member/js/mall-video-player.js` | Player logic, gestures, public API |
| `public/member/css/mall-video-player.css` | Fullscreen overlay styling, safe-area |
| `public/member/js/gesture-engine.js` | Shared gesture detection (swipe, tap) |

---

## 4. DOM Structure

```text
#videoPlayerFullscreen                 (fixed overlay, z-index: 9000)
 |- .video-player-top-bar              (back, title, share, save, more)
 |- .video-player-stage                (video/iframe element)
 |- .video-player-edge-trigger         (bottom edge hover/touch zone)
 |- .video-player-queue-rail           (auto-hide queue thumbnails)
 |   |- .video-player-queue-track      (horizontal scroll)
 |       |- .video-player-queue-item   (per-video thumbnail)
 |- .video-player-gesture-hint         (transient feedback overlay)
```

---

## 5. Fullscreen Entry

Entry point: `mallVideoPlayer.open(foundupId, queue, startIndex, resumeOpts?)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `foundupId` | string | The FoundUp ID — constrains the queue |
| `queue` | Array | Array of video objects from that FoundUp |
| `startIndex` | number | Index to start at (default: 0) |
| `resumeOpts` | object? | Optional `{ resumeSeconds: number }` — seeks after metadata load (HTML5 `<video>` only; embeds ignore) |

**Behavior**:
1. DOM container is created lazily on first open
2. `document.body.style.overflow = 'hidden'` prevents page scroll
3. Container gets `.open` class (triggers `display: flex`)
4. First video begins autoplay
5. Queue rail renders (hidden until revealed)
6. Chrome auto-hide timer starts (3s)
7. Dispatches `videoPlayerOpen` CustomEvent

**Entry triggers** (from Mall field):
- Corner expand control on tile
- Double-tap on video tile (if already playing)
- Programmatic call from tile-field.js

---

## 6. Fullscreen Exit

Exit methods:
- Swipe down on stage
- Pinch-in on stage (scale < 0.7)
- Back button in top bar
- Escape key
- `mallVideoPlayer.close()` API call

**Behavior**:
1. Container loses `.open` class
2. `document.body.style.overflow` restored
3. Video/iframe removed from stage
4. Queue and state cleared
5. Dispatches `videoPlayerClose` CustomEvent

### 6.1 Resume position (Phase 1, shell-local)

- Optional **continue-watching** for **`pfmall_watch_history`** only; same `localStorage` key, entries may include `playbackPosition` (seconds).
- **Written** on exit (`close`) and when **changing** the active queue index (`goToVideo`), for **HTML5 `<video>`** sources only; **not** for cross-origin embeds (no guessed timestamps).
- **Normalized away** when progress is below ~5s or at or above ~97% of duration (treated as finished).
- **Re-entry**: `mallVideoPlayer.open(foundupId, queue, startIndex, { resumeSeconds })` seeks after metadata load when applicable.

---

## 7. Gesture Semantics

| Gesture | Action |
|---------|--------|
| swipe-up | Next video in queue |
| swipe-down | Exit fullscreen |
| pinch-in | Exit fullscreen (scale < 0.7) |
| tap | Toggle chrome visibility |
| swipe-left | Toggle save (Phase 2) |
| swipe-right | Dismiss hook |

**Keyboard**:
| Key | Action |
|-----|--------|
| Escape | Exit fullscreen |
| ArrowUp / ArrowLeft | Previous video |
| ArrowDown / ArrowRight | Next video |
| Space | Toggle chrome |

---

## 8. Top Action Bar

| Button | Action | Event |
|--------|--------|-------|
| Back | Close player | none |
| Save | Toggle save (localStorage) | `videoPlayerSave` |
| Share | Share video (native or clipboard) | `videoPlayerShare` |
| More | Show options (stub) | none |

**Save behavior** (Phase 2):
- Toggles saved state per video
- Button shows `.saved` class when saved
- Persists to `pfmall_saved_videos` in localStorage

**Share behavior** (Phase 2):
- Tier 1: `navigator.share()` (mobile native)
- Tier 2: `navigator.clipboard.writeText()` (desktop)
- Tier 3: `document.execCommand('copy')` (legacy)
- URL source: `embed_url || source_url`

**Chrome visibility**:
- Top bar fades to `opacity: 0` when `.chrome-hidden` is set
- Auto-hide after 3 seconds of inactivity
- Any gesture resets the timer

---

## 9. Queue Rail

**Structure**:
- Horizontal scroll track with snap (`scroll-snap-type: x mandatory`)
- Each item: thumbnail (16:9) + label
- Active item has purple border (`#7c5cfc`)
- Tap thumbnail = autoplay that video

**Visibility**:
- Hidden by default (`transform: translateY(100%)`)
- Revealed by swipe-up from bottom edge trigger or hover
- Auto-hides after 4 seconds

**Constraint**:
- Queue rail only shows videos from the current FoundUp
- No cross-FoundUp drift — queue is locked to `currentFoundUpId`

---

## 10. Queue-Constrained Autoplay

**Rule**: The player never leaves the current FoundUp's queue.

**Autoplay-advance** (video ends → next video plays):
- YouTube embeds: via YouTube IFrame API `onStateChange` → `ENDED`
- HTML5 `<video>`: via native `ended` event
- Other embeds (Vimeo, etc.): NOT supported — no cross-origin ended event
- End of queue: `showEndOfQueue()` renders replay/close UI instead of advancing

When the user reaches the end of the queue:
- `nextVideo()` shows "End of queue" hint
- No automatic jump to another FoundUp
- User must exit fullscreen to browse elsewhere

This prevents TikTok-style infinite scroll across topics.

---

## 11. Safe-Area Handling

Top bar and queue rail respect notched device safe areas:

```css
.video-player-top-bar {
  padding-top: max(0.75rem, env(safe-area-inset-top));
}

.video-player-queue-rail {
  padding-bottom: max(0.5rem, env(safe-area-inset-bottom));
}
```

---

## 12. Events

| Event | Payload | When |
|-------|---------|------|
| `videoPlayerOpen` | `{ foundupId, videoIndex }` | Player opens |
| `videoPlayerClose` | none | Player closes |
| `videoPlayerNavigate` | `{ foundupId, videoIndex }` | Video changes |
| `videoPlayerSave` | `{ foundupId, video, saved }` | Save toggle (Phase 2) |
| `videoPlayerShare` | `{ foundupId, video }` | Share button |
| `videoPlayerDismiss` | `{ foundupId, video }` | Swipe-right dismiss |

---

## 13. Public API

```javascript
window.mallVideoPlayer = {
  // Core
  open(foundupId, queue, startIndex, resumeOpts?),  // Open with queue; resumeOpts: { resumeSeconds } (HTML5 only)
  close(),                              // Exit fullscreen
  goToVideo(index),                     // Jump to index
  next(),                               // Next video
  prev(),                               // Previous video
  isOpen(),                             // Returns boolean
  getFoundUpId(),                       // Returns current constraint
  getCurrentIndex(),                    // Returns current index
  getQueueLength(),                     // Returns queue length

  // Save (Phase 2)
  isCurrentSaved(),                     // Returns boolean
  getSavedVideos(),                     // Returns Object map (not array)
  getSavedCount(),                      // Returns number

  // History (Phase 2)
  getHistory(),                         // Returns Array (newest first, max 50)
  clearHistory()                        // Clears watch history
};
```

**localStorage Keys** (Phase 2):
| Key | Structure |
|-----|-----------|
| `pfmall_saved_videos` | `{ "{foundupId}::{videoId}": { foundupId, videoId, title, thumbnail, savedAt } }` |
| `pfmall_watch_history` | `[{ foundupId, videoId, videoIndex, title, thumbnail, timestamp, playbackPosition? }, ...]` — `playbackPosition` is shell-local seconds for HTML5 `<video>` items only; omitted when below 5s or near end (97%+); not set for iframe embeds. |

---

## 14. Video Rendering

The player supports three video source types:

| Source | Detection | Render | Autoplay-advance |
|--------|-----------|--------|-----------------|
| YouTube | `embed_url` matches `youtube.com/embed/{id}` | YouTube IFrame API (`YT.Player`) | YES — `onStateChange` → `ENDED` triggers next |
| Other embed | `embed_url` present, not YouTube | `<iframe src="..." autoplay>` | NO — no ended detection |
| Direct file | `.mp4`, `.webm`, `.ogg` | `<video src="..." autoplay controls>` | YES — `ended` event triggers next |
| Neither | fallback | Loading placeholder | NO |

**YouTube IFrame API**: The player loads `youtube.com/iframe_api` on first YouTube embed. This provides `onStateChange` callbacks, enabling queue autoplay-advance when a video ends. The API is loaded once and reused. `YT.Player` instances are destroyed on video navigation and player close.

YouTube embeds use `autoplay=1`, `rel=0`, `modestbranding=1`.

**Non-YouTube embeds** (Vimeo, etc.) fall back to raw `<iframe>`. These do not support autoplay-advance because there is no cross-origin ended event.

---

## 15. Mobile Optimizations

### Portrait (max-width: 480px)
- Top bar padding reduced
- Buttons shrink to 36px
- Title truncates at 140px
- Queue items shrink to 80px

### Landscape (max-height: 500px)
- Top bar and rail padding reduced
- Queue items shrink to 80px

---

## 16. Non-Goals

These are explicitly deferred:

- **Picture-in-picture**: Not implemented
- **Background audio**: Not implemented
- **Offline playback**: Not implemented
- **Cross-FoundUp playlists**: Violates topic constraint
- **Recommendation rail**: Would require AI integration
- **Comment overlay**: Requires backend integration
- **Backend sync**: Save/share/history are localStorage only (no server)

---

## 17. Cross-References

| Document | Relationship |
|----------|--------------|
| `PFMALL_VIDEO_MALL_RUNTIME_FOUNDATION_2026-04-02.md` | Parent runtime spec |
| `PFMALL_MALL_NAVIGATION_CONTRACT.md` | Mall field behavior (entry point) |
| `public/member/README.md` | Member shell overview |
| `public/member/INTERFACE.md` | Public interface for member shell |
| `test_video_mall_media_delivery.py` | Media path/safety rules |

---

## 18. Phase Status

**Phase 1** (landed):
- Fullscreen entry/exit
- Queue-constrained playback
- Gesture navigation
- Top bar and queue rail

**Phase 2** (landed):
- Save toggle (localStorage: `pfmall_saved_videos`)
- Share (native share → clipboard fallback)
- Watch history (localStorage: `pfmall_watch_history`, max 50, newest first)
- Concierge browse surfaces: Saved Videos and Recently Watched sections in Red Dog plane (see `public/member/INTERFACE.md` → `window.redDog`)
- Resume position: shell-local, HTML5 `<video>` only (see section 6.1)

**Phase 3** (future):
- Backend sync for save/history/resume
- AI-driven "more like this" rail (still queue-constrained)
- Chapter markers for long-form content
- Transcript/subtitle integration

---

## 19. Invariants

1. **Queue constraint**: Player never shows videos from a different FoundUp than `currentFoundUpId`
2. **No auto-drift**: Reaching end of queue does NOT auto-play another FoundUp
3. **Exit always works**: Swipe-down, pinch-in, Escape, and back button always close
4. **Safe-area respected**: Top and bottom controls clear notched device areas
5. **Chrome auto-hides**: UI fades after inactivity to maximize video view
6. **Gesture priority**: Player gestures override page scroll when open

---

*This contract locks the fullscreen player behavior for p.fMALL phase 2. Changes require 0102 review.*
