**Bridge interface: Effect And Process Lifecycle.**

[Interface directory](../../INTERFACE.md). Qualification boundaries below remain as recorded.

<a id="contract-039"></a>

## Single-effect proof handoff design — 2026-10-01

**Pure binding API implemented; authenticated effect handoff remains planned.**
Implementation source base: `252f700fbac4c4adb98f3dd81c3d05eadb8fce66`.
PR#2001's eleven local and exact PR/main controls established the existing domain
separation. The current layer adds structural construction and correlation in
existing owners. The delegated v1 two-child path remains unchanged.

`reddog_elevated_authority_consensus_evidence` now exposes:

```python
build_effect_target_binding(*, parent, target, expected_target, now) -> dict[str, str] | None
effect_target_binding_matches(binding, *, parent, target, expected_target, now) -> bool
```

The builder returns a fresh four-field mapping or `None`; the matcher recomputes
it and returns `False` on invalid input, including `None` supplied with invalid
construction inputs. Neither function authenticates a principal or producer,
issues a grant or permit, signs a request, consumes a lease, or admits a worker.
Local qualification: all 32 frozen new cases passed after all 32 baseline cases
failed at the expected missing-API assertion; both runs had zero errors/skips.
The prior pure-binding PR#2003 is merged/main-verified; see the current layer below.

<a id="contract-040"></a>

### Conditional effect-review verification API — 2026-10-01

`verify_effect_reviewer_decision(*, decision, context, authority_request, target,
expected_target, policy, signature_verifier, reviewer_key_resolver,
runtime_evidence_resolver, now, revoked_key_epochs=frozenset()) -> bool` lives in
the existing `reddog_elevated_authority_consensus_verification.py` owner.

- Decode a plain dictionary with exactly the existing reviewer-decision fields:
  every value nonempty ASCII text, at most4096 characters, total canonical JSON
  at most8192 bytes, with strict lowercase SHA-256 context/selection/runtime
  digests. The fixed schema is `reddog_effect_reviewer_decision.v1`.
- Correlate the exact validated effect context with the current actual parent,
  target and expected target through `effect_approval_context_matches`.
- Require a valid supplied policy whose digest, roles and minimum approvals
  match the context, with context lifetime no greater than policy maximum TTL.
- Require exact reviewer id/provider/role membership; exclude parent, RedDog and
  queue worker identities, parent/RedDog keys, and the author's runtime binding.
- Resolve exact key/runtime evidence classes; match key epoch, model and receipt
  identities/digests; reject revoked epochs and non-integer or expired timestamps
  before signature verification. Verifier result must be exactly `True`.
- Signed input is `reddog-effect-consensus-review.v1.` followed by sorted compact
  ASCII JSON containing every validated decision field except `signature`.
  The opaque nonempty signature is passed unchanged to the supplied verifier.
  All invalid inputs and collaborator exceptions return `False`.

`rehydrate_effect_reviewer_decision(value)` in the existing rehydration owner
only decodes this strict data boundary; it does not authenticate a review.
Delegated public receipt decoding and signing domains remain unchanged.

One-review validity is conditional on supplied policy/resolvers/verifier. It is
not authenticated production provenance, quorum, sovereign effect authority,
requester/beneficiary authorization, a capability/permit, replay consumption or
native admission. No production consumer is wired. An inert recording verifier
tests byte/decision logic; these fixtures are not independent runtime receipts.

Frozen qualification: 82 expected missing-API baseline failures → 82 local
passes. PR #2010 is merged/main-verified at `f4978e12`: exact PR and main CI
each passed all 222 selected cases, plus 74 correspondence, 308 measurement
(two known pytest configuration warnings) and 85 caller cases. All ten PR
checks and both main workflows succeeded; the owned lane is closed. These are
regression counts, not independent proof of runtime authority or retained gain.
Historical pending prose below is superseded by the canonical backlog closure.

Historical PR #2013 prerequisite (now merged/main-verified and closed): 6 frozen
test-only Ed25519 cases through
this unchanged API and the actual public verifier: valid signature accepts;
payload/signature/key tampering and two wrong-domain signatures reject. Local 95
cases pass including 82 prior and 7 structural controls; hosted 228 pending. Keys
exist only in test memory. Supplied resolver provenance and inner-designation
authentication remain unproven; no production caller or authority is added.

<a id="contract-041"></a>

### Connected current reviewer verification API — 2026-10-01

**Implemented in the current 15/P1 layer; locally verified, hosted/publication pending.**
PR #2013 closed at `c9d1273`. The existing consensus verification owner now exposes:

```python
verify_current_effect_reviewer_decision(
    *, owner_config_path, repo_root, decision, context, authority_request,
    target, expected_target, policy, runtime_evidence_resolver,
    revoked_key_epochs=frozenset(),
) -> bool
```

The caller does not inject owner data, a generation boundary, signature verifier or
reviewer-key resolver. The private current-review leaf loads authenticated owner
v5, derives one selection from that same config identity and holds its lease
through confined principal-artifact reading and effect review. The strict
`reddog_reviewer_designation_contract.py` leaf owns the exact 12/14/7-field root,
inner designation and reviewer-entry wire shapes. It bounds the complete prefixed
canonical signing input to 65536 bytes; validation alone authenticates nothing.
Both designation and review use the existing real Ed25519 backend.

Principal v2 adds exactly one designation to the existing identity envelope;
`PrincipalAuthorityRecord` and strict v1 parsing remain unchanged. The existing
supplier's optional `reviewer_authorizations` and `reviewer_principal_records`
carry 1–8 distinct reviewer identities with exact pair/key/repository/FoundUp
coverage; defaults retain v1 and the permission snapshot remains singular v1.
Readiness accepts the v2 principal shape without claiming signature authentication.
Existing grant-owner, transport and source-policy consumers recognize v5; their
separate grant/replay semantics are preserved.

Projection requires every role assigned to the reviewer pair in the pinned policy
to be authorized by the signed designation. Explicit owner/designation/entry and
manifest expiries bound the key; selection lifetime is checked separately. Inputs
are captured and compared after callbacks. Before success, authenticated owner
identity and trusted time are rechecked while the lease is held; the private key
resolver is closed on exit. These sampled checks are not atomic revocation or a
guarantee after return. Runtime evidence is still supplied by the caller.

Local candidate-4 passed 198/198 with no failures/errors/skips, exact IDs, stable
source samples and no unexpected denials. Hosted 331 portable and 8 Linux cases
are pending. The five actual-root cases cover positive, UID, mode, symlink and
anchor-tamper rejection; the last is not a valid signed-rotation proof. Three
existing transport v3/v4/v5 cases complete the Linux selection. This is one scoped
reviewer's conditional validity, not quorum, independent runtime provenance,
effect-scoped sovereign permission, a permit, native admission or retained gain.

<a id="contract-042"></a>

### Authenticated effect-authority qualification — 2026-10-01

Source-qualified at `f4978e12e94e1b0d151b38b16c295d2bda374b23` after
PR #2010's verified merge. The conditional reviewer API above is implemented;
the table below records the **historical pre-composition gaps**. The connected
key portion is now implemented as documented above; runtime/effect authority
and admission remain open.
The earlier scoped absence finding applies to effect-consensus adapters, not
to all identity/runtime verification infrastructure.

| Existing owner | Evidence it actually supplies | Missing effect-review bridge |
|---|---|---|
| `modules/ai_intelligence/ai_gateway/src/model_runtime_binding_use_time_verifier.py` | Re-verifies persisted signed model evidence and issues a one-shot runtime capability; the existing topology consumes that capability. | Bind that authenticated runtime and selection to this reviewer principal and decision. A model capability alone is not review authority. |
| `src/reddog_signer_current_principal_authority_resolver.py` | Selects and leases a signed generation for each resolution. | This is an effectful lease operation, not a passive lookup. Composition needs explicit lifetime/cleanup accounting. |
| `src/reddog_signer_owner_e0_principal_authority.py` and `src/reddog_authority_runtime_store.py` | Confined, digest-bound principal records provide identity, key and repo/FoundUp scopes. | `PrincipalAuthorityRecord` has no reviewer role membership, key epoch/expiry or authorization of this effect. Do not synthesize them from identity. |
| `src/reddog_elevated_authority_consensus_policy.py` | Protocols and strict supplied policy/evidence types; existing sovereign evidence binds a delegated parent. | Trusted policy origin, current reviewer key authority and explicit B/P/T/E plus requester/beneficiary authorization remain unresolved. |
| `src/reddog_elevated_authority_consensus_verification.py` | Conditional verification of one effect review, including actual-input correlation. | Supplied resolver results do not authenticate their own provenance; quorum/permit/replay remain later gates. |

<a id="contract-043"></a>

#### Reviewer-key designation contract — 2026-10-01

**Historical design contract, qualified at `1ff01a9`.** Its connected key
implementation is documented above; this original design is not a runtime grant. The architect selects an explicit, opt-in designation block in
the existing root-owned signer owner configuration as the trust source. This
resolves the source-design choice; it does not select real issuer identities,
provision keys, write operational configuration or authorize a worker.

**Version and ownership:** reserve owner-config v5 as v4 plus
`reviewer_designation_authority`, validated by the existing
`reddog_signer_system_service_manifest_selection_loader.py`. Preserve exact
v1–v4 behavior; none implicitly grants reviewer-designation permission. Reuse
the authenticated-read/revalidation pattern in
`reddog_grant_authority_source_policy_authority.py`; do not reuse its privilege
or secret-grant revocation evidence. The existing owner loader requires Linux,
root ownership, confined paths and secure ancestors; Windows must keep rejecting
this production path. An isolated Linux fixture is not a live installation.

The principal artifact remains `principal_authority_records.json`. A versioned
v2 envelope adds a sibling `reviewer_authorizations` collection to its existing
identity collection. `PrincipalAuthorityRecord` and strict v1 parsing remain
unchanged. Extend the existing resolver artifact supplier, principal parser/
loader and current-principal resolver; no new registry, database or orchestrator.
The outer manifest authenticates generation membership and artifact bytes;
the separately signed inner designation authenticates reviewer permission.

| Boundary | Required signed or trusted fields and semantics |
|---|---|
| Root-owned designation block | Exact schema; explicit `designate_effect_reviewers` privilege; issuer principal/provider/public key/key epoch; exact repository, FoundUp, consensus-policy digest and `reddog_effect_reviewer_decision.v1` domain; exact integer issuance/expiry. Actual values are separately authorized installation inputs. Neither the inner artifact nor manifest signer may supply its own trust anchor. |
| Inner designation | Distinct `reddog-reviewer-designation.v1.` signing domain; issuer identity/epoch and privilege; digest of the trusted designation block; exact repository/FoundUp/policy/decision-domain binding; issuance/expiry; bounded reviewer entries; signature. Canonical sorted compact ASCII JSON excludes only the signature from the signing input. Derive any audit digest; do not accept a self-asserted verified flag. |
| Reviewer entry | Exact principal/provider, public key, reviewer key epoch, authorized roles and issuance/expiry. Require the public key and identity to match the current manifest-bound principal record and its repository/FoundUp scope. Reviewer epoch/expiry are explicit values, never the manifest-signing epoch or selection TTL renamed. |
| Shape and bounds | Freeze exact wire keys before code; reject unknown/duplicate JSON keys and implicit coercions. Retain the existing 64 KiB owner-config and 1 MiB artifact ceilings. At most eight unique reviewer pairs, each with one key/epoch and 1–8 unique bounded ASCII roles. Exact integers only for time; false/zero/unknown evidence cannot become authenticated success. All lifetime intervals must be nonempty. |

The table fixes required semantics and domain separation; final spelling of the
new wire fields and canonical golden bytes must be frozen by the independent
test plan before implementation. Existing v1 field sets are not relaxed.
One exact scope/policy per verification keeps this first layer small; multiple
FoundUps use separately authorized scoped instances, not a wildcard grant.

**Connected use-time contract:** the narrow composition entry remains in the
existing effect-verification owner. It loads one authenticated owner snapshot,
checks the actual parent repository/FoundUp, actual policy digest and effect
decision domain, and derives the generation boundary from that same config ID.
Never combine a refreshed designation allowlist with a cached older boundary.
It validates the current policy shape/digest and captures the exact policy and
actual inputs used by `verify_effect_reviewer_decision`.

Acquire the existing one-use selection and hold its generation lease through
confined artifact reading, inner signature verification, scoped key resolution
and the conditional effect check. Issuer key/privilege must match the explicit
root-owned block before trusting any inner designation. The production composition
uses the existing `reddog_ed25519_signature_verifier_backend.py` public verifier
for designation and review signatures; caller-supplied recording or always-true
verifiers cannot establish authenticated acceptance. The earlier conditional API
keeps its explicit limits. Runtime evidence remains an independent required
input; this slice cannot authenticate it by assertion.
The consumer must not expose a reusable bare reviewer-key resolver/capability
that remains accepted after this composition/lease ends.

The existing `resolve(principal_id, provider)` cannot see a decision role.
Therefore collect **all** roles assigned to that pair in the exact pinned
policy's `reviewer_membership`; require a nonempty set wholly contained in the
signed entry's authorized roles before projecting key/epoch/expiry. Checking
only intersection or `required_roles` is insufficient. A policy assigning
critic+verifier with only a critic grant must reject the projection, even for
critic; this deliberate conservative rule preserves the existing protocol.
Using that projection with another policy or actual scope must fail.

Before acceptance, re-read authenticated owner configuration while the lease
is still held and reject observed config identity changes; recheck trusted time.
Effective authority expiry is the minimum of explicit owner/designation/entry
and manifest expiries, additionally respecting the effect context's existing
policy maximum-TTL/current-time checks. `ElevatedConsensusPolicy` has no absolute
expiry field: do not invent one. Selection lifetime is an additional use-time
gate, not reviewer-key lifetime. Every exception releases the lease and rejects.

**Temporal limit:** these are authenticated sampled owner reads and a fenced
generation at checked boundaries. They do not establish an atomic owner-config
and generation transaction, detect all change-and-restore events, guarantee
authority after return, or make revocation permanent across root-config rollback.
Current-generation reviewer removal/key rotation and explicit owner-block
removal/rotation revoke on the next observed use. Stronger monotonic revocation
requires separate authorized evidence; no new revocation store is selected.

**Historical implementation prerequisites:** loader changes alone cannot advertise v5
support. Existing `reddog_grant_authority_service_owner_binding.py` and
`reddog_signer_independent_grant_authority_client_supply.py` accept v3/v4, while
`reddog_grant_authority_source_policy_authority.py` load/revalidate requires v4.
The principal readiness consumer also requires v1 today; qualify its v2 branch
without widening permission snapshots. Bound the entire inner signing input,
including prefix, to the public verifier's 65536-byte ceiling. Expose trusted
manifest expiry through the current selection without changing legacy launch
values; selection expiry is not a substitute. Reuse the selection already
returned by `_manifest_selection_from_owner` rather than abandoning an extra one.

Qualify all affected schema consumers and preserve v1–v4 rejection/acceptance
behavior before allowing a v5 startup composition. Keep independent grant
re-verification/nonce ownership in the existing signer path; no effect permit,
sovereign authorization or worker activation is added by the key layer.

**Frozen acceptance before code:** legacy v1–v4 controls; exact-field/duplicate/
size/time bounds; unauthorized issuer despite a valid outer manifest/signature;
wrong issuer/key epoch/provider/role/repository/FoundUp/policy/domain; the
critic-only projection and cross-policy reuse counterexamples; owner A versus
boundary B; observed removal/rotation and stale selection; expiration during
verification; lease cleanup and escaped-resolver use; an independently supplied
signed positive reaching the existing effect verifier. Public vectors for other
messages or a recording verifier cannot supply that positive. Test-signing
budget/fixtures and installed authority are separate inputs; this document
authorizes neither operational signing nor production configuration.

Historical next selection: one connected, nonactivating reviewer-key implementation with independent
oracles and version-consumer tests, re-observed under WSP15. Runtime-to-reviewer,
sovereign B/P/T/E/requester/beneficiary authority, quorum/permit/replay and native
admission remain later gates. No source/runtime calls or retained RSI benefit
were produced by this contract-design sprint.

<a id="contract-044"></a>

### Pure effect-context correlation API — 2026-10-01

`effect_approval_context_matches(context, *, parent, target, expected_target, now)`
extends `reddog_elevated_authority_consensus_effect_context.py`. It returns an
exact Boolean. `True` means structural, current correlation, never approval.

- Require the exact `EffectApprovalContext` class and its strict canonical
  validation, including tuple roles; reject malformed manually built values.
- Require exact integer `now`; enforce `issued_at <= now < expires_at`.
- Recompute B through existing `effect_target_binding_matches` using the
  context's binding schema and P/T/E fields plus actual parent/target inputs.
- Revalidate the target payload and require context expiry no later than target
  expiry. The existing B matcher also bounds the target by both parent expiries.
- Return `False` for invalid input or a rejected existing validator. Preserve
  inputs and delegated v1. No production consumer is wired.

Well-formed policy/sovereign references remain untrusted assertions. This does
not resolve them, compare principal and requester identities, equate context
and target nonces, require context issuance after target issuance, limit policy
TTL/skew, or require approvals to be no greater than the number of roles.
Authenticated provenance, independent review and promotion remain separate.

The context decoder from PR #2008 is merged/main-verified (97 hosted controls).
New frozen correlation cases: 43 expected missing-API baseline failures → 43
candidate passes; existing CI now selects 140 cases, hosted results pending.
The guarded local runner is not an OS sandbox or an admitted WRE execution.

<a id="contract-045"></a>

### Inert effect-approval context API — 2026-10-01

The pure binding and structural checks are merged/main-verified in PR#2003/2005;
their owned lanes are closed. At source base `ae922cc30`, the focused sibling
`src/reddog_elevated_authority_consensus_effect_context.py` adds a data carrier
and decoder, not an authenticated producer or a production consumer.

Public APIs: `EffectApprovalContext.to_dict()`,
`rehydrate_effect_approval_context(value)`,
`canonical_effect_approval_context_bytes(context)` and
`canonical_effect_approval_context_digest(context)`.

The wire mapping has exactly these12 fields:

| Fields | Contract |
|---|---|
| `schema_version`, `binding_schema_version` | Exactly `reddog_effect_approval_context.v1` and existing `reddog_effect_target_binding.v1`. |
| `parent_authority_request_digest`, `target_signing_request_digest`, `effect_request_digest` | Declared P/T/E; together with the binding schema they reconstruct B. No digest is recomputed from an actual target at this layer. |
| `sovereign_authorization_digest`, `consensus_policy_digest` | Untrusted references to later independently resolved evidence. All five digests are exact strings containing canonical lowercase SHA-256. |
| `required_approvals`, `required_roles` | Exact integer1–8; plain list of1–8 unique nonempty ASCII strings of at most256 characters. Multiple reviewers may share a role; no approvals≤roles rule. These are policy assertions, not policy decisions. |
| `nonce`, `issued_at`, `expires_at` | Nonempty ASCII nonce≤256 characters; exact integers `0 <= issued_at < expires_at`. No clock, maximum TTL, provenance or freshness decision here. |

The entire sorted compact ASCII JSON wire representation is bounded by the
existing8192-byte consensus limit. No extra keys, subclasses or Boolean-as-integer
coercion. The frozen internal context uses a tuple of roles; exports contain a
fresh list. Canonical APIs reject malformed manually constructed contexts and
non-tuple internal roles. Invalid data raises `ValueError`.

Canonical bytes are `b"reddog-effect-approval-context.v1."` followed by that JSON;
the digest is `sha256:` plus SHA-256 of those bytes. This is deliberately distinct
from delegated v1 context/decision bytes. It is not a signature API or verified
receipt, and cannot enter the existing delegated decoder or two-child permit.
Future signed reviewer decisions must bind reviewer identity, role and admitted
runtime as well as this context; no incomplete context-only approval is issued.

Independent frozen47 cases: baseline47 expected missing-API failures; candidate
47pass/0fail/0error/0skip, exact case IDs and stable source samples. Existing CI
retains50 controls and adds47 (97total); PR #2008 and exact main checks passed.
The pure correlation API above now recomputes B. Next qualify the existing-owner
signed-decision/provenance boundary before permit/provider integration. Registry/identity evidence
alone does not establish explicit effect approval. Native RSI remains unadmitted.

<a id="contract-046"></a>

### Decision and evidence

Select explicit effect-domain authorization; reject implicit conversion of a
delegated-work receipt into an effect permit. The implemented pure adaptation
covers **HIGH / worktree_create only**. ULTRA and live_enqueue remain outside
this adaptation; their existing request schemas are not removed or downgraded.

`reddog_elevated_authority_consensus_evidence._sovereign_matches` binds sovereign
evidence to a delegated request, work order and identities. Reviewer evidence
signs its exact consensus context. Neither the scoped producer search nor the
existing two-HIGH-child permit establishes authenticated approval of the later
effect target. This is an evidence gap; installed runtime state is unknown.

An authentic producer must explicitly authorize the precise effect binding.
Its principal authority, policy membership, independent reviewer evidence,
scope, expiry and revocation must be resolved through existing trusted owners.
A matching work-order ID, signed parent receipt, self-asserted approval or a
synthetic test fixture is insufficient. Producer admission remains blocked
until that provenance is independently qualified.

<a id="contract-047"></a>

### Digest and carrier contract

| Name | Meaning and existing owner | Binding and later handoff rule |
|---|---|---|
| E | `authoritative_use_effect_digest(kind, payload)` in `reddog_authoritative_use_lease_contract` | Exact worktree effect; retain queue/slice/work-order, plan and valve bindings. |
| T | `signer_secret_access_request_digest(request.to_dict())` in `reddog_signer_secret_access_grant_contract` | Complete canonical effect SigningRequest, including requester, signer/key epoch, generation, session/replay identity, nonce and lifetime through its payload. No proof inserted into the target. |
| P | `canonical_authority_request_digest(parent)` in `reddog_elevated_authority_consensus_contract` | Parent reference only. Its projection removes back-references; P alone grants no authority. |
| B | Domain-separated single-effect binding over P, T and E | Implemented pure structural contract in existing contract/evidence owners; cannot reuse the delegated signing-input projection C, which hashes a different request domain. |
| G | Existing `signer_secret_access_grant_id(grant)` | Grant continues to bind T, exact beneficiary, operation, tier and replay owner. Grant issuer/requester and effect beneficiary stay distinct. |

The B mapping has exactly `schema_version`,
`parent_authority_request_digest`, `target_signing_request_digest`, and
`effect_request_digest`. Schema label: `reddog_effect_target_binding.v1`.
Hash it with the existing strict canonical JSON digest. Recompute P/T/E from
validated inputs; never accept supplied digests as independent evidence. T must
be formed after the issuer's existing replay-store binding is final; later
rebinding invalidates B and requires fresh authorization, not digest rewriting.

The pure builder requires exact `DelegatedAuthorityRuntimeRequest` and
`SigningRequest` types, parent `requested_operation == "worktree_create"`,
and HIGH derived by
`delegated_authority_tier(parent)`; there is no parent `authority_tier` field.
Both effect `work_order_id` and `work_order_digest` must equal the parent.
Check canonical HIGH/worktree_create target shape, its existing freshness
rules, and a plain `expected_target` dictionary whose strict canonical JSON
digest equals that of `target.to_dict()`. Python Boolean/integer equality is
insufficient. `now` and parent timestamps must be exact integers, with
`issued_at <= now` and both declared identity/work-authority
expiries greater than now; target expiry must not exceed either declared expiry.
These are structural comparisons, not authenticated parent freshness or scope.
Caller-supplied expected values remain untrusted test or planning inputs. Do
not infer that the parent principal equals the actual effect requester:
that mapping needs separately authenticated evidence.

The future effect proof has a distinct explicit domain/version and travels
**outside** the effect target. The existing lease request builder leaves proof and consensus
absent; `_request_matches` explicitly checks only consensus absence. The implemented
pure binding requires typed `SigningRequest.elevated_consensus_proof is None`
and canonical `to_dict()` omission of that key. This additional binding check
does not change the existing lease validator. The future provider handoff must
obtain the outer grant's receipt digest from a
verified effect proof, not copy the target's `None` or fill it from an arbitrary
mapping. The grant signer must independently reverify the same B and exact T.
The v1 delegated rehydrator and generic permit must not accept this by widening
their roles. Final effect-proof fields and authenticated producer registration
are a later gate; the B mapping is not a completed proof schema.

<a id="contract-048"></a>

### Existing ownership and lifecycle

| Stage | Extend only after its preceding gate passes |
|---|---|
| Canonical binding | `reddog_authoritative_use_lease_contract`, `reddog_elevated_authority_consensus_contract` and `reddog_elevated_authority_consensus_evidence`: pure validation/correlation only. |
| Authentic authorization | Existing sovereign/policy/reviewer resolver and verification owners: bind fresh authorized effect context to B; preserve independent review and revocation. No producer is admitted by this plan. |
| Local handoff | Existing consensus capability and issuer/provider owners: separately typed single-target permit, exact provider/beneficiary binding; never repurpose the two-child delegated permit. |
| Grant boundary | Existing grant issuance/admission and consensus signer verification owners: explicit proof-domain dispatch, re-verification and existing durable reservation. |
| Effect consumption | Existing resolve-per-sign backend, lease rehydration and effect registries: retain grant consumption, generation fencing and one-use exact-effect consumption. |

Proposed expiry is the earliest applicable bound: effect target (at most30s),
effect approval, parent authorization, independent grant policy, current owner
generation/selection and grant TTL. Check at each use; a later stage never
extends an earlier expiry. Unknown bounds reject. Numeric/type and clock rules
must remain explicit; no implicit Boolean-to-integer coercion.

Local permit consumption and durable signer reservation are separate events.
Use one target per effect permit and an explicit effect-domain durable nonce
binding B plus receipt identity in the existing replay owner. Do not reuse the
delegated two-child nonce domain. Successful grant signing consumes its own
authorization; it is not proof the final effect ran. A downstream failure must
not remint an equivalent permit or erase prior consumption. Ambiguous cleanup
stops and records the attempt for reconciliation. Existing rollback attempts
can suppress errors; they do not establish all-failure restoration. Detailed
restart/recovery behavior must be qualified before issuer composition.

<a id="contract-049"></a>

### Layer gates and acceptance

1. **Current pure layer, 13/P1 (C2/I4/D4/Impact3):** 32 new cases were frozen
   before implementation in the existing canonicalization test owner, including
   independent golden P/T/E values, work-order/time correlation, exact expected
   target and B substitution, and valid HIGH/live_enqueue rejection. Baseline:
   32 expected missing-API failures. Candidate: 32 passes. Both had zero
   errors/skips and the same exact case IDs. The original four cases remain
   unchanged and are excluded locally because their fixture invokes a signing
   helper. Synthetic positives establish structural agreement only; the later
   proof schema is not parsed here. Hosted checks and publication remain pending.
2. Qualify authentic effect-specific authorization provenance and independent
   signer re-verification; only then adapt the typed permit/provider handoff.
3. Test disposable full issuer composition, one-use/restart/rollback outcomes,
   then the remaining resident/supervision prerequisites. Re-observe before
   admitting one worker. AmIBot remains downstream of that gate.
4. Measure a held-out baseline/candidate outcome and retained use on a later
   invocation before calling the result RSI improvement; worker count is not
   an improvement metric.

Do not repeat PR#2001's eleven negative controls as new progress. No new
orchestrator, registry, storage family or skill is selected. This layer does
not clear the seven remaining resident trust reasons or the supervisor blocker.
Canonical sequencing and closure evidence: `docs/roadmaps/rsi_swarm_backlog.json`,
historical observation `effect_proof_design_20261001`. Current local evidence:
`O:/Foundups-Agent-audits/20261001-rsi-effect-binding/`, including frozen
`test-plan.json`, baseline/candidate XML and receipts, and independent source/
execution gate `execution-review-candidate.json`. No retained RSI gain is claimed.

<a id="contract-050"></a>

## Effect-lease consensus qualification — 2026-10-01

The finite existing-owner qualification passed **11/11 local cases**, with zero
failures, errors or skips. HIGH/ULTRA effect requests are valid in their own
contract but cannot enter the actual independent grant provider without its
typed consensus permit. The client rejects the effect role, and the existing
delegated pair remains valid while effect substitutions fail. No production
policy was changed; this is measured rejection/domain evidence, not successful
issuer composition, native admission or retained RSI improvement.

The first attempt stopped at collection (exit4, one collection error, zero case
bodies): pytest accessed an empty package initializer omitted from the source
inventory. A separately reviewed retry added only that binding; all eleven
case IDs, expectations and production sources stayed fixed. No database opened
and no unexpected guard denial occurred on the retry. Downstream counters stayed
untouched except for the declared local clock/provider identity calls.

Existing CI now selects these exact eleven cases with namespace isolation and
the same Python audit constraints. Hosted results are recorded separately after
execution. These constraints are not OS isolation or general native containment;
model-framework imports are denied, while reviewed dependency imports remain.
Source hashes are sampled before/after. The inherited local receipt field
`loaded_source_bindings` includes hash-check reads and is **not an import trace**;
CI uses the accurate `observed_source_read_bindings` name.

Evidence: `O:/Foundups-Agent-audits/20261001-rsi-effect-consensus/` and canonical
backlog `current_observation.effect_consensus_qualification_20261001`.

Next WSP15 13/P1: Specify the existing-owner effect-lease consensus proof handoff before any compatibility repair. No runtime activation is granted.

<a id="contract-051"></a>

## Canonical unsigned effect request preparation

`ExternalSignerAuthoritativeUseLeaseIssuer.prepare_request(*, payload, authority_tier)`
returns the existing `SigningRequest` or `None`. It applies the same exact owner
types, four replay-store bindings and canonical builder used by `issue`; mismatched
supplied bindings reject. It does not mutate the input, read the clock, acquire
grants, call a signer, resolve generation authority or consume a nonce.

Use the returned request as the target data for the existing effect-binding
consumer. HIGH and ULTRA retain builder compatibility; pure effect correlation
still supports HIGH/worktree only. Preparation is neither freshness validation
nor an effect proof/permit. Later admission must verify the exact target again;
data equality is not authentication or an immutable lease. `issue` still captures
time before preparation and retains its existing provider/cleanup/error behavior.
The real elevated provider handoff and resident resolver remain uncomposed.

<a id="contract-052"></a>

## Effect-lease admission map — 2026-10-01

Source-only trace at `71e26ea598dae90865b16bf8dfd9eb9a34117088`; installed
runtime/configuration remains **unknown**. No authority, model, socket, service,
operational-store or application-test call was made. This map names existing
owners and composition prerequisites; it does not admit a worker.

| Boundary | Existing producer → consumer | Required evidence / present gap |
|---|---|---|
| Work identity | `reddog_main_resident_queue_serial_loop_bootstrap` → `GovernedValveUseTimeAuthorityResolver` | Exact queue/slice, full work-order/base digest, runtime root, trusted time and signed authority. No concrete selected runtime ticket was supplied or observed in this slice. |
| Generation | Root-owned manifest selection → `verify_signer_current_generation_runtime_binding` → use-time collector | Accepted typed evidence removes only three of ten named trust reasons. Binding verification consumes a selection capability; it is not a passive status probe. |
| Readiness | `reddog_resident_runtime_artifact_readiness` → canary readiness projection | Seven artifact files are checked; three generation reasons are added independently. This is not the resolver's complete reason set or authority. |
| Remaining trust | Existing consensus, sovereign, principal, model, Memex and peer owners → resolver | Five reasons remain after accepted generation, principal and live peer evidence. This does not mean every lower-level verifier is absent; authentic consumer composition remains unqualified. |
| Effect-lease request | `reddog_authoritative_use_lease_contract` → `ExternalSignerAuthoritativeUseLeaseIssuer` | Only HIGH/ULTRA; role `signer:authoritative-use-lease`. Builder and validator require absent consensus digest. |
| Grant handoff | External issuer → `IndependentSignerSecretGrantProvider.lease` | Issuer supplies no elevated-consensus permit. Real provider rejects non-LOW without a consumed typed permit before owner/grant work. Positive issuer tests substitute `_LeasedGrantProvider`; they do not prove this direct production pairing. |
| Permit domain | `prepare_elevated_authority_signing_permit` / `ElevatedConsensusExternalSignerClient` | Existing permit preparation binds exactly two HIGH principal/reddog requests and their consensus digest; client dispatch supports those roles. Adding a keyword alone cannot qualify the effect-lease role or ULTRA. Effect requests also hash the payload directly, while elevated canonical requests hash the signing-input mapping; these digest contracts are distinct. |
| Effect consumer | Resolver → valve handler → worktree/live-enqueue admission registries | Resolver currently returns `authoritative_use_lease=None`. Rejection reasons close the valve; registries require an opaque exact-effect/digest lease and consume it once. Serialized acceptance is insufficient. |
| Skill safety | `skill_runtime_admission.admit_runtime_skill` → registered skill executor | Exact bundle/manifest/scanner fingerprint is separate from signed per-effect permission. |
| External supervision | Root-selected supervisor observation + actual requester → existing lifecycle owner | Existing corrected contract still needs authenticated transport, canonical consumption and qualified visibility. Earlier strict-decoder candidates remain rejected; no retry or new parser is selected here. |

After accepted generation, principal and peer evidence, the five remaining
resolver anchors are consensus receipt, sovereign authorization, model signed-
evidence trust, model-selection verification and Memex signed-evidence verification. Other validation failures may also occur;
These counts describe named subsets, not every possible rejection.

`ExternalSignerAuthoritativeUseLeaseIssuer.issue` enters a grant lease, external
signing and response rehydration. Rehydration consumes durable replay state;
later effect use consumes the process-local one-use lease handle.
Do not use these calls as read-only probes. The existing
`load_system_service_signer_identity(owner_config_path, repo_root)` is a narrower
non-consuming identity reader, but requires an explicit root-owned absolute
owner-config path and Linux ownership checks. It was not called. Do not guess a
service/path, infer installation absence, or turn a test receipt into live authority.

**Next qualification, 13/P1 (C2/I4/D4/Impact3):** Qualify the existing elevated-consensus and effect-lease request domains before issuer/provider integration.
Freeze finite cases using actual existing issuer/provider/consensus leaves in
the existing test owners, with isolated fake outer dependencies and no service,
secret resolution or signing authority. First demonstrate the current rejection
and identify the exact supported domain. Then select a separately reviewed
contract repair only if justified. Preserve HIGH/ULTRA and independent consensus;
do not demote to LOW, fabricate permits, relax validators, or extend role/tier
coverage merely to make a test pass. Supervisor/transport and resident trust
prerequisites remain separate; no generic orchestrator or new authority registry.

Evidence: RSI backlog `current_observation.admission_prerequisites_20261001`,
`O:/Foundups-Agent-audits/20261001-rsi-admission-prerequisites/resident-map.json`
and `issuer-map.json`. Their hashes/source bindings distinguish this static
assessment from the earlier portable and native-call experiments.

<a id="contract-053"></a>

## Process visibility qualification boundary — 2026-09-27

PR1922's connected socket mapper is merged/main-verified at `d6f9458b` with252
candidate cases passing. Its public policy, backend, receipt and lifecycle APIs
remain unchanged in this test-only slice. Two hosted child conditions exercise
the existing private association seam; [test contract](../../tests/README.md#cross-process-visibility-qualification--2026-09-27).
Same-UID readability/denial does not satisfy the public distinct-requester rule
or supply authenticated supervisor policy. Keep PR_SET_DUMPABLE=0 and all existing
signer restrictions. No new receipt schema, issuer or execution authority.

<a id="contract-054"></a>

## Connected socket ownership observation — 2026-09-27

The existing `observe_external_signer_os_state` now associates process socket
FDs with pathname metadata using exact Linux `NETLINK_SOCK_DIAG` VFS replies.
The public policy, receipt v1 and lifecycle entry points are unchanged. The
backend protocol adds `current_pid()`, `monotonic()` and
`query_unix_socket(inode, cookie, timeout)`; unsupported custom backends reject.
The default backend uses bounded `scandir` and the private same-module
`_reddog_unix_socket_identity.py`. This is an observation, not policy issuance.

The former absolute no-socket restriction is narrowed explicitly: only local
kernel AF_NETLINK/SOCK_RAW/protocol4, exact per-inode request, no dump, kernel
address `(0,0)`, one4096-byte response and no retry. No target socket connection,
service control, namespace switch, key read, provider or authority grant.
The source-boundary test inspects both files; AST checks are not containment.

At most256 FD entries and16 unique socket candidates are inspected. Duplicate
FDs are deduplicated. Well-formed unrelated/no-VFS sockets and correlated
discovery ENOENT can be skipped; malformed replies and ambiguous matches reject.
VFS inode must fit u32; compare device major/minor without truncation. Matching
VFS requires AF_UNIX stream/listening state. A concrete returned cookie and the
original FD are checked on both sides of queries and reused in the second
observation; replacement discovery is forbidden there.

Require numeric `/proc/self` equals `getpid()`, singleton matching Pid/NSpid in
self/target status, and equal stable pid/net/mnt/user namespace handles. These
checks restrict support to the same procfs/PID/namespace view; they do not
authenticate supervision. A shared2-second acceptance deadline uses the
backend's monotonic-clock contract, with remaining receive time. Nonfinite or
expired values reject; this is not a hard wall-clock guarantee for blocking
kernel/filesystem calls or a detector for every injected backward-clock step.

Source prepared; exact source/hosted/main review remains required. Existing
process/path checks, audit-only receipt, seven resident reasons and absent
effect-use lease remain. Snapshots/cookies do not prevent every ABA, FD transfer,
exit or exec; cross-UID supervision and authentic policy issuance remain open.
The earlier characterization-only contract below is historical PR1921 scope.

<a id="contract-055"></a>

## Socket characterization boundary — 2026-09-27

Production observer, policy, receipt and lifecycle APIs are unchanged. Two
hosted-only cases in the existing observer test owner characterize kernel socket
inode/cookie to VFS inode/device association, unlink/rebind and wrong-cookie
rejection. See [fixed effects and oracles](../../tests/README.md#hosted-socket-identity-characterization--2026-09-27).
This is a qualification experiment, not the production bridge or supervisor.

The reviewed test request is exact NETLINK_SOCK_DIAG for held test-created FDs;
it does not expand the production observer's no-network boundary. The first
query discovers a cookie; repeated queries use that concrete cookie. Scope is
one process in its recorded namespaces; it cannot prove external signer process
ownership or prevent exit/exec/ABA after observation. The old inode-comparison
helper's outcome is diagnostic and is not an ownership acceptance criterion.
All seven resident trust reasons and `authoritative_use_lease=None` remain.

Implementation qualification still requires an explicitly reviewed production
consumer/boundary, malformed/foreign/truncated-input controls, namespace and
cross-process FD/lifetime handling. No successful synthetic or disposable-kernel
result alone admits a signer or native RSI worker.

<a id="contract-056"></a>

## External supervision source contract — 2026-09-27

**Corrected design merged in PR1924 at `1033310bc`; authenticated observation
transport, canonical consumer registration and deployment visibility remain
unimplemented.** PR1922 repaired
socket/VFS association; PR1923 qualified same-UID child visibility and denial.
Neither qualifies an authenticated supervisor or the full distinct-UID path.
This correction changes no API, process identity, privilege or service state.

**Backend qualification, 2026-09-28:** source review rejected dbus-fast 5.0.22
MessageBus (pre-auth/received-FD ownership), Jeepney 0.9.0 Parser (non-advancing
container parse), and dbus-fast's stream-only codec (missing strict consumed-byte
and wire-validity evidence). No package/runtime was exercised; this changes no
API or dependency pin. The existing owner must receive reviewed strict-decoder
evidence for complete frame/container consumption, terminator/header validity,
bounded malformed-length progress and usable interpreted/compiled APIs before
implementation can be selected. No parser fork, new grammar, third-library
search or unchanged retry is selected. The [canonical checkpoint](../../../../../docs/operations/RSI_SWARM_DISPATCH.md#manager-backend-qualification-closure--2026-09-28)
binds the findings, source identities and remaining separate runtime gates.

<a id="contract-057"></a>

### Three roles and the current source constraint

| Role | Responsibility and boundary |
|---|---|
| Isolated signer | Existing system-service entrypoint enforces distinct non-root signer identity, no CAP_SYS_PTRACE, no tracer, core dumps disabled and `PR_SET_DUMPABLE=0` before secret resolution. Preserve these controls. |
| Authenticated supervisor observer | Observe only the owner-selected signer instance with independently qualified OS visibility; authenticate observation provenance and lifetime. It is not the requesting principal and must not perform the requester's handshake. No such production observer transport is currently admitted. |
| Actual handshake requester | Unprivileged process running the canonical healthcheck. Its effective UID/GID maps through authenticated current-generation `peer_policy/uid_to_principal`; the signer attests the actual connecting peer. Neither012, work subject nor supervisor identity substitutes. |

`reddog_external_signer_os_observer._validate_policy` currently requires the
observer's actual UID/GID to equal `policy.requester_uid/gid`. The default
`reddog_external_signer_lifecycle_admission._verified_admission_values` calls
that observer and the healthcheck sequentially in one process. Running this
unchanged path in a supervisor either rejects requester identity or changes the
connecting principal. Merely adding policy fields cannot resolve this constraint.
Do not override backend identity, relabel the supervisor, grant requester ptrace
access, or relax signer dumpability to obtain a positive result.

Keep the current public observer and audit injection behavior. A future distinct
supervisor path must reuse the kernel observation primitives under an explicit
observer-identity contract, then authenticate their result at the existing
lifecycle owner. It must not pretend to be the default requester-local observer.

<a id="contract-058"></a>

### Source and ownership

`reddog_signer_system_service_manifest_selection_loader.py` remains the
authenticated root-owned configuration/generation owner, and
`reddog_signer_system_service_entrypoint.py` remains the isolated signer launch
owner. This code ownership does not make the signer process its own supervisor.
Public startup still has unavailable production dependencies. No installed
signer-specific unit, systemd version or privileged observation policy was
observed. Keep service startup and observation as separate process roles.

Choose read-only observation from an authenticated local systemd **system**
manager for an explicitly owner-selected, already-loaded service unit. Extend
the existing root-owned config through a versioned schema only when implementing;
exact v1-v4 schemas have no unit selector and must preserve compatibility and
unknown-field rejection. Never guess a unit, accept caller-selected PID/unit,
fall back to the user bus, or start/stop/reload/LoadUnit a service.

Require a qualified simple/exec main-process service, active/running state,
current nonzero `MainPID` and nonempty `InvocationID`, not historical ExecMainPID
or a control process. Pin the process with pidfd; verify unit/invocation through
`GetUnitByPIDFD` and reject manager-owner/lifetime changes. That method's systemd253
introduction does not prove deployed support. Systemd metadata and a pidfd do
not grant procfs visibility or authenticate a later observation handoff.

| Existing policy field | Expected provenance and binding |
|---|---|
| `pid`, `expected_process_start_identity` | Owner-selected current MainPID, boot ID/start ticks, pinned lifetime and repeated manager/unit/invocation checks. |
| `expected_signer_uid/gid` | Authenticated owner signer identity, checked against actual process credentials and kept separate from observer and requester roles. |
| `requester_uid/gid` | Actual healthcheck process effective identity and owner-selected peer mapping. These fields retain requester-local meaning; they are not supervisor identity fields. |
| `expected_executable`, `expected_executable_device/inode` | Current authenticated packet argv[0], owner-authorized launch path/argv and descriptor metadata compared with procfs before/after. This is not code-content attestation. |
| `socket_path`, `expected_socket_uid/gid/mode` | Current selected packet/config and explicit owner policy, protected ancestry, compatible namespaces and actual metadata. Fixture0600 is not production access policy. |
| `authority_receipt_id/source_id` | Future canonical issuer binding owner/config/generation/packet/session plus observer and signer-instance identities. Existing strings, unkeyed digests and serialized receipts confer no authority. |

<a id="contract-059"></a>

### Authenticated handoff and canonical consumption (specified, not wired)

The future producer belongs to the existing external-supervision owner above.
The consumer belongs to `reddog_external_signer_lifecycle_admission.py`: verify
the authenticated observation before `_verified_admission_values` accepts it
and before `_make_admit` issues a local capability. Keep the actual healthcheck
in the requester process. This names extension seams, not an implemented verifier
or a new parallel authority registry.

The current `_verified_os_policy` checks the shape of an injected
`ExternalSignerOsPolicyAuthorityBoundary.require` result; it does not authenticate
a canonical supervisor. `VerifiedExternalSignerOsPolicy` construction or the
observation receipt's digest verifier cannot close that gap. Implementation must
bind a concrete producer/consumer pair and independently verify authenticated
transport, owner-selected issuer identity and replay state. The existing
verified-outcome root-authority signing service is not an observation authority;
its presence does not admit reuse of its socket or keys for this purpose.

One attempt must correlate authenticated observer issuer identity, intended
requester UID/GID/principal, accepted signer profile/public key/epoch, manifest,
generation/revision, config and raw digests, packet/session, manager/unit/invocation,
PID/start/boot identity, executable, namespace views, socket VFS identity and
concrete socket cookie. Bind a fresh requester-generated challenge/attempt ID,
observation time and expiry to that exchange and the actual handshake result.
Reject mismatches; never infer expected identities from the offered observation.
Wire format, transport mechanism, trust provisioning, bounded deadlines and
replay-store ownership must be frozen and reviewed before implementation.

Lifecycle capabilities are sealed, registered, process-local objects; their
copy/serialization hooks reject. Do not mint one in the supervisor and send its
JSON to the requester. Authenticate the observation in the requester process,
then issue and consume the local capability through
`consume_verified_external_signer_lifecycle_admission`. A cross-process resident
would require its own explicit verified handoff; current handles are not portable.

`require_default_dependencies=True` currently means exact captured original
observer/healthcheck and no clock overrides in the private registry. A future
authenticated-supervisor route cannot pass this by callback injection, alias,
boolean, public attribute or receipt label. Qualify a deliberate canonical mode
in that existing registration/consumer path, preserving current default/audit
semantics and rejection behavior. Do not silently broaden the meaning of default.
Resident bootstrap and `GovernedValveUseTimeAuthorityResolver` are downstream
integration seams only; their supplier and lifecycle consumption are not wired.

<a id="contract-060"></a>

### One-attempt lifetime

1. Load authenticated owner/config/generation and independently select requester
   and accepted profile/public key/epoch. The current unprofiled resident
   generation collector is insufficient for that selection.
2. Authenticate observer transport/issuer and qualify actual procfs visibility
   without giving the requester additional privileges. Check compatible
   PID/user/network/mount views; do not reinterpret IDs or paths across namespaces.
3. Keep manager connection and pidfd alive across authenticated observation and
   the requester's actual handshake. Recheck generation/config, invocation,
   process/executable/credentials and socket before proof issuance. Restart, exit,
   PID reuse, exec, replacement, rotation, denied visibility or owner drift reject.
4. Consume only the locally issued capability, once and before expiry, after
   earlier queue/work checks. Preserve rejection-before-consumption for malformed
   identities/foreign boundaries and spending on valid owned identity mismatch.
   Release all resources on every result. Revalidate at use if time has passed;
   observation cannot prevent later exit/exec. The effect-bound lease is separate.

A connected-peer alternative remains more invasive: the current client closes
each roundtrip and discards peer PID. A preserved connection alone would still
not prove current executable, rightful service ownership or procfs visibility.
The external-manager design is retained with the missing handoff made explicit.

<a id="contract-061"></a>

### Socket ownership prerequisite — source defect, not a live incident

**Historical defect repaired by PR1922; this is not an outstanding inode fix.**
The old pathname-inode/FD-inode equality and fake202/202 assumption are gone.
The existing observer now uses exact bounded VFS/socket association and concrete
cookie/namespace continuity. PR1923 main `5578f7bd` additionally records a readable
same-UID child and a live nondumpable child rejected with real permission errors.
Its254 candidate cases passed in PR/main;252 parent cases were preserved. This
qualifies the recorded permission boundary, not production cross-UID supervision.
See [socket contract](../../INTERFACE.md#connected-socket-ownership-observation--2026-09-27) and
[future connected acceptance](../../tests/README.md#supervisor-requester-connected-acceptance--2026-09-27).

Before any issuer implementation, freeze the transport/verifier/replay owner and
deployment observation policy above. Then qualify the connected producer-to-local
lifecycle consumer with real requester correlation; do not add disconnected
positive policy fixtures or duplicate the existing requester-mismatch test.
All seven native trust reasons and `authoritative_use_lease=None` remain.

Primary source references retained from the original design:
[systemd manager](https://raw.githubusercontent.com/systemd/systemd/v256/man/org.freedesktop.systemd1.xml),
[pidfd lifetime](https://man7.org/linux/man-pages/man2/pidfd_open.2.html),
[Linux pathname bind](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/unix/af_unix.c),
[socket FD naming](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/socket.c),
[diagnostic VFS association](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/unix/diag.c).

<a id="contract-062"></a>

## Healthcheck requester selection — 2026-09-27

Only `requester_principal_id=None` requests default selection. The existing
healthcheck reuses `rehydrate_peer_credential_policy` and maps the connecting
process's effective UID, requiring its effective primary GID when `allowed_gids`
is nonempty. Missing effective-ID APIs, OS read errors, unknown UIDs and denied
GIDs return `signer_healthcheck_requester_invalid` before connector invocation.
An empty GID allow-list imposes no GID restriction. Real IDs, supplementary groups
and the first configured policy entry do not select the requester.

Valid explicit requesters bypass local inference; malformed explicit values do
not fall back. The existing server must still match the requested principal to
its kernel-attested peer. Local inference assumes compatible user namespaces
and unchanged credentials before connect; it is a routing hint, not attestation,
delegation or authenticated expected-requester provenance.

<a id="contract-063"></a>

### Resident handoff ownership (specified, not wired)

The existing signer-owned `peer_policy/uid_to_principal` remains the mapping
owner. A same-process lifecycle producer must select from the authenticated
current-generation config and the actual handshake process's effective identity.
If another process performs the handshake, the resident process's UID cannot
substitute: the admitted external lifecycle owner must supply the independently
bound requester expectation and authenticated observation for each attempt; the
requester-local lifecycle owner must issue the opaque handle after verification.
Never derive the expectation from the offered receipt, external012 or work subject.

Thread that existing-owner supply through resident bootstrap into
`GovernedValveUseTimeAuthorityResolver`, after early work/queue checks. Reuse the
accepted signer profile and correlate manifest, generation/revision, config/raw
digest, run-packet and session; consume once with
the current `require_default_dependencies=True` contract. A future authenticated
supervisor mode needs deliberate canonical registration as specified above;
it cannot masquerade as the current default observer. This is a future integration contract.
The healthcheck fix does not fill lifecycle's mandatory requester parameter or
wire this supplier. All seven resident trust reasons and the absent effect-use
lease remain. No new profile field, identity registry or launch API is introduced.

<a id="contract-064"></a>

## Lifecycle default-dependency requirement — 2026-09-27

`consume_verified_external_signer_lifecycle_admission` adds keyword-only
`require_default_dependencies: bool = False`. Omission/False retains the current
audit/one-use behavior. Non-bool values reject before consuming. With True,
the captured private registry must record the original default observer and
healthcheck callables plus no wall/monotonic overrides. Explicit original
callables and explicit None clocks qualify; wrappers/replacements and any
non-None clock value (including falsey values) do not. Rebinding module aliases
after factory creation cannot promote a replacement or demote captured defaults.
Unqualified selection raises `external_signer_lifecycle_default_dependencies_required`
before consuming the handle. Malformed identity and foreign-boundary guards still
precede consumption; a valid owned identity mismatch still spends the handle.

Factory signature, audit receipt schema/digests and false authority flags remain
unchanged. No public property, serialized label or caller declaration promotes
selection. The stricter flag requests an additional check; it cannot grant trust.
This metadata is not full manifest/OS/generation/cryptographic provenance,
continuous supervision or a hostile-Python boundary. No resident reason is
removed and no effect lease is issued; resident/bootstrap wiring remains separate.

<a id="contract-065"></a>

# OpenClaw Bridge Interface

<a id="contract-066"></a>

## Governed use-time supplier admission

`GovernedValveUseTimeAuthorityResolver.resolve(...)` requests current-generation
evidence only when signature re-verification succeeds and earlier artifact,
queue, recorded-authority and binding checks have no rejection. Rejected inputs
skip the injected trusted clock and generation verifier, retain all missing-anchor
diagnostics, and return no generation receipt. `signed_authority_reverified` still
reports the signature result independently. Generation evidence never supplies an
authoritative effect-use lease. See the existing execution-valve roadmap section.

<a id="contract-067"></a>

## YouTube scheduling command repair (2026-09-22)

`youtube action scheduling channel=move2japan preflight=true` checks transport
without launching or changing YouTube. Preview/apply requires `video_ids`;
the default `max_videos=0` includes all selected clips. Pass
`preserve_metadata=true` to retain prepared metadata. Structured CLI failure
remains failure even with subprocess exit zero. See the scheduler
[runbook](../../../../platform_integration/youtube_shorts_scheduler/docs/REMOTE_SCHEDULING.md)
and existing Work prototype boundary before enabling recent discovery.

<a id="contract-068"></a>

## Public RedDog Lick PoC

`PublicSessionGate.open_lick_encounter(...)` accepts the exact open-source,
non-biometric consent/profile shape for the `autopost` public surface and
returns a bearer plus random challenge. `complete_lick_challenge(...)` consumes
that challenge once and returns a provisional `reddog.lick.receipt.v1` plus the
existing turn nonce. Lick-bound turns reject until challenge completion.

The bearer and challenge are not identity or capability material. The receipt
is unsigned, states that identity and human presence are unverified, states
that no biometrics were collected, and always grants `none` authority. Existing
origin/subject binding, quotas, idle/absolute expiry, replay defense,
withdrawal, and effect ceiling remain authoritative. The optional HTTP router
adds `lick` and `challenge` operations but remains unmounted and undeployed.

Canonical product and deployment boundaries are in
`extensions/reddog/docs/REDDOG_LICK_CONNECTION_HANDSHAKE.md` and
`extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md`.


[Return to the interface directory](../../INTERFACE.md).
