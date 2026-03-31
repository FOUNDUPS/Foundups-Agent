# p.fMALL Routing and Discovery Model

**Status**: Architecture specification (first tranche)
**Owner**: 0102
**Slice**: `pfmall_architecture_and_template_contract`
**WSP References**: WSP 3 (Domains), WSP 49 (Structure)

---

## 1. Purpose

Define how p.fMALL routes users to FoundUps, how FoundUps are discovered, and how navigation works between the shell and loaded FoundUps.

---

## 2. URL Structure

### 2.1 Shell Routes (owned by shell)

```
/                           → Redirect to /discover
/discover                   → Launch catalog
/discover?category={cat}    → Filtered by category
/discover?tier={tier}       → Filtered by DAO tier
/discover?stage={stage}     → Filtered by lifecycle stage
/search?q={query}           → HoloIndex cross-FoundUp search
/wallet                     → UPs balance, subscription, top-ups
/settings                   → Shell preferences (theme, notifications)
/auth/callback              → Auth provider callback
```

### 2.2 FoundUp Routes (delegated to FoundUp)

```
/f/{foundup_id}             → FoundUp default view
/f/{foundup_id}/{path}      → Deep link into FoundUp internal route
/f/{foundup_id}?{params}    → FoundUp with query parameters
```

### 2.3 Route Priority

1. Shell routes take priority over FoundUp routes
2. Any path starting with `/f/` is a FoundUp route
3. Unknown paths redirect to `/discover`

---

## 3. Launch Catalog

### 3.1 Catalog Format

The catalog is a JSON file listing all registered FoundUp manifests. Loaded at shell boot.

```json
{
  "version": "1.0.0",
  "updated_at": "2026-03-28T00:00:00Z",
  "foundups": [
    {
      "foundup_id": "a3f8c1d2e4b67890",
      "name": "GotJunk",
      "tagline": "Turn your junk into someone's treasure",
      "category": "marketplace",
      "tier": "F0_DAE",
      "lifecycle_stage": "proto",
      "required_subscription_tier": "free",
      "is_invite_only": true,
      "icon_url": "/foundups/gotjunk/icon-192.png",
      "manifest_url": "/foundups/gotjunk/foundup_manifest.json"
    }
  ]
}
```

Catalog entries are a **subset** of the full manifest (display fields only). The full manifest is loaded on demand when the user navigates to a FoundUp.

### 3.2 Catalog Loading

```
Shell boot
  → fetch catalog.json (stale-while-revalidate from cache)
  → validate catalog version
  → register routes for each FoundUp
  → render catalog UI
```

### 3.3 Catalog Updates

- Catalog is served as a static JSON file (Phase 1)
- Cache strategy: stale-while-revalidate (show cached, fetch fresh in background)
- Catalog version bump triggers UI refresh notification
- Phase 2: catalog served via API with real-time updates

---

## 4. Discovery Model

### 4.1 Browse by Category

Users can browse FoundUps by category (see `PFMALL_LAUNCH_CATALOG_TAXONOMY.md`):

```
/discover                    → All FoundUps
/discover?category=marketplace  → Marketplace FoundUps
/discover?category=media        → Media FoundUps
/discover?category=science      → Science FoundUps
```

### 4.2 Filter by Access

```
/discover?tier=F0_DAE           → Only F0 FoundUps
/discover?stage=proto           → Only proto-stage FoundUps
/discover?invite_only=false     → Only public FoundUps
```

### 4.3 Search by HoloIndex

```
/search?q=sell+old+furniture
```

HoloIndex semantic search across all FoundUps the user has access to. Results include:
- FoundUp name and tagline
- Matched content snippet (from HoloIndex collection)
- Relevance score
- Direct link to FoundUp (`/f/{foundup_id}`)

Search is filtered by user's subscription tier — results from FoundUps above the user's tier are excluded.

### 4.4 Pre-OPO Gating

FoundUps with `is_invite_only: true` (all F0_DAE FoundUps):

1. Catalog shows the FoundUp card with "Coming Soon" or "Angel Access" badge
2. User clicks → shell checks subscription tier
3. If tier >= Angel → load FoundUp
4. If tier < Angel → show "Upgrade to Angel ($195/mo) to access early FoundUps"
5. No preview, no partial access — invite-only means invite-only

---

## 5. FoundUp Loading

### 5.1 Load Sequence

```
User navigates to /f/{foundup_id}
  1. Shell looks up foundup_id in registered routes
  2. If not found → show 404 page
  3. Fetch full manifest from manifest_url
  4. Validate manifest (schema + HMAC signature)
  5. Check user subscription tier >= required_subscription_tier
  6. If invite_only && tier < Angel → block with upgrade prompt
  7. Create sandboxed iframe with entry_url
  8. iframe loads FoundUp bundle
  9. Shell sends "shell_ready" message via postMessage
  10. FoundUp sends "ready" message back
  11. Shell sends initial route (if deep link: /f/{id}/{path})
  12. Shell updates nav chrome (title, back button)
```

### 5.2 iframe Sandbox Attributes

```html
<iframe
  src="{entry_url}"
  sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
  allow="clipboard-write"
  loading="lazy"
  title="{name}"
></iframe>
```

**Sandbox restrictions**:
- `allow-scripts`: FoundUp JS can execute
- `allow-same-origin`: FoundUp can access its own IndexedDB
- `allow-forms`: FoundUp can submit forms
- `allow-popups`: FoundUp can open new windows (for OAuth flows)
- NO `allow-top-navigation`: FoundUp cannot navigate the shell
- NO `allow-modals`: FoundUp cannot show alert/confirm/prompt

### 5.3 Loading States

| State | Shell UI |
|-------|----------|
| Loading manifest | Spinner + "Loading {name}..." |
| Manifest validation failed | Error: "This FoundUp could not be verified" |
| Tier insufficient | Upgrade prompt with tier comparison |
| iframe loading | Skeleton UI in FoundUp area |
| FoundUp "ready" received | Remove skeleton, show FoundUp |
| FoundUp load timeout (30s) | Error: "FoundUp failed to load" + retry button |

---

## 6. Navigation

### 6.1 Shell Navigation

The shell owns the browser history stack. FoundUps use hash routing internally.

```
Browser URL: /f/a3f8c1d2e4b67890/listings
Shell state: { currentFoundUp: "a3f8c1d2e4b67890" }
FoundUp receives: { route: "/listings" } via postMessage
```

### 6.2 FoundUp-Initiated Navigation

FoundUps request navigation via postMessage:

```json
{
  "type": "foundup_event",
  "foundup_id": "a3f8c1d2e4b67890",
  "event": "navigate",
  "payload": {
    "target": "shell",
    "path": "/discover"
  }
}
```

The shell validates:
1. `target: "shell"` → navigate shell route
2. `target: "self"` → update FoundUp internal route (shell updates URL)
3. `target: "foundup"` with `foundup_id` → navigate to different FoundUp (if user has access)

### 6.3 Back/Forward

- Browser back/forward handled by shell
- Shell sends `route_change` event to FoundUp when URL changes
- FoundUp updates its internal view based on received route

### 6.4 Deep Linking

Deep links work by passing the path suffix to the FoundUp:

```
User visits: /f/a3f8c1d2e4b67890/item/42
Shell extracts: foundup_id = "a3f8c1d2e4b67890", path = "/item/42"
Shell loads FoundUp, waits for "ready"
Shell sends: { event: "route_change", payload: { path: "/item/42" } }
FoundUp navigates to item 42 internally
```

---

## 7. Cross-FoundUp Navigation

When a user navigates from one FoundUp to another:

```
1. Current FoundUp sends "navigate" with target: "foundup", foundup_id: "{other_id}"
2. Shell validates user access to target FoundUp
3. Shell destroys current FoundUp iframe
4. Shell loads target FoundUp (full load sequence)
5. Shell updates browser URL to /f/{other_id}
```

Phase 1: Only one FoundUp loaded at a time. Switching destroys the current iframe.
Phase 2 (module federation): Multiple FoundUps may coexist.

---

## 8. Offline Routing

When offline:

1. Shell routes work normally (cached by service worker)
2. Catalog shows cached FoundUp entries
3. FoundUp loading depends on FoundUp's own cache:
   - If FoundUp bundle cached → loads normally
   - If not cached → "This FoundUp is not available offline"
4. Agent requests blocked (require server)
5. HoloIndex search blocked (require server)

---

## 9. Error Routes

| Scenario | Route | UI |
|----------|-------|----|
| Unknown path | `/404` | "Page not found" with link to /discover |
| Unknown FoundUp ID | `/f/{bad_id}` | "FoundUp not found" with link to /discover |
| Manifest invalid | `/f/{id}` | "Could not verify this FoundUp" |
| Tier insufficient | `/f/{id}` | Upgrade prompt |
| FoundUp load error | `/f/{id}` | "Failed to load" + retry |
| Offline + uncached | `/f/{id}` | "Not available offline" |
