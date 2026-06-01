# HXA26_HXA27_DEFENSE_PRIMITIVES_REDUNDANCY_AUDIT_PHASE1

**Slice:** HXA26_HXA27_DEFENSE_PRIMITIVES_REDUNDANCY_AUDIT_PHASE1
**Worker-Lane:** W6
**Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY security/architecture audit. No code, tests, cherry-pick, or worktree mutation.

---

## 1. Mission and Scope

PR #742 flagged four HXA worktrees for architectural disposition; PR #743 cleared HXA29's
scope-to-action concern (enforced live via HXA30 Gate 13, #576). **Remaining question:** do
the stranded HXA26/HXA27 defense-in-depth primitives contain useful security behaviour
**not present in current main** (`origin/main` @ `e8715387d`, after #743)?

Focus primitives: (1) NonceRegistry / replay protection, (2) fail-closed DI
SignatureVerifier, (3) HXA27 token validation / Hermes integration variants, (4) any other
defense primitive present in the stranded trees but absent from main.

Scope: exactly one file (this audit). All four worktrees were read only (`git -C <path>`
status/log/diff/show + `rg`); none was edited, removed, unlocked, or had its branch deleted.

---

## 2. Predecessor Citations

| PR | Slice | Relationship |
|----|-------|--------------|
| #742 | WORKTREE_STRANDED_WORK_TRIAGE_PHASE1 | Flagged the 4 HXA worktrees for disposition |
| #743 | HXA29_SCOPE_ACTION_VALIDATION_ENFORCEMENT_AUDIT_PHASE1 | Cleared HXA29 scope concern (precedent for security-clear) |
| #576 | HXA30 scope-to-action-class enforcement into Hermes | Boundary context (Gate 13 live enforcement) |

Also relevant (merged, verified ancestors of `origin/main`): **#570** (HXA25 D3 sandbox) and
**#571** (HXA26 capability token validation service).

---

## 3. Current Main Security-Primitive Map

`rg` over `modules/infrastructure/wre_core`, `modules/foundups`, `modules/communication`
(`*.py`). Main already ships a complete HXA capability-token stack:

| Primitive (in main) | Location | Evidence |
|---------------------|----------|----------|
| Capability token validator (HXA26 #571) | `wre_core/src/capability_token_validator.py` | `LocalCapabilityTokenValidator`, 10 gates (Gate 1-10) |
| Nonce / replay protection | same file | `used_nonces: Set[str]` (L407), `register_nonce` (L409), **Gate 8 nonce replay** (L519-531), `replay_detected` (L289) |
| Signature gate (Phase-1 boolean) | same file | Gate 2 missing signature (L475), **Gate 3 `signature_verified`** (L483); explicitly "does NOT perform real signature verification in Phase 1" (L465) |
| Scope/action fail-closed | same file | "Unknown scopes fail closed (return False)" (L789) |
| HXA27 Hermes token-validation integration | `wre_core/src/hermes_job_executor.py` | imports `LocalCapabilityTokenValidator` (L68), `token_validator` ctor param (L560), `_extract_capability_token` / `_validate_token_if_present` (L1254), `_build_token_blocked_result`, `token_validation_performed/result` fields (L469-471), validation-before-guard |
| Destructive-action fail-closed guard | `wre_core/src/destructive_action_guard.py` | "fail-closed validation" (L6, L26, L923) |

Main also contains the merged HXA test family: `test_hxa26_token_validation_service.py`,
`test_hxa27_hermes_token_validation_integration.py`, `test_hxa29_token_scope_validation.py`,
`test_hxa30_scope_to_action_class_integration.py`.

---

## 4. Stranded HXA26/HXA27 Worktree Inventory

| Worktree | HEAD | Branch | Dirty | Nature |
|----------|------|--------|-------|--------|
| `agent-a5d1278fb48536509` | `e8caaefc1` (HXA25 #570) | `worktree-agent-a5d1278…` | 5 | HXA26 token-validator (DI variant) |
| `agent-a7eb1c4ac8465b49f` | `0c01a268a` (HXA26 #571) | `feat/hxa27-hermes-token-validation-integration` | 5 | HXA27 hermes (early draft) |
| `agent-ab7fd78b358b1cff2` | `0c01a268a` (HXA26 #571) | `feat/hxa27-hermes-token-validation-integration` | 2 | HXA27 (same commit as a7eb1c4; subset of dirty files) |
| `agent-a38c0fe37c0231091` | `50ac3dc11` (HXA27 integration) | `worktree-agent-a38c0fe…` | 0 | HXA27 HermesJobExecutor integration (committed) |

**Ancestry (verified `git merge-base --is-ancestor`):** HXA25 `e8caaefc1` → **IN main**; HXA26
`0c01a268a` → **IN main**; HXA27 `50ac3dc11` → **NOT in main** (but its content is present —
see §8).

Dirty files of interest: a5d1278 → `capability_token_validator.py` (untracked, DI variant) +
`test_hxa26…` + `HXA26_TOKEN_VALIDATION_SERVICE.md`; a7eb1c4/ab7fd78 → `hermes_job_executor.py`
(modified) + `test_hxa27…` (untracked).

---

## 5. Primitive Comparison Matrix

| Primitive | In main? | In stranded? | Classification |
|-----------|----------|--------------|----------------|
| Nonce replay protection (Gate 8 + `used_nonces`) | YES | YES (a5d1278) | **ALREADY_IN_MAIN** |
| `NonceRegistry` Protocol + `InMemoryNonceRegistry` (DI) | NO (main uses inline `used_nonces`) | YES (a5d1278 L566-602) | **SUPERSEDED_BY_MAIN** (DI refactor of equivalent behaviour) |
| Signature gate (boolean `signature_verified`) | YES (Gate 3) | YES | **ALREADY_IN_MAIN** |
| Fail-closed DI `SignatureVerifier` (Gate 0 verifier-must-be-injected + Gate 4 real verify) | **NO** | YES (a5d1278 L511/L153/L702/L742) | **ABSENT_AND_USEFUL** (Phase-2 hardening; no Phase-1 security delta) |
| HXA27 Hermes token-validation integration | YES (`hermes_job_executor.py`) | YES (a38c0fe, a7eb1c4) | **ALREADY_IN_MAIN** |

**Primitives compared: 5.**

---

## 6. Replay Protection Analysis (Q1)

**Does main provide replay protection equivalent to NonceRegistry? — YES.**
`capability_token_validator.py` holds `used_nonces: Set[str]` (L407); **Gate 8** rejects a
reused nonce (`token.nonce in self.used_nonces → replay_detected=True`, L519-531) and
registers the nonce only after all gates pass (L619-620). The stranded a5d1278 expresses the
same behaviour through a `NonceRegistry` Protocol + `InMemoryNonceRegistry`
(`is_used`/`mark_used`, L566-602) — a **dependency-injection refactor**, not new security
behaviour. Replay protection is **ALREADY_IN_MAIN**; the DI form is **SUPERSEDED_BY_MAIN**.

---

## 7. Signature Verification Fail-Closed Analysis (Q2)

**Does main fail closed when signature verification deps are absent/misconfigured? — Partially.**
- Main fails **closed on the boolean**: Gate 2 (missing signature → invalid) and Gate 3
  (`signature_verified=False` → invalid). But main performs **no real verification** in Phase 1
  ("does NOT perform real signature verification", L465) and has **no injected verifier
  dependency** — so the failure mode "verifier absent/misconfigured" does not exist in main's
  design.
- The stranded a5d1278 adds a **fail-closed DI `SignatureVerifier`**: a `SignatureVerifier(Protocol)`
  (L511) with a default that fails closed ("No signature verifier injected (fail-closed)",
  L153/L541), **Gate 0 "check verifier is injected"** (L702), and **Gate 4 real verify** (L742).

This DI fail-closed verifier is **ABSENT_AND_USEFUL** — but with an important truth-boundary
caveat: **both** sides are Phase-1 test-only (WSP 97: "No real secrets, no real signing"), so it
introduces **no Phase-1 security delta**. It is a cleaner architecture for Phase-2 real signing,
not a fix for a current vulnerability. → **SALVAGE_PRIMITIVE_TO_REMEDIATION** (engineering).

---

## 8. Hermes Token-Validation Integration Analysis (Q3)

**Does main validate capability tokens through Hermes in the same places as the HXA27 variants? — YES.**
`hermes_job_executor.py` on main contains the full HXA27 integration named in a38c0fe's commit
`50ac3dc11`: `token_validator` ctor param (L560, "default to singleton" L587),
`_extract_capability_token`, `_validate_token_if_present` (L1254), `_build_token_blocked_result`,
`token_validation_performed/result` fields (L469-471, L514-516), HXA27 blocked states (L306),
and validation invoked before the destructive-action guard. The committed a38c0fe HXA27 test
differs from main's merged `test_hxa27_hermes_token_validation_integration.py` by only **5
lines** (≈ the merged version); a7eb1c4's untracked draft differs by **1317 lines** (an older,
divergent draft). HXA27 integration is **ALREADY_IN_MAIN**; the stranded variants are
superseded/divergent drafts.

---

## 9. Per-Worktree Disposition Recommendation

| Worktree | Disposition | Rationale |
|----------|-------------|-----------|
| `agent-a5d1278…` (HXA26 DI) | **REMOVE_CANDIDATE_SECURITY_CLEAR** + **SALVAGE_PRIMITIVE_TO_REMEDIATION** | HXA26 merged via #571 (canonical, boolean design); the DI `SignatureVerifier`/`NonceRegistry` pattern is the only non-redundant content → salvage it (this audit captures it) before removal. Pending final file-level retirement check. |
| `agent-a7eb1c4…` (HXA27 draft) | **REMOVE_CANDIDATE_SECURITY_CLEAR** | HXA27 integration is in main; this is an older draft (1317-line test drift). Pending final file-level retirement check. |
| `agent-ab7fd78…` (HXA27, same commit) | **REMOVE_CANDIDATE_SECURITY_CLEAR** | Same commit `0c01a268a` as a7eb1c4 on the same branch; a strict subset. No unique security content. |
| `agent-a38c0fe…` (HXA27 integration) | **REMOVE_CANDIDATE_SECURITY_CLEAR** | Integration present in main; test ≈ main (5-line drift). Superseded. |

**Counts:** REMOVE_CANDIDATE_SECURITY_CLEAR = **4**; SALVAGE_PRIMITIVE_TO_REMEDIATION = **1**
(the DI fail-closed SignatureVerifier + NonceRegistry pattern); ARCHITECT_DECISION_REQUIRED =
**0** (no product/strategy/economic choice surfaced — pure engineering disposition; **not** 012's
call per the dispatch).

---

## 10. Security Impact

- **No current security regression** would result from removing these worktrees: their replay
  protection and HXA27 Hermes integration are already in main, and their signature handling is
  Phase-1-equivalent to main's.
- **One latent hardening** is captured for Phase 2: main's signature gate trusts a
  `signature_verified` boolean set by the (test) issuer; when real signing arrives, the stranded
  DI `SignatureVerifier` (Gate 0 verifier-required + Gate 4 real verify, fail-closed) is the
  stronger pattern. Documenting it here means the worktrees can be retired without losing it.
- Removal itself is out of scope (NO_WORKTREE_REMOVAL); this audit only classifies.

---

## 11. Recommended Next Slice

**`HXA_DI_FAILCLOSED_SIGNATURE_VERIFIER_SALVAGE_PHASE1`** — salvage the DI fail-closed
`SignatureVerifier` (+ optional `NonceRegistry` Protocol) pattern from a5d1278 into main's
`capability_token_validator.py` as a Phase-2-ready hardening (engineering; gated on whether/when
real token signing is introduced). The four worktree retirements themselves are a follow-on
worktree-cleanup slice after the file-level retirement check — not part of this read-only audit.

---

## 12. Internal Review Verdict

**READY.** All six dispatch questions are answered with `file:line`/ancestry evidence: main
provides replay protection (Q1) and Hermes token validation (Q3); main fails closed on the
signature boolean but lacks the DI verifier-absent fail-close (Q2); the stranded primitives are
classified (Q4); all four worktrees are REMOVE_CANDIDATE_SECURITY_CLEAR (Q5); one primitive —
the DI fail-closed SignatureVerifier — is SALVAGE_PRIMITIVE_TO_REMEDIATION (Q6). Only the
approved disposition terms are used; no 012 ruling is requested (engineering only). No worktree
was mutated, unlocked, removed, or had its branch deleted.

---

## 13. WSP_97 Truth Boundary Checklist

Declared count: **18 / 18 YES** (rows below = 18).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_SECURITY_AUDIT | YES | Only this audit doc written |
| 2 | NO_CODE_CHANGE | YES | No `.py` modified (git clean on src trees) |
| 3 | NO_TEST_CHANGE | YES | No test files modified |
| 4 | NO_CHERRY_PICK | YES | No `git cherry-pick` run |
| 5 | NO_STRANDED_WORK_MUTATION | YES | Worktrees read via `git -C` status/log/diff/show + `rg` only |
| 6 | NO_BRANCH_DELETE | YES | No branch deleted |
| 7 | NO_WORKTREE_REMOVAL | YES | All 4 worktrees remain locked and intact |
| 8 | HXA26_HXA27_PROTECTED_DURING_AUDIT | YES | No edit/unlock/remove of any HXA worktree |
| 9 | NO_012_RULING_FOR_ENGINEERING_DISPOSITION | YES | §9 ARCHITECT_DECISION_REQUIRED=0; no NEEDS_012_RULING used |
| 10 | CITES_PR_742 | YES | §1, §2 cite #742 |
| 11 | CITES_PR_743 | YES | §1, §2 cite #743 |
| 12 | NO_CABR_READY | YES | No CABR touched |
| 13 | NO_PAYOUT_READY | YES | No payout touched |
| 14 | NO_DAO_ACTIVATION | YES | No DAO activation |
| 15 | FOUR_WORKTREES_AUDITED | YES | §4, §9 cover a5d1278 / a7eb1c4 / ab7fd78 / a38c0fe |
| 16 | DISPOSITION_TERMS_ONLY | YES | Only the 5 approved terms used (§9) |
| 17 | ANCESTRY_VERIFIED | YES | §4 `merge-base --is-ancestor`: #570/#571 in main, 50ac3dc11 not |
| 18 | EVIDENCE_FILE_LINE_CITED | YES | file:line citations throughout §3, §6-8 |

**WSP 97 Truth Boundary Checklist: 18/18 YES.**

---

## Addendum — PolicyFlags Write-Back Seam Found During Adversarial Review

This audit remains valid for HXA26/HXA27 stranded-work disposition, but adversarial review
(an independent multi-agent re-audit) found a mainline seam **not covered by the original
primitive matrix (§5)**: inbound `policy_flags` are deserialized from the job payload and read
by the `hermes_job_executor` security/destructive-action gates, while the capability-token
validator verdict is **not written back** before those gates read the flags.

**Verified on `origin/main` @ `e8715387d`:**
- The destructive-action guard's token gate reads four flags **read-only** —
  `policy_flags.capability_token_checked / present / validated / scope_authorized`
  (`hermes_job_executor.py:1134-1137`); these are the *only* references, and there are
  **zero `policy_flags.capability_token_* =` write-backs** anywhere in the executor.
- `security_gate_passed` is likewise taken from the inbound flags (`:1090`).
- `PolicyFlags` fields default `False` and are populated from untrusted job data via `from_dict`
  (`foundup_job_contract.py:226-235`, `:271-274`, job deserialized at `:613`).
- `_validate_token_if_present` (`:1254`) performs validation but does **not** write its
  `TokenValidationResult` into `job.policy_flags`.
- **Consequence:** a tokenless job arriving with `capability_token_*` + `security_gate_passed`
  pre-set `True` clears the guard's token gate with **no validation ever running**.

**Bounded impact (also verified):** D4/D5/D6 are unconditionally blocked in Phase 1, and
`workspace_binding` / `path_constraints` are server-built (`:838`, `:1124-1127`), so the seam is
scoped to **D3_WRITE_SANDBOX**. End-to-end exploitability depends on the job-ingestion trust
boundary, which this audit did **not** trace.

**Effect on disposition:** This does **not** invalidate the removal disposition for the four
stranded worktrees (§9). It **does** mean the `a7eb1c4` validator→`policy_flags` write-back is
not irrelevant — it is the pattern that remediates this seam. Reclassify that write-back as
**`SALVAGE_PATTERN_TO_FOLLOWUP`**: a pattern to re-implement on main's current HXA30 base, **not**
production code to preserve from the worktree (whose draft is stale and likely production-unreachable).

**Follow-up slice:** `HXA_POLICYFLAGS_WRITEBACK_ENFORCEMENT_AUDIT_PHASE1`

Required question:
> Can any untrusted or semi-trusted job ingress pre-set `policy_flags.capability_token_*` or
> `security_gate_passed` such that D3_WRITE_SANDBOX clears without live validation?

Expected remediation shape if confirmed:
> Zero inbound token/security flags before validation, run the validator, write the validator
> verdict into `policy_flags`, then allow the destructive/security gates to read only
> server-authored flags.

*This addendum records a verified caveat surfaced after the original disposition; it does not
expand #744 into remediation (no code). Engineering only — no 012 ruling requested.*

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Read-only comparison of four stranded HXA26/HXA27 worktrees against `origin/main` @ e8715387d.
All four are REMOVE_CANDIDATE_SECURITY_CLEAR; one DI fail-closed SignatureVerifier primitive is
flagged SALVAGE_PRIMITIVE_TO_REMEDIATION. Engineering disposition only — no 012 ruling required.*
