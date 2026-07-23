# Configured AutoResearch Gateway WSP_97 Assumption Audit

- Date: 2026-07-24
- Owner: 0102 RedDog Architect / Codex isolated worker lane
- Decision timestamp: 2026-07-24T05:17:28+09:00
- Slice: `OPENROUTER_AUTORESEARCH_CANARY_PHASE1`
- WSP_15 score: Complexity 5 + Importance 5 + Deferability 5 + Impact 5 = 20 (P0)
- Live-activation evidence staleness: 48 hours

## 1. Problem and authority boundary

The configured AutoResearch runner needs a fail-closed path for future external
model comparisons without allowing partial campaigns, route substitution,
prompt leakage, stale append artifacts, or unverifiable success receipts.

This slice is authorized to harden the default-off runtime and its offline test
seams. It is not authorized to activate live provider execution, rank K3
against GLM, promote a model, bind a runtime champion, or treat operator-authored
budget claims as canonical catalog facts.

## 2. Assumptions, evidence, and confidence

| Assumption | Current evidence | Confidence |
|---|---|---|
| Configured mode remains default-off | Root startup default is `deterministic_fixture`; configured admission requires explicit paths, allowlist, total-call cap, and mode | High |
| A complete campaign can be rejected before its first provider call | Rehydrated plan/candidates/tasks produce an exact selected-role x normalized-task count checked against `runner_max_total_calls` | High |
| Phase 1 can execute multi-call or panel campaigns safely | False: configured admission requires exactly one executable planned call and rejects every multi-call or panel campaign before caller entry | High |
| Provider route aliases are not authorized | Candidate assignment suffix must equal `api_model`; no trusted alias mapping exists | High |
| Prompt egress is bounded and inspected | Source digest, final wrapped character limit, and canonical audit-only guard are checked before caller entry | High |
| Attempt and success evidence is tamper-detecting | IDs, statuses, routes, digests, costs, and call lists rehydrate and recompute | High |
| Budget/catalog metadata is trustworthy | The bundle contains an operator-supplied self-authenticated catalog-claim digest, but is not reconciled with the canonical catalog | Low |
| Reported token usage proves actual provider usage | The adapter currently derives whitespace estimates unless an injected caller supplies usage; no authoritative provider-usage receipt is bound | Low |
| Response buffering proves the campaign output cap | The transport may buffer up to the gateway's global 1 MiB response bound; this is not a model-budget-specific byte bound | Low |
| Runtime input and receipt reads are allocation-bounded | False: current JSON and JSONL readers use whole-file reads | High |
| Preflight path freshness and alias checks remain stable through execution | False: no exclusive runtime-directory claim prevents path replacement between check and use | High |

## 3. High-impact failure modes and mitigations

| Failure mode | Current mitigation | Residual boundary |
|---|---|---|
| A two-task or panel campaign reaches partial execution | Phase 1 rejects every planned call count other than exactly one before runner construction | Atomic whole-campaign preparation is required before a later phase may admit multi-call or panel execution |
| A candidate assignment silently routes through a provider alias | Exact assignment suffix/API-model equality | Trusted aliases require a future signed mapping |
| Append artifacts contain stale records or alias inputs/outputs | Windows-normalized canonical-path comparison and absent/empty write-target admission | Runtime directory ownership remains an operator responsibility |
| Output evidence append fails after a provider call | `EVIDENCE_FAILED` terminal receipt; no `COMPLETED` or success receipt | The attempted call remains consumed |
| Terminal completion persistence fails after durable evidence append | Indeterminate result and orphan evidence; no success receipt for semantic admission | Operator cleanup/reconciliation is required |
| Duplicate same-role evidence is hidden by map collapse | Semantic verifier retains all matching records and rejects duplicate roles | None within the deterministic verifier |
| Live cost/usage exceeds local estimates | Live execution is halted | Requires authoritative provider usage and bounded response handling |
| A large input or receipt file causes unbounded allocation | Live execution is halted | Requires bounded streaming readers with explicit byte/record/depth limits |
| A runtime artifact is replaced after preflight | Live execution is halted | Requires an exclusive runtime-directory claim or equivalent identity-preserving check/use boundary |

## 4. Alternatives considered

1. Enable a small K3-versus-GLM canary now. Rejected: catalog claims, sampling
   controls, endpoint identity, authoritative usage, and response-byte bounds
   are not all admitted evidence.
2. Trust OpenRouter aliases from the operator budget file. Rejected: the file
   is self-authenticated operator evidence, not an independently trusted route
   mapping.
3. Keep per-sample caps only and rely on the runner to stop later. Rejected:
   that permits partial campaigns and real calls before discovering the global
   limit.
4. Proceed with default-off hardening and offline injected tests. Accepted:
   it improves the future boundary without expanding live authority.

## 5. Decision

**PROCEED** with default-off defensive hardening, offline injected callers, and
durable receipt verification.

**HALT** all live configured-provider execution and comparative ranking until
phase B supplies:

- canonical catalog admission for exact provider, endpoint, route, prices,
  reasoning and sampling controls;
- authoritative provider-reported usage bound into receipts; and
- model-budget-specific bounded response-byte handling, or an equivalent
  independently verified transport bound;
- bounded streaming reads for every input and receipt artifact; and
- an exclusive runtime-directory claim, or an equivalent identity-preserving
  freshness and alias boundary across preflight and execution.

This audit expires for any future live-activation decision 48 hours after
2026-07-24, or immediately when any cited contract, provider catalog, endpoint,
pricing, transport, or prompt-guard behavior changes. Structural WSP_97 receipt
validation treats evidence references as opaque and does not override this
HALT decision.
