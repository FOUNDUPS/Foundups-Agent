# RedDog HoloIndex Runtime Contract

## Post-merge controller

`run_holoindex_postmerge_runtime_once(repo_root=..., query=...,
timeout_seconds=...)` requires a clean HEAD equal to
`refs/remotes/origin/main`. A verified CURRENT owner returns without starting
anything. Otherwise, only a sealed exact-head incident-repair receipt may
admit the existing broker-managed chain:

`OpenClaw poller -> AgentDB claim -> post-merge executor -> authority transaction -> atomic completion`

The ordinary post-merge transition first appears as a fail-closed
`REPO_HEAD_MISMATCH`: the exact-main authority is current while the canonical
freshness receipt still names the preceding commit. This happens before owner
acquisition, so `owner_attempts` is exactly zero and no owner query receipt
exists. Repair admission requires the fixed query, `STALE`, the stale receipt
HEAD distinct from the accepted authority HEAD, exact workspace/authority/root
bindings, generation and freshness digests, empty semantic result, committed-
HEAD authority, and explicit no-reindex/no-mutation claims. The coordinator
then independently repeats the query and requires the same stale receipt HEAD,
generation, freshness digest, and canonical bounded reason set before it can
create/reconcile the existing exact-HEAD task. The ordinary shared owner
classifier remains receipt-bound. All other
repairable owner failures still require an integrity-bound query receipt and
both lower-level attempts.

Register-only bootstrap directly registers only the resident and supervisor
specs; it invokes no main bootstrap, autostart, MCP registration, or ambient
environment mutation.
One canonical-store cross-process lease serializes the complete controller
lifecycle. When no OpenClaw runtime exists, the controller starts resident then
supervisor and records ownership. The supervisor receives explicit
`holoindex_postmerge_only` mode and the exact admitted task ID through broker
launch arguments; a live registration call must acknowledge the same task
before completion waiting. A bound poller cannot schedule or replace it. That mode
disables restart, self-audit, signed/autonomous/general-maintenance work,
skill/mutation reporting, nudges, and continuity breadcrumbs without changing
process-global environment. When both broker runtimes already exist, it
preserves their configuration and lifecycle. Partial or raced ownership
rejects.

Resident, supervisor, dispatch, sealed-executor, and server imports are
preflighted before repair coordination may create an AgentDB task. During
completion waiting, both broker threads and the exact task binding, status,
source, schema, target HEAD, sealed authority digest, skills, assignee, and
active claim are rechecked. Pending/assigned unchanged state is bounded to 60
seconds; executing observation retains its 7,500-second v2 integrity-bound
AgentDB claim lease because healthy materialization has exceeded 1,800 seconds.
The claim digest includes its schema, ID, issued time, expiry, assignee, and
complete task context; the stored assignment timestamp must equal issuance.
The atomic completion transaction rejects a first terminal commit at or after
expiry while permitting only an exact already-completed replay whose recorded
completion preceded expiry. This is deterministic AgentDB/CAS integrity, not a
secret MAC or signature against an arbitrary database writer. Runtime death/error,
missing or drifted tasks, failure/supersession, retry wait, expired claims, or
completed state without its atomic receipt rejects before the outer timeout.

After completion or failure, a pre-existing supervisor must acknowledge exact
release so another current task can bind. A controller-owned supervisor is not
released first: it remains task-bound until reverse-order shutdown proves its
thread dead, closing the release-to-periodic-poll interleaving.

Completion requires `validate_holoindex_postmerge_completion()`, equal final
owner generation/freshness receipt, CURRENT/no-gap/no-reindex evidence, and a
final clean exact-main Git proof on every accepted completion or OWNER_READY
path. Cleanup runs for normal, exceptional, and
interrupted paths; owned supervisor stops before owned resident, and success is
revoked unless every owned broker thread is dead. Rejected CLI operations exit
nonzero and expose fixed secret-free reasons.

The lease currently fences task admission, observation, and AgentDB completion.
It does not cancel an already-started authority call or recheck lease authority
inside every external activation/route CAS. Therefore timeout cannot be claimed
as full effect fencing, and A-grade remains blocked on a renewable execution
heartbeat or an equivalent use-time guard at the final external-effect boundary.

After exact atomic completion, owner readiness uses at most two controller
proofs inside one budget capped by both the remaining transaction deadline and
300 seconds from first proof. Only a fully receipt-integrity, authority,
semantic-evidence, and error-bound failure that exhausted both lower-level
owner attempts with an allowlisted transient reason admits the immediate second
proof. The controller supplies acquisition cycle zero then one; each cycle uses
two deterministic nonrepeating process shards, and the selected cycle is bound
into the result and receipt. There is no sleep. Wrong cycle, completion
generation/freshness, stale or
rejected authority, deterministic failure, malformed/forged evidence, and an
expired budget reject after the first observation. The lower-level two-attempt
owner acquisition remains independently bounded inside each proof.

## Owner response binding

`query_holoindex_owner(...)` requires descriptor digest, generation ID, replica
ID, path-identity digest, runtime ranker digest, runtime-environment digest, and
the explicit exact-closure flag. The one-shot bridge compares them with the
route admitted before owner startup. Missing, malformed, or unequal fields fail
closed.

`GenerationBoundHoloIndexQueryAdapter.query(...)` uses the supervisor-vetted
runtime through a scrubbed `python -S -B` child. It re-verifies receipts, filters
scope before limiting, and projects safe hit metadata only; raw buckets, route
data, credentials, and nested receipts never enter Fusion. The Python worker
wall is 60 seconds with 57 seconds available to the child and three reserved
for cleanup. Canonical CLI and asynchronous VSIX cold paths use 300 seconds.
Committed authority permits caller overlays; `clean_workspace_head` does not.

## Current truth and scale

Merged exact main `09e98fff04b4d94544d97a1dd7b795785d13db2e`
live-accepted the pre-owner `REPO_HEAD_MISMATCH` ingress. The exact canonical
task completed through OpenClaw/WRE at generation `sha256:7869f238...`, its
owned resident and supervisor stopped cleanly, and the controller performed no
reindex. A fresh owner query returned CURRENT/no-gap/no-reindex on attempt one
with equal workspace/authority HEADs and no overlay. Full verification retained
33 artifacts / 222,719,702 bytes at descriptor `sha256:af0e9a2a...`, replica
`sha256:fb03a1db...`, and path identity `sha256:4d5c10b7...`.
This exact-commit result closes the pre-owner repair gate only.

Exact-main `724954fa3799b19174a7ac0b653da8c95e9ccf13` exposed the controller
false-negative after real OpenClaw maintenance and atomic completion succeeded:
the post-completion classifier passed the selected clean authority back into
`query_once` as its workspace root, so the resolver correctly returned
`HOLOINDEX_AUTHORITY_ROOT_INVALID`. Merged exact-main
`da558d5187013dc77cb2fdc2ebfaaa2fe68dcaa6` then passed the repaired controller
on its first transaction. Maintenance, activation, verification, atomic task
completion, and reverse-order owned-runtime shutdown produced generation
`sha256:9c7e3ab6e5f8ebb45c622a6ab20ea8320fc2b530d858a7b214506cc69180b331`.
A fresh owner query was CURRENT/no-gap/no-reindex on attempt one; post-query
full verification retained 33 artifacts / 222,647,465 bytes at descriptor
`sha256:87990aba7757a556bd908f7fe64bc7ae7fe81f6f560c25aa4919285ccd953b1d`.
This proves the merged root-separation path at that commit only. The
high-risk decision record is
`docs/audits/security/REDDOG_HOLO_OWNER_QUERY_WORKSPACE_ROOT_ASSUMPTION_AUDIT_20260828.md`.

The runtime-environment digest covers executable, ABI/platform, verified RedDog
source, distribution build records, replica/model artifacts, and allowlisted
settings. It does not yet prove the current Python stdlib/native closure,
external loader policy, signature, or write denial, so
`runtime_environment_exact_closure_verified` remains false. The 1.85 GB
dependency closure cannot be hashed per query; A-grade scale requires
asynchronous signed/protected promotion plus a resident authenticated owner.

Base-bound maintenance/freshness self-repair and the merged pre-owner ingress
are observed operational at their named commits. Retrieval-quality RSI still requires
an authenticated proposer, independently sealed evaluator, separate promoter,
CAS/canary/semantic rollback, signed outcome ledger, and bounded WRE feedback
loop. No outbound Hermes dispatch is part of this contract.
