# Kosei AI Systems — Service Contract

**Worker**: F
**Date**: 2026-04-06
**Slice**: `KOSEI_BACKEND_DATA_AND_WORKSPACE_CONTRACT_PHASE1`

---

## 1. Three Surfaces

Kosei has exactly three web surfaces. They share one Firebase project but serve different audiences with different auth gates.

```
┌──────────────────────────────────────────────────────┐
│                  kosei.ai (domain)                    │
│                                                      │
│  /              Public landing page (no auth)        │
│  /audit         Pre-audit intake form (no auth)      │
│  /app/*         Client workspace (auth required)     │
│  /admin/*       Operator workspace (012 auth)        │
└──────────────────────────────────────────────────────┘
```

### 1.1 Public Landing Page (`/`, `/audit`)

| Aspect | Value |
|--------|-------|
| **Auth** | None — anonymous visitors |
| **Purpose** | Explain service, capture leads, run pre-audit intake |
| **Stack** | Static PWA (Vite + React + TS), hosted on Firebase Hosting or Cloud Run |
| **i18n** | EN/JP toggle (two markets: global + Japan) |
| **Data writes** | `kosei_audit_requests` Firestore collection (intake form submissions) |
| **Data reads** | None (static content) |
| **Backend** | Cloud Function for intake processing (optional — can be client-side write to Firestore) |

**Pages**:
- `/` — Hero, value prop, CTA → `/audit`
- `/audit` — Pre-audit intake form (platform handles, content URLs, contact email, business goals)
- `/pricing` — Tier comparison (Trial / Starter / Professional / Enterprise)
- `/login` — Auth gate → redirects to `/app/` or `/admin/`

### 1.2 Client Workspace (`/app/*`)

| Aspect | Value |
|--------|-------|
| **Auth** | Firebase Auth (email/password or Google OAuth) |
| **Purpose** | Client reviews content, approves posts, views analytics, manages preferences |
| **Stack** | Same PWA, route-guarded |
| **Data writes** | Approvals, scheduling preferences, feedback, branding config |
| **Data reads** | Workspace config, content queue, post history, analytics |
| **Firestore collections** | `workspaces/{workspace_id}/*` (scoped by workspace) |

**Pages**:
- `/app/dashboard` — Content queue, upcoming posts, engagement summary
- `/app/content` — Review and approve pending content
- `/app/schedule` — Posting calendar, time preferences
- `/app/analytics` — Post performance, engagement metrics
- `/app/settings` — Branding (white-label), notification preferences, connected platforms
- `/app/billing` — Tier, usage, invoices (future — Stripe integration)
- `/app/support` — Issue submission, feedback form

### 1.3 Operator/Admin Workspace (`/admin/*`)

| Aspect | Value |
|--------|-------|
| **Auth** | Firebase Auth with admin claim (012 / 0102 agents only) |
| **Purpose** | Manage all clients, onboarding pipeline, system health |
| **Stack** | Same PWA, admin-route-guarded |
| **Data writes** | Client status updates, notes, trial decisions, escalation routing |
| **Data reads** | All workspaces, all audit requests, all trial states, system metrics |
| **Firestore collections** | Root-level read across all `workspaces/`, `kosei_audit_requests/`, `trials/` |

**Pages**:
- `/admin/leads` — Intake submissions, audit request pipeline
- `/admin/clients` — Active client list, workspace status, tier
- `/admin/onboarding` — Onboarding checklist per client, platform connection status
- `/admin/trials` — Active trials, expiry countdown, conversion prompts
- `/admin/notes` — Per-client follow-up notes, escalation log
- `/admin/metrics` — System-wide reporting (see Section 7 below)

---

## 2. Firebase Reuse — Truthful Assessment

### What exists and is reusable

| Infrastructure | Location | Reusable? | Notes |
|---------------|----------|-----------|-------|
| Firebase project | `gen-lang-client-0061781628` | YES | Shared project, Kosei gets its own collections |
| Firebase Hosting | Root `.firebaserc` | YES | Add `kosei` site target |
| Cloud Functions | `functions/index.js` | YES | Add Kosei-specific functions |
| Firebase Auth | Root project | YES | Same auth instance, add Kosei-specific claims |
| Firestore | Root project | YES | Kosei collections namespaced by `kosei_*` prefix |

### What does NOT exist yet

| Need | Status | Action |
|------|--------|--------|
| Kosei Firestore collections | NOT CREATED | Define in data model, deploy rules |
| Kosei Firestore security rules | NOT CREATED | Must be written before any client data |
| Admin auth claims | NOT CREATED | Cloud Function to set `{ admin: true }` custom claim |
| Kosei Firebase Hosting site | NOT CREATED | Add site target in `.firebaserc` |
| Email notifications | PARTIAL — Resend SDK exists in root functions | Extend for Kosei welcome/trial emails |

### Auth pattern decision

**Reuse Firebase Auth** (not Clerk). Rationale:
- GotJunk already uses Firebase Auth with anonymous + Google sign-in
- Root landing uses Clerk, but Clerk adds complexity and cost for a FoundUp that doesn't need SSO
- Firebase Auth is free tier for email/password + Google OAuth
- Admin claims via `auth.setCustomUserClaims()` — proven pattern

**Auth flow**:
1. Public pages: no auth
2. Client login: Firebase Auth (email/password or Google) → workspace scoped by `auth.uid`
3. Admin login: Firebase Auth + `admin: true` custom claim → full read access

---

## 3. Backend Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Public PWA   │    │ Client PWA   │    │ Admin PWA    │
│ (no auth)    │    │ (auth)       │    │ (admin auth) │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────┐
│              Firebase Cloud Functions                  │
│  submitAudit()  │  routeTask()  │  adminAction()     │
└──────────────────────────┬───────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                    Firestore                          │
│  kosei_audit_requests/  │  workspaces/  │  trials/         │
│  leads/           │  issues/      │  metrics/        │
└──────────────────────────────────────────────────────┘
```

**No custom backend server.** Firebase Cloud Functions + Firestore is sufficient for Phase 1-3. If Kosei outgrows Cloud Functions (latency, compute), migrate to Cloud Run (same pattern as GotJunk).

---

## 4. Route Ownership

| Route | Owner | Auth |
|-------|-------|------|
| `kosei.ai/` | Kosei public | None |
| `kosei.ai/audit` | Kosei public | None |
| `kosei.ai/pricing` | Kosei public | None |
| `kosei.ai/login` | Kosei auth gate | None → redirect |
| `kosei.ai/app/*` | Kosei client workspace | Firebase Auth (client) |
| `kosei.ai/admin/*` | Kosei admin workspace | Firebase Auth (admin claim) |
| `autopost.foundups.com/*` | AutoPost (external) | AutoPost's own auth |

Kosei NEVER serves AutoPost UI. AutoPost NEVER serves Kosei UI. They are separate PWAs on separate domains.

---

## 5. API Surface (Cloud Functions)

### Phase 1 functions

| Function | Trigger | Auth | Description |
|----------|---------|------|-------------|
| `submitAuditRequest` | HTTPS callable | None | Public intake form → `kosei_audit_requests/` |
| `processAuditRequest` | Firestore trigger on `kosei_audit_requests/` create | Backend | Run AI analysis, write `AuditReport` |
| `createWorkspace` | HTTPS callable | Admin | Provision client workspace after audit acceptance |
| `updateTrialStatus` | Scheduled (daily) | Backend | Check trial expiry, update `trials/` |
| `submitIssue` | HTTPS callable | Client auth | Client feedback/issue → `issues/` |

### Phase 2+ functions

| Function | Trigger | Auth | Description |
|----------|---------|------|-------------|
| `routeServiceRequest` | HTTPS callable | Client auth | Route content task to AutoPost or social_media_orchestrator |
| `setAdminClaim` | HTTPS callable | Existing admin | Grant admin role to new operator |
| `generateReport` | Scheduled (weekly) | Backend | Aggregate metrics → `metrics/` |

---

## 6. Consent Boundaries

| Data | Consent required? | How obtained | Storage |
|------|-------------------|-------------|---------|
| Email (intake form) | YES — explicit checkbox | "I agree to be contacted about Kosei services" | `kosei_audit_requests/{id}.contact_email` |
| Platform handles | YES — implicit by submission | User provides willingly in intake form | `kosei_audit_requests/{id}.platform_handles` |
| Content URLs | YES — implicit by submission | User provides willingly for audit | `kosei_audit_requests/{id}.content_urls` |
| Workspace data | YES — terms of service | Accepted at onboarding | `workspaces/{id}.*` |
| Analytics (client posts) | YES — data processing agreement | Part of service contract | `workspaces/{id}/analytics/*` |
| Admin notes | NO — internal operations | 012/agent operational notes | `workspaces/{id}/notes/*` |

**Deletion rights**: Client can request workspace deletion. All data in `workspaces/{workspace_id}/` is purged. Audit request records in `kosei_audit_requests/` are anonymized (email removed, handles removed) but not deleted (audit trail).

**Data residency**: Firebase project region (currently `us-central1`). Japan clients may require `asia-northeast1` — document as future migration path, not blocking for Phase 1.

---

## 7. Reporting Minimum Metrics

### Client-visible metrics (in `/app/analytics`)

| Metric | Source | Update frequency |
|--------|--------|-----------------|
| Posts published (count) | AutoPost delivery confirmations | Real-time |
| Posts pending approval | Client content queue | Real-time |
| Engagement summary (likes, comments, shares) | Platform APIs via social_media_orchestrator | Daily |
| Platform connection status | Integration health check | Hourly |
| Trial days remaining | `trials/{id}.days_remaining` | Daily |

### Operator-visible metrics (in `/admin/metrics`)

| Metric | Source | Update frequency |
|--------|--------|-----------------|
| Total active clients | `workspaces/` count where status=active | Real-time |
| Active trials | `trials/` count where status=active | Real-time |
| Trial conversion rate | `trials/` converted / total | Weekly |
| Audit requests (pipeline) | `kosei_audit_requests/` by status | Real-time |
| Issues open | `issues/` count where status=open | Real-time |
| Revenue (MRR) | Billing system (Stripe, future) | Monthly |
| Posts delivered (total across clients) | Aggregated from all workspaces | Weekly |

---

*Worker F — service contract defined. No runtime changes made.*
