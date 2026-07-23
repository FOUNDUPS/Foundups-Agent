# OpenRouter Endpoint Route Single-Call Admission Phase B2A WSP_97 Audit

- Date: 2026-07-24
- Owner: 0102 RedDog Architect / Codex isolated worker lane
- Slice: `OPENROUTER_ENDPOINT_ROUTE_SINGLE_CALL_ADMISSION_PHASE_B2A`
- WSP_15 score: Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19 (P0)
- Original implementation base: `545f4b3b828cf083c20e266961c6df2fde1565c7`
- Integrated base: `a3c13f05299bf745a1fc01650e1ae91f0db2f820`
- Branch: `codex/openrouter-endpoint-route-admission-phase-b2a-20260724`
- Schema source: `https://openrouter.ai/openapi.json`, retrieved 2026-07-24
  (`PublicEndpoint`, `EndpointStatus`: `0, -1, -2, -3, -5, -10`)
- Route documentation: `https://openrouter.ai/docs/api-reference/chat-completion`
  and `https://openrouter.ai/docs/features/provider-routing`, retrieved
  2026-07-24

## 1. Problem and authority boundary

Phase B1 retained provider-asserted model controls but did not independently
identify one executable endpoint route or certify one bounded job. B2A may
project externally supplied endpoint fixtures, preserve exact immutable
lineage, and issue a pure task-specific eligibility receipt. It may not fetch
metadata, authenticate, read credentials, call a model/provider, wire a gateway
or configured runner, mutate runtime selection, or grant live authority.

## 2. Repository retrieval

WSP_00 awakening was applied in 0102 architect state. WSP 00, 15, 22, 50, 62,
and 97 plus the module README, INTERFACE, ROADMAP, ModLog, and TestModLog were
read before implementation. The HoloIndex-first offline query exited 0 in
lexical-only mode and returned unrelated hits, so it was recorded as impaired
semantic retrieval. Direct `rg`, bounded file reads, tests, AST inspection, and
diff review were the truthful fallback.

No framework WSP changed, so no WSP knowledge backup was required. The receipt
lists only verified framework paths that exist at the pinned base.

### Integration migration after WSP_97 PR #1334

The one focused B2A commit was rebased without conflict onto verified
`origin/main` `a3c13f05299bf745a1fc01650e1ae91f0db2f820`. This is a receipt
migration and integration correction, not a claim that the original retrieval
and research actions were rerun. Their truthful evidence is preserved.

The receipt migrated to `wsp97_execution_receipt.v1.1`, binds the exact
integrated base in `repository_context`, and retains canonical tracked WSP
paths/IDs. Integration RED proved that the Chat Completions control object used
the internal budget name `max_completion_tokens`. The corrected object contains
exactly `max_tokens`, `reasoning`, and `provider`; internal
`max_completion_tokens` remains separately bound for budgeting. Admission IDs
and the rehydration expectation are derived again from that corrected object.
The endpoint fixture bytes and endpoint-evidence IDs are unaffected because
they contain no request-control payload.

Integration RED was `2 failed, 34 passed`. Post-correction validation was `65`
focused endpoint/admission tests, `134` combined protected catalog/execution-
control tests, and `712 passed, 2 skipped` for the full AI Gateway. Ruff,
WSP_62, JSON/diff checks, and the WSP_97 v1.1 CLI with exact expected base
passed. This validation is integration evidence; it does not relabel earlier
research/retrieval actions as newly performed.

## 3. Assumptions and evidence

| Assumption | Evidence | Confidence |
|---|---|---|
| Endpoint payloads can identify one exact route | Strict model equality, exact tag selection, duplicate rejection, and base-tag/prefix collision rejection | High |
| Endpoint prices supersede model-summary prices | Exact canonical Decimal reconciliation and independent policy caps; both values remain in the receipt | High |
| An unknown zero-valued pricing key is safe to drop | False; additive cost-schema drift is rejected outside the complete explicit allowlist | High |
| Null and omission mean the same | False; presence flags preserve nullable caps, status, and quantization distinctly | High |
| Official negative endpoint statuses may remain evidence | Yes; they survive projection but fail the initial trusted exact `(0,)` admission policy | High |
| Status-policy membership proves availability | False; `endpoint_status_policy_accepted` is only a policy-membership proof | High |
| A trusted policy may weaken the parameters emitted by the request | False; policy normalization and independent admission derivation both require exact `max_tokens` and `reasoning` controls | High |
| Internal budget vocabulary may be copied directly to Chat Completions | False; wire controls use exact `max_tokens`; `max_completion_tokens` remains internal evidence only | High |
| Explicit `supports_max_tokens=false` can coexist with an emitted completion cap | False; the contradiction rejects before eligibility | High |
| Missing `supports_max_tokens` means unsupported | Not by itself; exact endpoint and model supported-parameter evidence may independently satisfy the requirement, but explicit false wins | High |
| Optional request price may be silently normalized to zero | False; presence is retained and absence becomes zero only under a named, content-digested PublicPricing schema policy | High |
| Provider route availability certifies a job | False; a trusted policy and content-bound intent are independently required | High |
| Job eligibility permits output training | False; training always fails without separate permission evidence | High |
| Requesting ZDR can rely on endpoint-list data | False; the endpoint schema supplies no sufficient ZDR evidence, so the request fails closed | High |
| This receipt permits a live call | False; authority is fixed to `eligibility_only` and HALTED reasons remain encoded | High |

## 4. Failure modes and mitigations

| Failure mode | Mitigation | Residual boundary |
|---|---|---|
| Secret-like or provider prose crosses the boundary | Allowlist projection before evidence construction; unknown fields are dropped | Upstream fixture supplier remains trusted to supply the exact bytes/receipt |
| Ambiguous provider tag routes to a variant | Reject duplicate tags and base tags when any `tag/...` variant is present | Future alias policy needs separate evidence |
| Optional price dimensions evade budget math | Preserve recognized dimensions and reject nonzero/overridden dimensions | Authoritative post-call usage is still absent |
| Provider adds an unknown cost dimension with a zero default | Reject every pricing key outside the explicit allowlist before projection | A future schema addition requires reviewed code/policy |
| Forward-unknown status is treated as healthy | Projection accepts only the current official enum | A future enum value requires reviewed code/policy |
| Omitted or known-negative status reaches execution | Require presence and membership in trusted exact `(0,)` policy | Policy membership is not authoritative availability |
| Policy names only a subset of emitted controls | Require exact immutable policy parameters and independently derive the mandatory set from the emitted request | Provider parameter evidence may still change and must match both sources |
| Internal completion-budget key leaks into the wire overlay | Assert exact three-key wire set and explicit absence of `max_completion_tokens` | No provider call is authorized by the corrected object |
| Model metadata explicitly denies max-token support | Reject `supports_max_tokens=false`; omitted/unknown needs exact supported-parameter evidence | Provider execution remains halted |
| Optional request price absence is erased | Preserve `request_price_present` and bind schema-policy ID, semantics digest, and acceptance proof | This is not authoritative provider billing or usage |
| Evidence is edited and its ID recomputed | Rebuild endpoint and model evidence from independent supplied sources and compare exact payloads | Authentic source transport is not implemented |
| Context and endpoint caps disagree | Enforce prompt, completion, and combined context bounds independently | Provider-side tokenization remains authoritative after a call |
| Eligibility is consumed twice | Fixed `max_calls=1`, but live authority stays halted | Atomic durable consumption remains unimplemented |
| Response exceeds memory policy before accounting | Bind `max_response_bytes` in policy/admission | Transport-level pre-buffer enforcement remains unimplemented |

## 5. Alternatives considered

1. Reuse model-list `top_provider` as route admission. Rejected because it does
   not identify an exact endpoint tag or independent per-route controls.
2. Fetch endpoints inside the admission builder. Rejected because it would mix
   network/authentication authority into a pure evidence gate.
3. Assume ZDR or training permission from endpoint availability. Rejected
   because the supplied endpoint schema does not prove either policy.
4. Allow endpoint fallback and later inspect provider metadata. Rejected
   because post-response display metadata cannot prevent wrong-route execution.
5. Trust a caller-selected subset of required parameters. Rejected because the
   policy could weaken controls the canonical request always emits.
6. Treat missing request price as zero without evidence. Rejected; the
   interpretation is named, content-digested, presence-preserving, and local to
   the current PublicPricing contract.
7. Reuse the internal completion-budget field name on the wire. Rejected
   because Chat Completions requires `max_tokens`.
8. Bind an exact no-fallback route and one trusted evaluation intent while
   explicitly halting transport. Accepted.

## 6. Decision

**PROCEED** with pure offline endpoint-route evidence and
`CanonicalSingleCallAdmission` as task-specific eligibility evidence.

**HALT** all live provider execution until independent work supplies:

- authenticated endpoint observation;
- authoritative live endpoint availability;
- atomic durable admission consumption;
- authoritative provider usage reconciliation;
- explicit caller/configured-runner wiring review;
- response-byte enforcement before transport buffering;
- an identity-preserving exclusive runtime directory.

Availability, job certification, and output-training permission remain separate
facts. `endpoint_status_policy_accepted` does not collapse availability into job
certification. The request-price schema proof does not prove billing or usage.
No live K3, GLM, OpenClaw, Hermes, gateway, model, or provider call was made by
this slice.
