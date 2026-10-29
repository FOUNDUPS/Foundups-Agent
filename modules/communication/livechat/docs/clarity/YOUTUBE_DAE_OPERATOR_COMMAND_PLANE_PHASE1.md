# YouTube DAE operator command plane — Phase 1

## Current contract, 2026-10-22

Owner: existing `OperatorCommandQueue` → `AutoModeratorDAE.run()` → existing
`LiveChat.send_chat_message` and stored-comment `load_broadcast` consumer.
WSP 00/5/6/10/11/15/22/50/84/91/97. This supersedes the initial September
proposal's exactly-once and malformed-input-as-empty assumptions. Source
history and dated ModLogs retain that proposal; this document describes the
tested boundary. No native worker or end-to-end RSI success is established.

## Interface and authority

```json
{"version":1,"commands":[{"id":"local-001","action":"announce","payload":{"message":"Operator update","ttl_seconds":3600}}]}
```

The inbox is trusted local operator state, not authenticated remote admission.
Only `status`, `announce`, `set_context`, `clear_context` exist. It cannot choose
models, invoke arbitrary tools, execute code or grant WRE authority. OS access
controls must protect inbox, ledger and state. Different runtimes/worktrees must
not point different ledgers at the same external effect stream.

Paths default to checkout-rooted `memory/012_manifest.json`,
`memory/012_manifest_acknowledgements.json`, and `memory/012_manifest_state.json`.
`YT_012_MANIFEST_FILE`, `YT_012_MANIFEST_ACK_FILE`, `YT_012_MANIFEST_STATE_FILE`
accept absolute or checkout-relative overrides; all three paths must differ.
The comment reader uses the same state resolver. Changing CWD changes neither
writer nor reader configuration. Inbox version is integer 1, with at most 100
commands; each JSON file is bounded to 4 MiB. IDs are nonempty strings up to 200
characters and cannot be reused with a different payload. Existing terminal
receipts without digests stay terminal; they cannot retrospectively prove payloads.

## Claims and outcomes

Reuse the shared runtime OS lock and an in-process guard for one canonical
ledger. Write/flush/replace an `unknown` claim before effects, then persist the
result before optional receipt telemetry. `unknown` is a terminal tombstone
after crashes, cancellation, timeouts, ambiguous sender results or final-write
failure. A provider may have acted: reconcile its outcome before any intentional
new command. Never delete the ledger or change an ID merely to retry uncertainty.
This prevents automatic duplicate attempts in the tested process-restart model;
it does not promise exactly-once external delivery or universal power-loss durability.

Only `deferred` work retries automatically. Its first observation is persisted;
expiry is that time plus the integer TTL (60–86,400 seconds, default 3,600), not
the latest poll time. Later context/clear intents supersede older deferred context
unless rejected, blocked or expired. A selected but unavailable live-chat surface
defers the whole context change; it does not partially activate comment context.
Live-chat text is at most 200 characters, matching the existing sender's bound;
comment-only context allows 500. Unknown actions/invalid payloads are rejected.

STOP, automation, selected send/announcement and comment-engagement gates are
checked before activation. Live-chat dry-run is `simulated`, with no sender or
context effect. Normal send acceptance is `sender_accepted=true` with
`delivery_verified=false` and amber receipt health. A boolean sender response
cannot establish provider readback. Local status/context acknowledgement can be
green. Shared-context clear does not clear legacy module-local broadcast intent.

Malformed or unreadable state blocks polling without erasing evidence. The
watcher records a sanitized failure class and retries later; cancellation still
propagates. Capacity exhaustion requires supervised ledger archival that retains
replay history. Poll cadence defaults to 60 seconds; sender deadline defaults to
30 seconds, bounded to 300 and reliant on cooperative async cancellation.
`run()` owns a single watcher and cancels/awaits it on normal, failed and cancelled
exits. Heartbeat copies the historical last result and separately reports watcher
state (`inactive`, `running`, `cancelled`, `stopped`); it does not authenticate delivery.

## Evidence and remaining gate

The three explicit offline test files cover real queue/reader composition,
temporary-file persistence, child-process lock contention and crash/restart,
receipt truth, malformed data, context expiry, gate rejection and lifecycle.
Lifecycle/heartbeat methods execute from current source with optional heavy
integrations replaced. The original source reproduces duplicate sends after a
failed acknowledgement, renewed expiry and leaked watchers. Windows/Linux CI
must pass on the reviewed head; exact receipts belong to PR1759.

Not yet demonstrated: full DAE startup/imports on its installed runtime, real
YouTube provider delivery/readback, authenticated remote work admission,
independent outcome evaluation, activation/rollback or later retained benefit.
Those remain with the current runtime/RSI owners. This PR is local contract
repair, not authority to post or a replacement RSI scheduler.

## Alternatives and selection

Reuse before extend before create: extend the existing ledger and shared runtime
lock instead of adding a database/scheduler or a network endpoint. Preserve the
existing sender's throttling/account boundary. Reject malformed state rather than
resetting evidence. Prefer at-most-one automatic attempt with explicit uncertainty
over an unsupported exactly-once claim. New actions require a separate scoped
acceptance and authority review.
