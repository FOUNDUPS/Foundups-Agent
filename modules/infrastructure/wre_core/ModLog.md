# WRE Core - ModLog
## Chronological Change Log

### [2026-09-09] - YUMORI.ME CONTACT LEDGER PROTOTYPE REGISTRATION

- Registered `yumori_contact_ledger` as the 29th WRE Skillz entry, owned by
  `modules/foundups/esingularity/skillz/yumori_contact_ledger`.
- Kept the capability at `prototype`: it is discoverable by RedDog/WRE Rolodex
  grounding but has no production execution or Gmail/Drive effect authority.
- The Skillz binds YUMORI.me contact reconciliation to Gmail `message_id` /
  `thread_id` lineage and the connected `YUMORI.me Contacts` / `Email Log`
  index rather than inventing a duplicate tracking signature.
- eSingularity owns the workflow/context tests; live correspondence truth stays
  in connected Gmail/Drive and must be read before current-state claims.
  (WSP 22/50/95/97)

### [2026-08-29] - BOUNDED GIT BINARY STDIN HARDENING

- Extended `run_bounded_stdout` with an <=8 MiB binary stdin channel for
  batched exact-object reads while concurrently draining bounded stdout.
- Added deterministic broken-pipe handling, timeout/output-overflow process
  termination, named writer/reader cleanup, and explicit pipe closure.
- Extracted the generic pipe/thread pump into `wre_git_process_io.py`; the
  public Git wrapper is 109 lines and the private pump is 143 lines, restoring
  the registry subsystem's stricter 200-line WSP_62 ceiling without changing
  the public API.
- Six focused tests cover round-trip input, pre-spawn ceiling rejection, early
  child exit, blocked-writer timeout cleanup, concurrent output overflow, and
  the existing stdout ceiling. This adds no Git mutation or execution authority.
- Reprojected the canonical test registry to **1,631 registered / 268
  quarantined**; the RedDog builder contract suite no longer invokes a local
  helper at module scope, check mode passes, and all 28 registry tests pass.

### [2026-08-28] - REDDOG OWNER-PROOF REGISTRY REPROJECTION

- Registered the distinct post-completion owner-proof falsifier after staging
  exact Git identity: **1,601 registered / 268 quarantined**.
- Generator write/check and the registry/differential/indexing selection pass
  **94/94** without relaxing capability, quarantine, shard, collection, timeout,
  or execution policy. (WSP 5/6/22/50/62/87/97)

### [2026-08-27] - HOLO LARGE-FILE PROOF REGISTRY HARDENING

- Reprojected the canonical registry after the Holo large-file health proof was
  made import-safe and cleanup-safe. It moves from quarantined operational
  collection to a collectable unit surface without relaxing registry policy:
  **1,591 registered / 267 quarantined**.
- The generator write/check and both dedicated registry suites pass **45/45**.
  (WSP 5/6/22/50/62/87/97)

### [2026-08-27] - GOVERNED FMAS HEALTH ADMISSION / TRACKED INVENTORY

- Added a clean-exact-HEAD WSP 62 health gate that binds candidate/baseline Git
  identity, canonical scanner bytes, the complete producer digest, exclusion
  reasons, exact tracked scope, deterministic dispositions, and capped dry-run
  `ImprovementJob` proposals. No-baseline debt emits no jobs.
- Quarantined direct string and structured WSP 62 bridge input, rejected
  traversal, Windows-aliased, reserved-device, and ADS scope from local
  auto-approval eligibility, replaced an exponential-backtracking path regex
  with bounded segment-delimited parsing, and kept
  every direct RedDog FMAS direction advisory with zero readiness authority.
- Changed canonical FMAS size inventory to Git-tracked files, with an explicit
  exact-inventory input for governed callers. The live scan fell from 4,955
  observations / roughly 64 seconds to 471 / 16.3 seconds; critical noise fell
  from 2,665 to 67 by excluding ignored/runtime/vendor closure before parsing.
- Applied WSP 62 to the implementation: extracted finding, WSP 62 parsing,
  path/identity, and triage contracts; the FMAS bridge fell from 876 to 722
  lines and no new or grown candidate function exceeds 50 lines.
- Reconciled WSP 4, WSP 62, and the master index in both canonical mirrors:
  inclusive 50-line ceilings, exact candidate-commit inventory, differential
  candidate debt, inherited-debt nonblocking, and proposal-only model/worker
  authority now match the implemented scanner and health gate.
- Clarified that the legacy `WSP15Priority` object is qualitative execution-
  risk metadata, not canonical numeric WSP 15 MPS or a signed allocation
  receipt. Updated README, interface, roadmap, navigation, and test ledgers.
- WSP 15 allocation: C=4, I=5, D=5, Impact=5, total **19/P0** because noisy
  health debt could otherwise be promoted as candidate work or block unrelated
  RedDog progress.
- Verification: the focused O:-resident command covering modular audit, health
  admission/bridge/job/direction, route exemptions, and WSP 97 validation is
  **310 passed / 1 capability skip**. It invoked no model, worker, queue,
  authority/shared-checkout mutation, Holo, promotion, or production database
  effect; isolated tests create and mutate disposable temporary Git fixtures.
- Separate exact-main integration validation used the real OpenClaw resident and
  supervisor to complete AgentDB task `holoindex_postmerge_refresh:3f2c11de...`
  in 481.6 seconds. Two governed queries then returned CURRENT/no-gap/no-reindex
  with unchanged generation, descriptor, replica, and path-identity digests.
  Retrieval found the canonical FMAS bridge but also ranked stale historical
  orphan reports, so direct current-code verification remained mandatory.
  (WSP 00/15/22/50/62/79/87/97)

### [2026-08-27] - REDDOG POST-MERGE REGISTRY REPROJECTION

- Reprojected the canonical test registry after the RedDog containment bridge
  and traceability work merged to `main`.
- Preserved the tested registry generation policy and recorded the resulting
  count movement rather than changing execution authority.

### [2026-08-26] - WSP 95 ADMISSION RECEIPT BINDING

- Bound production Skillz execution to exact registry/frontmatter agreement,
  adjacent manifest/scanner admission, stable bundle fingerprints, captured
  executor bytes, and exact Boolean + typed effect receipt validation.
- Clarified proposal-only local-model behavior, blocked unbound A/B runtime
  selection and CodeAct execution, and documented missing independent production
  promotion authority.

### [2026-08-25] - TEST REGISTRY SHARD PROJECTION

- Added canonical bounded test-registry shard generation and selection surfaces.
- Kept the registry as discovery/selection metadata rather than execution
  authority.
