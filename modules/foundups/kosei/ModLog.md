# Kosei AI Systems — ModLog

## 2026-04-13 — In-Browser Iframe Embed Verification

**Worker**: BX4
**Slice**: `KOSEI_IN_BROWSER_IFRAME_EMBED_VERIFICATION_PHASE1`

### Verification Performed

Tested actual iframe embedding in a modern browser (Chrome) against the FoundUps shell domain.

**Browser path used**: `https://foundupscom.web.app/f/kosei`
**Iframe source**: `https://foundupscom.web.app/kosei/app/`
**Method**: Injected iframe via JavaScript on the shell page

### Result: VERIFIED EMBEDDABLE

The Kosei app **successfully renders** inside an iframe on the FoundUps shell domain.

**Screenshot evidence**: Kosei auth gate fully visible inside iframe:
- Kosei logo and title
- "Sign in to your workspace" text
- "Sign in with Google" button
- Email/Password input fields
- "Sign in with Email" button

### Finding: CSP Takes Precedence

Per W3C CSP3 spec, modern browsers ignore `X-Frame-Options` when `Content-Security-Policy: frame-ancestors` is present. This is now **confirmed** in practice:
- Headers still show both `frame-ancestors` and `X-Frame-Options: DENY`
- Chrome correctly ignores `X-Frame-Options` and allows embedding
- The iframe renders without any frame policy errors

### Current State (WSP 97)

- **Iframe embedding**: VERIFIED ✓
- **CSP frame-ancestors**: Working correctly ✓
- **entry_url**: Remains `null` pending tiny metadata restore slice
- **App renders**: Auth gate fully functional in iframe

### Next Step

**`BX5 — KOSEI_RESTORE_ENTRY_URL_PHASE1`**: Tiny metadata update to:
1. Set `entry_url` to `/f/kosei/app` in `foundup_manifest.json`
2. Update `mall-video-catalog.json` if needed
3. Kosei will then appear as embeddable in the shell instead of "DISCOVERABLE ONLY"

### Remaining Blockers (P2)

| Blocker | Severity | Notes |
|---------|----------|-------|
| Landing page not deployed | P2 | Source needs cleanup before deploy |
| Firebase API keys empty | P2 | Runtime uses `/__/firebase/init.json` auto-config |

### WSP References

- WSP 15: Browser verification only, no fake readiness
- WSP 97: entry_url stays null until metadata slice (verification complete, metadata pending)
- WSP 104: Verified on `/f/kosei` shell route embedding `/kosei/app/`

---

## 2026-04-12 — Deploy-Time Header Verification

**Worker**: BX3
**Slice**: `KOSEI_DEPLOY_TIME_HEADER_VERIFICATION_PHASE1`

### Verification Performed

Deployed Firebase Hosting with path-specific header config and checked live headers.

**Deploy method**: `firebase deploy --only hosting --project gen-lang-client-0061781628`
**Live URL checked**: `https://foundupscom.web.app/kosei/app/`

### Live Headers Observed

```
HTTP/1.1 200 OK
Content-Security-Policy: frame-ancestors https://foundups.com https://*.foundups.com https://foundupscom.web.app https://foundupscom.firebaseapp.com http://localhost:* https://localhost:*
X-Frame-Options: DENY
```

### Finding: Firebase Cannot Clear Inherited Headers

Setting `X-Frame-Options: ""` does NOT clear the inherited global `X-Frame-Options: DENY`. Firebase Hosting's header rules are **additive** — path-specific rules add headers but cannot remove headers set by broader rules.

### Embeddability Assessment

**Per W3C CSP3 spec** (https://www.w3.org/TR/CSP3/):
> If a Content-Security-Policy header that contains the frame-ancestors directive is delivered with the resource, the X-Frame-Options header MUST be ignored.

This means:
- **Modern browsers** (Chrome 40+, Firefox 35+, Safari 10+, Edge 15+) should ignore `X-Frame-Options` and use `frame-ancestors`
- **Legacy browsers** would still honor `X-Frame-Options: DENY` and block embedding
- **Actual embeddability requires in-browser iframe test**

### Current State (WSP 97)

- **CSP frame-ancestors**: Live and correct ✓
- **X-Frame-Options**: Still present (cannot be cleared via Firebase config)
- **entry_url**: Remains `null` — truthful state until in-browser test confirms embedding
- **Next step**: In-browser iframe test to confirm CSP precedence

### Remaining Blockers

| Blocker | Severity | Notes |
|---------|----------|-------|
| In-browser iframe test needed | P1 | CSP should take precedence, but needs browser confirmation |
| Landing page not deployed | P2 | Source needs cleanup before deploy |
| Firebase API keys empty | P2 | Runtime uses `/__/firebase/init.json` auto-config |

### WSP References

- WSP 15: Verification only, no fake readiness
- WSP 97: entry_url null until browser test confirms embedding
- WSP 104: Verified on `/kosei/app/` path

---

## 2026-04-12 — Firebase Hosting Deploy Phase 1

**Worker**: BX2
**Slice**: `KOSEI_FIREBASE_HOSTING_DEPLOY_PHASE1`

### Hosting Path Provisioned

Created `public/kosei/app/` hosting structure (app bundle only):
- `public/kosei/css/kosei.css` — shared styles
- `public/kosei/app/index.html` — client workspace HTML
- `public/kosei/app/css/kosei-app.css` — app-specific styles
- `public/kosei/app/js/` — auth, data, UI scripts

**Source of truth**: `modules/foundups/kosei/app/` is source, `public/kosei/app/` is deploy target.

**NOT deployed**: Landing page (`/kosei/`) deferred to separate slice — source has encoding issues and missing assets.

### Iframe Embed Blocker (UNVERIFIED)

Root `firebase.json` is gitignored (ops-managed). The global header at `source: "**"` sets `X-Frame-Options: DENY`.

**Proposed config** (requires deploy-time verification):

```json
{
  "source": "/kosei/app/**",
  "headers": [
    { "key": "Content-Security-Policy", "value": "frame-ancestors https://foundups.com https://*.foundups.com https://foundupscom.web.app https://foundupscom.firebaseapp.com http://localhost:* https://localhost:*" },
    { "key": "X-Frame-Options", "value": "" },
    { "key": "X-Content-Type-Options", "value": "nosniff" },
    { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
  ]
}
```

**WARNING**: Whether `X-Frame-Options: ""` actually clears the inherited global `DENY` is **unverified**. Firebase Hosting docs describe ordered header application but do not confirm "empty value clears inherited header" semantics. This remains a deploy-time blocker until verified via:

```bash
firebase deploy --only hosting
curl -sI https://foundupscom.web.app/kosei/app/ | grep -iE "(x-frame|content-security)"
```

### Current State (WSP 97)

- **App bundle**: Staged at `public/kosei/app/` ✓
- **Landing page**: NOT deployed (deferred)
- **Iframe header fix**: UNVERIFIED blocker
- **entry_url**: Remains `null` — truthful state until deploy + header verification
- **Route tests**: 45 passed

### Remaining Blockers

| Blocker | Severity | Notes |
|---------|----------|-------|
| X-Frame-Options override behavior | P1 | Unverified — must test at deploy time |
| Landing page not deployed | P2 | Source needs cleanup before deploy |
| Firebase API keys empty | P2 | Runtime uses `/__/firebase/init.json` auto-config |
| Kosei Firestore rules | P2 | Needed before client data writes |

**UI fix**: No-workspace state CTA changed from dead link to informational text ("Contact support to request an audit").

### WSP References

- WSP 15: Smallest correct move (app bundle only)
- WSP 97: Current-truth (entry_url null, header fix unverified)
- WSP 104: Route namespace (`/kosei/app/**` scope)

---

## 2026-04-11 — Runtime Readiness Audit

**Worker**: BX
**Slice**: `KOSEI_RUNTIME_READINESS_AUDIT_PHASE1`

- Created `docs/RUNTIME_READINESS_AUDIT.md` — full deployment truth audit
- Canonical candidate for `/f/kosei/app`: `app/` surface (client workspace)
- **Finding**: Root Firebase substrate exists and is reusable (project `gen-lang-client-0061781628`, `.firebaserc`, service contract confirms reuse)
- **Finding**: Kosei-specific hosting/runtime not provisioned — no hosting target, no assets in `public/`, API keys empty, Firestore collections/rules not created
- **Finding**: Root `firebase.json` sends `X-Frame-Options: DENY` on all paths — blocks iframe embedding
- Two P0 hard blockers: (1) no deploy pipeline, (2) Kosei hosting/runtime not provisioned
- Two P2 soft blockers: (3) no build tooling (not blocking Phase 1 static HTML), (4) Firestore rules unverified
- Recommended next slice: `BX2 — KOSEI_FIREBASE_HOSTING_DEPLOY_PHASE1`
- WSP 97 (truth-first), WSP 104 (route namespace)

---

## 2026-04-07 — Phase 2: Issue Triage and Priority

**Worker**: Y2
**Slice**: `KOSEI_ISSUES_TRIAGE_AND_PRIORITY_PHASE2`

### Admin Issues Tab (Operator Triage)

- Added fourth tab "Issues" to admin console
- Real-time Firestore subscription to `kosei_issues` collection
- Dual filters: status + priority
- Issue cards display: title, status badge, priority badge, category, workspace ID (truncated), assignment status, created date
- Issue detail panel with full triage controls:
  - Status dropdown: open, in_progress, waiting_client, resolved, closed
  - Priority dropdown: low, medium, high, urgent
  - Assigned operator field
  - Resolution textarea + "Mark Resolved" action

### Client Priority Features

- Added priority selector to issue submission form (default: medium)
- `submitIssue()` now accepts priority parameter
- Issue cards display priority badge alongside status badge
- Clients see: status, priority, resolution
- Clients do NOT see: assigned_to, internal triage controls

### Files Modified

Admin surface:
- `admin/index.html` — Issues tab button + panel with filters
- `admin/js/kosei-admin-data.js` — `subscribeIssues()`, `getIssue()`, `updateIssueStatus()`, `updateIssuePriority()`, `resolveIssue()`
- `admin/js/kosei-admin-ui.js` — `renderIssues()`, `openIssueDetail()`, `saveIssueTriage()`, `resolveIssueTriage()`
- `admin/css/kosei-admin.css` — issue/priority badges, form elements

Client surface:
- `app/index.html` — priority selector in issue form
- `app/js/kosei-app-ui.js` — priority in submit + display
- `app/js/kosei-app-data.js` — priority parameter in `submitIssue()`
- `app/css/kosei-app.css` — priority badge styles

Tests:
- `tests/test_issue_triage.py` — 20 focused tests for issue triage features
- `tests/test_client_workspace.py` — updated boundary test (priority is client-settable)

### WSP 97 Applied

Status/priority model verified against `KOSEI_DATA_MODEL.md` Section 7 (IssueDoc interface). All values match canonical spec.

---

## 2026-04-06 — Phase 1: Admin Operator Surface

**Worker**: I
**Slice**: `KOSEI_ADMIN_OPERATOR_SURFACE_PHASE1`

- Created `admin/` directory with internal operator console
- Auth gate: Firebase Auth + `kosei_admin: true` custom claim check
- Three tabs: Leads, Clients, Trials — each with real-time Firestore subscription + status filter
- Slide-in detail panel shows full record: contact, intake answers, audit status, onboarding step, posting preferences, platform connections, operator notes, trial usage, timeline
- Status models: audit (5 states), workspace (4 states), trial (4 states), connection (5 states)
- Operator notes: read + write to `kosei_workspaces/{id}/notes` subcollection
- Boundaries: no public landing changes, no client workspace, no AutoPost code
- `noindex, nofollow` on admin HTML — not crawlable
- Protocol: WSP 97 (collections, fields, and statuses match KOSEI_DATA_MODEL.md)

Files created:
- `admin/index.html` — admin shell (auth gate + tabbed UI + detail panel)
- `admin/css/kosei-admin.css` — admin styles (extends kosei.css)
- `admin/js/kosei-admin-auth.js` — Firebase Auth + admin claim gating
- `admin/js/kosei-admin-data.js` — Firestore real-time subscriptions + reads + note writes
- `admin/js/kosei-admin-ui.js` — list/detail rendering, tab switching, filtering
- `admin/README.md` — admin surface documentation

---

## 2026-04-06 — Phase 1: Public Landing PWA

**Worker**: H
**Slice**: `KOSEI_PUBLIC_LANDING_PWA_PHASE1`

- Created `frontend/` directory with public landing PWA
- Implemented EN/JP i18n system (`kosei-i18n.js`) with centralized strings
- Built pre-audit intake form that writes to `kosei_audit_requests` Firestore collection
- Added PWA support: manifest.json, service worker, mobile-first CSS
- Landing includes: hero, value props, audit CTA, intake form, trust section, footer
- Form has localStorage fallback if Firestore unavailable
- Boundaries maintained: no client workspace, no admin workspace, no AutoPost code
- Protocol: WSP 97 (verified against service contract and data model)

Files created:
- `frontend/index.html` — main landing page
- `frontend/manifest.json` — PWA manifest
- `frontend/sw.js` — service worker
- `frontend/css/kosei.css` — all styles
- `frontend/js/kosei-i18n.js` — EN/JP switching
- `frontend/js/kosei-intake.js` — form → Firestore
- `frontend/README.md` — frontend docs

---

## 2026-04-06 — Phase 0: Scaffold

**Worker**: C
**Slice**: `KOSEI_FOUNDUP_SCAFFOLD_PHASE1`

- Created module scaffold: README, INTERFACE, ROADMAP, ModLog, module.json
- Defined 7 service contracts (audit, onboard, orchestrate, workspace, admin, trial, white-label)
- Locked Kosei vs AutoPost boundary: Kosei is business layer, AutoPost is external content engine
- Created `src/contracts.py` with dataclass contracts
- Created `tests/test_contracts.py` — validates contract structure
- WSP compliance: WSP 3 (domain), WSP 11 (interface), WSP 22 (modlog), WSP 49 (structure), WSP 72 (independence)
