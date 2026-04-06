# Kosei Admin - Operator Console

**Type**: Internal admin/operator workspace (private)
**Phase**: 1 (MVP)
**Auth**: Firebase Auth + `kosei_admin: true` custom claim

---

## Overview

Internal operator surface for managing the Kosei AI Systems pipeline. Shows leads, clients, trials, platform connections, and operator notes.

**This is NOT**:
- The public landing page (`/kosei/` -- see `frontend/`)
- The client workspace (`/kosei/app/` -- future build)

## Route

```
/kosei/admin/          -> Operator console (auth-gated)
```

Blocked by: `<meta name="robots" content="noindex, nofollow">` + Firebase Auth + admin claim check.

## Files

```
admin/
  index.html                    # Admin shell (auth gate + tabbed UI)
  css/
    kosei-admin.css             # Admin-specific styles (extends kosei.css)
  js/
    kosei-admin-auth.js         # Firebase Auth + admin-claim gate
    kosei-admin-data.js         # Firestore reads (real-time subscriptions)
    kosei-admin-ui.js           # List/detail rendering, tab switching
  README.md                     # This file
```

## Firestore Collections Read

| Collection | Purpose | Mode |
|-----------|---------|------|
| `kosei_audit_requests` | Lead pipeline | Real-time subscription + detail read |
| `kosei_workspaces` | Client list | Real-time subscription + detail read |
| `kosei_workspaces/{id}/integrations` | Platform connections | Detail read |
| `kosei_workspaces/{id}/notes` | Operator notes | Detail read + write |
| `kosei_trials` | Trial management | Real-time subscription + detail read |
| `kosei_issues` | Client issues | Detail read (per workspace) |

## Status Models Surfaced

### Audit funnel (`audit_status`)
`pending` | `in_progress` | `complete` | `accepted` | `expired`

### Client workspace (`status`)
`onboarding` | `active` | `paused` | `churned`

### Trial (`status`)
`active` | `expired` | `converted` | `cancelled`

### Platform connection (`status`)
`disconnected` | `connecting` | `connected` | `error` | `revoked`

## Auth Flow

1. Page loads -> auth gate shown (Google sign-in button)
2. User signs in with Google -> Firebase Auth
3. `getIdTokenResult()` checks for `kosei_admin: true` custom claim
4. If admin -> show admin shell, subscribe to Firestore collections
5. If not admin -> show "Access denied" error, do not grant access

## Setting Admin Claims

Admin claims must be set via Firebase Admin SDK (Cloud Function or CLI):

```javascript
// Cloud Function or admin script
const admin = require('firebase-admin');
admin.auth().setCustomUserClaims(uid, { kosei_admin: true });
```

## Development

```bash
# Serve locally
npx serve modules/foundups/kosei -p 3000
# Then open http://localhost:3000/admin/
```

## Boundaries

| Concern | This Surface | Other |
|---------|-------------|-------|
| Lead pipeline | YES | -- |
| Client management | YES | -- |
| Trial monitoring | YES | -- |
| Operator notes | YES (read + write) | -- |
| Public landing | NO | `frontend/` |
| Client dashboard | NO | Future `/kosei/app/` |
| AutoPost UI | NO | External repo |
| Billing/Stripe | NO | Future phase |
