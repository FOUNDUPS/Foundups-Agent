# DAE Gateway Envelope Gate-Flags Trust-Boundary Audit (Phase 1)

**Slice:** DAE_GATEWAY_ENVELOPE_GATEFLAGS_TRUST_BOUNDARY_AUDIT_PHASE1
**Worker-Lane:** W6 - **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY security audit. No code, tests, config, queue, or worktree mutation.
**Base:** origin/main @ 80535e2a1 (post-#751). All line numbers re-verified against current main.
**Method:** read-only subworkers (static map / gateway effect / ingress trust / policyflags boundary)
-> draft verdict -> adversarial critic. ASCII-clean.

---

## 1. Mission and Scope

Determine whether the inbound DAE-gateway envelope gate flags (security_gate_passed,
permission_gate_passed, human_approval, security_gate_checked) drive any SECURITY-RELEVANT
routing/authorization decision - i.e. whether this is a real trust-boundary defect or merely
advisory/structural state. This is the separate envelope -> dae_gateway path the #751 completeness
critic surfaced; it is DISTINCT from the FoundUpJob -> Hermes path that #747 fixed. Scope: one
audit doc.

---

## 2. Predecessor Citations

| PR | Slice | Relationship |
|----|-------|--------------|
| #744 | HXA26_HXA27 redundancy audit (addendum) | First surfaced the PolicyFlags seam |
| #746 | PolicyFlags write-back enforcement audit | Bounded the FoundUpJob seam |
| #747 | PolicyFlags write-back remediation | Sanitize-on-deserialize + verdict write-back (FoundUpJob path) |
| #751 | Persistent-queue PolicyFlags trip-wire | Its completeness critic surfaced THIS separate envelope path |

This audit does NOT re-litigate #744-#751; it audits the distinct dae_gateway envelope path.

---

## 3. Envelope Gate-Flag Read Map

Audited file (IMPORT_PATH_VERIFIED): `modules/infrastructure/wre_core/src/foundup_job_router.py`
(`validate_foundup_job_envelope` def at :337) - the router imported by
`modules/infrastructure/wre_core/wre_gateway/src/dae_gateway.py:50`. Single source def; no shadow router.

**The unsanitized read:** `validate_foundup_job_envelope` takes the policy snapshot VERBATIM from the
raw envelope dict - `policy_flags = envelope.get("policy_flags")` (:409), and `policy_snapshot = policy_flags`
(:421, after the :420 `elif isinstance(policy_flags, dict)` guard). There is NO `PolicyFlags.from_dict`
coercion: the envelope dict is read raw.

**Gate verdict logic** (`_validate_live_mode_gates`, def :549), invoked only when `is_live_mode` is True
(call site :462; `is_live_mode` set at :435 = `policy_snapshot.get("dry_run_mode") is False and not
dry_run_defaulted`). It returns valid=False iff `missing_gates` is non-empty (:599):

| Gate | Field(s) read | Condition (verbatim) | Appends |
|------|---------------|----------------------|---------|
| 1 | human_approval (:581), permission_gate_passed (:582) | `if not human_approval and not permission_gate_passed` (:584) | "human_approval" |
| 2 | security_gate_checked (:588), security_gate_passed (:589) | `if security_gate_checked and not security_gate_passed` (:591) | "security_gate_passed" |
| 3 | evidence_pending / evidence_count (:595) | `if evidence_pending or evidence_count == 0` (:595) | "evidence_refs" |

All four named gate flags are read directly from the raw envelope dict and DO drive the verdict.

**Headline weakness - Gate 2 is OPT-IN:** the security check (:591) fires ONLY when
`security_gate_checked` is truthy. If `security_gate_checked` is absent or False, the security gate is
SKIPPED entirely regardless of `security_gate_passed`. The sibling `route_foundup_job` repeats the same
opt-in pattern at :1101.

---

## 4. Gateway Routing-Effect Map

Path (re-verified): `route_to_dae` (`dae_gateway.py:149`) -> first guard `if not self._verify_envelope(envelope)`
(:167) -> `_verify_envelope` (:325) -> for FOUNDUP_JOB envelopes, `validate_foundup_job_envelope(envelope)`
(:339) -> `if not validation_result.valid: return False` (:341/:349).

**Failed-verdict effect: HARD_BLOCK (fail-closed).** When `_verify_envelope` returns False, `route_to_dae`
runs the block at :168-184 (increments `metrics["violations_prevented"]`, returns a WSP-97/WSP-50 error dict)
and RETURNS before reaching any dispatch statement (`_invoke_core_dae` :188, `_invoke_foundup_dae` :193,
spawn :197). `routingProceedsOnFailure = False`.

**Passing grants no capability:** a PASS returns a plain bool True (:357); dispatch is keyed solely on
`dae_name`. The check is structural/routing - it does not grant any scope, capability, DAE access, or
destructive authority. `grantsCapabilityOrAuthority = False`.

Caveat: the HARD_BLOCK is import-conditional on `FOUNDUP_JOB_VALIDATION_AVAILABLE` (`dae_gateway.py:56/58`);
if that import ever silently fails, FoundUpJob envelopes fall to the permissive "objective"-only path. Not
exploitable on the current server-authored envelope; worth a startup assertion.

---

## 5. Ingress Trust-Boundary Trace

**canAttackerSetEnvelopeGateFlags = NO** on the production path.

| Caller | Production | Envelope source |
|--------|-----------|-----------------|
| `run_wre.py:152` (`WREOrchestrator.route_operation -> gateway.route_to_dae`) | YES | SERVER_AUTHORED |
| `dae_gateway.py:516`, `:526` (`test_dae_gateway` under `__main__`) | NO | Hardcoded test literals |

Exhaustive grep confirms no other `route_to_dae` caller. The sole production envelope is built server-side
at `run_wre.py:144-150` from method arguments: `{objective, context, wsp_protocols, token_budget,
memory_bundle}` - **no `policy_flags` key and no top-level FoundUpJob identity field**. `detect_envelope_type`
inspects only `set(envelope.keys())` (:316-322) and requires >=2 identity fields or a canonical
`requested_action`, so this envelope ALWAYS classifies GENERIC_DAE; `validate_foundup_job_envelope` returns
valid on mere `objective` presence (:355-362) and `_validate_live_mode_gates` is NEVER invoked. The gate-flag
read at :581-592 is unreachable on the production path. (The `cmd_mlestar` job_id is nested under
`context.receipt`, not a top-level key, so it does not trigger FOUNDUP_JOB.) The modules that DO deserialize
untrusted FoundUpJob JSON (foundup_job_consumer.py, openclaw_foundup_orchestrator.py) do NOT call
`route_to_dae`; they run via the Hermes/contract path, where `PolicyFlags.from_dict` force-resets the
server-authored gate flags.

---

## 6. Security-Relevance Determination

The verdict IS security-relevant (`gatesSecurityRelevant = True`): it gates routing (HARD_BLOCK on fail) and
the gate flags drive it. BUT a PASS confers no authority - `route_to_dae` never constructs a FoundUpJob, never
calls `HermesJobExecutor.execute`, and there is no destructive-action guard in `wre_gateway/`. So the check is
an envelope-level security/approval REPORTING gate, not a destructive-execution authorization gate.

---

## 7. Relationship to the #747 PolicyFlags Chokepoint

- **Same field family, different object.** The envelope gate flags are the same `security_gate_*` /
  `permission_gate_*` / `human_approval` names that #747 sanitizes - but here they live on a **raw `envelope`
  dict** in dae_gateway, NOT on `FoundUpJob.policy_flags`.
- **Not protected by #747.** The envelope is read raw (`policy_snapshot = policy_flags`, :421); it is never
  routed through `PolicyFlags.from_dict` / `FoundUpJob.from_dict` (the #747 chokepoint at
  `modules/communication/moltbot_bridge/src/foundup_job_contract.py:284` / `:641`, force-resetting
  `_SERVER_AUTHORED_FLAGS` at :310-313). So #747 does NOT cover this path - the earlier "#747 fixed it" framing
  would be an overclaim.
- **Does not reach Hermes.** `reachesFoundUpJobOrHermesExecute = False`.

---

## 8. Finding Classification

### GAP_CONFIRMED_BOUNDED

The seam is real and verified - a security-relevant verdict computed from an UNSANITIZED raw-envelope read,
with an opt-in (bypassable) security gate - but no untrusted ingress reaches it today (the sole production
caller is server-authored and classifies GENERIC_DAE, so the gate-flag read is unreachable), and a PASS grants
no capability. The **adversarial critic independently confirmed** (`refuted=False`, high confidence): no
false-EXPLOITABLE, no false-NOT_CONFIRMED, no missed caller, correct file, no #747-overclaim.

---

## 9. Security Impact (if confirmed)

Latent only today. IF a future caller ever wired an externally-sourced envelope into `route_to_dae` carrying
`policy_flags` + >=2 FoundUpJob identity fields + `dry_run_mode=False`, an attacker could self-assert the gate
flags in the raw dict. The most acute consequence is the opt-in security gate: by omitting `security_gate_checked`
(or setting it False), the security check at :591 is skipped, so a live envelope passes the security gate with
zero security verification (combine with self-asserted `permission_gate_passed=True` and a present evidence_ref
to clear Gates 1 and 3). Even then the gateway PASS grants no capability (no FoundUpJob construction, no
HermesJobExecutor.execute, no destructive guard), so the realized impact is a bypass of envelope-level
security/approval REPORTING, not destructive-execution authorization. The unsanitized read at
`foundup_job_router.py:421` is the trip-wire that would convert this BOUNDED gap to EXPLOITABLE.

---

## 10. Recommended Remediation Slice

Defense-in-depth (not urgent; no live exposure). Name:
**FOUNDUP_JOB_ROUTER_POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED_PHASE1** - a single small slice in
`wre_core/src`, no Hermes/contract changes:
1. **Boundary sanitization:** replace the raw `policy_snapshot = policy_flags` (`foundup_job_router.py:421`)
   with a coercion through `PolicyFlags.from_dict` (or an equivalent force-reset of the server-authored gate
   flags to defaults), mirroring the contract chokepoint.
2. **Gate-2 fail-closed:** require `security_gate_passed=True` unconditionally in live mode rather than only when
   `security_gate_checked` is truthy, closing the opt-in pattern at :588-592 and the sibling at :1101.
3. **Optional hardening:** a startup assertion that `FOUNDUP_JOB_VALIDATION_AVAILABLE` is True so FoundUpJob
   envelopes cannot silently fall to the permissive path.

---

## Critic Review

The adversarial critic re-grepped origin/main @ 80535e2a1 and CONFIRMED the classification (not refuted, high
confidence). It substantiated every load-bearing claim: the unsanitized raw read (:421), the four gate-flag
reads driving the verdict (:581/:582/:588/:589), the opt-in Gate 2 (:591), the BOUNDED ceiling (sole
server-authored caller `run_wre.py:152` -> GENERIC_DAE -> gate read unreachable), the HARD_BLOCK fail-closed
effect (:167-184 before dispatch), and the correct imported router file. It found no false-exploitable claim,
no false-not-confirmed claim, no missed production caller, and no #747-fixed overclaim. It flagged two cosmetic
citation imprecisions in the draft, both corrected in this final: (1) the bare assignment is line 421 only (420
is the `elif` guard); (2) the contract chokepoint is `modules/communication/moltbot_bridge/src/foundup_job_contract.py`
with `PolicyFlags.from_dict` at :284 and `FoundUpJob.from_dict` at :641 (force-reset at :310-313), not ":662".

---

## 11. Internal Review Verdict

**READY.** All seven dispatch questions answered with file:line evidence on current main: (1) the gate-flag
reads + opt-in block condition (Sec 3); (2) permissive-on-absence = True, security gate bypassable by omitting
`security_gate_checked` (Sec 3/5); (3) failed verdict = HARD_BLOCK, fail-closed (Sec 4); (4) untrusted ingress
does NOT reach `route_to_dae` today - server-authored only (Sec 5); (5) passing grants no capability (Sec 6);
(6) does NOT touch the FoundUpJob/Hermes execute path (Sec 7); (7) same field family, different object,
unprotected by #747 (Sec 7). Classification GAP_CONFIRMED_BOUNDED, adversarial-critic-confirmed. NO_OVERCLAIM
honored: the seam is real but latent. Engineering/security only - no 012 ruling requested.

---

## 12. WSP_97 Truth Boundary Checklist

Declared items: 30 - Rows: 30 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_SECURITY_AUDIT | YES | Only this audit doc written; all evidence via git show/grep |
| 2 | NO_CODE_CHANGE | YES | No .py modified |
| 3 | NO_TEST_CHANGE | YES | No test modified |
| 4 | NO_CHERRY_PICK | YES | No cherry-pick |
| 5 | NO_WORKTREE_REMOVAL | YES | Audit performed no worktree removal |
| 6 | NO_BRANCH_DELETE | YES | No branch deleted |
| 7 | NO_CONFIG_CHANGE | YES | No config touched |
| 8 | NO_ENV_MUTATION | YES | No env var set |
| 9 | NO_SECRET_VALUES | YES | Only code structure / file:line; no tokens/keys/payloads |
| 10 | DISTINCT_FROM_POLICYFLAGS_CHAIN | YES | Audited the envelope->dae_gateway path; #744-#751 not re-litigated |
| 11 | NO_OVERCLAIM | YES | Classified BOUNDED (latent), not EXPLOITABLE; impact stated as latent |
| 12 | CITES_PR_751 | YES | Sec 1, Sec 2 cite #751 |
| 13 | NO_CABR_READY | YES | Not touched |
| 14 | NO_PAYOUT_READY | YES | Not touched |
| 15 | NO_DAO_ACTIVATION | YES | Not touched |
| 16 | NO_LIVE_DAE_RUN | YES | No DAE executed |
| 17 | NO_WRE_START | YES | WRE not started |
| 18 | NO_MODEL_CALL | YES | No model invoked |
| 19 | NO_NETWORK_CALL_REQUIRED | YES | Static read only |
| 20 | NO_DYNAMIC_EXECUTION_REQUIRED | YES | Static analysis; no code executed |
| 21 | ASCII_CLEAN_AUDIT | YES | Doc is ASCII-only |
| 22 | CURRENT_MAIN_ONLY_NO_STALE_LINE_NUMBERS | YES | All lines re-verified @ 80535e2a1; not trusted from #751 |
| 23 | IMPORT_PATH_VERIFIED | YES | dae_gateway.py:50 imports wre_core/src/foundup_job_router.py |
| 24 | ADVERSARIAL_CRITIC_COMPLETED | YES | Critic Review subsection; refuted=False, high confidence |
| 25 | FAILED_VERDICT_EFFECT_CLASSIFIED | YES | HARD_BLOCK (Sec 4, dae_gateway.py:167-184) |
| 26 | INGRESS_TRUST_BOUNDARY_CLASSIFIED | YES | NO - server-authored only (Sec 5) |
| 27 | FINDING_CLASSIFIED | YES | GAP_CONFIRMED_BOUNDED (Sec 8) |
| 28 | SEVEN_QUESTIONS_ANSWERED | YES | Sec 11 maps all 7 to file:line |
| 29 | SINGLE_FILE_DIFF | YES | Only this audit doc staged |
| 30 | REMEDIATION_SLICE_NAMED | YES | Sec 10 names the slice |

**WSP 97 Truth Boundary Checklist: 30/30 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Read-only trust-boundary audit of origin/main @ 80535e2a1. Finding: GAP_CONFIRMED_BOUNDED - the dae_gateway
envelope reads gate flags from a raw unsanitized dict with an opt-in security gate (a genuine latent gap,
unprotected by #747), but no untrusted ingress reaches it today and a pass grants no capability. Remediation
named, deferred; not urgent.*
