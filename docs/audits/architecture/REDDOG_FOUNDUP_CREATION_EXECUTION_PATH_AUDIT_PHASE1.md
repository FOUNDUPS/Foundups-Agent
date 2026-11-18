# REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1

**Slice:** `REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1`
**Author:** 0102 (WSP_00, WSP_97)
**Date:** 2026-07-04
**Type:** Audit / decision record — **no runtime mutation in this slice**
**Build under test:** Foundups®Agent extension **0.3.41**
**Predecessors:** #914–#918 RedDog senses/egress/packing stack; WSP 109 protocol (#718); OpenClaw genesis gate (#740)

---

## 1. Mission

Record the **WSP_97 verdict** from the FoundUp creation execution-path comparison:

- RedDog **0.3.41** (operational telemetry / senses spine)
- Claude direct-read audit (substance)
- External swarm adversarial read (coverage + self-correction)

This audit **updates slice ordering**: genesis envelope schema and validator already exist and are wired enough to test. The immediate gap is **not** “define the whole scaffold contract first.” It is **evidence selection, adversarial verification, intake packet population, and repair that preserves evidence**.

---

## 2. WSP_97 Verdict Table

| Claim | Label | Evidence |
|-------|-------|----------|
| RedDog 0.3.41 senses spine works: 6/6 recalled, 6/6 in model context, redaction passed, validation passed | **OBSERVED** | Golden 6-file Run Trace on installed 0.3.41 |
| RedDog missed deep evidence: `build_foundup == extract_foundup`, FAM handoff stub, stronger envelope/validator state | **OBSERVED** | Model output vs direct file reads; swarm correction |
| Claude direct-read beat RedDog on audit **substance** | **OBSERVED** | Same prompt family; Claude cited deeper line windows |
| Swarm beat Claude on **coverage** (read missing files, adversarial self-correction) | **OBSERVED** | Swarm session transcript |
| RedDog’s next gap is not retrieval — it is evidence selection + adversarial verification + repair preserving evidence | **INFERRED** | 0.3.41 recall/context telemetry green while Determine answers still thin |
| Next FoundUp path slice should be `WSP109_INTAKE_PACKET_BUILDER_PHASE1`, not scaffold contract first | **UPDATED DECISION** | Envelope + validator + gate exist (`openclaw_foundup_orchestrator.py`, `foundup_genesis/`) |

---

## 3. Why the Verdict Flips

The swarm established:

1. **`FoundUpGenesisEnvelope`** schema exists (`modules/ai_intelligence/ai_overseer/src/foundup_genesis/envelope.py`).
2. **`validate_genesis_envelope`** is wired in OpenClaw dispatch (`modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:404+`).
3. Empty/missing envelope → **`NO_ENVELOPE` → NOT_READY** W10 handoff (same file, `dispatch_foundup` path).
4. Valid envelope path → **`GATE_PASSED`** before FAM/Hermes handoff surfaces.

Therefore the **immediate missing piece** is not a greenfield scaffold contract. It is:

> Can 0102 build/populate a valid WSP_109 intake packet / genesis envelope from chat/idea (dry-run only), prove OpenClaw’s gate accepts it, and prove empty/missing envelope still returns NOT_READY — **without calling FAM or Hermes**?

Scaffold contract (`create_foundup` action, WSP-49 artifact set, packet → scaffold → registry seed) remains required but **sequenced after** intake builder proof.

---

## 4. Correct Execution Sequence (Updated)

```text
1. HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1     ← SHARPEST SAFETY FINDING
   - Flip HermesFoundUpBuilder dry-run default ON
   - Require explicit opt-in for real writes/delegation
   - See: hermes_adapter.py HERMES_BUILDER_DRY_RUN default "0"

2. WSP109_INTAKE_PACKET_BUILDER_PHASE1
   - Dry-run only
   - chat/idea → populated FoundUpGenesisEnvelope
   - Valid envelope → GATE_PASSED (validator + orchestrator)
   - Empty/missing → NOT_READY / NO_ENVELOPE
   - FAM/Hermes NOT called

3. FOUNDUP_SCAFFOLD_CONTRACT_PHASE1
   - Define create_foundup action artifact set (WSP-49 monorepo scaffold)
   - Map packet → scaffold → registry seed
   - Wire build_foundup vs extract_foundup semantics with tests
```

**Safety rationale:** `HermesFoundUpBuilder` currently defaults `dry_run=False` when `HERMES_BUILDER_DRY_RUN` is unset (`hermes_adapter.py:134`). Any path reaching the builder without explicit dry-run env is a **write-capable default**. Intake builder work must not run atop that default.

---

## 5. RedDog 0.3.41 — Where It Excels

RedDog is now **better than Claude** at **operational audit proof** (repeatable Run Trace):

| Telemetry field | Proves |
|-----------------|--------|
| `extension_version` | Installed build identity (not model parroting) |
| `required_targets_recalled` / `direct_read_*` | Senses spine: path-aware recall + governed fetch |
| `required_targets_in_model_context` / `_missing` | Post-cut packing proof (0.3.35+ authoritative 0.3.39+) |
| `audit_context_requested` / `_applied` | Audit-mode redaction bridge |
| `required_targets_redaction_*` | Per-target isolation (0.3.38+) |
| `continuation_enabled` / `continuation_appended` | Continuation honesty (0.3.36 default off) |
| `redaction_status` / validation fields | Egress gate before OpenRouter |

**Label:** **OBSERVED** on golden 6-file prompt (no WSP_95 — `private_reasoning` false positive).

---

## 6. RedDog — Where It Still Loses

| Gap | Label | Symptom in FoundUp creation audit |
|-----|-------|-----------------------------------|
| Symbol-aware excerpt depth | **SPECIFIED_NOT_IMPLEMENTED** | Misses `build_foundup` / `extract_foundup` line windows |
| Repair preserves evidence | **SPECIFIED_NOT_IMPLEMENTED** | Repair pass drops bounded context that scorecard says was packed |
| Determine Q/A contract | **SPECIFIED_NOT_IMPLEMENTED** | Does not force numbered answers with file:line for every Determine question |
| Adversarial verifier panel | **SPECIFIED_NOT_IMPLEMENTED** | No second pass that challenges first-pass claims against authoritative telemetry |

**Label:** Claude/swarm **OBSERVED** advantage on audit substance and adversarial correction despite RedDog **OBSERVED** advantage on telemetry.

---

## 7. RedDog Follow-Up Slices (Post-Intake)

These close the substance gap **after** WSP_109 intake builder lands:

```text
REDDOG_SYMBOL_AWARE_EXCERPT_DEPTH_PHASE1
  - When prompt names symbols (build_foundup, extract_foundup, validate_genesis_envelope),
    fetch bounded line windows around definitions/call sites, not just file headers.

REDDOG_REPAIR_PRESERVES_EVIDENCE_PHASE1
  - Repair pass may rewrite prose; must NOT drop required-target sections that passed
    authoritative packing proof. Telemetry: repair_evidence_preserved_count.

REDDOG_DETERMINE_QUESTION_ANSWER_CONTRACT_PHASE1
  - Output schema: numbered Determine answers; each cites path:line or Run Trace field;
    missing evidence → explicit HOLD with reason (WSP_97), not silent omission.

REDDOG_ADVERSARIAL_VERIFIER_PANEL_PHASE1
  - Lightweight second model/panel pass: challenge claims vs scorecard + cited lines;
    fail validation if claim contradicts authoritative telemetry.
```

---

## 8. Code Anchors (Existing — Not Greenfield)

| Surface | Path | Role |
|---------|------|------|
| Genesis envelope schema | `modules/ai_intelligence/ai_overseer/src/foundup_genesis/envelope.py` | `FoundUpGenesisEnvelope` dataclass |
| Genesis validator | `modules/ai_intelligence/ai_overseer/src/foundup_genesis/validator.py` | Pre-build validation |
| OpenClaw genesis gate | `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py` | `validate_genesis_envelope`, `GATE_PASSED`, NOT_READY handoff |
| FoundUpJob actions | `modules/communication/moltbot_bridge/src/foundup_job_contract.py` | `build_foundup`, `extract_foundup`, … |
| Hermes job executor | `modules/foundups/agent/src/hermes_foundup_job_executor.py` | Consumes jobs; respects `force_dry_run` |
| Hermes builder (risk) | `modules/foundups/agent/src/hermes_adapter.py:134` | **`HERMES_BUILDER_DRY_RUN` default off** |
| WSP 109 protocol | `WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md` | Intake-only boundary |
| Prior genesis gate audit | `docs/audits/architecture/OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1.md` | #740 behaviour matrix |

---

## 9. Golden Prompt Reference (FoundUp Creation Audit)

Use **path-only** required targets (no `symbol:create_foundup` — breaks recall):

```text
Audit the FoundUp creation monorepo WSP_109 execution path.

Required direct-read targets:
- WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md
- modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py
- modules/foundups/agent/src/hermes_foundup_job_executor.py
- modules/communication/moltbot_bridge/src/foundup_job_contract.py
- modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py
- modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py

Determine: (8 questions — numbered, file:line evidence, WSP_97 labels)
End with WSP_15 priority and next safest slice.
```

Exclude `WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md` until doc false-positive slice lands (`REDDOG_WSP_DOC_PRIVATE_REASONING_FALSE_POSITIVE_PHASE1`).

---

## 10. WSP_97 Checklist (This Audit Slice)

| Item | Status |
|------|--------|
| AUDIT_ONLY_NO_RUNTIME_MUTATION | YES |
| CITES_0.3.41_GOLDEN_EVIDENCE | YES |
| UPDATED_SLICE_ORDER_RECORDED | YES |
| HERMES_DRYRUN_SAFETY_PRIORITY_DOCUMENTED | YES |
| INTAKE_BUILDER_BEFORE_SCAFFOLD_CONTRACT | YES |
| REDDOG_SUBSTANCE_GAPS_NAMED_WITH_FOLLOWUPS | YES |
| CODE_ANCHORS_FILE_LINE | YES |
| 0102_ARCHITECT_APPROVAL_VIA_WSP_97 | YES |
| NO_FAM_HERMES_INVOCATION_IN_THIS_SLICE | YES |

---

## 11. Related Slice Specs (Authored Same Session)

| Slice | Doc |
|-------|-----|
| `HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1` | `docs/audits/architecture/HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1.md` |
| `WSP109_INTAKE_PACKET_BUILDER_PHASE1` | `docs/audits/architecture/WSP109_INTAKE_PACKET_BUILDER_PHASE1.md` |
| `FOUNDUP_SCAFFOLD_CONTRACT_PHASE1` (queued) | `docs/audits/architecture/FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md` |

---

*0102 architect decision: approval flows through WSP_97 applied evidence, not discretionary operator gate. Promotion of slices 1→3 requires OBSERVED test bars in each spec.*
