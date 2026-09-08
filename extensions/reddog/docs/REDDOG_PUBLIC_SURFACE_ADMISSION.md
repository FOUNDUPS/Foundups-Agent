# RedDog public-surface admission — bounded first slice

Date: 2026-09-08  
Status: implemented source boundaries; **not activated or deployed**  
Baseline: `28273b0005563a41b9aa738654e0b70361542efb`

Canonical navigation: [documentation map](../../../docs/REDDOG_DOCUMENTATION_MAP.md) ·
[identity boundary](../ARCHITECTURE.md) · [Lick](REDDOG_LICK_CONNECTION_HANDSHAKE.md) ·
[dual-loop architecture](../../../docs/architecture/REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md)

## Decision and scope

AutoPost is the first intended mobile RedDog surface. `foundups.com` and
`eSingularity.ai` are additional public surfaces, not public doors into 012's
private 0102 runtime. These slices implement their shared **guest admission
boundary**, not the complete voice, memory, dual-loop, Lick, or 3V system.

RedDog remains the fast surface. 0102 remains the deeper twin. A public
responder receives only a bounded public turn and a server-selected surface.
It must never be configured to call the existing private OpenClaw webhook,
private Memex, tools, work-order promotion, or worker dispatch.

No site, AutoPost source, deployment, existing webhook, WSP, model topology,
or signed runtime manifest is activated by these files. The router remains
unmounted until its host and public-only responder pass deployment review.

## Implemented ownership

| Source | Responsibility |
|---|---|
| `modules/communication/moltbot_bridge/src/reddog_public_policy.py` | Exact public origins, strict input, lowered-only ceilings, unsigned Lick Verification evidence |
| `modules/communication/moltbot_bridge/src/reddog_public_session_gate.py` | Atomic guest session/nonce/quota accounting, status recovery, host leases and owner-bound orphan recovery through an injected existing AgentDB SQLite connection factory |
| `modules/communication/moltbot_bridge/src/reddog_public_http.py` | Optional FastAPI router; bounded JSON, exact CORS, public-only responder, cancellation/deadline, late-result handling and bearer-bound status |
| `modules/communication/moltbot_bridge/tests/public_surface/` | Real SQLite, actual DatabaseManager-wrapper and in-process ASGI tests with synthetic responders plus a distinct host-lease lifecycle suite |

The gate accepts `agent_db.db.get_connection`; it does not create a second memory
database. Tests execute the unchanged DatabaseManager wrapper against temporary
SQLite databases; the actual PC binding and resident heartbeat are not verified.
Owned storage is limited to `reddog_public_budget_v1`,
`reddog_public_session_v1`, and `reddog_public_host_lease_v1`. Existing session
rows gain a nullable `busy_owner` column. No conversation text, raw address,
media, private memory, raw session bearer, or raw host-owner token is stored.
SQLite is the supported accounting backend for these slices; other backends must
fail closed until independently implemented and verified.

## Endpoints and hard ceilings

Routes are `/api/reddog/public/{surface}/{operation}` with POST operations
`encounter`, `turn`, `status`, and `withdraw`; OPTIONS is narrow CORS preflight.

| Surface | Exact allowed browser origin |
|---|---|
| `foundups` | `https://foundups.com` |
| `esingularity` | `https://esingularity.ai` |
| `autopost` | `https://autopost.foundups.com` |

These are **policy entries, not deployment evidence**. In particular, validate
AutoPost's final origin after its redirect before enabling that adapter. No
wildcard origins, automatic redirects, or browser-supplied principal IDs.
Origin checking constrains browsers; it does not authenticate people or agents.

Initial ceilings are engineering defaults, not measurements of production demand:

- ten turns per session; 120-second idle and 600-second absolute expiry;
- three sessions and twenty turns per subject per UTC day across all surfaces;
- 200 sessions and 1,000 turns globally per UTC day;
- four simultaneous provider calls and one call per session;
- 2,000 input characters, 256 requested output tokens, 4,000 reply characters;
- a fifteen-second provider wait, shortened by session expiry; a two-second
  bounded body read and 12 KiB request-body ceiling.

The operator may lower these values. No client input can raise or disable them.
The provider adapter must actually enforce its output-token and upstream
transport deadlines; the gate is not a tokenizer or billing oracle. The
fifteen-second wait is not a claim about total HTTP latency under database or
host contention. Edge request/concurrency controls remain necessary.

Limits reserve atomically before inference and are not refunded on failure.
Nonces rotate with a compare-and-check revision in the same SQLite write
transaction. A replay cannot invoke the responder again. Counts survive host
object replacement and session rotation. Daily counters are retained until
cleanup after the following UTC day; they are not conversation memory.

A timed-out or cancelled provider keeps its busy slot until it actually finishes.
An uncooperative provider cannot create unlimited replacement calls.

### Host lease and crash-orphan recovery

A configured public host may supply a cryptographically random 64-hex
`host_owner`. The gate hashes that value before persistence. `register_host()`
accepts a host-owner token exactly once and creates a short lease;
`renew_host()` is the only way for that same running process to extend an
unexpired lease. Re-registering the same token is rejected before or after
expiry, so a stalled process cannot resurrect itself by replaying its startup
identity.

When a configured host reserves a turn, the busy reservation is bound to the
hashed process owner. A separately registered replacement host may call
`reclaim_orphaned_turns()` after the prior owner lease is no longer active.
Recovery clears only `busy` and `busy_owner`. It does **not** decrement revision,
restore the prior nonce, renew expiry, replay inference, or refund session,
subject, or global usage. The old host cannot finish or deliver after its lease
expires. A live renewed owner blocks foreign recovery.

Legacy busy rows created before owner tracking have `busy_owner = NULL`. They
remain fail-closed and are not reclaimed merely because the schema changed;
there is insufficient evidence that the older provider call is dead.

These are lease/recovery primitives, not a running resident lifecycle. The
production host still needs one unique owner token per process, one startup
registration, periodic renewal before the lease expires, replacement-host
recovery, and shutdown/drain behavior. No heartbeat scheduler or process-death
adapter is mounted by this source slice.

### Guest status and lost-response recovery

`POST .../{surface}/status` requires the existing bearer, the same validated
surface/origin/subject binding, and exactly `{}` as its JSON body. It returns
`revision`, `nonce`, `remaining_turns`, `in_flight`, `expires_at`,
`idle_expires_at`, `server_time`, `disclosure: public`, and `effect_ceiling: NONE`.
It returns no reply history, raw bearer, private memory or identity authority.

Status does not invoke a responder, rotate a nonce, renew idle/absolute expiry,
refund a consumed turn, or clear a busy slot. Its transaction only advances the
existing fail-closed clock watermark. Expired sessions return 410; withdrawn,
unknown or cross-boundary sessions disclose no status. An exhausted but still
active session may report zero remaining turns; that does not reopen its budget.

After an uncertain network outcome, a client should fetch status rather than
replay the original turn. A new explicit turn may use the recovered revision
and nonce only when no work is in flight. A lost reply is not recoverable from
this content-free store. Clients must ignore late status responses that would
regress local revision/request order. Polling remains subject to the trusted
edge's request limits; this API is not an unlimited polling entitlement.

## Lick and 3V

Lick belongs at engagement ingress and supplies evidence to **Verification**.
This is not a renumbering of existing CABR/3V stages. It does not replace work
Validation or contribution Valuation, and does not grant authorization.

This subset accepts scoped consent and a self-declared `human`, `agent`, or
`unspecified` claim. Every participant remains provisional. The returned
`reddog.lick.public-verification.v1` projection explicitly declares:

- identity is not verified and human presence is not proven;
- agent assistance has **not been assessed**;
- the record is **unsigned**, grants no authority, and has an expiry;
- Validation and Valuation have not been evaluated.

This is an implemented evidence projection hook, not a live 3V-engine invocation
or an authenticated `LickReceipt`. Human account proof requires a separate
possession-bound authentication flow; an agent requires its own verifiable
key/registration/delegation binding. Neither can be inferred from conversation.
Assistive AI use by a human is not itself evidence of impersonation.

The full [Lick contract](REDDOG_LICK_CONNECTION_HANDSHAKE.md), including protected
step-up, signed evidence where required, participant changes across devices,
biometrics, and governed identity binding, remains separately gated.

## The 0102 question

012 supplied the explanation that 0102 represents a neuralnet end state, the AI
of tSingularity. Preserve that as an attributed personal meaning/onboarding
answer, not an authentication fact or scientific verification claim.

`Why does 012 call me 0102?` and `tSingularity` are ordinary conversation data.
They **never** authenticate 012/0102, remove a cap, expose private memory, or
create execution authority. A future authenticated owner tier may have its own
explicit budget; a public knowledge answer cannot select it.

## Host and client activation gates

The existing host must explicitly supply `PublicSurfaceBinding`: persistent
AgentDB accounting, a reviewed public-only responder, a deployment-owned secret
for pseudonymous peer accounting, and a trustworthy clock. A configured
lease-backed host must additionally own a unique process token and keep its
lease current. Without those bindings, the router remains unavailable and must
never fall back to private OpenClaw or a browser key.

The current adapter uses the direct transport peer and ignores forwarded headers.
Behind a proxy this may group visitors together; a trusted edge subject adapter,
TLS termination, bot/abuse controls, key custody, and aggregate budget placement
must be proven before public exposure. Multiple independent databases do not
constitute a global cap. Public sites must not share 012's private bearer or
conversation ID. Use separately authorized private sessions for the owner.

Withdrawal blocks new turns and late delivery. Minimal in-flight accounting is
retained until actual completion; abuse counters are retained as disclosed.
There are no biometric templates in this slice to delete.

## WSP and retrieval evidence

Read WSP_00, WSP_97, WSP_10, WSP_15, WSP_29 and the canonical RedDog/AutoPost
contracts before design. Each change remains a bounded implementation layer,
not live worker dispatch. Planning priority is recorded in the owning PR; it is
not represented as an authenticated WSP_15 allocation receipt because current
WSP_97 explicitly marks end-to-end allocation enforcement as not implemented.

This chat environment does not provide the configured resident HoloIndex owner
or canonical PC checkout needed for a live WSP_00/Holo execution receipt.
Exact-commit GitHub retrieval is the fallback evidence source. CI freshness
checks are useful repository gates but do not substitute for the live owner
query required by the remote work order. No Holo repair, bootstrap success, RSI
promotion, or PC working-tree state is asserted from these source changes.

Retain this retrieval regression case for the remote owner:

```json
{"query":"RedDog Lick public surface usage cap timeout host lease crash recovery 3V Verification tSingularity","limit":5,"include_bundle":true,"module_hint":"modules/communication/moltbot_bridge","must_include":["extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md","modules/communication/moltbot_bridge/src/reddog_public_policy.py","modules/communication/moltbot_bridge/src/reddog_public_session_gate.py","modules/communication/moltbot_bridge/src/reddog_public_http.py"]}
```

Require `ok=true`, `freshness=CURRENT`, `index_gap_detected=false`; retain exact
HEAD/receipt and evaluate missing targets, ordering, noise, and latency. On a
real owner failure use the existing governed maintenance/repair path, then test
and requery. Never reindex inside a user-facing query or promote retrieval
changes without independent held-out evidence.

## Verification and next transaction

See the suite [README](../../../modules/communication/moltbot_bridge/tests/public_surface/README.md)
and [TestModLog](../../../modules/communication/moltbot_bridge/tests/public_surface/TestModLog.md).
Source and CI evidence do not prove the PC or production host.

The next bounded transaction remains the
[remote integration work order](prompts/WSP97_REDDOG_PUBLIC_SURFACE_REMOTE_PROMPT.md).
It must connect the lease primitives to the actual resident host lifecycle,
public-only responder, trusted ingress and shared budgets before adding browser
or AutoPost UI. After the public host lane is proven, return to private resident
transport, authorized context deltas, voice, and omission-critic work. The public
guest gate does not complete those independent layers.

Technical anchors: [OWASP session timeouts](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OWASP REST security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html),
[NIST authenticators](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/).
