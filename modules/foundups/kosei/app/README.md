# Kosei Client Workspace

**Type**: Private client workspace (auth required)
**Phase**: 1 (MVP)
**Auth**: Firebase Auth (email/password or Google OAuth) -- no admin claim required

---

## Overview

Client-facing workspace for managing content, viewing trial status, and submitting feedback. Scoped to the client's own workspace via `owner_uid` matching.

**This is NOT**:
- The public landing page (`/kosei/` -- see `frontend/`)
- The admin/operator console (`/kosei/admin/` -- see `admin/`)

## Route

```
/kosei/app/          -> Client workspace (auth-gated)
```

Blocked by: `<meta name="robots" content="noindex, nofollow">` + Firebase Auth.

## Files

```
app/
  index.html                    # Client shell (auth gate + dashboard)
  css/
    kosei-app.css               # Client-specific styles (extends kosei.css)
  js/
    kosei-app-auth.js           # Firebase Auth gate (no admin claim)
    kosei-app-data.js           # Firestore reads (workspace-scoped) + issue writes
    kosei-app-ui.js             # Dashboard rendering, tabs, issue form
  README.md                     # This file
```

## Firestore Collections

### Read (client-scoped)

| Collection | Purpose | Mode |
|-----------|---------|------|
| `kosei_workspaces/{id}` | Workspace root | Real-time subscription |
| `kosei_workspaces/{id}/integrations` | Platform connections | Fetch on load |
| `kosei_workspaces/{id}/content_queue` | Content items | Fetch on load |
| `kosei_workspaces/{id}/post_history` | Published posts | Fetch on load |
| `kosei_trials/{id}` | Trial state | Fetch on load |

### Write

| Collection | Purpose | Mode |
|-----------|---------|------|
| `kosei_issues` | Client feedback/issues | Create |

### NOT exposed (admin-only)

| Collection | Reason |
|-----------|--------|
| `kosei_workspaces/{id}/notes` | Operator-only notes |
| `kosei_audit_requests` | Admin lead pipeline |
| `kosei_metrics` | System-wide aggregates |

## Auth Flow

1. Page loads -> auth gate shown (Google + email/password)
2. User signs in -> Firebase Auth
3. Data layer queries `kosei_workspaces` where `owner_uid == auth.uid`
4. If workspace found -> render dashboard with trial, platforms, reporting
5. If no workspace -> show "No Workspace Found" with link to request audit

## Dashboard Sections

- **Identity**: workspace name, tier badge, locale
- **Trial status**: days remaining, usage, progress bar
- **Onboarding**: 6-step checklist with visual progress
- **Posting preferences**: frequency, days, times, platforms
- **Reporting**: posts created, published, pending, replies, connected platforms, trial days
- **Platforms**: connection list with status badges
- **Support**: issue submission form + issue history

## Boundaries

| Concern | This Surface | Other |
|---------|-------------|-------|
| Client dashboard | YES | -- |
| Trial monitoring | YES (own only) | -- |
| Platform connections | YES (own only) | -- |
| Issue submission | YES | -- |
| Public landing | NO | `frontend/` |
| Admin console | NO | `admin/` |
| Operator notes | NO | Admin only |
| Billing/Stripe | NO | Future phase |
| AutoPost UI | NO | External repo |
