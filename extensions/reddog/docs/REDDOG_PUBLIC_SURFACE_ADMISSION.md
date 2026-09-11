# RedDog public-surface admission — bounded shared contract

Date: 2026-09-12 reconciliation  
Status: public/Lick source boundaries implemented; host-lease recovery reconstructed on current main and pending exact-head verification; **not activated or deployed**  
Reconciliation base: `3b74a04205b05fc0d84172d52b8862ff608b1d6e`

Canonical navigation: [documentation map](../../../docs/REDDOG_DOCUMENTATION_MAP.md) ·
[identity boundary](../ARCHITECTURE.md) · [Lick](REDDOG_LICK_CONNECTION_HANDSHAKE.md) ·
[dual-loop architecture](../../../docs/architecture/REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md) ·
[2026-09-12 surface audit](../../../docs/audits/architecture/REDDOG_SURFACE_RUNTIME_RECONCILIATION_20260912.md)

## Decision and scope

AutoPost is the first intended mobile RedDog surface. `foundups.com` and
`eSingularity.ai` are additional public surfaces, not public doors into 012's
private 0102 runtime. The current source implements their shared **guest admission
contract** plus the explicit non-biometric AutoPost Lick PoC. The current host
lease slice adds source-level process ownership/recovery without changing those
Lick semantics. This is not the complete voice, memory, dual-loop, biometric
Lick, or 3V system.

RedDog remains the fast surface. 0102 remains the deeper twin. A public
responder receives only a bounded public turn and a server-selected surface.
It must never be configured to call the existing private OpenClaw webhook,
private Memex, tools, work-order promotion, or worker dispatch.

The linked AutoPost source already adds the opt-in Lick client and capture
provenance. It does not yet implement the RedDog dormant/attending sensory loop.
No site deployment, existing private webhook, model topology, or signed runtime
manifest is activated here. The public router remains unmounted until its host,
public-only responder, trusted ingress, and shared-budget boundaries pass review.

## Implemented ownership

| Source | Responsibility |
|---|---|
| `modules/communication/moltbot_bridge/src/reddog_public_policy.py` | Exact public origins, strict inputs, bounded Lick consent/challenge/receipt schemas, unsigned Verification evidence |
| `modules/communication/moltbot_bridge/src/reddog_public_session_gate.py` | Atomic guest/Lick session, one-use challenge, nonce, quota, expiry, withdrawal, status, host lease and owner-bound orphan recovery through an injected existing AgentDB SQLite connection factory |
| `modules/communication/moltbot_bridge/src/reddog_public_http.py` | Optional FastAPI router; bounded JSON, exact CORS, lease-backed public-only responder binding, cancellation/deadline, late-result handling and bearer-bound status |
| `modules/communication/moltbot_bridge/tests/public_surface/` | Real SQLite, actual DatabaseManager-wrapper and in-process ASGI tests, including distinct non-biometric Lick and resident-host lifecycle contracts |

The gate accepts `agent_db.db.get_connection`; it does not create a second memory
database. Tests execute the unchanged DatabaseManager wrapper against temporary
SQLite databases; the actual PC binding and resident heartbeat remain separate
runtime evidence. Owned state is limited to `reddog_public_budget_v1`,
`reddog_public_session_v1`, the content-free `reddog_lick_open_v1` challenge/
profile binding, and the content-free `reddog_public_host_lease_v1`. Existing
session rows gain nullable `busy_owner` for configured hosts. No conversation
text, raw address, media, private memory, raw session bearer, raw Lick challenge,
or raw host-owner token is stored. SQLite is the supported accounting backend
for these source slices; other backends fail closed until independently verified.

## Single public-session contract

The public RedDog contract is singular even when more than one deployment
adapter exists. The Python/AgentDB gate is the current canonical reference
implementation for nonce/revision, quotas, expiry, Lick, host recovery, and
authority ceilings.

A web-edge adapter may implement the same contract for deployment reasons, but
it must pass parity tests against the canonical behavior and state its ownership
boundary explicitly. It may impose stricter edge limits. It must not silently
invent a second identity, Lick, quota, replay, recovery, or authorization model.

The open website PR #1648 contains useful UI/OpenRouter work but also a separate
D1 session/accounting implementation. That branch is not current authority and
must be reconciled before merge; its duplicated store is not implicitly
canonical merely because its constants currently resemble this policy.

## Endpoints and hard ceilings

Routes are `/api/reddog/public/{surface}/{operation}` with POST operations
`encounter`, `lick`, `challenge`, `turn`, `status`, and `withdraw`; OPTIONS is
narrow CORS preflight. `lick` returns a random challenge; `challenge` consumes
it exactly once before a Lick-bound session may submit a turn.

| Surface | Exact allowed browser origin |
|---|---|
| `foundups` | `https://foundups.com` |
| `esingularity` | `https://esingularity.ai` |
| `autopost` | `https://autopost.foundups.com` |

These are **policy entries, not deployment evidence**. Validate AutoPost's final
post-redirect origin before enabling that adapter. No wildcard origins,
automatic redirects, or browser-supplied principal IDs. Origin checking
constrains browsers; it does not authenticate people or agents.

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

A configured resident public host supplies a fresh random 64-hex `host_owner`
for one process lifetime. The gate hashes it before persistence.
`register_host()` accepts that owner exactly once. `renew_host()` is the only
operation that may extend an unexpired lease. Re-registering the same owner is
rejected before and after expiry, and expired owner hashes remain tombstones;
a stalled or restarted process therefore cannot replay its old owner token to
become current again.

When a configured host reserves a guest or Lick turn, the existing busy
reservation is bound to that host hash. A separately registered replacement
host may call `reclaim_orphaned_turns()` only after the recorded owner lease is
no longer active. Recovery clears `busy` and `busy_owner` only. It does **not**
rewind revision, restore an earlier nonce, reopen a consumed Lick challenge,
remove the provisional Lick profile, extend session/idle expiry, replay
inference, or refund session/subject/global usage. A live renewed owner blocks
foreign recovery; an expired old host cannot finish or deliver its result.

Rows created before host ownership have `busy_owner = NULL`. A schema migration
cannot prove their provider process is dead, so those legacy busy rows remain
fail-closed and are not reclaimed by assumption.

These are source-level lease primitives, not a running heartbeat. Production
still needs an adapter around the existing resident process that generates a
fresh owner on startup, registers once, renews before the 60-second lease
expires, lets a new process reclaim after verified expiry, and defines clean
shutdown/drain behavior. The DAE broker's existing registry heartbeat does not
by itself renew this public lease.

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

The legacy `encounter` operation returns that evidence projection. The opt-in
`lick` plus `challenge` operations return an unsigned, provisional
`reddog.lick.receipt.v1` only after a randomized challenge is consumed once.
That challenge proves request continuity, not identity, liveness, or human
presence. Human account proof still requires a separate possession-bound
authentication flow; an agent requires its own verifiable key/registration/
delegation binding. Neither can be inferred from conversation. Assistive AI use
by a human is not itself evidence of impersonation.

The full [Lick contract](REDDOG_LICK_CONNECTION_HANDSHAKE.md), including protected
step-up, signed evidence where required, participant changes across devices,
biometrics, and governed identity binding, remains separately gated.

## AutoPost attention boundary

AutoPost's existing Lick integration establishes encounter/provenance state but
does not itself mean RedDog is always looking or listening.

The mobile sensory contract is:

- camera preview available -> RedDog `dormant`;
- explicit hold/engagement -> RedDog `attending`;
- while attending, RedDog may consume bounded samples of the same visible camera
  viewport and permitted microphone audio/STT events;
- release, cancellation, backgrounding, participant/session invalidation, or
  transport failure -> RedDog returns to `dormant`;
- ordinary photo/video recording and local Liquid vision remain distinct from
  RedDog sensory ingress and retention.

This attention state is not implemented by the current public gate. See the
2026-09-12 surface audit for the owning AutoPost follow-up.

## The 0102 question

012 supplied the explanation that 0102 represents a neuralnet end state, the AI
of tSingularity. Preserve that as an attributed personal meaning/onboarding
answer, not an authentication fact or scientific verification claim.

`Why does 012 call me 0102?` and `tSingularity` are ordinary conversation data.
They **never** authenticate 012/0102, remove a cap, expose private memory, or
create execution authority. A future authenticated owner tier may have its own
explicit budget; a public knowledge answer cannot select it.

## Host and client activation gates

The existing resident OpenClaw host must eventually supply a separate reviewed
public binding: persistent AgentDB accounting, a public-only responder, a
deployment-owned secret for pseudonymous peer accounting, a trustworthy clock,
and the process-owned lease lifecycle above. Without that explicit public
binding, the router stays unavailable and never falls back to private OpenClaw,
private 0102 context, or a browser key.

The current HTTP adapter uses the direct transport peer and ignores forwarded
headers. Behind a proxy this may group visitors together; a trusted edge subject
adapter, TLS termination, bot/abuse controls, key custody, and aggregate budget
placement must be proven before public exposure. Multiple independent databases
do not constitute a global cap. Public sites must not share 012's private bearer
or conversation ID. Use separately authorized private sessions for the owner.

Withdrawal blocks new turns and late delivery. Minimal in-flight accounting is
retained until actual completion; abuse counters are retained as disclosed.
There are no biometric templates in this slice to delete.

## WSP and retrieval evidence

Read WSP_00, WSP_97, WSP_10, WSP_15, WSP_29 and the canonical RedDog/AutoPost
contracts before design. Host lease work is one bounded resident-lifecycle
slice. Its WSP_15 priority belongs in the owning PR and is not represented as an
authenticated allocation receipt because current WSP_97 marks end-to-end
allocation enforcement as specified-not-implemented.

This chat environment does not expose the configured resident HoloIndex owner or
canonical PC checkout needed for a live WSP_00/Holo execution receipt.
Exact-commit GitHub retrieval is the fallback evidence source. CI freshness is a
repository gate, not a substitute for the live owner query required on the PC.
No Holo repair, bootstrap success, RSI promotion, or PC working-tree state is
asserted from these source changes.

Retain this retrieval regression case for the remote owner:

```json
{"query":"RedDog Lick public surface usage cap timeout host lease crash recovery attention dormant looking listening 3V Verification","limit":5,"include_bundle":true,"module_hint":"modules/communication/moltbot_bridge","must_include":["extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md","docs/audits/architecture/REDDOG_SURFACE_RUNTIME_RECONCILIATION_20260912.md","modules/communication/moltbot_bridge/src/reddog_public_policy.py","modules/communication/moltbot_bridge/src/reddog_public_session_gate.py","modules/communication/moltbot_bridge/src/reddog_public_http.py"]}
```

Require `ok=true`, `freshness=CURRENT`, `index_gap_detected=false`; retain exact
HEAD/receipt and evaluate missing targets, ordering, noise, and latency. On a
real owner failure use the existing governed maintenance/repair path, then test
and requery. Never reindex inside a user-facing query or promote retrieval
changes without independent held-out evidence.

## Verification and next transactions

See the suite [README](../../../modules/communication/moltbot_bridge/tests/public_surface/README.md)
and [TestModLog](../../../modules/communication/moltbot_bridge/tests/public_surface/TestModLog.md).
Source and CI evidence do not prove the PC or production host.

The immediate transaction is fresh exact-head verification of the reconstructed
host-lease slice. After merge:

1. add the AutoPost `dormant | attending` RedDog attention adapter without
   duplicating camera or STT ownership;
2. connect the lease lifecycle to the existing resident launcher/DAE runtime;
3. bind a distinct zero-tool public model surface and trusted edge/shared budgets;
4. reconcile #1648 so website delivery conforms to this single contract rather
   than creating an independent session authority;
5. mount/activate public clients only after those gates pass;
6. return to private resident transport, authorized context deltas, voice/TTS,
   and the omission-critic/WSP_15 attention loop.

Technical anchors: [OWASP session timeouts](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OWASP REST security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html),
[NIST authenticators](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/).