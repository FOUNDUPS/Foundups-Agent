# Foundups®Agent Interface

## Purpose

`foundups-fusion-worker` is a local Cursor/VS Code extension whose user-facing product name is Foundups®Agent. It opens a RedDog Architect advisory surface backed by OpenRouter models through `scripts/advisory_model_once.py`.

It is an IDE-side proof surface for the future RedDog/pfMALL/WRE intake pattern. It does not implement pfMALL runtime wiring, WRE dispatch, FoundUp registration, repository creation, or CABR verification.

Foundups®Agent is the product surface. RedDog is the 0102 digital-twin architect inside it. Fusion is one internal reasoning mode, not the product identity.

## RedDog and the Recursive 0102 DAE Ecosystem

012 does not orchestrate every worker. 012 talks to RedDog. RedDog participates in the recursive 0102 DAE ecosystem. Autonomous WRE/DAE agents perform bounded system work under Hermes/OpenClaw/WRE governance.

### Architecture Stack

```text
012 work focus
  -> RedDog digital twin / architect interface
  -> recursive 0102 DAE ecosystem
```

### Layer Roles

| Layer | Role |
| --- | --- |
| RedDog | Digital-twin architect/interface. 012's first contact point. |
| Hermes | Scaffolding, lifecycle, scheduling, queues, receipts. Not policy authority. |
| OpenClaw | Policy and intent gate. |
| HoloIndex | Memory and retrieval. |
| Skillz/Rolodex | Capability catalog. |
| Autonomous WRE/DAE agents | Code, docs, tests, ops, promotion, FoundUp launch. |
| Sentinels | Critique, truth, drift, regression review. Review only, no execution. |
| WRE | Repo and process authority. Verification and dispatch. |
| CABR/pAVS | Benefit validation, routing, reputation. |
| 012 | Work focus, testing, sovereign authorization, override. |

### Autonomy Boundary

Autonomous WRE/DAE agents are NOT 012 work. 012 provides work focus, testing, sovereign approval, and override. 0102 DAEs communicate recursively and perform bounded autonomous work.

## Authority Boundary

| Capability | Status | Boundary |
|---|---|---|
| Advisory model review | YES | OpenRouter request after Fusion redaction gate passes |
| Bounded repo context | YES | Extension auto-gathers WSP/HoloIndex/editor/git/Skillz context by WSP_15 tier and sends it through redaction gate |
| HoloIndex recall | YES | `HOLO_SKIP_MODEL=1 --bundle-json` first; offline lexical fallback only if bundle recall fails |
| WSP_00/WSP_97/WSP_15 prompting | YES | System prompt requires role lock, truth labels, proposed fixes, and MPS priority |
| Repo edits | NO | No write tool exposed to model |
| Shell execution by model | NO | Extension host runs only bounded local context/bridge commands; model cannot execute Skillz/OpenClaw/Hermes |
| Merge/PR authority | NO | Advisory output only |
| CABR/payout/source authority | NO | Blocked by Fusion redaction gate and prompt contract |
| pfMALL integration | SPECIFIED_NOT_IMPLEMENTED | Roadmap only |
| FoundUp onboarding automation | SPECIFIED_NOT_IMPLEMENTED | Roadmap only; WSP_109 packet production is not implemented here |

## F0 Safety Boundary

F0 is the foundation Foundups-Agent repo. Foundups®Agent must never mutate F0 automatically.

The extension may gather bounded context and produce advisory review packets. It must not execute model-generated code, install packages, create persistence, write files, mutate repositories, publish artifacts, or call Skillz/OpenClaw/Hermes/WRE execution surfaces directly. Any future execution path must be a governed handoff where WRE retains repo/process authority and 012 remains sovereign for test, land, publish, and override decisions.

External repositories are assessed through advisory WSP intake before they can become FoundUps candidates. The extension can recommend a FoundUp intake packet and integration risk report; it cannot automatically enroll or mutate an external repo.

## Governed Repo Work Order Contract

RedDog is the 0102 architect interface — **not an authority owner**. RedDog receives **bounded delegated capability for one work order after fresh verification**; it does not "have authority."

| Artifact | Location |
|---|---|
| Authority contract + schema | `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md` |
| Slice queue | `extensions/foundups_advisory_workers/ROADMAP.md` |

**Dry-run validator (no mutation):** `modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py` — validates envelope + HoloIndex evidence packet; returns `WOULD_ACCEPT` / `WOULD_REJECT` / `WOULD_ACCEPT_WITH_RETRIEVAL_GAP`. Extension v0.3.27 does not invoke it yet.

**Permission probe (read-only):** `modules/platform_integration/github_integration/src/reddog_github_permission_probe.py` — `probe_repo_permission()` produces fresh `repo_permission_snapshot` evidence. Extension does not invoke it yet.

**OpenClaw policy gate (no execution):** `modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py` — `evaluate_work_order_policy_gate()` composes dry-run + permission freshness + HoloIndex policy; returns `PolicyGateReceipt`. Extension does not invoke it yet.

**Work-order receipt (Hermes-compatible audit):** `modules/communication/moltbot_bridge/src/reddog_work_order_receipt.py` — `emit_work_order_receipt()` persists/emits pre-execution audit records from `PolicyGateReceipt`. Extension does not invoke it yet.

**Runtime invocation dry-run:** `modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py` — `invoke_reddog_work_order_dryrun()` chains policy gate + receipt; returns audit result. Extension does not invoke it yet.

**WRE isolated worktree executor (contract only):** `docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md` — defines future executor cage; **no implementation**.

**WRE executor dry-run planner:** `modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py` — `plan_wre_isolated_worktree_execution_dryrun()`; plan + phase receipts; **no git/worktree mutation**.

**OpenClaw handoff adapter (contract only):** `docs/audits/architecture/REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md` — RedDog → FoundUpJob mapping; OpenClaw owns worker loop; **AssignmentDispatcher not canonical**.

**Specified flow (not implemented in extension v0.3.27):**

```text
authenticated principal -> GitHub permission snapshot -> RedDogGovernedWorkOrder
  -> OpenClaw policy gate -> Hermes lifecycle/receipts
  -> WRE isolated worktree (branch, tests, PR draft)
  -> Sentinel/reviewer opinions (review only)
  -> merge gate (012/operator sovereign valve on F0)
```

**WSP Applicability Preflight (specified):** before any future work-order emission, identify applicable WSPs (WSP_34, WSP_50, WSP_54, WSP_95, WSP_97, WSP_109) and Skillz candidates from HoloIndex; attach evidence refs; block if recall is weak.

**F0 autonomous merge:** SPECIFIED_NOT_IMPLEMENTED — not planned behavior until dryrun, permission probe, OpenClaw envelope gate, WRE executor, and review receipts land.

## Webview Contract

The UI copies the VS Code terminal/chat layout:

1. Header: build/model metadata only.
2. Output scrollback: status, 012 work focus, 0102 output, validation errors, and errors.
3. Working Tail / RedDog action strip (above controls).
4. Control row: **0102 Role**, routing/context pills, tests, Copy MD.
5. Bottom composer: fixed **012 work focus** input.

The output pane owns scrolling. Content must not pass behind the composer.

Keyboard:

- `Enter`: send work focus.
- `Shift+Enter`: newline.
- `Ctrl+Shift+C`: copy redacted review packet.

Copy:

- `Copy MD`: copies a markdown packet with `Run Trace` (role, tier, effort, mode, models, context, redaction, validation), `Work Trail` (allowlisted normalized events, cap 50), and 0102 output.
- Redaction-block runs include `## Redaction Gate Report` (`BLOCKED_LOCALLY`, WSP_97 truth labels, no raw snippets) before any model output.
- Validation-failure runs include `OUTPUT_VALIDATION_FAILED` with local static footer (no extra network call).
- Substantive tasks include `## Governed Handoff Recommendation` (`advisory_only`; bounded digest evidence refs only).
- Status/progress scrollback lines are summarized in Run Trace / Work Trail; raw status lines are not duplicated verbatim unless needed for trace fields.

## 0102 Roles

| 0102 Role | Intended Use |
|---|---|
| RedDog Architect | Default architecture review and FoundUps intake/orchestration reasoning |
| WSP Gate Critic | Gate reports, return-to-author findings, WSP_97 critique |
| Repair Planner | Smallest valid implementation and test-slice planning |
| Smoke Test | Bounded API/bridge checks without broad architecture review |

## Model Modes

| Mode | Traceability | Notes |
|---|---|---|
| FoundUps manual lead + panel | Higher | Stores lead, panel, and synthesis excerpts in review packet |
| OpenRouter Fusion alias | Lower | Black-box Fusion synthesis; individual critic transcripts are not exposed |
| Regular OpenRouter | Single-model | Fast direct lead review |

## HoloIndex Truth Boundary

The model cannot access the filesystem. It receives only the bounded context packet.

If HoloIndex recall reports zero WSP hits, missing Tier-0 docs, stale/offline fallback, or unavailable output, the answer must treat protocol claims as `NEEDS_VERIFICATION` and propose retrieval/index repair before strong claims.

Run Trace HoloIndex scorecard fields (v0.3.22+):

| Field | Meaning | WSP_97 |
| --- | --- | --- |
| `holoindex_status` | Bundle transport result (e.g. `bundle_json_ok`) | OBSERVED |
| `code_hits_count` | Count of code hits returned | OBSERVED |
| `target_recall_ok` | Requested target file/symbol appeared in hits | OBSERVED |
| `index_gap_detected` | Target-specific miss (may be true when `code_hits_count > 0`) | OBSERVED |
| `direct_read_fallback_used` | Offline lexical fallback used | OBSERVED |
| `target_content_included` | Target snippet section present in final bounded context | OBSERVED |
| `target_content_paths` | Relative paths whose snippets were included | OBSERVED |
| `target_content_chars` | Character count of included target snippets | OBSERVED |
| `target_content_omitted_reason` | Why snippets omitted when `target_content_included=false` | OBSERVED |
| `target_content_truncated` | Any target snippet truncated by per-file budget | OBSERVED |
| `target_content_sanitized` | Block-triggering literals replaced before egress | OBSERVED |
| `target_content_sanitized_categories` | Fusion BLOCK categories sanitized (metadata only) | OBSERVED |

Run Trace Unicode normalization fields (v0.3.24+) and bridge UTF-8 invariant (v0.3.25+):

| Field | Meaning | WSP_97 |
|---|---|---|
| `unicode_normalization_applied` | Bridge payload required surrogate replacement before gate | OBSERVED |
| `unicode_replacements_count` | Count of isolated surrogate replacements (counts only) | OBSERVED |
| `unicode_normalization_sources` | Pipe-separated: `prompt`, `context`, `repair_prompt` | OBSERVED |
| `unicode_normalization_form` | `NFC` when normalization ran; `none` when skipped | OBSERVED |

Bridge child env (v0.3.25+): `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`. Python bridge reads stdin via `sys.stdin.buffer` UTF-8 decode so valid Unicode (e.g. U+2014 em dash) is not mis-decoded on Windows before the redaction gate.

`evaluateTargetRecall(taskText, bundleOutput)` and `inferRecallTargetPaths(taskText)` implement target-specific recall inference from bundle `task_retrieval.code_hits`.

Target content egress (v0.3.22+): `buildTargetRecallContentSection(root, taskText, maxChars)` reads workspace-confined snippets for inferred recall targets after HoloIndex path ranking. Snippets pass through `sanitizeTargetSnippetForRedaction()` before inclusion (ADDENDUM F); placeholders use neutral `[SANITIZED_BLOCK:NN]` tokens so category names do not re-trigger the Fusion gate. Telemetry reflects the **final** bounded context string assembled by `buildBoundedRepoContext` (before the 42000-char slice). `buildWsp97ProtocolExcerpt(root, maxChars)` adds a bounded WSP_97 protocol excerpt when the task mentions WSP_97 or truth labels.

Exported helpers for contract tests: `isTargetReadPathDenied`, `resolveSafeRepoFile`, `readBoundedTargetSnippet`, `readBoundedTargetSnippets`, `buildTargetRecallContentSection`, `sanitizeTargetSnippetForRedaction`, `taskMentionsWsp97`, `buildWsp97ProtocolExcerpt`.

## WSP_97 Truth Boundary

Every substantive answer should classify claims:

- `OBSERVED`: present in supplied context.
- `INFERRED`: derived from supplied context but not directly proven.
- `NEEDS_VERIFICATION`: requires local read, test, live run, or external decision.
- `SPECIFIED_NOT_IMPLEMENTED`: documented requirement, not current behavior.

## WSP_15 Output Requirement

Every substantive answer ends with:

```text
## WSP_15 Priority
| Action | Complexity | Importance | Deferability | Impact | MPS | Priority |
|---|---:|---:|---:|---:|---:|---|
| ... | ... | ... | ... | ... | ... | P0-P4 |

## Next Safest Step
...
```

## RedDog Fusion Orchestrator (v0.3.14)

Internal contract layer. Advisory-only. No new authority.

| Function | Purpose |
|---|---|
| `classifyTaskForRedDog(prompt, contextMode, workerType)` | WSP_15-style effort/risk classification |
| `resolveAutoContextMode(classification, selectedContextMode)` | Maps Auto context to `wsp_holo` (REGULAR) / WSP+Holo+Skillz (HIGH) / WSP+Holo+git+Skillz (ULTRA) |
| `resolveAutoEffort(classification, selectedEffort)` | Maps Auto -> regular/high/ultra |
| `resolveModelMode(classification, selectedMode, workerType)` | RedDog WSP work defaults to auditable manual panel |
| `validateRedDogOutput(markdown)` | Required schema section check |
| `buildRepairPrompt(originalPrompt, badOutput, missingSections)` | One bounded repair pass; sanitizes draft for gate |
| `buildRepairBoundedContext()` | Minimal WSP-only context for repair (no HoloIndex resend) |
| `mergeRepairedOutput(primaryContent, repairContent)` | Appends schema supplement to primary Fusion output |

Required substantive output sections:

- Decision
- Findings
- Evidence
- Proposed fixes
- Uncertainties
- WSP_97 Truth Labels
- WSP_15 Priority
- Next safest step

Auto effort rules:

- `ULTRA`: auth/security/secrets/live runtime/public surface/pfMALL/WRE/OpenClaw/Hermes/Kanban/CABR/merge authority/repo creation.
- `HIGH`: architecture, WSP protocol, HoloIndex gaps, extension routing, FoundUp intake, RedDog/pfMALL planning.
- `REGULAR`: simple smoke tests, simple code explanation, non-runtime UI polish.
- If uncertain, choose `HIGH`.

Model and context routing:

- RedDog WSP/security/architecture/runtime work auto-routes to `foundups_fusion` (manual principal + panel).
- Principal/synthesis default: `z-ai/glm-5.2`.
- Adversarial critic default: `deepseek/deepseek-v4-pro`.
- Implementation critic default: `moonshotai/kimi-k2.7-code`.
- REGULAR smoke/simple prompts auto-route to `openrouter_single` with the GLM principal and `wsp_holo` HoloIndex grounding (no Fusion panel, Skillz, or git).
- Context is not a 012-facing selector; it is resolved from WSP_15 tier.
- Skillz/Wardrobe/Rolodex/OpenClaw/Hermes discovery is context only. RedDog may recommend a governed handoff, but this extension cannot execute it.
- `openrouter_fusion_alias` remains implemented for future explicit use, but is not the RedDog default because critic traces are not exposed.
- Repair pass: at most one; uses the same redaction-gated bridge; must not invent evidence.

Review packet additions:

- `task_classification`
- `resolved_effort`
- `resolved_mode`
- `resolved_context`
- `principal_model`
- `panel_models`
- `mode_selection_reasoning`
- `work_focus_digest` (`hash`, `excerpt`, `length` - redacted)
- `wsp_prompt_digest` (`hash`, `excerpt`, `length` - redacted)
- `prompt_construction`: `0102_generated_from_work_focus`
- `output_validation` (`validated`, `missing_sections`, `repair_attempted`, `repair_ok`, `repair_context_mode`, `repair_mode`, `fusion_panel_ok`)

## RedDog Follow-Up Memory (v0.3.28)

In-memory WSP_97-safe continuation from the last successful or `BLOCKED_LOCALLY` run:

- `buildSanitizedContinuationSummary()` — extracts Decision/Findings/WSP_97/WSP_15/Next step summaries; strips secrets and blocked-policy literals.
- `appendContinuationSummaryToWspPrompt()` — appends sanitized summary to the next WSP task prompt when **Use last RedDog packet** is enabled (default ON).
- `state.lastContinuationSummary` — per-tab in-memory only; no disk persistence in Phase 1.
- Copy MD may include a safe **Continuation Summary** section for the stored packet (not raw prior model output).

Does **not** paste raw Copy MD, bounded context, or blocked snippets into follow-up prompts.

## Bridge Hardening (v0.3.16)

| Control | Status |
| --- | --- |
| Python resolver chain | OBSERVED |
| Subprocess output caps | OBSERVED |
| Orphan cleanup on webview dispose | OBSERVED |
| Context/prompt char budget | OBSERVED |
| Panel models cap (max 6) | OBSERVED |
| HTTP retry 429/502/503 only, max 2 | OBSERVED |
| Failure taxonomy (low-cardinality reasons) | OBSERVED |
| Work-focus contract unchanged | OBSERVED |

Failure reasons include: `redaction_blocked`, `missing_key`, `timeout`, `retry_exhausted`, `http_error`, `malformed_response`, `subprocess_failed`, `output_cap_exceeded`.

## 012 Work Focus to 0102 WSP Task Prompt (v0.3.15)

Formal contract:

```text
012 work focus (non-authoritative)
  -> 0102 constructWspTaskPrompt(workFocus, classification, contextQuality, workerType)
  -> redaction gate (prompt + bounded context separately)
  -> OpenRouter bridge
  -> RedDog architect output
```

012 does not prompt RedDog directly. The bridge receives the assembled WSP task prompt, not raw work focus alone. Work focus is embedded inside the WSP prompt under an explicit non-authoritative label.

## WSP_97 Truth Table (v0.3.15)

| Claim | Status |
| --- | --- |
| Auto router REGULAR/HIGH/ULTRA | OBSERVED |
| 012 work focus -> 0102 WSP task prompt layer | OBSERVED |
| Review packet work_focus_digest + wsp_prompt_digest | OBSERVED |
| WORK_FOCUS_NOT_AUTHORITY | OBSERVED |
| WSP_PROMPT_0102_GENERATED | OBSERVED |
| RAW_FOCUS_NOT_SENT_AS_SOLE_AUTHORITY | OBSERVED |
| DIGESTS_NOT_RAW_CONTEXT | OBSERVED |
| ROUTING_UNCHANGED_FROM_0_3_14 | OBSERVED |
| Skillz/Rolodex non-vacuous for YouTube comment ops | OBSERVED |
| Advisory-only; no shell/repo/browser/OpenClaw/Hermes execution | OBSERVED |
| Redaction gate before OpenRouter | OBSERVED |
| Governed handoff contract (typed WRE dispatch) | SPECIFIED_NOT_IMPLEMENTED |
| GitHub permission probe (read-only snapshot) | OBSERVED (github_integration module) |
| OpenClaw work-order policy gate | OBSERVED (moltbot_bridge module); no execution |
| RedDog work-order receipt (Hermes-compatible audit) | OBSERVED (moltbot_bridge module); not live Hermes queue |
| RedDog runtime invocation dry-run | OBSERVED (moltbot_bridge module); no execution |
| WRE isolated worktree executor | SPECIFIED_NOT_IMPLEMENTED (contract doc only) |
| WRE executor dry-run planner | OBSERVED (moltbot_bridge module); no mutation |
| OpenClaw FoundUpJob adapter | SPECIFIED_NOT_IMPLEMENTED (contract doc only) |
| AssignmentDispatcher as worker launcher | FORBIDDEN (simulated scaffold only) |
| Governed repo work order dry-run validator | OBSERVED (OpenClaw bridge module) |
| Governed repo work order (`RedDogGovernedWorkOrder`) | SPECIFIED_NOT_IMPLEMENTED (runtime emission from extension) |
| GitHub permission snapshot per work order | SPECIFIED_NOT_IMPLEMENTED |
| F0 autonomous merge | SPECIFIED_NOT_IMPLEMENTED |
| WSP Applicability Preflight | SPECIFIED_NOT_IMPLEMENTED |
| pfMALL surface binding | SPECIFIED_NOT_IMPLEMENTED |
| Review packet memory / persistence | SPECIFIED_NOT_IMPLEMENTED |
| Bridge hardening (edge-case redaction/repair) | SPECIFIED_NOT_IMPLEMENTED |
| REDDOG_IS_ARCHITECT_INTERFACE | OBSERVED |
| AUTONOMOUS_DAE_WORK_NOT_012_WORK | OBSERVED |
| HERMES_IS_SCAFFOLDING_NOT_POLICY | OBSERVED |
| OPENCLAW_IS_POLICY_GATE | OBSERVED |
| WRE_RETAINS_REPO_AUTHORITY | OBSERVED |
| SENTINELS_REVIEW_NOT_EXECUTE | OBSERVED |
| CABR_PAVS_VALIDATES_BENEFIT | OBSERVED |
| EXTENSION_REMAINS_ADVISORY_ONLY | OBSERVED |

## Redaction Gate Report (v0.3.20)

When redaction blocks before OpenRouter, Copy MD includes `## Redaction Gate Report`. Raw blocked content is never included.

| Field | Notes |
| --- | --- |
| decision | `BLOCKED_LOCALLY` |
| made_network_call | `false` |
| blocked_stage | `pre_openrouter_request` |
| blocked_payload_part | `work_focus` \| `system_prompt` \| `repo_context` \| `holoindex_context` \| `skillz_context` \| `unknown` |
| rule_classes | Detector class names or safe categories |
| rule_counts | Category -> count map |
| raw_snippets_included | Always `false` |
| redacted_payload_digest | `sha256:<64 hex>` when available |
| safe_summary | One sentence, no raw content |
| next_safe_context | `none` \| `wsp_only` \| `narrowed_diff` \| `local_0102_review` |

All fields carry WSP_97 truth labels (`OBSERVED` or `UNKNOWN`). If the gate cannot identify the payload part, report `unknown`; do not infer.

## Governed Handoff Recommendation (v0.3.20+)

Substantive Copy MD packets append `## Governed Handoff Recommendation`:

| Field | Notes |
| --- | --- |
| handoff_needed | `true` \| `false` \| `unknown` |
| target | `WRE` \| `OpenClaw` \| `Hermes` \| `Sentinel` \| `none` |
| authority_level | Always `advisory_only` |
| suggested_slice_name | Bounded slice identifier |
| WSP_15 priority | Inferred from tier |
| required_human_gate | `012_sovereign` \| `none` |
| reason | Conservative blocked-local reason when no model output (e.g. `blocked_context_needs_local_0102_review`) |
| evidence_refs | Bounded digest references only |

Redaction-block-only runs default to `handoff_needed: unknown`, `wsp15_priority: P1`, and `suggested_slice_name: none` unless concrete fix evidence exists.

Extension retains no repo/shell/merge authority.

## External Acceptance Baseline (v0.3.21+)

Foundups(R)Agent external-lane usefulness is measured by a **fixed 15-prompt acceptance pack** documented in `docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`.

| Layer | Scope |
| --- | --- |
| CI | Contract tests, syntax, bridge AST — **no live OpenRouter** |
| 012 manual | Full prompt pack, rubric scoring, Copy MD artifacts, sovereign verdict |
| Artifacts | Redacted records under `docs/acceptance/` — no secrets |

Baseline pass records honest scores on v0.3.21. Replacement pass reruns the same prompts after HoloIndex/dispatch improvements.

Lane B (internal WRE architect / Sakana loop) is **excluded** from this acceptance boundary.

## Public/RedDog Roadmap Boundary

The extension is the IDE-side model for a future RedDog operation surface:

```text
012 work focus
  -> 0102 WSP task prompt assembly
  -> RedDog Architect advisory review
  -> HoloIndex recall
  -> WSP_97 truth classification
  -> WSP_15 priority
  -> WSP_109 intake packet or WRE dispatch recommendation
  -> Skillz/Wardrobe/Rolodex match and WRE/OpenClaw/Hermes governed handoff recommendation
  -> WRE/OpenClaw/Hermes governed execution
  -> pfMALL-visible state after verification
```

This interface documents that direction only. It does not expose a public intake route.
