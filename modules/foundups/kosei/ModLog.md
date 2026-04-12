# Kosei AI Systems — ModLog

## 2026-04-12 — Firebase Hosting Deploy Phase 1

**Worker**: BX2
**Slice**: `KOSEI_FIREBASE_HOSTING_DEPLOY_PHASE1`

### Hosting Path Provisioned

Created `public/kosei/` hosting structure:

**Landing** (from `frontend/`):
- `public/kosei/index.html` — public landing page
- `public/kosei/manifest.json` — PWA manifest
- `public/kosei/sw.js` — service worker
- `public/kosei/js/` — i18n, intake scripts

**App** (from `app/`):
- `public/kosei/css/kosei.css` — shared styles
- `public/kosei/app/index.html` — client workspace HTML
- `public/kosei/app/css/kosei-app.css` — app-specific styles
- `public/kosei/app/js/` — auth, data, UI scripts

**Source of truth**: `modules/foundups/kosei/{frontend,app}/` are source, `public/kosei/` is deploy target.

### CSP Header Override (Ops-Managed)

Root `firebase.json` is gitignored (ops-managed, not repo-tracked). The following config must be added to the local `firebase.json` before deploy:

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

**CRITICAL**: The `X-Frame-Options: ""` entry explicitly clears the inherited global `X-Frame-Options: DENY`. Without this, the global header still applies and blocks iframe embedding even with CSP `frame-ancestors` set.

**Note**: `firebase.json` already updated locally on this machine. Config is NOT version-controlled.

### Current State (WSP 97)

- **Hosting path**: Provisioned ✓
- **CSP header**: Configured ✓
- **Deployed**: NO — `firebase deploy` not yet run
- **entry_url**: Remains `null` — truthful state until deploy + header verification
- **Route tests**: 45 passed

### Verification After Deploy

```bash
firebase deploy --only hosting
curl -sI https://foundupscom.web.app/kosei/app/ | grep -i content-security
# Expected: Content-Security-Policy: frame-ancestors ...
```

### Remaining Blockers (P2)

1. Firebase API keys in `kosei-app-auth.js` are empty — runtime uses `/__/firebase/init.json` auto-config fallback
2. Kosei Firestore collections/rules not provisioned — needed before client data writes
3. Admin claim provisioning not implemented — needed for `/admin/` access

### WSP References

- WSP 15: Smallest correct move (hosting + CSP only)
- WSP 97: Current-truth (entry_url null until verified)
- WSP 104: Route namespace (`/kosei/app/**` CSP scope)

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
