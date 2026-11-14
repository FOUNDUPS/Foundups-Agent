# OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1

**Slice:** OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1
**Worker-Lane:** W6
**Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** Targeted remediation — patches OpenClaw's existing loop/routes. **No second layer.**

---

## 1. Mission and Scope

PR #737 identified OpenClaw/WSP 109 onboarding governance gaps; PR #738 locked them as
strict-xfail characterization tests. This slice **closes those gaps by patching the existing
OpenClaw dispatch** — it does not introduce a parallel orchestration framework. The
pre-existing genesis machinery (`OpenClawFoundUpOrchestrator.validate_genesis_envelope`,
`GenesisGateResult`, `_suggest_remediation`) is **reused**, not rebuilt (WSP 84).

**Files changed (7):**
| File | Change |
|------|--------|
| `src/openclaw_foundup_orchestrator.py` | Genesis gate wired into `dispatch_foundup`; launch/onboard detector; `create foundup` convergence; `_genesis_gate_handoff` |
| `src/openclaw_result_memory.py` | `build_w10_handoff` + W10 handoff for FOUNDUP outcomes (no self-approval) |
| `tests/test_openclaw_wsp109_onboarding_dryrun.py` | 4 strict xfails → passing assertions + behavioural tests |
| `tests/test_openclaw_foundup_routing.py` | Reload-pollution hygiene fix |
| `docs/audits/architecture/OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1.md` | This audit |
| `ModLog.md`, `tests/TestModLog.md` | Documentation |

`openclaw_intent_planner.py` and `test_openclaw_foundup_orchestrator.py` (both in the
dispatch's "likely files") were **not** needed — classification already routes onboarding
to FOUNDUP, and the orchestrator tests pass unchanged. Scope locked by discovery.

---

## 2. Predecessor Citations

| PR | Slice | Relationship |
|----|-------|--------------|
| #737 | OPUS_4_8_OPENCLAW_INTERNAL_MODEL_PROBE_PHASE1 | Identified the gaps (S1, 9.1#1-3) |
| #738 | OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1 | Strict-xfail contracts converted here |
| #718 | WSP_109_FOUNDUP_ONBOARDING_INTAKE_PROTOCOL_PHASE1 | Defines the WSP 109 intake gate |
| #725 | REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1 | RedDog bootstrap context |

---

## 3. HoloIndex Retrieval Evaluation

| # | Query | Top hits | Quality |
|---|-------|----------|---------|
| Q1 | OpenClaw WSP109 onboarding genesis gate validate_genesis_envelope | `openclaw_dae.py`, WSP_109, WSP_106 | MEDIUM |
| Q2 | dispatch_foundup launch_foundup validate_genesis_envelope | `fam_adapter.py`, `agent_market/ARCHITECTURE.md`, WSP_98 | MEDIUM |
| Q3 | create foundup job dual parser OpenClaw | `fam_adapter.py`, WSP_84, WSP_102 | MEDIUM |
| Q4 | W10 handoff READY NOT_READY OpenClaw validate_and_remember | `skill_safety_guard.py`, `test_openclaw_dae.py`, WSP_21 | LOW |
| Q5 | OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1 | drift to `foundup-cube.js`, `ARCHITECTURE.md` | LOW |

HoloIndex pointed at the FAM/orchestrator surfaces (Q1-Q3); the genesis methods and the
audit doc were reached by direct path. The reusable genesis gate
(`validate_genesis_envelope`, `GenesisGateResult`, `_suggest_remediation`) was found by
direct read of `openclaw_foundup_orchestrator.py` — the decisive WSP 84 reuse.

---

## 4. #738 Failing-Contract Summary

| #738 strict xfail | Gap | Status after this slice |
|-------------------|-----|--------------------------|
| onboard should route through intake | no genesis gate | CONVERTED → `_is_foundup_launch_or_onboard_intent` + NOT_READY handoff |
| dispatch should be genesis-gated | `validate_genesis_envelope` not invoked | CONVERTED → gate wired into `dispatch_foundup` |
| create-foundup variants should converge | divergent paths | CONVERTED → both → dry-run queue |
| mutating path should emit W10 handoff | self-approval | CONVERTED → `build_w10_handoff` for FOUNDUP |

---

## 5. Implementation Design

No new orchestrator. Three surgical edits to the existing loop:

**A. Genesis gate in `dispatch_foundup`** — order:
1. `_is_explicit_build_intent` → `_handle_build_intent` (typed dry-run QUEUED job; **never launches**). Unchanged for existing build words; now also catches bare `create foundup`.
2. **`_is_foundup_launch_or_onboard_intent`** (`onboard`, `launch foundup`, `launch this foundup`, `go live`) → `get_orchestrator().validate_genesis_envelope(_extract_envelope_data(intent))`. A chat prompt has no envelope → `NO_ENVELOPE` → `_genesis_gate_handoff` returns a **NOT_READY W10 packet**; `fam_adapter.launch_foundup` is never reached.
3. Else → FAM advisory/catalog passthrough (unchanged, no mutation).

`_extract_envelope_data` returns `{}` unless `intent.payload['genesis_envelope']` is a real dict (mock-safe). `validate_genesis_envelope({})` short-circuits at Check-1 **before** loading any validator → deterministic, no network/model import.

**B. W10 handoff in `validate_and_remember`** — for `category == "foundup"`, build and attach a `build_w10_handoff(status="NOT_READY", required_wsp="WSP_109", blocked_execution=True, ...)` packet. `success` still only means "a valid response was produced", never launch approval.

**C. Test hygiene** — removed the harmful `importlib.reload` in `test_openclaw_foundup_routing.py` (the call-time `fam_adapter` import makes it unnecessary), eliminating the pre-existing cross-file pollution flagged in #738 §6.

---

## 6. Gate Behaviour Before/After Matrix

| Intent | Before (#737) | After (this slice) |
|--------|---------------|--------------------|
| `launch foundup Shield with token SHLD` | FAM passthrough → **real launch** | genesis gate → **NOT_READY** W10 handoff (no launch) |
| `Follow WSP 109 and onboard a FoundUp called Shield` | FAM passthrough, no intake | genesis gate → **NOT_READY** handoff |
| `create foundup Shield` | FAM passthrough → real launch | dry-run **QUEUED** job (no launch) |
| `create foundup job for Shield` | dry-run queue | dry-run queue (unchanged) |
| `start build / hermes build / extract / validate foundup` | dry-run queue | dry-run queue (unchanged) |
| `what is cabr` (advisory) | FAM passthrough | FAM passthrough (unchanged) |
| FOUNDUP outcome recording | self-approve `success` | + **W10 NOT_READY handoff** packet |

The only paths that change are the previously-ungated launch/onboard/create-foundup ones.
No advisory or build-queue behaviour regressed (existing tests green).

---

## 7. Parser Convergence Proof

`_is_explicit_build_intent("create foundup Shield") == _is_explicit_build_intent("create foundup job for Shield")` → both `True` (added bare `create foundup` to `_FOUNDUP_BUILD_WORDS`). Both dispatch to `_handle_build_intent` → a single QUEUED dry-run job; neither reaches `fam_adapter.launch_foundup`. Proven by `test_create_foundup_variants_converge` and `test_create_foundup_variants_both_queue_no_launch`. The existing `_is_explicit_build_intent("create foundup job ...") is True` assertion (routing test L392) remains green — no third parser added.

---

## 8. W10 Handoff Packet Contract

`build_w10_handoff(status, reason, required_wsp="WSP_109", required_artifacts=None, suggested_next_slice=None, blocked_execution=True) -> dict`:

```
{ kind: "w10_handoff", status: "READY"|"NOT_READY", reason, required_wsp,
  required_artifacts: [...], suggested_next_slice, blocked_execution: bool }
```

- `status` normalises any non-{READY,NOT_READY} value to **NOT_READY** (no accidental self-approval).
- Emitted by (a) `_genesis_gate_handoff` for ungated launch/onboard intents, and (b) `validate_and_remember` for FOUNDUP outcomes.
- Does **not** merge, push, open PRs, or claim approval. Verified by `test_build_w10_handoff_packet_shape`.

---

## 9. Test Results

| Run | Result |
|-----|--------|
| `test_openclaw_wsp109_onboarding_dryrun.py` (remediated) | **10 passed**, 0 xfail |
| adjacent `test_openclaw_foundup_routing.py` + `test_openclaw_foundup_orchestrator.py` | **49 passed** (was `8 failed` pre-fix → pollution closed) |
| all three together | **59 passed, 0 failed, 0 xfail** |
| broader `-k "foundup or result or dae or routing or memory or continuity"` sweep | 483 passed, **4 pre-existing failures** (see §10) |

Determinism preserved: pure-function + `inspect.getsource` + lightweight mock; no live
process, network, `.env`, or model calls.

---

## 10. Remaining Deferred Items

- **4 pre-existing failures (out of scope, NOT caused by this slice):**
  `test_openclaw_dae.py::TestConversationRuntimeFlags::test_identity_snapshot_exposes_lineage_and_resolved_model`,
  `test_openclaw_dae.py::TestEndToEndProcess::test_blocked_command_returns_security_block`,
  `test_openclaw_dae_runtime_commands.py::test_execute_system_routes_to_dae_runtime_adapter`,
  `test_openclaw_dae_runtime_commands.py::test_execute_system_routes_pqn_simulation_to_dae_runtime_adapter`.
  **Verified pre-existing**: all fail on clean `origin/main` (62db6324a) with this slice's
  changes stashed. Symptoms (`handle_dae_runtime_intent` not called; remote-commander
  denied) are unrelated to FOUNDUP dispatch. Recommend a separate slice.
- **Envelope-carrying launch path:** when a real WSP 109 intake packet exists
  (`intent.payload['genesis_envelope']`), the gate would pass and delegate to
  `_handle_build_intent`; the full FAM launch wiring after a *valid* envelope is deferred
  (today every chat launch correctly yields NOT_READY).

---

## 11. Internal Review Verdict

**READY.** All four #738 strict-xfail contracts are converted to passing assertions; the
genesis gate is enforced before any FAM launch; create-foundup parser paths converge; a
W10 NOT_READY handoff replaces self-approval for FOUNDUP work; the pre-existing reload
pollution is cleaned up. No second orchestration layer (existing machinery reused). No new
test failures introduced (4 pre-existing failures verified and reported, not masked).

---

## 12. WSP_97 Truth Boundary Checklist

Declared count: **24 / 24 YES** (rows below = 24).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | OPENCLAW_WSP109_GATE_REMEDIATION_ONLY | YES | Only the four #737/#738 gaps addressed |
| 2 | NO_SECOND_ORCHESTRATION_LAYER | YES | Reused `OpenClawFoundUpOrchestrator` gate; patched existing dispatch |
| 3 | NO_DIRECT_FOUNDUP_LAUNCH_WITHOUT_GENESIS_GATE | YES | launch/onboard → `validate_genesis_envelope` → NOT_READY; FAM launch unreachable |
| 4 | NO_W10_SELF_APPROVAL | YES | `build_w10_handoff` NOT_READY for FOUNDUP; success ≠ approval |
| 5 | NO_AUTO_PR_OR_MERGE | YES | No git/PR actions in any code path |
| 6 | NO_LIVE_OPENCLAW_PROCESS_IN_TESTS | YES | Pure-function + mock; no DAE boot |
| 7 | NO_NETWORK_CALL_IN_TESTS | YES | `validate_genesis_envelope({})` short-circuits before validator load |
| 8 | NO_DOTENV_READ_IN_TESTS | YES | No `.env` access |
| 9 | NO_MODEL_CALL_IN_TESTS | YES | No LLM/Gemma calls |
| 10 | NO_WSP_FRAMEWORK_MUTATION | YES | WSP docs read-only |
| 11 | NO_SKILL_CREATION | YES | No SKILLz created |
| 12 | NO_REGISTRY_MUTATION | YES | No registry written |
| 13 | NO_MANIFEST_MUTATION | YES | No manifest written |
| 14 | NO_CATALOG_MUTATION | YES | No catalog written |
| 15 | NO_PUBLIC_SURFACE_MUTATION | YES | No routes/INTERFACE changed |
| 16 | NO_ROUTE_ACTIVATION | YES | No route activated |
| 17 | NO_CABR_READY | YES | No CABR touched |
| 18 | NO_PAYOUT_READY | YES | No payout touched |
| 19 | NO_DAO_ACTIVATION | YES | No DAO activation |
| 20 | GENESIS_GATE_ENFORCED | YES | §5A; `test_launch_msg_is_gated_not_fam_passthrough` |
| 21 | PARSER_CONVERGED | YES | §7; `test_create_foundup_variants_converge` |
| 22 | W10_HANDOFF_EMITTED | YES | §8; `test_validate_and_remember_emits_w10_handoff` |
| 23 | FOUR_XFAILS_CONVERTED | YES | 0 xfail in remediated file (10 passed) |
| 24 | PREEXISTING_FAILURES_REPORTED | YES | §10; verified on clean main via stash |

**WSP 97 Truth Boundary Checklist: 24/24 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary
discipline. Targeted remediation of the #737/#738 WSP 109 genesis-gate gaps by patching
OpenClaw's existing dispatch — no second orchestration layer; existing genesis machinery
reused.*
