# AI Overseer - FoundUp Genesis Intake ROADMAP

Scope: the `src/foundup_genesis/` intake trajectory (envelope -> validator -> gate -> builder ->
scaffold). The broader AI Overseer roadmap lives in README.md / ModLog.md.

## Genesis prototype compatibility qualification — 2026-09-21

Static C3/I3/D2/Impact2 = **10/P2** qualification after the consumer isolation
repair merged in PR1838. This records exact existing contracts, not a skill
invocation, fresh test pass, production admission or complete WSP109 workflow.

| Existing owner | Current contract and missing evidence |
|---|---|
| [Genesis Skillz](skillz/foundup_genesis_intake/SKILLz.md) | Prototype instruction document, `category: workflow`, `evals: []`; no adjacent executor or manifest. Empty evals alone is not a prototype hygiene rejection. The described scaffold/build sequence is a plan. |
| [Canonical loader](../../infrastructure/wre_core/skillz/wre_skills_loader.py) | `foundup_genesis_intake` has no canonical registry entry. `load_skill` rejects it before reading content; same-name search cannot substitute. A temporary injected registry can support local content evaluation without changing production registration. |
| [Safety guard](../../communication/moltbot_bridge/src/skill_safety_guard.py) | The default manifest-required path rejects the absent manifest before looking up/spawning a scanner. The rejection's `available=True` field does not prove scanner installation. Existing exact-file SKILLz CLI support needs no new adapter. |
| [Typed builder](src/foundup_genesis/intake_packet_builder.py) | Recognized `key: value` fields and four-part acceptance lines produce a draft; ordinary prose returns `NO_ENVELOPE`. It calls the existing programmatic gate, not the Skillz document, and neither writes the WSP109 document packet nor scaffolds, registers or authorizes workers. |
| [Validator](src/foundup_genesis/validator.py) and [actual gate](../../communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py) | Strict structural checks exist. `existing_ids` can reject new-ID collisions, but the lazy default gate supplies only strict mode. It does not certify current namespace occupancy. Evidence-string presence is not independent implementation verification. |

**AmIBot reuse:** `detect_ai` is already registered. Do not create another identity,
rerun new-entity onboarding as though it were absent, or inject a blanket duplicate-ID
rejection into the existing-FoundUp build path. The create-versus-extend contract
must remain explicit; current gate success grants neither registry nor build effects.

**Local evaluation:** existing loader/scanner tests already cover injected relative
registry roots, no same-name fallback, direct SKILLz scanning and manifest rejection
before subprocess. Existing intake tests cover structured success, unstructured/empty
input, invalid IDs and injected existing-ID conflicts. A disposable copy with temporary
registry/manifest and a mocked scanner can assess artifact compatibility, but adding
generic fixtures solely to repeat these mechanisms would duplicate coverage.

**Production gap:** retain WSP95's exact digests, held-out outcome/security/regression
evidence, runtime/model/tool binding, independent promotion receipt, rollback and lineage.
No such evidence is created by this static review. A model/evaluator experiment must
declare its fixtures, import/effect boundary and outcome oracle before execution.

Retrieval preserved `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`; the read-only lexical
bundle binds current `49f878ffa` with UNKNOWN freshness/index gap, not semantic authority.
Existing governed Holo maintenance owns repair; no inline reindex or service launch.
`memory/README.md` is absent; no placeholder was added. Static inspection followed
the adjacent actual gate and manifest-validation helper to settle their input/failure
boundaries; this narrow read refinement grants no additional execution scope.
Independent findings, source hashes, comparison and next selection live in the
[canonical RSI backlog](../../../docs/roadmaps/rsi_swarm_backlog.json).
The conditional next **10/P2** action is the existing public alias/discovery contract:
decide one compatible representation and behavioral oracle under WSP104 while
preserving hidden `detect_ai` and membership gates. No new identity or activation.

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
