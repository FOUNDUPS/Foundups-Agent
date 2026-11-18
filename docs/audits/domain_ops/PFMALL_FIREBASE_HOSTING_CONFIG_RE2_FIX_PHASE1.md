# PFmall Firebase Hosting Config — RE2 Fix + Reproducibility (Phase 1)

**Slice**: PFMALL_FIREBASE_HOSTING_CONFIG_REPRODUCIBILITY_AND_RE2_FIX_PHASE1
**Type**: CODE/CONFIG remediation (NOT deploy)
**Date**: 2026-06-13
**WSP**: 22 (ModLog), 50 (pre-action verification), 97 (truth boundary)

---

## 1. Problem

The DEPLOY slice `PFMALL_PUBLIC_BROWSE_HOSTING_DEPLOY_PHASE1` failed at finalization:

```
Error: Supplied header pattern invalid: error parsing regexp:
invalid or unsupported Perl syntax: `(?!`
```

Files uploaded; finalization rejected; **live site unchanged** (non-destructive).

**Root cause**: `firebase.json` used a negative-lookahead header pattern
`"regex": "^/(?!kosei/).*"`. Firebase Hosting header patterns are evaluated with
**RE2**, which does not support lookahead.

**Compounding hazard**: the entire Firebase hosting-config surface was gitignored,
so deploy behavior was machine-local rather than repo truth.

| File | Pre-fix state | Evidence |
|------|---------------|----------|
| `firebase.json` | ignored (`.gitignore:17`) | `git check-ignore -v`; `git ls-files` empty |
| `.firebaserc` | ignored (`.gitignore:21`) | `git check-ignore -v` |
| `firestore.rules` | ignored (`.gitignore:16`) | `git check-ignore -v` |
| `firestore.indexes.json` | ignored (`.gitignore:22`) | `git check-ignore -v` |

---

## 2. Firebase header semantics (authoritative)

Firebase Hosting `headers` rules are **LAST-MATCH-WINS**: all matching rules apply
cumulatively and, for a given header key, the **last** matching rule overrides earlier
ones. This is the opposite of `rewrites`/`redirects` (first-match-wins).

Source: firebase-tools issues #8917 and #9467 (Firebase engineering confirmation) +
`firebase.google.com/docs/hosting/full-config`.

The original lookahead was a workaround for rule **ordering**: the Kosei block was first,
the DENY rule second, so a DENY rule matching Kosei paths would have clobbered Kosei's
`X-Frame-Options: ""`. The author used `(?!kosei/)` to stop the DENY rule from matching
Kosei at all.

---

## 3. Fix (RE2-safe; no lookahead)

Removed the `regex` rule entirely. Restructured to rely on documented last-match-wins:

- **catch-all** `"source": "**"` -> `X-Frame-Options: DENY` (+ nosniff + referrer) **FIRST**
- Kosei `"source": "/kosei/app/**"` -> `X-Frame-Options: ""` (+ frame-ancestors CSP) **LAST**

Last-match-wins gives Kosei the empty-XFO override while every other route keeps DENY.
**Zero `regex` keys remain** -> the RE2 lookahead error class is structurally eliminated;
only `source` globs remain.

Kosei iframe policy preserved exactly: the `/kosei/app/**` block keeps its original
`X-Frame-Options: ""` + `frame-ancestors` CSP values (unchanged).

---

## 4. Route matrix proof

Header application is proven by documented last-match-wins (the hosting emulator does not
emit custom headers — see Section 5). Static/rewrite behavior is proven empirically on the
emulator.

| Route | Matching header rules (in order) | X-Frame-Options | Static/rewrite |
|-------|----------------------------------|-----------------|----------------|
| `/kosei/app/index.html` | `**` (DENY), `**/*.html` (cache), `/kosei/app/**` (XFO "") | **"" (no DENY)** — Kosei is last | static html |
| `/kosei/app/foo` | `**` (DENY), `/kosei/app/**` (XFO "") | **"" (no DENY)** — Kosei is last | rewrite -> index.html |
| `/f/` | `**` (DENY) | **DENY** | rewrite -> /f/index.html |
| `/f/public_catalog.json` | `**` (DENY), `**/*.json` (cache; diff key) | **DENY** | **static JSON** (precedence over `/f/**` rewrite) |
| `/member/` | `**` (DENY) | **DENY** | rewrite -> index.html |
| `/index.html` | `**` (DENY), `**/*.html` (cache; diff key) | **DENY** | static html |
| `/random` | `**` (DENY) | **DENY** | rewrite -> index.html |

Only Kosei app routes are exempt from `X-Frame-Options: DENY`; all others retain it.

---

## 5. Validation performed (non-production)

Firebase hosting emulator (`firebase emulators:start --only hosting`,
project `gen-lang-client-0061781628`, `127.0.0.1:5000`):

- **RE2 acceptance**: emulator parsed `firebase.json` and started cleanly — no
  header-pattern parse error (the exact failure production finalization raised). The
  regex error class is also structurally gone (0 `regex` keys).
- **Static-serving precedence (empirical)**:
  - `/f/public_catalog.json` -> `200`, `Content-Type: application/json`,
    `Content-Length: 2219` (exact repo file) — **not** swallowed by `/f/**` rewrite.
  - `/random`, `/f/` -> `200`, `text/html`, `Content-Length: 98748` (SPA `index.html`).
- **Header application NOT testable on emulator**: the hosting emulator emits no custom
  response headers on any route (confirmed: no `X-Frame-Options`/`X-Content-Type-Options`/
  `Referrer-Policy` on `/random` or any path). Header behavior is therefore proven by
  documented semantics (Section 2/4). Server-side header emission is confirmed at the
  next production (or preview-channel) deploy.

`json.load(firebase.json)` -> valid JSON.

---

## 6. Reproducibility decision

| File | Decision | Rationale |
|------|----------|-----------|
| `firebase.json` | **TRACK** (un-ignored) | Routing/headers only, no secrets; must be repo truth so deploy is reproducible across machines. |
| `.firebaserc` | leave ignored | Carries project binding; kept machine/operator-local by existing convention. |
| `firestore.rules` | leave ignored | Per the `.gitignore` comment, rules live per-module (`modules/foundups/gotjunk/firestore.rules`). |
| `firestore.indexes.json` | leave ignored | Deployment artifact; out of scope for this hosting slice. |

`.gitignore` updated: removed `/firebase.json`; added a comment noting it is tracked and
why. The other three remain ignored (verified post-edit).

---

## 7. Boundaries honored

- No production deploy run.
- No DNS / GoDaddy change.
- No `noindex`/`nofollow` change (still present on `/f/` by design — `CONTENT_DECISION_PENDING`).
- No application code / manifests / #799-#801 artifacts touched.
- No secrets read or printed.

---

## 8. Next step

After this lands, re-run `PFMALL_PUBLIC_BROWSE_HOSTING_DEPLOY_PHASE1`. Production
finalization will now accept the config (no RE2 regex). Optionally, a preview-channel
deploy (`firebase hosting:channel:deploy`) can confirm server-side header emission before
touching the live channel.
