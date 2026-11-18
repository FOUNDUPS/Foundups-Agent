# FOUNDUP_SCAFFOLD_CONTRACT_PHASE1

**Slice:** `FOUNDUP_SCAFFOLD_CONTRACT_PHASE1`
**Author:** 0102 (RedDog Architect)
**Date:** 2026-07-04
**Type:** Decision / contract doc ONLY (no runtime code)
**Base:** `ca32bc082` (main; includes P0 #919 Hermes dry-run default + P1 #920 WSP109 intake builder)
**WSP lock:** WSP_00, WSP_15, WSP_22, WSP_49, WSP_50, WSP_97, WSP_109
**Supersedes:** the queued-preview stub of this file (open questions Q1-Q3 resolved in Section 4.4).

---

## 0. Scope Guard / Truth Boundary Checklist (WSP_97)

This slice is a contract. It defines the missing binding from a validated WSP 109 intake packet
to a real monorepo FoundUp scaffold. It ships **no executor**.

| Scope guard | Status |
|-------------|--------|
| DECISION_CONTRACT_ONLY | YES |
| NO_RUNTIME_SCAFFOLD_WRITER | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_HERMES_FAM_EXECUTION | YES |
| NO_WORKTREE_CREATION | YES |
| NO_BRANCH_OR_FILE_MUTATION_IN_THIS_SLICE | YES |
| NO_SKILLZ_AUTHORING | YES |
| CREATE_FOUNDUP_MUST_NOT_ALIAS_EXTRACT | YES |
| REDDOG_DOES_NOT_DIRECTLY_WRITE_FILES | YES |

---

## 1. Problem (audit anchor)

The RedDog FoundUp-creation execution-path audit established (all OBSERVED):

- No canonical action creates a NEW monorepo FoundUp scaffold. `CANONICAL_ACTIONS` =
  `build_foundup / extract_foundup / validate_foundup / queue_foundup_job`
  (`foundup_job_contract.py:54-59`) -- no `create_foundup`.
- `build_foundup` is aliased to extraction of an EXISTING module: "Build = full extraction
  (same as extract for now)" (`hermes_foundup_job_executor.py:332-337`), and the executor requires a
  pre-existing validated manifest (`hermes_foundup_job_executor.py:181-214`).
- P1 (#920) made the genesis gate reachable (idea -> `FoundUpGenesisEnvelope` -> `GATE_PASSED`,
  dry-run) but nothing turns a validated envelope into a scaffold.

This contract defines that missing binding so a future, valve-gated executor can be authored safely
WITHOUT ambiguity.

---

## 2. Required Direct-Read Evidence (Addendum A)

Every claim below is anchored to a file read directly for this slice. Truth label per row.

| Source | Evidence | Label |
|--------|----------|-------|
| `WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md` | 8 intake artifacts :132-141; manifest draft fields :323-336; internal FoundUp needs monorepo scaffold :521; registry search :374 | OBSERVED |
| `WSP_framework/src/WSP_49_Module_Directory_Structure_Standardization_Protocol.md` | mandatory structure :51-68 (src/tests/memory/README/INTERFACE/requirements); memory MANDATORY :100,216-223; tests README+TestModLog :60-62 | OBSERVED |
| `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py` | genesis gate :404-513; dispatch :840-902; FAM handoff still a NOTE stub :571-573 | OBSERVED |
| `modules/communication/moltbot_bridge/src/foundup_job_contract.py` | CANONICAL_ACTIONS :54-59; FoundUpJob fields :345-435; PolicyFlags server-authored :200-215 | OBSERVED |
| `modules/foundups/agent/src/hermes_foundup_job_executor.py` | build==extract :332-337; manifest-path preflight :181-214 | OBSERVED |
| `modules/foundups/agent/src/hermes_adapter.py` | dry-run by default (P0) :132-149; REQUIRED_CONTRACTS README/INTERFACE/ROADMAP/ModLog :110; adapter write gated on `not self.dry_run` :523-537 | OBSERVED |
| `modules/foundups/agent/src/foundup_manifest_validator.py` | build_contract + execution_routing contract :313-501; REQUIRED_GATES (8) :66-75; pinned routing :83-88; declarative_only/no self-authorize :469-479 | OBSERVED |
| `modules/ai_intelligence/ai_overseer/src/foundup_genesis/envelope.py` | FoundUpGenesisEnvelope schema :160-278; id pattern :287 | OBSERVED |
| `modules/ai_intelligence/ai_overseer/src/foundup_genesis/validator.py` | validity rules :236-407; reserved ids :157-165; valid categories :169-173 | OBSERVED |
| `modules/ai_intelligence/ai_overseer/src/foundup_genesis/intake_packet_builder.py` (P1 #920) | `build_intake_packet_dry_run` dry-run intake -> gate | OBSERVED |
| `modules/foundups/src/foundup_registry_loader.py` + `modules/foundups/foundup_registry.json` | registry root `entities[]` :74-89; entry fields (foundup_id/display_name/entity_type/module_path/stage/tier/implementation_status/token_status/poc_status/next_slice/manifest_status/manifest_path/hermes_openclaw_build_status); read-only, NO_REGISTRY_MUTATION :8-11 | OBSERVED |
| `modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py` | VALVE states :49-51; canonical intake targets :57; spine chain gates :173-232; opens to WORKTREE_CREATE only with sovereign token :300-316 | OBSERVED |
| `modules/foundups/agent/src/source_authority.py` | MONOREPO_POC only active; promotion raises (per #777 landed) | NEEDS_VERIFICATION (not re-read this slice; cited from prior audit) |
| P0 tests `test_hermes_foundup_builder.py::TestDryRunDefaultSafety` (#919) | dry-run default proven | OBSERVED |

---

## 3. `create_foundup` Action Semantics (Addendum B -- no alias)

`create_foundup` is a NEW, distinct action that authors a NEW monorepo FoundUp scaffold from a
validated intake packet. It is NOT extraction of an existing module.

| Action | Meaning | Precondition | Writes |
|--------|---------|--------------|--------|
| `create_foundup` (NEW) | Author a new `modules/foundups/{foundup_id}/` scaffold from a validated `FoundUpGenesisEnvelope` | envelope `GATE_PASSED`; `foundup_id` NOT already in registry | scaffold artifacts (valve-gated only) |
| `build_foundup` (existing) | Currently aliased to `extract_foundup` (`hermes_foundup_job_executor.py:332-337`) | existing module + validated manifest | none in scaffold sense (extraction) |
| `extract_foundup` (existing) | Exfoliate an EXISTING module to an external repo | existing validated manifest | external repo (out of scope) |

**Alias prevention (REQUEST_CHANGES if violated):**

- `create_foundup` MUST NOT resolve to `build_foundup` or `extract_foundup` handlers. A future
  executor MUST branch on the action string BEFORE dispatch and MUST reject a `create_foundup` job
  whose `foundup_id` already resolves in the registry (that is an update/extract, not a create).
- If, for transport reasons, `build_foundup` is retained as the carrier, the job MUST carry an
  explicit disambiguator `creation_mode: "new_scaffold"` in a typed field (NOT the opaque
  `foundup_job_contract.py:407-412` payload), and the executor MUST treat absence of
  `creation_mode=new_scaffold` as "not a create". Silent reuse of the extraction path for a
  non-existent module is a contract violation.
- **Name-collision note (adversarial-verify finding):** the identifier `create_foundup` is already
  used, UNRELATED, as a registry method `create_foundup(self, foundup)` in the agent_market subsystem
  (`modules/foundups/agent_market/src/{interfaces.py,in_memory.py,registry.py,persistence/sqlite_adapter.py}`)
  and the simulator FAM bridge (`modules/foundups/simulator/adapters/fam_bridge.py:117`). Those are
  market-entity CRUD, NOT a FoundUpJob `requested_action`. The new canonical ACTION string
  `create_foundup` must be namespaced/documented so it is not confused with that existing API.

---

## 4. Typed Creation Fields (Addendum C)

### 4.1 `FoundUpScaffoldContract` (typed schema, docs-only this slice)

| Field | Type | Rule |
|-------|------|------|
| `foundup_id` | str | WSP 104 `^[a-z][a-z0-9_]{2,49}$` (`envelope.py:287`); NOT in registry; NOT reserved (`validator.py:157-165`) |
| `display_name` | str | non-empty display string (control-char rejected per `validator.py:367-384`) |
| `entity_type` | str | WSP 109 decision tree (`foundup` for monorepo) |
| `module_path` | str | `modules/foundups/{foundup_id}` (repo-relative; exact-equality checked by `foundup_manifest_validator.py:251-275`) |
| `source_intake_packet_digest` | str (sha256) | digest of the 8-artifact WSP 109 packet |
| `genesis_envelope_digest` | str (sha256) | digest of the validated envelope that reached `GATE_PASSED` |
| `scaffold_artifacts[]` | list[str] | the Section 6 artifact set |
| `manifest_fields` | object | the Section 7 `build_contract` + `execution_routing` contract |
| `registry_seed` | object | the Section 8 entities[] entry (specified, NOT written this slice) |
| `allowed_paths[]` | list[str] | MUST contain `module_path/**` only |
| `denied_paths[]` | list[str] | MUST NOT overlap `allowed_paths`; MUST cover `.env`, `main.py`, `**/*_dae.py`, `vendor` (`foundup_manifest_validator.py:79-81`) |
| `write_owner` | str | `hermes` (executor) under `openclaw` orchestration (`foundup_manifest_validator.py:83-84`); NOT RedDog |
| `required_valve_state` | str | `VALVE_OPEN_WORKTREE_CREATE` (`reddog_wre_execution_valve.py:51`) |
| `rollback_plan` | str | non-empty; how to revert the scaffold |
| `validation_commands[]` | list[argv] | argv-only, no shell metachars (`foundup_manifest_validator.py:94-97`) |
| `receipt_chain[]` | list[str] | the Section 11 receipt digests |

### 4.2 `create_foundup` FoundUpJob fields

Extend the FoundUpJob contract (`foundup_job_contract.py:54-59`) with:

- `requested_action = "create_foundup"` added to `CANONICAL_ACTIONS`.
- Typed creation fields (NOT opaque `payload`): `scaffold_contract_digest`, `genesis_envelope_digest`,
  `creation_mode = "new_scaffold"`.
- Required payload keys (schema-validated by the future executor): `foundup_id`, `display_name`,
  `entity_type`, `module_path`.

### 4.3 Fail-closed rejection reasons (new `StatusReasonCode` candidates)

`FAIL_FOUNDUP_ID_EXISTS`, `FAIL_CREATE_ALIASED_TO_EXTRACT`, `FAIL_VALVE_NOT_OPEN`,
`FAIL_ENVELOPE_NOT_GATE_PASSED`, `FAIL_PATH_SCOPE_VIOLATION`, `FAIL_MANIFEST_CONTRACT_INVALID`.

### 4.4 Resolved Open Questions (from the superseded stub)

- **Q1 (new action vs alias):** RESOLVED -> `create_foundup` is a NEW canonical action, scaffold-only;
  it MUST NOT alias `build_foundup`/`extract_foundup` (Section 3).
- **Q2 (template location):** This contract fixes the artifact SET (Section 6), NOT a template
  directory. A future writer MAY source templates from
  `modules/infrastructure/wre_core/templates/wsp49_foundup/` (stub hypothesis) or generate inline;
  either is acceptable so long as the emitted set matches Section 6. Labeled INFERRED.
- **Q3 (consumer):** RESOLVED -> a dedicated future `FOUNDUP_SCAFFOLD_WRITER_PHASE1` executor
  (valve-gated, dry-run first), NOT `build_plan_generator`, to preserve the non-alias boundary.

---

## 5. Intake Packet -> Scaffold Artifact Mapping (directive 3)

| Intake / envelope field (`envelope.py`) | Scaffold artifact |
|------------------------------------------|-------------------|
| `foundup_id` | `module_path = modules/foundups/{foundup_id}`; manifest `foundup_id`; registry entry key |
| `name` / `display_name` | README title; manifest/registry `display_name` |
| `tagline` + `description` | README body; INTERFACE overview |
| `category` | registry `entity_type`/category tag |
| `acceptance_criteria[]` | `tests/TestModLog.md` seed + `POC_SCOPE.md`-derived first tests |
| `truth_state_map[]` | ModLog seed truth markers (WSP 97) |
| `lifecycle_stage` (idea/incubating) | registry `stage=incubating`, `poc_status=idea` |
| WSP 109 `SKILLS_MAP.md` | referenced only; SKILLz creation deferred to WSP 95 |

---

## 6. Required Scaffold Artifact Set (Addendum D -- WSP-49 checklist)

Reconciled from WSP 49 (mandatory structure) + WSP 11/12/22/60 + Hermes `REQUIRED_CONTRACTS`.

| Artifact | Required | Evidence | Label |
|----------|----------|----------|-------|
| `modules/foundups/{foundup_id}/` dir | YES | WSP_49:53; WSP_109:333 | OBSERVED |
| `__init__.py` | YES | WSP_49:54 | OBSERVED |
| `README.md` | YES | WSP_49:66; hermes_adapter.py:110 | OBSERVED |
| `INTERFACE.md` | YES | WSP_49:67 (WSP 11); hermes_adapter.py:110 | OBSERVED |
| `ROADMAP.md` | YES | hermes_adapter.py:110 (REQUIRED_CONTRACTS) | OBSERVED |
| `ModLog.md` | YES | WSP 22; hermes_adapter.py:110 | OBSERVED |
| `requirements.txt` | YES | WSP_49:68 (WSP 12) | OBSERVED |
| `src/` (`__init__.py` + entrypoint) | YES | WSP_49:55-57 | OBSERVED |
| `tests/` (`__init__.py`, `README.md`, `TestModLog.md`, `test_*.py`) | YES | WSP_49:58-62 | OBSERVED |
| `memory/` (+ `README.md`) | YES | WSP_49:63-64,100,216-223 (WSP 60 MANDATORY) | OBSERVED |
| `foundup_manifest.json` | YES | foundup_manifest_validator.py:313-501; WSP_109:318 | OBSERVED |
| registry seed entry | YES (specified, not written) | foundup_registry.json entities[]; WSP_109:374 | OBSERVED |

**Note (correction to directive Addendum D):** the directive checklist omitted `memory/`, which WSP 49
(section 3.2 rule 3, :100) makes MANDATORY for every module via WSP 60. It is added above as OBSERVED.
`ROADMAP.md` is required by Hermes `REQUIRED_CONTRACTS` (:110) even though WSP 49 does not list it -->
labeled OBSERVED from that source.

---

## 7. Required Manifest Fields (directive 5)

`foundup_manifest.json` MUST satisfy `foundup_manifest_validator.validate_manifest`
(`foundup_manifest_validator.py:313-501`). Concrete contract:

- top-level `foundup_id`.
- `build_contract`: `foundup_id` (== top), `module_path` (exact repo-relative == manifest parent dir
  :251-275), `status` in `{BASELINE_DECLARATIVE_ONLY, NEEDS_LABEL_RECONCILIATION}` (:86-88), `build` /
  `test` / `dry_run` each an object whose nested `command` is an argv-list-or-null, never a shell
  string (:99,146-152,278-306), `dry_run.default != false` AND
  `dry_run.required == true` (:375-383), `forbidden_paths` covering `.env` / `main.py` / `_dae.py` /
  `vendor` (:79-81), all 8 `required_gates` (:66-75), `readiness` with NO promoted flags (:412-430),
  `safe_mutation_surface`, `evidence_output` (:432-435).
- `execution_routing`: `orchestrator=openclaw`, `executor=hermes`, `auditor=ai_overseer` (:83-88),
  `external_agent_allowed != true` (:463), `declarative_only == true` (:469), `can_self_authorize !=
  true` (:475), plus `wre_coordinator`, `external_agent_contract_required`, `build_plan_source`,
  `job_contract_source` (:481-488).
- global: NO truthy `*bypass*` flag anywhere (:166-179).

The 8 required gates include `policy_required_sovereign_valve_for_non_dry_run` (:74) -- this is the
manifest-level hook to Section 10.

---

## 8. Registry Seed Shape (directive 6 -- specified, NOT written)

New FoundUp seed = one `entities[]` entry in `modules/foundups/foundup_registry.json`
(`foundup_registry_loader.py:74-89`). At genesis:

```json
{
  "foundup_id": "{foundup_id}",
  "display_name": "{display_name}",
  "entity_type": "foundup",
  "module_path": "modules/foundups/{foundup_id}",
  "stage": "incubating",
  "tier": "F0_DAE",
  "implementation_status": "SPECIFIED",
  "poc_status": "idea",
  "manifest_status": "exists",
  "manifest_path": "modules/foundups/{foundup_id}/foundup_manifest.json",
  "hermes_openclaw_build_status": "scaffold",
  "token_status": "TOKEN_DEFERRED",
  "next_slice": "{FOUNDUP_ID}_POC_PHASE1"
}
```

Anchored to WSP_109 draft fields (:323-336) + the live registry entry shape. The registry loader is
read-only (`NO_REGISTRY_MUTATION`, :8-11); this slice writes NOTHING to the registry. The write is a
FUTURE, valve-gated, 012/DAO-authorized step.

---

## 9. Ownership & Authority Boundaries (directive 7)

| Stage | Owner | Evidence |
|-------|-------|----------|
| Idea | 012 (source, not operator) | WSP_109:16-18 |
| Intake packet / envelope | 0102 / RedDog (dry-run) | P1 #920 |
| Genesis validation | OpenClaw gate -> ai_overseer validator | openclaw:404-513 |
| Orchestration | OpenClaw | manifest execution_routing :83 |
| Scaffold WRITE (execution) | **Hermes** (executor), NOT RedDog | manifest execution_routing :84; hermes_adapter |
| Audit | ai_overseer | manifest execution_routing :85 |
| Source authority | `monorepo_poc` only; cannot self-promote | source_authority (NEEDS_VERIFICATION) |
| Promotion to write | 012 / DAO sovereign token | reddog_wre_execution_valve.py:308-312 |

**RedDog does NOT directly write files** -- it hands off a governed work order; OpenClaw owns the
worker loop; Hermes executes under the valve.

---

## 10. Valve Requirements Before Any Write (Addendum E)

No scaffold write is valid unless ALL are true (fail-closed; any false => VALVE_CLOSED):

1. P0 Hermes dry-run-default present (#919, on main `1c373279e`).
2. P1 intake packet / envelope valid and `GATE_PASSED`.
3. OpenClaw genesis gate passed (openclaw:404-513).
4. RedDog work-order policy gate `WOULD_ACCEPT` (reddog_governed_work_order_dryrun.py).
5. Hermes/spine receipt chain present with digests cross-linked (reddog_wre_execution_valve.py:190-226).
6. WRE execution valve state == `VALVE_OPEN_WORKTREE_CREATE` (reddog_wre_execution_valve.py:51,310-312).
7. sovereign worktree token / 012 promotion present (reddog_wre_execution_valve.py:308-312).
8. protected branch (`main`/`master`) NOT targeted (reddog_governed_work_order_dryrun.py:86,384-389).
9. `allowed_paths` is non-empty for a write operation (reddog_governed_work_order_dryrun.py:401
   `empty_allowed_paths_for_write_operation`); scaffold-path (`module_path/**`) containment is the
   future executor's obligation on `FoundUpScaffoldContract.allowed_paths` (Section 4.1).
10. `denied_paths` do not overlap `allowed_paths`; forbidden paths excluded (reddog...:395-400).
11. intake_target in `{foundup_job, autonomous_task}` (reddog_wre_execution_valve.py:57); no secrets /
    forbidden operations / credential markers (reddog_governed_work_order_dryrun.py:63-84
    `FORBIDDEN_OPERATION_TOKENS` + `FORBIDDEN_PATH_GLOBS`); no registry-wide mutation.

The manifest gate `policy_required_sovereign_valve_for_non_dry_run` (foundup_manifest_validator.py:74)
is the declarative mirror of conditions 6-7.

---

## 11. Tests / Receipts Required Before Implementation (Addendum F)

### 11.1 Receipt chain a future executor MUST produce (dry-run first)

`work_order_receipt -> policy_gate_receipt -> invocation_receipt -> executor_plan_receipt ->
execution_valve_decision` -- each with a digest, `no_execution_performed=true` until the valve opens
(reddog_wre_execution_valve.py:173-232).

### 11.2 Static contract tests (this slice; docs-only, no runtime writer)

The static test `modules/foundups/tests/test_foundup_scaffold_contract_phase1.py` asserts THIS doc:

1. `create_foundup` is defined AND stated distinct from `extract_foundup` (alias prohibited).
2. WSP-49 scaffold artifacts enumerated (incl. `memory/`).
3. `foundup_manifest.json` fields enumerated (build_contract + execution_routing).
4. registry seed specified AND marked not-written.
5. valve requirements explicit (11 conditions).
6. Hermes real-write paths marked out of scope.
7. no runtime scaffold writer added by this slice.
8. no branch/worktree/file mutation appears in this slice (scope guards present).
9. HoloIndex INDEX_GAP recorded.

---

## 12. HoloIndex Preflight (Addendum G)

Pre-run (base `ca32bc082`). No re-index, no ranking-code change in this slice.

| Query | Top hits | INDEX_GAP |
|-------|----------|-----------|
| FoundUp scaffold contract | build_plan.py, envelope.py, WSP_58/104 | contract doc absent (new) |
| create_foundup action | foundups_actions.py (browser), WSP_55/26 | no `create_foundup` action exists (confirms audit) |
| FoundUpGenesisEnvelope | envelope.py, validator.py | none |
| WSP109 intake packet builder | test_openclaw_wsp109..., WSP_109 | **P1 module intake_packet_builder.py absent** |
| WSP49 module scaffold | WSP_49, WSP_55 | none |
| foundup_manifest registry seed | foundup_registry_loader.py, test_foundup_registry_schema.py | none |
| build_foundup extract_foundup | openclaw_foundup_orchestrator.py, test_build_plan_generator.py | none |

**Recorded gap:** `HOLOINDEX_FOUNDUP_SCAFFOLD_CONTRACT_DISCOVERABILITY_PHASE1` -- the landed P1 module
(`ca32bc082`) and this new contract doc do not surface (code/docs index predate them). Re-index is an
explicit operator/worker action, NEVER RedDog runtime. Subsumes the earlier
`HOLOINDEX_FOUNDUP_CREATION_AUDIT_DISCOVERABILITY_PHASE1`.

---

## 13. WSP_15 Priority

| C | I | D | Impact | MPS | P |
|---:|---:|---:|---:|---:|---|
| 2 | 5 | 4 | 4 | 15 | P1 |

Low complexity (contract/doc). Critical importance (sole unblocker of a safe scaffold writer).
Do-soon deferability. High impact. Decision-only -> safe.

---

## 14. Residual SPECIFIED_NOT_IMPLEMENTED (directive 10)

- `create_foundup` action + typed fields: SPECIFIED here, NOT added to `foundup_job_contract.py`.
- Scaffold-authoring executor: SPECIFIED, NOT implemented (future `FOUNDUP_SCAFFOLD_WRITER_PHASE1`,
  valve-gated, dry-run first).
- Registry seed write: SPECIFIED, NOT implemented (loader remains read-only).
- OpenClaw -> FAM/Hermes handoff: still a NOTE stub (openclaw:571-573), unchanged.
- `source_authority.py` behavior: NEEDS_VERIFICATION (not re-read this slice).
- Scaffold template location (Q2): INFERRED, not fixed by this contract.
- HoloIndex re-index: pending operator action.

---

## 15. WSP_97 Truth Labels

- `CREATE_FOUNDUP_DISTINCT_FROM_EXTRACT` -- OBSERVED gap (no create action); contract mandates non-alias.
- `SCAFFOLD_ARTIFACT_SET_WSP49_ANCHORED` -- OBSERVED (WSP_49 + Hermes REQUIRED_CONTRACTS).
- `MANIFEST_CONTRACT_VALIDATOR_ANCHORED` -- OBSERVED (foundup_manifest_validator.py).
- `REGISTRY_SEED_SPECIFIED_NOT_WRITTEN` -- OBSERVED (read-only loader).
- `WRITE_IS_VALVE_GATED_AND_012_AUTHORIZED` -- OBSERVED (valve + sovereign token).
- `REDDOG_DOES_NOT_WRITE_FILES` -- OBSERVED (execution_routing executor=hermes).
- `NO_EXECUTOR_ADDED_THIS_SLICE` -- OBSERVED (contract doc + static test only).

---

## 16. Related / Sequence

- Parent audit: `REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1.md`
- P0 (merged #919): `HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1.md`
- P1 (merged #920): `WSP109_INTAKE_PACKET_BUILDER_PHASE1.md`
- Manifest readiness: `FOUNDUP_MANIFEST_READINESS_AUDIT_PHASE1.md`
- **P2 (this):** `FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md`
- Next (future, NOT this slice): `FOUNDUP_SCAFFOLD_WRITER_PHASE1` (valve-gated, dry-run first),
  `HOLOINDEX_FOUNDUP_SCAFFOLD_CONTRACT_DISCOVERABILITY_PHASE1` (operator re-index).

---

## 17. Adversarial Verification (CoR sweep)

Before landing, this contract was checked by 6 independent adversarial lenses (ALIAS, SCHEMA, WSP49,
VALVE, MANIFEST, COMPLETENESS), each re-reading the actual cited source to refute the citations.

- Result: **6/6 APPROVE, 0 blocker, 0 major**; 71 independent source confirmations.
- Minor precision fixes applied from the sweep: `create_foundup` name-collision note (Section 3);
  valve conditions 9 and 11 re-cited to the exact enforcing symbols (Section 10); manifest command
  rule reworded to the nested `command`/argv object shape (Section 7).
