# Member-authenticated draft intake — pre-authoring allocation

Date: 2026-10-26 JST. Self0102, rolearchitect, originautonomous_trigger;
external authority: 012's continuing FoundUps delivery instruction.
Parent: `4f37c8505c91f03d90c60ce835f1bc9b102491a8`.
WSP00 strict gate passed before retrieval. WSP3/6/11/15/22/49/50/62/77/84/97/109.

## Problem and selected component

The existing member browser uses Clerk, while the existing genesis HTTP-neutral
adapter verifies only internal HMAC session/invite tokens and has no concrete
HTTP caller. A browser UID, invite flag, issue author or host GitHub credential
cannot authenticate a project representative. Implement one connected local
component: real Clerk bearer verification -> existing proposal preflight and
genesis mapper -> explicitly labelled draft response at `POST /pfmall/proposals`.
This is a prerequisite, not the complete public repository-claim component.

Canonical WSP15 allocation: C3/I4/D4/Impact4 = **15/P1**. Need: authenticate the
actual product's identity instead of building another unused proof codec.
Affordability: two product owners, bounded offline RSA and HTTP tests, no model,
provider, paid media, new service or runtime activation. Deferral blocks the next
claim challenge/receipt integration. Execute tests before product implementation.

## Retrieval and alternatives

Current source read: PFMall README/INTERFACE/ROADMAP/ModLog/test inventory and
HTTP owner; genesis auth/transport/launch-request/nomination owners and module
docs/tests; project-claim architecture section7; adjacent RedDog/pAVS feasibility
report. Holo query at this parent returned
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH` against authority `a519f0ad`; freshness
UNKNOWN, index gap true. No semantic authority/reindex is claimed. Lexical
navigation's Firebase login leads are stale; direct current Clerk source wins.
PFMall requirements and memory README are absent, not silently retrieved.

Source-only donor inspection found no server authentication in the ignored local
signup handler, and local ignored rules permit client membership-field writes.
Deployed functions/rules were not inspected: this is not a production exposure
or incident conclusion. Donors are neither copied, imported nor executed.

Competing moves: GitHub-native nomination already supplies advisory drafts, not
member identity; generic OpenClaw ingress has a different execution trust domain;
GotJunk Firebase verification is a different identity provider. Preserve those
owners. Adding HMAC minting would create a second public login bridge. The full
Clerk SDK7 dependency set also requires cryptography>=45 while the FoundUps
umbrella file constrains it below42; do not migrate that umbrella incidentally.
Clerk explicitly supports manual JWT verification. Use maintained PyJWT2.15.1
with fixed server public-key/algorithm policy in an optional HTTP profile; do not
use the shared host's older2.12.1 as new-auth qualification.

Qwen/Gemma heuristics cannot prove authentication. Existing WSP77 review lane
independently selected this concrete host; actual signature/HTTP tests supply
the deterministic oracle. No model inference is claimed.

## Assumptions and failure modes

| Assumption | Evidence and confidence |
|---|---|
| Clerk is the current member identity provider | Current `public/member/index.html`, HIGH for source, deployment unknown |
| PFMall can own thin external HTTP wiring | Existing FastAPI app and module interface, HIGH; amendment below is explicit |
| Existing genesis mapper must stay pure | Current mapper/transport and unchanged AST tests, HIGH |
| Server configuration is independently administered | Required deployment input; not established by this PR |

| Failure | Impact | Mitigation and acceptance |
|---|---|---|
| Client UID/membership/body assertion becomes authority | HIGH | Bearer-only, no cookies/invites/UID fallback; unchanged proposal allowlist before auth |
| Wrong issuer/origin/algorithm or forged token | HIGH | Fixed public RSA key>=2048, RS256 only, exact issuer/azp/Origin, signed v2 user/session claims; real negative signatures |
| Expired/future/pending/overlong or audience-confused token | HIGH | Required strict integer times, zero skew, <=120s TTL, reject pending/status claims and any `aud` claim in this profile |
| Secret/identity/token leak or expensive hostile input | HIGH | Generic responses, pseudonymous subject binding, no raw-token repr/logging; 8KiB bearer/16KiB body, bounded read time |
| Config absence accidentally permits anonymous proposals | HIGH | Route503 until explicit valid server-owned policy, dependencies loaded only for configured authentication |
| Authentication silently grants ownership/work/token rights | HIGH | DRAFT_ONLY/IDEA/UNBOUND, no writes, nonce use, fetch, registry or runtime callbacks |
| Offline JWT accepted after remote session revocation | HIGH for later privileged use | Only a draft grant here; expiry<=120s, no standing claim authority. Current-session/revocation evidence required for later claim consumption |

## Explicit interface amendment and budget

The existing HMAC provider remains sole verifier for its unchanged legacy
contract. Authorize exactly one additional server-only Clerk wrapper to use
`intake_request`'s existing provider seam after its body preflight. Do not relax
HMAC token extraction, default provider, signature, nonce semantics or tests.
The wrapper captures only transport bearer/origin plus trusted policy, never
body authentication. It invokes verification when that existing seam is called.

Product: existing `modules/foundups/pfmall/http_api.py` <=260 lines, and one new
`modules/ai_intelligence/ai_overseer/src/foundup_genesis/clerk_intake.py` <=220
lines. Helpers <=50 lines; no new general auth/registry/service framework.
Tests: one materially distinct RSA/HTTP owner in PFMall <=500 lines, reuse all
existing HMAC/mapper/transport owners unchanged. At most22 changed paths total,
including owner docs/logs, optional HTTP requirements, existing CI, canonical
test registry, navigation and final evidence. Any expansion returns to allocation.

## Frozen acceptance and verification tiers

1. Default503; ordinary public GET contracts remain unchanged and importable
   without optional JWT/crypto packages. No environment/credential autoload.
2. Real ephemeral RSA-signed bearer reaches this actual HTTP app and unchanged
   genesis mapper; DRAFT_ONLY, IDEA/UNBOUND, no external repo/authority claim;
   requested_by binds issuer+case-sensitive subject, never caller username.
3. Forged/wrong-key/none/HMAC algorithms, issuer/azp/Origin mismatch, absent or
   duplicate bearer, cookie/invite fallback, wrong v/sub/sid, any aud/sts and
   missing/invalid/expired/future/overlong times reject generically. Independent
   review additionally requires rejecting any `act` claim until impersonation
   actor/subject policy is separately supported; add these cases before product.
4. Existing complete body allowlist precedes verification; invalid/oversize/
   malformed/authority-bearing proposals cause no verifier call. Actual streamed
   bytes, duplicates/encoding/content-type and read-timeout enforce wire limits.
5. No raw bearer, PEM, stable subject/session ID in response/errors/repr. No
   network/JWKS, storage/nonce, fetched code, registry/catalog/work/token effects.
6. Preserve exact parent test IDs/outcomes: existing HTTP routes, five nomination/
   mapper/auth/transport/validator owners. Add relevant dependency/security and
   independent held-out review; current Holo gap precludes a whole-closure claim.
7. Dedicated PR, exact-head hosted/security gates, guarded main convergence and
   affected main readback. No public deployment or protected runtime promotion
   without WSP6's independently admitted release/runner and real provider inputs.

HTTP ingress is the existing local FastAPI plane; WRE is not applicable to this
non-orchestrated draft request. It creates no resident continuity, autonomous
work, durable state or supervisor. Later repository challenge+immutable receipt
must select its durable owner and recheck session/revocation/control atomically.
No browser button is advertised until a real deployed service is qualified.

Decision: **PROCEED**, 0102/architect, 2026-10-26 JST, for the allocated component
only. Repository control, claim persistence, reviewed catalog publication, chain
issuance, financial signing and deployment remain incomplete.

Primary references: [Clerk verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification),
[session claims](https://clerk.com/docs/guides/sessions/session-tokens),
[PyJWT API](https://pyjwt.readthedocs.io/en/stable/api.html),
[security changelog](https://pyjwt.readthedocs.io/en/stable/changelog.html).

## Independent configuration finding — pre-repair amendment

Initial implementation frozen at `fff44de998c6e9eb13e78ad450173bcfa8cbd3d1`.
Independent actual-ASGI/RSA review passed10 functions and found one configuration
failure: the crypto parser accepts a public PEM followed by a private PEM, leaving
the latter retained in the public-key field. This is server configuration hygiene,
not a remote bearer bypass or observed exposure. Allocate four existing-owner
regressions before repair: appended private/public/junk reject, ordinary CRLF
public key remains accepted. Require a single canonical SubjectPublicKeyInfo
public PEM, with CRLF normalization; no custom cryptography or private input
retention. Existing product/test/file/function ceilings remain sufficient.

## Observed secrets-gate closure allocation — 2026-10-26

Current-head hosted CI40234746648/job121293788908 reports exactly two rows:
one tree and one introduced-history `generic-api-key` finding, both at line12
of the fixed member-intake evidence receipt. The line records the public,
reproducible normalized source hash of `pfmall/http_api.py`; receipt contents
differ between initial13cedc569 and currentcf7ad0a0c, so their whole-file-bound
fingerprints are distinct. No credential match value is displayed or retained.

Allocate C2/I4/D4/Impact3=13/P1 security closure, within the original22-path
ceiling. Before any ledger mutation, independently compare the two exact source
contexts, recompute their source-hash values and scanner fingerprints, and verify
the current2417-entry ordered ledger prefix. If both are confirmed public source
metadata, append only their two individual bindings to the existing reviewed
ledger. Preserve every prefix entry/other key. No detector, rule, fingerprint
algorithm, scan/history scope, test oracle, unknown finding or GitGuardian record
change is permitted. Fresh exact-head security and all other gates must pass;
this allocation is not itself a passing scan or disposition.

## Patched optional HTTP profile — pre-change amendment

Do not merge the5134 candidate on green functional/secrets checks alone. A fresh
public PyPI metadata audit of its24 resolved development distributions found
published advisories for Starlette0.50.0 and cryptography46.0.7. For example,
Starlette GHSA-82w8-qh3p-5jfq is fixed in1.3.1; cryptography
GHSA-g6cj-pr64-35w5 is fixed in50.0.0. These advisories do not by themselves prove
this JSON-only RSA route exploitable, but do not introduce those versions in a
new optional profile. Initial environment/results remain historical evidence.

Allocate C3/I4/D4/Impact4=15/P1, before changing pins. Select current stable
FastAPI0.162.0, Starlette1.10.0, PyJWT2.15.1 and cryptography50.0.2, verified from
their official PyPI metadata (no published advisories there at inspection).
FastAPI's current dependency contract permits Starlette1.10.0; do not force an
unsupported newer Starlette under old FastAPI0.128. Keep minimal package extras;
no provider, telemetry exporter, resident/umbrella or shared-venv migration.

Create a separate external qualification environment, retaining the first one
unchanged. Rerun the identical786 cases and independently authored11 ASGI/RSA
held-outs plus optional-import probe; compare exact IDs/outcomes and all legacy
source/test oracles. Inspect the entire newly resolved package inventory against
current public registry advisory metadata. This is not a complete security,
installed binary/platform, or live deployment qualification.

Only optional requirements, its existing CI install line and owner docs/evidence
may change; no product logic or test expectation changes to accommodate pins.
One additional patched-profile evidence receipt is permitted within the original
22-path ceiling. The older receipt is a retained V1 environment experiment, not
the final profile; do not rewrite it or its reviewed fingerprint contexts.
Fresh exact-head hosted/security/main-convergence gates remain required.

Independent installed-inventory comparison additionally found bootstrap pip25.0.1
outside the25 resolved application/test distributions, with published advisories.
Before changing installer tooling, extend this same optional-profile allocation
to pin pip26.2.2 in the isolated qualification environment and existing CI install
step; official PyPI currently lists no advisories for that release and supports
Python3.12. Retain the original bootstrap/inventory observation. Record a separate
installer acquisition report and inspect all26 installed distributions, without
claiming that registry metadata proves binary/platform safety. No global/shared
pip upgrade, product/test change, extra SDK or new path is authorized by this
amendment. Independent source/held-out qualification and fresh hosted gates remain
required after the tooling repair.

Primary advisory references:
[Starlette](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq),
[cryptography](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5).
