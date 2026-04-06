# FoundUps Domain & Hosting Audit

**Date**: 2026-04-06
**Worker**: L (FOUNDUPS_DOMAIN_TLS_AND_CANONICAL_HOST_FIX_PHASE1)
**WSP**: 15 (prioritization), 97 (CoT/CoR)

---

## 1. Hosting Ownership Determination

### Firebase Hosting (AUTHORITATIVE for public website)

- **Site ID**: `foundupscom`
- **Config**: `firebase.json` — serves `public/` directory
- **Rewrites**: `/f/**` -> `/f/index.html`, catch-all -> `/index.html`
- **Custom domain**: `foundups.com` (A record -> `199.36.158.100`)
- **www CNAME**: `www.foundups.com` -> `foundupscom.web.app`
- **Headers**: Security headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- **Content**: Landing page (`public/index.html`), Mall (`public/member/`), FoundUp bridge (`public/f/`)

### Vercel (SEPARATE — Python API backend only)

- **Config**: `vercel.json` — runs `main.py` via `@vercel/python`
- **Routes**: `/api/holoindex`, `/api/search`, catch-all to `main.py`
- **Region**: `iad1`
- **NOT serving the public website**

### `.firebaserc` State

- Root `.firebaserc`: Empty `projects: {}, targets: {}, etags: {}`
- `gotjunk/.firebaserc`: Points to `gen-lang-client-0061781628` (separate GCP project)

**Note**: Root `.firebaserc` has no project binding. Deploys to `foundupscom` must use `firebase deploy --project <project-id> --only hosting:foundupscom` or the project must be set.

---

## 2. Authoritative Answer

**Firebase Hosting is the sole authoritative platform for the public FoundUps website.**

Vercel is a separate backend API surface with no overlap on public domain serving.

There is **no split ownership conflict** — these serve different purposes.

---

## 3. Live DNS State (2026-04-06)

| Domain | Record | Resolves To | Status |
|--------|--------|------------|--------|
| `foundups.com` | A | `199.36.158.100` | LIVE, WORKING |
| `www.foundups.com` | CNAME | `foundupscom.web.app` -> `199.36.158.100` | DNS OK, **TLS BROKEN** |
| `mall.foundups.com` | (none) | Does not resolve | NO DNS RECORD |

---

## 4. Live HTTPS State (2026-04-06)

| Domain | HTTPS | Cert CN | Cert SANs | Result |
|--------|-------|---------|-----------|--------|
| `foundups.com` | 200 OK | `foundups.com` | `DNS:foundups.com` | WORKING |
| `www.foundups.com` | TLS FAIL | `firebaseapp.com` | (not covering www) | **SEC_E_WRONG_PRINCIPAL** |
| `mall.foundups.com` | DNS FAIL | N/A | N/A | Cannot connect |

---

## 5. Current Route Map

| URL | What it serves |
|-----|---------------|
| `https://foundups.com/` | Landing page (public/index.html) |
| `https://foundups.com/member/` | p.fMALL (public/member/index.html) |
| `https://foundups.com/f/{id}` | FoundUp bridge (public/f/index.html) |
| `https://www.foundups.com/` | BROKEN (TLS mismatch) |
| `https://mall.foundups.com/` | NONEXISTENT (no DNS) |
