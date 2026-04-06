# FoundUps TLS Issues & Root Cause

**Date**: 2026-04-06
**Worker**: L (FOUNDUPS_DOMAIN_TLS_AND_CANONICAL_HOST_FIX_PHASE1)

---

## The Problem

`https://www.foundups.com/` fails with TLS certificate mismatch:

```
SEC_E_WRONG_PRINCIPAL (0x80090322) - The target principal name is incorrect.
```

Browsers refuse the connection. Users hitting `www.foundups.com` get a security error, not a redirect.

---

## Root Cause

### DNS is correct

`www.foundups.com` CNAME -> `foundupscom.web.app` -> resolves to `199.36.158.100` (Firebase Hosting IP).

The DNS chain is working. Traffic reaches Firebase's servers.

### Certificate is wrong

When Firebase receives a TLS handshake with SNI `www.foundups.com`, it serves:

```
Subject: CN=firebaseapp.com
SANs:    (does not include www.foundups.com)
```

This is Firebase's **default/fallback certificate**. It means Firebase Hosting does not have `www.foundups.com` registered as a custom domain for this site.

### Comparison: `foundups.com` works

The apex domain has a properly provisioned certificate:

```
Subject: CN=foundups.com
SANs:    DNS:foundups.com
```

This confirms `foundups.com` IS registered as a custom domain in Firebase Hosting. `www.foundups.com` is NOT.

### Why Firebase also returns 404

Even with `-k` (skip TLS verify), Firebase returns `404 Not Found` for `www.foundups.com`. This is because Firebase Hosting routes by hostname — if the hostname is not registered as a custom domain, there is no site to serve, regardless of CNAME target.

---

## Root Cause Summary

| Layer | State |
|-------|-------|
| DNS record for `www` | Correct (CNAME to `foundupscom.web.app`) |
| Firebase custom domain for `www` | **NOT REGISTERED** |
| Firebase TLS cert for `www` | **NOT PROVISIONED** (falls back to `firebaseapp.com`) |
| Firebase routing for `www` | **404** (no site mapped to this hostname) |

**Fix location**: Firebase Console > Hosting > Custom domains > Add `www.foundups.com`

This is a **console-only fix**. No code changes, no DNS changes. The CNAME already exists and is correct.

---

## Why This Happened

Most likely: when the `foundups.com` custom domain was added in Firebase, only the apex was registered. Firebase does not automatically create custom domain entries for `www` — each must be added explicitly. The CNAME was created in GoDaddy DNS, but the Firebase side was never completed.
