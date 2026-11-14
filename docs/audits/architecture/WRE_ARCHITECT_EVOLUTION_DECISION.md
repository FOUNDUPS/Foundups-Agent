# WRE Architect Evolution Decision (WAE-AR1)

**Slice**: WAE-AR1 / WRE_ARCHITECT_EVOLUTION_ARCHITECTURE_REVIEW_PHASE1
**Status**: DECISION-ONLY (no runtime implementation)
**Base SHA**: `1a672a5dafbb4e704d67b33b98329f8766a94de3` (origin/main HEAD, 2026-06-26)
**Branch**: `audit/wae-architecture-review-phase1`
**Protocol**: WSP_00 (Zen State) + WSP_97 (CoT/CoR/CoA)
**Lane**: Internal RedDog / WRE architect lane. Does NOT touch the external Foundups(R)Agent extension lane or PR #879 acceptance-baseline work.

---

## 0. Executive Ruling

RedDog wears the **Architect / Researcher / Governor / Dispatcher** hats as a *coordinating-intelligence surface*. RedDog does **NOT** become four new DAEs, and does **NOT** become a new always-on daemon. Every execution path already has an owner; the WAE work folds the four hats into those existing owners and adds five thin invariant layers (L0-L4). No new orchestrator is created.

Existing owners (unchanged by this decision):

| Owner | Responsibility | Verified primitive(s) |
|-------|----------------|-----------------------|
| OpenClaw | policy + intent gate | `openclaw_permission_policy.py` (`check_permission_gate`, fail-closed SOURCE tier) |
| Hermes | execution scaffold / delegation | `hermes_job_executor.py` (seam only; real delegation BLOCKED Phase 1) |
| WRE | worker dispatch + verification + repo/process authority | `wre_master_orchestrator.py` (declares primacy), guards |
| Skillz / Wardrobe | worker capability selection | WSP 95; `wre_skills_loader.py`, `SkillSelector` |
| Sentinels | adversarial review | heterogeneous judge panel (escalations path; NOT Fusion) |
| CABR / pAVS | benefit validation | WSP 29 3V engine |
| 012 / DAO | sovereign merge / authority boundary | merge/promotion authority  -  code-side merge-on-consensus is REJECTED |

---

## 1. HoloIndex Phase 0 Quality

| Query | Quality | Note |
|-------|---------|------|
| recursive improvement loop pattern_memory improvement_job_contract | MEDIUM | Surfaced `recursive_improvement/` docs + WSP 48/67/27, but NOT `improvement_job_contract.py` / `pattern_memory.py` directly. Direct-read used. |
| OpenClaw Hermes WRE Skillz worker dispatch | MEDIUM | Surfaced `openclaw_dae.py`, `worker_assignment_protocol.py`, WSP 95/54/11. Did not surface `openclaw_execution_routes.py` / `hermes_job_executor.py`. Direct-read used. |
| FOUNDUP permission bypass fam_adapter orchestrator_launch | MEDIUM | Surfaced `fam_adapter.py` + FOUNDUP routing tests, but NOT `openclaw_foundup_orchestrator.py` (where the genesis gate lives). Direct-read used. |
| destructive_action_guard capability_token_validator source_authority merge | MEDIUM | Surfaced adjacent `DESTRUCTIVE_ACTION_GUARD_*` audit docs but NOT the guard `.py` files themselves. Direct-read used. |

**Overall**: MEDIUM with a localized INDEX_GAP  -  HoloIndex consistently returned the correct WSPs and *adjacent* docs/tests, but the exact runtime `.py` candidate files named in the spec did not surface in the top hits. All verdicts below are anchored on direct reads, not retrieval.

---

## 2. Verdict Table

For each proposed component: KEEP_NEW / FOLD_INTO(owner) / REJECT. Verified against direct reads (file:line evidence in `WAE_LAYER_SPECS.md`).

| # | Component | Verdict | Existing owner / rationale |
|---|-----------|---------|----------------------------|
| 1 | **Architect** | **FOLD_INTO** ImprovementJob / recursive_improvement / daemon_self_audit observe-propose path | Contract already exists: `improvement_job_contract.py` (PENDING, `dry_run=True` default, MEDIUM/HIGH -> architect review). Module `recursive_improvement/` exists. **Gap**: `execute_improvement` (`openclaw_execution_routes.py:865`) classifies + advises only; it does NOT yet emit `ImprovementJob`. No new DAE needed  -  wire the existing contract. |
| 2 | **Researcher** | **FOLD_INTO** existing research adapter path | `pqn_research_adapter.py` exists and is routed via `execute_research` (`openclaw_execution_routes.py:702`, route `pqn_research_adapter`). External-source / web research beyond PQN is an **adapter gap**, not a new DAE. |
| 3 | **Governor** | **REJECT** new DAE; **FOLD_INTO** WSP governance + `destructive_action_guard.py` + `capability_token_validator.py` | Both guards already implement fail-closed enforcement (D0-D6 classes; D4+ requires human approval; D4/D5/D6 BLOCKED Phase 1; token fail-closed on missing/expired/wrong-audience). Governor = these primitives + WSP, not a new component. |
| 4 | **Dispatcher** | **REJECT** new DAE; **FOLD_INTO** OpenClaw (intent) + Hermes (delegation scaffold) + WRE Skillz (capability) | Dispatch already exists across `openclaw_execution_routes.py` (`route_execution`), `hermes_job_executor.py` (`build_delegation_request` / `execute`), and `WRESkillsLoader` / `SkillSelector`. Adding a Dispatcher DAE would be a 6th competing orchestrator. |
| 5 | **Autonomous Approval Authority** | **REJECT** | Merge / promotion authority remains **012 / DAO**. Code-side merge-on-consensus is forbidden. NOTE: a real, conflicting auto-promotion already exists in `wre_master_orchestrator.py:1147-1171` (auto-promotes A/B variations with NO 012/DAO deference)  -  flagged as a remediation target, NOT a precedent to extend. |

---

## 3. Layer Specs (L0-L4) Summary

Full per-layer spec (objective / owner / candidate files / invariant / pass-fail test / WSP_97 truth boundary / stop condition) is in `WAE_LAYER_SPECS.md`. Summary:

| Layer | Objective | Owner | Status of precondition |
|-------|-----------|-------|------------------------|
| **L0** | Close #737 FOUNDUP permission/genesis bypass *before* any autonomy | OpenClaw | **NOT FULLY CLOSED**  -  genesis gate covers the main path, but `execute_foundup` (`openclaw_execution_routes.py:682-690`) has an `ImportError` fallback that calls `handle_fam_intent` directly, bypassing the gate. |
| **L1** | Observe-and-propose loop emits `ImprovementJob(PENDING, dry_run=True)`, no execution | WRE recursive_improvement + ImprovementJob | **GAP**  -  `daemon_self_audit_loop.py` currently *executes* allowlisted auto-fixes and does NOT emit ImprovementJob; `execute_improvement` advises only. |
| **L2** | Hard verifier + diversity retention + Goodhart stop in pattern memory | `pattern_memory.py` | **PARTIAL**  -  diversity (A/B) PRESENT; hard verifier ABSENT; Goodhart-stop ABSENT. |
| **L3** | Heterogeneous judge panel routed to escalations, **NOT Fusion** | Sentinels / escalations | **CONSTRAINT CONFIRMED**  -  Fusion redaction gate BLOCKs `private_reasoning`, `source_authority`, `governance_instruction` (`fusion_redaction_gate.py:128/140/147`). Governance content cannot flow through Fusion. |
| **L4** | Deterministic gate-ordering coordinator, no authority of its own | thin coordinator over existing gates | DESIGN  -  orders L0 policy -> token -> destructive-guard -> verifier; owns ordering only, never approval. |

---

## 4. Critical-Constraint Compliance

- **#737 NOT claimed closed.** Direct evidence: main launch/onboard path is genesis-gated (`openclaw_foundup_orchestrator.py:873-881`), but the `ImportError` fallback at `openclaw_execution_routes.py:682-690` is a residual ungated reach to `fam_adapter.handle_fam_intent`. Marked NEEDS_VERIFICATION. L0 must close this before any L1 autonomy.
- **Governance judge panel NOT routed through Fusion.** Confirmed Fusion redaction gate fails closed on governance categories.
- **No merge-on-consensus proposed.** 012/DAO retains merge authority. Existing `wre_master_orchestrator` auto-promotion flagged as remediation target.
- **RedDog NOT a new always-on daemon.** RedDog = coordinating intelligence / architect surface; WRE/OpenClaw/Hermes own execution.

---

## 5. WSP_97 Truth Boundary Table

| Boundary | Held | Evidence |
|----------|------|----------|
| DECISION_ONLY | YES | Only `docs/audits/architecture/*` changed. |
| NO_CODE_MUTATION | YES | Zero src/ diffs (validation in the completion report). |
| NO_NEW_ORCHESTRATOR | YES | All 5 components FOLD_INTO/REJECT; none KEEP_NEW as orchestrator. |
| NO_MERGE_AUTHORITY_CODE | YES | Autonomous Approval Authority REJECTED; 012/DAO retains merge. |
| REDDOG_NOT_DAEMON | YES | RedDog is architect/coordination surface, not an always-on loop. |
| OPENCLAW_RETAINS_POLICY | YES | OpenClaw owns intent + permission gate (`openclaw_permission_policy.py`). |
| WRE_RETAINS_REPO_AUTHORITY | YES | WRE owns dispatch/verify/repo; Hermes is scaffold-only. |
| HERMES_RETAINS_EXECUTION_SCAFFOLD | YES | `hermes_job_executor.py` is a seam; real delegation BLOCKED Phase 1. |
| FUSION_NOT_GOVERNANCE_JUDGE | YES | Redaction gate BLOCKs governance content (`fusion_redaction_gate.py:128/140/147`). |
| L0_REQUIRED_BEFORE_AUTONOMY | YES | L1+ gated on L0 (#737) closure; L0 NOT yet fully closed. |
| L1_OBSERVE_PROPOSE_ONLY | YES | L1 emits PENDING dry_run jobs; no execution. |
| HARD_VERIFIER_REQUIRED | YES | L2 verifier ABSENT today -> required before any stored pattern drives action. |

---

## 6. Residual NEEDS_VERIFICATION

1. **#737 ImportError fallback** (`openclaw_execution_routes.py:682-690`)  -  confirm whether the fallback can be reached in production (is the orchestrator import ever unavailable at runtime?) and gate it.
2. **WREMaster auto-promotion** (`wre_master_orchestrator.py:1147-1171`)  -  confirm scope; reconcile with 012/DAO authority boundary (does it promote *skill variations* only, or anything reaching merge?).
3. **Competing orchestrators**  -  5-8 orchestrators not yet converted to WSP 65 plugins; concurrency-race risk noted in prior `multi_agent_evolution_audit`. Out of scope here; do not construct a new layer over them.
4. **L1 emission wiring**  -  `execute_improvement` + `daemon_self_audit_loop` do not yet emit `ImprovementJob`; verify the contract's constructors before wiring.

---

*WAE-AR1 decision-only. Stop at PR-ready. Do not merge without explicit docs land token.*
