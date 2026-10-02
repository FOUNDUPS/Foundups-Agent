# #1779 sender authority audit — 2026-10-02

Baseline: main `ab0ce726b55a90da078f24d03905d01c6432e6c1` (PR #2029).
Issue #1779 and all five then-current comments, PR #1928, and PR #1979 were read.
#1979 was superseded by merged #1993, whose Sent-first contract is on this baseline.

## Problem, assumptions and decision

Recipient resolution was detached from the final provider mutation. The v2 V8
wrapper added another resolver and accepted receipts authenticated only by a
publicly recomputable SHA-256. It did not inspect correspondence state, consume
receipts durably, or require nonempty provider message/thread identities.

Trust assumption: an independently administered service owns reconciliation,
provider credentials and the private native correspondence DB. Composers can call
its RPCs but cannot construct its dependencies, write its DB, or call Gmail directly.
This assumption is **NOT satisfied by the current ChatGPT Work tool host**.
Python private members and a module import are not a security sandbox.

Alternative rejected: copying Python routing policy to JavaScript and loading it
alongside direct Gmail tools in an agent-selected V8 cell. It cannot isolate the
provider capability and permits composer self-authorization.

Decision: reuse the existing Python preflight/readback owner, extend the existing
native store for durable receipt registration and atomic claims, gate finalized
drafts and sends in one service-owned adapter, and quarantine the old V8 authority.
Do not install credentials, send mail, delete drafts, close #1779, or lift containment.

WSP00: V2 attempted, unavailable torch; tracker fallback gate is open, detector
witness absent. WSP97 retrieval: source-bound lexical bundle on baseline above,
`freshness=UNKNOWN`, `index_gap_detected=true`, `workspace_head`; no semantic freshness
claim. Direct file reads fill required evidence. Retrieval noise was reduced by
scope, exact paths and deduplication; no new contact database or memory system.

## Repository implementation

`CorrespondenceSenderBoundary.issue` reconstructs intended recipients/content and
state through a bootstrap-owned reconciler; composers supply no routing evidence or
capsule. Canonical preflight performs Pass A/Pass B. Receipts bind account, operation,
scope/purpose, Contact IDs/roles/normalized addresses, subject/MIME tree (attachments
included), draft/reply/thread identities, provenance, policy/duplicate result,
state/source/evidence digests, issue/expiry time and the transaction digest.

The issuer persists only receipt ID/digest. `execute` checks that private issuer
record, reruns reconciliation/preflight, reads the exact draft where applicable,
reconciles again after slow reads, rechecks expiry and commits an atomic unique claim
before mutation. Transaction uniqueness, receipt uniqueness and account/scope/state
reservation uniqueness prevent replay and concurrent sends from the same state.
Claims are never released automatically, including after provider timeout or crash.
All matching provider-Sent records (including integrity incidents) block repair.

Provider submission uses only reconstructed explicit To/CC/BCC and bound fields.
Success requires immediate exact-ID provider Sent readback: nonempty MID/TID,
expected thread when applicable, SENT label, and explicit complete To/CC/BCC arrays.
Missing, extra or wrong-role recipients become integrity incidents. Per-recipient
Contact-ID/role/submission-verification state is private runtime metadata, not a
claim of recipient delivery. Bounce absence grants no authority.

Finalized create/update draft uses the same capsule/preflight gate. On blocked state
it returns HOLD without provider mutation; existing drafts and new prose are preserved
by the caller as non-send-ready work. No draft deletion method exists.

Dry-run produces AUDIT_ONLY without registering a usable receipt. Supported service
operations are send_email, reply, send_draft, delivery_repair, create_draft, update_draft.
Unknown operations fail closed. Scheduled/helper callers use the same execute RPC.
The v2 V8 compatibility entrypoints always BLOCK without even reading the provider.
Their old positive tests are superseded by the stronger Python authority tests;
the Node suite now freezes the retired self-authorization bypass.

## Complete send-path search and WSP97 counterexamples

Searches covered the entire repository, not just issue-listed paths:
`send_email`, `send_draft`, Gmail message/draft send APIs, `gmail.googleapis`,
`sendmail`, `send_message`, `smtplib`, reply identities, delivery repair, schedules,
wrappers, host/source/Skillz paths. All executable file types and Markdown contracts
were inspected. Gitignored/untracked runtime deployments are outside repository truth.

| Path | Evidence and disposition |
| --- | --- |
| v2 host sender boundary | Only concrete repo Gmail callback seam on baseline. Quarantined; every legacy operation has zero provider callbacks. |
| New Python sender authority | Only governed correspondence submit owner; all six operations share execute. Not deployed to Work. |
| auto_meeting_orchestrator code_review_orchestrator | Calls `_send_email_notifications` but defines no implementation; no working Gmail provider path. Future implementation must use authority. |
| 0102_orchestrator notification_engine | Email notification is a TODO/pass, no SMTP/provider capability. |
| WRE capability/scope tests | Synthetic action strings, not Gmail submissions. |
| Hermes adapter / livechat / LinkedIn | Generic non-Gmail/simulated message APIs; no mail provider capability. |
| YUMORI correspondence/funding/operations Skillz | Prompt contracts referencing direct Work actions; external enforcement gap remains. |
| ChatGPT Gmail send_email | Actual exposed tool takes To/CC/BCC/subject/MIME/reply context, no receipt. Still a bypass. |
| ChatGPT Gmail send_draft | Actual exposed tool takes only draft_id, no receipt. Still a bypass. |
| ChatGPT Gmail create_draft/update_draft | Actual tools have no capsule/receipt parameters. Finalized drafts can bypass service. |
| Work automations/background tool invocations | Same external direct capabilities; repository cannot revoke/intercept them. |

1. Can a repo-owned path still submit without the boundary? Old concrete seam is
   disabled; new service uses one seam. External Work direct actions remain callable.
2. Can a caller fabricate/reuse receipt? Publicly recomputed/altered receipt fails
   issuer registry check; replay fails durable unique claims, including across restart.
3. BCC-only edit? Full normalized identity/role/address transaction digest changes.
4. Role swap at same addresses? Roles are transaction- and readback-bound.
5. Already-Sent repair? Matching Sent blocks all issuance; prior claim prevents retry
   even if provider readback fails or state loader has not yet observed the send.
6. Provider success without readback? Mandatory MID/TID/label/recipient readback;
   missing identity or readback never returns VERIFIED_SENT.
7. Background bypass? Service calls are gated; direct external tools still bypass.
8. Finalized draft bypass? Service operations gated; external tools still bypass.

## Concrete tool-host integration contract — remaining blocker

Deploy the service authority outside composer execution. Expose only:

- `correspondence.issue(transaction, ttl_seconds?, dry_run?)` -> registered v3 receipt
  or BLOCK/AUDIT_ONLY; no client evidence/capsule/provider callback arguments.
- `correspondence.execute(transaction, receipt)` -> BLOCK/HOLD, DRAFT_SAVED,
  VERIFIED_SENT, PROVIDER_STATE_UNKNOWN, or PROVIDER_SENT_INTEGRITY_INCIDENT.

Authenticated service bootstrap must pin account, work order, routing/Contacts source
and intended purpose/roles; fully paginate fresh Sent, full threads and drafts;
reconcile Email Log, Action Queue and Correspondence Routing; reconstruct the existing
state schema; declare conflicts/incomplete sources; and keep its evidence/DB/provider
capabilities unreachable to callers. Context source references must identify exact
current revisions. Sent message IDs/addresses mean **matching coverage of the proposed
ask/delta**, not every outbound ever in a thread. Even unmatched provider-Sent events
count toward the follow-up count. No pagination failure may become empty coverage.

Provider adapter contract:

- `read_draft(account_key, draft_id)` returns draft_id/message_id/thread_id,
  subject, complete MIME payload, and explicit normalized to/cc/bcc arrays.
- `submit(args)` maps one of the six supported operations to the provider action;
  must honor explicit recipient arrays, never expand reply-all implicitly, and
  returns canonical nonempty id/thread_id for sends. Draft updates apply the full
  bound payload/headers. No alternate helper may own credentials.
- `read_sent(account_key, exact_mid)` returns exact id/thread_id, SENT label_ids
  and complete explicit to/cc/bcc arrays; omitted BCC is not an empty verified BCC.

**Required host change:** remove/deny direct Gmail send_email/send_draft and finalized
create/update draft capabilities for the YUMORI operator and its scheduled/background
sessions, leaving provider mutations accessible only to this service. A prompt,
skill, loaded script, RPC receipt or one successful guarded email does not prove this
capability isolation. Provider credentials must not be reachable by alternate imports,
browser sends or generic tool dispatch in those governed sessions. If send_draft cannot
be conditionally submitted against a checked revision, pin a provider-owned immutable
send snapshot or reconstruct the authorized MIME message under an exclusive draft
lease. Current Work connector exposes no conditional draft-send revision parameter.

Before closure: install and qualify that authenticated reconciliation/adapter/host
configuration; test rejected direct tools and scheduled helpers on the actual operator;
prove durable DB exclusivity; test draft races; obtain exact-head CI/main receipts.
Live correspondence verification belongs to the independent operator, not this task.

## Acceptance disposition

Repository tests prove only the service-owned contract. Actual operator adapter,
trusted live reconciliation, capability isolation, immutable draft submission and
production deployment remain **OPEN**. #1779 remains OPEN; external-send containment
cannot be removed. Under 012's explicit merge condition, this corrective PR remains
unmerged until actual send-path acceptance is met. No historical message is resent.

## October 2 live evidence and regression update

The Council reply crossed provider Sent at 18:45 JST on October 2. Independent
exact-message readback confirmed SENT, the reported MID/TID, one To, one CC,
three BCC and the three-site PDF. The private canonical YUMORI Moshpit already
contained this event; its existing entry was reconciled in place, without duplicate
activity, private BCC disclosure or another send. State: provider-Sent with exact
recipient readback passed; Council owns the next move. Never recreate this message
as delivery repair. No real addresses, body or provider IDs are in public fixtures.

This is positive evidence of one transaction's recipient integrity and negative
evidence for any claim that the live operator was capability-isolated. It did not
pass through the repository service. Successful readback does not qualify #1779.

**A — Repository-enforceable:** the existing service owns canonical preflight,
private issuance, freshness, exact identity/role/BCC/attachment/reply/purpose/scope
binding, state and finalized-draft gates, Sent watermark, durable one-shot claims,
exact provider readback, unknown-state retention and no automatic incident resend.
The existing test owner now has one fully synthetic Council-shape fixture and
17 additional cases: exact submission/replay, missing/extra/role-moved BCC,
one-character address, thread/reply/purpose/scope/attachment drift, changed watermark,
MID/TID/recipient readback incident, provider ambiguity and already-Sent repair.
All pre-submission defects assert zero provider submissions (and zero Sent reads).

**B — Host-enforceable:** active Work still exposes send_email, send_draft and
recipient-finalized create/update draft with no receipt/capsule parameter. Repository
code cannot intercept tools outside its runtime. Host must deny those direct actions
and alternate mutation capabilities in every governed autonomous/operator/background
session, expose only authenticated service issue/execute, isolate credentials and
receipt/state storage, and qualify immutable/conditional draft submission. Until actual
host-denial evidence exists, #1779 remains OPEN and global mechanical external-send
containment cannot be declared removed. No second wrapper is proposed.

The separately merged #2032 operating policy permits specifically 012-directed Work
with its live checks; this policy distinction is not mechanical enforcement. Red Dog
AUTO remains contained. Neither this engineering task nor its fixtures send mail.
WSP97 lexical retrieval was source-bound to this feature head, with UNKNOWN freshness
and an index gap; direct tests/source/tool schemas filled the missing evidence.

## Recipient interpretation correction

Recent STT “Akida” / “Akita” refers to **Akira Hasegawa**. It is not a separate person
or Contact ID. Do not create an Akita contact or infer a new email route. Resolve the
existing Hasegawa contact from current authoritative records before live preflight.
