# Foundups®Agent Roadmap

## Status

Phase: IDE-side RedDog Architect proof surface.

Current implementation:

- Cursor command: `Foundups®Agent: Open`.
- Bottom-composer webview with scrollback output.
- OpenRouter bridge with redaction gate.
- WSP_00/WSP_97/WSP_15 operating prompt.
- HoloIndex bundle-json recall with offline fallback.
- Manual lead+panel mode for review-packet traceability.
- REDDOG_FUSION_ORCHESTRATOR_PHASE1: internal task classifier, auto effort, schema validator, one repair pass.
- REDDOG_UX_PACKET_POLISH_PHASE1 (v0.3.19): Working Tail above controls; 0102 Role label; Copy MD Run Trace; mojibake flag; validation-failure packet semantics.
- REDDOG_BLOCKED_COPY_POLISH_PHASE1 (v0.3.21, #878): Work Trail dedupe; conservative blocked-local Governed Handoff.
- REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1 (docs): fixed 15-prompt pack, rubric, runbook, artifact template for 012 replacement scoreboard.

## Architecture Direction

This extension is not the final RedDog runtime. It is the operator-facing proof surface for how RedDog should behave before becoming accessible through pfMALL or an OpenClaw/WRE route.

Foundups®Agent is the product surface. RedDog is the 0102 digital-twin architect inside it. Fusion is one internal reasoning mode, not the product identity.

### RedDog and the Recursive 0102 DAE Ecosystem

012 does not orchestrate every worker. 012 talks to RedDog. RedDog participates in the recursive 0102 DAE ecosystem. Autonomous WRE/DAE agents perform bounded system work under Hermes/OpenClaw/WRE governance.

```text
012 work focus
  -> RedDog digital twin / architect interface
  -> recursive 0102 DAE ecosystem
  -> Hermes scaffolding / lifecycle / scheduling
  -> OpenClaw policy + intent gate
  -> HoloIndex memory / retrieval
  -> Skillz / Rolodex capability catalog
  -> autonomous WRE/DAE agents
  -> Sentinels / AI overseer review
  -> WRE verification + repo/process authority
  -> CABR / pAVS benefit validation
  -> receipts / memory / recursive improvement
```

Autonomous WRE/DAE agents are NOT 012 work. 012 provides work focus, testing, sovereign approval, and override. 0102 DAEs communicate recursively and perform bounded autonomous work.

Target path:

```text
IDE extension POC
  -> RedDog Architect contract hardening
  -> WSP_109 FoundUp intake packet generation
  -> WRE/OpenClaw/Hermes dispatch surface
  -> pfMALL RedDog surface
  -> governed public FoundUp launch flow
```

## WSP_15 Priorities

| Work Item | Complexity | Importance | Deferability | Impact | MPS | Priority | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Layout + RedDog Architect contract | 2 | 5 | 5 | 4 | 16 | P0 | Required for usable 012 feedback loop |
| Tier-0/Tier-1 memory files | 1 | 4 | 4 | 4 | 13 | P1 | Required for HoloIndex discovery |
| WSP_109 intake packet mode | 3 | 5 | 4 | 5 | 17 | P0 | Converts external project ideas into FoundUp intake artifacts |
| Review packet persistence | 3 | 4 | 3 | 4 | 14 | P1 | Enables outcome learning and model performance memory |
| pfMALL RedDog binding | 4 | 5 | 3 | 5 | 17 | P0 | Public/operator surface after safety contracts harden |
| WRE/OpenClaw dispatch bridge | 4 | 5 | 3 | 5 | 17 | P0 | Must remain governed; extension cannot dispatch directly |

## External RedDog Lane Queue (post-#888)

Goal: **RedDog replaces Claude Code-style work** — not only extension polish. Advisory RedDog must bridge to governed WRE execution before random implementation.

```text
DONE
1. #886 Unicode / UTF-8 bridge (ca5703611, v0.3.25)
2. #888 schema repair hardening (9c3a8f829, v0.3.27)
3. #889 governed repo work-order contract (764084bc4)
4. #890 governed work-order dry-run validator (bd68ab83a)
5. #891 post-#890 queue docs (3cbc58913)
6. #892 GitHub permission probe (21aeff32d)

P0 NEXT (sequenced — policy before receipts before executor)
7. REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1
   - dry-run + permission freshness + HoloIndex policy; still no execution
8. REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1
   - persist policy gate receipts
9. REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_PHASE1
   - only after policy + receipts proven

P1
10. REDDOG_SANITIZED_TARGET_CONTEXT_PROVENANCE_PHASE1
11. REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1
12. HOLOINDEX_REDDOG_GOVERNED_WORK_ORDER_INDEX_GAP_PHASE1

P2/P3
13. REDDOG_REVIEW_CONSENSUS_RECEIPTS_PHASE1
14. REDDOG_AUTONOMOUS_MERGE_POLICY_PHASE1 (blocked)
```

**Rationale:** Sanitized provenance and telemetry are real polish issues, but the strategic blocker is that RedDog still cannot safely become a worker. The work-order contract is the missing bridge between “advisory RedDog” and “RedDog can direct WRE to do meaningful code work.”

## Next Slices

### REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1

- **Baseline pass (v0.3.21):** 15 fixed prompts, 012 rubric, redacted artifact template (`docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`).
- Measures "Can 012 use Foundups(R)Agent instead of Claude Code for advisory work?" — does **not** require fixes in the same slice.
- **Replacement pass (future):** rerun same pack after HoloIndex index-gap and dispatch improvements; compare against baseline artifacts in `docs/acceptance/`.

### REDDOG_EXTERNAL_ACCEPTANCE_REPLACEMENT_PHASE1

- Re-run baseline prompt pack after HOLOINDEX + dispatch slices land.
- Pass criteria: improved rubric scores and 012 verdicts vs baseline artifacts.

### FOUNDUPS_AGENT_INTAKE_MODE_PHASE1

- Assess arbitrary external repositories for FoundUps integration readiness.
- Produce advisory WSP readiness audit, FoundUp intake packet, Skillz map, and integration risk report.
- No automatic onboarding, repo mutation, package install, or execution.
- Governed WRE handoff recommendation only.

### REDDOG_BRIDGE_HARDENING_PHASE1

Addendum B required controls (after v0.3.15 lands):

- Python resolver: configured path -> .venv/venv -> system fallback; report selected interpreter in non-secret metadata
- Subprocess output caps: hard stdout/stderr caps; kill on exceed; bounded failure reason
- Orphan cleanup: webview dispose kills in-flight bridge child
- Python panel cap: advisory_model_once.py max 6 panel_models
- Retry invariant: only HTTP 429/502/503, max 2 retries, same redacted body, no re-redaction, no retry on redaction block or 400-class (except 429)
- Retry tests: 429-then-success and 400-no-retry
- Context budget: bounded char budget before bridge; truncation_applied + truncation_reason in packet
- Failure taxonomy: redaction_blocked, valve_closed, missing_key, timeout, retry_exhausted, http_error, malformed_response, subprocess_failed, output_cap_exceeded

Add slice spec section before WSP_15 table or after - actually add to ROADMAP with full acceptance criteria

### REDDOG_REDACTION_GATE_CONTEXT_ERROR_DIAGNOSTIC_PHASE1

- **Trigger:** Post-#882 EXT-ACC-001/003 probe returns `redactor_error` on `wsp_holo_skillz` bounded context (~25k chars).
- **Purpose:** Identify what in post-#882 bounded context triggers `redactor_error`; preserve fail-closed behavior.
- **In scope:** Low-cardinality reason telemetry; safe category reporting (`blocked_policy`, `residual_forbidden`, `non_text_context`, etc.); redaction tests.
- **Out of scope:** Policy weakening; raw blocked snippets in Copy MD; OpenRouter routing changes.
- **Acceptance:**
  - Same EXT-ACC-001 prompt no longer returns `redactor_error`
  - If blocked, reports specific safe category (not generic `redactor_error`)
  - No raw blocked content included
  - Redaction gate tests pass
- **Blocks:** `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1` until diagnostic lands and probe reruns successfully.

### HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1

- Index `extensions/foundups_advisory_workers/extension.js`, `scripts/advisory_model_once.py`, and Skillz/Rolodex discovery paths.
- Improve semantic recall for RedDog auto-router, WSP_15/97, and governed-handoff queries.
- Add regression retrieval tests so extension bridge code ranks above adjacent WRE routers.
- **Status:** **LANDED** #882 (`99d0e35c2`) — ranking + target recall telemetry only; not source-content inclusion.

### REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1

- **Status:** **LANDED** #885 (`888d0c9cc`) — REGULAR auto context `none` -> `wsp_holo`.
- Every auto-routed tier attaches HoloIndex bundle-json at minimum; REGULAR stays single-model without Skillz/git.
- Prerequisite: #883 landed (target content + sanitization on v0.3.22).
- Does not fix output validation, made_network_call telemetry, or mojibake (separate slices).

### REDDOG_CONTEXT_UNICODE_NORMALIZATION_PHASE1

- **Status:** **LANDED** #886 (`ca5703611`) — JS surrogate normalization + bridge UTF-8 stdin (0.3.25).

### REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1

- **Status:** **LANDED** #888 (`9c3a8f829`) — v0.3.27; 012 smoke PASS (2026-06-27).
- Repair telemetry, isolated Work Trail (`repair_single_*`), section-aware merge, OSR-007..010.
- Run Trace: `repair_context_mode: repair_minimal`, `repair_mode: openrouter_single`.
- Stale `provider_reasoning_note` deferred to `REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1`.

### REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1

- **Status:** **LANDED** #889 (`764084bc4`) — docs/audit only; no runtime wiring.
- **Canonical audit:** `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md`
- **Purpose:** Authority model for RedDog → WRE worker path; `RedDogGovernedWorkOrder` schema draft.
- **Records:** authenticated principal → GitHub permission snapshot → governed work order → OpenClaw → Hermes → WRE → review → merge gate.
- **RedDog receives bounded delegated capability per work order** — does not hold standing repo authority.
- **F0 autonomous merge:** SPECIFIED_NOT_IMPLEMENTED (not planned until prior gates land).
- **Blocks:** runtime execution slices until dryrun + permission probe land.
- **HoloIndex:** `--index-docs` gate PASS for audit doc (query 1); INDEX_GAP for extension ROADMAP/INTERFACE (probe 7) — follow-up slice required.

### REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1

- **Status:** **LANDED** #890 (`bd68ab83a`) — pure validation; stdlib only; `no_mutation_performed: true` invariant.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py`
- **Tests:** 13 pytest in `test_reddog_governed_work_order_dryrun.py`

### REDDOG_GITHUB_PERMISSION_PROBE_PHASE1

- **Status:** **LANDED** #892 (`21aeff32d`) — read-only `probe_repo_permission()` in github_integration.
- **Module:** `modules/platform_integration/github_integration/src/reddog_github_permission_probe.py`

### REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1

- **Status:** **PR-READY** — `evaluate_work_order_policy_gate()` in moltbot_bridge.
- **Module:** `modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py`
- Composes #890 dry-run + permission freshness + HoloIndex policy (Addenda A–D); Hermes-shaped receipt; no execution.

### REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1

- **Status:** **P0 QUEUED** — persist policy gate receipts; Hermes lifecycle only; no execution dispatch.

### REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_PHASE1

- **Status:** **P0 QUEUED** — after OpenClaw gate + Hermes receipts.

### REDDOG_REVIEW_CONSENSUS_RECEIPTS_PHASE1

- **Status:** **P1 QUEUED** — Sentinel + reviewer signed opinions; Hermes receipts.

### REDDOG_AUTONOMOUS_MERGE_POLICY_PHASE1

- **Status:** **P3 BLOCKED** — until dryrun, permission probe, OpenClaw gate, WRE executor, review receipts land.

### HOLOINDEX_REDDOG_GOVERNED_WORK_ORDER_INDEX_GAP_PHASE1

- **Status:** **P1 REQUIRED** — probe query 7 misses `extensions/foundups_advisory_workers/{ROADMAP,INTERFACE}.md`; `index_docs_entries` excludes `extensions/`.

### REDDOG_SANITIZED_TARGET_CONTEXT_PROVENANCE_PHASE1

- **Status:** **P1 QUEUED** — tell RedDog target snippets may contain egress-safe placeholders; not repo source truth.
- **Trigger:** model misreads `[SANITIZED_BLOCK:NN]` in bounded context as live repo source (F10 class).

### REDDOG_RUN_TRACE_TELEMETRY_CORRECTION_PHASE1

- **Status:** **P1 QUEUED** — report-only telemetry fixes; not functional blockers.
- **Scope:** stale `provider_reasoning_note: Report-only in v0.3.23`; `made_network_call: unknown`; Work Trail duplicate cleanup.

### REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1

- **Status:** VERIFIED_READY on #883 (v0.3.22) - stacked base for grounding slice.
- Inject target file **content/snippets** into bounded bridge context when HoloIndex ranks the path but omits source body.
- Trigger: EXT-ACC-001 criterion #2 fail with model egress (path hit ~7.4%, no source body) — **OBSERVED**.
- Run Trace: `target_content_included`, `target_content_paths`, `target_content_chars`, `target_content_omitted_reason`, `target_content_truncated`.
- WSP_97 tasks: bounded protocol excerpt section.
- Bump version **0.3.22** (install hygiene after #882 no-bump trap).
- Distinct from HoloIndex ranking (#882); bounded context assembly in `buildBoundedRepoContext`.
- 012 only: installed Cursor UX smoke + Copy MD usability after PR VERIFIED_READY.

### REDDOG_GOVERNED_HANDOFF_CONTRACT_PHASE1

- **Status:** DEFERRED — implementation follows `REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1` audit.
- Typed handoff from RedDog review packet to WRE/OpenClaw/Hermes.
- Skillz match recommendations become structured dispatch payloads.
- Extension remains advisory; WRE retains execution authority.

### REDDOG_PFMALL_SURFACE_BINDING_PHASE1

- Bind RedDog architect review packets to pfMALL operator surfaces.
- Classify public vs member-gated flows.
- No automatic publication without verification gate.

### REDDOG_REVIEW_PACKET_MEMORY_PHASE1

- Persist redacted review packets for HoloIndex recall and 0102 continuity.
- Bounded storage; no raw prompt leakage beyond redaction gate.

### REDDOG_FUSION_ORCHESTRATOR_PHASE2

- Structured JSON review packet schema for findings/evidence/fixes/WSP_15 rows/truth labels.
- Parser tests proving output remains copyable and shareable with 0102.
- Optional effort override audit trail in review packet.

### REDDOG_ARCHITECT_EXTENSION_CONTRACT_PHASE2

- Add a structured JSON review packet schema for findings, evidence, fixes, WSP_15 rows, and truth labels.
- Add parser tests proving the output remains copyable and shareable with 0102.
- Keep advisory-only boundary.

### REDDOG_FOUNDUP_INTAKE_PACKET_MODE_PHASE1

- Add worker mode that produces WSP_109 packet drafts:
  - `INTAKE_SOURCE.md`
  - `OUTCOME.md`
  - `SOLUTION.md`
  - `PAIN.md`
  - `POC_SCOPE.md`
  - `PROTOTYPE_GATE.md`
  - `SKILLS_MAP.md`
  - `FOUNDUP_MANIFEST_DRAFT.md`
- Do not write files automatically.
- Output as advisory packet for 012/0102 review.

### REDDOG_PFMALL_SURFACE_AUDIT_PHASE1

- Audit current pfMALL RedDog surfaces and determine where the advisory packet belongs.
- Explicitly classify public vs member-gated flows.
- No runtime wiring in audit slice.

### REDDOG_WRE_OPENCLAW_HANDOFF_CONTRACT_PHASE1

- **Status:** DEFERRED — folded under work-order contract + dryrun phases.
- Define a typed handoff from RedDog review packet to WRE/OpenClaw.
- No direct Hermes/Kanban dispatch from the extension.
- WRE remains dispatch authority.

## Non-Goals

- No direct merge authority.
- No direct repo creation.
- No automatic pfMALL publication.
- No CABR/payout/source-authority claims.
- No hidden access to `.env` or gitignored files.
- No automatic F0 mutation.
- No worm-like self-propagation, auto-install, or background repo modification behavior.
