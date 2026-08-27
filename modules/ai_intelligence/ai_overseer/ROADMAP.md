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

- `FoundUpGenesisEnvelope` schema + strict validator (WSP 97 truth markers, WSP 104 id format).
- OpenClaw genesis gate wired into `dispatch_foundup` and characterization-tested (#740).
- Hermes builder **dry-run by default** + double opt-in for real writes (#919).
- **WSP109_INTAKE_PACKET_BUILDER_PHASE1** (this slice): chat idea -> `FoundUpGenesisEnvelope` ->
  genesis gate, dry-run only. Proves the WSP 109 handoff artifact reaches the gate; makes the
  valid-envelope launch branch reachable end-to-end.

## Next

- **FOUNDUP_SCAFFOLD_CONTRACT_PHASE1** (P2): define the `create_foundup` action + typed creation
  fields, and the mapping intake packet -> WSP-49 module + `foundup_manifest.json` + registry seed,
  with a valve-gated write owner. Decision/contract only (no scaffold write).
- **WSP_109_FRESH_WORKER_EXECUTION_VALIDATION_PHASE1**: prove a fresh worker executes WSP 109 from
  protocol text alone.
- **HOLOINDEX_FOUNDUP_CREATION_AUDIT_DISCOVERABILITY_PHASE1**: re-index the new audit docs so they
  surface in HoloIndex (explicit operator action, never RedDog runtime).

## Boundary

Intake and scaffold remain dry-run / no-mutation until an explicit, valve-gated execution slice.
FAM and Hermes real-write paths stay blocked/stubbed. The genesis validator is the authority on
envelope validity; the builder only normalises structured intake -- it does not decide validity.
