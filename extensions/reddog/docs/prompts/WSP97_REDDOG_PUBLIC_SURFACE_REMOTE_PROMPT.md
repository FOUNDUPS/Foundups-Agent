# Remote work order: RedDog public host and first mobile adapter

Status: work order only; not completion or execution authority by itself.
Origin: external principal 012. Role: 0102 architect/engineer.

## Recover and isolate

Read `AGENTS.md`, WSP_00, WSP_97, WSP_10, WSP_15 and the RedDog documentation map.
Run the actual WSP_00 bootstrap and tracker from the canonical repository root.
Record exact current HEAD, status, worktrees, open owned PRs and available model
bindings. Do not reuse, reset or stage another worker's changes. Create a new
owned worktree/branch from verified current main.

Read `extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md` and its tests.
This source slice has **no mounted live host, deployed UI, authenticated owner
flow, 3V engine invocation, or voice/context-delta implementation**.

## HoloIndex before expansion

Use the canonical owner query in `AGENTS.md`, resolving the main/control root
through Git's common directory. Run the exact regression query in the admission
document. Require a current no-gap receipt, not merely a successful process exit.

On failure preserve the error and its original request/HEAD. Retrieve the current
owner incident classifier and governed post-merge repair/controller. Repair only
through that authority, run its closest existing tests, and requery before
returning to RedDog. Missing runtime configuration is not permission to alter
Holo source, widen timeout/freshness gates or reindex from the query path.
Record the retrieval case and held-out evaluation; do not claim recursive
improvement just because a query was attempted.

## First implementable scope

1. Inventory the existing authenticated resident host, public ingress, AgentDB
   connection factory, deployment routes and public-only model topology. Do not
   create a second host, queue, database or camera stack for convenience.
2. Review `PublicSessionGate` with the actual SQLite DatabaseManager wrapper,
   process concurrency, restart/crash and clock behavior. Prove orphaned busy-slot
   recovery through owned process/lease evidence; never erase counters or allow
   a second inference merely to clear an error.
3. Bind an independently reviewed zero-tool, public-only responder. Its input is
   PublicTurn, not the principal Memex or private resident work envelope. Enforce
   max output tokens and provider-side deadlines. No arbitrary URL/model selection
   from browser input and no private OpenClaw fallback.
4. Supply edge-authenticated subject accounting, TLS, origin routing, rate limits,
   key custody and shared budgets across replicas/surfaces. The existing direct
   peer HMAC is not sufficient attribution behind an unverified proxy.
5. Mount the router on the proven host only after those tests pass. Leave public
   exposure disabled when any dependency is unavailable.

## Then add surfaces, one at a time

Start inside the existing `FOUNDUPS/autopost` UI, not a copied monorepo camera.
Verify its actual post-redirect origin first. Reuse capture, correction and media
ownership. Add camera-off text conversation first; voice is a separately measured
adapter. Public guest conversation must not inherit the monk's private session.

Add the same thin public guest adapter on foundups.com and the canonical
`modules/foundups/esingularity/frontend` surface. Confirm deployment ownership
before editing. Keep public conversation consent distinct from recording,
biometrics, publishing and private-memory disclosure.

Client obligations: show consent and guest status; render output as text, not
trusted HTML; expose remaining turns and expiry; respect 429/410/503; do not
retry a consumed nonce; do not save credentials or raw conversation to localStorage.
A timeout consumes budget. Do not claim "sent", "saved", "remembered" or
"executed" from model text.

## Identity and 3V

Lick contributes to Verification. It does not perform Validation/Valuation or
authorize work. Keep unsigned public evidence explicitly unsigned/unverified.

A human account uses a separately verified possession-bound challenge. An agent
uses its own key/registration and bounded delegation. A voice/name/knowledge
answer, including `tSingularity`, proves neither. Never block assistive-AI users
merely because they receive assistance. Higher authenticated tiers retain
explicit budgets and independent work authority.

## Acceptance and publication

Read existing TestModLog/README and nearest tests before adding cases. Extend
this suite for same-boundary scenarios. Register new test files using the
canonical generator; do not hand-edit counts or skip its check.

Verify: wrong origin, spoofed forwarded identity, cross-surface/private-scope
leakage, expired and replayed nonce, parallel over-cap requests, restart quotas,
withdrawal during a response, body/output bounds, provider cancellation ignored,
clock rollback, unavailable DB/model, synthetic public/private canaries, and
`tSingularity` as ordinary capped text.

Run targeted tests, dependency/security tiers, required CI and exact-host live
acceptance. Record commands and results honestly. Keep deployment distinct from
source merge. Publish a clean PR; squash only when the applicable checks pass.
Preserve unowned work and report remaining blockers with exact receipts.

Return to the existing dual-loop work: authenticated private turn/status/cancel
handlers -> authorized Memex/context-delta admission -> fast surface injection
-> voice -> omission critic and WSP_15 intervention ranking -> governed workers.
Do not implement every layer in one unreviewable change.
