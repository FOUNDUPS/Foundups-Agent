# RedDog HoloIndex Runtime Contract

## P16 operational recovery controls — 2026-10-05

At source `6efbc3ac1`, four actual controller attempts ended in startup failure,
snapshot-probe failure, retry-wait, then semantic-backend failure. The last attempt
invalidated the canonical index before failure. Its saved
`cli_maintenance_in_progress` receipt, original failed task and retry history remain
preserved after normal new-head maintenance. Do not manually restore old receipts,
create a fresh task database, bypass retry delays or admit generic `STALE_INDEX`.

The bounded external launch qualified these exact process settings:

- `PYDANTIC_DISABLE_PLUGINS=__all__` disables installed plugin enumeration while
  retaining ordinary validation; prior denied startup observations remain evidence.
- `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=safe.directory`, and
  `GIT_CONFIG_VALUE_0=O:/Foundups-Agent` replay the verified existing trusted entry
  with private HOME. No wildcard or global Git change was made.
- `TORCHINDUCTOR_CACHE_DIR=O:/rsi-p16-temp-20261005/maintenance/torchinductor`
  selects owned private cache storage without importing an account username.

Keep the actual refresh `-S -B` and pinned site through `PYTHONPATH`; no
`site.addsitedir` change was needed. Offline paired imports measured the missing
`pwd` failure at 6.750s and successful import at 8.000s. One subsequent cached
MiniLM constructor and fixed encode passed in 8.047s parent time: 384 finite
nonzero float32 values, observed CPU, stable pins and no recorded denials. The
source-matched IPv6 loopback probe closed. These are finite diagnostics, not a
filesystem sandbox, index proof or service admission.

PR2063 merged/main-verified at `2eaa6de7`, with 181 hosted recovery cases. An
incident pointer still requires durable current-head/root task/request validation.
The actual 500.797s completion used normal admission for the new HEAD, not live
pointer resume. Both owned runtimes stopped, the new task completed at retry 0,
and the old task/three events stayed unchanged. A separate clean-checkout query
proved CURRENT/no-gap for generation `b90d637c…`; the stale shared-checkout query
remains a mismatch. Existing CLAUDE guidance already selects the correct source.
This is captured exact-head grounding, not all optional collections, retrieval
fitness or native RSI closure. See the [P16 checkpoint](../../../../docs/operations/RSI_SWARM_DISPATCH.md#existing-holo-grounding--p16-checkpoint).

## Post-merge controller

`run_holoindex_postmerge_runtime_once(repo_root=..., query=...,
timeout_seconds=..., resume_incident_id=None)` requires a clean HEAD equal to
`refs/remotes/origin/main`. A verified CURRENT owner returns without starting
anything. Otherwise, only a sealed exact-head incident-repair receipt may
admit the existing broker-managed chain:

`OpenClaw poller -> AgentDB claim -> post-merge executor -> authority transaction -> atomic completion`

To recover a previously admitted refresh after index invalidation, supply the
original `incident_id` as `resume_incident_id` (also accepted by the one-shot
JSON CLI). The controller returns this pointer after accepted admission and
preserves it through execution or cleanup failure. It is not authority: the
existing incident owner re-reads the exact root-owned event, task and request,
validates their HEAD/root bindings, and allows only pending, failed or retry-wait
tasks to reach the existing coordinator. Missing or altered admission rejects;
generic `STALE_INDEX` without a pointer still rejects. Existing retry count and
300-second delay remain authoritative; a resumed `RETRY_WAIT` returns non-success
without starting broker runtimes. Completion and cleanup requirements remain.
If main has advanced, the old pointer cannot admit work for the new HEAD: retain
its history and use the existing fresh-head incident path. These are canonical
store integrity checks, not protection against an arbitrary database writer.

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
