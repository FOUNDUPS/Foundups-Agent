# WRE Autonomous Build Context Bundle Audit (Phase 1)

- Lane: W9 (read-only architecture audit)
- Status: DECISION-ONLY (no manifest/validator/runtime/registry mutation; no consumer wired; no build run)
- Base: origin/main 89f4ea09c (includes #770 and #771)
- Date: 2026-06-09
- WSP refs: WSP_00, WSP_50/WSP_87 (HoloIndex pre-action), WSP_15 (priority), WSP_84 (reuse), WSP_97 (Truth Boundary), WSP_22 (ModLog)
- Predecessors: #770 (manifest readiness + ecosystem reconciliation), #771 (baseline build_contract + execution_routing + read-only validator)
- Secured base: #747 genesis gate, #762 no-live-launch, #768 typed shell=False exec + redaction, D0-D6 destructive-action guard, #769 build-on-existing-primitives

---

## 1. Mission and Scope

Define the minimum SAFE context bundle that WRE/Hermes MAY later read from FoundUp
manifests and build contracts - the bounded, non-executable, validated envelope a future
dry-run loop would consume. This audit answers WHAT that bundle should contain and WHAT it
must exclude, so that a later implementation cannot smuggle repo-wide concatenation, shell
commands, executor self-selection, or readiness promotion.

This is NOT an implementation slice. It does NOT wire any consumer (OpenClaw, Hermes, WRE,
AI Overseer) to manifest contracts. It does NOT run a build. It does NOT promote readiness.
No manifest, validator, runtime, registry, CI, dependency, or test is changed in this slice.

---

## 2. Predecessors and Secured Base

- #770 FOUNDUP_MANIFEST_READINESS_AUDIT_PHASE1: existing manifests were routing/product/
  governance, not build/test contracts; AI Overseer is auditor/critic, not builder;
  execution_routing is declarative only.
- #771 FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1: added declarative build_contract +
  execution_routing blocks to 6 incomplete manifests, plus a read-only
  `foundup_manifest_validator.py` and tests. No consumer wired, no runtime behavior changed,
  no readiness promoted.
- Secured base preserved: genesis gate (#747), no-live-launch (#762), typed shell=False exec
  + redaction (#768), D0-D6 destructive-action guard, build-on-existing-primitives (#769).

The context bundle defined here must keep every one of these gates load-bearing and add no
new orchestrator.

---

## 3. FOLLOW-WSP Evidence

### 3.1 HoloIndex discovery (DISCOVERY ONLY - never proof)

12 mandated queries were run FIRST. Ratings: HIGH (top hits identify the needed file/symbol),
MEDIUM (right module/WSP, needs rg/direct read), LOW (thematically related, misses
load-bearing files), FALSE_LEAD (wrong/stale/dead), NO_SIGNAL.

| # | Query (abbrev) | Top hits (abbrev) | Target found? | Signal | Direct-read follow-up |
|---|----------------|-------------------|---------------|--------|-----------------------|
| 1 | WRE context bundle build_contract execution_routing | pfmall-control-dispatcher.js, agent_market/ARCHITECTURE.md, fam_adapter.py, WSP_30/46/INIT | NO | LOW | read manifests + validator directly |
| 2 | build_contract manifest_ready build_ready autonomous_execution_ready | public/index.html, agent_market, fam_adapter.py, WSP_104/98/106 | NO | NO | read build_contract.readiness in manifests |
| 3 | foundup_manifest_validator module_path forbidden_paths argv | public/foundup.html, sw.js, openclaw_dae.py, WSP_106/85/9 | NO (misses the named validator) | LOW | read foundup_manifest_validator.py directly |
| 4 | BuildPlan BuildTarget build_plan_generator tests dry_run | agent_market, a qwen test, simulator/deploy-sse.sh, WSP_9/6/55 | NO | LOW | read build_plan.py / build_plan_generator.py |
| 5 | FoundUpJob Consumer Hermes evidence_refs workspace_binding | kosei-app-data.js, foundups_vision/vision_executor.py, agent_market, WSP_83/56/3 | NO | LOW | read foundup_job_consumer.py / hermes_job_executor.py |
| 6 | Hermes WorkspaceBinding forbidden_paths D0 D6 | pfmall vm test, AGENTS.md, wsp_orchestrator.py, WSP_35/86/violations | NO | LOW | read hermes_job_executor.py WorkspaceBinding/guard |
| 7 | OpenClaw FoundUp orchestrator create job | fam_adapter.py, agent_market, openclaw_dae.py, WSP_54/46/9 | PARTIAL (right module, not the orchestrator file) | MEDIUM | read openclaw_foundup_orchestrator.py |
| 8 | AI Overseer auditor critic not builder | ai_overseer.py (x3), WSP_30/100/35 | PARTIAL (right module) | MEDIUM | confirm no build imports in ai_overseer |
| 9 | repo concatenation context bundle evidence packet receipt | agent_market/in_memory.py, voice_command_ingestion.py, gemma_intent_classifier.py, WSP_107/56/14 | NO | LOW | read ExecutionReceipt/BuildEvidence/EvidencePacket directly |
| 10 | CABR payout DAO readiness verification_complete false | agent_market/in_memory.py, dae_registry.py, wsp_compliance_checker.py, WSP_26/29/109 | NO | LOW | read truth fields directly |
| 11 | external agent ollama capability catalog external_agent_allowed | agent_market/test_permissions.py, agent_permission_manager.py, openclaw_dae.py, WSP_43/36/74 | NO | LOW | confirm no external-agent symbols (rg, #770) |
| 12 | module_path suffix exact validator cross domain magadoom | openclaw_dae.py, style_guardrails.py, autonomous_refactoring.py, WSP_4/PLACEMENT/49 | NO (misses the validator) | LOW | read validator _expected_module_path_matches:159-166 |

### 3.2 HoloIndex Quality Findings

- Distribution (12 queries): 0 HIGH, 2 MEDIUM (Q7, Q8 - right module only), 10 LOW, 0
  FALSE_LEAD, 0 NO_SIGNAL. Every query returned 10 hits, but the relevant ones were the
  wrong files.
- Files MISSED by HoloIndex entirely (none surfaced in any query): `foundup_manifest_validator.py`
  (even Q3 named it), the 6 updated `foundup_manifest.json`, `build_plan.py`,
  `build_plan_generator.py`, `foundup_job_contract.py`, `foundup_job_consumer.py`,
  `hermes_job_executor.py`. The recurring noise hits were `agent_market/ARCHITECTURE.md` and
  `fam_adapter.py`.
- rg / direct-read fallback was REQUIRED for every load-bearing claim in this audit.
- HOLOINDEX_GAP_CONTEXT_BUNDLE_ARTIFACTS recorded: the #770/#771 artifacts (validator, the 6
  manifests, the build_plan/job/hermes chain) are not surfaced by semantic search; the index
  appears stale relative to #771. A later HoloIndex re-index of `modules/foundups/agent/src/`
  and the updated manifests is recommended (out of scope here).
- No HoloIndex hit is used as proof anywhere in this document. Phrasing standard:
  "HoloIndex suggested X; direct read confirmed/refuted Y at file:line."

### 3.3 Direct-read inventory (re-verified on 89f4ea09c this slice)

- `modules/foundups/agent/src/foundup_manifest_validator.py` (full, 436 lines).
- `modules/foundups/agent/tests/test_foundup_manifest_validator.py` (module_path/cross-domain cases).
- The 6 updated manifests (build_contract + execution_routing + readiness + status).
- `build_plan.py` (BuildEvidence:477), `build_plan_executor.py` (ExecutionReceipt:299),
  `hermes_job_executor.py` (WorkspaceBinding:149), `autofix_executor.py` (EvidencePacket:165).
- #770 audit doc (NEEDS_LABEL_RECONCILIATION + module_path observations).

---

## 4. Current Contract State After #771

The validator (`foundup_manifest_validator.py`) is genuinely read-only: it "EXECUTES
NOTHING ... no shell-out ... imports NO runtime executor or consumer" (validator.py:10-18)
and "Contract presence is NOT build readiness" (:16-18). It enforces, per manifest:
- build_contract.foundup_id matches top-level (:233-238); module_path present and matches
  manifest location (:240-249, via `_expected_module_path_matches` :159-166); status in
  {BASELINE_DECLARATIVE_ONLY, NEEDS_LABEL_RECONCILIATION} (:85-87, :251-256).
- build/test/dry_run commands are argv-list-or-null, never shell strings; argv rejected if it
  contains shell metacharacters (`_SHELL_METACHARACTERS` :93-96, `_validate_command_block`
  :169-198).
- forbidden_paths must cover `.env`, `main.py` (exact) and `_dae.py`, `vendor` (substring)
  (:76-80, :280-291) - this closes the #770 gap (BLOCKED_PATHS omitted main.py/*_dae.py).
- required_gates must include all 8 secured gates (:65-74, :293-301).
- readiness.build_ready / autonomous_execution_ready must NOT be true; manifest_ready must not
  be true (:303-321).
- execution_routing.orchestrator in {openclaw}, executor in {hermes}, auditor in {ai_overseer},
  external_agent_allowed not true, declarative_only true, can_self_authorize not true
  (:333-370); plus a recursive truthy-"bypass"-key reject (`_scan_bypass_flags` :143-156).

Observed manifest state (direct read, all readiness flags false):

| foundup_id | status | module_path | build.command | test.command (argv) |
|-----------|--------|-------------|---------------|---------------------|
| gotjunk_001 | BASELINE_DECLARATIVE_ONLY | modules/foundups/gotjunk | null (no_build) | ["python","-m","pytest","modules/foundups/gotjunk/tests"] |
| kosei | BASELINE_DECLARATIVE_ONLY | modules/foundups/kosei | null | pytest argv |
| magadoom_001 | BASELINE_DECLARATIVE_ONLY | modules/gamification/whack_a_magat | null | pytest argv |
| antifafm_001 | BASELINE_DECLARATIVE_ONLY | modules/platform_integration/antifafm_broadcaster | null | pytest argv |
| trade | NEEDS_LABEL_RECONCILIATION | modules/foundups/trade | null | pytest argv |
| voteballots | NEEDS_LABEL_RECONCILIATION | modules/foundups/voteballots | null | pytest argv |

All 6 module_paths are exact full repo paths, so all 6 currently match via the EXACT branch
(`parent == norm_module`, validator.py:166). The `endswith` suffix fallback in the same line
is NOT exercised by any current manifest - it is a latent loosening (section 13).

---

## 5. Context-Bundle Boundary Definition

A future ContextBundle is a small, deterministic, NON-EXECUTABLE, validator-backed,
path-bounded, evidence-oriented, dry-run-only envelope. It is PRODUCED ONLY from a manifest
that passes `validate_manifest_file(...).ok == True`. It carries DECLARATIONS and PROVENANCE,
never authority. It cannot self-authorize, cannot choose a privileged executor, cannot
include forbidden paths, and cannot promote readiness by declaration.

Required ContextBundle shape (DEFINED here, NOT implemented):

```
context_bundle_version        # bundle schema version (string)
foundup_id                    # joins registry/job/plan
source_commit                 # git commit the bundle was built from
manifest_path                 # repo-relative path
manifest_sha256               # digest of the exact manifest bytes
validator_name                # "foundup_manifest_validator"
validator_version_or_commit   # validator provenance
build_contract_digest         # sha256 of the build_contract block
execution_routing_digest      # sha256 of the execution_routing block
allowed_source_roots          # [module_path/] derived from EXACT-validated module_path
allowed_test_roots            # [module_path/tests/]
forbidden_paths               # carried verbatim from build_contract.forbidden_paths
required_gates                # gate NAMES to be RE-CHECKED (not asserted passed)
dry_run_required              # true (constant)
readiness_snapshot            # all-false copy (read-only; cannot promote)
evidence_output_policy        # {path, redaction_required:true}
max_context_bytes             # hard size cap; reject/trim, never concatenate
included_file_refs            # [{path, sha256}] refs ONLY - no repo-wide contents
dry_run_eligible              # false if status==NEEDS_LABEL_RECONCILIATION (section 12)
```

Decision (Addendum B): the bundle includes NO broad file content. It carries path refs +
hashes only. Bounded excerpts may be added ONLY with explicit per-field justification in a
later slice; the default is path-ref-plus-digest, never file bodies.

---

## 6. Safe Included Fields

| Source block | Safe to include | Why | Constraint |
|--------------|-----------------|-----|------------|
| build_contract | foundup_id, module_path, owner_lane, status | identity + lane + lifecycle | module_path EXACT-validated (section 13) |
| build_contract | test.command, dry_run.{required,default} | the discoverable dry-run/test contract | argv-or-null only; re-validated |
| build_contract | safe_mutation_surface | maps to WorkspaceBinding.allowed_paths | path-bounded; traversal-checked |
| build_contract | forbidden_paths | maps to WorkspaceBinding.blocked_paths | carried verbatim; used to EXCLUDE refs |
| build_contract | required_gates | gate NAMES to re-check | never asserted passed (section 8) |
| build_contract | evidence_output.{path,redaction_required} | where redacted evidence lands | declaration only |
| build_contract | readiness (all-false) | read-only snapshot | cannot promote (section 12) |
| execution_routing | orchestrator/executor/auditor (as DECLARED roles) | provenance of intended path | re-mapped via code-owned allowlist (section 14) |
| execution_routing | external_agent_allowed(false), declarative_only(true), can_self_authorize(false), external_agent_contract_required(true) | safety assertions | bundle cannot flip them |
| registry (minimal) | foundup_id, module_path, entity_type | confirm entity is a FoundUp; cross-check path | do not copy the whole registry entry |
| provenance | source_commit, manifest_sha256, *_digest, validator_name/version | staleness + integrity anchors | mandatory |

build.command is null today (no_build); if ever non-null it must be argv-or-null and is
re-validated. NOT included as authority: build_plan_source / job_contract_source are kept as
PROVENANCE strings only; the consumer uses its OWN code paths, never imports named by the
manifest.

---

## 7. Explicitly Excluded Fields / Content

- Repo-wide file contents, directory trees, or any concatenation of source/test bodies.
- Any file ref whose path matches build_contract.forbidden_paths (`.env`, `.env.*`,
  `main.py`, `**/*_dae.py`, `**/vendor/**`, wallet/token/reward/payout/cabr/blockchain,
  `**/credentials*`, `**/secrets*`).
- Secrets in any form: `.env`, credentials, tokens, OAuth output, logs carrying secrets, or
  raw stdout/stderr from an EvidencePacket without #768 redaction.
- Shell strings anywhere (commands are argv-or-null only).
- Any asserted gate-pass / verification_complete / cabr_ready / payout_ready / dao flag.
- Routing/product manifest fields irrelevant to build (entry_url, cabr_contract,
  token_symbol, capabilities, agent_routes) - excluded to keep the bundle small.
- Absolute paths, drive-root paths, UNC paths, symlinks escaping repo, `..` traversal, or
  glob expansion that reaches a forbidden path (section 9).

---

## 8. Gate Re-Check Requirements (GATE_PASS_NOT_SERIALIZED)

required_gates is a list of gate NAMES the FUTURE consumer MUST re-run; the bundle records
WHICH gates apply, never that any passed. The 8 gates (validator.py:65-74) map to existing
enforcement that stays authoritative at runtime:
- genesis_gate -> openclaw_foundup_orchestrator validate_genesis_envelope (re-run at intake).
- dry_run_gate / no_live_launch -> hermes_job_executor dry_run default + HERMES_DELEGATE_ENABLED=0.
- destructive_action_guard_d0_d6 -> hermes `_classify_destructive_action` (fail-closed).
- typed_exec_boundary -> argv-only + #768 typed exec.
- test_gate / manifest_gate -> re-validate manifest via foundup_manifest_validator before use.
- policy_required_sovereign_valve_for_non_dry_run -> code-enforced escalation for non-dry-run.
The bundle MUST NOT carry a boolean claiming any of these is satisfied. A consumer that reads
the bundle re-evaluates every gate from code.

---

## 9. No Repo-Concatenation Rule (FILE_REFS_NOT_REPO_CONCAT)

- The bundle carries `included_file_refs` = list of {path, sha256} ONLY. No file bodies.
- `max_context_bytes` is a hard cap; a builder that would exceed it REJECTS or TRIMS to refs,
  never concatenates repo content.
- `allowed_source_roots` / `allowed_test_roots` are derived solely from the EXACT-validated
  module_path; refs outside those roots are rejected.
- Path-traversal defense (mandatory): reject absolute paths, drive-root (`C:\`, `/`), UNC
  (`\\`), symlinks resolving outside the repo, any `..` segment, and any glob that expands to
  a forbidden path. Normalize then re-check against forbidden_paths AFTER expansion.
- Staleness: the bundle is INVALID if `source_commit` or `manifest_sha256` no longer matches
  the live tree; a consumer must reject a stale bundle rather than read drifted content.

---

## 10. No Execution / No Consumer-Wiring Rule

- This slice wires nothing and runs nothing. The ContextBundle is a data envelope; producing
  it is pure read + hash, with no process spawn, no import of an executor, no socket/network.
- A future builder slice (section 14) produces the bundle but still wires NO consumer: it does
  not call Hermes, does not create or drain a FoundUpJob, does not invoke build_plan_generator
  to execute. Consumer wiring is a separate, later, explicitly-gated slice.
- dry_run_required is a constant true; the bundle can never represent a live build request.

---

## 11. Role Boundary: OpenClaw / WRE / Hermes / AI Overseer / External Agents

| Component | Bundle relationship | Authority in the bundle |
|-----------|---------------------|-------------------------|
| OpenClaw | declared orchestrator (provenance) | none; runtime still maps intent->job in code |
| WRE | declared coordinator (wre_coordinator=true) | none; router/_ACTION_BACKEND_MAP decides backend |
| Hermes | declared executor; receiving shape = WorkspaceBinding | the bundle FEEDS WorkspaceBinding-shaped inputs; Hermes re-applies dry_run + D0-D6 |
| AI Overseer | declared auditor ONLY | may receive audit evidence; MUST NOT be assigned builder/executor authority |
| External agents | external_agent_allowed=false, contract_required=true | disabled; FUTURE_PHASE; no seam; cannot bypass gates |

AI_OVERSEER_NOT_BUILDER holds: ai_overseer imports no build machinery (#770 finding,
re-confirmed); its only build-shaped surface is a simulated MCP stub. The bundle's
`auditor: ai_overseer` is an audit-routing label, never an execution grant.

---

## 12. Readiness and Label-Reconciliation Handling

- All readiness flags (manifest_ready, build_ready, autonomous_execution_ready) remain FALSE
  until a LATER dry-run evidence slice proves them with redacted evidence. The bundle copies
  the readiness snapshot read-only and cannot set any flag true (validator rejects truthy
  readiness; the bundle inherits that invariant).
- voteballots and trade carry status NEEDS_LABEL_RECONCILIATION (the #770 data-quality
  conflict: registry/manifest SPECIFIED_NOT_IMPLEMENTED vs a real src+test surface). Rule:
  NEEDS_LABEL_RECONCILIATION BLOCKS build-readiness / dry-run ELIGIBILITY
  (`dry_run_eligible=false`) but STILL ALLOWS manifest-contract validation (the bundle may be
  built and validated for those two, just marked not dry-run-eligible until the label is
  reconciled).

---

## 13. Validator Follow-Up NIT: module_path Exact-Match Tightening

Finding (direct read): `_expected_module_path_matches` (validator.py:159-166) returns
`parent == norm_module OR parent.endswith("/" + norm_module)`. The `endswith` fallback is a
SUFFIX match: a module_path of e.g. `whack_a_magat` would match ANY manifest whose parent
ends in `/whack_a_magat`, and a crafted nested path could match a shorter declared suffix.

- magadoom cross-domain (Q10): module_path `modules/gamification/whack_a_magat` currently
  matches via the EXACT branch (`parent == norm_module`), so the legitimate cross-domain path
  works WITHOUT relying on the suffix fallback. The exact-canonical-path rule must keep
  supporting cross-domain paths (do NOT restrict to a `modules/foundups/` prefix); the correct
  tightening is exact-full-path match, not a prefix restriction.
- Is the NIT a blocker for #771? NO. No consumer is wired, and all 6 current module_paths are
  exact, so the suffix fallback is never decisive today. #771 stands.
- Must it be tightened before any RUNTIME consumer trusts module_path? YES. A future
  ContextBundle derives `allowed_source_roots` from module_path; if a mislocated/colliding
  module_path passed via `endswith`, the bundle could bound a build to the wrong directory
  (a wrong-target / path-confusion risk). There is also NO negative test today
  (test_foundup_manifest_validator.py covers the magadoom happy path at :49 but not a
  suffix-mismatch rejection).
- Recommendation: a SMALL validator-hardening slice (drop the `endswith` branch -> exact-only;
  add a negative test for a mislocated module_path) BEFORE, or bundled WITH, the context-bundle
  builder slice. This is a one-line logic tightening plus a test; no manifest changes needed
  (all 6 already match exactly).

---

## 14. Recommended Next Implementation Slice

Two ordered slices, both still pre-consumer:

1. FOUNDUP_MANIFEST_VALIDATOR_MODULE_PATH_EXACT_MATCH_HARDENING_PHASE1 (tiny, W6, W10-gated):
   tighten `_expected_module_path_matches` to exact-only; add a negative test. No manifest/
   runtime change.
2. WRE_CONTEXT_BUNDLE_BUILDER_PHASE1 (read-only producer, W6, W10-gated): implement a pure
   function that reads a validated manifest and emits the ContextBundle of section 5 (refs +
   digests + provenance, size-capped, traversal-checked, forbidden-excluded, dry_run-only).
   It MUST NOT: wire any consumer, call Hermes/OpenClaw/WRE/AI Overseer, run a build, include
   file bodies, assert any gate passed, choose an executor, enable external agents, or promote
   readiness. It SHOULD reuse the existing receiving shapes (WorkspaceBinding allowed/blocked/
   evidence fields; ExecutionReceipt/BuildEvidence for evidence orientation) rather than invent
   a parallel structure (Q17: the correct receiving shape already exists).

Only AFTER both land should a separate, ULTRA-effort, explicitly-gated slice consider wiring a
dry-run consumer that reads a ContextBundle - out of scope here.

---

## 15. Internal Review Verdict

READY. Decision-only audit; one doc; no manifest/validator/runtime/registry/test mutation; no
consumer wired; no build run. The minimum ContextBundle is defined (small, non-executable,
validator-backed, path-bounded, gate-rechecked, dry-run-only, unable to self-authorize/choose
privileged executors/include forbidden paths/promote readiness). Repo-concatenation is blocked
by refs+digests+size-cap; gates are re-checked not trusted; module_path suffix-match NIT is
evaluated (not a #771 blocker; must tighten before consumer wiring); voteballots/trade
NEEDS_LABEL_RECONCILIATION blocks dry-run eligibility but not validation; AI Overseer stays
auditor; external agents stay disabled. Q17 reuse confirmed (WorkspaceBinding/ExecutionReceipt).
HoloIndex was rated LOW with a recorded index gap and used only for discovery.

---

## 16. WSP_97 Truth Boundary Checklist

Declared items: 32 - Rows: 32 - All YES

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_AUDIT_ONLY | YES | Only this doc added under docs/audits/architecture/; nothing else changed |
| 2 | NO_MANIFEST_MUTATION | YES | No foundup_manifest.json edited; manifests read-only (section 4) |
| 3 | NO_VALIDATOR_MUTATION | YES | foundup_manifest_validator.py read only; NIT is a recommendation (section 13) |
| 4 | NO_RUNTIME_CONSUMER_WIRING | YES | No OpenClaw/Hermes/WRE/AI Overseer wired to contracts (section 10) |
| 5 | NO_BUILD_RUN | YES | No build executed; bundle is a pure read+hash envelope (section 10) |
| 6 | NO_READINESS_PROMOTION | YES | readiness stays false; bundle copies read-only (section 12) |
| 7 | CITES_PR_770 | YES | Section 2; readiness/ecosystem findings carried forward |
| 8 | CITES_PR_771 | YES | Section 2/4; validator + 6 manifests are the audited base |
| 9 | CONTEXT_BUNDLE_NON_EXECUTABLE | YES | Section 5/10; refs+digests only, no process/import/network |
| 10 | NO_REPO_CONCATENATION | YES | Section 9; file_refs + size cap, never bodies |
| 11 | GATES_RECHECKED_NOT_TRUSTED | YES | Section 8; required_gates are names to re-run, no pass asserted |
| 12 | AI_OVERSEER_NOT_BUILDER | YES | Section 11; auditor label only; no build imports (#770 re-confirmed) |
| 13 | EXECUTION_ROUTING_DECLARATIVE_ONLY | YES | validator.py:360-370 declarative_only/can_self_authorize; section 6/14 |
| 14 | EXTERNAL_AGENTS_DISABLED | YES | external_agent_allowed=false (validator.py:354-358); section 11 |
| 15 | COMMANDS_ARGV_OR_NULL_ONLY | YES | validator.py:123-198; section 5/7; build/test/dry_run argv-or-null |
| 16 | FORBIDDEN_PATHS_EXCLUDED | YES | Section 7/9; refs matching forbidden_paths excluded |
| 17 | MODULE_PATH_EXACT_MATCH_NIT_EVALUATED | YES | Section 13; endswith fallback evaluated; not a #771 blocker; tighten pre-consumer |
| 18 | VOTEBALLOTS_TRADE_LABEL_CONFLICT_HANDLED | YES | Section 12; NEEDS_LABEL_RECONCILIATION blocks dry-run eligibility, allows validation |
| 19 | NO_CABR_PAYOUT_DAO | YES | No CABR/payout/DAO readiness asserted; such paths D6-blocked/excluded |
| 20 | ASCII_CLEAN | YES | Byte-checked: zero bytes > 127 before commit |
| 21 | HOLOINDEX_RATED_NOT_TRUSTED | YES | Section 3.1 signal table; no hit used as proof |
| 22 | HOLOINDEX_GAPS_RECORDED | YES | Section 3.2 HOLOINDEX_GAP_CONTEXT_BUNDLE_ARTIFACTS; missed files listed |
| 23 | CONTEXT_BUNDLE_VERSIONED | YES | Section 5; context_bundle_version field required |
| 24 | MANIFEST_DIGEST_REQUIRED | YES | Section 5; manifest_sha256 + build_contract/execution_routing digests |
| 25 | SOURCE_COMMIT_REQUIRED | YES | Section 5/9; source_commit anchors staleness |
| 26 | PATH_TRAVERSAL_BLOCKED | YES | Section 7/9; absolute/UNC/drive-root/symlink/.. rejected |
| 27 | CONTEXT_SIZE_BOUNDED | YES | Section 5/9; max_context_bytes hard cap, reject/trim |
| 28 | FILE_REFS_NOT_REPO_CONCAT | YES | Section 9; included_file_refs are {path,sha256} only |
| 29 | GATE_PASS_NOT_SERIALIZED | YES | Section 8; no gate-pass boolean carried |
| 30 | EXECUTOR_SELECTION_CODE_OWNED | YES | Section 6/14; executor re-mapped via ALLOWED_EXECUTORS/router |
| 31 | SECRETS_EXCLUDED_OR_REDACTED | YES | Section 7; secrets excluded; EvidencePacket #768 redaction required |
| 32 | STALENESS_INVALIDATES_BUNDLE | YES | Section 5/9; source_commit/manifest_sha256 mismatch invalidates |

---

## ModLog (WSP 22)

- 2026-06-09: W9 read-only architecture audit defining the minimum safe WRE/Hermes context
  bundle to be read (later) from FoundUp manifests/build contracts. Decision-only: no
  manifest/validator/runtime/registry/test mutation, no consumer wired, no build run, no
  readiness promotion. Defined a versioned, digest-anchored, path-bounded, non-executable
  ContextBundle (refs+hashes, size-capped, traversal-checked, forbidden-excluded, dry-run-only)
  that cannot self-authorize, choose a privileged executor, include forbidden paths, or promote
  readiness; required_gates are re-checked not trusted. Evaluated the #771 module_path
  endswith suffix-match NIT: not a #771 blocker (no consumer; all 6 module_paths exact), but
  must be tightened to exact-only with a negative test before any runtime consumer trusts
  module_path. voteballots/trade NEEDS_LABEL_RECONCILIATION blocks dry-run eligibility but
  allows validation. Confirmed the correct receiving shape already exists
  (WorkspaceBinding/ExecutionReceipt/BuildEvidence) - reuse, do not duplicate. HoloIndex rated
  LOW (0 HIGH, 2 MEDIUM, 10 LOW) with HOLOINDEX_GAP_CONTEXT_BUNDLE_ARTIFACTS recorded; all
  evidence via direct read on 89f4ea09c. Named next slices: validator exact-match hardening,
  then a read-only context-bundle builder. WSP_97 32/32 YES. Left OPEN for W10.
