# RedDog HoloIndex Runtime Contract

## Post-merge controller

`run_holoindex_postmerge_runtime_once(repo_root=..., query=...,
timeout_seconds=...)` requires a clean HEAD equal to
`refs/remotes/origin/main`. A verified CURRENT owner returns without starting
anything. Otherwise, only a sealed exact-head incident-repair receipt may
admit the existing broker-managed chain:

`OpenClaw poller -> AgentDB claim -> post-merge executor -> authority transaction -> atomic completion`

Register-only bootstrap directly registers only the resident and supervisor
specs; it invokes no main bootstrap, autostart, MCP registration, or ambient
environment mutation.
One canonical-store cross-process lease serializes the complete controller
lifecycle. When no OpenClaw runtime exists, the controller starts resident then
supervisor and records ownership. The supervisor receives the explicit
`holoindex_postmerge_only` mode through broker launch arguments; that mode
disables restart, self-audit, signed/autonomous/general-maintenance work,
skill/mutation reporting, nudges, and continuity breadcrumbs without changing
process-global environment. When both broker runtimes already exist, it
preserves their configuration and lifecycle. Partial or raced ownership
rejects.

Completion requires `validate_holoindex_postmerge_completion()`, equal final
owner generation/freshness receipt, CURRENT/no-gap/no-reindex evidence, and a
final clean exact-main Git proof on every accepted completion or OWNER_READY
path. Cleanup runs for normal, exceptional, and
interrupted paths; owned supervisor stops before owned resident, and success is
revoked unless every owned broker thread is dead. Rejected CLI operations exit
nonzero and expose fixed secret-free reasons.

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

Exact-main `5e0835c690e0f4f1712c7021a75abdc35aadeca0` completed through
the real OpenClaw supervisor at generation `sha256:ee72c0a0d1e159e19971dac0bbdcdeb98917eb7051a1690759f72fa65b4b2915`. A governed
query returned CURRENT/no-gap/no-reindex in 3.75 seconds; full revalidation
preserved 33 artifacts / 221,734,133 bytes. Evidence is commit-bound.

The runtime-environment digest covers executable, ABI/platform, verified RedDog
source, distribution build records, replica/model artifacts, and allowlisted
settings. It does not yet prove the current Python stdlib/native closure,
external loader policy, signature, or write denial, so
`runtime_environment_exact_closure_verified` remains false. The 1.85 GB
dependency closure cannot be hashed per query; A-grade scale requires
asynchronous signed/protected promotion plus a resident authenticated owner.

Maintenance self-repair is operational. Retrieval-quality RSI still requires
an authenticated proposer, independently sealed evaluator, separate promoter,
CAS/canary/semantic rollback, signed outcome ledger, and bounded WRE feedback
loop. No outbound Hermes dispatch is part of this contract.
