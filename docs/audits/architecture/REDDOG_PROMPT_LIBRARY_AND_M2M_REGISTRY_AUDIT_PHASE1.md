# REDDOG_PROMPT_LIBRARY_AND_M2M_REGISTRY_AUDIT_PHASE1

Status: AUDIT
Mode: decision-only
Base: origin/main 4523f2af1
Date: 2026-07-13
WSP lock: WSP_00, WSP_15, WSP_22, WSP_50, WSP_95, WSP_97, WSP_99, WSP_109

Truth-label legend:
- OBSERVED: directly read from the repository or HoloIndex output during this audit.
- INFERRED: conclusion from OBSERVED evidence.
- SPECIFIED_NOT_IMPLEMENTED: required by this audit, not present as working code.
- NEEDS_VERIFICATION: not used as a final claim in this document.

## Purpose

012 currently coordinates RedDog work by copying worker prompts and worker returns between
windows. That does not scale. RedDog needs a governed prompt/orchestration memory so it can
author, approve, dispatch, track, verify, and learn from worker prompts without relying on
manual paste mediation.

This audit asks whether the repository already has that system.

Verdict:

```text
PROMPT_TEMPLATES_EXIST
WSP_99_M2M_EXISTS
PROMPT_FIXTURES_EXIST
EXECUTED_PROMPT_LIBRARY_MISSING
PROMPT_RECEIPT_REGISTRY_MISSING
PROMPT_OUTCOME_MEMORY_MISSING
```

The right next move is not another ad-hoc worker prompt. It is a generic RedDog/WRE
prompt registry. WSP_109 FoundUp prompts should be a domain profile inside that registry,
not the registry itself.

## Direct-read Evidence

| Surface | Evidence | WSP_97 |
|---------|----------|--------|
| Prompt system overview | `prompt/README.md` lists `WSP_SWARM_DAE_PROMPTING_SYSTEM.md`, lane prompts, `0102_M2M_SCHEMA.yaml`, and `m2m_compiler.py`. | OBSERVED |
| WSP_99 protocol | `WSP_framework/src/WSP_99_M2M_Prompting.md` defines ORCH -> Worker M2M packets, context, validation, role, origin, and principal metadata. | OBSERVED |
| M2M compiler | `prompt/swarm/m2m_compiler.py` defines `M2MPrompt`, `M2MCompiler`, compact/YAML serialization, parse, compile, and decompile. | OBSERVED |
| M2M schema | `prompt/swarm/0102_M2M_SCHEMA.yaml` defines envelope, mission, context, execution, validation, and status response fields. | OBSERVED |
| Fidelity gate | `modules/infrastructure/token_efficiency/src/m2m_fidelity_gate.py` defines `CTXHolo`, `RawRef`, `IndexGapEvent`, and fidelity checks. | OBSERVED |
| RedDog extension prompt fixtures | `extensions/foundups_advisory_workers/tests/fixtures.js` contains golden prompts and work-focus fixtures used by extension contract tests. | OBSERVED |
| RedDog prompt authoring | `extensions/foundups_advisory_workers/ModLog.md` records `REDDOG_PROMPT_AUTHORING_DELIVERABLE_CONTRACT_PHASE1` in v0.3.60. | OBSERVED |
| Typed grounding pipeline | `extension.js` exposes `repo_file_targets`, `semantic_targets`, `external_research_targets`, `quoted_reference_blocks`, and grounding telemetry. | OBSERVED |
| Runtime gate | `extension.js` emits `runtime_consumption_gate` and blocks runtime consumption when model, redaction, grounding, output validation, judgment verification, or Fusion quorum fails. | OBSERVED |
| WSP_109 domain fixtures | `WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md` and `docs/audits/architecture/WSP_109_EXAMPLE_FIXTURES_PHASE1.md` exist. | OBSERVED |

## HoloIndex Addendum

All HoloIndex probes in this audit were read-only. No re-index command was run.

| Query | Result | Finding |
|-------|--------|---------|
| `RedDog prompt library executed worker prompts` | Top code hits were RedDog WRE worktree modules; WSP_99 surfaced; no prompt registry surfaced. | INDEX_GAP |
| `WSP 99 M2M prompt registry receipt outcome` | `--bundle-json` surfaced WSP_99 and M2M-adjacent tests, but no prompt registry or PromptReceipt surface. Plain output path hit a display `KeyError: need`. | INDEX_GAP plus CLI_OUTPUT_GAP |
| `RedDog prompt relevance quorum Worker Prompt` | `--bundle-json` surfaced quorum engines, RedDog session docs, WSP_99, and autonomous_slice_worker skill; no prompt registry surfaced. Plain output path hit a display `KeyError: need`. | PARTIAL plus CLI_OUTPUT_GAP |
| `WSP 109 prompt fixtures FoundUp intake` | Surfaced WSP_109, intake transport, onboarding dry-run tests, and WSP_109 audit docs. | HIT for domain profile |

HoloIndex conclusion:

```text
HOLOINDEX_REDDOG_PROMPT_LIBRARY_M2M_REGISTRY_INDEX_GAP_PHASE1
```

Prompt registry concepts are not discoverable as a dedicated system. WSP_99 and WSP_109
are discoverable, but the prompt library / executed prompt receipt layer is missing. The
plain HoloIndex display path also failed on two queries due `KeyError: need`; the JSON
bundle path completed. That failure must be recorded by future freshness receipts instead
of silently falling back.

Boundary:
- RedDog runtime may query HoloIndex.
- RedDog runtime must not re-index HoloIndex.
- WRE/CI owns prompt-library index maintenance after prompt registry artifacts land.

## Current-state Map

| Layer | Current status | Gap |
|-------|----------------|-----|
| Human prompt templates | Present under `prompt/` and scattered docs. | Not execution memory. |
| WSP_99 M2M | Protocol, schema, compiler, and fidelity gate exist. | Not bound to a prompt registry or worker dispatch receipt. |
| RedDog prompt authoring | Extension requires a `## Worker Prompt` artifact for prompt-authoring asks. | Does not persist the prompt as an approved reusable object. |
| Prompt examples | Extension fixtures exist. | They are regression inputs, not a searchable library with outcomes. |
| Prompt approval | Fusion/validation gates exist. | No PromptApprovalReceipt exists. |
| Prompt dispatch | Worker prompts are copied/pasted by 012 or external sessions. | No WRE PromptRun record. |
| Prompt outcome | PR bodies, chat returns, and ModLogs hold evidence. | No canonical PromptOutcome linked to prompt_id. |
| Prompt learning | Successful and failed prompts inform humans. | No automated promotion of patterns into examples/templates. |
| HoloIndex | Can find WSP_99 and WSP_109. | Cannot find a dedicated prompt registry because none exists. |

## WSP_97 Verdict

1. OBSERVED: The repo has a prompt pack and M2M compiler.
2. OBSERVED: The repo has WSP_99 protocol and M2M fidelity work.
3. OBSERVED: The RedDog extension has prompt-authoring gates and fixtures.
4. OBSERVED: Recent RedDog runtime slices added typed extraction, grounding, wardrobe selection, Fusion quorum, and runtime-consumption gates.
5. INFERRED: RedDog is closer to governed operator-loop orchestration than it was, but still lacks prompt memory and prompt-run authority.
6. SPECIFIED_NOT_IMPLEMENTED: A canonical prompt library.
7. SPECIFIED_NOT_IMPLEMENTED: PromptReceipt, PromptApprovalReceipt, PromptRun, PromptOutcome, and PromptPatternPromotion schemas.
8. SPECIFIED_NOT_IMPLEMENTED: Runtime retrieval of approved prompt templates.
9. SPECIFIED_NOT_IMPLEMENTED: Automatic worker dispatch from approved prompt receipts.
10. SPECIFIED_NOT_IMPLEMENTED: HoloIndex freshness receipts for prompt registry lookups.

## Why This Is Not WSP_109-only

WSP_109 is the FoundUp onboarding/intake domain. It should provide FoundUp-specific
prompt profiles such as:

- FoundUp idea -> WSP_109 intake packet.
- WSP_109 intake packet -> create_foundup dry-run plan.
- create_foundup dry-run plan -> scaffold writer dry-run.

The prompt registry must be broader:

- RedDog runtime repair prompts.
- HoloIndex freshness/reindex prompts.
- WRE worker prompts.
- Security/Sentinel prompts.
- OpenClaw/Hermes prompts.
- RTK/M2M token-efficiency prompts.
- FoundUp creation prompts.

Therefore the correct root system is:

```text
REDDOG_PROMPT_LIBRARY_AND_M2M_REGISTRY
```

WSP_109 belongs as a domain profile inside the registry.

## Required PromptReceipt Schema

The first implementation contract should freeze this shape.

```yaml
PromptReceipt:
  prompt_id: string
  prompt_digest: sha256
  prompt_kind: worker_prompt | audit_prompt | verifier_prompt | sentinel_prompt | repair_prompt | m2m_packet
  slice_name: string
  lane: ORCH | A | B | C | D | QA | SENTINEL
  role: architect | worker | verifier | coordinator | validator
  origin: external_principal | internal_handoff | autonomous_trigger
  principal_ref: string | null
  wsp_refs: array[int]
  requested_outputs: array[string]
  in_scope_paths: array[string]
  out_scope_paths: array[string]
  read_first_targets: array[string]
  holoindex_query_digest: sha256 | null
  holoindex_freshness_receipt: string | null
  index_gap_detected: bool
  typed_grounding_receipt_digest: sha256 | null
  wardrobe_selection_receipt_digest: sha256 | null
  m2m_compiled: bool
  m2m_digest: sha256 | null
  raw_ref: string | null
  prompt_relevance_passed: bool
  fusion_quorum_passed: bool
  approved_for_dispatch: bool
  no_runtime_execution_performed: bool
  no_repo_mutation_performed: bool
```

Hard rule: a prompt may not be dispatched by WRE unless `approved_for_dispatch=true`,
`prompt_relevance_passed=true`, and all required grounding/freshness receipts are bound.

## Required PromptRun Schema

```yaml
PromptRun:
  run_id: string
  prompt_id: string
  prompt_digest: sha256
  worker_id: string
  worktree_id: string | null
  branch: string | null
  base_sha: string
  started_at: int
  completed_at: int | null
  status: PENDING | RUNNING | VERIFIED_READY | FAILED | BLOCKED | LANDED
  pr_url: string | null
  files_changed: array[string]
  tests_run: array[string]
  test_result: string
  codeql_status: string | null
  index_gap_events: array[string]
  receipts: array[string]
  no_merge_performed_by_worker: bool
```

## Required PromptOutcome Schema

```yaml
PromptOutcome:
  outcome_id: string
  run_id: string
  prompt_id: string
  status: success | partial | failed | blocked | superseded
  accepted_by: red dog | 0102 architect | 012 sovereign | ci
  landed_sha: string | null
  regressions_added: array[string]
  failure_class: string | null
  reusable_pattern: bool
  negative_fixture_required: bool
  promoted_to_library: bool
  promoted_template_id: string | null
  notes_digest: sha256
```

## Orchestration Model

If RedDog were operating as the 0102 orchestrator, the loop should be:

```text
012 intent
-> RedDog self-deterministic mode selection
-> typed target extraction
-> grounding preflight
-> prompt-library retrieval
-> prompt authoring or template selection
-> WSP_99 M2M compile
-> M2M fidelity gate
-> prompt relevance gate
-> Fusion/Sentinel quorum for risky prompts
-> PromptReceipt stored
-> WRE worker claim gate
-> isolated worktree execution
-> test/CI/CodeQL/review evidence
-> PromptRun stored
-> RedDog verification
-> PromptOutcome stored
-> successful pattern promoted to prompt library
-> HoloIndex re-index/freshness receipt by WRE/CI after merge
```

Fusion's role is review/refutation, not memory. HoloIndex's role is retrieval and
freshness evidence, not prompt authority. WRE's role is execution and durable lane state.
RedDog's role is architect/approver, receipt binder, and policy gate.

## Risks If Not Built

| Risk | Impact |
|------|--------|
| Prompt drift | RedDog generates schema-valid but irrelevant worker prompts. |
| Lane contamination | Outstanding work from one lane appears in another lane's prompt. |
| Duplicate work | RedDog commissions work already completed because prompt outcomes are not indexed. |
| No learning loop | Failed prompts do not become negative fixtures. |
| Manual paste bottleneck | 012 remains the orchestration bus. |
| HoloIndex masking | Direct-read fixtures pass while prompt registry discoverability rots. |
| Unsafe action path | A safely gated action could be derived from an ungrounded or stale prompt. |

## WSP_15 Implementation Sequence

1. `REDDOG_PROMPT_LIBRARY_CONTRACT_PHASE1`
   - Decision contract for PromptReceipt, PromptRun, PromptOutcome, PromptTemplate, and PromptPatternPromotion.
   - No runtime code.

2. `REDDOG_PROMPT_EXAMPLES_FIXTURE_LIBRARY_PHASE1`
   - Move good and bad prompt examples into executable fixture files.
   - Include positive and negative examples for prompt-authoring, DAEmon diagnostics, WSP_109 intake, worker dispatch, Sentinel review, and HoloIndex INDEX_GAP work.

3. `REDDOG_PROMPT_M2M_COMPILATION_GATE_PHASE1`
   - Bind PromptReceipt to WSP_99 M2M compile/decompile fidelity.
   - Require `raw_ref` recovery.

4. `REDDOG_PROMPT_RELEVANCE_AND_QUORUM_GATE_PHASE1`
   - Make prompt relevance and Fusion quorum part of PromptReceipt approval.
   - Critic `None` or missing requested slice blocks approval.

5. `REDDOG_PROMPT_LIBRARY_STORAGE_DRYRUN_PHASE1`
   - Store prompt receipts in a local dry-run registry.
   - No dispatch, no worker execution.

6. `REDDOG_PROMPT_LIBRARY_RETRIEVAL_DRYRUN_PHASE1`
   - Retrieve approved prompt templates by slice/domain/WSP.
   - Emit freshness and INDEX_GAP receipts.

7. `REDDOG_PROMPT_LIBRARY_TO_WRE_DISPATCH_DRYRUN_PHASE1`
   - Produce a WRE dispatch candidate from an approved prompt receipt.
   - No worktree creation.

8. `REDDOG_PROMPT_RUN_OUTCOME_MEMORY_PHASE1`
   - Record PromptRun and PromptOutcome after worker return.
   - Promote success/failure patterns into reusable examples.

9. `REDDOG_PROMPT_LIBRARY_HOLOINDEX_FRESHNESS_PHASE1`
   - WRE/CI indexes prompt library artifacts after merge.
   - RedDog runtime remains query-only.

10. `REDDOG_PROMPT_LIBRARY_RUNTIME_CONSUMPTION_PHASE1`
    - RedDog runtime may select approved prompt templates.
    - Still no live execution without signed authority and the relevant valve.

## Truth Boundary Checklist

| Check | Status |
|-------|--------|
| Docs/audit only | YES |
| No prompt registry implementation | YES |
| No WRE dispatch implementation | YES |
| No extension runtime mutation | YES |
| No HoloIndex re-index | YES |
| HoloIndex query-only addendum included | YES |
| WSP_99 M2M preserved as agent-to-agent prompt layer | YES |
| WSP_109 scoped as domain profile, not root registry | YES |
| PromptReceipt/PromptRun/PromptOutcome marked SPECIFIED_NOT_IMPLEMENTED | YES |
| Runtime authority remains blocked | YES |

## Residual SPECIFIED_NOT_IMPLEMENTED

- `REDDOG_PROMPT_LIBRARY_CONTRACT_PHASE1`
- `REDDOG_PROMPT_EXAMPLES_FIXTURE_LIBRARY_PHASE1`
- `REDDOG_PROMPT_M2M_COMPILATION_GATE_PHASE1`
- `REDDOG_PROMPT_RELEVANCE_AND_QUORUM_GATE_PHASE1`
- `REDDOG_PROMPT_LIBRARY_STORAGE_DRYRUN_PHASE1`
- `REDDOG_PROMPT_LIBRARY_RETRIEVAL_DRYRUN_PHASE1`
- `REDDOG_PROMPT_LIBRARY_TO_WRE_DISPATCH_DRYRUN_PHASE1`
- `REDDOG_PROMPT_RUN_OUTCOME_MEMORY_PHASE1`
- `REDDOG_PROMPT_LIBRARY_HOLOINDEX_FRESHNESS_PHASE1`
- `REDDOG_PROMPT_LIBRARY_RUNTIME_CONSUMPTION_PHASE1`
