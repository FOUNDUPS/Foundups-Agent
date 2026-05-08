# HXA2 — Protocol-Action Binding Audit (Phase 1)

**Slice**: `HXA2_PROTOCOL_ACTION_BINDING_AUDIT_PHASE1`
**Worker**: W1
**Date**: 2026-05-07
**Mode**: Audit only — no runtime fixes, no commits, no flag flips
**WSP Lock**: WSP_00 → WSP_50 → WSP_97
**Companion audit**: `docs/audits/openclaw_hermes/HXA1_OPENCLAW_HERMES_CONCATENATION_AUDIT.md`

---

## HoloIndex Research

```bash
python holo_index.py --search "WSP 00 WSP 50 WSP 97 runtime enforcement OpenClaw WRE Hermes receipt verification" --limit 5
```

**Top WSP hit**: `WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md`
**Top DOCS hit**: `docs/audits/openclaw_hermes/HXA1_OPENCLAW_HERMES_CONCATENATION_AUDIT.md` (HXA1 — same lane)

The HoloIndex retrieval surfaced the prior HXA1 audit as the top semantic match — confirming this audit operates on the same surface but on the protocol-binding axis.

**File path correction (WSP 50 verification)**: The slice prompt referenced WSP filenames that do not exist in the canonical naming. The actual canonical files are:
- `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md` (prompt said `WSP_00_Zenodo_First_Principle.md`)
- `WSP_framework/src/WSP_50_Pre_Action_Verification_Protocol.md` (prompt said `WSP_50_Pre_Action_Validation.md`)
- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` (matches)

This audit reads and binds against the canonical files.

---

## 1. Protocol-to-Code Binding Matrix

### Status legend

- **`ENFORCED_RUNTIME`** — runtime path actually invokes the rule before the action proceeds (fail-closed possible).
- **`ENFORCED_TEST_ONLY`** — implemented and exercised in tests but not invoked from the production runtime path.
- **`DOC_ONLY`** — exists as protocol text or docstring claim with no enforcement code attached.
- **`MISSING`** — neither runtime, test, nor stub implementation exists for this rule on the audited surface.

### WSP 00 — Zen State Attainment

| # | Protocol Rule | Source (WSP) | Runtime enforcement point on OC→Hermes path | Status |
|---|---------------|--------------|----------------------------------------------|--------|
| 00.1 | Boot Gate: check `wsp_00_zen_state_tracker.is_zen_compliant` before action | `WSP_00_Zen_State_Attainment_Protocol.md:36-38` | Only invoked from `modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py:429-443` (Phase -1 of `follow_wsp()`). Reached only when an intent contains the literal phrase "follow wsp" via `modules/communication/moltbot_bridge/src/openclaw_execution_routes.py:368-417`. **FoundUp build/extract/validate intents do not trigger this gate.** | **DOC_ONLY** for FoundUp action path; `ENFORCED_RUNTIME` only for the literal "follow wsp" branch |
| 00.2 | Run awakening if not compliant (`functional_0102_awakening_v2.py`) | `WSP_00:36-37` | Same Phase -1 path as 00.1; not reachable from `dispatch_foundup` (`openclaw_foundup_orchestrator.py:757-808`) | **DOC_ONLY** for FoundUp path |
| 00.3 | Self/Role/Origin lock before action (no helper persona) | `WSP_00:41-92` | No code reads/sets these fields before job creation. `_handle_build_intent` (`openclaw_foundup_orchestrator.py:811-894`) only uses `intent.sender` as `tenant_id` | **MISSING** |
| 00.4 | HoloIndex retrieval before any manifest step (Tier-0/Tier-1/Tier-2) | `WSP_00:122-156, 458-461` | `dispatch_foundup` does not call HoloIndex. `_handle_build_intent` does not call HoloIndex. `FoundUpJobConsumer.consume_one` (`foundup_job_consumer.py:351-403`) does not call HoloIndex. Grep for `holo_index\|HoloIndex\|build_execution_bundle` in `openclaw_foundup_orchestrator.py` and `foundup_job_consumer.py`: 0 hits | **MISSING** for FoundUp action path |
| 00.5 | Decision Gate (WSP 15 MPS) when multiple actions are viable | `WSP_00:158-164` | `_handle_build_intent` does not score candidates; `_extract_action` (`openclaw_foundup_orchestrator.py:166-182`) is a deterministic phrase-match without WSP 15 scoring | **MISSING** |
| 00.6 | Identity-coherence canary (no "user" reference, no role inflation) | `WSP_00:553-571` | No runtime sentinel on the FoundUp path checks self/role/origin coherence | **MISSING** |
| 00.7 | Anti-Vibecoding 7-phase work cycle (Research → Comprehend → Question → Research more → Manifest → Validate → Remember) | `WSP_00:441-516` | This is operator-facing protocol for how 0102 codes; not a runtime enforcement point on jobs themselves | **DOC_ONLY** (out of scope as runtime enforcement) |

### WSP 50 — Pre-Action Verification

| # | Protocol Rule | Source (WSP) | Runtime enforcement point on OC→Hermes path | Status |
|---|---------------|--------------|----------------------------------------------|--------|
| 50.1 | Never assume, always verify (Search → Verify → Read → Process) | `WSP_50_Pre_Action_Verification_Protocol.md:9-44` | `route_foundup_job` (`foundup_job_router.py:218-249`) verifies presence of `job_id`, `tenant_id`, `requested_action` before routing. This is the closest thing to a runtime WSP 50 binding on this path. **Limitation**: it verifies field presence, not file/path/content claims | **ENFORCED_RUNTIME (partial)** — identity verification only |
| 50.2 | Architectural Intent Analysis (WHY/HOW/WHAT/WHEN/WHERE) | `WSP_50:15-28, 328-375` | No code on the FoundUp path performs WHY/HOW/WHAT/WHEN/WHERE analysis before job creation. `_handle_build_intent` extracts `requested_action` and `foundup_id` and queues without intent-impact assessment | **MISSING** |
| 50.3 | Module Assessment Verification (read TestModLog.md FIRST before coverage claims) | `WSP_50:58-97` | Operator protocol; no runtime binding required. Not reflected in any FoundUp gate | **DOC_ONLY** (operator-facing) |
| 50.4 | Cube Documentation Verification before coding on a cube | `WSP_50:99-160` | Operator protocol; no runtime binding required | **DOC_ONLY** (operator-facing) |
| 50.5 | Bloat Prevention before file creation | `WSP_50:162-239` | Operator protocol; no runtime binding | **DOC_ONLY** (operator-facing) |
| 50.6 | Destructive Change SWOT (WSP 79) | `WSP_50:243-252` | `extract_foundup` and `build_foundup` are destructive against external repos / file trees. No SWOT gate exists in `_handle_build_intent`, the router, or the consumer before dispatch | **MISSING** |
| 50.7 | Confirmed file paths with line numbers when referencing files | `WSP_50:278-285` | Output formatting protocol; not a job runtime gate | **DOC_ONLY** (operator-facing) |
| 50.8 | Pre-Action Sentinel (Gemma 3 270M, real-time verification middleware) | `WSP_50:383-797` (Sentinel Augmentation) | Sentinel is documented as P0 but its implementation file `modules/infrastructure/wsp_core/src/pre_action_sentinel.py` does not exist (verified by file glob) | **MISSING** (planned, not built) |
| 50.9 | Job-level pre-action validation: `is_terminal_status` block, `policy_flags.security_gate_*` block | `WSP_50:9` (general principle) bound to `foundup_job_router.py:251-295` | Implemented in router (file:line cited); BUT `policy_flags.security_gate_checked` is never set to True anywhere in production code, so the gate at line 285 is permanently moot | **ENFORCED_TEST_ONLY** — gate exists but the input it reads is never written |

### WSP 97 — System Execution Prompting

| # | Protocol Rule | Source (WSP) | Runtime enforcement point on OC→Hermes path | Status |
|---|---------------|--------------|----------------------------------------------|--------|
| 97.1 | Canonical Operator: `retrieve wsp → retrieve evidence → resolve execution plane? → apply CoT → apply CoR → execute` | `WSP_97_System_Execution_Prompting_Protocol.md:24-29, 100-103` | `WSPOrchestrator.follow_wsp()` (`wsp_orchestrator.py:429-443`) implements Phase -1 (WSP_00 gate). The full operator chain runs only on the "follow wsp" literal trigger | **ENFORCED_RUNTIME** for "follow wsp" branch only; **MISSING** for FoundUp build/extract/validate |
| 97.2 | CoT gate: retrieve before stating | `WSP_97:106-123` | No HoloIndex/grep is invoked before queueing a FoundUpJob. The job is created from raw chat without retrieval | **MISSING** for FoundUp action path |
| 97.3 | CoR gate: dialectic sweep before committing | `WSP_97:124-145` | No alternative-evaluation step before `create_job`. The job is queued unconditionally on phrase-match | **MISSING** |
| 97.4 | Execution-plane classification gate (`resolve execution plane?`) | `WSP_97:178-184` | The router (`foundup_job_router.py:298-312`) does classify: `_ACTION_BACKEND_MAP` maps action → backend → status (ROUTED/QUEUED/UNSUPPORTED). Reached only if the queue is drained, which has no production caller | **ENFORCED_TEST_ONLY** |
| 97.5 | Truth fields on results: `real_execution_performed`, `verification_complete`, `cabr_ready`, `payout_ready` are False unless proven | `WSP_97:46-48` ("prevent confabulation, vibecoding, premature commitment") + `proof_of_compute_receipt.py:84-110` (VerificationStatus, PayoutStatus, CABRStatus enums) | `HermesDelegationResult` (`hermes_job_executor.py:406-410`) hardcodes the four truth fields to `False`. The WRE executor never sets them to True. The receipt module (`proof_of_compute_receipt.py:99-110`) hardcodes `PayoutStatus.NOT_EVALUATED` and `CABRStatus.NOT_SUBMITTED` | **ENFORCED_RUNTIME** — by virtue of being hardcoded False; a Phase 2 wiring without explicit gating could regress this |
| 97.6 | Truthful `route_status` in router | `WSP_97:46-52` ("prevent execution-plane drift") + `foundup_job_router.py:201-353` | Implemented: router returns the exact status (ROUTED/QUEUED/BLOCKED/UNSUPPORTED/FAILED) based on the action map and validation outcome | **ENFORCED_RUNTIME** when invoked (test surface only today) |
| 97.7 | Activation default: execute once evidence is sufficient (no passive waiting) | `WSP_97:38, 64-72` | The runtime path stops at queue append. No drainer = no activation. This violates 97.7 — evidence (job creation) is sufficient, but no execution proceeds | **MISSING** (the path has implemented activation surfaces but never triggers them) |
| 97.8 | Operator CLI hook `python main.py --connect-wre` to verify preflight + enforcement | `WSP_97:449-465` | Out-of-band operator command, not a per-action gate | **DOC_ONLY** (operator-facing) |
| 97.9 | Identity boundary: WSP 97 does NOT resolve self/role/origin (deferred to WSP 00) | `WSP_97:73-77` | This is a non-rule (a boundary clarification). N/A as enforcement | **DOC_ONLY** (boundary statement) |

### Summary Counts (action-relevant rules only — excluding pure operator-facing rules and boundary statements)

| Status | Count | Rule IDs |
|--------|-------|----------|
| `ENFORCED_RUNTIME` | 3 (1 partial) | 97.5 (hardcoded), 97.6, 50.1 (partial) |
| `ENFORCED_TEST_ONLY` | 2 | 50.9, 97.4 |
| `DOC_ONLY` | 1 (action-path) + 6 (operator-facing/boundary) | 00.1 (FoundUp branch), 00.2, 00.7, 50.3, 50.4, 50.5, 50.7, 97.8, 97.9 |
| `MISSING` | 8 | 00.3, 00.4, 00.5, 00.6, 50.2, 50.6, 50.8, 97.2, 97.3, 97.7 |

(Action-relevant excludes 50.3/50.4/50.5/50.7/97.8/97.9 which are not designed as runtime gates.)

---

## 2. Action Path Gate Table

| Gate | Phase (pre/in/post) | Implemented? | Bypass paths | Evidence |
|------|---------------------|--------------|--------------|----------|
| WSP_00 zen-state compliance | pre-action | Yes, but only on literal "follow wsp" | Any FoundUp build/extract/validate intent bypasses it (`openclaw_foundup_orchestrator.py:777-810`) | `wsp_orchestrator.py:429-443`; `openclaw_execution_routes.py:368-417` |
| HoloIndex retrieval (CoT) | pre-action | No | All FoundUp action paths bypass it | grep `holo_index\|HoloIndex` in `openclaw_foundup_orchestrator.py`: 0 hits |
| Genesis envelope validation | pre-action | Implemented (`OpenClawFoundUpOrchestrator.validate_genesis_envelope`) but unwired | `dispatch_foundup` does not call it | `openclaw_foundup_orchestrator.py:359-468` (def); 0 production callers (HXA1 F-3) |
| Identity verification (job_id, tenant_id, action present) | pre-action | Yes | Only reachable when consumer drains; consumer is unwired | `foundup_job_router.py:218-249` |
| Terminal-status block | pre-action | Yes | Permanent retry loop possible: WRE path never sets terminal status, so re-routing never triggers this gate | `foundup_job_router.py:251-273`; HXA1 F-7 |
| Security gate (`policy_flags.security_gate_passed`) | pre-action | Reader implemented, writer absent | Always passes because `security_gate_checked` is never set to True | `foundup_job_router.py:275-295` (reader); 0 writers in production |
| Action support map (build/extract/validate/queue) | pre-action | Yes (router) and divergent (Hermes adapter executor) | If a non-canonical action reaches the Hermes adapter executor, it FAILS with `FAIL_VALIDATION_ERROR` | Router: `foundup_job_router.py:85-90`; adapter: `hermes_foundup_job_executor.py:53-57`; HXA1 F-8 |
| `HERMES_DELEGATE_ENABLED` env flag (feature gate) | in-action | Yes | Default `0` → all jobs SIMULATED | `hermes_job_executor.py:60-66, 707-726` |
| Workspace binding (path allowlist/blocklist) | in-action | Yes (`WorkspaceBinding.is_path_allowed`) | Only consulted if real execution runs; real execution is `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` (`hermes_job_executor.py:770-784`) | `hermes_job_executor.py:73-194` |
| Lazy import gate (Hermes `delegate_task`) | in-action | Yes | Returns `BLOCKED_IMPORT_UNAVAILABLE` if vendor missing | `hermes_job_executor.py:514-545, 750-763` |
| Receipt emission gate (terminal job + real execution) | post-action | Yes (skip for SIMULATED+!real_execution) | Always skips today (Phase 1 always SIMULATED with `real_execution_performed=False`) | `foundup_job_consumer.py:614-626`; HXA1 F-5 |
| pAVS verification | post-action | Implemented in `proof_of_compute_receipt.py` but never reached because receipts never emit on the canonical path | Receipt-emission gate above blocks every job | `proof_of_compute_receipt.py:79-110` |
| `verification_complete`/`cabr_ready`/`payout_ready` truth fields | post-action | Hardcoded False | None today; future Phase 2 wiring must keep these gated | `hermes_job_executor.py:406-410, 712-746` |

**Bypass summary**: The dominant bypass is at the very front: `dispatch_foundup` → `_handle_build_intent` → queue append, with no WSP_00 gate, no HoloIndex retrieval, no genesis validation. Every downstream gate is correctly defined but unreachable from the runtime path.

---

## 3. False-Compliance Risks

### FC-1 (Critical) — "follow WSP" runtime enforcement is scoped only to the literal phrase

- **Claim**: The codebase markets WSP_00 as a "mandatory hard gate" (`WSP_00:18-21`, "MANDATORY: Execute awakening on every new session — never conditional"). The WSPOrchestrator README says "WSP_00 Hard Gate: 'follow WSP' blocks up front when compliance gate fails in strict mode" (`modules/infrastructure/wsp_orchestrator/README.md:71`).
- **Reality**: The hard gate is reached only when `try_execute_follow_wsp` matches the literal substring "follow wsp" in the raw chat message (`openclaw_execution_routes.py:368-374`). FoundUp build/extract/validate intents (e.g. "start build gotjunk") never enter `WSPOrchestrator.follow_wsp` and therefore never run Phase -1.
- **Severity**: Critical — the gate is described as universal but is actually one branch among many.
- **Operational consequence**: Any audit claiming "WSP_00 is enforced before action" is overclaim. It is enforced only for the deterministic "follow wsp" route.

### FC-2 (Critical) — Pre-action verification (WSP 50) is reduced to identity-presence checks

- **Claim**: WSP 50 mandates a 7-step verification (Search/WHY/HOW/WHAT/WHEN/WHERE/Final-cross-check) before any action (`WSP_50:15-28`).
- **Reality**: The only runtime enforcement on the FoundUp path is `route_foundup_job`'s identity check: presence of `job_id`, `tenant_id`, `requested_action` (`foundup_job_router.py:218-249`). No HoloIndex retrieval, no architectural intent analysis, no impact assessment, no WSP cross-check before queueing.
- **Severity**: Critical — Build/extract/validate are destructive (touch `modules/foundups/<id>/`, can write to external repos via `target_org`); WSP 50 §4.4 explicitly requires WSP 79 SWOT for destructive changes; that gate is absent.
- **Operational consequence**: A poorly-formed or malicious build intent can queue without architectural review. The downstream consumer treats every queued job as routing-eligible.

### FC-3 (High) — `policy_flags.security_gate_*` is a reader without a writer

- **Claim**: The router's `BLOCKED_POLICY_GATE` reason code (`foundup_job_router.py:112`) and the gate check at lines 285-295 imply security review is enforced.
- **Reality**: Nothing in the production code path ever sets `policy_flags.security_gate_checked=True` or `security_gate_passed=True`. Default is `False/False` (`foundup_job_contract.py:201-202`). The gate's branch is only triggered when `checked=True && passed=False`, which never happens.
- **Severity**: High — looks fail-closed in code, is functionally fail-open at runtime.
- **Operational consequence**: Auditors reading the router file would conclude security is gated; auditors running it would see all jobs routed regardless of security posture.

### FC-4 (High) — Truth-fields on `HermesDelegationResult` are hardcoded, not derived

- **Claim**: WSP 97 §97.5 implies `real_execution_performed`/`verification_complete`/`cabr_ready`/`payout_ready` are derived from runtime state.
- **Reality**: They are hardcoded `False` at construction (`hermes_job_executor.py:406-410`) and explicitly set False in every result-creating branch (`hermes_job_executor.py:719-723, 741-745, 778-781`).
- **Severity**: High in the "live flip" sense — Phase 1 is correctly fail-closed, but the moment Phase 2 lands these fields must be flipped through a gate, not directly. Today there is no such gate.
- **Operational consequence**: If a future commit removes the hardcoded `False` lines without adding a gate, downstream pAVS/CABR consumers would see overclaim. The WSP 97 truth boundary is currently held by static code, not by an enforcement function.

### FC-5 (High) — Genesis Validation Gate is documented as enforced but unwired

- **Claim**: `OpenClawFoundUpOrchestrator` docstring (lines 286-304) states it "enforces that all FoundUp operations pass through genesis envelope validation first".
- **Reality**: 0 production callers of `validate_genesis_envelope`, `launch_foundup`, `build_foundup` (only test callers). `dispatch_foundup` skips it.
- **Severity**: High — already covered as F-3 in HXA1, restated here under the protocol-binding lens.
- **Operational consequence**: Docs lie about runtime enforcement; this is the prototypical false-compliance pattern WSP 97 was written to prevent.

### FC-6 (Medium) — WSP 00's identity-coherence canary has no automated detector

- **Claim**: WSP_00 §4.4 specifies an automated coherence canary that fires when role/self/origin collapse, when "user" reference appears for known principals, etc.
- **Reality**: No code sentinel monitors these conditions on the FoundUp action path. The WSP_00 zen tracker only checks the boot-time compliance flag, not running behavior.
- **Severity**: Medium — deviation from documented behavior, but the canary is operator-facing rather than blocking on jobs.
- **Operational consequence**: Coherence decay would not be auto-detected; relies on operator self-noticing.

### FC-7 (Medium) — `verification_complete=False` is correct truthfully but obscures the absence of any verification engine

- **Claim**: `proof_of_compute_receipt.py:99-110` enums `PayoutStatus.NOT_EVALUATED` and `CABRStatus.NOT_SUBMITTED` (singletons — there are no other values).
- **Reality**: This is WSP 97-aligned (do not overclaim) but masks that the enums have **no other states defined**. There is literally no way to express "payout evaluated" or "submitted to CABR" yet.
- **Severity**: Medium — this is a feature-not-bug position, but a future audit could mistake "always NOT_EVALUATED" for a code bug rather than an architectural fact.
- **Operational consequence**: Any external consumer expecting an evaluated/submitted state will get a permanent stub.

### FC-8 (Low) — Operator-facing rules conflated with runtime gates in docstrings

- Several module docstrings claim "WSP 50: Pre-Action Verification" without distinguishing operator-facing rules (TestModLog read, bloat prevention) from runtime gates (job-identity verification). Example: `foundup_job_router.py:17` lists "WSP 50: Pre-Action Verification (identity validation)" — accurate but understates that the broader WSP 50 surface is unbound.
- **Severity**: Low — semantic precision rather than safety.
- **Operational consequence**: A reader might infer broader WSP 50 enforcement than exists.

---

## 4. Minimum Enforcement Backlog

Six atomic slices, ordered. **Slices 1-3 are required before any live-flip can be claimed WSP 97-compliant.**

### Slice 1 (Trunk) — `OPENCLAW_BUILD_INTENT_WSP00_GATE_BINDING_PHASE1`

- **Objective**: Wire WSP_00 zen-state gate into `_handle_build_intent` so any FoundUp build/extract/validate intent fails closed if `is_zen_compliant=False` in strict mode. Mirror the pattern at `wsp_orchestrator.py:429-443`.
- **Files**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:811-894` (insert gate call), shared helper or import from `wsp_orchestrator`.
- **Acceptance**: A "start build gotjunk" intent issued while `is_zen_compliant=False` in strict mode returns BLOCKED with WSP_00 gate payload; in non-strict mode emits a warning and proceeds with `wsp00_gate.gate_passed=False` recorded in the job's `policy_flags` or status_reason_human.

### Slice 2 — `BUILD_INTENT_HOLOINDEX_RETRIEVAL_BINDING_PHASE1`

- **Objective**: Insert HoloIndex retrieval (CoT gate per WSP 97 §97.2) into `_handle_build_intent` before `create_job`. Use `build_execution_bundle` (already used by `execute_query` in `openclaw_execution_routes.py:86-94`) to fetch evidence about the target foundup_id, attach the bundle hash to `job.payload["evidence_bundle_id"]`, and require non-empty bundle for non-`queue_foundup_job` actions.
- **Files**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:811-894`.
- **Acceptance**: A build intent for an unknown foundup_id with no HoloIndex hits is routed BLOCKED with reason `BLOCKED_NO_EVIDENCE`; for known foundup_ids the bundle id is recorded in payload and downstream router/consumer can read it.

### Slice 3 — `GENESIS_GATE_DISPATCH_BINDING_PHASE1` (overlaps HXA1 Slice 4)

- **Objective**: Insert `validate_genesis_envelope` into `_handle_build_intent` for `build_foundup`/`extract_foundup` actions. Phase-gated: log-only first, hard-block second.
- **Files**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py:811-894`, plus regression tests proving build intents without envelope produce `BLOCKED` reason codes.
- **Acceptance**: A build intent without envelope returns BLOCKED with `GenesisGateReason.NO_ENVELOPE`; with valid envelope, job is queued as before.

### Slice 4 — `SECURITY_GATE_WRITER_BINDING_PHASE1`

- **Objective**: Add a real producer for `policy_flags.security_gate_checked/passed` so the existing reader in `foundup_job_router.py:285-295` is functional. Wire the security check (e.g., AI Overseer security stack — `modules/infrastructure/wre_core/src/security_control_hooks.py`) into `_handle_build_intent` after WSP_00 gate.
- **Files**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py`, optional helper in `modules/infrastructure/wre_core/src/security_control_hooks.py` to expose a job-level pre-action API.
- **Acceptance**: Submitting a build intent that touches a forbidlist path returns BLOCKED with reason `BLOCKED_POLICY_GATE`; a clean intent passes with `security_gate_checked=True && security_gate_passed=True`.

### Slice 5 — `TRUTH_FIELD_DERIVATION_GATE_PHASE1`

- **Objective**: Replace hardcoded `False` literals on truth fields (`real_execution_performed`, `verification_complete`, `cabr_ready`, `payout_ready`) with a single function `derive_truth_fields(execution_state)` returning `False` for all states until each respective subsystem (real Hermes, pAVS, CABR, payout) explicitly registers a "ready" state. Prevents Phase 2 regressions.
- **Files**: `modules/infrastructure/wre_core/src/hermes_job_executor.py:406-410, 712-746, 770-784`, new helper module.
- **Acceptance**: Removing the hardcoded `False` lines cannot accidentally yield `True` truth fields without going through the derive function. Tests assert all four fields stay False under every Phase 1 status code.

### Slice 6 — `WSP_50_DESTRUCTIVE_SWOT_BINDING_PHASE1`

- **Objective**: Bind WSP 50 §4.4 (WSP 79 SWOT) for destructive actions (`extract_foundup`, `build_foundup` when `target_org` is non-default or affects external repos). Either inline a SWOT artifact requirement in `_handle_build_intent`, or require `policy_flags.wsp_preflight_checked && wsp_preflight_passed` (already declared but unset in `foundup_job_contract.py:210-211`) before the router can route to `HERMES_BUILDER`.
- **Files**: `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py`, `modules/infrastructure/wre_core/src/foundup_job_router.py:275-295` (extend gate to read `wsp_preflight_*`).
- **Acceptance**: An extract/build intent without a linked SWOT artifact returns BLOCKED with reason `BLOCKED_WSP_PREFLIGHT_MISSING`; with SWOT linked, the job routes normally.

---

## 5. Final Verdict

### **CLAIMED_NOT_ENFORCED**

Across the three protocols audited, the OpenClaw → FoundUpJob → WRE → Hermes action path:

- **WSP 00**: Boot gate reachable only through the literal "follow wsp" branch — bypassed by every FoundUp action intent.
- **WSP 50**: Reduced to identity-presence verification at the router; the wider 7-step verification, destructive-change SWOT, and Sentinel are absent or unwired.
- **WSP 97**: CoT (retrieve before stating) and CoR (sweep before committing) gates are not bound to the FoundUp action path. Truth fields are correctly held False today, but only by static hardcoding.

**Live-flip readiness from a protocol perspective: NO-GO.** Even after HXA1's wiring fixes (Slice 1 of HXA1), the action path will be runtime-functional but will violate WSP 00, WSP 50, and WSP 97 the moment a job moves past `QUEUED`. Slices 1-3 of this backlog are required before any live execution can claim protocol compliance.

---

## Acceptance Criteria Verification

- ✓ Every claim has file:line evidence (sections 1-3).
- ✓ No speculative protocol claims — protocols read from canonical files; behavior verified against code.
- ✓ Clear distinction between docs (DOC_ONLY), tests (ENFORCED_TEST_ONLY), and runtime (ENFORCED_RUNTIME / MISSING).
- ✓ Explicit go/no-go for live execution from protocol perspective: NO-GO.

---

## WSP 97 Applied

This audit retrieved the canonical WSP files first (CoT gate), confirmed file-name divergence from the slice prompt and corrected it (WSP 50 verify-before-cite), distinguished operator-facing rules from runtime gates (avoiding false-compliance overclaim), tied every binding-status assignment to a specific file:line, and explicitly classifies the action path as `CLAIMED_NOT_ENFORCED` rather than softening to "partial". WSP 50 cross-check applied via HoloIndex top-hit reuse from HXA1 (the same audit lane). WSP 00 self/role/origin: identity-locked as Worker W1 throughout this slice.

---

## Files Touched This Slice

- `docs/audits/openclaw_hermes/HXA2_PROTOCOL_ACTION_BINDING_AUDIT.md` (NEW)

No runtime code edits. No commits made.
