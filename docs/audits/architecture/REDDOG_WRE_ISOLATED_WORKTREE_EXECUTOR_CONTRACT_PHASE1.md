# REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1

**Retrieval tags:** WRE isolated worktree executor | RedDog work order executor | OpenClaw worktree policy | Hermes receipt WRE execution | branch cleanup rollback WRE | RedDogGovernedWorkOrder execution valve

**Slice:** External RedDog lane — WRE executor **contract only** (docs/audit)  
**Type:** Architecture contract / audit — **no executor implementation**  
**Date:** 2026-06-28  
**Base:** `f65ecff4e` (post-#896 runtime invocation dry-run land)  
**Status:** PR-READY — draft PR only; no merge without sovereign token  
**WSP lock:** WSP_00, WSP_15, WSP_34, WSP_50, WSP_54, WSP_91, WSP_95, WSP_97, WSP_109, WSP_22

**Predecessor spine (LANDED, pre-execution):**

| # | Artifact | Role |
|---|----------|------|
| #889 | `REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md` | Work-order envelope + authority model |
| #890 | `reddog_governed_work_order_dryrun.py` | Envelope validation, no mutation |
| #892 | `reddog_github_permission_probe.py` | Read-only permission snapshot |
| #893 | `reddog_openclaw_work_order_policy_gate.py` | Policy gate, no execution |
| #894 | `reddog_work_order_receipt.py` | Hermes-compatible audit receipt |
| #896 | `reddog_work_order_runtime_invocation.py` | End-to-end dry-run invocation |

**Canonical bindings:**

- `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md` — parent authority contract
- `extensions/foundups_advisory_workers/{ROADMAP,INTERFACE,ModLog}.md` — queue + pointers
- `modules/communication/moltbot_bridge/INTERFACE.md` — OpenClaw bridge API pointers

---

## Purpose

Define the **cage** for a future WRE isolated worktree executor that may eventually consume **accepted** RedDog governed work orders — after policy gate, Hermes receipt, and an explicit execution valve.

This slice is **architecture/contract only**. It does **not** create worktrees, branches, commits, PRs, file edits, subprocess executors, or runtime wiring.

```text
[LANDED pre-execution spine]
  contract -> dry-run -> permission -> policy gate -> receipt -> runtime invocation dry-run

[THIS SLICE — contract only]
  REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1

[FUTURE — not this slice]
  executor implementation -> valve-gated scoped execution -> PR draft (no merge)
```

---

## HoloIndex Phase 0 — Baseline (before edits)

**Method:** `python holo_index.py --search "<query>"` (2026-06-28; orphan-dataset warning on one run — direct-read fallback used per WSP_50)  
**Direct-read fallback:** `true` for all queries.

| # | Query | Top code hits | Top docs hits | Expected targets | Class |
|---|-------|---------------|---------------|------------------|-------|
| 1 | WRE isolated worktree executor | openclaw_execution_routes; openclaw_foundup_orchestrator | WORKTREE_REGISTRY_CLEANUP_*; GIT_WORKTREE_PARALLEL | Partial — worktree **ops audits yes**; RedDog executor contract **no** | **INDEX_GAP** |
| 2 | RedDog work order executor | reddog_work_order_runtime_invocation (post-#896) | REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT | Partial — invocation dry-run **yes**; executor contract **no** | **MEDIUM** |
| 3 | OpenClaw worktree policy | openclaw_permission_policy; openclaw_execution_routes | OPENCLAW_REDDOG_READINESS | Partial — intent gate **yes**; worktree isolation policy **no** | **MEDIUM** |
| 4 | Hermes receipt WRE execution | proof_of_compute_receipt; receipt_emitter | HXA OpenClaw Hermes audits | Partial — compute receipt **yes**; work-order executor receipt chain **no** | **MEDIUM** |
| 5 | branch cleanup rollback WRE | (vendor hermes-agent worktree cleanup pattern) | WORKTREE_STRANDED_WORK_*; WORKTREE_REGISTRY_* | Partial — cleanup **audits yes**; governed rollback contract **no** | **MEDIUM** |

---

## HoloIndex Discoverability (Addendum)

### Intended retrieval tags

`WRE isolated worktree executor`, `RedDog work order executor`, `execution valve`, `worktree isolation`, `rollback cleanup`, `PolicyGateReceipt`, `RedDogWorkOrderReceipt`, `no autonomous merge`, `F0 merge blocked`, `WSP_34`, `WSP_97`.

### Post-edit expectation

| Query | Expected hit |
|-------|----------------|
| WRE isolated worktree executor RedDog | This audit doc (docs top 5 after `--index-docs`) |
| RedDog work order executor contract | This audit doc |
| OpenClaw worktree policy RedDog | This audit doc + #893 policy gate module (code) |

### INDEX_GAP follow-up

If post-`--index-docs` probe fails to surface this doc in top 5 for query 1: **`HOLOINDEX_REDDOG_WRE_EXECUTOR_CONTRACT_INDEX_GAP_PHASE1`** — no HoloIndex ranking code changes in this slice; static INTERFACE/ModLog pointers only.

---

## Authority boundaries (§7)

| Actor | Role | This contract |
|-------|------|---------------|
| **RedDog (extension)** | Directs work; emits governed work orders; **advisory only** until valve | Directs — never executes |
| **OpenClaw** | Re-validates envelope; policy gate (#893); future execution intent gate | Gates — independent of Copy MD |
| **Hermes** | Lifecycle, scheduling, **receipt persistence** (#894) | Records — no silent auto-dispatch |
| **WRE executor** | Isolated worktree mutations **only after valve** | Executes — bounded by this contract |
| **Sentinels / reviewers** | Signed review opinions; no merge authority | Review only |
| **012 / operator** | Sovereign valve on F0 merge and execution enablement | Merge separately gated |

**F0 autonomous merge:** `SPECIFIED_NOT_IMPLEMENTED` — not planned until executor + review receipts + policy slices land.

---

## 1. Entry conditions (executor MAY NOT start unless ALL true)

Future executor entry MUST verify:

| # | Condition | Source | Fail-closed |
|---|-----------|--------|-------------|
| E1 | `PolicyGateReceipt.decision` ∈ `{POLICY_ACCEPT, POLICY_ACCEPT_WITH_RETRIEVAL_GAP}` | #893 | Reject |
| E2 | `RedDogWorkOrderReceipt` exists for `policy_gate_receipt_digest` | #894 store | Reject |
| E3 | Permission snapshot **fresh** at execution time (re-probe or TTL-valid embedded snapshot) | #892 + work order | Reject |
| E4 | Prior spine steps recorded `no_execution_performed: true` | #890–#896 | Reject if false |
| E5 | **Execution valve** explicitly open (env + typed authorization; default **CLOSED**) | Future valve module | Reject if closed |
| E6 | Work order **not expired** (`expiry`, `next_required_check_at`) | #889 envelope | Reject |
| E7 | Nonce not replayed | #890 dry-run nonce store | Reject |
| E8 | `permission_truth_label` ≠ `NEEDS_VERIFICATION` for write-sensitive ops | #893 | Reject |

**INDEX_GAP retrieval on write-sensitive ops:** executor MUST NOT start if work order carried `POLICY_ACCEPT_WITH_RETRIEVAL_GAP` **and** operation is write-sensitive (docs-only gap acceptance does not authorize execution).

---

## 2. Worktree isolation

| Rule | Requirement |
|------|-------------|
| W1 | **Unique worktree path** per execution: `{repo_root}/.reddog/worktrees/{work_order_id}/{nonce_suffix}/` |
| W2 | **Branch naming:** `{allowed_prefix}/{work_order_id}-{slug}` — must match work order `branch_name`; never `main`/`master` as working branch |
| W3 | **Workspace root confinement:** all file ops under worktree path + declared `allowed_paths` only |
| W4 | **Primary checkout untouched:** executor runs from linked worktree; primary repo checkout branch/HEAD unchanged |
| W5 | **Lock/lease:** exclusive lease keyed by `work_order_id`; second executor attempt → fail closed |
| W6 | **Cleanup on success:** worktree removed after PR draft receipt **if** no unpushed commits policy says discard (see §5) |
| W7 | **Cleanup on failure:** always remove worktree + delete local branch unless SALVAGE flag set by operator |

Precedent (read-only audits, not implementation): `WORKTREE_REGISTRY_CLEANUP_*`, `WSP_framework/docs/GIT_WORKTREE_PARALLEL_DEVELOPMENT.md`.

---

## 3. Mutation boundaries

| Boundary | Rule |
|----------|------|
| M1 | **Allowed paths:** intersection of work order `allowed_paths` and executor capability tier |
| M2 | **Denied paths:** work order `denied_paths` + global denylist (`.env`, `**/credentials*`, `**/.git/**`, secrets) |
| M3 | **No secrets:** no read/write of `.env`, tokens, OAuth material; redaction gate before any external model call |
| M4 | **No protected branch mutation:** no commits to `main`/`master`; base ref read-only |
| M5 | **No root/global config mutation:** no `.git/config`, hooks, CI workflow edits unless explicitly in allowed_paths (default: forbidden) |
| M6 | **Diff scope validation:** post-edit diff must ⊆ allowed_paths; forbidden path touch → abort + rollback |
| M7 | **Max files / max lines (future):** valve-configurable caps; default conservative |

---

## 4. Test / validation requirements

| Phase | Requirement | Receipt |
|-------|-------------|---------|
| V1 | Run all `required_tests` from work order | Test receipt digest |
| V2 | `git diff --check` + mojibake scan on changed paths | Validation receipt |
| V3 | WSP_97 evidence rows for each gate (OBSERVED / INFERRED / NEEDS_VERIFICATION) | Appended to executor receipt |
| V4 | Re-run applicable WSP compliance checks if work order lists them | Compliance sub-receipt |
| V5 | Security/redaction scan on diff content | Redaction receipt |
| V6 | Policy re-check if execution duration exceeds `next_required_check_at` | Mid-flight abort |

Executor MUST emit a **phase receipt** after: worktree create, edit phase, test phase, PR draft phase (future slices define schema).

---

## 5. Rollback / cleanup

| Trigger | Action |
|---------|--------|
| R1 | Failed validation (tests, diff scope, redaction) | Abort; remove worktree; delete branch; emit `EXECUTOR_ABORT_VALIDATION` receipt |
| R2 | Timeout (work order or valve TTL) | Abort; cleanup; emit `EXECUTOR_ABORT_TIMEOUT` |
| R3 | Interrupted worker (SIGTERM, crash) | Lease expiry; janitor removes stale worktree; emit `EXECUTOR_ABORT_INTERRUPTED` |
| R4 | Stale permission mid-flight | Abort before further edits; cleanup |
| R5 | Policy drift (work order amended, gate revoked) | Abort; cleanup |
| R6 | Unpushed commits on abort | Default: **discard** unless operator SALVAGE valve; never auto-push |

No autonomous merge on any rollback path.

---

## 6. Executor output contract (future `WREExecutorResult`)

When implementation lands, executor MUST return (digests/refs only in receipts; no raw secrets):

```yaml
WREExecutorResult:
  executor_run_id: string
  work_order_id: string
  branch_name: string
  worktree_path: string
  files_changed: [string]           # paths only
  tests_run: [string]
  test_outcome: passed|failed|skipped
  receipts:
    - worktree_create_receipt_digest
    - edit_phase_receipt_digest
    - test_phase_receipt_digest
    - pr_draft_receipt_digest        # SPECIFIED_NOT_IMPLEMENTED until PR slice
  pr_url: string|null               # draft only; never merged
  pr_ready: boolean
  merge_performed: false             # invariant until F0 valve (blocked)
  no_autonomous_merge: true          # invariant
  cleanup_status: pending|complete|salvaged
  wsp97_labels: [string]
  executor_receipt_digest: sha256:...
```

---

## 7. Explicit non-goals

| Non-goal | Status |
|----------|--------|
| Autonomous merge | **SPECIFIED_NOT_IMPLEMENTED** (F0 blocked) |
| Direct `main` mutation | **FORBIDDEN** |
| Permission elevation / admin ops | **FORBIDDEN** |
| Secrets / credential access | **FORBIDDEN** |
| Campaign / AutoPost / external publish | **FORBIDDEN** (separate Skillz track) |
| Live Hermes queue auto-dispatch | **SPECIFIED_NOT_IMPLEMENTED** |
| Extension runtime wiring | **SPECIFIED_NOT_IMPLEMENTED** |
| Skillz execution from executor | **FORBIDDEN** without separate work order |

---

## WSP_97 truth table

| # | Claim | Label |
|---|-------|-------|
| 1 | Pre-execution spine (#889–#896) is LANDED and proves zero repo mutation | **OBSERVED** |
| 2 | This doc defines executor cage only; no runtime code in this slice | **OBSERVED** |
| 3 | Worktree isolation rules align with existing worktree cleanup audits | **INFERRED** |
| 4 | Future executor will reuse #893 PolicyGateReceipt + #894 RedDogWorkOrderReceipt as entry proof | **INFERRED** |
| 5 | Execution valve default CLOSED until operator enables | **SPECIFIED_NOT_IMPLEMENTED** |
| 6 | WREExecutorResult schema will be implemented in executor slice | **SPECIFIED_NOT_IMPLEMENTED** |
| 7 | PR draft creation is a separate slice after executor PoC | **SPECIFIED_NOT_IMPLEMENTED** |
| 8 | F0 autonomous merge remains blocked | **OBSERVED** (#889) |

---

## WSP_15 — Next implementation slices (ordered)

| Order | Slice | Type | Depends on |
|-------|-------|------|------------|
| 1 | `REDDOG_WRE_EXECUTION_VALVE_PHASE1` | Module | This contract |
| 2 | `REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_POC_PHASE1` | Module | Valve + contract |
| 3 | `REDDOG_WRE_EXECUTOR_RECEIPT_PHASE1` | Module | PoC |
| 4 | `REDDOG_WRE_PR_DRAFT_ONLY_PHASE1` | Module | PoC + GitHub read/write valve |
| 5 | `REDDOG_WRE_EXECUTOR_JANITOR_PHASE1` | Module | PoC (stale worktree cleanup) |
| 6 | `REDDOG_REVIEW_CONSENSUS_RECEIPTS_PHASE1` | Module | Executor receipts |
| 7 | `REDDOG_AUTONOMOUS_MERGE_POLICY_PHASE1` | Policy | All above + F0 valve (**BLOCKED**) |

**Do not skip:** valve before PoC; PoC before PR draft; review receipts before merge policy.

---

## Cross-reference — pre-execution modules

| Module | Contract field consumed |
|--------|-------------------------|
| `validate_work_order_dryrun()` | Envelope shape, nonce, paths |
| `evaluate_work_order_policy_gate()` | `PolicyGateReceipt` |
| `emit_work_order_receipt()` | `RedDogWorkOrderReceipt` |
| `invoke_reddog_work_order_dryrun()` | Invocation result + stored receipt |

Future executor MUST accept **only** invocations that passed #896 with stored #894 receipt — not raw Copy MD or extension packets alone.

---

## ModLog pointer

See `extensions/foundups_advisory_workers/ModLog.md` and root audit ModLog for slice land tracking.

**Slice author:** 0102 worker lane  
**No runtime mutation performed in authoring this document.**
