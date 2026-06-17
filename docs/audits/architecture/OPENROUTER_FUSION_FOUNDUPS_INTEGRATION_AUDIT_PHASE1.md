# OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1

**Slice**: OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1
**Worker-Lane**: W9 / AUDIT
**Type**: READ-ONLY architecture audit. DECISION-ONLY. No code, no dependency, no env change, no API call, no OpenRouter key read, no runtime wiring.
**Base SHA**: 6f651a8c6 (origin/main at dispatch)
**Discipline**: WSP_00 zen state; WSP_97 Truth Boundary; WSP_00 / WSP_50 / WSP_84 / WSP_87 / WSP_97.

---

## 1. Executive Summary

OpenRouter Fusion is a multi-model "panel answers in parallel -> judge compares" engine, available both as the `openrouter/fusion` model alias and the `openrouter:fusion` server tool (same pipeline). The official docs verify every load-bearing claim in the dispatch; the server tool is explicitly beta (RISK, not assumption).

**Recommendation: ADOPT Fusion as a Hermes worker-panel reasoning engine, advisory-only, behind a redaction gate -- but build the FusionAdapter CONTRACT first, not runtime wiring.**

- **Placement**: under Hermes, attaching at the single gate-cleared seam in `hermes_job_executor.py` (`execute()`, between guard-allowed and dispatch). HoloIndex supplies context but does not call Fusion; OpenClaw enforces policy/gates; WRE stores receipts; the FoundUps consensus layer scores Fusion output against WSP 15 / 50 / 77 / 97. Fusion output is advisory until FoundUps verifies it -- it never becomes canonical authority.
- **First surface**: a typed `FusionAdapter` contract + a `ModelContributionReceipt` dataclass (sibling to the existing `ProofOfComputeReceipt`), with mock/local dry-run only. Follow-up slice: `HERMES_FUSION_ADAPTER_CONTRACT_PHASE1`.
- **Privacy classification: BLOCKED_PENDING_REDACTION_GATE.** OpenRouter's docs do not document how multi-provider panel context is handled. Sending HoloIndex/repo context externally requires a redaction gate before any live call.
- **Local fallback: LOCAL_FALLBACK_PRESENT** (gemma-270m + qwen3/3.5-4b + qwen-coder-7b), but marked lower-confidence `LOCAL_FALLBACK`.
- **Stale-landed flag**: the OpenClaw integration manifest declares OpenRouter `status: "landed"`, but the owner module `modules/infrastructure/openrouter_client/` is an empty shell (added then reverted). This is a verified contradiction the adapter slice must correct, not inherit.

---

## 2. OpenRouter Fusion Source Verification

Verified by reading the two official docs only (no API call, no key, no Fusion request):
- A = https://openrouter.ai/docs/guides/features/plugins/fusion
- B = https://openrouter.ai/docs/guides/features/server-tools/fusion/

| # | Claim | Status | Evidence (quote + source) |
|---|-------|--------|---------------------------|
| 1 | alias and server tool use the same pipeline | VERIFIED | "This is the same pipeline behind the `openrouter/fusion` model alias" (B); "These behave identically." (A) |
| 2 | panel models answer in parallel | VERIFIED | "a panel of models answers in parallel, a judge compares their responses" (B) |
| 3 | panel and judge can use `openrouter:web_search` / `web_fetch` | VERIFIED | "`openrouter:web_search` and `openrouter:web_fetch` are enabled on both the panel and the judge calls" (B) |
| 4 | judge returns structured consensus / contradictions / partial coverage / unique insights / blind spots | VERIFIED | "returns structured analysis as JSON: consensus ..., contradictions, partial coverage, unique insights ..., and blind spots" (A); fields `consensus`, `contradictions`, `partial_coverage`, `unique_insights`, `blind_spots` (B) |
| 5 | server tool is beta; API/behavior may change | RISK (beta-unstable) | "Server tools are currently in beta. The API and behavior may change." (B) |
| 6 | server tool gives more control: outer/panel/judge model | VERIFIED | "the most control: choose your own outer model ... configure the panel and judge independently." (B) |
| 7 | `analysis_models` supports 1-8 models | VERIFIED | "1-8 models allowed." (A and B) |
| 8 | `tool_choice: "required"` forces Fusion | VERIFIED | "To force fusion on every request, set `tool_choice: \"required\"`." (B) |
| 9 | degradation: failed panel / judge failure / hard error | VERIFIED | partial: "some panel models error but at least one succeeds ... status: \"ok\" ... `failed_models`"; judge: "panel succeeds but the judge fails ... does not error ... omits `analysis`"; hard: "status: \"error\" ... only when it can't produce any useful output" (B) |
| 10 | recursion protection exists | VERIFIED | "Panel and judge models cannot recursively invoke `openrouter:fusion` ... bounded to a single level." (B) |

**Not refuted; none unverified.** Beta status is the one RISK. Additional findings:
- **Pricing / rate limits**: NOT documented as policy; credits/rate-limit appear only as panel-failure triggers (B). Treat cost/rate as RISK (Section 10).
- **Privacy / data-handling**: NOT documented on either page. The panel fan-out implies prompt/context reaches multiple upstream models, but the docs neither confirm nor deny handling. Treated as an OPEN QUESTION, not an inferred fact -> drives the redaction gate (Section 9).

---

## 3. Current FoundUps Orchestration Map

```
User request
  -> OpenClaw policy / intent gate     openclaw_permission_policy.py (resolve_autonomy_tier:86, check_permission_gate:227,
                                       check_source_permission:114 fail-closed); openclaw_model_policy.py (parse_model_switch_target)
  -> HoloIndex memory retrieval        holo_index/qwen_advisor/pattern_memory.py (ChromaDB @ holo_index/memory/chroma);
                                       telemetry.py JSONL; SQLite stores (foundups.db, violations.db)
  -> Hermes foreman plan               wre_core/src/hermes_job_executor.py HermesJobExecutor.execute():1536
        gate sequence:
          validate(1570) -> build_request(1579) -> HXA30 classify D0-D6(1583)
          -> HXA27 token validation(1591) -> HXA#746 token writeback(1616)
          -> HXA23 destructive guard(1619)  [guard ALLOWED at 1669]
          -> Step 3 dispatch(1672)          [real delegation BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED:1849]
  -> [PROPOSED] Fusion worker-panel run    <-- attaches between 1669 and 1672 (gate-cleared, pre-dispatch)
  -> FoundUps consensus scoring            WSP 15 / 50 / 77 / 97 (WSP_framework/src/)
  -> Model Contribution Receipt            sibling of proof_of_compute_receipt.py ProofOfComputeReceipt:140
                                           emitted via receipt_emitter.py -> pavs_verification_seam.py
  -> HoloIndex worker-performance memory   append-only JSONL (telemetry.py record_advisor_event:30 idiom)
```

**Existing provider/model abstraction (PARTIAL -- three non-unified pieces):**
- `ai_gateway/src/model_registry.py` -- model catalog; `ModelInfo.provider` (`:23-31`); providers openai/anthropic/google/xai/lm_studio_local/ollama (`:41-302`). **No `openrouter` provider.**
- `ai_gateway/src/ai_gateway.py` -- runtime router; `_setup_providers()` hardcodes 4 providers as a dict literal (`:136-215`); `_call_provider()` dispatches via hardcoded `if provider.name == ...` (`:382-396`). **No pluggable provider seam.**
- `foundups/agent/src/hermes_model_router.py` -- capability router, LM Studio local-only (`:51-98`). No external providers.

**Existing receipt/evidence patterns (the shapes a Model Contribution Receipt mirrors):**
- Typed: `moltbot_bridge/src/proof_of_compute_receipt.py` `ProofOfComputeReceipt` (`:140`); `compute_summary` e.g. `{model, tokens_in, tokens_out}` (`:187-191`); `evidence_refs` (`:193`); truth enums `VerificationStatus` / `PayoutStatus.NOT_EVALUATED` / `CABRStatus.NOT_SUBMITTED`; `to_dict/from_dict` (`:228-292`); `generate_receipt_id` (`:308`).
- Append-only JSONL: `holo_index/qwen_advisor/telemetry.py record_advisor_event:30`; escalation store `wre_core/reports/daemon_self_audit_escalations.jsonl`.

---

## 4. Proposed Fusion Placement

**Fusion belongs under Hermes as a worker-panel reasoning engine.** Justification (HERMES_PLACEMENT_JUSTIFIED):

1. Hermes `execute()` is the single delegation path and already enforces the full gate sequence (Section 3). The seam **between guard-allowed (`:1669`) and dispatch (`:1672`)** is the only point where a job is gate-cleared but not yet handed to a delegate. A panel run inserted earlier would reason over un-gated (untrusted) input; inserted later it would bypass WSP 97 truth-field discipline.
2. Every terminal `HermesDelegationResult` hard-codes `real_execution_performed=False, verification_complete=False, cabr_ready=False, payout_ready=False` (dataclass `:447-451`). Attaching here makes the panel output itself an observability artifact, never a real-execution or verification claim.
3. **HoloIndex supplies context; it does not call Fusion** (HOLOINDEX_DISCOVERY_NOT_RUNTIME_AUTHORITY). HoloIndex retrieval is discovery, not proof; its memory is read into the foreman plan, and the panel reasons over redacted `context_refs`, not a live HoloIndex call.
4. **OpenClaw enforces policy and gate boundaries** (it is upstream of Hermes); **WRE stores execution/receipt evidence**; the **FoundUps consensus layer scores** the panel output against WSP 15 / 50 / 77 / 97.
5. **Fusion output is advisory until FoundUps verifies it** (MODEL_OUTPUT_ADVISORY_NOT_CANONICAL).

Placement answers (audit Q1/Q2): live in Hermes; reuse `model_registry.py` (catalog -- add an `openrouter` provider entry) and mirror `ai_gateway.py`'s `ProviderConfig`/`_call_*` pattern, but a new pluggable provider seam is required because providers are hardcoded literals in two places.

---

## 5. Authority Boundary

**What must remain canonical (Q3):**

| Authority | Lives in | Preserved by |
|-----------|----------|--------------|
| OpenClaw policy / permission | `openclaw_permission_policy.py` (`resolve_autonomy_tier:86`, `check_permission_gate:227`, `check_source_permission:114` fail-closed) | Fusion runs downstream of the tier/permission decision; never resolves its own tier |
| OpenClaw model routing | `openclaw_model_policy.py` (`parse_model_switch_target`) | panel/judge selection routes through the alias surface, not a hidden router |
| WSP | `WSP_framework/src/` (WSP 15 scoring, WSP 50 pre-action, WSP 77 coordination, WSP 97 truth boundary) | consensus layer scores panel output against these; agents do not replace 0102 authority (WSP 77) |
| Repo / PR | git + `gh`; pre-merge `W10_gate_worker` | Fusion cannot merge/write; a human/external 0102 gate merges |
| HoloIndex memory | `pattern_memory.py` (ChromaDB), JSONL telemetry, SQLite | discovery + worker-performance memory, never runtime authority |
| WRE receipts/evidence | `proof_of_compute_receipt.py` + `receipt_emitter.py` + `pavs_verification_seam.py`; `.hermes_evidence/{job_id}/`; RedDog state | the Model Contribution Receipt is an evidence artifact, not an authority grant |

**What Fusion must NEVER do (Q4):** no merge, no code write, no gate pass, no CABR / payout / source-authority mutation, no self-granted permission.

**Hard trust-boundary to preserve**: `PolicyFlags.from_dict()` (`foundup_job_contract.py:284-323`, HXA #746) forces ALL security/permission/gate flags and the four `capability_token_*` flags to `False` regardless of inbound data; only `dry_run_mode` is preserved. Server authority comes exclusively from runtime validation writeback inside `execute()` (Step 2.4). A Fusion worker-panel must never carry `True` gate flags to grant itself a passing gate.

---

## 6. Model Contribution Receipt Contract

A typed dataclass, sibling to `ProofOfComputeReceipt`, persisted one-per-line via the append-only JSONL idiom (`record_advisor_event`), with bulky panel artifacts under `.hermes_evidence/{job_id}/`. Required fields (Q6):

```
ModelContributionReceipt {
  receipt_id            : str        # generate_receipt_id() style: rcpt_{suffix}_{ts_hex}_{rand_hex}
  task_id / slice_id    : str
  provider              : "openrouter" | "local"
  mode                  : "alias" | "server_tool" | "local_fallback"
  outer_model           : str
  panel_models          : [str]      # 1-8
  judge_model           : str
  prompt_digest         : str        # NOT raw prompt unless explicitly allowed
  context_refs          : [str]      # NOT full HoloIndex dump
  response_digest       : str
  consensus             : str
  contradictions        : [str]
  unique_insights       : [str]
  blind_spots           : [str]
  failed_models         : [str]      # from Fusion degradation
  cost_estimate         : obj|null   # tokens/cost if available
  latency_ms            : number
  accepted_by_judge     : bool | score
  later_verified_outcome: obj|null   # filled by FoundUps consensus AFTER the fact
  wsp97_truth_outcome   : str        # truth-boundary result
  redaction_status      : "redacted" | "raw_allowed" | "blocked"
}
```

Truth-status defaults mirror `ProofOfComputeReceipt`: verification NOT_EVALUATED, payout NOT_SUBMITTED, CABR NOT_SUBMITTED until the consensus layer fills `later_verified_outcome`.

---

## 7. FusionAdapter Modes

The first implementation surface is the `FusionAdapter` CONTRACT, not full runtime wiring (Q5). Three modes:

1. **`alias_mode`** -- `model: openrouter/fusion`. Simplest; for controlled smoke tests only. Least control.
2. **`server_tool_mode`** -- `openrouter:fusion` with a chosen outer/foreman model + selected `analysis_models` panel (1-8) + judge model; `tool_choice: "required"` to force. Preferred long-term (most control), but beta (RISK).
3. **`local_fallback_mode`** -- simulate panel/judge with local providers (gemma-270m triage + qwen3/3.5-4b general + qwen-coder-7b code via `local_llm_backends.py` / `local_llm_resolver.py` / `ai_engine_singletons.py`). Explicitly marked lower-confidence `LOCAL_FALLBACK`. Used when OpenRouter is unavailable or when context cannot pass the redaction gate.

Adapter reuses `model_registry.py` (catalog), `openclaw_model_policy.provider_has_key` pattern (key presence; add an `openrouter` entry), `key_hygiene.py` / `env_managed.py` (env plumbing). The empty `modules/infrastructure/openrouter_client/` shell must be (re)built by the adapter slice, not assumed present.

---

## 8. Failure / Degradation Model

Mapped 1:1 to OpenRouter's verified status semantics (Q7):

| FoundUps state | OpenRouter signal | Receipt handling |
|----------------|-------------------|------------------|
| `ok_with_failed_models` | `status: "ok"` + `failed_models[]` (some panel error, >=1 succeeds) | record `failed_models`; usable, note reduced panel breadth |
| `ok_without_analysis` | `status: "ok"`, `analysis` omitted (panel ok, judge failed) | record consensus-absent; treat as raw panel only, lower confidence |
| `hard_error` | `status: "error"` (no useful output; e.g. all panel failed / insufficient credits / rate-limited) | no advisory output; fall back to `local_fallback_mode` or abort the optional panel step |

The panel step is OPTIONAL and non-fatal: a hard error must never block the Hermes job, only omit the advisory enrichment. Beta status (claim 5) means these shapes are themselves a RISK and must be covered by tests (Section 12) before any live call.

---

## 9. Privacy / Redaction / Secret Boundary

**Classification: BLOCKED_PENDING_REDACTION_GATE** (Q8/Q9/Q12).

Rationale: OpenRouter's Fusion docs do NOT document how multi-provider panel context is handled, and the panel fans context out to up to 8 upstream models. Therefore any HoloIndex/repo context sent to OpenRouter crosses an external, networked, beta boundary with undocumented retention.

**Must be redacted before any Fusion call:**
- All secrets / API keys / tokens / `.env` values (never egress; only key NAMES exist in-repo today).
- Raw private repo content / source; send `context_refs` (identifiers), not full HoloIndex dumps.
- `prompt_digest` (hash/summary), not the raw prompt, unless an explicit allow is set.
- PII / personal data beyond public PR identities.

**Secret boundary (verified):** there is no central provider-key loader; keys are read ad-hoc via `os.getenv` (`ai_gateway.py:142-199`); `key_hygiene.py` stores sha256 fingerprints only (`:61-63`). `.env.example` has NO `OPENROUTER_*` entries today; `OPENROUTER_API_KEY` exists only as a NAME in the OpenClaw manifest and one manifest-consistency test. The redaction gate is a hard precondition: until it exists and is tested, live Fusion calls stay BLOCKED.

---

## 10. Cost / Rate / Provider Risk

- **Cost**: not documented as a policy by OpenRouter; a 1-8 model panel + judge multiplies token spend per request. The receipt must capture `cost_estimate` / token usage where available, and a per-task budget cap belongs in the adapter (RISK, not assumption).
- **Rate limits**: documented only as a panel-failure trigger; treat as a degradation source (Section 8), not a guarantee.
- **Provider/beta risk**: the server tool is beta -- API and behavior may change (RISK). `alias_mode` is more stable than `server_tool_mode`; smoke-test on `alias_mode`, adopt `server_tool_mode` behind a feature flag with the degradation tests green.
- **External dependency**: Fusion is external + networked + paid. The optional, non-fatal placement (Section 8) bounds the blast radius; `local_fallback_mode` preserves function when OpenRouter is degraded or context cannot be redacted.

---

## 11. Gap Analysis

| Gap | Status | Evidence |
|-----|--------|----------|
| `openrouter` provider in the model catalog | MISSING | `model_registry.py` lists openai/anthropic/google/xai/lm_studio_local/ollama only (`:41-302`) |
| Pluggable provider seam (vs hardcoded literals) | MISSING | `ai_gateway.py:_setup_providers/_call_provider` hardcode 4 providers (`:136-215,382-396`) |
| OpenRouter client implementation | MISSING (stale-landed) | `modules/infrastructure/openrouter_client/` is an empty shell (added `a0fad35b3`, reverted `6f952f6b9`); manifest `openclaw_integration_manifest.json:86-104` claims `status:"landed"` -- CONTRADICTION to correct, not inherit |
| `OPENROUTER_*` env in `.env.example` | MISSING | names exist only in the OpenClaw manifest + one manifest-consistency test; not in `.env.example` |
| Central provider-key loader | MISSING | keys read ad-hoc via `os.getenv`; closest is `openclaw_model_policy.provider_has_key:263-275` |
| Runtime multi-model council / FusionAdapter / Model Contribution Receipt | MISSING | no first-party council class; `cabr_consensus_*` is CABR scoring, not a model council |
| Designed critic/gate roles (prior art) | PARTIAL (paper) | `WORKER_ORCHESTRATION_READ_ONLY_ANALYSIS_PHASE1.md` (#736) defines `critic_worker` + `W10_gate_worker` + 5-category gate, decision-only -- never built |
| LOCAL_FALLBACK panel | PRESENT | gemma-270m, qwen3/3.5-4b, qwen-coder-7b resolvable via `local_llm_backends.py` / `local_llm_resolver.py` -- LOCAL_FALLBACK_PRESENT |
| Vendored Fusion-like prior art (not wired) | PRESENT (vendored) | `vendor/hermes-agent/tools/openrouter_client.py` + `mixture_of_agents_tool.py` -- upstream, not in first-party `modules/` |

---

## 12. Recommended Roadmap

Rollout path docs-only -> adapter -> dry-run -> gated runtime (Q11):

1. **Phase 1 (this doc)**: decision-only audit. DONE.
2. **`HERMES_FUSION_ADAPTER_CONTRACT_PHASE1`** (next slice): typed `FusionAdapter` contract + `ModelContributionReceipt` dataclass; mock/local dry-run only; NO live OpenRouter call; NO API key read; tests for degraded result shapes (Section 8); AST guard -- no subprocess, no repo write, no merge authority. Corrects the stale `openrouter_client` shell + manifest `landed` claim.
3. **Dry-run**: `local_fallback_mode` panel end to end through the Hermes seam, emitting Model Contribution Receipts; consensus layer scores against WSP 15/50/77/97. Still no external call.
4. **Redaction gate**: build + test the Section 9 redaction (context_refs, prompt_digest, secret/PII scrub); BLOCKED_PENDING_REDACTION_GATE lifts only when this is green.
5. **Gated runtime**: `alias_mode` smoke test behind a feature flag, then `server_tool_mode` behind the flag, advisory-only, output non-canonical until FoundUps verifies.

**Tests required before any live OpenRouter call (Q12):** degraded result shapes (`ok_with_failed_models`, `ok_without_analysis`, `hard_error`); redaction enforcement (no secret/raw-repo egress); advisory-not-authority (receipt truth fields stay False; no gate flag set True); AST guard (no subprocess / repo write / merge); budget cap honored.

---

## 13. WSP_97 Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | OPENROUTER_DOCS_VERIFIED | YES | Section 2; both official pages read, 10/10 claims cited. |
| 2 | FUSION_BETA_STATUS_RECORDED | YES | Section 2 claim 5 = RISK; Sections 8, 10. "Server tools are currently in beta." |
| 3 | ALIAS_AND_SERVER_TOOL_DISTINGUISHED | YES | Section 2 claim 1; Section 7 modes 1-2 (alias vs server_tool). |
| 4 | PANEL_AND_JUDGE_BEHAVIOR_VERIFIED | YES | Section 2 claims 2-4 (parallel panel; judge consensus/contradictions/etc). |
| 5 | DEGRADATION_MODES_RECORDED | YES | Section 8 maps ok-with-failed / ok-without-analysis / hard-error. |
| 6 | HERMES_PLACEMENT_JUSTIFIED | YES | Section 4; seam between `hermes_job_executor.py:1669` and `:1672`. |
| 7 | OPENCLAW_POLICY_AUTHORITY_PRESERVED | YES | Section 5; `openclaw_permission_policy.py` + PolicyFlags HXA #746 fail-closed. |
| 8 | HOLOINDEX_DISCOVERY_NOT_RUNTIME_AUTHORITY | YES | Section 4.3; HoloIndex supplies context, does not call Fusion. |
| 9 | MODEL_OUTPUT_ADVISORY_NOT_CANONICAL | YES | Sections 4.5, 5; advisory until FoundUps verifies; never authority. |
| 10 | CONTRIBUTION_RECEIPT_DEFINED | YES | Section 6; ModelContributionReceipt sibling of ProofOfComputeReceipt. |
| 11 | NO_API_CALL_NO_KEY_READ | YES | Only public docs fetched; no OpenRouter request; no key read (Section 9). |
| 12 | PRIVACY_REDACTION_GATE_REQUIRED | YES | Section 9; BLOCKED_PENDING_REDACTION_GATE; undocumented OpenRouter data handling. |
| 13 | LOCAL_FALLBACK_CLASSIFIED | YES | Section 7 mode 3; LOCAL_FALLBACK_PRESENT (gemma-270m, qwen3/3.5-4b, qwen-coder-7b), lower-confidence. |
| 14 | NO_RUNTIME_WIRING | YES | Decision-only; contract recommended, no wiring (Sections 7, 12). |
| 15 | NO_CODE_CHANGE | YES | Only this doc + ModLog written; no .py touched. |
| 16 | FILE_SCOPE_EXACTLY_TWO | YES | This audit doc + root ModLog.md. |
| 17 | ASCII_CLEAN | YES | Byte-checked 0 non-ASCII at write time. |

**Declared == Actual: 17/17 YES.**

---

## 14. Internal Review

Phase 0 HoloIndex ratings recorded (Section 3 + below); external docs verified by direct fetch; internal seams/receipts/authorities verified by direct read with file:line. Discovery ratings: model-gateway queries MEDIUM/HIGH (one FALSE_LEAD: "Fusion ... receipt" returned CABR consensus, not a Fusion panel -- correctly classified, no such concept in-repo); council/receipt queries MEDIUM with a known slice-ID indexing gap (direct read filled it). HoloIndex was used as discovery, not proof.

**Return conditions applied:** no pluggable provider abstraction exists -> recommend the FusionAdapter contract only; external context egress -> BLOCKED_PENDING_REDACTION_GATE; no doc claim refuted (claim 5 = RISK, not assumption); local fallback buildable -> LOCAL_FALLBACK_PRESENT (not invented).

**Internal Review Verdict: MERGE_READY.** Stop at MERGE_READY; do not self-merge. Independent external 0102 gate merges.

Follow-up (do NOT build here): `HERMES_FUSION_ADAPTER_CONTRACT_PHASE1`.

---

## Cross-References

| Document | Location |
|----------|----------|
| OpenRouter Fusion plugin docs | https://openrouter.ai/docs/guides/features/plugins/fusion |
| OpenRouter Fusion server-tool docs | https://openrouter.ai/docs/guides/features/server-tools/fusion/ |
| Hermes seam | modules/infrastructure/wre_core/src/hermes_job_executor.py |
| Receipt pattern | modules/communication/moltbot_bridge/src/proof_of_compute_receipt.py |
| OpenClaw policy | modules/communication/moltbot_bridge/src/openclaw_permission_policy.py |
| Model catalog | modules/ai_intelligence/ai_gateway/src/model_registry.py |
| Worker-orchestration prior art | docs/audits/architecture/WORKER_ORCHESTRATION_READ_ONLY_ANALYSIS_PHASE1.md |

---

*Decision-only architecture audit. No code, no dependency, no env change, no API call, no OpenRouter key read. Synthesized from official-doc verification + 3 read-only discovery lanes under WSP_97 Truth Boundary discipline.*
