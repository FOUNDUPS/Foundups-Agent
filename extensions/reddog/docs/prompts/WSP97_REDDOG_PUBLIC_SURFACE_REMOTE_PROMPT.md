# Remote work order: RedDog public host and first mobile adapter

Status: work order only; not completion or execution authority by itself.
Origin: external principal 012. Role: 0102 architect/engineer.

Canonical navigation: [RedDog documentation map](../../../../docs/REDDOG_DOCUMENTATION_MAP.md) ·
[public admission contract](../REDDOG_PUBLIC_SURFACE_ADMISSION.md) ·
[Lick contract](../REDDOG_LICK_CONNECTION_HANDSHAKE.md) ·
[test inventory](../../../../modules/communication/moltbot_bridge/tests/public_surface/README.md).

## Source lineage and completion ledger

- PR #1633 -> squash `8980aa29b2a17655ad5d927c94059c068400c118`:
  bounded public guest consent/caps/expiry/replay/cancellation boundary.
- PR #1635 -> squash `fcbedcc6dae6c8a96334a3ed02eceaf3a35d2afd`:
  bearer-bound lost-response status recovery and actual DatabaseManager-wrapper tests.
- Main `e6dfa919f474158d0001296d3bd6e166129fc5f8`:
  open-source non-biometric Lick PoC, including explicit consent, one-use
  continuity challenge, provisional no-authority receipt and AutoPost integration
  boundaries. It remains unmounted/not deployed.
- Host-lease recovery is being rebuilt from that Lick-aware main on
  `feature/reddog-public-host-lease-recovery-v2-20260908`. The earlier pre-Lick
  lease PR #1640 is superseded and must not overwrite newer RedDog source.

| Work | Source state / remaining evidence |
|---|---|
| Public guest consent, caps, expiry, replay and cancellation | Implemented; optional/unmounted |
| Lost-response nonce/revision recovery | Implemented; no replay/refund/renewal |
| Non-biometric Lick consent/challenge/provisional receipt | Implemented source PoC; not protected identity or deployed runtime |
| AutoPost Lick capture/client boundary | Source-linked PoC exists; public RedDog conversation still needs resident host binding and deployment verification |
| SQLite DatabaseManager wrapper | Exercised with temporary databases; actual PC lifecycle unverified |
| Host lease / orphaned busy-slot recovery | Current Lick-aware slice: hashed one-use process owner, live renewal, expired-owner recovery without nonce/quota/Lick rollback; actual heartbeat/shutdown adapter still unbound |
| Public-only responder/runtime surface | Not implemented/verified; do not reuse private backend-architect surface by convenience |
| Trusted edge/TLS/shared budgets | Not implemented/verified |
| foundups.com and eSingularity.ai public RedDog clients | Not yet activated; preserve each surface's existing ownership/deployment path |
| Protected 012/0102 identity and 3V integration | Lick evidence remains provisional/no-authority; no protected identity or 3V engine invocation |
| Private RedDog -> 0102 continuity/context deltas/voice/omission critic | Separate unfinished dual-loop layers |
| Live HoloIndex repair and recursive improvement | Requires configured PC owner and exact CURRENT/no-gap receipt; GitHub CI is not that proof |

Do not equate a linked work order, source merge, test pass, provisional Lick
receipt, or mocked responder with completion of a downstream row.

## Recover and isolate

Read `AGENTS.md`, WSP_00, WSP_97, WSP_10, WSP_15 and the RedDog documentation map.
Run the actual WSP_00 bootstrap and tracker from the canonical repository root.
Record exact current HEAD, status, worktrees, open owned PRs and available model
bindings. Preserve unrelated worker changes. Create a new owned worktree/branch
from verified current main for each bounded slice.

Read `extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md`, the Lick contract,
and public-surface tests. Source is ahead of deployment: there is still **no
verified mounted public host, public model responder, trusted public ingress,
protected owner flow, 3V engine invocation, or private context-delta/voice loop**.

## HoloIndex before expansion

Use the canonical owner query in `AGENTS.md`, resolving the main/control root
through Git's common directory. Run the exact regression query in the admission
document. Require `ok=true`, `freshness=CURRENT`, and `index_gap_detected=false`.

On failure preserve the exact error/request/HEAD. Route repair only through the
existing governed Holo owner/post-merge maintenance path, run the closest tests,
and requery before returning to RedDog. Do not reindex inside the user-facing
query, widen freshness/timeout gates, or claim recursive improvement without
held-out retrieval evidence.

## Next implementable scope: resident lifecycle

1. Inventory the existing broker-managed resident host at
   `modules/communication/moltbot_bridge/scripts/launch.py` and the DAE broker.
   Reuse it; do not create a second server, queue, database, or camera stack.
2. Bind the verified lease primitives into the resident **public** lifecycle:
   generate a fresh random owner for each process start, initialize the gate,
   call `register_host()` once, renew before the 60-second lease expires, and let
   a separately registered replacement process call `reclaim_orphaned_turns()`.
   Never reuse a host-owner token after restart.
3. Do not confuse the DAE broker's registry heartbeat with the public lease. The
   current broker reports liveness but does not renew `PublicSessionGate`.
4. Define shutdown/drain behavior. Clean shutdown may wait/cancel only its own
   public provider tasks; it must not refund quota, rewind nonce/revision, clear
   another host's reservation, delete lease tombstones, or manufacture recovery.
5. Keep legacy `busy_owner=NULL` rows fail-closed until separate evidence proves
   how to safely retire them.
6. Test startup failure, renewal failure, late heartbeat, process replacement,
   double start/token replay, old-host late completion, Lick profile/challenge
   preservation, and crash/restart through the actual resident lifecycle.

## Then bind a public-only responder

1. Define a distinct reviewed zero-tool **public RedDog chat** runtime surface.
   Its input is `PublicTurn`, not the principal Memex/private resident envelope.
2. Do not reuse `reddog_backend_architect` or a private OpenClaw work path merely
   because a model binding already exists.
3. Enforce `PublicTurn.max_output_tokens`, provider-side transport deadline,
   response character bound, cancellation, no tool calls, no arbitrary client
   provider/model selection, and no private fallback.
4. Bind the router to that responder only after a signed/configured runtime
   mapping and failure behavior are verified.

## Trusted public ingress before mounting

Supply edge-authenticated pseudonymous subject accounting, TLS termination,
origin routing, abuse/rate limits, key custody and **shared** budgets across
replicas/surfaces. Direct peer HMAC is not sufficient attribution behind an
unverified proxy. Multiple independent SQLite files are not a global cap.
Leave public exposure disabled when any dependency is unavailable.

## Surface rollout after host proof

### AutoPost first

Continue in `FOUNDUPS/autopost`, not a copied monorepo camera. Preserve the
existing non-biometric Lick client/capture provenance. Verify its actual final
origin. Add/activate camera-off RedDog text conversation against the proven
public host; voice is a later measured adapter. Public guest state must never
inherit 012's private session.

### foundups.com and eSingularity.ai

Add the same thin public guest conversation adapter through each canonical
frontend/deployment owner. Keep conversation consent distinct from capture,
recording, publishing, biometrics, or private-memory disclosure.

Client obligations: render model output as text, show guest/Lick status, remaining
turns and expiry; respect 429/410/503/504; never automatically resubmit an
uncertain consumed turn; use `status` to recover revision/nonce; do not persist
bearers/raw conversation in localStorage. A timeout consumes budget.

## Identity and 3V

Lick contributes evidence to Verification. The non-biometric challenge proves
bounded request continuity only. It does not prove human presence, protected
identity, non-use of assistance, or authority; it does not perform Validation or
Valuation. A protected human account requires separately verified possession.
An agent requires its own key/registration/delegation. `tSingularity`, names,
voice answers, or knowledge questions never authenticate 012/0102 or remove caps.
Assistive-AI use by a human is not itself impersonation evidence.

## Acceptance and publication

Read TestModLog/README and nearest owning tests before changing code. Extend an
existing file for the same contract; create a new test file only for a materially
distinct lifecycle and update the inventory. Regenerate the canonical registry
with `generate_test_registry.py`; never hand-edit counts.

For host/lease work verify at minimum:
- both ordinary guest and non-biometric Lick flows still pass;
- one-use host-owner registration and expired-token replay rejection;
- live renewal blocks recovery;
- replacement host reclaims only expired owner-bound busy slots;
- revision, nonce, Lick challenge/profile state and quotas do not roll back;
- old host cannot finish/deliver;
- pre-lease NULL-owner rows remain fail-closed;
- actual DatabaseManager restart path;
- WSP 62 file/function bounds and existing public coverage floor.

Then run required repository CI and exact-host live acceptance. Record exact
head/checks honestly. Keep deployment distinct from source merge. Use a clean PR
and squash only after the exact final head passes.

After the public host lane is proven, return to the dual-loop sequence:

`authenticated private turn/status/cancel -> authorized Memex/context-delta admission -> fast RedDog injection -> voice -> omission critic -> WSP_15 intervention ranking -> governed workers`

Do not implement every layer in one unreviewable change.
