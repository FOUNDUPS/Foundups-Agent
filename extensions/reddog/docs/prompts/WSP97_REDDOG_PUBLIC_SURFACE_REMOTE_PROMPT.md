# Remote work order: RedDog public host and first mobile adapter

Status: work order only; not completion or execution authority by itself.
Origin: external principal 012. Role: 0102 architect/engineer.

Canonical navigation: [RedDog documentation map](../../../../docs/REDDOG_DOCUMENTATION_MAP.md) ·
[public admission contract](../REDDOG_PUBLIC_SURFACE_ADMISSION.md) ·
[test inventory](../../../../modules/communication/moltbot_bridge/tests/public_surface/README.md).

## Source lineage and completion ledger

The initial implementation entered `main` through [PR #1633](https://github.com/FOUNDUPS/Foundups-Agent/pull/1633),
squash `8980aa29b2a17655ad5d927c94059c068400c118`; it was not a direct main push.
[PR #1635](https://github.com/FOUNDUPS/Foundups-Agent/pull/1635), squash
`fcbedcc6dae6c8a96334a3ed02eceaf3a35d2afd`, added guest status recovery and
actual DatabaseManager-wrapper tests. Neither PR is deployment evidence.

The current host-lease recovery slice is developed on
`feature/reddog-public-host-lease-recovery-20260908`. Treat it as unavailable on
`main` until its PR is verified and squash-merged.

| Work | Source state / remaining evidence |
|---|---|
| Public guest consent, caps, expiry, replay and cancellation boundaries | Implemented in #1633; optional, unmounted |
| Lost-response nonce/revision recovery | Implemented in #1635; same bearer/surface/origin/subject; never replays inference |
| SQLite DatabaseManager wrapper | Exercised with temporary databases; actual PC lifecycle remains unverified |
| Host lease / orphaned busy-slot recovery | Source implementation in current lease slice: one-use hashed owner, live renewal, expired-owner recovery without nonce/quota rollback; actual heartbeat/process lifecycle still unbound |
| Resident host, trusted edge and public-only responder | Not activated; needs actual deployment/model/accounting bindings |
| AutoPost mobile, foundups.com and eSingularity.ai clients | Not implemented by these admission slices; preserve existing source ownership |
| Protected 012/0102 identity and 3V integration | Public evidence is unsigned/provisional; no protected identity or engine invocation |
| Private continuity, admitted context deltas, voice and omission critic | Still separate unfinished layers; use the existing dual-loop sequence |
| Live HoloIndex repair and recursive improvement | Requires a reachable configured owner and exact receipt; not established by GitHub CI |

Do not equate a linked work order, source merge, test pass or mocked responder
with completion of a downstream row. Continue the next unblocked bounded slice;
record exact missing environment dependencies rather than inventing readiness.

## Recover and isolate

Read `AGENTS.md`, WSP_00, WSP_97, WSP_10, WSP_15 and the RedDog documentation map.
Run the actual WSP_00 bootstrap and tracker from the canonical repository root.
Record exact current HEAD, status, worktrees, open owned PRs and available model
bindings. Do not reuse, reset or stage another worker's changes. Create a new
owned worktree/branch from verified current main.

Read `extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md` and its tests.
The source slices still have **no mounted live public host, deployed UI,
authenticated owner flow, 3V engine invocation, or voice/context-delta
implementation**.

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
2. Bind the existing lease primitives into the actual resident process lifecycle:
   generate a fresh random host owner on each process start, call `register_host`
   exactly once, renew before the 60-second lease expires, let a separately
   registered replacement process call `reclaim_orphaned_turns`, and preserve
   fail-closed legacy rows with no owner evidence. Do not reuse a host-owner
   token after restart. Do not clear busy state on ordinary exception or shutdown.
3. Prove shutdown/drain semantics. A clean host may wait/cancel its own provider
   tasks but must not rewrite quota, revision, nonce, or another host's busy
   owner. An expired host cannot finish or deliver a turn.
4. Bind an independently reviewed zero-tool, public-only responder. Its input is
   `PublicTurn`, not the principal Memex or private resident work envelope. Give
   public chat its own verified runtime surface/binding; do **not** reuse
   `reddog_backend_architect` merely because a model route already exists.
   Enforce max output tokens and provider-side deadlines. No arbitrary URL/model
   selection from browser input and no private OpenClaw fallback.
5. Supply edge-authenticated subject accounting, TLS, origin routing, rate limits,
   key custody and shared budgets across replicas/surfaces. The existing direct
   peer HMAC is not sufficient attribution behind an unverified proxy.
6. Mount the router on the proven host only after those tests pass. Leave public
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
A timeout consumes budget. After a lost reply, use `POST .../{surface}/status`
with the existing bearer and `{}` to recover the latest revision/nonce. Do not
resubmit the uncertain turn automatically. The response includes `in_flight`,
`expires_at`, `idle_expires_at` and `server_time`; status polling does not renew
those bounds or recover reply text. Apply status responses monotonically by
revision and request order; never overwrite newer client state with a late read.
Do not claim "sent", "saved", "remembered" or "executed" from model text.

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
existing files for the same contract; create a new test file only for a materially
distinct lifecycle/contract and update the inventory in the same slice. Register
new test files using the canonical generator; do not hand-edit counts or skip its
check.

Verify: wrong origin, spoofed forwarded identity, cross-surface/private-scope
leakage, expired and replayed nonce, parallel over-cap requests, restart quotas,
withdrawal during a response, body/output bounds, provider cancellation ignored,
clock rollback, unavailable DB/model, synthetic public/private canaries, and
`tSingularity` as ordinary capped text. Also verify lost-response status recovery,
no idle renewal, no quota refund, preserved busy slots, stale-client rejection,
host-owner one-use semantics, live renewal, expired-owner reclamation, old-host
finish/delivery rejection and pre-lease fail-closed rows.

Run targeted tests, dependency/security tiers, required CI and exact-host live
acceptance. Record commands and results honestly. Keep deployment distinct from
source merge. Publish a clean PR; squash only when the applicable checks pass.
Preserve unowned work and report remaining blockers with exact receipts.

Return to the existing dual-loop work: authenticated private turn/status/cancel
handlers -> authorized Memex/context-delta admission -> fast surface injection
-> voice -> omission critic and WSP_15 intervention ranking -> governed workers.
Do not implement every layer in one unreviewable change.
