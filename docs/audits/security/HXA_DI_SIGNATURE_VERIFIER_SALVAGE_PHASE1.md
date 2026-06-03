# HXA DI Fail-Closed SignatureVerifier - Salvage Decision (Phase 1)

**Slice:** HXA_DI_SIGNATURE_VERIFIER_SALVAGE_PHASE1
**Worker-Lane:** W6 - **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** DESIGN/CODE DECISION (fork: SALVAGE vs RETIRE). **Verdict: RETIRE / DEFER WITH DESIGN PRESERVED**
- decision-only, NO code change. (Adversarial critic UPHELD, high confidence ~0.9.)
**Base:** origin/main @ ba8dba7c7 (all line numbers re-verified; minor drift noted).

---

## 1. Mission and Scope

Resolve the lone ESCALATE from #758/#759: should the DI fail-closed SignatureVerifier in the parked
`agent-a5d1278` worktree (the only unique un-landed security primitive) be SALVAGED into main now, or
RETIRED/deferred with the design preserved? Let the evidence pick the branch; do not pre-decide; do not
port the worktree wholesale. The a5d1278 worktree is read-only evidence, never modified here.

---

## 2. Predecessors

| Item | Relationship |
|------|--------------|
| #744 HXA26/27 redundancy audit | Classified the DI SignatureVerifier `ABSENT_AND_USEFUL` ("no Phase-1 security delta"; "gated on whether/when real token signing is introduced"); NonceRegistry DI `SUPERSEDED_BY_MAIN` |
| #758 disposition refresh | a5d1278 -> ESCALATE_ENGINEERING_REVIEW ("salvage or abandon; do NOT remove until ruled") |
| #759 removal execution | Removed the 7 allowlisted worktrees; a5d1278 deliberately KEPT (live, locked, head e8caaefc1) - NOT in the #759 backup |

---

## 3. FOLLOW-WSP Evidence (methodology)

- **Occam:** salvage only the minimal non-redundant + Phase-1-safe primitive; default to not porting NonceRegistry.
- **HoloIndex (step 2):** queried `capability token signature verification verifier fail-closed phase 2 real
  signing` (returned matches; #744 is the governing prior audit). Discovery executed via direct read-only
  probes (the appropriate evidence for an absence/regression question).
- **WSP 84:** confirmed main has NO existing verifier abstraction to extend (grep = 0).
- **Probes:** `git grep` for the DI symbols on main; read main's `capability_token_validator.py` (booleans +
  gates + fake issuer); read a5d1278's DI source read-only; broad grep of ROADMAP/ModLog/WSP/docs for a
  Phase-2 real-signing consumer; an independent adversarial critic.

---

## 4. DI Primitive Map (a5d1278 vs main)

| Primitive | a5d1278 (parked) | origin/main @ ba8dba7c7 |
|-----------|------------------|-------------------------|
| `SignatureVerifier` Protocol | present (~L511) | **ABSENT** (grep = 0) |
| `AlwaysRejectVerifier` fail-closed default | present (~L537), Gate 0 `NO_VERIFIER` (L152), Gate 4 `verify(raw_token)` (~L742-749) | **ABSENT** |
| `NonceRegistry` / `InMemoryNonceRegistry` DI | present (~L566/L582) | **REDUNDANT** - inline `used_nonces` (:407), `register_nonce` (:409), Gate 8 (:521-534) |
| Signature handling | verifies against `request.raw_token` | self-asserted booleans `signature_present`/`signature_verified` (:149/:152); issuer FAKES both True (:710-711, "Fake signature"/"Fake verification"); Gate 2/3 reject only on the booleans (~:475/:484) |
| Real signature payload on token | yes (`raw_token`) | **NONE** - main `CapabilityToken` carries no raw_token/signature, only two booleans |

The DI fail-closed verifier is genuinely unique (absent on main). NonceRegistry DI is redundant.

---

## 5. Decision Axes

| Axis | Evidence | Verdict contribution |
|------|----------|----------------------|
| **Uniqueness** | DI verifier absent on main (grep 0 in `*.py`); unique to a5d1278 | Salvage-eligible (it is unique) |
| **Phase-1 value** | Main is fake/boolean signing (docstrings :104/:465/:692 "no real signing"; issuer fakes verified=True). There is no real signature to verify. A fail-closed verifier adds NO Phase-1 defense-in-depth today (per #744: "no Phase-1 security delta") | -> RETIRE (inert today) |
| **Phase-2 need** | NO scheduled real-signing consumer/roadmap. The only signing references are the "Phase 1 does NOT sign" docstrings + #744's conditional "gated on whether/when real signing is introduced". The one HMAC hit (wre_core/ModLog.md) is skill-file integrity, a different subsystem | -> RETIRE (no near-term consumer) |
| **Integration risk** | Main tokens carry no `raw_token`. A default-active `AlwaysRejectVerifier` (or any `verify(raw_token)`) wired into `validate_token()` would reject **100% of current Phase-1 tokens** -> Phase-1 REGRESSION. The only non-regressing shapes (interface-only-not-wired, or optional-disabled-by-default) add **dead architecture inventory** until a real-signing consumer exists | -> RETIRE (wire = regress; scaffold = YAGNI) |
| **NonceRegistry redundancy** | Gate 8 covers both NONCE_MISSING and REPLAY_DETECTED; the DI registry is a pure refactor (#744 SUPERSEDED) | -> do NOT port |

---

## 6. Verdict: RETIRE / DEFER WITH DESIGN PRESERVED

**Reasoning summary:** the DI fail-closed SignatureVerifier is unique and architecturally cleaner FOR A FUTURE
real-signing world - but that world is unscheduled. Salvaging now is one of two bad outcomes: (a) wiring it
active **regresses** Phase-1 (main tokens have no real signature to verify -> every token rejected), or (b)
adding it interface-only / disabled-by-default is **dead inventory** (no production caller, no Phase-1 security
delta) that a future `if/when real signing` slice can trivially recreate. The design is already preserved in
two places (the committed #744 audit prose + the live locked a5d1278 worktree), so RETIRE/DEFER loses nothing.
The NonceRegistry DI is redundant and not ported.

This is NOT a strategic toss-up requiring ESCALATE_ENGINEERING_DECISION: the evidence is clear (no consumer ->
defer). The one engineering/product decision that IS 012's is **whether/when to introduce real capability-token
signing** - and THAT is the trigger to revisit this salvage.

---

## 7. Abandonment Evidence + Design Preservation + a5d1278 Disposition

**Abandonment evidence:** (1) no Phase-1 security delta (#744; both sides fake-sign); (2) no scheduled Phase-2
real-signing consumer; (3) active wiring would regress Phase-1 (no `raw_token` on main tokens); (4) NonceRegistry
redundant. None of these is reversible by a "safe scaffold" that adds value today.

**Design preserved (NOT lost):**
- The DI shape (SignatureVerifier Protocol + AlwaysRejectVerifier fail-closed default + Gate 0 NO_VERIFIER + Gate
  4 real-verify-against-raw_token) is documented in `docs/audits/security/HXA26_HXA27_DEFENSE_PRIMITIVES_REDUNDANCY_AUDIT_PHASE1.md` with line refs.
- The full implementation lives in the **live, locked** `agent-a5d1278` worktree (head e8caaefc1). **Correction to
  the dispatch's assumption:** a5d1278 is NOT in the #759 backup snapshot (that snapshot holds the 7 REMOVE_NOW
  paths only); a5d1278 was deliberately kept by #759.

**Recommended future slice (when real signing gets a consumer):** `HXA_REAL_TOKEN_SIGNING_PHASE2` - introduce a
real signature payload on `CapabilityToken`, then salvage the DI verifier as the **optional-injected,
disabled-by-default** shape (safe-shape B) so Phase-1 stays green.

**a5d1278 worktree disposition recommendation (do NOT execute here):** move ESCALATE_ENGINEERING_REVIEW ->
**ARCHIVE_DOC** - keep the worktree parked/locked (or fold a one-page DI-design note into `docs/`) as the design
record; tie any future REMOVE to the explicit Phase-2 ruling, never a blind discard (a5d1278 is unique and not
backed up elsewhere). This is a recommendation for a later worktree slice, not this one.

---

## Critic Review

The adversarial critic (read-only, independent re-grep of origin/main + the parked worktree) **UPHELD
RETIRE_DEFER** at high confidence (~0.9). It re-verified all four facts (DI absent/unique; main fake-signing;
NonceRegistry redundant; no Phase-2 consumer), and **strengthened** the regression finding: main's
`CapabilityToken` carries no `raw_token`, the issuer fakes the booleans (:710-711), so any wired verifier rejects
all current tokens. Its one correction (the #759 backup does NOT contain a5d1278 - it is a live kept worktree)
reinforces RETIRE (nothing is lost). It found no scheduled real-signing consumer and no safe-shape salvage with
Phase-1 production value. Verdict: PASS.

---

## 8. Internal Review Verdict

**READY.** Decision reached on evidence: DI verifier unique-but-inert today; no Phase-2 consumer; active wiring
regresses Phase-1; scaffold-only is YAGNI; NonceRegistry redundant. Verdict RETIRE/DEFER WITH DESIGN PRESERVED,
critic-UPHELD. No code changed; a5d1278 worktree untouched (read-only). The design is preserved (worktree + #744
doc); a follow-up Phase-2 slice is named for when real signing acquires a consumer. NO_OVERCLAIM: the verdict is
"defer", not "the primitive is worthless" - it is a correct future hardening, just not for Phase 1.

---

## 9. WSP_97 Truth Boundary Checklist

Declared items: 18 - Rows: 18 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | DECISION_EVIDENCED | YES | Sec 5/6 axes with file:line + roadmap evidence |
| 2 | NO_CODE_CHANGE | YES | Decision-only; no `.py` modified (RETIRE branch) |
| 3 | A5D1278_WORKTREE_UNTOUCHED | YES | Read-only inspection only; not modified/removed/unlocked |
| 4 | NONCE_DI_REDUNDANCY_RECONFIRMED | YES | Sec 4/5 (main Gate 8 + used_nonces; #744 SUPERSEDED) |
| 5 | HOLOINDEX_UTILIZED | YES | Sec 3 (query run; #744 governing) |
| 6 | CURRENT_MAIN_LINE_NUMBERS_REVERIFIED | YES | Re-verified on ba8dba7c7; minor drift noted |
| 7 | NO_WHOLESALE_WORKTREE_PORT | YES | No cherry-pick/copy of the worktree; it is evidence only |
| 8 | PHASE1_BEHAVIOR_COMPATIBILITY_PROVEN | YES | Sec 5: wiring the verifier would reject all current tokens (no raw_token) -> regression |
| 9 | CURRENT_VALID_TOKEN_PATH_PRESERVED | YES | No change to `validate_token()` / #743-#756 gates |
| 10 | VERIFIER_NOT_ACTIVE_BY_DEFAULT_UNLESS_PROVEN_SAFE | YES | Not added at all (RETIRE); cannot be active by default |
| 11 | NONCE_DI_NOT_PORTED_UNLESS_PROVEN_NEEDED | YES | Not ported (proven redundant) |
| 12 | CRITIC_REVIEW_COMPLETED | YES | Critic Review section (UPHELD, ~0.9) |
| 13 | NO_DEPENDENCY_CHANGE | YES | No packaging/CI/dep change |
| 14 | NO_WSP_MUTATION | YES | No WSP doc changed |
| 15 | ASCII_CLEAN_AUDIT | YES | Doc is ASCII-only |
| 16 | NO_CABR_READY | YES | Not touched |
| 17 | NO_PAYOUT_READY | YES | Not touched |
| 18 | NO_DAO_ACTIVATION | YES | Not touched |

**WSP 97 Truth Boundary Checklist: 18/18 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline. Decision on
origin/main @ ba8dba7c7. Verdict: RETIRE / DEFER WITH DESIGN PRESERVED - the DI fail-closed SignatureVerifier is
unique but inert in Phase-1 (fake signing), would regress the current token path if wired, and has no scheduled
Phase-2 consumer; NonceRegistry DI is redundant. Design preserved in the live a5d1278 worktree + the #744 audit;
revisit at HXA_REAL_TOKEN_SIGNING_PHASE2. No code changed; a5d1278 untouched.*
