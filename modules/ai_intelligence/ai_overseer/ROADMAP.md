# AI Overseer - FoundUp Genesis Intake ROADMAP

Scope: the `src/foundup_genesis/` intake trajectory (envelope -> validator -> gate -> builder ->
scaffold). The broader AI Overseer roadmap lives in README.md / ModLog.md.

## Cross-cutting active P0

- Holo retrieval A-grade evidence now has a pure sealed-corpus gate with an
  injected signature-verifier seam; independent signing trust is not deployed.
  Its thresholds are non-downgradable and its callable facade is content-bound
  in the backend closure, but no non-test/VSIX operation invokes it yet.
  Runtime identity now binds the child executable, ABI/platform, verified
  RedDog source bytes, distribution build records, replica/model closure, and
  actual controls; the gate rejects because installed dependency payload bytes
  are not exact-closure verified. The benchmark reuses one owner across its
  corpus, but RedDog still needs a resident authenticated owner for normal
  operation. Then publish an exact-main generation, rerun the public corpus,
  and obtain an independently administered sealed evaluation. Promotion,
  canary, rollback, and outcome learning remain separate authority transactions.

## Landed

- Four baseline fixture failures repaired locally (2026-09-20): exact test error taxonomy and
  canonical disposable manifests/IDs; production guards unchanged. Focused205/connected677
  pass without skips. Independent review and remote closure are in the root RSI backlog.

- `FoundUpGenesisEnvelope` schema + strict validator (WSP 97 truth markers, WSP 104 id format).
- OpenClaw genesis gate wired into `dispatch_foundup` and characterization-tested (#740).
- Hermes builder **dry-run by default** + double opt-in for real writes (#919).
- **WSP109_INTAKE_PACKET_BUILDER_PHASE1** (this slice): chat idea -> `FoundUpGenesisEnvelope` ->
  genesis gate, draft evaluation only. It does not grant public launch/commander authority.
- Commander handoff candidate (2026-09-20): existing `OpenClawIntent.metadata` -> revalidated,
  detached queued-job payload. Independent acceptance and exact closure are tracked in the
  root RSI backlog; no new action, scaffold admission, registry entry, or live worker.

## Next

- **FOUNDUP_SCAFFOLD_CONTRACT_PHASE1**: typed creation fields, route snapshots and the dry-run
  planner already exist in `foundup_job_contract.py`, WRE's `foundup_scaffold_route_contract.py`
  and `modules/foundups/agent/src/create_foundup_dryrun.py`. Extend these owners; do not redefine them.
  Remaining: public draft -> authenticated owner/commander admission, planner lineage and an
  independently verified valve-gated execution path. Draft intake is not that authorization.
- **WSP_109_FRESH_WORKER_EXECUTION_VALIDATION_PHASE1**: prove a fresh worker executes WSP 109 from
  protocol text alone.
- **HOLOINDEX_FOUNDUP_CREATION_AUDIT_DISCOVERABILITY_PHASE1**: re-index the new audit docs so they
  surface in HoloIndex (explicit operator action, never RedDog runtime).

## Boundary

Intake and scaffold remain dry-run / no-mutation until an explicit, valve-gated execution slice.
FAM and Hermes real-write paths stay blocked/stubbed. The genesis validator is the authority on
envelope validity; the builder only normalises structured intake -- it does not decide validity.
