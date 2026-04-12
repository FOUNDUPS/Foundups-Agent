# Kosei Runtime Readiness Audit

**Worker**: BX
**Slice**: `KOSEI_RUNTIME_READINESS_AUDIT_PHASE1`
**Date**: 2026-04-11
**WSP**: 97 (Truth-First Routing), 104 (FoundUp Route Namespace)

---

## 1. Canonical Candidate Surface for `/f/kosei/app`

**Answer**: `modules/foundups/kosei/app/` (Client Workspace)

Per `KOSEI_SERVICE_CONTRACT.md`, Kosei has three surfaces:

| Surface | Path | Auth | Purpose |
|---------|------|------|---------|
| `frontend/` | `/kosei/` | None (public) | Landing page, audit intake |
| `app/` | `/kosei/app/` | Firebase Auth (email/Google) | Client workspace dashboard |
| `admin/` | `/kosei/admin/` | Firebase Auth + `kosei_admin` claim | Operator console |

The shell's `/f/kosei/app` iframe mount maps to the **`app/`** surface -- the client workspace. This is the surface that `entry_url` would point to once deployed.

The `frontend/` surface is the public landing (discovery), not the tenant app. The `admin/` surface is operator-only and not shell-embeddable.

---

## 2. Deployment Truth

### Current State: **Source exists, no Kosei-specific deployment provisioned**

**Root Firebase substrate exists** (shared project `gen-lang-client-0061781628`):
- Root `firebase.json` -- hosting, functions, Firestore config
- Root `.firebaserc` -- exists but targets are empty (`{}`)
- `KOSEI_SERVICE_CONTRACT.md` Section 2 confirms Kosei reuses root project
- `kosei-app-auth.js` already wired for Firebase auto-config via `/__/firebase/init.json`

**What is NOT provisioned for Kosei**:

| Check | Result |
|-------|--------|
| Kosei hosting site target | **NONE** -- `.firebaserc` targets empty, no Kosei entry |
| Files in `public/kosei/` | **NONE** -- Kosei assets not deployed to Firebase Hosting public dir |
| Files in `public/f/kosei/` | **NONE** -- no route-namespace deployment |
| Firebase API keys populated | **EMPTY** -- `kosei-app-auth.js` lines 12, 17, 18 have empty strings |
| Kosei Firestore collections | **NONE** -- `kosei_*` collections not created |
| Kosei Firestore security rules | **NONE** -- no rules for Kosei collections in root `firestore.rules` |
| `kosei_admin` auth claim | **NONE** -- no Cloud Function or script to set admin claim |
| Dockerfile | **NONE** -- not needed for Phase 1 (static HTML via Firebase Hosting) |
| package.json | **NONE** -- not needed for Phase 1 (no build step) |
| Cloud Build trigger | **NONE** -- not needed for Firebase Hosting deploy path |
| Live URL | **NONE** -- no deployed surface at any URL |

### What Exists (Source Only)

All three surfaces exist as **static HTML + vanilla JS** in `modules/foundups/kosei/`:

- `frontend/`: `index.html`, `manifest.json`, `sw.js`, `css/`, `js/` (EN/JP i18n, vanilla JS)
- `app/`: `index.html`, `css/kosei-app.css`, `js/` (kosei-app-auth.js, kosei-app-data.js, kosei-app-ui.js)
- `admin/`: `index.html`, `css/kosei-admin.css`, `js/` (kosei-admin-auth.js, kosei-admin-data.js, kosei-admin-ui.js)

All surfaces use Firebase SDK via CDN (compat v9.22.0). No build step required for current static HTML phase.

### module.json Status

```json
{
  "status": "scaffold",
  "surfaces": { "web": "kosei.ai" }
}
```

The `kosei.ai` domain is declared but no DNS, hosting, or deployment backs it.

---

## 3. Shell-Embeddability Assessment

### Blocker: `X-Frame-Options: DENY`

The root `firebase.json` (line 14) sets a global header:

```json
{ "key": "X-Frame-Options", "value": "DENY" }
```

This applies to **all** `**` sources under Firebase Hosting. If Kosei were deployed to Firebase Hosting (e.g., `public/kosei/app/`), the shell iframe at `/f/kosei/app` would be **blocked** by this header -- identical to the GotJunk problem (PR #317, #325).

**Two deployment paths exist, each with different header implications**:

| Deploy Target | Header Control | Embeddability |
|---------------|---------------|---------------|
| Firebase Hosting (`public/kosei/app/`) | Root `firebase.json` headers section | Blocked by `X-Frame-Options: DENY` unless overridden with path-specific CSP |
| Cloud Run (standalone container) | Dockerfile nginx config | Controllable (same pattern as GotJunk Dockerfile CSP fix) |

### Firebase Hosting Override Path

Add a path-specific header block to root `firebase.json`:

```json
{
  "source": "/kosei/app/**",
  "headers": [
    { "key": "Content-Security-Policy", "value": "frame-ancestors https://foundups.com https://*.foundups.com https://foundupscom.web.app https://foundupscom.firebaseapp.com http://localhost:* https://localhost:*" },
    { "key": "X-Frame-Options", "value": "" }
  ]
}
```

### Cloud Run Path

Create a Dockerfile with nginx CSP config (same pattern as `modules/foundups/gotjunk/frontend/Dockerfile`).

---

## 4. Exact Blockers Before `entry_url` Can Be Set

### Blocker 1: No Deployment Pipeline (P0 -- Hard Block)

No Dockerfile, no firebase.json hosting entry, no Cloud Build trigger. The source exists but has zero deploy path. Nothing is live.

**Resolution**: Choose deploy target (Firebase Hosting or Cloud Run), create deploy config, deploy at least the `app/` surface.

### Blocker 2: Kosei-Specific Hosting/Runtime Not Provisioned (P0 -- Hard Block)

The root Firebase substrate exists and is reusable:
- Firebase project `gen-lang-client-0061781628` (shared with GotJunk, root landing)
- Root `.firebaserc` exists (currently empty targets)
- Root `firebase.json` defines hosting, functions, and Firestore
- `KOSEI_SERVICE_CONTRACT.md` Section 2 explicitly says Kosei reuses this project
- `kosei-app-auth.js` already has project config + `/__/firebase/init.json` auto-config fallback

What is **not yet provisioned** for Kosei specifically:
- No Kosei site target in `.firebaserc` (`targets` is empty `{}`)
- No Kosei assets deployed to `public/` (source lives only in `modules/foundups/kosei/`)
- Firebase API keys in `kosei-app-auth.js` are empty strings (lines 12, 17, 18)
- Kosei Firestore collections (`kosei_*`) not created and no security rules written
- No `kosei_admin` custom auth claim provisioned

**Resolution**: Add Kosei hosting target to `.firebaserc`, populate API keys, provision Firestore collections and rules, deploy assets to `public/kosei/`.

### Blocker 3: X-Frame-Options Header (P1 -- Deploy-Time Block)

Root `firebase.json` sends `X-Frame-Options: DENY` on all paths. If deploying to Firebase Hosting, need path-specific CSP override. If deploying to Cloud Run, need Dockerfile with nginx CSP (GotJunk pattern).

**Resolution**: Add `Content-Security-Policy: frame-ancestors` for Kosei app path, same domains as GotJunk CSP.

### Blocker 4: No Build Tooling (P2 -- Soft Block)

No `package.json`, no Vite config. Current Phase 1 is static HTML which requires no build step. This is not a hard blocker for initial deployment -- static files can be served directly. Becomes a blocker when migrating to Vite + React + TS (per KOSEI_SERVICE_CONTRACT.md roadmap).

**Resolution**: Not blocking for Phase 1 deploy. Address when build tooling is needed.

### Blocker 5: Firestore Security Rules (P2 -- Soft Block)

`kosei_workspaces`, `kosei_audit_requests`, `kosei_trials`, `kosei_issues` collections are referenced in app JS but no Firestore security rules for these collections were found. The root `firestore.rules` may or may not cover them.

**Resolution**: Verify Firestore rules cover Kosei collections before public deploy.

---

## 5. Blocker Summary Matrix

| # | Blocker | Severity | Type | Resolution |
|---|---------|----------|------|------------|
| 1 | No deploy pipeline | P0 | Hard | Create deploy config (Firebase Hosting or Cloud Run) |
| 2 | Kosei hosting/runtime not provisioned | P0 | Hard | Add hosting target, populate API keys, provision Firestore collections/rules |
| 3 | X-Frame-Options: DENY | P1 | Deploy-time | Add CSP frame-ancestors override for Kosei paths |
| 4 | No build tooling | P2 | Soft | Not blocking Phase 1 (static HTML needs no build) |
| 5 | Firestore rules unverified | P2 | Soft | Verify rules before public deploy |

---

## 6. Recommended Next Slice

### `BX2 -- KOSEI_FIREBASE_HOSTING_DEPLOY_PHASE1`

**Scope**: Deploy Kosei `app/` surface to Firebase Hosting under `public/kosei/app/` with CSP header override.

**Steps**:
1. Add Kosei hosting site target to `.firebaserc`
2. Copy `modules/foundups/kosei/app/` assets to `public/kosei/app/`
3. Populate Firebase API keys in `kosei-app-auth.js` (or verify auto-config works once hosted)
4. Add path-specific CSP header override in root `firebase.json` for `/kosei/app/**`
5. Provision Kosei Firestore collections and add security rules to root `firestore.rules`
6. Deploy to Firebase Hosting (`firebase deploy --only hosting`)
7. Verify `curl -sI https://foundupscom.web.app/kosei/app/` returns `Content-Security-Policy: frame-ancestors`
8. If verified: set `entry_url` in `foundup_manifest.json` and `mall-video-catalog.json`

**Recommendation**: Firebase Hosting via the existing root project is the natural path for Phase 1 (static HTML, no build step, substrate already exists). Cloud Run makes more sense after Vite migration.

---

## 7. Comparison with GotJunk Deploy Path

| Aspect | GotJunk | Kosei |
|--------|---------|-------|
| Source | Vite + React (needs build) | Static HTML (no build needed) |
| Deploy target | Cloud Run (Dockerfile + nginx) | Firebase Hosting (recommended) or Cloud Run |
| CSP fix | In Dockerfile nginx config (PR #325) | Needs firebase.json header override |
| Current state | Deployed but stale (Feb 2026 build) | **Not deployed at all** |
| Blocker | Ops must trigger Cloud Build rebuild | Ops must provision Kosei hosting target + deploy assets |
| entry_url | null (blocked on redeploy) | null (blocked on first deploy) |

---

*Worker BX -- audit complete. Kosei app/ is the canonical candidate for /f/kosei/app. Root Firebase substrate exists and is reusable, but Kosei-specific hosting/runtime is not provisioned. Two P0 hard blockers (deploy pipeline + Kosei hosting/runtime provisioning) must be resolved before any app-binding slice can proceed truthfully.*
