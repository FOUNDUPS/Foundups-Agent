# p.fMALL Media Delivery Contract

**Version**: 1.0.0
**Date**: 2026-04-03
**Status**: Locked
**Owner**: 0102
**Test Suite**: `modules/foundups/pfmall/tests/test_video_mall_media_delivery.py` (50 tests)

---

## 1. Purpose

p.fMALL is an **AI interaction space** — a new way of interacting with AI and the world. Video is the default surface, but the paradigm extends to any content type: documents, community, FoundUps. The same interaction model (pinch, zoom, navigate) works everywhere, with AI mediating all engagement. Built for FoundUps first, with hooks into all content. Videos are the catalog layer — they tell each FoundUp's story.

This document defines the runtime rules for media delivery in the Video Mall:
- poster images on FoundUp tiles
- video thumbnails
- embed sources
- cache behavior
- fallback behavior for missing assets

This contract locks the media path conventions so E (content catalog), F (player), and future workers can build against stable delivery rules.

---

## 2. Media Path Conventions

### 2.1 Root-Level Media (`/media/`)

**Serving path**: `https://foundups.com/media/...`
**Repo location**: `public/media/`

```
public/media/
├── posters/     # FoundUp lane poster images
├── thumbs/      # Video thumbnail images
└── .gitkeep
```

**Usage**: The video catalog (`mall-video-catalog.json`) references posters at `/media/posters/{foundup_id}.jpg`.

### 2.2 Member-Level Media (`/member/media/`)

**Serving path**: `https://foundups.com/member/media/...`
**Repo location**: `public/member/media/`

```
public/member/media/
├── posters/     # Member-specific poster overrides
├── thumbs/      # Member-specific thumbnails
└── .gitkeep
```

**Usage**: Reserved for future member-specific media. Currently empty convention directories.

### 2.3 Naming Rules

| Asset Type | Path Pattern | Example |
|------------|--------------|---------|
| Lane poster | `/media/posters/{foundup_id}.jpg` | `/media/posters/move2japan.jpg` |
| Video thumb | `/media/thumbs/{foundup_id}-{video_id}.jpg` | `/media/thumbs/move2japan-CjJTdM4wjms.jpg` |
| Member poster | `/member/media/posters/{foundup_id}.jpg` | `/member/media/posters/custom.jpg` |

---

## 3. Allowed External Domains

### 3.1 Embed URLs (iframe src)

Only YouTube embed domains are allowed:

```
https://www.youtube.com/embed/{video_id}
https://www.youtube-nocookie.com/embed/{video_id}
```

**Rejected**: Any other domain for embed URLs.

### 3.2 Thumbnail URLs

Allowed patterns:

| Pattern | Source |
|---------|--------|
| `/media/*` | Local root-relative |
| `/member/media/*` | Local member-relative |
| `https://i.ytimg.com/*` | YouTube CDN |
| `https://img.youtube.com/*` | YouTube CDN (alt) |

**Rejected**: Any other external domain for poster/thumbnail assets.

### 3.3 Source URLs (link-out)

YouTube watch URLs only:

```
https://www.youtube.com/watch?v={video_id}
https://youtu.be/{video_id}
```

---

## 4. Firebase Hosting Cache Behavior

### 4.1 Cache Headers

| Asset Pattern | Cache-Control | Rationale |
|---------------|---------------|-----------|
| `media/**/*.@(jpg\|jpeg\|png\|webp\|avif)` | `public, max-age=86400, stale-while-revalidate=3600` | 1-day cache for images |
| `media/**/*.@(mp4\|webm)` | `public, max-age=86400, stale-while-revalidate=3600` | 1-day cache for video |
| `member/media/**/*.@(jpg\|jpeg\|png\|webp\|avif)` | `public, max-age=86400, stale-while-revalidate=3600` | 1-day cache for member images |
| `member/media/**/*.@(mp4\|webm)` | `public, max-age=86400, stale-while-revalidate=3600` | 1-day cache for member video |
| `**/*.html` | `no-cache` | Always fresh HTML |
| `**/*.json` | `no-cache` | Always fresh catalogs |

### 4.2 Security Headers

All responses include:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 5. Rewrite Trap Mitigation

### 5.1 The Trap

Firebase hosting has a catch-all rewrite:

```json
{ "source": "**", "destination": "/index.html" }
```

**Consequence**: Any request for a nonexistent file (e.g., `/media/posters/missing.jpg`) returns gateway HTML with HTTP 200, not a 404.

### 5.2 Mitigation

1. **`X-Content-Type-Options: nosniff`** — Browsers will not render HTML bytes as an image. The `<img>` tag fails silently rather than showing corrupted content.

2. **CSS fallback colors** — Every tile theme class has a `background-color` that survives when the inline `background-image` fails. Broken posters degrade to a solid theme tone.

3. **Test coverage** — `test_video_mall_media_delivery.py` validates that referenced media paths follow allowed patterns. Catalog validation catches bad URLs before they reach production.

### 5.3 What This Does NOT Fix

- The HTTP response is still 200, not 404
- Network tab shows a successful request returning HTML
- Console may show no error (silent image decode failure)

**Rule**: Only reference media paths that exist as real files, or use external YouTube CDN URLs.

---

## 6. Service Worker Exclusions

### 6.1 NEVER_CACHE List

The root service worker (`public/sw.js`) excludes these from caching:

```javascript
const NEVER_CACHE = [
  'clerk.accounts.dev',
  'clerk.',
  'firebaseapp.com',
  'googleapis.com/identitytoolkit',
  'googleapis.com/securetoken',
  'cloudfunctions.net',
  '/member/',
  '/sso-callback/',
  'gstatic.com/firebasejs'
];
```

### 6.2 Member Media Behavior

All `/member/` paths are excluded from SW caching. This means:

- `/member/media/*` is **not cached** by the service worker
- Member media requires network connectivity
- No offline support for member media

**Rationale**: Member content is online-only. The SW is for gateway static assets only.

---

## 7. CSS Fallback Colors

### 7.1 Theme Classes

Every tile theme in `mall-tile-field.css` declares both `background` (gradient) and `background-color` (solid fallback):

```css
.mall-tile.theme-antifafm {
  background: linear-gradient(145deg, rgba(60, 11, 16, 0.96), ...);
  background-color: #3c0b10;
}
```

### 7.2 Visual Stack

When a poster fails to load:

1. JS sets `style="background-image: url(/media/posters/foo.jpg)"` (inline)
2. Inline style overrides CSS `background` gradient
3. Image request returns HTML (rewrite trap) or 404
4. Browser cannot decode HTML as image — `background-image` fails
5. `background-color` remains visible as fallback
6. `::before` overlay adds subtle light gradient
7. Tile displays solid theme tone — intentional, not broken

### 7.3 Theme Fallback Colors

| Theme | Fallback Color |
|-------|----------------|
| `antifafm` | `#3c0b10` |
| `gotjunk` | `#0f3c38` |
| `magadoom` | `#1b1138` |
| `tq` | `#0b1d3c` |
| `vsa` | `#28282d` |
| `pqn` | `#14321e` |
| `default` | `#1e1e23` |

---

## 8. Video Catalog Media References

### 8.1 Lane-Level Posters

```json
{
  "foundup_id": "move2japan",
  "poster_url": "/media/posters/move2japan.jpg",
  ...
}
```

**Rule**: `poster_url` must match `/media/*`, `/member/media/*`, or YouTube CDN patterns.

### 8.2 Video Thumbnails

```json
{
  "video_id": "CjJTdM4wjms",
  "thumbnail_url": "https://i.ytimg.com/vi/CjJTdM4wjms/hqdefault.jpg",
  ...
}
```

**Rule**: `thumbnail_url` should use YouTube CDN (`i.ytimg.com`) for videos sourced from YouTube. Local thumbnails are allowed for non-YouTube content.

### 8.3 Embed URLs

```json
{
  "video_id": "CjJTdM4wjms",
  "embed_url": "https://www.youtube.com/embed/CjJTdM4wjms",
  ...
}
```

**Rule**: `embed_url` must be YouTube only.

---

## 9. Test Coverage

**Test file**: `modules/foundups/pfmall/tests/test_video_mall_media_delivery.py`

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestFirebaseCacheHeaders` | 7 | Cache header rules for media, HTML, JSON |
| `TestRewriteTrapMitigation` | 4 | Catch-all rewrite awareness |
| `TestMediaDirectoryConvention` | 6 | Both media directory conventions exist |
| `TestEmbedURLSafety` | 10 | Allowed/rejected URL patterns |
| `TestServiceWorkerMediaRules` | 4 | SW NEVER_CACHE rules |
| `TestThemeFallbackColors` | 3 | CSS background-color on all themes |
| `TestDeliverySurfaces` | 6 | Member index, entry, route bridge |
| `TestVideoCatalogMediaPaths` | 6 | Catalog URL validation |
| `TestExistingCatalog` | 4 | Backward compat for mall-catalog.json |

**Total**: 50 tests

---

## 10. Non-Goals

This contract does NOT cover:

- Video player internals (F owns)
- Catalog content/structure (E owns)
- Field behavior or gestures (B owns)
- Red Dog controls (C owns)
- Live ingestion or sync
- Offline support for member media

---

## 11. Related Contracts

- `PFMALL_VIDEO_MALL_RUNTIME_FOUNDATION_2026-04-02.md` — Video Mall architecture
- `PFMALL_MALL_NAVIGATION_CONTRACT.md` — Field navigation rules
- `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md` — `/f/{id}` routing

---

*Locked by Worker A. 50 tests passing.*
