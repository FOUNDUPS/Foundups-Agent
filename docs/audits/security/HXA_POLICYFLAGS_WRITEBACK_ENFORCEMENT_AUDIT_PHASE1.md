# HXA PolicyFlags Write-Back Enforcement Audit (Phase 1)

**Slice:** `HXA_POLICYFLAGS_WRITEBACK_ENFORCEMENT_AUDIT_PHASE1`
**Worker-Lane:** W6 · **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY security audit. No code, tests, config, env, or worktree mutation.
**Base:** `origin/main` @ `1cfced349` (after #744).
**Method:** multi-agent trace (ingress / deserialization / read-write matrix / D-class), then an
adversarial agent that argued the *opposite* finding and independently re-grepped `origin/main`.

---

## 1. Mission and Scope

Settle the seam recorded in the #744 addendum: **can any untrusted or semi-trusted job ingress
pre-set `policy_flags.capability_token_*` or `security_gate_passed` such that `D3_WRITE_SANDBOX`
clears without live validation?** Scope = static read of `origin/main` src (tests excluded), one
output file. No remediation code in this slice.

---

## 2. Predecessor Citations

| PR / Item | Relationship |
|-----------|--------------|
| **#744** `HXA26_HXA27_DEFENSE_PRIMITIVES_REDUNDANCY_AUDIT_PHASE1` | Addendum that surfaced this seam |
| **#743** `HXA29_SCOPE_ACTION_VALIDATION_ENFORCEMENT_AUDIT_PHASE1` | Scope→action-class enforcement precedent |
| **#740** WSP-109 genesis-gate remediation | Job-ingress / launch-intent boundary context |
| HXA24 capability-token PolicyFlags · HXA27 Hermes integration · HXA30 scope-to-action-class | Primitive lineage |

---

## 3. Ingress Map (the crux — trust boundary)

**Verdict: `canAttackerSetPolicyFlags = NO` on every production ingress today.**

| Ingress | Source | Flags controllable | Evidence |
|---------|--------|--------------------|----------|
| Chat "create/build foundup X" (**the production path**) | CHAT_SEMI_TRUSTED | **NO_SERVER_SET** | `openclaw_dae._execute_foundup` → `openclaw_execution_routes.execute_foundup` → `openclaw_foundup_orchestrator.dispatch_foundup` → `_handle_build_intent` → `create_job` (`orchestrator.py:957`). `create_job` (`foundup_job_contract.py:669-708`) has **no `policy_flags` parameter** → job born all-`False` (`:355` default_factory). Raw message confined to `job.payload` (`orchestrator.py:951-955`). Only `dry_run_mode` is submitter-influenceable, set server-side (`:984-985`); `dry_run=True` is the safe direction. |
| `FoundUpJob.from_dict` (the dangerous deserializer) | INTERNAL_TRUSTED | YES_FROM_PAYLOAD | `foundup_job_contract.py:613` blindly `bool()`-casts every gate flag (`PolicyFlags.from_dict`, `:258-275`). **Zero production callers** — grep of `origin/main` finds it only in tests. Not wired to any ingress today. |
| WRE `dae_gateway.route_to_dae` envelope dict | INTERNAL_TRUSTED | PARTIAL (validate-only) | `dae_gateway.py:149` reads `envelope['policy_flags']` for validation (`foundup_job_router.py:409`) but never constructs a job from it; sole prod caller `run_wre.py:152` builds the envelope server-side from an objective string with no `policy_flags`. |
| Consumer → Hermes (in-memory queue drain) | INTERNAL_TRUSTED | NO_SERVER_SET | `foundup_job_consumer.py:439` passes the live `FoundUpJob` **object** (not a dict) drained from the in-memory `_FOUNDUP_JOB_QUEUE`; no serialize/deserialize hop between create and execute. |

Genesis gate (#740) operates on a separate `FoundUpGenesisEnvelope` (no `policy_flags` field) and does not copy flags into the job.

---

## 4. PolicyFlags Deserialization Map

`anySanitizationOrOverwrite = False`. The 7 gate fields (`security_gate_checked/passed`,
`dry_run_mode`, `capability_token_checked/present/validated/scope_authorized`) default `False`
and `from_dict` copies each verbatim (`bool()` coercion only), no clamp/force-`False`/recompute
(`foundup_job_contract.py:258-294`, `:405-412`, `:613`).

| Constructor site | Authorship | Note |
|------------------|-----------|------|
| `foundup_job_contract.py:355` (`field(default_factory=PolicyFlags)`) | SERVER_AUTHORED | All-`False` default — safe |
| `:258-294` (`PolicyFlags.from_dict`) | MIXED | Verbatim copy, **no sanitization** |
| `:405-412` (`__post_init__`) | MIXED | Coerces dict → PolicyFlags; no zeroing |
| `:613` (`FoundUpJob.from_dict`) | CLIENT_FROM_PAYLOAD | Lifts attacker flags **— test-only caller** |
| `:700` (`create_job` factory) | SERVER_AUTHORED | `policy_flags` omitted → all-`False` |
| `orchestrator.py:957-985` (`_handle_build_intent`) | SERVER_AUTHORED | Only sets `dry_run_mode` server-side |
| `hermes_foundup_job_executor.py:362-365` | SERVER_AUTHORED | Only writer of `security_gate_*`, and only forces `passed=False` on failure |
| `foundup_job_router.py:408-431` (`validate_foundup_job_envelope`) | CLIENT_FROM_PAYLOAD | Validate-only; defensively forces `dry_run_mode=True` when missing |

---

## 5. PolicyFlags Read/Write Matrix

`anyValidatorVerdictWriteback = False`. Within `hermes_job_executor.py` and
`destructive_action_guard.py`, **every one of the 7 fields is read-only — zero writes/assignments**
(the apparent `= True` hits at `executor:1096-1099` are docstring text). Flag population is pure
passthrough from the inbound `FoundUpJob` envelope.

- **Guard token gate** — `capability_token_present_for_guard` = `AND` of the four
  `policy_flags.capability_token_*` (`hermes_job_executor.py:1131-1137`); `security_gate_passed`
  read straight from the envelope (`:1151`).
- `security_gate_checked` is read only by `foundup_job_router.py` (`:588/589/591/1101`), not by the
  executor/guard gate.
- Guard contract (`DestructiveActionRequest`) carries only 3 of 7 fields and is never mutated.

---

## 6. Validator Verdict Write-Back Analysis

The authoritative `TokenValidationResult` from `_validate_token_if_present`
(`hermes_job_executor.py:1254-1330`) is used **only** to (a) hard-block an explicitly-present-and-invalid
token (`:1447/1453`) and (b) serialize into result metadata (`.to_dict()`), and is **never written
into `job.policy_flags`** — explicit comment at `:1299-1301` ("PolicyFlags capability_token_* fields
control guard behavior separately"). No in-scope component sets the four `capability_token_*` flags
`True` from a trusted check (`capability_token_validator.py` never mutates `job.policy_flags`).

**Consequence:** the validator and the guard's token gate are **two independent channels**. A caller
can omit the token entirely (validator returns `None`, no block at `:1447`) yet still present
`capability_token_*=True` in the envelope to make the guard's `capability_token_present` collapse to
`True`. This is the genuine structural integrity defect.

---

## 7. D3 / D4 / D5 / D6 Exploitability Analysis

**D3_WRITE_SANDBOX — bounded, doubly.** ALLOW requires all four guard gates True
(`destructive_action_guard.py` Gate 3, `:462-527`): `workspace_binding_enforced` (`:466`),
`path_constraints_validated` (`:480`), `capability_token_present` (`:494`), `security_gate_passed`
(`:508`); each short-circuits to BLOCK.
- On the production all-`False` default, `capability_token_present` and `security_gate_passed` are
  `False` → **D3 is BLOCKED** (`MISSING_CAPABILITY_TOKEN` / `MISSING_SECURITY_GATE`). Pre-setting the
  flags is the only way to clear them, and **no production ingress can pre-set them** (§3).
- Even if cleared, D3 ALLOW is **dry-run/sandbox only** — `_allow_dry_run_result` hard-codes
  `live_execution_allowed=False`, `repo_created=False`, `production_source_modified=False`,
  `external_federation_initiated=False` (`:588-600`).

**D4 / D5 / D6 — immune.** Unconditional class-based BLOCKS in Phase 1 with no reference to any
`policy_flag` (`destructive_action_guard.py:530-567`). The classifier fails closed: unknown/empty →
`D6_IRREVERSIBLE`, and D6/D5/D4 prefixes match before D3 (`hermes_job_executor.py:973-977/1009-1067`),
so a destructive action can never fall through to D3 ALLOW.

---

## 8. Finding Classification

### `GAP_CONFIRMED_BOUNDED`

The write-back decoupling is **real and verified** (§5, §6: guard gates on caller-asserted inbound
flags; live verdict never written back; zero sanitization). But it is **not reachable from any
untrusted/semi-trusted ingress today** (§3): the live path is server-authored (`create_job` → all-`False`;
attacker text confined to `payload`), and the only flag-trusting deserializer (`FoundUpJob.from_dict`)
has no production caller. The adversarial pass **could not construct any present-day exploit**
(`refuted=False`, confidence high) and independently confirmed `BOUNDED`.

**The boundary is held by the *accident* that `from_dict` is unwired, not by positive control.** The
moment any HTTP/API/message-queue/persisted-job ingress accepting external JSON is wired to
`FoundUpJob.from_dict` (the documented "persistent queue" future, `orchestrator.py:40`), this
escalates to `GAP_CONFIRMED_EXPLOITABLE` with **no further code change**.

---

## 9. Recommended Remediation Shape

Defense-in-depth; smallest correct fix (deferred to an implementation slice — no code here):

1. **Zero inbound flags at ingestion.** In `PolicyFlags.from_dict` / `FoundUpJob.from_dict` /
   `__post_init__`, force every gate + token flag (`security_gate_*`, `capability_token_*`, and any
   future `*_gate_*`) to `False` regardless of input; **whitelist only `dry_run_mode`**. Treat these as
   server-derived, never client-supplied.
2. **Validate** — keep live capability-token validation + security gate as the single source of truth,
   run before guard evaluation.
3. **Write the verdict back** — have the validator/gate runners write their authoritative result into
   `job.policy_flags` so the guard reads trusted derived state (closes `anyValidatorVerdictWriteback=False`).
4. **Gates read only server-authored fields** — optionally assert provenance (a non-serialized
   server-authored marker) so a future `from_dict` path cannot reintroduce caller-asserted gate state.

---

## 10. Recommended Next Slice

`HXA_PERSISTENT_QUEUE_POLICYFLAGS_TRIPWIRE_AUDIT_PHASE1` — trace the persistent-queue / cross-process
boundary: confirm the in-memory `_FOUNDUP_JOB_QUEUE` has no serialize/deserialize hop today, and
inventory every job persistence/replay path (FAM daemon, idempotency store, any DR/JSONL rehydrate) for
a `to_dict()`→`from_dict()` round-trip that would re-lift `policy_flags`. That single boundary is the
trip-wire that converts this BOUNDED finding to EXPLOITABLE. The remediation (§9) should land before or
with the first such wiring.

---

## 11. Internal Review Verdict

**READY.** All six dispatch questions answered with `file:line` evidence: (1) no untrusted ingress can
pre-set the flags; (2) the guard reads inbound flags (`:1131-1137/1151`) — yes; (3) the validator
verdict is not written back (`anyValidatorVerdictWriteback=False`); (4) not exploitable today — bounded;
(5) D4/D5/D6 unconditionally blocked — yes; (6) remediation shape specified (§9). Finding
`GAP_CONFIRMED_BOUNDED` survived an adversarial challenge that argued the opposite (`refuted=False`,
high confidence). Static-only; a runtime trace (§10) should close the in-memory-queue and
reflective-dispatch residuals before relying on the boundary long-term. Engineering/security only — no
012 ruling requested.

---

## 12. WSP_97 Truth Boundary Checklist

Declared count: **18 / 18 YES** (rows below = 18).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_SECURITY_AUDIT | YES | Only this audit doc written; all traces `git show`/`git grep`/Read |
| 2 | NO_CODE_CHANGE | YES | No `.py` modified |
| 3 | NO_TEST_CHANGE | YES | No test modified (tests read-only, excluded from scope) |
| 4 | NO_CONFIG_CHANGE | YES | No config touched |
| 5 | NO_ENV_MUTATION | YES | No env var set |
| 6 | NO_WORKTREE_REMOVE | YES | No worktree removed |
| 7 | NO_UNLOCK | YES | No worktree unlocked |
| 8 | NO_BRANCH_DELETE | YES | No branch deleted |
| 9 | NO_CHERRY_PICK | YES | No cherry-pick |
| 10 | NO_SECRET_VALUES_IN_AUDIT | YES | Only code structure / `file:line`; no tokens, keys, or payloads |
| 11 | NO_REGISTRY_MUTATION | YES | Audit only |
| 12 | NO_MANIFEST_MUTATION | YES | Audit only |
| 13 | NO_PUBLIC_SURFACE_MUTATION | YES | Audit only |
| 14 | NO_DNS_CHANGE | YES | Not touched |
| 15 | NO_TOKEN_ASSIGNMENT | YES | No capability token issued/assigned |
| 16 | NO_CABR_READY | YES | Not touched |
| 17 | NO_PAYOUT_READY | YES | Not touched |
| 18 | NO_DAO_ACTIVATION | YES | Not touched |

**WSP 97 Truth Boundary Checklist: 18/18 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Read-only trust-boundary trace of `origin/main` @ `1cfced349`. Finding: `GAP_CONFIRMED_BOUNDED` —
the PolicyFlags write-back decoupling is a genuine integrity defect, not currently exploitable
(no untrusted ingress wires `FoundUpJob.from_dict`; D3 is sandbox-only; D4/D5/D6 unconditionally
blocked), one wiring decision deep. Remediation deferred to an implementation slice.*
