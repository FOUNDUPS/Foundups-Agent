# OpenRouter Model Execution-Control Evidence Phase B1 WSP_97 Audit

- Date: 2026-07-24
- Owner: 0102 RedDog Architect / Codex isolated worker lane
- Slice: `OPENROUTER_MODEL_EXECUTION_CONTROL_EVIDENCE_PHASE_B1`
- WSP_15 score: Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19 (P0)
- Base commit: `c7a3373b867efd077b153901db693979eb3966f7`
- Branch: `codex/openrouter-model-execution-control-evidence-phase-b1-20260724`
- Public metadata source: `https://openrouter.ai/api/v1/models`
- Public metadata evidence timestamp: 2026-07-24 (date-granularity; the exact
  request time was not retained in the supplied architect review evidence)
- Schema/type source: `https://openrouter.ai/openapi.json`, schemas
  `ModelReasoning`, `ReasoningEffort`, and `TopProviderInfo`, retrieved
  2026-07-24

## 1. Problem and authority boundary

The direct OpenRouter candidate snapshot already bound model IDs, prices,
context, parameters, freshness, and discovery lineage, but discarded optional
model-level reasoning and top-provider execution assertions. The configured
research runner therefore could not compare its operator-authored controls with
provider-asserted candidate evidence.

This slice may preserve a bounded recognized projection and derive immutable
exact-model evidence from a fresh candidate. It may not discover an execution
endpoint, choose sampling defaults, admit a canonical route, call a provider,
rank or promote a model, alter runtime selection, access credentials, or wire
`main.py`.

## 2. Retrieval and repository evidence

WSP_00 awakening completed in 0102 state and the tracker reported Zen
compliance. WSP 00, 5, 6, 15, 22, 50, 62, 81, and 97 plus the RedDog external
state bootstrap were read before implementation.

The required HoloIndex-first query exited successfully but returned no retrieval
output. This is recorded as an impaired/silent retrieval path, not semantic
evidence. Direct `rg`, file reads, focused tests, module-wide tests, AST checks,
and diff inspection were used as the explicit fallback. No WSP framework file
changed, so WSP_81 created no knowledge backup.

The current OpenAPI marks `mandatory` and `is_moderated` required in their
complete upstream objects. B1 deliberately accepts a strict partial recognized
projection for legacy compatibility and evidence collection, but grants that
partial evidence no route or runtime admission. Explicit null is preserved only
where the schema permits it. Null entries inside `supported_efforts` fail
closed because the public selector semantics do not define a coherent meaning.

## 3. Assumptions, evidence, and confidence

| Assumption | Evidence | Confidence |
|---|---|---|
| Existing v1 candidates remain valid | Legacy rows without either optional control rehydrate and emit explicit absent evidence controls | High |
| Optional provider assertions must not become admission requirements | Partial objects, empty effort lists, omitted fields, and explicit null effort claims are retained | High |
| OpenRouter nullable fields remain distinct from omission | Presence-aware evidence retains explicit null `default_effort`, `supported_efforts`, `context_length`, and `max_completion_tokens` claims | High |
| Unknown nested fields can be ignored safely | Only recognized fields enter the sanitized projection; secret/prose/default/limit fixtures do not survive | High |
| Malformed recognized claims must poison duplicate groups | Type, enum, order, bound, relationship, and duplicate-group tests fail closed | High |
| Candidate evidence can bind one exact model deterministically | Exact model, candidate, receipt, freshness, price, parameter, record/control digest, and evidence-ID tests pass | High |
| Provider assertions identify a canonical executable route | False: no independently admitted endpoint route exists | High |
| Provider assertions determine safe sampling defaults | False: optional fields may be partial, empty, omitted, or null | High |
| This evidence authorizes a live K3-versus-GLM comparison | False: transport, usage, sampling, route, and runtime-directory gates remain open | High |

## 4. Failure modes and mitigations

| Failure mode | Mitigation | Residual boundary |
|---|---|---|
| Provider adds prose, provider name, key-like data, defaults, or limits | Drop every unknown field before equality, digest, and evidence construction | Global bounded JSON parsing remains the outer input boundary |
| A malformed recognized field hides inside a duplicate set | Any malformed member poisons the complete duplicate ID group | None within candidate normalization |
| Omitted controls are confused with explicit null | Presence-aware reasoning and top-provider evidence preserves the distinction | Later admission must define sufficiency |
| Mandatory reasoning contradicts explicit disable/none claims | Reject only contradictory co-present assertions | Null/partial provider assertions remain non-authoritative |
| Model alias or case variation selects another record | Exact string identity and exactly one matching candidate record | A future trusted alias map would require separate evidence |
| Attacker edits evidence and recomputes its ID | Rebuild the entire expected evidence from the supplied canonical candidate and compare exact payloads | Candidate authenticity remains bounded by the existing discovery trust model |
| Provider metadata is mistaken for runtime permission | Dedicated provider-asserted trust class and explicit documentation HALT | Canonical route/sampling/usage/transport evidence is still required |

## 5. Alternatives considered

1. Hard-code K3 reasoning and pricing into runtime selection. Rejected: current
   provider metadata is candidate evidence and changes over time.
2. Preserve entire OpenRouter model records. Rejected: descriptions, provider
   identity, default parameters, limits, and possible secret-like material are
   outside this boundary.
3. Require every reasoning field before evidence construction. Rejected:
   OpenRouter assertions are optional and partial; this would turn collection
   into unauthorized admission.
4. Treat provider assertions as an executable route. Rejected: endpoint,
   sampling, usage, and transport evidence remain independent unsatisfied gates.
5. Add a pure provider-asserted evidence boundary with adversarial offline
   tests. Accepted.

## 6. Decision

**PROCEED** with the bounded optional projection and immutable
`provider_asserted_model_execution_controls` evidence.

**HALT** canonical execution admission and all live comparative model work until
independent evidence supplies:

- exact executable route and endpoint admission;
- explicit task/campaign sampling-control policy;
- authoritative provider-reported usage;
- pre-buffer response-byte transport bounds;
- bounded artifact reads and an identity-preserving runtime-directory claim;
- benchmark, verifier, promotion, and runtime-binding evidence already required
  by the existing architecture.

The K3 fixture reflects the cited public provider-asserted metadata only as an
offline test claim:
`moonshotai/kimi-k3`, 1,048,576 context, canonicalized per-token prices of
`0.000003` input and `0.000015` output, efforts `max/high/low`, non-mandatory
reasoning, unmoderated top-provider status, and an explicit null
`max_completion_tokens`. No runtime value is hard-coded by this slice and no
provider call was made in this worker lane. The public response is not treated
as authenticated canonical route or runtime authority.
