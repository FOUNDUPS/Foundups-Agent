# WAE Layer Specs L0-L4 (WAE-AR1)

**Companion to**: `WRE_ARCHITECT_EVOLUTION_DECISION.md`
**Status**: DECISION-ONLY (specification, no runtime implementation)
**Base SHA**: `1a672a5dafbb4e704d67b33b98329f8766a94de3`
**Protocol**: WSP_97 (each layer carries an explicit truth boundary + stop condition)

These five layers are NOT new DAEs and NOT a new orchestrator. They are invariants that fold into existing owners. Each layer is a LEGO block per the Occam layer discipline: build one, prove the invariant, then the next. L1+ autonomy is gated on L0 closure.

---

## L0  -  Close #737 FOUNDUP Permission Bypass

**Objective**: Guarantee that no FoundUp launch/onboard intent reaches `fam_adapter.launch_foundup` without passing the WSP 109 genesis gate (and, where applicable, OpenClaw's permission tier). This is the precondition for ALL downstream autonomy.

**Existing owner**: OpenClaw (intent + policy gate).

**Exact candidate files**:
- `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py`  -  genesis gate lives here: `dispatch_foundup` (line 840), `_is_foundup_launch_or_onboard_intent` (line 155), `validate_genesis_envelope` handoff (lines 873-881), `_genesis_gate_handoff` (line 802).
- `modules/communication/moltbot_bridge/src/openclaw_execution_routes.py`  -  `execute_foundup` (line 672) and the residual `ImportError` fallback (lines 682-690).
- `modules/communication/moltbot_bridge/src/fam_adapter.py`  -  `handle_fam_intent` (line 446), `parse_launch_intent` (line 373; matches both "launch foundup" and "create foundup"), `launch_foundup` (line 251).
- `modules/communication/moltbot_bridge/src/openclaw_permission_policy.py`  -  `check_permission_gate` (line 227), `check_source_permission` (line 114).

**Current state (verified, direct read)**:
- The PRIMARY path is gated: `dispatch_foundup` intercepts build intents (`_FOUNDUP_BUILD_WORDS` incl. "create foundup", line 47) -> safe dry-run queue; and launch/onboard intents (`_FOUNDUP_LAUNCH_ONBOARD_PHRASES` incl. "launch foundup", line 142) -> genesis gate -> NOT_READY W10 handoff when no envelope present. Neither reaches a real launch from a chat prompt.
- **RESIDUAL BYPASS**: `execute_foundup` (lines 682-690)  -  if `from .openclaw_foundup_orchestrator import dispatch_foundup` raises `ImportError`, it falls back to calling `handle_fam_intent(intent.raw_message, intent.sender)` DIRECTLY. A "launch foundup X with token Y" message in that fallback path would reach `fam_adapter.launch_foundup` ungated by the genesis gate.

**Invariant to prove**: For every FOUNDUP-category intent, there exists NO code path from `route_execution` to `fam_adapter.launch_foundup` that does not first return `gate_result.allowed == True` from `validate_genesis_envelope` (or its successor). The `ImportError` fallback must either (a) re-raise / return NOT_READY, or (b) route through the same gate  -  it must NOT call `handle_fam_intent` for launch/onboard intents.

**One pass/fail test**:
- PASS: With the orchestrator import forced to raise `ImportError`, send "launch foundup Shield with token SHLD" through `execute_foundup`; assert the response is a NOT_READY / blocked packet and that `fam_adapter.launch_foundup` was NOT invoked (mock + assert-not-called).
- FAIL: launch executes (a Foundup is created) or `launch_foundup` is called.

**WSP_97 truth boundary**: `L0_REQUIRED_BEFORE_AUTONOMY`  -  do not claim #737 closed; the decision doc records it as NOT FULLY CLOSED with the residual fallback. No autonomy layer (L1+) may ship while this remains open.

**Implementation stop condition**: Stop once the single ungated path (lines 682-690) is closed and the pass/fail test is green. Do NOT refactor the genesis gate, do NOT widen the permission model, do NOT add new intent categories.

---

## L1  -  Observe-and-Propose Loop (No Execution)

**Objective**: The recursive improvement loop OBSERVES (logs/FMAS/violations) and PROPOSES by emitting `ImprovementJob(status=PENDING, dry_run=True)`. It executes nothing. Execution remains a separate, gated step owned by WRE workers under L0/L4.

**Existing owner**: WRE recursive_improvement module + `improvement_job_contract.py` (Architect hat folds here).

**Exact candidate files**:
- `modules/infrastructure/wre_core/src/improvement_job_contract.py`  -  `ImprovementStatus.PENDING` (line 115), `dry_run=True` default documented in module truth boundaries (lines 24-30), risk -> architect-review mapping (`ImprovementRiskLevel`, lines 184-201; `WSP15Priority.requires_architect_review` default True, line 274).
- `modules/infrastructure/wre_core/src/daemon_self_audit_loop.py`  -  currently EXECUTES allowlisted auto-fixes (`_apply_policy_fix`, ~line 396; `_open_fix_task` auto-fix branch, ~lines 262-268). Escalation writer `_persist_escalation` (~lines 605-618) to `reports/daemon_self_audit_escalations.jsonl`.
- `modules/communication/moltbot_bridge/src/openclaw_execution_routes.py`  -  `execute_improvement` (line 865): classify + advise only; does NOT emit `ImprovementJob`.
- `modules/infrastructure/wre_core/recursive_improvement/`  -  existing module (INTERFACE.md, ROADMAP.md present).

**Current state (verified, direct read)**:
- The `ImprovementJob` contract EXISTS with the correct shape (PENDING, dry_run default, architect-review gating). GOOD.
- **GAP A**: `execute_improvement` only classifies + returns an advisory string ("Classified but not executed"); it does not construct an `ImprovementJob`.
- **GAP B**: `daemon_self_audit_loop.py` is an active execution loop (auto-fix under allowlist + cooldown), NOT observe-propose-only, and it emits its own `SelfAuditEscalation`/`SelfAuditEvent` dataclasses, NOT `ImprovementJob`.

**Invariant to prove**: Every proposal produced by the observe path is an `ImprovementJob` with `status == PENDING` and `dry_run == True`, and no proposal causes a source/repo/process mutation. The observe path has zero calls into execution primitives (no subprocess that mutates, no git write, no file write outside the proposal/escalation ledger).

**One pass/fail test**:
- PASS: Feed a synthetic FMAS/violation finding into the observe path; assert it yields exactly one `ImprovementJob` with `status==PENDING and dry_run==True`, and assert no mutation primitive was called.
- FAIL: status != PENDING, dry_run != True, or any mutation/auto-fix is invoked from the observe path.

**WSP_97 truth boundary**: `L1_OBSERVE_PROPOSE_ONLY`  -  observation surfaces needs; humans/012 (or a downstream gated worker) decide execution. The daemon self-audit auto-fix behaviour must be reconciled: either move auto-fix behind the same PENDING/dry_run + approval contract, or explicitly scope it out and document it.

**Implementation stop condition**: Stop once the observe path emits PENDING/dry_run `ImprovementJob`s and the no-mutation assertion holds. Do NOT implement the executor for those jobs in this layer.

---

## L2  -  Hard Verifier + Diversity Retention + Goodhart Stop

**Objective**: Before any stored pattern is allowed to influence a decision/action, it must pass a HARD VERIFIER (independent re-check, not the same signal that produced it). Retain diversity (do not collapse to a single "best" pattern). Add a Goodhart stop (halt when a metric saturates / looks gamed).

**Existing owner**: `pattern_memory.py` (no new component).

**Exact candidate files**:
- `modules/infrastructure/wre_core/src/pattern_memory.py`  -  `store_outcome` (line 331; currently stores WITHOUT verification), `recall_successful_patterns(min_fidelity=0.90)` (line 485), A/B framework `store_variation` (623), `schedule_ab_test` (809), `check_ab_promotion(min_margin=0.10)` (888), `promote_variation` (922), `archive_variation` (933). Tables: `skill_outcomes` (lines 123-139), `skill_variations` (154-166).

**Current state (verified, direct read)**:
- **Hard verifier: ABSENT.** `store_outcome` accepts any `pattern_fidelity` float and commits unconditionally (line ~365). No independent re-check before storage.
- **Diversity retention: PARTIAL/PRESENT.** A/B variation framework keeps multiple variations per skill with promote/archive; recall is ranked by fidelity DESC. No explicit anti-collapse guarantee beyond the A/B mechanism.
- **Goodhart stop: ABSENT.** No saturation threshold, no "too good to be true" alert/halt, no upper bound on continued A/B testing, no decay of stale high-fidelity patterns.

**Invariant to prove**: (a) No outcome influences a downstream decision unless `verified == True` from an independent verifier distinct from the producing signal. (b) Recall returns at least K distinct pattern lineages when available (diversity floor). (c) When a metric crosses a saturation/anomaly threshold, the loop emits a Goodhart-stop signal and refuses to auto-act on that metric.

**One pass/fail test**:
- PASS: Store an unverified outcome with `pattern_fidelity=0.99`; assert it cannot be recalled as "actionable" until the verifier marks it verified; and assert that injecting a sudden fidelity jump (e.g. 0.70 -> 0.99 in one step) raises the Goodhart-stop and blocks auto-promotion.
- FAIL: an unverified or anomalously-jumped pattern is recalled/promoted as actionable.

**WSP_97 truth boundary**: `HARD_VERIFIER_REQUIRED`  -  stored fidelity is a CLAIM, not proof, until an independent verifier confirms it. Pattern memory must not present unverified outcomes as actionable truth.

**Implementation stop condition**: Stop once the verifier gate, diversity floor, and Goodhart-stop are present and the pass/fail test is green. Do NOT redesign the SQLite schema beyond adding the verification/anomaly fields; do NOT couple pattern_memory to any LLM judge directly (verification is deterministic where possible).

---

## L3  -  Heterogeneous Judge Panel -> Escalations (NOT Fusion)

**Objective**: Adversarial / governance review uses a HETEROGENEOUS judge panel whose verdicts flow to the escalations path (Sentinels / W10 handoff / 012). It MUST NOT be routed through OpenRouter Fusion.

**Existing owner**: Sentinels + escalations ledger (the heterogeneous-judge concept; Fusion is advisory worker-panel only, never governance authority).

**Exact candidate files**:
- `modules/communication/moltbot_bridge/src/fusion_redaction_gate.py`  -  `ACTION_BLOCK` categories: `private_reasoning` (line 128), `source_authority` (line 140), `governance_instruction` (line 147); `BLOCK_CATEGORIES` (line 154); fail-closed `REDACTION_BLOCKED` (from `fusion_adapter.py`).
- `modules/communication/moltbot_bridge/src/fusion_adapter.py`  -  `REDACTION_BLOCKED = "BLOCKED_PENDING_REDACTION_GATE"` (line 47), `advisory_not_canonical` posture, `FusionLiveModeNotAvailable` raise (live modes blocked).
- `modules/infrastructure/wre_core/src/daemon_self_audit_loop.py`  -  escalation ledger `reports/daemon_self_audit_escalations.jsonl` (escalation sink precedent).

**Current state (verified, direct read)**:
- Fusion's redaction gate is fail-closed and BLOCKs exactly the content a governance judge would emit: `private_reasoning`, `source_authority`, `governance_instruction`. Therefore routing a governance judge panel through Fusion would either leak governance content (if the gate were bypassed) or be permanently `BLOCKED_PENDING_REDACTION_GATE`. Both outcomes are unacceptable -> Fusion is structurally disqualified as governance judge.

**Invariant to prove**: No governance/judge verdict carrying `private_reasoning` / `source_authority` / `governance_instruction` content is ever submitted to a Fusion code path. The judge panel emits verdicts only to the escalations sink (Sentinels / W10 / 012). The panel is heterogeneous (>=2 distinct model families / lenses), not a single model.

**One pass/fail test**:
- PASS: Attempt to submit a governance verdict payload to the Fusion adapter; assert the call is refused at the boundary (no Fusion submission occurs), and assert the same payload is accepted by the escalations sink. Assert the panel config lists >=2 distinct judge families.
- FAIL: a governance verdict reaches any Fusion code path, or the panel is homogeneous.

**WSP_97 truth boundary**: `FUSION_NOT_GOVERNANCE_JUDGE`  -  Fusion is an advisory worker panel, never governance authority. The redaction gate that BLOCKs governance content is the proof.

**Implementation stop condition**: Stop once the judge-panel verdicts route to escalations and the Fusion-refusal test is green. Do NOT build a new judge daemon; do NOT add governance categories to the Fusion REDACT allowlist.

---

## L4  -  Deterministic Gate-Ordering Coordinator (No Authority)

**Objective**: A thin, deterministic coordinator that ENFORCES the order in which existing gates run for a given action  -  it owns ORDERING ONLY and holds no approval/merge authority of its own.

**Existing owner**: a thin coordinator over existing gates (NOT a new orchestrator, NOT a DAE). Composes existing primitives; this is the RedDog "Dispatcher" coordination surface.

**Exact candidate files** (composed, not modified by L4 itself):
- `modules/communication/moltbot_bridge/src/openclaw_permission_policy.py`  -  `check_permission_gate` (line 227) [L0 policy].
- `modules/infrastructure/wre_core/src/capability_token_validator.py`  -  `validate_token` / `get_default_validator` (fail-closed; reason codes lines 50-70).
- `modules/infrastructure/wre_core/src/destructive_action_guard.py`  -  `evaluate_destructive_action` (D0-D6; D4+ approval; D4/D5/D6 BLOCKED Phase 1; lines 63-90+).
- `modules/infrastructure/wre_core/src/hermes_job_executor.py`  -  `execute` (line 1536) already chains: validate -> token validation -> destructive-action guard -> simulate/BLOCK. This is the de-facto ordering precedent to formalize.

**Current state (verified, direct read)**:
- `hermes_job_executor.execute` already runs the gates in a defensible order (token validation -> destructive guard -> real-delegation BLOCKED). L4 formalizes a single deterministic ordering contract so every action surface (not just Hermes) applies the same sequence.

**Invariant to prove**: For any action, gates always run in the fixed order [policy (L0) -> capability token -> destructive-action guard -> hard verifier (L2)], the coordinator short-circuits on the FIRST deny (fail-closed), and the coordinator NEVER returns "approved" on its own  -  approval/merge is only ever the result of the underlying gates + 012/DAO.

**One pass/fail test**:
- PASS: Drive the coordinator with an action that fails at the token stage; assert the destructive-guard and verifier stages are NOT reached (short-circuit) and the verdict is DENY; assert the coordinator exposes no method that grants merge/approval independent of the underlying gates.
- FAIL: gates run out of order, a later gate runs after an earlier deny, or the coordinator emits an approval not derived from a gate.

**WSP_97 truth boundary**: `NO_NEW_ORCHESTRATOR` + `NO_MERGE_AUTHORITY_CODE`  -  L4 sequences existing gates; it is not an orchestrator and holds no authority. Merge/promotion remains with 012/DAO.

**Implementation stop condition**: Stop once the ordering contract + short-circuit + no-authority assertions are green. Do NOT let L4 cache approvals, mutate state, or call workers directly  -  it returns an ordered verdict only.

---

## Layer Dependency / Build Order

```
L0 (close #737)  ->  MUST be green before any of L1-L4 ships autonomy.
   |
   v
L1 (observe-propose, PENDING/dry_run)  ->  produces proposals, executes nothing.
   |
   v
L2 (hard verifier + diversity + Goodhart)  ->  gates which patterns may inform action.
   |
   v
L3 (heterogeneous judge -> escalations, not Fusion)  ->  governance review path.
   |
   v
L4 (deterministic gate-ordering, no authority)  ->  sequences L0/token/guard/L2 per action.
```

Each layer is independently testable. No layer grants merge authority. 012/DAO remains the sole sovereign-merge boundary.
