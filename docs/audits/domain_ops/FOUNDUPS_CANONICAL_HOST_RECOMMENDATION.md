# FoundUps Canonical Host Recommendation

**Date**: 2026-04-06
**Worker**: L (FOUNDUPS_DOMAIN_TLS_AND_CANONICAL_HOST_FIX_PHASE1)

---

## Recommendation

### RECOMMEND KEEP CANONICAL = `foundups.com/member/`

### RECOMMEND DEFER `mall.foundups.com`

---

## Reasoning

### Why keep `foundups.com/member/`

1. **It works now.** Live, TLS valid, content serving correctly.
2. **SEO**: `public/member/index.html` has `noindex, nofollow` — no SEO equity to protect or migrate.
3. **Auth**: Clerk is configured with the current domain. Domain change = Clerk origin change = auth breakage risk.
4. **Simplicity**: Path-based routing (`/member/`) under `foundups.com` is one hosting surface, one cert, one deploy.

### Why fix `www.foundups.com`

1. Users type `www.` by habit. Currently they hit a TLS wall.
2. Fix is trivial: add custom domain in Firebase Console. Firebase auto-provisions cert.
3. After fixing, `www.foundups.com` should 301 redirect to `foundups.com` (Firebase supports this).

### Why defer `mall.foundups.com`

1. **No DNS record exists.** Activating requires: DNS A/CNAME record + Firebase custom domain registration + TLS provisioning + content routing decision.
2. **Routing ambiguity**: Would `mall.foundups.com` serve `public/member/` or something new? This is an architectural question, not an ops question.
3. **Auth scope**: Clerk publishable key is domain-scoped. Adding a new domain requires Clerk configuration.
4. **No urgency**: Current path (`/member/`) works. Mall subdomain is a future enhancement, not a fix.
5. **Premature activation risk**: If `mall.foundups.com` is created in DNS before Firebase routing is ready, it will show Firebase's default page or 404.

### Canonical host: `foundups.com` (apex, no www)

- `foundups.com` -> serves content (200 OK)
- `www.foundups.com` -> should 301 redirect to `foundups.com` (after fix)
- `mall.foundups.com` -> deferred until intentionally provisioned

This matches the existing `<link rel="canonical" href="https://foundups.com/">` in `public/index.html` and all OG/Twitter meta tags.

---

## WSP 97 Applied

Decision tree: live DNS/TLS truth -> root cause analysis -> minimal fix (console-only for www) -> defer speculative changes (mall subdomain). No code changes to routing. No domain migration.
