# 01(02) Domain Fix Checklist

**Date**: 2026-04-06
**Worker**: L (FOUNDUPS_DOMAIN_TLS_AND_CANONICAL_HOST_FIX_PHASE1)
**For**: 012 — operator console actions

---

## Phase 1: Fix `www.foundups.com` (NOW)

### Step 1: Add `www.foundups.com` as Firebase custom domain

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select the project that owns `foundupscom` hosting site
3. Navigate: **Hosting** > **Custom domains**
4. You should see `foundups.com` already listed (status: Connected)
5. Click **Add custom domain**
6. Enter: `www.foundups.com`
7. Firebase will show DNS verification steps — BUT the CNAME already exists and points to `foundupscom.web.app`, so it should verify quickly
8. If Firebase asks for a TXT record for ownership verification, add it in GoDaddy DNS (see Step 2)
9. Wait for Firebase to show status: **Connected** and certificate: **Active**

**Expected time**: 5-30 minutes for TLS cert provisioning (Firebase uses Let's Encrypt / Google Trust Services)

### Step 2: GoDaddy DNS (only if Firebase asks for verification)

1. Go to [GoDaddy DNS Management](https://dcc.godaddy.com/) for `foundups.com`
2. If Firebase requests a TXT or ACME record, add it:
   - Type: TXT (or whatever Firebase specifies)
   - Host: `www` or `_acme-challenge.www` (as Firebase instructs)
   - Value: (whatever Firebase provides)
3. Save. DNS propagation is usually fast for TXT records (minutes).
4. Return to Firebase Console and click verify/retry.

**Note**: The existing CNAME record (`www` -> `foundupscom.web.app`) should remain. Do not delete it.

### Step 3: Configure redirect behavior

After `www.foundups.com` is connected in Firebase:

1. In Firebase Console > Hosting, check if there's an option to redirect `www` to apex
2. If Firebase supports it natively: enable "redirect www to apex"
3. If not: the `firebase.json` catch-all rewrite will serve the same content on both

**Ideal end state**: `www.foundups.com` 301 redirects to `foundups.com`

### Step 4: Verify

After Firebase shows the custom domain as Connected:

```bash
# Test TLS (should show CN=www.foundups.com or SAN including it)
echo | openssl s_client -connect 199.36.158.100:443 -servername www.foundups.com 2>&1 | grep -i "subject\|DNS:"

# Test HTTPS (should get 200 or 301)
curl -sI https://www.foundups.com/

# Test redirect (should go to foundups.com)
curl -sIL https://www.foundups.com/ | grep -i "location\|HTTP"
```

---

## Phase 2: `mall.foundups.com` (DEFERRED)

**Do not execute these steps now.** Listed for future reference when 012 decides to activate.

### Prerequisites before activating `mall.foundups.com`

- [ ] Architectural decision: Does `mall.foundups.com` serve `public/member/` content or new content?
- [ ] Clerk auth: Add `mall.foundups.com` as allowed origin in Clerk dashboard
- [ ] Decide: Does `foundups.com/member/` redirect to `mall.foundups.com` or coexist?

### When ready to activate

1. **GoDaddy DNS**: Add A record or CNAME for `mall.foundups.com`
   - Option A (A record): `mall` -> `199.36.158.100` (same as apex)
   - Option B (CNAME): `mall` -> `foundupscom.web.app`
2. **Firebase Console**: Add `mall.foundups.com` as custom domain (same process as www fix)
3. **Firebase routing**: If `mall` should serve different content than apex, update `firebase.json` with host-based routing (requires Firebase Hosting `hosting` array with multiple sites, or rewrite rules)
4. **Verify**: DNS + TLS + content serving
5. **Update canonical**: If mall becomes the canonical mall URL, update `public/member/index.html` meta tags

---

## What NOT to do

- Do NOT delete the existing CNAME for `www` in GoDaddy
- Do NOT add `mall.foundups.com` DNS records until the architecture decision is made
- Do NOT change `firebase.json` rewrites for the www fix (it's console-only)
- Do NOT touch `vercel.json` (it's the API backend, unrelated to domain hosting)
- Do NOT change canonical URL tags in HTML (current `foundups.com` canonical is correct)

---

## Post-Fix Verification Checklist

After 012 completes Phase 1:

- [ ] `curl -sI https://www.foundups.com/` returns 200 or 301 (not TLS error)
- [ ] `openssl s_client -servername www.foundups.com` shows cert with `www.foundups.com` in subject/SAN
- [ ] `https://foundups.com/` still returns 200 (no regression)
- [ ] `https://foundups.com/member/` still loads pfMALL (no regression)
- [ ] Firebase Console shows both `foundups.com` and `www.foundups.com` as Connected

---

## GoDaddy System Access Question

012 asked about giving system access to manage the GoDaddy page.

**Options**:

1. **GoDaddy Delegate Access**: GoDaddy supports adding users to manage DNS. Go to GoDaddy Account > Settings > Delegate Access. This allows another person/account to manage DNS without sharing the main login.

2. **GoDaddy API**: GoDaddy has a DNS management API (api.godaddy.com). An API key+secret pair can be generated from the GoDaddy Developer Portal. This could allow automated DNS management but is NOT needed for the www fix (which is Firebase-console-only).

3. **For this fix specifically**: GoDaddy access is likely not needed at all. The CNAME for `www` already exists and is correct. The fix is entirely in Firebase Console. GoDaddy is only needed if Firebase requests a DNS verification record.
