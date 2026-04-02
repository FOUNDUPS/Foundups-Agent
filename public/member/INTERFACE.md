# Member Area Interface

**Module**: `public/member/`
**Version**: 2.1.0

## Public Interface

### Entry URL
```text
/member/
```

### Auth Requirements
- Clerk session required
- invite validation required
- username claim required before admitted users enter the Mall
- redirects to `/?signin=required` if not authenticated

### Runtime Surface

`/member/` is now the admitted-user p.fMALL shell hosted from Firebase static assets.

It owns:
- invite-gated post-auth landing
- Video Mall tile field with gesture-driven navigation
- FoundUp entry page (deep-linkable via `foundup.html?id={id}`)
- Red Dog unified plane with AI tools, channels, and context briefing

It does not yet own:
- direct tenant execution
- `/f/{foundup_id}` transport routing
- wallet or agent operations

### Hosted Assets

```text
/member/index.html
/member/foundup.html
/member/css/member.css
/member/css/account-concierge.css
/member/css/mall-planes.css
/member/css/mall-tile-field.css
/member/js/gesture-engine.js
/member/js/mall-planes.js
/member/js/mall-tile-field.js
/member/js/gesture-hints.js
/member/js/account-concierge.js
/member/js/red-dog-concierge.js
/member/mall-video-catalog.json     <- Video Mall data source
/member/mall-catalog.json           <- Legacy FoundUp catalog
```

### JavaScript Surface

The page bootstraps these internal behaviors:
- `initClerkAuth()`
- `initializeMall(clerkUserId, userData, clerkUser)`
- `loadMallCatalog()`
- `loadInviteContext(clerkUserId, clerkUser)`

---

#### `window.redDog` (Unified Plane API)

**Source**: `js/account-concierge.js`

The primary public API for the unified Red Dog plane. All concierge interactions go through this API.

| Method | Description |
|--------|-------------|
| `open()` | Open the Red Dog plane |
| `close()` | Close the Red Dog plane |
| `toggle()` | Toggle plane open/close |
| `isOpen()` | Returns boolean |
| **AI Tools** | |
| `setCategory(id)` | Set projection category |
| `getCategory()` | Get current category |
| `setDensity(preset)` | Set density preset (2x3, 3x4, 3x5, 5x8) |
| `getDensity()` | Get current density |
| `setMotionMode(mode)` | Set motion mode (snap, glide) |
| `getMotionMode()` | Get current motion mode |
| **Channels** | |
| `populateMyMall()` | Project Personal Mall (012 lanes) |
| `openPersonalMall()` | Alias for populateMyMall |
| `openSearchMall()` | Show search input |
| `searchByCreator(query)` | Filter by creator name |
| `clearSearch()` | Clear search and reset field scope |
| **Context** | |
| `getContext()` | Get current context briefing |
| `refreshBriefing()` | Refresh context briefing |
| `getRecommendations()` | Get AI recommendations |
| `runRecommendation(action)` | Execute a recommendation |
| **Identity** | |
| `setIdentity(clerkUser, userData)` | Set identity block |
| `setFoundUps(foundupDocs)` | Set FoundUps grid |
| `setInvites(inviteDocs)` | Set invites drawer |

**Backward Compatibility**: `window.accountConcierge` is an alias for `window.redDog` (will be removed).

---

#### `window.mallTileField` (Video Mall API)

**Source**: `js/mall-tile-field.js`

Video Mall tile grid with field scope projections.

| Method | Description |
|--------|-------------|
| `initialize(config)` | Initialize tile field |
| `enterFoundUp(index)` | Enter FoundUp view |
| **Video Runtime** | |
| `togglePlay()` | Toggle video play/pause |
| `getPlayingIndex()` | Get currently playing tile index |
| `expandFoundUp(index)` | Expand tile to FoundUp view |
| `collapseFoundUp()` | Collapse back to Mall |
| `isExpanded()` | Returns boolean |
| `getExpandedIndex()` | Get expanded tile index |
| **Motion** | |
| `setMotionMode(mode)` | Set snap or glide |
| `getMotionMode()` | Get current motion mode |
| **Density** | |
| `setDensity(preset)` | Set density preset |
| `getDensity()` | Get current density |
| **Projection** | |
| `setProjection(type)` | Set projection sort |
| `getProjection()` | Get current projection |
| `resetProjection()` | Reset to default |
| **Field Scope** | |
| `setFieldScope(options)` | Set field scope `{ type, query }` |
| `projectPersonalMall()` | Filter to 012 lanes |
| `searchByCreator(query)` | Case-insensitive creator search |
| `filterByCategory(cat)` | Filter by category |
| `filterByTag(tag)` | Filter by tag |
| `clearFieldScope()` | Clear scope, show all |
| `getFieldScope()` | Get current scope object |

**Field Scope Types**:
| Type | Match Logic |
|------|-------------|
| `personal` | `creator === '012'` |
| `creator` | Substring match on creator/entity |
| `category` | Exact match (case-insensitive) |
| `tag` | Exact match in tags array |

---

#### `window.mallPlanes` (FoundUp View API)

**Source**: `js/mall-planes.js`

Manages in-page FoundUp view plane (slides up from bottom).

| Method | Description |
|--------|-------------|
| `setCatalog(catalog)` | Set catalog for view |
| `openFoundUp(index)` | Open FoundUp at index |
| `closeView()` | Close FoundUp view |
| `isOpen()` | Returns boolean |
| `getActiveIndex()` | Get current FoundUp index |

---

#### `window.gestureZone` (Gesture Engine)

**Source**: `js/gesture-engine.js`

| Method | Description |
|--------|-------------|
| `gestureZone(el, handlers)` | Attach gesture handlers to element |
| `dragScroll(track)` | Enable drag-to-scroll on element |

**Gesture Handlers**: `onSwipeLeft`, `onSwipeRight`, `onSwipeUp`, `onSwipeDown`, `onDoubleTap`

---

#### Legacy: `js/red-dog-concierge.js`

Self-contained IIFE for FAQ topics. Will be removed when OpenClaw lands.
- Detects page context (Mall vs FoundUp entry)
- Injects contextual help topics into `#redDogPanel` (Mall), `#conciergeSheet` (entry)
- No network calls, no backend, no fake AI

---

### Shell-Local vs OpenClaw Capabilities

| Hook | Shell-Local (Current) | OpenClaw (Future) |
|------|----------------------|-------------------|
| `searchByCreator()` | String match on catalog | AI semantic search |
| `projectPersonalMall()` | Filter by creator | Personalized ranking |
| `setProjection()` | Client-side sort | AI-ranked projections |
| `getRecommendations()` | Static recommendations | AI-generated suggestions |

> **Dev/Testing Shim**: The Search Mall text input is a temporary shell-local shim for testing field scope APIs. It will be replaced by OpenClaw-powered search UI.

### Data Expectations

**Video Mall Catalog** (primary)
```json
/member/mall-video-catalog.json
```
Schema: `modules/foundups/docs/PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md`

**Legacy FoundUp Catalog**
```json
/member/mall-catalog.json
```

**User document shape**
```typescript
interface UserDoc {
  email: string;
  username?: string;
  inviteValidated?: boolean;
  usedInviteCode?: string;
  inviteCodes: string[];
  waitlistJoined?: string;
  createdAt: string;
}
```

**Invite document shape**
```typescript
interface InviteDoc {
  code: string;
  status: "active" | "used";
  createdBy: string;
  createdAt: string;
  usedBy: string | null;
  usedAt: string | null;
}
```

### UI Contract

**Mall Context (tile field)**:
- tap tile: play/pause video in Mall context
- double-tap tile: enter FoundUp view directly
- pinch-out on tile: expand into FoundUp's video field
- swipe: navigate snapped field (default) or glide (override)
- desktop mouse drag: maps to touch swipe (drag-scroll parity)

**FoundUp View (expanded)**:
- pinch-in: collapse back to Mall
- swipe up: close FoundUp view
- swipe left/right: navigate between FoundUps
- double-tap: toggle shell-local save (localStorage)
- "Full details" link: navigate to `/member/foundup.html?id={foundup_id}` (deep-linkable)

**Red Dog Plane**:
- swipe down from top or tap avatar: open Red Dog plane
- primary explicit control is the Red Dog icon

**Other**:
- first-time visitors see a gesture discovery hint overlay (dismissible, shown once)
- invite gate and username claim remain blocking surfaces ahead of the Mall

---

*Last Updated: 2026-04-03*
