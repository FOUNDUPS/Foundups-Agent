# REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_AUDIT_PHASE1

**Type:** Audit / contract recommendation ONLY. No code implemented. #925 NOT modified. No live write. No PR opened by this slice.
**Author:** 0102 (RedDog Architect) | Commander: 012
**WSP:** 00, 15, 50, 97 (method); governing protocols enumerated below.
**Base:** `4094ed58e` (main; #925 merged implementation-only).
**Date:** 2026-07-05

---

## 0. Question

Does the FoundUp live-writer work from #925 contain a reusable **generic write spine** that should be separated from FoundUp-specific policy, and if so, is now the time to extract it? Answered with WSP_97 CoT (retrieve-before-stating) + CoR (5-lens adversarial dialectic sweep). Nothing is assumed correct.

## 1. WSP governing protocols found (WSP preflight)

Retrieved from `WSP_framework/src/WSP_MASTER_INDEX.md`. This work is **governed, not ungoverned**:

| WSP | Role in this work |
|-----|-------------------|
| **WSP 97** | System Execution Prompting -- the AGENTIC ACTIVATION OPERATOR LOOP ("retrieve governing WSP -> evidence -> research -> dialectic sweep -> execute"). This IS the "am I following WSP" loop 012 wants RedDog to run. |
| **WSP 48** | Recursive Self-Improvement -- the "is this loop efficient / can it be improved" half. |
| **WSP 67** | Recursive Anticipation -- the "what is missing from this loop" half. |
| **WSP 46 / 54 / 41** | WRE core architecture / agent duties / simulation -- the engine the writer would plug into. |
| **WSP 66 / 33 / 49 / 104** | Proactive module creation / autonomous module implementation / module structure / id namespace -- govern a GENERIC proactive write-create capability. |
| **WSP 96 / 100** | MCP Governance & Consensus / DAE-SmartDAO escalation -- govern the "only on consensus, 012 out of the loop" substitute for human authority. |
| **WSP 95** | Skillz Wardrobe -- governs task-specific execution skills IF the generic writer is later wrapped as a Skill. |
| **WSP 109** | FoundUp Onboarding Intake -- where FoundUp-specificity legitimately lives (id shape, intake, manifest). |
| **WSP 64** | Violation Prevention -- prefer ENHANCING existing WSP over minting a new one. |

**Governance verdict:** the mapping is SOUND as a design target. A NEW WSP is NOT warranted (WSP 64); the gap is a *binding* -- extend WSP 97 with a "RedDog autonomous operator loop" subsection -- not a new protocol.

## 2. Direct-read evidence summary

All 7 required targets present (none `NEEDS_VERIFICATION`):

- `foundup_scaffold_writer_live.py` (410 lines) -- OBSERVED: 9 authorization guards; 8 SPINE couplings, ~5 FoundUp POLICY couplings (see table).
- `worktree_pr_runner.py` (101 lines) -- OBSERVED: performs NO authorization; contains ZERO FoundUp token; already fully generic. Only FoundUp string is the commit-message text built by the *orchestration*, not the runner.
- `live_writer_preauth_packet.py` -- OBSERVED: docstring claims a "GENERIC layer" but the sibling writer welds to `create_foundup` (docstring-vs-code drift).
- `scaffold_writer_dryrun.py` -- OBSERVED: `_content_for` (lines 130-171) hard-codes FoundUp WSP-49 content templates and returns `''` for anything outside the FoundUp set -> a generic caller would silently emit empty files.
- `reddog_wre_execution_valve.py` -- OBSERVED: `_resolve_valve_state` (line 300) keys only off `valve_worktree_create_enabled` + `sovereign_worktree_token`; the FULL `evaluate_reddog_execution_valve` (line 319) runs `_validate_spine_chain` + `_validate_intake_and_launch` and emits `decision_digest` + `rejection_reasons`. `CANONICAL_INTAKE_TARGETS` already admits a NON-FoundUp `autonomous_task`.
- `docs/audits/architecture/FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md` -- OBSERVED present (#921 decision doc).
- `WSP_framework/src/WSP_MASTER_INDEX.md` -- OBSERVED present.

## 3. Generic-vs-FoundUp coupling table

`WSP_97 label` = truth boundary (OBSERVED / INFERRED / SPECIFIED_NOT_IMPLEMENTED).

| Component | Generic spine | FoundUp policy | Mixed | Evidence | WSP_97 label |
|-----------|:---:|:---:|:---:|----------|--------------|
| isolated worktree | X | | | `foundup_scaffold_writer_live.py:263-293` (Guard 8: absolute, device-prefix, root-union, `_is_inside`) | OBSERVED |
| preauth digest binding | X | | | `:201-204` (Guard 2 recompute+compare) | OBSERVED |
| sovereign token | X | | | `:226-230` (Guard 6 `token==env_token`). Mechanism generic; **plaintext string-equality**, no signature/TTL/nonce | OBSERVED (weak: crypto = SPECIFIED_NOT_IMPLEMENTED) |
| receipt chain | X | | | `:154-157` ledger + per-guard `_receipt` | OBSERVED |
| draft PR only | X | | | `worktree_pr_runner.py:89-98` (`gh pr create --draft`; no ready/merge method) | OBSERVED |
| allowed_paths / denied_paths | | | X | Mechanism generic (`:214-218`); **values FoundUp-tuned** (`_HARD_DENIED_MARKERS :51-54` includes `foundup_registry.json`) | OBSERVED |
| modules/foundups/{id} path | | X | | `:209` `module_path = f"modules/foundups/{fid}"`; re-derived, not caller-trusted | OBSERVED |
| WSP-49 14 artifact set | | X | | `create_foundup_dryrun.py` `_wsp49_artifacts`; re-enforced `scaffold_writer_dryrun.py:294-301` | OBSERVED |
| foundup_manifest draft / registry seed | | X | | `scaffold_writer_dryrun.py:130-171` content templates; registry seed shape | OBSERVED |
| pAccess fixture | | X | | tests only (`test_foundup_scaffold_writer_live.py`) | OBSERVED |
| create_foundup action | | X | | `:46` `REQUESTED_OPERATION`; `:189-190` | OBSERVED |
| branch naming | X | | | `:295-298` (Guard 9 `feat/*`, reject main/master/base). Default `feat/foundup-live-writer-{fid}` is Mixed | OBSERVED |
| worktree cleanup | X | | | `_reject` -> `runner.cleanup_worktree` `:174-180` | OBSERVED |
| PR merge prohibition | X | | | runner exposes no `ready`/`merge`; `test_real_runner_create_draft_pr_only` | OBSERVED |

**Tally:** ~8 SPINE / ~5 POLICY couplings (roughly 60-65% spine by count; spine dominates by line count). **Seam:** the generic primitive ends at (a) `module_path = f"modules/foundups/{fid}"` (`:209`) and (b) the `materialize_scaffold_dry_run(scaffold_contract, ...)` call (`:344`). Everything else -- valve, token, worktree isolation, digests, branch guard, receipts, cleanup -- is a generic "author a scoped change in an isolated worktree and open a draft PR" primitive. **Reuse today is copy-not-call** (3 constants + 1 import must be edited to retarget).

## 4. Safety risks of genericizing (adversarial)

The CoR sweep's sharpest finding: **the `modules/foundups/{id}` pin is not one guard to loosen; it is the derivation invariant that gives every other guard its meaning.** Genericizing naively DELETES containment rather than widening it.

| Sev | Risk | Precondition it forces |
|-----|------|------------------------|
| **BLOCKER** | Replacing the re-derived `modules/foundups/{id}` root with a caller-supplied `allowed_paths` collapses 4 independent recomputations into 1 caller-trusted value. Blast radius: any agent writes anywhere (WSP_framework, .github/workflows, any module). | A generic writer must **re-derive** its authorized root from a *signed request*, never read it from the caller packet; add a per-domain canonical-root function analogous to `modules/foundups/{id}`. |
| **BLOCKER** | Writer authorizes on `_resolve_valve_state(env, [])` (`:234`) -- an env-flag read with EMPTY reasons that SKIPS the full gated spine (policy / receipt / invocation / executor / intake / permission). Latent today; a self-authorization vector the moment 012 leaves the loop. | Bind the writer to a fully-evaluated, signed `ExecutionValveDecision` (`evaluate_reddog_execution_valve`, verify `decision_digest` + `rejection_reasons==[]`). |
| **MAJOR** | Sovereign token is plaintext string-equality, no signature/TTL/identity. Whoever assembles env+packet satisfies it. | DAO/012-signed, TTL-bound, nonce'd token before 012-out-of-loop. |
| **MAJOR** | `_HARD_DENIED_MARKERS` omits self-authorization surfaces: `.github/workflows/**`, `settings.json`, the valve/gate/preauth source modules, holo_index config. A writer reaching these can rewrite its own authorization or CI. | Pin-INDEPENDENT governance/CI denylist so a writer can never edit its own authority. |
| **MAJOR** | No consensus / multi-signer enforcement exists in code; a single self-approving agent satisfies the entire chain. | N-of-M independent signatures (WSP 96) as the substitute for 012 before continuous operation. |
| MINOR | `_content_for` returns `''` outside the FoundUp set -> generic writer emits empty files; artifact-set exactness is FoundUp-only. | Per-domain content-emit + relaxed/kept exact-set check. |

## 5. Should #925 change before it is considered done?

**No -- keep #925 as-is for the first live FoundUp test.** The two blockers above are blockers for **genericization and for 012-out-of-loop continuous operation**, NOT for #925's actual scope, because #925 is: draft-PR-only + invoked directly with a 012-supplied sovereign token + human-reviewed + hard-pinned to `modules/foundups/{id}`. In that scope the token IS 012's authority and the draft-only human review is the backstop; the un-called spine-chain gates concern the *autonomous work-order pipeline* that #925 is not wired into. Changing #925 now would violate 012's "prove the narrow writer first" discipline. The valve-binding and token-hardening are **contract preconditions**, recorded here, to be closed **before** any generic writer or continuous run -- not retrofitted into the first test.

(If 012 wants belt-and-braces, binding #925 to `evaluate_reddog_execution_valve` is a small, safe, optional hardening -- but it is NOT required for the first test and is better sequenced into the contract slice.)

## 6. Verdict + recommended next slice

**Verdict: `KEEP_FOUNDUP_SPECIFIC_FOR_NOW` + `EXTRACT_GENERIC_SPINE_CONTRACT_NEXT` (sequenced).**

1. Keep #925 FoundUp-specific; run the first live pAccess test via its own separate authorization packet (`RUN_LIVE_WRITER_PACCESS_001_PHASE1`).
2. AFTER #925 proves safe live, author **`REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1`** -- a decision/contract-only doc (no code) that specifies the generic `agent_worktree_writer`: injected domain profile (`operation`, `id_validator`, `canonical_root_fn`, `materialize(contract,out_root,repo)`, `allowed/denied` as data), the re-derive-root invariant, the full-valve-decision binding, the signed-token upgrade, the pin-independent governance/CI denylist, and a mandatory `consensus_receipt_digest` guard.
3. Do NOT implement the generic writer until that contract lands. Then build layer-by-layer, dry-run/closed-by-default: (a) repo-write consensus receipt (dry-run), (b) generic `CapabilityWriteEnvelope` de-welding preauth/valve/writer + consensus guard, (c) WSP-ask + WSP-48/67 self-interrogation receipt producers, (d) spin-up edge from OpenClaw to the actuator gated on the consensus receipt.

Terminal state stays **draft-PR-only**; encode one positive invariant: **promotion requires 0102-architect WSP_97 evidence OR a DAO vote -- never the loop itself.**

## 7. HoloIndex results

Queries run against the post-#925 index (7 queries, top code hits shown). **INDEX_GAP CONFIRMED:** neither the generic-spine concept, nor the #925 writer/runner modules, nor the valve sovereign-token surface.

| # | Query | Top code hits | Verdict |
|---|-------|---------------|---------|
| 1 | generic agent worktree writer | `sub_agent_coordinator.py`, `simulator/agents/base_agent.py`, `agent_work_batcher/executor.py` | GAP -- no generic write spine |
| 2 | RedDog worktree write spine | `reddog_wre_executor_dryrun.py`, `reddog_openclaw_adapter_dryrun.py`, `reddog_governed_work_order_dryrun.py` | Partial -- pre-#925 RedDog spine surfaces; the #925 WRITER does not |
| 3 | WSP 48 recursive self improvement writer | `dae_sub_agents/improvement/wsp48_improver.py`, `wre_sdk_implementation.py`, `theorist_dae_poc.py` | Relevant -- `wsp48_improver.py` exists (a self-improve module to reuse) |
| 4 | WRE isolated worktree writer | `reddog_wre_executor_dryrun.py`, `test_reddog_wre_execution_valve.py`, `gotjunk/adapters/wre_adapter.py` | GAP -- #925 writer absent |
| 5 | sovereign token worktree valve | `simulator/economics/token_economics.py`, `pool_distribution.py`, `dae_envelope_system.py` | GAP -- `reddog_wre_execution_valve.py` (the actual sovereign-token valve) NOT discoverable |
| 6 | FoundUp scaffold writer live | `test_foundup_scaffold_contract_phase1.py`, `foundups_livechat_module.py`, `main.py` | GAP -- `foundup_scaffold_writer_live.py` NOT indexed |
| 7 | agent_worktree_writer | `simulator/agents/founder_agent.py`, `user_agent.py`, `base_agent.py` | GAP -- concept does not exist / not discoverable |

**Reusable asset surfaced:** `modules/infrastructure/dae_components/dae_sub_agents/improvement/wsp48_improver.py` (Q3) is a candidate WSP-48 self-interrogation producer for the future loop -- audit before reuse (WSP 50/84).
**INDEX_GAP:** `HOLOINDEX_FOUNDUP_SCAFFOLD_WRITER_LIVE_DISCOVERABILITY_PHASE1` -- operator/worker re-index closes both the #925 modules and the generic-spine vocabulary. **Never RedDog runtime; no ranking-code changes** (both explicitly out of scope for this slice).

## 8. Residual SPECIFIED_NOT_IMPLEMENTED

- **RedDog active WSP derivation:** RedDog starting each task by asking the WSP index / HoloIndex "which WSP governs this / am I following WSP" is NOT in code. `reddog_governed_work_order_dryrun.py:414-417` only *validates* caller-attached `applicable_wsps`; it never *derives* them. If human-0102 is removed from the loop, the governing-WSP derivation disappears and the gate degenerates to "was a non-empty list supplied." -> `REDDOG_OPERATOR_LOOP_WSP97_BINDING_PHASE1` (extend WSP 97; decision-only first).
- **WSP 48/67 self-interrogation** ("is this loop efficient / improvable / what is missing"): zero representation in any read module.
- **WSP 96 consensus gate** (N-of-M independent signatures substituting for 012): absent; valve opens on one static token + env flag. WSP 96 itself is Draft/Phase-0.1 and must be promoted before wiring 012-out-of-loop.
- **Generic capability envelope** (de-welding create_foundup / modules/foundups/{id}): absent -- no FIX/RESEARCH/ENHANCE write is expressible today.
- **Spin-up edge:** the writer is an ORPHAN leaf with no caller; the OpenClaw improvement loop never reaches it. OpenClaw IMPROVEMENT intent is advisory-only (no-repair truth boundary).
- **Positive promotion authority:** draft-only denial is enforced ad hoc; the positive rule ("who may promote") is unencoded.
- **Signed/TTL sovereign token + pin-independent governance/CI denylist:** both absent (see section 4).
- **HoloIndex discoverability:** the generic-spine concept and the #925 modules are not indexed -> INDEX_GAP `HOLOINDEX_FOUNDUP_SCAFFOLD_WRITER_LIVE_DISCOVERABILITY_PHASE1` (operator re-index; never RedDog runtime).

---

*Hard safety rule (restated): GENERIC DOES NOT MEAN UNBOUNDED. Any future generic writer MUST still require explicit allowed_paths + explicit denied_paths + no protected branch + no WSP-framework mutation unless separately authorized + no CI/security-config mutation unless separately authorized + no secrets access + no registry/public/API mutation unless separately authorized + consensus or sovereign token by authority tier + receipts on BOTH accept and reject + draft-PR-only unless a later merge gate approves.*
