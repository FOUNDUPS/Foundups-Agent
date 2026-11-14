# REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1

**Retrieval tags:** RedDog WRE OpenClaw governed work order | Claude Code replacement RedDog branch PR | authenticated principal GitHub permission RedDog | governed work order | repository authority

**Slice:** External RedDog lane — authority contract (docs/audit only)  
**Type:** Architecture contract / audit — no runtime mutation  
**Date:** 2026-06-28  
**Base:** `9c3a8f829` (post-#888 land) + queue revision `d67b376ad`  
**Status:** PR-READY — draft PR only; no merge without sovereign token  
**WSP lock:** WSP_00, WSP_34, WSP_50, WSP_54, WSP_95, WSP_97, WSP_109, WSP_22

**Canonical extension bindings:**

- `extensions/foundups_advisory_workers/ROADMAP.md` — slice queue and follow-on priorities
- `extensions/foundups_advisory_workers/INTERFACE.md` — authority boundary + work-order pointer
- `extensions/foundups_advisory_workers/README.md` — operator-facing summary

---

## Purpose

Define how RedDog becomes **Claude-Code-style useful** without granting the Cursor extension shell, git, branch, PR, merge, or shell authority.

RedDog is the **0102 architect / digital-twin interface**, not an authority owner. RedDog **receives a bounded delegated capability for one work order after fresh verification** — it does not "have authority."

This contract records:

```text
authenticated principal
  -> GitHub permission snapshot (source of truth)
  -> governed work order envelope (RedDogGovernedWorkOrder)
  -> OpenClaw policy / intent gate
  -> Hermes lifecycle / scheduling / receipts
  -> WRE isolated worktree execution (branch, tests, PR draft)
  -> Sentinel + reviewer RedDog signed review opinions (review only)
  -> policy-gated merge (012/operator sovereign valve on F0)
```

**Out of scope for this slice:** runtime wiring, OAuth, branch/PR creation, merge implementation, HoloIndex ranking code changes, extension write tools.

---

## HoloIndex Phase 0 — Baseline (before edits)

**Method:** `python holo_index.py --search "<query>"` (2026-06-28, pre-contract doc)  
**Skillz/Rolodex:** HoloIndex CLI top-5 output does not emit a separate Skillz collection; Skillz hits appear mixed in code/WSP/docs when indexed.  
**Direct-read fallback:** `true` for all queries (worker read required files per WSP_50).

| # | Query | Code (top 3) | WSP (top 3) | Docs (top 3) | Expected targets found? | Class |
|---|-------|--------------|-------------|--------------|-------------------------|-------|
| 1 | RedDog governed repo work order | ai_overseer/wardrobe_commit_organizer.py; voteballots/test_confidence…; ai_overseer/test_m2m… | WSP_CORE; WSP_2; WSP_34 | OPENCLAW_REDDOG_READINESS; REDDOG_SESSION_CONTINUITY; FOUNDUPS_AGENT_REDTEAM | **No** — audit doc absent; extension ROADMAP/INTERFACE not in docs index | **INDEX_GAP** |
| 2 | RedDog WRE OpenClaw handoff contract | openclaw_dae.py; openclaw_action_ledger.py; openclaw_execution_routes.py | WSP_54; WSP_11; WSP_95 | OPENCLAW_0102_HANDOFF; OPENCLAW_REDDOG_READINESS; moltbot_bridge/README | Partial — OpenClaw/WRE routes **yes**; typed work-order contract **no** | **MEDIUM** |
| 3 | GitHub permission branch PR work order WSP 34 | ai_overseer.py; menu_handler.py; main_menu.py | WSP_34; WSP_7; WSP_85 | github_orchestrator/README; AGENT_SECURITY_STACK annex; github_integration/COMPLIANCE | Partial — WSP_34 + github modules **yes**; RedDog work-order path **no** | **MEDIUM** |
| 4 | WSP 95 Skillz Wardrobe repo work execution | worker_assignment_protocol.py; wsp90_bulk_fix.py; autoagent_lab/test_eval… | WSP_95; WSP_97; WSP_35 | FOUNDUP_ONBOARDING_SKILLZ_WARDROBE; wre_core/INTERFACE; video_comments/skillz README | Partial — WSP_95 + Skillz docs **yes**; governed repo execution bridge **no** | **MEDIUM** |
| 5 | WSP 109 FoundUp intake RedDog WRE handoff | test_openclaw_wsp109_onboarding_dryrun.py; run_wre.py; openclaw_foundup_orchestrator.py | WSP_109; WSP_46; WSP_INIT | WSP_109_FOUNDUP_ONBOARDING…; REDDOG_FAM_GENESIS; REDDOG_CATALOG_CLASSIFICATION | Partial — intake/onboarding **yes**; repo work-order contract **no** | **MEDIUM** |
| 6 | OpenClaw permission gate WRE work order | openclaw_permission_policy.py; openclaw_dae.py; test_openclaw_dae.py | WSP_54; WSP_95; WSP_CORE | PLUGIN_SWITCH_MATRIX; OPENCLAW_PLUGIN_LEDGER; SKILL_BOUNDARY_POLICY | Partial — permission gate **yes**; work-order envelope **no** | **MEDIUM** |

---

## HoloIndex Discoverability (Addendum A)

### Intended retrieval tags

Future HoloIndex and RedDog bounded context should connect these terms:

`RedDog`, `governed work order`, `repository authority`, `GitHub permission`, `branch`, `PR`, `WRE`, `OpenClaw`, `Hermes`, `Sentinels`, `Skillz`, `Wardrobe`, `WSP_34`, `WSP_50`, `WSP_54`, `WSP_95`, `WSP_97`, `WSP_109`, `authenticated principal`, `Claude Code replacement`, `delegated capability`, `work order envelope`, `RedDogGovernedWorkOrder`.

### Expected discoverability after this slice

| Query | Expected hit |
|-------|----------------|
| RedDog governed repo work order | This audit doc (top 5 docs) |
| Claude Code replacement RedDog branch PR | This audit doc |
| authenticated principal GitHub permission RedDog | This audit doc |
| OpenClaw WRE governed execution | This audit doc + OpenClaw execution routes (code) |
| RedDog WRE OpenClaw governed work order | This audit doc; extension ROADMAP/INTERFACE via cross-links or INDEX_GAP follow-up |

### INDEX_GAP follow-up (required)

Post-`--index-docs` probe **#7 fails** ROADMAP/INTERFACE discoverability:

**`HOLOINDEX_REDDOG_GOVERNED_WORK_ORDER_INDEX_GAP_PHASE1`** — index `extensions/foundups_advisory_workers/**/*.md` into `navigation_docs` or add NAVIGATION retrieval aliases; re-run probe queries.

---

## Targeted HoloIndex Reindex Gate (Addendum C)

**Command used:** `python holo_index.py --index-docs` (established docs-only indexer; does **not** cascade `--index-all`; resets `navigation_docs` only).

**Not used:** `--index-all`, `--index-code`, ranking/indexer code edits.

**Post-index results:** recorded in **Before/After retrieval table** below after operator run completes.

### Before/After retrieval table

**Reindex command:** `python holo_index.py --index-docs` — 3435 docs indexed in 87.41s (2026-06-28).  
**Generated index artifacts:** on local SSD (`HOLO_SSD_PATH` / default `holo_index/ssd`); not committed to git per repo convention.

| # | Query | Before | After | Audit doc top 5? | ROADMAP/INTERFACE top 5? |
|---|-------|--------|-------|------------------|--------------------------|
| 1 | RedDog governed repo work order | INDEX_GAP | **HIGH** | **YES** (#1 docs) | No |
| 2 | RedDog WRE OpenClaw handoff contract | MEDIUM | MEDIUM | No (#4 docs: RECURSIVE_DAE) | No |
| 3 | GitHub permission branch PR work order WSP 34 | MEDIUM | MEDIUM | No | No |
| 4 | WSP 95 Skillz Wardrobe repo work execution | MEDIUM | MEDIUM | No | No |
| 5 | WSP 109 FoundUp intake RedDog WRE handoff | MEDIUM | MEDIUM | No | No |
| 6 | OpenClaw permission gate WRE work order | MEDIUM | MEDIUM | No | No |
| 7 | RedDog WRE OpenClaw governed work order | (probe) | MEDIUM | No | **No — INDEX_GAP** |

**Addendum C acceptance:**

| Criterion | Result |
|-----------|--------|
| At least one query retrieves audit doc in top 5 | **PASS** (query 1, docs #1) |
| ROADMAP or INTERFACE discoverable for probe query 7 | **FAIL** — `extensions/foundups_advisory_workers/{ROADMAP,INTERFACE}.md` not in `navigation_docs` index path |
| Follow-up required | **YES** — `HOLOINDEX_REDDOG_GOVERNED_WORK_ORDER_INDEX_GAP_PHASE1` |

**Root cause:** `index_docs_entries()` indexes `modules/**`, `docs/**`, `holo_index/docs/**`, `WSP_framework/docs/**` only — not `extensions/foundups_advisory_workers/`. Extension ROADMAP/INTERFACE/README require a targeted indexer extension or NAVIGATION aliases (out of scope this slice).

## RedDog WRE OpenClaw governed work order — extension bindings

| File | Role |
|------|------|
| `extensions/foundups_advisory_workers/ROADMAP.md` | Slice queue, P0 dryrun + implementation slices |
| `extensions/foundups_advisory_workers/INTERFACE.md` | Authority boundary + schema pointer |
| `extensions/foundups_advisory_workers/README.md` | Operator summary |
| This audit doc | Canonical authority contract + `RedDogGovernedWorkOrder` schema |

---

## Audit Findings

### F1 — Extension remains advisory-only (OBSERVED)

`extensions/foundups_advisory_workers/README.md`, `INTERFACE.md`, and `extension.js` enforce:

- No repo edits, shell, merge, or Skillz/OpenClaw/Hermes/WRE direct execution
- `buildGovernedHandoffRecommendation()` emits `authority_level: advisory_only`
- Copy MD includes `## Governed Handoff Recommendation` without dispatch

**Gap:** handoff is narrative + slice name only — no typed `RedDogGovernedWorkOrder` envelope.

### F2 — OpenClaw policy gate exists but is intent-local (OBSERVED)

`openclaw_permission_policy.py`:

- `resolve_autonomy_tier()` — ADVISORY / METRICS / DOCS_TESTS / SOURCE from intent category
- `check_source_permission()` — `AgentPermissionManager.check_permission(agent_id="openclaw", …)` with allowlist/forbidlist

`openclaw_execution_routes.py`:

- `execute_command()` — file-path permission gate before WRE `execute_skill` / `execute()`

**Gap:** gates bind to OpenClaw intent text + skills_registry agent id — not GitHub principal, not work-order nonce/expiry, not RedDog-originated envelope.

### F3 — AgentPermissionManager is repo-local graduated autonomy (OBSERVED)

`agent_permission_manager.py`:

- Permission levels: `read_only`, `metrics_write`, `edit_access_tests`, `edit_access_src`
- Allowlist/forbidlist patterns, confidence decay, SQLite + skills_registry

**Gap:** no `repo_full_name`, no GitHub permission snapshot, no per-work-order scope.

### F4 — GitHub integration supports branch/PR/merge APIs (OBSERVED, unwired)

`github_api_client.py`: `create_branch`, `create_pull_request`, `merge_pull_request`, `create_or_update_file`.

`github_orchestrator.py`: gh CLI for projects/issues — separate from RedDog path.

**Gap:** no caller validates authenticated principal + work order before these APIs.

### F5 — WRE execution route exists (OBSERVED)

OpenClaw routes `wre_orchestrator` → WRE skill execution with bounded context.

**Gap:** no isolated worktree contract, no mandatory CI gate receipt, no work-order id in context.

### F6 — F0 autonomous merge (SPECIFIED_NOT_IMPLEMENTED)

Extension F0 safety boundary and 012 sovereign land token pattern prohibit autonomous F0 merge. **Not planned behavior** until prior gates pass and policy slice lands.

### F7 — Single RedDog compromise must not suffice (NEEDS_VERIFICATION → contract specified)

Required controls (specified here, not implemented):

- Fresh GitHub permission snapshot per work order
- OpenClaw re-validates envelope independent of RedDog Copy MD
- WRE executes only in isolated worktree with path allowlist
- Merge requires separate authority tier + 012/operator valve on F0

---

## Authority Contract (14 principles)

1. **RedDog is the 0102 architect/digital-twin interface**, not an authority owner.
2. **Authority is delegated per request** from an **authenticated principal** (not "user").
3. **GitHub remains source of truth** for repository permissions.
4. **Before any future write action**, verify: authenticated principal; target repository; current GitHub permission; allowed branch/worktree scope; allowed file/path scope; operation type; expiry / nonce / replay protection.
5. **RedDog extension remains advisory-only** — no shell, git write, or merge from webview/model.
6. **RedDog emits a governed work order**, not shell commands or ad-hoc "run this."
7. **OpenClaw owns policy/intent gate** — must reject stale, over-scoped, or replayed orders.
8. **WRE owns repo/process execution** — branch, patch, test, PR draft in isolated worktree.
9. **Hermes owns lifecycle/scheduling/receipts** — queue, schedule, audit trail; not policy.
10. **Sentinels and reviewer RedDogs** produce **signed review opinions only** — no merge authority.
11. **Merge authority is separate** from review authority.
12. **F0 merge** remains strongest-gated; **autonomous F0 merge is SPECIFIED_NOT_IMPLEMENTED**, not planned behavior.
13. **External f(i) FoundUps** may later use policy-driven autonomy only after this contract is implemented and tested.
14. **Single RedDog compromise** must not be sufficient to compromise a repo (defense in depth across OpenClaw + WRE + GitHub snapshot + 012 valve).

**012/operator:** use this term only for the local F0 operator surface (work focus, sovereign land, override).

---

## End-to-end flow (specified)

```text
012/operator work focus
  -> RedDog advisory review (extension, v0.3.27)
  -> WSP Applicability Preflight (future runtime; specified below)
  -> RedDogGovernedWorkOrder draft (advisory packet field; not executed here)
  -> authenticated principal attestation + GitHub permission probe (future)
  -> OpenClaw policy gate (intent + envelope validation)
  -> Hermes enqueue + receipt id
  -> WRE isolated worktree executor (branch, patch, test, PR draft)
  -> Sentinel + reviewer RedDog review opinions (signed, review-only)
  -> 012/operator + policy merge gate (F0: sovereign token required)
```

---

## RedDogGovernedWorkOrder — schema draft

Typed envelope RedDog may **recommend**; OpenClaw/WRE **validate and execute**. All fields WSP_97-labeled at emission time.

```yaml
RedDogGovernedWorkOrder:
  work_order_id: string          # uuid v4
  created_at: string             # ISO-8601 UTC
  red_dog_instance_id: string    # extension build + host fingerprint digest
  authenticated_principal: string  # stable id of delegating principal
  principal_provider: string     # e.g. github_oauth, gh_cli_session, pfMALL_member
  repo_full_name: string         # owner/repo
  repo_permission_snapshot:
    permission_level: string     # read | triage | write | maintain | admin
    captured_at: string          # ISO-8601 UTC
    source: string               # github_api | gh_cli
    digest: string               # sha256 of canonical snapshot json
  requested_operation: string    # docs_patch | test_fix | feature_slice | audit_only | ...
  authority_tier: string         # advisory | docs_tests | source | merge_request (never autonomous_f0_merge)
  allowed_paths: [string]        # posix globs, repo-relative
  denied_paths: [string]         # explicit deny wins
  branch_name: string            # proposed feature/fix/docs branch
  base_ref: string               # e.g. main
  task_summary: string           # bounded plain text
  wsp_applicability: [string]    # e.g. WSP_34, WSP_50, WSP_97
  holoindex_evidence_refs: [string]  # bounded paths + digests, not raw snippets
  skillz_candidates: [string]    # skill_id recommendations from Wardrobe
  required_tests: [string]       # pytest paths or CI job ids
  required_policy_gates: [string]  # openclaw_source_check, github_permission_fresh, ...
  required_reviewers: [string]   # sentinel_profile ids, reviewer reddog roles
  sentinel_checks: [string]      # security, regression, wsp_compliance, ...
  rollback_plan: string          # bounded text
  expiry: string                 # ISO-8601 UTC; reject if now > expiry
  nonce: string                  # single-use id for replay protection
  evidence_digest: string        # sha256 of redacted advisory source packet
  advisory_only_source_packet:
    work_focus_digest: string
    wsp_prompt_digest: string
    copy_md_run_trace_digest: string
```

**Emission rule:** extension v0.3.27 may reference this schema in INTERFACE/README only — **RUNTIME_EMISSION_NOT_IMPLEMENTED**.

---

## WSP Applicability Preflight (future RedDog runtime — specified)

Before emitting any repo work order, future RedDog runtime must:

1. **Identify applicable WSPs** from work focus + HoloIndex hits (WSP_34, WSP_50, WSP_54, WSP_95, WSP_97, WSP_109 as applicable).
2. **Identify candidate Skillz/Wardrobe/Rolodex surfaces** (recommendation only).
3. **Attach evidence refs and confidence labels** (`OBSERVED` / `INFERRED` / `NEEDS_VERIFICATION`).
4. **If WSP/Skillz recall is weak**, block work-order emission and return retrieval-repair recommendation (fail closed).

**This slice:** docs contract only — no runtime preflight implementation.

---

## WSP_97 Truth Table

| Row | Status |
|-----|--------|
| EXTENSION_REMAINS_ADVISORY_ONLY | OBSERVED |
| GOVERNED_WORK_ORDER_SPECIFIED | OBSERVED |
| RUNTIME_EXECUTION_NOT_IMPLEMENTED | OBSERVED |
| GITHUB_PERMISSION_CHECK_REQUIRED | SPECIFIED_NOT_IMPLEMENTED |
| OPENCLAW_POLICY_GATE_REQUIRED | OBSERVED (intent gate); ENVELOPE_GATE SPECIFIED_NOT_IMPLEMENTED |
| WRE_EXECUTION_AUTHORITY_REQUIRED | OBSERVED |
| HERMES_LIFECYCLE_REQUIRED | SPECIFIED_NOT_IMPLEMENTED |
| SENTINELS_REVIEW_ONLY | OBSERVED |
| MERGE_AUTHORITY_SEPARATE | SPECIFIED_NOT_IMPLEMENTED |
| F0_AUTONOMOUS_MERGE_NOT_IMPLEMENTED | SPECIFIED_NOT_IMPLEMENTED |
| REDDOG_NO_STANDING_AUTHORITY | OBSERVED |
| DELEGATED_CAPABILITY_PER_WORK_ORDER | SPECIFIED_NOT_IMPLEMENTED |
| HOLOINDEX_DISCOVERABILITY_CONTRACT_DOCUMENTED | OBSERVED |
| TARGETED_INDEX_DOCS_GATE_DOCUMENTED | OBSERVED |

---

## WSP_15 — Follow-on implementation slices

| Slice | Priority | Notes |
|-------|----------|-------|
| REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1 | P0 | Validate envelope + gate semantics; no real branch/PR/write |
| REDDOG_GITHUB_PERMISSION_PROBE_PHASE1 | P0 | Fresh GitHub permission snapshot for authenticated principal |
| REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1 | P0 | OpenClaw validates RedDogGovernedWorkOrder envelope |
| REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_PHASE1 | P0/P1 | WRE executes in isolated worktree; tests + PR draft |
| REDDOG_REVIEW_CONSENSUS_RECEIPTS_PHASE1 | P1 | Sentinel + reviewer signed opinions + receipts |
| REDDOG_AUTONOMOUS_MERGE_POLICY_PHASE1 | P3 | **Blocked** until prior gates; F0 still 012/operator valve |
| HOLOINDEX_REDDOG_GOVERNED_WORK_ORDER_INDEX_GAP_PHASE1 | P1 | **Required** — extension ROADMAP/INTERFACE not in docs index path |
| REDDOG_SANITIZED_TARGET_CONTEXT_PROVENANCE_PHASE1 | P1 | Queued — unrelated to this contract |
| REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1 | P1 | Queued — unrelated to this contract |

---

## Residual SPECIFIED_NOT_IMPLEMENTED

- RedDogGovernedWorkOrder runtime emission from extension
- GitHub permission probe + snapshot storage
- OpenClaw envelope validator (nonce, expiry, replay)
- Hermes work-order queue + receipt persistence
- WRE isolated worktree executor
- Sentinel signed review pipeline
- Policy-gated merge (non-F0 and F0)
- F0 autonomous merge (explicitly not planned until proven)
- WSP Applicability Preflight runtime
- pfMALL / external-repo autonomous policy paths

---

## Out of scope (explicit)

- Extension runtime write tools, shell, branch/PR/merge
- GitHub OAuth implementation
- OpenClaw/Hermes/WRE wiring changes
- HoloIndex ranking/indexer code changes
- #841 / livechat
- Sanitized-target provenance fixes
- Run Trace telemetry fixes

---

## Validation commands

```bash
git diff --check docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md extensions/foundups_advisory_workers/
rg "RedDog governed repo work order" docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md
rg "authenticated principal" docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md extensions/foundups_advisory_workers/
python holo_index.py --index-docs
python holo_index.py --search "RedDog governed repo work order"
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

---

WSP: WSP_00, WSP_34, WSP_50, WSP_54, WSP_95, WSP_97, WSP_109, WSP_22
