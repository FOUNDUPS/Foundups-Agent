# Security audit remediation — 2026-10-10

Scope: source at main `b4f1a97bb2992e391634f83f949da6ee314c11a7`, seven npm lockfiles, WRE/scanner/CI, GotJunk rules/API/client, and eSingularity Sites source `90e539f760b6aefab027676ae7dff1ad2862e643`. This is evidence of source remediation and scoped validation, not certification that every code path or deployed environment is secure.

## Implemented corrections

| Area | Correction | Evidence |
| --- | --- | --- |
| Scanner F01/F02 | Fail on operational exits/error or malformed JSON; preserve Trivy vulnerabilities, secrets and misconfiguration categories without normalized secret values | Scanner regression and real-policy tests |
| WRE F03/F09/F10 | Exit 2 for incomplete coverage, preserve category/location and partial findings, propagate controller failures, trigger on source and modern lockfiles | Focused executor/controller/trigger and policy tests |
| CI F04 | Checksum-pinned Gitleaks, blocking tracked-tree plus introduced-commit scanning, nested environment-file guard, Monday full retained history | 14 tests and actual binary synthetic credential tests; reviewed exceptions bound to exact file bytes/rule/location |
| GotJunk F05–F07 | UID-bound uploads, append-only authenticated authors, owner-only thread administration, caller-bound votes, bounded reservations, identical rule mirrors | Nine emulator scenarios including actual TypeScript concurrent appends/votes |
| GotJunk F08 | Firebase JWT verification, exact configured origins, preparse body bounds, bounded per-process write admission, fail closed without identity configuration | Seven backend tests; production identity/runtime remains unverified |
| GotJunk release | Emulator gate, deploy matching Firebase rules before frontend, upload only tracked source to Cloud Build, actually fail missing security headers | Exact Firebase project checked against source; deployment permissions must be verified by real CI |
| eSingularity F11 | 8 KiB streamed JSON limit, validation/origin checks, transactional client/global quota, 24-hour email deduplication, generic errors/no-store | Eight handler and actual SQLite tests including UTC day rollover |
| eSingularity F12 | Move unpublished portraits and unused unblurred originals outside public assets; preserve approved 012/0102 images | Publication-boundary test; build/live exclusion checked separately |
| Public session identifiers | Replace weak Math.random/time fallback with crypto.randomUUID | Narrow source diff; animation randomness unchanged |
| IDE webview | Render external insight data via textContent rather than HTML/template interpolation | Malicious-markup regression passes |

## Dependency result

npm audit public advisory metadata was used with operator authorization. Counts include multiple affected dependency nodes from the same advisory; they are not a count of demonstrated exploit paths. No forced incompatible audit downgrade was accepted.

| Project | Before | After |
| --- | ---: | --- |
| Root tooling | 35 | 23 high |
| Firebase Functions | 23 | 2 high, 8 moderate |
| Clerk integration | 18 | 5 high |
| Claude WRE extension | 1 | 0 |
| eSingularity | 20 | 8 high |
| GotJunk | 14 | 0 |
| IDE extension | 26 | 0 |
| Total | 137 | 46; zero critical |

All five reported critical findings were removed. Next 16.3.8, React/RSC 19.2.8 and Vite 8.0.16 remove the identified website runtime/toolchain advisories. Matching vinext/Cloudflare peers and compatible scoped overrides were installed from exact lockfiles. GotJunk build and Claude WRE compilation passed; Vercel CLI version/deploy-help smoke tests passed. All seven installs/manifest-lock declarations validated.

Remaining: braces has no patched release indicated by the audit and propagates through development tooling; latest Vercel still pins vulnerable undici 5 / busboy 2; Functions requires Firebase major migration to remove node-forge/old uuid chains. `functions/index.js` is absent, so application compatibility cannot be validated. Clerk prerender needs its publishable key. IDE has existing missing WRE/orchestrator APIs and other type errors, so its full compile remains blocked. These issues are not suppressed or marked fixed.

## Validation and release boundaries

- Parent combined scanner/WRE/secret-gate suite: 134 passed; independent lane additionally ran policy/stack tests. eSingularity existing module contracts: 82 passed; domain-routing contracts: 18 passed; security tests: eight passed. TypeScript check passed after correcting pre-existing duplicate translation keys while preserving displayed values, and splitting the PWA icon purpose entries.
- GotJunk emulator tests use Firebase CLI 14.27.0, test credentials and temporary local services only. Rule deployment must use `gen-lang-client-0061781628`; failure of existing Google ADC permissions blocks rollout. The separate Python API is not proven deployed by the static Cloud Run workflow.
- A full retained historical secret scan has not yet been certified clean. The new weekly run must triage historical findings. No blanket directory/test/provider allowlist is used.
- The removed Cesium browser token remains in Git history and requires provider-side revocation/restriction. This connection has no verified Cesium account authority. No token value is reproduced in this report.
- GitHub rulesets were read: active default-branch PR rule, no required status-check rule. Classic branch-protection inspection returned HTTP 403 for this integration. Requiring `security / secrets` needs repository administration access; a workflow alone does not enforce merge protection.
- Application quotas bound accepted submissions, not volumetric ingress or provider billing. GotJunk's API limiter is per process; deployment needs ingress/distributed quotas. No unverified WAF configuration is claimed.
- The daily 0102 review automation and existing WRE/OpenClaw adapters are separate systems. No Red Dog daemon, SEC9 runtime enrollment or new production overseer was activated by these source changes.
- Publication/merge receipts belong to the release record and PR checks. A passing local build or Git merge is not itself proof of production rules, IAM, runtime configuration or custom-domain behavior.

## Retrieval and scope discipline

WSP00 used the documented torch-free fallback; no detector witness was fabricated. Source-bound lexical Holo retrieval retained UNKNOWN freshness/index-gap labels. Direct owner/source inspection resolved missing artifacts. Existing module owners were extended under WSP22/50/77/97. No Gmail messages, security alerts or private correspondence were sent, dismissed or mutated. No user submissions were deleted. Moving static assets does not erase historical copies or make the public Git repository a confidential store.
