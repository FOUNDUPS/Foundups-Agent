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

### Current State: **No deployment exists**

| Check | Result |
|-------|--------|
| Dockerfile | **NONE** -- no container build config anywhere in `modules/foundups/kosei/` |
| package.json | **NONE** -- no build tooling, no dependencies declared |
| firebase.json (Kosei-specific) | **NONE** -- Kosei has no Firebase Hosting config |
| Cloud Build trigger | **NONE** -- no `cloudbuild.yaml` or GCP trigger config |
| Deploy scripts | **NONE** -- no deploy, CI/CD, or release automation |
| Files in `public/kosei/` | **NONE** -- Kosei assets are not deployed to the Firebase Hosting public directory |
| Files in `public/f/kosei/` | **NONE** -- no route-namespace deployment |
| Live URL | **NONE** -- no Cloud Run service, no Firebase Hosting path |

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

### Blocker 2: No Firebase Project Binding (P0 -- Hard Block)

The app uses Firebase Auth and Firestore but there is no `firebase.json` in the Kosei module, no `.firebaserc`, and no Firebase project configuration. The HTML loads Firebase SDK from CDN but the runtime config (API key, project ID) must be provided.

**Resolution**: Bind to existing Firebase project (likely `foundupscom`) or create dedicated project. Add runtime config.

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
| 2 | No Firebase project binding | P0 | Hard | Bind to Firebase project, add runtime config |
| 3 | X-Frame-Options: DENY | P1 | Deploy-time | Add CSP frame-ancestors override for Kosei paths |
| 4 | No build tooling | P2 | Soft | Not blocking Phase 1 (static HTML needs no build) |
| 5 | Firestore rules unverified | P2 | Soft | Verify rules before public deploy |

---

## 6. Recommended Next Slice

### `BX2 -- KOSEI_FIREBASE_HOSTING_DEPLOY_PHASE1`

**Scope**: Deploy Kosei `app/` surface to Firebase Hosting under `public/kosei/app/` with CSP header override.

**Steps**:
1. Copy `modules/foundups/kosei/app/` assets to `public/kosei/app/`
2. Add Firebase runtime config (API key, project ID) to a shared config file
3. Add path-specific CSP header override in root `firebase.json` for `/kosei/app/**`
4. Deploy to Firebase Hosting (`firebase deploy --only hosting`)
5. Verify `curl -sI https://foundupscom.web.app/kosei/app/` returns `Content-Security-Policy: frame-ancestors`
6. If verified: set `entry_url` in `foundup_manifest.json` and `mall-video-catalog.json`

**Alternative slice** (if Cloud Run preferred): `BX2 -- KOSEI_CLOUD_RUN_DEPLOY_PHASE1` -- Create Dockerfile with nginx + CSP, set up Cloud Build trigger.

**Recommendation**: Firebase Hosting is simpler for Phase 1 (static HTML, no build step, already have the project). Cloud Run makes more sense after Vite migration.

---

## 7. Comparison with GotJunk Deploy Path

| Aspect | GotJunk | Kosei |
|--------|---------|-------|
| Source | Vite + React (needs build) | Static HTML (no build needed) |
| Deploy target | Cloud Run (Dockerfile + nginx) | Firebase Hosting (recommended) or Cloud Run |
| CSP fix | In Dockerfile nginx config (PR #325) | Needs firebase.json header override |
| Current state | Deployed but stale (Feb 2026 build) | **Not deployed at all** |
| Blocker | Ops must trigger Cloud Build rebuild | Ops must create deploy config + deploy |
| entry_url | null (blocked on redeploy) | null (blocked on first deploy) |

---

*Worker BX -- audit complete. Kosei app/ is the canonical candidate for /f/kosei/app. No deployment exists. Two P0 hard blockers (deploy pipeline + Firebase binding) must be resolved before any app-binding slice can proceed truthfully.*
