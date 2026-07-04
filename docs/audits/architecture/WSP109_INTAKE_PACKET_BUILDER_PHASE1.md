# WSP109_INTAKE_PACKET_BUILDER_PHASE1

**Slice:** `WSP109_INTAKE_PACKET_BUILDER_PHASE1`
**Author:** 0102 (WSP_97)
**Date:** 2026-07-04
**Type:** Dry-run implementation slice
**Depends on:** `HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1` (merged first)
**WSP lock:** WSP_00, WSP_15, WSP_22, WSP_50, WSP_97, WSP_109

---

## 1. Mission

Build a **dry-run-only** intake path that converts unstructured chat/idea input into a populated **`FoundUpGenesisEnvelope`**, validates it through the **existing** OpenClaw genesis gate, and proves:

1. Valid envelope → **`GATE_PASSED`**
2. Empty/missing envelope → **`NOT_READY` / `NO_ENVELOPE`**
3. **FAM and Hermes are NOT called**

This slice does **not** scaffold a monorepo module tree. It does **not** enqueue build jobs. It proves the WSP_109 handoff artifact reaches the gate.

---

## 2. Predecessor Proof (Already Landed)

| Artifact | Location | Status |
|----------|----------|--------|
| WSP 109 protocol | `WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md` | **OBSERVED** |
| Envelope schema | `modules/ai_intelligence/ai_overseer/src/foundup_genesis/envelope.py` | **OBSERVED** |
| Validator | `modules/ai_intelligence/ai_overseer/src/foundup_genesis/validator.py` | **OBSERVED** |
| OpenClaw gate | `openclaw_foundup_orchestrator.validate_genesis_envelope` | **OBSERVED** (#740) |
| NOT_READY handoff | `_genesis_gate_handoff`, `build_w10_handoff` | **OBSERVED** |

Swarm finding: schema + validator + gate are **wired enough to test** — this slice fills the **builder/populator** gap.

---

## 3. Proposed Module Placement

**Domain:** `modules/ai_intelligence/ai_overseer/` (intake validation authority) **or** `modules/communication/moltbot_bridge/` (OpenClaw adjacency).

**Preferred:** `modules/ai_intelligence/ai_overseer/src/foundup_genesis/intake_packet_builder.py`

Rationale: envelope + validator already live under `foundup_genesis/`; builder stays co-located (WSP 3 functional distribution — intake validation, not platform consolidation).

Public API (draft):

```python
def build_intake_packet_dry_run(
    idea_text: str,
    *,
    actor_id: str = "0102",
    source_channel: str = "reddog",
) -> IntakePacketBuilderResult:
    """
    Parse idea_text → FoundUpGenesisEnvelope dict.
    Run validate_genesis_envelope (or validator directly).
    NEVER call FAM, Hermes, or registry writers.
    """
```

Return type includes:

- `envelope: dict | None`
- `gate_result: GenesisGateResult` (or equivalent serializable)
- `gate_reason: GATE_PASSED | NO_ENVELOPE | VALIDATION_FAILED | ...`
- `dry_run: True`
- `fam_called: False`
- `hermes_called: False`
- `evidence_refs: list` (paths + digests only, no secrets)

---

## 4. Intake → Envelope Mapping (Minimum Viable)

From WSP 109 protocol required fields (see protocol § packet output order):

| Intake source | Envelope field | Rule |
|---------------|----------------|------|
| Idea title / name | `foundup_id`, `display_name` | Namespace per WSP 104; reject invalid |
| Problem statement | `pain_statement` | Required string |
| Proposed solution | `solution_summary` | Required string |
| Success criteria | `acceptance_criteria[]` | At least one `AcceptanceCriterion` |
| Entity classification | `entity_type` | Enum from protocol |
| Truth map | `truth_state_map` | WSP_97 markers — default IDEA_ONLY / SPECIFIED |
| Lifecycle | `lifecycle_stage` | IDEA or INCUBATING only at genesis |
| Binding | `binding_state` | UNBOUND or DISCOVERABLE_ONLY |

**Parser strategy (Phase 1):** structured section headers in idea text + conservative defaults + validator rejection on incomplete — **not** full LLM free-form unless redaction-gated and dry-run labelled.

Optional Phase 1b: RedDog extension emits structured markdown sections → builder consumes without new LLM.

---

## 5. Gate Integration

```text
idea_text
    → build_intake_packet_dry_run()
    → envelope dict
    → OpenClawFoundUpOrchestrator.validate_genesis_envelope(envelope, actor_id)
    → GenesisGateResult
```

**Empty input path:**

```python
validate_genesis_envelope({})  # → NO_ENVELOPE, allowed=False
```

Must match existing #740 matrix (`OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1.md` §6).

**Valid fixture path:** use Shield-style or minimal compliant envelope from `foundup_genesis` tests → `GATE_PASSED`.

---

## 6. Hard Prohibitions (Fail Closed)

| Prohibited call | Guard |
|-----------------|-------|
| `fam_adapter.launch_foundup` | No import in builder module |
| `HermesFoundUpBuilder.extract_foundup` / `build_foundup` | No import; AST test |
| Registry / catalog writers | No file write; dry-run result only |
| `FoundUpJobConsumer.consume_one` | No enqueue |

Telemetry fields on result: `fam_called=False`, `hermes_called=False`, `registry_mutated=False`.

---

## 7. Tests

| Test | Assert |
|------|--------|
| `test_empty_idea_returns_no_envelope_not_ready` | Gate blocked; reason NO_ENVELOPE |
| `test_minimal_valid_fixture_gate_passed` | allowed=True; GATE_PASSED |
| `test_invalid_foundup_id_rejected` | Validator errors; not GATE_PASSED |
| `test_no_fam_hermes_imports` | AST / import guard |
| `test_result_is_dry_run_only` | No filesystem side effects (sentinel file) |
| `test_openclaw_dispatch_simulation` | envelope in `intent.payload['genesis_envelope']` → gate passes; without → NOT_READY |

Target: new module tests + extend `test_openclaw_wsp109_onboarding_dryrun.py` if needed.

---

## 8. RedDog Integration (Phase 1 — Optional Hook)

Document-only in Phase 1 unless trivial:

- RedDog Copy MD may include `## Genesis Intake Packet (dry-run)` section when audit prompt mentions WSP_109.
- Extension calls builder via Python bridge **read-only** subprocess (pattern: `advisory_model_once.py`).
- Run Trace fields: `intake_packet_built`, `genesis_gate_reason`, `genesis_gate_passed`.

Full RedDog UI wiring → follow-up `REDDOG_WSP109_INTAKE_UI_PHASE1`.

---

## 9. Acceptance Bar (WSP_97)

| Item | Status when done |
|------|------------------|
| Valid chat fixture → populated envelope dict | OBSERVED (test) |
| Valid envelope → GATE_PASSED | OBSERVED (test) |
| Empty/missing → NOT_READY / NO_ENVELOPE | OBSERVED (test) |
| FAM/Hermes not invoked | OBSERVED (test + AST) |
| Hermes builder default dry-run | OBSERVED (dependency slice) |
| Docs: ModLog, INTERFACE, ROADMAP | YES |

---

## 10. WSP_15 Priority

| Priority | Slice |
|----------|-------|
| P0 | HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1 |
| **P1** | **This slice** |
| P2 | FOUNDUP_SCAFFOLD_CONTRACT_PHASE1 |
| P3 | RedDog substance slices (symbol depth, repair evidence, determine contract, adversarial panel) |

---

## 11. Related

- Audit: `REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1.md`
- Prior gate audit: `OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1.md`
- FAM flow spec: `docs/0102_session_briefings/REDDOG_FAM_GENESIS_FLOW_SPEC_PHASE1.md`
